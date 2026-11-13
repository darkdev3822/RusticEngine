#!/bin/bash
# Live Link test: an open RusticEngine editor picks up a Blender save and updates the open scene in place,
# keeping gameplay nodes added around the Blender model. Usage: tests/blender/live_link.sh  Output: tests/blender/out_live/
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="$HERE/out_live"
P="$OUT/proj"
EDITOR="$ROOT/engine/bin/godot.linuxbsd.editor.x86_64"
BLENDER="${BLENDER:-flatpak run org.blender.Blender}"
rm -rf "$OUT"
mkdir -p "$P/addons/live_check"
cp "$HERE/live/addon/"* "$P/addons/live_check/"
cp "$HERE/live/gameplay.gd" "$P/"
cat > "$P/project.godot" <<'PG'
config_version=5
[application]
config/name="live-link"
[editor_plugins]
enabled=PackedStringArray("res://addons/live_check/plugin.cfg")
[rendering]
renderer/rendering_method="gl_compatibility"
PG
cat > "$P/main.tscn" <<'TS'
[gd_scene load_steps=3 format=3]

[ext_resource type="PackedScene" path="res://art/blender/level.glb" id="1"]
[ext_resource type="Script" path="res://gameplay.gd" id="2"]

[node name="Main" type="Node3D"]

[node name="Level" parent="." instance=ExtResource("1")]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 5)

[node name="Gameplay" type="Node3D" parent="Level"]
script = ExtResource("2")
health = 42

[node name="Marker" type="Marker3D" parent="Level/Cube"]
TS
$BLENDER -b --factory-startup --python "$HERE/live/live_scene.py" -- "$P" 1 > "$OUT/blender1.log" 2>&1
grep "LIVE_STAGE_DONE 1 True" "$OUT/blender1.log" || { tail -20 "$OUT/blender1.log"; exit 1; }
# Import once so main.tscn can resolve the .glb, then open the real editor.
"$EDITOR" --headless --path "$P" --import > "$OUT/import.log" 2>&1 || true
LIVE_OUT="$OUT" timeout 180 xvfb-run -a -s "-screen 0 1280x800x24" "$EDITOR" -e --path "$P" --rendering-driver opengl3 \
	--audio-driver Dummy > "$OUT/editor.log" 2>&1 &
ED=$!
for i in $(seq 120); do [ -f "$OUT/READY" ] && break; sleep 1; done
[ -f "$OUT/READY" ] || { echo "editor never got ready"; tail -30 "$OUT/editor.log"; kill $ED; exit 1; }
$BLENDER -b --factory-startup --python "$HERE/live/live_scene.py" -- "$P" 2 > "$OUT/blender2.log" 2>&1
grep "LIVE_STAGE_DONE 2 True" "$OUT/blender2.log" || { tail -20 "$OUT/blender2.log"; kill $ED; exit 1; }
wait $ED || true
grep -E "Blender: updated|LIVE_RESULT|ERROR" "$OUT/editor.log" | head -20
grep -q "LIVE_RESULT level=true gameplay=true gameplay_script=true marker=true level_pos=(0.0, 0.0, 5.0) cube_x=3.00 ball=true cube_shader=true red=true" "$OUT/RESULT"
