#!/usr/bin/env bash
# A small object, from frames to a cropped, upright splat, in one command.
#
#   bash ~/sshah_workspace/projects/pipeline/object.sh <scan-dir> [steps] [max-splats]
#
# <scan-dir> is the folder video_to_frames.py wrote with --subject object,
# copied here whole (it needs images/). Runs, in order:
#   1. camera positions      01-poses.sh with MATCHER=sequential
#   2. training              02-train.sh: 30,000 steps, 500,000 splats, half-size frames
#   3. crop and stand up     refine/crop_object.py
# and writes <scan-dir>/clean/object.ply and object.json. Then, on the Mac:
#   sh scripts/object-scene.sh <name> <scan-dir's name>
#
# A stage whose result is already there is skipped, so a run that stopped can
# be started again. REDO=1 runs everything again. It stops after stage 1 if
# fewer than 90% of the frames were placed (FORCE=1 goes on anyway).
# CROP="--floor keep" passes options to the crop.
#
# No depth targets: on the test chair they added a false sheet under the seat
# and did not raise the score (PIPELINE.md, stage 3).
set -euo pipefail
S="$(readlink -f "${1:?usage: object.sh <scan-dir> [steps] [max-splats]}")"
STEPS="${2:-30000}"; CAP="${3:-500000}"
HERE="$(dirname "$(readlink -f "$0")")"
[ -d "$S/images" ] || { echo "no images/ in $S"; exit 1; }
[ -f "$HERE/refine/crop_object.py" ] || { echo "no refine/crop_object.py next to $0"; exit 1; }
set +u; source "$HOME/sshah_workspace/env/activate.sh"; set -u
# This machine is shared: CPUs 0-3 only, lowest priority, 2 threads.
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
low() { taskset -c 0-3 nice -n 19 "$@"; }
mkdir -p "$S/logs" "$S/clean"
T0=$(date +%s); t0=$T0; lap() { local now; now=$(date +%s); echo "TIME $1: $((now - t0)) s"; t0=$now; }
[ -n "${REDO:-}" ] && rm -rf "$S/sparse" "$S/colmap.db" "$S/gsplat"

echo "### 1. camera positions"
if [ -d "$S/sparse/0" ]; then
    echo "already there, skipped"
else
    THREADS=2 MATCHER=sequential low bash "$HERE/01-poses.sh" "$S" > "$S/logs/object-poses.out" 2>&1 \
        || { tail -5 "$S/logs/object-poses.out"; echo "stage 1 failed, see $S/logs/object-poses.out"; exit 1; }
    lap "camera positions"
fi
total=$(find "$S/images" -maxdepth 1 \( -type f -o -type l \) | wc -l)
placed=$(colmap model_analyzer --path "$S/sparse/0" 2>&1 | grep -a "Registered images" | grep -oE "[0-9]+$" || true); placed=${placed:-0}
echo "placed: $placed of $total frames"
if [ $((placed * 10)) -lt $((total * 9)) ] && [ -z "${FORCE:-}" ]; then
    echo "Fewer than 90% of the frames connected. The video moved too fast, was too blurred, or has"
    echo "too little pattern round the object. Reshoot, or go on with what connected: FORCE=1."
    exit 1
fi

echo "### 2. training ($STEPS steps, up to $CAP splats)"
PLY="$S/gsplat/ply/point_cloud_$((STEPS - 1)).ply"
if [ -f "$PLY" ]; then
    echo "already there, skipped"
else
    low bash "$HERE/02-train.sh" "$S" "$CAP" 2 "$STEPS" > "$S/logs/object-train.out" 2>&1 \
        || { tail -5 "$S/logs/object-train.out"; echo "stage 2 failed, see $S/logs/object-train.out"; exit 1; }
    lap "training"
fi

echo "### 3. crop and stand up"
# shellcheck disable=SC2086
low python "$HERE/refine/crop_object.py" "$S" "$PLY" "$S/clean/object.ply" --json "$S/clean/object.json" ${CROP:-} \
    > "$S/logs/object-crop.out" 2>&1 || { tail -5 "$S/logs/object-crop.out"; echo "stage 3 failed, see $S/logs/object-crop.out"; exit 1; }
lap "crop"
python - "$S/clean/object.json" <<'EOF'
import json, sys
o = json.load(open(sys.argv[1])); ring = o["camera_ring"]
print(f"kept {o['kept']:,} of {o['splats']:,} splats; object about {2 * o['radius'] / o['d']:.2f} wide and {o['height'] / o['d']:.2f} tall, in camera distances")
print(f"cameras looked down {ring['looked_down_deg'][0]:.0f} to {ring['looked_down_deg'][1]:.0f} degrees; largest unfilmed gap round the object {ring['largest_gap_deg']:.0f} degrees")
if not o["floor_found"]:
    print("WARNING: no floor found, so 'up' is the cameras' guess. Check that the object stands straight.")
if ring["largest_gap_deg"] > 30:
    print("WARNING: part of the way round was not filmed. That side of the model is a guess.")
if ring["looked_down_deg"][1] - ring["looked_down_deg"][0] < 25:
    print("NOTE: every frame looked down at about the same angle (one ring). Sides and undersides seen from other heights are a guess.")
EOF
echo "TIME in all: $(( $(date +%s) - T0 )) s"
echo "On the Mac:  sh scripts/object-scene.sh <name> $(basename "$S")"
