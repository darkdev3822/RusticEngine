#!/usr/bin/env bash
# Make a fresh starter RusticEngine project at $1 (same files the project manager creates).
set -e
D=$1; rm -rf "$D"
rustic-engine --headless --script ~/rustic-engine/tests/fresh_project.gd -- "$D" >/dev/null 2>&1
cp ~/rustic-engine/engine/editor/icons/DefaultProjectIcon.svg "$D/icon.svg"
