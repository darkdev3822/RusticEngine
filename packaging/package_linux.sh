#!/usr/bin/env bash
# Builds the RusticEngine Linux download: dist/RusticEngine-<version>-linux-x86_64.tar.xz
#
# Expects these to be built already:
#   engine/bin/godot.linuxbsd.editor.x86_64            (scons platform=linuxbsd target=editor)
#   engine/bin/godot.linuxbsd.template_{release,debug}.x86_64   (target=template_release / template_debug)
#   agent/target/release/rustic-agent                  (cargo build --release)
#   runtime/target-vulkan/release/ember-runtime        (CARGO_TARGET_DIR=target-vulkan cargo build --release --features vulkan)
# Optional: runtime/target/release/ember-runtime (CUDA) -> separate "cuda" add-on archive with --cuda.
#
# Ember's model and the picture-reading model are NOT included: the editor downloads them the first
# time they're needed (GitHub caps release files at 2 GB).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${VERSION:-2.0.0}"
NAME="RusticEngine-$VERSION-linux-x86_64"
OUT="$ROOT/dist/$NAME"
BIN="$ROOT/engine/bin"

need() { [[ -f "$1" ]] || { echo "missing: $1" >&2; exit 1; }; }
need "$BIN/godot.linuxbsd.editor.x86_64"
need "$BIN/godot.linuxbsd.template_release.x86_64"
need "$BIN/godot.linuxbsd.template_debug.x86_64"
need "$ROOT/agent/target/release/rustic-agent"
need "$ROOT/runtime/target-vulkan/release/ember-runtime"

rm -rf "$OUT" && mkdir -p "$OUT/templates"
install -m755 "$BIN/godot.linuxbsd.editor.x86_64" "$OUT/rusticengine"
install -m755 "$ROOT/agent/target/release/rustic-agent" "$OUT/rustic-agent"
install -m755 "$ROOT/runtime/target-vulkan/release/ember-runtime" "$OUT/ember-runtime"
# Export templates, named the way the export system expects; the editor installs them on first start.
install -m755 "$BIN/godot.linuxbsd.template_release.x86_64" "$OUT/templates/linux_release.x86_64"
install -m755 "$BIN/godot.linuxbsd.template_debug.x86_64" "$OUT/templates/linux_debug.x86_64"
strip --strip-unneeded "$OUT/rusticengine" "$OUT/templates/"* 2>/dev/null || true

install -m644 "$ROOT/branding/export/rusticengine-256.png" "$OUT/rusticengine.png"
# The Blender add-on (export with procedural materials, Live Link, reference images, Ember panel).
python3 - "$ROOT/blender/rustic_link" "$OUT/rusticengine-blender-addon.zip" <<'PY'
import os, sys, zipfile
src, dst = sys.argv[1:]
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
    for d, dirs, files in os.walk(src):
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        for f in files:
            z.write(os.path.join(d, f), os.path.relpath(os.path.join(d, f), src))
PY
cp "$ROOT/LICENSE" "$OUT/LICENSE.txt"

# Third-party notices: Godot (MIT + its bundled libraries), llama.cpp (MIT), Rust crates, data sources.
{
  echo "RusticEngine is licensed under the GNU GPL v3 (LICENSE.txt). It includes:"
  echo
  echo "== Godot Engine (MIT) =="; cat "$ROOT/engine/LICENSE.txt"; echo
  echo "== Libraries bundled with Godot =="; cat "$ROOT/engine/COPYRIGHT.txt"; echo
  LLAMA="$(ls -d ~/.cargo/registry/src/*/llama-cpp-sys-2-0.1.161/llama.cpp | head -1)"
  echo "== llama.cpp / ggml (MIT) =="; cat "$LLAMA/LICENSE"; echo
  echo "== Rust crates in rustic-agent and ember-runtime =="
  for m in agent runtime; do
    (cd "$ROOT/$m" && cargo metadata --format-version 1 --locked 2>/dev/null) |
      python3 -c 'import json,sys
for p in json.load(sys.stdin)["packages"]: print(p["name"], p["version"] + ":", p.get("license") or "see crate")'
  done | sort -u
  echo
  echo "== Blender (GPL-2.0-or-later) =="
  echo "RusticEngine's Blender material translation ports Blender's GPU shader node functions (hash, Perlin noise,"
  echo "fractal noise, Voronoi, Wave, Brick, Magic, color mixing) from https://projects.blender.org/blender/blender"
  echo "(source/blender/gpu/shaders), Copyright Blender Authors, GPL-2.0-or-later, used under GPL-3.0."
  echo "The mannequin in the Animated Character mechanic was made for RusticEngine (blender/tools/make_mannequin.py), CC0."
  echo
  echo "== Ember's reference library =="; cat "$ROOT/agent/examples/NOTICE"; echo
  echo "== Models (downloaded on first use, not included in this archive) =="
  echo "Ember: fine-tuned from Qwen3-8B (Apache-2.0). Picture reading: Qwen3-VL-4B-Instruct (Apache-2.0),"
  echo "downloaded from https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF."
} > "$OUT/THIRD_PARTY.txt"

