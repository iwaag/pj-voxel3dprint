# Phase 3 Execution Report — Step 0

Date: 2026-07-07
Plan: [plan.md](../../plans/phase3/plan.md)
Scope: Step 0 (vdbmat optics API verification; lattice hashing, formation domain,
gradient noise / fBm / ridged fBm; guard-test extensions).

## Summary

Step 0 complete. New subpackage `vdbmat_utils.procgen` with the determinism keystone
(`hashing.py`), the generation grid (`domain.py`), and the first primitives
(`noise.py`: gradient noise, fBm, ridged fBm returning `fields.ScalarField`). The
import-isolation and label-safety AST guards now cover `procgen`. No new dependencies
(plan D2 holds). Test suite grew from 219 to 256 tests (37 new), all green
(`ruff`, `mypy --strict` over 77 files, `pytest` including the `integration` leg).
**Not committed** — same manual-push workflow as earlier phases.

## Step 0.0 findings — vdbmat optics public API

Everything Phase 3 needs is public; **no upstream follow-ups raised**:

- **Built-in material-name table:** `vdbmat.optics.phase0_provisional_mapping()`
  returns the builtin `OpticalMappingConfig`; its material names are `air`,
  `axis-{x,y,z}-diagnostic`, `black-opaque-resin`, `transparent-resin`,
  `white-resin`. This is the table the D8 mapping-trigger rule compares against.
- **Canonical JSON + digest:** `OpticalMappingConfig.canonical_json` and `.digest`
  are public properties — no in-repo reimplementation needed (plan's fallback path
  is moot); the builtin digest resolves (`sha256:da83581c9…`).
- **Document I/O:** `vdbmat.optics.document.write_optical_mapping`,
  `load_optical_mapping`, and `optical_mapping_to_json_dict` are public.
  `io/optical_mapping.py` (Step 3) can build an `OpticalMappingConfig` and delegate
  serialization entirely.
- **EDT:** `fields/edt.py::squared_edt` / `signed_distance` are already N-D
  (per-axis separable loop over arbitrary `ndim` with per-axis spacing), so the
  Step 1.3 "generalize to 3-D" task reduces to adding a 3-D brute-force test.

## What was built

### `src/vdbmat_utils/procgen/hashing.py` (plan D3 — the keystone)

`hash_lattice(ix, iy, iz, *, stream_id, seed) -> uint64` — a SplitMix64-finalizer
fold over `(seed, x, y, z, stream)` in that fixed order, with per-input odd fold
keys, implemented in explicit `uint64` NumPy ops (broadcastable inputs; negative
coordinates wrap via two's complement; seed/stream wrap masked to 64 bits). Values
depend only on the five inputs — never on evaluation order or domain bounds.
`hash_to_unit` maps hashes to exact `[0, 1)` float64 via the top 53 bits. The
constants are pinned by golden-value tests (a failure there means every generated
formation would change) — to be recorded in ADR-0010 at Step 5.

### `src/vdbmat_utils/procgen/domain.py`

`FormationDomain(shape_zyx, voxel_size_xyz_m, local_to_world=identity)` with the
plan D2 size guards as fields (`max_axis_cells=256`, `max_total_cells=16_000_000`;
violations are `ConfigError`s naming the guard). `coordinates_xyz_m()` returns
voxel-centre metre coordinates as broadcastable per-axis arrays (`(i + 0.5) * size`),
so primitives handle anisotropic voxels once without materializing three dense
volumes. One deliberate clarification versus the plan's D4 wording: primitives
evaluate in **local-frame** metre coordinates; the rigid `local_to_world` placement
stays output metadata, exactly as in every other generator in the repo. This keeps
metre-denominated feature sizes (the point of "world-space" in D4) while matching
the repo-wide transform convention.

### `src/vdbmat_utils/procgen/noise.py` (plan D4)

- `gradient_noise(domain, *, frequency_per_m, stream_id, seed) -> ScalarField` —
  classic Perlin-style: hash-selected gradients from the fixed 12 cube-edge-vector
  table (`hash % 12`), quintic fade `6t⁵−15t⁴+10t³`, fixed x→y→z interpolation
  order. Range ≈ [−1, 1], not clamped. The lattice is anchored at the local origin,
  giving domain-extension invariance by construction.
- `fbm(…, octaves, lacunarity=2.0, gain=0.5)` — octave `i` uses frequency
  `f·lacunarity^i`, amplitude `gain^i`, stream id `stream_id + i` (the D3 stream
  scheme); normalized by total amplitude so range is octave-count-independent.
- `ridged_fbm(…)` — per octave `(1 − |noise|)²`, accumulated exactly like `fbm`;
  output in [0, 1] with ridge sheets near 1 (the veins/fractures guide field).

All three return `ScalarField` carrying the domain's geometry — continuous math
stays in `fields` space per D6; no label types appear anywhere in `procgen` yet.

### Guard-test extensions

- `test_import_isolation.py`: `procgen` allowlisted to `{core, io, fields, preview}`.
- `test_label_safety.py`: `procgen` added to the guarded packages (no float casts,
  no interpolating calls, no label averaging). The noise implementation was written
  to comply (no `astype(float…)` anywhere — int casts only for lattice indices).

## Tests added

- `tests/unit/test_procgen_hashing.py` (6 tests): golden hash values pinning the
  constants; broadcasting ≡ elementwise; **domain-extension invariance** (8³ interior
  of a 12³ evaluation is byte-equal); stream/seed sensitivity; `[0,1)` range and
  mean-uniformity of `hash_to_unit`; input validation (float coords, negative or
  bool stream/seed).
- `tests/unit/test_procgen_noise.py` (13 tests): domain validation incl. both size
  guards; voxel-centre coordinate values under anisotropic voxels; ScalarField
  geometry pass-through; range and variation; smoothness (max neighbour step bound
  at 10 voxels/cell); byte-equal determinism double-run; **domain-extension
  invariance for all three primitives**; stream/seed sensitivity; voxel size enters
  evaluation; `fbm(octaves=1)` ≡ `gradient_noise`; octave normalization keeps range;
  ridged range [0, 1]; parameter validation (`ProcgenError`s).

## Verification

- `uv run ruff check src tests` — clean.
- `uv run mypy src tests` (strict) — clean, 77 files.
- `uv run pytest tests -q` — 256 passed (unit + contract + integration).

One test-side adjustment during the run: the initial smoothness bound (0.8 at
400 /m) was tighter than the true derivative bound of gradient noise at 0.4 cells
per step; retuned to 10 voxels per lattice cell with a 0.35 step bound.

## Next

Step 1 — Worley cells (`cells.py`), domain warping (`warp.py`), morphology,
union-find connectivity, and the 3-D brute-force EDT test. Awaiting go-ahead.
