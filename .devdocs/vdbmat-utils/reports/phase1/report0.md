# Phase 1 Execution Report — Step 0

Date: 2026-07-06
Plan: [plan.md](../../plans/phase1/plan.md)
Scope: Step 0 (preview and diagnostics module, no new dependencies).

## Summary

Step 0 complete. New `vdbmat_utils.preview` package plus two CLI subcommands
(`material-counts`, `preview-slices`), all NumPy-only so they work in the base install
without OpenVDB or matplotlib. Test suite grew from 45 to 59 tests, all green
(`ruff`, `mypy --strict` over 22 files, `pytest`). **Not committed** — same
manual-push workflow as Phase 0 steps.

## What was built

### `src/vdbmat_utils/preview/__init__.py`

- `material_counts(volume) -> dict[int, int]` — voxel counts per material id via
  `np.unique`, keyed and ordered by the palette so unused palette entries appear with
  count 0 (useful for spotting "declared but never painted" materials).
- `slice_ascii(volume, axis, index) -> str` — one character per voxel: `.` for the
  background role, `0-9a-z` cycling by material id otherwise. The first line is an
  orientation legend (e.g. `slice z=2  +x →  +y ↓`) so any transpose inside the
  preview or an upstream generator is visible to the eye.
- `slice_pgm(volume, axis, index, path) -> Path` — binary P5 PGM; each palette id maps
  to a deterministic gray level (rank in ascending-id order spread evenly over 0–255).
- `PreviewError(VdbmatUtilsError)` — raised for an unknown axis or an out-of-range
  slice index, with the shape and valid range in the message. Defined in the preview
  package (not `core/errors.py`) to keep `core` generator-agnostic, matching the
  pattern the plan prescribes for `ImageStackError` in Step 1.

Slice geometry: perpendicular axis chosen from canonical `z, y, x` array order; the
slice's rows/columns are the remaining axes in array order (`z`→(y,x), `y`→(z,x),
`x`→(z,y)).

### CLI (`cli/main.py`)

- `vdbmat-utils material-counts MANIFEST [--json]` — human-readable lines
  (`1 (resin_clear, material): 30`) or a JSON object keyed by material id.
- `vdbmat-utils preview-slices MANIFEST [--axis z|y|x] [--index N] [--out FILE.pgm]` —
  ASCII to stdout by default; `--index` defaults to the middle slice; `--out` writes a
  PGM instead. `PreviewError` flows through the existing expected-error handler
  (single-line `error: …`, exit 1).

### Tests

- `tests/unit/test_preview.py` (10 tests): counts on the `anisotropic` and
  `multimaterial` fixture presets (values derived by hand from the `(7z+3y+x) % n`
  pattern, not recomputed with the code under test); zero-count palette entry;
  **golden ASCII on all three axes** of the `multimaterial` preset — its label pattern
  is asymmetric along every axis, so any z/y/x flip changes the golden text; PGM output
  byte-golden including the header; out-of-range and unknown-axis rejection.
- `tests/unit/test_cli.py` (+5 tests): both output modes of `material-counts`,
  default-middle-slice ASCII, PGM `--out`, and bad index → exit 1.

## Verification log

```text
$ uv run ruff check .    → All checks passed!
$ uv run mypy src tests  → Success: no issues found in 22 source files
$ uv run pytest -q       → 59 passed
$ uv run vdbmat-utils generate-fixture multimaterial -o <dir>
$ uv run vdbmat-utils material-counts <dir>/multimaterial.voxels.json
0 (void, background): 15
1 (resin_clear, material): 15
2 (resin_white, material): 15
3 (quartz_vein, material): 15
$ uv run vdbmat-utils preview-slices <dir>/multimaterial.voxels.json --axis z --index 2
slice z=2  +x →  +y ↓
23.
123
.12
3.1
```

## Deviations from plan

- None substantive. `slice_pgm` returns the written `Path` (convenient for the CLI
  message and tests); the plan did not specify a return value.
- The gray-level rule is pinned as "rank in ascending-id order × (255 // (n−1))" and
  byte-golden-tested, so a palette gaining a material will deliberately change PGM
  goldens — acceptable, previews are diagnostics, not contract outputs.

## Next

Step 1 — image-stack core port (`image/pgm.py`, `image/stack.py`,
`ImageStackConfig`, unit tests), porting from
`vdbmat/tools/image_stack_generator/generate.py`.
