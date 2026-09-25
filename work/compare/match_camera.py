"""Solve a stage camera pose for a photo of a 60 x 30 x 5 mm slab (PnP + focal).

Usage (repo root):

    vdbmat/.venv/bin/python work/compare/match_camera.py SPEC.json OUT_SPEC.json [--report OUT.md]

Reads every ``kind: photo`` entry of a spec-v3 file (see ``region_table.py``)
with ``corners_px`` (image points of the region face's model corners (0,0),
(60,0), (60,30), (0,30) mm), optional ``bottom_corners_px``
(``[[corner_index, u, v], ...]``: the same corners on the face 5 mm below),
and ``volume`` (which input the camera is for, see below). It writes the spec
back with a ``camera`` block per photo (the stage-config 1.4.0 pose form:
``position_m``, ``target_m``, ``up``, ``fov_deg``) and a ``pnp`` block
(reprojection RMS, focal length, distance).

Model: pinhole with square pixels and the principal point at the image
centre, unknown focal length. The photos carry no EXIF, so the solver starts
from a scan over fov 20..80 deg (cv2 IPPE planar PnP per focal, SQPnP when
IPPE fails) and refines all 7 parameters with scipy ``least_squares`` on the
pixel residuals. A prior of fov 22 +- 6 deg (5 px per sigma) holds the focal
length where four near top-down points cannot fix it (focal and distance
trade off). 22 deg is the typical value of the well-constrained batch1 views.

Frame: the optical zarrs span x 0..60, y 0..30, z 0..5 mm (metres in the
camera block). The corner picks are in the coordinates of the region face
(``pick_regions.py``). ``volume`` says which input the camera is for, i.e. how
those coordinates sit on that input's top face (z = 5 mm):

- ``mirror_y``: the print is a mirror image of the volume and lies top-up
  (agate, fur): (x, y) -> (x, 30 - y);
- ``mirror_z``: mirrored and lying bottom-up (amber, face ``bottom``): the
  bottom layer's (x, y) is the top of the z-mirrored volume, unchanged;
- ``none``: (x, y) unchanged.

Only a mirrored model puts the camera above the slab with a small residual
(p2 report3). ``flip_volume.py`` writes the matching inputs.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from slab import MODEL_CORNERS_MM, SLAB_MM

ROOT = Path(__file__).resolve().parents[2]
FOV_PRIOR_DEG = (22.0, 6.0)
PRIOR_PX = 5.0
VOLUMES = ("mirror_y", "mirror_z", "none")


def model_points(volume: str, bottom: bool = False) -> np.ndarray:
    """(4, 3) model corners in metres on the rendered input (top face, or 5 mm below)."""
    if volume not in VOLUMES:
        raise ValueError(f"volume must be one of {VOLUMES}, got {volume!r}")
    xs, ys = MODEL_CORNERS_MM[:, 0], MODEL_CORNERS_MM[:, 1]
    if volume == "mirror_y":
        ys = SLAB_MM[1] - ys
    z = 0.0 if bottom else SLAB_MM[2]
    return np.c_[xs, ys, np.full(4, z)] / 1000.0


def project(params: np.ndarray, pts: np.ndarray, width: int, height: int) -> np.ndarray:
    rvec, tvec, log_f = params[:3], params[3:6], params[6]
    cam = Rotation.from_rotvec(rvec).apply(pts) + tvec
    f = math.exp(log_f)
    return np.c_[width / 2 + f * cam[:, 0] / cam[:, 2], height / 2 + f * cam[:, 1] / cam[:, 2]]


def fov_of(f: float, width: int) -> float:
    return math.degrees(2 * math.atan(width / 2 / f))


def solve(obj: np.ndarray, img: np.ndarray, width: int, height: int) -> tuple[np.ndarray, float]:
    def residuals(p: np.ndarray) -> np.ndarray:
        prior = PRIOR_PX * (fov_of(math.exp(p[6]), width) - FOV_PRIOR_DEG[0]) / FOV_PRIOR_DEG[1]
        depth = (Rotation.from_rotvec(p[:3]).apply(obj) + p[3:6])[:, 2]
        behind = 1000.0 * np.clip(0.01 - depth, 0.0, None)  # points must be >= 1 cm in front
        return np.r_[(project(p, obj, width, height) - img).ravel(), prior, behind]

    best = None
    for fov in np.arange(20.0, 81.0, 5.0):
        f = width / 2 / math.tan(math.radians(fov) / 2)
        k = np.array([[f, 0, width / 2], [0, f, height / 2], [0, 0, 1.0]])
        # IPPE occasionally returns a NaN rotation (near 180 deg); SQPnP is the fallback.
        for flag in (cv2.SOLVEPNP_IPPE, cv2.SOLVEPNP_SQPNP):
            ok, rvec, tvec = cv2.solvePnP(obj[:4], img[:4], k, None, flags=flag)
            p0 = np.r_[rvec.ravel(), tvec.ravel(), math.log(f)] if ok else None
            if p0 is None or not np.all(np.isfinite(p0)) or p0[5] <= 0:
                continue
            res = least_squares(residuals, p0)
            if best is None or res.cost < best.cost:
                best = res
    assert best is not None
    rms = float(np.sqrt(np.mean((project(best.x, obj, width, height) - img) ** 2)))
    return best.x, rms


def camera_block(params: np.ndarray, width: int) -> tuple[dict, dict]:
    rot = Rotation.from_rotvec(params[:3])
    tvec = params[3:6]
    # world -> camera: x_c = R x_w + t; camera centre C = -R^T t.
    r = rot.as_matrix()
    centre = -r.T @ tvec
    forward = r.T @ np.array([0.0, 0.0, 1.0])
    down = r.T @ np.array([0.0, 1.0, 0.0])
    slab_centre = np.array(SLAB_MM) / 2000.0
    distance = float(np.dot(slab_centre - centre, forward))
    target = centre + forward * distance
    f = math.exp(params[6])
    camera = {
        "fov_deg": round(fov_of(f, width), 4),
        "position_m": [round(float(v), 7) for v in centre],
        "target_m": [round(float(v), 7) for v in target],
        "up": [round(float(v), 7) for v in -down],
    }
    info = {"focal_px": round(f, 1), "distance_m": round(distance, 4), "elevation_deg": round(math.degrees(math.asin(-forward[2])), 1)}
    return camera, info


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("spec", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    lines = ["| case | photo | volume | points | RMS px | fov ° | elevation ° | distance mm |", "|---|---|---|---:|---:|---:|---:|---:|"]
    for case, cdef in spec["cases"].items():
        for entry in cdef["images"]:
            if entry["kind"] != "photo" or "corners_px" not in entry:
                continue
            volume = entry["volume"]
            path = Path(entry["path"])
            with Image.open(path if path.is_absolute() else ROOT / path) as im:
                width, height = im.size
            obj = model_points(volume)
            img = np.asarray(entry["corners_px"], float)
            for idx, u, v in entry.get("bottom_corners_px", []):
                obj = np.r_[obj, model_points(volume, bottom=True)[int(idx)][None]]
                img = np.r_[img, [[u, v]]]
            params, rms = solve(obj, img, width, height)
            camera, info = camera_block(params, width)
            entry["camera"] = camera
            entry["pnp"] = {"rms_px": round(rms, 2), "points": len(obj), **info}
            lines.append(
                f"| {case} | {path.stem} | {volume} | {len(obj)} | {rms:.2f} | {camera['fov_deg']:.1f} | "
                f"{info['elevation_deg']:.1f} | {info['distance_m'] * 1000:.0f} |"
            )
    args.output.write_text(json.dumps(spec, indent=1) + "\n")
    if args.report:
        args.report.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
