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
    ("model", "hero", collab.HALF_BODY, "the shoulders look too wide, how do I fix it", ["scal", "**s**", "move", "**g**"]),
    ("model", "tree", collab.TREE, "can I make the leaves have two layers, like a pine tree?", ["extrude", "**e**", "inset", "**i**", "scale", "**s**"]),
    ("model", "tower", collab.HOUSE, "I want an arrow slit in my tower wall", ["inset", "**i**"]),
    ("model", "barrel", collab.CHEST, "my barrel is way too tall", ["scal", "**s**"]),
    ("model", "hero", collab.HALF_BODY, "how would I give my guy a big nose", ["extrude", "**e**", "inset", "**i**"]),
    ("sound", "laser", SC.LASER, "this laser goes on forever", ["decay", "stop below"]),
    ("sound", "coin", SC.COIN, "make the coin sound happier", ["pitch jump", "start pitch", "jump"]),
    ("sound", "boom", SC.BOOM, "make it sound like the explosion is underwater", ["low-pass", "lowpass"]),
    ("sound", "quiet", QUIET, "my sound is way too quiet", ["volume"]),
    ("sound", "step", STEP, "how do I make this footstep sound softer, less harsh?", ["low-pass", "lowpass", "decay", "punch"]),
]

# Pixel Art sprites (the .rpix the Studio saves) and the context line the editor sends.
def rpix(rows_per_frame, fps=8, palette=None):
    pal = palette or ["#00000000", "#14121c", "#3b3550", "#7a7390", "#c8c3d6", "#faf7f0", "#6e2a3c", "#c4473f", "#f0965a", "#fad97a", "#2f6b4a", "#6fb35a"]
    w, h = len(rows_per_frame[0][0]), len(rows_per_frame[0])
    return json.dumps({"format": "rustic-pixel", "version": 1, "width": w, "height": h, "fps": fps, "palette": pal, "frames": rows_per_frame}, indent="\t")
def rpix_picture(src, path):
    from PIL import Image
    v = json.loads(src); ch = ".123456789abcdefghijklmnopqrstuv"; w, h, n = v["width"], v["height"], len(v["frames"])
    img = Image.new("RGBA", (w * n, h))
    for f, rows in enumerate(v["frames"]):
        for y, r in enumerate(rows):
            for x, c in enumerate(r):
                hx = v["palette"][ch.index(c)].lstrip("#")
                img.putpixel((f * w + x, y), tuple(int(hx[i:i + 2], 16) for i in (0, 2, 4)) + ((int(hx[6:8], 16),) if len(hx) == 8 else (255,)))
    s = max(1, 256 // max(w, h))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    img.resize((w * n * s, h * s), Image.NEAREST).save(path)
def pix_ctx(name, src, tool="Pencil"):
    v = json.loads(src)
    return (f"in the Studio's Pixel Art painter: res://assets/art/{name}.rpix: {v['width']}x{v['height']} px, {len(v['frames'])} frame(s) at {v['fps']} fps; "
            f"editing frame 1 with the {tool} tool, left color 1 (#14121c), right color 0")
KNIGHT = rpix([["......1111......", ".....133331.....", ".....133331.....", ".....133331.....", "......1111......", "....11111111....", "...1333333331...",
               "...1333333331...", "...1333333331...", "....11111111....", ".....133331.....", ".....131131.....", ".....131131.....", ".....11..11.....", "................", "................"]])
GRASS = rpix([["bbbbbbbbbbbbbbbb", "bbbabbbbbbbbbbbb", "bbbbbbbbbabbbbbb", "bbbbbbbbbbbbbbbb", "bbbbbbbbbbbbbbbb", "bbbbbbbbbbbbbbbb", "bbbbbbbbbbbbbbba", "bbbbbbbbbbbbbbbb",
              "bbbbabbbbbbbbbbb", "bbbbbbbbbbbbbbbb", "bbbbbbbbbbbabbbb", "bbbbbbbbbbbbbbbb", "bbbbbbbbbbbbbbbb", "bbabbbbbbbbbbbbb", "bbbbbbbbbbbbbbbb", "aaaaaaaaaaaaaaaa"]])
COIN = rpix([["....9999....", "...999999...", "..99988999..", "..99899899..", "..99899899..", "..99988999..", "...999999...", "....9999...."]] * 2)
ENEMY = rpix([["................", ".....777777.....", "....77777777....", "...7757777577...", "...7717777177...", "...7777777777...", "...7777117777...", "....77777777....",
               "....77....77....", "...777....777...", "................", "................", "................", "................", "................", "................"]])
PROBES += [
    ("pixel", "knight", KNIGHT, "my little knight looks really flat, how do I make it look more 3D?", ["shad", "highlight", "darker"]),
    ("pixel", "grass", GRASS, "there's an obvious line where my grass tile repeats", ["tile view", "shift by half"]),
    ("pixel", "coin", COIN, "how can I make the coin spin?", ["copy", "onion", "frame"]),
    ("pixel", "knight", KNIGHT, "how do I draw a round head?", ["ellipse", "**o**"]),
    ("pixel", "slime", ENEMY, "I want a blue version of this slime too", ["color box", "palette", "swatch"]),
    ("pixel", "knight", KNIGHT, "how do I get both sides of him to match?", ["mirror"]),
    ("pixel", "knight", KNIGHT, "the edges look kinda staircase-y and messy", ["1:1", "2:1", "step", "jagg"]),
    ("pixel", "coin", COIN, "the coin looks blurry when i run the game", ["nearest", "texture filter"]),
]
if os.environ.get("PROBE_KIND"):
    PROBES = [p for p in PROBES if p[0] == os.environ["PROBE_KIND"]]
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
        elif kind == "pixel":
            Path(d + "/p/assets/art").mkdir(parents=True, exist_ok=True)
            Path(d + f"/p/assets/art/{name}.rpix").write_text(src)
            rpix_picture(src, d + f"/p/design/studio/{name}.png")
            ctx = pix_ctx(name, src)
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
