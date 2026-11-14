#!/bin/bash
# Bake fallback test: a material RusticEngine can't rebuild is baked into images on the export after the
# editor reported it, comes back as a translated "(baked)" material, and the next export reuses the cache.
# Usage: tests/blender/bake.sh   Output: tests/blender/out_bake/
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="$HERE/out_bake"
P="$OUT/proj"
EDITOR="$ROOT/engine/bin/godot.linuxbsd.editor.x86_64"
BLENDER="${BLENDER:-flatpak run org.blender.Blender}"
rm -rf "$OUT"; mkdir -p "$P"
printf 'config_version=5\n[application]\nconfig/name="bake"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n' > "$P/project.godot"
stage() { $BLENDER -b --factory-startup --python "$HERE/bake/bake_scene.py" -- "$P" "$1" > "$OUT/blender$1.log" 2>&1; grep "^BAKE_" "$OUT/blender$1.log"; }
import() { "$EDITOR" --headless --path "$P" --import > "$OUT/import$1.log" 2>&1; python3 -c "
import json,sys; r=json.load(open('$P/.godot/rustic/blender/art_crate.json'))
print('REPORT$1', 'translated=%d kept=%d' % (r['translated'], r['kept_standard']), [(m['material'], m['result']) for m in r['materials']])" | tee -a "$OUT/report.txt"; }
stage 1; import 1
stage 2; import 2
stage 3
ls "$P/art/crate_textures/baked/"
python3 - "$P/art/crate_textures/baked" <<'PY' | tee -a "$OUT/report.txt"
import os, sys
from PIL import Image, ImageStat
for ch in ("base", "roughness", "normal"):
    im = Image.open(os.path.join(sys.argv[1], f"Weird__Crate_{ch}.png")).convert("RGB")
    print(f"BAKE_IMAGE {ch} detail={'yes' if max(ImageStat.Stat(im).stddev) > 5 else 'no'}")
PY
{ grep -q "REPORT1 translated=1 kept=1" "$OUT/report.txt" && [ "$(grep -c "detail=yes" "$OUT/report.txt")" = 3 ] && grep -q "REPORT2 translated=2 kept=0" "$OUT/report.txt" &&
  grep -q "Baked: Weird on Crate\]" "$OUT/blender2.log" && grep -q "Baked: Weird on Crate (cached)" "$OUT/blender3.log" &&
  grep -q "BAKE_LEFTOVERS \[\] \[\] DATA Weird" "$OUT/blender3.log"; }
