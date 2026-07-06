# Phase 1 Implementation Plan — First Useful Conversion Workflows

Status: draft (2026-07-06). Source: `roadmap_vdbmat-utils.md`, Phase 1.
Target repository: `vdbmat-utils` (single distribution, `src/vdbmat_utils/`, as built in
Phase 0). Canonical spelling everywhere: `vdbmat` / `vdbmat-utils` (Decision Log,
2026-07-05).

## 1. Goal and Exit Criteria

Provide practical non-ML paths for producing valid `vdbmat` inputs.

Phase 1 is done when, from a clean checkout with the documented extras installed:

1. **Mesh workflow** — `vdbmat-utils voxelize-mesh <mesh.stl> --config <json> --out <dir> --name <name>`
   deterministically produces `<name>.voxels.json` + `<name>.material_id.npy` that pass
   `vdbmat-utils validate` and `vdbmat import-voxels`.
2. **Image-stack workflow** — `vdbmat-utils convert-image-stack <slices_dir> --config <json> --out <dir> --name <name>`
   does the same for a directory of labeled 2D slices.
3. **End-to-end** — at least one fixture from each workflow runs through
   `vdbmat import-voxels` → `vdbmat convert` (optical conversion) in an integration test
   marked `integration`, and this runs in CI.
4. **Diagnostics** — common failures (non-watertight mesh, undeclared gray level, missing
   slice, wrong dtype, palette mismatch) produce actionable single-line errors with exit
   code 1, and `preview-slices` / `material-counts` diagnostics work without OpenVDB or
   matplotlib.
5. Determinism, checksum stability, and axis-orientation tests pass on every workflow
   (see §8).

## 2. Inputs, Constraints, and Verified Facts

Facts verified against the working tree on 2026-07-06 — re-verify before starting:

- Phase 0 provides and Phase 1 must reuse (not duplicate):
  `build_material_label_volume` (`core/builder.py`), `GeneratorConfig` /
  `config_digest` (`core/config.py`), `rng_from_seed` / `spawn_rngs` (`core/seeds.py`),
  `build_provenance` (`core/provenance.py`), `write_asset` (`io/writer.py`),
  error hierarchy rooted at `VdbmatUtilsError` (`core/errors.py`), compatibility gate
  `require_compatible_volume_schema` (`core/compat.py`), and the argparse CLI in
  `cli/main.py` (subcommands `inspect`, `validate`, `generate-fixture`).
- `vdbmat` is a pinned editable path dependency (`[tool.uv.sources]`, ADR-0001). Its CLI
  exposes `import-voxels`, `convert`, `mapping-digest`, `inspect`, `validate`, `run`,
  `export`.
- The image-stack generator to migrate is
  `vdbmat/tools/image_stack_generator/generate.py` (269 lines, PGM P5/P2 input, gray→
  material-level config JSON, ADR-009 D2 reference generator). It has no public API and
  no tests of its own in that location.
- `vdbmat/.local/memo_stltovoxel.md` (added 2026-07-06) records that a complete mesh
  path — STL reader, winding-number voxelizer, topology validation, and tests — existed
  in `vdbmat` and was deleted; the last commit containing it is `8f55562`
  (`git show 8f55562:src/vbdmat/voxelize/mesh.py` etc.; note the old `vbdmat` spelling
  in historical paths). **The mesh work in this phase is a port of that recovered code,
  not a reimplementation.** Design rationale lives in the historical
  `docs/adr/0006-phase1-inputs-and-voxelization.md`.
- Backward compatibility is explicitly **not** required (user decision, 2026-07-06):
  prefer breaking changes, and delete superseded tools outright rather than stubbing or
  keeping equivalence shims.
- Extras `mesh`, `image`, `vdb`, `preview` already exist in `pyproject.toml` as empty
  lists; Phase 1 fills `mesh` and `image` and leaves the base install dependency-free
  beyond `numpy` + `vdbmat` (Principle 5).

