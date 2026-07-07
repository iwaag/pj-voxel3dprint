# Phase 2 Implementation Plan — Image Morphing and Volume Composition

Status: draft (2026-07-07). Source: `roadmap_vdbmat-utils.md`, Phase 2.
Target repository: `vdbmat-utils` (single distribution, `src/vdbmat_utils/`, unchanged from
Phases 0–1). Canonical spelling everywhere: `vdbmat` / `vdbmat-utils`.

## 1. Goal and Exit Criteria

Support authored volumetric structures that are not direct mesh voxelizations: interpolation
and morphing between labeled 2D slices, and a set of label-safe volume operations that can be
composed from configuration without custom Python scripts.

Phase 2 is done when, from a clean checkout with no extras installed:

1. **Morph workflow** — `vdbmat-utils morph-stack <slices_dir> --config <json> --out <dir> --name <name>`
   deterministically produces `<name>.voxels.json` + `<name>.material_id.npy` from a *sparse*
   set of labeled key slices (e.g. z = 0, 8, 20), interpolating the intermediate slices while
   preserving discrete material IDs, and the result passes `vdbmat-utils validate` and
   `vdbmat import-voxels`.
2. **Pipeline workflow** — `vdbmat-utils apply-pipeline --config <pipeline.json> --out <dir> --name <name>`
   loads one or more input assets, applies a configured sequence of operations (crop, pad,
   resample, transform, mask, boolean composition, material remapping), and writes a
   contract-valid asset — with no Python authored by the user.
3. **Label safety is structural** — no code path can interpolate or average `material_id`
   values as numeric intensities: label arrays and continuous scalar fields have distinct
   types, and the only scalar→label conversion is an explicit, tested quantization step.
4. **Documented semantics** — topology changes, missing slices, label conflicts, and
   interpolation outside the source domain each have a documented, deterministic, tested
   behavior (`docs/morphing.md`, `docs/volume-ops.md`).
5. **End-to-end** — at least one morphed fixture and one composed (boolean) fixture run
   through `vdbmat import-voxels` → `vdbmat convert` in tests marked `integration`, and a
   "Phase 2 exit criteria" CI step runs both CLI workflows, including on the minimal-install
   leg (Phase 2 adds **no** new runtime dependencies; see D2).
6. Determinism (byte-equal double run), payload-digest goldens, and axis-orientation ASCII
   goldens pass for both workflows (§8-style matrix in §5).

## 2. Inputs, Constraints, and Verified Facts

Facts verified against the working tree on 2026-07-07 — re-verify before starting:

- Phase 1 provides and Phase 2 must reuse (not duplicate):
  `build_material_label_volume` (`core/builder.py` — enforces 3-D `uint16` z,y,x, builds
  `GridGeometry`/`MaterialPalette` from `vdbmat.core` types), `GeneratorConfig` /
  `config_digest` / canonical-JSON rules (`core/config.py`), `rng_from_seed` / `spawn_rngs`
  (`core/seeds.py`), `build_provenance` (`core/provenance.py`), `write_asset` (`io/writer.py`),
  the error hierarchy rooted at `VdbmatUtilsError` (`core/errors.py`: `ConfigError`,
  `GeometryError`, `PaletteError`, `CompatibilityError`), the compatibility gate
  (`core/compat.py`), previews (`preview/`: `material_counts`, `slice_ascii`, `slice_pgm`),
  and the slice readers (`image/pgm.py`, `image/png.py`) plus level-mapping helpers in
  `image/stack.py` (`_parse_levels`, `_read_slice`, `stack_identity`).
- The CLI (`cli/main.py`, argparse) already has `inspect`, `validate`, `generate-fixture`,
  `material-counts`, `preview-slices`, `convert-image-stack`, `voxelize-mesh`. New
  subcommands extend the same parser; success/failure conventions (manifest path +
  material-count summary on success; single-line actionable error, exit 1 on failure) are
  fixed by Phase 1 and must be matched.
- Loading an existing asset for pipeline input: `vdbmat` exposes the manifest reader used by
  `inspect`/`validate`. Confirm the exact public read API in `vdbmat` at step start (Step 0.0)
  and reuse it — do not write a second manifest parser (Principle: no competing contract
  definition). If only a private reader exists, raise an upstream `vdbmat` follow-up and wrap
  it in one place (`io/reader.py`).
