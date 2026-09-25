#!/usr/bin/env bash
# p2 step 5: fur crop at printer pitch (dither and effective) vs the 0.2 mm review grid.
# Usage (repo root): work/halftone/build_fur_crop.sh LIBRARY.json TAG
# Needs .local/floating-fur/print-aware-<TAG>/fur.optical-mapping.json
# (work/resins/build_print_aware.sh LIBRARY TAG fur).
# Output: .local/floating-fur/halftone-crop-<TAG>/fur-crop-{dither,effective,review}-optical.zarr
set -euo pipefail
LIB=$1; TAG=$2
PY=vdbmat/.venv/bin/python
V=vdbmat/.venv/bin/vdbmat
O=.local/floating-fur/halftone-crop-$TAG
$PY work/halftone/fur_halftone_crop.py --library "$LIB" --out "$O" >/dev/null
for kind in dither effective review; do
  $V import-voxels --overwrite "$O/fur-crop-$kind.voxels.json" "$O/fur-crop-$kind-material.zarr" >/dev/null
done
$V convert --overwrite --mapping-file "$O/vero6-resins.optical-mapping.json" \
  "$O/fur-crop-dither-material.zarr" "$O/fur-crop-dither-optical.zarr" >/dev/null
for kind in effective review; do
  $V convert --overwrite --mapping-file ".local/floating-fur/print-aware-$TAG/fur.optical-mapping.json" \
    "$O/fur-crop-$kind-material.zarr" "$O/fur-crop-$kind-optical.zarr" >/dev/null
done
ls -d "$O"/*-optical.zarr
