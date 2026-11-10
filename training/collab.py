#!/usr/bin/env python3
"""Collaborative Ember conversations: Ember as a creative partner, not a one-prompt game machine.

Scenarios (all tool results are real, from running rustic-agent on a real project):
  kickoff     getting to know the creator's game, then writing design/vision.md in their words
  ask         a vague request -> Ember asks a creative question -> builds what the creator chose
  concept     concept art -> look_at_image -> "did I get it right?" -> notes into design/vision.md
  assets      the creator's own sound/sprite -> asset_info -> asks where it goes -> wires it in
  learning    learning mode: explain, let them type it, check it, hint (not fix) on mistakes
  modes       switching between learning and autonomous mode
  draw        the creator asks Ember for art: it draws an SVG, no lecture
  needs_art   what still needs real art -> design/assets.md

Usage: python3 collab.py OUT.jsonl [scenario ...]
"""
import json, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_traces as G  # noqa: E402
from gen_traces import FEATURES, Trace, tool, fresh_project, apply_silently, run_feature, rng  # noqa: E402

ART = HERE / "concept_art"
SAMPLES = HERE / "sample_assets"


def system_for(project: Path, mode: str) -> str:
    return subprocess.run([str(G.AGENT), "--print-system", "--project", str(project), "--mode", mode],
                          capture_output=True, text=True, check=True).stdout


def reimport(project: Path):
    """What the editor does when files are added through the Add... menu."""
    subprocess.run([str(G.ENGINE), "--path", str(project), "--headless", "--import"], capture_output=True, timeout=300)


def start(requires=(), mode="autonomous", files=None):
    p = fresh_project()
    for r in requires:
        apply_silently(p, r)
    for path, src in (files or {}).items():
        dest = p / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(src, Path):
            shutil.copy(src, dest)
        else:
            dest.write_text(src)
    if files and any(isinstance(s, Path) for s in files.values()):
        reimport(p)
    tool(p, "build_rust", {})
    return Trace(p), system_for(p, mode)


def pick(x):
    return rng.choice(x) if isinstance(x, (list, tuple)) else x


# ====================================================================== kickoff

OPENERS = ["Let's plan my game together", "I want to make a game but I don't know where to start",
           "hi! I have an idea for a game", "Can you help me make my dream game?", "let's start a new game"]
Q1 = ["I'd love to! Tell me about the game you want to make: what's it about, and what should it feel like to play?",
      "Let's do it. First, the big picture: what's your game about, and how do you want it to feel when someone plays it?",
      "Exciting! Let's start with you: what's the game in your head? What happens in it, and what's the feeling you want players to have?"]
Q2 = ["What inspired it? Games, films, books, music, anything goes. And what kind of look are you imagining?",
      "Where does it come from? Any games, movies, books or music that inspired it? And what aesthetic are you going for?",
      "Two things that'll help me a lot: what inspired this idea, and what should it look like?"]
Q3 = ["Two more questions. Do you have the mechanics worked out, or do you want to discover them together as we go? "
      "And how do you want to work with me: do you want to learn how it's built as we go (learning mode), or should I do the heavy lifting while you direct (autonomous mode)?",
      "Last two: have you outlined the mechanics yet, or should we figure them out together? And would you like to learn alongside me as we build (learning mode), "
      "or have me handle the code while you make the decisions (autonomous mode)?"]

