# Phase 0 Implementation Report: Step 8

**Date:** 2026-06-28
**Completed scope:** Step 8 — Resolve Boundary and IOR Semantics
**Status:** Complete

## Summary

Step 8 accepts ADR-003, retains cell-centred `ior` as required canonical data, and
selects an oriented sharp-interface face set as the minimum common derived boundary
representation. Mitsuba and Blender Cycles cannot consume the canonical field directly
as spatial bulk refractive index, so their explicit policies require diagnostics and
surface-based mappings rather than silent omission.

The implementation derives deterministic interfaces from adjacent IOR cells and an
explicit exterior ambient, preserves complete source geometry and provenance, exposes
world-space face corners and normals, and defines machine-readable policies for both
consumers. Step 9 and Step 10 will turn these common faces into consumer-specific closed
meshes and rendering artifacts.

## Consumer Evidence

### Mitsuba 3

Official Mitsuba documentation shows that:

- heterogeneous media accept spatial `sigma_t` and albedo volumes;
- `gridvolume` offers trilinear and nearest filtering;
- dielectric boundaries accept scalar `int_ior` and `ext_ior` values.

The locked optional environment was synchronized and probed with Mitsuba 3.9.0:

```text
heterogeneous medium with sigma_t/albedo: accepted
heterogeneous medium with ior constvolume: rejected as unreferenced property
dielectric int_ior=1.5, ext_ior=1.0: accepted; eta=1.5
```

Added `examples/phase0/probe_mitsuba_ior.py` to reproduce this check with:

```bash
uv run --group mitsuba python examples/phase0/probe_mitsuba_ior.py
```

### Blender Cycles

Blender is not installed in the execution environment, so the decision uses current
official Blender node and OpenVDB documentation:

- OpenVDB named grids are loaded as volume data;
- Blender 4.5 Principled Volume has no bulk IOR input;
- the development Volume Coefficients node's Fournier-Forand IOR describes scattering
  particles relative to water and is not canonical bulk-medium IOR;
- Glass/transmissive surface shaders perform refraction.

Cycles therefore preserves any exported IOR grid as data but must report it as
unsupported for bulk refraction. Derived region surfaces are an explicit approximation.

## ADR-003 Decision

Added `docs/adr/0003-boundaries-and-refractive-index.md` comparing:

1. cell-centred spatially varying IOR;
2. an explicit derived interface asset;
3. renderer-specific region/material boundary meshes.

The decision is:

- canonical `OpticalPropertyVolume.ior` remains unchanged and mandatory;
- Phase 0 reconstructs IOR as piecewise constant per cell and never interpolates it;
- faces are derived where adjacent values differ by more than absolute tolerance `1e-6`;
- grid boundary cells are compared with explicit ambient IOR, default `1.0`;
- equal-IOR material changes do not create false optical interfaces;
- the interface set is derived and renderer-neutral;
- closed mesh topology, triangulation, medium nesting, and shaders remain exporter
  concerns for Steps 9 and 10.

No schema extension is required. The canonical field contains sufficient values to
derive the selected Phase 0 piecewise-constant reconstruction without adding
renderer-specific state.

## Implemented Boundary API

Added `src/vbdmat/boundaries/`.

### Derivation configuration

`BoundaryDerivationConfig` defines:

- positive finite `ambient_ior`, default `1.0`;
- non-negative absolute IOR tolerance, default `1e-6`;
- whether exterior interfaces are included.

### Interface faces

Each immutable `InterfaceFace` records:

- semantic normal axis X, Y, or Z;
- minimum continuous XYZ corner index on the cell plane;
- negative-side and positive-side ZYX cells, with `None` denoting exterior;
- exact IOR value on both sides;
- orientation from the negative semantic side to the positive side.

`DerivedInterfaceSet` retains source geometry, schema, provenance, and derivation
configuration. It separates interior/exterior faces and computes correctly transformed
world corners and normals.

### Consumer policies

`vbdmat.boundaries.policies` defines required diagnostic dispositions:

| Consumer | Spatial canonical IOR | Derived interface |
| --- | --- | --- |
| Mitsuba 3 | `unsupported` | `transformed` to oriented dielectric boundaries |
| Blender Cycles | `unsupported` | `approximated` by closed refractive surfaces |

