# p2 step 4 report: Kubelka-Munk surrogate and library fit

## Done

- **`work/resins/km_surrogate.py`**: two-flux KM (K = 2σa, S = 0.75σs′)
  with a Saunderson top boundary (n = 1.52, k2 = 0.6, no external specular
  because the glossy top reflects the dark dome room), over the paper
  backing (ρ = 0.8), normalised like the photos (paper → 0.85 sRGB). Two
  region models:
  - `region_rgb`: area mix of whole-slab materials by surface composition;
  - `region_rgb_columns` (used): every 0.2 mm voxel of a label column is a
    KM layer (R_l, T_l), stacked from the paper up with
    R = R_l + T_l² R_below / (1 − R_l R_below). A homogeneous column
    reproduces the analytic slab exactly (checked).
- **`work/resins/km_validate.py`**: homogeneous 60 × 30 × 5 mm slabs of six
  recipes, rendered on the print-photo stage (320², spp 128, **depth 256**,
  see below) and measured on the central 20 × 10 mm.
- **`work/resins/km_fit.py`**: 36 log-parameters (σa, σs′ RGB × 6 resins),
  bounds ×/÷5 and a prior pull (weight 3.0) around v2. Observations: the
  three-photo means of the 20 named regions (fur margin excluded) and
  165 tiles of 5 mm (weight 0.5; fur weight 0.5). Region weight is
  1 / max(photo spread, 3), from step 2. Prediction per region:
  `KM(p) × c_r` with `c_r = render_r / KM_r` at the library that made the
  renders. The matched Mitsuba renders therefore carry the geometry (narrow
  bands, lateral transport, slab shading, viewing angle), and KM supplies the
  parameter sensitivity. `--prior-library` keeps the prior and the bounds at
  v2 during correction iterations. About 20 s per fit.
- Libraries: `work/resins/vero-j850-provisional-v3a.json` (first fit, from
  v2 renders) and **`vero-j850-provisional-v3b.json`** (refit from v3a
  renders, the result). Both carry a `fit` block with the settings and the
  predicted sums.

## Commands

```
# surrogate validation (v2 library)
vdbmat/.venv/bin/python work/resins/km_validate.py work/resins/vero-j850-provisional-v2.json .local/km-validate/v2 --build --render
# fit 1: from the v2 matched renders (step 3)
S3=.local/real_print/batch1/renders-p2/step3; O=.local/real_print/batch1/renders-p2/step4
vdbmat/.venv/bin/python work/resins/km_fit.py $S3/regions-v3-v2.json work/resins/vero-j850-provisional-v2.json \
    work/resins/vero-j850-provisional-v3a.json --prior 3.0 --report $O/fit-v3a.md
work/resins/build_print_aware.sh work/resins/vero-j850-provisional-v3a.json v3a agate-m amber-m fur-m
ln -sfn ../step3/stages $O/stages
work/compare/render_matched.sh v3a $O --spp 256 --denoise
vdbmat/.venv/bin/python work/compare/region_table.py work/compare/specs/batch1-v3.json $O/regions-v3-v3a.json --renders v3a $O
# fit 2: surrogate-correction iteration from the v3a renders, prior/bounds still at v2
vdbmat/.venv/bin/python work/resins/km_fit.py $O/regions-v3-v3a.json work/resins/vero-j850-provisional-v3a.json \
    work/resins/vero-j850-provisional-v3b.json --prior 3.0 --prior-library work/resins/vero-j850-provisional-v2.json \
    --version-id vero-j850-provisional-v3b --report $O/fit-v3b.md
O=.local/real_print/batch1/renders-p2/step4b     # same steps with v3b
vdbmat/.venv/bin/python work/compare/region_delta.py $O/regions-v3-v2.json $O/regions-v3-v3a.json $O/regions-v3-v3b.json
vdbmat/.venv/bin/python work/compare/pixel_diff.py work/compare/specs/batch1-v3.json v3b $O
```

## Surrogate validation (homogeneous slabs, depth 256)

| material | Mitsuba (norm. linear RGB) | KM | KM / Mitsuba | ΔE |
|---|---|---|---|---:|
| agate pale-pink | 0.322, 0.100, 0.062 | 0.429, 0.141, 0.097 | 1.33, 1.41, 1.56 | 7.0 |
| agate deep-teal | 0.009, 0.021, 0.022 | 0.010, 0.029, 0.031 | 1.22, 1.37, 1.38 | 3.7 |
| agate white | 0.516, 0.443, 0.304 | 0.647, 0.518, 0.412 | 1.25, 1.17, 1.36 | 7.9 |
| amber host-85 | 0.062, 0.043, 0.011 | 0.080, 0.053, 0.012 | 1.29, 1.25, 1.11 | 4.6 |
| amber host-100 | 0.300, 0.165, 0.014 | 0.429, 0.144, 0.015 | 1.43, 0.87, 1.05 | 16.2 |
| fur undercoat (18 % white) | 0.582, 0.618, 0.474 | 0.613, 0.609, 0.608 | 1.05, 0.98, 1.28 | 12.4 |