CONCEPTS = [
    dict(title="Lantern", short="a game about a kid lost in a foggy forest with a lantern",
         a1="It's about a kid who gets lost in a foggy forest at night. All they have is a lantern, and they have to find fireflies to keep it lit and find their way home. It should feel quiet and a little scary, but cozy too.",
         r1="Oh, I love that mix of scary and cozy, and the lantern as your lifeline is a strong idea.",
         a2="Limbo, Ori, and Totoro, mostly. And rainy days honestly. I want soft muted greens and greys with warm lantern light, and simple silhouettes.",
         r2="That palette tells me a lot: the warm light will really stand out against the grey-green fog.",
         a3="I know you walk around and collect fireflies, and the lantern light slowly shrinks. Not sure about the rest. And I want to learn! I've never coded before.",
         mode="learning",
         vision="# Lantern\n\n## The idea\nA kid gets lost in a foggy forest at night. All they have is a lantern, and they have to find fireflies to keep it lit and find their way home.\n\n## How it should feel\nQuiet and a little scary, but cozy too.\n\n## Inspirations\nLimbo, Ori, Totoro, rainy days.\n\n## Look\nSoft muted greens and greys, warm lantern light, simple silhouettes.\n\n## Mechanics\n- Walk around the forest\n- Collect fireflies\n- The lantern's light slowly shrinks (fireflies refill it?)\n- Still to discover: the rest!\n\n## How we work\nLearning mode: we build it together and I learn as we go.\n",
         next="A good first step could be the kid walking around in the dark with a little circle of light. Want to start there, or with something else?"),
    dict(title="Night Courier", short="a game where you deliver packages on a hoverboard in a neon city",
         a1="You're a courier on a hoverboard delivering packages across a neon city at night. It should feel fast and stylish, like you're the coolest person in the city.",
         r1="Fast and stylish is a great target. Speed games live or die by how good moving feels, so that'll be our north star.",
         a2="Synthwave music, Akira, and old arcade racers. Purples and pinks with cyan glow everywhere.",
         r2="Neon purple, pink and cyan with synthwave in your ears: I can already picture it.",
         a3="I have it mostly figured out: you dash, grind on rails, and every delivery has a time limit. I know a little code but I'd rather focus on the design, so you can do the heavy lifting.",
         mode="autonomous",
         vision="# Night Courier\n\n## The idea\nA courier on a hoverboard delivering packages across a neon city at night.\n\n## How it should feel\nFast and stylish, like you're the coolest person in the city.\n\n## Inspirations\nSynthwave music, Akira, old arcade racers.\n\n## Look\nPurples and pinks with cyan glow everywhere.\n\n## Mechanics\n- Dash\n- Grind on rails\n- Every delivery has a time limit\n\n## How we work\nAutonomous mode: Ember builds, I direct the design.\n",
         next="Since it's all about speed, I'd suggest starting with the hoverboard movement so we can tune how it feels. Sound good, or would you rather start somewhere else?"),
    dict(title="Big Fish", short="a game where you're a little fish that grows by eating smaller fish",
         a1="You're a tiny fish. You eat fish smaller than you to grow, and you have to avoid the bigger ones. Calm, but tense when a big fish shows up.",
         r1="That calm-then-tense rhythm is lovely, and it's really clear what the player is trying to do.",
         a2="Nature documentaries, and those old fish-eating flash games. Deep blues, bubbles, and a bright orange fish so you always know where you are.",
         r2="Making your fish bright orange against deep blue is a smart choice: players will never lose track of themselves.",
         a3="Yeah it's pretty clear: move, eat smaller fish, grow, avoid bigger fish. I want to learn how to make it.",
         mode="learning",
         vision="# Big Fish\n\n## The idea\nYou're a tiny fish. Eat fish smaller than you to grow, and avoid the bigger ones.\n\n## How it should feel\nCalm, but tense when a big fish shows up.\n\n## Inspirations\nNature documentaries, old fish-eating flash games.\n\n## Look\nDeep blues and bubbles; the player is a bright orange fish so you always know where you are.\n\n## Mechanics\n- Swim around\n- Eat smaller fish to grow\n- Avoid bigger fish\n\n## How we work\nLearning mode: we build it together and I learn as we go.\n",
         next="We could start with your orange fish swimming smoothly around the screen. Want to begin there?"),
    dict(title="Caravan", short="a cozy trading game with a camel caravan between ruined desert cities",
         a1="You lead a camel caravan between ruined cities in a desert, trading goods. Cozy strategy, nothing stressful.",
         r1="A cozy desert trading game is such a nice idea. Calm strategy has a lovely audience.",
         a2="Journey, Dune, and the history of the Silk Road. Sunset colors: purples and oranges, long shadows.",
         r2="Sunset purples and oranges with long shadows will make every trip feel like a journey.",
         a3="Honestly I haven't worked out the mechanics, let's figure it out together. And you can do the heavy lifting, I want to focus on the ideas.",
         mode="autonomous",
         vision="# Caravan\n\n## The idea\nLead a camel caravan between ruined desert cities, trading goods.\n\n## How it should feel\nCozy strategy, nothing stressful.\n\n## Inspirations\nJourney, Dune, the history of the Silk Road.\n\n## Look\nSunset colors: purples and oranges, long shadows.\n\n## Mechanics\nTo discover together.\n\n## How we work\nAutonomous mode: Ember builds, I focus on the ideas.\n",
         next="Since we're discovering the mechanics together, here's a question to start with: when you arrive in a city, what do you picture yourself doing first?"),
    dict(title="Candy Hop", short="a candy platformer for my little sister",
         a1="I want to make a game for my little sister! A candy world where you run and jump around. Bright and silly, and you can't die, she gets upset when she loses.",
         r1="Making a game for your sister is the best reason to make a game. No dying is a great call for her.",
         a2="Kirby, and her drawings honestly, she draws candy castles all the time. Pastel pinks and candy colors.",
         r2="Using her drawings as inspiration is wonderful. Maybe she'll recognise her candy castles in it!",
         a3="Run, jump, collect lollipops. Maybe bouncy gumdrops instead of enemies. I want to learn so I can keep making stuff for her.",
         mode="learning",
         vision="# Candy Hop\n\n## The idea\nA game for my little sister: a candy world where you run and jump around.\n\n## How it should feel\nBright and silly. You can't die.\n\n## Inspirations\nKirby, and my sister's drawings of candy castles.\n\n## Look\nPastel pinks and candy colors.\n\n## Mechanics\n- Run and jump\n- Collect lollipops\n- Bouncy gumdrops instead of enemies (maybe)\n- No dying\n\n## How we work\nLearning mode: I want to learn so I can keep making things for her.\n",
         next="Want to start with running and jumping? Once that feels fun, the lollipops are a great second step."),
    dict(title="Nightfall Keep", short="a gothic game about exploring a vampire's castle at night",
         a1="You explore a vampire's castle at night. Dark and challenging, every room should feel dangerous.",
         r1="Dangerous rooms in a vampire's castle: that's a strong mood to build around.",
         a2="Castlevania, Bloodborne and gothic novels like Dracula. Black silhouettes, deep purples, and red light in the windows.",
         r2="Black silhouettes with red windows against purple is a striking look.",
         a3="I have a whole doc for it: whip attack, platforming, and a boss at the end of each wing. You do the heavy lifting.",
         mode="autonomous",
         vision="# Nightfall Keep\n\n## The idea\nExplore a vampire's castle at night.\n\n## How it should feel\nDark and challenging. Every room should feel dangerous.\n\n## Inspirations\nCastlevania, Bloodborne, gothic novels like Dracula.\n\n## Look\nBlack silhouettes, deep purples, red light in the windows.\n\n## Mechanics\n- Whip attack\n- Platforming\n- A boss at the end of each wing\n(I have a full design doc too.)\n\n## How we work\nAutonomous mode: Ember builds, I direct.\n",
         next="Since you have a design doc, feel free to paste the parts you want me to follow and I'll add them here. Where should we start: platforming, or the whip?"),
    dict(title="Summit", short="a quiet climbing game about a tiny climber on a snowy mountain",
         a1="A tiny climber trying to reach the top of a snowy mountain. It's about not giving up. Quiet and kind of meditative.",
         r1="A game about not giving up, told through one tiny climber: that's beautiful.",
         a2="Real climbing videos, and Celeste. Blues and whites, with the climber in a red jacket so they pop.",
         r2="A red jacket against blue and white snow will look great and keeps the climber easy to spot.",
         a3="Climbing, a stamina meter, and wind gusts that push you. I want to learn as we go.",
         mode="learning",
         vision="# Summit\n\n## The idea\nA tiny climber trying to reach the top of a snowy mountain. It's about not giving up.\n\n## How it should feel\nQuiet and meditative.\n\n## Inspirations\nReal climbing videos, Celeste.\n\n## Look\nBlues and whites; the climber wears a red jacket so they pop.\n\n## Mechanics\n- Climbing\n- A stamina meter\n- Wind gusts that push you\n\n## How we work\nLearning mode: we build together and I learn as we go.\n",
         next="Want to start with the climber moving around, and add stamina once that feels right?"),
    dict(title="Fixer", short="a puzzle game about a little robot repairing a space station",
         a1="You're a little repair robot on a space station where everything keeps breaking. Puzzly, a bit funny.",
         r1="A little repair robot surrounded by things breaking: that's funny before anyone even presses a button.",
         a2="The Martian and Portal's humor. Dark space, grey metal, and red alert lights.",
         r2="Red alert lights on grey metal will make every breakdown feel urgent (and funny).",
         a3="Not sure about the puzzles yet. Let's work them out together. And you can do the coding.",
         mode="autonomous",
         vision="# Fixer\n\n## The idea\nYou're a little repair robot on a space station where everything keeps breaking.\n\n## How it should feel\nPuzzly, and a bit funny.\n\n## Inspirations\nThe Martian, Portal's humor.\n\n## Look\nDark space, grey metal, red alert lights.\n\n## Mechanics\nTo work out together (puzzles about fixing things).\n\n## How we work\nAutonomous mode: Ember codes, I direct.\n",
         next="To start finding the puzzles: what's the first thing you imagine breaking on the station?"),
    dict(title="Sprout", short="a cozy farming game where the vegetables talk",
         a1="A cozy farming game where the vegetables talk to you. You grow them and get to know them.",
         r1="Talking vegetables! That's charming, and getting to know them gives the farming a heart.",
         a2="Stardew Valley, Animal Crossing, and my grandma's garden. Bright greens and a red barn.",
         r2="Your grandma's garden is a lovely inspiration, it'll give the game warmth.",
         a3="Plant, water, harvest, and the vegetables talk. I'd love to learn how to make it myself.",
         mode="learning",
         vision="# Sprout\n\n## The idea\nA cozy farming game where the vegetables talk. You grow them and get to know them.\n\n## How it should feel\nCozy and warm.\n\n## Inspirations\nStardew Valley, Animal Crossing, my grandma's garden.\n\n## Look\nBright greens and a red barn.\n\n## Mechanics\n- Plant\n- Water\n- Harvest\n- The vegetables talk to you\n\n## How we work\nLearning mode: I want to learn to make it myself.\n",
         next="A nice first step could be walking around the farm. Or would you rather start with a single talking vegetable?"),
    dict(title="Minion Mayhem", short="a comedy game where you're the minion of a clumsy villain",
         a1="You're the overworked minion of a clumsy evil villain in a volcano lair, trying to keep everything from falling apart. Pure chaos comedy.",
         r1="Playing the overworked minion is a hilarious angle.",
         a2="Despicable Me and Overcooked. Reds and oranges, lava everywhere.",
         r2="Lava reds and oranges, perfect for a lair where everything's on fire.",
         a3="Lots of little tasks with a timer, things catch fire, the boss yells. You build, I'll come up with the jokes.",
         mode="autonomous",
         vision="# Minion Mayhem\n\n## The idea\nYou're the overworked minion of a clumsy villain in a volcano lair, trying to keep everything from falling apart.\n\n## How it should feel\nPure chaos comedy.\n\n## Inspirations\nDespicable Me, Overcooked.\n\n## Look\nReds and oranges, lava everywhere.\n\n## Mechanics\n- Lots of little tasks with a timer\n- Things catch fire\n- The boss yells at you\n\n## How we work\nAutonomous mode: Ember builds, I write the jokes.\n",
         next="What's the very first task you imagine the boss yelling about? We could build that one first."),
    dict(title="Hue", short="a game where you paint a grey world back into color",
         a1="The world has lost its color and you paint it back by moving through it. Hopeful and relaxing.",
         r1="Painting the color back into the world: that's such a hopeful idea.",
         a2="Okami and de Blob. It starts all grey, and colors spread wherever you go.",
         r2="Grey turning into color wherever you go will make progress something you can see.",
         a3="Moving paints the ground, that's all I know so far. I want to learn while we make it.",
         mode="learning",
         vision="# Hue\n\n## The idea\nThe world has lost its color, and you paint it back by moving through it.\n\n## How it should feel\nHopeful and relaxing.\n\n## Inspirations\nOkami, de Blob.\n\n## Look\nIt starts all grey; colors spread wherever you go.\n\n## Mechanics\n- Moving paints the ground\n- More to discover together\n\n## How we work\nLearning mode: I want to learn while we make it.\n",
         next="A great first step: a player who leaves a trail of color behind them. Want to start there?"),
    dict(title="Dad's Stories", short="a game about my dad's stories",
         a1="It's about the stories my dad used to tell me. You walk through places from his stories and find little memories.",
         r1="That's a really meaningful game to make. Thank you for sharing it with me.",
         a2="What Remains of Edith Finch and To the Moon. Soft, like watercolor.",
         r2="Soft watercolor fits memories perfectly.",
         a3="Walking and finding memories, I don't know much more yet. Can you do the heavy lifting? I want to focus on the stories.",
         mode="autonomous",
         vision="# Dad's Stories\n\n## The idea\nWalk through places from the stories my dad used to tell me and find little memories.\n\n## How it should feel\nTender and personal.\n\n## Inspirations\nWhat Remains of Edith Finch, To the Moon.\n\n## Look\nSoft, like watercolor.\n\n## Mechanics\n- Walking\n- Finding memories\n- More to discover\n\n## How we work\nAutonomous mode: Ember builds, I focus on the stories.\n",
         next="Which of his stories would you like to start with? We could build that place first."),
]


