#!/usr/bin/env python3
"""Generate Ember training conversations by replaying gold features through the REAL agent tools.

Every tool result in the output (file listings, file contents, compiler output, playtest logs)
comes from actually running rustic-agent's tools on a real RusticEngine project.

Usage: python3 gen_traces.py OUT.jsonl [feature ...]
"""
import importlib, json, os, random, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
AGENT = ROOT / "engine/bin/rustic-agent"
ENGINE = ROOT / "engine/bin/godot.linuxbsd.editor.x86_64"
WORK = ROOT / "sandbox/gen"
BASE = WORK / "base"
SHARED_TARGET = ROOT / "sandbox/gen-target"
rng = random.Random(7)

sys.path.insert(0, str(HERE))
FEATURES = {}
for mod in ("features_core", "features_more"):
    try:
        FEATURES.update(importlib.import_module(mod).FEATURES)
    except ModuleNotFoundError:
        pass

TOOLS = json.loads(subprocess.run([str(AGENT), "--print-tools"], capture_output=True, text=True, check=True).stdout)

LOOK_LINES = ["", "", "Let me take a look first.", "First, a quick look at the project."]
WRITE_LINES = ["", "", "Now I'll write the code.", "Here's the plan in code form:", "Writing it now."]
BUILD_LINES = ["", "Let me build it to make sure everything compiles.", "Building to check it compiles."]
RUN_LINES = ["", "It builds! Let me playtest it for a few seconds.", "Quick playtest to be sure it runs."]
NODE_LINES = ["", "I'll start by creating the new node.", "First, the new Rust node."]
CONTEXTS = ["", "", "open scene res://main.tscn", "open scene res://main.tscn; selected Player (Player)"]


def tool(project: Path, name: str, args: dict) -> dict:
    out = subprocess.run([str(AGENT), "--project", str(project), "--engine", str(ENGINE),
                          "--tool", name, "--args", json.dumps(args)], capture_output=True, text=True, timeout=600)
    return json.loads(out.stdout)


def make_base():
    """A starter project as the user sees it after first opening it: built and imported."""
    if (BASE / "agent_test.gdextension").exists():
        return
    shutil.rmtree(BASE, ignore_errors=True)
    subprocess.run([str(ROOT / "tests/fresh_project.sh"), str(BASE)], check=True)
    SHARED_TARGET.mkdir(parents=True, exist_ok=True)
    (BASE / "rust/target").symlink_to(SHARED_TARGET)
    r = tool(BASE, "build_rust", {})
    assert r["ok"], r["content"]
    subprocess.run([str(ENGINE), "--path", str(BASE), "--headless", "--import"], capture_output=True, timeout=300)


def fresh_project() -> Path:
    p = WORK / "trace"
    shutil.rmtree(p, ignore_errors=True)
    shutil.copytree(BASE, p, symlinks=True, ignore=shutil.ignore_patterns("target"))
    (p / "rust/target").symlink_to(SHARED_TARGET)
    return p


def apply_silently(project: Path, name: str):
    f = FEATURES[name]
    for req in f.get("requires", []):
        apply_silently(project, req)
    for cls, base in f.get("new_nodes", []):
        tool(project, "new_rust_node", {"name": cls, "base": base})
    for path, content in f.get("files", {}).items():
        tool(project, "write_file", {"path": path, "content": content})
    for path, old, new in f.get("edits", []):
        tool(project, "edit_file", {"path": path, "old_text": old, "new_text": new})


class Trace:
    def __init__(self, project: Path):
        self.project = project
        self.messages = []
        self.n = 0

    def user(self, text: str):
        self.messages.append({"role": "user", "content": text})

    def step(self, text: str, calls: list):
        """One assistant message with tool calls, followed by the real tool results."""
        msg = {"role": "assistant", "content": text, "tool_calls": []}
        results = []
        for name, args in calls:
            self.n += 1
            msg["tool_calls"].append({"type": "function", "function": {"name": name, "arguments": args}})
            results.append((name, tool(self.project, name, args)))
        self.messages.append(msg)
        for name, r in results:
            self.messages.append({"role": "tool", "name": name, "content": r["content"]})
        return [r for _, r in results]

    def say(self, text: str):
        self.messages.append({"role": "assistant", "content": text})


def existing(project: Path, path: str) -> bool:
    return (project / path).exists()


def feature_trace(name: str, prompt: str, mistake: bool):
    f = FEATURES[name]
    project = fresh_project()
    for req in f.get("requires", []):
        apply_silently(project, req)
    # Requirements shouldn't leave the project unbuilt.
    tool(project, "build_rust", {})
    t = Trace(project)
    run_feature(t, name, prompt, mistake)
    return t.messages


def chain_trace(chain: list):
    """Several requests in one conversation, each building on the last."""
    first = FEATURES[chain[0]]
    project = fresh_project()
    for req in first.get("requires", []):
        apply_silently(project, req)
    tool(project, "build_rust", {})
    t = Trace(project)
    for name in chain:
        run_feature(t, name, rng.choice(FEATURES[name]["prompts"]), False)
    return t.messages


