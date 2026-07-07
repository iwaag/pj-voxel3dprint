# Phase 3 Implementation Plan — Procedural Natural-Material Generators

Status: draft (2026-07-07). Source: `roadmap_vdbmat-utils.md`, Phase 3.
Target repository: `vdbmat-utils` (single distribution, `src/vdbmat_utils/`, unchanged from
Phases 0–2). Canonical spelling everywhere: `vdbmat` / `vdbmat-utils`.

## 1. Goal and Exit Criteria

Generate controllable mineral-, rock-, and formation-like material distributions as discrete
material-label volumes, from reusable seeded primitives (noise, cellular fields, domain
warping, morphology) composed into named formation models (host rock, strata, veins,
grains/crystals, pores, fractures), with measurable structural constraints and a companion
`vdbmat.optical-mapping` document whenever the palette uses non-built-in material names.

Phase 3 is done when, from a clean checkout with no extras installed:

1. **Formation workflow** — `vdbmat-utils generate-formation --config <formation.json> --out <dir> --name <name>`
   deterministically produces `<name>.voxels.json` + `<name>.material_id.npy` (and, when the
   palette requires it, `<name>.optical-mapping.json`) from a seeded procedural model, and
   the result passes `vdbmat-utils validate` and `vdbmat import-voxels`.
2. **Mapping pairing works end to end** — the emitted mapping document validates against
   `vdbmat mapping-digest`, its digest is recorded in the asset's provenance, and the asset +
   mapping pair runs through `vdbmat convert` with `mapping.path`/`mapping_digest` declared —
   no manual coordination.
3. **Statistical characterization** — `vdbmat-utils formation-stats <manifest>` reports, per
   material: volume fraction, feature-size distribution (local-thickness percentiles),
   connected-component count and largest-component fraction, and minimum printable thickness
   versus a configured threshold; the same metrics are computable from the Python API.
4. **Constraints are checkable** — a formation config may declare target constraints
   (volume-fraction ranges, minimum feature size, connectivity requirements, minimum
   printable thickness); `generate-formation` evaluates them after generation and reports
   pass/fail per constraint (`--strict` turns failures into exit 1). Generation does *not*
   iterate to satisfy constraints in this phase — it measures and reports (see §6).
5. **Sweeps and reference data** — `vdbmat-utils sweep-formation --config <sweep.json> --out <dir>`
   runs a declared parameter grid, writing one asset + stats record per point and a single
   `sweep_summary.json`; at least one small seeded reference formation (with its stats
   golden) lives in the repo for regression testing.
6. **Determinism** — byte-equal double runs for `generate-formation` at fixed seed;
   payload-digest goldens; axis-orientation ASCII goldens; changing only `seed` changes the
   payload digest (anti-fixed-output check).
7. **Claims are scoped** — `docs/procedural.md` states explicitly that models target visual
   and structural plausibility under declared metrics, not geological or printing-process
   validity, and lists per-model what is and is not claimed.
8. A "Phase 3 exit criteria" CI step runs the formation workflow → `validate` →
   `vdbmat import-voxels` → `vdbmat convert` (with the emitted mapping), including on the
   minimal-install leg (Phase 3 adds **no** new runtime dependencies; see D2).

## 2. Inputs, Constraints, and Verified Facts

Facts verified against the working tree on 2026-07-07 — re-verify before starting:

