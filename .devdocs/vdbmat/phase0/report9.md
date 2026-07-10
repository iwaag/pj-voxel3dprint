# Phase 0 Implementation Report: Step 9

**Date:** 2026-06-28
**Completed scope:** Step 9 — Build the Mitsuba 3 Consumer Proof
**Status:** Complete

## Summary

Step 9 accepts ADR-005 and implements an optional Mitsuba 3 adapter from the validated
canonical `OpticalPropertyVolume`. The adapter converts absorption and scattering into
Mitsuba's heterogeneous-medium parameterization, preserves geometry and metric units,
reduces spatial anisotropy through an explicit diagnostic approximation, builds complete
medium containment and dielectric IOR interface meshes, emits machine-readable
capability reports, and renders every Phase 0 fixture with fixed settings.

Reference EXR/PNG outputs, attenuation diagnostics, scene summaries, PLY boundary
artifacts, and capability reports were generated under `.local/phase0/mitsuba-step9/`.
Their stable hashes are recorded in `docs/mitsuba/phase0-proof.md` rather than committing
generated binary outputs.

## ADR-005 and Exporter Contract

Added `docs/adr/0005-exporter-boundary.md` defining:

- validated canonical optical volume input;
- renderer state confined below `vbdmat.exporters`;
- lazy optional renderer imports;
- required capability entries for geometry, units, optical basis, `sigma_a`, `sigma_s`,
  `g`, `ior`, derived interfaces, and provenance;
- `represented`, `transformed`, `approximated`, and `unsupported` dispositions;
- explicit rejection and artifact behavior;
- fixed render configuration and diagnostic-output semantics.

Added common immutable `CapabilityEntry` and `CapabilityReport` types with stable JSON
serialization and unique field enforcement.

## Mitsuba Field Mapping

Added `src/vbdmat/exporters/mitsuba.py`.

### Coefficients

The adapter computes in float64 and validates float32 representability before producing:

```text
sigma_t = sigma_a + sigma_s
albedo  = sigma_s / sigma_t when sigma_t > 0, otherwise exactly 0
```

Both outputs are immutable float32 arrays. The source volume is not mutated. Mitsuba
grid volumes receive canonical `(z, y, x, basis)` tensors, raw three-channel data,
nearest filtering, the complete metric transform, and medium scale `1` because both
scene coordinates and canonical lengths are metres.

### Phase function

Mitsuba's Henyey-Greenstein phase accepts one scalar `g`. The adapter computes the
global mean weighted by the per-cell mean RGB scattering coefficient. Zero total
scattering maps to `g=0`. A result at canonical endpoints `-1` or `1` fails clearly
because Mitsuba requires the open interval.

The capability report marks this spatial reduction `approximated`.

### IOR and boundaries

Canonical spatial `ior` remains `unsupported` as a heterogeneous-medium grid and is
always diagnosed. The Step 8 derived interface representation is transformed into PLY
surface patches:

- every domain boundary cell emits an outward face, including index-matched cells, so
  participating-medium containment is complete;
- index-matched exterior groups use a null BSDF;
- mismatched exterior groups use scalar dielectric `int_ior` and ambient `ext_ior`;
- internal faces use their oriented positive/negative side IORs and retain the same
  heterogeneous medium on both sides.

Faces are grouped by exact IOR pair but not merged. World vertices use the canonical
rigid transform and anisotropic voxel dimensions.

## Fixed Scene and Outputs

`MitsubaExportConfig` controls validated, explicit settings. Reference defaults are:

- Mitsuba variant `llvm_ad_rgb`;
- 64 × 64 pixels;
- 32 samples per pixel;
- seed `20260628`;
- volumetric path depth 8;
- 35-degree perspective camera;
- angled camera direction fixed relative to world axes;
- area backlight with linear radiance 1;
- ambient IOR 1 and IOR threshold `1e-6`.

The camera is fitted from all eight transformed grid corners. Near/far clipping scales
with the physical grid bounds, so micron-scale fixtures are not clipped or normalized
out of world units.

Each render writes synchronously before hashing:

- authoritative linear RGB EXR;
- display PNG;
- fixed-gain attenuation diagnostic PNG using
  `clip((1 - radiance) * 128, 0, 1)`;
- capability JSON and scene summary JSON;
- exterior containment and internal interface PLY files.

Synchronous writes were selected after verification exposed that Mitsuba's convenience
writer defaults to asynchronous output; hashing before completion could otherwise record
an empty-file SHA-256.

## Reference Fixture Results

All six fixtures load and render without scene edits.

| Fixture | Display PNG SHA-256 | Mean linear RGB |
| --- | --- | --- |
| homogeneous-transparent | `3436eabe928df2adec6b4d54d1764cc24d074b22865d9583296844145a028f90` | `(0.897956, 0.897965, 0.897970)` |
| homogeneous-scattering-white | `534ad7b3ea877a9be685b7ecc34e1dad159b072f3636523688c31bd5bdf3cbf9` | `(0.894781, 0.894781, 0.894781)` |
| transparent-opaque-interface | `1e999e5d22d33018cb5459882240397b72042ffdb23712176c80af7ebc5f1ef6` | `(0.896701, 0.896060, 0.895449)` |
| layered-material-slab | `cdaa81a3d6fcbdfcf8697763f6d6ca2f88ab8b2cf09c90d9a43de3df062c7e90` | `(0.895400, 0.894512, 0.893668)` |
| two-material-mixture-ramp | `107afd1fe687b01afbc94a6cc7c7ac578f616ab63578fed280ec699ceb62ecb4` | `(0.900689, 0.900690, 0.900690)` |
| anisotropic-axis-marker | `7d958bc7a4494bfc110ce5a411983fe0189079b49b0034e1d74604399548347d` | `(0.999901, 0.999901, 0.999947)` |

