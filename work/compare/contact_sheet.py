"""Photo-vs-render contact sheet for real-print comparisons.

Usage (from the repository root):

    vdbmat/.venv/bin/python work/compare/contact_sheet.py SPEC.json OUT.png

SPEC is a JSON document:

    {
      "title": "batch1 contact sheet v0",
      "tile_height": 360,
      "rows": [
        {"label": "case1 agate",
         "photos": ["path/to/photo.jpg", ...],
         "renders": ["path/to/render.png", ...]}
      ]
    }

Paths are relative to the repository root (or absolute).  Each row shows the
photos on the left and the renders on the right, every tile scaled to the same
pixel height, with the file name as a caption under each tile.  A render entry
may be an object ``{"path": ..., "caption": ...}`` to override the caption.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
BG = (250, 250, 248)
INK = (30, 30, 30)
MUTED = (110, 110, 110)
GAP = 12
CAPTION_H = 22
LABEL_W = 190
SEPARATOR_W = 28


def _entry(item: str | dict[str, str]) -> tuple[Path, str]:
    if isinstance(item, str):
        path = Path(item)
        caption = path.name
    else:
        path = Path(item["path"])
        caption = item.get("caption", path.name)
    if not path.is_absolute():
        path = ROOT / path
    return path, caption


def _tile(path: Path, height: int) -> Image.Image:
    with Image.open(path) as image:
        image = image.convert("RGB")
        width = max(1, round(image.width * height / image.height))
        return image.resize((width, height), Image.Resampling.LANCZOS)


def build_sheet(spec: dict) -> Image.Image:
    tile_h = int(spec.get("tile_height", 360))
    font = ImageFont.load_default(size=14)
    title_font = ImageFont.load_default(size=22)
    label_font = ImageFont.load_default(size=16)

    rows = []
    for row in spec["rows"]:
        photos = [(_tile(p, tile_h), c) for p, c in map(_entry, row.get("photos", []))]
        renders = [(_tile(p, tile_h), c) for p, c in map(_entry, row.get("renders", []))]
        width = LABEL_W + sum(t.width + GAP for t, _ in photos) + SEPARATOR_W
        width += sum(t.width + GAP for t, _ in renders)
        rows.append((row["label"], row.get("note", ""), photos, renders, width))

    title_h = 48
    row_h = tile_h + CAPTION_H + GAP * 2
    sheet_w = max(r[4] for r in rows) + GAP
    sheet = Image.new("RGB", (sheet_w, title_h + row_h * len(rows)), BG)
    draw = ImageDraw.Draw(sheet)
    draw.text((GAP, 12), spec.get("title", "contact sheet"), fill=INK, font=title_font)
    draw.text(
        (sheet_w - 360, 18),
        "left: photos  |  right: renders",
        fill=MUTED,
        font=font,
    )

    for index, (label, note, photos, renders, _) in enumerate(rows):
        y = title_h + index * row_h + GAP
        draw.text((GAP, y + 4), label, fill=INK, font=label_font)
        if note:
            for line_no, line in enumerate(note.split("\n")):
                draw.text((GAP, y + 28 + 18 * line_no), line, fill=MUTED, font=font)
        x = LABEL_W
        for tiles in (photos, renders):
            for tile, caption in tiles:
                sheet.paste(tile, (x, y))
                text = caption
                while draw.textlength(text, font=font) > tile.width and len(text) > 4:
                    text = text[:-4] + "…"
                draw.text((x, y + tile_h + 3), text, fill=MUTED, font=font)
                x += tile.width + GAP
            if tiles is photos:
                draw.line(
                    [(x + SEPARATOR_W // 2 - GAP // 2, y), (x + SEPARATOR_W // 2 - GAP // 2, y + tile_h)],
                    fill=(180, 180, 180),
                    width=2,
                )
                x += SEPARATOR_W
    return sheet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("spec", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    sheet = build_sheet(spec)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)
    print(f"{args.output} {sheet.width}x{sheet.height}")


if __name__ == "__main__":
    main()
