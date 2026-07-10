# Phase 0 Implementation Report: Step 7

**Date:** 2026-06-28
**Completed scope:** Step 7 — Implement the Zarr Prototype
**Status:** Complete

## Summary

Step 7 defines the Zarr v3 persistence contract and implements failure-safe writes,
validated full reads for all three canonical volume kinds, metadata-only inspection,
and explicit spatial-region reads for optical fields. It also adds corruption tests,
inspection and fixture-report examples, and measured size/partial-read evidence for
all six synthetic fixtures.

This is the selected stopping point. Step 8 begins the coupled boundary/IOR and
renderer-consumer work and is intentionally not started in this report.

## Implemented Artifacts

### ADR-004

Added `docs/adr/0004-zarr-layout-and-compatibility.md`, which selects:

- Zarr format 3 directory stores;
- a root `vbdmat` manifest and `arrays/` child group;
- canonical `uint16` and `float32` storage without conversion;
- Blosc/Zstandard level 5 with bit shuffle;
- up to `2 x 2 x 2` spatial chunks with complete basis/material trailing axes;
- redundant dtype, dimension, shape, and unit declarations for corruption detection;
- same-directory temporary writes and rename-based publication;
- explicit schema-major, minor, patch, and unknown-field behavior.

### Persistence API

Added `src/vbdmat/io/` with:

- `write_volume(path, volume, overwrite=False)`;
- `read_volume(path)`;
- `inspect_volume(path)`;
- `read_optical_region(path, region_zyx)`;
- immutable `VolumeInspection` and `ArrayInspection` results;
- path-oriented `VolumeIOError` failures.

The writer creates and validates a unique temporary sibling before publishing it.
Existing targets require explicit `overwrite=True`; replacement keeps a backup and
restores it if installation fails. Temporary and backup directories are cleaned
after successful writes.

### Manifest and validation

The persisted root manifest includes:

- schema name/version and asset type;
- shape, voxel size, rigid transform, and metre unit;
- provenance with optional UTC time, digest, sources, and notes;
- full ordered material palette or optical basis;
- required array declarations.

Inspection validates the required group/array structure, canonical dtype, dimensions,
units, stored/declaration/semantic shapes, geometry, palette, and optical basis without
reading payload chunks. Full reads then construct the canonical volume classes so all
existing numeric and physical invariants are revalidated.

Schema name and incompatible major versions fail explicitly. Runtime reads accept
schema `1.0.x`; newer minor versions are conservatively rejected. Unknown optional
root attributes, manifest keys, array attributes, and arrays are ignored.

### Spatial optical reads

`read_optical_region` accepts three non-empty, unit-stride half-open slices in ZYX
order. Coefficient reads append the full RGB basis slice. The returned geometry is
cropped and its local-to-world translation is adjusted by the rotated metric offset,
so region cell `(0, 0, 0)` exactly retains the selected source cell's world position.

### Commands and documentation

Added:

- `examples/phase0/inspect_zarr.py` to print asset type, schema, geometry, fields,
  dimensions, chunks, units, and dtypes without loading payloads;
- `examples/phase0/zarr_fixture_report.py` to regenerate all fixture measurements;
- `docs/zarr/phase0-fixture-report.md` with the measured results;
- README usage and design-contract links.

## Test Coverage Added

Added 21 tests in `tests/io/test_zarr.py`. They cover:

- exact round trips for all six material fixtures;
- exact optical-property round trips;
- schema, field, chunk, dimension, dtype, and unit inspection;
- proof that inspection does not invoke array payload reads;
- exact partial values and shifted world geometry;
- partial geometry under a non-identity rotation;
- empty, strided, and wrong-asset region rejection;
- missing array, wrong stored shape, invalid unit, incompatible major version, and
  missing root manifest corruption;
- forward-compatible unknown optional arrays and attributes;
- explicit overwrite behavior, old-target preservation, and work-directory cleanup.

The complete suite increased from 168 to 189 passing tests.

## Fixture Measurements

| Fixture | Canonical bytes | Optical bytes | Partial ZYX | Exact |
| --- | ---: | ---: | --- | --- |
| homogeneous-transparent | 3,116 | 7,176 | `(1, 1, 2)` | Yes |
| homogeneous-scattering-white | 3,121 | 7,821 | `(1, 1, 2)` | Yes |
| transparent-opaque-interface | 3,185 | 8,141 | `(1, 2, 3)` | Yes |
| layered-material-slab | 3,370 | 10,374 | `(2, 1, 2)` | Yes |
| two-material-mixture-ramp | 4,620 | 8,458 | `(1, 1, 2)` | Yes |
| anisotropic-axis-marker | 3,091 | 7,176 | `(1, 1, 2)` | Yes |

The codec is lossless, so floating-point round trips and partial reads were bit-exact;
no tolerance was needed. Directory sizes include metadata overhead and are not
representative of production-volume compression.

## Verification Results

| Check | Result |
| --- | --- |
| Material-label exact round trips | Passed for five fixtures |
| Material-mixture exact round trip | Passed |
| Optical-property exact round trip | Passed |
| Metadata-only inspection | Passed; payload access is not invoked |
| Optical partial reads | Passed for all fixtures |
| Partial world metadata | Passed for translated and rotated geometry |
| Missing array corruption | Rejected clearly |
| Wrong stored shape corruption | Rejected clearly |
| Invalid unit corruption | Rejected clearly |
| Incompatible schema major | Rejected clearly |
| Missing required manifest | Rejected clearly |
| Unknown optional additions | Accepted and ignored |
| Failure-safe target handling | Passed |
| Fixture size/partial report | Passed for all six fixtures |
| pytest | Passed; 189 tests |
| Ruff formatting | Passed |
| Ruff linting | Passed |
| mypy strict check | Passed; 20 source files checked |
| `uv lock --check` | Passed; 24 packages resolved |
| Git whitespace check | Passed |

## Decisions and Limitations

1. Phase 0 uses small chunks to make partial-read behavior directly observable. Chunk
   tuning for realistic volumes is deferred.
2. Material arrays support full reads only; the required Step 7 region proof is for
   optical fields.
3. Unknown non-semantic additions are ignored, but newer minor schemas are not loaded
   into the exact schema-1.0 runtime object model.
4. New-target publication relies on atomic same-directory rename where the filesystem
   provides it. Replacement is failure-safe but briefly removes the final path.
5. Object stores, remote stores, concurrent writers, locking, and commit markers are
   outside Phase 0.
6. Palette metadata is recursively restored through the canonical immutable material
   types; no arbitrary Python object serialization is used.

## Step 7 Completion Assessment

All Step 7 verification requirements are satisfied. Canonical assets preserve values
and semantics through Zarr, metadata can be inspected independently, requested optical
regions return correct values and world placement, corruption and incompatible versions
fail clearly, and every fixture has recorded compressed-size and partial-read evidence.

