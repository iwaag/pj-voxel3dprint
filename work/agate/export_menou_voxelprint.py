from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / ".local" / "pink-agate-v3" / "source" / "pink-teal-agate-strata-v3.material_id.npy"
SOURCE_MANIFEST = ROOT / ".local" / "pink-agate-v3" / "source" / "pink-teal-agate-strata-v3.voxels.json"
OUT = ROOT / "work" / "agate" / "menou_voxelprint_staging"
NAME = "menou"
SEED = np.uint32(20260902)

PITCH_X_M = 0.0254 / 600.0
PITCH_Y_M = 0.0254 / 300.0
PITCH_Z_M = 0.014e-3
EXTENT_X_M, EXTENT_Y_M, EXTENT_Z_M = 0.060, 0.030, 0.005
SRC_VOXEL_M = 0.0002
SHELL_M = 0.0003

RESINS = [
    ("VeroPureWht", (240, 240, 240)),
    ("VeroBlack_or_VeroFlexBK", (26, 26, 29)),
    ("VeroClear_or_VeroFlexCLR", (227, 233, 253)),
    ("VeroCyan_or_VeroFlexCY", (0, 90, 158)),
    ("VeroMgnt_or_VeroFlexMGT", (166, 33, 98)),
    ("VeroYellow_or_VeroFlexYL", (200, 189, 3)),
]

# white, black, clear, cyan, magenta, yellow
RECIPES = {
    1: [0.00, 0.00, 1.00, 0.00, 0.00, 0.00],
    2: [0.22, 0.00, 0.45, 0.00, 0.27, 0.06],
    3: [0.12, 0.01, 0.38, 0.01, 0.38, 0.10],
    4: [0.10, 0.02, 0.40, 0.08, 0.34, 0.06],
    5: [0.14, 0.01, 0.43, 0.18, 0.21, 0.03],
    6: [0.08, 0.03, 0.40, 0.30, 0.15, 0.04],
    7: [0.04, 0.04, 0.35, 0.48, 0.06, 0.03],
    8: [0.02, 0.10, 0.28, 0.53, 0.04, 0.03],
    9: [0.68, 0.00, 0.29, 0.00, 0.02, 0.01],
    10: [0.38, 0.00, 0.56, 0.01, 0.03, 0.02],
    11: [0.12, 0.06, 0.48, 0.01, 0.09, 0.24],
    12: [0.02, 0.22, 0.70, 0.03, 0.02, 0.01],
    13: [0.01, 0.00, 0.99, 0.00, 0.00, 0.00],
    14: [0.03, 0.25, 0.46, 0.18, 0.06, 0.02],
}

