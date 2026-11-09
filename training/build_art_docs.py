#!/usr/bin/env python3
"""Turn the Blender Manual's modeling chapters into entries for Ember's design library.

Source: corpus/art/blender-manual (sparse clone of projects.blender.org/blender/blender-manual).
The Blender Manual is by the Blender Documentation Team, licensed CC BY-SA 4.0
(https://docs.blender.org/manual/en/dev/). Entries keep that attribution.

Krita's manual (corpus/art/docs-krita-org) is GFDL, so it is study material only and is NOT
shipped in Ember's library.

Appends {"kind": "manual", ...} lines to agent/examples/design.jsonl (replacing earlier manual entries).
"""
import json, re
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "corpus/art/blender-manual/manual"
OUT = HERE.parent / "agent/examples/design.jsonl"
MAX_TEXT = 2200


def clean(rst: str) -> str:
    out, skip_indent = [], None
    for line in rst.splitlines():
        if skip_indent is not None:
            if line.strip() == "" or line.startswith(" " * (skip_indent + 1)):
                continue
            skip_indent = None
        s = line.strip()
        # Drop directives that carry no prose (images, toctrees, references, labels, figures).
        m = re.match(r"(\s*)\.\. (\w[\w-]*)::", line)
        if m and m.group(2) in ("figure", "image", "toctree", "only", "container", "rubric", "youtube", "peertube", "vimeo", "list-table"):
            skip_indent = len(m.group(1))
            continue
        if re.match(r"\s*\.\. _[^:]+:\s*$", line) or re.match(r"\s*\.\. \|", line) or s.startswith(".. index::"):
            continue
        if m and m.group(2) == "reference":
            continue  # its indented fields (Shortcut: ...) are kept below
        if m and m.group(2) in ("admonition", "note", "tip", "hint", "important", "seealso", "warning"):
            title = line.split("::", 1)[1].strip()
            out.append(f"{m.group(2).capitalize()}: {title}" if title else f"{m.group(2).capitalize()}:")
            continue
        if re.fullmatch(r"[=\-~^*#+\"']{3,}", s):
            continue  # heading underline
        if s in (":Mode:", ":Menu:") or re.match(r":(Mode|Menu|Panel|Header|Tool):", s):
            continue
        line = re.sub(r":kbd:`([^`]+)`", r"\1", line)
        line = re.sub(r":menuselection:`([^`]+)`", lambda m: m.group(1).replace("-->", ">"), line)
        line = re.sub(r":(?:doc|ref|term|abbr)?:?`([^`<]+?)\s*<[^>]+>`", r"\1", line)
        line = re.sub(r":doc:`/?(?:[\w-]+/)*([\w-]+)`", lambda m: m.group(1).replace("_", " "), line)
        line = re.sub(r":\w+:`([^`]+)`", r"\1", line)
        line = re.sub(r"``([^`]+)``", r"\1", line)
        line = re.sub(r"\|(\w[\w-]*)\|", r"\1", line)
        line = line.replace(":Shortcut:", "Shortcut:")
        out.append(line.rstrip())
    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def main():
    lines = [l for l in OUT.read_text().splitlines() if json.loads(l).get("kind") != "manual"]
    added = 0
    names = {json.loads(l)["name"] for l in lines}
    for f in sorted(SRC.rglob("*.rst")):
        if f.name in ("index.rst", "introduction.rst") and "meshes" not in f.parts[-2:]:
            pass
        raw = f.read_text(errors="ignore")
        title_m = re.search(r"^(?:[*=#]{3,}\n)?([^\n]+)\n[*=#\-]{3,}\n", raw, re.M)
        if not title_m:
            continue
        title = title_m.group(1).strip()
        text = clean(raw[title_m.end():])
        if len(text) < 200:
            continue
        rel = f.relative_to(SRC).with_suffix("")
        url = f"https://docs.blender.org/manual/en/latest/{rel.as_posix()}.html"
        topic = " ".join(p.replace("_", " ") for p in rel.parts[:-1])
        entry = {
            "kind": "manual",
            "name": f"{title} (Blender)",
            "keywords": f"{title} {topic} blender modeling 3d model mesh",
            "text": text[:MAX_TEXT],
            "source": f"Blender Manual, {url}, by the Blender Documentation Team, CC BY-SA 4.0",
        }
        if entry["name"] in names:
            continue
        names.add(entry["name"])
        lines.append(json.dumps(entry, ensure_ascii=False))
        added += 1
    OUT.write_text("\n".join(lines) + "\n")
    print(f"{added} Blender Manual entries -> {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