cat > "$OUT/README.txt" <<EOF
RusticEngine $VERSION (Linux x86_64)
====================================
A game engine (based on Godot 4.7) where games are written in Rust, with Ember, a built-in AI
partner that helps you make *your* game.

Start:  ./rusticengine
Add to your app menu (optional):  ./install-desktop-entry.sh

First start:
- If Rust isn't installed, RusticEngine offers to install it (official rustup installer, ~250 MB).
- The first time you talk to Ember, it downloads its model (~5.5 GB, once). Ember runs on your own
  computer: best with a graphics card that has 6 GB of memory or more (NVIDIA, AMD or Intel).
- The first time Ember looks at a picture, it downloads a picture-reading model (~3 GB, once).
  Models are kept in ~/.local/share/rusticengine/models.
- Prefer a cloud model (Claude, OpenAI...) or your own? Pick it in the AI Guide settings.
- Use RusticEngine with Claude Code, Codex or Cursor: Project > Tools > Connect an Outside AI Agent.
- Make art in Blender (4.2 or newer)? Install rusticengine-blender-addon.zip in Blender: Edit >
  Preferences > Get Extensions > drop-down > Install from Disk. Then the 3D View sidebar (N) has a
  RusticEngine tab: export with your node materials, Live Link (every save updates the open editor),
  reference images that line up by themselves, and Ember. Keep .blend files outside your project.

Licenses: LICENSE.txt (GPL v3) and THIRD_PARTY.txt.
EOF

cat > "$OUT/install-desktop-entry.sh" <<'EOF'
#!/bin/sh
# Adds RusticEngine to your application menu (for this user only).
DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p ~/.local/share/applications ~/.local/share/icons/hicolor/256x256/apps
cp "$DIR/rusticengine.png" ~/.local/share/icons/hicolor/256x256/apps/rusticengine.png
cat > ~/.local/share/applications/rusticengine.desktop <<DESKTOP
[Desktop Entry]
Type=Application
Name=RusticEngine
Comment=Make games in Rust, with Ember
Exec="$DIR/rusticengine" %f
Icon=rusticengine
Terminal=false
Categories=Development;IDE;Game;
DESKTOP
echo "Added RusticEngine to your app menu."
EOF
chmod +x "$OUT/install-desktop-entry.sh"

cd "$ROOT/dist"
tar -cJf "$NAME.tar.xz" "$NAME"
sha256sum "$NAME.tar.xz" > "$NAME.tar.xz.sha256"

if [[ "${1:-}" == "--cuda" ]]; then
  need "$ROOT/runtime/target/release/ember-runtime"
  C="RusticEngine-$VERSION-linux-x86_64-cuda-addon"
  rm -rf "$C" && mkdir -p "$C"
  install -m755 "$ROOT/runtime/target/release/ember-runtime" "$C/ember-runtime-cuda"
  echo "Copy ember-runtime-cuda next to rusticengine. On NVIDIA cards Ember then runs ~10% faster." > "$C/README.txt"
  tar -cJf "$C.tar.xz" "$C" && sha256sum "$C.tar.xz" > "$C.tar.xz.sha256"
fi
ls -la "$ROOT/dist"
