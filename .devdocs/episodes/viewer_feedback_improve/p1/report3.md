# p1 step 3 report — resin library and recipe→mapping tool

## Done

- `work/resins/vero-j850-provisional-v2.json`: six resins (white, black,
  UltraClear, cyan, magenta, yellow) with σa/σs (1/m, linear sRGB), g, ior,
  `names` (GrabCAD/export spellings), `source`/`note`, `calibration_status:
  provisional-uncalibrated`, `changelog`. Values = the plan's prior table, mid
  range for σs (white 10000, CMY 1000, clear 10, black 300), **g = 0** and
  **one IOR (1.52) for every resin** (reason below).
- `work/resins/recipes_to_mapping.py`: library + `*.resin-recipes.json` +
  semantic mapping (ids/names/basis) → print-aware `*.optical-mapping.json`,
  linear volume-fraction mixing of σa, σs, IOR; scattering-weighted g.
  Replaces `work/amber/build_print_preview_mapping.py`'s per-case `BASE`
  (left in place: it reproduces the archived v1 mapping, see
  `rebuild_batch1_sources.sh`).
- `work/resins/extract_recipes.py`: writes an export script's
  `*.resin-recipes.json` (same schema) by importing its `RESINS`/`RECIPES`
  globals — the three batch1 staging directories were never archived and
  re-exporting slices just for the recipe table is slow.
- `work/resins/build_print_aware.sh LIBRARY TAG`: extract → mapping →
  `vdbmat convert` for agate/amber/fur in parallel (~3 min) into
  `.local/<case>/print-aware-<TAG>/`. This step's run is tag **v2a**
  (library as committed); the frozen **v2** outputs come from step 7.
  ```
  work/resins/build_print_aware.sh work/resins/vero-j850-provisional-v2.json v2a
  work/compare/render_stage.sh .local/pink-agate-v3/print-aware-v2a/agate-optical.zarr .local/real_print/batch1/renders-p1/step3/agate-v2a.png
  work/compare/render_stage.sh .local/amber-branching/print-aware-v2a/amber-optical.zarr .local/real_print/batch1/renders-p1/step3/amber-v2a.png
  work/compare/render_stage.sh .local/floating-fur/print-aware-v2a/fur-optical.zarr .local/real_print/batch1/renders-p1/step3/fur-v2a.png
  ```
  (print-photo preset: 512², spp 128, depth 32, rr_depth 32; ~130–190 s each.)
  Added to `contact-sheet-v0.png`.
- **Schema/renderer change: `render.rr_depth`** (stage-config 1.3.0, default 5
  = Mitsuba default; `--rr-depth` CLI; **rr depth** GUI field; optional
  `render.rr_depth` in viewer sessions; digest keeps the 1.2.0 form while
  ambient and rr_depth are at their defaults). The print-photo preset sets
  `rr_depth = max_depth = 32` (roulette off). vdbmat tests 710 passed.

## Result

| case | v2a @ print-photo |
|---|---|
| agate | opaque, sharp bands, dark teal/blue-black dominant, pale bands near white. Pinks are magenta-pink; the photo's are salmon/coral |
| amber | opaque dark brown with fine dark veins, low vein contrast like the photo. A bit too dark/neutral; the photo is more olive-orange |
| fur | clear host, the paper shows through the margin; hair mass reads as an opaque, matte grey-white layer. It is greyer than the photo's light blue-grey undercoat, and the dark hairs show as dark speckle |

Done criterion met: agate and amber are opaque at roughly the right lightness,
and fur's host stays clear while the hair mass goes opaque. Colour tuning is
left for step 7.

Example mixed values (σt, 1/m): agate pinks 2200–3700, teals 1900–4500, white
bands ~6900 (albedo 0.99), translucent black ~3750 (albedo 0.09). Amber hosts
218–2039 (69–96 % clear), veins 1400–5600.

## Library values changed while getting there, and why

None yet: v2a = the plan's prior table. What had to change was the renderer, and one library-wide decision:

1. **Single IOR.** `prepare_mitsuba_scene` builds a dielectric interior mesh
   at every voxel face where the IOR differs. With per-resin IOR (old `BASE`:
   1.52/1.53/1.54), linear mixing gives every material a slightly different
   IOR, so every band/hair boundary becomes a refracting surface. That eats
   path depth and causes the dark rims seen in step 2. It also slows scene
   preparation (ASCII PLY per group). Real index differences between cured
   Vero resins (~0.01) reflect < 0.01 %. All resins are now 1.52, so the
   mapping produces no internal interfaces.
2. **Russian roulette fireflies (fur).** The first fur render had fireflies up
   to 700–1800 under ambient radiance 0.75, i.e. path weights of ~1000×, on
   the object *and* the floor. Diagnosis (256², 64 spp, key light removed):
   - grey coefficients: still present, so not the RGB hero-channel weighting;
   - clear host σ = 0: still present;
   - hair σ × 0.1: gone;
   - `rr_depth` 10000: gone (max 0.65).

   Dense, nearly white scatterers in a clear host give long paths. Roulette
   (from depth 5) then kills most of them and boosts the survivors by 1/q.
   Agate and amber paths are short (absorbing), so they are not affected.
   Turning roulette off roughly doubles render time.

## Skipped / notes

- `MaterialMixtureVolume` path (per-voxel resin fractions) not used: per-
  material pre-mixed constants are equivalent for effective-medium mixing and
  need no change to the voxel data.
- Plan said outputs under `.local/<case>/print-aware-v2/`; iteration outputs
  use `print-aware-v2a/`, the frozen library will be built as `print-aware-v2/`
  in step 7.
- Denoise and spp ≥ 256 are left for the final compare renders (step 6/7).
