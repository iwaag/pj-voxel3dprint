"""Measure slab-mm regions in photos and renders (spec v3 driven).

Usage (repo root):

    vdbmat/.venv/bin/python work/compare/region_table.py SPEC.json OUT.json [--md OUT.md]

SPEC (``work/compare/specs/batch1-v3.json`` and the step-specific specs):

    {
      "regions": "work/compare/specs/batch1-regions-mm.json",
      "cases": {
        "agate": {
          "images": [
            {"path": "...jpg", "kind": "photo", "face": "top",
             "white": [x0, y0, x1, y1],              # image fractions, paper
             "corners_px": [[u, v] x 4],             # model corners (0,0) (60,0) (60,30) (0,30) mm
             "volume": "mirror_y",                   # see match_camera.py
             "photo_tone": null},                    # optional, see below
            {"path": "...png", "kind": "render", "face": "top", "volume": "mirror_y",
             "white": [...], "camera": {stage-config camera block}}
          ]
        }
      }
    }

Each image gets a per-channel linear gain that maps the white patch mean to
0.85 sRGB neutral, as in ``contact_sheet.py``. For a render, the corners come
from projecting the slab through the stage camera (``slab.stage_camera``).
Every region and tile of the image's face (``regions`` file, from
``pick_regions.py``) is measured as a mean of normalised linear RGB. The
output also has the darkest and brightest 1 % (by luminance Y) of the face
interior (inset 2 mm): ``p01`` / ``p99``.

``photo_tone`` (optional, per photo): ``{"gamma": g}`` applies
``Y -> 0.85_lin * (Y / 0.85_lin) ** g`` to the normalised linear values
(per channel, anchored at the white patch) before Lab, i.e. it undoes a
phone tone curve that is a power law relative to paper white.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from contact_sheet import WHITE_SRGB, linear_to_lab, srgb_to_linear
from slab import MODEL_CORNERS_MM, SLAB_MM, apply_h, mm_to_image, projected_corners, region_mask, stage_camera

ROOT = Path(__file__).resolve().parents[2]
WHITE_LIN = float(srgb_to_linear(np.array(WHITE_SRGB)))
INSET_MM = 2.0


def _path(p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else ROOT / q


def image_corners(entry: dict, width: int, height: int) -> np.ndarray:
    """Image points of the region face's model corners.

    Photos use their picks. Renders project the corners through their stage
    camera, placed on the rendered input's top face according to ``volume``
    (``match_camera.py``: ``mirror_y`` puts face (x, y) at (x, 30 - y)).
    """
    if "corners_px" in entry:
        return np.asarray(entry["corners_px"], float)
    corners = projected_corners(stage_camera(entry["camera"], width, height))
    if entry.get("volume") == "mirror_y":
        # face corner (x, y) sits at (x, 30 - y): (0,0)<->(0,30), (60,0)<->(60,30)
        corners = corners[[3, 2, 1, 0]]
    return corners


def normalised_linear(entry: dict) -> np.ndarray:
    with Image.open(_path(entry["path"])) as im:
        lin = srgb_to_linear(np.asarray(im.convert("RGB"), dtype=np.float64) / 255.0)
    h, w = lin.shape[:2]
    x0, y0, x1, y1 = entry["white"]
    patch = lin[round(y0 * h) : round(y1 * h), round(x0 * w) : round(x1 * w)].reshape(-1, 3)
    lin = lin * (WHITE_LIN / patch.mean(axis=0))
    tone = entry.get("photo_tone")
    if tone:
        lin = WHITE_LIN * np.clip(lin / WHITE_LIN, 0, None) ** tone["gamma"]
    return lin


def luminance(rgb: np.ndarray) -> np.ndarray:
    return rgb @ np.array([0.2126, 0.7152, 0.0722])


def measure(entry: dict, regions: dict) -> dict:
    lin = normalised_linear(entry)
    h, w = lin.shape[:2]
    hmat = mm_to_image(image_corners(entry, w, h))
    face = regions[entry.get("face", "top")]
    out: dict = {"regions": {}, "tiles": {}}
    for group in ("regions", "tiles"):
        for name, reg in face[group].items():
            mask = region_mask(hmat, reg["rect"], (h, w))
            if mask.sum() < 4:
                continue
            rgb = lin[mask].mean(axis=0)
            out[group][name] = {"rgb": rgb.round(5).tolist(), "lab": linear_to_lab(np.clip(rgb, 0, None)).round(2).tolist(), "n": int(mask.sum())}
    inner = region_mask(hmat, [INSET_MM, INSET_MM, SLAB_MM[0] - INSET_MM, SLAB_MM[1] - INSET_MM], (h, w))
    y = luminance(lin[inner])
    out["p01"], out["p99"] = float(np.percentile(y, 1)), float(np.percentile(y, 99))
    out["face_rgb"] = lin[inner].mean(axis=0).round(5).tolist()
    out["corners_px"] = apply_h(hmat, MODEL_CORNERS_MM).round(1).tolist()
    return out


def add_matched_renders(spec: dict, tag: str, directory: str) -> None:
    """Append a render entry after every photo that has a matched camera."""
    for case, cdef in spec["cases"].items():
        images = []
        for entry in cdef["images"]:
            images.append(entry)
            if entry["kind"] == "photo" and "camera" in entry:
                stem = Path(entry["path"]).stem
                images.append(
                    {
                        "path": f"{directory}/{case}-{stem}-{tag}.png",
                        "kind": "render",
                        "caption": f"{stem} {tag}",
                        "photo": stem,
                        "face": entry.get("face", "top"),
                        "volume": entry["volume"],
                        "white": entry["white"],
                        "camera": entry["camera"],
                    }
                )
        cdef["images"] = images


def overlay(entry: dict, regions: dict, out: Path) -> None:
    """Save the image with the face outline, regions (red) and tiles (grey) drawn."""
    from PIL import ImageDraw

    with Image.open(_path(entry["path"])) as im:
        im = im.convert("RGB")
    hmat = mm_to_image(image_corners(entry, im.width, im.height))
    draw = ImageDraw.Draw(im)
    lw = max(1, im.width // 500)

    def quad(rect, colour, width):
        x0, y0, x1, y1 = rect
        pts = apply_h(hmat, np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]))
        draw.line([tuple(p) for p in pts], fill=colour, width=width)

    quad([0, 0, SLAB_MM[0], SLAB_MM[1]], (0, 255, 0), lw)
    origin = apply_h(hmat, np.array([[0.0, 0.0]]))[0]
    draw.ellipse([*(origin - 4 * lw), *(origin + 4 * lw)], outline=(0, 255, 0), width=lw)
    face = regions[entry.get("face", "top")]
    for reg in face["tiles"].values():
        quad(reg["rect"], (150, 150, 150), 1)
    for name, reg in face["regions"].items():
        quad(reg["rect"], (255, 40, 40), lw)
        x0, y0 = apply_h(hmat, np.array([reg["rect"][:2]]))[0]
        draw.text((x0, y0 - 12 * lw), name[:10], fill=(255, 255, 0))
    x0, y0, x1, y1 = entry["white"]
    draw.rectangle([x0 * im.width, y0 * im.height, x1 * im.width, y1 * im.height], outline=(0, 120, 255), width=lw)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)


def lab_of(rgb) -> np.ndarray:
    return linear_to_lab(np.clip(np.asarray(rgb, float), 0, None))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("spec", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--md", type=Path)
    parser.add_argument("--overlay", type=Path, help="also write each image with its regions drawn, into this directory")
    parser.add_argument(
        "--renders",
        nargs=2,
        metavar=("TAG", "DIR"),
        help="add each photo's matched render DIR/<case>-<photo stem>-<TAG>.png (render_matched.sh)",
    )
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    if args.renders:
        add_matched_renders(spec, *args.renders)
    regions = json.loads(_path(spec["regions"]).read_text())
    result: dict = {}
    md: list[str] = []
    for case, cdef in spec["cases"].items():
        result[case] = []
        for entry in cdef["images"]:
            m = measure(entry, regions[case])
            if args.overlay:
                overlay(entry, regions[case], args.overlay / f"{case}-{Path(entry['path']).stem}.png")
            result[case].append(
                {
                    "path": entry["path"],
                    "kind": entry["kind"],
                    "caption": entry.get("caption", Path(entry["path"]).name),
                    "photo": entry.get("photo", Path(entry["path"]).stem),
                    **m,
                }
            )
        md += [f"### {case}", "", "| region | " + " | ".join(r["caption"] for r in result[case]) + " |", "|---|" + "---|" * len(result[case])]
        names = list(regions[case][cdef["images"][0].get("face", "top")]["regions"])
        for name in names:
            cells = []
            for r in result[case]:
                v = r["regions"].get(name)
                cells.append("–" if v is None else "{:.0f} {:+.0f} {:+.0f}".format(*v["lab"]))
            md.append(f"| {name} | " + " | ".join(cells) + " |")
        md.append("| p01 / p99 Y | " + " | ".join(f"{r['p01']:.3f} / {r['p99']:.3f}" for r in result[case]) + " |")
        md.append("")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=1) + "\n")
    if args.md:
        args.md.write_text("Lab (L a b) of white-patch-normalised region means.\n\n" + "\n".join(md) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