- **The plan's ±5 % is not met.** KM runs 1.2–1.4× high on opaque and pale
  slabs, a fairly common scale (S = 0.75σs′, k2 and the stage irradiance
  constants are approximations). It cancels in `c_r`.
- The weakly scattering, translucent slabs differ in *shape*: amber host-100
  green 0.87×, fur undercoat blue 1.28×. Here most light reaches the
  paper and comes back, and long diffusion paths in Mitsuba pick up the
  small blue-leaning absorption of the clear resin (the render comes out
  yellowish, b +11 for 18 % white). KM with the same σ values stays neutral.
  So KM's colour derivatives are least reliable exactly for dilute white in
  clear, which is why fur has a low weight.

### Finding: path depth 32 truncates bright scatterers

The first validation (preset depth 32) gave KM/Mitsuba up to 2.0 for the
white slab. Rendering the white slab at depth 64 / 256 / 1024:
normalised R = 0.323 → 0.421 → 0.516 → 0.522. **At depth 32 a large
homogeneous white loses ~38 % of its reflectance.** p1's "depth 32 is
enough" was measured on the fur shell and agate (narrow absorbing bands),
and that still holds there: agate matched view at depth 256 vs 32 differs
by ≤ 2.2 ΔE per region (0.0 for most bands), and costs 875 s vs 281 s. So
the batch1 matched renders stay at depth 32 (the ≤ 2 ΔE is absorbed by
`c_r`), but the validation slabs, coupons and any large white part need
depth ≥ 256. The viewer default is decided in step 6.

## Result: Mitsuba-verified (three-photo mean vs three matched renders, 21 named regions)

| case / region | photos L a b (spread) | v2 (ΔE) | v3a (ΔE) | **v3b** (ΔE) |
|---|---|---|---|---|
| agate pale-pink | 50 +28 +13 (9.5) | 49 +16 +15 (11.7) | 50 +21 +13 (6.8) | 50 +22 +13 (**5.5**) |
| agate dusty-rose | 39 +4 +19 (24.3) | 40 +2 +7 (12.2) | 40 +6 +6 (13.8) | 40 +8 +6 (13.8) |
| agate mauve | 34 +4 +2 (14.5) | 37 −1 +5 (6.9) | 37 +2 +2 (3.8) | 36 +4 +3 (**3.2**) |
| agate lavender | 37 +0 −7 (9.8) | 41 −7 −0 (10.5) | 39 −4 −5 (4.9) | 38 −3 −5 (**4.1**) |
| agate blue-grey | 29 −3 −6 (5.5) | 35 −6 −1 (8.8) | 34 −4 −3 (5.7) | 33 −4 −3 (**4.9**) |
| agate teal | 25 −7 −7 (6.4) | 32 −6 −2 (8.2) | 29 −4 −4 (6.0) | 28 −3 −4 (**5.7**) |
| agate deep-teal | 21 −6 −5 (6.5) | 30 −5 −2 (9.2) | 28 −3 −3 (7.4) | 27 −3 −3 (7.0) |
| agate white | 56 +0 +1 (18.7) | 55 −3 +3 (3.7) | 53 −3 −1 (4.9) | 53 −1 +1 (**2.7**) |
| agate milky-white | 55 −5 −0 (9.0) | 49 −5 +2 (5.6) | 48 −4 −2 (6.7) | 48 −4 −0 (6.4) |
| agate light-tan | 32 +1 +14 (7.7) | 36 −0 +10 (6.2) | 36 +1 +10 (6.2) | 36 +2 +9 (6.0) |
| agate translucent-black | 19 −2 +1 (5.5) | 27 −0 +1 (7.9) | 27 −0 +1 (7.5) | 27 −0 +1 (7.3) |
| agate clear-band | 45 +26 +11 (12.0) | 44 +12 +12 (13.6) | 44 +15 +10 (11.0) | 43 +15 +10 (11.3) |
| amber host-80 | 26 +6 +20 (12.1) | 22 +0 +17 (8.2) | 24 +6 +21 (2.0) | 24 +5 +20 (**2.6**) |
| amber host-85 | 26 +3 +19 (10.6) | 24 −0 +18 (4.0) | 27 +7 +23 (5.4) | 27 +6 +22 (4.6) |
| amber host-90 | 33 +7 +26 (8.3) | 28 +1 +22 (8.7) | 32 +10 +27 (3.7) | 31 +9 +27 (**3.2**) |
| amber host-95 | 30 +11 +25 (9.8) | 28 +2 +22 (10.0) | 31 +10 +27 (2.3) | 31 +9 +27 (**3.1**) |
| amber host-100 | 30 +10 +25 (6.9) | 26 +1 +21 (10.6) | 29 +7 +24 (3.9) | 28 +7 +23 (**4.8**) |
| fur margin (not fitted) | 73 −0 +0 (18.6) | 84 +0 +1 (10.8) | 82 +1 +1 (9.0) | 81 +2 +0 (7.7) |
| fur undercoat | 69 +0 +0 (5.7) | 74 +0 +1 (5.6) | 70 +0 +3 (2.8) | 69 −0 +3 (**2.6**) |
| fur tuft | 68 +0 +1 (5.9) | 72 +0 +1 (3.9) | 69 +0 +3 (2.3) | 68 −0 +2 (**1.9**) |
| fur dark | 63 +0 −3 (12.1) | 69 +0 +1 (7.5) | 64 −3 +2 (6.2) | 63 −3 +2 (5.5) |
| **sum** | | **174** | **123** | **114** |

