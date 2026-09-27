"""Front view of a written resin slice stack (artifact_print p1 step 6).

For every slice, the first non-background pixel along printer +Y (the front) of each
column gives a resin colour; averaging 3x3 printer pixels (x) by 6 layers (z) gives a
rough "what the surface shows" image with square-ish pixels. Also saves the middle slice.
Usage: venv/bin/python work/artifact_print/stack_front_view.py SLICE_DIR OUT_PREFIX
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

d, prefix = Path(sys.argv[1]), sys.argv[2]
files = sorted(d.glob("slice_*.png"))
rows = []
for f in files:
    a = np.asarray(Image.open(f))
    occ = a[..., 3] > 0
    first = np.argmax(occ, axis=0)
    has = occ.any(0)
    rgb = a[first, np.arange(a.shape[1]), :3].astype(float)
    rgb[~has] = 255
    rows.append(rgb)
img = np.stack(rows[::-1])  # z up
z, w = img.shape[:2]
img = img[: z // 6 * 6, : w // 2 * 2].reshape(z // 6, 6, w // 2, 2, 3).mean((1, 3))
Image.fromarray(img.astype(np.uint8)).save(f"{prefix}-front.png")
mid = np.asarray(Image.open(files[len(files) // 2]))
bg = np.full(mid.shape[:2] + (3,), 255, np.uint8)
bg[mid[..., 3] > 0] = mid[mid[..., 3] > 0, :3]
Image.fromarray(bg).save(f"{prefix}-mid-slice.png")
print(img.shape, len(files))