def run_feature(t: "Trace", name: str, prompt: str, mistake: bool):
    f = FEATURES[name]
    project = t.project
    ctx = rng.choice(CONTEXTS)
    t.user(prompt + (f"\n\n[Editor context: {ctx}]" if ctx else ""))
    if f.get("explain"):
        look = [("list_files", {})] + [("read_file", {"path": p}) for p in f["explain"]]
        t.step(rng.choice(f["intro"]), look)
        t.say(rng.choice(f["final"]))
        return

    files = f.get("files", {})
    edits = f.get("edits", [])
    to_read = [p for p in list(files) + [e[0] for e in edits] if existing(project, p)]
    to_read = list(dict.fromkeys(to_read))
    look = []
    if f.get("new_nodes") or any(not existing(project, p) for p in files):
        look.append(("list_files", {}))
    look += [("read_file", {"path": p}) for p in to_read[:3]]
    intro = rng.choice(f["intro"])
    if look:
        t.step(intro + (" " + rng.choice(LOOK_LINES) if rng.random() < 0.2 else ""), look)
        intro = ""

    if f.get("new_nodes"):
        t.step(intro or rng.choice(NODE_LINES), [("new_rust_node", {"name": c, "base": b}) for c, b in f["new_nodes"]])
        intro = ""

    writes = dict(files)
    bad = f.get("mistake", {}) if mistake else {}
    writes.update(bad)
    calls = [("write_file", {"path": p, "content": c}) for p, c in writes.items()]
    calls += [("edit_file", {"path": p, "old_text": o, "new_text": n}) for p, o, n in edits]
    t.step(intro or rng.choice(WRITE_LINES), calls)

    (build,) = t.step(rng.choice(BUILD_LINES), [("build_rust", {})])
    if bad:
        if build["ok"]:
            raise RuntimeError(f"{name}: mistake variant unexpectedly built")
        note = f.get("mistake_note", "The compiler caught a small mistake. Let me fix it.")
        fix = [("write_file", {"path": p, "content": files[p]}) for p in bad]
        t.step(note, fix)
        (build,) = t.step("Building again.", [("build_rust", {})])
    if not build["ok"]:
        raise RuntimeError(f"{name}: gold code failed to build:\n{build['content'][:3000]}")

    if f.get("run"):
        (run,) = t.step(rng.choice(RUN_LINES), [("run_game", {"seconds": f["run"]})])
        if not run["ok"]:
            raise RuntimeError(f"{name}: playtest failed:\n{run['content'][:3000]}")

    t.say(rng.choice(f["final"]))


CHAINS = [
    ["topdown_body", "coins", "score_hud"],
    ["coins", "score_hud", "coin_spawner"],
    ["platformer", "double_jump", "moving_platform"],
    ["enemy", "health"],
    ["enemy", "shoot"],
    ["topdown_body", "camera_follow", "trail"],
    ["spin", "color_flash"],
    ["topdown_body", "dash", "trail"],
    ["coins", "score_hud", "high_score"],
    ["title_screen", "spin"],
]


def main():
    out = Path(sys.argv[1])
    only = sys.argv[2:]
    WORK.mkdir(parents=True, exist_ok=True)
    make_base()
    n_ok = n_fail = 0
    with out.open("a") as fh:
        for name, f in FEATURES.items():
            if only and name not in only:
                continue
            jobs = [(p, False) for p in f["prompts"]]
            if f.get("mistake"):
                jobs += [(p, True) for p in rng.sample(f["prompts"], min(2, len(f["prompts"])))]
            for prompt, mistake in jobs:
                t0 = time.time()
                try:
                    msgs = feature_trace(name, prompt, mistake)
                except Exception as e:  # noqa: BLE001
                    n_fail += 1
                    print(f"FAIL {name}: {e}", flush=True)
                    break  # gold code is broken; no point repeating it
                fh.write(json.dumps({"feature": name, "mistake": mistake, "messages": msgs, "tools": TOOLS}) + "\n")
                n_ok += 1
                print(f"ok   {name:16s} {'(mistake) ' if mistake else ''}{time.time() - t0:5.1f}s  {prompt[:50]}", flush=True)
        if not only or "chains" in only:
            for chain in CHAINS:
                for _ in range(3):
                    t0 = time.time()
                    try:
                        msgs = chain_trace(chain)
                    except Exception as e:  # noqa: BLE001
                        n_fail += 1
                        print(f"FAIL chain {chain}: {e}", flush=True)
                        break
                    fh.write(json.dumps({"feature": "chain:" + "+".join(chain), "mistake": False, "messages": msgs, "tools": TOOLS}) + "\n")
                    n_ok += 1
                    print(f"ok   chain {'+'.join(chain):40s} {time.time() - t0:5.1f}s", flush=True)
    print(f"done: {n_ok} traces, {n_fail} failures")


if __name__ == "__main__":
    main()
