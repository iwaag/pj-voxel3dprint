# Phase 0 Implementation Report: Step 3

**Date:** 2026-06-28
**Completed scope:** Step 3 — Implement Core Spatial Types
**Status:** Complete

## Summary

Step 3 implemented the immutable core value objects and coordinate helpers specified by ADR-001 and ADR-002. The implementation covers grid geometry, rigid transforms, optical basis metadata, material definitions and palettes, schema identity/version metadata, and provenance.

This is the selected stopping point. Step 4, which introduces NumPy-backed canonical volume containers and field validation, is intentionally not started in this report.

## Implemented Artifacts

### Axis and numeric normalization

Added `src/vbdmat/core/axes.py` with:

- explicit `ShapeZYX`, `IndexZYX`, `PointXYZ`, and `VoxelSizeXYZ` aliases;
- positive `(nz, ny, nx)` shape normalization;
- integer `(z, y, x)` cell-index normalization;
- finite semantic `(x, y, z)` point normalization;
- finite positive anisotropic voxel-size normalization;
- explicit rejection of booleans and invalid numeric values.

### Rigid transforms

Added `src/vbdmat/core/transforms.py` with:

- immutable row-major `4 x 4` transform representation;
- identity transform constant;
- finite-value and homogeneous-last-row checks;
- orthonormality and determinant `+1` checks at ADR tolerance `1e-9`;
- local-to-world point transformation;
- analytic world-to-local inverse for rigid transforms.

Scale, shear, reflection, malformed matrices, and non-finite matrices are rejected.

### Grid geometry

Added `src/vbdmat/core/geometry.py` with frozen `GridGeometry`:

- canonical `shape_zyx` and `voxel_size_xyz_m`;
- rigid `local_to_world` placement;
- derived semantic `shape_xyz` and local physical extent;
- cell-centre conversion to local and world coordinates;
- continuous index-to-local and index-to-world conversion;
- world-to-continuous-index conversion;
- half-open containment checks;
- continuous-index and world-point cell lookup without clamping;
- explicit array-order `(z, y, x)` cell results.

Constructor inputs are normalized to immutable tuples. Invalid cells and out-of-bounds points are rejected instead of clamped.

### Optical basis

Added `src/vbdmat/core/optical_basis.py` with:

- `OpticalBasisKind` for RGB and reserved spectral metadata;
- `OpticalBasis.phase0_rgb()` with the exact schema 1.0 RGB contract;
- `OpticalBasis.spectral_wavelengths_nm()` as a future-compatible metadata hook;
- exact RGB coordinate, white point, observer, and linear-transfer validation;
- finite, numeric, strictly increasing spectral wavelength validation;
- a basis-size property for later array-shape validation.

The spectral factory only represents metadata. It does not enable spectral volume processing, mapping, or rendering.

### Materials and palettes

Added `src/vbdmat/core/materials.py` with:

- `MaterialRole`;
- frozen `MaterialDefinition`;
- material-ID range checks for `uint16` compatibility;
- optional external ID and deeply frozen JSON-compatible metadata;
- frozen, ordered `MaterialPalette`;
- unique-ID enforcement;
- mandatory background material ID `0`;
- rejection of nonzero background-role entries;
- stable palette-order ID access and ID lookup.

Material identity remains separate from optical coefficients as required by ADR-002.

### Schema and provenance metadata

Added `src/vbdmat/core/metadata.py` with:

- strict `MAJOR.MINOR.PATCH` `SchemaVersion` parsing;
- major-version compatibility checks;
- `SchemaIdentity`;
- canonical `VOLUME_SCHEMA` set to `vbdmat.volume` version `1.0.0`;
- frozen `Provenance`;
- required generator identity and version;
- optional timezone-aware UTC timestamp;
- optional lowercase SHA-256 configuration digest;
- immutable ordered source identifiers;
- explicit rejection of a single string passed as a source sequence.

### Public API and documentation

Added `src/vbdmat/core/__init__.py` with the intended public Step 3 API. Updated `README.md` to list the implemented core modules and clarify that volume containers and I/O remain deferred.

## Test Coverage Added

Added:

- `tests/unit/test_geometry.py`;
- `tests/unit/test_materials.py`;
- `tests/unit/test_metadata.py`.

