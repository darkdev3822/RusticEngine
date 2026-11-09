#!/usr/bin/env python3
"""Score a model as Ember on tasks that are NOT in the training data.

For each task: fresh starter project -> run rustic-agent one-shot with the model -> check
  built:  does `cargo build` succeed at the end?
  looked: did it read/list before its first write?
  ran:    does a headless playtest run without errors?
  tools:  number of tool calls; secs: wall time
Usage: python3 eval_agent.py [--repeat N] MODEL [MODEL...]   (Ollama model names)
"""
import json, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT = ROOT / "engine/bin/rustic-agent"
ENGINE = ROOT / "engine/bin/godot.linuxbsd.editor.x86_64"
BASE = ROOT / "sandbox/gen/base"
SHARED_TARGET = ROOT / "sandbox/gen-target"

TASKS = [
    "Make the player grow bigger while I hold B",
    "Add a second player I control with WASD",
    "Make the player bounce off the edges of the screen",
    "Make the player slowly fade in when the game starts",
    "Add a pause: pressing P should freeze the player until I press P again",
    "Print my player's position every second",
    "Make the player shake a little when I press space",
    "I want the player to follow my mouse",
    # round 2 (added 2026-11-08; none of these are in the training data either)
    "Make the player move faster the longer I hold an arrow key",
    "Add a label at the bottom of the screen that says Good luck!",
    "Make the player jump back to the middle of the screen when I press C",
    "Let me rotate the player with Q and E",
    "Change the background color every time I press space",
    "Make the player move in a circle all by itself",
    "Show how many times I've pressed space in the top corner",
    "Make the player half see-through",
]


def fresh(name: str) -> Path:
    p = ROOT / "sandbox/eval" / name
    shutil.rmtree(p, ignore_errors=True)
    shutil.copytree(BASE, p, symlinks=True, ignore=shutil.ignore_patterns("target"))
    (p / "rust/target").symlink_to(SHARED_TARGET)
    return p


def tool(project: Path, name: str, args=None) -> dict:
    try:
        out = subprocess.run([str(AGENT), "--project", str(project), "--engine", str(ENGINE), "--tool", name,
                              "--args", json.dumps(args or {})], capture_output=True, text=True, timeout=600)
        return json.loads(out.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:  # a hang counts as a failure, not a crash
        return {"ok": False, "content": f"{name} failed: {type(e).__name__}"}


def run_task(model: str, task: str, idx: int) -> dict:
    project = fresh(f"{model.replace(':', '_')}-{idx}")
    t0 = time.time()
    try:
        stdout = subprocess.run([str(AGENT), "--project", str(project), "--engine", str(ENGINE), "--provider", "ollama",
                                 "--model", model, "--ask", task], capture_output=True, text=True, timeout=600).stdout
    except subprocess.TimeoutExpired as e:  # a stuck model counts as a failure, not a crash
        stdout = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        stdout += "\n" + json.dumps({"type": "error", "message": "timed out after 600 s"})
    secs = time.time() - t0
    events = []
    for l in stdout.splitlines():
        try:
            events.append(json.loads(l))
        except ValueError:
            pass
    calls = [e["name"] for e in events if e["type"] == "tool_start"]
    first_write = next((i for i, c in enumerate(calls) if c in ("write_file", "edit_file", "new_rust_node")), None)
    looked = first_write is None or any(c in ("read_file", "list_files") for c in calls[:first_write])
    text = "".join(e.get("delta", "") for e in events if e["type"] == "text")
    errors = [e["message"] for e in events if e["type"] == "error"]
    b = tool(project, "build_rust")
    built = b["ok"]
    r = tool(project, "run_game", {"seconds": 2}) if built else {"ok": False, "content": ""}
    ran = r["ok"]
    problem = "" if ran else (r["content"] if built else b["content"])[:1500]
    guards = [e["name"] for e in events if e["type"] == "guard"]
    return {"guards": guards, "model": model, "task": task, "built": built, "ran": ran, "looked": looked, "tools": len(calls),
            "changed": first_write is not None, "secs": round(secs), "errors": errors[:1], "reply": text[-400:], "problem": problem}


def main():
    out = Path(__file__).resolve().parent / "data/eval_results.jsonl"
    args = sys.argv[1:]
    repeat = 1
    if "--repeat" in args:
        i = args.index("--repeat"); repeat = int(args[i + 1]); del args[i:i + 2]
    for model in args:
        rows = []
        for i, task in [(i, t) for _ in range(repeat) for i, t in enumerate(TASKS)]:
            r = run_task(model, task, i)
            rows.append(r)
            with out.open("a") as fh:
                fh.write(json.dumps(r) + "\n")
            print(f"{model:22s} built={r['built']!s:5} ran={r['ran']!s:5} looked={r['looked']!s:5} "
                  f"changed={r['changed']!s:5} tools={r['tools']:2d} {r['secs']:4d}s  {task}", flush=True)
        n = len(rows)
        print(f"== {model}: built {sum(r['built'] and r['changed'] for r in rows)}/{n}, ran {sum(r['ran'] and r['changed'] for r in rows)}/{n}, "
              f"looked-first {sum(r['looked'] for r in rows)}/{n}, avg {sum(r['secs'] for r in rows) / n:.0f}s", flush=True)


if __name__ == "__main__":
    main()
