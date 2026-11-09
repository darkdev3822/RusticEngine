#!/usr/bin/env python3
"""Build and playtest every pattern's code in a fresh RusticEngine project, then write the
library Ember ships with: agent/examples/design.jsonl (patterns + Wikipedia game design notes).

Usage: python3 verify_patterns.py
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_traces as G  # noqa: E402
from design_patterns import PATTERNS  # noqa: E402

OUT = HERE.parent / "agent/examples/design.jsonl"

SCENE = """[gd_scene format=3]

[ext_resource type="Texture2D" path="res://icon.svg" id="1_icon"]

[node name="Main" type="Node2D"]

[node name="Player" type="Player" parent="." groups=["player"]]
position = Vector2(576, 324)

[node name="Sprite2D" type="Sprite2D" parent="Player"]
texture = ExtResource("1_icon")

[node name="Thing" type="{cls}" parent="."]
"""


def snake(name):
    return "".join("_" + c.lower() if c.isupper() else c for c in name).lstrip("_")


def main():
    G.WORK.mkdir(parents=True, exist_ok=True)
    G.make_base()
    ok_all = True
    for p in PATTERNS:
        if not p.get("code"):
            continue
        project = G.fresh_project()
        r = G.tool(project, "new_rust_node", {"name": p["cls"], "base": p["base"]})
        path = f"rust/src/{snake(p['cls'])}.rs"
        G.tool(project, "write_file", {"path": path, "content": p["code"]})
        G.tool(project, "write_file", {"path": "main.tscn", "content": SCENE.format(cls=p["cls"])})
        b = G.tool(project, "build_rust", {})
        if not b["ok"]:
            ok_all = False
            print(f"BUILD FAIL {p['name']}\n{b['content'][:2500]}\n")
            continue
        run = G.tool(project, "run_game", {"seconds": 2})
        status = "ok  " if run["ok"] else "RUN FAIL"
        if not run["ok"]:
            ok_all = False
            print(run["content"][:1500])
        print(f"{status} {p['name']}")
    if not ok_all:
        print("not writing the library: fix the failures above")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for p in PATTERNS:
        rows.append({"kind": "pattern", "name": p["name"], "keywords": p["keywords"], "feel": p["feel"], "seen_in": p["seen_in"],
                     "how": p["how"], "knobs": p["knobs"], "code": p.get("code", ""), "source": p["source"]})
    wiki = HERE / "corpus/design/wikipedia.jsonl"
    if wiki.exists():
        for line in open(wiki):
            g = json.loads(line)
            rows.append({"kind": "game", "name": g["title"], "url": g["url"], "sections": g["sections"]})
    with open(OUT, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"wrote {len(rows)} entries -> {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