The new tests cover:

- the exact ADR-001 anisotropic `4 x 3 x 2` worked example;
- translated and rotated grids;
- index/world round trips;
- cell centres, extents, and half-open boundary ownership;
- invalid shapes, voxel sizes, indices, and transforms;
- left-handed, scaled, sheared, and malformed transforms;
- tuple normalization and frozen dataclasses;
- palette order, lookup, background rules, duplicate IDs, and ID limits;
- deep freezing and validation of material metadata;
- exact Phase 0 RGB semantics;
- reserved spectral metadata ordering and finiteness;
- strict schema versions and compatibility;
- UTC provenance, digests, and source normalization.

## Decisions Made

1. **The Step 3 code abstraction is named `OpticalBasis`.** This replaces the earlier provisional `ColorBasis` name because the same abstraction reserves wavelength-coordinate metadata.
2. **Core values are frozen dataclasses.** Constructor sequences are copied into tuples so caller mutation cannot change canonical geometry or metadata.
3. **Rigid-transform inversion is analytic.** Because validation guarantees orthonormal rotation, the inverse uses `R.T` and avoids a general matrix inverse.
4. **Coordinate conversion can operate outside the grid, but cell lookup cannot.** This preserves useful affine conversion while keeping containment explicit.
5. **No conversion helper silently clamps.** Exact half-open bounds from ADR-001 determine cell ownership.
6. **Material metadata is deeply frozen and JSON-compatible.** Nested mappings become read-only proxies and lists become tuples.
7. **Spectral support is metadata-only.** Strictly increasing nanometre coordinates are representable without implying that Phase 0 supports spectral assets.
8. **No new dependency was added.** The existing NumPy dependency provides numeric transform validation and operations.

## Verification Results

| Check | Result |
| --- | --- |
| ADR anisotropic-grid values | Passed |
| Isotropic and anisotropic geometry | Passed |
| Translated and rotated transforms | Passed |
| Index/world round trips | Passed at the ADR tolerance |
| Half-open bounds | Passed |
| Invalid geometry rejection | Passed |
| Material and palette validation | Passed |
| RGB and spectral metadata validation | Passed |
| Schema and provenance validation | Passed |
| pytest | Passed; 51 tests collected and passed |
| Ruff formatting | Passed |
| Ruff linting | Passed |
| mypy strict check | Passed; 8 source files checked |
| `uv lock --check` | Passed; 24 packages resolved |
| Git whitespace check | Passed |
| Optional dependency isolation | Passed; Zarr, Mitsuba, Blender, and OpenVDB were not imported by `vbdmat.core` |

## Deviations and Observations

- No Step 3 requirement remains open.
- The implementation uses `OpticalBasis` instead of the plan's provisional `ColorBasis`. This is documented in the Step 2 report and matches ADR-002 more accurately.
- The public geometry object does not store a separate `origin`. ADR-001 deliberately makes transform translation the minimum-corner world origin, avoiding redundant state.
- Axis metadata is fixed by the canonical schema rather than configurable per object. `shape_zyx`, semantic XYZ conversion, and named types enforce it.
- Custom path-rich volume validation errors are deferred to Step 4, where array field paths and invalid-element summaries exist. Step 3 raises specific built-in validation exceptions with field-oriented messages.
- The original package smoke test remains valid. The complete suite now contains 51 tests.

## Step 3 Completion Assessment

The Step 3 verification requirements are satisfied:

- isotropic and anisotropic grid geometry is represented without implicit axes or units;
- index-to-world-to-index round trips pass for translated and rotated grids;
- boundary cells, internal planes, and excluded maximum bounds are tested;
- invalid shape, scale, reflection, shear, and metadata inputs fail early;
- core metadata and palette objects are immutable or mutation-controlled;
- core modules do not depend on storage or renderer modules.

## Next Step

Proceed with Step 4 by implementing NumPy-backed canonical volume types and path-aware validation:

- `MaterialLabelVolume`;
- `MaterialMixtureVolume`;
- `OpticalPropertyVolume`;
- geometry-to-array shape checks;
- exact dtype checks;
- material-ID and palette checks;
- fraction range and normalization checks;
- optical coefficient, anisotropy, IOR, and basis-size checks;
- focused invalid-invariant tests with no implicit repair.