## 3. Fixed Design Decisions

Settle these now so implementation does not re-litigate them.

### D1. Module layout (no package split)

Stay in the single distribution; add subpackages with imports flowing toward `core`:

```text
src/vdbmat_utils/
  mesh/
    __init__.py        # public: MeshVoxelizeConfig, voxelize_mesh, load_mesh
    loader.py          # STL (binary+ASCII) reading -> TriangleMesh
    voxelizer.py       # triangle mesh -> uint16 label array
    types.py           # TriangleMesh dataclass
  image/
    __init__.py        # public: ImageStackConfig, convert_image_stack
    pgm.py             # PGM P5/P2 reader (ported)
    png.py             # PNG reader via Pillow (extra: image)
    stack.py           # slice assembly, level mapping, validation
  preview/
    __init__.py        # public: slice_ascii, slice_pgm, material_counts
  cli/main.py          # extended with the new subcommands
```

`mesh` and `image` must not import each other; both may import `core`, `io`, `preview`.
Enforce with a unit test that walks module imports (cheap AST check), not with tooling
additions.

### D2. Dependencies and extras

- `mesh` extra: **no third-party mesh library.** The STL reader is ported from the
  historical `src/vbdmat/io/mesh.py` (`git show 8f55562:src/vbdmat/io/mesh.py`), which
  is already dependency-free and handles binary/ASCII including the "binary file that
  starts with `solid`" case. OBJ/PLY/glTF are explicitly out of scope for Phase 1
  ("deliberately narrow set of mesh formats first"). Record this as an ADR (see D7).
- `image` extra: `pillow>=10` for PNG input only. PGM keeps the ported zero-dependency
  reader so the base image workflow works without the extra.
- `preview`: stays empty; Phase 1 previews are text/PGM output using only NumPy.

### D3. Voxelization semantics (port of the deleted `vdbmat` mesh path)

Adopt the recovered implementation's semantics wholesale (memo + historical ADR-006);
deviate only where noted. Key rules, restated so the port can be reviewed against them:

- **Sampling rule: dense cell-centre classification.** Cell `(z, y, x)` gets the
  foreground material iff its centre is inside (or on the surface of) the mesh. Centres
  lie at `origin + (i + 0.5) * voxel_size` per axis.
- **Inside test: signed winding number along a +X ray** — sum of oriented triangle
  crossings per cell centre; inside iff `|winding| >= 0.5`. Requires watertight,
  consistently oriented input (enforced by D3-topology below). Triangles nearly
  parallel to the X axis (tiny YZ-projected `denom`) are excluded by the `facing` mask;
  the surface test compensates for them.
- **Closed-solid rule:** cell centres *on* the surface are inside. Detected by
  `_points_on_surface()`: plane distance `_SURFACE_TOLERANCE_M = 1e-9` + barycentric
  containment.
- **Numerical jitter:** YZ sample points get sub-voxel offsets
  `_SAMPLE_JITTER_Y = 7.3e-5`, `_SAMPLE_JITTER_Z = 3.1e-5` (fractions of voxel size;
  deliberately different per axis so samples cannot stay on a 45° triangulation
  diagonal). Jitter applies **only** to the barycentric surface test; winding X-crossings
  are evaluated at the unjittered centre. Preserve these constants and this split
  exactly — they encode debugged behavior.
- **Units:** STL is unitless; `source_unit` (`"m"` | `"mm"`) is a **required** config
  field with no default. The mm and m representations of the same shape must produce
  identical grids (regression test preserved from the old suite).
- **Axis order:** array is `z, y, x` (canonical). `placement` (4×4 rigid, default
  identity) is composed with the derived origin translation as
  `placement @ translation(origin)` to form the manifest's `local_to_world`.
