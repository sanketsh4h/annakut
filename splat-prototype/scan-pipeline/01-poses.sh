#!/usr/bin/env bash
# Camera poses for a folder of photos, with COLMAP.
#
#   bash ~/sshah_workspace/projects/pipeline/01-poses.sh <scan-dir>
#
# <scan-dir>/images/ holds the photos. Writes <scan-dir>/colmap.db and
# <scan-dir>/sparse/0/, and prints how many photos were placed. Also logs the
# machine's power draw to <scan-dir>/logs/power-poses-<time>.csv.
#
# Options (environment variables):
#   REUSE_MATCHES=1   keep an existing colmap.db and only redo the mapping
#   THREADS=4         cap COLMAP to this many CPU threads (default: all of them)
#   MAPPER=global     use COLMAP's fast global mapper instead of the default
#                     incremental one. Not recommended: on the South Building
#                     test set it reported all 128 photos placed but put 53 of
#                     them on the wrong side of the building (similar-looking
#                     facades), which ruined the splat.
set -euo pipefail
S="$(readlink -f "${1:?usage: 01-poses.sh <scan-dir>}")"
MAPPER="${MAPPER:-incremental}"
THREADS="${THREADS:--1}"   # -1 lets COLMAP use every thread
[ -d "$S/images" ] || { echo "no images/ folder in $S"; exit 1; }
set +u; source "$HOME/sshah_workspace/env/activate.sh"; set -u
# This machine is shared: give way to everyone else's work.
renice -n 15 -p $$ > /dev/null; ionice -c 3 -p $$ 2> /dev/null || true
mkdir -p "$S/logs" "$S/sparse"
# Log power draw while this runs (powerlog.sh). A new log every run.
PL="$(dirname "$(readlink -f "$0")")/powerlog.sh"; plog=""
PCSV="$S/logs/power-poses-$(date +%Y%m%d-%H%M%S).csv"
stage() { echo "$1" > "$S/logs/power-stage"; }
power_stop() {
    [ -n "$plog" ] || return 0
    kill "$plog" 2> /dev/null || true; wait "$plog" 2> /dev/null || true; plog=""
    bash "$PL" summary "$PCSV" || true
}
if [ -f "$PL" ]; then
    bash "$PL" sample "$PCSV" "$S/logs/power-stage" $$ & plog=$!
    trap power_stop EXIT
fi
t0=$(date +%s); lap() { local now; now=$(date +%s); echo "TIME $1: $((now - t0)) s"; t0=$now; }

echo "### photos: $(ls "$S/images" | wc -l)"
if [ "${REUSE_MATCHES:-0}" = 1 ] && [ -f "$S/colmap.db" ]; then
    echo "### reusing features and matches in colmap.db"
else
    rm -f "$S/colmap.db"
    stage "feature extraction"
    colmap feature_extractor --database_path "$S/colmap.db" --image_path "$S/images" \
        --ImageReader.single_camera 1 --FeatureExtraction.use_gpu 1 \
        --FeatureExtraction.num_threads "$THREADS" > "$S/logs/1-extract.log" 2>&1
    lap "feature extraction"
    stage "matching"
    colmap exhaustive_matcher --database_path "$S/colmap.db" \
        --FeatureMatching.use_gpu 1 --FeatureMatching.num_threads "$THREADS" > "$S/logs/2-match.log" 2>&1
    lap "matching"
fi

rm -rf "$S/sparse"/*
stage "mapping"
if [ "$MAPPER" = global ]; then
    colmap global_mapper --database_path "$S/colmap.db" --image_path "$S/images" \
        --output_path "$S/sparse" --GlobalMapper.num_threads "$THREADS" > "$S/logs/3-mapper.log" 2>&1
else
    colmap mapper --database_path "$S/colmap.db" --image_path "$S/images" \
        --output_path "$S/sparse" --Mapper.num_threads "$THREADS" > "$S/logs/3-mapper.log" 2>&1
fi
lap "mapping ($MAPPER)"
power_stop

echo "### result"
n=$(find "$S/sparse" -mindepth 1 -maxdepth 1 -type d | wc -l)
echo "separate models: $n   (more than 1 means the photos did not all connect; sparse/0 is used)"
colmap model_analyzer --path "$S/sparse/0" 2>&1 | grep -E "Cameras|Images|Registered|Points|Mean (track|observations|reprojection)" | sed -E 's/^.*\] //'
