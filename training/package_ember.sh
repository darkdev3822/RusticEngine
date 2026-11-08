#!/usr/bin/env bash
# Package out/ember-lora as the Ollama model `rustic-ember` (or $1).
#   LoRA -> merged fp16 (out/ember-merged, ~16 GB, deleted afterwards) -> out/ember.gguf (~5 GB) -> ollama create
# Ollama 0.40 can't load LoRA adapters or quantize on Linux, hence merge.py + to_gguf.py.
set -euo pipefail
cd "$(dirname "$0")"
NAME="${1:-rustic-ember}"
export HF_HOME=hf-cache HF_HUB_OFFLINE=1
ollama stop "$NAME" >/dev/null 2>&1 || true   # free VRAM for the merge
.venv/bin/python merge.py
.venv/bin/python to_gguf.py
rm -rf out/ember-merged
ollama create "$NAME" -f Modelfile.ember
echo "packaged $NAME"
