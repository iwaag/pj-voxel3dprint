# Phase 1 — Step 11 Report: Clean Installed-Environment Reproduction

- **Date:** 2026-07-02
- **Step:** 11 of 12 (`.local/phase1/plan.md`)
- **Status:** Complete. The Phase 1 workflow was reproduced from a built wheel outside
  the repository, and the default, Mitsuba, and native OpenVDB/Cycles paths passed
  independently.

## 1. Clean installation and package verification

The repository environment was synchronized from `uv.lock` with uv 0.10.3. A fresh
wheel was built and installed into `/tmp/vbdmat-step11/venv`; all CLI work below ran
from `/tmp/vbdmat-step11/work`, not the repository root.

```text
uv sync --locked --all-groups
uv build --wheel --clear --out-dir .local/phase1/step11/dist
uv venv --python 3.12 /tmp/vbdmat-step11/venv
uv pip install --python /tmp/vbdmat-step11/venv/bin/python \
  .local/phase1/step11/dist/vbdmat-0.1.0-py3-none-any.whl
```

The imported module resolved to the new venv's `site-packages`, not the source tree.
The 96,370-byte wheel contains all Phase 1 `cli`, `io`, `pipeline`, `voxelize`,
`optics`, and `exporters` packages and the `vbdmat = vbdmat.cli.main:main` console
entry point. Its SHA-256 is
`80c8dd1ae7ea6f243b1831f9e0464a7d511d93cbf8c2cbc6da8c0a66a11ef73b`.

Installed environment: CPython 3.12.11, NumPy 2.5.0, Zarr 3.2.1, Mitsuba 3.9.0.
Host: Linux 6.17.0-35-generic x86_64.

## 2. Installed CLI and canonical pipelines

The installed CLI successfully performed all of the following from the external work
directory:

1. imported `window_coupon.voxels.json` to canonical material Zarr;
2. voxelized `stepped_wedge.stl` with explicit millimetre units, 1 mm voxels,
   material ID 1, and one padding cell;
3. inspected and fully validated both material assets;
4. executed both complete pipeline configurations;
5. inspected and fully validated both published run bundles, including artifact
   checksums.

| Object | Shape / cells | Material counts | Pipeline runtime | Peak RSS | Bundle size |
| --- | --- | --- | ---: | ---: | ---: |
| window coupon | `(12,16,20)` / 3,840 | `{0:0, 1:3750, 2:72, 3:18}` | 1.02 s | 51,132 KiB | 119,976 B |
| stepped wedge | `(10,8,18)` / 1,440 | `{0:960, 1:480}` | 0.48 s | 50,976 KiB | 48,684 B |

The corresponding standalone imported/voxelized material Zarr sizes were 18,625 and
6,999 bytes. Both objects remain far below the Phase 1 limit of 128 cells per axis and
2,000,000 total cells. The near-limit benchmark was already recorded in the Step 2–3
report; this step records the contributor-facing reference-object costs.

## 3. Reference renderer reproduction

The fixed reference generator was copied to the external work directory and executed
with the wheel-installed package. Mitsuba regenerated both canonical bundles and both
256 x 256, 64 spp reference renders in 2.32 s with 319,396 KiB peak RSS.

The following Step 10 identities matched exactly for both objects:

- run ID;
- material Zarr SHA-256;
- optical Zarr SHA-256;
- Mitsuba baseline PNG SHA-256;
- OpenVDB/Cycles decoded-pixel SHA-256.

Mitsuba baseline PNG hashes remained:

- coupon: `f8a810cf078589c2bb3e32c1695f0422b1800869b2228ef57d1473a0ce06dfdc`;
- wedge: `a1aa8fa95c1e3a06342aa75751d32c5cfb4d3f35e45cd5408884ddf3436b242b`.

The current Dockerfile was rebuilt as
`vbdmat-phase1-step11:blender4.5.11` (image
`sha256:1fd1c3fa6b5d5dd981264c0d2ad90362fcc0e056992a6bb6e17f70366fbfc2f0`).
Inside it, the same wheel was installed into a temporary target before exporting and
rendering both restored `optical.zarr` assets with OpenVDB 10.0.1 and Blender/Cycles
4.5.11. The combined native command took 1.98 s; Blender reported 9.41 MiB and
9.11 MiB peak memory for the coupon and wedge renders. Both decoded-pixel hashes were
`sha256:25ef30d0af5bfafb64fd004efb026d06b7f9fca230661624879fdb470a06a1a0`,
matching Step 10. PNG file bytes remain intentionally non-stable.

The complete installed reproduction tree occupied 2,028,209 bytes: 1,134,874 bytes
for the coupon object directory and 856,561 bytes for the wedge object directory,
plus shared inputs and the baseline manifest.

## 4. Verification results

```text
uv lock --check                              pass
uv sync --locked --all-groups                pass
uv run ruff format --check .                 pass
uv run ruff check .                          pass
uv run mypy --strict src/vbdmat              pass (44 source files)
uv run pytest -q                             374 passed, 2 native-only skipped
uv run --locked --group mitsuba pytest -m mitsuba
                                                10 passed
pinned-container native integration tests    2 passed
cross-consumer conformance                    6 fixtures passed, 0 failures
git diff --check                              pass
```

The first formatting check exposed pre-existing formatting drift in 12 Phase 1 files;
Ruff formatting was applied and the complete gate was rerun successfully. The native
image tag available before this step predated the Phase 1 venv layer, so the current
Dockerfile was rebuilt rather than relying on stale local image state. No source edits,
editable installation, or repository-relative Python imports were required during the
external workflow.

Machine-readable evidence is retained under `.local/phase1/step11/`:

- `dist/vbdmat-0.1.0-py3-none-any.whl`;
- `conformance.json`;
- `installed-baseline-manifest.json`.

Coefficients remain provisional and uncalibrated. Successful reproduction demonstrates
software and interoperability consistency, not physical print accuracy.
