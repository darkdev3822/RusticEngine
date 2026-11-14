#!/usr/bin/env bash
# The Animated Character starter: compiles with the Third-Person Controller, its unit tests pass, and in the
# sandbox the AnimationTree follows the player: idle when standing, the speed when walking, Fall in the air.
#   tests/mechanics/character_animation.sh
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
EDITOR=$ROOT/engine/bin/godot.linuxbsd.editor.x86_64
mkdir -p "$ROOT/.tmp"; W=$(mktemp -d -p "$ROOT/.tmp"); P=$W/p; trap 'rm -rf "$W"' EXIT
cp -r "$ROOT/sandbox/gen/base" "$P"
mkdir -p "$P/mechanics"
for m in third_person character_animation; do cp -r "$ROOT/engine/modules/rustic/mechanics/$m" "$P/mechanics/"; done
rm -rf "$P"/mechanics/*/target
printf '\n#[path = "../../mechanics/third_person/src/mod.rs"]\nmod third_person;\n#[path = "../../mechanics/character_animation/src/mod.rs"]\nmod character_animation;\n' >> "$P/rust/src/lib.rs"
(cd "$P/rust" && cargo build --quiet 2> "$W/build.txt") || { echo "FAIL build"; grep -E '^(error|warning)' -A8 "$W/build.txt" | head -80; exit 1; }
grep -E '^warning' -A4 "$W/build.txt" | head -20
(cd "$P/rust" && cargo test --quiet character_animation 2>&1 | grep -E "test result|panicked|error" | head -5)
cp "$ROOT/tests/mechanics/animate.gd" "$P/animate.gd"
timeout 180 "$EDITOR" --headless --editor --path "$P" --quit > "$W/import.txt" 2>&1
out=$(timeout 120 "$EDITOR" --headless --path "$P" -s res://animate.gd 2>&1)
echo "$out" | grep -E "CharacterAnimator|ANIMATE|ERROR|SCRIPT ERROR|panicked" | grep -v "Could not set V-Sync"
echo "$out" | grep -q "ANIMATE idle tree=true active=true blend=0.00 state=ground" &&
echo "$out" | grep -qE "ANIMATE walking speed=4\.[0-9]+ blend=4\.[0-9]+ scale=1\.[0-9]+ root_bone=\(0\.0, 0\.0, 0\.0\)" &&
echo "$out" | grep -q "ANIMATE fall saw_air=true now=ground on_floor=true" &&
echo "$out" | grep -q "walk Some(\"Walk\") at 1.40 m/s, run Some(\"Run\") at 4.00 m/s" &&
! echo "$out" | grep -qE "ERROR|panicked" && echo "CHARACTER_ANIMATION PASS"
