from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from PIL import Image


FOLDERS = ("kohaku_tree", "menou", "floating_fur")
ALLOWED_RGB = {
    (240, 240, 240),
    (26, 26, 29),
    (227, 233, 253),
    (0, 90, 158),
    (166, 33, 98),
    (200, 189, 3),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_header(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(26)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise RuntimeError(f"Not a PNG: {path}")
    return header[24], header[25]


def convert(path: Path) -> None:
    if png_header(path) == (8, 6):
        return
    with Image.open(path) as source:
        rgb = source.convert("RGB")
        color_counts = rgb.getcolors(maxcolors=7)
        if color_counts is None:
            raise RuntimeError(f"More than 6 material RGB values in {path.name}")
        observed = {color for _, color in color_counts}
        rgba = rgb.convert("RGBA")
        rgba.putalpha(255)
    unexpected = observed - ALLOWED_RGB
    if unexpected:
        raise RuntimeError(f"Unexpected material RGB in {path.name}: {sorted(unexpected)}")
    temporary = path.with_suffix(".rgba.tmp.png")
    rgba.save(temporary, format="PNG", optimize=False, compress_level=6)
    bit_depth, color_type = png_header(temporary)
    if (bit_depth, color_type) != (8, 6):
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Invalid PNG encoding for {path.name}: depth={bit_depth}, type={color_type}")
    os.replace(temporary, path)


def update_manifest(folder: Path, pngs: list[Path]) -> None:
    manifests = list(folder.glob("*.printslices.json"))
    if not manifests:
        return
    manifest_path = manifests[0]
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    hashes = {path.name: sha256(path) for path in pngs}
    for record in document.get("slices", []):
        if record["file"] in hashes:
            record["sha256"] = hashes[record["file"]]
    document["png_encoding"] = {
        "color_type": 6,
        "mode": "RGBA",
        "bit_depth_per_channel": 8,
        "bits_per_pixel": 32,
        "alpha": 255,
    }
    manifest_path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def update_notes(folder: Path) -> None:
    note = "- PNG形式: 32-bit RGBA（8 bit/channel、Color Type 6、材料ピクセルのAlpha=255）"
    for path in list(folder.glob("*.md")) + list(folder.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        text = text.replace(
            "- PNGはインデックスカラーモード。背景色は使用せず、全ピクセルを6樹脂色のいずれかへ割り当て。",
            "- PNGは32-bit RGBA（各8 bit）。背景色は使用せず、全ピクセルを6樹脂色のいずれかへ割り当て（Alpha=255）。",
        )
        if "32-bit RGBA" not in text:
            text = text.rstrip() + "\n\n" + note + "\n"
        path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    report: dict[str, object] = {}
    for name in FOLDERS:
        folder = args.root / name
        pngs = sorted(folder.glob("slice_*.png"))
        if not pngs:
            raise RuntimeError(f"No slice PNGs: {folder}")
        for path in pngs:
            convert(path)
        update_manifest(folder, pngs)
        update_notes(folder)
        modes: set[str] = set()
        sizes: set[tuple[int, int]] = set()
        encodings: set[tuple[int, int]] = set()
        colors: set[tuple[int, int, int]] = set()
        alpha_values: set[int] = set()
        for path in pngs:
            with Image.open(path) as image:
                modes.add(image.mode)
                sizes.add(image.size)
                color_counts = image.getcolors(maxcolors=7)
                if color_counts is None:
                    raise RuntimeError(f"More than 6 RGBA values in {path.name}")
                rgba_values = {rgba for _, rgba in color_counts}
                colors.update(rgba[:3] for rgba in rgba_values)
                alpha_values.update(rgba[3] for rgba in rgba_values)
            encodings.add(png_header(path))
        report[name] = {
            "files": len(pngs),
            "modes": sorted(modes),
            "sizes": sorted(sizes),
            "png_depth_and_color_type": sorted(encodings),
            "alpha_values": sorted(alpha_values),
            "rgb_values": sorted(colors),
        }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
