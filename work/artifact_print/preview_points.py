"""Quick look at a textured scan without a GPU (artifact_print p1 step 2).

Samples surface points, colours them from the base-colour texture and z-buffers an
orthographic front and side view (glTF: +Y up, camera looks along -Z / -X).
Usage: venv/bin/python work/artifact_print/preview_points.py MESH OUT.png [--n 600000]
"""
import argparse
import numpy as np
import trimesh
from PIL import Image


def coloured_points(path, n):
    scene = trimesh.load(path, force="scene", process=False)
    pts_all, rgb_all = [], []
    geoms = list(scene.dump())
    total = sum(g.area for g in geoms)
    for g in geoms:
        k = max(1000, int(n * g.area / total))
        pts, fid = trimesh.sample.sample_surface(g, k, seed=1)
        rgb = np.full((len(pts), 3), 180.0)
        mat = getattr(g.visual, "material", None)
        img = getattr(mat, "baseColorTexture", None) or getattr(mat, "image", None)
        if img is not None and getattr(g.visual, "uv", None) is not None:
            bary = trimesh.triangles.points_to_barycentric(g.triangles[fid], pts)
            uv = (g.visual.uv[g.faces[fid]] * bary[:, :, None]).sum(1)
            im = np.asarray(img.convert("RGB"))
            h, w = im.shape[:2]
            x = ((uv[:, 0] % 1) * (w - 1)).astype(int)
            y = ((1 - uv[:, 1] % 1) * (h - 1)).astype(int)
            rgb = im[y, x].astype(float)
        # simple Lambert shading from the face normal so shape reads
        nrm = g.face_normals[fid]
        shade = 0.55 + 0.45 * np.clip(nrm @ np.array([0.3, 0.5, 0.8]) / np.linalg.norm([0.3, 0.5, 0.8]), 0, 1)
        pts_all.append(pts)
        rgb_all.append(rgb * shade[:, None])
    return np.vstack(pts_all), np.vstack(rgb_all)


def view(p, rgb, right, up, depth, size):
    u, v, d = p @ right, p @ up, p @ depth
    lo, hi = np.array([u.min(), v.min()]), np.array([u.max(), v.max()])
    s = (size - 8) / (hi - lo).max()
    x = ((u - lo[0]) * s + 4).astype(int)
    y = (size - 1 - ((v - lo[1]) * s + 4)).astype(int)
    img = np.full((size, size, 3), 255, np.uint8)
    order = np.argsort(-d)  # far first, near overwrites
    img[y[order], x[order]] = np.clip(rgb[order], 0, 255).astype(np.uint8)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mesh")
    ap.add_argument("out")
    ap.add_argument("--n", type=int, default=600000)
    ap.add_argument("--size", type=int, default=420)
    a = ap.parse_args()
    p, rgb = coloured_points(a.mesh, a.n)
    p = p - p.mean(0)
    front = view(p, rgb, np.array([1, 0, 0]), np.array([0, 1, 0]), np.array([0, 0, -1]), a.size)
    side = view(p, rgb, np.array([0, 0, -1]), np.array([0, 1, 0]), np.array([-1, 0, 0]), a.size)
    top = view(p, rgb, np.array([1, 0, 0]), np.array([0, 0, -1]), np.array([0, -1, 0]), a.size)
    Image.fromarray(np.hstack([front, side, top])).save(a.out)


if __name__ == "__main__":
    main()
