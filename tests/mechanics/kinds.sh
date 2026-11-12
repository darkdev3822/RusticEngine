#!/usr/bin/env bash
# Every new-mechanic kind template must compile, and its sandbox must run without errors.
#   tests/mechanics/kinds.sh            (uses agent/target/release/rustic-agent and the editor binary)
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
AGENT=${AGENT:-$ROOT/agent/target/release/rustic-agent}
EDITOR=$ROOT/engine/bin/godot.linuxbsd.editor.x86_64
# On disk, not /tmp (/tmp may be RAM, and each Rust build is ~1.7 GB).
mkdir -p "$ROOT/.tmp"; W=$(mktemp -d -p "$ROOT/.tmp"); P=$W/p; trap 'rm -rf "$W"' EXIT
cp -r "$ROOT/sandbox/gen/base" "$P"
mkdir -p "$P/mechanics" && cp -r "$ROOT/engine/modules/rustic/mechanics/first_person" "$ROOT/engine/modules/rustic/mechanics/stats" "$P/mechanics/"
rm -rf "$P"/mechanics/*/target
printf '\n#[path = "../../mechanics/first_person/src/mod.rs"]\nmod first_person;\n#[path = "../../mechanics/stats/src/mod.rs"]\nmod stats;\n' >> "$P/rust/src/lib.rs"
rc=0
KINDS="dash double_jump wall_jump glide pickup_counter door checkpoint trigger patrol chase countdown regen score"
for k in $KINDS; do
  key=""; [ $k = dash ] && key=Shift
  out=$("$AGENT" --project "$P" --tool mechanic --args "{\"action\":\"new\",\"id\":\"t_$k\",\"name\":\"Test $k\",\"summary\":\"test\",\"kind\":\"$k\",\"key\":\"$key\"}")
  echo "$out" | grep -q '"ok":true' || { echo "FAIL scaffold $k: $out"; rc=1; }
done
if ! (cd "$P/rust" && cargo build --quiet 2> "$W/build.txt"); then echo "FAIL build"; grep -E '^(error|warning)' -A6 "$W/build.txt" | head -60; exit 1; fi
grep -E '^warning' -A4 "$W/build.txt" | head -20
cp "$ROOT/tests/mechanics/behave.gd" "$P/behave.gd"
# Import once (registers the extension), then run each sandbox headless for 2 s.
timeout 120 "$EDITOR" --headless --editor --path "$P" --quit > "$W/import.txt" 2>&1
grep -q "Key::SHIFT" "$P/mechanics/t_dash/src/"*.rs || { echo "FAIL dash key not set to Shift"; rc=1; }
for k in $KINDS; do
  log=$(timeout 60 "$EDITOR" --headless --path "$P" --quit-after 120 "res://mechanics/t_$k/sandbox.tscn" 2>&1)
  errs=$(echo "$log" | grep -E 'ERROR|SCRIPT ERROR|panicked' | grep -v 'Could not set V-Sync' | head -5)
  if [ -n "$errs" ]; then echo "FAIL run $k:"; echo "$errs"; rc=1; continue; fi
  b=$(timeout 60 "$EDITOR" --headless --path "$P" -s res://behave.gd -- "$k" 2>&1 | grep -E '^BEHAVE|ERROR|SCRIPT ERROR' | head -3)
  case "$b" in "BEHAVE PASS"*) echo "PASS $k (runs and behaves)";; *) echo "FAIL $k: $b"; rc=1;; esac
done
exit $rc
