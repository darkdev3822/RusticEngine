#!/bin/bash
# Blender -> RusticEngine material translation test.
#   1. Blender (Flatpak or $BLENDER) builds test materials, bakes them with Cycles, exports via the add-on.
#   2. RusticEngine renders each translated material in UV space and diffs it against the bake.
# Usage: tests/blender/run.sh [case ...]     Output: tests/blender/out/
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="$HERE/out"
EDITOR="$ROOT/engine/bin/godot.linuxbsd.editor.x86_64"
BLENDER="${BLENDER:-flatpak run org.blender.Blender}"
rm -rf "$OUT"
mkdir -p "$OUT/proj"
$BLENDER -b --factory-startup --python "$HERE/make_scene.py" -- "$OUT" "$@" > "$OUT/blender.log" 2>&1 || { tail -20 "$OUT/blender.log"; exit 1; }
grep -q RUSTIC_TEST_DONE "$OUT/blender.log" || { tail -20 "$OUT/blender.log"; exit 1; }
printf '[application]\nconfig/name="blender-compare"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n' > "$OUT/proj/project.godot"
RUSTIC_BLENDER_BAKE_PREVIEW=1 xvfb-run -a -s "-screen 0 640x480x24" "$EDITOR" --path "$OUT/proj" --rendering-driver opengl3 \
	--audio-driver Dummy -s "$HERE/compare.gd" -- "$OUT/materials.glb" "$OUT/bake" "$OUT/render" > "$OUT/godot.log" 2>&1 || true
xvfb-run -a -s "-screen 0 640x480x24" "$EDITOR" --path "$OUT/proj" --rendering-driver opengl3 \
	--audio-driver Dummy -s "$HERE/compare.gd" -- lit "$OUT/materials.glb" "$OUT/render/lit.png" > "$OUT/godot_lit.log" 2>&1 || true
grep -E "^COMPARE|SHADER ERROR|ERROR" "$OUT/godot.log" "$OUT/godot_lit.log" | sed 's|^[^:]*godot[_a-z]*.log:||' | head -60
grep -q "COMPARE DONE failed=0" "$OUT/godot.log" && grep -q "COMPARE LIT saved" "$OUT/godot_lit.log" && ! grep -q "SHADER ERROR" "$OUT/godot.log" "$OUT/godot_lit.log"
