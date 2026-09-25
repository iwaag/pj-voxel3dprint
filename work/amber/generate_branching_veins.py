from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from vdbmat.core import MaterialDefinition, MaterialPalette, MaterialRole, Provenance
from vdbmat.io import read_material_label_manifest
from vdbmat_utils.core import build_material_label_volume
from vdbmat_utils.io import write_asset


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / ".local" / "amber-previews" / "source" / "seed-4102"
SOURCE_MANIFEST = SOURCE_DIR / "amber-4102.voxels.json"
SOURCE_MAPPING = SOURCE_DIR / "amber-4102.optical-mapping.json"
OUT_DIR = ROOT / ".local" / "amber-branching" / "source"
NAME = "amber-4102-branching-v2"
SEED = 42120


def smooth_random(rng: np.random.Generator, length: int, controls: int = 16) -> np.ndarray:
    xp = np.linspace(0.0, length - 1.0, controls)
    values = rng.normal(0.0, 1.0, controls)
    return np.interp(np.arange(length), xp, values)


def main() -> None:
    rng = np.random.default_rng(SEED)
    source = read_material_label_manifest(SOURCE_MANIFEST)
    labels = np.asarray(source.material_id, dtype=np.uint16).copy()
    nz, ny, nx = labels.shape

    # Remove the old four veins while retaining host variation and clear regions.
    old_vein = labels == 6
    host_choices = np.asarray([1, 2, 3, 4, 5], dtype=np.uint16)
    host_weights = np.asarray([0.04, 0.30, 0.35, 0.25, 0.06])
    labels[old_vein] = rng.choice(host_choices, old_vein.sum(), p=host_weights)
    clear_mask = labels == 7

    x = np.arange(nx, dtype=np.float64)
    z = np.arange(nz, dtype=np.float64)[:, None]
    vein_centres: list[np.ndarray] = []
    vein_widths: list[np.ndarray] = []
    tone_fields: list[np.ndarray] = []

    # Twenty long, independently warped veins. At 0.20 mm preview resolution,
    # widths of 1..4 cells represent the requested 0.1..0.8 mm range as closely
    # as the comparison grid permits.
    bases = np.linspace(4.0, ny - 5.0, 20)
    for index, base in enumerate(bases):
        phase = rng.uniform(0.0, 2.0 * np.pi)
        wave = rng.uniform(1.0, 3.3) * np.sin(x / rng.uniform(17.0, 44.0) + phase)
        fine = smooth_random(rng, nx, controls=rng.integers(18, 30)) * rng.uniform(0.5, 1.5)
        centre = base + wave + fine
        width_noise = smooth_random(rng, nx, controls=22)
        width = np.clip(rng.uniform(0.55, 1.55) + 0.35 * width_noise, 0.5, 2.2)
        tone = smooth_random(rng, nx, controls=28) + 0.45 * np.sin(x / 11.0 + phase)
        vein_centres.append(centre)
        vein_widths.append(width)
        tone_fields.append(tone)

        z_tilt = (z - (nz - 1) / 2.0) * rng.uniform(-0.045, 0.045)
        centre_zyx = centre[None, :] + z_tilt
        for xi in range(nx):
            radius = 0.5 * width[xi]
            y0 = np.floor(centre_zyx[:, xi] - radius).astype(int)
            y1 = np.ceil(centre_zyx[:, xi] + radius).astype(int)
            tone_base = int(np.clip(np.searchsorted([-0.65, 0.0, 0.65], tone[xi]), 0, 3))
            for zi in range(nz):
                lo, hi = max(0, y0[zi]), min(ny - 1, y1[zi])
                if lo > hi:
                    continue
                candidates = np.arange(lo, hi + 1)
                distances = np.abs(candidates - centre_zyx[zi, xi])
                ys = candidates[distances <= radius]
                if ys.size == 0:
                    ys = np.asarray([int(np.clip(round(centre_zyx[zi, xi]), 0, ny - 1))])
                edge = np.abs(ys - centre_zyx[zi, xi]) / max(radius, 0.25)
                # Darker core, lighter edge, plus a slowly changing longitudinal tone.
                ids = np.asarray([6, 8, 9, 10], dtype=np.uint16)
                tone_index = np.clip(tone_base + (edge > 0.65).astype(int), 0, 3)
                labels[zi, ys, xi] = ids[tone_index]

    # Curved local branches between neighbouring veins. Each connector exists
    # only over a limited X interval and rejoins a main vein, producing a network
    # instead of full-domain cross bands.
    for _ in range(42):
        lower = int(rng.integers(0, 19))
        upper = lower + 1
        start = int(rng.integers(5, nx - 55))
        length = int(rng.integers(18, 55))
        end = min(nx - 1, start + length)
        xs = np.arange(start, end + 1)
        t = np.linspace(0.0, 1.0, len(xs))
        if rng.random() < 0.5:
            a, b = lower, upper
        else:
            a, b = upper, lower
        ya = vein_centres[a][start]
        yb = vein_centres[b][end]
        curve = ya * (1.0 - t) + yb * t + np.sin(np.pi * t) * rng.uniform(-1.8, 1.8)
        branch_tone = int(rng.integers(1, 4))
        branch_id = np.uint16([6, 8, 9, 10][branch_tone])
        half_width = rng.uniform(0.20, 0.48)
        z_mid = rng.uniform(0.25 * nz, 0.75 * nz)
        z_radius = rng.uniform(0.28 * nz, 0.55 * nz)
        for xi, cy in zip(xs, curve, strict=True):
            for zi in range(nz):
                if abs(zi - z_mid) > z_radius:
                    continue
                candidates = np.arange(max(0, int(np.floor(cy - 0.6))), min(ny - 1, int(np.ceil(cy + 0.6))) + 1)
                ys = candidates[np.abs(candidates - cy) <= half_width]
                if ys.size == 0:
                    ys = np.asarray([int(np.clip(round(cy), 0, ny - 1))])
                labels[zi, ys, xi] = branch_id

    # Clear regions remain the top-priority material, matching the original model.
    labels[clear_mask] = 7

    palette = MaterialPalette.from_sequence(
        tuple(source.palette.materials)
        + (
            MaterialDefinition(8, "amber-vein-deep-brown", MaterialRole.MATERIAL),
            MaterialDefinition(9, "amber-vein-warm-brown", MaterialRole.MATERIAL),
            MaterialDefinition(10, "amber-vein-golden-brown", MaterialRole.MATERIAL),
        )
    )
    source_digest = hashlib.sha256(SOURCE_MANIFEST.read_bytes()).hexdigest()
    provenance = Provenance(
        generator="pj-voxel3dprint.branching-amber-veins",
        generator_version="1.0.0",
        sources=(f"sha256:{source_digest}", f"seed:{SEED}"),
        notes="Twenty X-direction veins with local branches and four brown optical classes; host and clear-region labels inherited from amber-4102.",
    )
    volume = build_material_label_volume(
        material_id=labels,
        voxel_size_xyz_m=source.geometry.voxel_size_xyz_m,
        palette=palette,
        provenance=provenance,
        local_to_world=source.geometry.local_to_world,
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = write_asset(volume, OUT_DIR, NAME)

    mapping = json.loads(SOURCE_MAPPING.read_text(encoding="utf-8"))
    mapping["configuration_id"] = "amber-branching-veins-v1"
    mapping["materials"].extend(
        [
            {"material_id": 8, "name": "amber-vein-deep-brown", "sigma_a_rgb_per_m": [72.0, 138.0, 278.0], "sigma_s_rgb_per_m": [25.0, 21.0, 18.0], "g": 0.02, "ior": 1.56},
            {"material_id": 9, "name": "amber-vein-warm-brown", "sigma_a_rgb_per_m": [56.0, 104.0, 210.0], "sigma_s_rgb_per_m": [21.0, 18.0, 15.0], "g": 0.02, "ior": 1.555},
            {"material_id": 10, "name": "amber-vein-golden-brown", "sigma_a_rgb_per_m": [41.0, 76.0, 151.0], "sigma_s_rgb_per_m": [17.0, 15.0, 12.0], "g": 0.02, "ior": 1.55},
        ]
    )
    mapping_path = OUT_DIR / f"{NAME}.optical-mapping.json"
    mapping_path.write_text(json.dumps(mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    counts = {int(mid): int(np.count_nonzero(labels == mid)) for mid in np.unique(labels)}
    stats = {
        "seed": SEED,
        "shape_zyx": list(labels.shape),
        "voxel_size_xyz_m": list(source.geometry.voxel_size_xyz_m),
        "main_veins": 20,
        "branch_connectors": 42,
        "material_counts": counts,
        "vein_fraction": sum(counts.get(mid, 0) for mid in (6, 8, 9, 10)) / labels.size,
        "clear_region_fraction": counts.get(7, 0) / labels.size,
    }
    (OUT_DIR / f"{NAME}.stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(manifest)
    print(mapping_path)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
