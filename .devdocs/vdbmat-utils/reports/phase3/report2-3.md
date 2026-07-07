# Phase 3 Execution Report — Steps 2 and 3

Date: 2026-07-07
Plan: [plan.md](../../plans/phase3/plan.md)
Scope: Step 2 (formation statistics and constraints) and Step 3 (formation
models, optical mapping emission, `generate-formation`, and `formation-stats`).

## Summary

Steps 2 and 3 are implemented. `vdbmat_utils.procgen` now computes formation
statistics and structured constraint results, and can generate material-label
formation assets through ordered host/strata/vein/grain/pore/fracture layers.
The CLI gained `generate-formation` and `formation-stats`. Non-built-in
material names trigger a companion `vdbmat.optical-mapping` document; the
document is built with vdbmat's public optics API, validates with
`load_optical_mapping`, and records the mapping digest in provenance sources.

No new runtime dependencies were added.

## Step 2 — Stats and Constraints

- Added `procgen/stats.py`.
- Computes per material:
  - exact voxel count and volume fraction,
  - local-thickness percentiles from the plan D7 proxy (`2 * EDT(mask)` at mask
    voxels, anisotropic spacing in z/y/x order),
  - 6-connected component count,
  - largest-component fraction,
  - minimum printable thickness value.
- Added structured constraint evaluation for:
  - `volume-fraction`,
  - `min-feature-size`,
  - `connected` (`single-component` or max components),
  - `min-largest-component-fraction`,
  - `min-printable-thickness`.
- Added canonical sorted JSON stats report serialization.

Note: the slab test interpretation follows D7's explicit `2 * EDT(mask)` proxy.
That proxy is conservative and does not implement future full sphere-fitting
local thickness.

## Step 3 — Models, Mapping, CLI

- Added `procgen/models/FormationConfig`, `generate_formation`, and
  `write_formation`.
- Implemented ordered painter assembly:
  - host fill or fBm-quantized host,
  - unwarped or fBm-warped strata,
  - sheet-like veins and fractures,
  - Worley site-id grains with hash-stable weighted material picks,
  - noise-thresholded pores with optional boolean opening.
- Added palette validation after each layer; errors name the offending layer.
- Added `io/optical_mapping.py`.
  - Built-in material names and canonical digest come from vdbmat's public
    `phase0_provisional_mapping`.
  - Custom mapping documents are written through vdbmat's public
    `write_optical_mapping`.
  - The user config supplies coefficients only for non-built-in material names.
    The emitted document covers the full palette so it can be used directly by
    `vdbmat convert`.
- Added CLI:
  - `vdbmat-utils generate-formation --config CONFIG --out DIR --name NAME
    [--seed N] [--strict]`
  - `vdbmat-utils formation-stats MANIFEST [--constraints CONFIG] [--out FILE]`

## Tests Added

- `tests/unit/test_procgen_stats.py`
  - volume fractions,
  - component counts and largest-component fractions,
  - constraint pass/fail cases,
  - anisotropic local-thickness proxy,
  - empty-material stats.
- `tests/unit/test_procgen_models.py`
  - exact unwarped strata bands,
  - painter precedence,
  - palette violation errors naming the layer,
  - no mapping file for all-built-in palettes,
  - custom mapping emission and `load_optical_mapping` validation,
  - missing custom coefficients fail,
  - `--strict` returns exit 1 on failed constraints.

## Verification

- `uv run ruff check src tests` — clean.
- `uv run mypy src tests` — clean, 88 files.
- `uv run pytest tests -q` — 286 passed.
- Manual smoke:
  - generated a small formation,
  - validated it with `vdbmat-utils validate`,
  - recomputed stats with `formation-stats`,
  - checked emitted mapping digest with `vdbmat mapping-digest`.

## Status

Steps 2 and 3 are complete. Not committed.
