# batch1 provenance (written 2026-09-25, viewer_feedback_improve p1 step 1)

Printer: Stratasys J850, High Quality (14 µm layers, 600×300 dpi = 42.3×84.7 µm
pixel pitch), glossy finish. "Clear" slot = **Vero UltraClear** (not VeroClear;
see `printer_info/memo.txt`). Resin order in every recipe below:
white, black, clear, cyan, magenta, yellow (VeroPureWht, VeroBlack,
VeroUltraClear, VeroCyan, VeroMgnt, VeroYellow). All three are 60×30×5 mm slabs.
Halftone: deterministic 3-D hash dither of the per-material recipe at printer
pitch (each export script, `hash_uniform` / `noise`).

All source volumes are **regenerated** in this checkout by
`work/compare/rebuild_batch1_sources.sh`; the original `.local/<case>` trees
were not present. Each regenerated optical zarr is byte-identical
(`zarr_store_sha256`) to the `optical_sha256` in the archived sessions, so the
regenerated data *is* the data that was rendered/printed.

## case1 — pink/teal agate (`pink_teal_agate`)

| item | value |
|---|---|
| source labels | `.local/pink-agate-v3/source/pink-teal-agate-strata-v3.{voxels.json,material_id.npy}` (0.2 mm, 25×150×300, 14 materials) from `work/agate/generate_pink_agate.py` (seed 104729) |
| print export | `work/agate/export_menou_voxelprint.py` → `menou` slices, `RECIPES` (14 materials; mat 1 = 0.3 mm 100 % clear shell, exact 0.3 mm on print grid) |
| recipe file | `work/agate/menou_voxelprint_staging/menou.resin-recipes.json` (not archived; same numbers as `RECIPES` in the export script and the generator) |
| rendered optical | `.local/pink-agate-v3/viewer/pink-teal-agate-optical-v3.zarr` sha256 fa3dc222… (verified) |
| mapping of archived renders | `pink-teal-agate-strata-v3.optical-mapping.json` = recipes × generator `BASE` (white σs 520/m, CMY σa ≤ 250/m, clear σs 2/m). Recipe-based but ~10–50× too weak → effectively **semantic/translucent** |
| archived PNGs | `pink-teal-agate-v3-saturated-current-camera-HQ{,-02}.png` (fa3dc222 input). Older `pink-agate-*` / `pink-teal-agate-v3-current-camera-HQ` are earlier designs (v2 / unsaturated v3, sha 0d42e24b / a114c08d / 1af0a152), **not** what was printed |
| session camera | az −53.95°, el 67.48°, fov 34.14°, dist 4.48 (−02), 1.79 (older) |
| session stage | floor solid 0.25/0.25/0.28, backdrop teal (0.02,0.09,0.11), key (12,11,9) ×1.4 from (−1,−1.5,2.1), **backlight 8** |

## case2 — amber / kohaku (`kohaku`)

| item | value |
|---|---|
| source labels | `.local/amber-branching/source/amber-4102-branching-v2.*` (10 materials) from `generate-formation` seed 4102 with `work/amber/amber-preview.formation.json` (as checked in, pores threshold 0.374) + `work/amber/generate_branching_veins.py` (seed 42120). Verified: remapping it with `export_kohaku_tree.py`'s table reproduces the archived `case2/data/kohaku_tree_build/kohaku_tree.material_id.npy` 100 % |
| print export | `work/amber/export_kohaku_tree_voxelprint.py` (reads the **10-class** branching-v2 labels directly; `kohaku_tree_build` 6-class remap is *not* what was printed) with `RECIPES` "black-minus20" (69–96 % clear in host classes, 31–51 % clear in veins) |
| recipe file | `work/amber/kohaku_tree_voxelprint_staging/kohaku_tree.resin-recipes.json` (not archived; numbers = `RECIPES` in export script = `RECIPES` in `build_print_preview_mapping.py`) |
| rendered optical, semantic | `.local/amber-branching/viewer/amber-branching-optical.zarr` sha256 3f5a815b… (verified) → `amber-branching-current-frame-hq.png`, `amber-branching-final-hq.png` |
| rendered optical, print-aware v1 | `.local/amber-branching/print-preview-v2/amber-print-black80-optical.zarr` sha256 6c59db58… (verified; mapping from `build_print_preview_mapping.py`, white σs 800, black σa 450, CMY σa ≤ 520) → `kohaku_tree-print-aware-black-minus20-HQ.png`, `kohaku_tree-black-minus20-current-camera-HQ.png` |
| other archived PNGs | `kohaku_tree-print-aware-HQ.png` (sha 50ad5481, pre-black-reduction recipe, not printed); `amber-final-hq.png` (seed 4102 without branching veins); `amber-seed-comparison.png`, `amber-branching-veins-preview.png` (2-D previews) |
| `seed-4101/` | an **older** formation (pores threshold 0.60, bubbles 0.04 %); not used by the print |
| session camera | az −53.95°, el 67.48°, fov 34.14°, dist 1.28–3.46 |
| session stage | same art stage as case1 (backlight 8) |

## case3 — floating fur (`floating_fur`)

| item | value |
|---|---|
| source labels | `.local/floating-fur/source/floating-fur-v1.*` (0.2 mm, 7 materials) from `work/fur/generate_floating_fur.py` (seed 77171) |
| print export | `work/fur/export_floating_fur_voxelprint.py`: hairs are **re-drawn at printer pitch** (0.06 mm tips, 0.10–0.16 mm roots), `REC` 7 materials, mat 1 = 100 % clear host, hairs 18–48 % white, dark hairs 5.5–10 % black |
| recipe file | `work/fur/floating_fur_voxelprint_staging/floating_fur.resin-recipes.json` (not archived; = `REC`) |
| rendered optical | `.local/floating-fur/viewer/floating-fur-optical-v1.zarr` sha256 dac059d8… (verified); mapping = recipes × same weak `BASE` as agate (hairs σs ≈ 95–250/m) → **semantic/translucent** |
| archived PNG | `floating-fur-current-camera-HQ-depth64.png` (1024×2048). Note: the sidecar session says `max_depth 8`, 512×1024 — the file name says depth 64. Sidecar `render` blocks generally do not match the PNG size (viewer final-render settings are not recorded there), so treat depth/spp in all archived sidecars as uncertain |
| session camera | az −53.95°, el 67.48°, fov 34.14°, dist 3.5 |
| session stage | art stage, backdrop teal visible at top, backlight 8 |

## Photos

`case*/result/Unknown-*.jpg`, phone JPEGs, ~2048², white paper on a desk,
overhead diffuse room light, auto exposure/white balance. Elevation ≈ 60–90°
(case1 `Unknown-2`, case3 `Unknown-9` are near top-down; `Unknown-3/5/8` are
≈ 35–45°). No white card, no scale, no fixed light.

## Contact sheets

- `contact-sheet-v0.png` — photos vs the archived renders listed above.
  Built by `vdbmat/.venv/bin/python work/compare/contact_sheet.py work/compare/specs/batch1-v0.json .local/real_print/batch1/contact-sheet-v0.png`.
