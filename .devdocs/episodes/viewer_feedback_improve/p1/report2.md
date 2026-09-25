# p1 step 2 report — `stage-print-photo` preset

## Done

- New preset `vdbmat/examples/pipeline_run/demo/presets/stage-print-photo.stage.json`
  (stage-config 1.3.0):
  - floor solid 0.80 neutral, scale 8, **drop 0.005** (see below); backdrop off
  - **ambient** (new, see schema change) 0.75 neutral: diffuse room light
  - key light direction (−0.3, −0.4, 1.0), distance 4, scale 1.2, radiance 2.2
    neutral (gives directional shading and a short soft shadow)
  - camera az −54°, el 65°, dist 3.6, fov 35
  - backlight radiance 0.75 (= ambient; see below)
  - render 512², spp 128, depth 32, denoise off
  - Measured floor (linear, corners of the 512² frame): 0.64–0.72.
- **Schema change (stage-config 1.3.0):** new `ambient` section
  `{enabled (default false), radiance}` → Mitsuba `constant` emitter
  (`stage_ambient`), in `mitsuba_stage.py` (+ `apply_stage`),
  `mitsuba_stage_core.py` (structure key + live radiance traverse),
  `mitsuba_stage_binder.py` (new **Ambient** GUI tab), `mitsuba_viewer_session.py`
  (session effective stage requires `ambient` only for 1.3.0),
  `mitsuba_stage_presets.py` (digest: a default/disabled ambient hashes in the
  1.2.0 form, so every existing session digest stays valid — all 13 archived
  batch1 sessions still parse). Shipped presets bumped to 1.3.0. GUI manual
  screenshots recaptured (`mitsuba_gui_capture.py`, Ambient tab added) and the
  manual gained an Ambient section. vdbmat tests: 698 passed, 2 skipped
  (pyopenvdb); ruff: no new findings (pre-existing ones untouched).
- Renders (all from the *existing* zarr = archived mappings), 512², spp 128,
  depth 32, `cuda_ad_rgb`, seed 20260628, ~80–95 s each:
  `.local/real_print/batch1/renders-p1/step2/{agate-semantic,amber-semantic,amber-printaware-v1,fur-semantic}-printphoto.png`
  ```
  work/compare/render_stage.sh .local/pink-agate-v3/viewer/pink-teal-agate-optical-v3.zarr .local/real_print/batch1/renders-p1/step2/agate-semantic-printphoto.png
  work/compare/render_stage.sh .local/amber-branching/viewer/amber-branching-optical.zarr .local/real_print/batch1/renders-p1/step2/amber-semantic-printphoto.png
  work/compare/render_stage.sh .local/amber-branching/print-preview-v2/amber-print-black80-optical.zarr .local/real_print/batch1/renders-p1/step2/amber-printaware-v1-printphoto.png
  work/compare/render_stage.sh .local/floating-fur/viewer/floating-fur-optical-v1.zarr .local/real_print/batch1/renders-p1/step2/fur-semantic-printphoto.png
  ```
  (`work/compare/render_stage.sh` = `mitsuba_stage_demo.py` with the
  print-photo preset and `cuda_ad_rgb`; extra args are passed through.)
- Added to `contact-sheet-v0.png` (spec `work/compare/specs/batch1-v0.json`).

## Learned (three stage traps found while tuning)

1. **Without ambient the render is dominated by noise.** Light can only enter
   the medium through the smooth dielectric boundary, so volpath cannot do
   next-event estimation into the interior; a single area light is found by
   chance only. An environment emitter is hit by nearly every escaping path.
   It is also what the photos show (ceiling/room light from everywhere).
2. **The canonical backlight is a black wall at this camera.** It is a
   7r-wide rectangle at `center − (1.6,−2.2,1.4)·4r`, tilted, and pokes above
   the floor exactly in the mirror direction of an az −54° camera. Dimmed to
   0.05 it blocks the ambient and appears as a large dark area reflected in
   the top face. Setting its radiance equal to the ambient makes it
   invisible. It cannot be removed from a preset (canonical scene entry).
3. **Floor coplanar with the object bottom (drop 0) produces seams**
   (dark lines at the slab mid-lines). drop 0.005 r ≈ 0.17 mm removes them.

## Result

Floor, shadow and highlight now read like the photos (white paper, short soft
shadow, soft sheen). The remaining gap is clearly the object: all semantic
renders are pastel/translucent, amber print-aware v1 is pale beige instead of
dark olive-brown, and fur's shell still looks milky with a dark rim around the
hair mass. Suspect for the rim/milkiness: every IOR difference between
materials (1.52 vs 1.53 vs 1.54 in the old `BASE`) creates internal dielectric
interfaces in `prepare_mitsuba_scene`; the print-aware v2 library will use one
IOR for all resins (step 3), step 4 checks depth.

## Skipped

- Per-case camera azimuth matching: photos are hand-held at random
  rotations; one preset camera is used for all cases.
- `exposure` scalar: not needed (floor lands at 0.64–0.72 linear directly);
  step 6 normalises images on the paper/floor patch anyway.
