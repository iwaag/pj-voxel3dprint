"""Printer-pitch resin slices from a coarse semantic label volume (artifact_print p1 step 6).

Ports the batch1 exporters' halftone (work/fur/export_floating_fur_voxelprint.py:
deterministic 3-D hash `noise` + cumulative-recipe `searchsorted`) to a label volume
of any pitch, one slice at a time (memory = one slice):

* geometry: --geometry coarse = nearest coarse label (0.5 mm staircase);
  --geometry mesh = Open3D occupancy of the STL at every printer pixel centre
  (exact surface at printer pitch), label from the nearest non-air coarse voxel;
* colour: per-pixel resin index from the label's recipe (white, black, clear,
  cyan, magenta, yellow) and the hash.

Writes slice_NNNN.png (RGBA, alpha 255, <= 6 resin colours + transparent background
like batch1) and NAME.printslices.json + NAME.resin-recipes.json + a material memo.
--every N writes only every N-th slice (timing/preview runs), the manifest says so.

Usage: venv/bin/python work/artifact_print/export_dither_slices.py SEM.voxels.json
           SEM.resin-recipes.json OUT_DIR NAME [--geometry mesh --stl MESH.stl]
           [--layer-um 14] [--every 1]
"""
import argparse, hashlib, json, math, shutil, time
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

PX, PY = 0.0254 / 600, 0.0254 / 300
DSEED = np.uint32(20260927)
RES = [("VeroPureWht", (240, 240, 240)), ("VeroBlack_or_VeroFlexBK", (26, 26, 29)),
       ("VeroClear_or_VeroFlexCLR", (227, 233, 253)), ("VeroCyan_or_VeroFlexCY", (0, 90, 158)),
       ("VeroMgnt_or_VeroFlexMGT", (166, 33, 98)), ("VeroYellow_or_VeroFlexYL", (200, 189, 3))]


