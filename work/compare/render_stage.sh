#!/usr/bin/env bash
# Headless render of one optical zarr through a stage preset.
# Usage (repo root): work/compare/render_stage.sh OPTICAL_ZARR OUT.png [extra mitsuba_stage_demo args]
# Default preset: stage-print-photo; override with --stage-config (later args win).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
zarr=$(realpath "$1"); out=$(realpath -m "$2"); shift 2
cd "$ROOT/vdbmat"
unset VIRTUAL_ENV
uv run --group mitsuba python examples/pipeline_run/demo/mitsuba_stage_demo.py -- \
  "$zarr" "$out" \
  --stage-config examples/pipeline_run/demo/presets/stage-print-photo.stage.json \
  --variant cuda_ad_rgb "$@" 2>&1 | grep -E "PIXELSTATS|Error|error" || true
rm -rf "${out%.png}_scene"
