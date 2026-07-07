# Phase 2 Execution Report — Steps 4 and 5

Date: 2026-07-07
Plan: [plan.md](../../plans/phase2/plan.md)
Scope: Step 4 (contract and integration tests) and Step 5 (documentation, CI,
phase close-out). Follows [report2-3.md](report2-3.md). **Phase 2 is complete.**

## Summary

Steps 4 and 5 complete. Two new in-code fixture generators, a Phase 2
contract-test suite (byte-equal double runs, payload/manifest digest goldens,
three-axis ASCII orientation goldens, conservation identities), two
end-to-end integration tests through `vdbmat import-voxels` → `vdbmat
convert`, three user docs, ADRs 0007–0009, README quick-start additions, a
"Phase 2 exit criteria" CI step on the integration leg plus a Phase 2
workflow step on the minimal-install leg, and the roadmap Phase 2 status
block. Test suite: 227 → **237 tests**, all green (`ruff`, `mypy --strict`
over 71 files, `pytest` including `integration`). Commits: `a244e1d` (p2s4),
`a815b78` (p2s5, vdbmat-utils submodule); CI/roadmap/report changes live in
the parent repo.

## Step 4 — what was built

### Fixtures (`src/vdbmat_utils/fixtures.py`)

- `write_morph_fixture(dir) -> (slices_dir, MorphStackConfig)` — sparse key
  slices at z = 0, 3, 7 (output depth 8), 10×12 pixels, three materials
  (background + 2), asymmetric shapes, and one merge event (two
  transparent-resin squares → one bar between z=3 and z=7) plus a
  white-resin block that translates across the gaps. Gray levels reuse the
  Phase 1 stack levels so material names stay inside vdbmat's builtin
  optical mapping (`vdbmat convert` runnable).
- `write_pipeline_fixture(dir) -> config_path` — writes two same-geometry
  assets (`base.voxels.json`, `overlay.voxels.json`) and a `pipeline.json`
  that remaps the overlay's material onto a fresh id renamed `white-resin`
  and composes with `union`.

### Contract tests (`tests/contract/test_phase2_contract.py`, 8 tests)

- Byte-equal double runs through the CLI for both `morph-stack` and
  `apply-pipeline`.
- Hardcoded payload + manifest SHA-256 goldens for both workflows (a change
  means the output contract moved and must be reviewed deliberately, same
  policy as the Phase 0/1 goldens).
- ASCII orientation goldens on all three axes (z=5, y=3, x=3) of the morphed
  fixture — the y-axis slice visibly pins the merge event completing between
  z=3 and z=5.
- `validate` passes on both outputs.
- Conservation identities where they genuinely hold: `remap_materials`
  preserves the total voxel count and moves per-id counts exactly as mapped
  (with pruning); `compose` foreground counts follow the union/intersect/
  subtract set identities; `apply_mask` keep/clear partition the base
  foreground exactly, and keep-mask ≡ intersect. **Not claimed for
  `resample`** (stated in `docs/volume-ops.md` instead).

### Integration tests (`tests/integration/test_phase2_workflows.py`, 2 tests)

Morphed fixture and composed fixture each run CLI → `vdbmat import-voxels`
→ `vdbmat convert` via subprocess, mirroring the Phase 1 integration style.

## Step 5 — what was built

### Documentation

- `docs/morphing.md` — the D4 spec as user documentation: input contract,
  config table, algorithm, an ASCII merge figure, and the deterministic
  rules for every edge: tie → lowest id, absence → `+inf` (with the
  documented consequence that one-sided labels vanish immediately on
  interior slices), the `-inf`/`+inf` NaN corner, midpoint-zero exclusion
  for exactly-symmetric morphs, edge policy, label conflicts, size guards,
  cost model.
- `docs/volume-ops.md` — D5 op table, exact-geometry rule for binary ops,
  boolean semantics, NN-only resampling with the aliasing caveat, explicit
  conservation claims (and the resample non-claim), deferred work.
- `docs/pipelines.md` — D6 schema with a full worked example (the fixture
  pipeline), the resolved-path rule, fail-fast validation guarantees,
  `--dry-run`, provenance/identity recipe, deferrals.
- ADR 0007 (label-safety architecture), ADR 0008 (per-label SDF morphing
  semantics), ADR 0009 (volume-op and pipeline contracts, including the
  recorded deferrals: generator steps in pipelines, conditionals/caching/
  parallelism, smooth SDF label rescaling, non-90° rigid resampling).
- README: status paragraph now says Phases 0–2 complete; new quick-start
  sections for the morph and pipeline workflows.

### CI (`.github/workflows/ci.yml`, parent repo)

- Integration leg: new **"Phase 2 exit criteria"** step — writes both
  fixtures, runs `morph-stack` and `apply-pipeline`, `validate` on both,
  then `vdbmat import-voxels` → `vdbmat convert` on both. The full command
  sequence was executed locally and passes (both optical zarr stores
  produced).
- Minimal-install leg: new **"Minimal-install Phase 2 workflows"** step
  running both workflows (including `--dry-run`) and `validate` — asserting
  the plan's D2 claim that Phase 2 added no runtime dependencies.

### Roadmap

`roadmap_vdbmat-utils.md` Phase 2 now carries a **complete (2026-07-07)**
status block in the Phase 0/1 style. No new upstream `vdbmat` follow-ups
were raised in Phase 2 (the pipeline reader is the public
`vdbmat.io.read_material_label_manifest`); the open Phase 0/1 follow-ups are
restated.

## Deviations from the plan

- **Pipeline fixture does not reuse a Phase 1 volume preset.** The plan
  suggested reusing Phase 1 fixtures as pipeline inputs; the volume presets
  (`anisotropic` etc.) use palette names (`void`, `resin_clear`) outside
  vdbmat's builtin optical mapping, so `vdbmat convert` rejects their
  composition (verified: exit 5, "material names disagree with the
  mapping"). The fixture instead builds same-pattern assets in-code with
  builtin-mapping names (`air`/`transparent-resin`/`white-resin`), keeping
  the Step 4.3/CI convert leg runnable. Noted in the fixture docstring.
- The exit-criteria CI step could not be exercised on GitHub Actions from
  here; the exact command sequence was run locally instead and passed
  end-to-end.

## Verification log

```text
$ uv run ruff check .      → All checks passed!
$ uv run mypy src tests    → Success: no issues found in 71 source files
$ uv run pytest -q         → 237 passed in 2.55s   (integration included)
$ <Phase 2 exit criteria command sequence> → all OK, both optical zarr written
```

## Phase 2 exit-criteria checklist (plan §1)

1. Morph workflow — ✅ CLI produces a contract-valid asset from sparse keys
   (z = 0, 3, 7), passes `validate` and `vdbmat import-voxels`.
2. Pipeline workflow — ✅ config-only remap + compose over two assets.
3. Label safety structural — ✅ `ScalarField` split, quantize-only gate, AST
   guard, NN-only resample (Steps 0–1, held through Steps 2–5).
4. Documented semantics — ✅ `docs/morphing.md`, `docs/volume-ops.md`
   (+ `docs/pipelines.md`), all edge behaviors deterministic and tested.
5. End-to-end — ✅ integration tests + CI exit-criteria step, minimal-install
   leg covers both workflows with no extras.
6. Determinism/goldens/orientation — ✅ double runs, digest goldens, and
   three-axis ASCII goldens for both workflows.
