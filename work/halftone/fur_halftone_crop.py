"""Printer-pitch crop of the printed fur vs the 0.2 mm review grid (p2 step 5).

Writes three material-label volumes of the same ~6 x 6 mm window through all
layers of the floating-fur print:

* ``fur-crop-dither``: the six resin labels actually printed there (1..6 =
  white, black, clear, cyan, magenta, yellow), produced with the export's
  own hair drawing (``hairs()``, same seed), undercoat core and
  ``noise``/``REC`` dither on the global printer indices (42.3 x 84.7 x 14 um);
* ``fur-crop-effective``: the undithered semantic label (fur material ids
  1..7) per printer voxel, i.e. the printed geometry with per-material
  effective media;
* ``fur-crop-review``: the same window cut from the 0.2 mm review volume
  (``.local/floating-fur/source/floating-fur-v1``), which is what the viewer
  shows. Its hairs come from a different generator, so it is a different
  object, not a downsample.

Plus ``vero6-resins.optical-mapping.json`` (one material per resin). Build
with ``work/halftone/build_fur_crop.sh``.

The export draws all 6800 hairs into a full-grid uint8 memmap (1418 x 354 x
358). It is regenerated at ``--cache`` unless that file exists (~10 min, CPU).

Usage (repo root):

    vdbmat/.venv/bin/python work/halftone/fur_halftone_crop.py --library LIB.json --out DIR \
        [--x0-mm 26 --y0-mm 12 --size-mm 6] [--cache .local/floating-fur/halftone/native_labels.dat]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from agate_halftone_crop import RESIN_IDS, _write_volume, resin_mapping  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
EXPORT = ROOT / "work" / "fur" / "export_floating_fur_voxelprint.py"
REVIEW = ROOT / ".local/floating-fur/source/floating-fur-v1"


def _load_export():
    spec = importlib.util.spec_from_file_location("fur_export", EXPORT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--x0-mm", type=float, default=26.0)
    parser.add_argument("--y0-mm", type=float, default=12.0)
    parser.add_argument("--size-mm", type=float, default=6.0)
    parser.add_argument("--cache", type=Path, default=ROOT / ".local/floating-fur/halftone/native_labels.dat")
    args = parser.parse_args()
    ex = _load_export()
    args.out.mkdir(parents=True, exist_ok=True)
    args.cache.parent.mkdir(parents=True, exist_ok=True)
    if args.cache.exists():
        hair = np.memmap(args.cache, dtype=np.uint8, mode="r", shape=(ex.NZ, ex.H, ex.W))
    else:
        ex.CACHE = args.cache
        hair, _ = ex.hairs()

    x_lo, y_lo = math.floor(args.x0_mm / (ex.PX * 1000)), math.floor(args.y0_mm / (ex.PY * 1000))
    nx, ny = math.ceil(args.size_mm / (ex.PX * 1000)), math.ceil(args.size_mm / (ex.PY * 1000))
    xi, yi = np.arange(x_lo, x_lo + nx), np.arange(y_lo, y_lo + ny)
    xx, yy = np.meshgrid((xi + 0.5) * ex.PX * 1000, (yi + 0.5) * ex.PY * 1000)
    gx = np.broadcast_to(xi.astype(np.uint32)[None, :], (ny, nx))
    gy = np.broadcast_to(yi.astype(np.uint32)[:, None], (ny, nx))
    thr = {k: np.cumsum(v) for k, v in ex.REC.items()}
    semantic = np.zeros((ex.NZ, ny, nx), np.uint16)
    dither = np.zeros((ex.NZ, ny, nx), np.uint16)
    for zi in range(ex.NZ):  # same per-slice logic as export_floating_fur_voxelprint.main()
        z = (zi + 0.5) * ex.PZ * 1000
        core = (np.abs((xx - 29) / 25) ** 6 + np.abs((yy - 15) / 10.4) ** 6 + abs((z - 2.5) / 1.35) ** 6 < 1) & (
            np.sin(xx * 2.1 + yy * 1.3 + z * 4.7) + np.sin(xx * 0.43 - yy * 1.8) > 1.25
        )
        sem = np.ones((ny, nx), np.uint8)
        sem[core] = 2
        hm = np.asarray(hair[zi, y_lo : y_lo + ny, x_lo : x_lo + nx])
        sem[hm > 0] = hm[hm > 0]
        u = ex.noise(gx, gy, zi)
        idx = np.zeros((ny, nx), np.uint8)
        for mid, q in thr.items():
            m = sem == mid
            idx[m] = np.searchsorted(q, u[m], side="right").astype(np.uint8) + 1
        semantic[zi], dither[zi] = sem, idx

    voxel = (ex.PX, ex.PY, ex.PZ)
    origin = f"printer x {x_lo}..{x_lo + nx}, y {y_lo}..{y_lo + ny}, all {ex.NZ} layers"
    review_doc = json.loads(Path(f"{REVIEW}.voxels.json").read_text())
    names = {m["material_id"]: m["name"] for m in review_doc["materials"] if m["material_id"]}
    eff = _write_volume(args.out, "fur-crop-effective", semantic, voxel, sorted(names.items()),
                        f"Undithered fur labels on the printer grid ({origin}).")
    dit = _write_volume(args.out, "fur-crop-dither", dither, voxel,
                        [(i, f"resin-{r}") for i, r in enumerate(RESIN_IDS, 1)],
                        f"Printed six-resin dither from export_floating_fur_voxelprint hairs/noise/REC ({origin}).")
    review = np.load(f"{REVIEW}.material_id.npy")
    rx0, ry0 = round(args.x0_mm / 0.2), round(args.y0_mm / 0.2)
    rn = round(args.size_mm / 0.2)
    rev = _write_volume(args.out, "fur-crop-review", review[:, ry0 : ry0 + rn, rx0 : rx0 + rn], (0.0002,) * 3,
                        sorted(names.items()), f"0.2 mm review labels, x {rx0}..{rx0 + rn}, y {ry0}..{ry0 + rn} voxels.")
    library = json.loads(args.library.read_text())
    basis = json.loads(Path(f"{REVIEW}.optical-mapping.json").read_text())["optical_basis"]
    mapping = args.out / "vero6-resins.optical-mapping.json"
    mapping.write_text(json.dumps(resin_mapping(library, basis), indent=2) + "\n")

    def column_stats(vol: np.ndarray, hair_ids: list[int]) -> dict:
        return {"hair_voxel_fraction": round(float(np.isin(vol, hair_ids).mean()), 4),
                "columns_with_hair": round(float(np.isin(vol, hair_ids).any(axis=0).mean()), 4)}

    print(json.dumps({
        "printer_shape_zyx": list(semantic.shape), "review_shape_zyx": [review.shape[0], rn, rn],
        "effective": str(eff), "dither": str(dit), "review": str(rev), "resin_mapping": str(mapping),
        "printer_stats": column_stats(semantic, [2, 3, 4, 5, 6, 7]),
        "review_stats": column_stats(review[:, ry0 : ry0 + rn, rx0 : rx0 + rn], [2, 3, 4, 5, 6, 7]),
        "resin_fraction_dither": dict(zip(RESIN_IDS, np.round(np.bincount(dither.ravel(), minlength=7)[1:] / dither.size, 4).tolist())),
    }, indent=1))


if __name__ == "__main__":
    main()
