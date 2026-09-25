from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".local" / "pink-agate-v3" / "source"
NAME = "pink-teal-agate-strata-v3"
SEED = 104729
VOXEL_M = 0.0002
SHAPE_ZYX = (25, 150, 300)  # 5 x 30 x 60 mm review grid

# white, black, clear, cyan, magenta, yellow
RECIPES = {
    1: [0.00, 0.00, 1.00, 0.00, 0.00, 0.00],  # clear shell
    2: [0.22, 0.00, 0.45, 0.00, 0.27, 0.06],  # saturated pale pink, near #e6c5e1
    3: [0.12, 0.01, 0.38, 0.01, 0.38, 0.10],  # dusty rose
    4: [0.10, 0.02, 0.40, 0.08, 0.34, 0.06],  # mauve
    5: [0.14, 0.01, 0.43, 0.18, 0.21, 0.03],  # lavender
    6: [0.08, 0.03, 0.40, 0.30, 0.15, 0.04],  # blue-grey transition
    7: [0.04, 0.04, 0.35, 0.48, 0.06, 0.03],  # teal, near #0f6d75
    8: [0.02, 0.10, 0.28, 0.53, 0.04, 0.03],  # deep teal accent
    9: [0.68, 0.00, 0.29, 0.00, 0.02, 0.01],  # white
    10: [0.38, 0.00, 0.56, 0.01, 0.03, 0.02], # milky white
    11: [0.12, 0.06, 0.48, 0.01, 0.09, 0.24], # light tan
    12: [0.02, 0.22, 0.70, 0.03, 0.02, 0.01], # translucent black
    13: [0.01, 0.00, 0.99, 0.00, 0.00, 0.00], # occasional clear band
    14: [0.03, 0.25, 0.46, 0.18, 0.06, 0.02], # smoky blue-black
}

