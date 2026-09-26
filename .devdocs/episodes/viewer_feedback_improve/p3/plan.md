# viewer_feedback_improve Phase 3 — Coupon batch: forward calibration instead of inverse fitting

Parent: `../braindump.md`. Previous: `../p2/plan.md`, `../p2/report6.md`
(read it first: wish list, mirrored-print finding, depth-32 finding).
Human-side procedure: `manual.md` (Japanese; what to print, how to shoot,
what can be skipped). This plan is the tool side.

## Why this phase, and what changes

p1/p2 estimated 36 resin coefficients from three hand-held photos of
patterned parts. That is an inverse problem with three symptoms that will
not go away with more fitting: parameters at the ×/÷5 bounds (magenta σa R,
magenta σs′ R, yellow σs′ R), ±15–20 % exposure scatter between photos of
the same part, and dark narrow bands whose colour is set by their neighbours.

Phase 3 turns it into a forward problem: **single-resin and two-resin
coupons** are measured under a **fixed photo protocol**, coefficients are
solved per resin from thickness series, and the batch1 parts become a
*validation* of the mixing rule and lateral transport, not a fitting target.

Two halves:

- **A (before the prints arrive)**: coupon generator, generic camera
  matching, direct KM inversion, transmission support, viewer depth fix.
- **B (after batch2 arrives)**: ingest, solve, validate, freeze `v4`.

## Facts to reuse

- Printer limits (`.devdocs/vision/printer_export/roadmap.md`): PNG method,
  600 × 300 dpi, 14 µm HQ layers, max 6 colours per image plus background,
  min 30 slices. batch1 used six slots: white, black, UltraClear, C, M, Y.
- Custom exporters (`work/*/export_*_voxelprint.py`) write PNG row 0 = y 0
  and the prints came out **y-mirrored** (p2 report3). The vdbmat-utils
  exporter has `flip_y`. The coupon batch includes a handed test part to
  settle the convention before any exporter is changed.
- `work/compare/match_camera.py` hard-codes the 60 × 30 × 5 mm box;
  `specs/batch1-v3-picks.json` holds corner picks in pixels. `slab.py`
  holds the face/region geometry. `pixel_diff.py` warps by face
  homographies.
- `work/resins/km_surrogate.py` (two-flux KM, Saunderson boundary, paper
  backing ρ = 0.8), `km_validate.py` (homogeneous 60 × 30 × 5 slabs,
  depth 256), `km_fit.py` (36-parameter fit with prior and bounds).
- Depth: homogeneous white needs `max_depth ≥ 256`, roulette off
  (`stage-print-photo-deep`). Patterned batch1 parts change ≤ 2 ΔE
  between 32 and 256.
- Photo normalisation: per-channel gain on a white patch → 0.85 sRGB. With
  a grey card in frame this becomes a two-point check (white and 18 %).
- `.local/` is git-ignored; specs, scripts and libraries live under `work/`.

## Part A — tooling while waiting for the prints

### Step 1 — Coupon generator and build

- `work/coupons/make_coupons.py`: from a JSON list of coupons
  (`id`, `size_mm` [x, y, z], `recipe` over the six slots, optional
  `features`: corner notch, "F" relief, line target underneath) emit for
  each: material-label voxels at review grid (0.2 mm) **and** the print
  slice stack at printer pitch via the existing RGBA writer conventions
  (deterministic 3D hash dither as in the batch1 exporters, same
  `RESINS` colour codes, `flip_y` **off**, exactly like batch1, so the
  handed part reveals the convention). Write `<id>.resin-recipes.json`
  and a `batch2-manifest.json` (ids, sizes, recipes, notch position,
  which face is up on the tray).
- Default coupon list = `manual.md` §2 (thickness series of UltraClear,
  white-in-clear series, large black/cyan patches with 1 mm bands in
  white, M/Y 50/50 with clear and with white, the three batch1 recipes
  that stayed off, one pure-white 5 mm block, one handed "F" part).
  Keep every coupon 30 × 30 mm unless the manual says otherwise, and put
  a notch on the +x+y top corner of every part.
- Print-aware build: extend `build_print_aware.sh` to accept the coupon
  directory so all coupons get `print-aware-<TAG>` zarrs in one call.

Done when: the slice stacks and manifest exist under
`.local/coupons/batch2/`, a `README` in that directory lists the GrabCAD
slot ↔ resin mapping exactly as batch1 used it, and one coupon round-trips
through `convert-image-stack` to its label volume.

### Step 2 — Generic camera matching and photo ingest

- `match_camera.py`: read the box size (and notch) from the manifest per
  part instead of the constant; support several parts in one photo (each
  with its own corner picks and its own pose; one focal length per photo).
