# p2 step 3 report: camera-matched renders and pixel-wise diffs

## Done

- **Camera pose in the stage schema** (vdbmat `e76c6bb`, stage-config
  1.4.0): `camera` accepts `position_m`, `target_m` and `up` (world metres)
  besides the orbit form. `fov_deg` is horizontal in both forms. Validation:
  position and target come together and differ, finite values, non-zero up.
  Wired through the digest (1.3.0 form while no pose is set), sessions
  (pose keys from 1.4.0), the core (a camera change updates `sensor.to_world`
  as before), the GUI (Camera tab: **form** orbit/pose, **position m** /
  **target m** / **up** vectors; manual section and screenshot updated),
  and `mitsuba_stage._sensor_override_dict` (the far clip grows with the
  pose distance; the orbit form is unchanged). Tests: +10 (config, session,
  binder). vdbmat suite: 734 passed, 2 skipped. Ruff: nothing new.
- **`work/compare/match_camera.py`**: PnP with unknown focal length for the
  60 × 30 × 5 mm slab: the four corner picks, plus 1–3 bottom corners where
  I noted them while picking. The photos carry no EXIF. Solver: IPPE
  (SQPnP when IPPE returns NaN) per focal length over a fov 20–80° scan,
  then `least_squares` on all 7 parameters with a depth ≥ 1 cm constraint
  and a fov prior of 22 ± 6° (5 px per σ). The prior matters only for
  near top-down views with four points, where focal length and distance
  trade off. The picks are in `specs/batch1-v3-picks.json`; the solved
  cameras are in `specs/batch1-v3.json`, which step 4 uses. Re-running
  reproduces `batch1-v3.json` byte for byte.
- `work/compare/matched_stages.py`: writes one stage file per photo (the
  print-photo preset + the matched camera, cap azimuth = the camera's
  azimuth so the ceiling light stays on the photographer's side, as in
  step 1). `work/compare/render_matched.sh TAG DIR` renders them.
- `work/compare/pixel_diff.py`: normalises both images on the photo's
  white rectangle (the matched view puts the same paper there), blurs the
  photo to render scale and resamples it into the render frame through the
  face homographies. It writes photo | render | warped photo | ΔL | Δa | Δb
  per photo, `contact-sheet-v3-<TAG>.png` and `diff-stats-<TAG>.md`.
- `region_table.py --renders TAG DIR` pairs every photo with its matched
  render. `region_delta.py` compares three-photo means with three-render
  means per named region.

## Finding: the prints are mirror images of the voxel volumes

With the model as-is, agate and fur only solve with the camera **below**
the slab, or with large residuals once there are more than four points.
With a y-mirrored model every photo solves with the camera above:

| photo | points | as-is RMS px | mirrored RMS px |
|---|---:|---:|---:|
| agate Unknown | 5 | 12.4 (camera below) | **2.2** |
| agate Unknown-3 | 6 | 55.1 (below) | **6.7** |
| fur Unknown-8 | 5 | 16.9 (below) | **2.6** |
| amber Unknown-5 (bottom face, z-mirror) | 6 | 44.4 with y-mirror | **3.0** |
| amber Unknown-6 (bottom face, z-mirror) | 7 | 16.3 with y-mirror | **7.4** |

With exactly four points both solutions have the same RMS, and only the
side of the camera decides. The fur is certainly photographed top-up
(glossy, perfectly clear top face). Its texture matches only with mirrored
handedness, so the print is mirrored, not flipped over. For amber, a
mirrored print lying bottom-up is a pure z-mirror of the volume. That fits
all three amber photos and the step 2 result: the bottom layers match, and
the face is matte (support side). **Most likely cause:** a y-axis convention
flip between the exported slice PNGs (row 0 = y 0) and the printer software.
None of the three export scripts flips anything. For the batch1 designs it
makes no difference (none has handed features), but for anything with
text or a handed shape it matters. It goes on the wish list (step 6).

To render the prints as photographed:
- `work/compare/flip_volume.py SRC DST --axes y|z|yz`, added to
  `rebuild_batch1_sources.sh` (agate and fur `-mirror-y`, amber
  `-mirror-z` material zarrs);
- `work/resins/build_print_aware.sh LIB TAG agate-m amber-m fur-m` →
  `.local/<case>/print-aware-<TAG>/<name>-mirror-optical.zarr` (~3 min);
- spec entries carry `volume: mirror_y | mirror_z`, and `match_camera.py`
  and `region_table.py` place the face coordinates accordingly.

## Commands

```
vdbmat/.venv/bin/python work/compare/match_camera.py work/compare/specs/batch1-v3-picks.json \
    work/compare/specs/batch1-v3.json --report .local/real_print/batch1/renders-p2/step3/pnp.md
work/resins/build_print_aware.sh work/resins/vero-j850-provisional-v2.json v2 agate-m amber-m fur-m
O=.local/real_print/batch1/renders-p2/step3
vdbmat/.venv/bin/python work/compare/matched_stages.py work/compare/specs/batch1-v3.json $O/stages
work/compare/render_matched.sh v2 $O --spp 256 --denoise          # 9 views, 191-281 s each
vdbmat/.venv/bin/python work/compare/pixel_diff.py work/compare/specs/batch1-v3.json v2 $O
vdbmat/.venv/bin/python work/compare/region_table.py work/compare/specs/batch1-v3.json $O/regions-v3-v2.json --renders v2 $O --overlay $O/overlay
vdbmat/.venv/bin/python work/compare/region_delta.py $O/regions-v3-v2.json --md $O/region-delta-v2.md
```

