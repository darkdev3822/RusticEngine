#!/bin/bash
# Reference-image alignment test: synthetic front/side/top pictures with a known subject must land on the
# ground, exactly the real height, centred, facing their view.  Usage: tests/blender/refs.sh
HERE="$(cd "$(dirname "$0")" && pwd)"
BLENDER="${BLENDER:-flatpak run org.blender.Blender}"
OUT=$($BLENDER -b --factory-startup --python "$HERE/refs/test_refs.py" -- "$HERE/out_refs" 2>&1); echo "$OUT" | grep "^REFS"
echo "$OUT" | grep -q "REFS DONE ok"
