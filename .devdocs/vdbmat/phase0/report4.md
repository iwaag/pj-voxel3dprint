# Phase 0 Implementation Report: Step 4

**Date:** 2026-06-28
**Completed scope:** Step 4 — Implement Canonical Volume Types and Validation
**Status:** Complete

## Summary

Step 4 implemented the three NumPy-backed canonical volume containers defined by ADR-002, shared array validation, and structured field-level errors. Canonical arrays are validated without casting or repair, copied into C-contiguous storage, and exposed read-only.

This is the selected stopping point. Step 5, which introduces reusable deterministic synthetic fixture generators, is intentionally not started in this report.

## Implemented Artifacts

### Structured validation errors

Added `src/vbdmat/core/errors.py` with `VolumeValidationError`.

Every error contains:

- `field_path`;
- a human-readable invariant message;
- optional `invalid_count`;
- optional `first_index`;
- optional `first_value`.

The formatted exception includes the same information for logs while the attributes remain directly inspectable by tests and future CLI code.

### Shared array validation

Added `src/vbdmat/core/validation.py` with helpers that:

- require a real NumPy `ndarray` rather than converting array-like input;
- require canonical `uint16` or `float32` dtype;
- require exact declared shape;
- reject NaN and positive or negative infinity;
- summarize Boolean invalid-value masks without allocating a full invalid-index list;
- copy validated arrays into C-contiguous, read-only storage.

The copy isolates a volume from later caller mutation. It also canonicalizes memory layout without changing dtype or values.

### Material-label volumes

Added `MaterialLabelVolume` with:

- geometry, palette, provenance, and schema metadata;
- `uint16[z, y, x]` material IDs;
- exact geometry-to-array shape validation;
- validation that every voxel refers to a declared palette ID;
- declared `material-label` asset type and dimension names.

### Material-mixture volumes

Added `MaterialMixtureVolume` with:

- `float32[z, y, x, material]` fractions;
- `uint16[material]` material IDs;
- exact material-axis length and palette-order validation;
- finite closed-range `[0, 1]` validation;
- per-cell normalization using float64 accumulation;
- absolute normalization tolerance `1e-6` and zero relative tolerance;
- declared `material-mixture` asset type and dimension names.

Invalid mixtures are rejected without clipping or normalization.

### Optical-property volumes

Added `OpticalPropertyVolume` with separate arrays for:

- `sigma_a: float32[z, y, x, basis]`;
- `sigma_s: float32[z, y, x, basis]`;
- `g: float32[z, y, x]`;
- `ior: float32[z, y, x]`.

Validation enforces:

- the exact Phase 0 `linear-srgb-effective-v1` basis;
- basis extent matching the declared basis size;
- finite values in every field;
- non-negative absorption and scattering;
- closed anisotropy range `[-1, 1]`;
- strictly positive refractive index;
- fixed coefficient unit `m^-1` and dimensionless unit `1`;
- declared `optical-property` asset type and dimension names.

Spectral metadata remains representable by `OpticalBasis`, but Phase 0 optical volumes reject it because spectral processing is not implemented.

### Common metadata and public API

All volume types require:

- `GridGeometry`;
- `Provenance`;
- exact `vbdmat.volume` schema version `1.0.0`.

Material volumes additionally require a validated `MaterialPalette`. The three containers, asset type, tolerance constant, and validation error are exported from `vbdmat.core`.

Updated `README.md` to list the new modules and public volume API while retaining persistence and renderer I/O as future work.

## Test Coverage Added

Added `tests/unit/test_volumes.py` with 52 focused tests. The complete suite now contains 103 tests.

Coverage includes:

- valid label, mixture, and optical volumes;
- caller-array isolation and read-only output;
- non-C-contiguous input canonicalization;
- rejection of Python lists instead of implicit NumPy conversion;
- exact dtype checks;
- geometry, basis, material-axis, and field-shape checks;
- undeclared material IDs;
- palette-order mismatch;
- NaN and both infinity signs in all floating fields;
- fraction lower and upper bounds;
- fraction normalization and tolerance behavior;
- non-negative absorption and scattering;
- anisotropy interior, endpoints, and out-of-range values;
- positive IOR;
- RGB-only Phase 0 optical volumes;
- common geometry, provenance, and schema metadata;
- error field path, count, first index, first value, and formatted text;
- preservation of invalid source arrays after rejected construction.

