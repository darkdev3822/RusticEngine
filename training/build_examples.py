#!/usr/bin/env python3
"""Build Ember's example library from the official godot-rust repos (MPL-2.0) in corpus/.

Chunks: each Rust fn / impl / struct item (split per method inside big impls), and each Rust code
block from the godot-rust book with its section heading. Output: ../agent/examples/examples.jsonl
  {"src": "book/src/register/signals.md", "title": "...", "code": "..."}

Usage: python3 build_examples.py
"""
import json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
C = HERE / "corpus"
OUT = HERE.parent / "agent/examples/examples.jsonl"
MAX_LINES = 60
GODOT_USE = re.compile(r"base_mut\(\)|base\(\)\.|\.signals\(\)|get_node_as|::singleton\(\)|new_alloc\(\)|instantiate|#\[func\]|godot_print!|Gd<|::new_gd\(\)|#\[class\(")
SKIP = re.compile(r"benchmarks|framework|editor_test|/target/|build\.rs")


def strip_noise(line):
    # Remove strings and comments so braces inside them don't count.
    line = re.sub(r'"(\\.|[^"\\])*"', '""', line)
    line = re.sub(r"'(\\.|[^'\\])'", "''", line)
    return line.split("//")[0]


def items(text):
    """Yield (start, end) line ranges of brace-balanced items, splitting impl blocks per member."""
    lines = text.split("\n")
    depth, start, out, attrs = 0, None, [], None
    stack = []  # (depth_at_open, start_line, header)
    for i, raw in enumerate(lines):
        l = strip_noise(raw)
        s = l.strip()
        if depth in (0, 1) and start is None and (s.startswith("#[") or s.startswith("///")):
            attrs = i if attrs is None else attrs
        head = re.match(r"\s*(pub(\([^)]*\))?\s+)?(unsafe\s+)?(async\s+)?(fn|impl|struct|enum|trait|mod)\b", l)
        if head and start is None and depth in (0, 1):
            start = attrs if attrs is not None else i
            kind = head.group(5)
            stack.append((depth, start, kind))
        if not head and not s.startswith("#[") and not s.startswith("///") and s:
            if start is None:
                attrs = None
        depth += l.count("{") - l.count("}")
        if start is not None and depth == stack[-1][0] and ("}" in l or l.rstrip().endswith(";")):
            d0, st, kind = stack.pop()
            out.append((st, i, kind))
            start, attrs = None, None
    return lines, out


def rust_chunks(path, rel):
    text = path.read_text(errors="ignore")
    lines, spans = items(text)
    for st, en, kind in spans:
        body = lines[st:en + 1]
        if kind in ("impl", "mod") and len(body) > MAX_LINES:
            # Recurse into the block: split it per member.
            inner = "\n".join(body[1:-1])
            ilines, ispans = items(textwrap_dedent(inner))
            header = body[0].strip().rstrip("{").strip()
            for a, b, _ in ispans:
                part = ilines[a:b + 1]
                if 3 <= len(part) <= MAX_LINES * 2:
                    yield {"src": rel, "title": header, "code": "\n".join(part)[:4000]}
            continue
        if 3 <= len(body) <= MAX_LINES * 2:
            yield {"src": rel, "title": body[0].strip()[:120], "code": "\n".join(body)[:4000]}


def textwrap_dedent(s):
    import textwrap
    return textwrap.dedent(s)


