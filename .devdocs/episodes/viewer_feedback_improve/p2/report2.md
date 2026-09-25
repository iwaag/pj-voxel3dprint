# p2 step 2 report: are the p1 gaps real? Photo consistency and tone curve

## Done

- **Same physical regions in every photo.** A region is now a rectangle in
  slab millimetres on the visible face and is mapped into each image by the
  top-face homography. It is no longer a per-image rectangle.
  - Corner picks: the four top-face corners of all nine photos, read by eye
    from 3× zoomed, gridded crops (the user was not needed). In the spec they
    are stored in model-corner order, (0,0) (60,0) (60,30) (0,30) mm.
  - Orientation: which picked corner is which model corner was decided by
    normalised cross-correlation of the warped face against the step 1
    render's warped top face (4 rotations × top/bottom-up):
    agate 0.60 / 0.84 / 0.66 against ≤ 0.12 for the next candidate; fur
    0.58–0.64 against ≤ 0.53. The amber veins are nearly parallel stripes,
    so there the texture was correlated with the label volume's vein map
    (outer 1 mm).
  - Renders: corners come from projecting the slab through the stage camera,
    checked against the render (`work/compare/slab.py`).
  - Registration check: `…/step2/{agate,amber,fur}-faces.png` (every image
    warped to 60 × 30 mm and stacked). Agate bands line up across the three
    photos and the render to about 0.5 mm.
