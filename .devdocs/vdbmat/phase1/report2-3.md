# Phase 1 — Steps 2 & 3 Report: Direct-Voxel Input and Mesh Voxelization

- **Date:** 2026-07-01
- **Steps:** 2 (direct material-voxel input) and 3 (mesh input + dense voxelization)
- **Status:** Complete. `ruff`, `mypy --strict`, and the full test suite pass
  (278 passed, 3 optional integration tests skipped for absent renderers).

Steps 2 and 3 were implemented together because Step 1 (ADR-006) fixed both contracts;
they share no code but share the ADR-006 unit/axis/palette conventions.

## 1. Step 2 — Direct material-voxel input

New module [src/vbdmat/io/voxel_manifest.py](../../src/vbdmat/io/voxel_manifest.py)
implements a strict reader for the `vbdmat.voxels/1.0.0` interchange (ADR-006 D1–D6):

- `read_material_label_manifest(path) -> MaterialLabelVolume`;
- `inspect_material_label_manifest(path) -> ManifestInspection` (metadata-only; no
  payload read or checksum verification);
- error type `VoxelManifestError(field_path, message)` in
  [src/vbdmat/io/errors.py](../../src/vbdmat/io/errors.py).

Behaviour, all enforced by tests:

- UTF-8 JSON parsed strictly; unknown top-level fields rejected (no silent forward
  leniency — the major-version gate handles compatibility).
- Payload path resolved only beneath the manifest directory; absolute paths, `..`
  traversal, backslashes, and drive prefixes rejected.
- SHA-256 recomputed over raw `.npy` bytes and compared **before** the array is loaded.
- `.npy` loaded with `allow_pickle=False`; exact `uint16` dtype and `shape_zyx` required
  — no transpose, cast, unit inference, or ID remap.
- Convenience unit `voxel_size: {value, unit}` (`m`/`mm`) converted explicitly; exactly
  one of `voxel_size_xyz_m` / `voxel_size` required.
- Canonical `GridGeometry`, `MaterialPalette`, `Provenance`, and `MaterialLabelVolume`
  built unchanged; provenance records `vbdmat.voxels/1.0.0`, the payload
  `sha256:…`, and the source identity.

Worked Example V (ADR-006) is reproduced exactly by
[tests/io/test_voxel_manifest.py](../../tests/io/test_voxel_manifest.py): the asymmetric
black marker stays at `material_id[0, 2, 3]`, per-material counts are
`{1: 21, 2: 2, 3: 1}`, and the marker world centre is `(0.01014, 0.020125, 0.030015)` m.
(During testing the ADR text was corrected: the transparent count is **21**, not 20 —
24 cells total.)

Step 2 verification coverage: exact cells/geometry/palette/checksum; field-oriented
failures for malformed JSON, incompatible major version, wrong dtype, wrong shape,
undeclared IDs, missing payload, checksum mismatch, path traversal, absolute path,
non-finite geometry, and invalid transform; repeated reads structurally equal;
metadata-only inspection; and a source-level assertion that the reader imports no Zarr
or renderer dependency.

## 2. Step 3 — Mesh input and dense voxelization

Two new modules:

- [src/vbdmat/io/mesh.py](../../src/vbdmat/io/mesh.py) — a repository-owned STL reader
  (`read_stl` / `read_stl_bytes`) parsing ASCII and binary STL into a `RawMesh`
  triangle soup. Binary/ASCII detection uses the exact 84 + 50·n length check with a
  `solid` fallback. **No third-party mesh dependency** (ADR-006 D2); `uv.lock`
  unchanged.
- [src/vbdmat/voxelize/mesh.py](../../src/vbdmat/voxelize/mesh.py) — `inspect_topology`
  and `voxelize_mesh`, returning a `VoxelizationResult` (canonical
  `MaterialLabelVolume` + `VoxelizationDiagnostics`). Errors `MeshTopologyError` and
  `VoxelizationError` live in [src/vbdmat/voxelize/errors.py](../../src/vbdmat/voxelize/errors.py).

Implementation follows ADR-006 D7–D10:

- required explicit `source_unit` (`m`/`mm`), `voxel_size_xyz_m`, and non-background
  `material_id`; missing/invalid values fail rather than defaulting;
- domain from the metre-space bounding box with one padding cell per side; the padded
  minimum corner becomes the volume `local_to_world` translation, composed with an
  optional rigid placement;
