#!/usr/bin/env python3
"""Fetch a hand-picked list of respected, human-made open-source games and engines.

Each repo is pinned to its last commit before 2023 (before AI coding assistants were common),
unless `head` is set (projects whose pre-2023 code targets an older Godot API).
Only source code and design docs are checked out (sparse), not art or music.

Output: corpus/curated/<name>/ and corpus/curated/repos.json
Usage: python3 crawl_curated.py
"""
import json, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "corpus/curated"
CUTOFF = "2023-01-01"
CODE = ["*.rs", "*.gd", "*.cs", "*.cpp", "*.hpp", "*.h", "*.c", "*.java", "*.lua", "*.md", "*.txt", "Cargo.toml", "project.godot", "*.tscn"]

REPOS = [
    # name, url, license, language, why, head?
    ("veloren", "https://gitlab.com/veloren/veloren.git", "GPL-3.0", "Rust", "large open-world voxel RPG, years of human design", False),
    ("jumpy", "https://github.com/fishfolk/jumpy.git", "MIT/Apache-2.0", "Rust", "polished 2D platform shooter", False),
    ("punchy", "https://github.com/fishfolk/punchy.git", "MIT/Apache-2.0", "Rust", "beat 'em up", False),
    ("zemeroth", "https://github.com/ozkriff/zemeroth.git", "MIT/Apache-2.0", "Rust", "turn-based tactics, small and clean", False),
    ("rust-roguelike-tutorial", "https://github.com/amethyst/rustrogueliketutorial.git", "MIT", "Rust", "roguelike built step by step, explained", False),
    ("bracket-lib", "https://github.com/amethyst/bracket-lib.git", "MIT", "Rust", "roguelike toolkit: FOV, pathfinding, noise", False),
    ("doukutsu-rs", "https://github.com/doukutsu-rs/doukutsu-rs.git", "MIT", "Rust", "Cave Story engine reimplementation", False),
    ("abstreet", "https://github.com/a-b-street/abstreet.git", "Apache-2.0", "Rust", "traffic simulation game", False),
    ("macroquad", "https://github.com/not-fl3/macroquad.git", "MIT/Apache-2.0", "Rust", "small game library with clean examples", False),
    ("godot-demo-projects", "https://github.com/godotengine/godot-demo-projects.git", "MIT", "GDScript", "official Godot demos by the engine's maintainers (Godot 4 API)", True),
    ("pixelorama", "https://github.com/Orama-Interactive/Pixelorama.git", "MIT", "GDScript", "established pixel art editor built in Godot", True),
    ("godot-open-rpg", "https://github.com/gdquest/godot-open-rpg.git", "MIT", "GDScript", "GDQuest's teaching RPG", True),
    ("tanks-of-freedom", "https://github.com/w84death/Tanks-of-Freedom.git", "MIT", "GDScript", "turn-based strategy in Godot", False),
    ("wesnoth", "https://github.com/wesnoth/wesnoth.git", "GPL-2.0", "C++", "Battle for Wesnoth: turn-based strategy, 20 years of design", False),
    ("supertux", "https://github.com/SuperTux/supertux.git", "GPL-3.0", "C++", "classic 2D platformer", False),
    ("openttd", "https://github.com/OpenTTD/OpenTTD.git", "GPL-2.0", "C++", "transport tycoon simulation", False),
    ("openmw", "https://github.com/OpenMW/openmw.git", "GPL-3.0", "C++", "open reimplementation of Morrowind's engine: Bethesda-style RPG mechanics", False),
    ("endless-sky", "https://github.com/endless-sky/endless-sky.git", "GPL-3.0", "C++", "space trading and combat", False),
    ("mindustry", "https://github.com/Anuken/Mindustry.git", "GPL-3.0", "Java", "factory tower defense", False),
    ("shattered-pixel-dungeon", "https://github.com/00-Evan/shattered-pixel-dungeon.git", "GPL-3.0", "Java", "beloved roguelike", False),
    ("doom", "https://github.com/id-Software/DOOM.git", "GPL-2.0", "C", "id Software's DOOM (1993), released by id", False),
    ("quake", "https://github.com/id-Software/Quake.git", "GPL-2.0", "C", "id Software's Quake, released by id", False),
    ("cataclysm-dda", "https://github.com/CleverRaven/Cataclysm-DDA.git", "CC-BY-SA-3.0", "C++", "deep survival roguelike", False),
    ("supertuxkart", "https://github.com/supertuxkart/stk-code.git", "GPL-3.0", "C++", "kart racer", False),
    ("pioneer", "https://github.com/pioneerspacesim/pioneer.git", "GPL-3.0", "C++/Lua", "space sim", False),
    # Open recreations of beloved games (clean reimplementations, not decompilations) and official source releases.
    ("daggerfall-unity", "https://github.com/Interkarma/daggerfall-unity.git", "MIT", "C#", "recreation: The Elder Scrolls II: Daggerfall", False),
    ("openrct2", "https://github.com/OpenRCT2/OpenRCT2.git", "GPL-3.0", "C++", "recreation: RollerCoaster Tycoon 2", False),
    ("openra", "https://github.com/OpenRA/OpenRA.git", "GPL-3.0", "C#", "recreation: Command & Conquer, Red Alert, Dune 2000", False),
    ("openxcom", "https://github.com/OpenXcom/OpenXcom.git", "GPL-3.0", "C++", "recreation: X-COM: UFO Defense", False),
    ("fheroes2", "https://github.com/ihhub/fheroes2.git", "GPL-2.0", "C++", "recreation: Heroes of Might and Magic II", False),
    ("vcmi", "https://github.com/vcmi/vcmi.git", "GPL-2.0", "C++", "recreation: Heroes of Might and Magic III", False),
    ("corsixth", "https://github.com/CorsixTH/CorsixTH.git", "MIT", "Lua/C++", "recreation: Theme Hospital", False),
    ("openlara", "https://github.com/XProger/OpenLara.git", "BSD-2-Clause", "C++", "recreation: Tomb Raider", False),
    ("xoreos", "https://github.com/xoreos/xoreos.git", "GPL-3.0", "C++", "recreation: BioWare's Aurora engine (Neverwinter Nights, KotOR)", False),
    ("exult", "https://github.com/exult/exult.git", "GPL-2.0", "C++", "recreation: Ultima VII", False),
    ("freeciv", "https://github.com/freeciv/freeciv.git", "GPL-2.0", "C", "open take on Civilization", False),
    ("openage", "https://github.com/SFTtech/openage.git", "GPL-3.0", "C++/Python", "recreation: Age of Empires II engine", False),
    ("arx-libertatis", "https://github.com/arx/ArxLibertatis.git", "GPL-3.0", "C++", "official source release: Arx Fatalis (Arkane), an immersive sim", False),
    ("system-shock", "https://github.com/Interrupt/systemshock.git", "GPL-3.0", "C", "official source release: System Shock", False),
    ("wolf3d", "https://github.com/id-Software/wolf3d.git", "GPL-2.0", "C", "official source release: Wolfenstein 3D", False),
    ("quake3", "https://github.com/id-Software/Quake-III-Arena.git", "GPL-2.0", "C", "official source release: Quake III Arena", False),
    ("warzone2100", "https://github.com/Warzone2100/warzone2100.git", "GPL-2.0", "C++", "official source release: Warzone 2100", False),
    ("celeste-player", "https://github.com/NoelFB/Celeste.git", "see repo", "C#", "Celeste's player controller, published by its developer for learning", True),
]


