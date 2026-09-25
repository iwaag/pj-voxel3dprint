"""Slab geometry helpers shared by the p2 comparison scripts.

The batch1 prints are 60 x 30 x 5 mm boxes. Their optical zarrs use an
identity local-to-world transform with the volume at x 0..0.06, y 0..0.03,
z 0..0.005 m, so "slab millimetres" (x, y on the top face z = 5 mm) are the
same coordinates as the voxel volume, times 1000.

- ``stage_camera``: the stage-config camera (az/el/distance/fov or a full
  pose) as a pinhole model in image pixels, the same convention as
  ``mitsuba_stage._sensor_override_dict`` (look_at, up +Z, fov on the x axis).
- ``homography``: 3x3 map from top-face mm to image pixels from the four
  corner picks ``corners_px`` = image points of the model corners
  (0,0), (60,0), (60,30), (0,30) mm, in that order.
- ``region_mask``: boolean image mask of a top-face rectangle given in mm.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

SLAB_MM = (60.0, 30.0, 5.0)
MODEL_CORNERS_MM = np.array([[0.0, 0.0], [60.0, 0.0], [60.0, 30.0], [0.0, 30.0]])


@dataclass(frozen=True)
class Pinhole:
    origin: np.ndarray  # world, metres
    right: np.ndarray  # unit vectors of the camera frame
    down: np.ndarray
    forward: np.ndarray
    focal_px: float
    width: int
    height: int

    def project(self, points_m: np.ndarray) -> np.ndarray:
        v = np.atleast_2d(points_m) - self.origin
        z = v @ self.forward
        u = self.width / 2 + self.focal_px * (v @ self.right) / z
        w = self.height / 2 + self.focal_px * (v @ self.down) / z
        return np.stack([u, w], axis=-1)


def slab_bounds() -> tuple[np.ndarray, float]:
    hi = np.array(SLAB_MM) / 1000.0
    return hi / 2, float(np.linalg.norm(hi) / 2)


def look_at(origin, target, up, fov_deg: float, width: int, height: int) -> Pinhole:
    origin = np.asarray(origin, float)
    forward = np.asarray(target, float) - origin
    forward /= np.linalg.norm(forward)
    left = np.cross(np.asarray(up, float), forward)
    left /= np.linalg.norm(left)
    cam_up = np.cross(forward, left)
    focal = (width / 2) / math.tan(math.radians(fov_deg) / 2)
    return Pinhole(origin, -left, -cam_up, forward, focal, width, height)


def stage_camera(camera: dict, width: int, height: int) -> Pinhole:
    """Pinhole for a stage-config ``camera`` block (either form)."""
    center, radius = slab_bounds()
    if "position_m" in camera:
        return look_at(
            camera["position_m"],
            camera["target_m"],
            camera.get("up", [0.0, 0.0, 1.0]),
            camera["fov_deg"],
            width,
            height,
        )
    az, el = math.radians(camera["azimuth_deg"]), math.radians(camera["elevation_deg"])
    direction = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    origin = center + direction * radius * camera["distance_factor"]
    return look_at(origin, center, [0.0, 0.0, 1.0], camera["fov_deg"], width, height)


def projected_corners(cam: Pinhole) -> np.ndarray:
    """Image points of the four top-face model corners (MODEL_CORNERS_MM order)."""
    z = SLAB_MM[2]
    pts = np.array([[x, y, z] for x, y in MODEL_CORNERS_MM]) / 1000.0
    return cam.project(pts)


def homography(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """DLT homography mapping 4+ src points to dst points."""
    rows = []
    for (x, y), (u, v) in zip(src, dst):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.asarray(rows, float))
    h = vt[-1].reshape(3, 3)
    return h / h[2, 2]


def apply_h(h: np.ndarray, pts: np.ndarray) -> np.ndarray:
    p = np.c_[np.atleast_2d(pts), np.ones(len(np.atleast_2d(pts)))] @ h.T
    return p[:, :2] / p[:, 2:3]


def mm_to_image(corners_px) -> np.ndarray:
    return homography(MODEL_CORNERS_MM, np.asarray(corners_px, float))


def region_mask(h_mm_to_px: np.ndarray, rect_mm, shape_hw) -> np.ndarray:
    """Pixels whose centre maps (via the inverse homography) inside rect_mm."""
    x0, y0, x1, y1 = rect_mm
    quad = apply_h(h_mm_to_px, np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]))
    lo = np.floor(quad.min(axis=0)).astype(int)
    hi = np.ceil(quad.max(axis=0)).astype(int)
    lo = np.maximum(lo, 0)
    hi = np.minimum(hi, [shape_hw[1] - 1, shape_hw[0] - 1])
    mask = np.zeros(shape_hw, bool)
    if np.any(hi < lo):
        return mask
    ys, xs = np.mgrid[lo[1] : hi[1] + 1, lo[0] : hi[0] + 1]
    mm = apply_h(np.linalg.inv(h_mm_to_px), np.c_[xs.ravel() + 0.5, ys.ravel() + 0.5])
    inside = (mm[:, 0] >= x0) & (mm[:, 0] <= x1) & (mm[:, 1] >= y0) & (mm[:, 1] <= y1)
    mask[ys.ravel()[inside], xs.ravel()[inside]] = True
    return mask


def warp_top_face(image: np.ndarray, h_mm_to_px: np.ndarray, px_per_mm: float = 10.0) -> np.ndarray:
    """Resample the top face into a (30*ppm, 60*ppm) image in mm coordinates (bilinear)."""
    w, hgt = int(SLAB_MM[0] * px_per_mm), int(SLAB_MM[1] * px_per_mm)
    ys, xs = np.mgrid[0:hgt, 0:w]
    mm = np.c_[(xs.ravel() + 0.5) / px_per_mm, (ys.ravel() + 0.5) / px_per_mm]
    p = apply_h(h_mm_to_px, mm) - 0.5
    x0 = np.clip(np.floor(p[:, 0]).astype(int), 0, image.shape[1] - 2)
    y0 = np.clip(np.floor(p[:, 1]).astype(int), 0, image.shape[0] - 2)
    fx = np.clip(p[:, 0] - x0, 0, 1)[:, None]
    fy = np.clip(p[:, 1] - y0, 0, 1)[:, None]
    img = image.reshape(image.shape[0], image.shape[1], -1).astype(np.float64)
    out = (
        img[y0, x0] * (1 - fx) * (1 - fy)
        + img[y0, x0 + 1] * fx * (1 - fy)
        + img[y0 + 1, x0] * (1 - fx) * fy
        + img[y0 + 1, x0 + 1] * fx * fy
    )
    return out.reshape(hgt, w, -1).squeeze()
