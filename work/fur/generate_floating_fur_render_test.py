from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / ".local" / "floating-fur" / "source" / "floating-fur-v1.material_id.npy"
OUT = ROOT / ".local" / "floating-fur-render-test" / "source"
NAME = "floating-fur-render-test-v1"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shift(mask: np.ndarray, dz: int, dy: int, dx: int) -> np.ndarray:
    out = np.zeros_like(mask)
    z0, z1 = max(0, dz), mask.shape[0] + min(0, dz)
    y0, y1 = max(0, dy), mask.shape[1] + min(0, dy)
    x0, x1 = max(0, dx), mask.shape[2] + min(0, dx)
    out[z0:z1, y0:y1, x0:x1] = mask[z0-dz:z1-dz, y0-dy:y1-dy, x0-dx:x1-dx]
    return out


def main() -> None:
    original = np.load(SOURCE, allow_pickle=False)
    labels = np.ones_like(original, dtype=np.uint16)
    hair = original >= 2
    dark = original >= 6

    # Render-only connected fiber cores. Fill one-voxel gaps along the dominant
    # X flow, then broaden laterally so hairs behave as continuous optical paths
    # rather than isolated point samples at the 0.2 mm review resolution.
    bridge_x = shift(hair, 0, 0, -1) & shift(hair, 0, 0, 1)
    core = hair | bridge_x
    core |= shift(core, 0, 1, 0) | shift(core, 0, -1, 0)

    # Thin milky undercoat around the bundles. It is deliberately weaker than
    # the fiber core and remains inside the original 0.6 mm clear envelope.
    halo = core.copy()
    for offset in ((0, 1, 0), (0, -1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)):
        halo |= shift(core, *offset)
    halo &= ~core
    halo[:3] = False
    halo[-3:] = False
    halo[:, :3] = False
    halo[:, -3:] = False
    halo[:, :, :3] = False
    halo[:, :, -3:] = False

    labels[halo] = 2                    # translucent milky undercoat
    labels[core] = 3                    # high-scattering white fiber core
    dark_core = dark | (shift(dark, 0, 0, -1) & core) | (shift(dark, 0, 0, 1) & core)
    labels[dark_core] = 4               # stronger black, same strand population

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    array_path = OUT / f"{NAME}.material_id.npy"
    np.save(array_path, labels, allow_pickle=False)

    materials = [
        {"material_id": 0, "name": "air", "role": "background"},
        {"material_id": 1, "name": "clear-slab", "role": "material"},
        {"material_id": 2, "name": "render-test-milky-undercoat", "role": "material"},
        {"material_id": 3, "name": "render-test-white-fiber", "role": "material"},
        {"material_id": 4, "name": "render-test-black-fiber", "role": "material"},
    ]
    manifest = {
        "format": "vdbmat.voxels", "format_version": "1.0.0", "asset_type": "material-label",
        "payload": {"path": array_path.name, "sha256": digest(array_path), "dtype": "uint16", "dimensions": ["z", "y", "x"]},
        "shape_zyx": list(labels.shape), "voxel_size_xyz_m": [0.0002, 0.0002, 0.0002],
        "local_to_world": np.eye(4).tolist(), "materials": materials,
        "source": {
            "generator": "pj-voxel3dprint.floating-fur-render-test", "generator_version": "1.0.0",
            "notes": "Temporary max-depth-64 visibility study. Original floating_fur source remains unchanged. Connected fiber cores, milky halo, and deliberately amplified optical contrast are render-only approximations."
        },
    }
    manifest_path = OUT / f"{NAME}.voxels.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    mapping = {
        "format": "vdbmat.optical-mapping", "format_version": "1.0.0",
        "configuration_id": "floating-fur-render-visibility-test-v1", "version": "1.0.0",
        "optical_basis": {"kind": "rgb", "identifier": "linear-srgb-effective-v1", "coordinates": ["R", "G", "B"], "reference_white": "D65", "observer": "CIE-1931-2deg", "transfer": "linear"},
        "mixing_rule": "linear-volume-fraction-v1", "calibration_status": "provisional-uncalibrated",
        "materials": [
            {"material_id": 0, "name": "air", "sigma_a_rgb_per_m": [0, 0, 0], "sigma_s_rgb_per_m": [0, 0, 0], "g": 0.0, "ior": 1.0},
            {"material_id": 1, "name": "clear-slab", "sigma_a_rgb_per_m": [1.2, 1.5, 2.6], "sigma_s_rgb_per_m": [0.8, 0.8, 0.8], "g": 0.02, "ior": 1.52},
            {"material_id": 2, "name": "render-test-milky-undercoat", "sigma_a_rgb_per_m": [5, 5, 6], "sigma_s_rgb_per_m": [1400, 1400, 1400], "g": 0.42, "ior": 1.525},
            {"material_id": 3, "name": "render-test-white-fiber", "sigma_a_rgb_per_m": [8, 8, 9], "sigma_s_rgb_per_m": [6200, 6200, 6200], "g": 0.58, "ior": 1.53},
            {"material_id": 4, "name": "render-test-black-fiber", "sigma_a_rgb_per_m": [1600, 1600, 1700], "sigma_s_rgb_per_m": [260, 260, 260], "g": 0.35, "ior": 1.535},
        ],
    }
    mapping_path = OUT / f"{NAME}.optical-mapping.json"
    mapping_path.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    stats = {"counts": {str(i): int(np.count_nonzero(labels == i)) for i in np.unique(labels)}, "render_test_only": True}
    (OUT / f"{NAME}.stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)
    print(mapping_path)
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
