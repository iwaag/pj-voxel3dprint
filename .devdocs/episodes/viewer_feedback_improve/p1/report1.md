# p1 step 1 report — evidence sheet and gap table

## Done

- **Source data recovered.** None of the registered `.local/<case>` trees
  (pink-agate-v3, floating-fur, amber-branching, amber-previews) existed in
  this checkout. All were regenerated from the generators in `work/`; the
  resulting optical zarrs are byte-identical (`zarr_store_sha256`) to the
  `optical_sha256` recorded in the archived sessions:
  - case1 `pink-teal-agate-optical-v3.zarr` fa3dc222… ✓
  - case2 `amber-branching-optical.zarr` 3f5a815b… ✓, `amber-print-black80-optical.zarr` 6c59db58… ✓
  - case3 `floating-fur-optical-v1.zarr` dac059d8… ✓
  - Amber needed care: the archived `case2/data/seed-4101` was made with an
    older pores threshold (0.60, found by bisection; bit-identical at 0.60),
    but the printed seed-4102 matches the checked-in config (0.374). Check:
    `generate_branching_veins.py` output remapped with `export_kohaku_tree.py`'s
    table equals the archived `kohaku_tree.material_id.npy` 100 %.
  - Script: `work/compare/rebuild_batch1_sources.sh` (~15 min, CPU).
- **Provenance:** `.local/real_print/batch1/provenance.md` (per case: source
  labels, export script + recipes, resin order, print mode, which mapping made
  each archived PNG, camera/stage).
- **Contact sheet script:** `work/compare/contact_sheet.py` + JSON spec
  `work/compare/specs/batch1-v0.json` →
  `.local/real_print/batch1/contact-sheet-v0.png`.
  ```
  vdbmat/.venv/bin/python work/compare/contact_sheet.py work/compare/specs/batch1-v0.json .local/real_print/batch1/contact-sheet-v0.png
  ```
- **Gap table:** `gap-table.md` (5 differences per case, tagged M/S/R/U).

## Learned

- The agate and fur "semantic" mappings are already recipe × `BASE` mixes, but
  `BASE` (white σs 520/m, CMY σa ≤ 250/m) makes 5 mm of pigment mix only ~1
  optical depth — hence the translucent pastel look. Amber print-aware v1 is
  2–3× stronger but still translucent and too black-dominated.
- Amber was printed from the **10-class** `amber-4102-branching-v2` labels, not
  the 6-class `kohaku_tree_build` remap archived in batch1.
- Archived sessions all use backlight radiance **8** (not the canonical 1) and a
  floor of 0.25 — a large part of the "glowing translucent" look.
- Archived session `render` blocks often do not match the PNG size (e.g. fur
  sidecar says 512×1024 depth 8, PNG is 1024×2048 named "depth64"), so their
  depth/spp are unreliable. Step 2+ renders use documented command lines.
- Photo observations: case3 undercoat (mat 2, only 18 % white) already reads as
  an opaque-ish blue-grey matte layer → white σs must be several thousand /m.
  Amber top surface looks satin rather than mirror-glossy.
- Session replay works headlessly on `cuda_ad_rgb` (~100 s for 512×1024, 128 spp,
  depth 8). Note: ComfyUI holds ~44 GB of the 48 GB GPU; renders still fit.

## Skipped / not archived

- `.local/` is git-ignored: provenance.md and the contact sheet live only
  locally; the facts are summarised here.
- The per-export `*.resin-recipes.json` were never archived; the numbers are
  identical to the `RECIPES`/`REC` dicts in the export scripts (step 3 will
  read them from there).
