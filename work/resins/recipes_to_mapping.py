"""Build a print-aware optical mapping from a resin library and print recipes.

Replaces the per-case ``BASE``/``effective`` constants (agate/fur generators,
``work/amber/build_print_preview_mapping.py``) with one shared resin table.

Usage (repository root):

    vdbmat/.venv/bin/python work/resins/recipes_to_mapping.py \\
        --library work/resins/vero-j850-provisional-v2.json \\
        --recipes NAME.resin-recipes.json \\
        --semantic NAME.optical-mapping.json \\
        --out NAME.print-aware.optical-mapping.json

``--recipes`` is the ``*.resin-recipes.json`` written by every export script
(``resin_order`` + ``recipes_by_material_id`` or
``recipes_by_source_material_id``); ``work/resins/extract_recipes.py`` writes
the same document straight from an export script without exporting slices.
``--semantic`` supplies material ids, names and the optical basis.

Mixing: linear volume fractions for sigma_a, sigma_s and IOR
(``linear-volume-fraction-v1``).  The global ``g`` is the scattering-weighted
mean of the library ``g`` values (0 for the v2 library).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

FIELDS = ("sigma_a_rgb_per_m", "sigma_s_rgb_per_m")


def _resin_lookup(library: dict) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for resin in library["resins"]:
        for name in resin["names"]:
            lookup[name.lower()] = resin
    return lookup


def _recipes(document: dict) -> dict[int, list[float]]:
    for key in ("recipes_by_material_id", "recipes_by_source_material_id"):
        if key in document:
            return {int(k): list(map(float, v)) for k, v in document[key].items()}
    raise SystemExit("recipes document has no recipes_by_*material_id table")


def mix(recipe: list[float], resins: list[dict]) -> dict[str, object]:
    weights = np.asarray(recipe, dtype=np.float64)
    if weights.shape != (len(resins),) or np.any(weights < 0.0):
        raise SystemExit(f"recipe {recipe} does not match {len(resins)} resins")
    if not np.isclose(weights.sum(), 1.0, atol=1e-6):
        raise SystemExit(f"recipe {recipe} sums to {weights.sum()}, not 1")
    mixed = {
        field: sum(w * np.asarray(r[field], dtype=np.float64) for w, r in zip(weights, resins))
        for field in FIELDS
    }
    ior = float(sum(w * r["ior"] for w, r in zip(weights, resins)))
    scatter = np.asarray([w * np.mean(r["sigma_s_rgb_per_m"]) for w, r in zip(weights, resins)])
    g = float(np.dot(scatter, [r["g"] for r in resins]) / scatter.sum()) if scatter.sum() > 0 else 0.0
    return {
        "sigma_a_rgb_per_m": [round(float(v), 6) for v in mixed["sigma_a_rgb_per_m"]],
        "sigma_s_rgb_per_m": [round(float(v), 6) for v in mixed["sigma_s_rgb_per_m"]],
        "g": round(g, 6),
        "ior": round(ior, 6),
    }


def build_mapping(library: dict, recipes_doc: dict, semantic: dict) -> dict:
    lookup = _resin_lookup(library)
    try:
        resins = [lookup[name.lower()] for name in recipes_doc["resin_order"]]
    except KeyError as error:
        raise SystemExit(f"resin {error} is not in library {library['library_id']}") from error
    recipes = _recipes(recipes_doc)

    materials = []
    for material in semantic["materials"]:
        material_id = int(material["material_id"])
        if material_id == 0:
            materials.append(material)
            continue
        if material_id not in recipes:
            raise SystemExit(f"material {material_id} ({material['name']}) has no recipe")
        materials.append(
            {"material_id": material_id, "name": material["name"], **mix(recipes[material_id], resins)}
        )
    return {
        **semantic,
        "configuration_id": f"{semantic['configuration_id']}+{library['library_id']}",
        "mixing_rule": "linear-volume-fraction-v1",
        "calibration_status": library["calibration_status"],
        "materials": materials,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--recipes", type=Path, required=True)
    parser.add_argument("--semantic", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    library = json.loads(args.library.read_text(encoding="utf-8"))
    recipes_doc = json.loads(args.recipes.read_text(encoding="utf-8"))
    semantic = json.loads(args.semantic.read_text(encoding="utf-8"))
    mapping = build_mapping(library, recipes_doc, semantic)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
