# Phase 3 Execution Report — Step 1

Date: 2026-07-07
Plan: [plan.md](../../plans/phase3/plan.md)
Scope: Step 1 (Worley cells, domain warping, binary morphology, union-find
connectivity, 3-D EDT verification).

## Summary

Step 1 complete. `vdbmat_utils.procgen` gained the remaining reusable primitives:
Worley/Voronoi cellular fields (`cells.py`), coordinate-displacement domain warping
(`warp.py`), boolean morphology (`morphology.py`), and 6-connected components
(`connectivity.py`). Supporting refactor: every noise primitive now has a
coordinate-level `*_at` form — the mechanism warping plugs into. Still no new
dependencies. Test suite grew from 256 to 276 tests (20 new), all green (`ruff`,
`mypy --strict` over 83 files, `pytest` including the `integration` leg).
**Not committed** — same manual-push workflow as earlier phases.

## Step 1.3 finding — EDT already 3-D

`fields/edt.py` is dimension-generic (separable per-axis loop), and
`tests/unit/test_fields_edt.py` already brute-force-verifies a 3-D anisotropic case
(`(4, 5, 6)` with spacing `(1.0, 0.25, 3.0)`). The plan's "verify/generalize for 3-D"
task required **no code or test change** — recorded here as the verification.

## What was built

### Noise refactor (`noise.py`)

`gradient_noise_at`, `fbm_at`, `ridged_fbm_at` evaluate at arbitrary broadcastable
metre-coordinate arrays; the domain-level `gradient_noise`/`fbm`/`ridged_fbm` are now
thin wrappers that pass voxel-centre coordinates and box the result in `ScalarField`.
Identical algorithm and constants — the Step 0 golden/invariance tests pass unchanged,
confirming the refactor is behavior-preserving.

### `procgen/hashing.py` addition

`hash_derive(hashes, *, salt)` — derives independent uniform draws from one lattice
point's hash (`mix(h ^ (2·salt+1)·KEY)`), used for the three jitter components of a
Worley feature point and, later, per-cell material picks (plan D5 grains). Constants
join the ADR-0010 set.

### `procgen/cells.py` (plan D4)

`worley(domain, *, cell_size_m, stream_id, seed) -> WorleyCells` and the
coordinate-level `worley_at`. One feature point per lattice cell (pitch in world
metres), position jittered by three `hash_derive` draws, searched over the 3×3×3
neighbourhood. Outputs: `f1`, `f2` (metre distances, `ScalarField`), `site_id`
(uint64 hash identity of the nearest feature point — stable under domain changes),
and `WorleyCells.boundary()` = `f2 − f1` (the crystal-boundary field). Semantics
note fixed for ADR-0011: the 3×3×3 window **is the definition** of f1/f2/site_id,
not an approximation — the brute-force tests use the same window.

### `procgen/warp.py` (plan D4)

`warped_coordinates(domain, *, offsets_xyz, amplitude_m)` returns voxel-centre
coordinates displaced by `amplitude_m · offsets` — ready to feed any `*_at`
primitive. Warping therefore displaces *coordinates before evaluation* and never
resamples an evaluated field: no interpolation exists anywhere on this path (plan
D6). Offset fields must match the domain's shape and voxel size (validated).

### `procgen/morphology.py` (plan D4)

`dilate`/`erode`/`open_mask`/`close_mask` on 3-D bool arrays, 6- or 26-neighbourhood,
iterated one-step operations via padded boolean shifts (no wraparound). Boundary
rule (documented in docstrings): outside-domain cells are `False`, so erosion is
conservative at walls — a slab against the boundary is not treated as infinitely
thick, the right bias for printability checks. Bool-only by validation (plan D6).

### `procgen/connectivity.py` (plan D7)

`connected_components(mask) -> ComponentResult(component_ids, count, sizes)` —
6-connected, NumPy-extracted adjacency edges + Python union-find with path halving,
components renumbered deterministically by first-encountered voxel in C order.
`uint32` ids, 0 = background.

## Tests added

- `tests/unit/test_procgen_cells.py` (8 tests): Worley f1/f2/site_id against an
  independent brute-force reimplementation built on the public hash API (re-pins the
  jitter salt scheme); f1 ≥ 0, f2 ≥ f1, boundary ≥ 0, multiple cells present;
  byte-equal determinism + stream sensitivity; **domain-extension invariance** for
  f1 and site_id; pitch validation; warp: array equality with manual composition and
  `fbm_at(warped) ≡ fbm_at(manual)` byte-equal; zero-amplitude identity; negative
  amplitude and shape/voxel-size mismatch errors.
- `tests/unit/test_procgen_morphology.py` (12 tests): single-voxel dilation goldens
  for 6 and 26 neighbourhoods; box erosion golden; boundary-conservative erosion of
  a wall-touching slab; no wraparound; opening removes a one-voxel sheet; closing
  fills a one-voxel gap between slabs; radius-0 identity; dtype/shape/connectivity
  validation; components: two blobs with sizes and first-seen numbering, diagonal
  touch separate under 6-connectivity, empty/full masks, U-shape merging across scan
  order (exercises the union step), validation.

Two test-side corrections during the run (implementation was right, expectations
were not): opening with a supporting spine does *not* clear the sheet (the spine
protects one voxel — spine removed from the fixture), and closing a 1-voxel-thick
*line* gap under 6-connectivity does not fill (classic result; fixture changed to
slabs, where it does).

## Verification

- `uv run ruff check src tests` — clean.
- `uv run mypy src tests` (strict) — clean, 83 files.
- `uv run pytest tests -q` — 276 passed (unit + contract + integration).

## Next

Step 2 — `procgen/stats.py`: volume fractions, local-thickness percentiles (2×EDT
proxy on the verified 3-D EDT), connectivity metrics, constraint evaluation, and
`.stats.json` serialization. Awaiting go-ahead.
