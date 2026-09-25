# viewer_feedback_improve Phase 1 — Close the photo/render gap with what we already have

Parent: `.devdocs/episodes/viewer_feedback_improve/braindump.md`.
Evidence: `.local/real_print/batch1/` (J850, HQ 14 µm, Vero UltraClear used as "clear").
Scope: no new prints, no new measurements. Only data, scripts and renders that
exist in this checkout today. Calibration coupons and photo protocol are Phase 2.

## Why this phase exists

Photos and renders of all three cases differ in the same direction: the render
shows a transparent block with faint colour floating inside; the print is an
opaque, saturated, slightly grainy object (case1 agate, case2 amber) or a truly
clear block with an opaque white interior (case3 fur). Two root causes, in order
of weight:

1. **The rendered optical mapping is not the printed material.** The archived
   case1/case3 renders were made from the *semantic* mappings (e.g. `amber-host-80`,
   `sigma_s` ≈ 10/m, i.e. nearly non-scattering resin). The printer received
   halftone recipes over six Vero resins (`work/*/export_*_voxelprint.py`,
   `RECIPES`). Only amber had a "print-aware" mapping
   (`work/amber/build_print_preview_mapping.py`) and even that uses provisional
   per-resin values that are 1–2 orders of magnitude too transparent for
   pigmented Vero.
2. **The stage is an art stage, not a photo stage.** Dark gradient floor, teal
   backdrop, warm key light `(12, 11, 9)`, camera per case. Photos: white paper,
   soft overhead room light, neutral phone white balance, elevation ≈ 60–75°.

Fix 1 first; 2 is cheap and makes every later comparison honest.

## Facts found during planning (use them, don't re-derive)

- Optical mapping schema: `vdbmat/src/vdbmat/optics/config.py` —
  `sigma_a_rgb_per_m`, `sigma_s_rgb_per_m`, `g`, `ior` per `material_id`,
  `mixing_rule = linear-volume-fraction-v1`, `calibration_status` string.
  `MaterialMixtureVolume` (per-voxel fractions) is already supported by
  `optics/mapping.py::_map_mixture`, so recipes can also be expressed as
  mixture volumes instead of pre-mixed per-material constants.
- Mitsuba scene: `vdbmat/src/vdbmat/exporters/mitsuba.py::prepare_mitsuba_scene`.
  `volpath` integrator, `heterogeneous` medium with `sigma_t`/`albedo` grid
  volumes (`filter_type: nearest`, scale 1, metres), HG phase with a single
  global `g`, exterior boundary = smooth `dielectric` (or `null` when
  index-matched), plus one canonical white `backlight` rectangle behind the
  object (radiance 1). IOR is per-interface only, not a field.
- Stage: `vdbmat/examples/pipeline_run/demo/mitsuba_stage.py` (`StageConfig`:
  render / backdrop / floor / key_light / camera / backlight). Floor and backdrop
  are `diffuse` planes; key light is an area rectangle. Presets live in
  `demo/presets/*.stage.json`; the viewer (`mitsuba_stage_viewer.py`) and the
  headless CLI (`mitsuba_stage_demo.py --session ... | OPTICAL_ZARR OUT.png
  --stage-config ...`) share the same resolver. `--denoise` needs `cuda_ad_rgb`.
  Output goes through `mi.util.write_bitmap` (linear → sRGB PNG, no tone
  mapping, no exposure control).
- Mapping regeneration from the viewer exists: `mitsuba_stage_regen.py` re-runs
  a bundle's `source/*.voxels.json` through a chosen `*.optical-mapping.json`.
- Recipes actually printed (white, black, clear, cyan, magenta, yellow order):
  - agate: `work/agate/export_menou_voxelprint.py` `RECIPES` (14 materials;
    0.3 mm 100 % clear shell = material 1; most colours are 28–56 % clear).
  - fur: `work/fur/export_floating_fur_voxelprint.py` `REC` (7 materials;
    material 1 = 100 % clear host; hairs are 18–48 % white in clear).
  - amber: `work/amber/build_print_preview_mapping.py` `RECIPES` + `BASE`
    (provisional per-resin optics; 69–96 % clear per material).
  Each export also wrote `<name>.resin-recipes.json` next to the slices.
- Archived renders per case: `.local/real_print/batch1/case*/data/outputs/`
  with `*.session.json` (case1: spp 512, depth 64; case2: spp 128, depth 16;
  case3: spp 128, depth 8). Case1 and case3 source zarr paths are registered in
  `work/materials/<slug>/material.json` (`.local/pink-agate-v3/...`,
  floating_fur likewise); batch1 only archived the outputs.
- Case1 photo shows fine grain along the bands (halftone visible at
  42×85 µm pitch) and a glossy top face. Case3 photo shows a perfectly clear
  shell, sharp edges, hairs rendered as matte white/grey. Case2 photo: uniform
  olive-brown, opaque, glossy, vein contrast low.
