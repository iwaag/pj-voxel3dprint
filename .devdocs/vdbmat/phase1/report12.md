# Phase 1 — Step 12 Report: Final Documentation and Review

- **Date:** 2026-07-02
- **Step:** 12 of 12 (`.local/phase1/plan.md`)
- **Status:** Complete. Phase 1 documentation, final decision status, reproducible
  quickstarts, exit-criteria review, and Phase 2 handoff are aligned with the tested
  implementation.

## 1. Final research MVP report

Created `docs/phase1-research-mvp-report.md`. It records:

- the direct JSON + NumPy material-label input and narrow watertight STL input,
  including explicit rejection and scale limits;
- accepted ADR-006 through ADR-008 decisions;
- pipeline configuration, stage order, deterministic identity, atomic publication,
  and run-bundle schemas;
- all seven CLI commands, exit codes 0–6, overwrite and JSON-output behavior, and
  success/failure boundaries;
- window-coupon and stepped-wedge geometry, counts, provenance, and source digests;
- analytic, end-to-end, default, Mitsuba, native, conformance, and installed-wheel
  evidence;
- Mitsuba baseline hashes and local screenshots, plus explicit Mitsuba/Cycles
  capability differences;
- runtime, peak-memory, dense-limit, wheel-size, and artifact-size observations;
- a matrix mapping every Phase 1 exit criterion to passing evidence;
- risks with an owner, consequence, and recommended action;
- a recommendation to proceed to a bounded Phase 2 without changing the canonical
  schema or Phase 0/1 contracts.

The report prominently states that coefficients are provisional and uncalibrated and
that software/render reproducibility is not a physical print prediction.

## 2. README and reproducible examples

Updated README to describe Phase 1 as complete and added a minimal end-to-end
quickstart for both supported inputs. The quickstart:

1. synchronizes the locked environment;
2. runs the direct-voxel coupon config;
3. validates its complete run bundle and checksums;
4. runs the explicit-unit stepped-wedge config;
5. validates that complete run bundle;
6. shows machine-readable inspection commands and links optional export guidance.

Example configs and their deterministic generator now publish quickstart output under
`.local/phase1/quickstart/`, rather than writing generated bundles below
`examples/phase1/configs/`. Regeneration produced config digests
`sha256:20861913…47cf4b` (coupon) and `sha256:26d1d3a0…4f296` (wedge).

The documented commands were executed verbatim from a clean quickstart output root.
Both pipelines and both full bundle validations returned status `ok`, with expected
shapes/counts and checksum status `ok`.

## 3. Final decisions and migration review

ADR-006, ADR-007, and ADR-008 were changed from Proposed to Accepted after Steps 2–11
demonstrated implementation and clean-environment reproduction. Phase 1 does not alter
ADR-001 through ADR-005 or `vbdmat.volume/1.0.0`, so no migration note is needed.

## 4. Phase 2 handoff

The final report fixes the following handoff:

- the commanded process-model input is the validated Phase 1
  `MaterialLabelVolume` in `material.zarr`, before optical mapping;
- a process stage is inserted before optical mapping and normally outputs the existing
  normalized `MaterialMixtureVolume` contract;
- any separate fill/void representation requires an explicit intermediate contract,
  not silent renormalization or optical-field overloading;
- every neighborhood operator declares physical support, XYZ cell halo, boundary
  condition, layer dependence, deterministic chunk semantics, and dense/chunked
  equivalence;
- per-material transfer, intentional boundary loss, void, and reactions are explicitly
  accounted for under a numeric conservation tolerance;
- printer XY resolution, layer thickness, build orientation, deposition order,
  material identities, and material-pair interactions are mandatory metadata gates;
- isolated impulse/line, XYZ boundary, overlap, alternating-layer, asymmetric pair,
  boundary-loss, mixture-ramp, and chunk-boundary fixtures are required to expose
  spread, blur, bleeding, mixing, and conservation behavior.

## 5. Verification

```text
README direct-voxel quickstart             pass
README mesh quickstart                     pass
full validation/checksums for both bundles pass
relative documentation link targets       pass
uv lock --check                            pass
uv run ruff format --check .               pass (84 files)
uv run ruff check .                        pass
uv run mypy --strict src/vbdmat            pass (44 source files)
uv run pytest -q                           374 passed, 2 native-only skipped
git diff --check                            pass
```

The two host skips remain only the pinned OpenVDB/Blender tests; Step 11 executed both
successfully in the native container. No unsupported scale, printer compatibility, or
physical-accuracy claim was added.

## 6. Recommendation

Phase 1 is complete. Proceed to Phase 2 only as a bounded process-model research phase.
Keep schema 1.0.0, the 2,000,000-cell dense safety bound, and renderer capability
diagnostics unchanged. Resolve the printer/process metadata gate before selecting or
fitting spread, blur, or mixing kernels.
