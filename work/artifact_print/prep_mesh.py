"""Scan GLB -> scaled, upright, vertex-merged STL for voxelize-mesh (artifact_print p1 step 6).

glTF is +Y up; the voxel volume is z-up, so (x, y, z)_gltf -> (x, -z, y). The mesh is
scaled so its longest side is --longest-mm and translated to start at the origin.
Writes OUT.stl (mm) and OUT.transform.json (4x4 from GLB units to mm, for colour lookup
against the original textured mesh).

Usage: venv/bin/python work/artifact_print/prep_mesh.py MESH.glb OUT_STEM --longest-mm 60
"""
import argparse, json
from pathlib import Path

import numpy as np
import trimesh

UP = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mesh")
    ap.add_argument("out_stem")
    ap.add_argument("--longest-mm", type=float, required=True)
    a = ap.parse_args()
    scene = trimesh.load(a.mesh, force="scene", process=False)
    m = trimesh.util.concatenate(list(scene.dump()))
    m = trimesh.Trimesh(m.vertices, m.faces, process=False)
    m.merge_vertices(merge_tex=True, merge_norm=True)
    m.remove_unreferenced_vertices()
    m.apply_transform(UP)
    s = a.longest_mm / (m.bounds[1] - m.bounds[0]).max()
    T = np.diag([s, s, s, 1.0])
    T[:3, 3] = -m.bounds[0] * s
    m.apply_transform(T)
    full = T @ UP
    info = {
        "source": a.mesh, "longest_mm": a.longest_mm, "scale": s,
        "extent_mm": (m.bounds[1] - m.bounds[0]).round(3).tolist(),
        "watertight": bool(m.is_watertight), "winding_consistent": bool(m.is_winding_consistent),
        "components": len(m.split(only_watertight=False)),
        "volume_mm3": float(m.volume) if m.is_watertight else None,
        "area_mm2": float(m.area),
        # for a closed thin shell (inner + outer skin) volume ~ (area / 2) * wall
        "wall_estimate_mm": float(2 * m.volume / m.area) if m.is_watertight else None,
        "gltf_to_mm": full.tolist(),
    }
    out = Path(a.out_stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    m.export(out.with_suffix(".stl"))
    out.with_suffix(".transform.json").write_text(json.dumps(info, indent=1) + "\n")
    print(json.dumps({k: v for k, v in info.items() if k != "gltf_to_mm"}))


if __name__ == "__main__":
    main()
