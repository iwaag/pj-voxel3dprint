# VBDMAT Utils Roadmap

## Vision

`vbdmat-utils` will be the monorepo for tools and services that generate material-labeled voxel
inputs for `vbdmat`. It will turn heterogeneous sources—meshes, image stacks, procedural models,
and eventually learned models—into one stable interchange contract:

```text
source data
    |
    v
generator or converter
    |
    v
canonical material-label volume
    |
    v
<name>.voxels.json + <name>.material_id.npy
    |
    v
vbdmat validation and optical simulation
```

The repository should make generation algorithms easy to experiment with without allowing each
algorithm to invent its own coordinate system, material semantics, provenance, or output format.
Python is the initial implementation language. Native code or GPU execution should be introduced
only for measured bottlenecks behind stable Python interfaces.

## Product Boundary

`vbdmat-utils` owns:

- importing source geometry, images, and generator-specific parameters;
- producing canonical `uint16` material-label arrays in `z, y, x` axis order;
- voxel geometry, material palette construction, and generator provenance;
- deterministic generation and conversion workflows;
- validation against the `vbdmat.voxels` input contract;
- emitting companion `vbdmat.optical-mapping` documents (per `docs/schemas/optical-mapping-v1.md`)
  whenever a generator's palette uses material names outside `vbdmat`'s built-in table, so every
  generated asset ships with a mapping that lets it run end to end;
- previews and diagnostics needed to inspect generated volumes;
- optional adapters for formats useful during generation, such as meshes or OpenVDB.

`vbdmat-utils` does not own:

- the optical coefficient *values* or their scientific validity (coefficients come from `vbdmat`'s
  built-in table, calibration, or user-supplied data; utils only packages them into mapping
  documents paired with generated palettes);
- optical-property generation itself;
- print-process simulation, calibration, or renderer-specific optical export;
- a production renderer or DCC application;
- printer control, slicing, or firmware;
- a second competing definition of the `vbdmat.voxels` contract.

The handoff to `vbdmat` is the checksummed manifest and NPY payload. OpenVDB may be useful for
preview, sparse inspection, or external interchange, but it is not the primary `vbdmat` input
contract.

## Architectural Principles

1. **One canonical output.** Every generator must produce the same material-label volume contract,
   regardless of its source data or algorithm.
2. **Contract compatibility is tested.** Outputs must pass the public `vbdmat` validator and
   selected fixtures must run through the `vbdmat` pipeline end to end.
3. **Physical metadata is explicit.** Axis order, voxel size, rigid transform, units, material
   palette, random seed, source identity, and generator version must never be implicit.
4. **Determinism is the default.** Given the same inputs, configuration, and seed, a generator must
   reproduce byte-equivalent or scientifically equivalent output according to a documented rule.
5. **A lightweight core, optional heavy features.** Mesh, image, OpenVDB, preview, ML, and GPU
   dependencies belong to separate extras or workspace packages.
6. **Algorithms depend on the core contract.** Core data structures must not depend on individual
   generators, OpenVDB, DCC tools, ML frameworks, or web-service frameworks.
7. **Dense NumPy first.** Establish correctness on small, inspectable volumes before introducing
   sparse, chunked, native, or GPU implementations.
8. **Split by proven lifecycle needs.** Begin with a small number of coherent packages in one
   repository. Create independently published packages only when dependency, release, or ownership
   boundaries justify them.

## Initial Monorepo Shape

The exact package split may evolve, but dependencies should flow toward `core`:

```text
vbdmat-utils/
  pyproject.toml                 # workspace, shared tooling, dependency groups
  packages/
    vbdmat-utils-core/           # volume model, transforms, palette, manifest output
    vbdmat-utils-mesh/           # mesh import and voxelization
    vbdmat-utils-image/          # image stacks, interpolation, and morphing
    vbdmat-utils-procedural/     # noise, strata, veins, pores, and crystal models
    vbdmat-utils-vdb/            # optional OpenVDB adapter
  apps/
    cli/                         # unified local and batch CLI
    service/                     # optional HTTP/job service when requirements are known
  examples/
  tests/
    contract/
    integration/
  experiments/                  # unstable research code; no public API guarantees
```

The first milestone does not need to create every package. If a single Python distribution with
internal modules is simpler, use that first while preserving these dependency boundaries. Avoid
duplicating packaging infrastructure before a second independently installable component is
needed.

## Near-Term Roadmap

### Phase 0 — Repository and Contract Foundation

