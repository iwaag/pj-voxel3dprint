"""Kubelka-Munk surrogate: resin library + recipe -> top-face reflectance (RGB).

A fast forward model for fitting the resin library to region colours and,
later, to coupon photos. For a slab of a mixed material of thickness ``d``
over a diffuse backing of reflectance ``Rg`` (the paper / stage floor):

- mixing: linear volume fractions of sigma_a and sigma_s (as
  ``recipes_to_mapping.py``); the library has g = 0, so sigma_s = sigma_s';
- two-flux KM: K = 2 sigma_a, S = S_FACTOR * sigma_s', with
  a = 1 + K/S, b = sqrt(a^2 - 1),
  R = (1 - Rg (a - b coth(b S d))) / (a - Rg + b coth(b S d));
- dielectric boundary (Saunderson, n = 1.52): the camera sees
  R_obs = k1 * env + (1 - k1)(1 - k2) R / (1 - k2 R), with k2 = 0.6 (diffuse
  internal reflectance) and k1 * env = 0: in the step 1 dome stage (and the
  hand-held photos) the glossy top reflects a dark room;
- normalisation: region values are white-patch normalised (paper = 0.85 sRGB
  = 0.694 linear). With the paper / floor albedo RHO_PAPER = 0.8 and the same
  irradiance on the slab top, the predicted normalised value is
  R_obs * 0.694 / 0.8.

Regions are predicted per voxel column (``region_rgb_columns``): each 0.2 mm
voxel of the column is a KM layer (R_l, T_l of its mixed material), and the
layers are stacked from the backing up by the adding method
R = R_l + T_l^2 R_below / (1 - R_l R_below). The region value is the mean of
its columns' observed values. This is needed because the amber hosts and the
agate clear bands are translucent, so what lies below the surface shows. It
still ignores lateral light transport between columns (bands narrower than
the mean free path). ``region_rgb`` (area mixing of whole-slab materials by
the surface ``composition``) is kept for comparison.

This module holds the model and the case/recipe plumbing only. The Mitsuba
validation and the fit live in ``km_validate.py`` and ``km_fit.py``.
"""

from __future__ import annotations

import importlib.util
import json
from functools import cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RESIN_IDS = ("white", "black", "clear", "cyan", "magenta", "yellow")
S_FACTOR = 0.75
K2 = 0.6
RHO_PAPER = 0.8
WHITE_LIN = 0.6939  # sRGB 0.85 in linear
THICKNESS_M = 0.005

CASES = {
    "agate": {
        "export": "work/agate/export_menou_voxelprint.py",
        "voxels": ".local/pink-agate-v3/source/pink-teal-agate-strata-v3.voxels.json",
        "prefix": "agate-",
    },
    "amber": {
        "export": "work/amber/export_kohaku_tree_voxelprint.py",
        "voxels": ".local/amber-branching/source/amber-4102-branching-v2.voxels.json",
        "prefix": "amber-",
    },
    "fur": {
        "export": "work/fur/export_floating_fur_voxelprint.py",
        "voxels": ".local/floating-fur/source/floating-fur-v1.voxels.json",
        "prefix": "",
    },
}


def load_library(path: Path) -> tuple[dict, np.ndarray, np.ndarray]:
    """(document, sigma_a (6, 3), sigma_s (6, 3)) in RESIN_IDS order."""
    doc = json.loads(Path(path).read_text())
    by_id = {r["id"]: r for r in doc["resins"]}
    sa = np.array([by_id[i]["sigma_a_rgb_per_m"] for i in RESIN_IDS], float)
    ss = np.array([by_id[i]["sigma_s_rgb_per_m"] for i in RESIN_IDS], float)
    return doc, sa, ss


def library_with(doc: dict, sa: np.ndarray, ss: np.ndarray) -> dict:
    out = json.loads(json.dumps(doc))
    for resin in out["resins"]:
        k = RESIN_IDS.index(resin["id"])
        resin["sigma_a_rgb_per_m"] = [round(float(v), 2) for v in sa[k]]
        resin["sigma_s_rgb_per_m"] = [round(float(v), 2) for v in ss[k]]
    return out