## Matched cameras

| case | photo | volume | points | RMS px | fov ° | elevation ° | distance mm |
|---|---|---|---:|---:|---:|---:|---:|
| agate | Unknown-2 | mirror_y | 4 | 2.36 | 21.1 | 85.8 | 266 |
| agate | Unknown | mirror_y | 5 | 2.21 | 20.9 | 65.6 | 223 |
| agate | Unknown-3 | mirror_y | 6 | 6.72 | 14.9 | 38.7 | 330 |
| amber | Unknown-5 | mirror_z | 6 | 3.00 | 22.2 | 43.0 | 226 |
| amber | Unknown-4 | mirror_z | 4 | 2.32 | 24.8 | 65.2 | 219 |
| amber | Unknown-6 | mirror_z | 7 | 7.45 | 29.8 | 53.6 | 212 |
| fur | Unknown-9 | mirror_y | 4 | 1.95 | 14.6 | 72.9 | 321 |
| fur | Unknown-8 | mirror_y | 5 | 2.60 | 22.8 | 55.8 | 330 |
| fur | Unknown-7 | mirror_y | 4 | 3.33 | 10.9 | 73.2 | 487 |

RMS 2–7.5 px on 2048 px frames (≤ 0.35 %). The 6–7 px cases include
bottom corners that I estimated rather than saw directly.

## Images

- **`.local/real_print/batch1/contact-sheet-v3.png`** (=
  `renders-p2/step3/contact-sheet-v3-v2.png`): one row per photo: photo |
  matched render (v2 library, dome stage) | ΔL | Δb.
- `renders-p2/step3/diff-<case>-<photo>-v2.png`: photo | render | warped
  photo | ΔL | Δa | Δb.
- `renders-p2/step3/overlay/`: regions and tiles drawn on every photo and
  render.

## Result

Silhouettes, side faces, band positions and the shadow direction line up in
all nine pairs, so a difference image is now meaningful. Face-mean
differences (photo − render, `diff-stats-v2.md`):

| case | photo | mean ΔL | mean Δa | mean Δb | mean ΔE |
|---|---|---:|---:|---:|---:|
| agate | Unknown-2 | −12.9 | +2.1 | −0.6 | 15.8 |
| agate | Unknown | +6.6 | +4.3 | −2.4 | 11.2 |
| agate | Unknown-3 | +3.1 | +3.9 | −3.7 | 10.7 |
| amber | Unknown-5 | +0.3 | +6.9 | +9.3 | 12.2 |
| amber | Unknown-4 | +5.8 | +6.3 | +1.3 | 9.3 |
| amber | Unknown-6 | +4.3 | +5.6 | +0.6 | 7.8 |
| fur | Unknown-9 | −7.5 | +0.1 | −2.3 | 9.6 |
| fur | Unknown-8 | −5.3 | +0.4 | −1.4 | 7.2 |
| fur | Unknown-7 | −9.9 | −0.3 | +0.5 | 11.2 |

- The ΔL sign flips between photos of the same case (agate −13 / +7 / +3).
  That is step 2's per-photo exposure normalisation, now visible as a
  uniform tint of the whole ΔL map. Band-shaped ΔL/Δb structure on top of
  it (agate) is band colour error plus ~0.3 mm residual misregistration at
  band edges.
- Consistent across all photos of a case (so render-side):
  - agate a +2…+4, b −1…−4: pinks and the clear band are too little red
    in the render;
  - amber a +6…+7: the render lacks orange/red; the amber is too olive;
  - fur: the render is 5–10 L lighter. The ΔL map shows blue stripes on
    the undercoat, i.e. the photo undercoat is darker/greyer than the
    render. This is step 5's question.

Named-region comparison (three-photo mean vs three matched-render mean,
`region-delta-v2.md`), 21 regions: **sum ΔE76 = 174** with v2 on the dome
stage. This is the baseline for step 4. It is not comparable with p1's 42
(6 regions, one photo, different rectangles).

| region group | photos (mean L) | v2 render | largest gaps |
|---|---|---|---|
| agate pinks (pale-pink, dusty-rose, clear-band) | 50 / 39 / 45 | 49 / 40 / 44 | a +28/+4/+26 vs +16/+2/+12: **hue, not lightness** |
| agate teals / darks | 21–29 | 27–35 | render 6–9 L too light (the matched views are more oblique than the p1 preset) |
| amber hosts | 26–33 | 22–28 | render 4–5 L darker and a +0…+2 vs +3…+11 |
| fur undercoat / tuft / dark | 69 / 68 / 63 | 74 / 72 / 69 | render too light |

## Learned

- The prints are mirrored. Without camera matching this would have stayed
  invisible: the p1 rectangles were placed on similar-looking features.
- With the room reflected correctly (step 1) and the geometry matched,
  the agate pinks are right in lightness and wrong in **hue** (too
  little red). p1's "pinks −8 L" was the darkest photo (step 2).

## Skipped / notes

- The white rectangle for the matched renders is the photo's (same paper
  area). It can include a bit of the render's shading gradient; the
  numbers compare within that convention.
- The Δ maps have ~0.2–0.3 mm residual registration error, which shows as
  thin ±ΔL lines along band edges; region means are not affected much
  (regions are ≥ 2 mm).
- I did not add a mirrored-export check to the export scripts. That is a
  design change for the print pipeline and is listed for step 6.