**Status: complete (2026-07-05).** All bullets below are implemented in `vdbmat-utils`; the exit
criteria run in CI (`.github/workflows/ci.yml`, "Phase 0 exit criteria" step). Execution reports:
`.devdocs/vdbmat-utils/reports/phase0/`. Decisions recorded as ADRs 0001–0003 in
`vdbmat-utils/docs/adr/`. Two upstream follow-ups noted for `vdbmat`: ship a `py.typed` marker
and re-export `Matrix4` from `vdbmat.core`.

**Goal:** establish a small, testable foundation shared by every generator.

- Set up Python packaging, a supported Python-version policy, linting, type checking, tests, and CI.
- Decide and document the dependency mechanism on `vbdmat`, which is not published to PyPI: a
  pinned git/commit dependency or a local path/submodule dependency, with the pin recorded in the
  workspace configuration and bumped deliberately. Contract-compatibility tests run against the
  pinned version.
- Define canonical in-memory types for a material-label volume, voxel geometry, rigid transform,
  material palette, and provenance.
- Reuse the public `vbdmat` manifest writer and validator where practical; do not fork its schema
  rules into an incompatible local implementation.
- Add golden fixtures covering anisotropic voxels, non-zero origins, rotations, multiple materials,
  and invalid metadata.
- Provide a minimal CLI that can inspect and validate a generated asset.
- Define configuration serialization, seed handling, error conventions, and generator versioning.
- Record compatibility with an explicit supported range of `vbdmat` contract versions.

**Exit criteria:** a synthetic in-memory volume can be written deterministically, validated by
`vbdmat import-voxels`, inspected by the CLI, and exercised in CI without optional dependencies.

### Phase 1 — First Useful Conversion Workflows

**Status: complete (2026-07-07).** All bullets below are implemented in `vdbmat-utils`
(plan: `.devdocs/vdbmat-utils/plans/phase1/plan.md`; execution reports 0–6:
`.devdocs/vdbmat-utils/reports/phase1/`). The mesh path (`voxelize-mesh`) is a port of the
voxelizer recovered from `vdbmat` commit `8f55562` per `memo_stltovoxel.md`, constants
preserved verbatim; the image-stack generator moved to `convert-image-stack` and
`vdbmat/tools/image_stack_generator/` was deleted outright (no equivalence shim, per the
2026-07-06 no-backward-compat decision). Decisions recorded as ADRs 0004–0006; user docs in
`vdbmat-utils/docs/{voxelization,image-stacks,previews}.md`. Exit criteria run in CI
("Phase 1 exit criteria" step: both workflows → `validate` → `vdbmat import-voxels` →
`vdbmat convert`), alongside a minimal-install leg proving STL + PGM + previews need no
extras (only PNG needs `image`/Pillow). Upstream `vdbmat` follow-ups: the two Phase 0 items
(`py.typed`, `Matrix4` re-export) remain open, plus new: 8 pre-existing ruff errors in
`vdbmat/examples/phase1/demo/blender_glass_demo.py`, and the superproject submodule pin must
be bumped for the tool-deletion commit (ADR 0001 procedure).

**Goal:** provide practical non-ML paths for producing valid `vbdmat` inputs.

- Port or reimplement mesh-to-voxel conversion using the preserved knowledge in
  `vbdmat/.local/memo_stltovoxel.md`; support a deliberately narrow set of mesh formats first.
- Move the existing image-stack reference generator out of the `vbdmat` repository when its public
  API and compatibility tests are ready.
- Support explicit material assignment, voxel size, transform, domain bounds, and background rules.
- Add slice and material-count previews that work without OpenVDB.
- Test watertight and invalid meshes, boundary behavior, axis orientation, checksum stability, and
  material conservation where applicable.
- Add end-to-end fixtures that generate assets and run them through `vbdmat` optical conversion.

**Exit criteria:** users can reproducibly convert at least one mesh workflow and one image-stack
workflow into validated `vbdmat` inputs, with diagnostic output for common failures.

### Phase 2 — Image Morphing and Volume Composition

