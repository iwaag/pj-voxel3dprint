# Phase 0 Implementation Report: Step 5

**Date:** 2026-06-28
**Completed scope:** Step 5 — Build Deterministic Synthetic Fixtures
**Status:** Complete

## Summary

Step 5 implemented six small deterministic fixture generators, machine-readable expectation manifests, a fixture inspection example, and regression coverage for summaries, selected cells, bounds, world locations, reproducibility, and axis transposition.

The fixtures produce the canonical material volumes implemented in Step 4. They do not embed provisional optical coefficients; that conversion belongs to Step 6.

This is the selected stopping point. Step 6, which implements the minimal material-to-optical mapping, is intentionally not started in this report.

## Implemented Artifacts

### Synthetic fixture package

Added `src/vbdmat/fixtures/` as a separate package above the lightweight core:

- `synthetic.py` contains generators and expectation types;
- `__init__.py` exposes the stable fixture API.

This placement allows tests, examples, and later renderer proofs to share fixtures without adding fixture concerns to `vbdmat.core`.

### Fixture wrapper and manifest

Added:

- `SyntheticFixture` pairing one canonical volume with expectations;
- `FixtureManifest` containing name, description, shape, bounds, material summaries, and selected cells;
- `SelectedCellExpectation` containing array index, world centre, and either material ID or fraction vector.

Every manifest includes:

- canonical `shape_zyx`;
- local XYZ minimum and maximum bounds in metres;
- world-axis-aligned XYZ bounds in metres;
- exact material voxel counts for label volumes;
- exact material fraction totals for mixture volumes;
- selected cell values and world-space centres.

### Deterministic provenance

Every generated volume uses:

- generator `vbdmat.synthetic-fixtures`;
- generator version `1.0.0`;
- a stable `fixture:<name>` source identifier;
- no generated timestamp.

Omitting timestamps makes repeated generation structurally identical.

### Fixture generators

#### Homogeneous transparent

- Asset: material-label volume.
- Shape: `(2, 3, 4)` in ZYX order.
- Material ID: transparent resin `1`.
- Count: 24 cells.

#### Homogeneous scattering white

- Asset: material-label volume.
- Shape: `(2, 3, 4)`.
- Material ID: white resin `2`.
- Count: 24 cells.

The word “scattering” describes the intended Step 6 mapping. The Step 5 material identity does not itself claim an optical coefficient.

#### Transparent/opaque interface

- Asset: material-label volume.
- Shape: `(2, 4, 6)`.
- X cells `0..2`: transparent resin `1`.
- X cells `3..5`: black opaque resin `3`.
- Counts: 24 transparent and 24 opaque cells.
- Interface plane: world X coordinate `0.01012 m`.

#### Layered material slab

- Asset: material-label volume.
- Shape: `(4, 3, 5)`.
- Z-layer sequence: `(1, 2, 3, 1)`.
- Counts: 30 transparent, 15 white, and 15 black cells.
- The non-palindromic layer sequence exposes Z reversal.

#### Two-material mixture ramp

- Asset: material-mixture volume.
- Shape: `(2, 3, 5)`.
- Material axis: background `0`, transparent `1`, white `2`.
- Background fraction: zero throughout.
- X ramp: transparent/white fractions from `(1, 0)` through `(0.5, 0.5)` to `(0, 1)`.
- Fraction totals: 0 background, 15 transparent, and 15 white cell-equivalents.

#### Anisotropic axis marker

- Asset: material-label volume.
- Shape: `(2, 3, 4)`.
- Voxel size XYZ: `(40, 50, 30)` micrometres.
- X marker: ID `10`, length 4.
- Y marker: ID `20`, length 3.
- Z marker: ID `30`, length 2.
- Background: 15 cells.

The unequal shape, unequal voxel sizes, separate marker locations, and distinct marker IDs make all three pairwise spatial-axis swaps detectable.

### Inspection example

Added `examples/phase0/inspect_synthetic_fixtures.py`. It generates all fixtures in stable order and prints shape, material summary, and world bounds.

Run it with:

```bash
uv run python examples/phase0/inspect_synthetic_fixtures.py
```

Updated `README.md` with the fixture package, command, and fixture-set summary.

## Test Coverage Added

Added `tests/fixtures/test_synthetic.py` with 29 tests. The complete suite now contains 132 tests.

Coverage includes:

- stable generator order and fixture names;
- byte-value-equivalent arrays across repeated generation;
- identical manifests, geometry, and provenance;
- absence of nondeterministic timestamps;
- manifest shape and local bounds;
- selected values recomputed from each canonical volume;
- selected world centres recomputed from grid geometry;
- material counts recomputed with NumPy;
- mixture totals recomputed with float64 accumulation;
- exact expected summaries for all six fixtures;
- translated world bounds and anisotropic extents;
- homogeneous material uniformity;
- exact interface regions and world interface plane;
- non-palindromic layer sequence;
- exact five-step linear mixture ramp;
- axis marker arrays and physical world deltas;
- Z/Y, Z/X, and Y/X swaps rejected by canonical shape validation.

## Decisions Made

1. **Step 5 fixtures are material-domain inputs.** Transparent, white, and opaque names identify intended materials; Step 6 owns their provisional optical mapping.
2. **The mixture ramp has three palette entries but two active materials.** Background remains required by schema and has zero fraction.
3. **All fixtures use translated anisotropic geometry.** This exercises units and world placement rather than only identity-space indexing.
4. **Expectation manifests are code-generated immutable data.** No binary fixture payloads are committed.
5. **Material summaries differ by volume type.** Label volumes report integer voxel counts; mixture volumes report float64-accumulated fraction totals.
6. **Selected expectations include world centres.** This couples value checks to the accepted coordinate contract and catches half-voxel mistakes.
7. **The axis marker uses disjoint lines.** X, Y, and Z marker values do not overwrite each other, so their expected counts remain direct.
8. **The fixture package is shipped with the distribution.** It is useful to downstream adapter proofs and is not test-only data.

## Verification Results

| Check | Result |
| --- | --- |
| Six required generators | Passed |
| Homogeneous transparent count | Passed; 24 cells |
| Homogeneous white count | Passed; 24 cells |
| Interface counts and plane | Passed; 24/24 cells |
| Layer sequence and counts | Passed |
| Linear mixture values and totals | Passed |
| Axis marker counts and world deltas | Passed |
| Repeated generation | Passed; arrays, manifests, geometry, and provenance agree |
| Selected cell values | Passed for every fixture |
| Selected world locations | Passed for every fixture |
| Local and world bounds | Passed |
| All three pairwise axis swaps | Passed; each is rejected by shape validation |
| Inspection example | Passed and printed all summaries |
| pytest | Passed; 132 tests, including 29 Step 5 tests |
| Ruff formatting | Passed; 20 Python files formatted |
| Ruff linting | Passed |
| mypy strict check | Passed; 13 source files checked |
| `uv lock --check` | Passed; 24 packages resolved |
| Git whitespace check | Passed |
| Package build | Passed; sdist and wheel built with uv |
| Wheel content | Passed; `vbdmat/fixtures` is included |

## Deviations and Observations

- No Step 5 requirement remains open.
- The plan used the phrase “homogeneous scattering/white volume.” The generated volume contains the white material command, not `sigma_s`; assigning scattering is deliberately deferred to Step 6.
- Floating-point bounds can display binary representation tails when printed, such as `0.030119999999999997`. Tests use numeric comparison and canonical values remain float64.
- The manifest records world axis-aligned bounds. All current fixtures use translation-only placement, but the calculation evaluates all eight corners and also supports later rigid rotations.
- Generated `dist/` artifacts are ignored and are not source deliverables.

## Step 5 Completion Assessment

The Step 5 verification requirements are satisfied:

- generation is deterministic and free of random or timestamp state;
- each fixture has exact material summaries, selected values, bounds, and world positions;
- expected values are recomputed in tests rather than trusted only from manifests;
- all fixtures are small enough to inspect directly;
- the anisotropic marker fails canonical validation for any pairwise spatial-axis swap;
- no opaque binary fixture data is required.

## Next Step

Proceed with Step 6 by implementing a deterministic provisional mapping from material labels or mixtures into optical volumes:

- define explicit provisional properties for background, transparent, white, black, and axis-marker materials;
- implement label lookup and documented mixture rules;
- preserve geometry, schema, configuration, and provenance;
- confirm pure mixture endpoints equal their base materials;
- calculate ramp values by hand and in tests;
- reject unknown materials and invalid mapping configurations;
- label all output coefficients as provisional and uncalibrated.