def noise(x, y, z):  # batch1 fur, verbatim constants
    with np.errstate(over="ignore"):
        q = (x.astype(np.uint32) * np.uint32(0x9E3779B1) ^ y.astype(np.uint32) * np.uint32(0x85EBCA77)
             ^ np.uint32(z) * np.uint32(0xC2B2AE3D) ^ DSEED)
        q ^= q >> np.uint32(16); q *= np.uint32(0x7FEB352D); q ^= q >> np.uint32(15)
        q *= np.uint32(0x846CA68B); q ^= q >> np.uint32(16)
    return (q.astype(float) + 0.5) / 4294967296


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("voxels"); ap.add_argument("recipes"); ap.add_argument("out"); ap.add_argument("name")
    ap.add_argument("--geometry", choices=["coarse", "mesh"], default="coarse")
    ap.add_argument("--stl")
    ap.add_argument("--layer-um", type=float, default=14.0)
    ap.add_argument("--every", type=int, default=1)
    a = ap.parse_args()
    t0 = time.time()
    man = json.loads(Path(a.voxels).read_text())
    lab = np.load(Path(a.voxels).parent / man["payload"]["path"])
    vs = np.array(man["voxel_size_xyz_m"])
    origin = np.array(man["local_to_world"])[:3, 3]
    nz, ny, nx = lab.shape
    rec = json.loads(Path(a.recipes).read_text())["recipes_by_material_id"]
    maxid = int(lab.max())
    cum = np.ones((maxid + 1, 6))
    for k, v in rec.items():
        cum[int(k)] = np.cumsum(v)
    cum[:, -1] = 1.0 + 1e-9
    PZ = a.layer_um * 1e-6
    # printer grid over the coarse volume's occupied bounding box
    occ_idx = np.argwhere(lab > 0)
    lo = origin + occ_idx.min(0)[::-1] * vs
    hi = origin + (occ_idx.max(0)[::-1] + 1) * vs
    if a.geometry == "mesh":
        import open3d as o3d
        mesh = o3d.t.io.read_triangle_mesh(a.stl)
        scene = o3d.t.geometry.RaycastingScene(); scene.add_triangles(mesh)
        v = mesh.vertex.positions.numpy() / 1000.0
        lo, hi = v.min(0), v.max(0)
        # nearest non-air coarse label for any printer pixel inside the true surface
        _, near = ndimage.distance_transform_edt(lab == 0, return_indices=True)
    W, H, NZ = (math.ceil((hi[0] - lo[0]) / PX - 1e-6), math.ceil((hi[1] - lo[1]) / PY - 1e-6),
                math.ceil((hi[2] - lo[2]) / PZ - 1e-6))
    xs = lo[0] + (np.arange(W) + 0.5) * PX
    ys = lo[1] + (np.arange(H) + 0.5) * PY
    ix = np.clip(np.floor((xs - origin[0]) / vs[0]).astype(int), 0, nx - 1)
    iy = np.clip(np.floor((ys - origin[1]) / vs[1]).astype(int), 0, ny - 1)
    gx = np.broadcast_to(np.arange(W, dtype=np.uint32)[None, :], (H, W))
    gy = np.broadcast_to(np.arange(H, dtype=np.uint32)[:, None], (H, W))
    if a.geometry == "mesh":
        XX, YY = np.meshgrid(xs * 1000, ys * 1000)
    rgba = np.asarray([(0, 0, 0, 0), *((*rgb, 255) for _, rgb in RES)], np.uint8)
    out = Path(a.out) / a.name
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    counts = np.zeros(7, np.int64); records = []; t_geom = 0.0; t_png = 0.0
    for zi in range(0, NZ, a.every):
        z = lo[2] + (zi + 0.5) * PZ
        iz = min(max(int(math.floor((z - origin[2]) / vs[2])), 0), nz - 1)
        sem = lab[iz][np.ix_(iy, ix)]
        if a.geometry == "mesh":
            tg = time.time()
            q = np.stack([XX, YY, np.full_like(XX, z * 1000)], -1).reshape(-1, 3).astype(np.float32)
            inside = scene.compute_occupancy(o3d.core.Tensor(q)).numpy().reshape(H, W).astype(bool)
            nzi, nyi, nxi = (near[d][iz][np.ix_(iy, ix)] for d in range(3))
            sem = np.where(inside, lab[nzi, nyi, nxi], 0)
            t_geom += time.time() - tg
        u = noise(gx, gy, zi)
        idx = np.zeros((H, W), np.uint8)
        m = sem > 0
        c = cum[sem[m]]
        idx[m] = (u[m][:, None] >= c).sum(1).astype(np.uint8) + 1
        tp = time.time()
        fn = f"slice_{zi:04d}.png"; p = out / fn
        Image.fromarray(rgba[idx], mode="RGBA").save(p, compress_level=6)
        t_png += time.time() - tp
        counts += np.bincount(idx.ravel(), minlength=7)
        records.append({"file": fn, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    secs = time.time() - t0
    manifest = {"format": "vdbmat.print-slices", "format_version": "1.0.0", "name": a.name,
                "source": {"voxels": str(a.voxels), "payload_sha256": man["payload"]["sha256"], "geometry": a.geometry,
                           "stl": a.stl, "every": a.every},
                "printer": {"profile": "Stratasys J850 PNG method", "dpi_x": 600.0, "dpi_y": 300.0, "pitch_x_mm": PX * 1000,
                            "pitch_y_mm": PY * 1000, "layer_thickness_mm": PZ * 1000},
                "grid": {"width_px": W, "height_px": H, "slice_count": NZ, "written_slices": len(records),
                         "physical_mm": {"x": W * PX * 1000, "y": H * PY * 1000, "z": NZ * PZ * 1000}},
                "palette": {str(i): {"material": n, "rgb": list(rgb), "voxel_count": int(counts[i])} for i, (n, rgb) in enumerate(RES, 1)},
                "halftone": {"method": "deterministic-3d-hash (batch1 fur noise)", "seed": int(DSEED)},
                "timing_s": {"total": round(secs, 1), "geometry": round(t_geom, 1), "png": round(t_png, 1)},
                "slices": records}
    (out / f"{a.name}.printslices.json").write_text(json.dumps(manifest, indent=2) + "\n")
    shutil.copy(a.recipes, out / f"{a.name}.resin-recipes.json")
    memo = ["# " + a.name + " — Voxel Print 材料対応メモ", "", f"- X 600 dpi / Y 300 dpi / 積層 {PZ * 1000:.3f} mm",
            f"- PNG {W} × {H} px、{NZ} 層", "", "|Index|RGB|想定材料|", "|---:|---|---|"]
    memo += [f"|{i}|{rgb[0]}, {rgb[1]}, {rgb[2]}|{n}|" for i, (n, rgb) in enumerate(RES, 1)]
    (out / "材料対応メモ.md").write_text("\n".join(memo) + "\n")
    print(json.dumps({"W": W, "H": H, "NZ": NZ, "written": len(records), "voxels_total": W * H * NZ,
                      "timing_s": manifest["timing_s"], "counts": counts.tolist()}))


if __name__ == "__main__":
    main()