- **Domain bounds:** auto-fit = mesh AABB snapped to whole cells with
  `_DOMAIN_SNAP_EPS = 1e-6` (absorbs float32 STL rounding so the grid does not gain a
  spurious cell), then `padding_cells` (default 1) added on all sides. Explicit
  `domain_min_m`/`domain_max_m` override remains available (both or neither).
- **Size guards:** per-axis and total cell-count limits, ported but made configurable
  (`max_axis_cells: int = 128`, `max_total_cells: int = 2_000_000`); exceeding them is
  an explicit error suggesting a coarser voxel size. The dense method is
  O(cells × triangles); `_points_on_surface` is the known hotspot — do not optimize it
  in Phase 1 beyond what the port already does.
- **Material assignment:** exactly one foreground material per mesh (config `material`
  block with `material_id`, `name`, `role`) plus one background (default
  `{"material_id": 0, "name": "air", "role": "background"}`). Multi-mesh composition is
  Phase 2.
- **Topology validation (`inspect_topology`, ported):** accept only watertight,
  consistently oriented, single-connected solids. Steps: (1) vertex weld at tolerance
  `max(scale, 1) * 1e-9` via integer keying + `np.unique`; (2) reject degenerate faces
  (duplicate welded vertices, area ≤ `(max(scale,1))² * 1e-18`); (3) undirected edges
  must have exactly 2 faces (1 = open, ≥3 = non-manifold) and each directed edge must
  appear once per orientation; (4) union-find over shared edges must yield one
  component (multiple solids rejected). No `allow_open_mesh` escape hatch — invalid
  topology is always an error (matches the old contract; composition workflows come
  later).

### D4. Image-stack semantics

Port the existing tool's contract unchanged, then extend:

- Slices stack in ascending filename order as z = 0, 1, …; rows → +Y, columns → +X
  (unchanged from the tool).
- Every gray value present must be declared in `levels`; undeclared values raise
  `ImageStackError` naming the value and the first offending file/pixel (unchanged).
- All slices must share one shape and one bit depth; a missing index in a
  numerically-named sequence (`slice_0003.pgm` … gap … `slice_0005.pgm`) is an error —
  interpolation is Phase 2, not Phase 1.
- New over the old tool: config gains `voxel_size_xyz_m` (kept), plus optional
  `local_to_world` (4×4 rigid), `name`/`role` per level (kept), and formats PGM + PNG
  (grayscale 8-bit; PNG requires the `image` extra with a clear error otherwise).

### D5. Configuration files

Both workflows use frozen-dataclass configs subclassing `GeneratorConfig` (so canonical
JSON, digest, and seed handling are inherited). CLI accepts `--config <path.json>`;
individual flags (`--voxel-size`, `--material-id`, …) override config fields, and the
*effective* config (post-override) is what gets digested into provenance. Neither
workflow consumes randomness in Phase 1; `seed` stays at its default 0 and is still
digested (documented as reserved).

### D6. Generator identity

- Mesh: `generator="vdbmat-utils.mesh.voxelize"`, version starts at `"0.1.0"`,
  provenance `sources=(f"sha256:{digest-of-mesh-bytes}",)` and `identity` passed to
  `write_asset` as the mesh file's SHA-256.
- Image: `generator="vdbmat-utils.image.stack"`, version `"0.1.0"` (fresh identity; no
  compatibility claim with the deleted `vdbmat-image-stack` tool), `sources` = per-slice
  digests in stack order, `identity` = SHA-256 over the concatenated slice digests plus
  config digest.
- Bump the version whenever output for the same inputs changes byte-wise; this is the
  documented rule from `docs/determinism.md`.

### D7. ADRs to write during this phase

- ADR-0004: STL-only, dependency-free mesh loading for Phase 1, ported from the
  historical `vdbmat` reader (D2/D3).
- ADR-0005: adoption of the recovered winding-number cell-centre voxelization semantics
  (D3), citing historical ADR-0006 of `vdbmat` and the constants preserved verbatim.