- Phase 0–2 provide and Phase 3 must reuse (not duplicate):
  - `fields.ScalarField`, `fields/edt.py` (`squared_edt`, `signed_distance` — exact separable
    Felzenszwalb–Huttenlocher, anisotropic spacing), and
    `fields/quantize.py::quantize_to_labels(field, bin_edges, material_ids)` — **the only
    scalar→label conversion** (Phase 2 D3). All procedural smoothness lives in `ScalarField`
    space; labels appear only through `quantize_to_labels` or explicit integer `where`-style
    assembly on already-discrete masks.
  - `core`: `build_material_label_volume`, `GeneratorConfig`/`config_digest` canonical-JSON
    rules, `rng_from_seed`/`spawn_rngs` (single non-negative int seed; substreams via
    `spawn`; no Python `random`, no NumPy legacy global state), `build_provenance`,
    error hierarchy (`ConfigError`, `GeometryError`, `PaletteError`), `core/compat.py`.
  - `io/writer.py::write_asset`; `preview/` (`material_counts`, `slice_ascii`, `slice_pgm`);
    the argparse CLI in `cli/main.py` with its fixed success/failure conventions (manifest
    path + material-count summary on success; single-line actionable error, exit 1).
  - The label-safety AST guard (`tests/unit/test_label_safety.py`) and import-isolation test
    (`tests/unit/test_import_isolation.py`) — new subpackages join both.
- The optical-mapping contract is `vdbmat/docs/schemas/optical-mapping-v1.md`: all top-level
  fields required; `optical_basis` must be exactly the Phase 0 RGB basis; `materials[]`
  entries carry `material_id`, `name`, `sigma_a_rgb_per_m`, `sigma_s_rgb_per_m`, `g`, `ior`;
  `external_id` forbidden; identity = SHA-256 of canonical JSON, reported by
  `vdbmat mapping-digest FILE`; `vdbmat convert` accepts `mapping.path` + `mapping_digest` in
  its pipeline configuration. The reader is `vdbmat.optics.load_optical_mapping` — confirm at
  step start (Step 0.0) whether the canonical-JSON/digest routine is public and reuse it; if
  it is private, compute the digest in-repo and cross-check against `vdbmat mapping-digest`
  in an integration test, and log the upstream follow-up (do not fork schema rules).
- `vdbmat`'s built-in material-name table determines when a mapping document is *required*.
  Confirm the public way to enumerate built-in names at Step 0.0 (the built-in mapping
  document `examples/phase1/mappings/phase0-provisional-materials-v1.optical-mapping.json`
  and/or an optics API). The rule (roadmap): emit a mapping whenever any palette name falls
  outside the built-in table — mineral/vein/formation names will.
- Backward compatibility is **not** required (user decision, 2026-07-06): breaking changes
  preferred; delete superseded code rather than shimming.
- No new extras: base install stays `numpy` + `vdbmat` (Principle 5). In particular **no
  scipy, no noise/opensimplex packages** — primitives are implemented in-repo (D2). No
  performance work beyond vectorized NumPy (Principle 7; Phase 5 owns acceleration); size
  guards bound cost as in Phase 2.

## 3. Fixed Design Decisions

Settle these now so implementation does not re-litigate them.

### D1. Module layout

```text
src/vdbmat_utils/
  procgen/
    __init__.py        # public re-exports + ProcgenError(VdbmatUtilsError)
    domain.py          # FormationDomain: shape, voxel size, world coords helper, size guards
    hashing.py         # SplitMix64-style uint64 lattice hash (the determinism keystone, D3)
    noise.py           # gradient (Perlin-style) 3-D noise, fBm, ridged fBm -> ScalarField
    cells.py           # Worley/Voronoi F1/F2 cellular fields + nearest-site id field
    warp.py            # domain warping: coordinate offset by vector of noise fields
    morphology.py      # binary erode/dilate/open/close on boolean masks (6/26-neighbourhood)
    models/
      __init__.py      # FormationConfig, generate_formation, layer registry
      host.py          # host-rock base layer
      strata.py        # layered strata (warped planar bands)
      veins.py         # veins (warped surface-distance shells)
      grains.py        # grains/crystals (Worley cells + per-cell material assignment)
      pores.py         # pores (thresholded noise or seeded spheres, morphologically shaped)
      fractures.py     # fractures (thin warped-plane shells)
    stats.py           # volume fractions, local thickness, connectivity, constraint checks
    connectivity.py    # in-repo two-pass union-find connected components (6-connected)
  io/optical_mapping.py  # build + write optical-mapping documents, digest, built-in-name check
  cli/main.py          # extended with generate-formation, formation-stats, sweep-formation
```

