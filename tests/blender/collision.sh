#!/bin/bash
# Collision test: Blender rigid bodies (and the add-on's Trigger / Collision Only) become physics bodies with
# fitted shapes, and dropped objects land on the floor. Usage: tests/blender/collision.sh  Output: tests/blender/out_collision/
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="$HERE/out_collision"
EDITOR="$ROOT/engine/bin/godot.linuxbsd.editor.x86_64"
BLENDER="${BLENDER:-flatpak run org.blender.Blender}"
rm -rf "$OUT"; mkdir -p "$OUT/proj"
printf 'config_version=5\n[application]\nconfig/name="collision"\n' > "$OUT/proj/project.godot"
$BLENDER -b --factory-startup --python "$HERE/collision/scene.py" -- "$OUT/proj" > "$OUT/blender.log" 2>&1
grep -q COLLISION_EXPORTED "$OUT/blender.log" || { tail -20 "$OUT/blender.log"; exit 1; }
"$EDITOR" --headless --path "$OUT/proj" --import > "$OUT/import.log" 2>&1
"$EDITOR" --headless --path "$OUT/proj" -s "$HERE/collision/check.gd" > "$OUT/engine.log" 2>&1
grep "^COLLISION_\|SCRIPT ERROR\|ERROR" "$OUT/engine.log" | tee "$OUT/result.txt"
python3 - "$OUT/result.txt" <<'PY'
import re, sys
t = open(sys.argv[1]).read()
need = {
    "floor exact": "Floor StaticBody3D shapes=[\"ConcavePolygonShape3D\"] meshes=1",
    "crate box + settings": "Crate RigidBody3D shapes=[\"BoxShape3D size=(1.0, 1.0, 1.0)\"] meshes=1 mass=5.0 friction=0.80 bounce=0.30",
    "ball sphere": "Ball RigidBody3D shapes=[\"SphereShape3D r=0.50\"]",
    "pillar scaled into shape": "Pillar StaticBody3D shapes=[\"CylinderShape3D r=1.00 h=3.00\"] meshes=1 scale=(1.0, 1.0, 1.0)",
    "invisible wall": "InvisibleWall StaticBody3D shapes=[\"BoxShape3D size=(2.0, 2.0, 2.0)\"] meshes=0",
    "trigger": "Checkpoint Area3D",
    "platform": "Platform AnimatableBody3D",
    "decoration untouched": "Decoration MeshInstance3D shapes=[] meshes=1",
    "godot -col naming": "COLLISION_NAMED Wall 1",
}
fails = [k for k, v in need.items() if v not in t]
for name in ("Crate", "Ball"):
    m = re.search(rf"COLLISION_REST {name} y=([-\d.]+)", t)
    if not m or abs(float(m.group(1)) - 0.5) > 0.05:
        fails.append(f"{name} didn't land on the floor")
fails += ["errors in the log"] if "ERROR" in t else []
print("COLLISION", "DONE ok" if not fails else "FAILED: " + "; ".join(fails))
sys.exit(1 if fails else 0)
PY
