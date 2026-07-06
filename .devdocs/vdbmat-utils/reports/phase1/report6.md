# Phase 1 Execution Report — Step 6

Date: 2026-07-07
Plan: [plan.md](../../plans/phase1/plan.md)
Scope: Step 6 (documentation, CI, phase close-out). **Phase 1 is complete.**

## Summary

Docs, ADRs 0004–0006, README quick-start, CI ("Phase 1 exit criteria" + extras coverage),
and the roadmap status block are done. Final state: `ruff` clean, `mypy --strict` clean
(38 files), `pytest` 128 passed / 0 skipped (PNG tests now run — Pillow present via the
`image` extra). Every CI command was dry-run locally before landing. **Not committed** —
manual-push workflow.

## Step 6.1 — Documentation

New in `vdbmat-utils/docs/`:

- `voxelization.md` — input contract (STL-only, watertightness, required `source_unit`),
  D3 semantics (cell-centre winding rule, closed-solid tie rule, jitter split as the code
  does it), domain fitting (snap epsilon, padding vs. verbatim explicit bounds, size
  guards), config schema, and a worked L-bracket example with its ASCII slice
  (4 mm³ ÷ 0.125 mm³ = 32 occupied cells).
- `image-stacks.md` — D4 contract (filename-order stacking, declared-levels rule, gap
  detection), config schema, PGM/PNG formats and the `image` extra, provenance/identity
  rules.
- `previews.md` — `material-counts` / `preview-slices` usage, the ASCII legend as the
  primary axis-orientation diagnostic, no-optional-dependency guarantee.

ADRs (per plan D7):

- `0004-stl-only-mesh-loading.md` — dependency-free ported STL reader over a mesh library;
  `mesh` extra stays empty; OBJ/PLY/glTF out of scope.
- `0005-winding-number-voxelization-port.md` — recovered semantics adopted wholesale,
  constants verbatim, code-wins-over-memo delta noted, explicit bounds as the one addition.
- `0006-image-stack-migration.md` — migration contract, PNG extension, fresh generator
  identity, and the Step 5 deletion of `vdbmat/tools/image_stack_generator`.

`README.md`: status advanced to Phase 1 complete; quick-start now shows the mesh workflow,
the image-stack workflow, previews, and the vdbmat hand-off through `convert`; extras text
corrected (minimal install covers STL + PGM + previews; `image` adds PNG).

## Step 6.2 — CI (`.github/workflows/ci.yml`, superproject)

- **Minimal job (no extras)** — plan's minimal-install matrix leg. Kept `uv sync` with no
  extras and added a "Minimal-install workflows" step: fixture generation in-code, then
  `convert-image-stack` (PGM) + `voxelize-mesh` + `validate` + `preview-slices` +
  `material-counts`, proving the base install runs both workflows and previews.
- **Integration job** — now syncs `--all-extras` and reruns the unit/contract suite so the
  two PNG tests execute in CI (they were silently skipped everywhere before), then runs the
  `integration`-marked tests.
- **"Phase 1 exit criteria" step** (mirroring Phase 0's): both fixtures → CLI conversion →
  `validate` → `vdbmat import-voxels` → `vdbmat convert` to optical Zarr, for the stack and
  the bracket. All commands verified locally end to end (both optical Zarrs produced).

## Step 6.3 — Roadmap close-out

`roadmap_vdbmat-utils.md` Phase 1 gained a **Status: complete (2026-07-07)** block in the
Phase 0 style: what shipped, the port provenance, the deletion decision, ADR/doc pointers,
CI coverage, and upstream `vdbmat` follow-ups — the two open Phase 0 items (`py.typed`,
`Matrix4` re-export), the 8 pre-existing ruff errors in
`examples/phase1/demo/blender_glass_demo.py`, and the pending submodule-pin bump for the
Step 5 deletion commit.

## Verification log

```text
$ uv run ruff check .              → All checks passed!
$ uv run mypy src tests            → Success: no issues found in 38 source files
$ uv run pytest -q                 → 128 passed (0 skipped; PNG tests active)
$ uv run --extra image pytest tests/unit/test_image_stack.py → 19 passed
$ (local dry-run of every CI step) → both workflows through vdbmat convert: ok
$ yaml.safe_load(ci.yml)           → parses
```

## Deviations from plan

- The plan's "matrix leg that installs without extras" was realized by keeping the existing
  minimal job extras-free and adding the workflow-exercise step to it, while the integration
  job took `--all-extras` — same coverage split as a matrix, without restructuring the jobs.
- `voxelize-mesh` was added to the exit-criteria/minimal steps' fixture generation via a
  small inline Python block (fixtures are in-code by design, so there is no STL to check in).

## Phase 1 exit criteria — final check (plan §1)

1. ✅ `voxelize-mesh` produces assets passing `validate` + `import-voxels` (report4, CI).
2. ✅ `convert-image-stack` likewise (report2, CI).
3. ✅ End-to-end through `vdbmat convert` for one fixture per workflow, `integration`-marked,
   in CI (reports 2/4, CI exit-criteria step).
4. ✅ Diagnostics: single-line exit-1 errors for non-watertight mesh, undeclared gray,
   missing slice, wrong dtype/format, palette mismatch; previews need no OpenVDB/matplotlib
   (reports 0–4).
5. ✅ Determinism, checksum-stability goldens, and axis-orientation goldens per workflow
   (reports 2/4).

## Next

Phase 1 is closed. Remaining manual step: commit (vdbmat deletion first, then the
superproject gitlink bump per ADR-0001). Next phase per roadmap: Phase 2 — image morphing
and volume composition.
