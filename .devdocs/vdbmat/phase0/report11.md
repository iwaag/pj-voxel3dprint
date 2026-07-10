# Phase 0 Implementation Report: Step 11

**Date:** 2026-06-29  
**Completed scope:** Step 11 — Add Cross-Consumer Conformance Checks  
**Status:** Complete

## Result

Added a renderer-independent conformance module and command that process all six
canonical fixtures through exact Zarr persistence and both pure consumer conversions.
The command compares shared contracts before renderer-specific scene construction and
attributes every failure to `canonical`, `serialization`, `adapter_conversion`, or
`image_sanity`.

The contract-only run passed 60/60 checks. A second run inspected all existing proof
PNGs and passed 72/72 total checks. Reports were generated as:

- `.local/phase0/conformance-step11.json`
- `.local/phase0/conformance-step11-with-images.json`

## Implemented checks

For each fixture:

1. canonical units and ZYX dimensions;
2. exact optical-volume Zarr round-trip;
3. exact OpenVDB component-grid reconstruction;
4. exact Mitsuba extinction/albedo conversion;
5. full world-domain corner and transform equality;
6. region values and canonical boundary locations;
7. zero-extinction background treatment;
8. coefficient units and scale factor;
9. common scattering-weighted global `g`;
10. complete capability reports and explicit expected differences.

The optional standard-library PNG inspector verifies fixture coverage, readable image
payloads, dimensions, channels, and non-flat spatial output. It deliberately does not
compare pixels between renderers. Axis ordering and scale are checked at field and
transform level, where failures can be attributed reliably.

## Expected differences

- Mitsuba consumes RGB `sigma_t`/albedo; Cycles consumes equal-weight scalar density
  grids while OpenVDB retains all RGB component grids.
- Both reduce spatial `g` to the same weighted scalar.
- Mitsuba emits derived IOR interface meshes; Cycles retains the IOR grid but does not
  consume internal interfaces.
- Scene, camera, light, boundary behavior, and transport differ, so final pixels are
  not physically equated.

These differences are present in every machine-readable report and documented in
`docs/conformance/phase0-cross-consumer.md`; no fixture-specific correction was added.

## Verification commands

```bash
uv run python examples/phase0/check_cross_consumer_conformance.py \
  .local/phase0/conformance-step11.json

uv run python examples/phase0/check_cross_consumer_conformance.py \
  .local/phase0/conformance-step11-with-images.json \
  --mitsuba-renders .local/phase0/mitsuba-step9 \
  --cycles-renders .local/phase0/cycles-step10-native \
  --cycles-width 16 --cycles-height 16
```

The 16 × 16 Cycles artifacts are the current one-sample native integration smoke
outputs. The adapter's documented reference configuration remains 64 × 64 at 32
samples.

