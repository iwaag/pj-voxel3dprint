# Phase 0 Implementation Report: Step 6

**Date:** 2026-06-28
**Completed scope:** Step 6 — Implement the Minimal Optical Mapping
**Status:** Complete

## Summary

Step 6 implemented a deterministic reference conversion from canonical material-label or material-mixture volumes into canonical optical-property volumes. It adds immutable versioned mapping configuration, explicit provisional material coefficients, direct label lookup, a documented linear mixture rule, configuration hashing, source provenance fingerprinting, examples, and regression tests.

Every supplied optical value is explicitly provisional and uncalibrated. This implementation proves the data path; it does not claim printer or resin accuracy.

This is the selected stopping point. Step 7, which defines ADR-004 and implements Zarr persistence, is intentionally not started in this report.

## Implemented Artifacts

### Optics package

Added `src/vbdmat/optics/`:

- `config.py` defines material properties, mapping configuration, rule/status identifiers, and canonical configuration hashing;
- `mapping.py` implements label and mixture conversion plus output provenance;
- `errors.py` provides path-oriented mapping compatibility errors;
- `__init__.py` exposes the stable Step 6 API.

This module depends on the core volume contracts. The core does not depend on optics.

### Material optical properties

Added immutable `MaterialOpticalProperties` with:

- `uint16`-compatible material ID;
- non-empty descriptive name;
- RGB `sigma_a` in `m^-1`;
- RGB `sigma_s` in `m^-1`;
- scalar `g` in `[-1, 1]`;
- positive scalar IOR.

Every numeric value is normalized to finite Python float and validated before entering a configuration.

### Mapping configuration

Added immutable `OpticalMappingConfig` with:

- configuration identifier and semantic version;
- exact `linear-srgb-effective-v1` basis;
- explicit `linear-volume-fraction-v1` rule;
- explicit `provisional-uncalibrated` status;
- unique material properties normalized into ascending material-ID order;
- ID lookup;
- stable canonical JSON serialization;
- SHA-256 configuration digest.

The Phase 0 default digest produced during verification is:

```text
sha256:da83581c56ca175bf5888de2650cc84020602f56d8de9111d0bbefb5033252eb
```

The digest covers configuration ID, version, calibration status, basis, rule, and every material property. Input material order does not change it.

### Provisional material table

The default configuration covers fixture material IDs `0, 1, 2, 3, 10, 20, 30`.

| ID | Purpose | `sigma_a` RGB (`m^-1`) | `sigma_s` RGB (`m^-1`) | `g` | IOR |
| ---: | --- | --- | --- | ---: | ---: |
| 0 | Air | `(0, 0, 0)` | `(0, 0, 0)` | 0.0 | 1.00 |
| 1 | Transparent resin | `(2, 1, 0.5)` | `(0, 0, 0)` | 0.0 | 1.48 |
| 2 | White resin | `(1, 1, 1)` | `(1000, 1000, 1000)` | 0.2 | 1.52 |
| 3 | Black opaque resin | `(4000, 5000, 6000)` | `(100, 100, 100)` | 0.1 | 1.52 |
| 10 | X diagnostic | `(0, 100, 100)` | `(0, 0, 0)` | 0.0 | 1.00 |
| 20 | Y diagnostic | `(100, 0, 100)` | `(0, 0, 0)` | 0.0 | 1.00 |
| 30 | Z diagnostic | `(100, 100, 0)` | `(0, 0, 0)` | 0.0 | 1.00 |

The axis entries are diagnostic colors for future adapter orientation checks, not physical materials.

### Direct label mapping

For `MaterialLabelVolume`, each cell receives `sigma_a`, `sigma_s`, `g`, and IOR by exact material-ID lookup. Every palette entry must have configuration coverage before any output arrays are allocated.

### Linear mixture mapping

For `MaterialMixtureVolume`, each field is the direct volume-fraction weighted sum of its material values:

```text
property(x) = sum_m(fraction_m(x) * property_m)
```

The same rule applies independently to RGB absorption, RGB scattering, scalar anisotropy, and scalar IOR. Computation uses float64 matrix multiplication; final arrays are explicitly converted to canonical float32.

For a 50/50 transparent/white mixture, the verified hand calculation is:

```text
sigma_a = (1.5, 1.0, 0.75) m^-1
sigma_s = (500, 500, 500) m^-1
g       = 0.1
ior     = 1.5
```

### Output metadata and provenance

Mapping preserves the exact input geometry and schema object. Output provenance includes:

- mapping generator `vbdmat.optics.reference-mapping` and version `1.0.0`;
- exact mapping configuration SHA-256;
- original source identifiers;
- original generator identity and version;
- SHA-256 fingerprint of all input provenance fields;
- mapping configuration ID and version;
- explicit provisional/uncalibrated note;
- no generated timestamp.

This retains deterministic lineage without expanding the core provenance schema.

### Documentation and example

Added `docs/optics/reference-mapping-v1.md` with formulas, the property table, worked example, determinism rules, and physical limitations.

Added `examples/phase0/map_synthetic_fixtures.py`, which maps every Step 5 fixture and prints its absorption and scattering ranges. Updated `README.md` with the optics package and example command.

## Test Coverage Added

Added 36 tests across:

- `tests/optics/test_config.py`;
- `tests/optics/test_mapping.py`.

The complete suite now contains 168 tests.

Coverage includes:

