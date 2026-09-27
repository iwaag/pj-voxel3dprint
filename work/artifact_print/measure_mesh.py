"""Measure candidate scan meshes for the MVP selection (artifact_print p1 step 2).

Usage (repo root, throwaway venv from report2):
    .local/study/3dprint_artifact/venv/bin/python work/artifact_print/measure_mesh.py FILE... [--json OUT]

Per file: triangle/vertex counts, texture images (size, mode), bbox in the file's
units (glTF = metres), watertight / winding-consistent / manifold-edge flags,
connected components (count, share of the largest), boundary-edge count, and a
colour-complexity estimate: area-weighted texel colours at 20k surface samples,
k-means in CIELAB, the smallest k whose mean dE76 to its centre is < 6 and the
dE at k = 6 (the per-slice material limit). Also writes a contact thumbnail of the
base-colour texture next to the output JSON.
"""
import argparse, hashlib, json, sys
from pathlib import Path

import numpy as np
import trimesh
from scipy.cluster.vq import kmeans2


def srgb_to_lab(rgb):
    c = rgb / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], 1)


def sample_colours(mesh, n=20000, seed=0):
    vis = mesh.visual
    if isinstance(vis, trimesh.visual.TextureVisuals) and vis.uv is not None:
        mat = vis.material
        img = getattr(mat, "baseColorTexture", None) or getattr(mat, "image", None)
        if img is not None:
            pts, fid = trimesh.sample.sample_surface(mesh, n, seed=seed)
            bary = trimesh.triangles.points_to_barycentric(mesh.triangles[fid], pts)
            uv = (vis.uv[mesh.faces[fid]] * bary[:, :, None]).sum(1)
            im = np.asarray(img.convert("RGB"))
            h, w = im.shape[:2]
            x = np.clip((uv[:, 0] % 1.0) * (w - 1), 0, w - 1).astype(int)
            y = np.clip((1 - uv[:, 1] % 1.0) * (h - 1), 0, h - 1).astype(int)
            return im[y, x].astype(float), "uv-texture"
    if isinstance(vis, trimesh.visual.ColorVisuals) and vis.kind == "vertex":
        return vis.vertex_colors[:, :3].astype(float), "vertex-colour"
    return None, "none"


def colour_stats(rgb):
    lab = srgb_to_lab(rgb)
    out = {"lab_mean": lab.mean(0).round(1).tolist(), "lab_std": lab.std(0).round(1).tolist()}
    res = {}
    rng = np.random.default_rng(0)
    for k in range(1, 13):
        best = None
        for _ in range(3):
            cent, lab_ = kmeans2(lab, k, minit="++", seed=rng)
            d = np.linalg.norm(lab - cent[lab_], axis=1).mean()
            best = d if best is None else min(best, d)
        res[k] = round(float(best), 2)
    out["mean_dE_by_k"] = res
    out["k_for_dE6"] = next((k for k, d in res.items() if d < 6), None)
    out["dE_at_k6"] = res[6]
    return out


def measure(path):
    scene = trimesh.load(path, force="scene", process=False)
    geoms = list(scene.dump()) if hasattr(scene, "dump") else [scene]
    info = {"file": str(path), "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "n_geometries": len(geoms)}
    textures = []
    for g in geoms:
        mat = getattr(g.visual, "material", None)
        for attr in ("baseColorTexture", "image", "normalTexture", "metallicRoughnessTexture"):
            im = getattr(mat, attr, None) if mat is not None else None
            if im is not None:
                textures.append({"slot": attr, "size": list(im.size), "mode": im.mode})
    info["textures"] = textures
    mesh = trimesh.util.concatenate(geoms) if len(geoms) > 1 else geoms[0]
    raw = mesh.copy()
    info["triangles"] = int(len(raw.faces))
    info["vertices"] = int(len(raw.vertices))
    ext = raw.bounds[1] - raw.bounds[0]
    info["bbox_extent_file_units"] = ext.round(5).tolist()
    # Topology on a vertex-merged copy: UV seams split vertices, which would make every
    # textured scan look "open". merge_vertices ignoring UV/normals gives the true shape.
    m = trimesh.Trimesh(raw.vertices, raw.faces, process=False)
    m.merge_vertices(merge_tex=True, merge_norm=True)
    m.remove_unreferenced_vertices()
    info["merged_vertices"] = int(len(m.vertices))
    info["degenerate_faces"] = int((m.area_faces < 1e-18).sum())
    edges = m.edges_sorted
    uniq, counts = np.unique(edges, axis=0, return_counts=True)
    info["boundary_edges"] = int((counts == 1).sum())
    info["nonmanifold_edges"] = int((counts > 2).sum())
    info["watertight"] = bool(m.is_watertight)
    info["winding_consistent"] = bool(m.is_winding_consistent)
    comps = m.split(only_watertight=False)
    areas = sorted((c.area for c in comps), reverse=True)
    info["components"] = len(comps)
    info["largest_component_area_share"] = round(areas[0] / sum(areas), 4) if areas else None
    info["volume_if_watertight"] = float(m.volume) if m.is_watertight else None
    rgb, kind = sample_colours(raw)
    info["colour_source"] = kind
    if rgb is not None:
        info["colour"] = colour_stats(rgb)
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json")
    a = ap.parse_args()
    res = []
    for f in a.files:
        try:
            r = measure(f)
        except Exception as e:  # keep going; the failure is a finding
            r = {"file": f, "error": repr(e)}
        res.append(r)
        print(json.dumps(r, ensure_ascii=False))
        sys.stdout.flush()
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
