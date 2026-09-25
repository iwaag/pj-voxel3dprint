from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / ".local" / "amber-previews" / "source"
OUTPUT = ROOT / "outputs" / "amber-seed-comparison.png"

COLORS = np.asarray(
    [
        (15, 15, 18),
        (150, 79, 18),
        (172, 94, 22),
        (194, 113, 30),
        (216, 140, 48),
        (235, 171, 77),
        (67, 27, 10),
        (255, 229, 151),
    ],
    dtype=np.uint8,
)


def fit_slice(labels: np.ndarray, box_w: int, box_h: int) -> Image.Image:
    rgb = COLORS[labels]
    image = Image.fromarray(rgb, "RGB")
    scale = min(box_w / image.width, box_h / image.height)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(size, Image.Resampling.NEAREST)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default(size=18)
    small = ImageFont.load_default(size=14)
    canvas = Image.new("RGB", (1500, 1060), (244, 239, 228))
    draw = ImageDraw.Draw(canvas)
    draw.text((40, 25), "Amber voxel seed comparison — 60 × 30 × 5 mm, preview voxel 0.20 mm", fill=(35, 29, 22), font=font)
    headers = ["Top / XY (mid Z)", "Longitudinal / XZ (mid Y)", "Transverse / YZ (mid X)"]
    for col, header in enumerate(headers):
        draw.text((320 + col * 390, 75), header, fill=(55, 44, 31), font=small)

    for row, seed in enumerate((4101, 4102, 4103)):
        arr = np.load(SOURCE / f"seed-{seed}" / f"amber-{seed}.material_id.npy", mmap_mode="r")
        slices = [arr[arr.shape[0] // 2, :, :], arr[:, arr.shape[1] // 2, :], arr[:, :, arr.shape[2] // 2]]
        y0 = 120 + row * 280
        draw.text((42, y0 + 95), f"seed {seed}", fill=(55, 37, 20), font=font)
        bubble_pct = float(np.count_nonzero(arr == 7)) * 100.0 / arr.size
        vein_pct = float(np.count_nonzero(arr == 6)) * 100.0 / arr.size
        draw.text((42, y0 + 130), f"clear regions {bubble_pct:.2f}%", fill=(70, 54, 38), font=small)
        draw.text((42, y0 + 153), f"dark veins {vein_pct:.2f}%", fill=(70, 54, 38), font=small)
        for col, labels in enumerate(slices):
            panel = fit_slice(labels, 360, 230)
            px = 285 + col * 400 + (360 - panel.width) // 2
            py = y0 + (230 - panel.height) // 2
            canvas.paste(panel, (px, py))
            draw.rectangle((284 + col * 400, y0 - 1, 646 + col * 400, y0 + 231), outline=(128, 107, 79), width=1)

    legend_y = 980
    labels = ["80%", "85%", "90%", "95%", "100%", "dark vein", "clear region"]
    ids = [1, 2, 3, 4, 5, 6, 7]
    draw.text((40, legend_y), "Material classes:", fill=(35, 29, 22), font=small)
    x = 200
    for material_id, label in zip(ids, labels, strict=True):
        draw.rectangle((x, legend_y, x + 24, legend_y + 24), fill=tuple(COLORS[material_id]), outline=(60, 50, 40))
        draw.text((x + 31, legend_y + 2), label, fill=(45, 36, 27), font=small)
        x += 165

    canvas.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
