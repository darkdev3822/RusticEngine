---
license: apache-2.0
base_model: Qwen/Qwen3-8B
tags:
  - gguf
  - game-development
  - godot
  - rust
  - godot-rust
  - agent
language:
  - en
---

# Ember 8B (GGUF)

Ember is the AI partner built into **RusticEngine**, a game engine based on Godot 4.7 where games are written in Rust ([godot-rust](https://github.com/godot-rust/gdext) 0.5).

Ember is meant to work *with* a creator rather than build a whole game from one prompt. It asks about the creator's idea and inspirations before making creative choices, explains what it builds when the creator wants to learn, and guides people to make their own art in RusticEngine's Studio instead of making it for them.

RusticEngine downloads this model automatically the first time you open the AI Guide. You only need this page if you want to run Ember yourself.

## What it is

- **Base:** Qwen3-8B (Apache-2.0). Fine-tuned with QLoRA (rank 16) on several hundred RusticEngine agent traces: real tool calls (reading and editing code, `cargo` builds with compiler feedback, headless playtests, Godot API lookups), plus collaboration conversations (kickoff questions, learning mode, concept art, Studio guidance).
- **Format:** GGUF, mixed 4/5-bit (attention and ffn_down in Q5_0, ffn_gate/up and embeddings in Q4_0, output in Q8_0), about 5.5 GB.
- **Chat format:** Qwen3 ChatML with `<tool_call>` tool calls, non-thinking mode (an empty `<think></think>` block before each reply).

## How well it does

On RusticEngine's own evaluation (32 unseen godot-rust coding tasks, scored by whether the code builds and the game runs), Ember with RusticEngine's agent harness built about 17 of 32 and ran about 16 of 32 per pass. Base Qwen3-8B scored roughly 7 of 16 on an earlier, smaller version of the same evaluation. On held-out Studio and Mechanics questions it gives grounded, step-by-step guidance (34/34 and 8/9 on the current probes).

It is an 8B model, so it still invents Godot methods sometimes. RusticEngine's harness compensates: builds feed compiler errors back to it, missing imports are fixed automatically, and API lookups are offered before it writes code. For harder work, RusticEngine can also use a frontier model (Claude, OpenAI and others) in the AI Guide settings.

## Running it yourself

- **RusticEngine:** built in, nothing to do.
- **llama.cpp:** `llama-server -m ember.gguf --jinja`. Turn thinking off by ending prompts with an empty `<think>\n\n</think>\n\n` block, as in training.
- **Ollama:** create a model from this GGUF using Qwen3's template, with `think: false`.

The tools Ember was trained with come from RusticEngine's agent (`rustic-agent --print-tools`). RusticEngine can also act as an MCP server (`rustic-agent --mcp`), so other agents can use the same tools.

## License

Apache-2.0, like the Qwen3 base model. RusticEngine itself is GPL-3.0.