- Import-flow rule from Phase 1 (`tests/unit/test_import_isolation.py`): subpackages must not
  import each other laterally; everything flows toward `core`. New subpackages (`ops`,
  `morph`, `pipeline`) join that test.
- Backward compatibility is **not** required (user decision, 2026-07-06): breaking changes
  preferred; delete superseded code rather than shimming.
- No new extras are expected; base install stays `numpy` + `vdbmat` (Principle 5). In
  particular **scipy is not added** — the distance transform is implemented in-repo (D4).

## 3. Fixed Design Decisions

Settle these now so implementation does not re-litigate them.

### D1. Module layout

```text
src/vdbmat_utils/
  ops/
    __init__.py        # public re-exports + OpsError(VdbmatUtilsError)
    crop_pad.py        # crop, pad
    resample.py        # nearest-neighbor label resample
    transform.py       # flips, 90° rotations, placement (metadata) updates
    mask.py            # apply_mask
    boolean.py         # compose (union / intersect / subtract)
    remap.py           # remap_materials
    palette.py         # palette merge/derivation helpers shared by the ops above
  fields/
    __init__.py        # ScalarField dataclass + FieldError
    edt.py             # exact Euclidean distance transform (Felzenszwalb–Huttenlocher)
    quantize.py        # the ONLY scalar→label conversion (thresholds → material ids)
  morph/
    __init__.py        # public: MorphStackConfig, morph_stack; MorphError
    keyslices.py       # key-slice discovery, gap analysis, per-slice level mapping
    interpolate.py     # per-label SDF interpolation between key slices
  pipeline/
    __init__.py        # public: PipelineConfig, run_pipeline; PipelineError
    registry.py        # op-name → implementation + parameter-schema registry
    engine.py          # load inputs, apply steps, provenance accumulation
  cli/main.py          # extended with morph-stack, apply-pipeline
  io/reader.py         # single wrapper around the vdbmat manifest read API (if needed)
```

Import direction: `morph` may import `fields`, `image`, `ops`, `core`, `io`; `pipeline` may
import `ops`, `morph`, `core`, `io`, `preview`; `ops` and `fields` may import only `core`.
`ops` must not import `morph`/`pipeline`; `fields` must not import anything label-typed
except for `quantize.py`'s output construction. Extend `test_import_isolation.py` accordingly.

### D2. Dependencies

None added. The exact 1-D squared-distance transform (Felzenszwalb & Huttenlocher 2012,
lower-envelope-of-parabolas algorithm) is implemented in `fields/edt.py` with NumPy, applied
separably per axis with anisotropic voxel sizes as axis weights. It is O(n) per row, exact,
and deterministic — no scipy, no floating-point-order ambiguity beyond IEEE ops in a fixed
loop order. Pure-Python row loops are acceptable at Phase 2 volume sizes (size guards below);
do **not** optimize with Numba/C in this phase (Principle 7; Phase 5 owns acceleration).

### D3. Label-safety type split (roadmap: "never accidentally interpolated")

- Label data stays `MaterialLabelVolume` / `uint16` arrays. **No function in `ops/`,
  `morph/`, or `pipeline/` may cast a label array to float or call any interpolating
  routine on it.** Enforced three ways:
  1. `fields.ScalarField` — frozen dataclass `(values: float64 zyx array,
     voxel_size_xyz_m, local_to_world)` with no palette; the type systems keeps float data
     out of label APIs and vice versa (mypy-checked signatures).
  2. `fields/quantize.py::quantize_to_labels(field, thresholds) -> uint16 array` is the only
     sanctioned conversion; everything else must go through it.
  3. A unit test walks the AST of `ops/` and `morph/` and fails on calls to
     `astype(float…)`, `np.interp`, `ndimage`-style names, or arithmetic mean/multiply on
     names bound to `material_id` — cheap lint-style guard, same spirit as the Phase 1
     import-isolation test. Interpolation of *distance fields* (which are `ScalarField`
     data) is where all smoothness lives.
- Label resampling is **nearest-neighbor only** in Phase 2 (D5). Smooth label rescaling via
  per-label SDF resampling is possible with the same machinery but deferred; note it in
  `docs/volume-ops.md` as future work.

### D4. Morphing semantics (per-label SDF interpolation)

The algorithm, fixed so review has a spec to check against:

