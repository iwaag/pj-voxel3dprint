# Phase 1 Implementation Plan: Research MVP

## 1. Objective

Phase 1 will turn the Phase 0 technical proofs into a complete, inspectable workflow
for small representative objects. It must answer five practical questions:

1. Can a user provide material placement without writing Python fixture code?
2. Can one simple geometry input be voxelized with explicit units, placement, and
   material identity?
3. Can source material data be converted reproducibly into a validated optical volume
   through one deterministic pipeline?
4. Can the complete run, including configuration and provenance, be inspected,
   validated, repeated, and exported from a CLI?
5. Can small reference objects produce stable baseline artifacts without introducing
   renderer-specific logic into the core pipeline?

Phase 1 is complete when a new user can take either a supported direct material-voxel
input or a supported simple mesh, run one documented command sequence, and obtain:

- a validated canonical material volume;
- a validated canonical RGB optical-property volume;
- an immutable run configuration and provenance manifest;
- Zarr persistence for source and effective fields;
- machine-readable inspection and validation results;
- optional Mitsuba and OpenVDB/Cycles export artifacts;
- reproducible baseline output for a small representative object.

The Phase 1 result remains a research MVP. Optical coefficients are explicitly
provisional and uncalibrated. Successful execution or a plausible render must not be
described as a prediction of a physical print.

## 2. Phase 0 Baseline to Reuse

Phase 1 must extend, not reimplement, the accepted Phase 0 foundation:

- `vbdmat.volume` schema 1.0.0;
- right-handed metre world space, semantic XYZ coordinates, ZYX NumPy storage,
  cell-centred sampling, anisotropic voxel size, and rigid placement;
- immutable `MaterialLabelVolume`, `MaterialMixtureVolume`, and
  `OpticalPropertyVolume` types with strict validation;
- deterministic provisional mapping for transparent, white, black, background, and
  diagnostic materials;
- exact Zarr v3 write/read/inspection/partial-read support;
- renderer-neutral IOR interface derivation;
- Mitsuba 3 and OpenVDB/Blender Cycles proof adapters with capability diagnostics;
- six synthetic fixtures and cross-consumer conformance checks;
- uv-only core environment, locked Mitsuba group, and isolated native
  OpenVDB/Blender Docker environment.

ADR-001 through ADR-005 remain accepted. Phase 1 may amend them only if a supported
real input or end-to-end workflow demonstrates a contradiction. Convenience APIs must
adapt input into the existing canonical contracts rather than weakening those
contracts.

## 3. Scope

### Included

- One direct material-voxel interchange input usable without Python code.
- One simple watertight triangle-mesh input for a single material.
- Explicit input units, voxel size, grid placement, material palette, and background.
- A deterministic dense NumPy reference voxelizer suitable for small objects.
- A versioned pipeline configuration and deterministic orchestration API.
- A run-artifact bundle containing source and effective Zarr assets, configuration,
  provenance, diagnostics, and checksums.
- CLI commands for import, voxelization, conversion, inspection, validation, pipeline
  execution, and export.
- Transparent, white, and black provisional base-material profiles.
- One direct-voxel multi-material reference object and one mesh reference object.
- Analytic and synthetic tests for geometry, transforms, material conservation,
  homogeneous media, boundaries, persistence, and deterministic reruns.
- Small Mitsuba reference scenes and OpenVDB/Cycles smoke outputs.
- Reproducible documentation and a Phase 1 review report.

### Excluded

- Printer-vendor formats without an available representative file and format contract.
- General CAD/B-rep ingestion, arbitrary scene graphs, textures, or per-face materials.
- Production-quality or high-performance mesh voxelization.
- Non-watertight, self-intersecting, degenerate, or ambiguous meshes.
- Droplet spread, interface blur, material bleeding, curing, shrinkage, or other
  print-process models; these belong to Phase 2.
- Fitted optical coefficients, laboratory workflows, or claims of physical accuracy;
  these belong to Phase 3.
- Spectral transport, polarization, fluorescence, or richer phase functions.
- Sparse processing, out-of-core pipeline execution, GPU acceleration, LOD, or
  practical object-scale performance.
- Production renderer plugins, interactive preview, a GUI, or stable public APIs.
- Cross-renderer pixel equality.

## 4. Recommended MVP Inputs

