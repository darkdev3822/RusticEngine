#!/bin/bash
# LOD test: Blender _LOD0.._LODn objects get visibility ranges, line up with LOD0 and move with LOD0's physics body.
# Usage: tests/blender/lod.sh   Output: tests/blender/out_lod/
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="$HERE/out_lod"
EDITOR="$ROOT/engine/bin/godot.linuxbsd.editor.x86_64"
BLENDER="${BLENDER:-flatpak run org.blender.Blender}"
rm -rf "$OUT"; mkdir -p "$OUT/proj"
printf 'config_version=5\n[application]\nconfig/name="lod"\n' > "$OUT/proj/project.godot"
$BLENDER -b --factory-startup --python "$HERE/lod/scene.py" -- "$OUT/proj" > "$OUT/blender.log" 2>&1
grep -q LOD_EXPORTED "$OUT/blender.log" || { tail -20 "$OUT/blender.log"; exit 1; }
"$EDITOR" --headless --path "$OUT/proj" --import > "$OUT/import.log" 2>&1
"$EDITOR" --headless --path "$OUT/proj" -s "$HERE/lod/check.gd" > "$OUT/engine.log" 2>&1
grep "^LOD_BLENDER" "$OUT/blender.log"; grep "^LOD_ENGINE\|SCRIPT ERROR\|ERROR" "$OUT/engine.log" | tee "$OUT/result.txt"
python3 - "$OUT/result.txt" <<'PY'
import re, sys
t = open(sys.argv[1]).read()
need = [
    "start Rock_LOD0 holder=Node3D tris=5120 begin=0.0 end=20.8", "start Rock_LOD1 holder=Node3D tris=2048 begin=20.8 end=40.0",
    "start Rock_LOD2 holder=Node3D tris=818 begin=40.0 end=100.0",
    "after_fall Barrel_LOD0 holder=RigidBody3D tris=252 begin=0.0 end=9.1", "after_fall Barrel_LOD1 holder=RigidBody3D tris=100 begin=9.1 end=22.6",
    "after_fall Barrel_LOD2 holder=RigidBody3D tris=40 begin=22.6 end=0.0",
]
fails = [n for n in need if n not in t]
fails += [l for l in t.splitlines() if "offset=" in l and "offset=0.000" not in l]               # every LOD on LOD0
fails += [l for l in t.splitlines() if "fade=1" not in l and "LOD_ENGINE" in l]                 # cross-fade on
fails += [l for l in t.splitlines() if l.startswith("LOD_ENGINE after_fall Barrel") and "y=0.40" not in l]  # LODs fell with the body
fails += ["errors"] if "ERROR" in t else []
print("LOD", "DONE ok" if not fails else "FAILED: " + " | ".join(fails))
sys.exit(1 if fails else 0)
PY
