# Phase 0 Implementation Plan: Foundations and Technical Proofs

## 1. Objective

Phase 0 will establish the smallest technically credible foundation for VBDMAT before the research MVP is built. It must answer four questions:

1. Can material placement and optical properties be represented without ambiguity?
2. Can those volumes be saved to and partially read from Zarr without losing semantics?
3. Can the same canonical optical volume be mapped to two substantially different rendering consumers?
4. Can future implementation proceed behind stable module and schema boundaries?

This phase is complete when a tiny synthetic material volume can be converted into optical fields, validated, persisted, restored, and consumed by both a Mitsuba 3 proof and an OpenVDB/Cycles proof.

Phase 0 is a foundation and feasibility phase. It does not attempt calibrated appearance prediction, production rendering quality, large-volume performance, general CAD support, or a stable public API.

## 2. Scope

### Included

- Python package and development-tool setup.
- Canonical definitions for coordinates, units, transforms, axis order, channels, and metadata.
- Versioned schemas for material-label, material-mixture, and optical-property volumes.
- A minimal deterministic material-to-optical conversion used only to exercise the contracts.
- Small synthetic fixtures with analytically inspectable values.
- Zarr write, read, validation, and partial-read proofs.
- A Mitsuba 3 consumer proof.
- An OpenVDB export plus Blender Cycles consumer proof.
- Automated unit, round-trip, and integration tests where the external dependencies permit them.
- Architecture decision records and a final feasibility report.

### Excluded

- Production-quality voxelization of CAD or meshes.
- Real printer input formats.
- Droplet spread, material bleeding, curing, shrinkage, or other print-process models.
- Material calibration or laboratory measurement workflows.
- Spectral rendering beyond reserving a compatible schema extension path.
- GPU acceleration, sparse processing, LOD, and large-volume optimization.
- Production renderer plugins or a graphical interface.

## 3. Technical Baseline

Use a single repository and one Python distribution with a `src` layout. The project is managed exclusively with uv for Python installation, virtual environments, dependency resolution, locking, and command execution.

```text
vbdmat/
  .python-version
  pyproject.toml
  uv.lock
  src/vbdmat/
    __init__.py
    core/
      axes.py
      transforms.py
      metadata.py
      volumes.py
      validation.py
    optics/
      mapping.py
    io/
      zarr.py
    exporters/
      mitsuba.py
      openvdb.py
  tests/
    unit/
    integration/
    fixtures/
  examples/phase0/
  docs/
    adr/
    schemas/
    phase0-feasibility-report.md
```

Initial implementation stack:

- uv as the only supported Python project and environment manager;
- Python 3.11 or newer;
- NumPy for the reference dense-array implementation;
- Zarr for persistent chunked arrays;
- pytest for tests;
- Ruff for formatting and linting;
- mypy for static type checks;
- standard-library dataclasses and enums for core value objects unless an ADR demonstrates a need for another runtime schema library.

`pyproject.toml` is the source of project and dependency declarations, and the generated `uv.lock` is committed. Core runtime packages belong in `project.dependencies`; development and proof-only packages belong in named `dependency-groups` such as `dev`, `mitsuba`, and `openvdb`. Dependencies are changed with `uv add` and `uv remove`, not by maintaining a separate requirements file. Routine commands run through `uv run`. Local setup uses `uv sync`, while CI and documented reproduction use `uv sync --locked` so an outdated lockfile fails rather than being rewritten.

Mitsuba, OpenVDB Python bindings, and Blender are optional integration dependencies. They must be isolated from the default core environment and tested in separate uv groups, environments, or CI jobs. Blender itself may remain an external system dependency because of its embedded runtime, but repository-owned Python scripts and tools still run through uv. Exact dependency versions will be captured by `uv.lock` when implementation starts, recorded in the feasibility report, and not imported by `vbdmat.core`.

## 4. Required Design Decisions

Each decision must be recorded in `docs/adr/` before dependent code is treated as complete.

### ADR-001: Coordinates, Axes, and Units

Define:

