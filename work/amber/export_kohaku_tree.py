from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / ".local" / "amber-branching" / "source"
SOURCE_MANIFEST = SOURCE_DIR / "amber-4102-branching-v2.voxels.json"
SOURCE_ARRAY = SOURCE_DIR / "amber-4102-branching-v2.material_id.npy"
BUILD_DIR = ROOT / "work" / "amber" / "kohaku_tree_build"
NAME = "kohaku_tree"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)

    source = np.load(SOURCE_ARRAY, mmap_mode="r")
    # Six printable non-background classes:
    # host light/mid/deep, clearer inclusion, warm vein, deep vein.
    remap = np.array([0, 3, 3, 2, 1, 1, 6, 4, 6, 5, 5], dtype=np.uint16)
    output = remap[source]
    array_path = BUILD_DIR / f"{NAME}.material_id.npy"
    np.save(array_path, output, allow_pickle=False)

    original = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    manifest = {
        **original,
        "payload": {
            **original["payload"],
            "path": array_path.name,
            "sha256": sha256(array_path),
        },
        "materials": [
            {"material_id": 0, "name": "air", "role": "background"},
            {"material_id": 1, "name": "amber-host-light", "role": "material"},
            {"material_id": 2, "name": "amber-host-medium", "role": "material"},
            {"material_id": 3, "name": "amber-host-deep", "role": "material"},
            {"material_id": 4, "name": "amber-clear-inclusion", "role": "material"},
            {"material_id": 5, "name": "amber-vein-warm", "role": "material"},
            {"material_id": 6, "name": "amber-vein-deep", "role": "material"},
        ],
        "source": {
            "generator": "pj-voxel3dprint.stratasys-material-remap",
            "generator_version": "1.0.0",
            "notes": "Six-class print remap of amber-4102-branching-v2; geometry unchanged.",
        },
    }
    manifest_path = BUILD_DIR / f"{NAME}.voxels.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    config = {
        "dpi_x": 600.0,
        "dpi_y": 300.0,
        "layer_thickness_m": 1.4e-05,
        "max_materials": 6,
        "palette": {
            "1": [238, 203, 132],
            "2": [224, 174, 88],
            "3": [205, 143, 56],
            "4": [252, 230, 178],
            "5": [139, 78, 31],
            "6": [82, 40, 20],
        },
        "background_rgb": [0, 0, 0],
        "printer_x_axis": "x",
        "printer_y_axis": "y",
        "flip_x": False,
        "flip_y": False,
        "flip_z": False,
        "name_prefix": "slice_",
        "index_start": 0,
        "min_slices": 30,
        "max_total_pixels": 4000000000,
    }
    config_path = BUILD_DIR / f"{NAME}.printslices-config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)
    print(config_path)


if __name__ == "__main__":
    main()
