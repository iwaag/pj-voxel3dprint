"""Compare the fur crop renders (printer pitch vs review grid) with the photos (p2 step 5).

Usage (repo root):

    vdbmat/.venv/bin/python work/halftone/fur_crop_compare.py CROP_DIR OUT_DIR \
        [--renders NAME=PNG ...] [--window 26 12 32 18]

Writes ``OUT_DIR/fur-crop-panel.png`` and ``OUT_DIR/fur-crop-stats.md``.

- Photos: the window (fur face mm, i.e. volume x/y) is resampled from each
  fur photo of ``batch1-v3.json`` through its corner homography, white-patch
  normalised, at 40 px/mm. The matched v2 render of step 3 goes the same way.
- Crop renders (``--renders name=png``, each rendered with
  ``fur-crop.stage.json``): the crop's own top face is resampled at 40 px/mm.
  The crop volumes are not mirrored, so their window is flipped in y to match
  the photos' (mirror_y) orientation.

Statistics per image over the window: mean Lab; L std (texture contrast);
the fraction of "undercoat" pixels (the darker half by L, a proxy) and the
mean Lab of the darker 30 % (undercoat stripes) and the brighter 30 % (tufts).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter

sys.path.insert(0, str(Path(__file__).parents[1] / "compare"))
from contact_sheet import linear_to_srgb  # noqa: E402
from pixel_diff import lab_image  # noqa: E402
from region_table import image_corners, normalised_linear  # noqa: E402
from slab import apply_h, homography, look_at, mm_to_image  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PPM = 40.0
STAGE = {"azimuth_deg": -27.8, "elevation_deg": 72.8, "distance_factor": 3.0, "fov_deg": 35.0}


def sample(lin: np.ndarray, h_mm_to_px: np.ndarray, rect, ppm: float = PPM, blur: float = 0.0) -> np.ndarray:
    x0, y0, x1, y1 = rect
    w, hgt = int(round((x1 - x0) * ppm)), int(round((y1 - y0) * ppm))
    ys, xs = np.mgrid[0:hgt, 0:w]
    mm = np.c_[x0 + (xs.ravel() + 0.5) / ppm, y0 + (ys.ravel() + 0.5) / ppm]
    p = apply_h(h_mm_to_px, mm)
    out = np.zeros((hgt * w, 3))
    from scipy.ndimage import map_coordinates

    for ch in range(3):
        img = gaussian_filter(lin[..., ch], blur) if blur else lin[..., ch]
        out[:, ch] = map_coordinates(img, [p[:, 1] - 0.5, p[:, 0] - 0.5], order=1, mode="nearest")
    return out.reshape(hgt, w, 3)


def crop_face_h(size_mm: tuple[float, float, float], width: int, height: int) -> np.ndarray:
    """mm (crop-local x, y) -> px on the crop's top face for the STAGE orbit camera."""
    import math

    hi = np.array(size_mm) / 1000
    centre, radius = hi / 2, float(np.linalg.norm(hi) / 2)
    az, el = math.radians(STAGE["azimuth_deg"]), math.radians(STAGE["elevation_deg"])
    d = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    cam = look_at(centre + d * radius * STAGE["distance_factor"], centre, [0, 0, 1], STAGE["fov_deg"], width, height)
    corners_mm = np.array([[0, 0], [size_mm[0], 0], [size_mm[0], size_mm[1]], [0, size_mm[1]]])
    px = cam.project(np.c_[corners_mm, np.full(4, size_mm[2])] / 1000)
    return homography(corners_mm, px)


def stats(lin: np.ndarray) -> dict:
    lab = lab_image(lin).reshape(-1, 3)
    order = np.argsort(lab[:, 0])
    n = len(order)
    dark, bright = lab[order[: int(0.3 * n)]], lab[order[-int(0.3 * n) :]]
    return {"mean": lab.mean(0), "L_std": lab[:, 0].std(), "dark30": dark.mean(0), "bright30": bright.mean(0)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("crop_dir", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--renders", nargs="*", default=[])
    parser.add_argument("--window", nargs=4, type=float, default=[26.0, 12.0, 32.0, 18.0])
    parser.add_argument("--matched", default=".local/real_print/batch1/renders-p2/step3/fur-{stem}-v2.png")
    args = parser.parse_args()
    rect = args.window
    spec = json.loads((ROOT / "work/compare/specs/batch1-v3.json").read_text())
    tiles: list[tuple[str, np.ndarray]] = []
    for photo in spec["cases"]["fur"]["images"]:
        lin = normalised_linear(photo)
        h = mm_to_image(image_corners(photo, lin.shape[1], lin.shape[0]))
        tiles.append((f"photo {Path(photo['path']).stem}", sample(lin, h, rect)))
    photo = spec["cases"]["fur"]["images"][0]
    stem = Path(photo["path"]).stem
    render = {"path": args.matched.format(stem=stem), "kind": "render", "white": photo["white"], "camera": photo["camera"], "volume": photo["volume"]}
    lin = normalised_linear(render)
    tiles.append((f"matched v2 {stem} (0.2 mm)", sample(lin, mm_to_image(image_corners(render, lin.shape[1], lin.shape[0])), rect)))
    for item in args.renders:
        name, png = item.split("=", 1)
        vox = json.loads((args.crop_dir / f"fur-crop-{name.split()[0]}.voxels.json").read_text())
        shape = vox["shape_zyx"]
        size = tuple(n * v * 1000 for n, v in zip(shape[::-1], vox["voxel_size_xyz_m"]))
        lin = normalised_linear({"path": png, "white": [0.03, 0.65, 0.13, 0.85]})
        h = crop_face_h(size, lin.shape[1], lin.shape[0])
        w = rect[2] - rect[0]
        face = sample(lin, h, [0.0, 0.0, w, rect[3] - rect[1]])
        tiles.append((name, face[::-1]))  # crop is unmirrored; photos show the mirror image
    font = ImageFont.load_default(size=12)
    tw, th = tiles[0][1].shape[1], tiles[0][1].shape[0]
    panel = Image.new("RGB", (len(tiles) * (tw + 6), th + 18), "white")
    draw = ImageDraw.Draw(panel)
    lines = ["| image | mean L a b | L std | darker 30 % L a b | brighter 30 % L a b |", "|---|---|---:|---|---|"]
    for k, (name, lin) in enumerate(tiles):
        panel.paste(Image.fromarray((linear_to_srgb(lin) * 255).round().astype(np.uint8)), (k * (tw + 6), 18))
        draw.text((k * (tw + 6) + 2, 2), name[:34], fill=(0, 0, 0), font=font)
        s = stats(lin)
        f = lambda v: f"{v[0]:.0f} {v[1]:+.1f} {v[2]:+.1f}"  # noqa: E731
        lines.append(f"| {name} | {f(s['mean'])} | {s['L_std']:.1f} | {f(s['dark30'])} | {f(s['bright30'])} |")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    panel.save(args.out_dir / "fur-crop-panel.png")
    (args.out_dir / "fur-crop-stats.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