Import direction (extends the Phase 1/2 isolation test): `procgen` may import `fields`,
`core`, `io`, `preview`; `procgen/models` may import the rest of `procgen`; nothing outside
`procgen` imports `procgen` except `cli`. `io/optical_mapping.py` may import only `core` and
`vdbmat` optics APIs. `procgen` must not import `ops`, `morph`, `pipeline`, `mesh`, `image`.

### D2. Dependencies

None added. All primitives are NumPy implementations:

- Noise, cellular fields, and warping are vectorized lattice algorithms (D3/D4) — no
  `noise`/`opensimplex` package.
- Morphology is implemented with `np.pad` + shifted boolean ORs/ANDs over structuring-element
  offsets (6- or 26-neighbourhood, iterated for radius) — exact, allocation-simple, adequate
  at Phase 3 sizes; no scipy.
- Local thickness reuses `fields/edt.py` in 3-D (it is separable; verify the existing wrapper
  exposes 3-D use — if it is 2-D-only, generalize it in place rather than duplicating).
- Connected components is an in-repo two-pass union-find over the 6-neighbourhood
  (`procgen/connectivity.py`), returning a `uint32` component-id array plus component sizes.
  Pure-NumPy row scanning with a Python union-find table is acceptable at guarded sizes.

Size guards as config fields, same convention as Phase 2: `max_axis_cells: int = 256`,
`max_total_cells: int = 16_000_000`; exceeding them is an explicit `ConfigError` suggesting a
smaller domain (Phase 5 owns scale).

### D3. Determinism and the lattice hash (the keystone decision)

Reproducibility must be *structural*, not incidental:

- **Coordinate hashing, not array-order RNG.** Lattice-dependent randomness (noise gradients,
  Worley feature points, per-cell material picks) derives from a counter-based integer hash
  `h(ix, iy, iz, stream_id, seed) -> uint64` implemented in `procgen/hashing.py` as a fixed
  SplitMix64-style mix over `uint64` NumPy ops (documented constants, fixed forever once
  ADR'd). Consequences, which are the point: values are independent of evaluation order,
  chunking, and domain bounds — the same world lattice point always gets the same gradient or
  feature point for a given seed, so enlarging or cropping the domain does not reshuffle the
  interior. Unit-tested exactly (golden hash values for fixed inputs) and property-tested
  (domain-extension invariance).
- **Stream ids are enumerated constants.** Each consumer (each noise instance, each Worley
  instance, each per-cell assignment) gets a distinct `stream_id` derived from its layer
  index and role, allocated by a documented scheme in `models/__init__.py`. Adding a layer
  never shifts existing layers' fields (same guarantee `spawn_rngs` gives sequential RNG
  code, achieved hash-side).
- `rng_from_seed`/`spawn_rngs` remain for non-lattice randomness (e.g. jittered sweep points
  if ever needed); Phase 3 generators should need **no** sequential RNG draws — everything is
  hash-derived. `seed` lives in `FormationConfig` as usual and feeds the hash.
- Float determinism: all field math is float64 NumPy with fixed expression order; no
  reductions with order ambiguity (no `np.sum` over parallel chunks — dense whole-array ops
  only). Byte-equal double runs are therefore expected and contract-tested, same as
  Phases 0–2.

### D4. Primitive specifications

Fixed so implementation and review have a spec. All primitives take a `FormationDomain`
(shape `z, y, x`, `voxel_size_xyz_m`, optional `local_to_world`) and evaluate on world-space
metre coordinates of voxel centres, so anisotropic voxels and feature sizes in metres are
handled once, in `domain.py`.