- a right-handed world coordinate system;
- the meaning and unit of voxel size, origin, and world transform;
- the relationship between semantic axes `(x, y, z)` and NumPy storage indices;
- voxel-center versus voxel-corner sampling;
- support for anisotropic voxel sizes;
- array bounds and index-to-world/world-to-index behavior;
- length units, initially SI metres in canonical metadata even if convenience inputs use millimetres.

The recommended storage convention to test is scalar arrays shaped `(z, y, x)` with semantic mapping made explicit by metadata. The ADR may reject this convention, but no implicit convention is allowed.

### ADR-002: Canonical Volume Schemas

Define three logical assets:

1. **Material label volume**: one discrete material identifier per voxel.
2. **Material mixture volume**: fractions for a declared, ordered material palette.
3. **Optical property volume**: `sigma_a`, `sigma_s`, `g`, and `ior` fields plus spatial and color metadata.

The ADR must specify:

- array shapes and channel ordering;
- required and optional fields;
- numeric types and valid ranges;
- behavior for empty/background voxels;
- mixture normalization tolerance;
- coefficient units;
- RGB color-space semantics for Phase 0;
- schema name and semantic version;
- provenance, generator version, and material-palette metadata;
- rules for adding future spectral sample dimensions without reinterpreting existing data.

### ADR-003: Boundaries and Refractive Index

Determine whether canonical voxel fields alone can represent the boundary behavior required by target renderers. Compare at least:

- cell-centered spatially varying `ior`;
- an explicitly derived boundary/interface asset;
- region or material boundary meshes combined with volume fields.

The decision must distinguish canonical data from renderer-specific approximations. If neither renderer can consume spatially varying IOR faithfully, preserve it in the canonical schema and document the adapter limitation rather than silently dropping it.

### ADR-004: Zarr Layout and Compatibility

Define:

- group and array paths;
- metadata placement;
- chunk-shape selection for Phase 0 fixtures;
- compression choice;
- atomic or failure-safe write expectations;
- schema-version checks;
- forward-compatibility behavior for unknown optional fields;
- rejection behavior for incompatible major schema versions.

### ADR-005: Exporter Boundary

Define a narrow adapter contract that accepts a validated canonical optical volume and produces either an external artifact or a renderer scene description. Exporters may approximate fields, but must return or write a machine-readable capability/diagnostic report listing represented, transformed, approximated, and unsupported properties.

## 5. Implementation Steps

Steps are ordered by dependency. A step is complete only when its listed verification passes and its artifacts are committed together.

### Step 1 — Bootstrap the Project

Create:

- the project with `uv init --package` or an equivalent explicit `pyproject.toml` setup;
- `.python-version` with the selected Phase 0 interpreter baseline;
- `pyproject.toml` with core dependencies and `dev`, `mitsuba`, and `openvdb` dependency groups;
- a committed `uv.lock` produced by `uv lock`;
- the `src/vbdmat` package layout;
- pytest, Ruff, and mypy configuration;
- a basic CI workflow that installs a pinned uv release, runs `uv sync --locked`, and executes checks with `uv run`;
- `README.md` uv-based development commands and supported Python versions.

Document these baseline commands:

```bash
uv sync
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
```

Renderer proof environments use explicit groups, for example `uv sync --locked --group mitsuba`, rather than becoming part of the default core environment. If renderer groups cannot be resolved together, declare and document that conflict in uv configuration instead of introducing another environment manager.

Add a smoke test that imports `vbdmat` from an installed package rather than from repository-path side effects.

**Verification**

- a clean environment can install uv, install the selected Python with `uv python install`, and synchronize the core package from `uv.lock`;
- `uv lock --check` confirms that `pyproject.toml` and `uv.lock` agree;
- formatting, linting, typing, and tests run only through the documented `uv run` commands;
- importing the core does not import Zarr, Mitsuba, Blender, or OpenVDB bindings unnecessarily.

### Step 2 — Write the Coordinate and Schema ADRs

Complete ADR-001 and ADR-002 before implementing volume classes. Include worked examples for:

