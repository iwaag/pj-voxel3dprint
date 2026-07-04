# Phase 0 Execution Report — Steps 5–6

Date: 2026-07-05
Plan: [plan.md](../../plans/phase0/plan.md)
Scope: Step 5 (golden fixtures and contract tests), Step 6 (minimal CLI). Executed together
because the CLI's `generate-fixture` command directly reuses the Step 5 fixture presets.

## Summary

Both steps complete. The test suite grew from 20 to 45 tests, all green (`ruff`, `mypy --strict`
over 20 files, `pytest`). The Phase 0 exit-criteria chain now runs end to end:
`vdbmat-utils generate-fixture` → `vdbmat-utils inspect` → `vdbmat-utils validate` →
`vdbmat import-voxels` (verified manually and in the integration test suite).
**Not committed** — same manual-push workflow as previous steps.

## Step 5 — Golden fixtures and contract tests

- `src/vdbmat_utils/fixtures.py` — three deterministic presets, each exercising a roadmap risk:
  - `anisotropic`: anisotropic voxel size (0.1/0.2/0.4 mm), identity transform;
  - `transformed`: non-zero origin plus a 90° rotation about the world z axis;
  - `multimaterial`: four materials including `quartz_vein`, a name outside vdbmat's built-in
    optical table, pre-staging the Phase 3 optical-mapping requirement.
  All presets use an axis-asymmetric label pattern (`(7z + 3y + x) mod n`) so no z/y/x
  transposition error can cancel out. Placed in `src/` (not `tests/`) so the CLI and later
  phases can reuse them.
- `tests/contract/test_golden_fixtures.py`:
  - **Golden digests**: hardcoded SHA-256 for each preset's payload *and* manifest. Any byte
    change in the output contract fails the suite and must be reviewed deliberately.
  - **Round-trip**: every preset re-read via `read_material_label_manifest` /
    `inspect_material_label_manifest` with array and geometry equality.
  - **Invalid metadata** (6 negative cases): payload checksum mismatch, wrong dtype, wrong axis
    order (`x,y,z`), undeclared material reference, non-rigid (scaled) transform, missing voxel
    size — each rejected by the pinned vdbmat reader with its public error types.
- `tests/integration/test_import_voxels.py` — every preset imports cleanly through the
  `vdbmat import-voxels` CLI (subprocess); a corrupted payload is rejected end to end.

## Step 6 — Minimal CLI

`vdbmat-utils` entry point (`src/vdbmat_utils/cli/main.py`) with three subcommands:

- `inspect MANIFEST [--json]` — metadata-only view via `inspect_material_label_manifest`
  (format version, shape, voxel size, material IDs, payload path/sha256, source identity).
- `validate MANIFEST` — compat-range check (`require_compatible_volume_schema`) plus a full
  `read_material_label_manifest` round-trip including payload checksum verification.
- `generate-fixture PRESET -o DIR [--seed N]` — writes a preset asset deterministically;
  demonstrates the exit criteria without any optional dependencies.

Exit-code convention implemented as planned: 0 success, 1 validation/generation failure
(expected error types printed as `error: …` on stderr), 2 usage error (argparse). Covered by
`tests/unit/test_cli.py` (7 tests), including the corrupt-payload → exit 1 and unknown-preset →
exit 2 paths.

## Verification log

```text
$ uv run ruff check .          → All checks passed!
$ uv run mypy src tests        → Success: no issues found in 20 source files
$ uv run pytest -q             → 45 passed
$ uv run vdbmat-utils generate-fixture multimaterial -o out/
$ uv run vdbmat-utils inspect out/multimaterial.voxels.json    → metadata printed
$ uv run vdbmat-utils validate out/multimaterial.voxels.json   → OK
$ uv run vdbmat import-voxels out/multimaterial.voxels.json out/out.zarr
import-voxels: ok
```

## Deviations from plan

- The plan sketched fixture generation under `tests/fixtures/`; the presets live in
  `src/vdbmat_utils/fixtures.py` instead so `generate-fixture` and later phases share one
  implementation. Golden state is pinned as hardcoded digests rather than committed binary
  files — equivalent regression power, no binaries in git.
- The earlier `--version`-only CLI stub test was replaced: with required subcommands, a bare
  invocation is now a usage error (exit 2), matching the documented convention.
- README updated with the real CLI workflow (was a Step 6 placeholder).

## Remaining for Phase 0

Step 7 (documentation wrap-up): ADR for the contract-compatibility range, exit-criteria run
recorded in CI, roadmap Phase 0 status note. The exit criteria themselves are already
demonstrably met; Step 7 is documentation and closure.
