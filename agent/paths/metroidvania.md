# Metroidvania (like Hollow Knight, Super Metroid, Ori, Castlevania: Symphony of the Night)
A metroidvania is one big connected world that opens up as you gain new abilities. The magic is the "aha!": that ledge you couldn't reach an hour ago is now a doorway. Exploration, not levels, is the structure.

## Step 1: Brainstorm the world and its locks
**Design question:** What is the world (a ruined kingdom, a derelict ship, a cursed castle)? What abilities will the player earn, and what does each one unlock (double jump → high ledges, dash → wide gaps, a key item → sealed doors)?
**Why this genre needs it:** Every ability is both a new verb and a key. Planning abilities and the obstacles they open together is the heart of the design.
**Build:** A journal entry: the setting, 3-4 abilities, and the kind of obstacle each one opens.
**Patterns:** "Interconnected world with shortcuts (Souls-style level design)".
**Done when:** You can say "you'll see a place you can't reach yet, and later you'll come back with X".

## Step 2: A player that feels great to move
**Design question:** Floaty and graceful (Ori) or weighty and precise (Hollow Knight)?
**Build:** A side-view CharacterBody2D with run, jump, coyote time and a jump buffer.
**You'll learn:** CharacterBody2D, gravity, input actions, `move_and_slide`.
**Patterns:** "Forgiving platformer jump (Celeste-style)".
**Done when:** Just running and jumping around an empty room is fun.

## Step 3: Rooms that connect
**Design question:** One seamless map, or separate rooms joined at the edges? How big is a room?
**Why this genre needs it:** The world is the level. Moving between rooms must be smooth so the world feels like one place.
**Build:** Two or three rooms as separate scenes. Walking off an edge loads the next room and places the player at the matching doorway.
**You'll learn:** PackedScene, changing scenes from code, keeping the player between rooms.
**Done when:** You can walk in a loop through three rooms and end up where you started.

## Step 4: The camera
**Build:** A camera that follows the player, stops at each room's edges and looks ahead a little in the direction you're moving.
**Patterns:** "Camera that looks ahead".
**Done when:** You never see outside a room, and you can see what you're running toward.

## Step 5: Your first ability gate
**Design question:** Which ability comes first, and where will the player first see a place they can't reach yet?
**Why this genre needs it:** Showing the locked path BEFORE giving the key is what makes the "aha!" happen later.
**Build:** A ledge too high to reach, a pickup somewhere else that grants double jump, and the save data remembering you have it.
**You'll learn:** Flags for unlocked abilities, checking them in movement code.
**Done when:** Getting the ability makes you think "I know exactly where to go now".

## Step 6: Enemies and combat
**Design question:** What does combat feel like: quick slashes, ranged shots, knockback?
**Build:** A melee attack with a short hitbox, an enemy that patrols and hurts on touch, knockback and invincibility frames when hit.
**Patterns:** "Invincibility frames (i-frames) after getting hit", "Hit stop and screen shake (game juice)", "Readable, fair enemy AI (Doom-style)".
**Done when:** Hitting an enemy feels punchy, and getting hit feels fair.

## Step 7: The map screen
**Design question:** Does the map fill in automatically, or does the player have to buy or find it (Hollow Knight)?
**Why this genre needs it:** In a big world, the map is how players plan where to go back to. Marking unexplored exits invites return trips.
**Build:** A map screen that shows the rooms you've visited and marks where you are.
**You'll learn:** Storing visited rooms, drawing simple shapes in a Control with `draw_rect`.
**Done when:** You can open the map and decide where to go next.

## Step 8: Save rooms and dying
**Design question:** What happens when you die? Back to the last bench, and lose something?
**Build:** Save points that restore health and save progress (room, abilities, visited map). Dying returns you to the last one.
**Patterns:** "Rest points / bonfires", "Saving and loading progress".
**Done when:** Quitting and coming back puts you at your last save with everything you've earned.

## Step 9: A boss guarding an ability
**Design question:** What does this boss test? Ideally the ability the player just learned, or the one they're about to get.
**Build:** A boss with two or three attacks it telegraphs before using, and a new ability as the reward.
**Patterns:** "Easy to learn, hard to master", "Teaching without tutorials (level 1-1 design)".
**Done when:** You lose a few times, learn its patterns, and winning feels earned.
