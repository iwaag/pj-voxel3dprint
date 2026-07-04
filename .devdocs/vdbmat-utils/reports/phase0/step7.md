# Phase 0 Execution Report — Step 7 (closure)

Date: 2026-07-05
Plan: [plan.md](../../plans/phase0/plan.md)
Scope: Step 7 — documentation, ADRs, exit-criteria automation, roadmap status. **Phase 0 is now
complete.**

## Work done

- **ADR 0003** (`vdbmat-utils/docs/adr/0003-contract-compatibility-range.md`): the supported
  vdbmat contract range is major version 1 of `vdbmat.volume`, held in the single constant
  `SUPPORTED_VOLUME_SCHEMA_MAJOR`, enforced at runtime by the builder and `validate` command,
  and backstopped byte-level by the golden-fixture digests. A schema-2.x submodule bump fails
  CI until the constant is raised deliberately.
- **Exit criteria automated in CI**: the integration job in
  `pj-voxel3dprint/.github/workflows/ci.yml` gained a "Phase 0 exit criteria" step running the
  full chain — `generate-fixture` → `inspect` → `validate` → `vdbmat import-voxels` — on every
  push/PR, so the exit criteria stay demonstrated rather than once-demonstrated.
- **README** status section updated to "Phase 0 complete", pointing at Phase 1 and the ADRs.
- **Roadmap** Phase 0 section marked complete with pointers to reports, ADRs, and the two
  upstream follow-ups.

## Final verification

```text
$ uv run ruff check .      → All checks passed!
$ uv run mypy src tests    → Success: no issues found in 20 source files
$ uv run pytest -q         → 45 passed
$ generate-fixture → inspect → validate → vdbmat import-voxels → EXIT-CRITERIA-OK
```

## Phase 0 exit criteria — final check

| Criterion | Status |
| --- | --- |
| Synthetic in-memory volume written deterministically | ✅ byte-equal double-write contract test; golden digests |
| Validated by `vdbmat import-voxels` | ✅ integration tests + CI exit-criteria step |
| Inspected by the CLI | ✅ `vdbmat-utils inspect` (human + `--json`) |
| Exercised in CI without optional dependencies | ✅ both CI jobs run on the minimal install (`uv sync`, no extras) |

## Carried forward

- Upstream `vdbmat` follow-ups: add a `py.typed` marker (removes the mypy override) and
  re-export `Matrix4` from `vdbmat.core`.
- Not committed; manual push as with previous steps. After push, verify the first GitHub
  Actions run of the updated workflow (the CI itself has never executed remotely yet).
- Next: Phase 1 planning (mesh voxelizer scope per `vdbmat/.local/memo_stltovoxel.md`, and
  migration of the image-stack reference generator).
