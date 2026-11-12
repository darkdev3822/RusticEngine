#!/usr/bin/env python3
"""Does each new mechanic do what was asked? Scores saved probe runs (training/probe_runs/<model>/<key>.txt)
by checking the mechanic's own code for the behavior the ask needs (a cheap semantic check on top of
'it builds'). Usage: python3 score_new_mechanic.py [MODEL_DIR ...]"""
import re, sys
from pathlib import Path

# key -> (description, regexes that must ALL match the mechanic's logic code)
NEEDS = {
    "dash": ("uses Shift", [r"Key::SHIFT|\"shift\"|SHIFT"]),
    "wall_jump": ("checks for a wall", [r"is_on_wall|get_wall_normal|is_on_wall_only"]),
    "regen": ("heals through Character Stats after a delay", [r"stats", r"heal|restore|health"]),
    "coin": ("counts coins", [r"coins?|count", r"\+=\s*1|\+ 1|add"]),
    "door": ("moves/opens something", [r"set_position|set_rotation|set_visible|translate|rotate|open"]),
    "timer": ("60 seconds + a time-up signal", [r"60", r"#\[signal\]"]),
    "patrol": ("walks between two points", [r"move_and_slide", r"direction|point|target"]),
    "checkpoint": ("remembers a respawn position and uses it after a fall", [r"global_position|position", r"respawn|fall|y\s*<"]),
}

def logic(text):
    """The created mechanic's .rs files except tuning.rs and mod.rs."""
    out, keep = [], False
    for line in text.split("\nFILES:\n", 1)[-1].splitlines():
        if line.startswith("--- "):
            keep = line.endswith(".rs") and not line.endswith(("/mod.rs", "/tuning.rs"))
            continue
        if keep:
            out.append(line)
    return "\n".join(out)

def main():
    for d in sys.argv[1:] or [str(p) for p in (Path(__file__).parent / "probe_runs").iterdir() if p.is_dir()]:
        n = total = 0
        for f in sorted(Path(d).glob("*.txt")):
            t = f.read_text()
            built = "FINAL BUILD: True" in t
            desc, pats = NEEDS.get(f.stem, ("?", []))
            code = logic(t)
            does = bool(code) and all(re.search(p, code, re.I) for p in pats)
            ok = built and does
            n += ok; total += 1
            print(f"{Path(d).name:12s} {'OK ' if ok else '-- '} {f.stem:11s} built={built!s:5} does_it={does!s:5} ({desc})")
        print(f"== {Path(d).name}: {n}/{total} build AND do what was asked\n")


if __name__ == "__main__":
    main()