- **Gradient noise (`noise.py`).** Classic Perlin-style: integer lattice with unit gradients
  chosen by hash (12-direction table indexed by `h & 0xF` mod 12 — fixed table in the ADR),
  trilinear blend with quintic fade `6t⁵−15t⁴+10t³`. Parameters: `frequency_per_m`
  (isotropic; anisotropy comes from domain warping, not per-axis frequency — one less
  ambiguity), `stream_id`. Output range documented as approximately [−1, 1], not clamped.
  - **fBm:** `octaves: int`, `lacunarity: float = 2.0`, `gain: float = 0.5`; octave `i` uses
    `stream_id + i` (scheme in D3). Normalized by `sum(gain^i)` so amplitude is
    octave-count-independent.
  - **Ridged fBm:** per-octave `1 − |noise|`, squared, then fBm-accumulated — the standard
    ridge formula, written out in the docstring with the exact accumulation order.
- **Cellular fields (`cells.py`).** Worley: one feature point per lattice cell at a
  hash-derived jittered position (three hash draws mapped to [0,1)³), searched over the 3×3×3
  cell neighbourhood. Outputs, all as `ScalarField` or integer arrays on the domain grid:
  `f1` (distance to nearest feature point, metres), `f2`, `f2 − f1` (crystal-boundary field),
  and `site_id` (uint64 hash id of the nearest feature point — the key for per-cell material
  assignment in grains). Parameter: `cell_size_m` (isotropic lattice pitch in world metres),
  `stream_id`.
- **Domain warping (`warp.py`).** `warp(domain, offsets_xyz: three ScalarFields, amplitude_m)`
  produces displaced world coordinates fed into any primitive's evaluation — implemented as
  "evaluate primitive at `coords + amplitude · offsets`", not as a resampling of an already
  evaluated field (no interpolation, no label risk, exact and deterministic). Warp fields are
  themselves fBm instances with their own stream ids.
- **Morphology (`morphology.py`).** `erode/dilate(mask, radius_cells: int, connectivity: 6|26)`
  by iterated one-step operations; `open`/`close` as compositions. Boolean arrays in/out
  only — never label arrays (the AST guard is extended to `procgen/`, D6).
- **Thresholding to masks.** Boolean masks come from comparisons on `ScalarField.values`
  (allowed — bool is not a label); *material ids* enter only in model assembly (D5) via
  integer selection on masks or via `quantize_to_labels`.

### D5. Formation model and label assembly

- **Config shape.** `FormationConfig(GeneratorConfig)`: `shape_zyx`, `voxel_size_xyz_m`,
  optional `local_to_world`, `palette: tuple[{material_id, name, role?}, ...]`,
  `layers: tuple[LayerConfig, ...]`, `constraints: tuple[ConstraintConfig, ...] = ()`,
  `mapping: MappingConfig | None`, size guards, `seed`. Layer configs are tagged unions
  (`kind: "host" | "strata" | "veins" | "grains" | "pores" | "fractures"`) with per-kind
  parameter dataclasses; unknown kinds/params are `ConfigError`s at validation time with the
  layer index in the message (same fail-fast style as the Phase 2 pipeline registry).
- **Assembly = ordered painter's algorithm.** The label array starts as the host layer's
  output; each subsequent layer computes a boolean **support mask** plus a per-voxel material
  assignment on that mask, and paints it over the current array ("last writer wins", matching
  Phase 2 compose-union semantics). Layer order in the config *is* the precedence order —
  explicit, deterministic, and documented; no hidden priority table. Every painted
  material_id must exist in `palette` (else `PaletteError` naming the layer).
