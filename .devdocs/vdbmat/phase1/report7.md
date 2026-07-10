# Phase 1 — Step 7 Report: Implement the Phase 1 CLI

- **Date:** 2026-07-02
- **Step:** 7 of 12 (`.local/phase1/plan.md`)
- **Status:** Complete. `uv lock --check`, `ruff check .`, `mypy --strict
  src/vbdmat`, and the full suite pass (354 passed; 3 optional renderer tests skipped).
  A built wheel was installed into a clean virtual environment and its `vbdmat`
  executable completed import, conversion, and validation outside the repository.

## 1. Goal

Expose the Step 2–6 package APIs through the installed `vbdmat` entry point without
duplicating scientific logic. Implement the ADR-008 commands, stable JSON/human output,
documented exit categories, overwrite protection, asset/run inspection and validation,
and expected-error handling without tracebacks.

## 2. Deliverables produced

### Installed entry point and CLI package

`pyproject.toml` now declares `vbdmat = "vbdmat.cli.main:main"` under
`[project.scripts]`. The new `src/vbdmat/cli/` package contains:

- `main.py`: argument parsing and thin calls into `vbdmat.io`, `vbdmat.voxelize`,
  `vbdmat.optics`, and `vbdmat.pipeline`;
- `errors.py`: stable `ExitCode` values and typed expected CLI failures;
- `output.py`: sorted, compact, one-document JSON and concise human summaries.

Implemented commands:

```text
vbdmat import-voxels MANIFEST OUTPUT [--overwrite] [--json]
vbdmat voxelize MESH OUTPUT --unit {m,mm} --voxel-size M[,M,M]
                 --material-id ID [--placement FILE] [--overwrite] [--json]
vbdmat convert MATERIAL_ZARR OUTPUT [--mapping NAME] [--overwrite] [--json]
vbdmat inspect ASSET [--json]
vbdmat validate ASSET [--json]
vbdmat run CONFIG [--json]
vbdmat export {mitsuba|openvdb} OPTICAL_ZARR OUTPUT
```

`export` establishes the command and failure boundary but deliberately returns exit 6
with a Step 8 connection message. Renderer adapter wiring and capability artifact
publication belong to Step 8; no renderer dependency enters the Step 7 core CLI.

### Inspection and validation

Canonical-volume inspection exposes schema/asset type, ZYX shape and storage order,
XYZ metre voxel size, rigid transform, right-handed/cell-centred conventions,
provenance, material counts or optical field ranges, RGB basis metadata, and the
`provisional-uncalibrated` calibration state.

Run-bundle inspection loads `run.json`, the deterministic summary, and both canonical
Zarr assets. Run-bundle validation additionally verifies every declared file/store
SHA-256, rejects paths escaping the bundle, and fully restores both volumes through the
canonical reader.

### Failure semantics

The ADR-008 categories are implemented and covered by subprocess tests:

| Exit | Category | Covered example |
| ---: | --- | --- |
| 2 | usage | missing required mesh flags; unauthorized overwrite |
| 3 | validation | open mesh / invalid canonical content |
| 4 | I/O | missing input; payload checksum mismatch |
| 5 | conversion/pipeline | optical asset passed as material conversion input |
| 6 | optional dependency | pre-Step-8 renderer export request |

Expected failures emit no traceback unless `--debug` or `VBDMAT_DEBUG=1` is active.
With `--json`, stdout contains exactly one parseable success/error document; diagnostics
remain on stderr, including argument-parser failures.

## 3. Verification

`tests/cli/test_cli.py` adds seven subprocess tests covering:

- direct import with paths containing spaces;
- byte-identical Zarr output versus the corresponding package API call;
- mesh voxelization (480 occupied wedge cells), conversion, inspection, validation;
- complete config-driven run and run-bundle inspection;
- refusal and explicit authorization of overwrite;
- exit codes 2–6 and absence of expected-error tracebacks;
- parseable JSON/error separation and help text for units, defaults, provisional
  coefficients, and physical-prediction non-goals.

Final repository checks:

```text
uv lock --check                         pass (no dependency change)
uv run ruff check .                     pass
uv run mypy --strict src/vbdmat         pass (43 source files)
uv run pytest -q                        354 passed, 3 skipped
```

Installed-wheel check:

1. `uv build --wheel` produced `vbdmat-0.1.0-py3-none-any.whl`.
2. The wheel was installed into a fresh `uv venv`.
3. From a temporary directory outside the repository, the installed executable ran
   `import-voxels`, `convert`, and `validate --json` successfully against copied input
   files, producing valid material and optical Zarr stores.

## 4. Scope boundary for Step 8

No renderer is imported by the CLI or canonical commands. Step 8 must replace the
current explicit export-boundary failure with the existing Mitsuba/OpenVDB adapters,
surface adapter capability diagnostics, and provide actionable environment-specific
installation instructions while retaining the exit-6 and canonical-artifact isolation
contracts established here.
