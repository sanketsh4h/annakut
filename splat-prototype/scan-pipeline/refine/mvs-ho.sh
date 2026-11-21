#!/usr/bin/env bash
# Dense stereo + fusion without the held-out photos, same settings as mesh-v0's mvs-ho:
#   bash tools/mvs-ho.sh <name> IMG_a.jpg IMG_b.jpg     -> mvs-<name>/fused.ply
# GTX 1080 (GPU 1), CPUs 0-3, nice 19, idle IO. Photos are mesh-v0's full-size copies.
set -euo pipefail
V1=~/sshah_workspace/projects/annakut-2025-splat-v1; M0=~/sshah_workspace/projects/annakut-2025-mesh-v0
NAME=$1; shift
set +u; source ~/sshah_workspace/env/activate.sh; set -u
renice -n 19 -p $$ >/dev/null; ionice -c 3 -p $$ 2>/dev/null || true; taskset -cp 0-3 $$ >/dev/null
SP=$V1/sparse-$NAME; M=$V1/mvs-$NAME; L=$V1/logs; mkdir -p $SP $L
printf "%s\n" "$@" > $SP/deleted.txt
t0=$(date +%s)
[ -f $SP/images.bin ] || colmap image_deleter --input_path $V1/sparse/0 --output_path $SP --image_names_path $SP/deleted.txt
[ -f $M/sparse/cameras.bin ] || colmap image_undistorter --image_path $M0/images --input_path $SP --output_path $M --output_type COLMAP --num_threads 2
sed -i "s/^__auto__, .*/__auto__, 14/" $M/stereo/patch-match.cfg
echo "undistort $(( $(date +%s)-t0 )) s"
colmap patch_match_stereo --workspace_path $M --PatchMatchStereo.max_image_size 2400 --PatchMatchStereo.gpu_index 1 \
   --PatchMatchStereo.geom_consistency 1 --PatchMatchStereo.num_threads 2
echo "patchmatch done $(( $(date +%s)-t0 )) s"
colmap stereo_fusion --workspace_path $M --input_type geometric --output_path $M/fused.ply \
   --StereoFusion.max_image_size 2400 --StereoFusion.min_num_pixels 2 --StereoFusion.num_threads 2
echo "TOTAL $(( $(date +%s)-t0 )) s"; grep -a -m1 'element vertex' $M/fused.ply
