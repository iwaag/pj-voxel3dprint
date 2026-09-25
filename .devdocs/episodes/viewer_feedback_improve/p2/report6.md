# p2 step 6 report: freeze v3, viewer defaults, wish list

## Done

- **`work/resins/vero-j850-provisional-v3.json`**: the fitted library (=
  fit v3b, step 4), with `source` ("fitted, not measured"), a changelog entry
  listing every v2 → v3 value, per-resin notes, and a
  `fit_residuals_dE76` table (21 regions: photo spread, v2, v3a, v3 ΔE, sums
  174 / 123 / 114). v2 is kept for p1 reproducibility; v3a/v3b stay as the
  iteration records.
- Built `.local/<case>/print-aware-v3/` for all three cases, in design
  orientation (`<name>-optical.zarr`, what the viewer opens) and as printed
  (`<name>-mirror-optical.zarr`). The v3 arrays are byte-identical to v3b's
  (checked by hashing every chunk), so the step 4 v3b matched renders are
  the v3 renders.
- **Viewer: predict the print by default** (for this project):
  - `work/compare/view_print.sh agate|amber|fur [TAG=v3] [--mirror] [--deep]`
    opens the print-aware zarr on `stage-print-photo`. The Input tab lists
    everything under `.local/<case dir>/` (semantic, all print-aware tags,
    crops). Smoke-tested: the viewer came up with
    `print-aware-v3/agate-optical.zarr` on the dome stage
    (`.local/real_print/batch1/renders-p2/step6/viewer-launcher.png`).
  - `work/materials/{pink_teal_agate,kohaku,floating_fur}/material.json` gain
    `print_aware_variants` (library, build command, both zarrs, the mirror
    note) and `viewer` (launcher + preset).
  - vdbmat: new preset `stage-print-photo-deep` (= print-photo with
    depth 256, no roulette), plus a manual paragraph on when to use it. I did
    not change the vdbmat viewer's built-in default. It has no notion of a
    "print-aware" input: the only marker is the `+<library_id>` suffix of
    the mapping-config id in the zarr provenance, which is a project
    convention, not a vdbmat one. The launcher and `material.json` are the
    project-level default the plan allowed as the minimum.
- Why depth 32 stays in `stage-print-photo`: see "Depth" below.

## Commands

```
work/resins/build_print_aware.sh work/resins/vero-j850-provisional-v3.json v3 agate amber fur agate-m amber-m fur-m
work/compare/view_print.sh agate            # or amber / fur; --mirror for the as-printed volume, --deep for pale parts
# final sheet = step 4b (v3b == v3):
cp .local/real_print/batch1/renders-p2/step4b/contact-sheet-v3-v3b.png .local/real_print/batch1/contact-sheet-v3-final.png
# depth options (white slab, fur U9 view)
D=.local/km-validate/v2; O=.local/real_print/batch1/renders-p2/step6/depth
work/compare/render_stage.sh $D/agate-white-optical.zarr $O/white-d128-rr128.png --width 320 --height 320 --spp 128 --max-depth 128 --rr-depth 128
work/compare/render_stage.sh $D/agate-white-optical.zarr $O/white-d256-rr64.png  --width 320 --height 320 --spp 128 --max-depth 256 --rr-depth 64
S=$(realpath .local/real_print/batch1/renders-p2/step3/stages/fur-Unknown-9.stage.json)
work/compare/render_stage.sh .local/floating-fur/print-aware-v3b/fur-mirror-optical.zarr $O/fur-U9-d256-rr64.png --stage-config $S --spp 256 --max-depth 256 --rr-depth 64
```

## Depth

Central white on a homogeneous white slab (normalised R, converged value
0.516 at depth 256–1024):

| setting | R | time (320², spp 128) | notes |
|---|---|---:|---|
| depth 32 (preset) | 0.323 (−38 %) | not timed | |
| depth 64 | 0.421 (−18 %) | 109 s | |
| depth 128, no roulette | 0.487 (−6 %) | 170 s | |
| depth 256, no roulette | 0.516 | 228 s | `stage-print-photo-deep` |
| depth 256, roulette from 64 | 0.477 (noisy) | 142 s | fireflies (max 632) |

On the fur view, roulette from 64 brings p1's fireflies back (max 343 vs
7.9), so roulette stays off. Batch1-like patterned parts change by ≤ 2 ΔE
between depth 32 and 256 (agate matched view, step 4) at a third of the
cost. So `stage-print-photo` keeps depth 32 (which also keeps every p2 render
reproducible), and `--deep` / `stage-print-photo-deep` is for large pale
areas and coupons.

## Final contact sheet

**`.local/real_print/batch1/contact-sheet-v3-final.png`**: one row per photo
(9): photo | camera-matched v3 render | ΔL | Δb. Numbers:
`contact-sheet-v3-final.md` (per-region three-photo mean vs three-render
mean, v2 / v3a / v3).

| | v2 (p1 library, p2 stage) | **v3** |
|---|---:|---:|
| sum ΔE76, 21 named regions | 174 | **114** |
| regions within their photo spread | 11 / 21 | **19 / 21** |
| face-mean ΔE per photo: agate | 10.7–15.8 | 11.0–15.0 |
| amber | 7.8–12.2 | **5.4–8.0** |
| fur | 7.2–11.2 | **7.1–8.6** |

(The agate face means are dominated by the per-photo exposure offset:
ΔL −12 / +9 / +6 for the three photos of the same object.)

## Per case: closed, photo-limited, needs coupons