The final choice is made in Step 1 after checking available representative data. The
default plan, used when no printer-specific sample is available, is deliberately
small and explicit.

### Direct material-voxel input

Use a versioned JSON manifest plus one NumPy `.npy` payload:

```text
sample.voxels.json
sample.material_id.npy
```

The manifest declares:

- format name and semantic version;
- relative payload path and SHA-256;
- canonical dtype and dimensions;
- `shape_zyx`;
- `voxel_size_xyz_m` or explicitly declared convenience input unit;
- rigid `local_to_world`;
- ordered material palette, including background ID 0;
- source identity and provenance fields.

The label payload is `uint16[z,y,x]`. Mixture input may be added only if a real Phase 1
sample requires it; otherwise canonical mixture volumes remain supported internally
and through Zarr but are not a new external interchange format.

This format is a transparent research interchange, not a claimed printer-vendor
format. If a real printer/material voxel format is supplied before Step 1 closes,
prefer a narrow reader for that format and retain the manifest format as the canonical
test fixture.

### Simple geometry input

Use a watertight single-solid STL with explicit CLI/config values for:

- STL coordinate unit;
- target voxel size in metres;
- material ID;
- optional rigid placement;
- deterministic inside/outside policy.

STL does not carry trustworthy units or material identity. Missing unit or material
arguments must fail rather than default silently. Phase 1 supports one material per
mesh and rejects unsupported mesh topology clearly.

The reference implementation should prefer a small, well-tested dependency only if it
provides demonstrably safer STL parsing/topology inspection than repository-owned code.
Dependency selection and license/lockfile impact are recorded in Step 1. Voxelization
semantics remain owned and tested by VBDMAT.

## 5. Required Design Decisions

Record these before dependent APIs are treated as complete.

### ADR-006: Phase 1 Inputs and Voxelization

Define:

- the selected direct-voxel format and version;
- the selected mesh format and dependency policy;
- required unit, transform, palette, and provenance metadata;
- payload checksum and path-safety rules;
- voxelization domain construction and padding;
- cell-centre inside/outside semantics;
- boundary/tie-breaking behavior;
- topology checks and supported rejection cases;
- material assignment and background behavior;
- deterministic numeric tolerances.

The ADR must include one worked direct-voxel example and one mesh-to-grid example with
analytically known occupied cells.

### ADR-007: Pipeline Run and Artifact Bundle

Define:

- the versioned pipeline configuration;
- stage order and typed stage inputs/outputs;
- run identifier and deterministic configuration digest;
- source, material, optical, diagnostic, and export artifact locations;
- atomic/failure-safe bundle publication expectations;
- overwrite and resume behavior for Phase 1;
- per-artifact SHA-256 and schema identity;
- provenance chaining from input through mapping and export;
- what constitutes a reproducible rerun;
- forward-compatible manifest behavior.

Recommended bundle layout:

```text
run/
  run.json
  config.json
  source/
  material.zarr/
  optical.zarr/
  diagnostics/
    validation.json
    summary.json
  exports/
    mitsuba/
    openvdb/
```

`material.zarr` and `optical.zarr` use ADR-004 unchanged. `run.json` links assets and
checksums; it does not duplicate or reinterpret canonical metadata.

### ADR-008: CLI Contract and Failure Semantics

Define:

- command names and stable Phase 1 arguments;
- human-readable versus `--json` output;
- exit codes for usage, validation, I/O, conversion, and optional dependency errors;
- stdout/stderr separation;
- overwrite confirmation policy;
- mapping and renderer capability diagnostics;
- guarantees that CLI commands call package APIs rather than implementing a parallel
  pipeline in scripts.

CLI stability is scoped to Phase 1 examples and documentation. It is not yet the
long-term public compatibility promise planned for Phase 7.

## 6. Target Package Layout

```text
src/vbdmat/
  core/                 # existing canonical contracts
  io/
    zarr.py             # existing canonical persistence
    voxel_manifest.py   # direct voxel input
    mesh.py             # selected narrow mesh reader boundary
  voxelize/
    mesh.py             # dense reference voxelization
  optics/               # existing provisional mapping
  pipeline/
    config.py
    artifacts.py
    runner.py
  cli/
    main.py
    errors.py
    output.py
  exporters/            # existing optional adapters
examples/phase1/
tests/
  io/
  voxelize/
  pipeline/
  cli/
  integration/
docs/
  adr/
  phase1/
```

