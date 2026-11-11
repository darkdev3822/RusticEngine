"""Check that ember-runtime builds the exact prompt Ember was trained with.

Takes real training samples (and a few hand-made edge cases), converts them to the Ollama-style
request rustic-agent sends, renders them with `ember-runtime --render`, and compares against
tokenizer.apply_chat_template(..., enable_thinking=False) from the Qwen3 tokenizer used in training.

Usage: .venv/bin/python check_runtime_prompt.py [N_SAMPLES]
"""
import json, subprocess, sys, tempfile
from pathlib import Path

from transformers import AutoTokenizer

HERE = Path(__file__).parent
RUNTIME = HERE.parent / "runtime/target/release/ember-runtime"
tok = AutoTokenizer.from_pretrained("unsloth/Qwen3-8B-unsloth-bnb-4bit", cache_dir=str(HERE / "hf-cache/hub"))


def to_ollama(msgs):
    out = []
    for m in msgs:
        m = dict(m)
        if m.get("tool_calls"):
            m["tool_calls"] = [{"function": {"name": c["function"]["name"],
                                             "arguments": c["function"]["arguments"] if not isinstance(c["function"]["arguments"], str)
                                             else json.loads(c["function"]["arguments"])}} for c in m["tool_calls"]]
        out.append(m)
    return out


JINJA = "--jinja" in sys.argv  # render through the runtime's Jinja path with the real template instead
if JINJA: sys.argv.remove("--jinja")


def render(msgs, tools):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        req = {"messages": to_ollama(msgs), "tools": tools, "think": False}
        if JINJA:
            req["template"] = tok.chat_template
        json.dump(req, f)
    return subprocess.run([str(RUNTIME), "--render", f.name], capture_output=True, text=True, check=True).stdout


def expected(msgs, tools):
    # Generation prompt: everything up to (not including) the final assistant reply.
    return tok.apply_chat_template(msgs, tools=tools or None, tokenize=False, add_generation_prompt=True, enable_thinking=False)


samples = []
data = HERE / "data/train.jsonl"
if data.exists():
    for line in data.read_text().splitlines()[: int(sys.argv[1]) if len(sys.argv) > 1 else 40]:
        s = json.loads(line)
        msgs = s["messages"]
        # Cut before the last assistant message, as at inference time.
        last = max(i for i, m in enumerate(msgs) if m["role"] == "assistant")
        samples.append((msgs[:last], s.get("tools") or []))
# Alphabetized, like the tool definitions in the training data (see runtime/src/prompt.rs).
tools = [{"function": {"description": "Read a file — ünïcode", "name": "read_file",
          "parameters": {"properties": {"path": {"type": "string"}}, "required": ["path"], "type": "object"}}, "type": "function"}]
samples += [
    ([{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}], []),
    ([{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}], tools),
    ([{"role": "system", "content": "sys"}, {"role": "user", "content": "read it"},
      {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "read_file", "arguments": {"path": "a.rs"}}},
                                                          {"function": {"name": "read_file", "arguments": {"path": "b.rs"}}}]},
      {"role": "tool", "content": "A"}, {"role": "tool", "content": "B"},
      {"role": "assistant", "content": "Looking closer.", "tool_calls": [{"function": {"name": "read_file", "arguments": {"path": "c.rs"}}}]},
      {"role": "tool", "content": "C"}, {"role": "assistant", "content": "Done."}, {"role": "user", "content": "thanks"}], tools),
]

bad = 0
for i, (msgs, tl) in enumerate(samples):
    a, b = render(msgs, tl), expected(msgs, tl)
    if a != b:
        bad += 1
        if bad <= 3:
            k = next(j for j in range(min(len(a), len(b))) if a[j] != b[j]) if a[:min(len(a), len(b))] != b[:min(len(a), len(b))] else min(len(a), len(b))
            print(f"MISMATCH sample {i} at char {k}:\n  runtime : {a[max(0,k-80):k+80]!r}\n  expected: {b[max(0,k-80):k+80]!r}")
print(f"{len(samples) - bad}/{len(samples)} prompts identical")
sys.exit(1 if bad else 0)
