"""Fit the resin library to photo regions with the KM surrogate (p2 step 4).

Usage (repo root):

    vdbmat/.venv/bin/python work/resins/km_fit.py REGIONS.json LIBRARY.json OUT_LIBRARY.json \
        [--version-id vero-j850-provisional-v3a] [--report OUT.md] [--prior 0.3] [--tiles 0.5] [--fur 0.5]

REGIONS.json is ``work/compare/region_table.py --renders TAG DIR`` output for
batch1-v3.json: the three photos per case, each followed by its camera-matched
render made with LIBRARY. Observations are the **mean of the three photos**
(white-normalised linear RGB) per named region and per 5 mm tile.

Prediction for a region r with parameters p (see ``km_surrogate.py``):

    pred_r(p) = KM_r(p) * c_r,   c_r = render_r(LIBRARY) / KM_r(LIBRARY)   (per channel)

KM_r is the column-stack KM model over the region's label columns, and render_r
the mean of the three matched Mitsuba renders. The correction c_r carries
everything KM does not model (lateral transport between narrow bands and veins,
slab shading of the paper, the stage's environment and viewing angle), with KM
supplying the parameter sensitivity. c_r is a property of the region's
geometry, not a library constant. After rebuilding with the fitted library,
refit from the new renders (a surrogate-correction iteration).

Parameters: log sigma_a and log sigma_s' of the six resins (36 numbers), with
bounds LIBRARY x/÷ 5. Residuals: ΔL, Δa, Δb (Lab of the normalised linear RGB)
per region, weighted by 1 / max(photo spread, 3) (the pairwise ΔE between the
three photos, p2 report2), with a weight of ``--tiles`` for tiles and ``--fur``
for fur regions. The fur margin is not used, because it shows refracted paper.
A prior pull of ``--prior`` * ln(p / p_LIBRARY) / ln 5 per parameter is added.
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[1] / "compare"))
import km_surrogate as km  # noqa: E402
from contact_sheet import linear_to_lab  # noqa: E402

FACES = {"agate": "top", "amber": "bottom", "fur": "top"}


def lab_rows(rgb: np.ndarray) -> np.ndarray:
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = np.clip(rgb, 1e-9, None) @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], -1)


class Problem:
    def __init__(self, data: dict, regions_mm: dict, sa0: np.ndarray, ss0: np.ndarray, tile_weight: float, fur_weight: float) -> None:
        self.items = []  # (case, group, name, columns, weights, recipe_table, obs_rgb, c_r, weight)
        for case, images in data.items():
            face = FACES[case]
            table = km.case_recipe_table(case)
            photos = [im for im in images if im["kind"] == "photo"]
            renders = [im for im in images if im["kind"] == "render"]
            for group in ("regions", "tiles"):
                for name, reg in regions_mm[case][face][group].items():
                    if case == "fur" and name == "margin":
                        continue
                    pv = [np.asarray(p[group][name]["rgb"]) for p in photos if name in p[group]]
                    rv = [np.asarray(r[group][name]["rgb"]) for r in renders if name in r[group]]
                    if len(pv) < 2 or len(rv) < 1:
                        continue
                    cols, wts = km.region_columns(case, face, reg["rect"])
                    km0 = km.column_rgb(cols, wts, table, sa0, ss0)
                    spread = max(np.linalg.norm(linear_to_lab(a) - linear_to_lab(b)) for a, b in combinations(pv, 2))
                    w = 1.0 / max(spread, 3.0)
                    if group == "tiles":
                        w *= tile_weight
                    if case == "fur":
                        w *= fur_weight
                    self.items.append(
                        {
                            "case": case,
                            "group": group,
                            "name": name,
                            "cols": cols,
                            "wts": wts,
                            "table": table,
                            "obs": np.mean(pv, axis=0),
                            "render": np.mean(rv, axis=0),
                            "c": np.mean(rv, axis=0) / np.maximum(km0, 1e-6),
                            "w": w,
                            "spread": spread,
                        }
                    )
        self.obs_lab = lab_rows(np.array([it["obs"] for it in self.items]))
        self.sqrt_w = np.sqrt([it["w"] for it in self.items])

    def predict(self, sa: np.ndarray, ss: np.ndarray) -> np.ndarray:
        return np.array([km.column_rgb(it["cols"], it["wts"], it["table"], sa, ss) * it["c"] for it in self.items])

    def residual_lab(self, sa: np.ndarray, ss: np.ndarray) -> np.ndarray:
        return lab_rows(self.predict(sa, ss)) - self.obs_lab


def unpack(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return np.exp(x[:18]).reshape(6, 3), np.exp(x[18:]).reshape(6, 3)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("regions", type=Path)
    parser.add_argument("library", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--version-id", default="vero-j850-provisional-v3a")
    parser.add_argument("--regions-mm", type=Path, default=km.ROOT / "work/compare/specs/batch1-regions-mm.json")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--prior", type=float, default=0.3)
    parser.add_argument("--tiles", type=float, default=0.5)
    parser.add_argument("--fur", type=float, default=0.5)
    args = parser.parse_args()

    doc, sa0, ss0 = km.load_library(args.library)
    data = json.loads(args.regions.read_text())
    prob = Problem(data, json.loads(args.regions_mm.read_text()), sa0, ss0, args.tiles, args.fur)
    x0 = np.r_[np.log(sa0).ravel(), np.log(ss0).ravel()]
    ln5 = np.log(5.0)

    def residuals(x: np.ndarray) -> np.ndarray:
        sa, ss = unpack(x)
        r = prob.residual_lab(sa, ss) * prob.sqrt_w[:, None]
        return np.r_[r.ravel(), np.sqrt(args.prior) * (x - x0) / ln5]

    res = least_squares(residuals, x0, bounds=(x0 - ln5, x0 + ln5), x_scale=1.0, diff_step=1e-3, max_nfev=400)
    sa, ss = unpack(res.x)

    before = np.linalg.norm(prob.residual_lab(sa0, ss0), axis=1)
    after = np.linalg.norm(prob.residual_lab(sa, ss), axis=1)
    out = km.library_with(doc, sa, ss)
    out["library_id"] = args.version_id
    out["source"] = (
        "Fitted (p2 step 4, work/resins/km_fit.py) to three-photo means of batch1 regions and 5 mm tiles, "
        "KM column surrogate corrected per region by camera-matched Mitsuba renders of "
        f"{doc['library_id']}. Bounds x/÷5 around {doc['library_id']}. Not calibration data."
    )
    out["fit"] = {
        "from": doc["library_id"],
        "regions": args.regions.as_posix(),
        "prior": args.prior,
        "tile_weight": args.tiles,
        "fur_weight": args.fur,
        "cost": float(res.cost),
        "nfev": int(res.nfev),
        "status": int(res.status),
        "named_region_dE_sum_before_after": [
            round(float(before[[i for i, it in enumerate(prob.items) if it["group"] == "regions"]].sum()), 1),
            round(float(after[[i for i, it in enumerate(prob.items) if it["group"] == "regions"]].sum()), 1),
        ],
    }
    args.output.write_text(json.dumps(out, indent=2) + "\n")

    lines = [
        f"# KM fit {doc['library_id']} -> {args.version_id}",
        "",
        f"least_squares status {res.status}, nfev {res.nfev}, cost {res.cost:.2f}; prior {args.prior}, tile weight {args.tiles}, fur weight {args.fur}.",
        "",
        "Predicted (surrogate-corrected) ΔE76 to the three-photo mean, named regions:",
        "",
        "| case | region | photo spread | ΔE before | ΔE after |",
        "|---|---|---:|---:|---:|",
    ]
    for it, b, a in zip(prob.items, before, after):
        if it["group"] == "regions":
            lines.append(f"| {it['case']} | {it['name']} | {it['spread']:.1f} | {b:.1f} | {a:.1f} |")
    reg = [i for i, it in enumerate(prob.items) if it["group"] == "regions"]
    til = [i for i, it in enumerate(prob.items) if it["group"] == "tiles"]
    lines += [
        f"| **sum** | {len(reg)} regions | | **{before[reg].sum():.0f}** | **{after[reg].sum():.0f}** |",
        "",
        f"Tiles ({len(til)}): mean ΔE {before[til].mean():.1f} -> {after[til].mean():.1f}.",
        "",
        "## Parameters (1/m), ratio to the start",
        "",
        "| resin | σa R G B | ratio | σs' R G B | ratio |",
        "|---|---|---|---|---|",
    ]
    for k, rid in enumerate(km.RESIN_IDS):
        lines.append(
            f"| {rid} | {', '.join(f'{v:.0f}' for v in sa[k])} | {', '.join(f'{v:.2f}' for v in sa[k] / sa0[k])} | "
            f"{', '.join(f'{v:.0f}' for v in ss[k])} | {', '.join(f'{v:.2f}' for v in ss[k] / ss0[k])} |"
        )
    at_bound = np.isclose(np.abs(res.x - x0), ln5, atol=1e-3)
    lines += ["", f"Parameters at a bound: {int(at_bound.sum())} / 36."]
    text = "\n".join(lines) + "\n"
    if args.report:
        args.report.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
