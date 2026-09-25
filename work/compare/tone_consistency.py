"""p2 step 2: photo-to-photo consistency and a global tone-curve test.

Usage (repo root):

    vdbmat/.venv/bin/python work/compare/tone_consistency.py REGIONS.json OUT_DIR

REGIONS.json is the output of ``region_table.py`` for a spec with three photos
and one render per case (``batch1-p2s2.json``). Writes to OUT_DIR:

- ``consistency.md``: per named region, the L of each photo, the photo spread
  (largest pairwise ΔE76 between the photos), the render's ΔE76 to the photo
  mean, and a verdict: *render-limited* when the render is further from the
  photo mean than the photos are from each other (ΔE_render > spread),
  otherwise *photo-limited*. Tile statistics come after it.
- ``tone.md`` + ``tone.png``: fits of y_photo = s_p * y_render ** g over the
  agate and fur tiles and the amber host regions (y = Y / Y_white, Y =
  luminance of the white-patch-normalised linear RGB; Y_white = 0.85 sRGB).
  Fit A has g = 1 (only a per-photo scale s_p), fit B one g shared by all
  nine photos, fit C one g per case. Residuals are reported in L*.
  Amber photos show the bottom face and the render the top, so only regions
  of the same host class are paired there, not tiles.
"""

from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, str(Path(__file__).parent))
from contact_sheet import WHITE_SRGB, linear_to_lab, srgb_to_linear  # noqa: E402

W = float(srgb_to_linear(np.array(WHITE_SRGB)))
LUM = np.array([0.2126, 0.7152, 0.0722])


def lab(rgb) -> np.ndarray:
    return linear_to_lab(np.clip(np.asarray(rgb, float), 0, None))


def y_rel(rgb) -> float:
    return float(np.asarray(rgb) @ LUM) / W


def l_of_y(y: np.ndarray) -> np.ndarray:
    """CIE L* of relative luminance y (relative to paper white, with paper at L(0.85 sRGB))."""
    t = np.clip(y * W, 1e-6, None)
    f = np.where(t > (6 / 29) ** 3, np.cbrt(t), t / (3 * (6 / 29) ** 2) + 4 / 29)
    return 116 * f - 16


def consistency(data: dict) -> list[str]:
    md = ["# Photo consistency (white-patch normalised, per named region)", ""]
    md += ["| case | region | L per photo | photo spread ΔE | render L | ΔE render→photo mean | verdict |", "|---|---|---|---:|---:|---:|---|"]
    counts = {"photo-limited": 0, "render-limited": 0}
    for case, images in data.items():
        photos = [im for im in images if im["kind"] == "photo"]
        render = next(im for im in images if im["kind"] == "render")
        names = list(photos[0]["regions"]) + ["(whole face)"]
        for name in names:
            if name == "(whole face)":
                labs = [lab(p["face_rgb"]) for p in photos]
                rlab = lab(render["face_rgb"]) if case != "amber" else None
            else:
                if any(name not in p["regions"] for p in photos):
                    continue
                labs = [np.array(p["regions"][name]["lab"]) for p in photos]
                rlab = np.array(render["regions"][name]["lab"]) if name in render["regions"] else None
            spread = max(float(np.linalg.norm(a - b)) for a, b in combinations(labs, 2))
            mean = np.mean(labs, axis=0)
            if rlab is None:
                md.append(f"| {case} | {name} | {' / '.join(f'{v[0]:.0f}' for v in labs)} | {spread:.1f} | – | – | – |")
                continue
            d = float(np.linalg.norm(rlab - mean))
            verdict = "render-limited" if d > spread else "photo-limited"
            counts[verdict] += 1
            md.append(
                f"| {case} | {name} | {' / '.join(f'{v[0]:.0f}' for v in labs)} | {spread:.1f} | {rlab[0]:.0f} | {d:.1f} | {verdict} |"
            )
    md += ["", f"Totals: {counts}", ""]
    md += ["## Tiles (5 mm squares, same physical area in every photo)", "", "| case | tiles | median L range | 90th pct L range | median pairwise ΔE |", "|---|---:|---:|---:|---:|"]
    for case, images in data.items():
        photos = [im for im in images if im["kind"] == "photo"]
        names = [n for n in photos[0]["tiles"] if all(n in p["tiles"] for p in photos)]
        ranges, des = [], []
        for n in names:
            labs = [np.array(p["tiles"][n]["lab"]) for p in photos]
            ls = [v[0] for v in labs]
            ranges.append(max(ls) - min(ls))
            des.append(np.median([np.linalg.norm(a - b) for a, b in combinations(labs, 2)]))
        md.append(f"| {case} | {len(names)} | {np.median(ranges):.1f} | {np.percentile(ranges, 90):.1f} | {np.median(des):.1f} |")
    md.append("")
    return md


def pairs(data: dict) -> list[tuple[str, int, float, float]]:
    """(case, photo index, y_render, y_photo) samples for the tone fit."""
    out = []
    for case, images in data.items():
        photos = [im for im in images if im["kind"] == "photo"]
        render = next(im for im in images if im["kind"] == "render")
        group = "regions" if case == "amber" else "tiles"
        for p_index, p in enumerate(photos):
            for name, v in p[group].items():
                if name in render[group]:
                    out.append((case, p_index, y_rel(render[group][name]["rgb"]), y_rel(v["rgb"])))
    return out


