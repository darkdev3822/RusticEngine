#!/usr/bin/env python3
"""Collect game design write-ups from Wikipedia (CC BY-SA 4.0): for each game, the Gameplay,
Development/Design and Reception sections. Ember uses these to understand what creators mean
when they say "like Dark Souls" or "Stardew vibes" (its design, not its code).

Output: corpus/design/wikipedia.jsonl  {"game", "title", "url", "sections": {name: text}}
Usage: python3 crawl_design.py
"""
import json, re, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "corpus/design/wikipedia.jsonl"
UA = "RusticEngine-design-crawler/0.1 (open-source game engine research; non-commercial)"
API = "https://en.wikipedia.org/w/api.php"

GAMES = """
Dark Souls|Dark Souls II|Dark Souls III|Bloodborne|Sekiro: Shadows Die Twice|Elden Ring|Demon's Souls|Armored Core VI: Fires of Rubicon
The Elder Scrolls III: Morrowind|The Elder Scrolls IV: Oblivion|The Elder Scrolls V: Skyrim|Fallout 3|Fallout: New Vegas|Fallout 4|Starfield
BioShock|BioShock Infinite|Civilization VI|XCOM: Enemy Unknown|Borderlands 2|NBA 2K|Mafia (video game)
Super Mario Bros.|Super Mario 64|Super Mario Odyssey|The Legend of Zelda: Ocarina of Time|The Legend of Zelda: Breath of the Wild|Metroid Prime|Super Metroid|Animal Crossing: New Horizons|Pokémon Red and Blue|Kirby's Dream Land|Super Smash Bros. Melee|Splatoon
Hollow Knight|Celeste (video game)|Hades (video game)|Stardew Valley|Undertale|Terraria|Minecraft|Dead Cells|Cuphead|Ori and the Blind Forest|Shovel Knight|Spelunky|The Binding of Isaac (video game)|Slay the Spire|Into the Breach|FTL: Faster Than Light|Braid (video game)|Limbo (video game)|Inside (video game)|Journey (2012 video game)|Fez (video game)|Papers, Please|Return of the Obra Dinn|Outer Wilds|Disco Elysium|Baba Is You|Vampire Survivors|Balatro|Hotline Miami|Katamari Damacy|Untitled Goose Game|A Short Hike|Firewatch|What Remains of Edith Finch|To the Moon (video game)|Gris (video game)|Night in the Woods|Oxygen Not Included|Rimworld|Factorio|Dwarf Fortress|Don't Starve|Subnautica|Valheim|Among Us|Fall Guys|Rocket League|Stray (video game)|Cult of the Lamb|Tunic (video game)|Animal Well|Lethal Company|Pizza Tower|Death Stranding|Hi-Fi Rush|Inscryption|Loop Hero|Noita (video game)|Risk of Rain 2|Enter the Gungeon|Darkest Dungeon|Frostpunk|Kentucky Route Zero|Sayonara Wild Hearts|Thomas Was Alone|VVVVVV|Super Meat Boy|N++|Downwell|Nuclear Throne|Brotato|Halls of Torment|Dave the Diver|Unpacking (video game)|Wilmot's Warehouse|Mini Metro|Townscaper|Superhot|Portal (video game)|Portal 2|Half-Life (video game)|Half-Life 2|Left 4 Dead|Team Fortress 2|Doom (1993 video game)|Doom (2016 video game)|Quake (video game)|Deus Ex (video game)|Thief: The Dark Project|System Shock|Prey (2017 video game)|Dishonored|Metal Gear Solid|Metal Gear Solid V: The Phantom Pain|Silent Hill 2|Resident Evil 4|Resident Evil (1996 video game)|Shadow of the Colossus|Ico (video game)|Okami|Devil May Cry 3: Dante's Awakening|Bayonetta|God of War (2018 video game)|Uncharted 2: Among Thieves|The Last of Us|Red Dead Redemption 2|Grand Theft Auto V|The Witcher 3: Wild Hunt|Mass Effect 2|Baldur's Gate 3|Divinity: Original Sin II|Chrono Trigger|Final Fantasy VI|Final Fantasy VII|EarthBound|Persona 5|Dragon Quest XI|Monster Hunter: World|Tetris|Pac-Man|Space Invaders|Street Fighter II|Sonic the Hedgehog (1991 video game)|Mega Man 2|Castlevania: Symphony of the Night|Contra (video game)|Galaga|Diablo II|StarCraft|World of Warcraft|League of Legends|Dota 2|Overwatch (video game)|Counter-Strike|Fortnite|Apex Legends|The Sims|SimCity (1989 video game)|RollerCoaster Tycoon|Age of Empires II|Heroes of Might and Magic III|Crusader Kings III|Stellaris|Kerbal Space Program|Cities: Skylines|Euro Truck Simulator 2|Microsoft Flight Simulator (2020 video game)|Guitar Hero|Beat Saber|Rhythm Heaven|Crypt of the NecroDancer|Overcooked|It Takes Two (video game)|Little Big Planet|Spore (2008 video game)|No Man's Sky|Sea of Thieves|Firewatch|Alan Wake 2|Control (video game)|Outlast|Amnesia: The Dark Descent|Five Nights at Freddy's|Phasmophobia|Lies of P|Nioh|Salt and Sanctuary|Blasphemous (video game)|Hyper Light Drifter|Death's Door|Hollow Knight: Silksong|Ender Lilies: Quietus of the Knights|Grime (video game)|Tetris Effect|Lumines|Rez (video game)|Thumper (video game)|Mirror's Edge|Titanfall 2|Tony Hawk's Pro Skater 2|Burnout 3: Takedown|Mario Kart 8|Gran Turismo (1997 video game)|F-Zero|Wipeout (video game)|Jet Set Radio|Pikmin|Advance Wars|Fire Emblem: Three Houses|Tactics Ogre|Into the Pit|Signalis|Cave Story|Lisa: The Painful|OneShot (video game)|Omori|Yume Nikki|Rain World|Hollow Knight|Ape Out|Getting Over It with Bennett Foddy|QWOP|Jump King|Celeste Classic
""".replace("\n", "|").split("|")
GAMES = list(dict.fromkeys(g.strip() for g in GAMES if g.strip()))
KEEP = re.compile(r"^(gameplay|game ?play|mechanics|synopsis|plot|development|design|production|game design|reception|legacy|influence|critical reception|setting)", re.I)


