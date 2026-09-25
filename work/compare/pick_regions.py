"""Pick top-face regions (slab mm) per material from the label volumes.

Usage (repo root):

    vdbmat/.venv/bin/python work/compare/pick_regions.py OUT.json

For every batch1 case this reads the 0.2 mm semantic label volume
(``.local/<case>/source/*.material_id.npy``, from
``work/compare/rebuild_batch1_sources.sh``). It reduces the volume to per-pixel
material fractions of what the camera sees through the face (a 2-D one-hot
stack), and places for every material the ``WINDOW_MM`` square with the
highest fraction of that material, at least ``BORDER_MM`` from the slab edge.
A region is kept if that fraction is >= ``MIN_PURITY``. Agate bands are only
0.4-1 mm wide, so a region is rarely pure: each region stores its full
``composition`` (material name -> area fraction) for fits that unmix.
``tiles`` is a regular grid of ``TILE_MM`` squares over the face interior (for
photo-to-photo and tone statistics).

Fraction maps per case:
- agate: the bands are extruded through z, so layer 12 (below the 0.3 mm
  clear shell) is what both faces show (``bottom`` = ``top``).
- amber: the veins change with depth. The map is the mean over the outer
  1 mm, ``top`` = z 20..24 and ``bottom`` = z 0..4 (the batch1 photos show
  the bottom face, see p2 report2).
- fur: seen through the clear block, each column (x, y) is one class by its
  hair content over all layers: ``margin`` (no hair), ``undercoat``
  (material 2 only, the 18 % white undercoat), ``tuft`` (materials 3-5 make
  up most of the hair voxels, no dark hair), ``dark`` (materials 6-7 present).
  ``bottom`` = ``top``.

Rectangles are ``[x0, y0, x1, y1]`` in mm on the visible face, in the model
coordinates of the face's own layer (x 0..60, y 0..30), i.e. the coordinates
the corner picks use (reversed assignment for a bottom-up photo).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import uniform_filter

ROOT = Path(__file__).resolve().parents[2]
VOXEL_MM = 0.2
WINDOW_MM = 2.0
BORDER_MM = 2.5
MIN_PURITY = 0.45
TILE_MM = 5.0


def _names(voxels_json: Path) -> list[str]:
    doc = json.loads(voxels_json.read_text())
    return [m["name"] for m in doc["materials"]]


def _rect(cx: float, cy: float, half: float) -> list[float]:
    return [round(cx - half, 2), round(cy - half, 2), round(cx + half, 2), round(cy + half, 2)]


def _composition(frac: np.ndarray, names: list[str], j0: int, j1: int, i0: int, i1: int) -> dict[str, float]:
    mean = frac[:, j0:j1, i0:i1].mean(axis=(1, 2))
    return {names[m]: round(float(v), 3) for m, v in enumerate(mean) if v >= 0.005}


def _face(frac: np.ndarray, names: list[str], skip: set[int]) -> dict:
    """frac: (n_materials, ny, nx) fractions of the visible material per pixel."""
    _, ny, nx = frac.shape
    win = int(round(WINDOW_MM / VOXEL_MM))
    border = int(round(BORDER_MM / VOXEL_MM))
    regions = {}
    for m in range(frac.shape[0]):
        if m in skip or frac[m].max() == 0:
            continue
        # uniform_filter centres an even window at [j - win/2, j + win/2).
        local = uniform_filter(frac[m], size=win, mode="constant")
        edge = border + win // 2
        local[:edge, :] = local[-edge:, :] = 0
        local[:, :edge] = local[:, -edge:] = 0
        j, i = np.unravel_index(np.argmax(local), local.shape)
        if local[j, i] < MIN_PURITY:
            continue
        j0, i0 = j - win // 2, i - win // 2
        regions[names[m]] = {
            "rect": _rect((i0 + win / 2) * VOXEL_MM, (j0 + win / 2) * VOXEL_MM, WINDOW_MM / 2),
            "purity": round(float(frac[m, j0 : j0 + win, i0 : i0 + win].mean()), 3),
            "composition": _composition(frac, names, j0, j0 + win, i0, i0 + win),
        }
    tiles = {}
    step = int(round(TILE_MM / VOXEL_MM))
    for ty, j0 in enumerate(range(border, ny - border - step + 1, step)):
        for tx, i0 in enumerate(range(border, nx - border - step + 1, step)):
            tiles[f"tile {tx},{ty}"] = {
                "rect": _rect((i0 + step / 2) * VOXEL_MM, (j0 + step / 2) * VOXEL_MM, TILE_MM / 2),
                "composition": _composition(frac, names, j0, j0 + step, i0, i0 + step),
            }
    return {"regions": regions, "tiles": tiles}


def _one_hot(layers: np.ndarray, n: int) -> np.ndarray:
    return np.stack([(layers == m).mean(axis=0) for m in range(n)]).astype(float)


def agate() -> dict:
    base = ROOT / ".local/pink-agate-v3/source/pink-teal-agate-strata-v3"
    lab = np.load(f"{base}.material_id.npy")
    names = [n.removeprefix("agate-") for n in _names(Path(f"{base}.voxels.json"))]
    top = _face(_one_hot(lab[12:13], len(names)), names, {0, 1})
    return {"top": top, "bottom": top}


def amber() -> dict:
    base = ROOT / ".local/amber-branching/source/amber-4102-branching-v2"
    lab = np.load(f"{base}.material_id.npy")
    names = [n.removeprefix("amber-") for n in _names(Path(f"{base}.voxels.json"))]
    return {
        "top": _face(_one_hot(lab[20:25], len(names)), names, {0}),
        "bottom": _face(_one_hot(lab[0:5], len(names)), names, {0}),
    }


def fur() -> dict:
    base = ROOT / ".local/floating-fur/source/floating-fur-v1"
    lab = np.load(f"{base}.material_id.npy")
    counts = np.stack([(lab == m).sum(axis=0) for m in range(8)])  # (mat, y, x)
    hair = counts[2:].sum(axis=0)
    cls = np.zeros(hair.shape, int)
    cls[hair == 0] = 1
    cls[(hair > 0) & (counts[2] == hair)] = 2
    cls[(hair > 0) & (counts[3:6].sum(axis=0) > 0.5 * hair) & (counts[6:].sum(axis=0) == 0)] = 3
    cls[counts[6:].sum(axis=0) > 0] = 4
    names = ["-", "margin", "undercoat", "tuft", "dark"]
    top = _face(np.stack([(cls == c).astype(float) for c in range(5)]), names, {0})
    return {"top": top, "bottom": top}


def main() -> None:
    out = {"agate": agate(), "amber": amber(), "fur": fur()}
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1) + "\n")
    for case, faces in out.items():
        for face, d in faces.items():
            print(case, face, {k: v["purity"] for k, v in d["regions"].items()}, len(d["tiles"]), "tiles")


if __name__ == "__main__":
    main()
