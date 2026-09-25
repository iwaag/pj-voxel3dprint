"""Per-region ΔE between the photos and their matched renders (three-photo means).

Usage (repo root):

    vdbmat/.venv/bin/python work/compare/region_delta.py REGIONS.json [REGIONS_B.json ...] [--md OUT.md]

REGIONS.json is ``region_table.py --renders TAG DIR`` output: every photo is
followed by its camera-matched render (same ``photo`` key). For every named
region of every case, the photo value is the mean of the three photos'
white-normalised linear RGB and the render value the mean of the three
matched renders. It reports both Lab values, ΔE76, and the photo spread
(largest pairwise ΔE between the photos). The sum of ΔE over all named
regions is the headline number. Given several files (e.g. one per library
tag), it adds one render column per file and uses the photos of the first.
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from contact_sheet import linear_to_lab  # noqa: E402


def lab(rgb) -> np.ndarray:
    return linear_to_lab(np.clip(np.asarray(rgb, float), 0, None))


def means(data: dict, case: str, kind: str, name: str, group: str = "regions") -> tuple[np.ndarray | None, list]:
    vals = [np.asarray(im[group][name]["rgb"]) for im in data[case] if im["kind"] == kind and name in im[group]]
    return (np.mean(vals, axis=0) if vals else None), vals


def table(files: list[Path]) -> tuple[list[str], list[float]]:
    datas = [json.loads(f.read_text()) for f in files]
    tags = [f.stem for f in files]
    head = "| case | region | photos L a b (spread) | " + " | ".join(f"{t} L a b (ΔE)" for t in tags) + " |"
    md = [head, "|---|---|---|" + "---|" * len(tags)]
    sums = [0.0] * len(files)
    for case in datas[0]:
        photos = [im for im in datas[0][case] if im["kind"] == "photo"]
        for name in photos[0]["regions"]:
            p_mean, p_vals = means(datas[0], case, "photo", name)
            if p_mean is None or len(p_vals) < 2:
                continue
            spread = max(np.linalg.norm(lab(a) - lab(b)) for a, b in combinations(p_vals, 2))
            pl = lab(p_mean)
            cells = []
            for k, data in enumerate(datas):
                r_mean, _ = means(data, case, "render", name)
                if r_mean is None:
                    cells.append("–")
                    continue
                rl = lab(r_mean)
                de = float(np.linalg.norm(rl - pl))
                sums[k] += de
                cells.append(f"{rl[0]:.0f} {rl[1]:+.0f} {rl[2]:+.0f} ({de:.1f})")
            md.append(f"| {case} | {name} | {pl[0]:.0f} {pl[1]:+.0f} {pl[2]:+.0f} ({spread:.1f}) | " + " | ".join(cells) + " |")
    md.append("| **sum** | | | " + " | ".join(f"**{s:.0f}**" for s in sums) + " |")
    return md, sums


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("regions", type=Path, nargs="+")
    parser.add_argument("--md", type=Path)
    args = parser.parse_args()
    md, _ = table(args.regions)
    text = "\n".join(md) + "\n"
    if args.md:
        args.md.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
