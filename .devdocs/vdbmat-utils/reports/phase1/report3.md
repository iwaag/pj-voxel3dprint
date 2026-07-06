# Phase 1 Execution Report — Step 3

Date: 2026-07-06
Plan: [plan.md](../../plans/phase1/plan.md)
Scope: Step 3 (mesh loader and voxelizer core, ported from vdbmat git history).

## Summary

Step 3 complete. The deleted mesh path was recovered from vdbmat commit `8f55562`
(`src/vbdmat/io/mesh.py`, `src/vbdmat/voxelize/mesh.py`, errors, tests, historical
ADR-0006) and ported into a new `vdbmat_utils.mesh` package with **no algorithmic
changes** — all debugged constants preserved verbatim. Suite grew from 85 to 118
tests, green (`ruff`, `mypy --strict` over 36 files, `pytest`). Recovered originals
kept for review in the session scratch area (not committed). **Not committed** —
manual-push workflow.

## Step 3.0 — Recovery and memo verification

Recovered: `io/mesh.py` (141 lines), `voxelize/mesh.py` (440), both error modules,
`tests/voxelize/test_mesh_voxelize.py` (309), `docs/adr/0006…`, `cli/main.py`.
Memo claims checked against the code; two deltas found (**code wins**, per plan):

1. **Jitter split is the reverse of the memo/plan D3 wording.** The recovered code
   applies the Y/Z jitter to the *winding-ray* barycentric evaluation (`yc`, `zc`)
   and runs `_points_on_surface` on the **unjittered** centres — the memo said jitter
   applies only to the surface test with winding at unjittered centres. Ported as the
   code does it; the comment in `voxelizer.py::_classify` now states the actual split.
2. **No separate io/mesh unit-test file existed** at `8f55562`; all mesh tests lived
   in `tests/voxelize/test_mesh_voxelize.py` (which also covers the reader). The
   loader-specific cases were split out into `test_mesh_loader.py` during the port.

Also: the recovered `_domain` has **no** explicit-bounds override, although plan D3
says the override "remains available". Implemented fresh per D3 (see below).

Verified as matching the memo: `_SAMPLE_JITTER_Y/Z = 7.3e-5 / 3.1e-5`,
`_SURFACE_TOLERANCE_M = 1e-9`, `_DOMAIN_SNAP_EPS = 1e-6`, guards 128 / 2 000 000,
facing-mask epsilon, weld tolerance `max(scale,1)*1e-9`, area epsilon
`(max(scale,1))²*1e-18`, closed-solid rule, `placement @ translation(origin)`.

## What was built — `src/vdbmat_utils/mesh/`

- `__init__.py` — `MeshReadError` / `MeshTopologyError` / `VoxelizationError`
  re-rooted under `VdbmatUtilsError` (keeping their `field_path` constructor
  contract), plus the public API re-exports.
- `types.py` — `TriangleMesh` (renamed from `RawMesh`), extended with
  `source_sha256` set by the loader so provenance/identity (D6) needs no side
  channel.
- `loader.py` — STL reader ported verbatim (binary detection by exact length —
  including the "binary starting with `solid`" case — tolerant ASCII parser);
  public `load_mesh(path)` / `read_stl_bytes(data)`.
- `voxelizer.py` — `_classify`, `_points_on_surface` (hotspot, kept as ported),
  `inspect_topology`, `_domain`, `_compose_placement` ported without change.
  Adaptations per plan only:
  - output via `build_material_label_volume` + `build_provenance`
    (generator `vdbmat-utils.mesh.voxelize` v0.1.0, `sources=("sha256:<mesh>",)`,
    config digest included; note carries the triangle count);
  - `MeshVoxelizeConfig(GeneratorConfig)`: required `source_unit` (no default) and
    `voxel_size_xyz_m` and `material` block; `background` defaults to air/0;
    optional `domain_min_m`/`domain_max_m` (both or neither; **new**, used verbatim
    with no padding added), `padding_cells=1`, optional `placement`,
    `max_axis_cells=128`, `max_total_cells=2_000_000` (guards now config fields);
  - `inspect_topology` stayed in the voxelizer module, as in the original.

## Tests (33 new)

- `test_mesh_loader.py` (10): binary/ASCII agreement, binary-with-`solid`-header
  length rule, truncated binary, non-numeric / truncated / non-multiple-of-3 ASCII,
  empty meshes, missing file, `source_sha256` recorded.
- `test_voxelizer.py` (22): every analytic case from the recovered suite ported —
  cube occupancy 27/shape (5,5,5), translation invariance, closed-solid boundary
  rule, non-cubic box, **mm/m grid equivalence**, anisotropic voxels, 90° placement
  (array unchanged, world moved), triangle-reorder invariance, ASCII/binary
  agreement, diagnostics, open / non-manifold / degenerate / empty / multi-solid
  rejection, unknown unit, background-id rejection, axis bound. New per plan:
  float32 domain-snap regression (3.0000002 mm cube stays 3 cells), explicit
  domain bounds (match auto-fit; one-sided and inverted rejected), configurable
  size guards, background-role enforcement, seed reserved-but-digested.
- `test_import_isolation.py`: AST walk enforcing D1 — `mesh` and `image` never
  import each other.

## Verification log

```text
$ uv run ruff check .    → All checks passed!
$ uv run mypy src tests  → Success: no issues found in 36 source files
$ uv run pytest -q       → 118 passed, 2 skipped (PNG tests; Pillow extra not installed)
```

## Deviations from plan

- Jitter-split description corrected per the recovered code (above); plan D3's
  wording should be read accordingly.
- Explicit domain bounds are new code (recovered version had none): bounds are taken
  verbatim (origin = `domain_min_m`, cells = ceil of the span with the snap epsilon)
  and `padding_cells` is *not* added — explicit means explicit.
- `VoxelizationResult`/`VoxelizationDiagnostics` (recovered API) were kept even
  though the plan does not mention them; Step 4's CLI will use the diagnostics for
  its shape/count output.

## Next

Step 4 — mesh CLI (`voxelize-mesh`), in-code STL fixtures (cube + asymmetric
L-bracket), contract tests (byte-equal double run, payload-digest golden,
three-axis `slice_ascii` orientation goldens), and the `integration`-marked
end-to-end run.