def git(*args, cwd=None, timeout=1800):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta_path = OUT / "repos.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    for name, url, lic, lang, why, head in REPOS:
        if meta.get(name, {}).get("ok"):
            continue
        d = OUT / name
        if not d.exists():
            r = git("clone", "-q", "--filter=blob:none", "--no-checkout", url, str(d))
            if r.returncode:
                print("clone failed", name, r.stderr[:200], flush=True)
                meta[name] = {"ok": False, "error": r.stderr[:200]}
                continue
        rev = "HEAD"
        if not head:
            old = git("rev-list", "-1", f"--before={CUTOFF}", "HEAD", cwd=d).stdout.strip()
            rev = old or "HEAD"
        git("sparse-checkout", "set", "--no-cone", *CODE, cwd=d)
        r = git("checkout", "-q", rev, cwd=d)
        date = git("log", "-1", "--format=%cs", rev, cwd=d).stdout.strip()
        files = sum(1 for _ in d.rglob("*") if _.is_file() and ".git" not in _.parts)
        meta[name] = {"ok": r.returncode == 0, "url": url, "license": lic, "language": lang, "why": why, "commit_date": date, "files": files}
        print(f"{'ok' if r.returncode == 0 else 'FAIL'} {name}: {lang}, {lic}, code as of {date}, {files} files", flush=True)
        meta_path.write_text(json.dumps(meta, indent=1))
    meta_path.write_text(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