- a `4 x 3 x 2` anisotropic volume;
- conversion of index `(z, y, x)` to a world-space voxel center;
- an RGB optical coefficient at one voxel;
- a two-material mixture and its normalization rule.

Add JSON-like schema examples under `docs/schemas/` even if the runtime representation is Python plus NumPy rather than JSON.

**Verification**

- every dimension, unit, axis, and transform in each example has exactly one interpretation;
- the future spectral extension can add wavelength samples without changing Phase 0 RGB meaning;
- schema invariants can be translated directly into validation code.

### Step 3 — Implement Core Spatial Types

Implement immutable or mutation-controlled value objects for:

- `GridGeometry`: shape, voxel size, origin, axis mapping, and transform;
- `ColorBasis`: Phase 0 RGB semantics and future spectral metadata hooks;
- `MaterialDefinition` and `MaterialPalette`;
- schema/version and provenance metadata.

Implement index-to-world and world-to-index helpers. Reject singular transforms, non-positive voxel dimensions, unsupported axis metadata, and shape mismatches early.

**Verification**

- unit tests cover isotropic and anisotropic grids, translated grids, boundary indices, and invalid inputs;
- index-to-world-to-index round trips satisfy a documented numerical tolerance;
- core metadata objects do not depend on storage or renderer modules.

### Step 4 — Implement Canonical Volume Types and Validation

Implement lightweight wrappers around NumPy arrays:

- `MaterialLabelVolume`;
- `MaterialMixtureVolume`;
- `OpticalPropertyVolume`.

Keep coefficient arrays separate unless ADR-002 provides a measured reason to interleave them. Implement validation for:

- geometry/array shape consistency;
- finite numeric values;
- non-negative `sigma_a` and `sigma_s`;
- bounded `g` according to the selected phase-function contract;
- physically admissible positive `ior`;
- valid material IDs;
- mixture fractions and normalization;
- declared RGB basis and coefficient units.

Expose explicit validation errors containing field paths and offending indices or summary counts.

**Verification**

- valid canonical fixtures pass;
- one focused test exists for each invalid invariant;
- validation never silently clamps or normalizes input unless the API explicitly requests a repair operation.

### Step 5 — Build Deterministic Synthetic Fixtures

Create small generated fixtures rather than storing opaque binary samples:

- homogeneous transparent volume;
- homogeneous scattering/white volume;
- two-region transparent/opaque interface;
- layered material slab;
- two-material linear mixture ramp;
- anisotropic-voxel checker or axis marker that reveals transposition errors.

Each generator must define expected material counts, selected voxel values, bounds, and world-space locations. Keep fixture dimensions small enough for code review and exact comparisons.

**Verification**

- generation is deterministic;
- expected summaries and selected cells are asserted in tests;
- at least one fixture fails visibly if any two spatial axes are swapped.

### Step 6 — Implement the Minimal Optical Mapping

Implement a deliberately simple reference mapping from palette entries or mixture fractions to optical fields. It exists to prove the data flow, not to claim physical accuracy.

Requirements:

- palette entries provide provisional RGB `sigma_a`, RGB `sigma_s`, scalar or explicitly defined RGB `g`, and `ior`;
- label mapping performs direct lookup;
- mixture mapping uses a documented Phase 0 rule for every property;
- output preserves geometry, schema version, configuration, and provenance;
- mapping is deterministic and side-effect free.

Record the mixing assumptions and known physical limitations. Do not label the coefficients as calibrated.

**Verification**

- pure mixture endpoints equal their base materials;
- synthetic mixture values match hand-calculated expected values;
- invalid palette references and fractions fail before conversion;
- repeated conversion produces identical arrays and metadata apart from explicitly variable timestamps, if any.

### Step 7 — Implement the Zarr Prototype

Complete ADR-004, then implement:

- `write_volume()` for the three canonical volume kinds;
- `read_volume()` with schema and invariant validation;
- metadata-only inspection;
- explicit spatial-region reads for optical fields;
- a small command or example that prints asset type, geometry, fields, chunks, units, and schema version.

Writers must not expose partially written output as a valid asset. The Phase 0 implementation may use a temporary sibling path plus final rename where the target filesystem permits it; unsupported guarantees must be documented.