- Resin colour codes GrabCAD expects are in `printer_info/Unknown-10.jpg`
  (VeroPureWht 240/240/240 … VeroUltraClr 247/247/247). They are labels, not
  optics.

## Physical priors for the resin library (starting points, not truth)

Thinking tool: transmittance through thickness `d` ≈ `exp(-sigma_t · d)`,
diffusion depth ≈ `1 / sqrt(3 · sigma_a · sigma_s')` with
`sigma_s' = sigma_s · (1 - g)`. Slabs are 5 mm thick; case1 colours at 45 %
clear are fully opaque in the photo, so pigmented Vero must have
`sigma_t` well above ~2000 /m. Suggested first values (per metre, linear sRGB
channels R,G,B; `g = 0` with reduced scattering, which is cheaper for volpath
than a forward-peaked phase function and equivalent in the diffusive regime):

| resin | sigma_a | sigma_s (reduced) | ior | note |
|---|---|---|---|---|
| VeroPureWhite | 20, 20, 25 | 8000–15000 | 1.52 | opaque within ~0.3 mm; slight warm tint |
| VeroBlack | 15000+, all ch. | 300 | 1.52 | effectively opaque |
| Vero UltraClear | 5, 8, 15 | 5–30 | 1.51–1.53 | faint yellow; keep it truly clear |
| VeroCyan | 4000, 800, 250 | 800–1500 | 1.52 | absorbs red; is not transparent |
| VeroMagenta | 700, 4000, 1200 | 800–1500 | 1.52 | absorbs green |
| VeroYellow | 250, 500, 5000 | 800–1500 | 1.52 | absorbs blue |