- **Input:** a slice directory as in Phase 1's image-stack contract (PGM/PNG, levels config),
  except filenames declare *key-slice z indices*: `slice_0000.pgm`, `slice_0008.pgm`, … The
  numeric suffix **is** the z index in the output volume. `z_count` in config sets the total
  depth; it must be ≥ max index + 1, and defaults to max index + 1.
- **Per-label signed distance:** for each key slice and each material id `m` present anywhere
  in the stack (background included), compute the 2-D signed EDT of the mask `label == m`
  (negative inside, positive outside, in metres using `voxel_size_xyz_m[0:2]`). A label
  absent from a key slice gets distance `+inf` everywhere on that slice — this is the
  documented "appears/disappears" rule.
- **Interpolation:** for output slice z between consecutive key slices `z0 < z < z1`,
  interpolate each label's distance linearly in z:
  `d_m(z) = (1-t)·d_m(z0) + t·d_m(z1)`, `t = (z-z0)/(z1-z0)`. `(1-t)·inf` follows IEEE
  (stays `+inf` for t<1), which yields the intended behavior: a label present on one side
  only shrinks to nothing as t→ the absent side, changing topology cleanly.
- **Label resolution:** each output pixel takes
  `argmin_m d_m(z)` (the most-inside label). Ties are broken by **lowest material_id** —
  deterministic and documented. If no label has `d_m(z) < 0` at a pixel, the pixel gets the
  configured `background` material (this covers the all-`+inf` and "gap between shapes"
  cases). Key slices themselves are emitted verbatim from the input, not re-derived, so
  key-slice pixels are byte-faithful to their source images (regression-tested).
- **Topology changes:** are allowed and are an *emergent* property of SDF interpolation
  (merge/split/appear/disappear). Document with worked figures (two circles merging; a label
  vanishing) in `docs/morphing.md`; golden-test one merge and one disappearance case.
- **Missing slices:** interior gaps between declared key indices are the *point* of this
  generator, not an error. However `z_count` extending **beyond** the last key slice (or the
  first key slice not being 0) is extrapolation outside the source domain and is an error by
  default; config `edge_policy: "error" | "clamp" = "error"` — `"clamp"` repeats the nearest
  key slice. No linear extrapolation, ever.
- **Label conflicts:** all key slices share one `levels` table (one gray value → one
  material id stack-wide, exactly the Phase 1 contract). A gray value present in pixels but
  absent from `levels` is a `MorphError` naming file and value (same behavior as
  `convert-image-stack`). Two levels mapping to one material_id, or duplicate gray values,
  are config errors (reuse `_parse_levels` validation).
- **Size guards:** `max_axis_cells: int = 256`, `max_total_cells: int = 8_000_000` (config
  fields; the EDT is per-slice 2-D so this bounds slice count × slice area). Exceeding them
  is an explicit error suggesting fewer output slices or downsampled input.
- **Config:** `MorphStackConfig(GeneratorConfig)`: `voxel_size_xyz_m`, `levels`,
  `background` (default air/0), `z_count: int | None`, `edge_policy`, optional
  `local_to_world`, `format: "pgm" | "png" = "pgm"`, the size guards. No randomness; `seed`
  stays reserved as in Phase 1 (D5 there).
- **Generator identity:** `generator="vdbmat-utils.morph.stack"`, version `"0.1.0"`;
  `sources` = per-key-slice digests in z order; `identity` = SHA-256 over concatenated slice
  digests + config digest (same recipe as `stack_identity`, factored to be shared rather
  than copied).

### D5. Volume-operation semantics

All ops are pure functions `MaterialLabelVolume (+ params) -> MaterialLabelVolume` on dense
arrays; each validates via `build_material_label_volume` on output. Fixed rules:

- **crop(min_zyx, max_zyx)** — half-open index box in canonical z,y,x; must lie within the
  array (no implicit clamping — out-of-range is a `GeometryError`). `local_to_world` is
  recomposed with the translation of the cropped origin so world positions of surviving
  voxels are unchanged (regression-tested by comparing a world-space voxel-centre before and
  after).
- **pad(before_zyx, after_zyx, fill_material_id=background)** — fill id must exist in the
  palette; `local_to_world` recomposed the same way (negative translation).
- **resample(factor per axis or new voxel_size)** — nearest-neighbor only; sample the source
  at output cell centres, forbid interpolation by construction. Voxel size in the manifest
  updates accordingly. Integer up/downsampling factors are exact; non-integer resampling is
  allowed but documented as alias-prone. Material conservation is *not* claimed for
  resampling (document this).
