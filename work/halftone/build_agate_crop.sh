#!/usr/bin/env bash
# p1 step 5: dither vs effective-medium agate crop, material + optical zarr.
# Usage (repo root): work/halftone/build_agate_crop.sh LIBRARY.json TAG
# Needs .local/pink-agate-v3/print-aware-<TAG>/agate.optical-mapping.json
# (work/resins/build_print_aware.sh LIBRARY TAG agate).
# Output: .local/pink-agate-v3/halftone-crop-<TAG>/agate-crop-{dither,effective}-optical.zarr
set -euo pipefail
LIB=$1; TAG=$2
PY=vdbmat/.venv/bin/python
V=vdbmat/.venv/bin/vdbmat
O=.local/pink-agate-v3/halftone-crop-$TAG
$PY work/halftone/agate_halftone_crop.py --library "$LIB" --out "$O" 2>/dev/null
for kind in dither effective; do
  $V import-voxels --overwrite "$O/agate-crop-$kind.voxels.json" "$O/agate-crop-$kind-material.zarr" >/dev/null
done
$V convert --overwrite --mapping-file "$O/vero6-resins.optical-mapping.json" \
  "$O/agate-crop-dither-material.zarr" "$O/agate-crop-dither-optical.zarr" >/dev/null
$V convert --overwrite --mapping-file ".local/pink-agate-v3/print-aware-$TAG/agate.optical-mapping.json" \
  "$O/agate-crop-effective-material.zarr" "$O/agate-crop-effective-optical.zarr" >/dev/null
ls -d "$O"/*-optical.zarr
