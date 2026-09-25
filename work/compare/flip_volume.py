"""Write a label volume mirrored along y and/or z (the print as it was photographed).

Usage (repo root):

    vdbmat/.venv/bin/python work/compare/flip_volume.py SRC.voxels.json DST.voxels.json --axes y|z|yz

p2 step 3 found that the batch1 prints are **mirror images** of the voxel
volumes: the photos only fit a camera above the slab when the model is
mirrored (see p2 report3). The stage has no object transform, so a render of
the print as photographed uses a mirrored input:

- ``y``: (x, y, z) -> (x, Y - y, z), the print lying top-up (agate, fur);
- ``z``: (x, y, z) -> (x, y, Z - z), the mirrored print lying bottom-up,
  which is a pure z-mirror (amber: its photos show the bottom face);
- ``yz``: 180 degrees about x (bottom-up without a mirror).

Material ids, voxel size and transform are unchanged.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("src", type=Path)
    parser.add_argument("dst", type=Path)
    parser.add_argument("--axes", choices=("y", "z", "yz"), required=True)
    args = parser.parse_args()
    doc = json.loads(args.src.read_text())
    labels = np.load(args.src.parent / doc["payload"]["path"])
    assert doc["payload"]["dimensions"] == ["z", "y", "x"]
    if "y" in args.axes:
        labels = labels[:, ::-1, :]
    if "z" in args.axes:
        labels = labels[::-1, :, :]
    npy = args.dst.with_name(args.dst.name.removesuffix(".voxels.json") + ".material_id.npy")
    np.save(npy, np.ascontiguousarray(labels))
    out = copy.deepcopy(doc)
    out["payload"]["path"] = npy.name
    out["payload"]["sha256"] = hashlib.sha256(npy.read_bytes()).hexdigest()
    source = out.setdefault("source", {})
    source["notes"] = (source.get("notes", "") + f" Mirrored along {args.axes} from {args.src.name}.").strip()
    args.dst.write_text(json.dumps(out, indent=2) + "\n")
    print(args.dst)


if __name__ == "__main__":
    main()