- ADR-0006: image-stack migration contract and PNG extension (D4), including the
  **deletion** of `vdbmat/tools/image_stack_generator` (see Step 5).

## 4. Implementation Steps

Execute in order; each step ends with `ruff check`, `mypy`, `pytest` green and a short
report under `.devdocs/vdbmat-utils/reports/phase1/` (follow the phase0 report style).
Commit per step.

### Step 0 — Preview and diagnostics module (no new deps)

Previews come first because every later step uses them in its own verification.

1. `preview/__init__.py` exposing:
   - `material_counts(volume) -> dict[int, int]` — voxel count per material id,
     including background, computed with `np.unique`.
   - `slice_ascii(volume, axis: Literal["z","y","x"], index: int) -> str` — one
     character per voxel (`.` for background role, `0-9a-z…` cycling by material id),
     with an axis/orientation legend line (`+x →`, `+y ↓` etc.) so transposes are
     visible to the eye.
   - `slice_pgm(volume, axis, index, path)` — grayscale PGM where each material id maps
     to a distinct, deterministic gray level; reuses no external libs.
2. CLI subcommands:
   - `vdbmat-utils material-counts MANIFEST [--json]`
   - `vdbmat-utils preview-slices MANIFEST --axis z --index 4 [--out FILE.pgm]`
     (no `--out` → ASCII to stdout; `--index` defaults to the middle slice).
3. Tests (`tests/unit/test_preview.py`): counts on the Phase 0 fixture presets;
   ASCII output golden-tested against an asymmetric fixture so any axis flip changes
   the golden text; PGM output byte-golden.

### Step 1 — Image-stack core port

