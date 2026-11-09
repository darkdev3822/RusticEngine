# Survival and crafting (like Don't Starve, Minecraft, Subnautica, Valheim)
Survival games are about pressure and preparation: the world wears you down, and you push back by gathering, crafting and building. The best moments are when a plan comes together just in time.

## Step 1: Brainstorm the pressure
**Design question:** What threatens the player: hunger, cold, the night, monsters, oxygen? What's the feeling: cozy-tense (Valheim), lonely and eerie (Subnautica), harsh (Don't Starve)?
**Why this genre needs it:** The pressure defines every decision. Pick one or two to start.
**Build:** A journal entry: setting, the main pressure, and what the player's first night should feel like.
**Done when:** You know what kills the player and why they'd want to survive.

## Step 2: A world to roam
**Design question:** Handmade or randomly generated? How big?
**Build:** A player walking a map with resources scattered around (trees, rocks, berry bushes), placed randomly at the start.
**You'll learn:** Spawning many nodes from code, random numbers, PackedScenes.
**Done when:** Each new game scatters resources differently.

## Step 3: Needs that drain
**Design question:** How fast does hunger drain? What happens at zero: slow damage or instant death?
**Why this genre needs it:** Slowly draining needs create constant, low-level pressure that drives every choice.
**Build:** A hunger meter that drains over time and shows on screen; at zero, health slowly drops.
**You'll learn:** Timers, UI bars (ProgressBar), signals between systems.
**Done when:** Doing nothing eventually becomes dangerous.

## Step 4: Gathering
**Design question:** Instant pickup, or does gathering take time and tools?
**Build:** Walk up to a resource and hold a key to gather it into your inventory; it disappears or regrows later.
**You'll learn:** Inventories (HashMap of item to count), Area2D overlap checks.
**Done when:** You can gather wood, stone and food.

## Step 5: Crafting
**Design question:** What can be crafted first, and what does it unlock?
**Why this genre needs it:** Crafting is the progression ladder: each recipe opens new options (an axe gathers wood faster, a campfire survives the night).
**Build:** A recipe list (data, not code: recipe name, ingredients, result) and a crafting menu that checks your inventory.
**You'll learn:** Data-driven design, iterating over collections.
**Done when:** You can craft a tool and it makes gathering faster.

## Step 6: Day, night and danger
**Design question:** What changes at night? More monsters, darkness, cold?
**Why this genre needs it:** The day/night cycle is a natural rhythm: gather by day, survive by night.
**Build:** A day/night cycle (tint the world darker) and something dangerous that only appears at night.
**Patterns:** "Escalating enemy waves".
**Done when:** Nightfall makes you hurry home.

## Step 7: Building a base
**Design question:** What does a base protect you from? Walls, light, warmth?
**Build:** Place crafted structures on a grid (a wall, a campfire that keeps darkness away).
**You'll learn:** Snapping positions to a grid, placing scenes from code.
**Done when:** Your base makes the night survivable.

## Step 8: Saving your world
**Build:** Save and load the player, inventory, placed buildings and the time of day.
**Patterns:** "Saving and loading progress".
**Done when:** Your base is still there after quitting.
