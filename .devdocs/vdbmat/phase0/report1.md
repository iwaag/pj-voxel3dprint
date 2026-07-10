# Phase 0 Implementation Report: Step 1

**Date:** 2026-06-28  
**Completed scope:** Step 1 — Bootstrap the Project  
**Status:** Complete

## Summary

Step 1 established a working uv-based Python project, an installable `src`-layout package, a reproducible lockfile, baseline quality checks, CI configuration, and a package-installation smoke test.

This is the selected stopping point. Step 2 begins the coordinate and schema architecture decisions and is intentionally not started in this report.

## Implemented Artifacts

### Project and dependency management

- Added `.python-version` with Python 3.11 as the repository baseline.
- Added `pyproject.toml` using the uv native build backend.
- Added and committed-by-design `uv.lock` generated with uv 0.10.3.
- Added core runtime dependencies:
  - NumPy;
  - Zarr.
- Added the default `dev` dependency group:
  - pytest;
  - Ruff;
  - mypy.
- Added a separate `mitsuba` dependency group.
- Added an empty `openvdb` dependency group as an explicit integration boundary until a compatible binding source and host environment are selected.

### Package skeleton

- Added `src/vbdmat/__init__.py`.
- Exposed the installed distribution version as `vbdmat.__version__`.
- Kept the package free of renderer, OpenVDB, and Zarr imports at import time.

### Tests and quality configuration

- Added strict pytest configuration.
- Added strict mypy configuration for Python 3.11.
- Added Ruff formatting and lint rules.
- Added `tests/test_package.py` to verify that:
  - `vbdmat` imports through the installed editable package;
  - the module resolves from the `src/vbdmat` tree;
  - the package and distribution versions agree.

### Continuous integration

- Added `.github/workflows/ci.yml`.
- Pinned the uv setup action by commit and pinned uv to 0.10.3.
- Configured CI to:
  1. install the repository-selected Python;
  2. run `uv sync --locked`;
  3. check formatting;
  4. run linting;
  5. run mypy;
  6. run pytest.

### Documentation and repository hygiene

- Added uv-only development and dependency-management instructions to `README.md`.
- Documented the separate Mitsuba and OpenVDB integration environments.
- Expanded `.gitignore` for the uv environment, Python bytecode, test/tool caches, build artifacts, and distribution metadata.
- Preserved the pre-existing empty `REDME_DEV.md`; it was unrelated to Step 1 and was not removed or renamed.

## Commands Executed

```bash
uv lock
uv sync --locked
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
```

An additional import inspection confirmed that the installed package resolves from `src/vbdmat` and that Mitsuba is absent from the default environment.

## Verification Results

| Check | Result |
| --- | --- |
| uv lock generation | Passed; 24 packages resolved |
| Python selection | Passed; uv installed and used CPython 3.11.14 |
| Locked synchronization | Passed; package built and installed in `.venv` |
| Lockfile consistency | Passed; `uv lock --check` exited successfully |
| Ruff formatting | Passed; 2 Python files already formatted |
| Ruff linting | Passed; no issues |
| mypy strict check | Passed; no issues in 1 source file |
| pytest | Passed; 1 test collected and passed |
| Installed import path | Passed; resolved to `src/vbdmat/__init__.py` |
| Default dependency isolation | Passed; Mitsuba was not installed in the default environment |
| Mitsuba lock coverage | Passed; Mitsuba and Dr.Jit entries are present in `uv.lock` |
| Git whitespace check | Passed; `git diff --check` reported no errors |

## Decisions Made

1. **uv is the exclusive Python workflow.** Python installation, environment creation, dependency updates, locking, synchronization, and commands use uv.
2. **Python 3.11 is the minimum and selected Phase 0 baseline.** The project metadata allows Python 3.11 or newer, while `.python-version` selects the 3.11 series for local and CI reproduction.
3. **The uv native build backend is used.** Its version range follows the pinned uv 0.10 minor series for Phase 0.
4. **`uv.lock` is a repository artifact.** Local initial setup may update it deliberately, while CI uses `--locked` and rejects drift.
5. **Renderer proof dependencies are not default dependencies.** Mitsuba has a named group; OpenVDB has an explicit empty group pending the environment decision.
6. **The package remains structurally minimal.** Core, I/O, optics, and exporter modules will be added only after their contracts are decided in subsequent steps.

## Deviations and Observations

- No implementation deviation from Step 1 remains open.
- During the first lock operation, uv detected and removed one broken entry in its user-level interpreter cache, then downloaded CPython 3.11.14 and completed normally. This did not affect repository files or subsequent checks.
- OpenVDB bindings are not yet locked because their source and compatibility constraints depend on the later Blender/OpenVDB proof environment. The named empty group prevents this unresolved external dependency from entering the core environment silently.
- `uv.lock` includes the optional Mitsuba group even though `uv sync --locked` does not install it by default. This is expected uv project behavior and preserves default-environment isolation.

## Step 1 Completion Assessment

The Step 1 verification requirements are satisfied:

- a clean uv-managed Python 3.11 environment synchronized successfully from the lockfile;
- the lockfile and project metadata agree;
- all quality and test commands run through `uv run` and pass;
- the package imports through its editable installation;
- optional renderer dependencies do not leak into the default package import or environment.

## Next Step

Proceed with Step 2 by writing ADR-001 and ADR-002 before adding volume model implementation:

- coordinates, axes, transforms, units, and sampling conventions;
- canonical material-label, material-mixture, and optical-property schemas;
- worked anisotropic-grid, world-coordinate, RGB coefficient, and mixture examples.
