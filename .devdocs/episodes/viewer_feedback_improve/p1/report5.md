# p1 step 5 report — halftone-scale sanity check (agate crop)

## Done

- `work/halftone/agate_halftone_crop.py` builds a direct crop generator instead
  of export → slice crop → `convert-image-stack`. It imports
  `work/agate/export_menou_voxelprint.py` and runs its per-slice logic
  (`hash_uniform`, `RECIPES`, shell rule) on the **global** printer indices of
  the crop. The six-resin labels are therefore the voxels that were actually
  printed there, and producing them takes < 1 s instead of a full
  1418×354×358 export. From the same crop it writes:
  - `agate-crop-dither.voxels.json`: labels 1..6 = white, black, clear, cyan,
    magenta, yellow;
  - `agate-crop-effective.voxels.json`: the undithered semantic agate ids
    (1..14, including the 0.3 mm shell) on **the same printer grid**, so the
    two volumes have identical geometry;
  - `vero6-resins.optical-mapping.json`: one material per resin, straight from
    the library (single IOR 1.52, so the dither creates no internal interfaces).
- `work/halftone/build_agate_crop.sh LIBRARY TAG`: generator → `import-voxels`
  → `convert`. The dither volume goes through the resin mapping; the effective
  volume goes through the case's print-aware mapping
  (`.local/pink-agate-v3/print-aware-<TAG>/agate.optical-mapping.json`). The
  only difference between the two renders is dither vs per-voxel linear mixing.
  12 min, almost all of it `convert` on 2.5 M anisotropic voxels.
- Crop: x 34.4–39.4 mm, y 14.4–19.4 mm, all 358 layers, i.e. 119 × 60 × 358
  voxels of 42.3 × 84.7 × 14 µm. It is an interior window with all 14 agate
  materials, bands crossing the top. Resin fractions of the dither match the
  recipe expectation to 1e-4 (white 0.137, black 0.035, clear 0.531, cyan 0.137,
  magenta 0.121, yellow 0.038).

```
work/halftone/build_agate_crop.sh work/resins/vero-j850-provisional-v2.json v2a
C=.local/pink-agate-v3/halftone-crop-v2a; O=.local/real_print/batch1/renders-p1/step5
work/compare/render_stage.sh $C/agate-crop-dither-optical.zarr    $O/agate-crop-dither.png    --spp 256   # 393 s
work/compare/render_stage.sh $C/agate-crop-effective-optical.zarr $O/agate-crop-effective.png --spp 256   # 307 s
```

Side by side: `.local/real_print/batch1/renders-p1/step5/panel-agate-crop-dither-vs-effective.png`.
(print-photo preset, 512², depth 32, no denoise; the camera frames the 5 mm cube.)

## Result

Mean sRGB (8 bit) and high-pass luminance std (pixel − 7×7 box mean) per band:

| band | dither mean | effective mean | dither grain | effective grain |
|---|---|---|---|---|
| teal (top) | 76, 91, 99 | 76, 89, 97 | 8.8 | 5.6 |
| pink | 111, 87, 99 | 110, 87, 98 | 8.9 | 5.8 |
| dark | 65, 64, 63 | 64, 63, 63 | 9.1 | 6.6 |
| white | 140, 127, 138 | 141, 128, 138 | 8.2 | 6.1 |
| whole object | 140.0, 138.9, 144.1 | 139.6, 138.4, 143.3 | | |

The effective-render grain is the Monte Carlo noise floor (spp 256). The dither
adds ≈ √(8.8² − 5.8²) ≈ 6.6 / 255 of real grain at 3–6 px per dither cell,
which matches the fine grain visible along the bands in the case1 photo. The
dither render also has slightly crisper band edges.

**Conclusion:** with the v2a library, per-voxel linear mixing gives the same
mean colour as the printed dither (≤ 2/255 per band). The effective-medium
model is enough for colour, and the step 7 library values are not
compensating for mixing bias. The dither only adds a fine grain visible in
close-ups.

For phase 2: this holds while the pigment mean free path (white σs 10 000/m →
0.1 mm; CMY ~0.5–1 mm) is at least the dither cell size (42–85 µm). If coupon
measurements give much larger σs, e.g. white > 30 000/m, rerun this crop with
the measured library: linear mixing could become biased there.

## Skipped / notes

- `vdbmat-utils convert-image-stack` route not used. The generator reuses the
  export code, so the labels are the same as in the printed slices, and reading
  PNGs back adds nothing.
- Cut side faces of the crop look pale: grazing-angle Fresnel reflection of
  the bright floor. That affects both renders equally.
