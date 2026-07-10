# Phase 0 Implementation Report: Step 2

**Date:** 2026-06-28
**Completed scope:** Step 2 — Write the Coordinate and Schema ADRs
**Status:** Complete

## Summary

Step 2 accepted the coordinate, axis, unit, sampling, and logical volume-schema contracts required by later Phase 0 implementation. It also added an implementation-oriented schema summary and three valid JSON examples with checked numeric results.

This is the selected stopping point. Step 3, which turns these decisions into core spatial types, is intentionally not started in this report.

## Implemented Artifacts

### ADR-001: coordinates, axes, units, and sampling

Added `docs/adr/0001-coordinates-axes-units-and-sampling.md` with decisions for:

- right-handed world coordinates;
- nominal `+Z` build/up direction;
- SI metres as the canonical length unit;
- semantic coordinate order `(x, y, z)`;
- NumPy spatial storage order `(z, y, x)`;
- cell-centred, piecewise-constant voxel sampling;
- half-open grid bounds;
- anisotropic voxel sizes;
- finite, right-handed rigid `local_to_world` placement;
- explicit index/local/world conversion formulas;
- float64 geometry metadata and Phase 0 validation tolerances.

The ADR includes a complete `4 x 3 x 2` anisotropic-grid example and computes the world centre of array element `[1, 2, 3]`.

### ADR-002: canonical volume schemas

Added `docs/adr/0002-canonical-volume-schemas.md` with versioned logical contracts for:

- material-label volumes;
- material-mixture volumes;
- optical-property volumes;
- material palettes and reserved background ID `0`;
- field dimensions and canonical dtypes;
- value ranges, units, and validation invariants;
- schema identity and semantic versioning;
- minimum provenance;
- explicit background properties;
- Phase 0 RGB transport semantics;
- a non-reinterpreting path to future spectral basis coordinates.

The optical schema requires `sigma_a`, `sigma_s`, `g`, and `ior`. It preserves `ior` while explicitly deferring the canonical representation of sharp boundaries to ADR-003.

### Implementation-oriented schema summary

Added `docs/schemas/volume-schema-v1.md` to collect the field tables, common manifest, dtypes, units, and invariants that Steps 3 and 4 will implement.

This is a logical schema. Zarr groups, array paths, chunks, compression, and persistence compatibility remain intentionally deferred to ADR-004.

### Worked JSON examples

Added:

- `docs/schemas/examples/anisotropic-grid-4x3x2.json`;
- `docs/schemas/examples/optical-rgb-voxel.json`;
- `docs/schemas/examples/two-material-mixture.json`.

The examples cover all Step 2 requirements:

- a `shape_zyx = [2, 3, 4]` anisotropic grid;
- array-index to world-centre conversion;
- one RGB optical voxel with coefficients and derived extinction;
- one ordered two-material mixture with explicit background fraction.

### README discoverability

Updated `README.md` with links to both ADRs, the schema summary, and the worked examples.

## Decisions Made

1. **Canonical world space is right-handed, Z-up, and measured in metres.** This aligns nominal world up with the printer build direction while allowing rigid placement elsewhere.
2. **Semantic and storage orders differ deliberately.** Coordinates use `(x, y, z)`; NumPy spatial arrays use `(z, y, x)`. Dimension names are mandatory.
3. **Voxel size is not encoded in the placement transform.** `voxel_size_xyz_m` carries anisotropic scale; `local_to_world` is rigid and carries rotation and origin translation.
4. **Values are cell-centred.** Integer indices identify cells and bounds are half-open.
5. **Schema 1.0 has three asset types.** Material labels, material fractions, and effective optical fields are separate contracts.
6. **Material ID 0 is physical background, not missing data.** Mixture volumes include background as an explicit normalized component.
7. **Canonical storage dtypes are fixed.** Material IDs use `uint16`; mixture and optical arrays use `float32`; geometry metadata uses `float64`.
8. **RGB coefficients are linear effective transport coefficients.** They are not gamma-encoded image colors and are not wavelength samples.
9. **The optical basis is the final array axis.** A future spectral basis can replace three RGB coordinates with ordered wavelengths without changing existing RGB meaning.
10. **IOR is preserved but boundary representation remains open.** ADR-003 must decide whether cell-centred IOR is sufficient or a derived/canonical interface representation is required.

## Key Invariants Ready for Implementation

- Spatial extents and voxel dimensions are finite and positive.
- `local_to_world` is finite, orthonormal, right-handed, and homogeneous.
- Spatial dimension names and extents match geometry exactly.
- Palette IDs are unique and include exactly one background entry with ID `0`.
- Label values reference declared material IDs.
- Fractions are finite, lie in `[0, 1]`, and sum to `1 +/- 1e-6` per cell.
- Optical coefficients are finite and non-negative.
- `g` lies in `[-1, 1]` and `ior` is positive.
- Basis array extent equals the number of declared basis coordinates.
- Invalid values are rejected rather than silently cast, clipped, normalized, or transposed.

## Verification Results

| Check | Result |
| --- | --- |
| ADR-001 required topics | Passed |
| ADR-002 required asset schemas | Passed |
| Anisotropic-grid JSON syntax | Passed with `python -m json.tool` |
| Optical-voxel JSON syntax | Passed with `python -m json.tool` |
| Mixture JSON syntax | Passed with `python -m json.tool` |
| Local-centre calculation | Passed by programmatic recomputation |
| World-centre calculation | Passed by programmatic recomputation |
| RGB extinction calculation | Passed by programmatic recomputation |
| Mixture normalization example | Passed by programmatic recomputation |
| Future spectral extension path | Documented without changing RGB semantics |
| Schema invariants | Expressed as direct validation requirements |
| Ruff formatting | Passed |
| Ruff linting | Passed |
| mypy strict check | Passed |
| pytest | Passed; 1 test passed |
| Git whitespace check | Passed |

## Deviations and Open Decisions

- No Step 2 requirement remains open.
- The examples contain logical array descriptors and selected worked values, not persisted array payloads. This is intentional because ADR-004 owns Zarr layout.
- The meaning of spatially varying IOR at sharp material boundaries is not resolved by ADR-002. This is explicitly assigned to ADR-003 in Step 8, after canonical types, fixtures, mapping, and initial Zarr work exist.
- Spectral wavelength range, sampling, and interpolation are not selected. Step 2 only guarantees that adding a spectral basis will not reinterpret RGB assets.
- The RGB basis is an explicitly approximate transport convention. Calibration and physically spectral conversion remain outside Phase 0 Step 2.

## Step 2 Completion Assessment

The Step 2 verification requirements are satisfied:

- every dimension, axis, unit, transform, and sample location in the worked grid has exactly one interpretation;
- RGB and future spectral basis semantics are distinct and versionable;
- material and optical field shapes, dtypes, ranges, and units are explicit;
- the listed invariants can be translated directly into Step 3 and Step 4 validation code;
- all worked JSON examples are syntactically valid and numerically consistent.

## Next Step

Proceed with Step 3 by implementing and testing core spatial and metadata types based on ADR-001 and ADR-002:

- `GridGeometry`;
- `ColorBasis` or a more accurately named `OpticalBasis`;
- `MaterialDefinition` and `MaterialPalette`;
- schema-version and provenance metadata;
- index-to-world and world-to-index helpers;
- strict rejection of invalid geometry and metadata.

Before implementation, use `OpticalBasis` rather than `ColorBasis` unless code-level review identifies a reason to retain the earlier plan name. The accepted schema covers both RGB and future spectral coordinates, so `OpticalBasis` is the less misleading abstraction.
