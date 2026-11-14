#!/usr/bin/env python3
"""Build Ember's Blender library: agent/examples/blender.jsonl (searched by the blender_help tool).

Sources (all openly licensed; each entry carries its source line):
  - Blender Manual (corpus/art/blender-manual), Blender Documentation Team, CC BY-SA 4.0
  - Wikipedia concept articles (corpus/art/concepts.jsonl, crawl_art_concepts.py), CC BY-SA 4.0
  - Blender's default keymap (corpus/art/blender_keymap.json, dump_blender_keymap.py), from Blender (GPL) itself
  - Free asset catalogues: Poly Haven (CC0), ambientCG (CC0), Blender Extensions platform (GPL add-ons)
Entry: {"kind": manual|concept|keymap|resource|extension, "name", "keywords", "text", "source", "url"}
"""
import json, re
from collections import defaultdict
from pathlib import Path

from build_art_docs import clean

HERE = Path(__file__).parent
ART = HERE / "corpus/art"
OUT = HERE.parent / "agent/examples/blender.jsonl"
CHUNK = 1800
entries = []


def add(kind, name, text, source, url="", keywords=""):
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 80:
        return
    entries.append({"kind": kind, "name": name, "keywords": keywords, "text": text[:CHUNK], "source": source, "url": url})


def manual():
    src = ART / "blender-manual/manual"
    heading = re.compile(r"^([^\n]+)\n([=\-~^*#\"+])\2{2,}\s*$", re.M)
    for f in sorted(src.rglob("*.rst")):
        raw = f.read_text(errors="ignore")
        raw = re.sub(r"^([*=#]{3,})\n([^\n]+)\n\1\s*$", r"\2\n" + "*" * 5, raw, flags=re.M)  # over+underlined title
        parts = list(heading.finditer(raw))
        if not parts:
            continue
        rel = f.relative_to(src).with_suffix("")
        url = f"https://docs.blender.org/manual/en/latest/{rel.as_posix()}.html"
        area = " > ".join(p.replace("_", " ").title() for p in rel.parts[:-1])
        page = parts[0].group(1).strip()
        source = f"Blender Manual, {url}, by the Blender Documentation Team, CC BY-SA 4.0"
        for i, m in enumerate(parts):
            body = raw[m.end(): parts[i + 1].start() if i + 1 < len(parts) else len(raw)]
            text = clean(body)
            sec = m.group(1).strip()
            name = page if i == 0 else f"{page} > {sec}"
            if len(text) > CHUNK and i == 0:
                text = text[:CHUNK]
            add("manual", name, text, source, url, f"{area} {page} {sec}")


def concepts():
    for line in (ART / "concepts.jsonl").read_text().splitlines():
        v = json.loads(line)
        source = f"Wikipedia, \"{v['title']}\", {v['url']}, CC BY-SA 4.0"
        for sec, text in v["sections"].items():
            name = v["title"] if sec == "Intro" else f"{v['title']} > {sec}"
            add("concept", name, text, source, v["url"], f"{v['topic']} {v['title']} {sec}")


def short_props(p):
    """Only the settings that tell shortcuts apart (type=VERT, action=DESELECT), not long data paths."""
    out = []
    for k, v in p.items():
        if k in ("data_path", "release_confirm") or isinstance(v, float) or k.endswith("_path") or k.startswith("data_path"):
            continue
        v = str(v)
        if v == "" or len(v) > 24 or "/" in v or "." in v:
            continue
        out.append(f"{k}={v}")
    return " ".join(out[:3])


def keymap():
    d = json.loads((ART / "blender_keymap.json").read_text())
    groups = defaultdict(list)
    for r in d["items"]:
        extra = short_props(r["props"])
        groups[r["keymap"]].append(f"{r['keys']}: {r['label']}" + (f" ({extra})" if extra else ""))
    for km, rows in groups.items():
        rows = list(dict.fromkeys(rows))
        for n in range(0, len(rows), 45):
            entries.append({"kind": "keymap", "name": f"Shortcuts: {km}" + (f" (part {n // 45 + 1})" if len(rows) > 45 else ""),
                            "keywords": f"{km} shortcut hotkey keyboard key", "text": "\n".join(rows[n:n + 45]),
                            "source": f"Blender {d['blender']} default keymap (left-click select)", "url": ""})
    # One flat row per shortcut too, so "shortcut for loop cut" finds the exact key.
    (OUT.parent / "blender_keys.json").write_text(json.dumps(
        [[r["keymap"], r["keys"], r["label"], r["operator"], short_props(r["props"])] for r in d["items"]],
        ensure_ascii=False))


