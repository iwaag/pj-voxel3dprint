# viewer_feedback_improve Phase 2 — Structured stage, aligned comparison, fitted library (still no new prints)

Parent: `../braindump.md`. Previous: `../p1/plan.md`, `../p1/report1..7.md`
(read report7 first). Evidence: `.local/real_print/batch1/`.
Scope: still only batch1 photos and the p1 toolchain. Coupons are not printed
yet; this phase makes the toolchain ready to consume them and squeezes what
batch1 can still tell us. Anything that needs a measured coefficient stays
on the wish list.

## Where p1 left things

- Print-aware pipeline works: `work/resins/vero-j850-provisional-v2.json` →
  `recipes_to_mapping.py` → `build_print_aware.sh LIB TAG` → three optical
  zarrs (~3 min) → `work/compare/render_stage.sh` on the `stage-print-photo`
  preset (512², spp 128, depth 32, rr 32, ~2–3 min each; spp 256 + denoise
  ~4–7 min). Sum ΔE76 over six regions went 58 → 42 by hand-tuning.
- What remains, per report7, and what this phase can do about it:

| gap | cause hypothesis | p2 answer |
|---|---|---|
| no bright sharp edges on the clear fur block; glassy instead of satin amber top; no highlights | stage is a uniform 0.75 ambient + small key; photos have a dark room and one overhead source reflected in the faces | Step 1: structured environment |
| agate pinks −8 L, dark teal +10 L; unclear if real or the phone tone curve | linear white-patch gain cannot undo a JPEG tone curve; hand rectangles on different cameras | Steps 2–3: tone-curve test, camera-matched renders |
| hand tuning of 36 library numbers against 6 regions | no fast forward model, no fit | Step 4: Kubelka-Munk surrogate + fit over many regions |
| fur undercoat is blue-grey opaque stripes in the photo, washed out in the render | 0.2 mm effective grid vs hairs drawn at printer pitch; dilute white looks bluish | Step 5: fur at printer pitch, wavelength-shaped white scattering |
| library "v2" is tuned by eye | | Step 6: freeze v3 from the fit, update the wish list |

## Facts to reuse

- Stage schema 1.3.0 (`mitsuba_stage.py`): `ambient` = Mitsuba `constant`
  emitter; `backlight` is a canonical rectangle that cannot be removed, only
  set to a radiance (p1 set it equal to ambient to hide it); the camera
  override is `azimuth/elevation/distance_factor/fov` only, looking at the
  bounds centre. `stage_config_digest` normalises defaults to the 1.2.0 form
  so archived sessions keep replaying; extend it if you add fields.
- The floor is a `diffuse` plane; the key light an `area` rectangle.
  Photos: white paper on a desk, ceiling light, dark room otherwise, phone
  hand-held at 60–75° elevation, random azimuth.
- `work/compare/contact_sheet.py` + `specs/batch1-v2.json`: per-image white
  patch and named regions as image-fraction rectangles; outputs per-region
  mean sRGB/Lab after per-channel linear gain to white = 0.85; `--table`.
- Three photos per case at different angles/exposures exist. Only one per
  case was used for numbers.
- Step 5 of p1 (`work/halftone/agate_halftone_crop.py`): direct printer-pitch
  crop generator reusing the export's hash/recipes; 12 min for 2.5 M
  anisotropic voxels, dominated by `vdbmat convert`. Fur export grid is
  1418 × 354 × 358 (60 × 30 × 5 mm at 42.3 × 84.7 × 14 µm); its hairs are
  drawn straight at printer pitch (`work/fur/export_floating_fur_voxelprint.py`),
  so the 0.2 mm review zarr is a *different* object, not a downsample.
- GPU: ~43 GB of 48 GB used by ComfyUI; 512² renders fit. `cv2` is not
  installed in either venv (needed for PnP in step 3; `pip install
  opencv-python-headless` into `vdbmat/.venv` is fine, or solve PnP with
  scipy least squares, 6 DoF + fov).
- Slab geometry is known exactly: 60 × 30 × 5 mm boxes, sharp edges.

## Steps

Each step ends with `reportN.md` here (done / commands / images / learned /
skipped), same as p1.

### Step 1 — Structured environment and finish

Goal: faces reflect a room, not a grey fog. Edges of the clear block become
bright lines, the amber top gets a soft highlight, the semantic "milky" look
of clear parts disappears.