- cell-centre classification by a **signed-winding +X ray** test (winding `≠ 0 ⇒
  inside`), robust to inward/outward global orientation;
- topology rejection of open, non-manifold, degenerate, empty, and multi-solid meshes,
  and of inconsistent orientation across shared edges.

### Two subtle correctness fixes made during Step 3 (both tested)

1. **Interior triangulation diagonals.** A cell centre landing exactly on a face's
   internal triangulation diagonal (a non-physical shared edge) was double-counted,
   inflating occupancy. Resolved with the ADR-006 D8 deterministic sub-voxel sample
   offset, using **distinct** Y and Z fractions so centres with equal Y and Z do not
   remain on a 45° diagonal. The offset (~7e-5 of a voxel) is far smaller than the
   ≥ ½-voxel distance from any real surface for well-posed inputs, so real
   classification is unchanged.
2. **float32 STL round-off at cell boundaries.** STL stores float32, so a metre-declared
   `0.003` becomes `0.00300000002`, and a naïve `ceil` added a spurious padded cell,
   breaking mm/m equivalence. Resolved by snapping near-integer spans within `1e-6` of a
   cell down; padding still covers the boundary. Millimetre and metre expressions of the
   same solid now produce byte-identical volumes.

### Analytic verification (all passing)

- **Worked Example M**: a 3 mm cube at 1 mm voxels → `shape_zyx = (5, 5, 5)`, exactly
  **27 occupied cells** in the padded index block `1..3`³; a 1 mm translation preserves
  the count.
- non-cubic box `5×3×2 mm` → 30 cells; anisotropic voxels `(2,1,1) mm` on a 6 mm cube →
  108 cells.
- millimetre vs metre of the same solid → identical volumes.
- rigid 90° rotation about Z preserves occupancy and maps world centres by the rotation.
- triangle reordering and ASCII vs binary produce identical volumes.
- open, non-manifold, degenerate, empty, and multi-solid meshes are rejected clearly;
  bad unit, background material ID, and the cell-count bound raise field-oriented
  errors.
- source-level assertion that the voxelizer imports no renderer dependency.

### Peak memory and runtime at the Phase 1 bound

Measured on the largest allowed grid (a 123 mm cube → `125³ = 1,953,125` cells, just
under the 2,000,000-cell / 128-axis bound):

| Metric | Value |
| --- | --- |
| Grid | `125 × 125 × 125` (1,953,125 cells) |
| Occupied | 1,860,867 |
| Runtime | ~1.6 s |
| Python peak (tracemalloc) | ~29 MB |
| Process max RSS | ~76 MB |

The dense method is comfortably tractable within the Phase 1 safety bound. The
`128³` case is correctly rejected by the total-cell bound.

## 3. Files added / changed

- added: `src/vbdmat/io/voxel_manifest.py`, `src/vbdmat/io/mesh.py`,
  `src/vbdmat/voxelize/__init__.py`, `src/vbdmat/voxelize/mesh.py`,
  `src/vbdmat/voxelize/errors.py`;
- changed: `src/vbdmat/io/errors.py` (added `VoxelManifestError`, `MeshReadError`),
  `src/vbdmat/io/__init__.py` (exports);
- tests: `tests/io/test_voxel_manifest.py`, `tests/voxelize/test_mesh_voxelize.py`;
- docs: corrected the ADR-006 Worked Example V material count (20 → 21).

No changes to `core`, schema 1.0.0, Zarr persistence, optics, or `uv.lock`. The core
dependency set is unchanged; import and voxelization require neither Zarr nor a
renderer.

## 4. Verification-item status

All Step 2 and Step 3 verification bullets from `plan.md` are covered by passing tests
or recorded measurements, with two exceptions noted as documented Phase 1 limitations:

- **Self-intersection detection** is not implemented (ADR-006 D9 explicitly allows
  non-exhaustive detection in Phase 1). Revisit only if a representative mesh needs it.
- The **multi-material coupon fixture** and **stepped-wedge mesh fixture** themselves are
  built in Step 4; Steps 2–3 prove the readers against equivalent analytic inputs
  (Worked Examples V and M).

## 5. Recommendation

Proceed to **Step 4** (build the committed Phase 1 representative input fixtures), which
will exercise these readers end to end and produce the analytic expected summaries the
pipeline steps depend on.
