# Platformer (like Super Mario Bros., Celeste, Hollow Knight's movement)
Platformers live and die by how the jump feels. Get the controls right first, then build levels that teach, test and twist one idea at a time.

## Step 1: Brainstorm the feel
**Design question:** Precise and tough (Celeste, Super Meat Boy), floaty and relaxed (Kirby), or momentum-based (Sonic)? What's your character's special move?
**Why this genre needs it:** The movement IS the game. Everything else is built to show it off.
**Build:** A journal entry: the feel, the special move, and the world your character runs through.
**Done when:** You can describe the jump in three words.

## Step 2: Run and jump
**Design question:** How fast does the character reach top speed? How much control do they have in the air?
**Why this genre needs it:** Acceleration and air control decide whether the game feels tight or slippery.
**Build:** A CharacterBody2D that runs with acceleration (not instant top speed) and jumps, on a floor of StaticBody2D blocks.
**You'll learn:** Velocity, gravity, `is_on_floor`, collision shapes.
**Done when:** Running and jumping across a few platforms feels responsive.

## Step 3: Make the jump forgiving
**Design question:** How forgiving should the jump be?
**Why this genre needs it:** Coyote time, jump buffering and variable height are invisible, but players notice immediately when they're missing.
**Build:** Add coyote time (jump just after leaving a ledge), a jump buffer (a press just before landing counts), variable height (release to cut the jump short) and a floaty apex.
**Patterns:** "Forgiving platformer jump (Celeste-style)".
**Try it yourself:** Set coyote time to 0, play, then set it back. Feel the difference.
**Done when:** Missed jumps feel like your fault, never the game's.

## Step 4: Hazards and respawning
**Design question:** What happens when you fail? Instant respawn (Celeste) or lives (Mario)?
**Why this genre needs it:** Fast respawns keep frustration low and encourage experimenting.
**Build:** Spikes or pits that send you back to the last checkpoint instantly.
**Done when:** Dying and retrying takes under a second.

## Step 5: Your special move
**Design question:** How does your special move (dash, wall jump, double jump, glide) change how levels can be built?
**Why this genre needs it:** One great move, explored deeply, beats ten shallow ones. Celeste builds its whole game around one dash.
**Build:** The special move, with clear feedback (a sound, a flash, a refill indicator).
**Patterns:** "Hit stop and screen shake (game juice)".
**Done when:** The move opens up a new way to get through a level.

## Step 6: A level that teaches
**Design question:** What's the one idea this level teaches, and how will the player figure it out without text?
**Why this genre needs it:** Great platformers teach by level design: introduce safely, test, twist, combine (Mario 1-1).
**Build:** One short level that introduces your special move in a safe spot, tests it with a small risk, and ends with a twist.
**Patterns:** "Teaching without tutorials (level 1-1 design)".
**Done when:** A friend can play it without you explaining anything.

## Step 7: Camera and juice
**Design question:** Should the camera lead the player, or stay fixed per room?
**Build:** A camera that looks ahead in the direction of movement, plus dust when landing and a little screen shake for big impacts.
**Patterns:** "Camera that looks ahead", "Hit stop and screen shake (game juice)".
**Done when:** The game feels alive even with placeholder art.

## Step 8: Collectibles and a goal
**Design question:** What does the player chase: a flag, a strawberry, a key? Is it required or optional?
**Why this genre needs it:** Optional collectibles in hard-to-reach spots give skilled players their own challenge without blocking anyone.
**Build:** A level exit plus one optional collectible hidden off the main path, and a counter on screen.
**Done when:** Finding the collectible feels like a secret you earned.
