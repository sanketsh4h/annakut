#!/usr/bin/env bash
# Final-quality splat with gsplat (MCMC strategy) on the TITAN V.
#
#   bash ~/sshah_workspace/projects/pipeline/02-train.sh <scan-dir> [max-splats] [downscale] [steps]
#
# Needs <scan-dir>/images/ and <scan-dir>/sparse/0/ (from 01-poses.sh).
# Defaults: 2,000,000 splats, photos downscaled 2x, 30,000 steps.
# Writes <scan-dir>/gsplat/ply/point_cloud_<step>.ply, and logs the machine's
# power draw to <scan-dir>/logs/power-train-<time>.csv.
set -euo pipefail
S="$(readlink -f "${1:?usage: 02-train.sh <scan-dir> [max-splats] [downscale] [steps]}")"
CAP="${2:-2000000}"; FACTOR="${3:-2}"; STEPS="${4:-30000}"
[ -d "$S/sparse/0" ] || { echo "no sparse/0 in $S, run 01-poses.sh first"; exit 1; }
set +u; source "$HOME/sshah_workspace/env/activate.sh"; set -u
# This machine is shared: give way to everyone else's work.
renice -n 15 -p $$ > /dev/null 2>&1 || true; ionice -c 3 -p $$ 2> /dev/null || true
mkdir -p "$S/logs"
# The trainer insists on an images_<N> folder and then makes its own
# downscaled copies in images_<N>_png; a link to the originals satisfies it.
if [ "$FACTOR" -gt 1 ] && [ ! -e "$S/images_$FACTOR" ]; then ln -s images "$S/images_$FACTOR"; fi

# Record peak memory on the TITAN V while training.
( peak=0; while sleep 10; do
    m=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 0 | tr -d ' ')
    [ "$m" -gt "$peak" ] && { peak=$m; echo "$peak" > "$S/logs/5-gsplat-peak-mib.txt"; }
  done ) &
mon=$!
# Log power draw while this runs (powerlog.sh). A new log every run.
PL="$(dirname "$(readlink -f "$0")")/powerlog.sh"; plog=""
PCSV="$S/logs/power-train-$(date +%Y%m%d-%H%M%S).csv"
stage() { echo "$1" > "$S/logs/power-stage"; }
power_stop() {
    [ -n "$plog" ] || return 0
    kill "$plog" 2> /dev/null || true; wait "$plog" 2> /dev/null || true; plog=""
    bash "$PL" summary "$PCSV" || true
}
trap 'kill $mon 2>/dev/null || true; power_stop' EXIT
if [ -f "$PL" ]; then
    stage "training"
    bash "$PL" sample "$PCSV" "$S/logs/power-stage" $$ & plog=$!
fi

t0=$(date +%s)
cd "$GSPLAT_EXAMPLES"
CUDA_VISIBLE_DEVICES=0 python simple_trainer.py mcmc \
    --data-dir "$S" --data-factor "$FACTOR" --result-dir "$S/gsplat" \
    --strategy.cap-max "$CAP" --max-steps "$STEPS" \
    --eval-steps "$STEPS" --save-steps "$STEPS" --save-ply --ply-steps "$STEPS" \
    --disable-viewer --disable-video
power_stop
echo "TIME training: $(( $(date +%s) - t0 )) s"
echo "PEAK TITAN V memory: $(cat "$S/logs/5-gsplat-peak-mib.txt") MiB"
ls -la "$S/gsplat/ply"