@cache
def case_recipes(case: str) -> dict[str, np.ndarray]:
    """Material name (prefix stripped, as in the regions file) -> resin fractions (6,)."""
    info = CASES[case]
    script = ROOT / info["export"]
    spec = importlib.util.spec_from_file_location(script.stem, script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    resins = getattr(module, "RESINS", None) or module.RES
    recipes = getattr(module, "RECIPES", None) or module.REC
    order = [name.lower() for name, _ in resins]
    expected = ["veropurewht", "veroblack_or_veroflexbk", "veroclear_or_veroflexclr", "verocyan_or_veroflexcy", "veromgnt_or_veroflexmgt", "veroyellow_or_veroflexyl"]
    assert order == expected, order
    names = {m["material_id"]: m["name"] for m in json.loads((ROOT / info["voxels"]).read_text())["materials"]}
    return {names[int(k)].removeprefix(info["prefix"]): np.asarray(v, float) for k, v in recipes.items()}


def km_reflectance(sa: np.ndarray, ss: np.ndarray, d: float = THICKNESS_M, rg: float = RHO_PAPER) -> np.ndarray:
    """Two-flux KM reflectance of a slab over a backing (inside the boundary)."""
    k = 2.0 * np.asarray(sa, float)
    s = np.maximum(S_FACTOR * np.asarray(ss, float), 1e-9)
    a = 1.0 + k / s
    b = np.sqrt(np.maximum(a * a - 1.0, 1e-18))
    x = np.clip(b * s * d, 1e-9, 50.0)
    coth = 1.0 / np.tanh(x)
    return (1.0 - rg * (a - b * coth)) / (a - rg + b * coth)


def observed(r_inside: np.ndarray) -> np.ndarray:
    """Saunderson boundary, no external specular, normalised to paper white."""
    r_obs = (1.0 - 0.04) * (1.0 - K2) * r_inside / (1.0 - K2 * r_inside)
    return r_obs * WHITE_LIN / RHO_PAPER


def material_rgb(fractions: np.ndarray, sa: np.ndarray, ss: np.ndarray) -> np.ndarray:
    """Predicted white-normalised linear RGB of one recipe as a 5 mm slab on paper."""
    return observed(km_reflectance(fractions @ sa, fractions @ ss))


def region_rgb(composition: dict[str, float], recipes: dict[str, np.ndarray], sa: np.ndarray, ss: np.ndarray) -> np.ndarray:
    total = sum(composition.values())
    return sum(f / total * material_rgb(recipes[name], sa, ss) for name, f in composition.items())


def layer_rt(sa: np.ndarray, ss: np.ndarray, h: float) -> tuple[np.ndarray, np.ndarray]:
    """KM reflectance and transmittance of one layer of thickness h (no backing)."""
    k = 2.0 * np.asarray(sa, float)
    s = np.maximum(S_FACTOR * np.asarray(ss, float), 1e-12)
    a = 1.0 + k / s
    b = np.sqrt(np.maximum(a * a - 1.0, 1e-18))
    x = np.clip(b * s * h, 1e-12, 50.0)
    sh, ch = np.sinh(x), np.cosh(x)
    den = a * sh + b * ch
    return sh / den, b / den


@cache
def case_labels(case: str, face: str) -> np.ndarray:
    """Label volume as (layer from the viewer, y, x) in the face's own (x, y) indices."""
    info = CASES[case]
    doc = json.loads((ROOT / info["voxels"]).read_text())
    lab = np.load((ROOT / info["voxels"]).parent / doc["payload"]["path"])  # (z, y, x)
    return np.ascontiguousarray(lab[::-1] if face == "top" else lab)


def case_recipe_table(case: str) -> np.ndarray:
    """(max material id + 1, 6) resin fractions by material id (row 0 = air = 0)."""
    info = CASES[case]
    names = {m["material_id"]: m["name"].removeprefix(info["prefix"]) for m in json.loads((ROOT / info["voxels"]).read_text())["materials"]}
    recipes = case_recipes(case)
    table = np.zeros((max(names) + 1, len(RESIN_IDS)))
    for mid, name in names.items():
        if mid and name in recipes:
            table[mid] = recipes[name]
    return table


def region_columns(case: str, face: str, rect_mm, voxel_mm: float = 0.2) -> tuple[np.ndarray, np.ndarray]:
    """Unique label columns (n, layers) under a face rectangle and their weights."""
    lab = case_labels(case, face)
    x0, y0, x1, y1 = (int(round(v / voxel_mm)) for v in rect_mm)
    cols = lab[:, y0:y1, x0:x1].reshape(lab.shape[0], -1).T
    uniq, counts = np.unique(cols, axis=0, return_counts=True)
    return uniq, counts / counts.sum()


def column_rgb(columns: np.ndarray, weights: np.ndarray, recipe_table: np.ndarray, sa: np.ndarray, ss: np.ndarray, h: float = 0.0002, rg: float = RHO_PAPER) -> np.ndarray:
    """Weighted mean observed RGB of label columns (viewer first) over a paper backing."""
    msa, mss = recipe_table @ sa, recipe_table @ ss
    r_l, t_l = layer_rt(msa, mss, h)
    r_l[0], t_l[0] = 0.0, 1.0  # air voxels (outside the part) are transparent
    r = np.full((columns.shape[0], 3), rg)
    for layer in range(columns.shape[1] - 1, -1, -1):
        rl, tl = r_l[columns[:, layer]], t_l[columns[:, layer]]
        r = rl + tl * tl * r / (1.0 - rl * r)
    return weights @ observed(r)
