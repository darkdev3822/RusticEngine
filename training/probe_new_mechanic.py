#!/usr/bin/env python3
"""Can Ember make a NEW mechanic that builds? Held-out asks from the Mechanics tab's
"A new mechanic of my own (with Ember)". Pass = a new mechanics/<id>/ exists, `mechanic` tool used,
and the project builds at the end (checked independently with cargo, not just Ember's last build).
Usage: python3 probe_new_mechanic.py MODEL [MODEL...]   (PROBE_ONLY=dash  PROBE_KEEP=1 keeps projects)
Writes failing build errors to /tmp-free location: training/probe_runs/<model>/<id>.txt
"""
import json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path
from probe_mechanics import model_args, AGENT, BASE, MECH, NAMES
from score_new_mechanic import NEEDS

ASKS = [  # (key, ask)
    ("dash", "make me a new mechanic: a dash. Pressing Shift gives the first-person player a quick burst forward, with a cooldown"),
    ("wall_jump", "new mechanic please: wall jump, so the first-person player can jump off walls"),
    ("regen", "I want a new mechanic: health slowly regenerates if you haven't been hurt for a few seconds (uses Character Stats)"),
    ("coin", "make a new mechanic: coins you can pick up, with a counter of how many you have"),
    ("door", "new mechanic: a door that opens when the player walks close to it and closes again after"),
    ("timer", "make me a countdown timer mechanic: the level has 60 seconds, and a signal fires when time runs out"),
    ("patrol", "new mechanic: an enemy that walks back and forth between two points"),
    ("checkpoint", "I need a checkpoint mechanic: touching a checkpoint saves where the player respawns after falling off the map"),
]
CTX = "in the Mechanics tab, looking at the First-Person Controller mechanic (res://mechanics/first_person, ...). The user chose Add Mechanic > A new mechanic of my own."
OUT = Path(__file__).parent / "probe_runs"
# On disk, not /tmp: /tmp is RAM here, and each project's Rust build is ~1.7 GB.
WORK = Path(__file__).parent / "probe_tmp"
WORK.mkdir(exist_ok=True)

def is_template(proj, mid):
    """True if the mechanic's logic files are still exactly one of the kind templates (nothing of its own)."""
    tp = Path(proj, "mechanics", mid, "mechanic.toml")
    if not tp.exists():
        return False  # made by hand, not from a template
    toml = tp.read_text()
    val = lambda k: next((l.split("=", 1)[1].strip().strip('"') for l in toml.splitlines() if l.startswith(k + " ")), "")
    def logic(root):
        src = Path(root, "mechanics", mid, "src")
        return {f.name: f.read_text() for f in src.glob("*.rs") if f.name not in ("mod.rs", "tuning.rs")}
    mine = logic(proj)
    for kind in ("player_ability", "trigger", "mover", "timer", "custom"):
        t = tempfile.mkdtemp(prefix="tmpl_", dir=WORK)
        Path(t, "rust/src").mkdir(parents=True); Path(t, "rust/src/lib.rs").write_text("")
        args = {"action": "new", "id": mid, "name": val("name"), "summary": val("summary"), "node": val("node"), "kind": kind,
                "base": "Node" if kind == "custom" else ""}
        subprocess.run([AGENT, "--project", t, "--tool", "mechanic", "--args", json.dumps(args)], capture_output=True)
        same = logic(t) == mine
        shutil.rmtree(t)
        if same:
            return True
    return False

