#!/bin/sh
# Turn one trained splat (.ply / .sog / .spz ...) into a streamed, multi-detail
# scene the website can load:  site/scene/lod-meta.json + chunk files.
#
#   sh scripts/build-scene.sh <input-splat> [output-dir]
#
# A fresh scan comes out tilted. Set ROTATE to the "rotate" angles printed by
# the scan pipeline's scene_frame.py to stand it upright:
#
#   ROTATE=179.4,-36.2,170.8 sh scripts/build-scene.sh scan.ply site/scene
#
# The viewer downloads the lowest-detail level first and refines from there,
# within a splat budget it picks for the device.
set -eu

IN="${1:?usage: sh scripts/build-scene.sh <input-splat> [output-dir]}"
OUT="${2:-site/scene}"
TMP="build-tmp"
ST="node_modules/.bin/splat-transform"

mkdir -p "$TMP"
rm -rf "$OUT"
mkdir -p "$OUT"

# The bundling step only accepts local .ply files, so normalise the input first.
"$ST" -q -w "$IN" ${ROTATE:+-r "$ROTATE"} "$TMP/lod0.ply"

# Lower-detail copies. Decimation has to be the last action and write a .ply.
"$ST" -q -w "$TMP/lod0.ply" -d 50% "$TMP/lod1.ply"
"$ST" -q -w "$TMP/lod0.ply" -d 25% "$TMP/lod2.ply"
"$ST" -q -w "$TMP/lod0.ply" -d 10% "$TMP/lod3.ply"

# Bundle all levels into chunked SOG files. Level 0 is full detail.
"$ST" -q -w \
  "$TMP/lod0.ply" -l 0 \
  "$TMP/lod1.ply" -l 1 \
  "$TMP/lod2.ply" -l 2 \
  "$TMP/lod3.ply" -l 3 \
  "$OUT/lod-meta.json" \
  --filter-nan

rm -rf "$TMP"
"$ST" "$OUT/lod-meta.json" --info null
