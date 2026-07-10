# Phase 1 — Step 5 Report: Implement Versioned Pipeline Configuration

- **Date:** 2026-07-01
- **Step:** 5 of 12 (`.local/phase1/plan.md`)
- **Status:** Complete. `ruff check`, `mypy --strict src/vbdmat`, and the full test
  suite pass (331 passed, +44 new; 3 optional integration tests skipped for absent
  renderers). `uv lock --check` passes with no dependency change.

## 1. Goal

Implement immutable, versioned Phase 1 pipeline configuration types with canonical JSON
serialization and SHA-256 digests, so a run can be declared once, portably, and
inspected/hashed/round-tripped without any I/O or output side effects (plan Step 5,
ADR-007 D2, ADR-008 D1). The configuration is the input to Step 6 orchestration and the
`vbdmat run CONFIG` command.

## 2. Deliverables produced

### `vbdmat.pipeline` package (new)

[src/vbdmat/pipeline/config.py](../../src/vbdmat/pipeline/config.py) with
[errors.py](../../src/vbdmat/pipeline/errors.py) and package exports in
[__init__.py](../../src/vbdmat/pipeline/__init__.py):

- `PipelineConfig` — frozen dataclass carrying every declared setting:
  `input_kind` (`direct-voxel` | `mesh`), `input_path`, `output_path`, `mapping_name`,
  optional `voxelization`, `validate_material`/`validate_optical` stage flags,
  `exports`, `overwrite`, `random_seed`, and optional `renderer`.
- `MeshVoxelizationSettings` — explicit `source_unit`, `voxel_size_xyz_m`,
  `material_id`, `material_name`, rigid `placement`, `padding_cells`; validated at
  construction (units against `SUPPORTED_MESH_UNITS`, material ID range, finite/positive
  voxel size, rigid transform via `normalize_rigid_transform`).
- `ExportSettings` / `ExportTarget` (`mitsuba` | `openvdb`) and `RendererConfig`
  (opaque external references), both kept outside the scientific digest.
- `PIPELINE_CONFIG_SCHEMA` = `vbdmat.pipeline-config/1.0.0`; `DEFAULT_MAPPING_NAME` =
  `phase0-provisional-materials-v1` (ADR-008 D1); a builtin mapping registry resolving a
  name to the concrete `OpticalMappingConfig` and its ADR-007 `mapping_digest`.
- Two canonicalizations, both sorted-key/tight-separator JSON matching
  `OpticalMappingConfig.canonical_json()`:
  - `canonical_json()` / `digest` — the whole config (ADR-007 D2 `config_digest`);
  - `scientific_canonical_json()` / `scientific_digest` — only the settings that
    determine `material.zarr`/`optical.zarr` (input kind + voxelization + mapping +
    validation flags + seed), **excluding** `output`, `overwrite`, `exports`, `renderer`
    and the input *path*.
- `to_json_dict` / `from_json_dict` / `from_json` round-trip; `resolve_mapping`,
  `resolve_input_path(base_dir)`, `resolve_output_path(base_dir)`.

Supporting change: `SUPPORTED_MESH_UNITS` is now exported from `vbdmat.voxelize` so the
config validates units at build time using the voxelizer's own authoritative set (no
drift).

### Example run configurations (new)

[examples/phase1/generate_configs.py](../../examples/phase1/generate_configs.py)
regenerates two committed, human-reviewable configs byte-identically:

- [configs/window_coupon.run.json](../../examples/phase1/configs/window_coupon.run.json)
  (direct-voxel; digest `sha256:a77eeb2e…5881`);
- [configs/stepped_wedge.run.json](../../examples/phase1/configs/stepped_wedge.run.json)
  (mesh, `--unit mm --voxel-size 0.001 --material-id 1`; digest `sha256:fada7a2b…95a6`).

Paths in these files are portable and relative to the config's own directory
(`../inputs/…`, `runs/…`); `vbdmat run` will resolve them against the config directory.

## 3. Key design decisions

- **No implicit behaviour.** Mesh input *requires* explicit voxelization settings
  (missing unit/material/voxel-size fails, never a default); direct-voxel input *forbids*
  them (units/palette come from the manifest). `overwrite` defaults to the safe explicit
  `false`; `random_seed` is always recorded (default `0`); paths are stored verbatim and
  only ever resolved against an **explicit** `base_dir`, so there is no current-directory
  assumption in the recorded config.
