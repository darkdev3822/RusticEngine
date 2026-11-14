#!/usr/bin/env bash
# Release check: with a packaged build in a clean environment (no settings, no installed templates), make a
# fresh Rust project with Blender exports in it, export it for Linux and run the exported game. The game
# checks that the Blender features (collision bodies, physics, lights, looping animations, root motion)
# survived the export, and that the project's Rust code runs.
#   tests/export_release.sh [path/to/RusticEngine-x.y.z-linux-x86_64]
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PKG=${1:-$(ls -d "$ROOT"/dist/RusticEngine-*-linux-x86_64 | grep -v cuda | tail -1)}
mkdir -p "$ROOT/.tmp"; W=$(mktemp -d -p "$ROOT/.tmp"); trap 'rm -rf "$W"' EXIT
export XDG_DATA_HOME=$W/xdg/data XDG_CONFIG_HOME=$W/xdg/config XDG_CACHE_HOME=$W/xdg/cache
P=$W/game
"$PKG/rusticengine" --headless --script "$ROOT/tests/fresh_project.gd" -- "$P" > "$W/new.log" 2>&1
[ -f "$P/project.godot" ] || { echo "FAIL: no project"; tail "$W/new.log"; exit 1; }
cp "$ROOT/engine/editor/icons/DefaultProjectIcon.svg" "$P/icon.svg"
# Blender exports made by the test suites (run tests/blender/collision.sh, lights.sh and anim.sh first).
mkdir -p "$P/art"
cp "$ROOT/tests/blender/out_collision/proj/level.glb" "$ROOT/tests/blender/out_anim/proj/arm.glb" \
   "$ROOT/tests/blender/out_anim/proj/walker.glb" "$ROOT/tests/blender/out_lights/proj/point_orange.glb" "$P/art/"
cat > "$P/release_check.gd" <<'GD'
extends Node3D
var frames := 0
var level: Node
func _ready() -> void:
	level = load("res://art/level.glb").instantiate(); add_child(level)
	var arm: Node = load("res://art/arm.glb").instantiate(); add_child(arm)
	var walker: Node = load("res://art/walker.glb").instantiate(); add_child(walker)
	var lamp: Node = load("res://art/point_orange.glb").instantiate(); add_child(lamp)
	var ap: AnimationPlayer = arm.find_children("*", "AnimationPlayer", true, false)[0]
	var wp: AnimationPlayer = walker.find_children("*", "AnimationPlayer", true, false)[0]
	var omni := lamp.find_children("*", "OmniLight3D", true, false)
	print("RELEASE_CHECK bodies=%d area=%d walk_loop=%d root_motion=%s omni_energy=%.3f" % [
		level.find_children("*", "RigidBody3D", true, false).size() + level.find_children("*", "StaticBody3D", true, false).size(),
		level.find_children("*", "Area3D", true, false).size(), ap.get_animation("Walk").loop_mode, wp.root_motion_track,
		omni[0].light_energy if omni.size() > 0 else -1.0])
func _physics_process(_d: float) -> void:
	frames += 1
	if frames == 180:
		print("RELEASE_CHECK crate_y=%.2f" % (level.find_child("Crate", true, false) as Node3D).global_position.y)
		get_tree().quit()
GD
printf '[gd_scene load_steps=2 format=3]\n\n[ext_resource type="Script" path="res://release_check.gd" id="1"]\n\n[node name="Main" type="Node3D"]\nscript = ExtResource("1")\n' > "$P/release_check.tscn"
sed -i 's|^run/main_scene=.*||' "$P/project.godot"
sed -i 's|^\[application\]|[application]\nrun/main_scene="res://release_check.tscn"|' "$P/project.godot"
cat > "$P/export_presets.cfg" <<'CFG'
[preset.0]
name="Linux"
platform="Linux"
runnable=true
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path=""
[preset.0.options]
binary_format/architecture="x86_64"
CFG
timeout 600 "$PKG/rusticengine" --headless --editor --path "$P" --quit > "$W/import.log" 2>&1
mkdir -p "$W/out"
# The first export of a brand-new project runs its first Rust build and asks to export again (by design).
timeout 900 "$PKG/rusticengine" --headless --path "$P" --export-release "Linux" "$W/out/game.x86_64" > "$W/export1.log" 2>&1
grep -q "first Rust build" "$W/export1.log" && echo "first export: Rust built, exporting again (expected)"
timeout 900 "$PKG/rusticengine" --headless --path "$P" --export-release "Linux" "$W/out/game.x86_64" > "$W/export.log" 2>&1
[ -x "$W/out/game.x86_64" ] || { echo "FAIL: export"; grep -E "ERROR|error" "$W/export.log" | head; exit 1; }
ls "$XDG_DATA_HOME"/*/export_templates/* >/dev/null 2>&1 && echo "templates installed by first start: $(ls -d "$XDG_DATA_HOME"/*/export_templates/*)"
out=$(timeout 60 "$W/out/game.x86_64" --headless 2>&1)
echo "$out" | grep -E "RELEASE_CHECK|Rust|ERROR|panicked" | head -10
echo "$out" | grep -q "RELEASE_CHECK bodies=7 area=1 walk_loop=1 root_motion=Walker/Skeleton3D:root omni_energy=0.253" &&
echo "$out" | grep -qE "RELEASE_CHECK crate_y=0\.(4|5)" && ! echo "$out" | grep -qE "ERROR|panicked" && echo "EXPORT_RELEASE PASS"
