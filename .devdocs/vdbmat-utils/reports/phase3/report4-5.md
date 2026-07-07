# Phase 3 Execution Report — Steps 4 and 5

Date: 2026-07-07
Plan: [plan.md](../../plans/phase3/plan.md)
Scope: Step 4 (sweeps, reference fixtures, contract/integration tests) and
Step 5 (documentation, CI, and phase close-out).

## Summary

Steps 4 and 5 are complete. Phase 3 now has the sweep workflow, committed
reference formation configs, contract and integration coverage for deterministic
generation and vdbmat handoff, user documentation, ADRs 0010-0012, CI exit
criteria, and an updated roadmap status block.

No new runtime dependencies were added.

## Step 4 — Sweeps, References, Tests

- Added `procgen/sweep.py` and the `vdbmat-utils sweep-formation` CLI.
  - `SweepConfig` declares a `base` formation config plus explicit dotted-path
    axes.
  - The Cartesian product is bounded by `max_runs`.
  - Each run writes its own formation directory.
  - `sweep_summary.json` records overrides, formation config digests, payload
    digests, mapping digests, and stats with root-relative paths so double runs
    are byte-stable.
- Added reference configs under `examples/phase3/`:
  - `marble-like.formation.json`
  - `granite-like.formation.json`
  - `tiny-sweep.sweep.json`
- Added Phase 3 contract tests:
  - byte-equal double runs for `generate-formation`,
  - byte-equal double runs and golden digest for `sweep-formation`,
  - payload and stats digest goldens for both reference formations,
  - seed-change anti-fixed-output check,
  - ASCII orientation goldens on all three axes of the asymmetric marble-like
    formation.
- Added Phase 3 integration tests:
  - reference formation generation with `--strict`,
  - `vdbmat-utils validate`,
  - `vdbmat import-voxels`,
  - `vdbmat mapping-digest`,
  - `vdbmat convert --mapping-file`,
  - digest equality between the emitted mapping and convert output.

Implementation note: vdbmat's voxel manifest schema does not serialize arbitrary
`Provenance.sources`; Phase 3 records the mapping digest in the manifest
`source.notes`, which survives the asset handoff without schema changes.

## Step 5 — Docs, CI, Close-Out

- Added user docs:
  - `docs/procedural.md`
  - `docs/stats.md`
  - `docs/optical-mappings.md`
- Added ADRs:
  - ADR 0010: procedural determinism
  - ADR 0011: formation model
  - ADR 0012: metrics and optical-mapping emission
- Updated `README.md` with Phase 3 commands and documentation links.
- Updated `.github/workflows/ci.yml`:
  - minimal-install Phase 3 workflow: generate both reference formations,
    recompute stats, validate, import, and convert with mapping files;
  - integration Phase 3 exit criteria: reference generation, sweep, stats,
    validation, mapping digest, import, and convert.
- Updated `roadmap_vdbmat-utils.md` Phase 3 status to complete.
- Re-checked upstream follow-ups: Step 0 found no missing public optics APIs.
  Existing Phase 0/1 follow-ups remain open (`py.typed`, `Matrix4` re-export,
  example ruff errors, submodule pin bump).

## Verification

- `uv run ruff check .` — clean.
- `uv run mypy src tests` — clean, 91 source/test files.
- `uv run pytest tests -q` — 293 passed.

## Status

Phase 3 Steps 4 and 5 are complete. Not committed.