**Verification**

- exact round trips for labels and metadata;
- tolerance-based round trips for floating-point fields if a selected codec is not bit-exact;
- partial reads return the requested spatial region and correct world metadata;
- incompatible schema major versions and missing required attributes fail clearly;
- corruption tests cover a missing array, wrong shape, and invalid units;
- a simple report records compressed size and partial-read behavior for all fixtures.

### Step 8 — Resolve Boundary and IOR Semantics

Use the interface and layered fixtures to complete ADR-003. For each candidate representation:

- identify which data are canonical and which are derived;
- test interpolation behavior at material boundaries;
- test whether `ior` is supported as a spatial field, region property, or only a surface transition in each target consumer;
- document how background/air and object boundaries are formed;
- define diagnostics for any unsupported mapping.

Implement only the minimum derived boundary representation required by the two consumer proofs.

**Verification**

- a written decision compares the candidates and selects one canonical contract;
- both adapters have an explicit, testable policy for `ior` and interfaces;
- no canonical field is silently omitted by an exporter.

### Step 9 — Build the Mitsuba 3 Consumer Proof

Implement an optional adapter or example that:

- accepts a validated `OpticalPropertyVolume`;
- maps supported absorption, scattering, phase, and boundary data into a minimal Mitsuba scene;
- uses a fixed camera, lighting, sampling configuration, and random seed where supported;
- emits a capability/diagnostic report;
- renders the homogeneous, interface, layered, and axis-marker fixtures.

The proof may generate intermediate files if direct NumPy ingestion is unsuitable. Any renderer-required normalization or coefficient transformation must be explicit and tested independently.

**Verification**

- all required fixtures load and render without manual scene edits;
- the axis-marker fixture confirms orientation and world scale;
- increasing absorption or scattering creates the expected monotonic qualitative response in a controlled scene;
- unsupported fields appear in diagnostics;
- core tests still pass when Mitsuba is not installed.

### Step 10 — Build the OpenVDB/Cycles Consumer Proof

Implement an optional OpenVDB exporter and a minimal Blender scene script that:

- exports one named grid per required optical or derived field;
- preserves index-to-world transformation and units;
- constructs the necessary Cycles volume/surface nodes from documented mappings;
- uses a fixed camera, lighting, and render configuration;
- emits the same capability/diagnostic structure as the Mitsuba proof;
- renders the same fixture set.

Because Cycles may not expose a one-to-one mapping for all canonical coefficients, conversions must be isolated in this adapter and labeled as approximations.

**Verification**

- OpenVDB grid names, types, dimensions, transforms, and selected values are inspected automatically where bindings allow;
- Blender loads and renders exported assets without manual edits;
- orientation and scale match the Mitsuba proof;
- approximation and unsupported-field diagnostics are complete;
- core installation and tests do not require Blender or OpenVDB.

### Step 11 — Add Cross-Consumer Conformance Checks

Do not compare final pixel values as if the renderers were physically identical. Compare the shared contracts first:

- volume bounds and transforms;
- field values before renderer-specific conversion;
- material regions and boundary locations;
- background treatment;
- coefficient units and conversion factors;
- adapter capability reports.

Add lightweight image-level sanity checks only for gross regressions, such as empty output, transposed geometry, missing layers, or reversed absorption trends.

**Verification**

- a conformance command processes every canonical fixture through both adapters;
- failures identify whether the mismatch originates in canonical data, serialization, or adapter conversion;
- expected adapter differences are documented rather than hidden by fixture-specific adjustments.

### Step 12 — Finalize Documentation and Phase Review

Create `docs/phase0-feasibility-report.md` containing:

- the final canonical schemas and ADR outcomes;
- tested environment and pinned integration dependency versions;
- Zarr layout, round-trip results, size observations, and known limitations;
- a renderer capability matrix for every canonical field;
- screenshots or checksums of reference proof outputs;
- unresolved risks and proposed Phase 1 work;
- any roadmap changes justified by the proofs.

Update the user-facing README with the architecture, explicit non-goals, fixture demo, and reproducible commands.

