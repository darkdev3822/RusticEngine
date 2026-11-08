#!/usr/bin/env python3
"""Assemble Ember's fine-tuning dataset (OpenAI-style messages + tools) from:
  data/traces*.jsonl  real tool-using conversations (gen_traces.py)
  conversations.py    explanation / brainstorming / encouragement samples
The system prompt is Ember's real prompt (agent/prompt/ember.md), exactly as the agent sends it.
Output: data/train.jsonl, data/eval.jsonl
"""
import glob, json, random, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from conversations import CONVERSATIONS  # noqa: E402

AGENT = HERE.parent / "engine/bin/rustic-agent"
BASE = HERE.parent / "sandbox/gen/base"
# Exactly what the agent sends for a project with no design notes yet, in autonomous mode.
SYSTEM = subprocess.run([str(AGENT), "--print-system", "--project", str(BASE)], capture_output=True, text=True, check=True).stdout
TOOLS = json.loads(subprocess.run([str(AGENT), "--print-tools"], capture_output=True, text=True, check=True).stdout)
rng = random.Random(11)


def main():
    samples = []
    tools = None
    for path in sorted(glob.glob(str(HERE / "data/traces*.jsonl"))):
        for line in open(path):
            rec = json.loads(line)
            samples.append({"kind": "trace:" + rec["feature"] + (":mistake" if rec.get("mistake") else ""),
                            "messages": [{"role": "system", "content": rec.get("system") or SYSTEM}] + rec["messages"], "tools": TOOLS})
    n_traces = len(samples)
    for phrasings, answer in CONVERSATIONS:
        for q in phrasings:
            samples.append({"kind": "chat", "messages": [
                {"role": "system", "content": SYSTEM}, {"role": "user", "content": q},
                {"role": "assistant", "content": answer}], "tools": TOOLS})
    rng.shuffle(samples)
    # Hold out ~6% for evaluation, at least one of each kind where possible.
    n_eval = max(8, len(samples) * 6 // 100)
    eval_set, train = samples[:n_eval], samples[n_eval:]
    (HERE / "data").mkdir(exist_ok=True)
    for name, rows in (("train", train), ("eval", eval_set)):
        with open(HERE / f"data/{name}.jsonl", "w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
    print(f"{n_traces} traces + {len(samples) - n_traces} chats -> train {len(train)}, eval {len(eval_set)}")


if __name__ == "__main__":
    main()