**Agate**
- *Closed:* hue of the pinks (pale-pink a +22 vs +28, v2 +16), lavender and
  blue-grey (ΔE 4–5), mauve, white band (2.7), deep teal on the top-down
  view. The room reflection problem (p1 dark-teal +10 L) was the stage and
  was fixed in step 1.
- *Photo-limited:* dusty-rose (photo spread 24 ΔE), white (19), clear-band
  (12). Absolute lightness per photo is ±15–20 % (step 2).
- *Needs coupons:* dark bands stay +6–8 L (deep-teal, translucent-black);
  black and cyan in a large area separate the resin from the lateral light
  of narrow bands. The dusty-rose vs clear-band conflict (same magenta, one
  too red, one not red enough) needs the 50/50 magenta-clear and
  magenta-white coupons.

**Amber**
- *Closed:* the orange-brown (host a +5…+9 vs photo +3…+11; v2 +0…+2),
  lightness. All five host classes are within their photo spread (ΔE 2.6–4.8).
- *Found:* the photos show the **bottom (matte support) face** of a **mirrored**
  print (step 2/3). The "satin top" of p1 is the support face.
- *Needs coupons:* black-vs-yellow balance in thick translucent hosts (yellow
  σs′ and magenta σs′ ended at the ×5 bound); matte-face roughness (the
  `finish` option exists and is unused, since only the bottom is matte).

**Fur**
- *Closed:* clear shell with bright edges (step 1), stripe lightness
  contrast and region lightness (undercoat 69 vs 69, tuft 68 vs 68). The
  0.2 mm review grid is not the cause (step 5: printer pitch renders
  identically).
- *Partly:* the blue-grey core: v3's blue-leaning white scattering moves the
  core-vs-gap tint from Δb −0.2 to −1.9 (photo −4.2).
- *Needs coupons:* the remaining yellow cast of white-in-clear (gap b +3.5 vs
  +0.5). Over long diffusion paths the *shape* of the small clear and white
  absorptions decides the colour, which photos of this object cannot
  resolve.

## Wish list (refreshed for the coupon batch)

**Print pipeline**
1. **The prints are mirror images of the voxel volumes** (step 3, 5–7-point
   PnP: 2–7 px mirrored vs 12–55 px as-is). The batch1 exporters write PNG
   row 0 = y 0. Set the exporter's `flip_y` (vdbmat-utils
   `export-print-slices` already has it) or flip the custom exporters, and
   check with one handed test part (a letter "F" relief) in the coupon
   batch before relying on it.
2. Mark top/bottom on every part (a small notch on a corner), so photos
   can be matched without texture correlation.

**Coupons** (J850 HQ glossy, same resin slots, 30 × 30 mm; thickness steps
where noted). Priority by what the fit could not resolve:
- **clear (UltraClear) slabs at 2 / 5 / 10 mm over a black-and-white line
  target**: the absorption shape that yellows every dilute white (fur)
  and the paper seen through clear parts;
- **white-in-clear series 5 / 10 / 18 / 32 / 48 / 100 % white at 1 and 5 mm**:
  the dilute-white tint and scattering. The fitted white σs′ B/R 1.75 is
  a prediction to test, as is the fur undercoat at 18 %;
- **large black and cyan patches (10 × 10 mm) at 5 mm**, next to 1 mm bands
  of the same resins in white: separates the resin darkness from lateral
  light (agate darks +6–8 L);
- **magenta and yellow 50/50 with clear and with white**: magenta σa R,
  magenta σs′ R and yellow σs′ R hit the ×5 bound;
- the agate "dusty rose" and "clear band" recipes side by side (the
  conflict above), and the amber host-85 recipe at 5 mm, **both faces
  photographed** (glossy top vs matte support side);
- one 5 mm pure-white block for the depth/brightness check (it needs
  `stage-print-photo-deep`).

**Photo protocol** (so step 3's camera matching becomes routine and ±15–20 %
exposure scatter goes away):
- one overhead light (no window light), the room otherwise dark. The
  stage models exactly this (step 1);
- tripod or copy stand; top-down (el ~85°) + one oblique (~55°) per part,
  same distance, the phone not casting a shadow on the part (the top-down
  batch1 photos are 0.7× darker than the oblique ones, step 2);
- fixed exposure and white balance (manual / RAW), no HDR or auto tone;
- a grey card (18 %) and a white card **in every frame, next to the part**,
  plus a ruler. The white card replaces the paper patch as the
  normalisation reference;
- the full part inside the frame with a margin, so the four top corners
  can be picked. Mark the top face (see 2);
- optional: the same shots on a light box (backlit) for the clear and
  translucent parts.

**Toolchain follow-ups**
- Spectral or at least wavelength-shaped absorption for clear/white.
  RGB effective coefficients over centimetre paths are the fur's limit.
- Region colour in narrow bands depends on neighbours (lateral transport).
  After the coupons, refit with the render-corrected surrogate
  (`km_fit.py`); the KM surrogate alone is 1.2–1.4× high (step 4).
- The viewer could read the mapping provenance and offer the print-photo
  preset automatically once vdbmat has a generic "print-aware" marker in the
  optical-mapping schema.

## Skipped / notes

- Nothing was changed in `vdbmat/src`. All vdbmat changes in p2 are in the
  demo track (`examples/pipeline_run/demo/`), its tests, docs and presets.
  Submodule commits: `7558e37` (dome + finish), `e76c6bb` (camera pose),
  plus this step's preset/manual commit.
- Installed into `vdbmat/.venv` outside its lock file: scipy,
  opencv-python-headless, matplotlib (steps 2–3).
