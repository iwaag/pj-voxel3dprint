"""Photo vs camera-matched render: warped side-by-side and ΔL / Δa / Δb maps.

Usage (repo root):

    vdbmat/.venv/bin/python work/compare/pixel_diff.py SPEC_V3.json TAG OUT_DIR [--tile 320]

For every photo in the spec (with ``camera`` from ``match_camera.py``) the
matched render is ``OUT_DIR/<case>-<photo stem>-<TAG>.png``
(``render_matched.sh``). Both images are white-patch normalised
(``region_table.normalised_linear``). The render uses the photo's white
rectangle, since the matched view puts the same paper there. The photo is
blurred to the render's pixel scale and resampled into the render frame
through the visible face (render px -> face mm -> photo px), so the
difference maps cover the face only.

Writes per photo ``OUT_DIR/diff-<case>-<stem>-<TAG>.png`` (photo | render |
warped photo | ΔL | Δa | Δb, with ΔL in L* from -20 blue to +20 red, positive
= photo lighter/redder/yellower than render) and ``OUT_DIR/contact-sheet-v3-<TAG>.png``
(one row per photo: photo, render, ΔL, Δb) plus ``diff-stats-<TAG>.md`` (mean
and mean-absolute ΔL/Δa/Δb over the face interior).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, map_coordinates

from contact_sheet import linear_to_srgb
from region_table import image_corners, normalised_linear
from slab import SLAB_MM, apply_h, mm_to_image, region_mask

INSET_MM = 1.0


def lab_image(lin: np.ndarray) -> np.ndarray:
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = np.clip(lin, 0, None) @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def diverging(d: np.ndarray, mask: np.ndarray, limit: float = 20.0) -> np.ndarray:
    t = np.clip(d / limit, -1, 1)
    rgb = np.ones(d.shape + (3,))
    rgb[..., 0] = np.where(t < 0, 1 + t, 1)
    rgb[..., 1] = 1 - np.abs(t)
    rgb[..., 2] = np.where(t > 0, 1 - t, 1)
    rgb[~mask] = 0.35
    return (rgb * 255).astype(np.uint8)


def srgb8(lin: np.ndarray) -> np.ndarray:
    return (linear_to_srgb(lin) * 255).round().astype(np.uint8)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("spec", type=Path)
    parser.add_argument("tag")
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--tile", type=int, default=320)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    font = ImageFont.load_default(size=13)
    sheet_rows, stats = [], ["| case | photo | mean ΔL | mean Δa | mean Δb | mean abs ΔL | mean ΔE76 |", "|---|---|---:|---:|---:|---:|---:|"]
    for case, cdef in spec["cases"].items():
        for photo in cdef["images"]:
            if photo["kind"] != "photo" or "camera" not in photo:
                continue
            stem = Path(photo["path"]).stem
            render_path = args.out_dir / f"{case}-{stem}-{args.tag}.png"
            render = {"path": str(render_path), "kind": "render", "white": photo["white"], "camera": photo["camera"], "volume": photo["volume"]}
            p_lin = normalised_linear(photo)
            r_lin = normalised_linear(render)
            rh, rw = r_lin.shape[:2]
            ph, pw = p_lin.shape[:2]
            h_r = mm_to_image(image_corners(render, rw, rh))
            h_p = mm_to_image(image_corners(photo, pw, ph))
            mask = region_mask(h_r, [INSET_MM, INSET_MM, SLAB_MM[0] - INSET_MM, SLAB_MM[1] - INSET_MM], (rh, rw))
            ys, xs = np.nonzero(mask)
            mm = apply_h(np.linalg.inv(h_r), np.c_[xs + 0.5, ys + 0.5])
            pp = apply_h(h_p, mm) - 0.5
            sigma = max(pw / rw, ph / rh) / 2
            warped = np.zeros_like(r_lin)
            for ch in range(3):
                blurred = gaussian_filter(p_lin[..., ch], sigma)
                warped[ys, xs, ch] = map_coordinates(blurred, [pp[:, 1], pp[:, 0]], order=1, mode="nearest")
            d = lab_image(warped) - lab_image(r_lin)
            d[~mask] = 0
            de = np.linalg.norm(d, axis=-1)[mask]
            mean = d[mask].mean(axis=0)
            stats.append(
                f"| {case} | {stem} | {mean[0]:+.1f} | {mean[1]:+.1f} | {mean[2]:+.1f} | {np.abs(d[mask][:, 0]).mean():.1f} | {de.mean():.1f} |"
            )
            warped_show = np.where(mask[..., None], warped, r_lin * 0.3)
            panels = [
                Image.fromarray(srgb8(p_lin)).resize((rw, rh), Image.Resampling.LANCZOS),
                Image.fromarray(srgb8(r_lin)),
                Image.fromarray(srgb8(warped_show)),
                Image.fromarray(diverging(d[..., 0], mask)),
                Image.fromarray(diverging(d[..., 1], mask)),
                Image.fromarray(diverging(d[..., 2], mask)),
            ]
            labels = ["photo", f"render {args.tag}", "photo warped to render", "dL (+-20)", "da (+-20)", "db (+-20)"]
            row = Image.new("RGB", (rw * 6 + 25, rh + 20), "white")
            draw = ImageDraw.Draw(row)
            for k, (panel, label) in enumerate(zip(panels, labels)):
                row.paste(panel, (k * (rw + 5), 20))
                draw.text((k * (rw + 5) + 2, 3), label, fill=(0, 0, 0), font=font)
            row.save(args.out_dir / f"diff-{case}-{stem}-{args.tag}.png")
            t = args.tile
            sheet_rows.append((f"{case} {stem}  dE {de.mean():.1f}", [panels[i].resize((t, round(t * rh / rw))) for i in (0, 1, 3, 5)]))
    t = args.tile
    th = max(r[1][0].height for r in sheet_rows)
    sheet = Image.new("RGB", (190 + 4 * (t + 6), 40 + len(sheet_rows) * (th + 8)), (250, 250, 248))
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 10), f"contact sheet v3 ({args.tag}): photo | matched render | dL photo-render (+-20 L, red = photo lighter) | db (+-20, red = photo yellower)", fill=(0, 0, 0), font=font)
    for i, (label, tiles) in enumerate(sheet_rows):
        y = 40 + i * (th + 8)
        draw.text((10, y + 4), label, fill=(0, 0, 0), font=font)
        for k, tile in enumerate(tiles):
            sheet.paste(tile, (190 + k * (t + 6), y))
    sheet.save(args.out_dir / f"contact-sheet-v3-{args.tag}.png")
    (args.out_dir / f"diff-stats-{args.tag}.md").write_text("\n".join(stats) + "\n")
    print("\n".join(stats))


if __name__ == "__main__":
    main()
