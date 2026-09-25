#!/usr/bin/env bash
# Print-aware optical zarr for the three batch1 cases from one resin library.
# Usage (repo root): work/resins/build_print_aware.sh LIBRARY.json TAG [case ...]
#   cases: agate amber fur (default: all three, converted in parallel)
# Output: .local/<case dir>/print-aware-<TAG>/<name>.{resin-recipes,optical-mapping}.json
#         and <name>-optical.zarr.  Needs the material zarr from
#         work/compare/rebuild_batch1_sources.sh.
set -euo pipefail
LIB=$1; TAG=$2; shift 2
CASES=${*:-agate amber fur}
PY=vdbmat/.venv/bin/python
V=vdbmat/.venv/bin/vdbmat
one() {  # dir name export_script semantic_mapping material_zarr
  local out=.local/$1/print-aware-$TAG
  mkdir -p "$out"
  $PY work/resins/extract_recipes.py "$3" "$out/$2.resin-recipes.json" >/dev/null
  $PY work/resins/recipes_to_mapping.py --library "$LIB" --recipes "$out/$2.resin-recipes.json" \
      --semantic "$4" --out "$out/$2.optical-mapping.json" >/dev/null
  $V convert --overwrite --mapping-file "$out/$2.optical-mapping.json" "$5" "$out/$2-optical.zarr" >/dev/null
  echo "$out/$2-optical.zarr"
}
for c in $CASES; do
  case $c in
    agate) one pink-agate-v3 agate work/agate/export_menou_voxelprint.py \
             .local/pink-agate-v3/source/pink-teal-agate-strata-v3.optical-mapping.json \
             .local/pink-agate-v3/viewer/pink-teal-agate-material-v3.zarr & ;;
    amber) one amber-branching amber work/amber/export_kohaku_tree_voxelprint.py \
             .local/amber-branching/source/amber-4102-branching-v2.optical-mapping.json \
             .local/amber-branching/viewer/amber-branching-material.zarr & ;;
    fur)   one floating-fur fur work/fur/export_floating_fur_voxelprint.py \
             .local/floating-fur/source/floating-fur-v1.optical-mapping.json \
             .local/floating-fur/viewer/floating-fur-material-v1.zarr & ;;
    *) echo "unknown case $c" >&2; exit 2 ;;
  esac
done
wait