def resources():
    for t, label in (("textures", "textures (PBR maps)"), ("hdris", "HDRIs (sky lighting)"), ("models", "models")):
        d = json.loads((ART / f"ph_{t}.json").read_text())
        cats = defaultdict(list)
        for aid, a in d.items():
            for c in a.get("categories", [])[:3]:
                cats[c].append((a.get("download_count", 0), a["name"], aid, ", ".join(a.get("tags", [])[:4])))
        for c, items in cats.items():
            items.sort(reverse=True)
            lines = [f"- {n} ({tags}) https://polyhaven.com/a/{aid}" for _, n, aid, tags in items[:20]]
            add("resource", f"Poly Haven {label}: {c}", f"{len(items)} free CC0 {label} in '{c}' (no credit needed, any use). Most used:\n" + "\n".join(lines),
                "Poly Haven catalogue (api.polyhaven.com), assets CC0", f"https://polyhaven.com/{t}/{c.replace(' ', '%20')}",
                f"{c} {t} cc0 free download polyhaven {' '.join(x[1] for x in items[:20])}")
    a = json.loads((ART / "acg_materials.json").read_text())["foundAssets"]
    fams = defaultdict(list)
    for x in a:
        fam = re.sub(r"\d+[A-Z]?$", "", x["assetId"])
        fams[fam].append((x.get("downloadCount", 0), x["assetId"], ", ".join(t for t in x.get("tags", []) if not t.isdigit() and t.lower() != x["assetId"].lower())[:80]))
    for fam, items in fams.items():
        items.sort(reverse=True)
        lines = [f"- {i} ({tags}) https://ambientcg.com/view?id={i}" for _, i, tags in items[:12]]
        add("resource", f"ambientCG materials: {fam}", f"{len(items)} free CC0 PBR materials in the {fam} family (color, normal, roughness, displacement maps). Most downloaded:\n" + "\n".join(lines),
            "ambientCG catalogue (ambientcg.com/api/v2), assets CC0", f"https://ambientcg.com/list?q={fam}", f"{fam} material texture pbr cc0 free ambientcg")
    ext = json.loads((ART / "ext_blender.json").read_text())["data"]
    for e in ext:
        if e.get("type") != "add-on":
            continue
        lic = ", ".join(l.replace("SPDX:", "") for l in e.get("license", []))
        add("extension", f"{e['name']} (Blender extension)",
            f"{e['name']}: {e.get('tagline', '')}\nCategory: {', '.join(e.get('tags', []))}. Free, license {lic}. Version {e.get('version')}, "
            f"for Blender {e.get('blender_version_min')}+. Install: Edit > Preferences > Get Extensions, search \"{e['name']}\".",
            "Blender Extensions platform (extensions.blender.org)", e.get("website", ""),
            f"{e['name']} {e.get('tagline', '')} {' '.join(e.get('tags', []))} addon add-on extension plugin")


def guides():
    """RusticEngine's own Blender Art Paths (agent/paths/art-blender-*.md), one entry per step, so a question
    like 'how do I make lava' finds the guided course too."""
    for f in sorted((HERE.parent / "agent/paths").glob("art-blender-*.md")):
        text = f.read_text()
        title = text.splitlines()[0].lstrip("# ").replace("Art Path: ", "")
        pid = f.stem
        for i, step in enumerate(text.split("\n## ")[1:], 1):
            head = step.splitlines()[0]
            entries.append({"kind": "guide", "name": f"{title} > {head}", "keywords": f"{pid.replace('-', ' ')} {title} {head} guide path tutorial",
                            "text": step[len(head):].strip()[:CHUNK], "source": f"RusticEngine Blender Art Path '{pid}' step {i} (open it with game_path)", "url": ""})


manual(); concepts(); keymap(); resources(); guides()
seen, out = set(), []
for e in entries:
    k = (e["kind"], e["name"])
    if k not in seen:
        seen.add(k); out.append(e)
OUT.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in out) + "\n")
from collections import Counter
print(Counter(e["kind"] for e in out), f"{OUT.stat().st_size // 1024} KB")
