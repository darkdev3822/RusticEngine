#!/usr/bin/env python3
"""Does Ember guide Studio modeling (instead of doing it)? Held-out questions, not in training.

A pass: Ember checks the model (asset_info or look_at_image), names the right Studio tool or key,
and doesn't write files itself. Usage: python3 probe_studio.py MODEL [MODEL...]
"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.argv, models = sys.argv[:1], sys.argv[1:]
sys.path.insert(0, str(Path(__file__).parent))
import collab  # noqa: E402

AGENT = os.path.expanduser("~/rustic-engine/engine/bin/rustic-agent")
BASE = os.path.expanduser("~/rustic-engine/sandbox/gen/base")
HOUSE = collab.rmodel(*collab.box(2.0, 1.6, 2.0), ["#c9a27e"] * 6)

# (model name, source, question, any of these must appear in the reply)
PROBES = [
    ("house", HOUSE, "how do I make a window in the wall of my house?", ["inset", "**i**"]),
    ("house", HOUSE, "I want a chimney on the roof", ["extrude", "**e**", "subdivide", "**d**"]),
    ("tree", collab.TREE, "how do I make the trunk thinner at the top?", ["scale", "**s**"]),
    ("chest", collab.CHEST, "how can I paint the metal bands a different color", ["paint", "**p**"]),
    ("hero", collab.HALF_BODY, "how do I add legs?", ["extrude", "**e**"]),
    ("chest", collab.CHEST, "make the chest look old and worn", ["vertices", "**g**", "move"]),
]

for model in models:
    passed = 0
    for name, src, q, want in PROBES:
        d = tempfile.mkdtemp()
        shutil.copytree(BASE, d + "/p")
        Path(d + f"/p/assets/models").mkdir(parents=True, exist_ok=True)
        Path(d + f"/p/assets/models/{name}.rmodel").write_text(src)
        collab.render_preview(src, d + f"/p/design/studio/{name}.png")  # the Studio saves this picture on every save
        p = subprocess.Popen([AGENT, "--project", d + "/p", "--model", model, "--mode", "learning"],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        p.stdin.write(json.dumps({"type": "user", "text": q, "context": collab.studio_ctx(name, src)}) + "\n")
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
        ok = looked and named and hands_off
        passed += ok
        print(f"{model:22s} {'OK ' if ok else '-- '} looked={looked!s:5} named={named!s:5} hands_off={hands_off!s:5} {q[:45]}", flush=True)
        if not ok:
            print(f"    tools={tools} reply: {' '.join(text.split())[-300:]}", flush=True)
    print(f"== {model}: studio {passed}/{len(PROBES)}", flush=True)
