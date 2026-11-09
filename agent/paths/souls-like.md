# Souls-like action RPG (like Dark Souls, Elden Ring, Hollow Knight)
This genre is about mastery through challenge: hard but fair fights, a world you learn by heart, and the thrill of finally beating what beat you twenty times. Fairness is everything. Every death should feel like the player's mistake, never the game's.

## Step 1: Brainstorm the challenge and the world
**Design question:** Which part of the Souls feeling do you want most: the punishing-but-fair combat, the interconnected world, the cryptic storytelling, or the bosses? And what's your setting's mood (decaying kingdom, cosmic horror, overgrown ruins)?
**Why this genre needs it:** "Souls-like" means different things to different people. Picking your core lets you spend effort where it counts.
**Build:** A journal entry: your setting, the one feeling you want most, and your first boss idea.
**Done when:** You can say in one sentence what makes YOUR game hard and why it's fair.

## Step 2: Deliberate movement and a dodge
**Design question:** How heavy should your character feel? Souls characters commit to actions: once you swing or roll, you can't cancel.
**Why this genre needs it:** Commitment is what makes timing matter. A dodge with invincibility frames rewards reading the enemy.
**Build:** A character that moves, plus a dodge roll: a short burst of speed with a brief window where they can't be hurt, and no way to cancel it.
**You'll learn:** State (an enum: Idle, Moving, Rolling), timers, input buffering.
**Patterns:** "Invincibility frames (i-frames) after getting hit".
**Done when:** Rolling feels weighty and you can time it through a hazard.

## Step 3: Stamina
**Design question:** How much can the player do before they need to back off?
**Why this genre needs it:** Stamina turns combat into a rhythm (attack, retreat, recover) and punishes mashing.
**Build:** A stamina bar: attacks and rolls cost stamina, regen starts after a short delay, and an action is allowed while stamina is above zero.
**Patterns:** "Stamina that gates actions (Souls-style)".
**Try it yourself:** Change the regen delay from 0.6 to 1.5 seconds and feel how much harsher it gets.
**Done when:** Spamming attacks leaves you exhausted and vulnerable.

## Step 4: An enemy that telegraphs
**Design question:** How does your first enemy warn the player before it attacks? A wind-up animation, a flash, a sound?
**Why this genre needs it:** Fair difficulty means every attack is readable. The wind-up (anticipation) is what the player learns to react to.
**Build:** An enemy with a clear cycle: notice the player, approach, wind up (visible for about half a second), strike, recover (an opening to punish).
**You'll learn:** State machines, timers, signals between enemy and player.
**Patterns:** "Readable, fair enemy AI (Doom-style)".
**Done when:** A new player can learn the enemy's pattern after a few deaths.

## Step 5: Rest points
**Design question:** How far apart are your rest points? What does resting cost (enemies come back)?
**Why this genre needs it:** The distance between rest points is the real difficulty dial, and the relief of finding one is iconic.
**Build:** A bonfire-like rest point: touching it heals you, sets your respawn and resets enemies.
**Patterns:** "Rest points / bonfires".
**Done when:** Dying sends you back to the last rest point with enemies restored.

## Step 6: Death with stakes (and a way back)
**Design question:** What do players lose when they die, and can they win it back?
**Why this genre needs it:** In Dark Souls you drop your souls where you died and can recover them if you reach that spot without dying again: tension and hope in one mechanic.
**Build:** A currency the player collects; on death it's dropped at the death spot as a pickup; dying again before reaching it loses it.
**Done when:** The run back to your lost currency feels tense.

## Step 7: A level that loops back
**Design question:** Where does your first area loop back to the rest point?
**Why this genre needs it:** One-way shortcuts reward pushing forward and make the world click together.
**Build:** An area with a locked gate that can only be opened from the far side, leading back to the rest point.
**Patterns:** "Interconnected world with shortcuts (Souls-style level design)".
**Done when:** Opening the shortcut gives that "oh, it's HERE!" moment.

## Step 8: The first boss
**Design question:** What's your boss's personality, and what does it teach or test?
**Why this genre needs it:** Bosses are exams on what the area taught. Great bosses have two or three readable attacks, a phase change at half health, and a fog gate so the arena feels like a duel.
**Build:** A boss with 2-3 telegraphed attacks, a health bar on screen, and a second phase.
**Patterns:** "Hit stop and screen shake (game juice)".
**Done when:** Beating it feels earned.