- **Per-kind semantics (the marble/granite vocabulary):**
  - `host`: fills the domain with one material, or with `quantize_to_labels` over an fBm
    field (bin edges + ids from config) for mottled base rock.
  - `strata`: bands of `thickness_m` stacked along a config axis, warped by an fBm
    displacement field (`amplitude_m`); band index → material id via a repeating sequence
    from config. Implemented as quantization of the warped plane-coordinate field.
  - `veins`: the marble look. Support = `|field| < width_m/2` where `field` is a warped
    planar/linear coordinate field (fBm-displaced), giving sheet-like veins whose
    waviness/width come from warp amplitude/frequency; one material id per vein layer.
    Multiple vein generations = multiple layers with different stream ids.
  - `grains`: the granite/crystal look. Worley `site_id` field; each cell's material id is
    picked from a configured weighted id list by hashing the site id (`hashing.py`, so the
    pick is stable under domain changes); optional boundary material where
    `f2 − f1 < boundary_width_m`. Support = whole domain or a mask from a noise threshold.
  - `pores`: support = `fbm > threshold` shaped by morphology (`open` with radius) to control
    minimum pore size, painted as a configured pore material (which may be background/air);
    documented as the way to make *voids*.
  - `fractures`: thin shells like veins but with `width_m` typically one–two voxels and
    stronger warping; painted last by convention (documented, not enforced).
- **Result** goes through `build_material_label_volume` + `build_provenance` and
  `write_asset`, exactly like every other generator. Generator identity:
  `generator="vdbmat-utils.procgen.formation"`, version `"0.1.0"`; `sources=()` (purely
  procedural); `identity` = SHA-256 over the config digest (documented: config **is** the
  source).

### D6. Label safety (carry Phase 2's discipline into procgen)

- All continuous math is `ScalarField`/float arrays; labels appear only via
  `quantize_to_labels` or integer writes onto boolean masks. The AST guard test extends to
  `procgen/` (no `astype(float…)`, no `np.interp`, no arithmetic mean/multiply on names bound
  to `material_id`).
- `morphology.py` and `connectivity.py` accept boolean/`uint32` arrays only and assert dtype.
- Warping displaces *coordinates before evaluation*, never resamples evaluated arrays — this
  is what keeps warp out of interpolation territory entirely (D4).

### D7. Statistics, constraints, and printability metrics

Definitions are fixed here because "feature size" is otherwise a re-litigation magnet:

- **Volume fraction** per material id: count / total, exact integers reported alongside the
  float fraction.
- **Local thickness** of a material's mask: `2 × EDT(mask)` sampled at mask voxels (distance
  to the nearest non-mask voxel, metres, anisotropic-aware) — the standard inscribed-sphere
  *lower-bound* proxy; report min / p05 / p50 / p95 / max. Documented as a conservative
  proxy, not full sphere-fitting local thickness (record in ADR; upgrade is future work).
- **Minimum printable thickness** check: `min_local_thickness(material) ≥ threshold_m` for
  each material the config marks `printable: true`; a constraint, not a transform — Phase 3
  measures, it does not repair (§6).
- **Connectivity**: 6-connected components per material id (via `connectivity.py`); report
  component count, largest-component volume fraction; constraint forms:
  `connected: "single-component" | "max-components N"` and
  `min_largest_component_fraction: float`.
- **Constraint evaluation** returns a structured report (constraint, measured value, bound,
  pass/fail) printed by the CLI and written as `<name>.stats.json` next to the asset;
  `--strict` exits 1 on any failure. `formation-stats` computes the same report for any
  existing asset (loaded via the Phase 2 reader path), so stats are decoupled from
  generation.

### D8. Optical-mapping emission (`io/optical_mapping.py`)

- **Trigger rule (roadmap):** after building the palette, compare material names against
  `vdbmat`'s built-in table (public API per Step 0.0). If any name is outside it, a mapping
  document is **required**: config must supply `mapping.materials` covering exactly the
  non-built-in names (coefficients `sigma_a_rgb_per_m`, `sigma_s_rgb_per_m`, `g`, `ior` are
  **user-supplied numbers passed through verbatim** — utils owns the document, never the
  values, per the product boundary). Missing or extra entries are `ConfigError`s naming the
  material. If all names are built-in, no document is written and provenance records the
  built-in digest instead.
- **Document construction:** exactly the schema-v1 layout; `optical_basis` hardcoded to the
  Phase 0 RGB basis; `calibration_status` from config, default `"provisional-uncalibrated"`;
  `configuration_id` = `"<name>-materials-v1"` unless overridden; no `external_id` ever.
  Written as `<name>.optical-mapping.json` beside the manifest.
