#!/usr/bin/env bash
# Every new-mechanic kind template must compile, and its sandbox must run without errors.
#   tests/mechanics/kinds.sh            (uses agent/target/release/rustic-agent and the editor binary)
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
AGENT=${AGENT:-$ROOT/agent/target/release/rustic-agent}
EDITOR=$ROOT/engine/bin/godot.linuxbsd.editor.x86_64
W=$(mktemp -d); P=$W/p; trap 'rm -rf "$W"' EXIT
cp -r "$ROOT/sandbox/gen/base" "$P"
mkdir -p "$P/mechanics" && cp -r "$ROOT/engine/modules/rustic/mechanics/first_person" "$ROOT/engine/modules/rustic/mechanics/stats" "$P/mechanics/"
rm -rf "$P"/mechanics/*/target
printf '\n#[path = "../../mechanics/first_person/src/mod.rs"]\nmod first_person;\n#[path = "../../mechanics/stats/src/mod.rs"]\nmod stats;\n' >> "$P/rust/src/lib.rs"
rc=0
for k in player_ability trigger mover timer; do
  out=$("$AGENT" --project "$P" --tool mechanic --args "{\"action\":\"new\",\"id\":\"t_$k\",\"name\":\"Test $k\",\"summary\":\"test\",\"kind\":\"$k\"}")
  echo "$out" | grep -q '"ok":true' || { echo "FAIL scaffold $k: $out"; rc=1; }
done
if ! (cd "$P/rust" && cargo build --quiet 2> "$W/build.txt"); then echo "FAIL build"; grep -E '^(error|warning)' -A6 "$W/build.txt" | head -60; exit 1; fi
grep -E '^warning' -A4 "$W/build.txt" | head -20
# Import once (registers the extension), then run each sandbox headless for 2 s.
timeout 120 "$EDITOR" --headless --editor --path "$P" --quit > "$W/import.txt" 2>&1
for k in player_ability trigger mover timer; do
  log=$(timeout 60 "$EDITOR" --headless --path "$P" --quit-after 120 "res://mechanics/t_$k/sandbox.tscn" 2>&1)
  errs=$(echo "$log" | grep -E 'ERROR|SCRIPT ERROR|panicked' | grep -v 'Could not set V-Sync' | head -5)
  if [ -n "$errs" ]; then echo "FAIL run $k:"; echo "$errs"; rc=1; else echo "PASS $k"; fi
done
exit $rc
