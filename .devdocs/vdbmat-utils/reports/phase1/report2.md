# Phase 1 Execution Report — Step 2

Date: 2026-07-06
Plan: [plan.md](../../plans/phase1/plan.md)
Scope: Step 2 (image-stack CLI, PNG extra, shared fixture, contract + integration
tests). `image/png.py` itself was already written in Step 1 (see report1).

## Summary

Step 2 complete: the image-stack workflow now satisfies exit criterion §1.2 end to
end — `vdbmat-utils convert-image-stack` → `vdbmat-utils validate` →
`vdbmat import-voxels` → `vdbmat convert` all pass, covered by an
`integration`-marked test. Suite grew from 76 to 85 tests, green under both installs:
85 passed with the `image` extra, 83 passed + 2 PNG skips on the base install.
**Not committed** — manual-push workflow.

## What was built

### CLI — `convert-image-stack` (`cli/main.py`)

`vdbmat-utils convert-image-stack SLICES_DIR --config CONFIG --out DIR --name NAME`
with overrides `--voxel-size X Y Z` and `--format pgm|png` applied via
`dataclasses.replace`, so the *effective* post-override config is what gets digested
into provenance (D5). On success it prints the manifest path plus the material-count
summary (reusing Step 0's `material_counts`). Failures flow through the existing
expected-error handler: single-line `error: …`, exit 1.

### Asset identity (D6) — `stack_identity` in `image/stack.py`

`identity` = SHA-256 over the concatenated per-slice `sha256:` digests (provenance
`sources`, stack order) plus the configuration digest; passed to `write_asset` and
recorded in the manifest's source block.

### `image` extra and PNG

`pyproject.toml` `image` extra now carries `pillow>=10`. Unit tests (skipped cleanly
when Pillow is absent): PNG stack produces the identical label array as the PGM stack;
RGB PNG rejected. The "PNG requires the 'image' extra" message is tested by hiding
`PIL` via `monkeypatch` so it runs in both environments.

### Shared fixture — `fixtures.write_image_stack_fixture`

Deterministic in-code generator (no binaries in git): writes a 3×4×5 PGM stack with
the `(7z + 3y + x) % 3` axis-asymmetric pattern, three materials (gray 0→`air`
background, 100→`transparent-resin`, 255→`white-resin`). Gray/material ids 0–2 were
chosen deliberately so the palette stays inside the pinned vdbmat builtin optical
mapping (`phase0-provisional-materials-v1`), keeping `vdbmat convert` runnable without
an external mapping document. Used by unit, contract, and integration tests alike.

### Contract tests — `tests/contract/test_image_stack_contract.py`

- **Determinism**: two full CLI runs are byte-equal (manifest + payload).
- **Checksum stability**: hardcoded payload and manifest SHA-256 goldens.
- **Material-count conservation**: per-material counts summed over the source slices
  equal `material_counts` of the produced volume.
- Output passes `vdbmat-utils validate` and the manifest records the D6 identity.

### Integration test — `tests/integration/test_convert_image_stack.py`

Fixture stack → `convert-image-stack` (in-process `main`) → `vdbmat import-voxels` →
`vdbmat convert` (both via `subprocess`, mirroring `test_import_voxels.py`), asserting
exit 0 and that the optical Zarr exists. Marker `integration`.

## Fix found by the goldens

The ported provenance note included the slices directory basename
(`layered image stack from {dir.name}`), making the manifest digest depend on where
the input happened to live — caught immediately by the golden test when the fixture
was generated under a different directory name. The note is now the fixed string
`"layered image stack; rows=+Y, columns=+X"`; the manifest digest depends only on
slice bytes and configuration.

## Verification log

```text
$ uv run --extra image ruff check .   → All checks passed!
$ uv run --extra image mypy src tests → Success: no issues found in 29 source files
$ uv run --extra image pytest -q      → 85 passed
$ uv sync && uv run pytest -q         → 83 passed, 2 skipped (PNG tests skip without Pillow)
```

## Deviations from plan

- The fixture generator lives in `src/vdbmat_utils/fixtures.py` (the plan offered
  this or a tests helper) so later phases and docs can reuse it, matching where the
  Phase 0 volume presets live.
- Slice-count conservation is asserted per material id (aggregated over slices),
  which is equivalent to the plan's "counts in slices == counts in volume".

## Next

Step 3 — mesh loader and voxelizer core, ported from `vdbmat` git history
(`git show 8f55562:…`), starting with source recovery and memo verification (3.0).
