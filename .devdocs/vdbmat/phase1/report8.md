# Phase 1 — Step 8 Report: Integrate Export Commands Without Core Leakage

- **Date:** 2026-07-02
- **Step:** 8 of 12 (`.local/phase1/plan.md`)
- **Status:** Complete. Standalone CLI and config-driven exports restore canonical
  `optical.zarr`, publish capability/version/checksum diagnostics, and preserve the
  renderer-free canonical path. Both Phase 1 objects loaded through Mitsuba and
  OpenVDB and rendered through Blender Cycles without scene edits.

## 1. Implementation

Added `vbdmat.exporters.export_restored_optical`, the common API used by CLI and the
pipeline. It fully restores and type-checks `optical.zarr` before dispatching to an
adapter. No in-memory pipeline optical object or renderer-specific state crosses this
boundary.

`vbdmat export` now supports:

```text
vbdmat export mitsuba OPTICAL_ZARR OUTPUT [--render] [--overwrite] [--json]
vbdmat export openvdb OPTICAL_ZARR OUTPUT [--overwrite] [--json]
```

Mitsuba's default operation prepares the loadable scene, PLY containment/interface
meshes, summary, and capability report; `--render` additionally writes its fixed EXR
and PNG outputs. OpenVDB writes ten named grids, its affine/field manifest, and the
capability report. Blender/Cycles remains the documented external native follow-up.
Standalone output is staged beside the destination and atomically published, so a
missing dependency or failed replacement retains any previous output.

Missing Mitsuba/OpenVDB runtimes have dedicated dependency error types and map to CLI
exit 6 with locked-group/container instructions. Other valid-input adapter failures map
to conversion exit 5. Unsupported and approximated semantics are returned in JSON;
OpenVDB output also returns the Cycles follow-up instruction.

## 2. Pipeline and run bundle

The pipeline now uses the real adapter dispatcher by default when `stages.exports` is
non-empty. Export runs only after atomic canonical bundle publication and reads the
published `optical.zarr`. A failure marks only `export=failed`, removes its partial
target directory, and leaves material/optical assets readable.

On success, `run.json` records:

- target, adapter and adapter version;
- renderer name and detected version;
- complete capability report;
- export provenance;
- every exported file's relative path, SHA-256, and size;
- export stage status.

Bundle inspection now surfaces export state and version records, and full validation
checks export checksums together with canonical assets.

## 3. Native environment correction

The previous OpenVDB/Cycles image had OpenVDB bindings but no Zarr reader, so it could
not satisfy the restored-Zarr CLI contract. The Dockerfile now adds a
system-site-packages venv with NumPy 1.26.4 and Zarr 3.0.10. This retains compatibility
with Ubuntu's OpenVDB 10.0.1 binding. Zarr 3.1+ was rejected because it requires NumPy
2, which cannot load the NumPy-1.x-built binding safely.

Reproduction commands and failure semantics are documented in
`docs/phase1-export-workflow.md`.

## 4. Verification

Core and static checks:

```text
uv lock --check                         pass
uv run ruff check .                     pass
uv run mypy --strict src/vbdmat         pass (44 source files)
uv run pytest -q                        366 passed, 2 native-only skipped
focused Step 8 suite                    60 passed
```

The host full suite included the locked Mitsuba tests. The two skips were OpenVDB and
Blender tests, which passed separately in the rebuilt native image:

```text
tests/integration/test_openvdb.py        1 passed
tests/integration/test_blender_cycles.py 1 passed
```

Reference-object evidence under `.local/phase1/step8/`:

| Object | Mitsuba 3.9.0 | OpenVDB 10.0.1 | Blender 4.5.11 |
| --- | --- | --- | --- |
| `window_coupon` | scene loaded/prepared, 5 artifacts | 10 grids exported/read | 64x64, 32 spp render |
| `stepped_wedge` | scene loaded/prepared, 5 artifacts | 10 grids exported/read | 64x64, 32 spp render |

Both Cycles smoke PNGs have SHA-256
`95364a39a86f8f2d4c35d244d664bcf7981eaa038e76960dc92e8f76251f076f`.
The equal dark smoke images are load/interoperability evidence only, not a visual
baseline or orientation discriminator; Step 10 owns diagnostic scene improvement.
Field/order/transform tests remain the authoritative pre-render conformance evidence.

The generated Step 8 evidence occupies approximately 528 KiB. No Mitsuba, OpenVDB,
or Blender import is required by canonical import, voxelization, mapping, validation,
or Zarr persistence; adapters load optional runtime modules lazily only when requested.
