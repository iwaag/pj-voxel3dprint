# Phase 1 Execution Report — Step 5

Date: 2026-07-06
Plan: [plan.md](../../plans/phase1/plan.md)
Scope: Step 5 (delete the superseded `vdbmat` image-stack tool; cross-repo).

## Summary

Step 5 complete. `vdbmat/tools/image_stack_generator/` and its test are
deleted outright (no deprecation shim, per the 2026-07-06 no-backward-compat
decision); the one forward-looking reference now points at
`vdbmat-utils convert-image-stack`. Both suites are green after the deletion:
`vdbmat` 357 passed, `vdbmat-utils` 126 passed. The precondition — Step 2's
contract tests green — has held since report2. **Not committed** — and note
this step *requires* two commits the manual workflow must make in order:
first in `vdbmat`, then the superproject gitlink bump (ADR-0001).

## What was deleted (in `vdbmat`)

- `tools/image_stack_generator/generate.py` (the 269-line ADR-009 D2
  reference generator whose logic was ported in Steps 1–2)
- `tests/tools/test_image_stack_generator.py` (directory now gone)

Both removed via `git rm`; the old behavior stays recoverable from git
history, and no equivalence test was added — the Step 2 contract tests are
the source of truth (plan Step 5.2).

## Reference sweep

Grepped `vdbmat` (and the utils repo + devdocs) for
`image_stack_generator` / `image-stack` / `tools/`:

- **Updated:** `README_EXTEND.md` §"conveniences for generator authors" — the
  pointer to `tools/image_stack_generator/generate.py` now names
  `vdbmat-utils convert-image-stack` (PGM/PNG) and the `vdbmat_utils.image`
  API as the reference generator.
- **Left as written (historical/generic, per plan):** ADR-0009's mentions of
  "image stacking" as a generator *category*; README_EXTEND's generic
  "2D image-stack importers" phrasing; `vdbmat_utils/image/__init__.py`'s
  docstring recording what it was ported from. The plan's expectation that
  `docs/phase0-feasibility-report.md` references the tool did not hold — its
  only `tools/` mentions are the unrelated `tools/phase0` Dockerfile.
- CI workflows and `pyproject.toml` never referenced the tool.

## Verification log

```text
vdbmat:        $ uv run pytest -q → 357 passed, 3 skipped (mitsuba/openvdb extras absent)
vdbmat-utils:  $ uv run pytest -q → 126 passed, 2 skipped (Pillow extra absent)
```

`uv run ruff check .` in `vdbmat` reports 8 pre-existing errors, all in
`examples/phase1/demo/blender_glass_demo.py` — untouched by this step (the
step only deletes files) and left for a `vdbmat`-side cleanup.

## Deviations from plan

- None in substance. The "bump the pinned dependency" sub-step translates,
  per ADR-0001, into updating the `vdbmat` submodule gitlink in
  `pj-voxel3dprint` once the `vdbmat` deletion commit exists — deferred to
  the manual commit workflow, with the contract suite (already green against
  the deleted-tool tree) as the gate.

## Next

Step 6 — docs (`voxelization.md`, `image-stacks.md`, `previews.md`,
README quick-start, ADRs 0004–0006), CI "Phase 1 exit criteria" step plus a
no-extras matrix leg, and the roadmap Phase 1 status update.
