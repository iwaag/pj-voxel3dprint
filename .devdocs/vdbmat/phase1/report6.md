# Phase 1 — Step 6 Report: Implement Pipeline Orchestration and Run Bundles

- **Date:** 2026-07-02
- **Step:** 6 of 12 (`.local/phase1/plan.md`)
- **Status:** Complete. `ruff check .`, `mypy --strict src/vbdmat`, and the full test
  suite pass (347 passed, +16 new; 3 optional integration tests skipped for absent
  renderers). `uv lock --check` passes with no dependency change.

## 1. Goal

Turn the Step 5 `PipelineConfig` into an executed, inspectable, failure-safe run bundle:
implement the ADR-007 typed deterministic stage sequence, publish a `run/` directory
atomically, chain provenance from input through mapping, and make reproducible reruns
testable by digest comparison (plan Step 6, ADR-007 D1–D9).

## 2. Deliverables produced

### `vbdmat.pipeline.runner` (new)

[src/vbdmat/pipeline/runner.py](../../src/vbdmat/pipeline/runner.py) —
`run_pipeline(config, *, base_dir, created_utc=None, export_runner=None) -> RunResult`.
It executes the fixed ADR-007 D1 stages

```text
load/voxelize -> validate material -> persist material
              -> map optics -> validate optical -> persist optical
              -> summarize -> optional export
```

reusing the existing Phase 0/Step 2–5 APIs unchanged: `read_material_label_manifest` /
`inspect_material_label_manifest` (direct voxel), `read_stl` + `voxelize_mesh` (mesh),
`map_material_volume_to_optical` (optics), and `vbdmat.io.zarr.write_volume` /
`read_volume` (persistence). `StageStatus` (`ok`/`skipped`/`failed`), `StageRecord`, and
`RunResult` are the typed outputs.

### `vbdmat.pipeline.artifacts` (new)

[src/vbdmat/pipeline/artifacts.py](../../src/vbdmat/pipeline/artifacts.py) — the stable
non-Zarr artifact schemas and deterministic checksum helpers:

- `RUN_SCHEMA` = `vbdmat.run/1.0.0`, `SUMMARY_SCHEMA` = `vbdmat.summary/1.0.0`,
  `VALIDATION_SCHEMA` = `vbdmat.validation/1.0.0`;
- `sha256_file`, `zarr_store_sha256` (a deterministic digest over a store's sorted
  POSIX-relative files + lengths, since a Zarr store is a directory, ADR-007 D5),
  `path_size_bytes`;
- `build_summary` (implementation-independent geometry/material-count/optical-range/
  digest document) and `build_validation`.

`PipelineRunError(stage, message)` was added to
[errors.py](../../src/vbdmat/pipeline/errors.py) so a failure is attributable to a named
stage; package exports updated in [__init__.py](../../src/vbdmat/pipeline/__init__.py).

## 3. Key design decisions

- **Content-addressed `run_id` (ADR-007 D3).** `run-` + first 16 hex of
  `sha256(config_digest \n input_payload_sha256 \n mapping_digest)`. No timestamp; two
  equivalent runs share the id.
- **`config.json` is the canonical configuration verbatim**, so its file checksum *is*
  the `config_digest` by construction (verified by a test). `summary.json` /
  `validation.json` are written with the project's sorted/tight canonicalization for
  byte-stable reruns; `run.json` is pretty-printed and is the only artifact carrying the
  isolated `created_utc`.
- **Atomic, failure-safe publication (ADR-007 D7/D8).** The whole bundle is built in a
  sibling `.<name>.tmp-<run_id>` directory, validation stages read the *persisted* Zarr
  back, `run.json` is written last, and publication is a single `os.replace` rename. On
  overwrite the previous run is moved aside to `.<name>.bak-<run_id>` and only removed
  after the new run renames in (restored on failure). Any stage exception cleans the temp
  directory and raises `PipelineRunError(stage, …)`; no partial `run/` ever appears.
