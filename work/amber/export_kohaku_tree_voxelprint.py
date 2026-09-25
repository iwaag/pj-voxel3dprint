from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / ".local" / "amber-branching" / "source" / "amber-4102-branching-v2.material_id.npy"
SOURCE_MANIFEST = ROOT / ".local" / "amber-branching" / "source" / "amber-4102-branching-v2.voxels.json"
OUT = ROOT / "work" / "amber" / "kohaku_tree_voxelprint_staging"
NAME = "kohaku_tree"
SEED = np.uint32(20260901)

PITCH_X_M = 0.0254 / 600.0
PITCH_Y_M = 0.0254 / 300.0
PITCH_Z_M = 0.014e-3
EXTENT_X_M, EXTENT_Y_M, EXTENT_Z_M = 0.060, 0.030, 0.005
SRC_VOXEL_M = 0.0002

# Palette index 0 is reserved for background. The six printable colors are the
# official Vero base-resin RGB identifiers from Stratasys' voxel-print guide.
RESINS = [
    ("VeroPureWht", (240, 240, 240)),
    ("VeroBlack_or_VeroFlexBK", (26, 26, 29)),
    ("VeroClear_or_VeroFlexCLR", (227, 233, 253)),
    ("VeroCyan_or_VeroFlexCY", (0, 90, 158)),
    ("VeroMgnt_or_VeroFlexMGT", (166, 33, 98)),
    ("VeroYellow_or_VeroFlexYL", (200, 189, 3)),
]

