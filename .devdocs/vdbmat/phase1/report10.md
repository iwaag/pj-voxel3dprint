# Phase 1 — Step 10 Report: Reference Scenes and Baseline Outputs

- **Date:** 2026-07-02
- **Step:** 10 of 12 (`.local/phase1/plan.md`)
- **Status:** Complete. Both Phase 1 objects have reproducible canonical bundles,
  fixed Mitsuba visual baselines, and pinned OpenVDB/Cycles interoperability smoke
  outputs with machine-readable digests and capability records.

## 1. Reproducible baseline workflow

Added `examples/phase1/generate_reference_baselines.py`. From a clean output root it:

1. regenerates both representative inputs;
2. executes both canonical pipelines with relative paths and a fixed recorded time;
3. renders restored `optical.zarr` assets through Mitsuba;
4. verifies PNG dimensions/non-flatness and all field-level conformance checks;
5. writes `baseline-manifest.json` with canonical summaries, provenance/digests,
   renderer settings, capability reports, artifact paths, sizes, and hashes.

The fixed Mitsuba configuration is 256 x 256, 64 spp, seed `20260628`, max depth 8,
35-degree perspective, geometry-framed camera direction `(1.6, -2.2, 1.4)`, and an
opposed unit-RGB rectangular backlight. Mitsuba is version 3.9.0 and the adapter is
`vbdmat.exporters.mitsuba` 1.0.0.

The higher resolution replaces the Step 8 smoke-scale view. Visual inspection confirms
that the coupon view separates the bright white inclusion from the smaller asymmetric
dark marker, making orientation reversal detectable. The wedge view exposes all four
steps without manual scene edits.

Reproduction and renderer-difference guidance is documented in
`docs/phase1-reference-baselines.md`.

## 2. Canonical and Mitsuba evidence

| Object | Source SHA-256 | Config digest | Run ID | Material / optical Zarr SHA-256 |
| --- | --- | --- | --- | --- |
| window coupon | `fc9c3b36…372e0b` | `868d8f73…18d1c4` | `run-39e618b0049e5ef6` | `765ffd52…42cc81` / `969b152b…5995c5` |
| stepped wedge | `68c03e6e…4c818d` | `f7cc6360…c8c0d8` | `run-044b29275258b6bf` | `b7c487ad…e9f649` / `b80bebb2…5ff693` |

Canonical summaries match the analytic fixtures:

- coupon shape `(12,16,20)`, counts `{0:0, 1:3750, 2:72, 3:18}`;
- wedge shape `(10,8,18)`, counts `{0:960, 1:480}`.

Mitsuba image results:

| Object | Baseline PNG SHA-256 | Attenuation PNG SHA-256 | Sanity |
| --- | --- | --- | --- |
| window coupon | `f8a810cf…06dfdc` | `7217fe29…d492c` | 256x256 RGB, byte range 255 |
| stepped wedge | `a1aa8fa9…6b242b` | `18a8be77…125c0a` | 256x256 RGB, byte range 255 |

All ten field/transform/unit/background/capability conformance checks pass for each
object. The existing locked Mitsuba monotonic-response tests pass for controlled
absorption and scattering increases (`mean(0) > mean(10000) > mean(50000)`).

## 3. OpenVDB/Cycles smoke evidence

Both restored optical assets were exported with OpenVDB 10.0.1 and adapter 1.0.0,
then rendered by Blender/Cycles 4.5.11 in the pinned container. Settings are 64 x 64,
32 samples, seed `20260629`, and 8 maximum bounces. Both images are non-empty and
non-flat (RGBA byte range 2).

Cycles reduces RGB coefficients to scalar fields and omits internal IOR interfaces;
these dark images are interoperability smoke outputs, not visual baselines. Their
decoded pixels are currently identical, which is acceptable for this limited role.

Blender PNG file bytes vary across clean runs because of encoder metadata. The
observed file SHA-256 values are retained, but `baseline-manifest.json` marks them
non-byte-stable and records the stable decoded-pixel SHA-256
`25ef30d0…06a1a0` for both. OpenVDB and `.blend` bytes are also not claimed stable.

## 4. Clean-rerun and test results

A complete second generation under `.local/phase1/step10-rerun/` confirmed equal:

- material and optical Zarr hashes for both objects;
- both Mitsuba baseline PNG hashes;
- both Cycles decoded-pixel hashes;
- canonical summaries, run IDs, settings, and conformance results.

Primary evidence is under `.local/phase1/step10/` and occupies 2,028,209 bytes.

```text
uv lock --check                         pass
uv run ruff check .                     pass
uv run mypy --strict src/vbdmat         pass (44 source files)
baseline generator strict mypy          pass
uv run pytest -q                        374 passed, 2 native-only skipped (23.45 s)
focused conformance + Mitsuba tests     20 passed
OpenVDB/Cycles container generation     pass for both objects
git diff --check                        pass
```

The host skips are only the two native OpenVDB/Blender integration tests; the same
pinned container path generated and validated both Step 10 smoke outputs. Renderer
pixels are not compared across Mitsuba and Cycles as physical equivalents.