Surrogate prediction vs Mitsuba (named regions without the margin): fit 1
163 → 92 predicted, 163 → 114 measured. Fit 2 114 → 96 predicted,
106 measured. About 70 % of the predicted gain survives the real renderer,
and the second iteration adds little, so I stopped there. **The fitted library beats
v2 on the same regions: 174 → 114 (−35 %).** 19 of the 21 regions are now
within their photo spread (v2: 11, v3a: 18).

Face-mean pixel diffs (v3b, `step4b/diff-stats-v3b.md`): amber 5.4–8.0 ΔE
(v2 7.8–12.2), fur 7.1–8.6 (v2 7.2–11.2), agate 11.0–15.0 (v2 10.7–15.8;
dominated by the per-photo exposure offset, ΔL −12 / +9 / +6).

## What moved (v2 → v3b, 1/m) and why

| resin | σa R G B | σs′ R G B | reading |
|---|---|---|---|
| white | 15/15/15 → 6/9/14 | 9500/10000/11000 → 9512/10141/**16631** | much more blue scattering (B/R 1.75): bluish dilute white. The same direction as the plan's step 5 hypothesis, found by the fit without being asked. |
| black | 12000 → 21978/15482/23065 | 300 → 184/203/270 | stronger, slightly greenish-transparent black |
| clear | 2/3/4 → 9/12/11 | 10 → 4/6/7 | UltraClear a bit more absorbing, but flatter across RGB |
| cyan | 8000/900/200 → **14577**/1599/174 | 1200 → 286/737/1074 | deeper red absorption (teals) |
| magenta | 150/2200/1800 → **30** (bound)/2351/**909** | 1200 → **6000** (bound)/851/1058 | far less red and blue absorption, strong red scattering: a pinker, lighter magenta. This fixes the pinks' hue (a +16 → +22). |
| yellow | 60/600/12000 → 22/1075/19611 | 1200 → **6000** (bound)/3067/3014 | yellow scatters a lot (a pigment, not a dye). Together with the magenta change it gives amber its orange (a +1 → +7). |

Three parameters sit at the ×/÷5 bound (magenta σa R, magenta σs′ R, yellow
σs′ R). The data wants to go further there, and only a coupon can say by how
much.

## What the surrogate cannot see (why the rest needs coupons)

- **Agate darks stay +6–8 L** (deep-teal 27 vs 21, translucent-black 27 vs
  19) across v2/v3a/v3b, although black σa went up ×1.8. With bands
  narrower than the light's lateral reach, the dark bands' colour is set by
  light arriving from their bright neighbours, which the per-region
  `c_r` freezes at the v2 geometry. The surface reflection of the dark-room
  dome also puts a floor under L. A black/teal coupon (large area)
  separates the two.
- **Dusty-rose and clear-band** (a +8/+15 vs +4/+26) conflict: the fit
  cannot make one magenta-bearing mix redder without the other. The photo
  spread there is 24 and 12, so they are photo-limited as well.
- **Absolute lightness** is tied to the per-photo exposure scale (step 2):
  ±15–20 % between photos. A fitted library is only as good as the mean of
  three hand-held photos.

## Skipped / notes

- Fur is fitted with weight 0.5 through the column model, which does not
  represent hair strands (step 5 looks at the fur directly).
- The ×/÷5 bounds and the prior weight of 3.0 are my choice: prior 0.3
  gives a predicted sum of 88 vs 92 at 3.0, with six parameters at bounds
  and non-physical shapes (black σs′ B/R = 16).
- v3b is frozen as v3 in step 6.
