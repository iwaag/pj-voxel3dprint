"""Colour a coarse geometry label volume from the scan texture (artifact_print p1 step 6).

Input: the voxelize-mesh output (material 1 = object), the original GLB and the
prep_mesh transform. Steps:

1. shell = object voxels within --shell-mm of the outside (EDT on the occupancy);
2. each shell voxel centre -> closest point on the textured mesh (Open3D
   RaycastingScene, Embree) -> UV -> base-colour texel (sRGB);
3. k-means in CIELAB over the shell voxels -> semantic labels 2..k+1; the core is
   label 1 ("core", white resin);
4. per label a six-resin recipe (white, black, clear, cyan, magenta, yellow) from
   the Kubelka-Munk surrogate (work/resins/km_surrogate.py): a --shell-mm layer of
   the mix over a thick white core, fitted in CIELAB to the cluster colour.
   --mode pure instead assigns the single nearest resin (plan's "6-colour
   quantisation", shown for comparison).

Writes NAME.voxels.json/.material_id.npy (uint16), NAME.resin-recipes.json (batch1
format), NAME.optical-mapping.json (semantic, for recipes_to_mapping --semantic) and
NAME.colour-report.json (cluster colour, KM prediction, dE76).

Usage: venv/bin/python work/artifact_print/shell_colour.py GEOM.voxels.json MESH.glb
           TRANSFORM.json OUT_DIR NAME --k 8 --shell-mm 1.0 [--mode km|pure]
"""
import argparse, hashlib, importlib.util, json, time
from pathlib import Path

import numpy as np
import open3d as o3d
import trimesh
from scipy import ndimage, optimize
from scipy.cluster.vq import kmeans2

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("km", ROOT / "work/resins/km_surrogate.py")
km = importlib.util.module_from_spec(spec)
spec.loader.exec_module(km)
LIB = ROOT / "work/resins/vero-j850-provisional-v3.json"
RESIN_ORDER = ["VeroPureWht", "VeroBlack_or_VeroFlexBK", "VeroClear_or_VeroFlexCLR",
               "VeroCyan_or_VeroFlexCY", "VeroMgnt_or_VeroFlexMGT", "VeroYellow_or_VeroFlexYL"]


def srgb_to_lin(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_lab(lin):
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = np.atleast_2d(lin) @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(np.maximum(xyz, 0)), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], 1)


def lin_to_srgb8(lin):
    lin = np.clip(lin, 0, 1)
    s = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * lin ** (1 / 2.4) - 0.055)
    return np.round(s * 255).astype(int)


def textured_mesh(glb, to_mm):
    scene = trimesh.load(glb, force="scene", process=False)
    geoms = list(scene.dump())
    assert len(geoms) == 1, "one textured geometry expected"
    g = geoms[0]
    g.apply_transform(np.asarray(to_mm))
    img = np.asarray(g.visual.material.baseColorTexture.convert("RGB"))
    return g, img


def sample_texture(g, img, pts):
    tm = o3d.t.geometry.TriangleMesh()
    tm.vertex.positions = o3d.core.Tensor(g.vertices.astype(np.float32))
    tm.triangle.indices = o3d.core.Tensor(g.faces.astype(np.int32))
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(tm)
    ans = scene.compute_closest_points(o3d.core.Tensor(pts.astype(np.float32)))
    fid = ans["primitive_ids"].numpy().astype(np.int64)
    buv = ans["primitive_uvs"].numpy()  # barycentric (u, v) of vertices 1 and 2
    w = np.stack([1 - buv[:, 0] - buv[:, 1], buv[:, 0], buv[:, 1]], 1)
    uv = (g.visual.uv[g.faces[fid]] * w[:, :, None]).sum(1)
    h, wd = img.shape[:2]
    x = np.clip(np.round((uv[:, 0] % 1) * (wd - 1)), 0, wd - 1).astype(int)
    y = np.clip(np.round((1 - uv[:, 1] % 1) * (h - 1)), 0, h - 1).astype(int)
    return img[y, x] / 255.0, scene


def km_shell_over_white(frac, sa, ss, shell_m):
    backing = km.km_reflectance(sa[0], ss[0], d=0.05, rg=0.0)  # thick white core
    return km.observed(km.km_reflectance(frac @ sa, frac @ ss, d=shell_m, rg=backing))


