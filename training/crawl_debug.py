#!/usr/bin/env python3
"""Solved godot-rust problems: closed gdext issues (bugs and questions) with maintainer replies.
Output: corpus/debug/gdext_qa.jsonl  {"title","url","date","labels","question","answers":[...]}"""
import json, subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent / "corpus/debug/gdext_qa.jsonl"
MAINTAINER = {"MEMBER", "OWNER", "COLLABORATOR", "CONTRIBUTOR"}


def api(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else []


def main():
    rows = []
    for page in range(1, 16):
        issues = api(f"repos/godot-rust/gdext/issues?state=closed&per_page=100&page={page}&sort=comments")
        if not issues:
            break
        for i in issues:
            if "pull_request" in i or i["comments"] == 0 or i.get("state_reason") == "not_planned":
                continue
            comments = api(f"repos/godot-rust/gdext/issues/{i['number']}/comments?per_page=30")
            answers = [c["body"][:2500] for c in comments if c.get("author_association") in MAINTAINER][:4]
            if not answers:
                continue
            rows.append({"title": i["title"], "url": i["html_url"], "date": i["created_at"][:10],
                         "labels": [l["name"] for l in i["labels"]], "question": (i["body"] or "")[:3000], "answers": answers})
        print(f"page {page}: {len(rows)} solved issues so far", flush=True)
    with open(OUT, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(len(rows), "solved issues")


if __name__ == "__main__":
    main()