- **transform** — two distinct sub-ops, kept separate on purpose:
  - `orient(flips, rot90s)` — data movement in exact 90° steps (`np.flip`, `np.rot90` on
    declared axis pairs), with the inverse rotation composed into `local_to_world` so world
    geometry is preserved unless `update_transform: false` is passed (then it's a real
    re-orientation).
  - `place(matrix4)` — metadata-only replacement/composition of `local_to_world` (rigid,
    validated by the canonical types). Never resamples. General (non-90°) rigid resampling
    is out of scope (would need interpolation policy; defer).
- **apply_mask(mask_volume, mode="keep"|"clear", fill=background)** — mask is a second label
  volume of identical shape/voxel size; nonzero = selected. Geometry mismatch is an error
  (no auto-alignment in Phase 2).
- **compose(base, overlay, mode)** — boolean composition of two volumes with identical
  geometry (shape, voxel size, and `local_to_world` must match exactly; anything else is a
  `GeometryError` telling the user to resample/crop first):
  - `union`: overlay's foreground (nonzero after its own background id is mapped out) wins
    over base — "last writer wins", the deterministic conflict rule where both are foreground;
  - `intersect`: keep base labels only where overlay is foreground, else background;
  - `subtract`: base labels except where overlay is foreground.
  Palettes are merged by `ops/palette.py`: same id + same (name, role) merges; same id with
  different definitions is a `PaletteError` (the *material remapping* op exists precisely to
  fix this before composing — say so in the error message).
- **remap_materials(mapping: {old_id: new_id}, palette_updates)** — bulk id rewrite via a
  lookup table; unmapped ids pass through; mapping onto an id with a conflicting existing
  definition is a `PaletteError`; may also rename/re-role and drop now-unused palette
  entries (`prune_palette: bool = true`).
- Every op is exact/deterministic (integer moves only, apart from resample's centre
  arithmetic which is fixed-formula). No RNG anywhere in `ops/`.

### D6. Pipeline configuration

- `PipelineConfig(GeneratorConfig)` with fields: `inputs: tuple[{id, manifest_path}, ...]`,
  `steps: tuple[{op, args…}, ...]`, `output: {input_ref}`. Steps reference volumes by string
  ids: each step reads named inputs (`"from": "a"`, binary ops take `"base"`/`"overlay"`)
  and binds its result to `"as": "b"`; the `output` block names the id to write. This is a
  flat SSA-style list, not a nested expression tree — simpler to validate, diff, and log.
- `pipeline/registry.py` maps op name → (callable, params dataclass). Unknown op names,
  unknown parameters, unbound references, rebinding an existing id, and unused inputs are
  all `PipelineError`s at *validation time*, before any array work (fail fast, with the step
  index in the message).
- Paths in the config are resolved relative to the config file's directory (documented);
  absolute paths allowed. The manifest digests of all inputs go into provenance `sources`;
  `identity` = SHA-256 over input digests + config digest. Generator:
  `"vdbmat-utils.pipeline"`, version `"0.1.0"`. Note: config canonical JSON includes the
  paths as written, so provenance is honest about what was referenced, while `sources`
  digests pin the actual content.
- `morph-stack`/`convert-image-stack` are **not** pipeline steps in Phase 2 — pipelines
  start from existing `.voxels.json` assets. (Chaining generators into pipelines is a small
  follow-up once the step registry is proven; record as deferred in the ADR.)
- CLI: `apply-pipeline --config PIPELINE.json --out DIR --name NAME [--dry-run]`;
  `--dry-run` runs validation + prints the resolved step plan without touching arrays.

### D7. ADRs to write during this phase

- ADR-0007: label-safety architecture — the `ScalarField` split, quantize-only conversion,
  and the AST guard test (D3).
- ADR-0008: per-label SDF morphing semantics — EDT choice (in-repo Felzenszwalh–Huttenlocher,
  no scipy), argmin/lowest-id tie rule, `+inf` absence rule, edge policy (D2, D4).
- ADR-0009: volume-op and pipeline contracts — exact-geometry requirement for binary ops,
  last-writer-wins union, palette-merge rules, SSA-style pipeline config (D5, D6).

## 4. Implementation Steps

Execute in order; each step ends with `ruff check`, `mypy`, `pytest` green and a short
report under `.devdocs/vdbmat-utils/reports/phase2/` (follow the phase1 report style).
Commit per step.