def kickoff(c, short_opener):
    t, system = start()
    if short_opener:
        t.user(f"I want to make {c['short']}")
        t.say(f"{c['r1'].split('.')[0]}! Tell me more: what happens in it, and how should it feel to play?")
    else:
        t.user(pick(OPENERS))
        t.say(pick(Q1))
    t.user(c["a1"])
    t.say(f"{c['r1']} {pick(Q2)}")
    t.user(c["a2"])
    t.say(f"{c['r2']} {pick(Q3)}")
    t.user(c["a3"])
    calls = [("write_file", {"path": "design/vision.md", "content": c["vision"]})]
    if c["mode"] == "learning":
        calls.append(("set_mode", {"mode": "learning"}))
    t.step(pick(["Let me write that down so we both remember it.", "I'll put all of this in your design notes.", ""]), calls)
    mode_line = ("I've switched to learning mode, so I'll explain things as we go and you'll get to try parts yourself."
                 if c["mode"] == "learning" else "I'll handle the code; you make the calls on everything creative.")
    t.say(f"I wrote it all down in design/vision.md, in your words. It's yours: change it any time and I'll keep it in mind. "
          f"{mode_line}\n\n{c['next']}")
    return t, system


# ====================================================================== ask (vague -> question -> build)

ASK = [
    (["add an enemy", "can you add a bad guy?", "i want enemies"],
     "Sure! What should the enemy do? For example:\n- chase you\n- wander around on its own\n- stay put and turn to aim at you\nWhich fits your game?",
     ["enemy", "wander_npc", "turret_look"]),
    (["make it look cooler", "add some juice", "it looks kind of plain"],
     "Happy to! What kind of cool are you after? A few directions:\n- sparkles around the player\n- a slow day/night color cycle\n- a trail behind the player when they move\n- a flash of color when something happens\nOr something else you have in mind?",
     ["sparkles", "day_night", "trail", "color_flash"]),
    (["add a hud", "i want some ui on screen", "add a ui"],
     "Good idea. What should it show? For example a score, a health bar, or a timer?",
     ["score_hud", "health_bar", "stopwatch"]),
    (["add a power-up", "give the player a special move", "add an ability"],
     "Fun! What kind of ability? A quick dash, a double jump, or a button that makes you faster?",
     ["dash", "double_jump", "speed_button"]),
    (["add something dangerous", "add an obstacle", "make it harder"],
     "Sure! What kind of danger fits your game? Spikes that send you back to the start, solid rocks in the way, or mud that slows you down?",
     ["spikes", "rock_field", "mud_zone"]),
    (["add a companion", "can the player have a friend?"],
     "Aw, I like that. Should the friend follow you around like a pet, or circle around you like a little moon?",
     ["pet_follow", "orbiting_moon"]),
    (["make the camera better", "the camera feels off"],
     "What would you like the camera to do: follow the player smoothly, or let you zoom in and out?",
     ["camera_follow", "camera_zoom"]),
    (["add a way to finish the level", "how do you win?"],
     "Good question, and it's your call! Should there be a second level you move on to, or a locked door you need to find a key for?",
     ["next_level", "key_door"]),
]


def ask(vague, question, feature):
    f = FEATURES[feature]
    t, system = start(f.get("requires", []))
    t.user(vague)
    t.say(question)
    run_feature(t, feature, rng.choice(f["prompts"]), False)
    return t, system


# ====================================================================== concept art

CONCEPT = {
    "foggy_forest.png": ("Lantern", "a lone figure holding a warm orange light in a misty forest of tall, sharp pine silhouettes. The palette is almost all muted grey-greens, so that little warm light really stands out. It feels quiet and mysterious, and the figure is tiny next to the trees, which makes the forest feel huge",
                         "Yes!! that's exactly it. the kid and the lantern.",
                         "Muted grey-green fog and dark pine silhouettes; the only warm color is the lantern's orange light. The kid is tiny next to the trees so the forest feels huge. Quiet and mysterious.",
                         "That warm-light-in-the-fog contrast is the heart of it. Want me to set the game's background to that misty grey-green to start?"),
    "neon_city.png": ("Night Courier", "a night skyline of tall dark towers dotted with pink, cyan and yellow lights, a big magenta moon, and a purple sky. There's a small dark shape in the middle with a cyan light on it. I think it might be a chimney or a figure, I'm not sure. It feels calm and neon-lit",
                      "the dark thing in the middle is my courier! the cyan line is their visor",
                      "Dark towers with pink, cyan and yellow window lights, a big magenta moon, purple sky. The courier is a dark silhouette with a glowing cyan visor. Calm and neon-lit.",
                      "A cyan visor glowing on a silhouette is a great, readable character design. Want me to use those neon colors for the first test level?"),
    "underwater.png": ("Big Fish", "an underwater scene: deep blue water full of bubbles, green seaweed swaying up from a sandy floor, and one bright orange fish in the middle. It's calm, and the orange fish really pops against the blue",
                       "yep that's my fish",
                       "Deep blue water, lots of bubbles, green seaweed on a sandy floor. The player fish is bright orange so it always pops. Calm.",
                       "The orange-on-blue contrast is perfect for keeping the player easy to spot. Want me to make the background that deep blue?"),
    "desert_ruins.png": ("Caravan", "a desert at sunset: a big golden sun low on the horizon, a sky fading from deep purple to orange, rolling brown dunes, and the dark ruins of old columns. It feels calm and a little lonely, like the end of a long trip",
                         "the columns are ruins of an old city, you got the vibe right",
                         "Sunset desert: big golden sun on the horizon, purple-to-orange sky, rolling brown dunes, dark ruined columns of an old city. Calm, a little lonely, like the end of a long trip.",
                         "That lonely-but-calm feeling is a lovely target for a cozy trading game. Should the first scene be a caravan arriving at those ruins?"),
    "candy_land.png": ("Candy Hop", "a bright candy world: pastel pink hills, a mint-green ground, fluffy white clouds, and a row of giant lollipops in purple, pink and yellow. It's flat and simple, and it feels cheerful and playful",
                       "my sister drew the lollipops! yes",
                       "Pastel pink hills, mint-green ground, fluffy white clouds, giant lollipops in purple, pink and yellow (my sister drew them!). Flat and simple, cheerful and playful.",
                       "Using your sister's lollipops in the game would be so special. Want to add the lollipops as things to collect?"),
    "gothic_castle.png": ("Nightfall Keep", "a black castle silhouette with sharp spires against a purple night sky, a big pale moon, a few small windows glowing red, and bats flying past. It feels eerie and spooky",
                          "perfect, that's the keep",
                          "Black castle silhouette with sharp spires, purple night sky, big pale moon, small windows glowing red, bats. Eerie.",
                          "Those red windows are a great detail: they could even mark rooms you haven't explored yet. Want me to set up the night-sky colors first?"),
    "snowy_peaks.png": ("Summit", "two blue mountains with snowy tops, a pale blue sky with falling snow, and a tiny red figure standing on the snow at the bottom. The figure is tiny compared to the mountains, which makes the climb feel huge. It's calm and wintry",
                        "that's my climber in the red jacket :)",
                        "Blue mountains with snowy peaks, pale sky, falling snow. The climber is a tiny figure in a red jacket, dwarfed by the mountains so the climb feels huge. Calm and wintry.",
                        "The tiny red climber against the huge mountain says everything about the game. Want gently falling snow as a first touch?"),
    "space_station.png": ("Fixer", "deep space with stars, a big blue planet on the left, and a station in the middle: a grey ring with a cross-shaped frame, two dark blue solar panels, and a red light at its center. It feels calm and exploratory",
                          "the red light is the alarm that's always going off lol. but yeah",
                          "Deep space with stars, a big blue planet, the station: grey ring, cross-shaped frame, dark blue solar panels, a red alarm light at the center that's always going off. Calm, with a funny undercurrent of constant emergency.",
                          "An alarm that's always going off is a great running joke. Want me to start with a blinking red alarm light?"),
    "cozy_farm.png": ("Sprout", "a sunny farm: a green hill, a red barn with a white door, a pale yellow sun, and rows of brown soil with little red plants growing in them. Flat and simple, calm and pastoral",
                      "those are tomatoes, they'll be the first talking veggies",
                      "A sunny green hill, a red barn with a white door, a pale yellow sun, rows of brown soil with red tomato plants (the first talking veggies). Flat, simple, calm and pastoral.",
                      "Tomatoes as the first talking vegetables, love it. Want to start with walking around the farm?"),
    "volcano_lair.png": ("Minion Mayhem", "a dark volcano with lava pouring down the middle and a glowing crater spitting sparks, against a deep red sky. It's flat and bold, and it feels urgent and fiery",
                         "it's supposed to be funny too, not just scary. but the colors are right",
                         "A dark volcano, lava pouring down the middle, a glowing crater spitting sparks, deep red sky. Flat and bold. The colors are urgent and fiery, but the tone is FUNNY, not scary.",
                         "Got it: fiery colors, silly tone. Bright lava with goofy characters could be a fun contrast. What's the first silly thing that should happen in the lair?"),
}
CONCEPT_ASKS = ["I added concept art: design/concept/{f}. Take a look and tell me what you see.",
                "here's some concept art for the vibe: design/concept/{f}",
                "I drew this, can you look at it? design/concept/{f}"]


