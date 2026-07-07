# Phase 2 Execution Report — Steps 2 and 3

Date: 2026-07-07
Plan: [plan.md](../../plans/phase2/plan.md)
Scope: Step 2 (morph core) and Step 3 (morph CLI + `ops/resample` + pipeline
engine and CLI). Follows [report0-1.md](report0-1.md).

## Summary

Steps 2 and 3 complete. Two new subpackages — `vdbmat_utils.morph` (per-label
SDF interpolation of sparse labeled key slices, plan D4) and
`vdbmat_utils.pipeline` (SSA-style config-driven op pipelines, plan D6) — plus
`ops/resample.py` (nearest-neighbor, plan D5) and two new CLI subcommands,
`morph-stack` and `apply-pipeline` (with `--dry-run`). The shared asset-identity
recipe was factored out of `image/stack.py` into
`core/provenance.py::provenance_identity` as the plan required. No new
dependencies. Test suite grew from 208 (191 + 17 added during Step 2 as it
landed) to **227 tests**, all green (`ruff`, `mypy --strict` over 69 files,
`pytest`). Committed as `p2s2` (e6f52ec) and `p2s3` (87427dc).

## What was built

### Step 2 — `src/vdbmat_utils/morph/` (plan D4)

- `keyslices.py::load_key_slices` — reuses the Phase 1 slice readers
  (`_read_slice`) and `_parse_levels` from `image/stack.py` (allowed by the
  import-direction rule `morph → image`). Filename parsing is strict: exactly
  one numeric group per stem (that group *is* the output z index); duplicate
  indices and lexicographic order disagreeing with numeric order are
  `MorphError`s. Undeclared gray values name the file, pixel position, and
  value, matching `convert-image-stack` behavior. Slice-file SHA-256 digests
  are collected in z order for provenance `sources`.
- `interpolate.py::MorphStackConfig(GeneratorConfig)` — `voxel_size_xyz_m`,
  `levels`, `background=0`, `z_count=None` (defaults to last key index + 1),
  `edge_policy="error"|"clamp"`, optional `local_to_world`,
  `format="pgm"|"png"`, size guards `max_axis_cells=256` /
  `max_total_cells=8_000_000`. `seed` stays inherited and reserved.
- `interpolate.py::morph_stack` — per plan D4: 2-D signed EDT per material id
  per key slice (via `fields.signed_distance`, in metres, spacing ordered
  y, x from `voxel_size_xyz_m`), linear interpolation of distances in z,
  argmin label resolution with strict-`<` updates in ascending id order (ties
  → lowest id), background where no label has distance < 0. Key slices are
  emitted verbatim from the mapped input pixels. Edge policy `"error"`
  rejects a first key slice ≠ 0 and `z_count` past the last key;
  `"clamp"` repeats the nearest key slice. Generator identity
  `vdbmat-utils.morph.stack` v0.1.0; asset identity = shared
  `provenance_identity` recipe (slice digests + config digest).
- Memory follows the plan §7 rule: the label loop keeps only two float64
  distance slices per label plus the running (min-distance, label) buffers;
  no per-label field stack is materialized.
- `core/provenance.py::provenance_identity` — the D4 "factored, not copied"
  identity recipe; `image/stack.py::stack_identity` now delegates to it.

### Step 3 — resample, pipeline, CLI

- `ops/resample.py::resample(volume, factor_zyx=... | voxel_size_xyz_m=...)`
  (exactly one) — nearest-neighbor only: output cell centers map to source
  indices by a fixed `floor((i + 0.5)/factor)` formula with integer indexing,
  so interpolation is impossible by construction; integer factors are exact
  repetition/decimation; manifest voxel size updates; `local_to_world` is
  untouched (local origin unchanged). Registered in the label-safety AST
  guard's scope automatically (it lives in `ops/`).
- `pipeline/registry.py` — `OpSpec` registry mapping op names to volume-ref
  keys, parameter-name sets, and JSON→kwargs adapters for all eight ops:
  `crop`, `pad`, `resample`, `orient`, `place`, `apply-mask`, `compose`,
  `remap-materials`. Adapters validate parameter shapes (int/float triplets,
  4×4 matrices, string-keyed remap tables) with precise messages.
- `pipeline/engine.py` — `PipelineConfig(GeneratorConfig)` with `inputs`
  (`{id, manifest_path}`), `steps` (flat SSA list: volume refs via `"from"`
  or `"base"`/`"overlay"`/`"mask"`, result bound via `"as"`), and `output`
  (`{"ref": id}`). `validate_pipeline` runs before any manifest read or
  array work and reports unknown ops, unknown parameters, unbound/rebound
  ids, malformed inputs/output, and unused inputs — each with the step index.
  `run_pipeline` loads inputs through the public
  `vdbmat.io.read_material_label_manifest` (per the Step 0.0 finding, no
  wrapper needed), resolves relative paths against the config file's
  directory, wraps op failures as `PipelineError` with `step N (op):`
  context, and stamps the result with `vdbmat-utils.pipeline` v0.1.0
  provenance (`sources` = input-manifest SHA-256 digests in input order).