Input parsing may depend on `core`; voxelization may depend on input types and `core`;
pipeline orchestration may depend on core, I/O, optics, and exporter boundaries. Core
must not depend on any Phase 1 module. CLI is a thin outer layer and must not contain
scientific or conversion logic.

## 7. Implementation Steps

Steps are dependency ordered. A step is complete only when its code, tests,
documentation, and generated evidence agree.

### Step 1 — Freeze the Research MVP Workflow and Inputs

Inventory any available representative geometry and material-voxel files. Select the
smallest formats supported by actual data. If no printer-specific sample exists, adopt
the JSON + `.npy` material-label format and watertight single-solid STL baseline in
Section 4.

Create ADR-006, ADR-007, and ADR-008 in proposed status, plus worked examples for:

- a direct multi-material voxel input;
- a unit-explicit watertight mesh;
- a full pipeline configuration;
- the expected run bundle and CLI commands.

Define the Phase 1 representative objects before implementation:

1. **Multi-material window coupon**: transparent matrix, visible white inclusion,
   asymmetric black marker, and background. Its asymmetry must expose axis reversal.
2. **Single-material stepped wedge**: a watertight mesh with analytically predictable
   bounds and thickness progression.

Define maximum Phase 1 reference size, recommended at no more than 128 cells on any
axis and no more than 2 million cells total. This is a safety bound, not a performance
claim.

**Verification**

- every supported input field has one unit, axis, and transform interpretation;
- unsupported printer, mesh, topology, and material cases are listed explicitly;
- reference objects have analytic expected bounds and selected cells;
- the run bundle can link all Phase 1 artifacts without changing schema 1.0.0;
- dependency additions, if any, are justified and locked with uv;
- accepted decisions do not introduce renderer state into core or pipeline stages.

### Step 2 — Implement Direct Material-Voxel Input

Implement a strict reader for the selected direct-voxel format. For the default
manifest format:

- parse UTF-8 JSON with an explicit format version;
- resolve payload paths only beneath the manifest directory;
- reject absolute paths and traversal;
- verify SHA-256 before loading;
- load `.npy` without pickle;
- require exact `uint16`, C-compatible shape, and ZYX dimensions;
- construct existing `GridGeometry`, `MaterialPalette`, `Provenance`, and
  `MaterialLabelVolume` objects;
- preserve source format/version/checksum in provenance;
- provide metadata-only inspection where possible;
- never transpose, cast, infer units, or remap IDs silently.

Add a writer only if it materially improves fixture generation and round-trip testing;
do not turn the input interchange into a competing persistence layer. Zarr remains the
canonical persisted asset.

**Verification**

- valid direct inputs reproduce exact selected cells, geometry, palette, and checksum;
- malformed JSON, incompatible versions, wrong dtype/shape, undeclared IDs, missing
  payloads, checksum mismatch, path traversal, non-finite geometry, and invalid
  transforms fail with field-oriented errors;
- loading does not require Zarr or renderer dependencies;
- repeated reads produce structurally equal canonical volumes and provenance;
- the multi-material coupon imports without Python fixture construction.

### Step 3 — Implement Simple Mesh Input and Dense Voxelization

Implement the selected narrow mesh reader and dense cell-centre voxelizer:

- accept one watertight, consistently oriented triangle solid;
- normalize declared source units to metres;
- apply an explicit rigid placement;
- compute a deterministic grid domain from bounds, voxel size, and documented padding;
- classify voxel centres with the ADR-006 inside/outside rule;
- assign one declared material ID inside and background ID 0 outside;
- return a canonical `MaterialLabelVolume` with source and voxelization provenance;
- return structured diagnostics including triangle count, bounds, occupied cells, and
  rejected topology findings.

The implementation must favor correctness and inspectability over speed. Any library
acceleration must be wrapped behind VBDMAT-owned semantics and tested against analytic
solids. Do not add repair heuristics for broken meshes in Phase 1.

**Verification**

- axis-aligned boxes, translated boxes, and the stepped wedge have analytic occupancy
  or tightly specified boundary expectations;
- millimetre and metre inputs representing the same solid produce equal world-space
  volumes;