def concept(fname, with_vision):
    title, seen, reply, notes, nxt = CONCEPT[fname]
    files = {f"design/concept/{fname}": ART / fname}
    c = next(c for c in CONCEPTS if c["title"] == title)
    if with_vision:
        files["design/vision.md"] = c["vision"]
    t, system = start(files=files)
    t.user(pick(CONCEPT_ASKS).format(f=fname))
    t.step("", [("look_at_image", {"path": f"design/concept/{fname}"})])
    t.say(f"I see {seen}. Did I get that right? Anything I missed or misread?")
    t.user(reply)
    if with_vision:
        t.step("Thanks! I'll add that to your design notes.", [("edit_file", {"path": "design/vision.md", "old_text": "## Look\n",
                                                                                   "new_text": f"## Look\nFrom design/concept/{fname}: {notes}\n\n"})])
    else:
        t.step("Thanks! I'll start your design notes with that.", [("write_file", {"path": "design/vision.md",
                                                                                        "content": f"# {title}\n\n## Look and feel\nFrom design/concept/{fname}: {notes}\n"})])
    t.say(f"Saved in design/vision.md, so I'll keep it in mind whenever we build. {nxt}")
    return t, system


# ====================================================================== assets

SOUND_SCENE = """[gd_scene format=3]

[ext_resource type="Texture2D" path="res://icon.svg" id="1_icon"]
[ext_resource type="AudioStream" path="res://assets/audio/{f}" id="2_sound"]

[node name="Main" type="Node2D"]

[node name="Player" type="Player" parent="."]
position = Vector2(576, 324)

[node name="Sprite2D" type="Sprite2D" parent="Player"]
texture = ExtResource("1_icon")

[node name="{node}" type="AudioStreamPlayer" parent="Player"]
stream = ExtResource("2_sound")
"""
MUSIC_SCENE = """[gd_scene format=3]

[ext_resource type="Texture2D" path="res://icon.svg" id="1_icon"]
[ext_resource type="AudioStream" path="res://assets/audio/theme.ogg" id="2_music"]

[node name="Main" type="Node2D"]

[node name="Player" type="Player" parent="."]
position = Vector2(576, 324)

[node name="Sprite2D" type="Sprite2D" parent="Player"]
texture = ExtResource("1_icon")

[node name="Music" type="AudioStreamPlayer" parent="."]
stream = ExtResource("2_music")
autoplay = true
"""
HERO_SCENE = """[gd_scene format=3]

[ext_resource type="Texture2D" path="res://assets/art/hero.png" id="1_hero"]

[node name="Main" type="Node2D"]

[node name="Player" type="Player" parent="."]
position = Vector2(576, 324)

[node name="Sprite2D" type="Sprite2D" parent="Player"]
texture_filter = 1
scale = Vector2(3, 3)
texture = ExtResource("1_hero")
"""


def asset_sound(fname, node):
    t, system = start(files={f"assets/audio/{fname}": SAMPLES / fname})
    t.user(pick([f"I added these to the project: assets/audio/{fname}. Take a look at what they are.",
                 f"I made a sound effect: assets/audio/{fname}"]))
    t.step("", [("asset_info", {"path": f"assets/audio/{fname}"})])
    t.say(f"Nice, it's a short sound effect, well under a second. When should it play? For example when you press a key, or when something happens in the game?")
    t.user(pick(["when I press space", "play it when i press space", "space bar"]))
    t.step("", [("read_file", {"path": "main.tscn"}), ("read_file", {"path": "rust/src/player.rs"})])
    t.step(pick(["I'll give the player a sound player with your sound in it.", "First, a sound player node that holds your sound."]),
           [("write_file", {"path": "main.tscn", "content": SOUND_SCENE.format(f=fname, node=node)})])
    t.step("Now the player plays it when you press space.", [
        ("edit_file", {"path": "rust/src/player.rs", "old_text": "use godot::classes::{INode2D, Input, Node2D};",
                       "new_text": "use godot::classes::{AudioStreamPlayer, INode2D, Input, Node2D};"}),
        ("edit_file", {"path": "rust/src/player.rs", "old_text": "        self.base_mut().set_position(position + step);\n    }",
                       "new_text": f"        self.base_mut().set_position(position + step);\n\n        if input.is_action_just_pressed(\"ui_accept\") {{\n"
                                   f"            let mut sound = self.base().get_node_as::<AudioStreamPlayer>(\"{node}\");\n            sound.play();\n        }}\n    }}"})])
    (b,) = t.step(pick(G.BUILD_LINES) or "Building.", [("build_rust", {})])
    assert b["ok"], b["content"]
    (r,) = t.step("Quick playtest.", [("run_game", {"seconds": 2})])
    assert r["ok"], r["content"]
    t.say(f"Done! Press Play (F5) and hit space to hear your sound. Since you made it yourself, want me to note it in design/assets.md so your work is credited?")
    return t, system


def asset_music():
    t, system = start(files={"assets/audio/theme.ogg": SAMPLES / "theme.ogg"})
    t.user(pick(["I added these to the project: assets/audio/theme.ogg. Take a look at what they are.", "my friend made a song for the game! assets/audio/theme.ogg"]))
    t.step("", [("asset_info", {"path": "assets/audio/theme.ogg"})])
    t.say("It's a 24 second piece of music. Should it play in the background the whole time, or only somewhere specific, like a title screen?")
    t.user(pick(["the whole time", "background music for the whole game"]))
    t.step("", [("read_file", {"path": "main.tscn"})])
    t.step("I'll add a music player to the main scene that starts by itself.", [("write_file", {"path": "main.tscn", "content": MUSIC_SCENE})])
    (r,) = t.step("Quick playtest.", [("run_game", {"seconds": 2})])
    assert r["ok"], r["content"]
    t.step("And I'll credit it in your asset list.", [("write_file", {"path": "design/assets.md", "content":
        "# Assets\n\n| Asset | Made by | Status |\n|---|---|---|\n| assets/audio/theme.ogg (background music) | a friend (add their name!) | final |\n"})])
    t.say("Done! Press Play (F5) and the music starts right away. To make it loop, select theme.ogg in the FileSystem dock, open the Import tab, tick Loop and click Reimport. "
          "I put it in design/assets.md; tell me your friend's name and I'll credit them properly.")
    return t, system


def asset_sprite():
    t, system = start(files={"assets/art/hero.png": SAMPLES / "hero.png"})
    t.user(pick(["I added these to the project: assets/art/hero.png. Take a look at what they are.", "i drew my character! assets/art/hero.png"]))
    t.step("", [("asset_info", {"path": "assets/art/hero.png"}), ("look_at_image", {"path": "assets/art/hero.png"})])
    t.say("It's a 32x32 pixel-art character. Is this your player? If so, I'll swap it in for the placeholder icon.")
    t.user(pick(["yes that's the player", "yep, use it for the player"]))
    t.step("", [("read_file", {"path": "main.tscn"})])
    t.step("I'll use it for the player's sprite. Pixel art this small gets blurry when scaled, so I'll keep it crisp and make it 3x bigger.",
           [("write_file", {"path": "main.tscn", "content": HERO_SCENE})])
    (r,) = t.step("Quick playtest.", [("run_game", {"seconds": 2})])
    assert r["ok"], r["content"]
    t.step("I'll note it in your asset list too.", [("write_file", {"path": "design/assets.md", "content":
        "# Assets\n\n| Asset | Made by | Status |\n|---|---|---|\n| assets/art/hero.png (player) | you | final |\n"})])
    t.say("Your character is in the game! Press Play (F5) to see them move. If they look too big or small, change the Sprite2D's Scale in the Inspector.")
    return t, system


# ====================================================================== learning mode

SPEED_EXPLAIN = ("Let's do it together! Speed lives in `rust/src/player.rs`. Near the top, `speed: f32` declares it: a number with a decimal point (`f32`). "
                 "Its starting value is set in `init`:\n\n```rust\nSelf {{ speed: 300.0, base }}\n```\n\n"
                 "Change `300.0` to something bigger, like `{n}.0`. Keep the `.0`: Rust wants a decimal number there. Save with Ctrl+S and tell me when you're done!")