### Step 0 — Ops core (crop, pad, orient/place, mask, remap, palette merge)

0. Verify the `vdbmat` public asset-read API for later steps (see §2); add `io/reader.py`
   only if a wrapper is genuinely needed, and log the upstream follow-up if the API is
   private.
1. Implement `ops/crop_pad.py`, `ops/transform.py`, `ops/mask.py`, `ops/remap.py`,
   `ops/palette.py` per D5, with `OpsError` and reusing `GeometryError`/`PaletteError` where
   the existing names fit.
2. Unit tests (`tests/unit/test_ops_*.py`) on small hand-written asymmetric arrays where the
   expected output array is written literally in the test: crop/pad world-position
   preservation (compare a voxel-centre world coordinate through `local_to_world` before and
   after), orient + inverse-transform round-trip, mask keep/clear, remap collision error,
   palette-merge accept/reject cases, out-of-range crop error.
3. Extend `test_import_isolation.py` for the new subpackages and add the D3 AST-guard test
   (it starts passing trivially now and constrains Steps 1–3).

### Step 1 — Scalar fields, EDT, quantization, boolean compose

1. `fields/`: `ScalarField`, exact separable squared-EDT (`edt.py`) with signed wrapper
   (`signed_distance(mask, spacing)`), `quantize_to_labels`.
2. EDT tests against brute-force O(n²) distances on random small masks (property-style, fixed
   seeds via `rng_from_seed`), plus analytic cases (single point, filled/empty, anisotropic
   spacing) and a determinism double-run.
3. `ops/boolean.py::compose` per D5 (it lands here because good tests want the palette merge
   from Step 0 and, for fixtures, quantized shapes are convenient). Unit tests: union
   last-writer-wins, intersect, subtract, geometry-mismatch error, palette-conflict error
   pointing at `remap-materials`.

### Step 2 — Morph core

1. `morph/keyslices.py`: reuse Phase 1 slice readers and `_parse_levels`; parse z indices
   from filenames (strict: one numeric group; duplicates and non-monotonic parses are
   errors); factor the shared identity recipe out of `image/stack.py` instead of copying it.
2. `morph/interpolate.py` + `morph/__init__.py::morph_stack(slices_dir, config) ->
   MaterialLabelVolume` per D4, built on `fields/` and emitted via
   `build_material_label_volume` + `build_provenance`.
3. Unit tests (`tests/unit/test_morph.py`): key slices reproduced byte-faithfully; midpoint
   of two offset squares (expected array literal); circle→two-circles split golden; label
   present on one side disappearing (verify shrink monotonicity: foreground count
   non-increasing toward the absent side); tie → lowest id; edge_policy error and clamp;
   undeclared gray; gap-is-fine (contrast with `convert-image-stack` which errors);
   size-guard errors.

### Step 3 — Morph CLI + pipeline engine and CLI

1. CLI `morph-stack SLICES_DIR --config CONFIG --out DIR --name NAME` (+ `--voxel-size`,
   `--z-count` overrides; effective config digested, matching Phase 1 D5); success output =
   manifest path + material counts via `preview`.
2. `pipeline/registry.py` + `pipeline/engine.py` + `PipelineConfig` per D6; register all
   Step 0/1 ops (`crop`, `pad`, `resample`, `orient`, `place`, `apply-mask`, `compose`,
   `remap-materials`). Wait — `resample` is implemented here if not already: implement
   `ops/resample.py` per D5 now, with nearest-neighbor tests (integer factor exactness,
   voxel-size metadata update).
3. CLI `apply-pipeline` with `--dry-run`. Unit tests: validation-time failures (unknown op,
   unknown param, unbound/rebound ref, missing input file) each name the step index; dry-run
   touches no output; a 3-step config (crop → remap → compose) matches applying the same
   ops directly through the Python API.

### Step 4 — Contract and integration tests

1. Fixture generators (in-code, no binaries): a sparse morph key-slice set (asymmetric,
   ≥3 materials, one merge event) and a two-asset composition scenario (reuse Phase 1
   fixtures as inputs where possible).
2. Contract tests (`tests/contract/`): byte-equal double runs for `morph-stack` and
   `apply-pipeline`; payload-digest goldens for both; orientation ASCII goldens on all three
   axes of the morphed fixture; material-conservation checks where they genuinely hold
   (remap: total voxel count preserved and per-id counts move as mapped; mask/compose:
   documented count identities), explicitly not claimed for resample.