- anisotropic voxel size and rigid rotation preserve expected bounds and centres;
- triangle ordering does not change output;
- open, non-manifold, degenerate, empty, self-intersecting when detectable, and
  multi-solid/multi-material inputs fail clearly;
- no renderer dependency is imported;
- peak memory and runtime are recorded for the Phase 1 maximum reference size.

### Step 4 — Build Phase 1 Representative Input Fixtures

Add generated, reviewable Phase 1 inputs rather than opaque large binaries:

- the direct multi-material window coupon;
- the watertight stepped-wedge mesh;
- their input manifests, configuration, and expected summaries;
- selected cells, material counts, bounds, transforms, and source checksums;
- intentionally invalid samples for error-path tests.

The coupon should be large enough to produce a recognizable render but small enough
for fast dense tests. The transparent matrix, white inclusion, and black marker must
not be symmetric across X/Y/Z.

**Verification**

- fixtures regenerate byte-identically or from deterministic source text;
- expected summaries are independent of the implementation under test;
- direct and mesh paths both produce valid canonical material volumes;
- fixture licenses and provenance permit repository use;
- no fixture is called representative of a specific printer unless sourced from that
  printer and documented as such.

### Step 5 — Implement Versioned Pipeline Configuration

Implement immutable Phase 1 pipeline configuration types for:

- input kind and path;
- input units and mesh material assignment when applicable;
- geometry/voxelization settings;
- optical mapping configuration identity and digest;
- requested validation and export stages;
- output path and overwrite policy;
- deterministic execution settings;
- optional renderer configuration references kept outside core stages.

Use canonical JSON serialization and SHA-256 configuration digests. Reject unknown
required semantics and incompatible major versions. Paths should be normalized for
execution but portable relative paths should be retained in the recorded configuration
when possible.

**Verification**

- equivalent configurations serialize and hash identically;
- meaningful setting changes alter the digest;
- invalid combinations fail before any output is created;
- renderer configuration cannot alter canonical material or optical results;
- configuration round-trip preserves every declared setting;
- the configuration contains no implicit current-directory, unit, material, seed, or
  overwrite behavior.

### Step 6 — Implement Pipeline Orchestration and Run Bundles

Implement typed deterministic stages:

```text
load/voxelize -> validate material -> persist material
              -> map optics -> validate optical -> persist optical
              -> summarize -> optional export
```

Implement ADR-007 run bundles with:

- `config.json` containing the exact canonical configuration;
- `material.zarr` and `optical.zarr` written through the existing Zarr API;
- `validation.json` and `summary.json` with stable schemas;
- `run.json` containing stage status, schema versions, provenance links, relative
  artifact paths, sizes, and SHA-256 values;
- failure-safe temporary-directory construction and final publication;
- explicit overwrite behavior;
- deterministic reruns with no generated timestamp in content-addressed comparisons,
  or timestamps isolated from the deterministic scientific payload.

Optional exports must consume the persisted or restored optical volume, not a hidden
in-memory variant.

**Verification**

- both supported input paths complete the same typed stage sequence;
- persisted material and optical assets exactly equal stage outputs;
- provenance links input checksum, voxelization if used, mapping digest, and run
  configuration;
- interrupted or failed runs do not publish a valid-looking partial bundle;
- overwrite never destroys a previous valid run before the replacement validates;
- two identical runs have equal scientific artifacts and declared checksums;
- a renderer export failure does not corrupt canonical artifacts and is attributed to
  the export stage.

### Step 7 — Implement the Phase 1 CLI

Add a `vbdmat` console entry point backed by package APIs. The minimum command set is:

```text
vbdmat import-voxels MANIFEST OUTPUT
vbdmat voxelize MESH OUTPUT --unit ... --voxel-size ... --material-id ...
vbdmat convert MATERIAL_ZARR OUTPUT
vbdmat inspect ASSET [--json]
vbdmat validate ASSET [--json]
vbdmat run CONFIG
vbdmat export {mitsuba|openvdb} OPTICAL_ZARR OUTPUT
```

Exact names may change in ADR-008, but the capabilities may not disappear. Commands
must:

- return documented nonzero exit codes on failure;
- keep machine JSON on stdout and diagnostics on stderr;
- refuse overwrite unless explicitly requested;
- expose schema, geometry, units, basis, provenance, field ranges, material counts,
  and capability diagnostics;