- **Finding: all three amber photos show the bottom (support) face.** The
  bottom-up assignment wins clearly (Unknown-4: 0.47 vs 0.04, Unknown-6:
  0.24 vs 0.08; Unknown-5 weaker, 0.10 vs 0.07, but its speck lands where
  Unknown-4's does). The bottom layers z 0–4 match slightly better than the
  top layers (0.47 vs 0.41, 0.24 vs 0.22). No export script flips anything
  (`[::-1]`/flip/transpose: none). So the "satin" amber top in p1 is the
  **matte support face**, not a glossy top. The v2 amber render shows the top
  layer, where only 32 % of pixels match the bottom layer. Step 3 must render
  amber bottom-up and consider a rough finish on that face.
- New scripts (all under `work/compare/`):
  - `slab.py`: stage camera → pinhole, homography, mm-rect → image mask,
    face warp.
  - `pick_regions.py` → `specs/batch1-regions-mm.json`: per case and face,
    for each material the 2 mm square with the highest area fraction of that
    material (kept if ≥ 0.45). Its full composition is stored, because agate
    bands are only 0.4–1 mm wide and a region is rarely pure. There is also a
    grid of 55 tiles of 5 mm. Agate: 12 of 14 materials (purity 0.53–1.0;
    smoky-blue-black and the shell have no 2 mm spot). Amber: the 5 host
    classes per face (veins are thinner than 2 mm). Fur: margin / undercoat /
    tuft / dark by column hair content.
  - `region_table.py`: spec → per-image, per-region white-normalised linear
    RGB and Lab, plus the darkest and brightest 1 % of the face interior
    (**p01 / p99**, now a standard column), with an optional `photo_tone`
    gamma and `--overlay`.
  - `face_sheet.py`: the registration sheets above.
  - `tone_consistency.py`: the analysis below.
- Spec `specs/batch1-p2s2.json` (three photos per case with white patches and
  corners, plus the step 1 dome render).

## Commands

```
vdbmat/.venv/bin/python work/compare/pick_regions.py work/compare/specs/batch1-regions-mm.json
O=.local/real_print/batch1/renders-p2/step2
vdbmat/.venv/bin/python work/compare/region_table.py work/compare/specs/batch1-p2s2.json $O/regions-p2s2.json --md $O/regions-p2s2.md --overlay $O/overlay
vdbmat/.venv/bin/python work/compare/face_sheet.py work/compare/specs/batch1-p2s2.json $O
vdbmat/.venv/bin/python work/compare/tone_consistency.py $O/regions-p2s2.json $O     # consistency.md, tone.md, tone.png
```

Installed into `vdbmat/.venv` (not in its lock file): `scipy`,
`opencv-python-headless`, `matplotlib`, via
`uv pip install --python vdbmat/.venv/bin/python …`.

## Result 1: the three photos disagree by more than 3 L

5 mm tiles (the same physical area in all three photos):

| case | median L range | 90th pct L range | median pairwise ΔE |
|---|---:|---:|---:|
| agate | 6.3 | 8.9 | 4.8 |
| amber | 4.2 | 5.9 | 8.6 |
| fur | 7.8 | 11.7 | 6.5 |

This is above the plan's ~3 L threshold everywhere. The main part is a
**per-photo exposure-normalisation error**, not a tone curve (Result 2).
Fitted photo/render luminance scale per photo (fit A, g = 1):

| case | photo 0 (the p1 reference) | photo 1 | photo 2 |
|---|---:|---:|---:|
| agate | Unknown-2 **1.11** | Unknown 1.56 | Unknown-3 1.34 |
| amber | Unknown-5 **1.07** | Unknown-4 1.44 | Unknown-6 1.35 |
| fur | Unknown-9 0.76 | Unknown-8 0.83 | Unknown-7 0.70 |

The near-top-down photos that p1 used (Unknown-2, Unknown-5) come out
darkest: 0.70–0.75× the other two. Most likely the phone and photographer
shade the slab more than the paper patch next to it. Normalising on white
paper next to the object therefore leaves ±15–20 % exposure uncertainty per
photo (≈ ±4–7 L at L 30–60). **p1's "pinks −8 L" was measured on the darkest
photo:** averaged over the three photos, the agate is brighter than in
Unknown-2 alone, and with the step 1 stage the render is darker than all
three (scale 1.1–1.6).

## Result 2: a tone curve does not explain it

Model y_photo = s_p · y_render^g (y = luminance relative to paper white,
residuals in L\*), 345 samples (agate and fur tiles, amber host classes):

| fit | g | RMS ΔL | per case |
|---|---|---:|---|
| A: scale per photo, g = 1 | 1 | 3.28 | agate 2.0, amber 1.6, fur 4.3 |
| B: one g for all nine photos | 0.66 | 3.14 | agate 2.1, amber 1.8, fur 4.0 |
| C: g per case | agate 0.90, amber 1.02, fur 0.13 | 2.97 | agate 2.0, amber 1.6, fur 3.8 |

Within a case the tiles span a narrow range of luminance, so B's g = 0.66 is
set by the offsets *between* cases, i.e. by render error, not by the
phone. Only the agate bands span a wide range (black to white, ~20× in Y).
Fitted per photo there:

| photo | s | g | RMS ΔL (g free) | RMS ΔL (g = 1) |
|---|---:|---:|---:|---:|
| Unknown-2 | 0.70 | 0.85 | 3.9 | 4.2 |
| Unknown | 1.36 | 0.93 | 3.9 | 4.0 |
| Unknown-3 | 1.31 | 1.05 | 3.2 | 3.3 |

g stays within 0.85–1.05, and freeing it gains ≤ 0.3 L. **No `photo_tone` is
applied.** A single gamma does not explain the residual for all three cases,
and within agate the phone's tone curve is close to linear relative to paper
white. What remains is (a) the per-photo exposure scale and (b) region-level
render error. The `photo_tone` option stays in `region_table.py` (unused).

## Result 3: per region, photo-limited or render-limited

Verdict: *render-limited* when the render (step 1 dome, v2 library) is
further from the mean of the three photos than the photos are from each
other (ΔE_render > largest pairwise photo ΔE). Otherwise *photo-limited*.
Full table: `.local/real_print/batch1/renders-p2/step2/consistency.md`.

| case | region | L photos | photo spread ΔE | render L | ΔE render→mean | verdict |
|---|---|---|---:|---:|---:|---|
| agate | pale-pink | 48/54/49 | 9.5 | 46 | 11.5 | render |
| agate | dusty-rose | 33/50/32 | 24.3 | 33 | 9.5 | photo |
| agate | mauve | 24/36/38 | 14.5 | 34 | 5.8 | photo |
| agate | lavender | 33/43/35 | 9.8 | 34 | 12.1 | render |
| agate | blue-grey | 27/32/27 | 5.5 | 26 | 7.8 | render |
| agate | teal | 24/28/22 | 6.4 | 23 | 4.3 | photo |
| agate | deep-teal | 21/25/18 | 6.5 | 19 | 3.3 | photo |
| agate | white | 46/64/54 | 18.7 | 53 | 3.7 | photo |
| agate | milky-white | 50/58/55 | 9.0 | 46 | 9.2 | render |
| agate | light-tan | 29/36/30 | 7.7 | 27 | 4.6 | photo |
| agate | translucent-black | 18/23/17 | 5.5 | 12 | 7.4 | render |
| agate | clear-band | 38/46/49 | 12.0 | 41 | 12.4 | render |
| amber | host-80 | 24/28/26 | 12.1 | 22 | 7.5 | photo |
| amber | host-85 | 23/27/28 | 10.6 | 24 | 3.2 | photo |
| amber | host-90 | 31/35/33 | 8.3 | 27 | 8.8 | render |
| amber | host-95 | 26/33/31 | 9.8 | 27 | 10.5 | render |
| amber | host-100 | 28/31/30 | 6.9 | 27 | 10.1 | render |
| fur | margin | 64/71/82 | 18.6 | 88 | 15.0 | photo |
| fur | undercoat | 67/72/67 | 5.7 | 75 | 6.3 | render |
| fur | tuft | 71/65/69 | 5.9 | 76 | 7.8 | render |
| fur | dark | 57/69/62 | 12.1 | 69 | 7.5 | photo |

(amber: the render region is the same host class on the top face, the photo
region on the bottom face.)

Totals: 13 render-limited, 10 photo-limited (whole-face means included:
agate and fur render-limited). What the render-limited ones say, beyond
lightness:
- agate pale-pink / lavender / clear-band / blue-grey: hue. The render's
  pinks and pink clear band are much less red (a +14–18 vs +23–31), and
  lavender / blue-grey are too green (a −9/−10 vs 0/−3). This is the
  magenta / cyan balance, which the fit can move.
- agate translucent-black: 12 vs 17–23 L (render too dark).
- amber hosts 90–100: too little chroma (a +1–2 vs +6–12). This is the p1
  "less orange" gap, now seen on the correct face.
- fur undercoat / tuft / whole face: the render is 5–10 L too bright and
  the tuft/undercoat contrast is reversed in two of three photos. That is
  step 5's subject.

p01 / p99 of the face (luminance relative to the patch; photos … | render):
agate 0.021–0.025 / 0.29–0.42 | 0.012 / 0.24; amber 0.021–0.037 /
0.08–0.10 | 0.022 / 0.065; fur 0.17–0.26 / 0.68–0.72 | 0.33 / 0.96.

## What this means for steps 3–4

- Observations for the fit are the **mean of the three photos** (linear,
  after white normalisation). The photo spread per region is the noise
  scale: weight = 1 / max(spread, 3 ΔE).
- Fitting per-photo exposure factors would be a photo nuisance, not a case
  constant. It is tempting (it removes ±20 %), but it would also absorb any
  global lightness error of the library. Not done. Only the three-photo
  mean is used.
- Amber must be compared bottom-up.

## Skipped / notes

- Corner picks are by eye (±3–5 px ≈ ±0.2 mm on 2048² photos). They are in
  `batch1-p2s2.json` and will move to `batch1-v3.json` in step 3.
- The fur margin (64/71/82) depends on what the clear block refracts, so it
  varies with angle. It is not a colour region.
- The white patches for the six photos p1 did not use were chosen by eye
  on lit paper next to the slab.