- **Digest:** computed as SHA-256 of the canonical JSON via the `vdbmat` public routine if
  available (Step 0.0), else in-repo with the identical canonicalization; an integration test
  asserts byte-for-byte agreement with `vdbmat mapping-digest` output either way. The digest
  is recorded in the asset's provenance (extend `build_provenance` inputs or the generator's
  provenance `parameters` — decide at Step 3 based on what the provenance model already
  allows without schema forks; record the choice in ADR-0012).
- **End-to-end:** the Phase 3 integration test drives `vdbmat convert` with a pipeline
  configuration declaring `mapping.path` + `mapping_digest`, proving the "asset plus mapping
  pair runs through vdbmat without manual coordination" roadmap bullet.

### D9. Sweeps and reference datasets

- `SweepConfig(GeneratorConfig)`: `base: FormationConfig payload`, `axes: tuple[{path,
  values}, ...]` (dotted config path → explicit value list; full Cartesian product; guard
  `max_runs: int = 64`). No random search, no distributed execution (Phase 4/5).
- Each run writes `<name>-<NNN>/` containing the asset, stats, and (if required) mapping;
  `sweep_summary.json` records, per run: the overridden values, config digest, payload
  digest, and the flat stats record. Determinism: the summary is byte-stable across double
  runs (contract-tested).
- **Reference dataset:** one small seeded formation config per model family that Phase 3
  ships (minimum: a veined "marble-like" config and a grained "granite-like" config,
  ≤ 64³), committed under `examples/` with golden payload digests and golden stats JSON in
  `tests/contract/` — the regression anchor the roadmap asks for.

### D10. ADRs to write during this phase

- ADR-0010: procedural determinism — the lattice-hash design (constants, stream-id scheme,
  domain-extension invariance) and why hash-derived beats sequential RNG here (D3).
- ADR-0011: formation model — layer/painter assembly, per-kind semantics, the
  coordinate-warp-not-resample rule, size guards (D4, D5, D6).
- ADR-0012: metrics and mapping emission — local-thickness proxy definition, connectivity
  and printability constraints, measure-don't-repair, mapping trigger rule, digest recording
  in provenance (D7, D8).

## 4. Implementation Steps

Execute in order; each step ends with `ruff check`, `mypy`, `pytest` green and a short
report under `.devdocs/vdbmat-utils/reports/phase3/` (follow the phase1/2 report style).
Commit per step.

### Step 0 — Hashing, domain, noise

0. Verify the `vdbmat` public APIs this phase depends on: built-in material-name
   enumeration, mapping canonical-JSON/digest routine, `load_optical_mapping`, and the
   `vdbmat convert` mapping-declaration syntax (`mapping.path` + `mapping_digest`). Record
   findings in the step report; log upstream follow-ups for anything private.
1. `procgen/hashing.py` (fixed constants + golden-value tests + domain-extension property
   test), `procgen/domain.py` (`FormationDomain`, world-coordinate helper, size guards),
   `procgen/noise.py` (gradient noise, fBm, ridged fBm per D4).
2. Unit tests (`tests/unit/test_procgen_noise.py`): value range, smoothness sanity
   (finite-difference bound), octave normalization, stream-id independence (two ids →
   different fields), seed sensitivity, **domain-extension invariance** (evaluate on 32³ and
   on 48³ containing it; interior must be byte-equal — the D3 keystone test), anisotropic
   voxel handling (feature size in metres, not cells), determinism double-run.
3. Extend `test_import_isolation.py` and the label-safety AST guard to `procgen/`.

### Step 1 — Cells, warp, morphology, connectivity

1. `procgen/cells.py` (Worley f1/f2/site_id per D4), `procgen/warp.py`,
   `procgen/morphology.py`, `procgen/connectivity.py`.