MATERIAL_NAMES = {
    1: "透明表面膜",
    2: "淡いピンク #e6c5e1",
    3: "ダスティローズ",
    4: "モーヴ",
    5: "ラベンダー",
    6: "ブルーグレー",
    7: "青緑 #0f6d75",
    8: "濃い青緑",
    9: "白",
    10: "乳白",
    11: "薄茶",
    12: "透明感のある黒",
    13: "透明レイヤー",
    14: "スモーキーブルーブラック",
}


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def hash_uniform(x: np.ndarray, y: np.ndarray, z: int) -> np.ndarray:
    h = (
        x.astype(np.uint32) * np.uint32(0x9E3779B1)
        ^ y.astype(np.uint32) * np.uint32(0x85EBCA77)
        ^ np.uint32(z) * np.uint32(0xC2B2AE3D)
        ^ SEED
    )
    h ^= h >> np.uint32(16)
    h *= np.uint32(0x7FEB352D)
    h ^= h >> np.uint32(15)
    h *= np.uint32(0x846CA68B)
    h ^= h >> np.uint32(16)
    return (h.astype(np.float64) + 0.5) / 4294967296.0


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    source = np.load(SOURCE, mmap_mode="r")
    width = math.ceil(EXTENT_X_M / PITCH_X_M - 1e-6)
    height = math.ceil(EXTENT_Y_M / PITCH_Y_M - 1e-6)
    slices = math.ceil(EXTENT_Z_M / PITCH_Z_M - 1e-6)

    x_m = (np.arange(width) + 0.5) * PITCH_X_M
    y_m = (np.arange(height) + 0.5) * PITCH_Y_M
    z_m = (np.arange(slices) + 0.5) * PITCH_Z_M
    src_x = np.clip(np.floor(x_m / SRC_VOXEL_M), 0, source.shape[2] - 1).astype(np.intp)
    src_y = np.clip(np.floor(y_m / SRC_VOXEL_M), 0, source.shape[1] - 1).astype(np.intp)
    src_z = np.clip(np.floor(z_m / SRC_VOXEL_M), 0, source.shape[0] - 1).astype(np.intp)
    grid_x = np.broadcast_to(np.arange(width, dtype=np.uint32)[None, :], (height, width))
    grid_y = np.broadcast_to(np.arange(height, dtype=np.uint32)[:, None], (height, width))
    shell_xy = (
        (x_m[None, :] <= SHELL_M)
        | ((EXTENT_X_M - x_m[None, :]) <= SHELL_M)
        | (y_m[:, None] <= SHELL_M)
        | ((EXTENT_Y_M - y_m[:, None]) <= SHELL_M)
    )

    rgba_lut = np.asarray([(0, 0, 0, 0), *((*rgb, 255) for _, rgb in RESINS)], dtype=np.uint8)
    cumulative = {mid: np.cumsum(np.asarray(recipe, dtype=np.float64)) for mid, recipe in RECIPES.items()}
    counts = np.zeros(7, dtype=np.int64)
    records: list[dict[str, object]] = []

    for zi, (source_zi, z_pos) in enumerate(zip(src_z, z_m, strict=True)):
        semantic = np.asarray(source[source_zi])[np.ix_(src_y, src_x)].copy()
        if z_pos <= SHELL_M or (EXTENT_Z_M - z_pos) <= SHELL_M:
            semantic.fill(1)
        else:
            semantic[shell_xy] = 1
        uniform = hash_uniform(grid_x, grid_y, zi)
        indices = np.zeros((height, width), dtype=np.uint8)
        for material_id, thresholds in cumulative.items():
            mask = semantic == material_id
            if np.any(mask):
                indices[mask] = np.searchsorted(thresholds, uniform[mask], side="right").astype(np.uint8) + 1
        if np.any(indices == 0):
            raise RuntimeError(f"unassigned printer voxel in slice {zi}")

        counts += np.bincount(indices.ravel(), minlength=7)
        filename = f"slice_{zi:04d}.png"
        path = OUT / filename
        image = Image.fromarray(rgba_lut[indices], mode="RGBA")
        image.save(path, format="PNG", optimize=False, compress_level=9)
        records.append({"file": filename, "sha256": sha256(path)})

    source_doc = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    manifest = {
        "format": "vdbmat.print-slices",
        "format_version": "1.0.0",
        "name": NAME,
        "source": {
            "manifest": str(SOURCE_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
            "manifest_sha256": sha256(SOURCE_MANIFEST),
            "payload_sha256": source_doc["payload"]["sha256"],
        },
        "printer": {
            "profile": "Stratasys J750 PNG method High Quality",
            "dpi_x": 600.0,
            "dpi_y": 300.0,
            "pitch_x_mm": PITCH_X_M * 1000.0,
            "pitch_y_mm": PITCH_Y_M * 1000.0,
            "layer_thickness_mm": PITCH_Z_M * 1000.0,
        },
        "grid": {
            "width_px": width,
            "height_px": height,
            "slice_count": slices,
            "physical_mm": {"x": width * PITCH_X_M * 1000.0, "y": height * PITCH_Y_M * 1000.0, "z": slices * PITCH_Z_M * 1000.0},
            "axis_mapping": {"columns": "+X", "rows": "+Y", "stack": "+Z"},
        },
        "palette": {str(i): {"material": n, "rgb": list(rgb), "voxel_count": int(counts[i])} for i, (n, rgb) in enumerate(RESINS, 1)},
        "halftone": {"method": "deterministic-3d-hash", "seed": int(SEED), "recipes_by_material_id": RECIPES},
        "surface_clear_membrane_mm": 0.3,
        "slices": records,
    }
    (OUT / f"{NAME}.printslices.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUT / f"{NAME}.resin-recipes.json").write_text(
        json.dumps({"resin_order": [name for name, _ in RESINS], "material_names": MATERIAL_NAMES, "recipes_by_material_id": RECIPES}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# menou — Stratasys Voxel Print 材料対応メモ",
        "",
        "## 出力条件",
        "",
        f"- X解像度: 600 DPI（{PITCH_X_M * 1000:.6f} mm/px）",
        f"- Y解像度: 300 DPI（{PITCH_Y_M * 1000:.6f} mm/px）",
        "- 積層ピッチ: 0.014 mm",
        f"- PNG: {width} × {height} px、{slices}層",
        "- 軸: 列=+X、行=+Y、ファイル順=+Z",
        "- 表面透明膜: 全6面に0.3 mm",
        "- PNGは32-bit RGBA（各8 bit）。背景色は使用せず、全ピクセルを6樹脂色のいずれかへ割り当て（Alpha=255）。",
        "",
        "## PNG色 → GrabCADで想定する材料",
        "",
        "|Index|RGB|想定材料|",
        "|---:|---|---|",
    ]
    for index, (name, rgb) in enumerate(RESINS, 1):
        lines.append(f"|{index}|{rgb[0]}, {rgb[1]}, {rgb[2]}|{name}|")
    lines += ["", "## 瑪瑙内の仮想材料配合", "", "配合値は White / Black / Clear / Cyan / Magenta / Yellow の体積比想定です。", "", "|ID|表現|W|B|Clear|C|M|Y|", "|---:|---|---:|---:|---:|---:|---:|---:|"]
    for material_id, recipe in RECIPES.items():
        lines.append(f"|{material_id}|{MATERIAL_NAMES[material_id]}|" + "|".join(f"{v:.3f}" for v in recipe) + "|")
    lines += [
        "",
        "## 注意",
        "",
        "- RGBは見た目の色指定ではなく、GrabCADが6種類の樹脂を識別するためのコードです。",
        "- 混合比は決定論的3Dディザリングで近似しています。隣接ピクセルの集合として体積比を実現します。",
        "- 光学レンダーは暫定係数によるプレビューであり、実機の色・透明度を保証する校正値ではありません。",
    ]
    (OUT / "材料対応メモ.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT), "width": width, "height": height, "slices": slices, "counts": counts.tolist()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