def get(params):
    params = {**params, "format": "json", "formatversion": "2", "maxlag": "5"}
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429 and e.code < 500:
                raise
            wait = int(e.headers.get("Retry-After") or 0) or 20 * (attempt + 1)
            time.sleep(wait)
    raise RuntimeError("gave up after retries")


def sections(text):
    """Split explaintext output ('== Gameplay ==' headings) into {heading: text}."""
    out, cur, buf = {}, "Intro", []
    for line in text.split("\n"):
        m = re.match(r"^(=+)\s*(.+?)\s*=+$", line)
        if m:
            out[cur] = "\n".join(buf).strip()
            cur, buf = m.group(2), []
            if len(m.group(1)) > 2:  # keep subsections under their parent
                cur = f"{list(out)[-1] if out else 'Intro'} / {m.group(2)}"
        else:
            buf.append(line)
    out[cur] = "\n".join(buf).strip()
    return out


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if OUT.exists():
        done = {json.loads(l)["game"] for l in open(OUT)}
    with open(OUT, "a") as fh:
        for g in GAMES:
            if g in done:
                continue
            try:
                # The exact article title first (names here are written as Wikipedia titles), search only as a fallback.
                page = get({"action": "query", "prop": "extracts", "explaintext": 1, "titles": g, "redirects": 1})["query"]["pages"][0]
                if page.get("missing") or not page.get("extract"):
                    hit = get({"action": "query", "list": "search", "srsearch": g + " video game", "srlimit": 1})["query"]["search"]
                    if not hit:
                        print("no match:", g); continue
                    page = get({"action": "query", "prop": "extracts", "explaintext": 1, "titles": hit[0]["title"], "redirects": 1})["query"]["pages"][0]
                title = page["title"]
                secs = sections(page.get("extract", ""))
                keep = {"Intro": secs.get("Intro", "")[:2500]}
                for k, v in secs.items():
                    head = k.split(" / ")[0]
                    if KEEP.match(head) and v.strip():
                        keep[k] = v[:6000]
                fh.write(json.dumps({"game": g, "title": title, "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
                                     "sections": keep}) + "\n")
                print(f"ok {g} -> {title} ({', '.join(list(keep)[:6])})", flush=True)
            except Exception as e:  # noqa: BLE001
                print("fail", g, e, flush=True)
            time.sleep(3.0)


if __name__ == "__main__":
    main()
