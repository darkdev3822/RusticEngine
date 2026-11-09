# Cozy farming and life sim (like Stardew Valley, Animal Crossing)
Cozy games are about comfort and routine: small daily goals, gentle progress, and a place that slowly becomes yours. Nothing should feel punishing. Warmth comes from characters, seasons and the satisfaction of watching things grow.

## Step 1: Brainstorm the place and the people
**Design question:** Where is your little world, and why does the player come here? Who lives there? What makes it cozy for YOU?
**Build:** A journal entry: the place, three neighbors with one quirk each, and the player's reason for being there.
**Patterns:** "Cozy games: low pressure, high comfort".
**Done when:** You can picture a perfect day in your game.

## Step 2: Walking the farm
**Build:** A top-down player on a small farm with a house, a field area and a path to town.
**You'll learn:** CharacterBody2D, TileMapLayer for the ground, a following camera.
**Done when:** Walking around feels relaxed.

## Step 3: Days and energy
**Design question:** How long is a day? What limits how much you can do: energy, time, or nothing?
**Why this genre needs it:** The daily rhythm (wake, work, socialize, sleep) is the core loop. Limits make choices matter without stress.
**Build:** A clock that runs during the day, a bed that ends the day, and an energy meter that tools use up.
**Done when:** Each day has a beginning and an end.

## Step 4: Plant, water, grow
**Design question:** How long do crops take? What happens if you forget to water?
**Build:** Till a tile, plant a seed, water it, and watch it grow one stage per day, then harvest.
**You'll learn:** Per-tile data on a grid, saving growth stages, signals at the start of each day.
**Done when:** You can grow and harvest a crop over a few in-game days.

## Step 5: Selling and buying
**Build:** A shipping bin (sell overnight) and a shop to buy new seeds and upgrades.
**Done when:** Money turns into more interesting things to grow.

## Step 6: Neighbors who remember you
**Design question:** How do friendships grow? Gifts, chatting, helping?
**Why this genre needs it:** Relationships give cozy games their heart. Characters who remember what you did make the world feel like home.
**Build:** NPCs with a friendship value that rises when you talk daily or give liked gifts, unlocking new dialogue.
**Done when:** A neighbor says something new because you've become friends.

## Step 7: Seasons
**Design question:** What changes each season: crops, colors, events, music?
**Build:** Seasons that change after N days, with different crops and a recolored world.
**Done when:** The first change of season feels like an event.

## Step 8: Making it yours
**Build:** Furniture or decorations the player can place, and saving everything.
**Patterns:** "Saving and loading progress".
**Done when:** Your farm looks different from anyone else's.