2. Unit tests: Worley distances against brute-force all-sites search on small domains;
   site_id stability under domain extension; warp = evaluation at displaced coordinates
   (compare against manual composition); morphology against hand-written expected arrays
   (asymmetric masks, 6 vs 26, radius iteration); union-find components against handmade
   cases (touching corners under 6-connectivity are separate; sizes correct); dtype
   assertions reject label arrays.
3. Verify/generalize `fields/edt.py` for 3-D use with anisotropic spacing (brute-force
   comparison test in 3-D if not already present).

### Step 2 — Stats and constraints

1. `procgen/stats.py`: volume fractions, local-thickness percentiles (D7 definition on top
   of the 3-D EDT), connectivity metrics, constraint evaluation returning the structured
   report; `<name>.stats.json` serialization (canonical JSON, sorted keys).
2. Unit tests on analytic shapes: a `w`-voxel slab has min local thickness `w·voxel_size`
   (exact for the proxy); a sphere's max thickness ≈ diameter within one voxel; two separate
   blobs → 2 components with correct fractions; each constraint form passes/fails on
   constructed cases; anisotropic voxel sizes respected.

### Step 3 — Formation models, mapping emission, generate-formation CLI

1. `procgen/models/`: `FormationConfig`, per-kind layer configs and implementations, the
   painter assembly, palette validation (D5); `io/optical_mapping.py` (D8).
2. CLI `generate-formation --config CONFIG --out DIR --name NAME [--seed N] [--strict]`
   (seed override folded into the effective config before digesting, matching Phase 1 D5;
   success output = manifest path + material counts + constraint report + mapping path when
   emitted).
3. Unit tests: each layer kind on a small domain with golden payload digests and at least
   one exact hand-checkable case (e.g. unwarped strata bands as an expected array literal;
   single-cell grains domain); painter precedence (later layer overwrites); palette
   violations name the layer; mapping trigger rule (all-built-in → no file; mixed → file
   with exactly the non-built-in names; missing coefficients → `ConfigError`); mapping
   document validates against `load_optical_mapping`; constraint `--strict` exit code.
4. `formation-stats MANIFEST [--constraints CONFIG]` CLI reusing the Phase 2 asset reader;
   test on a Phase 3 fixture and on a Phase 1 fixture (stats are generator-agnostic).

### Step 4 — Sweeps, reference fixtures, contract and integration tests

1. `sweep-formation` per D9 (a thin loop over `generate_formation` — no new engine);
   `sweep_summary.json`; `max_runs` guard.
2. Reference configs under `examples/` (marble-like veins, granite-like grains, ≤ 64³) with
   committed golden payload digests and golden stats JSON.
3. Contract tests (`tests/contract/test_phase3_contract.py`): byte-equal double runs for
   `generate-formation` and `sweep-formation`; payload-digest goldens for both reference
   formations; seed-change ⇒ digest-change; orientation ASCII goldens on all three axes of
   an asymmetric formation; stats goldens.
4. Integration tests (marker `integration`): reference formation → `vdbmat-utils validate`
   → `vdbmat import-voxels` → `vdbmat mapping-digest` (digest equality with our recorded
   value) → `vdbmat convert` with the mapping pair declared — via subprocess, mirroring
   `tests/integration/test_import_voxels.py`.

### Step 5 — Documentation, CI, and phase close-out

1. Docs: `docs/procedural.md` (primitive specs, layer vocabulary with worked marble and
   granite configs, determinism/hashing explanation, the visual-plausibility-vs-validity
   scope statement per model), `docs/stats.md` (metric definitions, proxy caveats,
   constraint forms), `docs/optical-mappings.md` (trigger rule, config shape, digest and
   `vdbmat convert` pairing walk-through); README quick-start; ADRs 0010–0012.
2. CI: add "Phase 3 exit criteria" step (generate both reference formations → `validate` →
   `vdbmat import-voxels` → `vdbmat convert` with mapping; run `formation-stats`) to the
   main leg **and** the minimal-install leg (no extras needed — assert it).