- provide actionable optional-dependency instructions;
- avoid tracebacks for expected user errors while preserving a debug option;
- work from an installed package outside the repository root.

`examples/phase1/` may demonstrate the CLI but must not be the only supported entry
point.

**Verification**

- subprocess tests cover success and each exit-code category;
- JSON output is stable, parseable, and free of human log text;
- paths containing spaces work;
- commands do not overwrite without authorization;
- `--help` documents units, defaults, provisional coefficients, and non-goals;
- an installed wheel can run the full direct-voxel pipeline from another directory;
- CLI results match direct package API results exactly.

### Step 8 — Integrate Export Commands Without Core Leakage

Connect the CLI/pipeline export stage to existing adapters:

- Mitsuba scene preparation and optional rendering through the locked `mitsuba` group;
- OpenVDB export through the isolated native environment;
- Blender Cycles rendering as a documented external/native follow-up command;
- capability reports copied or linked into the run bundle;
- export configuration and adapter versions recorded in `run.json`;
- unsupported/approximated fields surfaced in CLI output.

Do not make rendering mandatory for a successful canonical pipeline run. The default
core environment must complete import, voxelization, conversion, validation, and Zarr
output without any renderer installed.

**Verification**

- export starts from restored `optical.zarr` and preserves the Step 11 conformance
  contracts;
- missing optional dependencies fail only the requested export with actionable text;
- the core environment remains free of Mitsuba, OpenVDB, and Blender imports;
- adapter capability reports are included in run diagnostics;
- all Phase 1 reference objects load in Mitsuba and OpenVDB/Cycles without manual scene
  edits;
- geometry bounds and selected fields agree before renderer conversion.

### Step 9 — Add Analytic and End-to-End Verification

Extend the test strategy beyond the existing Phase 0 fixtures:

- material-count and fraction conservation through input and persistence;
- exact homogeneous-medium mapping;
- translated, rotated, and anisotropic transform cases;
- mesh occupancy and boundary tie cases;
- source-to-material and material-to-optical provenance;
- sharp IOR interface locations;
- repeated run determinism;
- artifact corruption and missing-stage failures;
- CLI/API equivalence;
- cross-consumer field, transform, unit, background, and capability conformance.

Add metamorphic cases where appropriate: triangle reordering, equivalent unit
conversion, input path relocation with unchanged payload, and chunk-independent reads.
Keep stochastic tests seeded; prefer analytic expectations over binary goldens.

**Verification**

- each Phase 1 invariant has a focused failing test;
- tests distinguish input, voxelization, canonical validation, persistence, mapping,
  pipeline, CLI, and adapter failures;
- the default suite requires no optional native dependency;
- optional suites run under the same locked/containerized environments established in
  Phase 0;
- test runtime remains appropriate for normal development on small dense objects.

### Step 10 — Produce Reference Scenes and Baseline Outputs

Create fixed reference scenes for both Phase 1 objects. Mitsuba is the primary visual
baseline because it retains RGB coefficient mapping and derived IOR interfaces more
fully. Cycles remains an interoperability smoke consumer because its selected path
uses scalar coefficient reductions and omits internal IOR interfaces.

For each object record:

- canonical material and optical summaries;
- source/configuration/run digests;
- renderer and adapter versions;
- fixed camera, lighting, seed, resolution, and sample settings;
- output paths and SHA-256 values;
- image dimensions, non-empty/non-flat checks, and field-level conformance;
- known visual differences and unsupported semantics.

The multi-material coupon baseline should visibly expose its white inclusion and
asymmetric black marker under a view where axis reversal is detectable. If the image
cannot discriminate these features, improve the diagnostic scene rather than changing
canonical coefficients per fixture.

**Verification**

- clean regeneration produces the documented deterministic summaries and expected
  hashes where the renderer is byte-stable;
- both objects render without manual scene edits;
- images are non-empty, non-flat, correctly sized, and linked to exact source/config
  digests;
- controlled increases in absorption and scattering retain the expected monotonic
  qualitative response;
- pixel values are not compared across different renderers as physical equivalents;
- baseline limitations are stated next to the artifacts.

### Step 11 — Reproduce the MVP from a Clean Installed Environment

Exercise the documented workflow as a new contributor would:

1. install/sync with uv from the lockfile;
2. build and install the wheel;
3. run the CLI outside the repository root;
4. import the direct-voxel coupon;
5. voxelize the stepped-wedge mesh;
6. execute both complete canonical pipelines;
7. inspect and validate both run bundles;
8. reproduce the Mitsuba reference export/render;
9. reproduce OpenVDB/Cycles export/render in the pinned container;
10. rerun conformance and checksum reports.

Capture commands, runtime, peak memory for the reference objects, versions, artifact
sizes, and expected output summaries. Verify that examples do not depend on editable
installation or repository-relative imports.

**Verification**

- `uv lock --check`, formatting, linting, mypy, and default tests pass;
- the wheel contains all required Phase 1 packages and CLI metadata;
- the installed CLI works from a temporary directory;
- default, Mitsuba, and native container suites pass independently;
- the reference pipeline stays within the Step 1 cell-count safety bound;
- reproduction does not require manual file edits or undocumented environment state.

### Step 12 — Finalize Phase 1 Documentation and Review

Create `docs/phase1-research-mvp-report.md` containing:

- supported inputs and their explicit limitations;
- final ADR-006 through ADR-008 decisions;
- pipeline and artifact-bundle schemas;
- CLI command reference and exit codes;
- representative-object descriptions and provenance;
- analytic, end-to-end, and optional integration results;
- baseline render hashes/screenshots and capability diagnostics;
- runtime, peak-memory, and artifact-size observations;
- known risks and Phase 2 input requirements;
- a recommendation to proceed, revise a named contract, or stop.

Update README with a minimal end-to-end quickstart for both input paths. Add a migration
note only if Phase 1 changes an accepted Phase 0 contract.

The Phase 2 handoff must specify:

- which material volume is the commanded input to process models;
- where intermediate mixture/fill-ratio volumes enter the pipeline;
- required neighborhood/halo semantics;
- mass-conservation expectations;
- printer resolution, layer thickness, orientation, and material-pair metadata still
  missing from Phase 1;
- representative fixtures that expose blur, spread, and mixing effects.

**Verification**

- a new user can reproduce both canonical pipelines from README and linked docs;
- every Phase 1 exit criterion maps to a passing test, artifact, or accepted decision;
- every supported input and CLI command has success and failure documentation;
- provisional coefficients and lack of physical calibration are prominent;
- unresolved Phase 2 prerequisites have an owner, consequence, and recommended action;
- the report makes no scale, printer compatibility, or physical accuracy claim not
  supported by evidence.

## 8. Execution Order and Dependencies

```text
Step 1: input, pipeline, and CLI decisions
   |
   +----------------------+
   |                      |
   v                      v
Step 2: voxel input   Step 3: mesh + voxelization
   |                      |
   +----------+-----------+
              |
              v
Step 4: representative objects
              |
              v
Step 5: pipeline configuration
              |
              v
Step 6: orchestration + run bundle
              |
              v
Step 7: CLI
              |
              v
Step 8: optional exports
              |
              v
Step 9: analytic/end-to-end verification
              |
              v
Step 10: reference scenes and baselines
              |
              v
Step 11: clean-environment reproduction
              |
              v
Step 12: final report and Phase 2 handoff
```

Steps 2 and 3 may proceed in parallel only after Step 1 fixes their contracts. Pipeline
configuration begins after both inputs and their representative fixtures establish the
actual required settings. Renderer work must not begin until canonical end-to-end runs
pass without renderers.

## 9. Test Strategy

### Default core/MVP suite

Runs through `uv run` without Mitsuba, OpenVDB, or Blender:

- direct-input parsing and security tests;
- mesh reader and dense voxelization tests;
- canonical validation and mapping regressions;
- Zarr round-trip, corruption, and partial-read tests;
- pipeline configuration/digest tests;
- run-bundle failure-safety and determinism tests;
- CLI subprocess and installed-wheel tests;
- Phase 0 regression and cross-consumer pure-conversion tests.

### Optional integration suites

- locked Mitsuba scene load, render smoke, qualitative trend, and baseline checks;
- Docker OpenVDB grid readback and transform checks;
- Docker Blender headless load/render smoke checks;
- end-to-end export from restored Phase 1 `optical.zarr` assets.

### Reference evidence

