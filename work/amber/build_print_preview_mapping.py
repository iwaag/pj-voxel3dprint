from __future__ import annotations

import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / ".local" / "amber-branching" / "source" / "amber-4102-branching-v2.optical-mapping.json"
OUTPUT = ROOT / ".local" / "amber-branching" / "source" / "amber-4102-print-preview.optical-mapping.json"

# Provisional optical basis for the six loaded Vero materials. These are not
# manufacturer calibration values; they provide a print-aware first review.
BASE = {
    "white":   ([15.0, 15.0, 15.0], [800.0, 800.0, 800.0], 1.53),
    "black":   ([450.0, 450.0, 470.0], [70.0, 70.0, 70.0], 1.54),
    "clear":   ([3.0, 4.0, 8.0], [2.0, 2.0, 2.0], 1.52),
    "cyan":    ([420.0, 65.0, 35.0], [22.0, 18.0, 16.0], 1.53),
    "magenta": ([45.0, 390.0, 95.0], [22.0, 20.0, 18.0], 1.53),
    "yellow":  ([28.0, 55.0, 520.0], [20.0, 18.0, 15.0], 1.53),
}

# white, black, clear, cyan, magenta, yellow
RECIPES = {
    1: [0.02, 0.032, 0.688, 0.00, 0.06, 0.20],
    2: [0.02, 0.020, 0.740, 0.00, 0.045, 0.175],
    3: [0.02, 0.008, 0.802, 0.00, 0.03, 0.14],
    4: [0.01, 0.004, 0.866, 0.00, 0.02, 0.10],
    5: [0.01, 0.00, 0.91, 0.00, 0.01, 0.07],
    6: [0.03, 0.24, 0.31, 0.02, 0.20, 0.20],
    7: [0.01, 0.00, 0.96, 0.00, 0.00, 0.03],
    8: [0.03, 0.176, 0.344, 0.01, 0.20, 0.24],
    9: [0.02, 0.08, 0.44, 0.00, 0.17, 0.29],
    10: [0.02, 0.04, 0.51, 0.00, 0.12, 0.31],
}


def effective(recipe: list[float]) -> tuple[list[float], list[float], float]:
    names = ("white", "black", "clear", "cyan", "magenta", "yellow")
    weights = np.asarray(recipe, dtype=np.float64)
    assert np.isclose(weights.sum(), 1.0)
    absorption = sum(weights[i] * np.asarray(BASE[name][0]) for i, name in enumerate(names))
    scattering = sum(weights[i] * np.asarray(BASE[name][1]) for i, name in enumerate(names))
    ior = sum(weights[i] * BASE[name][2] for i, name in enumerate(names))
    return absorption.tolist(), scattering.tolist(), float(ior)


def main() -> None:
    mapping = json.loads(SOURCE.read_text(encoding="utf-8"))
    mapping["configuration_id"] = "amber-branching-vero6-print-preview-v1"
    mapping["calibration_status"] = "provisional-uncalibrated"
    for material in mapping["materials"]:
        material_id = int(material["material_id"])
        if material_id == 0:
            continue
        absorption, scattering, ior = effective(RECIPES[material_id])
        material["sigma_a_rgb_per_m"] = [round(v, 6) for v in absorption]
        material["sigma_s_rgb_per_m"] = [round(v, 6) for v in scattering]
        material["ior"] = round(ior, 6)
        material["g"] = 0.02
    OUTPUT.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