def learn_speed(n, mistake):
    t, system = start(mode="learning")
    t.user(pick(["make my player faster", "how do i make the player go faster?", "the player is too slow"]))
    t.step("", [("read_file", {"path": "rust/src/player.rs"})])
    t.say(SPEED_EXPLAIN.format(n=n))
    path = t.project / "rust/src/player.rs"
    src = path.read_text()
    if mistake:
        path.write_text(src.replace("speed: 300.0", f"speed: {n}"))
        t.user(pick(["done", "ok I changed it", "did it!"]))
        t.step("Let me check it.", [("read_file", {"path": "rust/src/player.rs"})])
        (b,) = t.step("", [("build_rust", {})])
        assert not b["ok"]
        t.say(f"So close! The compiler is saying `{n}` is a whole number, but `speed` is an `f32`, a number with a decimal point. "
              "Rust won't guess for you. Look at your number in `init`: what could you add to make it a decimal?")
        path.write_text(src.replace("speed: 300.0", f"speed: {n}.0"))
        t.user(pick([f"oh, {n}.0?", "added .0", "fixed it"]))
    else:
        path.write_text(src.replace("speed: 300.0", f"speed: {n}.0"))
        t.user(pick(["done", "ok I changed it", "did it!", "saved"]))
    t.step("Let me check it builds.", [("read_file", {"path": "rust/src/player.rs"}), ("build_rust", {})])
    t.say(f"It builds, nice work! Your player now moves at {n} pixels per second. Press Play (F5) and try it.\n\n"
          "Bonus: because `speed` has `#[export]` above it, you can also select the Player in the scene and change Speed in the Inspector, no code needed. Try a few values and find the one that feels right.")
    return t, system


def learn_print(msg):
    t, system = start(mode="learning")
    t.user(pick(["how do I make the game say something when it starts?", "teach me how to print a message"]))
    t.step("", [("read_file", {"path": "rust/src/player.rs"})])
    t.say("Great first thing to learn! In `rust/src/player.rs`, the `ready` function runs once when the player appears in the game. Inside it:\n\n"
          "```rust\ngodot_print!(\"Hello from Rust! Use the arrow keys to move.\");\n```\n\n"
          "`godot_print!` writes a message to the Output panel at the bottom of the editor. Change the text between the quotes to anything you like, save, and tell me when you're done.")
    path = t.project / "rust/src/player.rs"
    path.write_text(path.read_text().replace("Hello from Rust! Use the arrow keys to move.", msg))
    t.user(pick(["done!", "ok changed it"]))
    t.step("Let's see it run.", [("run_game", {"seconds": 1})])
    t.say(f"It printed \"{msg}\". You just changed what your game does with code! Press Play (F5) and look at the Output panel to see it yourself.\n\n"
          "Try next: add a second `godot_print!(...)` line under the first one. Each line runs in order, top to bottom.")
    return t, system


SPIN_LINE = "        self.base_mut().rotate(2.0 * delta as f32);\n"


def learn_spin(mistake):
    t, system = start(mode="learning")
    t.user(pick(["teach me how to make the player spin", "I want the player to spin, can you show me how?"]))
    t.step("", [("read_file", {"path": "rust/src/player.rs"})])
    t.say("Let's do it! The `process` function in `rust/src/player.rs` runs every frame, many times a second. `delta` is how much time passed since the last frame, "
          "so multiplying by it keeps things smooth on fast and slow computers alike.\n\nAdd this line at the end of `process`, just before its closing `}`:\n\n"
          "```rust\nself.base_mut().rotate(2.0 * delta as f32);\n```\n\n`rotate` turns the node a little, `2.0` is the speed, and `as f32` converts `delta` into the kind of number `rotate` wants. Tell me when it's in!")
    path = t.project / "rust/src/player.rs"
    src = path.read_text()
    anchor = "        self.base_mut().set_position(position + step);\n"
    if mistake:
        path.write_text(src.replace(anchor, anchor + "        self.base_mut().rotate(2.0 * delta);\n"))
        t.user(pick(["done", "added it"]))
        (b,) = t.step("Let me build it.", [("build_rust", {})])
        assert not b["ok"]
        t.say("Almost! The compiler says `rotate` wants an `f32`, but `delta` is an `f64` (a bigger kind of decimal number). "
              "Look at the line I showed you again and compare it with yours. One small piece is missing at the end.")
        path.write_text(src.replace(anchor, anchor + SPIN_LINE))
        t.user(pick(["oh, as f32", "fixed!"]))
    else:
        path.write_text(src.replace(anchor, anchor + SPIN_LINE))
        t.user(pick(["done", "added it", "ok it's in"]))
    t.step("Building and playtesting.", [("build_rust", {}), ("run_game", {"seconds": 1})])
    t.say("It works! Press Play (F5) and your player spins as it moves. Try changing `2.0` to `10.0` for a crazy spin, or `-2.0` to spin the other way.")
    return t, system


# ====================================================================== modes

def mode_switch(to):
    t, system = start(mode="autonomous" if to == "learning" else "learning")
    if to == "learning":
        t.user(pick(["can you teach me how to do this stuff myself instead?", "I want to learn how to code this", "switch to learning mode"]))
        t.step("", [("set_mode", {"mode": "learning"})])
        t.say("Learning mode is on! From now on I'll explain what we're doing, and you'll get to write some of it yourself. I'll check your work and help when you're stuck. "
              "What would you like to learn first? A gentle start is making the player faster: it's a one-number change.")
    else:
        t.user(pick(["honestly just build things for me for now", "can you just do it for me?", "switch to autonomous mode"]))
        t.step("", [("set_mode", {"mode": "autonomous"})])
        t.say("No problem, I'll do the heavy lifting. I'll still check with you on creative choices, since it's your game. Switch back any time if you want to learn a part. What should we build?")
    return t, system


# ====================================================================== draw on request

SVGS = {
    "coin": ('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">\n  <circle cx="32" cy="32" r="28" fill="#f4c430" stroke="#b8860b" stroke-width="4"/>\n'
             '  <circle cx="32" cy="32" r="18" fill="none" stroke="#fff3b0" stroke-width="3"/>\n  <rect x="29" y="20" width="6" height="24" rx="3" fill="#b8860b"/>\n</svg>\n',
             ["can you draw a coin for me?", "make me a coin sprite"], "a gold coin with a shiny inner ring"),
    "heart": ('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">\n  <path d="M32 56 L8 32 A13 13 0 0 1 32 14 A13 13 0 0 1 56 32 Z" fill="#e63946" stroke="#9d0208" stroke-width="3"/>\n'
              '  <circle cx="22" cy="26" r="4" fill="#ffb3b9"/>\n</svg>\n',
              ["draw a heart for the health", "can you make a heart icon?"], "a red heart with a little highlight"),
    "star": ('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">\n  <polygon points="32,4 40,24 62,24 44,38 51,60 32,46 13,60 20,38 2,24 24,24" fill="#ffd166" stroke="#e09f3e" stroke-width="3"/>\n</svg>\n',
             ["draw me a star pickup", "can you make a star sprite?"], "a yellow star with an orange outline"),
}


def draw(name):
    svg, asks, desc = SVGS[name]
    t, system = start()
    t.user(pick(asks))
    t.step(f"Sure! Here's {desc}.", [("write_file", {"path": f"assets/art/{name}.svg", "content": svg})])
    t.step("I'll note it in your asset list.", [("write_file", {"path": "design/assets.md", "content":
        f"# Assets\n\n| Asset | Made by | Status |\n|---|---|---|\n| assets/art/{name}.svg | Ember | simple first version |\n"})])
    t.say(f"Done: assets/art/{name}.svg. It's a vector image, so it stays sharp at any size. Want me to use it somewhere in the game? "
          "And if you ever draw your own version, add it with Add... > Game Assets and I'll swap it in.")
    return t, system


# ====================================================================== needs art

def needs_art(requires):
    t, system = start(requires)
    t.user(pick(["what still needs real art?", "which things in my game are placeholders?"]))
    (ls, scene) = t.step("", [("list_files", {}), ("read_file", {"path": "main.tscn"})])
    names = [n for n, _ in G.scene_nodes(scene["content"]) if n != "Main"]
    rows = "\n".join(f"| {n} | Godot icon / plain shape | needs art |" for n in names if not n.endswith(("Shape2D", "Layer", "Label", "Timer")))
    t.step("I'll make a list you can work through.", [("write_file", {"path": "design/assets.md", "content":
        f"# Assets\n\n| Thing | Uses now | Status |\n|---|---|---|\n{rows}\n"})])
    t.say("Everything visible is still a placeholder, so the whole look is yours to create. I listed each thing in design/assets.md. "
          "When you have art (yours, or from an artist you work with), add it with Add... > Game Assets and I'll wire it in. Which one would you like to start with?")
    return t, system


# ====================================================================== journal

