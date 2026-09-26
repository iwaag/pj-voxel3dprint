#!/usr/bin/env bash
# Rebuild the source label volumes and the archived optical zarr of the three
# batch1 prints from the generators in work/.  Every optical zarr produced here
# is byte-identical (zarr_store_sha256) to the optical_sha256 recorded in the
# archived casestudy/real_print/batch1/case*/data/outputs/*.session.json:
#   case1 .local/pink-agate-v3/viewer/pink-teal-agate-optical-v3.zarr   fa3dc222...
#   case2 .local/amber-branching/viewer/amber-branching-optical.zarr    3f5a815b...
#         .local/amber-branching/print-preview-v2/amber-print-black80-optical.zarr 6c59db58...
#   case3 .local/floating-fur/viewer/floating-fur-optical-v1.zarr       dac059d8...
# Run from the repository root.  Takes ~15 min (zarr convert is CPU bound).
set -euo pipefail
PY=vdbmat/.venv/bin/python
UPY=vdbmat-utils/.venv/bin/python
V=vdbmat/.venv/bin/vdbmat
U=vdbmat-utils/.venv/bin/vdbmat-utils

build() {  # source_manifest mapping material_zarr optical_zarr
  mkdir -p "$(dirname "$3")" "$(dirname "$4")"
  $V import-voxels --overwrite "$1" "$3" >/dev/null
  $V convert --overwrite --mapping-file "$2" "$3" "$4" >/dev/null
  echo "$4"
}

# case1 agate (printed from pink-teal-agate-strata-v3)
$PY work/agate/generate_pink_agate.py >/dev/null
build .local/pink-agate-v3/source/pink-teal-agate-strata-v3.voxels.json \
      .local/pink-agate-v3/source/pink-teal-agate-strata-v3.optical-mapping.json \
      .local/pink-agate-v3/viewer/pink-teal-agate-material-v3.zarr \
      .local/pink-agate-v3/viewer/pink-teal-agate-optical-v3.zarr

# case3 fur
$PY work/fur/generate_floating_fur.py >/dev/null
build .local/floating-fur/source/floating-fur-v1.voxels.json \
      .local/floating-fur/source/floating-fur-v1.optical-mapping.json \
      .local/floating-fur/viewer/floating-fur-material-v1.zarr \
      .local/floating-fur/viewer/floating-fur-optical-v1.zarr

# case2 amber: formation seed 4102 with the checked-in formation config, then
# the branching-vein pass.  (The archived seed-4101 in batch1 was made with an
# older pores threshold of 0.60; seed 4102 used today's 0.374.)
$U generate-formation --config work/amber/amber-preview.formation.json --seed 4102 \
   --out .local/amber-previews/source/seed-4102 --name amber-4102 >/dev/null
$UPY work/amber/generate_branching_veins.py >/dev/null
$UPY work/amber/build_print_preview_mapping.py >/dev/null
D=.local/amber-branching
build $D/source/amber-4102-branching-v2.voxels.json $D/source/amber-4102-branching-v2.optical-mapping.json \
      $D/viewer/amber-branching-material.zarr $D/viewer/amber-branching-optical.zarr
$V convert --overwrite --mapping-file $D/source/amber-4102-print-preview.optical-mapping.json \
      $D/viewer/amber-branching-material.zarr $D/print-preview-v2/amber-print-black80-optical.zarr >/dev/null
echo $D/print-preview-v2/amber-print-black80-optical.zarr
# the prints as photographed: mirror images of the volumes (p2 report3);
# amber lies bottom-up, which makes it a pure z-mirror
mirror() {  # source_stem axes material_zarr
  $PY work/compare/flip_volume.py "$1.voxels.json" "$1-mirror-$2.voxels.json" --axes "$2" >/dev/null
  $V import-voxels --overwrite "$1-mirror-$2.voxels.json" "$3" >/dev/null
  echo "$3"
}
mirror .local/pink-agate-v3/source/pink-teal-agate-strata-v3 y .local/pink-agate-v3/viewer/pink-teal-agate-material-v3-mirror-y.zarr
mirror .local/floating-fur/source/floating-fur-v1 y .local/floating-fur/viewer/floating-fur-material-v1-mirror-y.zarr
mirror $D/source/amber-4102-branching-v2 z $D/viewer/amber-branching-material-mirror-z.zarr