1. Copy `read_pgm` and the level-mapping/stacking logic from
   `vdbmat/tools/image_stack_generator/generate.py` into `image/pgm.py` and
   `image/stack.py`, refactored to:
   - raise `ImageStackError(VdbmatUtilsError)` (new, in `core/errors.py` style —
     define it in `image/__init__.py` to keep `core` generator-agnostic);
   - build the volume via `build_material_label_volume` + `build_provenance`
     (replacing the tool's direct `MaterialLabelVolume` construction);
   - accept an in-memory API: `convert_image_stack(slices_dir: Path, config: ImageStackConfig) -> MaterialLabelVolume`.
2. `ImageStackConfig(GeneratorConfig)`: `voxel_size_xyz_m: tuple[float, float, float]`,
   `levels: tuple[dict, ...]` (gray, material_id, name, role), optional
   `local_to_world`, `format: "pgm" | "png" = "pgm"`.
3. Unit tests (`tests/unit/test_image_stack.py`), writing tiny slices into `tmp_path`:
   P5 and P2 parsing, correct z/y/x placement (asymmetric 2×3×4 stack whose expected
   array is written out literally in the test), undeclared gray value, shape mismatch,
   empty directory, missing sequence index, duplicate `material_id` across levels,
   duplicate gray values.

### Step 2 — Image-stack CLI, PNG, and end-to-end

1. CLI: `convert-image-stack SLICES_DIR --config CONFIG --out DIR --name NAME`
   with overrides `--voxel-size X Y Z` and `--format pgm|png`; on success print the
   manifest path and the material-count summary (reusing Step 0).
2. `image/png.py` behind the `image` extra (`pillow`); import lazily inside the
   function and raise
   `ImageStackError("PNG input requires the 'image' extra: pip install 'vdbmat-utils[image]'")`
   on `ImportError`. Reject non-grayscale and >8-bit PNGs explicitly.
3. Fixture: check in a deterministic generator (not binaries) at
   `src/vdbmat_utils/fixtures.py` or `tests/` helper that writes a small labeled stack
   (asymmetric features, ≥3 materials, one background) used by unit, contract, and
   integration tests alike.
4. Contract tests (`tests/contract/`): byte-equal double run (determinism), checksum
   stability golden (record the manifest's payload digest as a constant), palette/count
   conservation (counts in slices == counts in volume, per material).
5. Integration test (`tests/integration/`, marker `integration`): generate → run
   `vdbmat import-voxels` → `vdbmat convert` via `subprocess`, assert exit 0 and that
   the optical Zarr exists. Mirror the invocation style of the existing
   `tests/integration/test_import_voxels.py`.

### Step 3 — Mesh loader and voxelizer core (port from git history)

0. Recover the sources first and keep copies for review in the step report's scratch
   area (not committed):
   `git -C vdbmat show 8f55562:src/vbdmat/io/mesh.py`,
   `git -C vdbmat show 8f55562:src/vbdmat/voxelize/mesh.py`,
   `…voxelize/errors.py`, `…io/errors.py`,
   `git -C vdbmat show 8f55562:tests/voxelize/test_mesh_voxelize.py`, the io/mesh unit
   tests, and `docs/adr/0006-phase1-inputs-and-voxelization.md`. Verify the memo's
   claims (constants, guards, jitter split) against the recovered code; the code wins
   where they disagree, with the delta noted in the step report.
1. Port `io/mesh.py` → `mesh/loader.py` (+ `mesh/types.py` for the mesh dataclass as
   recovered). Keep the binary-detection-by-exact-length rule and the tolerant ASCII
   parser. Rename errors into the utils hierarchy: `MeshReadError` /
   `MeshTopologyError` / `VoxelizationError` become subclasses of `VdbmatUtilsError`,
   defined in `mesh/__init__.py`.
2. Port `voxelize/mesh.py` → `mesh/voxelizer.py` with these adaptations and no
   algorithmic changes (D3):
   - output via `build_material_label_volume` + `build_provenance` + `write_asset`
     instead of the old core-internal writer;
   - configuration comes from `MeshVoxelizeConfig` (below) modeled on the old
     `MeshVoxelizationSettings` (`source_unit`, `voxel_size_xyz_m`, `material_id`,
     `material_name`, `placement`, `padding_cells`);
   - size guards become config fields per D3;
   - keep `inspect_topology` as a public function (`mesh/topology.py` if it was a
     separate concern in the original; otherwise leave it in the voxelizer module as
     recovered).
3. `MeshVoxelizeConfig(GeneratorConfig)`: `source_unit: "m" | "mm"` (required, no
   default), `voxel_size_xyz_m`, `material: {...}`, `background: {...}`, optional
   `domain_min_m`/`domain_max_m` (both or neither), `padding_cells: int = 1`, optional
   `placement` (4×4 rigid), `max_axis_cells: int = 128`,
   `max_total_cells: int = 2_000_000`.
4. Port the old test suite into `tests/unit/test_mesh_loader.py` /
   `test_voxelizer.py`, preserving at minimum the analytic cases the memo calls out:
   cube with known volume, **mm/m unit equivalence producing identical grids**,
   degenerate-face rejection, open-mesh rejection, non-manifold rejection,
   multi-solid rejection, float32-rounding domain-snap case. Add what the old suite
   lacked: anisotropic voxel sizes, non-identity `placement` (90° rotation → transform
   is metadata, voxel-local array unchanged), and size-guard errors.

### Step 4 — Mesh CLI, fixtures, and end-to-end

1. CLI: `voxelize-mesh MESH --config CONFIG --out DIR --name NAME` with overrides
   `--source-unit m|mm`, `--voxel-size X Y Z`, `--material-id`, `--material-name`,
   `--padding` (mirroring the old `vbdmat voxelize` argument set, recoverable via
   `git show 8f55562:src/vbdmat/cli/main.py`); success prints manifest path, material
   counts, and shape; failures per §1.4.
2. Deterministic STL fixtures generated in-code (a function emitting the cube and an
   asymmetric L-bracket as bytes) — no binary blobs in git.
3. Contract tests: double-run byte equality; payload-digest golden; **orientation
   fixture** — the L-bracket voxelized, then `slice_ascii` golden on all three axes so
   any z/y/x confusion in the voxelizer changes visible text.
4. Integration test: L-bracket → `voxelize-mesh` → `vdbmat import-voxels` →
   `vdbmat convert`, marker `integration`.

### Step 5 — Delete the superseded vdbmat tool

Only after Step 2's contract tests are green (roadmap: "when its public API and
compatibility tests are ready"). Backward compatibility is not required — delete, do
not deprecate:

1. In `vdbmat`: delete `tools/image_stack_generator/` entirely. Grep `vdbmat` for
   references (at least `docs/adr/0009-…` and `docs/phase0-feasibility-report.md`
   mention stacks) and update them to point at `vdbmat-utils convert-image-stack`;
   historical ADR text itself stays as written, only forward-looking references change.
2. No equivalence test against the old tool's output — the new generator's own contract
   tests (Step 2.4) are the source of truth. The old behavior remains recoverable from
   git history if ever needed.
3. This is a cross-repo change: commit in `vdbmat` separately, then bump the pinned
   dependency per ADR-0001's procedure.

### Step 6 — Documentation, CI, and phase close-out

1. Docs in `vdbmat-utils/docs/`: `voxelization.md` (D3 semantics, tie rule, domain
   fitting, worked example), `image-stacks.md` (D4, config schema, example),
   `previews.md`; update `README.md` quick-start with both workflows; write
   ADRs 0004–0006.
2. CI (`.github/workflows/ci.yml`): add a "Phase 1 exit criteria" step running both
   workflows end to end (mirroring the Phase 0 step); add a matrix leg that installs
   **without** extras and asserts the base install + PGM workflow + previews still
   pass (Principle 5 / minimal-install risk).
3. Update `roadmap_vdbmat-utils.md` Phase 1 status block (as was done for Phase 0) and
   record any upstream `vdbmat` follow-ups discovered.

## 5. Test Matrix Summary (roadmap bullet coverage)

| Roadmap requirement | Where covered |
| --- | --- |
| Watertight and invalid meshes | Step 3.4 (topology-rejection cases), Step 4.3 |
| Boundary behavior | Step 3.4 (closed-solid surface rule, domain-snap case), `docs/voxelization.md` |
| Axis orientation | Step 0.3 golden ASCII, Step 4.3 orientation fixture |
| Checksum stability | Steps 2.4 and 4.3 payload-digest goldens |
| Material conservation | Step 2.4 (slice counts == volume counts) |
| End-to-end optical conversion | Steps 2.5 and 4.4 (`integration` marker) |
| Explicit material/voxel-size/transform/bounds/background | D3–D5 configs + unit tests |
| Previews without OpenVDB | Step 0 |

## 6. Out of Scope (defer explicitly)

- OBJ/PLY/glTF loading; mesh repair; conservative or fractional voxel coverage;
  multi-material mesh composition (Phase 2 booleans); slice interpolation/morphing
  (Phase 2); OpenVDB anything (Phase 5); performance work — in particular the known
  `_points_on_surface` hotspot stays as ported (benchmark first, per Principle 7; the
  configurable size guards bound the damage in the meantime).

## 7. Risks Specific to This Phase

- **Port drift:** rewriting instead of porting would silently change the debugged
  numerics (jitter constants, snap epsilon, facing mask). Mitigation: Step 3.0 recovers
  the exact sources and tests first, and the ported analytic tests (cube volume, mm/m
  grid equivalence) pin behavior.
- **Historical spelling:** recovered code uses `vbdmat` module paths and names; rename
  mechanically to `vdbmat_utils` conventions during the port and let mypy/ruff catch
  stragglers.
- **Cross-repo deletion (Step 5)** touches `vdbmat`; keep it last and independent so
  Phase 1 exit does not block on `vdbmat` review, and remember the old tool remains in
  git history if anything was missed.
