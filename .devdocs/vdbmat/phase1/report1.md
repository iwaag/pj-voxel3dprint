Representative Input Fixtures# Phase 1 — Step 1 Report: Freeze the Research MVP Workflow and Inputs

- **Date:** 2026-07-01
- **Step:** 1 of 12 (`.local/phase1/plan.md`)
- **Status:** Complete (design/decision step; ADRs authored in *Proposed* status)

## 1. Goal

Freeze the Phase 1 MVP workflow and inputs before any reader/voxelizer/pipeline/CLI
code is written: inventory available representative data, select the smallest supported
formats, author ADR-006/007/008 with worked examples, define the two representative
objects with analytic expectations, and set the maximum reference size.

## 2. Data inventory and format selection

A repository search found **no** representative printer data and **no** mesh library
already vendored:

- no `.stl`, `.vox`, `.ply`, or non-test `.npy` payload under version control
  (only NumPy's own test `.npy` files under `.venv`);
- no `trimesh` / `numpy-stl` / `meshio` / `pyvista` / `open3d` entry in `uv.lock`.

Per plan Section 4, with no printer-specific sample available, the **default baseline is
adopted**:

- **Direct material-voxel input:** `vbdmat.voxels/1.0.0` — a strict UTF-8 JSON manifest
  plus one `uint16[z,y,x]` `.npy` label payload, SHA-256 verified, path-safe, no pickle.
- **Mesh input:** a watertight single-solid STL (binary or ASCII) with **required**
  explicit `--unit`, `--voxel-size`, `--material-id` and optional rigid placement.

**Dependency decision:** Phase 1 uses a **repository-owned** STL reader and
VBDMAT-owned voxelization; **no new dependency is added** to the core environment.
Rationale: STL parsing is small and fully specified, topology/voxelization correctness
must be owned and analytically tested regardless of any library, and a new core
dependency carries licensing/ABI/install cost that the plan's stop conditions guard
against. `uv.lock` is therefore unchanged by Step 1.

## 3. Deliverables produced

Three ADRs, all in **Proposed** status (they move to Accepted only if an end-to-end run
demonstrates a contradiction requiring amendment):

- [docs/adr/0006-phase1-inputs-and-voxelization.md](../../docs/adr/0006-phase1-inputs-and-voxelization.md)
  — direct-voxel format `vbdmat.voxels/1.0.0`; STL mesh format + owned-reader dependency
  policy; required unit/transform/palette/provenance metadata; SHA-256 + path-safety
  rules; dense cell-centre voxelization domain/padding; ray-parity inside/outside rule;
  boundary tie-breaking; topology checks and rejection cases; numeric tolerances.
  Includes **Worked Example V** (direct multi-material voxel) and **Worked Example M**
  (mesh-to-grid with analytically known 27 occupied cells).
- [docs/adr/0007-pipeline-run-and-artifact-bundle.md](../../docs/adr/0007-pipeline-run-and-artifact-bundle.md)
  — fixed typed stage graph; versioned configuration + digest; deterministic
  timestamp-free `run_id`; bundle layout; `run.json` schema; provenance chaining;
  atomic temp-dir-build + rename publication; overwrite/no-resume policy; precise
  "reproducible rerun" definition; forward-compatible manifest behaviour. Includes a
  worked window-coupon bundle and `summary.json` shape.
- [docs/adr/0008-cli-contract-and-failure-semantics.md](../../docs/adr/0008-cli-contract-and-failure-semantics.md)
  — `vbdmat` command set; stdout(JSON)/stderr(diagnostics) split; exit codes `2` usage /
  `3` validation / `4` I/O / `5` conversion-pipeline / `6` optional-dependency (`1`
  reserved for internal bugs); overwrite policy; inspection surface; capability
  diagnostics; installed-package robustness; API/CLI equivalence. Includes worked
  success and each expected-failure invocation.

All three reuse the existing Phase 0 types unchanged (`GridGeometry`,
`MaterialPalette`/`MaterialDefinition`, `Provenance`, `MaterialLabelVolume`,
`OpticalMappingConfig`, `vbdmat.io.zarr`) and do **not** modify schema 1.0.0. The
canonicalization/digest approach in ADR-007 matches the existing
`OpticalMappingConfig.canonical_json()` / `.digest`.

## 4. Representative objects (defined; fixtures built in Step 4)

1. **Multi-material window coupon** (direct voxel): transparent matrix, one white
   inclusion, one asymmetric black marker, background. Features are non-symmetric across
   X/Y/Z so a render exposes axis reversal. ADR-006 Worked Example V is the tiny
   `shape_zyx=(2,3,4)` seed of this object, with the unique black marker at
   `material_id[0,2,3]` (moves under any transpose) and analytic per-material counts.
2. **Single-material stepped wedge** (mesh): a watertight staircase with fixed thickness
   steps giving analytically predictable per-layer occupancy and bounds. ADR-006 Worked
   Example M gives the companion analytic box case (3 mm cube at 1 mm voxels ⇒ exactly
   27 occupied cells; count preserved under a 1 mm translation).

## 5. Maximum Phase 1 reference size

Safety bound (not a performance claim): **≤ 128 cells on any axis** and **≤ 2,000,000
cells total**. Voxelization and pipeline runs assert this; exceeding it is a usage error
pointing to a coarser voxel size. Peak memory/runtime at the bound are recorded in Steps
3 and 11.

## 6. Verification against the Step 1 checklist

| Plan verification item | Status |
| --- | --- |
| Every supported input field has one unit, axis, transform interpretation | Met — ADR-006 D1–D8 fix a single meaning per field; no inferred units/axes. |
| Unsupported printer/mesh/topology/material cases listed explicitly | Met — ADR-006 D9 rejection list; ADR-006 "no printer format claimed". |
| Reference objects have analytic expected bounds and selected cells | Met — Worked Examples V and M; stepped-wedge/coupon analytic expectations to be committed with Step 4 fixtures. |
| Run bundle links all Phase 1 artifacts without changing schema 1.0.0 | Met — ADR-007 composes ADR-004 Zarr assets; `run.json` links, never reinterprets. |
| Dependency additions justified and locked with uv | Met — **no** additions; owned STL reader; `uv.lock` unchanged. |
| Decisions do not introduce renderer state into core or pipeline stages | Met — ADR-007 D1 keeps renderer state out of all stages before optional `export`; core completes without any renderer. |

## 7. Stop conditions checked

None triggered. The selected inputs provide unambiguous units/axes/palette/placement
(ADR-006); the run bundle composes rather than reinterprets schema 1.0.0 (ADR-007); the
CLI never infers units, transposes, casts, remaps IDs, or overwrites without
authorization (ADR-008); mesh boundary behaviour is deterministic (ADR-006 D8); no mesh
dependency cost is incurred (owned reader). The absence of a printer-vendor format is
explicitly acknowledged, not worked around.

## 8. Notes and follow-ups

- ADRs are **Proposed**; they are ratified (Accepted) once Steps 2–8 demonstrate the
  contracts hold end to end, per plan Section 5.
- Exact SHA-256 digests for Worked Example V and the coupon payload are produced with
  the Step 4 fixtures (they depend on the committed `.npy` bytes).
- Self-intersection detection is documented as non-exhaustive in Phase 1 (ADR-006 D9);
  revisit if a representative mesh requires it.

## 9. Readiness for the next steps

Step 1 fixes the contracts for Steps 2 (direct-voxel reader) and 3 (mesh + voxelization),
which may now proceed in parallel. Recommendation: **proceed** to Step 2 and Step 3.
