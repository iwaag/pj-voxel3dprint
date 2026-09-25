# p1 step 7 report — converge the library, freeze v2, phase 2 wish list

## Done

- Only the resin library was tuned (no per-case constants, no recipe or stage
  changes). Each iteration = `work/resins/build_print_aware.sh LIB TAG` (3 min) +
  three print-photo renders into `.local/real_print/batch1/renders-p1/step7/<case>-<TAG>.png`
  (spp 128, ~9 min) + the step 6 regions (`batch1-v1.json` rectangles).
- Frozen as `work/resins/vero-j850-provisional-v2.json` (library_id unchanged,
  `changelog` + per-resin `note` updated, `source` says "tuned against batch1
  photos, not calibration").
- Final build and renders, tag **v2** (`.local/<case>/print-aware-v2/`):
  ```
  work/resins/build_print_aware.sh work/resins/vero-j850-provisional-v2.json v2
  O=.local/real_print/batch1/renders-p1/step7
  work/compare/render_stage.sh .local/pink-agate-v3/print-aware-v2/agate-optical.zarr   $O/agate-v2.png --spp 256 --denoise   # 332 s
  work/compare/render_stage.sh .local/amber-branching/print-aware-v2/amber-optical.zarr $O/amber-v2.png --spp 256 --denoise   # 438 s
  work/compare/render_stage.sh .local/floating-fur/print-aware-v2/fur-optical.zarr      $O/fur-v2.png   --spp 256 --denoise   # 244 s
  vdbmat/.venv/bin/python work/compare/contact_sheet.py work/compare/specs/batch1-v2.json \
      .local/real_print/batch1/contact-sheet-v2.png --table .local/real_print/batch1/contact-sheet-v2.md
  ```
  Final sheet: `.local/real_print/batch1/contact-sheet-v2.png` (all three
  photos per case | semantic, v2a, v2 final; numbers under each row).

## Iterations (ΔE76 to the photo, white-paper normalised)

| region | v2a | v2b | v2c | v2d | v2e = v2 | v2 final (spp256 dn) |
|---|---|---|---|---|---|---|
| agate top face | 4.5 | 6.2 | 1.7 | 3.7 | 3.7 | 3.7 |
| agate pink band | 18.5 | 19.7 | 11.7 | 10.3 | 10.0 | 9.4 |
| agate dark teal | 9.5 | 9.1 | 9.2 | 10.6 | 9.3 | 10.2 |
| amber top face | 11.0 | 9.5 | 7.8 | 5.8 | 6.4 | 6.4 |
| fur hair field | 6.4 | 5.9 | 5.9 | 6.8 | 5.9 | 5.5 |
| fur clear margin | 10.0 | 6.7 | 6.7 | 5.8 | 6.7 | 6.7 |
| **sum** | 58 | 57 | 43 | 43 | 42 | 42 |

What changed and why (library values, 1/m):

- **v2b** — clear σa 5/8/15 → 3/4/6 and white σa 20/20/25 → 15/15/15 with σs
  9500/10000/11000 (slightly blue scattering): fur margin and hair were too
  yellow (b +4/+5 vs −2/−1). Worked (margin 10 → 6.7). Also magenta σa
  700/4000/1200 → 250/3500/600, cyan 4000/800/250 → 6000/700/200,
  yellow 250/500/5000 → 80/250/5000, CMY σs 1000 → 800, black 15000 → 12000.
  **Magenta was the wrong direction:** pinks went more violet (b −2).
- **v2c** — the photo pinks are salmon (R > G > B), so real Vero Magenta must
  absorb blue strongly as well: magenta 150/2800/1800; yellow 60/200/9000 for
  amber chroma; clear 2/3/4. Pink b fixed (+11), top face 1.7, amber 7.8.
- **v2d** — magenta green 2800 → 2200 (pinks too red/dark), yellow
  60/600/12000 (amber needs orange, not just yellow), black 12000 → 9000.
  Amber 5.8, but the agate lightened.
- **v2e** — black back to 12000, cyan 8000/900/200, CMY σs 800 → 1200. Best
  sum; the last changes moved every region by ≤ 1.5 ΔE. Frozen as v2.

Checked and refuted: "the dark teal is too light because the stage reflects a
uniform bright environment". The darkest 1 % of the agate top face is the same
in photo and render (normalised Y 0.022 vs 0.023). The dark-teal ΔE comes from
the render's narrower dark bands under a small rectangle (5th percentile 0.035
vs 0.027). It did not respond to cyan 4000 → 8000.