JOURNAL = [
    ("Boss ideas", "boss-ideas.md",
     "# Boss ideas\n\n## The Hollow Mother\nA giant moth in the Hollow. Her wings blow out your lantern, so the fight is about relighting it from fireflies she scatters.\nPhase 2: she flies above the trees and you only see her shadow.\n\n## The Lamplighter\nAn old man who wants your lantern. Talks to you during the fight. Should feel sad, not scary.\n",
     ["let's work on my first boss", "can we start on the moth boss from my journal?"],
     "moth boss",
     "Your journal has the Hollow Mother: a giant moth whose wings blow out your lantern, so the fight is about relighting it from the fireflies she scatters, and in phase 2 she flies above the trees and you only see her shadow. Great idea, it turns your lantern into the core of the fight!\n\nBefore we build: when your lantern goes out, what should happen? Is the screen almost dark until you grab a firefly, or does the player take damage over time while it's out?"),
    ("World outline", "world-outline.md",
     "# World outline\n\nThree islands connected by rope bridges.\n- Saltrock: fishing village, start of the game\n- The Spire: a wizard tower that's half underwater\n- Ember Isle: a volcano, final area\nBoats unlock fast travel after you fix the harbor.\n",
     ["where should we start building my world?", "let's build the first area"],
     "islands world",
     "From your world outline: three islands joined by rope bridges, starting in Saltrock, the fishing village, then The Spire (a half-sunken wizard tower) and Ember Isle (the volcano at the end).\n\nSaltrock makes sense as the first area since it's where the game starts. What should a player do in their first minute there: talk to someone, explore the docks, or get pulled straight into trouble?"),
]


def journal_ref(title, fname, text, asks, query, reply):
    t, system = start(files={f"design/journal/{fname}": text})
    t.user(pick(asks))
    (res,) = t.step("Let me check your journal first.", [("journal", {"action": "search", "query": query})])
    assert "Nothing" not in res["content"], res["content"]
    t.step("", [("read_file", {"path": f"design/journal/{fname}"})])
    t.say(reply)
    return t, system


SAVE_IDEAS = [
    ("oh I just had an idea: what if the fireflies are actually the souls of other lost kids, and you find out at the end",
     "Ooh, that's a powerful twist. It would make every firefly you collect feel different on a second playthrough. Want me to save it in your Concept Journal so we don't lose it?",
     "Story twist: fireflies are lost kids",
     "What if the fireflies are actually the souls of other lost kids? The player finds out at the end, so every firefly collected means something different on a second playthrough."),
    ("random thought: enemies should get scared of you once you're strong enough instead of always attacking",
     "I love that. It makes getting stronger something you SEE in the world, not just in numbers. Should I put it in your journal?",
     "Enemies fear a strong player",
     "Once the player is strong enough, weaker enemies get scared and run away instead of attacking. Getting stronger shows in the world, not just in numbers."),
    ("what if the shop moves to a different island every day",
     "That's a fun little routine to plan around: players would learn the schedule. Want me to save that idea in your journal?",
     "Traveling shop",
     "The shop moves to a different island every day. Players learn its schedule and plan their trips around it."),
]


def journal_save(said, offer, title, text):
    t, system = start()
    t.user(said)
    t.say(offer)
    t.user(pick(["yes!", "yeah save it", "sure"]))
    t.step("", [("journal", {"action": "add", "title": title, "text": text})])
    t.say(f"Saved as \"{title}\" in your Concept Journal. It'll be there whenever we need it. Want to keep brainstorming, or build something?")
    return t, system


# ====================================================================== game paths

PATH_STARTS = [
    (["I want to make something like Skyrim but I have no idea where to start", "how would I even make an elder scrolls type game?"], "open-world-rpg",
     "Open-world RPGs are huge, so the trick is building the systems small and letting them combine. We start with one town, a dungeon and a few characters, and make them feel alive. There's a 10-step path for exactly this, from walking around to quests, crime and saving the world.\n\nStep 1 is the most important one: what makes YOUR world worth wandering? Is it a strange place, a strong situation (like Fallout's world after the bombs), or a big fantasy you get to live out?"),
    (["I want to make a souls-like", "how do i make a game like dark souls"], "souls-like",
     "Souls-likes are about hard but fair challenges and a world you learn by heart. There's an 8-step path for it, from a weighty dodge roll to stamina, enemies that telegraph their attacks, bonfires and your first boss.\n\nFirst question, because \"Souls-like\" means different things to different people: which part do you want most? The tough-but-fair combat, the interconnected world, the cryptic story, or the bosses?"),
    (["teach me how to make a platformer", "i want to make a platformer like celeste"], "platformer",
     "Platformers live and die by how the jump feels, so that's where we start. There's an 8-step path, from running and jumping to forgiving controls, your special move and a level that teaches without words.\n\nFirst, the feel: precise and tough like Celeste, floaty and relaxed like Kirby, or all about momentum like Sonic? And what's your character's special move?"),
    (["I want to make a cozy farming game", "how do i start a stardew type game?"], "cozy-farming",
     "Cozy games are about comfort and routine, and they're a lovely thing to make. There's an 8-step path, from walking your farm to growing crops, neighbors who remember you, and seasons.\n\nLet's start with the heart of it: where is your little world, and why does the player come there? Who's one neighbor they'll meet?"),
]


def path_start(asks, pid, reply):
    t, system = start()
    t.user(pick(asks))
    t.step("", [("game_path", {}), ("game_path", {"path": pid})])
    t.say(reply)
    return t, system


def path_continue(pid, step, title):
    t, system = start(files={"design/path.md": f"# Game Path\nPath: {pid}\nCurrent step: {step - 1}\n"})
    t.user(pick(["what's next?", "ok that works! what do we do next", "next step please"]))
    (res,) = t.step("", [("game_path", {"path": pid, "step": step})])
    q = res["content"].split("**Design question:**")[1].split("\n")[0].strip()
    t.say(f"Next up, step {step}: {title}. {q}")
    return t, system


# ====================================================================== references

REFERENCES = [
    ("I want the combat to feel like Dark Souls", "Dark Souls",
     "Dark Souls is a great reference! Its combat is loved for a few different things: deliberate, committed attacks, a stamina bar that punishes mashing, enemies that telegraph every swing so deaths feel fair, and a dodge roll you have to time. Which of those matters most for your game? It's fine if the answer is \"all of them\", but knowing the top one tells me where to start."),
    ("make the movement feel like Celeste", "coyote time",
     "Celeste's movement feels so good because of a few invisible rules: you can still jump a moment after leaving a ledge, a jump pressed just before landing still counts, holding jump makes you go higher, and there's a little hang time at the top. Do you want that tight, precise feel for your whole game, or something a bit floatier?"),
    ("I want my world to feel alive like Skyrim", "NPC daily schedules",
     "A big part of that feeling is that people in Skyrim go about their day without you: the blacksmith works the forge, everyone heads to the inn at night. Simple daily routines, overlapping, make a town feel lived in. Is that the part you mean, or more the freedom to go anywhere and do anything?"),
    ("something cozy like stardew valley", "Stardew Valley",
     "Stardew's coziness comes from a gentle daily rhythm (farm, chat, sleep), no harsh failure, neighbors who remember you, and a place that slowly becomes yours. Which of those do you want to start with?"),
]


def reference(ask, query, reply):
    t, system = start()
    t.user(ask)
    t.step("", [("game_design", {"query": query})])
    t.say(reply)
    return t, system


# ====================================================================== studio (3D modeler)

def rmodel(verts, faces, colors, mirror=False):
    """A Studio .rmodel file (the format the editor's 3D modeler saves)."""
    return json.dumps({"format": "rustic-model", "version": 1, "mirror_x": mirror,
                       "vertices": [[round(x, 4) for x in v] for v in verts],
                       "faces": [{"v": f, "color": c} for f, c in zip(faces, colors)]}, indent=1)


def box(w, h, d, x0=None):
    """A box standing on the ground (y from 0 to h). With x0 set, it spans x0..w instead of -w/2..w/2."""
    a, b = (-w / 2, w / 2) if x0 is None else (x0, w)
    v = [(a, 0, -d / 2), (b, 0, -d / 2), (b, h, -d / 2), (a, h, -d / 2), (a, 0, d / 2), (b, 0, d / 2), (b, h, d / 2), (a, h, d / 2)]
    f = [[4, 5, 6, 7], [1, 0, 3, 2], [5, 1, 2, 6], [0, 4, 7, 3], [7, 6, 2, 3], [0, 1, 5, 4]]
    return v, f


