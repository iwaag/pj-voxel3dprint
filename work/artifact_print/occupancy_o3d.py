"""Cell-centre occupancy of a watertight STL with Open3D (artifact_print p1 step 6).

Same grid convention as vdbmat-utils voxelize-mesh (AABB + padding cells, cell centres
at origin + (i + 0.5) * pitch), but the inside test is Open3D RaycastingScene
compute_occupancy (Embree ray parity), for a speed/agreement check against the
dense reference voxelizer. Writes a material-label manifest (material 1).

Usage: venv/bin/python work/artifact_print/occupancy_o3d.py MESH.stl OUT_DIR NAME --pitch-mm 0.5 [--padding 1]
"""
import argparse, hashlib, json, math, time
from pathlib import Path

import numpy as np
import open3d as o3d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mesh"); ap.add_argument("out"); ap.add_argument("name")
    ap.add_argument("--pitch-mm", type=float, default=0.5)
    ap.add_argument("--padding", type=int, default=1)
    a = ap.parse_args()
    t0 = time.time()
    mesh = o3d.t.io.read_triangle_mesh(a.mesh)
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(mesh)
    v = mesh.vertex.positions.numpy()
    lo, hi = v.min(0), v.max(0)
    p = a.pitch_mm
    n = [math.ceil((hi[i] - lo[i]) / p - 1e-6) + 2 * a.padding for i in range(3)]
    origin = lo - a.padding * p
    xs, ys, zs = [origin[i] + (np.arange(n[i]) + 0.5) * p for i in range(3)]
    zz, yy, xx = np.meshgrid(zs, ys, xs, indexing="ij")
    q = np.stack([xx, yy, zz], -1).reshape(-1, 3).astype(np.float32)
    occ = scene.compute_occupancy(o3d.core.Tensor(q)).numpy().reshape(n[2], n[1], n[0])
    labels = occ.astype(np.uint16)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    npy = out / f"{a.name}.material_id.npy"
    np.save(npy, labels, allow_pickle=False)
    l2w = np.eye(4); l2w[:3, 3] = origin / 1000
    man = {"format": "vdbmat.voxels", "format_version": "1.0.0", "asset_type": "material-label",
           "payload": {"path": npy.name, "sha256": hashlib.sha256(npy.read_bytes()).hexdigest(), "dtype": "uint16", "dimensions": ["z", "y", "x"]},
           "shape_zyx": list(labels.shape), "voxel_size_xyz_m": [p / 1000] * 3, "local_to_world": l2w.tolist(),
           "materials": [{"material_id": 0, "name": "air", "role": "background"}, {"material_id": 1, "name": "object", "role": "material"}],
           "source": {"generator": "pj-voxel3dprint.artifact-print.occupancy-o3d", "generator_version": "0.1.0", "notes": a.mesh}}
    (out / f"{a.name}.voxels.json").write_text(json.dumps(man, indent=2) + "\n")
    print(json.dumps({"shape_zyx": labels.shape, "occupied": int(occ.sum()), "queries": int(q.shape[0]), "seconds": round(time.time() - t0, 2)}))


if __name__ == "__main__":
    main()