**Status: complete (2026-07-07).** All bullets below are implemented in `vdbmat-utils`
(plan: `.devdocs/vdbmat-utils/plans/phase2/plan.md`; execution reports:
`.devdocs/vdbmat-utils/reports/phase2/`). New workflows: `morph-stack` (per-label SDF
interpolation of sparse key slices; in-repo exact EDT, no scipy) and `apply-pipeline`
(SSA-style config-driven op pipelines over `crop`/`pad`/`resample`/`orient`/`place`/
`apply-mask`/`compose`/`remap-materials`). Label safety is structural: the
`fields.ScalarField` type split, the quantize-only scalar→label gate, an AST guard test,
and nearest-neighbor-only resampling. Topology/missing-slice/label-conflict/edge behavior
is documented in `vdbmat-utils/docs/{morphing,volume-ops,pipelines}.md`; decisions recorded
as ADRs 0007–0009. Exit criteria run in CI ("Phase 2 exit criteria" step: both workflows →
`validate` → `vdbmat import-voxels` → `vdbmat convert`) and the minimal-install leg runs
both workflows with no extras (Phase 2 added no runtime dependencies). No new upstream
`vdbmat` follow-ups: the pipeline input reader uses the public
`vdbmat.io.read_material_label_manifest` (Step 0.0 finding); the Phase 0/1 follow-ups
(`py.typed`, `Matrix4` re-export, example ruff errors, submodule pin bump) remain open.

**Goal:** support authored volumetric structures that are not direct mesh voxelizations.

- Add interpolation and morphing between labeled 2D slices while preserving discrete material IDs.
- Add volume crop, pad, resample, transform, mask, boolean composition, and material remapping
  operations.
- Define behavior for topology changes, missing slices, label conflicts, and interpolation outside
  the source domain.
- Separate label-safe operations from continuous scalar-field operations so material IDs are never
  accidentally interpolated as numeric intensities.
- Provide configuration-driven pipelines that compose operations without custom Python scripts.

**Exit criteria:** a user can build a multi-material volume from sparse or morphed image inputs and
obtain deterministic, contract-valid output with documented topology and label behavior.

### Phase 3 — Procedural Natural-Material Generators

**Goal:** generate controllable mineral-, rock-, and formation-like material distributions.

- Implement reusable seeded primitives: multi-scale noise, Voronoi/Worley cells, ridges, domain
  warping, distance fields, and morphology.
- Build composable models for host rock, strata, veins, grains or crystals, pores, and fractures.
- Express outputs as discrete material labels with measurable constraints such as volume fraction,
  feature size, connectivity, and minimum printable thickness.
- Emit a companion `vbdmat.optical-mapping` document alongside every generated asset whose palette
  names fall outside `vbdmat`'s built-in table (mineral, vein, and formation materials will).
  Compute the mapping digest with `vbdmat mapping-digest` and record it in provenance so the asset
  plus mapping pair runs through `vbdmat` without manual coordination.
- Separate visual plausibility from geological or physical validity; document what each model does
  and does not claim.
- Add parameter sweeps, summary statistics, and small reference datasets for regression testing.

**Exit criteria:** at least one seeded procedural formation can be regenerated, statistically
characterized, previewed, and consumed by `vbdmat` end to end.

### Phase 4 — Batch Generation Service

**Goal:** make stable generators usable as reproducible jobs, locally and in shared environments.

- Define a versioned job specification containing generator type, parameters, inputs, seed,
  resource limits, and expected outputs.
- Implement batch execution, structured logs, progress reporting, cancellation, artifact manifests,
  and safe temporary-file handling.
- Add content-addressed caching and idempotent job behavior before introducing distributed workers.
- Expose an HTTP API only after the job model and operational requirements are stable; keep the CLI
  and Python API as first-class clients of the same application layer.
- Treat untrusted uploads, path traversal, archive expansion, resource exhaustion, and generated
  artifact retention as explicit security concerns.

**Exit criteria:** the same versioned job runs through the Python API, CLI, and—if justified—service
adapter with equivalent outputs and auditable provenance.

### Phase 5 — Scale and Optional Acceleration

**Goal:** process larger domains and batches based on measured workload requirements.

- Establish benchmark datasets and budgets for memory, runtime, output size, and acceptable error.
- Add chunked execution and halo rules for local operations before considering a wholesale sparse
  rewrite.
- Introduce OpenVDB import/export where sparsity or ecosystem integration provides a measured
  benefit.
- Accelerate demonstrated hotspots with vectorized NumPy, Numba, Taichi, PyTorch, C++, or CUDA as
  appropriate while retaining the reference implementation as a correctness oracle.
- Support resumable jobs and bounded-memory pipelines for service operation.

**Exit criteria:** representative large jobs meet documented resource targets, and accelerated
results remain consistent with small-volume reference implementations.

### Phase 6 — Learned Generators and Dataset Tooling

**Goal:** add ML-based generation only after data and evaluation requirements are concrete.

- Define dataset manifests, preprocessing, train/validation/test separation, and licensing records.
- Evaluate whether 3D CNN, VAE, diffusion, implicit-field, or hybrid procedural models match the
  target data and controllability requirements.