- exact default configuration contents and uncalibrated status;
- material order normalization;
- canonical JSON and stable digest;
- digest sensitivity to configuration changes;
- frozen configuration and properties;
- invalid material IDs, names, RGB lengths, non-finite values, negative coefficients, anisotropy, and IOR;
- duplicate and empty configurations;
- rejection of spectral basis in Phase 0 mapping;
- successful conversion of all six synthetic fixtures;
- direct transparent, white, interface, and diagnostic-axis lookup;
- hand-calculated 50/50 mixture values;
- pure mixture endpoints equal to direct label lookup;
- exact geometry and schema preservation;
- configuration and input provenance lineage;
- deterministic repeated output;
- source-array immutability and no memory sharing with output;
- missing palette mapping rejected before conversion;
- invalid fractions rejected by the canonical input volume before mapping;
- input provenance changes reflected in output fingerprints.

## Decisions Made

1. **Material identity and optical properties remain separate.** The configuration associates properties by material ID without modifying `MaterialDefinition`.
2. **All Phase 0 mixture fields use one linear rule.** A rule identifier prevents later physical improvements from silently changing v1 behavior.
3. **`g` is scalar per material.** RGB anisotropy is not introduced in schema 1.0.
4. **Configuration order is non-semantic.** Entries are sorted by ID before serialization and lookup construction.
5. **Configuration is preserved by content digest plus ID/version.** The output does not embed an arbitrary configuration object into the core volume schema.
6. **Source provenance is preserved by readable generator/source fields and a complete fingerprint.** Mapping itself becomes the output generator.
7. **Mapping has no timestamp.** Identical input and configuration produce identical arrays and metadata.
8. **Every declared palette ID requires coverage, even when unused.** This catches incomplete material libraries before array conversion and keeps related assets predictable.
9. **Extra configuration IDs are allowed.** One shared configuration can cover multiple related fixture palettes.
10. **Output construction uses Step 4 validation.** Mapping does not bypass canonical dtype, shape, finite-value, or physical-range checks.

## Known Physical Limitations

- No coefficient is measured or fitted.
- RGB transport values are not spectra.
- Printer commands are treated as effective material volume fractions.
- There is no droplet, bleeding, curing, shrinkage, or interface process model.
- Linear `sigma_a` and `sigma_s` ignore microstructure and dependent scattering.
- Linear `g` is not scattering-weighted.
- Linear IOR is not an effective-medium theory.
- Surface roughness, Fresnel interfaces, and sharp IOR boundary representation are unresolved.
- The mapping is appropriate only for pipeline and renderer-integration proofs.

## Verification Results

| Check | Result |
| --- | --- |
| Default provisional configuration | Passed |
| Configuration canonicalization and digest | Passed |
| Material property validation | Passed |
| Direct label lookup | Passed |
| Linear mixture rule | Passed |
| 50/50 hand calculation | Passed |
| Pure mixture endpoints | Passed; equal direct label output |
| All six synthetic fixtures | Passed |
| Palette coverage preflight | Passed |
| Invalid fractions rejected before mapping | Passed |
| Geometry and schema preservation | Passed |
| Configuration and provenance lineage | Passed |
| Deterministic repeated conversion | Passed |
| Side-effect-free input handling | Passed |
| Mapping example | Passed for all fixtures |
| pytest | Passed; 168 tests, including 36 Step 6 tests |
| Ruff formatting | Passed; 27 Python files formatted |
| Ruff linting | Passed |
| mypy strict check | Passed; 17 source files checked |
| `uv lock --check` | Passed; 24 packages resolved |
| Git whitespace check | Passed |
| Package build | Passed; sdist and wheel built with uv |
| Wheel content | Passed; `vbdmat/optics` is included |

## Deviations and Observations

- No Step 6 requirement remains open.
- The plan allowed scalar or explicitly defined RGB `g`; this implementation deliberately selects scalar `g`, matching `OpticalPropertyVolume` schema 1.0.
- “Preserve configuration” is implemented as exact content digest plus ID/version rather than embedding configuration in the optical volume. The canonical JSON is available from the config object and should be stored beside future persisted outputs.
- Input provenance timestamps, if present, contribute to the source fingerprint but are not copied as the output creation time. This retains deterministic mapping output.
- The default property magnitudes are chosen to exercise transparent, scattering, absorbing, and orientation cases. Their relative behavior is intentional; their physical accuracy is not.

## Step 6 Completion Assessment

The Step 6 verification requirements are satisfied:

- palette entries receive explicit provisional RGB absorption/scattering, scalar anisotropy, and IOR through a versioned configuration;
- labels use direct lookup;
- every mixture field follows a documented versioned rule;
- geometry, schema, configuration identity, and source provenance are retained;
- pure endpoints equal direct material output;
- synthetic mixture values match hand calculations;
- palette coverage and fraction validity fail before conversion;
- repeated conversion produces identical arrays and metadata;
- assumptions and limitations are recorded without calibrated claims.

## Next Step

Proceed with Step 7 by completing ADR-004 and implementing the Zarr prototype:

- select group and array paths;
- define metadata encoding and schema-version checks;
- choose fixture-scale chunks and compression;
- implement failure-safe writes;
- write and read all three canonical volume types;
- provide metadata-only inspection and spatial-region reads;
- test exact/tolerant round trips, incompatible versions, missing arrays, wrong shapes, invalid units, size, and partial-read behavior;
- store the exact mapping configuration JSON beside mapped optical assets or define its external-reference contract.
