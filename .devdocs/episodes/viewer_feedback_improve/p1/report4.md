# p1 step 4 report — clear shell and depth check

## Done

Renders (print-photo preset, 512², spp 128, v2a library, `--rr-depth` = `--max-depth`
so roulette stays off) in `.local/real_print/batch1/renders-p1/step4/`:

```
z=.local/floating-fur/print-aware-v2a/fur-optical.zarr        # agate: .local/pink-agate-v3/print-aware-v2a/agate-optical.zarr
O=.local/real_print/batch1/renders-p1/step4
work/compare/render_stage.sh $z $O/fur-v2a-d$D.png --max-depth $D --rr-depth $D          # D = 8, 32, 64 (agate likewise)
work/compare/render_stage.sh $z $O/fur-v2a-d32-spp512-dn.png --spp 512 --denoise        # also writes *.raw.png
CK=$(realpath work/compare/stages/print-photo-checker.stage.json)
work/compare/render_stage.sh $z $O/fur-v2a-d$D-checker.png --stage-config $CK --max-depth $D --rr-depth $D   # D = 8, 32
work/compare/render_stage.sh .local/pink-agate-v3/print-aware-v2a/agate-optical.zarr $O/agate-v2a-d32-checker.png --stage-config $CK
```

Times: fur d8/32/64 77/140/154 s, agate 92/169/260 s, fur spp512+denoise 385 s,
checker renders 77–174 s.

New file: `work/compare/stages/print-photo-checker.stage.json` is the print-photo
preset with a 48× grey/black checker floor. It is a diagnostic stage and was not
added to the shipped presets: seen over a uniform floor, a clear block and a
frosted block look the same.

Panels (added next to the renders):
`panel-fur-depth-8-32-64.png`, `panel-agate-depth-8-32-64.png`,
`panel-checker-fur-d8-d32-agate-d32.png`,
`panel-fur-denoise-crop-spp128-raw512-dn512.png` (3× crop of the hair field).

## Result

- **Fur material 1 is truly clear.** In print-aware v2a it is 100 % UltraClear:
  σs 10/m, σa (5, 8, 15)/m. Over the checker floor the checker shows through the
  margin undistorted and at full contrast, at d8 and at d32. The step 1 "frosted"
  shell came from the semantic mapping plus fireflies (report3). In the
  print-photo renders it still *looks* milky because the stage is uniform: a clear
  block that refracts a featureless grey floor and a uniform ambient light shows
  no edges. The photo's bright, sharp edges are the room reflected in the faces
  (dark surroundings, one overhead light). That is a stage gap, not a material or
  depth gap. It is listed for phase 2's photo protocol / stage.
- **Depth.** Mean |Δ| per 8-bit channel:

  | case | d8 vs d32 | d32 vs d64 |
  |---|---|---|
  | fur | 10.2 | 0.68 |
  | agate | 1.7 | 0.04 |

  At d8 the fur hair mass renders dark grey: paths inside the dense white
  scatterers get cut off. The clear shell itself is already right at d8. The
  0.3 mm agate shell and the opaque agate body barely depend on depth.
  **Depth 32 (rr_depth 32) is enough.** It is already the print-photo preset
  default (step 3), so the preset stays as it is.
- **Denoiser.** Hair-field crop, luminance std in two frequency bands:

  | image | < 3 px | 5–17 px |
  |---|---|---|
  | spp128 raw | 6.30 | 3.34 |
  | spp512 raw | 3.86 | 3.14 |
  | spp512 OptiX | 1.99 | 3.08 |

  Going from spp 128 to 512 halves the noise, so the spp512 raw is ≈ 3.15 noise
  plus ≈ 2.2 real fine texture. The denoised image keeps ≈ 2.0, so the denoiser
  does **not** smear the internal white texture. It keeps the mid-scale hair
  structure and most of the fine detail. The mean changes by 0.02/255.
  Denoising is fine for the final pictures.

## Skipped

- Optional matte support-facing faces (`roughdielectric` on −Z faces): not done.
  The bottom faces are not visible from the photo cameras. The remaining finish
  gap (amber top looks satin in the photos, the renders look glassy) is on the
  top face, which J850 glossy mode prints glossy. The most likely cause is the
  uniform environment reflected in that face, not the surface roughness. Left
  for phase 2 together with the stage/photo protocol.
