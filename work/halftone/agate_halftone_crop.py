"""Halftone-scale sanity crop of the printed agate (p1 step 5).

Writes two material-label volumes of the same ~5 x 5 x 5 mm crop on the
printer grid (600 x 300 dpi, 14 um layers), so they share geometry exactly:

* ``dither``: six resin labels (1..6 = white, black, clear, cyan, magenta,
  yellow), produced with the export's own ``hash_uniform``/``RECIPES`` on the
  global printer indices, i.e. the voxels that were actually printed there.
* ``effective``: the undithered semantic label per printer voxel (agate
  material ids 1..14, including the 0.3 mm clear shell on top/bottom).

Plus a six-resin optical mapping (one material per resin) from a resin
library.  The effective volume is mapped with the case's print-aware mapping
(``work/resins/recipes_to_mapping.py``), so the only difference between the
two renders is per-voxel averaging vs the real dither.

Usage (repository root):

    vdbmat/.venv/bin/python work/halftone/agate_halftone_crop.py \\
        --library work/resins/vero-j850-provisional-v2.json --out DIR \\
        [--x0-mm 34.4 --y0-mm 14.4 --size-mm 5.0]

Then ``vdbmat import-voxels`` + ``vdbmat convert`` each ``*.voxels.json``
(see ``work/halftone/build_agate_crop.sh``).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EXPORT = ROOT / "work" / "agate" / "export_menou_voxelprint.py"
RESIN_IDS = ("white", "black", "clear", "cyan", "magenta", "yellow")


def _load_export():
    spec = importlib.util.spec_from_file_location("menou_export", EXPORT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_volume(out: Path, stem: str, labels: np.ndarray, voxel_size: tuple[float, float, float],
                  materials: list[tuple[int, str]], notes: str) -> Path:
    payload = out / f"{stem}.material_id.npy"
    np.save(payload, labels.astype(np.uint16))
    manifest = {
        "format": "vdbmat.voxels",
        "format_version": "1.0.0",
        "asset_type": "material-label",
        "payload": {"path": payload.name, "sha256": _sha256(payload), "dtype": "uint16", "dimensions": ["z", "y", "x"]},
        "shape_zyx": list(labels.shape),
        "voxel_size_xyz_m": list(voxel_size),
        "local_to_world": [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]],
        "materials": [{"material_id": 0, "name": "air", "role": "background"}]
        + [{"material_id": mid, "name": name, "role": "material"} for mid, name in materials],
        "source": {"generator": "pj-voxel3dprint.agate-halftone-crop", "generator_version": "1.0.0", "notes": notes},
    }
    path = out / f"{stem}.voxels.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def resin_mapping(library: dict, basis: dict) -> dict:
    by_id = {r["id"]: r for r in library["resins"]}
    materials = [{"material_id": 0, "name": "air", "sigma_a_rgb_per_m": [0, 0, 0],
                  "sigma_s_rgb_per_m": [0, 0, 0], "g": 0.0, "ior": 1.0}]
    for mid, rid in enumerate(RESIN_IDS, 1):
        r = by_id[rid]
        materials.append({"material_id": mid, "name": f"resin-{rid}", "sigma_a_rgb_per_m": r["sigma_a_rgb_per_m"],
                          "sigma_s_rgb_per_m": r["sigma_s_rgb_per_m"], "g": r["g"], "ior": r["ior"]})
    return {
        "format": "vdbmat.optical-mapping",
        "format_version": "1.0.0",
        "configuration_id": f"vero6-single-resin+{library['library_id']}",
        "version": "1.0.0",
        "optical_basis": basis,
        "mixing_rule": "linear-volume-fraction-v1",
        "calibration_status": library["calibration_status"],
        "materials": materials,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--x0-mm", type=float, default=34.4)
    parser.add_argument("--y0-mm", type=float, default=14.4)
    parser.add_argument("--size-mm", type=float, default=5.0)
    args = parser.parse_args()
    ex = _load_export()
    args.out.mkdir(parents=True, exist_ok=True)

    source = np.load(ex.SOURCE, mmap_mode="r")
    px, py, pz = ex.PITCH_X_M, ex.PITCH_Y_M, ex.PITCH_Z_M
    x_lo = math.floor(args.x0_mm * 1e-3 / px)
    y_lo = math.floor(args.y0_mm * 1e-3 / py)
    nx = math.ceil(args.size_mm * 1e-3 / px)
    ny = math.ceil(args.size_mm * 1e-3 / py)
    nz = math.ceil(ex.EXTENT_Z_M / pz - 1e-6)
    xi = np.arange(x_lo, x_lo + nx)
    yi = np.arange(y_lo, y_lo + ny)
    x_m = (xi + 0.5) * px
    y_m = (yi + 0.5) * py
    z_m = (np.arange(nz) + 0.5) * pz
    src_x = np.clip(np.floor(x_m / ex.SRC_VOXEL_M), 0, source.shape[2] - 1).astype(np.intp)
    src_y = np.clip(np.floor(y_m / ex.SRC_VOXEL_M), 0, source.shape[1] - 1).astype(np.intp)
    src_z = np.clip(np.floor(z_m / ex.SRC_VOXEL_M), 0, source.shape[0] - 1).astype(np.intp)
    shell_xy = (
        (x_m[None, :] <= ex.SHELL_M) | ((ex.EXTENT_X_M - x_m[None, :]) <= ex.SHELL_M)
        | (y_m[:, None] <= ex.SHELL_M) | ((ex.EXTENT_Y_M - y_m[:, None]) <= ex.SHELL_M)
    )
    grid_x = np.broadcast_to(xi.astype(np.uint32)[None, :], (ny, nx))
    grid_y = np.broadcast_to(yi.astype(np.uint32)[:, None], (ny, nx))
    cumulative = {mid: np.cumsum(np.asarray(r, dtype=np.float64)) for mid, r in ex.RECIPES.items()}

    semantic = np.zeros((nz, ny, nx), dtype=np.uint16)
    dither = np.zeros((nz, ny, nx), dtype=np.uint16)
    for zi in range(nz):  # same per-slice logic as export_menou_voxelprint.main()
        sem = np.asarray(source[src_z[zi]])[np.ix_(src_y, src_x)].copy()
        if z_m[zi] <= ex.SHELL_M or (ex.EXTENT_Z_M - z_m[zi]) <= ex.SHELL_M:
            sem.fill(1)
        else:
            sem[shell_xy] = 1
        uniform = ex.hash_uniform(grid_x, grid_y, zi)
        idx = np.zeros((ny, nx), dtype=np.uint16)
        for mid, thresholds in cumulative.items():
            mask = sem == mid
            if np.any(mask):
                idx[mask] = np.searchsorted(thresholds, uniform[mask], side="right") + 1
        if np.any(idx == 0):
            raise RuntimeError(f"unassigned printer voxel in slice {zi}")
        semantic[zi], dither[zi] = sem, idx

    voxel = (px, py, pz)
    origin = f"printer x {x_lo}..{x_lo + nx}, y {y_lo}..{y_lo + ny}, all {nz} layers"
    source_doc = json.loads(ex.SOURCE_MANIFEST.read_text(encoding="utf-8"))
    names = {m["material_id"]: m["name"] for m in source_doc["materials"] if m["material_id"]}
    eff = _write_volume(args.out, "agate-crop-effective", semantic, voxel, sorted(names.items()),
                        f"Undithered semantic agate labels on the printer grid ({origin}).")
    dit = _write_volume(args.out, "agate-crop-dither", dither, voxel,
                        [(i, f"resin-{r}") for i, r in enumerate(RESIN_IDS, 1)],
                        f"Printed six-resin dither from export_menou_voxelprint hash/RECIPES ({origin}).")
    library = json.loads(args.library.read_text(encoding="utf-8"))
    semantic_map = json.loads((ex.SOURCE_MANIFEST.parent / "pink-teal-agate-strata-v3.optical-mapping.json")
                              .read_text(encoding="utf-8"))
    mapping = args.out / "vero6-resins.optical-mapping.json"
    mapping.write_text(json.dumps(resin_mapping(library, semantic_map["optical_basis"]), indent=2) + "\n",
                       encoding="utf-8")

    fractions = np.bincount(dither.ravel(), minlength=7)[1:] / dither.size
    expected = np.zeros(6)
    for mid, recipe in ex.RECIPES.items():
        expected += np.asarray(recipe) * np.count_nonzero(semantic == mid) / semantic.size
    print(json.dumps({
        "shape_zyx": list(semantic.shape), "voxel_um": [v * 1e6 for v in voxel],
        "effective": str(eff), "dither": str(dit), "resin_mapping": str(mapping),
        "resin_fraction_dither": dict(zip(RESIN_IDS, np.round(fractions, 4).tolist())),
        "resin_fraction_recipes": dict(zip(RESIN_IDS, np.round(expected, 4).tolist())),
    }, indent=1))


if __name__ == "__main__":
    main()