3. Update `roadmap_vdbmat-utils.md` Phase 3 status block (Phase 0–2 style) and record
   upstream `vdbmat` follow-ups (notably anything from Step 0.0 on optics API visibility);
   re-check the standing Phase 0/1 follow-ups list.

## 5. Test Matrix Summary (roadmap bullet coverage)

| Roadmap requirement | Where covered |
| --- | --- |
| Seeded primitives: noise, Voronoi/Worley, ridges, warping, distance fields, morphology | D3/D4, Steps 0–1 (ridged fBm in noise.py; distance fields reuse `fields/edt.py`) |
| Composable host rock, strata, veins, grains/crystals, pores, fractures | D5, Step 3, reference configs (Step 4.2) |
| Discrete labels with measurable constraints (fraction, feature size, connectivity, printable thickness) | D6 label safety, D7 metrics, Step 2, `--strict` (Step 3.2) |
| Companion optical-mapping document + `mapping-digest` + provenance recording | D8, Steps 3.1/3.3, integration (Step 4.4) |
| Visual plausibility vs validity separated and documented | Exit criterion 7, `docs/procedural.md` scope statements (Step 5.1) |
| Parameter sweeps, summary statistics, reference regression datasets | D9, Steps 2, 4.1–4.3 |
| Exit: seeded formation regenerated, characterized, previewed, consumed end to end | Contract double-run + stats goldens + previews (existing `preview/` via CLI success output) + Step 4.4 |

## 6. Out of Scope (defer explicitly)

- **Constraint-satisfying generation** (search/optimization loops until constraints pass) —
  Phase 3 measures and reports only; iterating is a recorded deferral in ADR-0012.
- Geological or printing-process validity claims of any kind; calibration; optical
  coefficient *values* (user-supplied pass-through only, per the product boundary).
- Simplex/OpenSimplex noise, curl noise, reaction–diffusion, erosion simulation, and
  correspondence/exemplar-based texture synthesis — the primitive set is fixed to D4.
- Full sphere-fitting local thickness and 26-connected or per-axis connectivity options
  beyond D7's forms.
- Procedural layers as Phase 2 pipeline steps (same deferral as generators-in-pipelines,
  ADR-0009); chunked/parallel evaluation, GPU/Numba, sparse domains (Phase 5); job/batch
  semantics beyond the in-process sweep loop (Phase 4); ML anything (Phase 6).
- Vector-valued fields as public API (warp uses three scalar fields internally; a
  `VectorField` type is future work if a real consumer appears).

## 7. Risks Specific to This Phase

- **Silent non-determinism in lattice randomness:** hashing bugs (overflow behavior,
  platform-dependent ops) would be invisible in previews. Mitigation: `hashing.py` uses only
  explicit `uint64` NumPy ops, golden hash-value tests, the domain-extension invariance
  test, and byte-equal double runs at contract level.
- **Parameter soup:** procedural models accumulate knobs until configs are write-only.
  Mitigation: per-kind frozen dataclasses with few, metre-denominated parameters
  (frequencies and sizes in world metres, never in cells), validated fail-fast; worked
  example configs in docs are the API's usability test.
- **Plausibility mistaken for validity:** a convincing marble preview invites unfounded
  claims. Mitigation: exit criterion 7 — every model's doc section has an explicit
  "claims / non-claims" list, and stats reports are the only quantitative statements made.
- **Metric definition drift:** "feature size" and "thickness" have many literatures.
  Mitigation: D7 fixes proxy definitions now, tests them on analytic shapes, and ADR-0012
  names the upgrade path so implementation does not improvise.
- **Mapping/schema fork:** re-implementing canonical JSON or digest rules could drift from
  `vdbmat`. Mitigation: Step 0.0 API check, reuse where public, and a byte-for-byte
  integration test against `vdbmat mapping-digest` regardless.
- **Memory blow-up from per-layer fields:** each layer may materialize several float64
  fields. Mitigation: evaluate layers one at a time, release fields after painting, size
  guards (D2); document cost as O(layers × domain) time, O(domain) resident memory.
