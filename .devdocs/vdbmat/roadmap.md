# VBDMAT Long-Term Roadmap

## Vision

VBDMAT will become a renderer-independent preprocessing backend for predicting the appearance of voxel-based material-jetting prints made from transparent and opaque photopolymers. Its primary job is to transform intended material placement into a calibrated three-dimensional optical-property volume. Rendering is a downstream concern and should remain replaceable.

The target pipeline is:

```text
CAD, mesh, slice data, or printer voxels
                    |
                    v
          material voxel volume
                    |
                    v
             print-process model
                    |
                    v
       effective optical-property volume
                    |
                    v
        renderer-specific export adapters
```

The project should initially be one repository and one installable Python package, split internally into modules with explicit boundaries. Repository or package separation should happen only after interfaces and dependency boundaries have proven stable.

## Product Boundaries

VBDMAT owns:

- coordinate systems, physical units, voxel geometry, metadata, and volume schemas;
- ingestion and voxelization of geometry and printer-oriented material data;
- simulation of printing effects such as material mixing, interface blur, and droplet spread;
- conversion from material composition to effective optical properties;
- scalable volume processing and renderer-neutral persistence;
- calibration workflows, datasets, parameter estimation, and validation;
- export adapters for downstream visualization and research tools.

VBDMAT does not initially own:

- a production renderer or interactive DCC application;
- a complete fluid, curing, or structural simulation of the printing process;
- printer control, slicing, or machine firmware;
- universal support for every CAD, printer, material, or renderer format.

## Architectural Principles

1. **Optical properties are the canonical output.** Material identifiers are inputs, not the final interchange representation. The core output describes absorption (`sigma_a`), scattering (`sigma_s`), anisotropy (`g`), refractive index (`ior`), and any required surface or boundary properties.
2. **Physical meaning must be explicit.** Every field carries defined units, wavelength or color-space semantics, voxel dimensions, axis order, transforms, and provenance.
3. **Dense first, sparse later.** A small, inspectable NumPy implementation should establish correctness before optimization with chunking, sparse volumes, GPU processing, or native code.
4. **Process models are composable and versioned.** Mixing, bleeding, curing, shrinkage, and interface effects should be independently replaceable and reproducible.
5. **Calibration is a first-class subsystem.** Model parameters, test-piece definitions, measurements, fitting procedures, uncertainties, and validation results belong to the product rather than to ad hoc scripts.
6. **Heavy integrations remain optional.** OpenVDB, USD, NanoVDB, Blender, and renderer SDK dependencies must not enter the lightweight core.
7. **Performance work follows measurement.** Representative datasets and benchmarks should determine whether Numba, CuPy, C++, or Rust is justified.

## Proposed Module Boundaries

The initial package should evolve around these logical modules:

```text
vbdmat/
  core/             # volume schemas, coordinates, units, metadata, validation
  io/               # mesh, printer data, Zarr, and optional external formats
  voxelize/         # geometry and material placement to voxel volumes
  process_model/    # mixing, spread, blur, curing, shrinkage approximations
  optics/           # material composition to effective optical properties
  calibration/      # measurements, fitting, uncertainty, validation
  pipeline/          # configuration and reproducible orchestration
  cli/               # stable command-line workflows
  exporters/         # optional OpenVDB, USD, NanoVDB, and renderer adapters
  examples/
  tests/
```

Dependencies should generally flow toward `core`; `core` must not depend on exporters, renderers, laboratory tooling, or GPU frameworks.

## Roadmap

The phases below are capability-driven rather than date-driven. Each phase should start only when the preceding exit criteria are met.

### Phase 0 — Foundations and Technical Proofs

**Goal:** remove the highest-risk ambiguities before committing to a broad implementation.

- Define the supported voxel coordinate convention, physical units, transforms, axis order, and anisotropic voxel sizes.
- Specify a versioned schema for material volumes, material mixtures, and optical-property volumes.
- Decide how interfaces and refractive-index discontinuities are represented; do not assume that a single scalar volume is sufficient without a renderer proof.
- Define the initial RGB approximation and a compatible path to wavelength-dependent fields.
- Prototype Zarr round trips and inspect chunking, compression, metadata, and partial reads.
- Build minimal export experiments against at least two materially different downstream consumers, preferably Mitsuba 3 and OpenVDB/Cycles, to test whether the intermediate representation is genuinely renderer-neutral.
- Establish project packaging, automated tests, linting, type checking, documentation, and small canonical fixtures.

**Exit criteria:** the schemas are documented and versioned; a tiny synthetic material volume can be converted to optical fields, persisted without semantic loss, and consumed by two proof-of-concept adapters.

### Phase 1 — Research MVP

**Goal:** establish a complete, correct, inspectable pipeline for small samples.