Both policies explicitly prohibit IOR interpolation. Mitsuba must map oriented sides to
`ext_ior`/`int_ior`. Cycles must report that OpenVDB grids alone do not provide bulk
refraction and diagnose internal/nested-medium approximation limits.

## Background and Boundary Policy

Background cells remain ordinary cells with explicit optical properties. An internal
background/material IOR mismatch creates the same face as any other pair. Grid exterior
is not inferred from the palette; it uses the derivation's ambient IOR.

IOR faces and medium containment surfaces are distinct. Even when an exterior cell is
index matched to ambient and no IOR face exists, a renderer may still need a closed
index-matched mesh to delimit participating-medium integration. That mesh is an adapter
artifact, not canonical boundary data.

## Fixture Results

Added `examples/phase0/inspect_ior_interfaces.py` with these deterministic results:

| Fixture | Total faces | Interior | Exterior | Interior axes |
| --- | ---: | ---: | ---: | --- |
| homogeneous-transparent | 52 | 0 | 52 | none |
| homogeneous-scattering-white | 52 | 0 | 52 | none |
| transparent-opaque-interface | 96 | 8 | 88 | X: 8 |
| layered-material-slab | 124 | 30 | 94 | Z: 30 |
| two-material-mixture-ramp | 86 | 24 | 62 | X: 24 |
| anisotropic-axis-marker | 0 | 0 | 0 | none |

The interface fixture's eight internal faces lie on continuous X plane index `3`, world
X `0.01012 m`, oriented from IOR `1.48` to `1.52`. The layered fixture has no face at
the white/black material boundary because both map to IOR `1.52`. The mixture ramp is
deliberately reconstructed as piecewise constant and therefore produces a stair-step
face at each changed X cell. Diagnostic axis materials and background all map to IOR
`1.0`, producing no refractive interface.

## Tests Added

Added 16 tests covering:

- exact total, interior, exterior, and axis-specific face counts for all fixtures;
- interface plane, orientation, adjacent indices, and side values;
- suppression of equal-IOR material boundaries;
- piecewise-constant threshold behavior above and below tolerance;
- explicit ambient matching and exterior suppression;
- world-space corners, normals, anisotropic voxel scale, translation, and rotation;
- invalid ambient, tolerance, and exterior configuration;
- exact Mitsuba and Cycles policy dispositions and required policy text.

The full suite increased from 189 to 205 passing tests.

## Verification Results

| Check | Result |
| --- | --- |
| Candidate comparison and selected contract | Passed; ADR-003 accepted |
| Canonical versus derived distinction | Passed |
| Piecewise-constant interpolation policy | Passed and tested |
| Mitsuba runtime IOR probe | Passed with Mitsuba 3.9.0 |
| Cycles official API review | Passed; Blender runtime unavailable |
| Explicit Mitsuba policy | Passed |
| Explicit Cycles policy | Passed |
| No silent canonical IOR omission policy | Passed |
| Background and exterior behavior | Passed |
| Interface fixture | Passed; 8 sharp internal X faces |
| Layered fixture | Passed; equal-IOR boundary suppressed |
| Rotated/anisotropic geometry | Passed |
| pytest | Passed; 205 tests |
| Ruff formatting | Passed |
| Ruff linting | Passed |
| mypy strict check | Passed; 23 source files checked |
| `uv lock --check` | Passed; 24 packages resolved |
| Git whitespace check | Passed |

## Limitations and Deferred Work

- Derived faces are unit cell faces and are not merged, triangulated, or written as a
  mesh.
- The interface set does not solve renderer medium nesting or coincident-boundary rules.
- A mixture IOR ramp becomes voxel-scale sharp steps; gradient-index transport is not
  approximated.
- The default tolerance is a representation decision, not a calibrated physical
  threshold.
- Blender/Cycles behavior still needs runtime validation in Step 10.
- Containment geometry for index-matched media is separate from IOR derivation and will
  be created by each adapter as needed.

## Step 8 Completion Assessment

All Step 8 verification requirements are satisfied. The candidates and consumer
capabilities are documented, interface interpolation and background behavior are
explicit, both adapters have testable IOR policies, no canonical field may be silently
omitted, and the minimum shared derived interface representation is implemented and
verified. Step 9 is the next dependency-ordered task.

