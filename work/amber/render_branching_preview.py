from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
ARRAY = ROOT / ".local" / "amber-branching" / "source" / "amber-4102-branching-v2.material_id.npy"
OUTPUT = ROOT / "outputs" / "amber-branching-veins-preview.png"
COLORS = np.asarray(
    [
        (15, 15, 18), (150, 79, 18), (172, 94, 22), (194, 113, 30),
        (216, 140, 48), (235, 171, 77), (64, 24, 8), (255, 229, 151),
        (91, 39, 12), (128, 61, 18), (169, 93, 28),
    ], dtype=np.uint8,
)


def fit(labels: np.ndarray, width: int, height: int) -> Image.Image:
    image = Image.fromarray(COLORS[labels], "RGB")
    scale = min(width / image.width, height / image.height)
    return image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.NEAREST)


def main() -> None:
    arr = np.load(ARRAY, mmap_mode="r")
    slices = [arr[arr.shape[0] // 2], arr[:, arr.shape[1] // 2, :], arr[:, :, arr.shape[2] // 2]]
    titles = ["Top / XY — 20 main veins + local branches", "Longitudinal / XZ", "Transverse / YZ"]
    canvas = Image.new("RGB", (1500, 760), (244, 239, 228))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=20)
    small = ImageFont.load_default(size=15)
    draw.text((35, 25), "Branching amber vein preview — 60 × 30 × 5 mm, 0.20 mm voxel", fill=(35, 28, 20), font=font)
    for i, (labels, title) in enumerate(zip(slices, titles, strict=True)):
        panel = fit(labels, 450, 520)
        x = 30 + i * 490 + (450 - panel.width) // 2
        y = 105 + (520 - panel.height) // 2
        canvas.paste(panel, (x, y))
        draw.rectangle((29 + i * 490, 104, 481 + i * 490, 626), outline=(120, 98, 70))
        draw.text((35 + i * 490, 72), title, fill=(55, 42, 29), font=small)
    labels = [(6, "dark"), (8, "deep"), (9, "warm"), (10, "golden"), (7, "clear region")]
    x = 40
    for mid, text in labels:
        draw.rectangle((x, 680, x + 28, 708), fill=tuple(COLORS[mid]), outline=(60, 45, 30))
        draw.text((x + 36, 684), text, fill=(45, 34, 24), font=small)
        x += 220
    draw.text((1110, 684), "veins 16.65% / clear 3.04%", fill=(45, 34, 24), font=small)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