3. Integration tests (marker `integration`): morphed fixture and composed fixture each →
   `vdbmat import-voxels` → `vdbmat convert` via subprocess, mirroring
   `tests/integration/test_import_voxels.py`.

### Step 5 — Documentation, CI, and phase close-out

1. Docs: `docs/morphing.md` (D4 spec, topology figures, edge/tie rules, worked config),
   `docs/volume-ops.md` (D5 table of ops, geometry rules, conservation claims),
   `docs/pipelines.md` (D6 schema, resolved-path rule, dry-run, full worked example);
   README quick-start additions; ADRs 0007–0009.
2. CI: add "Phase 2 exit criteria" step (morph workflow and pipeline workflow → `validate` →
   `vdbmat import-voxels` → `vdbmat convert`) to the main leg **and** confirm the
   minimal-install leg covers them (no extras are needed, so it should — assert it).
3. Update `roadmap_vdbmat-utils.md` Phase 2 status block (Phase 0/1 style) and record any
   new upstream `vdbmat` follow-ups (notably the asset-read API from Step 0.0).

## 5. Test Matrix Summary (roadmap bullet coverage)

| Roadmap requirement | Where covered |
| --- | --- |
| Label-preserving slice interpolation/morphing | D4, Steps 2–3, contract goldens (Step 4.2) |
| Crop, pad, resample, transform, mask, boolean, remap | D5, Steps 0, 1, 3.2 |
| Topology-change behavior defined | D4 (emergent SDF rule), Step 2.3 merge/split/disappear goldens, `docs/morphing.md` |
| Missing slices / outside-domain behavior | D4 (key-slice gaps by design; `edge_policy`), Step 2.3 |
| Label conflicts | D4 (one levels table; palette rules), D5 (palette merge / remap), Steps 1.3, 2.3 |
| Labels never numerically interpolated | D3 type split + quantize-only rule + AST guard (Step 0.3), NN-only resample (D5) |
| Config-driven pipelines, no custom Python | D6, Step 3, Step 4 pipeline contract tests |
| Deterministic, contract-valid output | Step 4.2 double runs + digests, Step 4.3 integration |

## 6. Out of Scope (defer explicitly)

- 3-D (multi-axis) morphing, non-linear/curve-guided morph timing, and correspondence-based
  (feature-matching) morphing — Phase 2 is per-label SDF only.
- Smooth (SDF-based) label resampling and general rigid resampling with interpolation.
- Generator steps (mesh/image/morph) inside pipelines; pipeline caching; parallel execution
  (Phase 4/5 concerns).
- Scalar-field *inputs* (e.g. importing gray volumes as fields) beyond what morphing needs
  internally; procedural field synthesis is Phase 3.
- Any performance work on the EDT or per-label loops beyond vectorized NumPy (Phase 5;
  the size guards bound the damage).
- OpenVDB anything (Phase 5).

## 7. Risks Specific to This Phase

- **Hidden label interpolation:** the classic failure is a "convenience" float cast deep in
  a resample or morph path producing plausible but wrong mixed labels. Mitigation: the D3
  type split, the quantize-only rule, the AST guard test, and NN-only resampling — all in
  place *before* the morph code lands (Step 0.3 precedes Steps 1–2).
- **EDT correctness/performance:** an in-repo EDT is more code than `scipy.ndimage`, but the
  dependency-free base install is a standing principle. Mitigation: brute-force comparison
  tests (Step 1.2) make correctness cheap to trust; size guards and per-slice 2-D scope keep
  cost bounded; if profiling later shows pain, Phase 5 owns it.
- **Per-label memory:** morphing materializes one distance field per label per key-slice
  pair. With `uint16` palettes this could explode if a stack declares hundreds of labels.
  Mitigation: iterate labels one at a time keeping only the running argmin/min-distance
  pair (two float64 slices + one uint16 slice resident), and document the cost as
  O(labels × slice area) time, O(slice area) memory.
- **Pipeline scope creep:** conditionals, loops, variables, and generator steps are all
  tempting. Mitigation: D6 fixes a flat SSA-style step list with named ids and nothing else;
  anything more is a recorded deferral in ADR-0009.
- **Geometry mismatch surprises in compose:** users will try to combine assets with slightly
  different transforms. Mitigation: exact-match requirement with an error message that names
  the mismatching field and points at `resample`/`crop`/`place` as the fix, tested verbatim.
