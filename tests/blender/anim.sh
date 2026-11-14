#!/bin/bash
# Character test: a skinned rig with actions and a shape key, exported by the add-on, must arrive with the same
# bones, animations (looping where Blender's action is cyclic) and the same bone positions over time.
# Usage: tests/blender/anim.sh   Output: tests/blender/out_anim/
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="$HERE/out_anim"
EDITOR="$ROOT/engine/bin/godot.linuxbsd.editor.x86_64"
BLENDER="${BLENDER:-flatpak run org.blender.Blender}"
rm -rf "$OUT"; mkdir -p "$OUT/proj"
printf 'config_version=5\n[application]\nconfig/name="anim"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n' > "$OUT/proj/project.godot"
$BLENDER -b --factory-startup --python "$HERE/anim/rig.py" -- "$OUT/proj" > "$OUT/blender.log" 2>&1
grep -q ANIM_DONE "$OUT/blender.log" || { tail -20 "$OUT/blender.log"; exit 1; }
"$EDITOR" --headless --path "$OUT/proj" --import > "$OUT/import.log" 2>&1
"$EDITOR" --headless --path "$OUT/proj" -s "$HERE/anim/check.gd" > "$OUT/engine.log" 2>&1
$BLENDER -b --factory-startup --python "$HERE/anim/root.py" -- "$OUT/proj" > "$OUT/blender_root.log" 2>&1
"$EDITOR" --headless --path "$OUT/proj" --import > "$OUT/import_root.log" 2>&1
"$EDITOR" --headless --path "$OUT/proj" -s "$HERE/anim/check_root.gd" > "$OUT/engine_root.log" 2>&1
grep "^ROOT_" "$OUT/blender_root.log" "$OUT/engine_root.log" | sed 's|^[^:]*:||'
grep "^ROOT_ENGINE" "$OUT/engine_root.log" >> "$OUT/engine_root.txt"
grep "^ANIM_BLENDER" "$OUT/blender.log" > "$OUT/blender.txt"; grep "^ANIM_ENGINE\|SCRIPT ERROR" "$OUT/engine.log" > "$OUT/engine.txt"
cat "$OUT/engine.txt"
python3 - "$OUT/blender.txt" "$OUT/engine.txt" <<'PY'
import re, sys
bl = {(m[0], m[1]): eval(m[2]) for m in re.findall(r"ANIM_BLENDER (\w+) t=([\d.]+) tip=(\(.*\))", open(sys.argv[1]).read())}
en_text = open(sys.argv[2]).read()
en = {(m[0], m[1]): eval(m[2]) for m in re.findall(r"ANIM_ENGINE (\w+) t=([\d.]+) tip=(\(.*\))", en_text)}
fails = []
for k, b in bl.items():
    e = en.get(k)
    if e is None or max(abs(x - y) for x, y in zip(b, e)) > 0.02:   # Godot's import compression allows ~1 degree
        fails.append(f"{k}: blender {b} engine {e}")
checks = {"bones": 'bones=["Upper", "Lower"]', "walk loops": "anim=Walk length=1.0000 loop=1", "wave once": "anim=Wave length=0.7917 loop=0",
          "shape key": 'shapes=[&"Smile"]', "smile plays": "smile_end=1.000"}
fails += [name for name, needle in checks.items() if needle not in en_text]
root_text = open(sys.argv[2].replace("engine.txt", "engine_root.txt")).read()
m = re.search(r"half_second_motion=\(([-\d.]+), ([-\d.]+), ([-\d.]+)\) root_bone_pose=\(0.00, 0.00, 0.00\)", root_text)
if "track=Walker/Skeleton3D:root loop=1" not in root_text or not m or not (0.9 <= float(m.group(3)) <= 1.05) or abs(float(m.group(1))) > 0.02:
    fails.append("root motion: " + root_text.strip().replace("\n", " | "))
print("ANIM", "DONE ok" if not fails else "FAILED: " + "; ".join(fails))
sys.exit(1 if fails else 0)
PY