def run(model, key, ask):
    d = tempfile.mkdtemp(prefix="newmech_", dir=WORK)
    shutil.copytree(BASE, d + "/p")
    shutil.copytree(MECH, d + "/p/mechanics", ignore=shutil.ignore_patterns("target"))
    lib = Path(d + "/p/rust/src/lib.rs")
    lib.write_text(lib.read_text() + "".join(f'\n#[path = "../../mechanics/{m}/src/mod.rs"]\nmod {m};' for m in NAMES) + "\n")
    t0 = time.time()
    p = subprocess.Popen([AGENT, "--project", d + "/p", *model_args(model), "--mode", "autonomous"],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    tools, builds, text, guards = [], [], "", []
    # Ember is told to ask what the mechanic should do before making it; a creator would answer.
    turns = [ask, "Sounds good, go ahead and make it. Use sensible defaults for anything I didn't say."]
    try:
        for turn in turns:
            if turn is not ask and "mechanic" in [t.split("(")[0] for t in tools] and any(t.split("(")[0] in ("edit_file", "write_file") for t in tools[[t.split("(")[0] for t in tools].index("mechanic") + 1:]):
                break
            p.stdin.write(json.dumps({"type": "user", "text": turn, "context": CTX}) + "\n"); p.stdin.flush()
            for line in p.stdout:
                v = json.loads(line)
                if v["type"] == "tool_start": tools.append(v["name"])
                elif v["type"] == "tool_end":
                    if v["name"] == "build_rust": builds.append(v["ok"])
                    if not v.get("ok", True) and tools: tools[-1] += "(FAILED)"
                elif v["type"] == "text": text += v["delta"]
                elif v["type"] == "guard": guards.append(v.get("name"))
                elif v["type"] in ("done", "error"): break
                if time.time() - t0 > 900: break
            text += "\n[turn end]\n"
    finally:
        p.kill()
    created = [x.name for x in Path(d + "/p/mechanics").iterdir() if x.is_dir() and x.name not in NAMES]
    r = subprocess.run(["cargo", "build", "--quiet", "--message-format=short"], cwd=d + "/p/rust", capture_output=True, text=True)
    ok_build = r.returncode == 0
    # The logic must actually be written: some edit after the mechanic was created (a bare scaffold also builds).
    wrote = "mechanic" in [t.split("(")[0] for t in tools] and any(t.split("(")[0] in ("edit_file", "write_file") for t in tools[[t.split("(")[0] for t in tools].index("mechanic") + 1:])
    unchanged = bool(created) and is_template(d + "/p", created[0])
    # Pass = it builds AND its code does what was asked (score_new_mechanic.NEEDS). A starting variant that
    # already is the asked mechanic is fine unchanged; an unrelated example left as-is fails the check.
    code = "\n".join(f.read_text() for c in created for f in Path(d + f"/p/mechanics/{c}/src").glob("*.rs")
                     if f.name not in ("mod.rs", "tuning.rs"))
    does = bool(code) and all(re.search(pat, code, re.I) for pat in NEEDS[key][1])
    ok = bool(created) and ok_build and does
    errs = [l for l in r.stderr.splitlines() if l.startswith(("error", "src/", "../")) or "error[" in l]
    od = OUT / model.replace(":", "_").replace("/", "_"); od.mkdir(parents=True, exist_ok=True)
    (od / f"{key}.txt").write_text(f"ASK: {ask}\nTOOLS: {tools}\nBUILDS: {builds}\nCREATED: {created}\nFINAL BUILD: {ok_build}\n\n"
                                   + r.stderr[-6000:] + "\n\nREPLY:\n" + text[-3000:] + "\n\nFILES:\n"
                                   + "".join(f"--- {f}\n{f.read_text()}\n" for c in created for f in sorted(Path(d + f"/p/mechanics/{c}").rglob("*.rs"))))
    print(f"{model:20s} {'OK ' if ok else '-- '} {key:11s} created={created} builds={builds} final={ok_build} "
          f"does_it={does} wrote={wrote} template_unchanged={unchanged} {int(time.time()-t0)}s tools={len(tools)} {(errs[:2] if not ok_build else '')}", flush=True)
    if os.environ.get("PROBE_KEEP"): print("    kept", d)
    else: shutil.rmtree(d)
    return ok

if __name__ == "__main__":
    only = [k for k in os.environ.get("PROBE_ONLY", "").split(",") if k]
    for model in sys.argv[1:]:
        n = sum(run(model, k, a) for k, a in ASKS if not only or k in only)
        print(f"== {model}: new mechanics {n}/{len([1 for k,_ in ASKS if not only or k in only])}", flush=True)
