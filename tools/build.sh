#!/bin/bash
# Regenerates every generated file in project/ from the scripts in art/ and tools/.
# usage: tools/build.sh <splashpack-cli>
# Needs Blender (blender on PATH, or $BLENDER) and Python 3 with Pillow.
set -e
cli=${1:?usage: tools/build.sh <splashpack-cli>}
cd "$(dirname "$0")/.."
blender=${BLENDER:-blender}
rm -rf art/out
"$blender" -b --factory-startup --python art/models.py -- art/out
python3 -P art/textures.py art/out
for m in art/out/*.glb; do "$cli" import "$m" --project project; done
mkdir -p project/textures
cp art/out/*.png project/textures/
python3 -P tools/scenes.py project
for s in project/*.scene; do "$cli" resave "$s" "$s"; done
