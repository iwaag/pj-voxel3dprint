from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".local" / "floating-fur" / "source"
NAME = "floating-fur-v1"
SEED = 77171
VOXEL_MM = 0.2
VOXEL_M = VOXEL_MM / 1000.0
SHAPE_ZYX = (25, 150, 300)  # 5 x 30 x 60 mm review grid

# VeroPureWhite, Black, Clear, Cyan, Magenta, Yellow
RECIPES = {
    1: [0.00, 0.00, 1.00, 0.00, 0.00, 0.00],
    2: [0.18, 0.00, 0.82, 0.00, 0.00, 0.00],
    3: [0.32, 0.00, 0.68, 0.00, 0.00, 0.00],
    4: [0.48, 0.00, 0.52, 0.00, 0.00, 0.00],
    5: [0.25, 0.015, 0.735, 0.00, 0.00, 0.00],
    6: [0.10, 0.055, 0.845, 0.00, 0.00, 0.00],
    7: [0.06, 0.10, 0.84, 0.00, 0.00, 0.00],
}
MATERIALS = [
    (0, "air", "background"),
    (1, "clear-slab", "material"),
    (2, "fur-translucent-white", "material"),
    (3, "fur-soft-white", "material"),
    (4, "fur-bright-white", "material"),
    (5, "fur-silver-white", "material"),
    (6, "fur-translucent-charcoal", "material"),
    (7, "fur-translucent-black", "material"),
]
BASE = {
    "white": ([15.0, 15.0, 15.0], [520.0, 520.0, 520.0], 1.53),
    "black": ([126.0, 126.0, 134.0], [45.0, 45.0, 45.0], 1.54),
    "clear": ([3.0, 4.0, 8.0], [2.0, 2.0, 2.0], 1.52),
    "cyan": ([220.0, 50.0, 25.0], [18.0, 15.0, 13.0], 1.53),
    "magenta": ([35.0, 200.0, 60.0], [18.0, 16.0, 14.0], 1.53),
    "yellow": ([25.0, 50.0, 250.0], [16.0, 14.0, 12.0], 1.53),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def effective(recipe: list[float]) -> tuple[list[float], list[float], float]:
    names = ("white", "black", "clear", "cyan", "magenta", "yellow")
    w = np.asarray(recipe, dtype=np.float64)
    absorption = sum(w[i] * np.asarray(BASE[n][0]) for i, n in enumerate(names))
    scattering = sum(w[i] * np.asarray(BASE[n][1]) for i, n in enumerate(names))
    ior = sum(w[i] * BASE[n][2] for i, n in enumerate(names))
    return absorption.tolist(), scattering.tolist(), float(ior)


def put_point(labels: np.ndarray, p_xyz: np.ndarray, material_id: int, thick: bool) -> None:
    ix, iy, iz = np.floor(p_xyz / VOXEL_MM).astype(int)
    nz, ny, nx = labels.shape
    if not (0 <= ix < nx and 0 <= iy < ny and 0 <= iz < nz):
        return
    labels[iz, iy, ix] = material_id
    if thick:
        for dz, dy, dx in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            jz, jy, jx = iz + dz, iy + dy, ix + dx
            if 0 <= jx < nx and 0 <= jy < ny and 0 <= jz < nz:
                labels[jz, jy, jx] = material_id


def main() -> None:
    rng = np.random.default_rng(SEED)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    labels = np.ones(SHAPE_ZYX, dtype=np.uint16)  # Entire object is clear resin.

    # A porous, slab-shaped undercoat anchors the individual hairs without
    # becoming a solid opaque insert. It stays at least 0.6 mm off every face.
    nz, ny, nx = SHAPE_ZYX
    zc = (np.arange(nz) + 0.5) * VOXEL_MM
    yc = (np.arange(ny) + 0.5) * VOXEL_MM
    xc = (np.arange(nx) + 0.5) * VOXEL_MM
    zz, yy, xx = np.meshgrid(zc, yc, xc, indexing="ij")
    qx = np.abs((xx - 29.0) / 25.0) ** 6
    qy = np.abs((yy - 15.0) / 10.4) ** 6
    qz = np.abs((zz - 2.5) / 1.35) ** 6
    core = qx + qy + qz < 1.0
    wispy = np.sin(xx * 2.1 + yy * 1.3 + zz * 4.7) + np.sin(xx * 0.43 - yy * 1.8) > 1.25
    labels[core & wispy] = 2

    strand_count = 6800
    dark_count = 0
    face_prob = np.asarray([0.08, 0.08, 0.28, 0.28, 0.14, 0.14])
    face_prob /= face_prob.sum()
    for _ in range(strand_count):
        face = int(rng.choice(6, p=face_prob))
        root = np.array([rng.uniform(5.0, 53.0), rng.uniform(5.0, 25.0), rng.uniform(1.15, 3.85)])
        normal = np.zeros(3)
        if face == 0:
            root[0], normal[0] = rng.uniform(5.0, 8.0), -1.0
        elif face == 1:
            root[0], normal[0] = rng.uniform(50.0, 53.0), 1.0
        elif face == 2:
            root[1], normal[1] = rng.uniform(5.0, 7.0), -1.0
        elif face == 3:
            root[1], normal[1] = rng.uniform(23.0, 25.0), 1.0
        elif face == 4:
            root[2], normal[2] = rng.uniform(1.15, 1.35), -1.0
        else:
            root[2], normal[2] = rng.uniform(3.65, 3.85), 1.0

        # Initial growth follows the local surface normal. The tip bends into
        # the long-axis flow, with coherent waves plus strand-level randomness.
        sign_x = 1.0 if rng.random() < 0.82 else -1.0
        flow = np.array([sign_x, rng.normal(0, 0.34), rng.normal(0, 0.16)])
        flow /= np.linalg.norm(flow)
        length = rng.uniform(0.8, 3.2) if face < 4 else rng.uniform(0.4, 1.0)
        phase = rng.uniform(0, 2 * np.pi)
        nsteps = max(5, int(length / 0.11))
        dark = rng.random() < 0.15
        dark_count += int(dark)
        white_id = int(rng.choice([2, 3, 4, 5], p=[0.18, 0.34, 0.31, 0.17]))
        dark_id = 7 if rng.random() < 0.28 else 6
        material_id = dark_id if dark else white_id
        for i, t in enumerate(np.linspace(0.0, 1.0, nsteps)):
            blend = t * t * (3.0 - 2.0 * t)
            direction = (1.0 - blend) * normal + blend * flow
            transverse = np.array([
                0.11 * np.sin(phase + 5.7 * t),
                0.32 * np.sin(phase + 7.2 * t) + 0.10 * np.sin(phase * 1.7 + 17.0 * t),
                0.13 * np.cos(phase * 0.7 + 8.1 * t),
            ])
            p = root + length * t * direction + transverse
            # Maintain the visible clear gap and keep the complete hair inside.
            p = np.clip(p, [0.65, 0.65, 0.65], [59.35, 29.35, 4.35])
            put_point(labels, p, material_id, thick=(t < 0.08 and i == 0 and rng.random() < 0.35))

    array_path = OUT / f"{NAME}.material_id.npy"
    np.save(array_path, labels, allow_pickle=False)
    manifest = {
        "format": "vdbmat.voxels", "format_version": "1.0.0", "asset_type": "material-label",
        "payload": {"path": array_path.name, "sha256": digest(array_path), "dtype": "uint16", "dimensions": ["z", "y", "x"]},
        "shape_zyx": list(SHAPE_ZYX), "voxel_size_xyz_m": [VOXEL_M] * 3, "local_to_world": np.eye(4).tolist(),
        "materials": [{"material_id": mid, "name": name, "role": role} for mid, name, role in MATERIALS],
        "source": {
            "generator": "pj-voxel3dprint.floating-fur", "generator_version": "1.0.0",
            "notes": "60x30x5 mm clear slab with an internally offset silky fur mass. Hair tips flow mostly along X while roots cover all faces. Design intent: 0.06 mm tips, 0.10-0.16 mm roots, 15% black strands, 0.6 mm surface clearance; the 0.2 mm review grid represents sub-voxel tips with one voxel.",
        },
    }
    manifest_path = OUT / f"{NAME}.voxels.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    mapped = [{"material_id": 0, "name": "air", "sigma_a_rgb_per_m": [0, 0, 0], "sigma_s_rgb_per_m": [0, 0, 0], "g": 0.0, "ior": 1.0}]
    for mid, name, _ in MATERIALS[1:]:
        absorption, scattering, ior = effective(RECIPES[mid])
        mapped.append({"material_id": mid, "name": name, "sigma_a_rgb_per_m": [round(v, 6) for v in absorption], "sigma_s_rgb_per_m": [round(v, 6) for v in scattering], "g": 0.18, "ior": round(ior, 6)})
    mapping = {
        "format": "vdbmat.optical-mapping", "format_version": "1.0.0", "configuration_id": "floating-fur-vero6-preview-v1", "version": "1.0.0",
        "optical_basis": {"kind": "rgb", "identifier": "linear-srgb-effective-v1", "coordinates": ["R", "G", "B"], "reference_white": "D65", "observer": "CIE-1931-2deg", "transfer": "linear"},
        "mixing_rule": "linear-volume-fraction-v1", "calibration_status": "provisional-uncalibrated", "materials": mapped,
    }
    mapping_path = OUT / f"{NAME}.optical-mapping.json"
    mapping_path.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    counts = {str(mid): int(np.count_nonzero(labels == mid)) for mid in np.unique(labels)}
    stats = {"seed": SEED, "shape_zyx": list(SHAPE_ZYX), "strand_count": strand_count, "dark_strand_count": dark_count, "counts": counts}
    (OUT / f"{NAME}.stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)
    print(mapping_path)
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