def tone(data: dict, out_dir: Path) -> list[str]:
    samples = pairs(data)
    cases = sorted({s[0] for s in samples})
    photo_ids = sorted({(s[0], s[1]) for s in samples})
    pid = {p: i for i, p in enumerate(photo_ids)}
    idx = np.array([pid[(s[0], s[1])] for s in samples])
    cid = np.array([cases.index(s[0]) for s in samples])
    yr = np.array([s[2] for s in samples])
    yp = np.array([s[3] for s in samples])

    def model(params, mode):
        log_s = params[: len(photo_ids)]
        if mode == "A":
            g = np.ones_like(yr)
        elif mode == "B":
            g = np.full_like(yr, params[len(photo_ids)])
        else:
            g = params[len(photo_ids) + cid]
        return np.exp(log_s[idx]) * yr**g

    def fit(mode):
        n_g = {"A": 0, "B": 1, "C": len(cases)}[mode]
        x0 = np.r_[np.zeros(len(photo_ids)), np.ones(n_g)]
        res = least_squares(lambda p: l_of_y(model(p, mode)) - l_of_y(yp), x0)
        return res.x, res.fun

    md = ["# Tone-curve test: y_photo = s_p · y_render^g", ""]
    md += [f"{len(samples)} samples: agate/fur tiles (55 per photo) + amber host regions (5 per photo).", ""]
    md += ["| fit | g | RMS ΔL | per-case RMS ΔL | s_p range |", "|---|---|---:|---|---|"]
    fits = {}
    for mode, label in (("A", "A: scale only (g = 1)"), ("B", "B: one g for all"), ("C", "C: g per case")):
        x, r = fit(mode)
        fits[mode] = (x, r)
        g = "1" if mode == "A" else (f"{x[len(photo_ids)]:.3f}" if mode == "B" else ", ".join(f"{c} {v:.2f}" for c, v in zip(cases, x[len(photo_ids):])))
        per_case = ", ".join(f"{c} {np.sqrt(np.mean(r[cid == k] ** 2)):.1f}" for k, c in enumerate(cases))
        s = np.exp(x[: len(photo_ids)])
        md.append(f"| {label} | {g} | {np.sqrt(np.mean(r ** 2)):.2f} | {per_case} | {s.min():.2f}–{s.max():.2f} |")
    md.append("")
    md += ["Per-photo scale s_p (photo luminance / render luminance, fits A and B):", ""]
    xa, xb = fits["A"][0], fits["B"][0]
    for (case, i), sa, sb in zip(photo_ids, np.exp(xa[: len(photo_ids)]), np.exp(xb[: len(photo_ids)])):
        md.append(f"- {case} photo {i}: A {sa:.3f}, B {sb:.3f}")
    md.append("")
    md += agate_bands(data)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(cases), figsize=(5 * len(cases), 4.6))
    grid = np.linspace(0.005, 1.3, 200)
    for k, c in enumerate(cases):
        ax = axes[k]
        for (case, i), p in pid.items():
            if case != c:
                continue
            m = idx == p
            s_b = np.exp(xb[p])
            ax.scatter(yr[m], yp[m] / s_b, s=8, label=f"photo {i} (/s={s_b:.2f})")
        ax.plot(grid, grid, "k--", lw=1, label="y = x")
        ax.plot(grid, grid ** xb[len(photo_ids)], "r-", lw=1, label=f"g = {xb[len(photo_ids)]:.2f}")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("render y (rel. paper white)")
        ax.set_ylabel("photo y / s_p")
        ax.set_title(c)
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out_dir / "tone.png", dpi=110)
    return md


def agate_bands(data: dict) -> list[str]:
    """Per-photo s and g on the 12 named agate regions (Y spans ~20x, unlike the 5 mm tiles)."""
    images = data["agate"]
    render = next(im for im in images if im["kind"] == "render")
    md = ["## Agate bands only (12 named regions, per photo)", "", "| photo | s | g | RMS ΔL (g free) | RMS ΔL (g = 1) |", "|---|---:|---:|---:|---:|"]
    for i, p in enumerate(im for im in images if im["kind"] == "photo"):
        names = [n for n in p["regions"] if n in render["regions"]]
        yr = np.array([y_rel(render["regions"][n]["rgb"]) for n in names])
        yp = np.array([y_rel(p["regions"][n]["rgb"]) for n in names])
        free = least_squares(lambda q: l_of_y(np.exp(q[0]) * yr ** q[1]) - l_of_y(yp), [0.0, 1.0])
        one = least_squares(lambda q: l_of_y(np.exp(q[0]) * yr) - l_of_y(yp), [0.0])
        md.append(
            f"| {i} {Path(p['path']).stem} | {np.exp(free.x[0]):.2f} | {free.x[1]:.2f} | "
            f"{np.sqrt(np.mean(free.fun ** 2)):.1f} | {np.sqrt(np.mean(one.fun ** 2)):.1f} |"
        )
    md.append("")
    return md


def main() -> None:
    data = json.loads(Path(sys.argv[1]).read_text())
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "consistency.md").write_text("\n".join(consistency(data)) + "\n")
    (out_dir / "tone.md").write_text("\n".join(tone(data, out_dir)) + "\n")
    print((out_dir / "consistency.md").read_text())
    print((out_dir / "tone.md").read_text())


if __name__ == "__main__":
    main()
