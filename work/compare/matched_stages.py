"""Write one stage-config per matched photo: the print-photo preset + its camera.

Usage (repo root):

    vdbmat/.venv/bin/python work/compare/matched_stages.py SPEC_V3.json OUT_DIR [--preset P] [--size 512]

For each photo with a ``camera`` block (from ``match_camera.py``) this writes
``OUT_DIR/<case>-<photo stem>.stage.json``: the preset with ``camera``
replaced by the matched pose and the render size set to the photo's aspect
(long side ``--size``). The dome cap keeps the preset's tilt, but its azimuth
follows the camera: the ceiling light stays on the photographer's side, as in
step 1 (a hand-held phone above the slab blocks the light in the mirror
direction). It prints ``case zarr_kind stage_path`` lines for the render loop.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PRESET = ROOT / "vdbmat/examples/pipeline_run/demo/presets/stage-print-photo.stage.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("spec", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--preset", type=Path, default=PRESET)
    parser.add_argument("--size", type=int, default=512)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    preset = json.loads(args.preset.read_text())
    args.out_dir.mkdir(parents=True, exist_ok=True)
    centre = np.array([0.03, 0.015, 0.0025])
    for case, cdef in spec["cases"].items():
        for entry in cdef["images"]:
            if entry["kind"] != "photo" or "camera" not in entry:
                continue
            with Image.open(ROOT / entry["path"]) as im:
                w, h = im.size
            scale = args.size / max(w, h)
            stage = json.loads(json.dumps(preset))
            stage["render"]["width"] = max(16, round(w * scale))
            stage["render"]["height"] = max(16, round(h * scale))
            stage["camera"] = entry["camera"]
            d = np.asarray(entry["camera"]["position_m"]) - centre
            stage["ambient"]["cap_azimuth_deg"] = round(math.degrees(math.atan2(d[1], d[0])), 2)
            out = args.out_dir / f"{case}-{Path(entry['path']).stem}.stage.json"
            out.write_text(json.dumps(stage, indent=1) + "\n")
            print(case, entry["volume"], out)


if __name__ == "__main__":
    main()
