"""Warp every image of a spec-v3 case onto the slab face (mm) and stack them.

Usage (repo root):

    vdbmat/.venv/bin/python work/compare/face_sheet.py SPEC.json OUT_DIR [--ppm 10]

Writes ``OUT_DIR/<case>-faces.png``: one row per image (photos and renders),
each the visible face resampled to 60 x 30 mm (white-patch normalised, sRGB),
with the ``regions`` rectangles drawn and labelled. If the corner picks and
orientation are right, bands line up vertically across rows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from contact_sheet import linear_to_srgb
from region_table import _path, image_corners, normalised_linear
from slab import mm_to_image, warp_top_face


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("spec", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--ppm", type=float, default=10.0)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    regions = json.loads(_path(spec["regions"]).read_text())
    font = ImageFont.load_default(size=12)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for case, cdef in spec["cases"].items():
        rows = []
        for entry in cdef["images"]:
            lin = normalised_linear(entry)
            face = warp_top_face(lin, mm_to_image(image_corners(entry, lin.shape[1], lin.shape[0])), args.ppm)
            tile = Image.fromarray((linear_to_srgb(face) * 255).round().astype(np.uint8))
            draw = ImageDraw.Draw(tile)
            for name, reg in regions[case][entry.get("face", "top")]["regions"].items():
                x0, y0, x1, y1 = (np.asarray(reg["rect"]) * args.ppm).tolist()
                draw.rectangle([x0, y0, x1, y1], outline=(255, 40, 40), width=1)
                draw.text((x0, y1 + 1), name[:12], fill=(255, 255, 0), font=font)
            draw.text((4, 4), entry.get("caption", Path(entry["path"]).name), fill=(0, 255, 0), font=font)
            rows.append(tile)
        sheet = Image.new("RGB", (rows[0].width, sum(r.height + 4 for r in rows)), "white")
        y = 0
        for r in rows:
            sheet.paste(r, (0, y))
            y += r.height + 4
        sheet.save(args.out_dir / f"{case}-faces.png")
        print(args.out_dir / f"{case}-faces.png")


if __name__ == "__main__":
    main()
