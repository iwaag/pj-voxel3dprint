# p2 step 1 report — structured environment (dome) and finish

## Done

- **Stage schema 1.4.0** (vdbmat, `examples/pipeline_run/demo/mitsuba_stage.py`).
  I chose the dome/envmap option over a list of area lights:
  - `ambient` gains `cap_radiance`, `cap_deg`, `cap_softness_deg`,
    `cap_tilt_deg`, `cap_azimuth_deg`. With `cap_radiance` = 0 it is the old
    uniform `constant` emitter. With a non-zero cap it becomes a Mitsuba
    `envmap` built from a generated 1024×512 equirect bitmap
    (`dome_image()`): the base radiance (dark room) plus a soft-edged
    bright disc (smoothstep over `cap_softness_deg`), centred `cap_tilt_deg`
    from the zenith toward `cap_azimuth_deg` (the camera's azimuth
    convention). Why an envmap and not more area lights: every path that
    escapes still finds light (p1 report2, trap 1), only one environment
    emitter is allowed, and a disc plus a dark surround is what the photos
    show.
  - New `finish` section: `exterior_roughness` (0 = smooth). A value > 0 turns
    the `exterior_*` dielectric shapes into GGX `roughdielectric` with that
    alpha. Index-matched (`null`) boundaries and interior interfaces stay as
    they are.
  - Wired through: `mitsuba_stage_core.py` (structure key: any dome or
    roughness change rebuilds the scene, because the envmap data is padded
    and a live traverse is not worth it), `mitsuba_stage_presets.py`
    (digest: a config that uses no 1.4.0 feature hashes in the 1.3.0 form,
    and one that uses no 1.3.0 feature either hashes in the 1.2.0 form, so
    older sessions keep replaying), `mitsuba_viewer_session.py` (version-
    dependent `ambient` keys, `finish` from 1.4.0), `mitsuba_stage_binder.py`
    (cap controls on the **Ambient** tab, new **Finish** tab),
    `mitsuba_gui_capture.py` (tab list). Manual section updated and all
    panel screenshots recaptured (`docs/gui/images/*.png`, new
    `finish-panel.png`).
  - Shipped presets bumped to 1.4.0. `stage-print-photo` has been replaced (below).
    The p1 version is kept as `work/compare/stages/print-photo-p1.stage.json`
    so p1 renders stay reproducible (`--stage-config` on `render_stage.sh`).
  - Tests: new tests for 1.4.0 parsing, version gating, validation,
    `dome_image` direction/values, `apply_stage` envmap + rough finish, and
    session round-trip/digest. The full vdbmat suite passes: **725 passed,
    2 skipped** (pyopenvdb). Ruff: no new findings (the 7 pre-existing ones
    in `blender_glass_demo.py` are unchanged); touched files are formatted.
- `work/compare/contact_sheet.py`: the Markdown table now has a ΔE76 column
  (against the first measured image of the row, i.e. the photo).

### New `stage-print-photo` (light layout numbers)