The complete display and attenuation hashes are in
`docs/mitsuba/phase0-proof.md`. Regenerating all six fixtures into a separate directory
produced a byte-identical `render-report.json`.

## Orientation and Scale Verification

The axis-marker proof checks the consumer contract directly rather than relying only on
a small rendered image:

- tensor dimensions remain `(2, 3, 4, 3)` in ZYX-basis order;
- selected X, Y, and Z marker cells retain distinct coefficient triplets;
- the unit volume maps to translated physical extents through the exact metric matrix;
- PLY face vertices use the same transformed continuous grid coordinates;
- the fixed angled camera and attenuation image provide a gross visual regression aid.

This verifies axis ordering and world scale before Mitsuba interpolation or projection
can obscure the source of an error.

## Monotonic Qualitative Checks

Controlled homogeneous volumes use index-matched IOR and the fixed backlight. Increasing
either absorption or scattering from `0` to `10,000` to `50,000 m^-1` strictly reduces
mean rendered radiance. The automated tests assert ordering with fixed seed, resolution,
and sample count rather than matching renderer-dependent pixel values.

## Commands and Documentation

Added:

- `examples/phase0/render_mitsuba_fixtures.py`;
- `docs/mitsuba/phase0-proof.md`;
- README reproduction commands and architecture links.

The existing runtime probe remains available as:

```bash
uv run --group mitsuba python examples/phase0/probe_mitsuba_ior.py
```

## Tests Added

Added 26 tests across common diagnostics, pure conversion, and optional integration:

- capability lookup, serialization, and duplicate rejection;
- exact coefficient conversion and zero-extinction behavior;
- scattering-weighted phase reduction;
- axis tensor values, ordering, and metric transform;
- complete required capability fields and statuses;
- invalid export configuration;
- all six fixture scene loads and render smoke tests;
- raw/nearest grids and metre-scale medium configuration;
- absorption and scattering monotonic response;
- fixed-seed PNG and linear-summary reproducibility;
- subprocess proof that core and lazy adapter imports do not import Mitsuba.

The full installed-group suite increased from 205 to 231 passing tests.

## Optional Dependency Isolation

The locked Mitsuba group resolved Mitsuba 3.9.0 and Dr.Jit 1.4.0. Isolation was tested by
removing the group and running:

```text
221 passed, 1 optional module skipped
```

In that environment, `import mitsuba` failed as expected while `vbdmat`, `vbdmat.core`,
and `vbdmat.exporters.mitsuba` imported successfully without loading renderer bindings.
The locked group was then restored and Mitsuba 3.9.0 rechecked.

## Verification Results

| Check | Result |
| --- | --- |
| ADR-005 accepted | Passed |
| Exact `sigma_t`/albedo conversion | Passed |
| Zero-extinction handling | Passed |
| Fixed phase approximation | Passed and diagnosed |
| Spatial IOR unsupported diagnostic | Passed |
| Exterior containment meshes | Passed |
| Internal dielectric interface meshes | Passed |
| All six fixture scenes load | Passed |
| All six fixture renders | Passed |
| Axis order and world scale | Passed |
| Absorption monotonic response | Passed |
| Scattering monotonic response | Passed |
| Fixed-seed reproducibility | Passed |
| Reference report regeneration | Byte-identical |
| Core environment without Mitsuba | 221 passed, 1 optional module skipped |
| Full pytest with Mitsuba | 231 passed |
| Ruff formatting | Passed; 46 Python files |
| Ruff linting | Passed |
| mypy strict check | Passed; 26 source files |
| `uv lock --check` | Passed; 24 packages resolved |
| Git whitespace check | Passed |
| Package build | Passed |
| Wheel content | Passed; exporter modules included |

## Limitations

- Spatial `g` is represented by one scattering-weighted global value.
- Mitsuba RGB mode is an effective-RGB approximation, not spectral transport.
- Unit-cell PLY patches are not merged and can show coincident-edge artifacts.
- Complex nested dielectric region correctness remains approximate.
- The attenuation PNG is a visualization and can amplify Monte Carlo or mesh-edge
  errors; EXR is authoritative.
- Reference optical coefficients remain provisional and uncalibrated.
- Renderer outputs are sanity/regression evidence, not a calibrated appearance claim.

## Step 9 Completion Assessment

All Step 9 requirements are satisfied. The same validated canonical optical volume maps
to a deterministic Mitsuba scene, supported coefficient semantics are explicitly
converted, unsupported and approximated fields are reported, boundaries are represented
through oriented artifacts, all fixtures render without edits, orientation and scale are
verified, controlled trends are monotonic, and the core environment remains independent
of Mitsuba.

