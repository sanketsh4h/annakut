#!/usr/bin/env bash
# How close together do the photos need to be? Trains the same scan from every
# frame, every 2nd, every 4th ... and scores each model on frames none of them
# saw. Where the score stops improving is the spacing to shoot and keep at.
#
#   bash ~/sshah_workspace/projects/pipeline/spacing_study.sh <scan-dir> [steps] [max-splats]
#
# Needs <scan-dir>/sparse/0 from 01-poses.sh (frames named in shooting order,
# as video_to_frames.py writes them) and the refine/ scripts next to this file.
# Every 10th frame is held back as the test set for all the runs. For each
# thinning K (default: KS="1 2 4 8 16") it
#   1. recomputes camera positions from the thinned frames alone, to see
#      whether they still connect, and
#   2. trains a splat from the thinned frames, using the full scan's camera
#      positions so every run is scored on the same views.
# Writes <scan-dir>/study/results.tsv and prints it. Defaults: 7,000 steps and
# 500,000 splats per run, which is a quick look, not final quality.
set -euo pipefail
S="$(readlink -f "${1:?usage: spacing_study.sh <scan-dir> [steps] [max-splats]}")"
STEPS="${2:-7000}"; CAP="${3:-500000}"; KS="${KS:-1 2 4 8 16}"
HERE="$(dirname "$(readlink -f "$0")")"
[ -d "$S/sparse/0" ] || { echo "no sparse/0 in $S, run 01-poses.sh first"; exit 1; }
[ -f "$HERE/refine/run.sh" ] || { echo "no refine/ scripts next to $0"; exit 1; }
set +u; source "$HOME/sshah_workspace/env/activate.sh"; set -u
D="$S/study"; mkdir -p "$D/txt" "$S/images_2_png"
[ -e "$S/images_2" ] || ln -s images "$S/images_2"
colmap model_converter --input_path "$S/sparse/0" --output_path "$D/txt" --output_type TXT > /dev/null 2>&1

python - "$S" "$D" $KS <<'EOF'
import csv, os, sys
S, D, ks = sys.argv[1], sys.argv[2], [int(k) for k in sys.argv[3:]]
rows = [l.split() for l in open(f"{D}/txt/images.txt") if not l.startswith("#")][0::2]
placed = sorted(r[9] for r in rows if len(r) >= 10)
frames = [n for n in placed if not n.startswith("still_")]
test = frames[5::10]
rest = [n for n in frames if n not in test]
travel = {}
if os.path.exists(f"{S}/frames.csv"):
    travel = {r["kept_as"]: float(r["travel"]) for r in csv.DictReader(open(f"{S}/frames.csv")) if r["kept_as"]}
open(f"{D}/test.txt", "w").write("\n".join(test) + "\n")
with open(f"{D}/plan.tsv", "w") as f:
    for k in ks:
        keep = rest[::k]
        os.makedirs(f"{D}/k{k}", exist_ok=True)
        open(f"{D}/k{k}/keep.txt", "w").write("\n".join(keep) + "\n")
        open(f"{D}/k{k}/delete.txt", "w").write("".join(n + "\n" for n in placed if n not in keep and n not in test))
        gaps = [travel[b] - travel[a] for a, b in zip(keep, keep[1:])] if all(n in travel for n in keep) else []
        f.write(f"{k}\t{len(keep)}\t{100 * sum(gaps) / len(gaps) if gaps else float('nan'):.1f}\n")
print(f"{len(frames)} frames placed; {len(test)} held back for scoring; thinning {ks}")
EOF

for k in $KS; do
    K="$D/k$k"; n=$(wc -l < "$K/keep.txt")
    echo "### every ${k}: $n frames"
    # 1. Do the thinned frames still connect on their own?
    rm -rf "$K/poses"; mkdir -p "$K/poses/images"
    while read -r f; do ln -s "$S/images/$f" "$K/poses/images/$f"; done < "$K/keep.txt"
    t0=$(date +%s)
    THREADS=2 MATCHER=sequential taskset -c 0-3 nice -n 19 bash "$HERE/01-poses.sh" "$K/poses" > "$K/poses.log" 2>&1 || true
    echo "$(( $(date +%s) - t0 ))" > "$K/poses.seconds"
    # 2. Train on them, with the full scan's camera positions.
    rm -rf "$K/sparse" "$K/runs"; mkdir -p "$K/sparse/0" "$K/logs"
    if [ -s "$K/delete.txt" ]; then
        colmap image_deleter --input_path "$S/sparse/0" --output_path "$K/sparse/0" \
            --image_names_path "$K/delete.txt" > "$K/logs/delete.log" 2>&1
    else
        cp "$S/sparse/0"/* "$K/sparse/0/"
    fi
    ln -sfn "$S/images" "$K/images"; ln -sfn images "$K/images_2"
    ln -sfn "$S/images_2_png" "$K/images_2_png"   # one set of half-size copies for all runs
    ln -sfn "$HERE/refine" "$K/tools"
    HOLDOUT="$(paste -sd, "$D/test.txt")" INIT_PTS=0 bash "$K/tools/run.sh" run -- \
        --data-factor 2 --strategy.cap-max "$CAP" --max-steps "$STEPS" \
        --eval-steps "$STEPS" --save-steps "$STEPS" > "$K/logs/train.log" 2>&1 || echo "    training failed, see $K/logs/train.log"
    rm -rf "$K/runs/run/ckpts"
done

python - "$D" "$STEPS" <<'EOF' | tee "$D/results.tsv"
import json, os, re, sys
D, steps = sys.argv[1], int(sys.argv[2])
print("every\tframes\tspacing_%_of_width\tplaced\tposes_s\ttrain_s\tPSNR\tSSIM\tLPIPS")
for k, n, gap in (l.split("\t") for l in open(f"{D}/plan.tsv").read().splitlines()):
    K = f"{D}/k{k}"
    log = open(f"{K}/poses.log").read() if os.path.exists(f"{K}/poses.log") else ""
    reg = re.search(r"placed: (\d+) of", log); models = re.search(r"separate models: (\d+)", log)
    connect = f"{reg.group(1)}/{n}" + (f" ({models.group(1)} models)" if models.group(1) != "1" else "") if reg and models else "0/" + n
    try:
        v = json.load(open(f"{K}/runs/run/stats/val_step{steps - 1:04d}.json"))
        score = f"{v['psnr']:.2f}\t{v['ssim']:.3f}\t{v['lpips']:.3f}"
    except OSError:
        score = "-\t-\t-"
    t = re.search(r"TIME (\d+)", open(f"{K}/runs/run/time.txt").read()) if os.path.exists(f"{K}/runs/run/time.txt") else None
    print(f"{k}\t{n}\t{gap}\t{connect}\t{open(f'{K}/poses.seconds').read().strip()}\t{t.group(1) if t else '-'}\t{score}")
EOF