def book_chunks(path, rel):
    heading = ""
    page = ""
    text = path.read_text(errors="ignore")
    for m in re.finditer(r"^(#{1,4}) ([^\n]+)$|^```(\w*)[^\n]*\n(.*?)^```", text, re.M | re.S):
        if m.group(1):
            if len(m.group(1)) == 1:
                page = m.group(2).strip()
            heading = m.group(2).strip()
        elif m.group(3) in ("rust", "rs") and m.group(4).strip():
            code = "\n".join(l for l in m.group(4).split("\n") if not l.startswith("# "))  # mdbook hidden lines
            if code.count("\n") >= 2:
                yield {"src": rel, "title": f"{page} > {heading}" if page != heading else heading, "code": code[:4000]}


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    seen, rows = set(), []
    for p in sorted((C / "book/src").rglob("*.md")):
        if "/migrate/" in str(p) or "/contribute/" in str(p):  # old APIs and contributor docs
            continue
        rows += book_chunks(p, str(p.relative_to(C)))
    for base in ("demo-projects", "gdext/itest/rust/src"):
        for p in sorted((C / base).rglob("*.rs")):
            rel = str(p.relative_to(C))
            if not SKIP.search(rel):
                rows += rust_chunks(p, rel)
    # Ember's own verified training traces: every .rs file written there compiled and ran.
    for p in sorted((HERE / "data").glob("traces*.jsonl")):
        for line in open(p):
            t = json.loads(line)
            ask = next((m["content"].split("\n\n[Editor")[0] for m in t["messages"] if m["role"] == "user"), "")
            files, changed, pending = {}, set(), []
            for m in t["messages"]:
                if m["role"] == "assistant":
                    pending = []
                    for c in m.get("tool_calls") or []:
                        a = c["function"]["arguments"]
                        pending.append((c["function"]["name"], json.loads(a) if isinstance(a, str) else a))
                elif m["role"] == "tool" and pending:
                    name, a = pending.pop(0)
                    path = a.get("path", "")
                    if not path.endswith(".rs"):
                        continue
                    if name == "read_file" and not m["content"].startswith("Can't"):
                        files[path] = m["content"]
                    elif name == "write_file":
                        files[path] = a.get("content", ""); changed.add(path)
                    elif name == "edit_file" and path in files and a.get("old_text") and a["old_text"] in files[path]:
                        files[path] = files[path].replace(a["old_text"], a.get("new_text", ""), 1); changed.add(path)
            # Replay mistakes would leave broken code; only keep traces without a deliberate mistake.
            if t.get("mistake"):
                continue
            for path in sorted(changed):
                text = files[path]
                if 5 <= text.count("\n") <= 150:
                    rows.append({"src": f"ember-verified: {path}", "title": ask[:100], "code": text})
    # Open-source games found by crawl_github.py (licenses in corpus/github/repos.json).
    meta_path = C / "github/repos.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    per_repo = {}
    for name, e in sorted(meta.items()):
        d = C / "github" / name.replace("/", "__")
        if not e.get("kept") or not d.exists():
            continue
        for p in sorted(d.rglob("*.rs")):
            rel = str(p.relative_to(d))
            if re.search(r"(^|/)(target|tests?|benches|examples)/|build\.rs$", rel) or p.stat().st_size > 200_000:
                continue
            for r in rust_chunks(p, f"github {name}/{rel} ({e['license']})"):
                # Only code that actually touches Godot is useful as a reference.
                if GODOT_USE.search(r["code"]) and per_repo.get(name, 0) < 250:
                    per_repo[name] = per_repo.get(name, 0) + 1
                    rows.append(r)
    # Official Godot 4 demos (MIT): GDScript, but the API names are the same in Rust (snake_case).
    demos = C / "curated/godot-demo-projects"
    for p in sorted(demos.rglob("*.gd")) if demos.exists() else []:
        rel = str(p.relative_to(demos))
        lines = p.read_text(errors="ignore").split("\n")
        starts = [i for i, l in enumerate(lines) if l.startswith("func ")]
        for n, st in enumerate(starts):
            en = starts[n + 1] if n + 1 < len(starts) else len(lines)
            body = "\n".join(lines[st:en]).rstrip()
            if 3 <= body.count("\n") <= 60 and "." in body:
                rows.append({"src": f"godot-demo-projects/{rel} (GDScript, MIT: translate to Rust)", "title": lines[st][5:].split("(")[0], "code": body})
    # Solved godot-rust problems (crawl_debug.py). Older issues describe APIs that have since changed.
    qa = C / "debug/gdext_qa.jsonl"
    for line in open(qa) if qa.exists() else []:
        q = json.loads(line)
        if q["date"] >= "2025-01-01" and ({"bug", "question"} & set(q["labels"])):
            text = f"QUESTION: {q['question'][:1200]}\n\nMAINTAINER ANSWER: {q['answers'][0][:1800]}"
            rows.append({"src": f"gdext issue {q['url']} ({q['date']})", "title": q["title"], "code": text})
    out = []
    for r in rows:
        key = re.sub(r"\s+", "", r["code"])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    with open(OUT, "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    print(f"{len(out)} examples, {OUT.stat().st_size // 1024} KB -> {OUT}")


if __name__ == "__main__":
    main()
