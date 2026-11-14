#!/bin/bash
# Lights and world test: Blender sun/point/spot/area lights and a world HDRI rendered by Cycles and by
# RusticEngine (after the add-on export) must match. Usage: tests/blender/lights.sh  Output: tests/blender/out_lights/
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="$HERE/out_lights"
EDITOR="$ROOT/engine/bin/godot.linuxbsd.editor.x86_64"
BLENDER="${BLENDER:-flatpak run org.blender.Blender}"
rm -rf "$OUT"; mkdir -p "$OUT/proj"
printf 'config_version=5\n[application]\nconfig/name="lights"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n' > "$OUT/proj/project.godot"
$BLENDER -b --factory-startup --python "$HERE/lights/scenes.py" -- "$OUT" > "$OUT/blender.log" 2>&1
grep -q SCENES_DONE "$OUT/blender.log" || { tail -20 "$OUT/blender.log"; exit 1; }
"$EDITOR" --headless --path "$OUT/proj" --import > "$OUT/import.log" 2>&1
# Forward+ (the default renderer): the Compatibility renderer has no sky ambient from panoramas.
xvfb-run -a -s "-screen 0 640x480x24" "$EDITOR" --path "$OUT/proj" --rendering-driver vulkan --rendering-method forward_plus --audio-driver Dummy \
	-s "$HERE/lights/check.gd" > "$OUT/engine.log" 2>&1
grep "^CYCLES" "$OUT/blender.log" > "$OUT/cycles.txt"; grep "^ENGINE\|SCRIPT ERROR" "$OUT/engine.log" > "$OUT/engine.txt"
python3 - "$OUT/cycles.txt" "$OUT/engine.txt" <<'PY'
import re, sys
def read(p, tag):
    out = {}
    for line in open(p):
        m = re.match(rf"{tag} (\w+) \[([^\]]+)\](.*)", line)
        if m: out[m.group(1)] = ([float(x) for x in m.group(2).split(",")], m.group(3).strip())
    return out
cy, en = read(sys.argv[1], "CYCLES"), read(sys.argv[2], "ENGINE")
bad = 0
for k, (c, _) in cy.items():
    e, extra = en.get(k, ([0, 0, 0], "missing"))
    if k.startswith("sky"):
        ok = max(range(3), key=lambda j: c[j]) == max(range(3), key=lambda j: e[j]) and abs(sum(c) - sum(e)) < 0.4 * sum(c) + 0.05
    else:
        ok = all(abs(a - b) <= 0.12 * max(a, 0.05) + 0.01 for a, b in zip(c, e))
    bad += not ok
    print(f"LIGHTS {k:13} {'OK  ' if ok else 'DIFF'} cycles={[round(x, 3) for x in c]} engine={[round(x, 3) for x in e]} {extra}")
print("LIGHTS DONE failed=%d" % bad)
sys.exit(1 if bad else 0)
PY
