#!/usr/bin/env bash
# One splat-v1 run: TITAN V only, CPUs 0-3 at nice 19, 2 threads (v0's run.sh, with v1_train.py).
#   HOLDOUT=... DENSE=... MASKS=... bash tools/run.sh <name> -- <simple_trainer args...>
set -euo pipefail
S="$(cd "$(dirname "$0")/.." && pwd)"
NAME="$1"; shift; [ "$1" = "--" ] && shift
set +u; source "$HOME/sshah_workspace/env/activate.sh"; set -u
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 CUDA_VISIBLE_DEVICES=0
OUT="$S/runs/$NAME"; mkdir -p "$OUT" "$S/logs"
PL="$HOME/sshah_workspace/projects/pipeline/powerlog.sh"
echo "train $NAME" > "$S/logs/power-stage"
bash "$PL" sample "$S/logs/power-train-$NAME.csv" "$S/logs/power-stage" $$ & plog=$!
( peak=0; while sleep 5; do
    m=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 0 | tr -d ' ')
    [ "$m" -gt "$peak" ] && { peak=$m; echo "$peak" > "$OUT/peak-mib.txt"; }
  done ) & mon=$!
trap 'kill $mon $plog 2>/dev/null || true' EXIT
t0=$(date +%s)
{ echo "HOLDOUT=${HOLDOUT-} DENSE=${DENSE-} MASKS=${MASKS-} MONO=${MONO-} INIT_PTS=${INIT_PTS-} DEPTH_PTS=${DEPTH_PTS-}"; echo "$*"; } > "$OUT/cmd.txt"
taskset -c 0-3 nice -n 19 python "$S/tools/v1_train.py" mcmc \
    --data-dir "$S" --result-dir "$OUT" --disable-viewer --disable-video "$@"
echo "TIME $(( $(date +%s) - t0 )) s" | tee "$OUT/time.txt"
echo "PEAK $(cat "$OUT/peak-mib.txt") MiB (whole TITAN V, incl ~90 MiB desktop)" | tee -a "$OUT/time.txt"
kill $mon $plog 2>/dev/null || true; wait $plog 2>/dev/null || true
bash "$PL" summary "$S/logs/power-train-$NAME.csv" | tee -a "$OUT/time.txt" || true
echo idle > "$S/logs/power-stage"