- `pick_regions.py` / new `ingest_photos.py`: given `batch2/photos/` and
  the manifest, produce the spec JSON (paths, white card, grey card,
  per-part corners, orientation) with a small interactive pick tool
  (matplotlib clicks are fine). Store picks in `work/coupons/specs/`.
- Two-point normalisation: gain from the white card, then report the grey
  card's normalised value; if it is off by > 10 % the photo's tone curve is
  non-linear and the report flags it (do not fit a curve unless every photo
  agrees on the same one).

Done when: a synthetic test (render a coupon with a known pose, pick its
corners) recovers the pose to < 3 px RMS, and the ingest tool makes a spec
from a folder of images.

### Step 3 — Direct inversion from coupons (reflectance and transmission)

- `work/resins/km_invert.py`: for a single-resin (or fixed-recipe)
  coupon series at thicknesses `d_i`, with reflectance over white card
  and, where shot, over the light box (transmission), solve `sigma_a`,
  `sigma_s′` per channel by least squares on the KM slab model (use the
  Saunderson boundary from `km_surrogate.py`). A thickness series alone
  separates absorption from scattering for opaque-ish resins; clear
  resins need the transmission shots. Produce per-resin confidence from the
  residuals.
- Mixture coupons (white-in-clear series, M/Y 50/50): predict with linear
  volume-fraction mixing from the single-resin solutions and report the
  residual. This is the direct test of `linear-volume-fraction-v1`. If the
  dilute white series fails systematically (the p2 "bluish dilute white"
  effect), fit a concentration-dependent scattering tint in
  `recipes_to_mapping.py` and document it as a mixing-rule extension.
- Mitsuba check: render each coupon on the print-photo-deep stage from
  its matched camera and compare with the photo, as p2 step 4 did for
  validation slabs. The known 1.2–1.4× KM/Mitsuba scale from p2 must be
  re-measured here; if it is stable, bake it into `km_invert.py`.

Done when: the inversion recovers the coefficients of a synthetic
(rendered) coupon series to within 15 %, and the tool runs end to end on a
mocked batch2 spec.

### Step 4 — Viewer depth and print-aware defaults

- Fix the depth trap: either make `stage-print-photo` depth 64 + a
  launcher warning for large pale areas, or choose depth by the volume's
  max albedo/extent automatically in `view_print.sh` (deep when a
  material with albedo > 0.95 covers > 10 % of the volume). Document the
  choice.
- Add the batch2 coupons to `view_print.sh` and `material.json`-style
  registry so a coupon can be opened in the viewer by id.
- Record scipy / opencv-python-headless / matplotlib in the vdbmat uv
  group used by the compare scripts (p2 installed them outside the lock).

## Part B — after batch2 arrives

### Step 5 — Ingest and sanity

- Copy photos to `.local/real_print/batch2/<id>/result/` and the slices,
  manifest and recipes to `.../data/`. Run ingest, pick corners, build the
  spec. First check: the handed "F" part. Decide and record the y
  convention; if mirrored, set `flip_y` in the coupon generator and in
  the three batch1 exporters (one-line change each) and note that batch1
  artefacts are as-printed-mirrored.
- Grey-card check per photo; list photos that fail it.

### Step 6 — Solve the library

- Run `km_invert.py` on every series; assemble
  `work/resins/vero-j850-measured-v4.json` with per-resin residuals,
  `calibration_status: coupon-fitted-v1`, source = batch2 ids and photo
  protocol version. Keep v3 for comparison.
- Compare v4 against v3 per resin; the three parameters at bounds should
  now be inside the range or the coupon says the bound was wrong.

### Step 7 — Validate on batch1 and the off recipes

- Rebuild batch1 print-aware with v4 (mirror variants) and re-run the p2
  matched comparison (`render_matched.sh`, `region_delta.py`). Report the
  21-region sum vs v3's 114 without any fitting on batch1. A worse number
  here means the mixing rule or lateral transport is at fault, not the
  coefficients; say which, using the M/Y 50/50 and dilute white residuals.
- The three "still off" recipes printed as coupons (dusty-rose, clear-band,
  amber host-85) get their own line: photo vs v4 render, both faces.

### Step 8 — Freeze, and the next wish list

- Freeze v4, update the launcher default to v4, write `report8.md` with
  the final table, the y-convention decision, and what a batch3 would
  need (expected: spectral shape for clear/white if the light-box shots
  show it, matte-face roughness from the two-face photos).

## Rules (minimal)

- `.local/real_print/batch1/` and `batch2/` are evidence: add, never edit.
- No compatibility shims; `work/` scripts and specs may change freely;
  vdbmat tests stay green if `vdbmat` is touched.
- Coefficients come from coupons; batch1 is validation only in this phase.
- Every number in a report is reproducible from a spec or command line.

## Out of scope

Spectrophotometer measurements, spectral rendering, GrabCAD halftone
emulation, Blender parity.
