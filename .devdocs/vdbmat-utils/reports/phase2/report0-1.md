# Phase 2 Execution Report — Steps 0 and 1

Date: 2026-07-07
Plan: [plan.md](../../plans/phase2/plan.md)
Scope: Step 0 (ops core, import-isolation extension, label-safety guard) and
Step 1 (scalar fields, exact EDT, quantization, boolean compose).

## Summary

Steps 0 and 1 complete. Two new subpackages — `vdbmat_utils.ops` (label-safe volume
operations: crop, pad, orient, place, apply_mask, remap_materials, merge_palettes,
compose) and `vdbmat_utils.fields` (`ScalarField`, exact NumPy-only Euclidean distance
transform, `quantize_to_labels`) — plus the plan D3 structural guards. No new
dependencies (plan D2 holds: no scipy). Test suite grew from 128 to 191 tests
(63 new), all green (`ruff`, `mypy --strict` over 59 files, `pytest`).
**Not committed** — same manual-push workflow as earlier phases.

## Step 0.0 finding — vdbmat asset-read API

The plan flagged verifying whether `vdbmat` exposes a public manifest reader for
pipeline inputs. It does: `vdbmat.io.read_material_label_manifest` (alongside
`inspect_material_label_manifest`) is public. **No `io/reader.py` wrapper is needed
and no upstream follow-up is raised.** Step 3 (pipeline engine) can use it directly.

## What was built

### `src/vdbmat_utils/ops/` (plan D5)

Pure functions `MaterialLabelVolume (+ params) -> MaterialLabelVolume`, each
re-validated through `build_material_label_volume`; provenance passes through from
the input (`base` for binary ops) until the pipeline engine (Step 3) assembles its own.

- `crop(min_zyx, max_zyx)` / `pad(before_zyx, after_zyx, fill_material_id)` — half-open
  index boxes, no implicit clamping; `local_to_world` is recomposed
  (`L @ translation(offset)`) so surviving voxels keep world positions.
- `orient(steps, update_transform=True)` — ordered `("flip", axis)` /
  `("rot90", from_axis, to_axis)` steps; data moves via exact `np.flip`/`np.swapaxes`,
  voxel sizes swap on rotation, and the inverse motion is composed into
  `local_to_world`. A net mirror (odd flips, det −1) is rejected as non-rigid unless
  `update_transform=False` (genuine re-orientation).
- `place(local_to_world, compose_with_existing=False)` — metadata only, never resamples.
- `apply_mask(mask, mode="keep"|"clear", fill_material_id)` — exact-geometry mask volume.
- `compose(base, overlay, mode="union"|"intersect"|"subtract")` — exact-geometry
  requirement with an error naming the mismatching field and the reconciling ops;
  union is last-writer-wins with palette merge; intersect/subtract keep the base palette.
- `remap_materials(mapping, definitions=None, prune_palette=True)` — LUT rewrite;
  collapsing ids must agree on definition; `definitions` renames by new id; pruning
  keeps only ids that still label voxels (background always kept).
- `merge_palettes` (`ops/palette.py`) — shared id merges only on identical
  name/role/external_id; conflicts point at `remap-materials`.

### `src/vdbmat_utils/fields/` (plan D2/D3)

- `ScalarField` — frozen dataclass (float64 z,y,x array + grid geometry, no palette).
- `squared_edt(mask, spacing)` / `signed_distance(mask, spacing)` (`fields/edt.py`) —
  in-repo Felzenszwalb-Huttenlocher separable lower-envelope algorithm, exact,
  deterministic, anisotropic spacing; all-false masks are `+inf` (the morphing
  "absent label" rule), all-true `-inf`. Row loops are plain Python per plan
  (acceleration is Phase 5).
- `quantize_to_labels(field, bin_edges, material_ids)` (`fields/quantize.py`) — the
  **only** sanctioned scalar→label conversion; strictly increasing edges, edge values
  go to the higher bin, NaN is an error.

### Guards (plan D3 / D1)

- `tests/unit/test_label_safety.py` — AST walk over `ops/` (and `morph/` once it
  exists) forbidding interpolating calls (`interp`, `map_coordinates`, `zoom`, …),
  float casts, and `.mean()` on label-ish names. `fields/` is exempt by design.
- `tests/unit/test_import_isolation.py` — rewritten from the Phase 1 mesh/image pair
  rule to an allowlist over all subpackages (`ops`/`fields` → `core` only; `morph` and
  `pipeline` allowlists pre-declared for Steps 2–3).
- `tests/unit/conftest.py` — shared `make_volume` factory fixture and a
  `world_centers` helper mapping foreground voxel centers to world coordinates,
  used by the transform-preservation tests.

## Deviations from the plan

- **`single_background_id` helper dropped:** `vdbmat.core.MaterialPalette` structurally
  guarantees background = id 0, exists, and is unique (verified from its source). Ops
  use a `BACKGROUND_ID = 0` constant; compose/mask/pad "default background" semantics
  are therefore simpler than planned, with no behavior difference.
- **`remap_materials` does not support role changes** in `definitions` overrides —
  roles are structural (only id 0 may be background), so only `name` is overridable.
- **`ops/resample.py` not written yet:** the plan schedules it in Step 3.2; noted here
  so the Step 3 executor doesn't assume it exists.
- **`compose` landed in Step 0's package but is Step 1 scope** (as planned — it needs
  the palette merge); listed under Step 1 in testing below.

## Test coverage added (63 tests)

- `test_ops_crop_pad.py` (8): expected-array literals, world-position preservation
  through `local_to_world` (crop and pad), out-of-range and negative-amount errors,
  unknown fill id, crop∘pad round trip restoring array and transform.
- `test_ops_transform.py` (13): world-preservation over six step sequences (all three
  rot90 planes, double rot90, flip pairs, mixed) on an array asymmetric along every
  axis; rot90 data/voxel-size swap; mirror rejection; `update_transform=False`
  re-orientation; bad-step errors; `place` replace and compose.
- `test_ops_mask.py` (5), `test_ops_remap.py` (7), `test_ops_palette.py` (2),
  `test_ops_boolean.py` (7): the D5 semantics incl. conflict errors naming
  `remap-materials` and exact-geometry errors naming the mismatching field.
- `test_fields_edt.py` (14): brute-force O(n²) comparison on random masks (3 seeds ×
  {2-D, anisotropic 2-D, anisotropic 3-D}), analytic single-point/empty/full cases,
  signed-distance signs and ±inf extremes, determinism double run, input validation.
- `test_fields_quantize.py` (6): bin mapping, higher-bin tie rule, NaN/edge/count
  errors, `ScalarField` validation.
- `test_label_safety.py` (1) and the rewritten import-isolation test (1).

## Verification log

```text
$ uv run ruff check .      → All checks passed!
$ uv run mypy src tests    → Success: no issues found in 59 source files
$ uv run pytest -q         → 191 passed in 1.74s
```

## Notes for the next steps

- Step 2 (morph core) can build directly on `signed_distance` + the per-label argmin
  loop described in plan D4; keep the O(labels × slice area) memory rule (two float64
  slices + one uint16 slice resident).
- Step 3 must add `ops/resample.py` (nearest-neighbor, D5) and register everything in
  the pipeline registry; `vdbmat.io.read_material_label_manifest` is the input reader.
- The `morph`/`pipeline` rows of the import allowlist and the `morph` half of the
  label-safety guard are already in place and will activate as those packages appear.
