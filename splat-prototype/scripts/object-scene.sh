#!/bin/sh
# A small object's splat, from the gpu machine to a page on the local site.
#
#   sh scripts/object-scene.sh <name> <scan>
#
# <scan> is the scan's folder name on the gpu machine, after
# scan-pipeline/object.sh has finished there. Fetches its clean/object.ply and
# object.json, builds site/scene-<name>/ upright on the origin, and writes
# site/<name>.json with the starting camera. Then look at it:
#
#   npm run serve      and open  http://localhost:4173/?config=<name>
#
# The model file is kept in ../object-models/<name>/ (MODELS=... to change),
# outside the repo: a .ply is never committed. View limits are not set here;
# add "viewLimits" to site/<name>.json by hand (PIPELINE.md, 6c). An existing
# site/<name>.json is left alone, so hand edits survive a rebuild.
set -eu
NAME="${1:?usage: sh scripts/object-scene.sh <name> <scan>}"
SCAN="${2:?usage: sh scripts/object-scene.sh <name> <scan>}"
HOST="${GPU_HOST:-gpu}"
DIR="${MODELS:-../object-models}/$NAME"
mkdir -p "$DIR"
scp -q "$HOST:sshah_workspace/projects/$SCAN/clean/object.ply" "$HOST:sshah_workspace/projects/$SCAN/clean/object.json" "$DIR/"
value() { python3 -c "import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$DIR/object.json" "$1"; }
ROTATE="$(value rotate)" TRANSLATE="$(value translate)" sh scripts/build-scene.sh "$DIR/object.ply" "site/scene-$NAME"
if [ -e "site/$NAME.json" ]; then
    echo "site/$NAME.json is already there and was left as it is"
else
    python3 - "$DIR/object.json" "$NAME" <<'EOF'
import json, sys
o, name = json.load(open(sys.argv[1])), sys.argv[2]
c = {"scene": f"scene-{name}/lod-meta.json", "background": [0.06, 0.05, 0.05],
     "initialCamera": o["initialCamera"], "fitPortrait": False, "hotspots": []}
json.dump(c, open(f"site/{name}.json", "w"), indent=2)
print(f"wrote site/{name}.json")
EOF
fi
echo "http://localhost:4173/?config=$NAME"
