# Phase 1 Execution Report — Step 4

Date: 2026-07-06
Plan: [plan.md](../../plans/phase1/plan.md)
Scope: Step 4 (mesh CLI, in-code STL fixtures, contract tests, end-to-end).

## Summary

Step 4 complete. The mesh workflow is now reachable end to end:
`vdbmat-utils voxelize-mesh MESH --config CONFIG --out DIR --name NAME`
produces a valid asset that passes `validate`, `vdbmat import-voxels`, and
`vdbmat convert` (optical Zarr), verified by an `integration`-marked test.
Suite grew from 118 to 126 tests, green (`ruff`, `mypy --strict` over 38
files, `pytest` including the integration leg). **Not committed** —
manual-push workflow, as in the previous steps.

## Step 4.1 — CLI `voxelize-mesh`

Added to `cli/main.py`, mirroring the recovered `vbdmat voxelize` argument
set (checked against `git show 8f55562:src/vbdmat/cli/main.py`):

- `voxelize-mesh MESH --config CONFIG --out DIR --name NAME` with overrides
  `--source-unit m|mm` (choices come from the voxelizer's
  `SUPPORTED_MESH_UNITS`, not a second hardcoded list), `--voxel-size X Y Z`,
  `--material-id`, `--material-name`, `--padding`.
- Overrides are applied with `dataclasses.replace` **before** voxelization, so
  the provenance config digest covers the effective config (plan D5).
  `--material-id`/`--material-name` rewrite the `material` block, leaving
  `role` and the background untouched.
- On success prints the manifest path, `shape_zyx` plus triangle/occupied
  counts (from the `VoxelizationDiagnostics` kept in Step 3 for exactly this),
  and the Step 0 material-count summary. Failures flow through the existing
  `_EXPECTED_ERRORS` handler: single-line `error: …` on stderr, exit 1 (§1.4).
- Asset identity (plan D6): the mesh file's SHA-256, recorded via
  `write_asset(..., identity=f"sha256:{mesh.source_sha256}")`. The prefix
  matters — the first golden run exposed that a bare hex digest broke the
  `sha256:`-prefixed identity convention `stack_identity` established.

## Step 4.2 — STL fixtures (in-code, no binary blobs)

`fixtures.py` gained a small prism-extrusion emitter and two public byte
generators plus a config helper:

- `_extrude_polygon` — CCW polygon + cap triangulation → outward-oriented
  triangle soup (bottom cap reversed, side quads split; passes Step 3's
  `inspect_topology`). `_stl_ascii` renders deterministic ASCII STL.
- `cube_stl_bytes()` — 2 mm cube.
- `l_bracket_stl_bytes()` — 3×2×1 mm L-prism; the footprint is the 6-vertex L
  polygon fan-triangulated **from the reflex vertex (1, 1)** so every polygon
  edge appears in exactly one cap triangle (no T-junctions → watertight).
  Asymmetric along all three axes so no z/y/x transposition can cancel out.
- `write_mesh_fixture(dir) -> (mesh_path, MeshVoxelizeConfig)` — mirrors
  `write_image_stack_fixture`; mm units, 0.5 mm voxels, material
  `transparent-resin` id 1 (inside vdbmat's builtin optical table so
  `vdbmat convert` stays runnable), default padding → 8×6×4 grid.

Sanity check: bracket volume 4 mm³ / (0.5 mm)³ = 32 cells, and the run
reports exactly `occupied=32`.

## Step 4.3 — Contract tests (`tests/contract/test_mesh_contract.py`)

- Byte-equal double CLI run (determinism).
- Golden digests: payload `8956…b2ed`, manifest `3174…f85b` (hardcoded; a
  change means the output contract moved and must be reviewed deliberately).
- **Orientation goldens**: middle `slice_ascii` on all three axes of the
  L-bracket asserted against literal text — the z view shows the L, the y and
  x views show the differing side profiles, so any axis confusion in the
  voxelizer changes visible characters.
- `validate` passes on the output; manifest records a `sha256:` identity.
- Error path: single-triangle open mesh → exit 1, one-line stderr naming the
  watertightness violation.

CLI override coverage went into `tests/unit/test_cli.py` instead (success
with all five overrides — 1 mm voxels, padding 0 → asserted
`shape_zyx: (1, 2, 3)` — plus a bad `source_unit` config → exit 1).

## Step 4.4 — Integration test

`tests/integration/test_voxelize_mesh.py` (marker `integration`, same
subprocess style as `test_convert_image_stack.py`): L-bracket →
`voxelize-mesh` → `vdbmat import-voxels` → `vdbmat convert`, asserting exit 0
at each stage and that the optical Zarr exists.

## Verification log

```text
$ uv run ruff check .    → All checks passed!
$ uv run mypy src tests  → Success: no issues found in 38 source files
$ uv run pytest -q       → 126 passed, 2 skipped (PNG tests; Pillow extra not installed)
```

## Deviations from plan

- Plan D6 said identity is "the mesh file's SHA-256"; implemented as
  `sha256:<hex>` to match the existing identity convention (see above) —
  the golden manifest digest was recomputed once, deliberately, for this.
- The plan put the failure-mode checks under "failures per §1.4" without a
  test location; they landed in the contract file (open mesh) and
  `test_cli.py` (bad unit) rather than a new test module.

## Next

Step 5 — delete `vdbmat/tools/image_stack_generator` in the `vdbmat` repo,
update forward-looking references to `vdbmat-utils convert-image-stack`, and
bump the pinned dependency (separate cross-repo commit per ADR-0001).