## Decisions Made

1. **Volume containers are frozen dataclasses with automatic equality disabled.** NumPy array equality is elementwise and unsuitable for generated dataclass equality.
2. **Validated arrays are copied and marked read-only.** Phase 0 prioritizes stable invariants over zero-copy construction. Large-volume ownership and copy policies can be reconsidered after profiling.
3. **Array-like inputs are rejected.** Callers must perform explicit conversion and accept responsibility for dtype before construction.
4. **No field is interleaved.** Optical properties remain separate arrays because their ranks, units, and downstream support differ.
5. **Normalization uses float64 accumulation.** Stored fractions remain float32, but validation avoids avoidable sum error.
6. **Schema acceptance is exact in memory for Step 4.** Later minor-version and unknown-field persistence behavior belongs to ADR-004.
7. **Units and dimensions are fixed class-level schema declarations.** They cannot vary per instance and therefore cannot silently contradict schema 1.0.
8. **The first invalid element is deterministic C-order.** Errors also report total invalid count without generating all invalid coordinates.

## Verification Results

| Check | Result |
| --- | --- |
| Valid material-label volume | Passed |
| Valid material-mixture volume | Passed |
| Valid optical-property volume | Passed |
| Geometry/array shape consistency | Passed |
| Exact canonical dtypes | Passed |
| Finite numeric values | Passed |
| Valid material IDs and palette order | Passed |
| Fraction range and normalization | Passed |
| Absorption/scattering non-negativity | Passed |
| Anisotropy bounds | Passed |
| Positive IOR | Passed |
| Declared RGB basis and units | Passed |
| Structured validation details | Passed |
| No implicit cast, clamp, or normalization | Passed |
| Read-only C-contiguous copies | Passed |
| pytest | Passed; 103 tests, including 52 Step 4 tests |
| Ruff formatting | Passed; 16 Python files formatted |
| Ruff linting | Passed |
| mypy strict check | Passed; 11 source files checked |
| `uv lock --check` | Passed; 24 packages resolved |
| Git whitespace check | Passed |
| Optional dependency isolation | Passed; Zarr, Mitsuba, Blender, and OpenVDB were not imported by `vbdmat.core` |

## Deviations and Observations

- No Step 4 requirement remains open.
- The plan called for lightweight wrappers. The implementation performs one defensive copy per array, which is intentionally not zero-copy. This is acceptable for the small Phase 0 reference implementation and prevents post-validation mutation by the input owner.
- NumPy's read-only flag is mutation control, not a security boundary. A determined owner of the returned array can attempt to change flags; ordinary writes are rejected.
- Spectral `OpticalBasis` metadata is not accepted by `OpticalPropertyVolume`. This follows ADR-002, which reserves spectral layout without implementing spectral assets in Phase 0.
- Sharp IOR boundary semantics remain assigned to ADR-003 in Step 8. Step 4 validates and preserves the cell-centred IOR field only.
- Zarr paths, serialization, endianness, chunking, and unknown optional fields remain assigned to ADR-004 and Step 7.

## Step 4 Completion Assessment

The Step 4 verification requirements are satisfied:

- all three canonical volume types accept valid schema 1.0 arrays;
- each listed invalid invariant has focused test coverage;
- error objects identify the field and summarize invalid locations;
- no constructor silently casts, transposes, clips, clamps, or normalizes input;
- canonical optical coefficients remain separate arrays;
- geometry, material, basis, provenance, and schema contracts are enforced before storage.

## Next Step

Proceed with Step 5 by implementing deterministic synthetic fixture generators for:

- homogeneous transparent volume;
- homogeneous scattering/white volume;
- transparent/opaque interface;
- layered material slab;
- two-material mixture ramp;
- anisotropic axis marker that reveals transposition.

Each generator should return the Step 4 canonical containers and expose expected counts, selected values, bounds, and world locations for regression tests.