Linear volume-fraction mixing is the right first model for recipes: a 40 %
pigment / 60 % clear cell has ~0.4× the pigment's coefficients. Literature with
measured Stratasys Vero coefficients (Elek et al. 2017 "Scattering-aware
texture reproduction for 3D printing"; Brunton et al. 2018 "Pushing the limits
of 3D color printing") can replace the table if the implementer has access;
cite the source in the library file when used.

## Steps

Each step ends with a short `reportN.md` in this directory: what was done,
commands, images produced (paths), what was learned, what was skipped.

### Step 1 — Evidence sheet and gap table

Goal: one place that says, per case, what was printed vs what was rendered.

- Write `.local/real_print/batch1/case*/data/provenance.md` (or one
  `batch1/provenance.md`): source voxel data path, recipe file, resin order,
  print mode, which optical mapping produced each archived PNG (semantic or
  print-aware), session camera. For case1/case3 confirm the source zarr still
  exists at the registered path.
- Make a contact-sheet script (PIL + numpy, put it under `work/compare/`):
  photo(s) left, render(s) right, same pixel height, filename captions.
  Produce `batch1/contact-sheet-v0.png`.
- Write `gap-table.md` here: per case, 3–5 concrete visible differences
  (opacity, saturation, hue, grain, gloss/edges, shadow), each tagged with the
  suspected cause (mapping / stage / render settings / unknown).

Done when: contact sheet exists and the gap table lists causes to attack.

### Step 2 — `stage-print-photo` preset

Goal: a stage that looks like the photos, reused for every comparison.

- Add `demo/presets/stage-print-photo.stage.json`: floor enabled, `solid`,
  reflectance ≈ 0.80 neutral; backdrop disabled (or solid same grey as floor);
  key light near-vertical (`direction` ≈ `(-0.3, -0.4, 1.0)`), large
  (`scale_factor` 3–4), neutral radiance chosen so the floor renders around
  0.7–0.85 linear; camera elevation ≈ 65°, azimuth to match the photo, fov 35;
  backlight radiance set to a neutral low value (it exists in every canonical
  scene; you cannot remove it from the preset, only dim it — dim it).
- If the schema is in the way (e.g. no way to disable backdrop cleanly, or you
  want an `exposure` scalar applied before `write_bitmap`), change
  `mitsuba_stage.py` and bump `format_version`. No compatibility shim for old
  presets; update the two shipped presets and the viewer binder.
- Render all three cases with this preset from their *existing* zarr
  (semantic mappings), 512², spp 128, depth 32. Add to the contact sheet.

Done when: the floor/shadow/highlight look comparable to the photos and the
remaining gap is clearly "the object", not "the room".

### Step 3 — Resin library and recipe→mapping tool

Goal: make "print-aware" the default path for all cases, driven by one shared
resin table instead of per-case constants.

- Create `work/resins/vero-j850-provisional-v2.json`: six resins with the
  optical fields above plus `source`/`note` strings and
  `calibration_status: provisional-uncalibrated`.
- Generalise `work/amber/build_print_preview_mapping.py` into
  `work/resins/recipes_to_mapping.py`: inputs = a resin library, a
  `*.resin-recipes.json` (already emitted by every export script), and the
  semantic `*.optical-mapping.json` (for ids/names); output = a print-aware
  `*.optical-mapping.json` using linear volume-fraction mixing. IOR: mix
  linearly; it barely matters here. `g`: take from library (0 recommended).
- Run it for agate, fur, amber. Regenerate optical zarr for each (pipeline via
  `vdbmat run`, or the viewer's Load/Rebuild + mapping regen path). Keep the
  outputs under `.local/<case>/print-aware-v2/`.
- Render with the Step 2 preset. Hint: opaque media need far fewer bounces
  through the volume but still need depth ≥ 32 for the dielectric shell;
  set spp ≥ 256 for the final compare, denoise on if CUDA is available.

Done when: agate and amber render opaque at roughly the right lightness, and
fur's host stays clear while hairs go opaque-white. Record which library values
you changed while getting there, and why, in the report.

### Step 4 — Clear shell and depth check (fur first)

Goal: the case3 frosted look is a render-settings bug, not a material bug.

- Confirm the fur material-1 optical values are truly clear
  (`sigma_s` ≤ 30/m). If the semantic mapping has more, the print-aware one
  from Step 3 already fixes it.
- Render the fur bundle at depth 8 / 32 / 64 with the print-photo preset and
  compare. Expect the shell to become transparent with sharp edge highlights
  as depth rises; the 0.3 mm agate shell is the same test.
- Check the denoiser is not smearing the internal white texture: compare
  `*.raw.png` against the denoised output at spp 512.
- Optional: matte support-facing faces. The J850 glossy mode leaves the top
  glossy and support-contact faces matte. If the photo edges/bottom look
  matte and the render does not, allow a `roughdielectric` (alpha 0.05–0.15)
  on faces with outward normal −Z in `prepare_mitsuba_scene`'s exterior groups.
  Only do this if Step 3/4 leave it as a visible gap.

Done when: fur shell reads as clear in the render and the depth needed is
recorded as the new default for the print-photo preset.

### Step 5 — Halftone-scale sanity check (one crop, optional but informative)

Goal: learn whether the effective-medium (per-voxel averaged) model is enough
or the visible grain needs the real dither.

- Take the printed slice stack for agate (or regenerate a small crop via the
  export script with a reduced extent), read it back as a six-resin
  material-label volume (`convert-image-stack` with the six RGB labels), map it
  through the same resin library, and render a ~5×5×5 mm crop at the printer
  pitch. Render the same crop from the 0.2 mm effective-medium zarr.
- Compare grain and mean colour. If the mean colour differs noticeably, linear
  mixing is biased (dither cells are comparable to the pigment mean free path)
  and the library values fitted in Step 3 are compensating for it; note that
  for Phase 2.

Done when: a side-by-side of the two crops exists and the conclusion is one
sentence in the report.

### Step 6 — Comparison script with exposure normalisation

Goal: stop judging by eye alone, without building a colour pipeline.

- Extend the Step 1 script: user gives a rectangle on the white paper/floor
  in both photo and render; scale each image so that patch's mean is 0.85
  (sRGB); then report mean sRGB and a rough Lab for 2–3 user-chosen object
  regions per case (e.g. agate pink band, teal band; amber host; fur hair,
  fur shell). Print a small table, embed it in the contact sheet.
- Phone JPEGs are auto-exposed and auto-white-balanced; treat all numbers as
  relative. Do not chase ΔE below ~10 in this phase.

Done when: `batch1/contact-sheet-v1.png` shows photo, semantic render,
print-aware render, and the numbers per region.

### Step 7 — Converge the library, freeze v2, write the Phase 2 wish list

- Tune only the resin library (never per-case constants) until the three cases
  move toward their photos together. Typical knobs: white `sigma_s`
  (lightness of pale bands, fur hairs), CMY `sigma_a` magnitude (saturation),
  clear `sigma_a` tint (amber/fur host hue), black `sigma_a` (vein darkness).
- Save as `vero-j850-provisional-v2.json` with a changelog; re-render the
  three finals with the print-photo preset; final contact sheet.
- `report7.md` lists: remaining gaps per case, which need measurement
  (coupon set: single-resin slabs at 0.5/1/2/4 mm, 50/50 dithers, backlit and
  reflected photos with a white reference), and what photo protocol Phase 2
  should fix (same lighting, fixed camera, white card + ruler in frame).

## Rules (kept minimal)

- Do not modify or delete anything under `.local/real_print/batch1/`
  except adding provenance notes and contact sheets. It is the evidence.
- No backward compatibility work: schemas, presets, scripts and the amber
  print-aware builder may be changed or replaced freely. If `vdbmat/src` is
  touched, keep its test suite green; everything else may live under `work/`
  or `examples/pipeline_run/demo/` with whatever structure fits.
- Every render used for comparison must be reproducible from a
  `*.session.json` or a documented command line in the step report.
- Prefer one shared resin library over per-case fudge factors; a value that
  only fixes one case is a hint that something else is wrong.

## Out of scope for this phase

New prints, photometric calibration, spectral rendering, GrabCAD-side
halftoning emulation beyond the Step 5 crop, Blender/Cycles parity.
