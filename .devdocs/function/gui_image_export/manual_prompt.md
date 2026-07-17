# Prompt: generate the stage viewer GUI manual from a capture run

This file is a self-contained instruction set for an AI agent writing or
refreshing `vdbmat/docs/gui/stage_viewer_manual.md` from the output of
`vdbmat/examples/pipeline_run/demo/tools/mitsuba_gui_capture.py`. It assumes
no other context from this conversation is available — read it cold.

## What this manual is (and is not)

The manual documents the **GUI panel** of `mitsuba_stage_viewer.py`: what
tabs exist, what each widget does, and what a first-time user should click
in what order. It is not a scientific reference — optical mapping schema,
digest/provenance semantics, and pipeline internals are already documented
in `README_QUICK.md` and `.devdocs/vision/mitsubagui_improve/roadmap.md`;
link to those rather than re-explaining them.

Viewport (3D render) content is explicitly out of scope. Captures may show
a low-spp placeholder image — never describe or caption what is rendered in
the viewport, only the panel around it.

## Inputs you have

1. A capture directory, e.g. `.local/gui_image_export/captures/<timestamp>/`,
   containing:
   - `manifest.json` (schema `vdbmat.gui-capture-manifest/1.0`) — one entry
     per screenshot, with `tab`, `actions` (what was clicked to reach this
     state), `status_text`, `panel_text` (every visible line of text in the
     control panel, in DOM order), and `image_full` / `image_panel` file
     names.
   - The PNG files themselves (`NN-<slug>-full.png` covers the whole
     browser viewport; `NN-<slug>-panel.png` is cropped to just the control
     panel).
2. `README_QUICK.md`, sections "Tune the Stage Interactively in a Browser
   (viser GUI)" through "Operations: Staying in Control During Day-to-Day
   Use" — the existing prose description of viewer workflows.
3. `.devdocs/vision/mitsubagui_improve/roadmap.md` — background on why each
   tab/workflow exists.

## Ground-truth rule

Every factual claim about a widget's label, a button's name, or a status
message's wording must come from `manifest.json`'s `panel_text` /
`status_text` fields or from the README sections above — never from
eyeballing a screenshot. Screenshots illustrate; they do not source facts.
If a widget you want to describe does not appear in any `panel_text` entry,
either find it in the README or omit it — do not guess its behavior from
its position in an image.

If a capture entry has a non-null `error`, that tab/interaction could not be
reached this run. Do not silently drop it — note it in a short "known gaps"
line at the end of the relevant section so a re-run is prompted, rather than
letting the manual quietly go stale.

## Chapter structure

Write `vdbmat/docs/gui/stage_viewer_manual.md` with these sections, in
order:

1. **Launching the viewer** — the `uv run --group mitsuba-viewer python
   examples/pipeline_run/demo/mitsuba_stage_viewer.py ...` invocation from
   README_QUICK.md, and what `viewer ready: http://127.0.0.1:PORT` means.
2. **Screen layout** — one panel-scoped image (any tab's `*-panel.png`,
   e.g. the Input tab) with a short paragraph pointing out the fixed
   regions: title/status line at top, tab strip, per-tab body below.
3. **Tab reference** — one subsection per tab in `manifest.json` order
   (Input, Preset, Render, Backdrop, Floor, Key light, Camera, Backlight,
   Output). For each:
   - the tab's `*-panel.png` image
   - a short list of the widgets visible in that tab's `panel_text`
     (labels only — do not invent a description of a control beyond what
     README_QUICK.md already says about it)
   - for Input and Preset specifically, also use the
     `input-dropdown-open` and `preset-summary` capture entries to show the
     selection state, and describe the Load/Rebuild vs. Refresh distinction
     using the exact wording from README_QUICK.md ("Changing the dropdown
     or clicking Refresh only updates the selection/catalog; neither
     action rebuilds the scene.") — do not paraphrase away that distinction,
     it is safety-relevant.
4. **Representative workflow** — a short numbered walkthrough (open Input
   tab → pick a candidate → Load/Rebuild → adjust Render tab max depth →
   Output tab → Render final) cross-referencing the images already placed
   in section 3. Do not introduce a new screenshot here.
5. **Reading viewer status** — explain the status line format shown at the
   top of every panel capture (`status_text` in the manifest, e.g. "preview
   settled/traverse ... — PIXELSTATS ..."), sourced from
   README_QUICK.md's "Operations: Staying in Control During Day-to-Day Use"
   section, not invented.

## Image intake rule

1. Do not reference `.local/...` paths from the manual body — every image
   the manual links to must already be copied into
   `vdbmat/docs/gui/images/` under a stable, tab-based name (`input-panel.png`,
   `render-panel.png`, `input-dropdown-open.png`, `preset-summary.png`, ...).
   Rename during copy; do not keep the timestamped/numbered capture
   filename.
2. Before copying, open each candidate image and check for local-machine
   information leaking into visible text fields — this is a known,
   documented risk (see plan.md's "スクリーンショットにローカル環境情報が
   写り込む" risk): the Output tab's "preset path" / "final PNG path" text
   boxes and the Input tab's summary text show whatever absolute
   `--work-dir` / `--out` path the capture run used, which can include a
   local username. Either:
   - crop the offending text field out of the image before copying, or
   - redact it in place (paint over the value with a solid rectangle,
     optionally labelled e.g. "(local path redacted)") so the surrounding
     layout stays intact — this is what the Output tab image in the current
     manual does, since cropping it would have cut off the Save/Render
     buttons that sit between the two path fields, or
   - accept it only if the path is a generic repo-relative-looking one
     (e.g. it clearly reads as `.../pj-voxel3dprint/vdbmat/.local/...`
     with no unrelated personal info), and note in the PR/commit message
     that this was reviewed.
   Never copy an image you have not opened and checked.
3. Only copy images you actually reference from the manual body. Unused
   captures stay in `.local/` and are not committed.

## Regeneration

State this verbatim near the top of the manual (after the title, before
section 1), so the next person knows how to refresh it:

> This manual is generated from screenshots captured by
> `examples/pipeline_run/demo/tools/mitsuba_gui_capture.py`. If the viewer's
> GUI changes (new/renamed tabs or widgets), re-run that script, then
> regenerate this manual by giving an agent
> `.devdocs/function/gui_image_export/manual_prompt.md` plus the new capture
> directory. Do not hand-edit around a stale screenshot — re-capture
> instead.

## Output checklist before you finish

- [ ] Every image link in the manual resolves to a file under
      `vdbmat/docs/gui/images/`.
- [ ] No `.local` path or local absolute filesystem path appears anywhere
      in the manual body.
- [ ] Every tab named in `TAB_NAMES` (see the capture script) has a
      subsection, even if brief.
- [ ] Any capture entry with a non-null `error` is mentioned as a known gap,
      not silently omitted.
- [ ] README_QUICK.md's viewer section gets a one-line pointer to this new
      manual (add it once; do not duplicate on regeneration).
