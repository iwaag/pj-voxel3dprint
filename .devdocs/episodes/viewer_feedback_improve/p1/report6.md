# p1 step 6 report — comparison script with exposure normalisation

## Done

- `work/compare/contact_sheet.py` extended. Old specs render pixel-identically;
  `contact-sheet-v0.png` was rebuilt and compared. An entry object may now carry
  - `"white": [x0, y0, x1, y1]`: white paper / floor patch,
  - `"regions": {"name": [x0, y0, x1, y1], ...}`,

  with rectangles as fractions of the image size. Each image gets a per-channel
  linear gain that maps the white patch mean to 0.85 sRGB neutral. This removes
  phone auto-exposure and auto-white-balance, and render exposure, in one step.
  For each region the sheet reports mean normalised sRGB and CIE Lab (D65,
  sRGB primaries). The tiles show the rectangles: grey/white = white patch,
  then red, blue and yellow for the regions. A table sits under each row.
  `--table OUT.md` writes the same numbers as Markdown.
  Note: this change ended up in commit `46dc75c` (the previous session's
  hand-over commit ran while this step was being edited). It belongs to step 6.
- `work/compare/specs/batch1-v1.json`: one top-down-ish photo per case
  (Unknown-2 / -5 / -9), the step 2 semantic render and the step 3 print-aware
  v2a render, all on the print-photo stage. Regions:
  agate top-face mean, salmon/pink band, dark teal; amber top-face mean;
  fur hair-field mean, clear margin. The photo and render cameras differ, so
  each image has its own rectangles, placed on the same kind of feature.

```
vdbmat/.venv/bin/python work/compare/contact_sheet.py work/compare/specs/batch1-v1.json \
    .local/real_print/batch1/contact-sheet-v1.png --table .local/real_print/batch1/contact-sheet-v1.md
```

Outputs: `.local/real_print/batch1/contact-sheet-v1.png` (photo | semantic |
print-aware v2a, numbers under each row) and `contact-sheet-v1.md`.

## Result (normalised Lab, ΔE76 to the photo)

| case / region | photo L a b | semantic L a b (ΔE) | print-aware v2a L a b (ΔE) |
|---|---|---|---|
| agate top face | 36 +1 +2 | 56 +0 −3 (21) | 36 +3 −2 (**4**) |
| agate pink band | 58 +11 +11 | 63 +9 −2 (14) | 44 +16 0 (**19**) |
| agate dark teal | 21 −5 −4 | 65 −10 −7 (44) | 30 −2 −3 (**10**) |
| amber top face | 34 +5 +16 | 69 +1 +17 (35) | 32 +1 +6 (**11**) |
| fur hair field | 70 +1 −1 | 81 0 +2 (11) | 72 0 +5 (**6**) |
| fur clear margin | 82 0 −2 | 76 0 +2 (7) | 74 0 +4 (**10**) |

Print-aware v2a beats the semantic render everywhere except the pink band (the
semantic pink is pastel, so it is close in lightness by accident) and the fur
margin. What the numbers ask of step 7, as one shared library:

- agate pinks: too dark (L 44 vs 58), too magenta and too blue (b 0 vs +11).
  Magenta absorbs too much red and blue; the photo pinks are salmon.
- agate dark teal: too light (L 30 vs 21) and not cyan enough (a −2 vs −5).
  Part of this is the stage: the uniform ambient light reflected in the glossy
  top face lifts every dark colour (≈ 4 % × 0.75), while the photo reflects a
  mostly dark room.
- amber: right lightness, too little chroma (b +6 vs +16, a +1 vs +5). The
  neutral black share dilutes the yellow; yellow's green absorption makes it
  olive-grey instead of orange-brown.
- fur: the hair field and the clear margin are both too yellow (b +5 / +4 vs
  −1 / −2). This points at the UltraClear tint (σa 5/8/15) and the warm white
  (σa 20/20/25), which are the same resins in all three cases.

## Skipped / notes

- Numbers are relative. The photos are tone-mapped phone JPEGs, and the
  per-channel white-patch gain assumes the paper is neutral. The plan's
  threshold: don't chase ΔE below ~10.
- Photo-to-photo repeatability (the same region in a second photo of the same
  case) was not measured. A second photo row with its own rectangles in the
  spec would give it; phase 2's fixed-camera protocol makes that easy.
