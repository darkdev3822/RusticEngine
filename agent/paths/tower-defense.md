# Tower defense (like Bloons TD, Kingdom Rush, Plants vs. Zombies, Defense Grid)
Tower defense is about planning under pressure: enemies follow a route, and you decide where to spend limited money on towers to stop them. The fun is watching your plan work, then finding its weak spot when a new enemy shows up.

## Step 1: Brainstorm the defense
**Design question:** What are you defending, and from what? Fixed path (Kingdom Rush), lanes (Plants vs. Zombies), or open ground where your towers shape the maze (Defense Grid)?
**Why this genre needs it:** The map style decides everything: how enemies move, where towers go and what "clever" means.
**Build:** A journal entry: the theme, the map style, and three towers with a one-line personality each.
**Patterns:** "Easy to learn, hard to master".
**Done when:** You can picture the first wave and the first tower you'd build.

## Step 2: Enemies that follow a path
**Build:** A Path2D across the screen and enemies that move along it with PathFollow2D. An enemy reaching the end costs a life.
**You'll learn:** Path2D, PathFollow2D, moving by `progress` each frame, signals when an enemy escapes.
**Done when:** A line of enemies walks the path, and lives drop when they get through.

## Step 3: Waves
**Design question:** How do waves grow: more enemies, faster enemies, tougher ones? Does the player start the next wave or is it on a timer?
**Build:** Wave data (how many of which enemy and how far apart) and a spawner that plays them in order.
**You'll learn:** Data-driven design, Timer, keeping a list of what's still alive.
**Patterns:** "Escalating enemy waves".
**Done when:** Each wave is a little harder than the last.

## Step 4: Placing towers
**Design question:** Where can towers go: anywhere, on a grid, or only on fixed spots (Kingdom Rush)?
**Build:** Click a valid spot to place a tower if you can afford it. Show where you're about to place it before you click.
**You'll learn:** Mouse input, converting screen to world positions, snapping to a grid.
**Done when:** You can place towers only where they're allowed.

## Step 5: Towers that shoot
**Design question:** Which enemy should a tower aim at: first in line, closest, strongest?
**Why this genre needs it:** Targeting rules are a hidden part of strategy. "First in line" is usually what players expect.
**Build:** A tower with a range (Area2D) that picks a target, fires on a cooldown and deals damage. Enemies die and drop money.
**You'll learn:** Area2D overlaps, choosing from a list, cooldowns.
**Done when:** A few well-placed towers can hold the first waves.

## Step 6: Towers that differ
**Design question:** What does each tower do that the others can't? (Splash vs. single-target, slowing, hitting flying enemies.)
**Why this genre needs it:** Strategy comes from combinations. A slowing tower plus a heavy hitter is stronger than either alone.
**Build:** Two more towers with real differences, and one enemy type that forces you to use them (armored, fast or flying).
**Done when:** A wave appears that your favorite tower can't handle alone.

## Step 7: Upgrades and selling
**Design question:** Upgrade paths with choices (Bloons) or simple levels? How much do you get back when selling?
**Build:** Click a tower to upgrade it (more range, damage or speed) or sell it for part of its cost.
**You'll learn:** UI panels that appear on click, changing a node's stats at runtime.
**Done when:** Choosing between a new tower and an upgrade is a real decision.

## Step 8: Win, lose and the next level
**Build:** Winning after the last wave and losing at zero lives, each with a screen. Save which levels are unlocked and the best result on each.
**Patterns:** "Saving and loading progress".
**Done when:** Beating a level makes you want to try the next one, or replay it for a better score.