## Remaining gaps per case

- **agate** (visually close: coral pinks, deep teal, near-white pale bands,
  fine grain):
  - pinks are still ~8 L too dark. That did not move with CMY σs 800 → 1200 or
    magenta green 2800 → 2200. Either white σs is too low for mixtures (but fur
    says white is already too bright), or the photo's tone curve lifts
    mid-tones. It needs a measured pink coupon.
  - Dark teal region +10 L (above).
  - The photo shows gold specks (yellow-rich "light tan") and a stronger glossy
    top highlight. The render stage has no structured environment to reflect.
- **amber**: lightness matches; still less orange (a +1 vs +5, b +11 vs +16).
  The photo's edge glow (light entering the sides) is weaker in the render.
  More yellow/less black would push it, but that is the knob that lightened
  the agate. A value that fixes only amber is the warning sign from the plan,
  so it stays.
- **fur**: the shell is clear (report4). The hair field is +5 L and neutral,
  while in the photo it is a distinct **blue-grey opaque undercoat with white
  hair tufts between the stripes**. In the render the stripes are washed out.
  Suspects: the 0.2 mm review grid (hairs are drawn at printer pitch in the
  export, but the render uses the per-material effective medium at 0.2 mm), and
  the fact that thin white-in-clear really does look bluish (a scattering-size
  effect that an RGB σs can only mimic). Needs a white-in-clear coupon series.
- **all**: the stage. The uniform floor + ambient cannot give the photos' bright
  glass edges or glossy highlights (report4). The J850 finish (glossy top /
  matte support faces) was not modelled.

## Phase 2 wish list

**Coupon set** (J850 HQ, same resin slots, glossy):
- single-resin slabs of white, black, UltraClear, cyan, magenta, yellow at
  0.5 / 1 / 2 / 4 mm (transmission and reflectance give σa and σs' per resin);
- 50/50 dithers of each pigment with clear, plus 25/75 white-in-clear
  (tests linear mixing and the bluish white-in-clear look; step 5 says mixing
  is unbiased at v2 values, and this confirms it with measured values);
- the recipes that are still off: agate "dusty rose" / "pale pink" (L gap),
  amber host (mat 3), fur undercoat (mat 2, 18 % white);
- one clear slab with a printed black/white line target underneath
  (shell clarity, edge sharpness).

**Photo protocol** (so ΔE < 10 means something):
- same lighting for every shot (one diffuse overhead source, no window light),
  fixed white balance and exposure (manual / RAW, no auto tone);
- fixed camera: tripod, top-down + one ~65° oblique, same distance;
- white card (or grey card) and a ruler in every frame; the white card is
  the normalisation patch;
- backlit shot on a light box for the clear/translucent cases.

**Stage** follow-up: match that protocol in `stage-print-photo` (overhead
area light + dark surround instead of uniform ambient), then consider
`roughdielectric` on support-contact faces if the coupons show matte bottoms.

## Skipped / notes

- Denoise is on for the final three renders only (step 4: it keeps the texture).
  The amber raw has one firefly pixel (max 22.7), which the denoiser removes.
- The step 5 crop was not rebuilt with v2. The conclusion depends on the mean
  free path vs cell size, and v2 CMY σs (1200) keeps the same regime.
