# Phase 1 Execution Report — Step 1

Date: 2026-07-06
Plan: [plan.md](../../plans/phase1/plan.md)
Scope: Step 1 (image-stack core port). Includes one small piece pulled forward from
Step 2.2 (`image/png.py`), see Deviations.

## Summary

Step 1 complete. The `vdbmat/tools/image_stack_generator/generate.py` logic is ported
into a new `vdbmat_utils.image` package rebuilt on the shared `core` conventions
(config digest, provenance, volume builder). Test suite grew from 59 to 76 tests, all
green (`ruff`, `mypy --strict` over 27 files, `pytest`). **Not committed** — same
manual-push workflow. The old tool in `vdbmat` is untouched (deletion is Step 5, gated
on Step 2's contract tests).

## What was built

### `src/vdbmat_utils/image/`

- `__init__.py` — defines `ImageStackError(VdbmatUtilsError)` (as the plan prescribes,
  keeping `core/errors.py` generator-agnostic) and re-exports the public API:
  `ImageStackConfig`, `convert_image_stack`, `ImageStackError`.
- `pgm.py` — `read_pgm` ported near-verbatim from the old tool (P5 binary + P2 ASCII,
  8-bit only, comment-tolerant header parsing); errors renamed
  `StackError` → `ImageStackError`. Zero dependencies.
- `stack.py` — the level-mapping/stacking logic, refactored per plan:
  - `ImageStackConfig(GeneratorConfig, kw_only=True)`: `voxel_size_xyz_m` (required),
    `levels` (required; tuple of `{gray, material_id, name, role}` mappings), optional
    `local_to_world` (4×4, validated by the builder/canonical types), and
    `format: "pgm" | "png" = "pgm"`. Inherits `seed` (unused, reserved, digested).
  - `convert_image_stack(slices_dir, config) -> MaterialLabelVolume` — in-memory API;
    builds through `build_material_label_volume` + `build_provenance` instead of the
    tool's direct `MaterialLabelVolume` construction.
  - Provenance per D6: `generator="vdbmat-utils.image.stack"`, version `0.1.0`,
    `sources` = per-slice `sha256:` digests in stack order, `configuration_digest`
    from the config's canonical JSON. (The combined asset `identity` is written at
    CLI time — Step 2.)
- `png.py` — 8-bit grayscale PNG reader with lazy Pillow import; missing Pillow raises
  `ImageStackError("PNG input requires the 'image' extra: …")`; non-grayscale and
  >8-bit modes rejected explicitly.

### Contract kept from the old tool (D4)

Ascending-filename z-order with rows→+Y / columns→+X; every present gray value must be
declared (error now also names the **first offending file, row, column** — an
extension over the old value-only message); one shape and bit depth across slices;
duplicate gray levels and duplicate material ids rejected; empty directory rejected.

New over the old tool: optional `local_to_world`, `format` selection, and a
**missing-sequence-index check** — when every filename ends in a number
(`slice_0003.pgm` … `slice_0005.pgm`), a gap raises an error naming the missing
index(es); non-numeric names (e.g. `bottom.pgm`/`top.pgm`) still stack fine in
filename order.

### Tests — `tests/unit/test_image_stack.py` (17 tests)

P5/P2 parsing agreement; non-8-bit and truncated-header rejection; **z/y/x placement
against a literal expected array** for an asymmetric 2×3×4 stack; provenance sources
and config-digest stability; `local_to_world` passthrough; undeclared gray naming
value + file/pixel; shape mismatch; empty directory; missing sequence index (and the
non-numeric-name non-trigger case); duplicate material_id; duplicate gray; level field
validation (empty, wrong type, unknown field); PNG-without-extra message; unsupported
format.

## Verification log

```text
$ uv run ruff check .    → All checks passed!
$ uv run mypy src tests  → Success: no issues found in 27 source files
$ uv run pytest -q       → 76 passed
```

## Deviations from plan

- `image/png.py` (planned for Step 2.2) was written now: `stack.py` routes
  `format="png"` to it, and mypy --strict cannot typecheck a route to a module that
  does not exist. Step 2 only needs to add `pillow>=10` to the `image` extra and the
  PNG test coverage.
- `ImageStackError` is defined in `image/__init__.py` as planned; the submodule
  re-import that requires places the package's public-API imports after the class
  definition (one `# noqa: E402`).
- `pyproject.toml` gained a mypy override (`PIL.*` → `ignore_missing_imports`) so the
  lazy Pillow import typechecks in environments without the extra installed.

## Next

Step 2 — image-stack CLI (`convert-image-stack`), `image` extra (`pillow>=10`) + PNG
tests, shared deterministic stack fixture, contract tests (determinism, payload-digest
golden, material-count conservation), and the `integration`-marked end-to-end run
through `vdbmat import-voxels` → `vdbmat convert`.
