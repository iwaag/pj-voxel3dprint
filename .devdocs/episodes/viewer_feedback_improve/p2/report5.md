# p2 step 5 report: fur at printer pitch and dilute-white scattering

## Done

- **`work/halftone/fur_halftone_crop.py`** (+ `build_fur_crop.sh`): a direct
  crop generator, like p1's agate crop. It imports
  `work/fur/export_floating_fur_voxelprint.py` and re-runs its `hairs()`
  (same seed, all 6800 hairs drawn on the full printer grid into a memmap,
  5 s), the undercoat-core formula and the `noise`/`REC` dither on the global
  printer indices. For a 6 × 6 mm window (x 26–32, y 12–18 mm), all 358
  layers (142 × 71 × 358 voxels of 42.3 × 84.7 × 14 µm), it writes:
  - `fur-crop-dither`: the six resins as printed;
  - `fur-crop-effective`: the semantic fur labels on the printer grid
    (per-material effective media);
  - `fur-crop-review`: the same window cut from the 0.2 mm review volume the
    viewer shows.
  The conversion takes 19 min, almost all of it `vdbmat convert` on 3.6 M
  anisotropic voxels. The printer and review windows have the same amount
  of hair: 9.0 % vs 9.7 % of voxels, 62 % vs 63 % of columns.
- **`work/halftone/fur_crop_compare.py`**: renders the crops with
  `work/compare/stages/fur-crop.stage.json` (dome preset, camera from the
  Unknown-9 direction) and compares them with the same window warped out of
  the three photos and the step 3 matched render. It writes
  `fur-crop-panel.png` and `fur-crop-stats.md`.
- **`work/halftone/fur_core_contrast.py`**: on the full slab (face window
  x 10–50, y 6–24 mm), Lab of the undercoat-core stripes (the top 30 % of
  columns by core voxels) vs the gaps (no core), in the photos and in
  renders camera-matched to Unknown-9.
- Dilute-white tint: tested with the fitted library (v3b, whose white
  σs′ came out 9512/10141/16631, B/R 1.75, from step 4) and with a
  diagnostic variant with white σs′ × 3 (`.local/floating-fur/p2s5-whitex3.json`,
  not kept).

## Commands

```
work/halftone/build_fur_crop.sh work/resins/vero-j850-provisional-v2.json v2        # 19 min
C=.local/floating-fur/halftone-crop-v2; O=.local/real_print/batch1/renders-p2/step5
S=$(realpath work/compare/stages/fur-crop.stage.json)
for k in review effective dither; do
  work/compare/render_stage.sh $C/fur-crop-$k-optical.zarr $O/fur-crop-$k-v2.png --stage-config $S --spp 256 --denoise
done                                                                                  # 65 / 341 / 343 s
# dither crop with the v3b resins and with white x3 (resin mappings via agate_halftone_crop.resin_mapping)
vdbmat/.venv/bin/python work/halftone/fur_crop_compare.py $C $O --renders \
  "review 0.2mm v2=$O/fur-crop-review-v2.png" "effective printer-pitch v2=$O/fur-crop-effective-v2.png" \
  "dither printer-pitch v2=$O/fur-crop-dither-v2.png" "dither printer-pitch v3b=$O/fur-crop-dither-v3b.png" \
  "dither printer-pitch white x3=$O/fur-crop-dither-s5wx3.png"
S3=.local/real_print/batch1/renders-p2
vdbmat/.venv/bin/python work/halftone/fur_core_contrast.py "render v2=$S3/step3/fur-Unknown-9-v2.png" \
  "render v3a=$S3/step4/fur-Unknown-9-v3a.png" "render v3b=$S3/step4b/fur-Unknown-9-v3b.png" \
  "render v3b white σs×3=$S3/step5/fur-Unknown-9-s5wx3.png"
```

## Images

- `.local/real_print/batch1/renders-p2/step5/fur-crop-panel.png`: the
  window in the three photos | matched v2 render (0.2 mm) | review 0.2 mm |
  printer-pitch effective | printer-pitch dither (v2, v3b, white × 3).
- `…/step5/fur-crop-{review,effective,dither}-v2.png`, `fur-crop-dither-{v3b,s5wx3}.png`,
  `fur-Unknown-9-s5wx3.png`.

## Result 1: printer pitch vs review grid is not the cause

6 × 6 mm window, same camera, same library (v2):

| render | mean L a b | L std | darker 30 % | brighter 30 % |
|---|---|---:|---|---|
| review 0.2 mm | 58 +0.1 −0.4 | 11.0 | 44 | 70 |
| printer pitch, effective media | 58 +0.1 −0.4 | 11.1 | 44 | 70 |
| printer pitch, real dither | 57 +0.1 −0.4 | 11.1 | 44 | 70 |