- **Renderer independence is structural.** `scientific_digest` omits `renderer`,
  `exports`, `output`, and `overwrite`, giving a testable guarantee that renderer/export
  configuration cannot alter canonical material/optical identity. The whole-config
  `digest` still changes (it is the run identity), which is correct.
- **Path-independent science.** `scientific_digest` also omits the input path, matching
  ADR-007 D3 (canonical results depend on input payload content, not file location).
- **Strict deserialization.** `from_json_dict` rejects an incompatible major schema
  version, accepts compatible minors, and rejects unknown top-level or nested keys, so
  unrecognized required semantics fail loudly. A recorded `mapping.digest` that disagrees
  with the named mapping is rejected (tamper-evidence).

## 4. Tests added

[tests/pipeline/test_pipeline_config.py](../../tests/pipeline/test_pipeline_config.py)
(44 tests, all passing) — filename is unique to avoid the pytest basename collision with
`tests/optics/test_config.py`:

- construction defaults, immutability, mapping resolution + digest;
- **equivalent configs hash identically** (rebuild and JSON round-trip);
- **meaningful changes alter the digest** (input/output path, overwrite, seed, stage
  flag, exports, renderer, voxelization);
- **renderer/exports do not change `scientific_digest`** while `digest` differs; input
  path/output are ignored by `scientific_digest`; mapping/voxelization tracked;
- **full round-trip preserves every declared setting** (`from_json_dict(to_json_dict())`
  equals the original);
- canonical JSON is sorted/tight; schema and mapping digest recorded;
- **invalid combinations fail before output**: mesh without voxelization, direct-voxel
  with voxelization, unknown mapping, unsupported kind, empty paths, duplicate export
  targets, bad unit/voxel-size/material-id/padding, non-rigid placement;
- deserialization guards: incompatible major rejected, compatible minor accepted,
  unknown top-level/nested keys rejected, mapping-digest mismatch rejected, invalid JSON
  text reports a field;
- path resolution requires an explicit base dir; committed example configs parse and are
  stable.

## 5. Verification against the Step 5 checklist

| Plan verification item | Status |
| --- | --- |
| Equivalent configurations serialize and hash identically | Met — `test_equivalent_configurations_hash_identically`, `test_json_roundtrip_hashes_identically`. |
| Meaningful setting changes alter the digest | Met — `test_meaningful_changes_alter_the_digest`, `test_voxelization_change_alters_the_digest`. |
| Invalid combinations fail before any output is created | Met — construction is pure/no-I/O; the invalid-combination and mesh-settings tests all raise `PipelineConfigError`. |
| Renderer configuration cannot alter canonical material/optical results | Met — `scientific_digest` excludes renderer/exports; `test_renderer_and_exports_do_not_change_scientific_digest`. |
| Configuration round-trip preserves every declared setting | Met — `test_roundtrip_preserves_every_declared_setting`. |
| No implicit current-directory, unit, material, seed, or overwrite behaviour | Met — explicit mesh unit/material required; paths verbatim + explicit `resolve_*`; `overwrite`/`random_seed` always recorded; `test_paths_are_recorded_verbatim`, `test_resolution_requires_explicit_base_dir`, `test_direct_config_defaults_are_explicit`. |

## 6. Files added / changed

- added: `src/vbdmat/pipeline/{__init__,config,errors}.py`,
  `tests/pipeline/test_pipeline_config.py`, `examples/phase1/generate_configs.py`,
  `examples/phase1/configs/{window_coupon,stepped_wedge}.run.json`;
- changed: `src/vbdmat/voxelize/{__init__,mesh}.py` (export `SUPPORTED_MESH_UNITS`).

No changes to `core`, schema 1.0.0, Zarr persistence, optics, the Step 2/3 readers, the
Step 4 fixtures, or `uv.lock`. The pipeline package imports no renderer/exporter module
(only enum string values name the targets).

## 7. Recommendation

Proceed to **Step 6** (pipeline orchestration and run bundles). `PipelineConfig` now
provides the `config_digest`, `mapping_digest`, and resolved input/voxelization/mapping
settings the ADR-007 runner and `run.json` require, plus two committed example configs to
drive the first end-to-end runs.
