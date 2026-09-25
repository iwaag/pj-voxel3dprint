"""Validate the KM surrogate against Mitsuba on homogeneous 60 x 30 x 5 mm slabs.

Usage (repo root):

    vdbmat/.venv/bin/python work/resins/km_validate.py LIBRARY.json OUT_DIR [--build] [--render] [--spp 128]

``--build`` writes one all-ones label volume and, per test material, a
one-material optical mapping (the recipe mixed with ``LIBRARY`` exactly as
``recipes_to_mapping.py`` does) and its optical zarr. ``--render`` renders each
slab on the ``stage-print-photo`` preset (320², no denoise) at ``--depth``
(default 256, Russian roulette off). A homogeneous white slab loses ~40 % of
its reflectance at the preset's depth 32 (p2 report4). Without flags it
only measures what exists. The measurement is the white-normalised mean of the
central 20 x 10 mm of the top face (``region_table.measure``), compared with
``km_surrogate.material_rgb`` of the same recipe. Report: ``OUT_DIR/km-validate.md``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[1] / "compare"))
import km_surrogate as km  # noqa: E402
from contact_sheet import linear_to_lab  # noqa: E402
from recipes_to_mapping import mix  # noqa: E402
from region_table import measure  # noqa: E402

ROOT = km.ROOT
TESTS = [
    ("agate pale-pink", "agate", "pale-pink-e6c5e1"),
    ("agate deep-teal", "agate", "deep-teal"),
    ("agate white", "agate", "white"),
    ("amber host-85", "amber", "host-85"),
    ("amber host-100", "amber", "host-100"),
    ("fur undercoat (18 % white)", "fur", "fur-translucent-white"),
]
CAMERA = {"azimuth_deg": -54.0, "elevation_deg": 65.0, "distance_factor": 3.6, "fov_deg": 35.0}
WHITE = [0.03, 0.65, 0.13, 0.85]
CENTRE_MM = [20.0, 10.0, 40.0, 20.0]
V = ROOT / "vdbmat/.venv/bin/vdbmat"


def slug(label: str) -> str:
    return label.split(" (")[0].replace(" ", "-")


def build(library: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    labels = np.ones((25, 150, 300), np.uint16)
    np.save(out / "homog.material_id.npy", labels)
    import hashlib

    manifest = {
        "format": "vdbmat.voxels",
        "format_version": "1.0.0",
        "asset_type": "material-label",
        "payload": {"path": "homog.material_id.npy", "sha256": hashlib.sha256((out / "homog.material_id.npy").read_bytes()).hexdigest(), "dtype": "uint16", "dimensions": ["z", "y", "x"]},
        "shape_zyx": [25, 150, 300],
        "voxel_size_xyz_m": [0.0002, 0.0002, 0.0002],
        "local_to_world": np.eye(4).tolist(),
        "materials": [{"material_id": 0, "name": "air", "role": "background"}, {"material_id": 1, "name": "test", "role": "material"}],
        "source": {"generator": "pj-voxel3dprint.km-validate", "generator_version": "1.0.0", "notes": "homogeneous 60x30x5 mm slab"},
    }
    (out / "homog.voxels.json").write_text(json.dumps(manifest, indent=1))
    subprocess.run([V, "import-voxels", "--overwrite", out / "homog.voxels.json", out / "homog-material.zarr"], check=True, capture_output=True)
    semantic = json.loads((ROOT / ".local/pink-agate-v3/print-aware-v2/agate.optical-mapping.json").read_text())
    by_id = {r["id"]: r for r in library["resins"]}
    resins = [by_id[i] for i in km.RESIN_IDS]
    for label, case, name in TESTS:
        recipe = km.case_recipes(case)[name]
        mapping = {
            **{k: v for k, v in semantic.items() if k != "materials"},
            "configuration_id": f"km-validate-{slug(label)}+{library['library_id']}",
            "materials": [semantic["materials"][0], {"material_id": 1, "name": "test", **mix(list(recipe), resins)}],
        }
        mpath = out / f"{slug(label)}.optical-mapping.json"
        mpath.write_text(json.dumps(mapping, indent=1))
        subprocess.run([V, "convert", "--overwrite", "--mapping-file", mpath, out / "homog-material.zarr", out / f"{slug(label)}-optical.zarr"], check=True, capture_output=True)
        print("built", label)


def render(out: Path, spp: int, depth: int) -> None:
    for label, _, _ in TESTS:
        subprocess.run(
            [
                ROOT / "work/compare/render_stage.sh",
                out / f"{slug(label)}-optical.zarr",
                out / f"{slug(label)}.png",
                "--width", "320", "--height", "320", "--spp", str(spp),
                "--max-depth", str(depth), "--rr-depth", str(depth),
            ],
            check=True,
            cwd=ROOT,
        )
        print("rendered", label)


def report(library_path: Path, out: Path) -> list[str]:
    _, sa, ss = km.load_library(library_path)
    regions = {"top": {"regions": {"centre": {"rect": CENTRE_MM}}, "tiles": {}}}
    lines = [
        f"KM surrogate vs Mitsuba, homogeneous 5 mm slabs on the print-photo stage ({library_path.name})",
        "",
        "| material | Mitsuba RGB (norm. linear) | KM RGB | KM / Mitsuba | Mitsuba Lab | KM Lab | ΔE76 |",
        "|---|---|---|---|---|---|---:|",
    ]
    for label, case, name in TESTS:
        png = out / f"{slug(label)}.png"
        if not png.exists():
            continue
        m = measure({"path": str(png), "kind": "render", "white": WHITE, "camera": CAMERA, "volume": "none"}, regions)
        mit = np.asarray(m["regions"]["centre"]["rgb"])
        pred = km.material_rgb(km.case_recipes(case)[name], sa, ss)
        ml, kl = linear_to_lab(np.clip(mit, 0, None)), linear_to_lab(pred)
        lines.append(
            f"| {label} | {', '.join(f'{v:.3f}' for v in mit)} | {', '.join(f'{v:.3f}' for v in pred)} | "
            f"{', '.join(f'{v:.2f}' for v in pred / mit)} | {ml[0]:.0f} {ml[1]:+.0f} {ml[2]:+.0f} | "
            f"{kl[0]:.0f} {kl[1]:+.0f} {kl[2]:+.0f} | {np.linalg.norm(kl - ml):.1f} |"
        )
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("library", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--spp", type=int, default=128)
    parser.add_argument("--depth", type=int, default=256, help="max_depth = rr_depth (homogeneous white slabs need >= 256)")
    args = parser.parse_args()
    if args.build:
        build(json.loads(args.library.read_text()), args.out_dir)
    if args.render:
        render(args.out_dir, args.spp, args.depth)
    lines = report(args.library, args.out_dir)
    (args.out_dir / "km-validate.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
