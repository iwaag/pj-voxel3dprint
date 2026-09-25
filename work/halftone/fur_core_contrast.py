"""Fur: undercoat-core stripes vs gaps, photos and full-slab matched renders (p2 step 5).

Usage (repo root):

    vdbmat/.venv/bin/python work/halftone/fur_core_contrast.py [NAME=RENDER_PNG ...]

The design's undercoat core (material 2 voxels per 0.2 mm column, from
``.local/floating-fur/source/floating-fur-v1``) is resampled onto the face
window x 10..50, y 6..24 mm (5 px/mm). Photos are warped through their
corner picks (``batch1-v3.json``). Renders (``name=png``) are camera-matched
to Unknown-9 (mirror_y). The script reports, per image, Lab over
"core-rich" columns (top 30 % of core voxels) and "gap" columns (no core),
their difference, and the correlation of L and b with the core map.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[1] / "compare"))
from fur_crop_compare import sample  # noqa: E402
from pixel_diff import lab_image  # noqa: E402
from region_table import image_corners, normalised_linear  # noqa: E402
from slab import mm_to_image  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RECT = [10.0, 6.0, 50.0, 24.0]


def main() -> None:
    lab = np.load(ROOT / ".local/floating-fur/source/floating-fur-v1.material_id.npy")
    core = (lab == 2).sum(0).astype(float)[int(RECT[1] / 0.2) : int(RECT[3] / 0.2), int(RECT[0] / 0.2) : int(RECT[2] / 0.2)]
    rich, gap = core >= np.percentile(core[core > 0], 70), core == 0
    spec = json.loads((ROOT / "work/compare/specs/batch1-v3.json").read_text())
    photos = spec["cases"]["fur"]["images"]
    entries = [(f"photo {p['caption']}", p) for p in photos]
    u9 = next(p for p in photos if p["caption"] == "Unknown-9")
    for item in sys.argv[1:]:
        name, png = item.split("=", 1)
        entries.append((name, {"path": png, "white": u9["white"], "camera": u9["camera"], "volume": "mirror_y"}))
    print("| image | core-rich L a b | gap L a b | ΔL core-gap | Δb core-gap | corr(L, core) | corr(b, core) |")
    print("|---|---|---|---:|---:|---:|---:|")
    for name, e in entries:
        lin = normalised_linear(e)
        h = mm_to_image(image_corners(e, lin.shape[1], lin.shape[0]))
        lab_img = lab_image(sample(lin, h, RECT, ppm=5))
        c, g = lab_img[rich].mean(0), lab_img[gap].mean(0)
        cl = np.corrcoef(lab_img[..., 0].ravel(), core.ravel())[0, 1]
        cb = np.corrcoef(lab_img[..., 2].ravel(), core.ravel())[0, 1]
        f = lambda v: f"{v[0]:.0f} {v[1]:+.1f} {v[2]:+.1f}"  # noqa: E731
        print(f"| {name} | {f(c)} | {f(g)} | {c[0] - g[0]:+.1f} | {c[2] - g[2]:+.1f} | {cl:+.2f} | {cb:+.2f} |")


if __name__ == "__main__":
    main()
