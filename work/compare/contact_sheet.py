"""Photo-vs-render contact sheet for real-print comparisons.

Usage (from the repository root):

    vdbmat/.venv/bin/python work/compare/contact_sheet.py SPEC.json OUT.png [--table OUT.md]

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
pixel height, with the file name as a caption under each tile.  An entry may be
an object ``{"path": ..., "caption": ...}`` to override the caption.

Exposure-normalised numbers (p1 step 6): an entry object may also carry

    "white": [x0, y0, x1, y1],                 # white paper / floor patch
    "regions": {"pink band": [x0, y0, x1, y1], ...}

with rectangles as fractions (0..1) of the image width/height.  The image is
then scaled per channel in linear light so that the white patch's mean becomes
0.85 sRGB (neutral), which removes phone auto-exposure / auto-white-balance
and render exposure alike.  For every region the sheet reports the mean
normalised sRGB (0..255) and CIE Lab (D65).  Rectangles are drawn on the tile
(white patch dashed grey, regions coloured) and a table goes under the row;
``--table`` also writes all numbers as Markdown.  Treat the numbers as
relative: phone JPEGs are tone-mapped, so differences below ~10 dE mean nothing.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
BG = (250, 250, 248)
INK = (30, 30, 30)
MUTED = (110, 110, 110)
GAP = 12
CAPTION_H = 22
LABEL_W = 190
SEPARATOR_W = 28
TABLE_LINE_H = 17
WHITE_SRGB = 0.85
REGION_COLOURS = [(230, 40, 40), (20, 150, 230), (240, 170, 0), (140, 60, 200), (0, 170, 90)]


def srgb_to_linear(c: np.ndarray) -> np.ndarray:
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def linear_to_lab(rgb: np.ndarray) -> np.ndarray:
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = m @ rgb / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


@dataclass
class Entry:
    path: Path
    caption: str
    white: list[float] | None = None
    regions: dict[str, list[float]] = field(default_factory=dict)
    stats: dict[str, tuple[np.ndarray, np.ndarray]] = field(default_factory=dict)


def _entry(item: str | dict) -> Entry:
    if isinstance(item, str):
        item = {"path": item}
    path = Path(item["path"])
    if not path.is_absolute():
        path = ROOT / path
    return Entry(path, item.get("caption", path.name), item.get("white"), dict(item.get("regions", {})))


def _box(rect: list[float], width: int, height: int) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = rect
    return round(x0 * width), round(y0 * height), max(round(x1 * width), round(x0 * width) + 1), max(
        round(y1 * height), round(y0 * height) + 1
    )


def measure(entry: Entry, image: Image.Image) -> None:
    """Fill ``entry.stats`` with exposure-normalised (sRGB 0..255, Lab) per region."""
    if entry.white is None or not entry.regions:
        return
    lin = srgb_to_linear(np.asarray(image, dtype=np.float64) / 255.0)
    x0, y0, x1, y1 = _box(entry.white, image.width, image.height)
    gain = srgb_to_linear(np.array(WHITE_SRGB)) / lin[y0:y1, x0:x1].reshape(-1, 3).mean(axis=0)
    for name, rect in entry.regions.items():
        x0, y0, x1, y1 = _box(rect, image.width, image.height)
        mean = lin[y0:y1, x0:x1].reshape(-1, 3).mean(axis=0) * gain
        entry.stats[name] = (linear_to_srgb(mean) * 255.0, linear_to_lab(np.clip(mean, 0.0, None)))


def _tile(entry: Entry, height: int) -> Image.Image:
    with Image.open(entry.path) as image:
        image = image.convert("RGB")
        measure(entry, image)
        width = max(1, round(image.width * height / image.height))
        tile = image.resize((width, height), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(tile)
    if entry.white is not None and entry.regions:
        box = _box(entry.white, width, height)
        draw.rectangle(box, outline=(90, 90, 90), width=2)
        draw.rectangle((box[0] + 2, box[1] + 2, box[2] - 2, box[3] - 2), outline=(255, 255, 255), width=1)
    for colour, rect in zip(REGION_COLOURS, entry.regions.values()):
        draw.rectangle(_box(rect, width, height), outline=colour, width=2)
    return tile


def _region_names(row_entries: list[Entry]) -> list[str]:
    names: list[str] = []
    for entry in row_entries:
        names += [n for n in entry.stats if n not in names]
    return names


def _table_lines(entries: list[Entry]) -> list[str]:
    lines = []
    for name in _region_names(entries):
        cells = []
        for entry in entries:
            if name in entry.stats:
                rgb, lab = entry.stats[name]
                cells.append(
                    f"{entry.caption}: sRGB {rgb[0]:.0f},{rgb[1]:.0f},{rgb[2]:.0f}  Lab {lab[0]:.0f},{lab[1]:+.0f},{lab[2]:+.0f}"
                )
        lines.append(f"{name} —  " + "  |  ".join(cells))
    return lines


def build_sheet(spec: dict) -> tuple[Image.Image, list[str]]:
    tile_h = int(spec.get("tile_height", 360))
    font = ImageFont.load_default(size=14)
    title_font = ImageFont.load_default(size=22)
    label_font = ImageFont.load_default(size=16)

    rows = []
    markdown: list[str] = []
    for row in spec["rows"]:
        photo_entries = list(map(_entry, row.get("photos", [])))
        render_entries = list(map(_entry, row.get("renders", [])))
        photos = [(_tile(e, tile_h), e.caption) for e in photo_entries]
        renders = [(_tile(e, tile_h), e.caption) for e in render_entries]
        measured = [e for e in photo_entries + render_entries if e.stats]
        table = _table_lines(measured)
        width = LABEL_W + sum(t.width + GAP for t, _ in photos) + SEPARATOR_W
        width += sum(t.width + GAP for t, _ in renders)
        width = max([width] + [LABEL_W + round(font.getlength(line)) for line in table])
        rows.append((row["label"], row.get("note", ""), photos, renders, width, table))
        if measured:
            markdown += [f"### {row['label']}", "", "| region | image | sRGB | L | a | b |", "|---|---|---|---:|---:|---:|"]
            for name in _region_names(measured):
                for e in measured:
                    if name in e.stats:
                        rgb, lab = e.stats[name]
                        markdown.append(
                            f"| {name} | {e.caption} | {rgb[0]:.0f}, {rgb[1]:.0f}, {rgb[2]:.0f} "
                            f"| {lab[0]:.0f} | {lab[1]:+.0f} | {lab[2]:+.0f} |"
                        )
            markdown.append("")

    title_h = 48
    row_heights = [tile_h + CAPTION_H + GAP * 2 + (TABLE_LINE_H * len(r[5]) + GAP if r[5] else 0) for r in rows]
    sheet_w = max(r[4] for r in rows) + GAP
    sheet = Image.new("RGB", (sheet_w, title_h + sum(row_heights)), BG)
    draw = ImageDraw.Draw(sheet)
    draw.text((GAP, 12), spec.get("title", "contact sheet"), fill=INK, font=title_font)
    draw.text(
        (sheet_w - 360, 18),
        "left: photos  |  right: renders",
        fill=MUTED,
        font=font,
    )

    y = title_h
    for (label, note, photos, renders, _, table), row_h in zip(rows, row_heights):
        y += GAP
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
        table_y = y + tile_h + CAPTION_H + GAP // 2
        for line_no, line in enumerate(table):
            draw.text((LABEL_W, table_y + TABLE_LINE_H * line_no), line, fill=INK, font=font)
        y += row_h - GAP
    if markdown:
        markdown = [
            f"Exposure-normalised per image: white patch -> {WHITE_SRGB} sRGB neutral (per-channel linear gain).",
            "",
            *markdown,
        ]
    return sheet, markdown


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("spec", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--table", type=Path, help="also write the region numbers as Markdown")
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    sheet, markdown = build_sheet(spec)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)
    if args.table:
        args.table.write_text("\n".join(markdown) + "\n", encoding="utf-8")
    print(f"{args.output} {sheet.width}x{sheet.height}")


if __name__ == "__main__":
    main()