| item | p1 | p2 |
|---|---|---|
| environment | uniform 0.75 | dome: base **0.10** (dark room) + cap **2.4**, radius **30°**, softness **15°**, tilt **30°** toward azimuth **−54°** (= the camera's side) |
| key light | (−0.3,−0.4,1) ×4r, scale 1.2, 2.2 | **off** |
| backlight | 0.75 (= ambient, hidden) | **0.10** (= dome base, hidden) |
| finish | smooth | smooth (`exterior_roughness` 0) |
| floor | 0.8 solid, drop 0.005 | same; measured corner 0.70–0.71 linear |
| camera / render | az −54 el 65 d 3.6 fov 35; 512² spp128 depth 32 rr 32 | unchanged |

Why the cap is tilted toward the camera and not into the mirror direction:
with the cap in the top face's mirror direction (az 126°), every top face
reflects a bright disc: agate darks wash out and amber turns grey. In a
hand-held photo taken from above, the phone and the photographer sit in that
mirror direction and block the ceiling light, so the glossy top reflects
a dark room. With the cap on the camera side, the top reflects dark and the
side faces and edges pick up the cap.

## Commands

```
# final renders (spp 256 + OptiX denoise), v2 library zarrs from p1
O=.local/real_print/batch1/renders-p2/step1
work/compare/render_stage.sh .local/pink-agate-v3/print-aware-v2/agate-optical.zarr   $O/agate-v2-dome.png --spp 256 --denoise   # 337 s
work/compare/render_stage.sh .local/amber-branching/print-aware-v2/amber-optical.zarr $O/amber-v2-dome.png --spp 256 --denoise   # 357 s
work/compare/render_stage.sh .local/floating-fur/print-aware-v2/fur-optical.zarr      $O/fur-v2-dome.png   --spp 256 --denoise   # 244 s
R=$(realpath work/compare/stages/print-photo-rough05.stage.json)   # = new preset with exterior_roughness 0.05
work/compare/render_stage.sh .local/amber-branching/print-aware-v2/amber-optical.zarr $O/amber-v2-dome-rough05.png --stage-config $R --spp 256 --denoise  # 312 s
work/compare/render_stage.sh .local/floating-fur/print-aware-v2/fur-optical.zarr      $O/fur-v2-dome-rough05.png   --stage-config $R --spp 256 --denoise  # 243 s
vdbmat/.venv/bin/python work/compare/contact_sheet.py work/compare/specs/batch1-p2s1.json \
    $O/contact-sheet-p2s1.png --table $O/contact-sheet-p2s1.md
```

The layout exploration (uniform, cap in mirror direction, cap toward camera,
rough 0.05/0.08/0.10/0.15, a dim fill panel, 45° cap, tilt 15/25/30) was done
at 256–384², 64–128 spp with a scratch script that patched the scene dict. Only
the chosen configuration and the rough-0.05 comparison are kept as
reproducible renders.

## Images

- `.local/real_print/batch1/renders-p2/step1/contact-sheet-p2s1.png`:
  photos | v2 on the p1 stage | v2 on the dome stage | rough 0.05 (amber, fur).
- `…/step1/{agate,amber,fur}-v2-dome.png`, `…/{amber,fur}-v2-dome-rough05.png`.

## Result (same v2 library, same camera and rectangles as p1 step 7; ΔE76 to the photo)

| region | p1 stage | dome stage | dome + rough 0.05 |
|---|---|---|---|
| agate top face | 4.1 | 5.0 | – |
| agate pink band | 9.7 | 13.6 | – |
| agate dark teal | 9.9 | **3.6** | – |
| amber top face | 6.3 | 7.4 | 7.2 |
| fur hair field | 5.8 | 5.2 | 4.8 |
| fur clear margin | 6.6 | 10.4 | 10.2 |
| sum | 42 | 45 | |

- **Visual:** the fur block now has bright, sharp edge lines along the top and
  side edges, and the clear shell reads as glass over the paper instead of
  a milky slab, like Unknown-7/-8. The shadow is short and soft, and the floor
  measures 0.70 linear. Agate darks are deep, and the teal reads blue-black as
  in the photo. Amber is darker and more orange-olive.
- **Dark teal (+10 L in p1) was the stage.** The p1 report7 refutation only
  checked the darkest 1 %. The region mean was lifted by the uniform 0.75
  environment reflected in the glossy top (~4 % × 0.75). With a dark room
  reflected, the region lands at L 22 vs the photo's 21.
- The same effect makes agate pinks (L 47 vs 58) and amber (L 28 vs 34)
  darker. The v2 library was hand-tuned against the bright stage, so part of
  its lightness was stage reflection. This is for the step 4 fit, not the
  stage: there are no per-stage corrections.
- Fur clear margin L 72 vs 82: through the clear block the render now sees
  paper that the hair mass and the block edges partly shade, and the photo
  is top-down while the render is at 65°. This rectangle is not comparable
  until the cameras match (step 3).

### Finish

- `roughdielectric` α 0.05 already blurs the fur edge lines visibly
  (α 0.10–0.15 more so), while the region numbers barely move (≤ 0.4 ΔE).
  On amber it gives a satin sheen, but with the dark-room reflection the
  top-face mean does not change (28 L either way).
- The done criterion is sharp edge lines on the clear block, so the preset
  stays **smooth**. The option stays in the schema for coupon work
  (e.g. matte support faces).

## Learned

- The largest single stage error in p1 was not the light level but **what
  the glossy top face reflects**. A uniform bright environment adds a
  constant ~0.03 linear to every dark colour.
- The dome needs no key light. The cap alone gives the soft shadow, and
  the key rectangle shows up as a reflected straight-edged patch on the
  amber top (tried as a fill panel).
- The dome costs nothing in render time (same as p1 ± noise), because the envmap
  is importance-sampled. The floor is a bit noisier at spp 64 than under a
  constant emitter; at spp 256 + denoise it is clean.

## Skipped / notes

- Lights list (`lights: [...]`): not needed.
- The `work/compare/stages/print-photo-checker.stage.json` diagnostic
  (1.3.0) stays as it was for report4 reproducibility; 1.3.0 files still parse.
- vdbmat submodule commit: see the step 1 commit message in the parent repo.
