#!/usr/bin/env python3
"""Does Ember guide Studio modeling (instead of doing it)? Held-out questions, not in training.

A pass: Ember (given the open file's asset_info by the agent) names the right Studio tool or key,
and doesn't write files itself. Usage: python3 probe_studio.py MODEL [MODEL...]
"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.argv, models = sys.argv[:1], sys.argv[1:]
sys.path.insert(0, str(Path(__file__).parent))
import collab  # noqa: E402

AGENT = os.path.expanduser("~/rustic-engine/engine/bin/rustic-agent")
BASE = os.path.expanduser("~/rustic-engine/sandbox/gen/base")
SC = collab.SC
FENCE = collab.rmodel(*collab.box(0.2, 1.2, 0.2), ["#a0784a"] * 6)
SWORD = collab.rmodel(*collab.box(0.1, 1.0, 0.03), ["#c0c4c8"] * 6)
QUIET = SC.sfx(freq=600, sustain=0.1, decay=0.2, volume=0.12)
STEP = SC.sfx(wave="noise", freq=900, sustain=0.02, decay=0.08)

# Held out: none of these questions are in training. (kind, name, source, question, any of these must appear in the reply)
PROBES = [
    ("model", "fence", FENCE, "how do I give this fence post a pointy top?", ["merge", "**m**", "scale", "**s**", "subdivide", "**d**"]),
    ("model", "sword", SWORD, "I want a crossguard on my sword, how?", ["extrude", "**e**", "subdivide", "**d**"]),
    ("model", "rock", collab.ROCK, "can I tilt the whole rock a bit?", ["rotate", "**r**"]),
    ("model", "house", collab.HOUSE, "how do I make the walls a different color than the roof", ["paint", "**p**"]),
    ("model", "hero", collab.HALF_BODY, "the shoulders look too wide, how do I fix it", ["scale", "**s**", "move", "**g**"]),
    ("model", "tree", collab.TREE, "can I make the leaves have two layers, like a pine tree?", ["extrude", "**e**", "inset", "**i**", "scale", "**s**"]),
    ("sound", "quiet", QUIET, "my sound is way too quiet", ["volume"]),
    ("sound", "step", STEP, "how do I make this footstep sound softer, less harsh?", ["low-pass", "lowpass", "decay", "punch"]),
]

for model in models:
    passed = 0
    for kind, name, src, q, want in PROBES:
        d = tempfile.mkdtemp()
        shutil.copytree(BASE, d + "/p")
        if kind == "model":
            Path(d + "/p/assets/models").mkdir(parents=True, exist_ok=True)
            Path(d + f"/p/assets/models/{name}.rmodel").write_text(src)
            collab.render_preview(src, d + f"/p/design/studio/{name}.png")  # the Studio saves this picture on every save
            ctx = collab.studio_ctx(name, src)
        else:
            Path(d + "/p/assets/sounds").mkdir(parents=True, exist_ok=True)
            Path(d + f"/p/assets/sounds/{name}.rsfx").write_text(src)
            ctx = SC.sfx_ctx(name, src)
        p = subprocess.Popen([AGENT, "--project", d + "/p", "--model", model, "--mode", "learning"],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        p.stdin.write(json.dumps({"type": "user", "text": q, "context": ctx}) + "\n")
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
            shutil.rmtree(d)
        looked = any(t in ("asset_info", "look_at_image", "read_file") for t in tools)
        named = any(w in text.lower() for w in want)
        hands_off = not any(t in ("write_file", "edit_file", "new_rust_node") for t in tools)
        clean = "</think>" not in text  # no leaked reasoning tags
        ok = named and hands_off and clean  # the agent inspects the open Studio file itself (main.rs studio_file)
        passed += ok
        print(f"{model:22s} {'OK ' if ok else '-- '} looked={looked!s:5} named={named!s:5} hands_off={hands_off!s:5} clean={clean!s:5} {q[:45]}", flush=True)
        if not ok or os.environ.get("PROBE_ALL"):
            print(f"    tools={tools} reply: {' '.join(text.split())[-300:] if not os.environ.get('PROBE_ALL') else text}", flush=True)
    print(f"== {model}: studio {passed}/{len(PROBES)}", flush=True)