- **Provenance chaining (ADR-007 D6).** Both canonical volumes are re-stamped with
  `Provenance.configuration_digest = config_digest`; the material adds
  `input-payload:<sha>` and the optical adds `mapping-digest:<sha>` to `sources` (the
  mapper's own `mapping-config:…@version` source is retained). `run.json.provenance`
  additionally links input kind/path/payload sha, mesh voxelization settings, mapping
  name+digest, and config digest.
- **Renderer independence (ADR-007 D1).** The core stage sequence completes with no
  renderer installed. Optional export runs **after** the canonical bundle is published
  and consumes the persisted `optical.zarr`; an `ExportRunner` backend is injected (wired
  in Step 8). A backend exception is caught, recorded as `export` = `failed` with the
  message, and cannot corrupt the already-published canonical artifacts. With no backend
  a requested export is `skipped` (deferred to Step 8), never silently claimed done.

## 4. Tests added

[tests/pipeline/test_pipeline_runner.py](../../tests/pipeline/test_pipeline_runner.py)
(16 tests, all passing), driven by the deterministic `write_phase1_fixtures` inputs:

- both input paths complete the identical stage sequence (`load`/`voxelize` prefix);
- bundle layout matches ADR-007 D4; `config.json` checksum equals `config_digest`;
- persisted material/optical read back and match the summary counts/ranges;
- provenance links input checksum, mesh voxelization, mapping digest, and config;
- `run_id` is deterministic and timestamp-free;
- overwrite is required when output exists; a corrupt payload fails without publishing a
  bundle and leaves no temp directory; overwrite leaves no backup residue;
- two identical runs (different `created_utc`) produce equal `assets[*].sha256` and equal
  `run.json` apart from `created_utc`;
- export without a backend is `skipped`; an injected failing backend yields `export` =
  `failed` with intact readable canonical assets; a successful backend records adapter
  versions and writes `exports/mitsuba/`;
- validation stages can be skipped and are reflected in `validation.json`.

## 5. Verification against the Step 6 checklist (ADR-007 D-compliance)

| Plan verification item | Status |
| --- | --- |
| Both input paths complete the same typed stage sequence | Met — `test_direct_voxel_…`, `test_mesh_…`; only the first stage name differs (`load` vs `voxelize`). |
| Persisted material/optical assets exactly equal the stage outputs | Met — read-back counts/ranges + re-stamped-volume-is-what-is-persisted; `test_persisted_…`. |
| Provenance links input checksum, voxelization, mapping digest, config | Met — asset `configuration_digest` + `sources`, and `run.json.provenance`; `test_provenance_…`, `test_mesh_provenance_…`. |
| Interrupted/failed run publishes no valid-looking bundle | Met — build-in-temp + `run.json`-last + single rename; `test_failed_run_publishes_no_valid_looking_bundle`. |
| Overwrite never destroys a previous valid run before replacement validates | Met — temp build+validate precedes any touch of the live output; backup-then-rename on publish; `test_overwrite_preserves_…`. |
| Two identical runs have equal scientific artifacts and checksums; only `created_utc` differs | Met — `test_two_identical_runs_have_equal_scientific_artifacts`. |
| Export failure does not corrupt canonical artifacts and is attributed to `export` | Met — post-publish, isolated try/except; `test_export_failure_is_attributed_…`. |

## 6. Files added / changed

- added: `src/vbdmat/pipeline/{runner,artifacts}.py`,
  `tests/pipeline/test_pipeline_runner.py`;
- changed: `src/vbdmat/pipeline/{__init__,errors}.py` (exports + `PipelineRunError`).

No changes to `core`, schema 1.0.0, Zarr persistence, optics, the Step 2/3 readers, the
Step 4 fixtures, the Step 5 configuration, or `uv.lock`. The pipeline package still
imports no renderer/exporter module; export is reached only through the injected
`ExportRunner`.

## 7. Stop conditions checked

None triggered. The bundle composes ADR-004 Zarr assets rather than reinterpreting
schema 1.0.0; deterministic reruns cleanly separate the scientific payload from the
isolated `created_utc`; and an optional-renderer failure does not prevent the canonical
pipeline from completing.

## 8. Recommendation

Proceed to **Step 7** (the Phase 1 `vbdmat` CLI). `run_pipeline` gives the CLI `run`
command a single package API returning `RunResult` (run id, digests, stage statuses,
manifest, summary), and the `ExportRunner` seam is ready for the Step 8 adapters.