- Implement dense NumPy volumes and deterministic pipeline stages.
- Support one simple geometry input and direct printer/material voxel input; prioritize formats backed by real test data.
- Support transparent, white, and black base materials with fixed, explicitly provisional optical coefficients.
- Convert material IDs or fill ratios into RGB optical fields: `sigma_a`, `sigma_s`, `g`, and `ior`.
- Persist source data, effective fields, configuration, schema version, and provenance in Zarr.
- Provide a CLI for conversion, inspection, validation, and export.
- Add analytic and synthetic tests for conservation of material fractions, transforms, boundaries, and homogeneous media.
- Produce small reference scenes and baseline outputs for regression testing.

**Exit criteria:** a user can reproducibly convert a small representative object from supported input into a validated optical-property volume, with no renderer-specific logic in the core pipeline.

### Phase 1-side1 — Material & Input Contract Extensibility

**Goal:** before deepening print-process fidelity, fix the input boundary so that geometry/material
generation and material coefficient data can evolve independently of the core, without weakening
reproducibility. This is a side mission inserted at the Phase 1 exit point, not a fidelity phase.

- Restrict the core pipeline's supported input to the raw voxel manifest (`vbdmat.voxels` + its
  checksummed `.npy` payload) as the single stable contract; treat it as the narrow interface that
  any external generator must produce.
- Remove or relocate STL/mesh voxelization (`input.kind: "mesh"`) out of the core pipeline into an
  external, independently versioned tool that emits a conforming voxel manifest; the core stops
  owning geometry-to-voxel conversion.
- Define an input-generator contract so alternative generation methods — mesh voxelization, layered
  3D-image stacking or morphing, generative natural-formation (e.g. mineral growth) models — can be
  built and evolved externally, as long as they emit a valid voxel manifest.
- Make the material coefficient mapping (currently the single hardcoded
  `phase0-provisional-materials-v1` table) pluggable/externalizable, so material data can be
  supplied or swapped without code changes to `optics/`.