# white, black, clear, cyan, magenta, yellow. Black is 80% of the initial
# print-preview recipe; the removed share is transferred to Clear.
RECIPES = {
    1: [0.020, 0.032, 0.688, 0.000, 0.060, 0.200],
    2: [0.020, 0.020, 0.740, 0.000, 0.045, 0.175],
    3: [0.020, 0.008, 0.802, 0.000, 0.030, 0.140],
    4: [0.010, 0.004, 0.866, 0.000, 0.020, 0.100],
    5: [0.010, 0.000, 0.910, 0.000, 0.010, 0.070],
    6: [0.030, 0.240, 0.310, 0.020, 0.200, 0.200],
    7: [0.010, 0.000, 0.960, 0.000, 0.000, 0.030],
    8: [0.030, 0.176, 0.344, 0.010, 0.200, 0.240],
    9: [0.020, 0.080, 0.440, 0.000, 0.170, 0.290],
    10: [0.020, 0.040, 0.510, 0.000, 0.120, 0.310],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_uniform(x: np.ndarray, y: np.ndarray, z: int) -> np.ndarray:
    """Return deterministic decorrelated [0,1) values for printer voxels."""
    h = (
        x.astype(np.uint32) * np.uint32(0x9E3779B1)
        ^ y.astype(np.uint32) * np.uint32(0x85EBCA77)
        ^ np.uint32(z) * np.uint32(0xC2B2AE3D)
        ^ SEED
    )
    h ^= h >> np.uint32(16)
    h *= np.uint32(0x7FEB352D)
    h ^= h >> np.uint32(15)
    h *= np.uint32(0x846CA68B)
    h ^= h >> np.uint32(16)
    return (h.astype(np.float64) + 0.5) / 4294967296.0


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    source = np.load(SOURCE, mmap_mode="r")
    width = math.ceil(EXTENT_X_M / PITCH_X_M - 1e-6)
    height = math.ceil(EXTENT_Y_M / PITCH_Y_M - 1e-6)
    slices = math.ceil(EXTENT_Z_M / PITCH_Z_M - 1e-6)

    src_x = np.clip(np.floor((np.arange(width) + 0.5) * PITCH_X_M / SRC_VOXEL_M), 0, source.shape[2] - 1).astype(np.intp)
    src_y = np.clip(np.floor((np.arange(height) + 0.5) * PITCH_Y_M / SRC_VOXEL_M), 0, source.shape[1] - 1).astype(np.intp)
    src_z = np.clip(np.floor((np.arange(slices) + 0.5) * PITCH_Z_M / SRC_VOXEL_M), 0, source.shape[0] - 1).astype(np.intp)
    grid_x = np.broadcast_to(np.arange(width, dtype=np.uint32)[None, :], (height, width))
    grid_y = np.broadcast_to(np.arange(height, dtype=np.uint32)[:, None], (height, width))

    rgba_lut = np.asarray([(0, 0, 0, 0), *((*rgb, 255) for _, rgb in RESINS)], dtype=np.uint8)

    cumulative = {material_id: np.cumsum(np.asarray(recipe, dtype=np.float64)) for material_id, recipe in RECIPES.items()}
    counts = np.zeros(7, dtype=np.int64)
    records: list[dict[str, object]] = []
    for zi, source_zi in enumerate(src_z):
        semantic = np.asarray(source[source_zi])[np.ix_(src_y, src_x)]
        uniform = hash_uniform(grid_x, grid_y, zi)
        indices = np.zeros((height, width), dtype=np.uint8)
        for material_id, thresholds in cumulative.items():
            mask = semantic == material_id
            if not np.any(mask):
                continue
            indices[mask] = np.searchsorted(thresholds, uniform[mask], side="right").astype(np.uint8) + 1
        if np.any(indices == 0):
            raise RuntimeError(f"unassigned printer voxel in slice {zi}")
        counts += np.bincount(indices.ravel(), minlength=7)
        filename = f"slice_{zi:04d}.png"
        path = OUT / filename
        image = Image.fromarray(rgba_lut[indices], mode="RGBA")
        image.save(path, format="PNG", optimize=False, compress_level=9)
        with Image.open(path) as check:
            if check.mode != "RGBA" or np.any(np.asarray(check)[..., 3] != 255):
                raise RuntimeError(f"invalid 32-bit RGBA encoding in {filename}")
        records.append({"file": filename, "sha256": sha256(path)})

    source_doc = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    manifest = {
        "format": "vdbmat.print-slices",
        "format_version": "1.0.0",
        "name": NAME,
        "source": {
            "manifest": SOURCE_MANIFEST.name,
            "manifest_sha256": sha256(SOURCE_MANIFEST),
            "payload_sha256": source_doc["payload"]["sha256"],
        },
        "printer": {
            "profile": "Stratasys J750 PNG method High Quality",
            "dpi_x": 600.0,
            "dpi_y": 300.0,
            "pitch_x_mm": PITCH_X_M * 1000.0,
            "pitch_y_mm": PITCH_Y_M * 1000.0,
            "layer_thickness_mm": PITCH_Z_M * 1000.0,
        },
        "grid": {
            "width_px": width,
            "height_px": height,
            "slice_count": slices,
            "physical_mm": {
                "x": width * PITCH_X_M * 1000.0,
                "y": height * PITCH_Y_M * 1000.0,
                "z": slices * PITCH_Z_M * 1000.0,
            },
            "axis_mapping": {"columns": "+X", "rows": "+Y", "stack": "+Z"},
        },
        "palette": {
            str(index): {"material": name, "rgb": list(rgb), "voxel_count": int(counts[index])}
            for index, (name, rgb) in enumerate(RESINS, start=1)
        },
        "background_rgb": [0, 0, 0],
        "background_voxel_count": int(counts[0]),
        "halftone": {
            "method": "deterministic-3d-hash",
            "seed": int(SEED),
            "recipe": "amber-branching-vero6-black-minus20-v1",
            "black_reduction": 0.20,
            "removed_black_transferred_to": "VeroClear_or_VeroFlexCLR",
        },
        "slices": records,
    }
    (OUT / f"{NAME}.printslices.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUT / f"{NAME}.resin-recipes.json").write_text(
        json.dumps({"resin_order": [name for name, _ in RESINS], "recipes_by_source_material_id": RECIPES}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(OUT), "width": width, "height": height, "slices": slices, "counts": counts.tolist()}))


if __name__ == "__main__":
    main()
