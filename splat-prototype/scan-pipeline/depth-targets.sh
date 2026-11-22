#!/usr/bin/env bash
# Stage 3 as one command: depth targets for the trainer's depth loss.
#
#   bash ~/sshah_workspace/projects/pipeline/depth-targets.sh <scan-dir>
#
# Needs <scan-dir>/images and <scan-dir>/sparse/0 (01-poses.sh), and the
# refine/ scripts next to this file. Runs COLMAP dense stereo on the GTX 1080,
# fuses it, and writes
#   <scan-dir>/depth/all.npz        stereo points per photo (refine/prep_depth.py)
#   <scan-dir>/depth/mono-all.npz   monocular depth for the gaps (refine/mono_depth.py)
# Train with them:  DENSE=$S/depth/all.npz MONO=$S/depth/mono-all.npz ... --depth-loss
#
# Options (environment variables):
#   HOLDOUT=a.jpg,b.jpg  photos kept out of the stereo, so a held-back score stays honest
#   DEPTH_SIZE=1600      longest side of the depth maps, in pixels (2400 was used for 15 photos)
#   DEPTH_SOURCES=12     how many other photos each photo is compared with
#   DEPTH_MIN_PIXELS=3   photos that must agree on a point (2 for under 20 photos, 5 is COLMAP's own)
# Time grows with the number of photos times DEPTH_SIZE squared. (Plain SIZE is
# taken: activating the tools sets it to something else.)
set -euo pipefail
S="$(readlink -f "${1:?usage: depth-targets.sh <scan-dir>}")"
DSIZE="${DEPTH_SIZE:-1600}"; SOURCES="${DEPTH_SOURCES:-12}"; MIN_PIXELS="${DEPTH_MIN_PIXELS:-3}"
HERE="$(dirname "$(readlink -f "$0")")"
[ -d "$S/sparse/0" ] || { echo "no sparse/0 in $S, run 01-poses.sh first"; exit 1; }
[ -f "$HERE/refine/prep_depth.py" ] || { echo "no refine/ scripts next to $0"; exit 1; }
set +u; source "$HOME/sshah_workspace/env/activate.sh"; set -u
# This machine is shared: CPUs 0-3 only, lowest priority, 2 threads.
renice -n 19 -p $$ > /dev/null 2>&1 || true; ionice -c 3 -p $$ 2> /dev/null || true; taskset -cp 0-3 $$ > /dev/null
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
M="$S/mvs"; mkdir -p "$S/logs" "$S/depth"
t0=$(date +%s); lap() { local now; now=$(date +%s); echo "TIME $1: $((now - t0)) s"; t0=$now; }

SP="$S/sparse/0"
if [ -n "${HOLDOUT:-}" ]; then
    SP="$S/sparse-mvs"; rm -rf "$SP"; mkdir -p "$SP"
    echo "$HOLDOUT" | tr ',' '\n' > "$S/logs/mvs-left-out.txt"
    colmap image_deleter --input_path "$S/sparse/0" --output_path "$SP" \
        --image_names_path "$S/logs/mvs-left-out.txt" > "$S/logs/3-mvs.log" 2>&1
fi
rm -rf "$M"
colmap image_undistorter --image_path "$S/images" --input_path "$SP" --output_path "$M" \
    --output_type COLMAP --num_threads 2 >> "$S/logs/3-mvs.log" 2>&1
sed -i "s/^__auto__, .*/__auto__, $SOURCES/" "$M/stereo/patch-match.cfg"
lap "undistort"
colmap patch_match_stereo --workspace_path "$M" --PatchMatchStereo.max_image_size "$DSIZE" \
    --PatchMatchStereo.gpu_index 1 --PatchMatchStereo.geom_consistency 1 \
    --PatchMatchStereo.num_threads 2 >> "$S/logs/3-mvs.log" 2>&1
lap "dense stereo"
colmap stereo_fusion --workspace_path "$M" --input_type geometric --output_path "$M/fused.ply" \
    --StereoFusion.max_image_size "$DSIZE" --StereoFusion.min_num_pixels "$MIN_PIXELS" \
    --StereoFusion.num_threads 2 >> "$S/logs/3-mvs.log" 2>&1
lap "fusion"
echo "fused points: $(grep -a -m1 'element vertex' "$M/fused.ply" | cut -d' ' -f3)"
[ -e "$S/images_2" ] || ln -s images "$S/images_2"
python "$HERE/refine/prep_depth.py" "$S" "$M/fused.ply" "$S/depth/all.npz" > "$S/logs/3-prep.log" 2>&1 \
    || { tail -5 "$S/logs/3-prep.log"; echo "stereo targets failed, see $S/logs/3-prep.log"; exit 1; }
tail -3 "$S/logs/3-prep.log"
lap "stereo targets"
# The depth model needs the "transformers" package, which the main tools do not
# have. In 2025 it was put in a small environment of its own, on top of them:
#   python -m venv --system-site-packages <folder> && <folder>/bin/pip install transformers
# MONO_PYTHON names that environment's python; HF_HOME is where the model is kept.
OLD="$HOME/sshah_workspace/projects/annakut-2025-splat-v1"
PY=""
for c in "${MONO_PYTHON:-}" python "$HERE/venv-mono/bin/python" "$OLD/venv-mono/bin/python"; do
    [ -n "$c" ] && "$c" -c "import transformers" 2> /dev/null && { PY="$c"; break; }
done
[ -n "$PY" ] || { echo "no python with the transformers package: set MONO_PYTHON (see the note in $0). depth/all.npz is written; mono-all.npz is not."; exit 1; }
[ -n "${HF_HOME:-}" ] || { [ -d "$OLD/hf-cache" ] && export HF_HOME="$OLD/hf-cache"; }
CUDA_VISIBLE_DEVICES=1 "$PY" "$HERE/refine/mono_depth.py" "$S" "$S/depth/all.npz" "$S/depth/mono-all.npz" > "$S/logs/3-mono.log" 2>&1 \
    || { tail -5 "$S/logs/3-mono.log"; echo "monocular depth failed, see $S/logs/3-mono.log"; exit 1; }
tail -3 "$S/logs/3-mono.log"
lap "monocular depth"
rm -rf "$M/stereo/depth_maps" "$M/stereo/normal_maps" "$M/images"   # large, and not needed again
ls -la "$S/depth"