**Verification**

- a new contributor can reproduce the core pipeline and both consumer proofs from the documentation;
- every Phase 0 exit criterion maps to a passing test, generated artifact, or recorded decision;
- unresolved blockers have an owner, consequence, and recommended decision for Phase 1.

## 6. Execution Order and Dependencies

```text
Step 1: project bootstrap
   |
   v
Step 2: coordinate and schema ADRs
   |
   v
Steps 3-4: core types and validation
   |
   +------------------+
   |                  |
   v                  v
Step 5: fixtures   Step 7: Zarr framework
   |                  ^
   v                  |
Step 6: mapping ------+
   |
   v
Step 8: boundary/IOR decision
   |
   +------------------+
   |                  |
   v                  v
Step 9: Mitsuba   Step 10: OpenVDB/Cycles
   |                  |
   +--------+---------+
            |
            v
Step 11: conformance checks
            |
            v
Step 12: feasibility report and review
```

The two renderer proofs may proceed in parallel only after Steps 3–8 define validated inputs and boundary policy. Renderer-specific discoveries that invalidate a canonical assumption must return to the relevant ADR rather than being patched locally in both adapters.

## 7. Test Strategy

### Core test suite

Runs with `uv run` in every supported Python environment without renderer dependencies:

- metadata and geometry unit tests;
- schema invariant tests;
- coordinate transform property tests;
- deterministic fixture tests;
- optical mapping tests;
- Zarr round-trip and corruption tests.

### Optional integration suites

Run in dedicated uv dependency groups or uv-managed environments:

- Mitsuba adapter loading and render smoke tests;
- OpenVDB grid inspection tests;
- Blender headless load and render smoke tests.

### Reference artifacts

Generated images and volume files should normally be reproducible outputs, not large files committed to Git. Commit small configuration files, expected metadata, selected numeric values, and checksums. If binary golden files prove necessary, record why and keep them minimal.

## 8. Phase 0 Deliverables

- Installable core Python package.
- Committed `pyproject.toml`, `.python-version`, and reproducible `uv.lock`.
- Five architecture decision records.
- Versioned canonical volume schema documentation.
- Core volume, geometry, validation, and provisional mapping implementation.
- Deterministic synthetic fixture generators.
- Zarr reader, writer, inspector, and round-trip evidence.
- Mitsuba 3 proof and capability report.
- OpenVDB/Cycles proof and capability report.
- Cross-consumer conformance command and results.
- Automated core and optional integration test suites.
- Phase 0 feasibility report with a Phase 1 recommendation.

## 9. Definition of Done

Phase 0 is done only when all of the following are true:

- Coordinate, unit, axis, transform, sampling, and color semantics are documented and enforced.
- Material-label, material-mixture, and optical-property schemas have explicit versions and validation rules.
- The canonical optical representation includes `sigma_a`, `sigma_s`, `g`, and `ior`, with boundary behavior explicitly decided.
- A synthetic material asset converts deterministically to a validated optical asset.
- Zarr round trips preserve values and semantics, and spatial partial reads are demonstrated.
- Both consumer proofs operate from the same canonical asset without renderer-specific state entering the core model.
- Each exporter reports approximated and unsupported semantics.
- Core checks pass without optional renderer dependencies.
- A clean checkout can reproduce the core environment with uv alone, and CI rejects an outdated lockfile.
- The feasibility report demonstrates the exit criteria and recommends either proceeding to Phase 1 or revising a named foundation decision.

## 10. Stop Conditions and Decision Gates

Pause broad implementation and revisit the relevant ADR if any of these occurs:

- the proposed schema cannot distinguish storage axes from physical axes;
- Zarr cannot round-trip required metadata or support practical partial reads under the selected layout;
- sharp boundaries or refractive transitions require canonical data absent from the schema;
- either target consumer requires destructive reinterpretation of optical coefficients;
- optional renderer dependencies leak into the core package;
- proof outputs cannot reveal axis, scale, or boundary errors reliably.

These are Phase 0 findings, not integration details. Resolving them before Phase 1 is more important than preserving an early API.