def tree_model():
    import math
    n = 6
    v = [(math.cos(2 * math.pi * i / n) * 0.15, 0, -math.sin(2 * math.pi * i / n) * 0.15) for i in range(n)]
    v += [(math.cos(2 * math.pi * i / n) * 0.15, 0.8, -math.sin(2 * math.pi * i / n) * 0.15) for i in range(n)]
    v += [(math.cos(2 * math.pi * i / n) * 0.7, 0.8, -math.sin(2 * math.pi * i / n) * 0.7) for i in range(n)]
    v.append((0, 2.4, 0))
    f = [list(range(n - 1, -1, -1))] + [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    c = ["#6b4423"] * (1 + n)
    f += [list(range(3 * n - 1, 2 * n - 1, -1))] + [[2 * n + i, 2 * n + (i + 1) % n, 3 * n] for i in range(n)]
    c += ["#2f6b3a"] * (1 + n)
    return rmodel(v, f, c)


CHEST = rmodel(*box(1.0, 0.6, 0.6), ["#8b5a2b"] * 6)
TREE = tree_model()
_hv, _hf = box(0.35, 1.1, 0.4, x0=0.0)
HALF_BODY = rmodel(_hv, _hf[:3] + _hf[4:], ["#3a6ea5"] * 5, mirror=True)  # no face on the mirror seam, like the Studio
HOUSE = rmodel(*box(2.0, 1.6, 2.0), ["#c9a27e"] * 6)
ROCK = rmodel(*box(1.0, 0.7, 0.8), ["#7d7d78"] * 6)
import studio_cases as SC  # noqa: E402
STUDIO_QA_ALL = None  # filled below, after STUDIO_QA

STUDIO_CTX = "in the Studio's 3D modeler: res://assets/models/{name}.rmodel ({nv} vertices, {nf} faces, {nc} colors{mir}), {sel}, picture from last save: design/studio/{name}.png"


def render_preview(src, out_path, size=(640, 480)):
    """A flat-shaded picture of an .rmodel, like the Studio's preview (design/studio/<name>.png)."""
    import math
    from PIL import Image, ImageDraw
    m = json.loads(src)
    vs = [tuple(v) for v in m["vertices"]]
    faces = [(f["v"], f.get("color", "#b0b0b0")) for f in m["faces"]]
    if m.get("mirror_x"):
        n = len(vs)
        vs = vs + [(-x, y, z) for x, y, z in vs]
        faces = faces + [([i + n for i in reversed(f)], c) for f, c in faces]
    yaw, pitch = 0.6, 0.45
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    lo = [min(v[k] for v in vs) for k in range(3)]; hi = [max(v[k] for v in vs) for k in range(3)]
    c = [(lo[k] + hi[k]) / 2 for k in range(3)]
    def view(v):
        x, y, z = v[0] - c[0], v[1] - c[1], v[2] - c[2]
        x, z = x * cy - z * sy, x * sy + z * cy
        y, z = y * cp - z * sp, y * sp + z * cp
        return x, y, z
    pv = [view(v) for v in vs]
    ext = max(max(abs(p[0]) for p in pv), max(abs(p[1]) for p in pv)) or 1
    scale = min(size) * 0.4 / ext
    img = Image.new("RGB", size, (58, 62, 70)); d = ImageDraw.Draw(img)
    light = (0.4, 0.8, 0.45)
    def normal(f):
        a, b, cc = [pv[i] for i in f[:3]]
        u = [b[k] - a[k] for k in range(3)]; w = [cc[k] - a[k] for k in range(3)]
        n = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
        l = math.sqrt(sum(x * x for x in n)) or 1
        return [x / l for x in n]
    for f, col in sorted(faces, key=lambda fc: sum(pv[i][2] for i in fc[0]) / len(fc[0])):
        n = normal(f)
        if n[2] < 0:
            continue  # facing away
        shade = 0.45 + 0.55 * max(0.0, sum(n[k] * light[k] for k in range(3)))
        rgb = tuple(int(int(col[1 + 2 * k:3 + 2 * k], 16) * shade) for k in range(3))
        d.polygon([(size[0] / 2 + pv[i][0] * scale, size[1] / 2 - pv[i][1] * scale) for i in f], fill=rgb, outline=(20, 20, 20))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


def studio_ctx(name, src, sel="1 faces selected"):
    d = json.loads(src)
    return STUDIO_CTX.format(name=name, nv=len(d["vertices"]), nf=len(d["faces"]), nc=len({f["color"] for f in d["faces"]}),
                             mir=", mirrored on X" if d["mirror_x"] else "", sel=sel)


STUDIO_QA = [
    ("chest", CHEST, "learning", ["How do I make the lid stick out a little on all sides?", "i want the lid to overhang the box a bit, how?"],
     "Nice, a chest is a great first model! Here's a classic trick for a lid that overhangs, three moves:\n\n"
     "1. In **Faces (2)**, click the top face and press **E** (extrude), then type **0** and press Enter. That makes a copy of the top edge right where it is.\n"
     "2. Press **S** (scale), type **1.1**, Enter. The copy grows 10% wider, and that ring becomes the lip that sticks out.\n"
     "3. Press **E** again and move the mouse up (or type **0.25**, Enter) to give the lid its height.\n\n"
     "Why it works: extrude always builds new sides between the old edge and the new one, so scaling right after extruding makes a ledge. You'll use this for roofs, tabletops and hat brims too. Want to try it and tell me how it looks?"),
    ("chest", CHEST, "learning", ["how would I add a lock on the front?", "can I make a little lock plate on the front"],
     "Inset is perfect for that. It makes a smaller face inside a face, so the lock gets a clean border:\n\n"
     "1. In **Faces (2)**, click the front face (the side facing you) and press **I** (inset). Move the mouse toward the face's center until it's lock-sized, or type **0.25** and Enter.\n"
     "2. Press **E** and pull it out just a little (type **0.05**, Enter) so the plate stands off the wood.\n"
     "3. Pick a gold or dark metal color in the color button and press **P** to paint it.\n\n"
     "Small, bright details like this are where the eye goes first, so one gold lock can make the whole chest feel like treasure. What color are you thinking for it?"),
    ("tree", TREE, "learning", ["my tree looks really boring and perfect", "the tree looks too much like a computer made it"],
     "It's a solid start: a 6-sided trunk with a cone of leaves, about 2.4 units tall. It looks \"computer-made\" because it's perfectly symmetrical, and nature never is. Let's rough it up:\n\n"
     "1. Press **1** for Vertices and click one corner on the edge of the leaves. Press **G** and nudge it out or up a little.\n"
     "2. Do that to 2 or 3 more corners, each by a different amount. Shift+click selects several at once.\n"
     "3. Select the top point and move it a bit off-center, so the tree leans slightly.\n\n"
     "Small, uneven changes read as \"natural\". Big regular ones read as \"designed\". Try it and orbit around with the middle mouse to check it from every side. Does it start to feel more alive?"),
    ("hero", HALF_BODY, "learning", ["how do I make an arm?", "ok I have the body, how do i add arms"],
     "You've got Mirror X on, so you only build the right arm and the left one appears by itself. Here's how:\n\n"
     "1. In **Faces (2)**, click the outer side face of the torso (the one pointing right, along X).\n"
     "2. Press **I** and inset it to about shoulder size (type **0.5**, Enter). That leaves a border so the arm doesn't take the whole side.\n"
     "3. Press **E** and pull out about **0.3** for the upper arm, then **E** again for the forearm. Two pieces give you an elbow.\n"
     "4. Move the top corners down a bit (Vertices, **G**, **Y**) if the shoulders look too square.\n\n"
     "Extrude-move-extrude is how all limbs are built, legs too. Want to do the legs next, or tweak the arm first?"),
    ("chest", CHEST, "learning", ["part of my model disappeared, I can see through it", "some faces look see-through from one side"],
     "That usually means one of two things, and both are quick fixes:\n\n"
     "- **The face is flipped** (it faces inward, so you only see it from inside). Select it in **Faces (2)** and click **Flip**.\n"
     "- **The face is missing** (deleted by accident). Press **1** for Vertices, Shift+click the 3 or 4 corners around the hole in order, going around the edge, then press **F** to fill it. Little numbers show the order you clicked.\n\n"
     "If it happened just now, **Ctrl+Z** undoes it too. Which one does it look like?"),
    ("tree", TREE, "learning", ["how do i make it smooth and round?", "can I make the leaves rounder"],
     "Low-poly models get their \"roundness\" from more sides, not smoothing. Here's how to round off the leaves:\n\n"
     "1. In **Faces (2)**, select the leaf faces (Shift+click, or drag a box around them) and press **D** to subdivide. Each face splits into smaller ones.\n"
     "2. Press **1** for Vertices, select the new corners around the middle of the leaves, and press **S** to push them out a little.\n\n"
     "Keep it chunky: a few big faces is what makes low-poly charming, and too many makes it look like a lumpy ball. The Studio doesn't do smooth shading yet. For a truly smooth look, Blender (free) can do it, and the .glb imports the same way. Want to keep the faceted style, or is smooth important for your game's look?"),
    ("chest", CHEST, "autonomous", ["how do I put this in my game?", "ok it's done, how do I use it in the game"],
     "Every time you save, the Studio also exports **assets/models/chest.glb**, and that's the file your game uses.\n\n"
     "- In the FileSystem panel, drag **chest.glb** into an open 3D scene.\n"
     "- If the player should bump into it, it needs a collision shape too (a box around it is plenty).\n\n"
     "Want me to set that up for you: the chest in your scene with a collision box?"),
    ("chest", CHEST, "learning", ["it looks huge next to my player", "how do I make the whole thing smaller"],
     "Right now it's 1.0 wide, 0.6 tall and 0.6 deep. 1 unit is about 1 meter, so it's actually a pretty big chest. To shrink the whole thing:\n\n"
     "1. Press **3** for Object mode (everything at once).\n"
     "2. Press **S**, type **0.7**, Enter. That's 70% of the current size.\n\n"
     "Typing a number while scaling or moving gives you exact sizes. Hold **Ctrl** instead to snap to steps. How tall is your player? I can help you pick a size that feels right next to them."),
    ("chest", CHEST, "autonomous", ["can you just make the model for me?", "just make the chest yourself please"],
     "I can't shape models in the Studio myself. That's yours, and honestly it's one of the most rewarding parts. But I can make it fast: a chest is about five moves (extrude, scale, inset, paint), and I'll tell you each key as you go. It takes about five minutes.\n\n"
     "If you'd rather keep building the game for now, I can put a plain gray box in its place and add it to \"Needs art\" for later. Which do you prefer?"),
    ("tree", TREE, "learning", ["what colors should i use?", "I don't know which colors to pick"],
     "Right now it's a brown trunk and a dark green top, a fine start. The best color choices come from the mood, so first: should your world feel bright and cheerful, calm and soft, or dark and moody?\n\n"
     "A few rules artists use:\n"
     "- **3 to 5 colors per model**, shared across all your models, so the world looks like one place.\n"
     "- **Light vs. dark matters more than hue.** If the leaves and trunk are close in brightness, the tree turns into a blob from far away.\n"
     "- **One accent color** for what should catch the eye (fruit, flowers).\n\n"
     "Once we pick a palette, I can save it in your Concept Journal so every model uses it. What mood are you going for?"),
]


def studio_qa(name, src, mode, asks, reply, look="no"):
    """look: "no" (asset_info is enough), "yes" (also look at the saved picture, once), "missing" (picture not there: answer anyway)."""
    t, system = start(files={f"assets/models/{name}.rmodel": src}, mode=mode)
    if look == "yes":
        render_preview(src, t.project / f"design/studio/{name}.png")
    t.user(pick(asks) + f"\n\n[Editor context: {studio_ctx(name, src)}]")
    calls = [("asset_info", {"path": f"assets/models/{name}.rmodel"})]
    if look != "no":
        calls.append(("look_at_image", {"path": f"design/studio/{name}.png"}))
    res = t.step("", calls)
    assert "Studio 3D model" in res[0]["content"], res[0]["content"]
    if look == "yes":
        assert res[1]["ok"], res[1]["content"]
    elif look == "missing":
        assert not res[1]["ok"], res[1]["content"]
        reply = "(There's no saved picture yet, so I went by the model's numbers.)\n\n" + reply
    t.say(reply)
    return t, system


def sfx_qa(name, src, mode, asks, reply):
    t, system = start(files={f"assets/sounds/{name}.rsfx": src}, mode=mode)
    t.user(pick(asks) + f"\n\n[Editor context: {SC.sfx_ctx(name, src)}]")
    (res,) = t.step("", [("asset_info", {"path": f"assets/sounds/{name}.rsfx"})])
    assert "Studio sound effect" in res["content"], res["content"]
    t.say(reply)
    return t, system


STUDIO_QA_ALL = STUDIO_QA + SC.more_model_qa(CHEST, TREE, HALF_BODY, HOUSE, ROCK)

ART_PATH_STARTS = [
    (["I want to learn how to make 3D models", "how do I start making my own 3d art?", "I've never modeled anything, where do I begin"], "art-low-poly-prop",
     "Love that you want to make your own! The best first model is something small your game actually needs, like a chest, a lantern or a crate. There's a 7-step Art Path for exactly that in the Studio tab, from finding references to extrude, inset, colors, and seeing it in your game.\n\n"
     "Step 1: which object does your game need, and what should it say about your world? Old and worn, magical, cozy?"),
    (["how do I make my own character model?", "I want to model my main character"], "art-low-poly-character",
     "Characters are the most rewarding thing to model, and you don't need detail, just good shapes. There's a 7-step Art Path: you model one half with Mirror X, and the other half builds itself.\n\n"
     "First, who are they? Give me three words for their personality. Round shapes feel friendly, square ones sturdy, pointy ones dangerous, so that tells us where to start."),
    (["how do I make trees and rocks for my world?", "I want to make my own environment art"], "art-low-poly-environment",
     "Worlds are built from kits: a few pieces (a couple of trees, some rocks, a wall) placed many times at different sizes and rotations. There's a 6-step Art Path for building one in the Studio.\n\n"
     "Step 1 is the look of the whole world, so every piece matches: what's the mood? Lush and bright, dry and harsh, cold and quiet?"),
    (["how do I make sound effects?", "I want to make my own sounds for the game", "can I make my own jump and coin sounds"], "art-sound-effects",
     "Yes, and it's one of the quickest ways to make a game feel alive! The Studio has a Sound Effects maker, and there's a 7-step Art Path for it: you start from a preset (Jump, Coin, Laser...) and learn to shape it with envelope, pitch and filters.\n\n"
     "Step 1: what does the player do most? List the actions that need a sound (jump, collect, get hit...), with one word for how each should feel."),
]


def art_path_start(asks, pid, reply):
    t, system = start(mode="learning")
    t.user(pick(asks))
    t.step("", [("game_path", {}), ("game_path", {"path": pid})])
    t.say(reply)
    return t, system


# ====================================================================== main

def jobs():
    for i, c in enumerate(CONCEPTS):
        for short in (False, True):
            yield "kickoff", (lambda c=c, s=short: kickoff(c, s))
    for vagues, q, feats in ASK:
        for feat in feats:
            yield "ask", (lambda v=rng.choice(vagues), q=q, f=feat: ask(v, q, f))
    for i, fname in enumerate(sorted(CONCEPT)):
        yield "concept", (lambda f=fname, w=(i % 2 == 0): concept(f, w))
    yield "assets", (lambda: asset_sound("jump.wav", "JumpSound"))
    yield "assets", (lambda: asset_sound("coin.wav", "CoinSound"))
    yield "assets", (lambda: asset_music())
    yield "assets", (lambda: asset_sprite())
    for n, m in ((500, False), (450, False), (600, True), (800, False)):
        yield "learning", (lambda n=n, m=m: learn_speed(n, m))
    for msg in ("Welcome to my game!", "Lantern is starting..."):
        yield "learning", (lambda msg=msg: learn_print(msg))
    for m in (False, True):
        yield "learning", (lambda m=m: learn_spin(m))
    for to in ("learning", "learning", "autonomous", "autonomous"):
        yield "modes", (lambda to=to: mode_switch(to))
    for name in SVGS:
        yield "draw", (lambda name=name: draw(name))
    for req in ([], ["enemy"], ["topdown_body", "coins"]):
        yield "needs_art", (lambda r=req: needs_art(r))
    for args in JOURNAL:
        for _ in range(2):
            yield "journal", (lambda a=args: journal_ref(*a))
    for args in SAVE_IDEAS:
        yield "journal", (lambda a=args: journal_save(*a))
    for asks, pid, reply in PATH_STARTS:
        yield "paths", (lambda a=asks, p=pid, r=reply: path_start(a, p, r))
    for pid, step, title in (("open-world-rpg", 3, "characters with daily routines"), ("open-world-rpg", 8, "consequences: crime and reputation"),
                             ("souls-like", 3, "stamina"), ("platformer", 3, "making the jump forgiving"), ("survival", 5, "crafting"),
                             ("roguelike", 2, "a generated level")):
        yield "paths", (lambda p=pid, st=step, ti=title: path_continue(p, st, ti))
    for args in REFERENCES:
        yield "reference", (lambda a=args: reference(*a))
    for i, args in enumerate(STUDIO_QA_ALL):
        yield "studio", (lambda a=args: studio_qa(*a, look="no"))
        yield "studio", (lambda a=args, m=("missing" if i % 10 == 3 else "yes"): studio_qa(*a, look=m))
    for args in SC.SFX_QA:
        for _ in range(2):
            yield "studio", (lambda a=args: sfx_qa(*a))
    for args in ART_PATH_STARTS:
        for _ in range(2):
            yield "studio", (lambda a=args: art_path_start(*a))


def main():
    out = Path(sys.argv[1])
    only = set(sys.argv[2:])
    G.WORK.mkdir(parents=True, exist_ok=True)
    G.make_base()
    ok = bad = 0
    with out.open("a") as fh:
        for kind, fn in jobs():
            if only and kind not in only:
                continue
            t0 = time.time()
            try:
                t, system = fn()
            except Exception as e:  # noqa: BLE001
                bad += 1
                print(f"FAIL {kind}: {str(e)[:400]}", flush=True)
                continue
            fh.write(json.dumps({"feature": f"collab:{kind}", "mistake": False, "system": system,
                                 "messages": t.messages, "tools": G.TOOLS}) + "\n")
            ok += 1
            print(f"ok   {kind:10s} {time.time() - t0:5.1f}s", flush=True)
    print(f"done: {ok} traces, {bad} failures")


if __name__ == "__main__":
    main()