- `cli/main.py` — `morph-stack SLICES_DIR --config C --out D --name N`
  (`--voxel-size`, `--z-count` overrides applied via `dataclasses.replace`
  before digesting, matching Phase 1 D5) and `apply-pipeline --config P
  --out D --name N [--dry-run]`; both follow the fixed success convention
  (manifest path + material counts) and single-line `error:` + exit 1 on
  failure. `--dry-run` prints the resolved step plan and touches no output.

## Semantics discovered while testing (worth knowing for docs, Step 5)

Two consequences of the plan's fixed rules surfaced as initially-wrong test
expectations; both are correct per D4 and should be documented in
`docs/morphing.md`:

1. **Absent labels vanish immediately, not gradually.** D4 fixes IEEE
   arithmetic on the `+inf` "absent" distance, so `(1-t)·d + t·(+inf)` is
   `+inf` for every interior t — a label present on only one key slice
   appears *only* on that key slice. (The related `-inf`/`+inf` → NaN corner,
   a label filling one key slice and absent from the other, is resolved to
   `+inf` with a code comment.)
2. **Cell-centered SDFs make "exactly touching" morphs empty at the
   midpoint.** A shape shifted by an even offset interpolates to distance
   exactly 0 at cell centers, and 0 is not inside (`< 0`), so the symmetric
   swap fixture yields all-background at t = 0.5. Exact *negative* ties are
   provably impossible in the separable 1-D constructions we tried, so the
   lowest-id tie rule is pinned by a monkeypatched-distance unit test instead
   of a geometric fixture.

## Deviations from the plan

- **`output: {input_ref}`** (plan D6) was interpreted as `output:
  {"ref": "<id>"}` — the plan's key name was ambiguous; `"ref"` is what the
  config schema, tests, and `--dry-run` output use.
- The tie-rule test uses monkeypatched distance fields (see above) rather
  than a purely geometric golden; the geometric swap case documents the
  companion "no label inside → background" rule instead.
- `resample` keeps `local_to_world` untouched rather than recomposing: the
  local origin (corner) is preserved by the cell-center formula, so world
  positions of the grid domain are unchanged. This matches D5's "voxel size
  in the manifest updates accordingly" with no transform note needed.

## Test coverage added (36 tests)

- `test_morph.py` (19): key slices byte-faithful; offset-square midpoint as
  an expected-array literal; merge golden (monotone growth, disconnected →
  connected); disappearing-label monotonicity (immediate vanish per D4);
  symmetric-swap → background; lowest-id tie (monkeypatched); edge-policy
  error and clamp; z_count too small; undeclared gray naming file/value;
  gap-is-fine contrasted against `convert-image-stack` erroring; duplicate z;
  multiple numeric groups; non-monotonic order; both size guards; background
  not declared; determinism/provenance double run; CLI success with
  overrides and CLI error → exit 1.
- `test_ops_resample.py` (6): integer up/downsample exactness as array
  literals, voxel-size metadata update, factor-form ≡ voxel-size-form,
  output labels ⊆ input labels (no mixing), exactly-one-parameter and
  positivity errors.
- `test_pipeline.py` (11): validation-time failures each naming the step
  index (unknown op, unknown param, unbound ref, rebound id, unused input);
  missing input file; runtime op error with step context; 3-step config
  (crop → remap-materials → compose) matching the direct Python API
  byte-for-byte plus provenance determinism; CLI dry-run (plan printed, no
  output dir created), CLI run producing a `validate`-clean asset, CLI
  invalid config → exit 1.

The Step 0 guards picked the new code up automatically: the import-isolation
allowlist rows for `morph`/`pipeline` were pre-declared, and the label-safety
AST guard now walks `morph/` (and `ops/resample.py`) — both pass unchanged.

## Verification log

```text
$ uv run ruff check .      → All checks passed!
$ uv run mypy src tests    → Success: no issues found in 69 source files
$ uv run pytest -q         → 227 passed in 1.81s
```

Commits: `e6f52ec` (p2s2 — morph core + tests), `87427dc` (p2s3 — resample,
pipeline, CLI + tests).

## Notes for the next steps

- Step 4 (contract/integration) has everything it needs: both CLI workflows
  are argv-driven through `main()`, provenance is deterministic
  (`created_utc` unset), and `provenance_identity` supplies the manifest
  `source.identity` for both generators.
- Step 5 docs must cover the two semantics notes above (immediate vanish;
  midpoint-zero exclusion) plus the `output: {"ref": ...}` schema choice, and
  ADR-0009 should record the deferrals (generator steps in pipelines, smooth
  label resampling).
