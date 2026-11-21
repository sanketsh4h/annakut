#!/bin/bash
# Chosen setup (from pair B): sparse seeds, MVS depth loss + aligned mono depth, people masks, no bilateral grid.
cd ~/sshah_workspace/projects/annakut-2025-splat-v1
BASE="--data-factor 2 --strategy.cap-max 1000000 --steps-scaler 0.5 --eval-steps 7000 15000 30000 --save-steps 30000 --save-ply --ply-steps 30000 --depth-loss --depth-lambda 0.05"
export MASKS=$PWD/tools/people-masks.json INIT_PTS=0
HOLDOUT=IMG_1524.jpg,IMG_1526.jpg DENSE=$PWD/depth/hoA.npz MONO=$PWD/depth/mono-hoA.npz bash tools/run.sh hoA-mono -- $BASE > logs/hoA-mono.log 2>&1
HOLDOUT= DENSE=$PWD/depth/all15.npz MONO=$PWD/depth/mono-all15.npz bash tools/run.sh all15-mono -- $BASE > logs/all15-mono.log 2>&1
echo DONE > logs/queue5.done
