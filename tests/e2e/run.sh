#!/usr/bin/env bash
# RusticEngine editor end-to-end tests on a virtual screen.
#   tests/e2e/run.sh [scenario ...]   (default: every scenarios/*.gd)
# Each run: fresh project -> editor under xvfb -> scenario -> tests/e2e/out/<name>/
# (result.txt, *.png, editor.log). Fails on a scenario FAIL or on engine errors in the log.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
EDITOR=${RUSTIC_EDITOR:-$ROOT/engine/bin/godot.linuxbsd.editor.x86_64}
TIMEOUT=${E2E_TIMEOUT:-420}
names=("$@"); [ ${#names[@]} -eq 0 ] && names=($(cd "$HERE/scenarios" && ls *.gd | sed 's/\.gd$//'))
# Errors that are known noise from running under xvfb/opengl3 (not RusticEngine bugs).
IGNORE='BadWindow|XInput|libdecor|Vulkan|vk|ALSA|PulseAudio|dbus|portal|GLX|swrast'
rc=0
for n in "${names[@]}"; do
  out="$HERE/out/$n"; rm -rf "$out"; mkdir -p "$out"; proj="$out/project"
  "$ROOT/tests/fresh_project.sh" "$proj"
  mkdir -p "$proj/addons" && cp -r "$HERE/addon/rustic_e2e" "$proj/addons/"
  printf '\n[editor_plugins]\n\nenabled=PackedStringArray("res://addons/rustic_e2e/plugin.cfg")\n' >> "$proj/project.godot"
  # Isolated editor settings so the test never touches the user's own.
  export XDG_CONFIG_HOME="$out/xdg/config" XDG_DATA_HOME="$out/xdg/data" XDG_CACHE_HOME="$out/xdg/cache"
  # Share the already-installed models/templates instead of re-downloading.
  mkdir -p "$XDG_DATA_HOME"; ln -s "$HOME/.local/share/rusticengine" "$XDG_DATA_HOME/rusticengine" 2>/dev/null
  E2E_SCENARIO="$HERE/scenarios/$n.gd" E2E_OUT="$out" timeout "$TIMEOUT" \
    xvfb-run -a -s "-screen 0 1600x900x24" "$EDITOR" --editor --path "$proj" \
      --rendering-driver opengl3 --audio-driver Dummy > "$out/editor.log" 2>&1
  code=$?
  errs=$(grep -E 'ERROR|SCRIPT ERROR|p_I->data|Condition .* is true' "$out/editor.log" | grep -vE "$IGNORE" | sort | uniq -c | sort -rn)
  result=$(head -1 "$out/result.txt" 2>/dev/null || echo "NO RESULT (exit $code)")
  if [ "$result" = PASS ] && [ -z "$errs" ]; then echo "PASS  $n"; else
    echo "FAIL  $n: $result"; rc=1
    sed -n '2,$p' "$out/result.txt" 2>/dev/null | grep -i fail | sed 's/^/      /'
    [ -n "$errs" ] && echo "      engine errors:" && echo "$errs" | head -15 | sed 's/^/      /'
  fi
done
exit $rc