- Replace the uniform ambient with a **room**: keep `ambient` low (0.05–0.15,
  dark walls) and add one large overhead soft emitter (`scale_factor` 4–8,
  radiance so the floor still lands ~0.65–0.75 linear), directly above with a
  slight offset toward the camera. Consider one more dim fill panel opposite
  the camera to shape the side faces. Schema options, pick one:
  - generalise `key_light` into a list of area lights (`lights: [...]`) and
    keep `ambient`; or
  - add a `dome`/`envmap` entry with a procedural gradient (bright cap, dark
    horizon) via a small generated EXR loaded by Mitsuba's `envmap`.
  Bump stage-config to 1.4.0, update the two shipped presets, the binder,
  `stage_config_digest` normalisation, and the GUI manual screenshots as p1
  did. No compatibility shims.
- Finish: try `roughdielectric` (alpha 0.05–0.12) for the exterior boundary
  as a stage/export option (`MitsubaExportConfig` or a stage override applied
  to `exterior_*` shapes), compare against smooth on amber and fur. The J850
  glossy top is glossy but not mirror-like in the photos (satin sheen). Keep
  whichever reads closer; note that roughness also softens the clear-block
  edge lines, so judge on fur edges and amber top together.
- Re-render the three v2 cases. Update `stage-print-photo` (this replaces
  the p1 version; keep the p1 one as `stage-print-photo-v1` only if a p1
  report render must stay reproducible — a documented command line is
  enough, so probably delete).

Done when: fur edges are sharp bright lines over the paper as in the photo,
and the floor/shadow still match. Record the light layout numbers.

### Step 2 — Is the pink −8 L real? Tone-curve and consistency test

Goal: know how much of the remaining ΔE is the phone, before fitting anything.

- For each case, apply the step 6 regions to **all three photos** (they differ
  in exposure and angle). If the normalised Lab of the same band varies by
  more than ~3 L between photos, the tone curve (or specular/angle) is the
  limit and single-photo ΔE below that is noise.
- Fit a global tone curve: on agate, choose ~8 regions spanning dark teal to
  white band; plot render-vs-photo normalised luminance; if a single gamma
  (or a 2-parameter curve) explains the residual for all three cases at once,
  add it as an optional `photo_tone` per image in the spec (applied before
  Lab), and report the fitted parameter. If it does not, leave the numbers
  as they are and say so.
- Cheap extra: the darkest 1 % / brightest 1 % of the object per image, as
  p1 did once by hand, made a standard column of the table.

Done when: the report states, per region, "photo-limited" or "render-limited".

### Step 3 — Camera-matched renders and pixel-wise diffs

Goal: render from the photo's viewpoint so regions coincide and a difference
image is meaningful. Also the base for future coupon photos.

- Extend the camera override to a full pose: `position_m`, `target_m`,
  `up`, `fov_deg` (in object-local metres; keep the az/el form as the other
  variant or drop it — no shim). Expose it in the binder/GUI.
- `work/compare/match_camera.py`: user clicks/records the 4 top-face corners
  (and optionally 2 bottom corners) of the slab in a photo; solve PnP for the
  known 60 × 30 × 5 mm box (fov unknown → solve for focal length too; phone
  JPEGs carry EXIF focal length and sensor size, use as the initial guess).
  Emit a stage camera block. Store corner picks in the spec JSON so the
  match is reproducible.
- Render the three cases from the matched cameras with the step 1 stage at
  the photo's aspect ratio; warp the photo's object quad onto the render's
  (homography of the top face is enough, the slab is flat) and produce:
  side-by-side, |ΔL| map, Δa/Δb maps, and the region table now measured on
  the same rectangles in both images.
- Add per-band regions on agate (each of the 14 materials appears as a
  distinct band; pick 6–8), the amber host and vein, fur undercoat stripe vs
  tuft vs margin. That gives ~15 regions for the fit in step 4.

Done when: `contact-sheet-v3.png` shows photo / matched render / ΔL map per
case, and the region list is in `specs/batch1-v3.json`.

### Step 4 — Kubelka-Munk surrogate and library fit

Goal: replace hand-tuning with a fit, and have a fast predictor for coupon
data later.