- Keep model training and inference in optional packages; the core contract must remain independent
  of PyTorch or other ML frameworks.
- Record model identity, weights digest, inference parameters, seed, and postprocessing in output
  provenance.
- Compare learned results against procedural baselines using declared structural and downstream
  simulation metrics, not screenshots alone.

**Exit criteria:** a versioned model can generate contract-valid volumes reproducibly and shows a
documented advantage over simpler generators on held-out evaluation criteria.

## Cross-Cutting Workstreams

- **Compatibility:** continuously test the currently supported `vbdmat` manifest and pipeline
  versions; fail clearly on unsupported major versions.
- **Verification:** use unit, property-based, golden-file, contract, and end-to-end tests, including
  axis-orientation diagnostics.
- **Reproducibility:** capture source hashes, configuration, software versions, seeds, environment,
  and generator identity in each artifact or its adjacent execution manifest.
- **Usability:** keep CLI help, examples, failure diagnostics, and preview workflows aligned with the
  public Python API.
- **Performance:** benchmark before optimizing and preserve a simple correctness implementation.
- **Documentation:** distinguish file-format requirements, algorithm behavior, parameter guidance,
  and scientific limitations.
- **Governance:** keep experimental modules explicitly unstable and define API/versioning policy
  before third-party generator plugins are accepted.

## Major Risks and Decision Gates

- **Contract drift:** `vbdmat` and this repository could interpret manifests differently. Mitigate
  this with public API reuse, pinned compatibility ranges, and cross-repository contract tests.
- **Axis and transform errors:** a plausible-looking preview can still be physically wrong. Maintain
  asymmetric orientation fixtures and validate transforms at every output boundary.
- **Dependency growth:** mesh, image, VDB, service, and ML stacks can make installation fragile.
  Keep them optional and test the minimal installation independently.
- **Premature package splitting:** too many distributions will slow changes while interfaces are
  unstable. Split only when installation or release boundaries are demonstrated.
- **Large-volume memory use:** dense arrays will eventually be limiting, but sparse or chunked
  designs should follow representative benchmarks rather than assumptions.
- **False scientific claims:** procedural realism and learned visual similarity do not establish
  geological or printing-process validity. State validation scope and metrics explicitly.
- **Service complexity:** authentication, multi-tenancy, distributed scheduling, and public hosting
  are not justified until local batch semantics and actual deployment requirements are stable.

## Immediate Planning Priorities

Detailed implementation planning should begin with:

1. the canonical in-memory material-label model and its relationship to `vbdmat` public APIs;
2. monorepo/workspace packaging, optional-dependency boundaries, and the pinned dependency
   mechanism on the `vbdmat` repository;
3. a contract-test matrix against the pinned `vbdmat` commit, covering both the voxel manifest and
   the optical-mapping document formats;
4. the mesh voxelizer scope and migration of the existing image-stack generator;
5. CLI commands, configuration schema, deterministic output rules, and diagnostic previews;
6. representative small fixtures and benchmark candidates for later phases.

These decisions should be settled before implementing procedural, service, OpenVDB, or ML layers.

## Decision Log

- **Naming correction (2026-07-05, Phase 0 Step 0):** the canonical spelling is `vdbmat` /
  `vdbmat-utils` — matching the actual GitHub repositories, the published Python package name
  (`vdbmat`, per its `pyproject.toml`), and the submodule paths in `pj-voxel3dprint`. The earlier
  decision below declared `vbdmat` canonical, but that spelling contradicts every artifact on
  disk and was itself a typo. All occurrences of `vbdmat` in this document should be read as
  `vdbmat`.
- **Naming (2026-07-05, superseded):** the canonical spelling is `vbdmat` / `vbdmat-utils`
  everywhere — repository names, package names, docs, and devdocs paths. Earlier documents used
  `vdmat-utils` and `vdbmat` inconsistently; those spellings are deprecated.
- **OpenVDB positioning (2026-07-05):** the original discussion started from "generate voxels
  usable in OpenVDB", but in this project the primary handoff is the `vbdmat.voxels` manifest +
  NPY payload. OpenVDB is deliberately demoted to an optional adapter (preview, sparse inspection,
  external interchange) introduced in Phase 5 only where a measured benefit exists. This is a
  conscious narrowing of the initial intent, not an omission.
- **Optical-mapping responsibility (2026-07-05):** with `vbdmat` ADR-009 making the coefficient
  mapping pluggable, `vbdmat-utils` owns emitting the mapping *document* paired with each generated
  palette; it does not own the coefficient values or their scientific validity.