Generated Zarr, VDB, EXR, PNG, and `.blend` files remain reproducible outputs under
`.local/` unless a minimal binary fixture is essential for parsing. Commit source
generators, small textual manifests/meshes, expected summaries, capability diagnostics,
and checksums. Record why any committed binary golden cannot be generated reliably.

## 10. Deliverables

- ADR-006: Phase 1 inputs and voxelization.
- ADR-007: pipeline run and artifact bundle.
- ADR-008: CLI contract and failure semantics.
- Direct material-voxel input reader and documented interchange example.
- Narrow watertight mesh reader and dense reference voxelizer.
- Multi-material coupon and stepped-wedge reference inputs.
- Versioned pipeline configuration, deterministic runner, and failure-safe run bundle.
- Installed `vbdmat` CLI for import, voxelize, convert, inspect, validate, run, and
  export workflows.
- Exact material/optical Zarr assets with complete provenance and checksums.
- Phase 1 analytic and end-to-end test suites.
- Mitsuba reference scenes and OpenVDB/Cycles smoke outputs.
- Clean-environment reproduction evidence.
- `docs/phase1-research-mvp-report.md` and README quickstarts.
- Explicit Phase 2 process-model handoff.

## 11. Definition of Done

Phase 1 is done only when all of the following are true:

- A user can ingest a direct material-voxel input without writing Python.
- A user can voxelize one supported watertight single-material mesh with explicit
  units, voxel size, placement, and material ID.
- Both inputs produce validated schema 1.0.0 material volumes.
- The same deterministic pipeline converts both material volumes into validated RGB
  optical volumes using versioned provisional coefficients.
- Source and effective fields, configuration, schema, provenance, diagnostics, and
  checksums are persisted in a failure-safe run bundle.
- CLI commands can run, inspect, validate, and export the workflow from an installed
  package outside the repository.
- Analytic tests cover material conservation, transforms, homogeneous fields,
  boundaries, persistence, and deterministic reruns.
- The multi-material coupon and stepped wedge have reproducible reference outputs.
- Optional renderers consume restored canonical optical assets; renderer-specific
  state does not enter core or canonical pipeline stages.
- Every approximation and unsupported renderer semantic remains machine-readable.
- The default environment and tests require no renderer or native DCC dependency.
- Documentation distinguishes technical reproducibility from physical prediction.
- Phase 2 can add process-model stages without changing canonical schema semantics or
  bypassing provenance.

## 12. Stop Conditions and Decision Gates

Pause broad implementation and revisit the named decision if any of these occurs:

- no available input can provide unambiguous units, axes, palette, or placement;
- a proposed printer format lacks a stable contract or representative test file;
- mesh voxelization cannot define deterministic boundary behavior for supported
  watertight inputs;
- mesh dependencies introduce unacceptable licensing, ABI, or core-install costs;
- the run bundle requires reinterpretation of schema 1.0.0 rather than composition of
  existing assets;
- a CLI convenience path would silently infer units, transpose arrays, cast payloads,
  remap material IDs, or normalize invalid input;
- deterministic reruns cannot distinguish scientific payloads from timestamps or
  environment noise;
- optional renderer failures prevent the canonical pipeline from completing;
- the representative object exceeds dense Phase 1 memory/runtime bounds;
- a requested feature is actually process modeling, calibration, scale optimization,
  or production interoperability and would blur the Phase boundary;
- reference images cannot expose gross orientation/material errors even though field
  checks pass.

These are research MVP contract findings. Resolve them in ADR-006, ADR-007, or ADR-008
instead of adding fixture-specific exceptions.

## 13. Estimated Work Distribution

Relative Phase 1 implementation effort, excluding Phase 0 work already complete:

| Workstream | Approximate share |
| --- | ---: |
| Input contracts and direct voxel reader | 15% |
| Mesh ingestion and dense voxelization | 25% |
| Pipeline configuration, bundles, and provenance | 20% |
| CLI and installed-package workflows | 15% |
| Verification and failure handling | 15% |
| Reference renders, documentation, and review | 10% |

Mesh topology/voxelization is the largest uncertainty. If an actual printer format or
complex mesh support is pulled into Phase 1, re-estimate before implementation rather
than absorbing it silently. Calibration and print-process fitting are not included in
this estimate.