MATERIALS = [
    (0, "air", "background"),
    (1, "agate-clear-shell", "material"),
    (2, "agate-pale-pink-e6c5e1", "material"),
    (3, "agate-dusty-rose", "material"),
    (4, "agate-mauve", "material"),
    (5, "agate-lavender", "material"),
    (6, "agate-blue-grey", "material"),
    (7, "agate-teal-0f6d75", "material"),
    (8, "agate-deep-teal", "material"),
    (9, "agate-white", "material"),
    (10, "agate-milky-white", "material"),
    (11, "agate-light-tan", "material"),
    (12, "agate-translucent-black", "material"),
    (13, "agate-clear-band", "material"),
    (14, "agate-smoky-blue-black", "material"),
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
    absorption = sum(w[i] * np.asarray(BASE[name][0]) for i, name in enumerate(names))
    scattering = sum(w[i] * np.asarray(BASE[name][1]) for i, name in enumerate(names))
    ior = sum(w[i] * BASE[name][2] for i, name in enumerate(names))
    return absorption.tolist(), scattering.tolist(), float(ior)


def main() -> None:
    rng = np.random.default_rng(SEED)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    nz, ny, nx = SHAPE_ZYX
    z = (np.arange(nz) + 0.5) * 0.2
    y = (np.arange(ny) + 0.5) * 0.2
    x = (np.arange(nx) + 0.5) * 0.2
    zz, yy, xx = np.meshgrid(z, y, x, indexing="ij")

    # Several moving, anisotropic growth nuclei produce contours that are
    # deliberately non-circular.  Angular harmonics and XY cross-coupling make
    # each "year" drift sideways instead of remaining a scaled copy.
    centres = [
        (5.5, 6.0, 0.88, 1.35, 0.0, 0.22),
        (25.0, 34.0, 1.28, 0.82, 1.6, -0.19),
        (52.0, 9.0, 1.16, 0.76, 3.1, 0.16),
        (38.0, -9.0, 0.72, 1.42, 4.7, -0.24),
        (65.0, 32.0, 1.34, 0.90, 2.4, 0.20),
    ]
    distances = []
    for cx, cy, sx, sy, offset, shear in centres:
        dx = xx - cx
        dy = yy - cy
        u = dx / sx + shear * dy
        v = dy / sy - 0.11 * np.sin(dx * 0.16 + offset) * dx
        radial = (np.abs(u) ** 2.35 + np.abs(v) ** 2.35) ** (1.0 / 2.35)
        angular = np.arctan2(v, u)
        drift = 0.48 * np.sin(0.17 * radial + angular + offset)
        lobes = 0.38 * np.sin(0.55 * radial + 2.0 * angular + offset)
        ripples = 0.16 * np.sin(1.37 * radial + 5.0 * angular - offset)
        distances.append(radial + drift + lobes + ripples)

    distance_stack = np.stack(distances, axis=0)
    nearest_two = np.partition(distance_stack, 1, axis=0)[:2]
    field = nearest_two[0]
    # Pull neighbouring contour systems together near their bisectors.  This
    # yields Y/V mergers and reconnections instead of a clean circular Voronoi seam.
    gap = nearest_two[1] - nearest_two[0]
    field -= 0.34 * np.exp(-((gap / 0.75) ** 2)) * np.sin((xx + 1.7 * yy) * 0.19)

    # Multi-octave deterministic deformation gives fractal-like wave disorder.
    warp = (
        0.36 * np.sin(xx * 0.29 + yy * 0.43 + zz * 0.08)
        + 0.19 * np.sin(xx * 0.81 - yy * 0.57 + zz * 0.13)
        + 0.085 * np.sin(xx * 2.37 + yy * 1.91 - zz * 0.20)
        + 0.14 * np.sin((xx * yy) * 0.018 + zz * 0.05)
    )
    field = field + warp

    # Local phase offsets create discontinuities and later reconnections.
    phase_jump = np.zeros_like(field)
    phase_jump[(xx > 18) & (xx < 32) & (yy > 8) & (yy < 19)] += 0.42
    phase_jump[(xx > 39) & (xx < 48) & (yy > 16) & (yy < 27)] -= 0.31
    field += phase_jump * (0.5 + 0.5 * np.sin((xx + yy) * 0.22))

    # 0.16..0.28 mm nominal review strata.  Dense/dark material is selected by
    # contour phase (a run of "years"), never by a filled spatial ellipse.  The
    # result is a biased layer stack that follows and rejoins the growth lines.
    spacing = 0.22 + 0.045 * np.sin(field * 0.21 + xx * 0.08 - yy * 0.05)
    spacing += 0.018 * np.sin(xx * 0.31 + yy * 0.17)
    spacing = np.clip(spacing, 0.16, 0.28)
    band = np.floor(field / spacing).astype(np.int32)

    # Pink -> mauve -> blue -> teal hue travel. A low-frequency displacement
    # shifts that travel locally, so adjacent contour systems do not repeat the
    # same palette in lockstep.
    hue_palette = np.asarray([2, 3, 4, 5, 6, 7, 8, 7, 6, 5, 4, 3], dtype=np.uint16)
    hue_shift = np.floor(
        2.4 * np.sin(xx * 0.11 - yy * 0.07 + zz * 0.05)
        + 1.6 * np.sin(xx * 0.037 + yy * 0.13)
    ).astype(np.int32)
    labels = hue_palette[np.mod(np.floor_divide(band, 2) + hue_shift, len(hue_palette))]

    # Mineral strata interrupt the hue gradient. They form long contour-following
    # sequences, with locally uneven widths like sediment or tree-ring density.
    phase = np.mod(band + np.floor(2.0 * np.sin(xx * 0.055 + yy * 0.09)).astype(np.int32), 43)
    labels[np.isin(phase, [3, 19, 35])] = 9
    labels[np.isin(phase, [4, 20, 21, 36])] = 10
    labels[np.isin(phase, [10, 11, 27])] = 11
    labels[np.isin(phase, [12, 28])] = 12
    labels[np.isin(phase, [13, 29])] = 14
    labels[np.isin(phase, [14, 30])] = 8
    labels[np.isin(phase, [7, 24, 40])] = 13

    # Short interruptions erase selected line segments into their pale neighbour.
    interruptions = (
        (np.sin(xx * 0.31 + yy * 0.19 + zz * 0.10) > 0.985)
        & (np.sin(xx * 0.77 - yy * 0.51) > 0.72)
    )
    labels[interruptions & np.isin(labels, [3, 4, 6, 7, 8, 12, 14])] = 10

    # Sparse crystalline specks, biased to white/milky bands.
    speckle = rng.random(labels.shape)
    labels[(speckle < 0.006) & np.isin(labels, [9, 10, 11])] = 9

    # Agate bands are a coherent mineral cross-section through the 5 mm slab,
    # not dozens of alternating laminations along the viewing/thickness axis.
    # Extruding the middle section preserves the complex XY strata while keeping
    # a normal depth-8 ray path physically meaningful and interactive.
    labels = np.broadcast_to(labels[nz // 2 : nz // 2 + 1], labels.shape).copy()

    # Transparent membrane over all six faces. At the 0.20 mm review grid this
    # is quantized to 0.2/0.4 mm; print-grid export uses the exact 0.3 mm intent.
    face_distance = np.minimum.reduce([xx, 60.0 - xx, yy, 30.0 - yy, zz, 5.0 - zz])
    labels[face_distance <= 0.30] = 1

    array_path = OUT / f"{NAME}.material_id.npy"
    np.save(array_path, labels.astype(np.uint16), allow_pickle=False)
    manifest = {
        "format": "vdbmat.voxels",
        "format_version": "1.0.0",
        "asset_type": "material-label",
        "payload": {"path": array_path.name, "sha256": digest(array_path), "dtype": "uint16", "dimensions": ["z", "y", "x"]},
        "shape_zyx": list(SHAPE_ZYX),
        "voxel_size_xyz_m": [VOXEL_M, VOXEL_M, VOXEL_M],
        "local_to_world": np.eye(4).tolist(),
        "materials": [{"material_id": mid, "name": name, "role": role} for mid, name, role in MATERIALS],
        "source": {
            "generator": "pj-voxel3dprint.multicenter-agate",
            "generator_version": "3.0.0",
            "notes": "Pink-to-teal multi-nucleus agate with a 0.3 mm clear membrane, non-circular drifting contours, discontinuous fractal warps, mergers, and contour-phase-biased mineral/dark strata.",
        },
    }
    manifest_path = OUT / f"{NAME}.voxels.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    mapping_materials = [{"material_id": 0, "name": "air", "sigma_a_rgb_per_m": [0, 0, 0], "sigma_s_rgb_per_m": [0, 0, 0], "g": 0.0, "ior": 1.0}]
    for mid, name, _ in MATERIALS[1:]:
        absorption, scattering, ior = effective(RECIPES[mid])
        mapping_materials.append({
            "material_id": mid,
            "name": name,
            "sigma_a_rgb_per_m": [round(v, 6) for v in absorption],
            "sigma_s_rgb_per_m": [round(v, 6) for v in scattering],
            "g": 0.02,
            "ior": round(ior, 6),
        })
    mapping = {
        "format": "vdbmat.optical-mapping",
        "format_version": "1.0.0",
        "configuration_id": "pink-teal-agate-vero6-print-preview-v3",
        "version": "3.0.0",
        "optical_basis": {"kind": "rgb", "identifier": "linear-srgb-effective-v1", "coordinates": ["R", "G", "B"], "reference_white": "D65", "observer": "CIE-1931-2deg", "transfer": "linear"},
        "mixing_rule": "linear-volume-fraction-v1",
        "calibration_status": "provisional-uncalibrated",
        "materials": mapping_materials,
    }
    mapping_path = OUT / f"{NAME}.optical-mapping.json"
    mapping_path.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    stats = {"seed": SEED, "shape_zyx": list(SHAPE_ZYX), "counts": {str(mid): int(np.count_nonzero(labels == mid)) for mid in np.unique(labels)}}
    (OUT / f"{NAME}.stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)
    print(mapping_path)
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
