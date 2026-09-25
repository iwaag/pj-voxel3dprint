#!/usr/bin/env bash
# Open a batch1 design in the Mitsuba stage viewer as the print is expected to
# look: the print-aware optical zarr of a resin library tag, on the
# stage-print-photo preset (white paper, dark room with one ceiling light).
# Usage (repo root): work/compare/view_print.sh agate|amber|fur [TAG=v3] [--mirror] [--deep] [extra viewer args]
#   --mirror   open the mirrored volume (the prints are mirror images of the
#              volumes, p2 report3; amber also lies bottom-up in the photos)
#   --deep     stage-print-photo-deep (path depth 256): needed for large white or
#              pale areas, which lose ~40 % at depth 32 (p2 report4); ~3x slower
# The Input tab lists every zarr under .local/<case dir>/ (semantic, print-aware
# tags, crops); the Preset tab lists the checked-in presets.
# Needs: work/resins/build_print_aware.sh work/resins/vero-j850-provisional-v3.json v3 [agate-m amber-m fur-m]
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
CASE=$1; shift
TAG=v3; [[ $# -gt 0 && $1 != --* ]] && { TAG=$1; shift; }
SUFFIX=""; [[ $# -gt 0 && $1 == --mirror ]] && { SUFFIX=-mirror; shift; }
PRESET=stage-print-photo; [[ $# -gt 0 && $1 == --deep ]] && { PRESET=stage-print-photo-deep; shift; }
case $CASE in
  agate) DIR=pink-agate-v3; NAME=agate ;;
  amber) DIR=amber-branching; NAME=amber ;;
  fur)   DIR=floating-fur; NAME=fur ;;
  *) echo "unknown case $CASE (agate|amber|fur)" >&2; exit 2 ;;
esac
ZARR=$ROOT/.local/$DIR/print-aware-$TAG/$NAME$SUFFIX-optical.zarr
[[ -d $ZARR ]] || { echo "missing $ZARR (build it with work/resins/build_print_aware.sh)" >&2; exit 1; }
cd "$ROOT/vdbmat"
unset VIRTUAL_ENV
exec uv run --group mitsuba-viewer python examples/pipeline_run/demo/mitsuba_stage_viewer.py -- \
  "$ZARR" --input-root "$ROOT/.local/$DIR" \
  --stage-config examples/pipeline_run/demo/presets/$PRESET.stage.json \
  --variant cuda_ad_rgb --work-dir "$ROOT/.local/viewer-work/$CASE" "$@"
