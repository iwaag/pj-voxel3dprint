# Phase 1 — Step 9 Report: Analytic and End-to-End Verification

- **Date:** 2026-07-02
- **Step:** 9 of 12 (`.local/phase1/plan.md`)
- **Status:** Complete. Phase 1 invariants are covered by focused analytic,
  metamorphic, persistence, pipeline, CLI, and cross-consumer tests in the default
  and pinned optional environments.

## 1. Boundary-rule defect found and corrected

The new analytic boundary case exposed a mismatch between ADR-006 D8 and the dense
voxelizer. For a cube whose six faces pass through cell-centre planes, only 8 of the
27 closed-solid cells were classified inside. The ray test used jitter for shared-edge
ties but had no explicit test for a sample lying on the surface.

The voxelizer now performs a metre-space point-on-triangle test using ADR-006's
`1e-9 m` surface tolerance before combining that result with the deterministic ray
classification. Surface samples are assigned to the solid independent of triangle
orientation or which face contains the sample. The focused regression verifies the
expected `3 x 3 x 3 = 27` occupied block.

## 2. Added Step 9 verification

Added `tests/integration/test_phase1_end_to_end.py` with six end-to-end and
metamorphic tests:

- mixture fractions, material IDs, and analytic per-material totals survive Zarr
  persistence before exact optical mapping;
- a homogeneous transparent medium retains exact provisional coefficients through
  material and optical persistence;
- relocating an unchanged manifest and payload produces the same geometry, palette,
  provenance, and material field;
- full and differently partitioned, chunk-crossing optical reads return identical
  fields;
- the installed CLI and direct pipeline API produce identical canonical material and
  optical Zarr stores for one complete run;
- bundle validation distinguishes a checksum-corrupted declared artifact (validation
  exit 3) from a missing canonical stage artifact (I/O exit 4).

Existing focused suites continue to cover translated/rotated/anisotropic transforms,
unit-equivalent and triangle-reordered meshes, source-to-material and
material-to-optical provenance, sharp IOR interfaces, deterministic reruns, atomic
failure handling, and field/transform/unit/background/capability conformance for both
adapter conversions.

## 3. Verification results

```text
uv lock --check                         pass
uv run ruff check .                     pass
uv run mypy --strict src/vbdmat         pass (44 source files)
uv run pytest -q                        373 passed, 2 native-only skipped (23.96 s)
focused Step 9 + voxelizer tests        26 passed (4.16 s)
git diff --check                        pass
```

The host suite includes the locked Mitsuba tests. The two native-only tests passed in
the established `vbdmat-openvdb-cycles` container:

```text
tests/integration/test_openvdb.py
tests/integration/test_blender_cycles.py
2 passed (1.77 s)
```

The container emitted one upstream `numcodecs` CRC32C deprecation warning; it does not
affect test results or persisted data. The default suite imports no OpenVDB or Blender
runtime and remains suitable for normal development.
