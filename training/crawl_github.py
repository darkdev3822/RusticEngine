#!/usr/bin/env python3
"""Find open-source projects on GitHub that use godot-rust 0.5 and collect their Rust code
for Ember's example library. Only permissively licensed repos are kept (license recorded per repo).

Uses the authenticated `gh` CLI. Code search allows ~10 requests/minute, so this paces itself.
Output: corpus/github/<owner>__<repo>/ (shallow clones, big files skipped) and corpus/github/repos.json

Usage: python3 crawl_github.py
"""
import json, re, subprocess, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "corpus/github"
LICENSES = {"MIT", "Apache-2.0", "MPL-2.0", "BSD-2-Clause", "BSD-3-Clause", "Unlicense", "CC0-1.0", "Zlib", "ISC", "0BSD"}
QUERIES = [
    'godot "version = \\"0.5" filename:Cargo.toml',
    '"godot = \\"0.5" filename:Cargo.toml',
    'godot "0.5" "api-4" filename:Cargo.toml',
    '"godot = { version = \\"0.5" filename:Cargo.toml',
]
V05 = re.compile(r'^\s*godot\s*=\s*(\{[^}\n]*version\s*=\s*)?"[=^~]?0\.5', re.M)
SKIP_REPOS = {"godot-rust/gdext", "godot-rust/demo-projects", "godot-rust/book"}


def gh(*args):
    r = subprocess.run(["gh", "api", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:300])
    return json.loads(r.stdout) if r.stdout.strip() else None


def search():
    found = {}
    for q in QUERIES:
        for page in range(1, 11):
            try:
                res = gh("-X", "GET", "search/code", "-f", f"q={q}", "-f", "per_page=100", "-f", f"page={page}")
            except RuntimeError as e:
                print("search stopped:", e)
                time.sleep(60)
                break
            for it in res.get("items", []):
                found.setdefault(it["repository"]["full_name"], set()).add(it["path"])
            print(f"{q[:40]!r} page {page}: {len(res.get('items', []))} hits, {len(found)} repos")
            time.sleep(7)
            if len(res.get("items", [])) < 100:
                break
    return found


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta_path = OUT / "repos.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    found = search()
    for name, paths in sorted(found.items()):
        if name in SKIP_REPOS or name in meta:
            continue
        try:
            info = gh(f"repos/{name}")
        except RuntimeError as e:
            print("skip", name, e)
            continue
        lic = (info.get("license") or {}).get("spdx_id")
        entry = {"license": lic, "stars": info.get("stargazers_count", 0), "pushed": info.get("pushed_at"), "kept": False}
        meta[name] = entry
        if lic not in LICENSES or info.get("fork") or info.get("size", 0) > 300_000:
            print(f"skip {name}: license {lic}, size {info.get('size')}")
            continue
        # Confirm a Cargo.toml really depends on godot 0.5 (not 0.1-0.4, whose APIs differ).
        ok = False
        for p in sorted(paths)[:5]:
            try:
                c = gh(f"repos/{name}/contents/{p}", "-H", "Accept: application/vnd.github.raw")
            except Exception:
                c = None
            if c is None:
                r = subprocess.run(["gh", "api", f"repos/{name}/contents/{p}", "-H", "Accept: application/vnd.github.raw"],
                                   capture_output=True, text=True)
                c = r.stdout
            if isinstance(c, str) and V05.search(c):
                ok = True
                break
        if not ok:
            print(f"skip {name}: not godot 0.5")
            continue
        dest = OUT / name.replace("/", "__")
        if not dest.exists():
            r = subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:limit=300k",
                                f"https://github.com/{name}.git", str(dest)], capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                print("clone failed", name, r.stderr[:200])
                continue
        entry["kept"] = True
        print(f"kept {name} ({lic}, {entry['stars']} stars)")
        meta_path.write_text(json.dumps(meta, indent=1))
    meta_path.write_text(json.dumps(meta, indent=1))
    kept = [n for n, e in meta.items() if e["kept"]]
    print(f"{len(kept)} repos kept")


if __name__ == "__main__":
    main()
