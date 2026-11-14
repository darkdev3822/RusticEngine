#!/bin/bash
# Ember-in-Blender test: an open editor answers a question asked from the add-on's Ember panel, seeing the
# Blender scene. Needs the local model (ollama rustic-ember). Usage: tests/blender/ember.sh ["question"]
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="$HERE/out_ember"
P="$OUT/proj"
EDITOR="$ROOT/engine/bin/godot.linuxbsd.editor.x86_64"
BLENDER="${BLENDER:-flatpak run org.blender.Blender}"
Q="${1:-How do I round off the edges I have selected, just those?}"
rm -rf "$OUT"; mkdir -p "$P"
printf 'config_version=5\n[application]\nconfig/name="ember-blender"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n' > "$P/project.godot"
"$EDITOR" --headless --path "$P" --import > "$OUT/import.log" 2>&1 || true
timeout 460 xvfb-run -a -s "-screen 0 1280x800x24" "$EDITOR" -e --path "$P" --rendering-driver opengl3 \
	--audio-driver Dummy > "$OUT/editor.log" 2>&1 &
ED=$!
$BLENDER -b --factory-startup --python "$HERE/ember/ask.py" -- "$P" "$Q" > "$OUT/blender.log" 2>&1
kill $ED 2>/dev/null; pkill -f "rustic-agent.*$P" 2>/dev/null
grep -E "^EMBER_(CONTEXT|ASKED|DONE)" "$OUT/blender.log"
sed -n '/EMBER_REPLY_BEGIN/,/EMBER_REPLY_END/p' "$OUT/blender.log"
grep -q "EMBER_DONE True" "$OUT/blender.log" && ! grep -q "didn't pick up\|stopped without" "$OUT/blender.log"