- `work/resins/km_surrogate.py`: for an opaque or thick slab of a mixed
  material over a white diffuse backing, predict top-face reflectance per
  RGB channel from `(sigma_a, sigma_s')` via Kubelka-Munk (K = 2σa,
  S ≈ 0.75σs' is a serviceable mapping; or use the two-flux form directly) with
  a dielectric boundary correction (Saunderson, n = 1.52). Validate the
  surrogate against Mitsuba on 4–5 single-material slabs first (render a
  homogeneous 60 × 30 × 5 box per material with the step 1 stage; agree to
  ~±5 % or note the offset per material).
- Fit: parameters = 6 resins × (σa RGB, σs' RGB) = 36 numbers, log-space,
  bounds from the p1 prior table ×/÷ 5. Observations = the step 3 regions
  (~15) as normalised linear RGB (after step 2's tone decision). Each region's
  material recipe comes from the export scripts (`RECIPES`/`REC`; the agate
  band ↔ material id map needs to be made once by eye from the semantic
  render). Loss = ΔE76 in Lab plus a mild prior pull. scipy `least_squares`.
  Fur hair regions are not opaque slabs; either exclude them from the KM fit
  or model them as white-in-clear of known thickness (2.7 mm core, mat 2 at
  18 % white) over paper.
- Verify: build print-aware with the fitted library (`build_print_aware.sh
  LIB v3a`), render the three matched views, compare the sum ΔE against v2's
  42 (recomputed on the new regions so the number is comparable). Iterate
  once or twice if the surrogate offset is systematic.

Done when: a fitted library beats the hand-tuned v2 on the same regions, or
the report explains why the surrogate cannot see the remaining gap (which
then becomes the strongest argument for coupons).

### Step 5 — Fur at printer pitch and dilute-white scattering

Goal: the blue-grey opaque undercoat with white tufts.

- Build a fur crop at printer pitch the way p1 step 5 did for agate
  (`work/halftone/fur_halftone_crop.py` reusing the export's `hairs()`,
  `REC`, noise): a 6 × 6 mm window over the hair mass, all 358 layers. Map
  through the six-resin mapping and render with the matched camera crop.
  Compare with the 0.2 mm effective render of the same window: if the stripes
  and tufts appear only at printer pitch, the review grid is the cause and
  the report should recommend rendering fur-like materials at ≥ 2× finer
  review grid (or straight from the print stack) in the viewer.
- Dilute white in clear scatters bluish (particle-size effect). Try a
  stronger wavelength shape on white `sigma_s` only when the white fraction
  is low: either make the library entry `sigma_s` 1 : 1.25 : 1.6 (R:G:B) and
  check that the agate white bands (68 % white) do not go blue, or add a
  per-recipe rule in `recipes_to_mapping.py` (scattering tint grows as the
  white fraction falls). Keep it if the fur undercoat a/b move toward the
  photo (photo ≈ +1/−1 vs render +0/+1 now) without hurting agate.
- Optional: use `MaterialMixtureVolume` for the fur review grid (per-voxel
  resin fractions from the print stack, box-filtered to 0.1 mm) instead of
  per-material constants. That is the principled "downsample of the print"
  and would make the viewer show what was printed, not what was designed.

Done when: a side-by-side of printer-pitch vs review-grid fur exists and the
report says which of the two effects (grid, tint) explains the undercoat.

### Step 6 — Freeze v3, viewer defaults, wish list

- Save the fitted library as `work/resins/vero-j850-provisional-v3.json`
  with changelog and the fit residual table; keep v2 for reproducibility of
  p1 reports.
- Viewer: make `stage-print-photo` the default preset when a print-aware
  mapping is loaded, or at least list the print-aware zarrs in the input
  catalog root used by `material.json`. Small, but it is the point of the
  episode: the viewer should predict the print by default.
- `report6.md`: final contact sheet v3; per case what is closed, what is
  photo-limited, what needs coupons. Refresh the coupon list with what the
  fit could not resolve (expect: absolute lightness of pale mixtures, dilute
  white tint, black-vs-yellow balance in amber), and the photo protocol
  (tripod, fixed exposure/RAW, white card + ruler, one overhead light,
  optional light-box backlit shot) so that step 3's camera matching becomes
  routine.

## Rules (minimal)

- `.local/real_print/batch1/` stays untouched except for added notes,
  sheets and renders under `renders-p2/`.
- No backward compatibility: stage schema, presets, specs and `work/`
  scripts may change freely. If `vdbmat/src` changes (camera pose, rough
  boundary option), keep its tests green and note the submodule commit.
- Every number in a report must be reproducible from a command line or a
  spec JSON committed under `work/`.
- Fit the library, not the cases: no per-case constants.

## Out of scope

New prints, spectral rendering, GrabCAD halftone emulation beyond the
crops, Blender/Cycles parity, a full colour-managed photo pipeline.