- Formalize the distinction between the simulation-side material name/palette contract (used
  between external voxel generators and the core's optical mapping) and any future physical printer
  material catalog (`external_id`-style identifiers), so the two are never silently conflated.

**Exit criteria:** the core pipeline accepts only the voxel manifest as input; mesh voxelization
exists (if at all) as a separate example/tool built against that same manifest contract; the
material coefficient mapping is swappable without touching core code; at least one external
generator other than mesh voxelization demonstrates the contract end-to-end.

### Phase 2 — Print-Process Modeling

**Goal:** model the fact that commanded material voxels are not identical to cured optical voxels.

- Introduce a composable process-model API with versioned parameters.
- Add empirically useful models in increasing order of complexity: interface blur, anisotropic droplet spread, local material mixing, and optional shrinkage or curing adjustments.
- Represent fill ratios and preserve material mass where the selected model requires it.
- Make printer resolution, layer thickness, orientation, and material pairing explicit inputs.
- Add parameter sweeps, sensitivity analysis, and diagnostic intermediate volumes.
- Avoid claiming predictive accuracy until the models are fitted and independently validated.

**Exit criteria:** process models can be enabled, configured, compared, and tested independently; their effects are measurable on canonical samples and traceable in output metadata.

### Phase 3 — Calibration and Experimental Validation

**Goal:** turn qualitative approximation into a measured prediction system.

- Define calibration test pieces spanning thickness, material fraction, interface orientation, feature size, and transparent/opaque combinations.
- Establish measurement protocols for transmittance, reflectance, haze or scattering, color, and internal-feature visibility as available.
- Store raw measurements, environmental conditions, printer/material batch identity, preprocessing, and uncertainty alongside fitted parameters.
- Implement estimation of absorption, scattering, anisotropy, refractive index, and process-model parameters, beginning with robust simple fits.
- Maintain a versioned material library scoped to printer, material batch, print mode, and measurement method.
- Separate fitting datasets from held-out validation artifacts.
- Define quantitative acceptance metrics and report confidence or error bounds, not only rendered visual comparisons.

**Exit criteria:** at least one printer/material configuration has a reproducible calibration package and demonstrates improved metrics on held-out physical samples over the fixed-coefficient baseline.

### Phase 4 — Scale and Performance

**Goal:** process practical object sizes without weakening reproducibility or correctness.

- Create representative memory, throughput, and accuracy benchmarks before choosing optimization technology.
- Introduce chunked and out-of-core execution using Zarr as the working format.
- Add sparse-region detection and OpenVDB export where sparsity provides a measured benefit.
- Parallelize stages with well-defined halo requirements for neighborhood operations.
- Add multiresolution volumes and level-of-detail policies with quantified approximation error.
- Accelerate demonstrated hotspots with Numba or CuPy; consider C++ or Rust only for stable, performance-critical kernels.
- Investigate NanoVDB only when GPU-native consumers or interactive workloads become concrete requirements.

**Exit criteria:** agreed representative objects fit within documented hardware budgets and meet throughput targets, while small-volume results remain numerically consistent with the reference implementation.

### Phase 5 — Stable Interoperability

**Goal:** make calibrated volumes usable across rendering and DCC ecosystems without coupling the core to them.

- Harden OpenVDB export, including field naming, transforms, units, grids, and metadata conventions.
- Add USD/UsdVol packaging that references volume assets and preserves scene transforms and material metadata.
- Maintain optional adapters for prioritized consumers such as Mitsuba 3 and Blender Cycles.
- Add adapter conformance fixtures that expose differences in phase functions, spectral assumptions, interpolation, IOR boundaries, and volume/surface composition.
- Document which physical fields each consumer can represent faithfully and which require approximations.
- Define an exporter plugin contract so downstream integrations can evolve independently.

**Exit criteria:** multiple supported consumers render the same calibrated asset through documented, tested mappings, and unsupported semantics fail clearly rather than being silently discarded.

### Phase 6 — Higher-Fidelity Prediction

**Goal:** improve fidelity where experiments show that simpler models are insufficient.

- Extend RGB fields to wavelength-dependent absorption, scattering, and refractive index.
- Evaluate richer phase functions, spatially varying anisotropy, polarization, and fluorescence only when supported by measurement evidence and target renderers.
- Add surface roughness and print-surface models distinct from bulk volume properties.
- Refine curing, inter-layer, and material-boundary models using microscopy or other process observations.
- Introduce inverse estimation and automated experiment design for efficient calibration.
- Track uncertainty through process modeling, optical mapping, and validation.

**Exit criteria:** each added model produces a statistically and practically meaningful improvement on held-out samples relative to its complexity and runtime cost.

### Phase 7 — Productization and Ecosystem

**Goal:** make the system dependable for users beyond the original research workflow.

- Stabilize public Python and CLI APIs with migration policies for schemas and material libraries.
- Provide reproducible example projects, tutorials, diagnostics, and compatibility documentation.
- Add artifact caching, resumable pipelines, structured logs, and execution manifests.
- Establish release, security, data-governance, and long-term file-migration practices.
- Consider a service, desktop interface, or DCC plugin only after command-line workflows and user needs are stable.
- Split packages or repositories only where release cadence, ownership, licensing, or dependency isolation provides a demonstrated benefit.

**Exit criteria:** independent users can install the project, process a supported dataset, select a calibrated material profile, diagnose failures, and reproduce published validation results.

## Repository Evolution

The expected evolution is:

1. **Early research:** one repository, one Python distribution, multiple internal modules.
2. **Stable interfaces:** one repository with optional distributions for dependency-heavy I/O, exporters, and laboratory tooling if installation or release management demands it.
3. **Mature ecosystem:** separate repositories only for components with genuinely independent ownership or lifecycle, such as a Blender plugin, a native NanoVDB exporter, or laboratory acquisition software.

Core schemas and compatibility fixtures should remain centrally governed even if implementations later move out of the repository.

## Cross-Cutting Workstreams

These activities continue throughout all phases:

- **Verification:** unit tests, property-based tests, analytic cases, regression fixtures, and cross-adapter comparisons.
- **Reproducibility:** versioned schemas, immutable configurations, seeded stochastic operations, dependency capture, and data provenance.
- **Documentation:** physical definitions, assumptions, limitations, supported combinations, and worked examples.
- **Data management:** small synthetic fixtures in the repository; large measurements and generated volumes in versioned external storage with manifests and checksums.
- **Performance:** benchmark before optimization and retain the simple implementation as a correctness oracle.
- **Scientific validity:** distinguish fitted results from held-out validation and publish failure cases and uncertainty.

## Major Risks and Decision Gates

- **Optical representation mismatch:** heterogeneous bulk fields may not fully describe sharp material interfaces. Resolve this with early multi-renderer proofs and explicit boundary semantics.
- **Parameter identifiability:** several combinations of `sigma_a`, `sigma_s`, and `g` can produce similar measurements. Calibration must use complementary measurements and report uncertainty.
- **Printer variability:** coefficients may change by printer, batch, orientation, cure settings, and aging. Material profiles must encode their domain of validity.
- **Scale explosion:** 20–50 micrometre voxels create very large volumes. Chunking, sparsity, and multiresolution processing are essential, but only after the reference pipeline is correct.
- **Premature ecosystem coupling:** renderer SDKs and native libraries can dominate packaging. Keep adapters optional and enforce dependency direction.
- **False precision:** increasingly complex process models are not automatically more predictive. Promote a model only after held-out validation demonstrates value.

## Near-Term Planning Priorities

Detailed implementation planning should begin with Phase 0. The first design documents should cover:

1. canonical volume schemas and physical conventions;
2. the minimum supported input and a representative physical test artifact;
3. material and calibration metadata models;
4. Zarr layout and schema-versioning strategy;
5. two narrow renderer-adapter feasibility tests;
6. validation metrics and the first experimental measurement plan.

These decisions establish the contracts on which every later phase depends and should be settled before broad format support or performance optimization begins.
