# p1 hand-over (2026-09-25, stopped during step 4)

Steps 1–3 are done and committed, each with a report (`report1..3.md`). Steps 4–7
remain. Read `report1..3.md` first; this note lists only what is not obvious
from them.

## State

- Committed: step 1 `b9aebde`, step 2 `f30e4f4`, step 3 `e388fd1` (parent);
  the vdbmat submodule has two local commits (ambient / rr_depth). Nothing is
  pushed, in either repo.
- Step 4 was started as a background loop of renders into
  `.local/real_print/batch1/renders-p1/step4/`:
  fur and agate v2a at depth 8/32/64 (`--max-depth D --rr-depth D`), then
  fur d32 spp512 `--denoise`. **All renders finished after the stop**
  (fur d8/32/64: 77/140/154 s, agate d8/32/64: 92/169/260 s, fur spp512
  denoise: 385 s; also `fur-v2a-d32-spp512-dn.raw.png`). They have not been
  inspected yet. Next: compare them, write `report4.md`. To regenerate any of them:
  ```
  z=.local/floating-fur/print-aware-v2a/fur-optical.zarr   # or .local/pink-agate-v3/print-aware-v2a/agate-optical.zarr
  work/compare/render_stage.sh $z .local/real_print/batch1/renders-p1/step4/fur-v2a-d32.png --max-depth 32 --rr-depth 32
  work/compare/render_stage.sh $z .local/real_print/batch1/renders-p1/step4/fur-v2a-d32-spp512-dn.png --spp 512 --denoise
  ```
  `report4.md` is not written yet.

## Environment notes

- `.local/` is git-ignored. Everything under it (regenerated sources, zarr,
  renders, contact sheets, provenance.md) exists only on this machine. To
  rebuild: `work/compare/rebuild_batch1_sources.sh` (~15 min), then
  `work/resins/build_print_aware.sh work/resins/vero-j850-provisional-v2.json <TAG>` (~3 min).
- ComfyUI holds ~44 GB of the 48 GB GPU. Renders still fit (512², cuda_ad_rgb).
- Unset `VIRTUAL_ENV` before `uv run` in `vdbmat/` (the shell exports the
  vdbmat-utils venv). `work/compare/render_stage.sh` already does this.
- Most of each render's time goes to scene preparation, not sampling.
  The print-photo preset has roulette off (`rr_depth 32`), so a render takes
  ~130–190 s at 512², spp 128.
- ruff: the vdbmat repo has pre-existing findings (8 check, 7 unformatted
  files). Compare against the baseline; don't expect clean output.

## Things to keep in mind for the remaining steps

- **Step 4:** the milky fur shell in step 3 turned out to be fireflies, not
  depth. The v2a fur shell already reads clear at depth 32. The depth
  comparison mainly needs to confirm that and pick the preset default (32 now).
  Always pass `--rr-depth` ≥ `--max-depth`, or roulette comes back.
  Optional matte bottom faces: only do this if a visible gap remains (amber
  top looks satin in photos, see gap-table).
- **Step 5:** the plan's route is: agate export → crop slices →
  `vdbmat-utils convert-image-stack` → map through the same library. Two notes:
  - The export (`work/agate/export_menou_voxelprint.py`) writes the full
    1418×354×357 stack to `work/agate/menou_voxelprint_staging/` (ignored).
  - A direct crop generator that reuses the export's `hash_uniform` and
    `RECIPES` would be much faster.

  Use one IOR for all six resin labels, otherwise every dither cell becomes a
  dielectric interface.
- **Step 6:** extend `work/compare/contact_sheet.py` (spec JSON driven). Photos
  are phone JPEGs; normalise on a paper/floor patch.
- **Step 7:** tune only `vero-j850-provisional-v2.json`. Build the final set
  with tag `v2` (the plan wants `.local/<case>/print-aware-v2/`); `v2a` was the
  iteration tag. Visible colour gaps from step 3:
  - agate pinks are too magenta; the photo is salmon/coral, so yellow is too
    weak or magenta's red absorption too strong;
  - amber is too dark and neutral; the photo is olive-orange, so black is
    too strong relative to yellow/magenta;
  - fur hair mass is too grey; the photo is a light blue-grey undercoat with
    beige hairs, so check white σs and the black share.
- Archived session `render` blocks don't match their PNGs (see provenance).
  Reproduce renders from command lines, not from those sidecars.
- Stage-config 1.3.0 digests: while `ambient` is disabled and `rr_depth` is
  5, a config hashes in the 1.2.0 form (`stage_config_digest`). If you add
  more fields, extend that normalisation, or the archived sessions stop
  replaying.
