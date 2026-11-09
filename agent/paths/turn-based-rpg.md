# Turn-based RPG (like Final Fantasy, Pokémon, Dragon Quest, Persona, Undertale)
A turn-based RPG is about a journey and a party: exploring towns and dungeons, getting stronger, and battles where you think instead of reacting fast. Its heart is the story and characters; its spine is a battle system with clear choices.

## Step 1: Brainstorm the journey
**Design question:** Who is the party, and what's the journey? What makes your battles different (a twist like Undertale's mercy, Pokémon's type matchups, Persona's weakness rounds)?
**Why this genre needs it:** Many turn-based RPGs share the same menu. Your twist is what players will remember.
**Build:** A journal entry: the hero and two companions, where the journey goes, and your battle twist in one sentence.
**Done when:** You can describe one battle that could only happen in your game.

## Step 2: Walking the overworld
**Design question:** Top-down grid steps (Pokémon) or free movement?
**Build:** A top-down player walking a small town built from a TileMapLayer, with walls you can't walk through.
**You'll learn:** CharacterBody2D, TileMapLayer with collisions, a following camera.
**Done when:** You can explore a little town.

## Step 3: Talking to people
**Build:** NPCs you can face and press a key to talk to, showing dialogue in a text box one line at a time.
**You'll learn:** Detecting what's in front of you, a dialogue box UI, storing dialogue as data.
**Patterns:** "NPC daily schedules" (later, if you want towns that feel alive).
**Done when:** A townsperson tells you where to go next.

## Step 4: The battle screen
**Design question:** How does a battle start: random encounters, visible enemies, or story events only?
**Build:** Going into a separate battle scene with your party and enemies, a menu (Attack, Defend, Item, Run), and taking turns until one side falls.
**You'll learn:** Switching scenes and coming back, a state machine for whose turn it is, menus with Buttons.
**Done when:** You can win or lose a simple fight.

## Step 5: Turn order and speed
**Design question:** Strict turns by side (Pokémon) or by speed, so fast characters act more often (Final Fantasy X)?
**Why this genre needs it:** Turn order is strategy. Speed-based turns make slowing enemies or hasting allies meaningful.
**Build:** Order turns by a speed stat and show the upcoming order on screen.
**Patterns:** "Turns by time spent (speed-based turn order)".
**Done when:** A faster character visibly gets more turns.

## Step 6: Skills, weaknesses and your twist
**Design question:** What resources do skills cost (MP, cooldowns, a shared meter)? Which enemies are weak to what?
**Why this genre needs it:** "Attack every turn" is boring. Weaknesses and costs turn each battle into a small puzzle.
**Build:** Two skills per character with costs, enemies with a weakness, and your battle twist from Step 1.
**Done when:** Using the right skill at the right time clearly beats just attacking.

## Step 7: Growing stronger
**Design question:** Levels and experience, equipment, or skills that grow by use?
**Build:** Experience and level-ups that raise stats, and one piece of equipment you can find and wear.
**Patterns:** "Skills that grow by using them (Bethesda-style)" (an alternative to levels), "Weighted loot tables".
**Done when:** A fight that was hard becomes easy after some leveling.

## Step 8: A quest and an inn
**Build:** A quest with stages (talk to someone, beat a monster, come back) and an inn that heals the party and saves the game.
**Patterns:** "Quests as numbered stages (Bethesda-style)", "Rest points / bonfires", "Saving and loading progress".
**Done when:** You can finish one small story from start to end.