The three are statistically identical: the same mean, the same stripe
contrast. At printer pitch the individual hairs are visible as thin
squiggles and the dither adds grain, but the colour and the stripes do not
change. **The review grid does not explain the fur.** The viewer does not
need a finer grid or a print-stack render for this kind of material. (The
crops are darker than the full slab, and their gaps much darker, because a
lone 6 mm cube shades the floor under it. They are compared only with each
other.)

## Result 2: what the photo shows, and what differs

Stripes of undercoat core vs the gaps between them (full slab, face
window 40 × 18 mm, `fur-core-contrast.md`):

| image | core L a b | gap L a b | ΔL core − gap | Δb core − gap | corr(L, core) | corr(b, core) |
|---|---|---|---:|---:|---:|---:|
| photo Unknown-9 (top-down, el 73°) | 64 −0.0 −3.7 | 71 +0.8 +0.5 | **−6.6** | **−4.2** | −0.39 | −0.64 |
| photo Unknown-8 (el 56°) | 70 +0.6 −0.2 | 71 +0.9 +0.4 | −1.1 | −0.6 | −0.06 | −0.18 |
| photo Unknown-7 (el 73°, other side) | 66 +0.2 +2.4 | 63 −0.2 +1.6 | +3.3 | +0.8 | +0.25 | +0.18 |
| render v2 (matched to U9) | 72 +0.3 +1.2 | 75 +0.2 +1.4 | −2.9 | −0.2 | −0.37 | −0.16 |
| render v3a | 68 −0.0 +2.5 | 71 +0.4 +4.0 | −3.5 | −1.4 | −0.38 | −0.32 |
| **render v3b (= v3)** | 66 −0.2 +1.7 | 70 −0.5 +3.5 | −3.5 | −1.9 | −0.37 | −0.33 |
| render v3b, white σs′ × 3 | 65 −0.5 +3.0 | 65 −0.7 +5.0 | +0.0 | −2.1 | −0.02 | −0.26 |

- The core sits 1.2–3.9 mm below the top. Seen at an angle through the
  refracting top face, it shifts sideways by about 1 mm, a third of the 3 mm
  stripe period. So only the top-down photo (Unknown-9) gives a clean
  stripe-vs-gap comparison. The two oblique photos wash it out or flip it
  (parallax), which is also why step 2 saw the "undercoat / tuft" regions
  swap order between photos.
- In the photo and in the render alike, **the core stripes are darker than
  the gaps**: the gaps show lit paper through clear resin. The p1 phrase
  "white tufts between opaque stripes" describes the same thing: the gaps
  read white.
- What differs is **tint and contrast**. The photo's core is blue-grey (b −3.7,
  Δb −4.2), while the v2 render is neutral to yellowish (Δb −0.2) with half
  the lightness contrast.
- **Dilute-white tint: kept.** The fitted v3 white (σs′ B/R 1.75) moves
  the core tint halfway toward the photo (Δb −0.2 → −1.9) and the contrast a
  little (−2.9 → −3.5), and it does not hurt the agate: the agate white band
  is 53 −1 +1 vs photo 56 +0 +1 (ΔE 2.7, better than v2's 3.7). No separate
  per-recipe tint rule is needed. The library shape does the job.
- **More white scattering: rejected.** White σs′ × 3 removes the stripe
  contrast (ΔL 0.0) and makes everything greyer.
- Remaining gap: the whole fur render is still yellower than the photo
  (gap b +3.5 vs +0.5, core +1.7 vs −3.7). In a white-in-clear medium,
  light diffuses over centimetres, so the colour is set by the *shape* of
  the small UltraClear and white absorptions (v3 clear 9/12/11 per m)
  times the path length. Step 4 showed the same yellowing on the homogeneous
  18 % white slab. That shape cannot be recovered from these photos. It
  needs a clear-slab transmission coupon and a white-in-clear series.

**Which effect explains the undercoat:** not the grid. The wavelength shape
of the dilute white (the tint) explains part of the blue-grey. The rest is
absorption shape over long diffusion paths, which needs coupons.

## Skipped / notes

- `MaterialMixtureVolume` for the fur review grid (optional): not done.
  Result 1 shows that a 0.2 mm per-material grid already gives the same
  window statistics as the printed dither, so a fractional-resin review
  grid would not change the fur.
- The crop and matched renders use depth 32. The fur region values differ
  by < 1 L between depth 32 and 64 (p1 report4), and the step 4 depth
  finding concerns large homogeneous whites.
- The diagnostic white × 3 library and its zarrs stay under `.local/` only.