def fit_recipe(target_lin, sa, ss, shell_m):
    target = lin_to_lab(target_lin)[0]

    def frac(z):
        e = np.exp(z - z.max())
        return e / e.sum()

    def loss(z):
        return np.sum((lin_to_lab(km_shell_over_white(frac(z), sa, ss, shell_m))[0] - target) ** 2)

    best = None
    for start in np.eye(6) * 3:
        r = optimize.minimize(loss, start, method="Nelder-Mead", options={"maxiter": 4000, "xatol": 1e-4, "fatol": 1e-4})
        if best is None or r.fun < best.fun:
            best = r
    f = frac(best.x)
    f[f < 0.005] = 0
    return f / f.sum()


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("geom"); ap.add_argument("glb"); ap.add_argument("transform")
    ap.add_argument("out"); ap.add_argument("name")
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--shell-mm", type=float, default=1.0)
    ap.add_argument("--mode", choices=["km", "pure"], default="km")
    a = ap.parse_args()
    t0 = time.time()
    man = json.loads(Path(a.geom).read_text())
    occ = np.load(Path(a.geom).parent / man["payload"]["path"]) > 0
    vs_mm = np.array(man["voxel_size_xyz_m"]) * 1000
    origin_mm = np.array(man["local_to_world"])[:3, 3] * 1000
    dist = ndimage.distance_transform_edt(occ, sampling=vs_mm[::-1])
    shell = occ & (dist <= a.shell_mm + 1e-6)
    zyx = np.argwhere(shell)
    centres = origin_mm + (zyx[:, ::-1] + 0.5) * vs_mm
    g, img = textured_mesh(a.glb, json.loads(Path(a.transform).read_text())["gltf_to_mm"])
    rgb, _ = sample_texture(g, img, centres)
    lin = srgb_to_lin(rgb)
    lab = lin_to_lab(lin)
    cent, lab_idx = kmeans2(lab, a.k, minit="++", seed=np.random.default_rng(0))
    # order clusters by lightness so labels are stable to read
    order = np.argsort(-cent[:, 0])
    remap = np.empty(a.k, int)
    remap[order] = np.arange(a.k)
    lab_idx = remap[lab_idx]
    labels = np.zeros(occ.shape, np.uint16)
    labels[occ] = 1
    labels[tuple(zyx.T)] = lab_idx + 2
    _, sa, ss = km.load_library(LIB)
    shell_m = a.shell_mm / 1000
    white = np.array([1.0, 0, 0, 0, 0, 0])
    recipes = {1: white}
    report = []
    for c in range(a.k):
        members = lab_idx == c
        target_lin = lin[members].mean(0)
        if a.mode == "km":
            f = fit_recipe(target_lin, sa, ss, shell_m)
        else:  # nearest single resin, judged on its own thick-slab colour
            cand = [lin_to_lab(km_shell_over_white(e, sa, ss, shell_m))[0] for e in np.eye(6)]
            f = np.eye(6)[int(np.argmin([np.linalg.norm(x - lin_to_lab(target_lin)[0]) for x in cand]))]
        pred = km_shell_over_white(f, sa, ss, shell_m)
        dE = float(np.linalg.norm(lin_to_lab(pred)[0] - lin_to_lab(target_lin)[0]))
        recipes[c + 2] = f
        report.append({"material_id": c + 2, "voxels": int(members.sum()),
                       "target_srgb8": lin_to_srgb8(target_lin).tolist(),
                       "km_pred_srgb8": lin_to_srgb8(pred).tolist(),
                       "recipe_wkcCMY": [round(float(x), 3) for x in f], "dE76_km": round(dE, 2)})
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    npy = out / f"{a.name}.material_id.npy"
    np.save(npy, labels, allow_pickle=False)
    mats = [(0, "air", "background"), (1, "core-white", "material")] + [(c + 2, f"shell-{c + 2:02d}", "material") for c in range(a.k)]
    vox = {"format": "vdbmat.voxels", "format_version": "1.0.0", "asset_type": "material-label",
           "payload": {"path": npy.name, "sha256": digest(npy), "dtype": "uint16", "dimensions": ["z", "y", "x"]},
           "shape_zyx": list(labels.shape), "voxel_size_xyz_m": man["voxel_size_xyz_m"],
           "local_to_world": man["local_to_world"],
           "materials": [{"material_id": m, "name": n, "role": r} for m, n, r in mats],
           "source": {"generator": "pj-voxel3dprint.artifact-print.shell-colour", "generator_version": "0.1.0",
                      "notes": f"{a.glb}; shell {a.shell_mm} mm; k={a.k}; mode={a.mode}; library {LIB.name}"}}
    (out / f"{a.name}.voxels.json").write_text(json.dumps(vox, indent=2) + "\n")
    (out / f"{a.name}.resin-recipes.json").write_text(json.dumps(
        {"resin_order": RESIN_ORDER, "recipes_by_material_id": {str(k): [round(float(x), 4) for x in v] for k, v in recipes.items()}}, indent=2) + "\n")
    basis = {"kind": "rgb", "identifier": "linear-srgb-effective-v1", "coordinates": ["R", "G", "B"],
             "reference_white": "D65", "observer": "CIE-1931-2deg", "transfer": "linear"}
    sem = {"format": "vdbmat.optical-mapping", "format_version": "1.0.0", "configuration_id": f"{a.name}-semantic",
           "version": "0.1.0", "optical_basis": basis, "mixing_rule": "linear-volume-fraction-v1",
           "calibration_status": "provisional-uncalibrated",
           "materials": [{"material_id": m, "name": n, "sigma_a_rgb_per_m": [0, 0, 0], "sigma_s_rgb_per_m": [0, 0, 0], "g": 0.0, "ior": 1.0 if m == 0 else 1.5} for m, n, _ in mats]}
    (out / f"{a.name}.optical-mapping.json").write_text(json.dumps(sem, indent=2) + "\n")
    summary = {"shape_zyx": list(labels.shape), "object_voxels": int(occ.sum()), "shell_voxels": int(shell.sum()),
               "shell_mm": a.shell_mm, "k": a.k, "mode": a.mode, "seconds": round(time.time() - t0, 1),
               "dE76_km_mean_voxel_weighted": round(float(np.average([r["dE76_km"] for r in report], weights=[r["voxels"] for r in report])), 2),
               "clusters": report}
    (out / f"{a.name}.colour-report.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "clusters"}))
    for r in report:
        print(r)


if __name__ == "__main__":
    main()
