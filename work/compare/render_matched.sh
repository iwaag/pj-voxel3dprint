#!/usr/bin/env bash
# Render every matched photo view (p2 step 3) with one resin library tag.
# Usage (repo root): work/compare/render_matched.sh TAG OUT_DIR [extra render_stage args]
# Needs .local/<case>/print-aware-<TAG>/<name>-mirror-optical.zarr
# (work/resins/build_print_aware.sh LIB TAG agate-m amber-m fur-m) and the stage
# files from work/compare/matched_stages.py in OUT_DIR/stages/.
set -euo pipefail
TAG=$1; OUT=$2; shift 2
declare -A ZARR=(
  [agate]=.local/pink-agate-v3/print-aware-$TAG/agate-mirror-optical.zarr
  [amber]=.local/amber-branching/print-aware-$TAG/amber-mirror-optical.zarr
  [fur]=.local/floating-fur/print-aware-$TAG/fur-mirror-optical.zarr
)
for stage in "$OUT"/stages/*.stage.json; do
  name=$(basename "$stage" .stage.json); case=${name%%-*}
  s=$(date +%s)
  work/compare/render_stage.sh "${ZARR[$case]}" "$OUT/$name-$TAG.png" --stage-config "$(realpath "$stage")" "$@"
  echo "$name $TAG $(( $(date +%s) - s )) s"
done
