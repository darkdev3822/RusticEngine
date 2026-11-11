#!/usr/bin/env python3
"""Does Ember use Mechanics well? Held-out questions in the Mechanics tab (and one build request).
A pass: the reply names the right tuning value / idea, and Ember doesn't rewrite mechanic code for a tuning question.
Usage: python3 probe_mechanics.py MODEL [MODEL...]   (PROBE_ALL=1 prints every reply)
"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
models = sys.argv[1:]
AGENT = os.path.expanduser("~/rustic-engine/engine/bin/rustic-agent")
BASE = os.path.expanduser("~/rustic-engine/sandbox/gen/base")
MECH = os.path.expanduser("~/rustic-engine/engine/modules/rustic/mechanics")
NAMES = {"first_person": "First-Person Controller", "third_person": "Third-Person Controller", "stats": "Character Stats",
         "combat": "Attack & Damage", "inventory": "Inventory", "hud": "HUD"}
def ctx(mid):
    return f"in the Mechanics tab, looking at the {NAMES[mid]} mechanic (res://mechanics/{mid}, ...)"
# (mechanic, mode, question, any of these must appear, may_change_code, must_create)
PROBES = [
    ("first_person", "learning", "the player feels really slow", ["walk_speed"], False, None),
    ("first_person", "learning", "jumping feels floaty, like on the moon", ["gravity", "fall_gravity_multiplier"], False, None),
    ("first_person", "learning", "Explain the First-Person Controller mechanic to me (res://mechanics/first_person). Start with the idea, not the code.", ["delta"], False, None),
    ("third_person", "learning", "the character turns way too slowly when I change direction", ["turn_speed", "turn speed"], False, None),
    ("hud", "learning", "how does the health bar know when I got hurt?", ["every frame", "each frame", "signal"], False, None),
    ("inventory", "learning", "why can't I pick up the stone?", ["capacity", "strength"], False, None),
    ("combat", "learning", "my sword hits enemies that are way off to the side", ["arc"], False, None),
    ("combat", "learning", "players can spam attacks way too fast", ["attack_cooldown", "cooldown", "stamina_cost"], False, None),
    ("first_person", "autonomous", "make me a new mechanic: a double jump, so the player can jump once more in the air", [], True, "double"),
]
for model in models:
    passed = 0
    for mid, mode, q, want, may_code, must_create in PROBES:
        d = tempfile.mkdtemp()
        shutil.copytree(BASE, d + "/p")
        shutil.copytree(MECH, d + "/p/mechanics", ignore=shutil.ignore_patterns("target"))
        lib = Path(d + "/p/rust/src/lib.rs")
        lib.write_text(lib.read_text() + "".join(f'\n#[path = "../../mechanics/{m}/src/mod.rs"]\nmod {m};' for m in NAMES) + "\n")
        before = {str(p): p.read_text() for p in Path(d + "/p/mechanics").rglob("*.rs")}
        p = subprocess.Popen([AGENT, "--project", d + "/p", "--model", model, "--mode", mode], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        p.stdin.write(json.dumps({"type": "user", "text": q, "context": ctx(mid)}) + "\n")
        p.stdin.flush()
        tools, text = [], ""
        try:
            for line in p.stdout:
                v = json.loads(line)
                if v["type"] == "tool_start":
                    tools.append(v["name"])
                elif v["type"] == "text":
                    text += v["delta"]
                elif v["type"] in ("done", "error"):
                    break
        finally:
            p.kill()
        code_changed = any(Path(f).read_text() != t for f, t in before.items() if Path(f).exists())
        created = [x.name for x in Path(d + "/p/mechanics").iterdir() if x.is_dir() and x.name not in NAMES]
        low = text.lower()
        named = any(w in low for w in want) if want else True
        ok = named and (may_code or not code_changed) and "</think>" not in text
        if must_create:
            ok = ok and any(must_create in c for c in created) and "mechanic" in tools
        passed += ok
        print(f"{model:22s} {'OK ' if ok else '-- '} named={named!s:5} code_changed={code_changed!s:5} created={created} tools={tools[:6]}  {q[:50]}", flush=True)
        if not ok or os.environ.get("PROBE_ALL"):
            print(f"    reply: {' '.join(text.split())[-400:]}", flush=True)
        shutil.rmtree(d)
    print(f"== {model}: mechanics {passed}/{len(PROBES)}", flush=True)
