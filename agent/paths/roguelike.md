# Roguelike / roguelite (like Hades, The Binding of Isaac, Slay the Spire, Shattered Pixel Dungeon)
Runs are short, every run is different, and death is part of the loop. The fun comes from adapting to what the random dice give you and building combinations no two runs repeat.

## Step 1: Brainstorm the run
**Design question:** Real-time action (Hades, Isaac) or turn-based (Shattered Pixel Dungeon, Slay the Spire)? How long is a run? What carries over when you die?
**Build:** A journal entry: combat style, run length, and what makes your upgrades interesting together.
**Patterns:** "Death as progress (roguelite loop)".
**Done when:** You can describe one exciting "build" a player could stumble into.

## Step 2: A generated level
**Design question:** Rooms and corridors, connected arenas (Hades), or a grid of rooms (Isaac)?
**Why this genre needs it:** Generated levels make every run fresh, but they must stay fair and readable.
**Build:** Generate a layout of rooms connected by corridors on a grid (place random rectangles that don't overlap, then connect each to the next).
**You'll learn:** 2D grids (Vec of Vecs), random placement, TileMapLayer.
**Done when:** Every new run has a different layout you can walk through.

## Step 3: Turns or action
**Build:** Turn-based: everyone acts in order of time spent (moving costs 1, slow monsters spend more). Real-time: an attack with a short cooldown.
**Patterns:** "Turns by time spent (speed-based turn order)" or "Invincibility frames (i-frames) after getting hit".
**Done when:** Fighting one enemy works.

## Step 4: Enemies with personalities
**Design question:** What does each enemy force the player to do differently? (Run, close in, prioritize it, avoid an area.)
**Why this genre needs it:** Variety comes from enemies that combine: a slow tank plus a fast shooter is a new problem.
**Build:** Two enemy types with different behaviors, spawned in rooms.
**Patterns:** "Readable, fair enemy AI (Doom-style)".
**Done when:** Rooms with both enemies feel different from rooms with one.

## Step 5: Random rewards
**Design question:** What does the player find? Items, abilities, cards? How rare is the exciting stuff?
**Build:** A weighted loot table for rewards after each room, with rarer items being stronger.
**Patterns:** "Weighted loot tables".
**Done when:** Some rewards make you excited, most are solid.

## Step 6: Upgrades that combine
**Design question:** Which two upgrades are amazing together?
**Why this genre needs it:** Synergies are the genre's magic: players feel clever finding them.
**Build:** Three upgrades that change how attacks work and stack in interesting ways (e.g. "attacks pierce" + "attacks split").
**Done when:** Taking two specific upgrades together feels like a discovery.

## Step 7: Death and the next run
**Design question:** What does the player keep? Unlocks, currency, story?
**Build:** On death, show a summary, keep a meta-currency, and start a fresh run. Save the meta-progress.
**Patterns:** "Saving and loading progress".
**Done when:** You immediately want one more run.
