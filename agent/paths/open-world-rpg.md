# Open-world RPG (like The Elder Scrolls or Fallout)
The heart of this genre is freedom: a world that feels alive, where players become whoever they want through what they do. Big studios take years to make these games, so the trick is to build the SYSTEMS small and let them combine. Start with one town, one dungeon and a handful of characters, and make them feel real.

## Step 1: Brainstorm your world
**Design question:** What makes YOUR world worth wandering? Choose one strong hook: a strange place (Morrowind's alien mushroom forests), a strong situation (Fallout's world after the bombs), or a strong fantasy (Skyrim's "you are the dragon slayer").
**Why this genre needs it:** In an open world the player chooses what to do next, so the world itself has to pull them forward. Curiosity is the main goal.
**Build:** Nothing yet. Write it in the Concept Journal: the world's hook, three places worth visiting, three characters, and what the player is when the game starts (a prisoner? a stranger? a nobody?).
**You'll learn:** How to scope a big dream down to a small first version.
**Done when:** There's a journal entry with the hook, places and characters.

## Step 2: Walk around a small world
**Design question:** First person or top-down? How fast should walking feel: slow and immersive, or quick so travel isn't a chore?
**Why this genre needs it:** Players spend most of their time moving. If walking feels bad, nothing else matters.
**Build:** A player (CharacterBody2D for top-down, CharacterBody3D for 3D) moving around a small map with a few landmarks you can see from far away, like a tower or a big tree.
**You'll learn:** Nodes and scenes, `physics_process`, `move_and_slide`, input actions.
**Patterns:** "Camera that looks ahead".
**Try it yourself:** Change the walk speed and find the number that feels right for exploring.
**Done when:** You can walk from one landmark to another and it feels pleasant.

## Step 3: Characters with daily routines
**Design question:** Who lives here, and what do they do all day? A blacksmith at the forge in the morning, at the tavern at night?
**Why this genre needs it:** Oblivion's Radiant AI and Skyrim's NPC schedules make towns feel alive even when nothing scripted is happening. Routines are cheap to build and huge for immersion.
**Build:** An NPC that walks between two or three spots depending on an in-game clock (a Timer advancing the hour), using a simple list of (hour, place).
**You'll learn:** Structs and Vecs in Rust, timers, moving toward a target.
**Done when:** Watching the town for a few in-game hours, the NPC goes about their day.

## Step 4: Talking to people
**Design question:** How do conversations work in your game? Morrowind uses topics (click a keyword like "latest rumors"); Fallout and Skyrim use dialogue choices. Do people's moods toward you matter?
**Why this genre needs it:** Conversation is how players learn about the world and get quests. In The Elder Scrolls each NPC has a disposition (0-100) toward you that changes what they say and what they charge.
**Build:** Walk up to an NPC, press a key, and see a dialogue box with 2-3 choices. Store each NPC's lines in a simple data file so you can write dialogue without touching code.
**You'll learn:** UI with Control nodes and Labels, signals from Buttons, loading data from files.
**Done when:** You can have a short conversation with two different characters.

## Step 5: Skills that grow by doing
**Design question:** What can the player get better at, and how? Elder Scrolls games level the skills you actually use: run a lot and you run faster.
**Why this genre needs it:** "Become what you do" lets players build a character through play, the genre's core fantasy.
**Build:** A skills system: using an action adds progress, and progress needed grows with the level (Morrowind's rule: (1 + level) x a factor; major skills grow faster). Show a "Sneak increased to 6" message.
**You'll learn:** HashMaps, functions with parameters, signals to the UI.
**Patterns:** "Skills that grow by using them (Bethesda-style)".
**Done when:** Doing something many times raises its skill, and the player sees it happen.

## Step 6: Items, inventory and trading
**Design question:** What do players carry, and does weight matter? What do merchants want?
**Why this genre needs it:** Loot is a reward for exploring, and trading turns it into progress. In Morrowind prices depend on your Mercantile skill, Personality and Luck vs. the merchant's, plus how much they like you: social skills have real value.
**Build:** An inventory (a Vec of items with name, value and weight), picking items up from the world, and a merchant whose prices change with disposition.
**You'll learn:** Custom data types, Resources, simple formulas.
**Patterns:** "Weighted loot tables".
**Done when:** You can find an item, carry it, and sell it, and a friendly merchant pays more.

## Step 7: Quests with stages
**Design question:** What does one good quest in your world look like? Who gives it, what's the twist, how many ways can it end?
**Why this genre needs it:** Bethesda quests are a list of numbered stages (10: talked to the farmer, 20: found the cave, 30: chose to spare the bandit...). Anything in the world can check or advance a stage, which makes quests easy to branch.
**Build:** A quest log where each quest has a current stage number and a journal line for each stage. Advance stages from dialogue and from entering an area.
**You'll learn:** Enums and match, saving state, connecting systems with signals.
**Done when:** One quest can be started, progressed and finished two different ways.

## Step 8: Consequences: crime and reputation
**Design question:** What happens when the player does something wrong? Do people notice? Can they be forgiven?
**Why this genre needs it:** Freedom only matters if the world reacts. In Morrowind each crime adds a fixed bounty (trespassing, theft by item value, assault, murder) and lowers disposition, and only witnesses within an alarm radius react, so being unseen matters.
**Build:** Taking an item marked as owned while an NPC can see you adds a bounty; guards confront you; you can pay the fine.
**You'll learn:** Distance checks, ownership data, game state the whole world can read.
**Done when:** Stealing in front of someone has consequences, and stealing unseen doesn't.

## Step 9: A dungeon worth exploring
**Design question:** What's at the bottom of your first dungeon? How does it loop back so the player doesn't backtrack the whole way?
**Why this genre needs it:** Dungeons are where open-world games concentrate challenge and reward. Skyrim's dungeons almost always end with a shortcut back to the entrance.
**Build:** A small dungeon with enemies, a reward at the end and a one-way shortcut back to the start.
**Patterns:** "Readable, fair enemy AI (Doom-style)", "Interconnected world with shortcuts".
**Done when:** Finishing the dungeon feels like an achievement and the way out is quick.

## Step 10: Saving the world
**Design question:** What does the world need to remember? Dead NPCs, taken items, quest stages, the player's bounty?
**Why this genre needs it:** Persistence is what makes choices matter. Elder Scrolls games remember where you dropped every cheese wheel.
**Build:** Save and load the player's position, skills, inventory, quest stages and which NPCs are dead.
**Patterns:** "Saving and loading progress".
**Done when:** Quit, reload, and the world is exactly as you left it.
