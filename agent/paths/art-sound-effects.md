# Art Path: your game's sound effects (in the Studio's Sound Effects maker)
Sound is half of how a game feels. A jump without a sound feels floaty; a coin without a "ding" feels like nothing happened. You'll make the core sounds for your game yourself, and learn the ideas every sound designer and synth uses: waves, envelopes, pitch and filters.

## Step 1: Make a sound list
**Design question:** What does the player do most? Every frequent action (jump, shoot, collect, get hit, click a menu) needs a sound. What should your game sound like overall: retro and beepy, soft and cozy, harsh and punchy?
**Why it matters:** Sounds are feedback: they tell players their action worked. A short list of 5-8 sounds that match each other beats 30 random ones.
**Build:** Write the list in your Concept Journal, with one word for the feel of each (bouncy jump, heavy hit, sparkly coin).
**Done when:** You know which sounds you need and how each should feel.

## Step 2: Start from a preset
**Build:** Open the Studio tab, choose Sound Effects, and press the preset closest to your first sound (Jump, Pickup/Coin, Laser/Shoot...). Press it several times: each press is a new random variation. Stop when one is close.
**You'll learn:** Presets are starting points, not answers. Professionals start from presets too, then shape them.
**Try it yourself:** Press Mutate a few times for small changes. Undo goes back.
**Done when:** You have a sound that's in the right family.

## Step 3: The envelope (volume over time)
**Design question:** Should it start instantly or swell in? End sharply or ring out?
**Why it matters:** Attack, sustain and decay shape how a sound feels more than its pitch. Short attack and decay = snappy and responsive (jumps, clicks). Long decay = big and heavy (explosions, bells).
**Build:** Change Attack, Sustain and Decay and watch the waveform's outline change. Add Punch for impact.
**You'll learn:** The ADSR envelope, used by every synthesizer and DAW (LMMS, Ardour, Vital, hardware synths).
**Done when:** The sound's length and shape match the action.

## Step 4: Pitch and slide
**Design question:** Up or down? Rising pitch feels positive (jumps, power-ups, collecting); falling pitch feels negative or forceful (getting hit, shooting, falling).
**Build:** Set Start pitch (higher = smaller and lighter, lower = bigger and heavier) and Slide. For a coin, try a Pitch jump of +5, +7 or +12 semitones.
**You'll learn:** Hz and octaves (double the Hz = one octave up), semitones (12 per octave), and why +7 and +12 jumps sound musical.
**Done when:** The sound moves in the direction the action does.

## Step 5: Wave and filters (the sound's color)
**Build:** Try each Wave on the same settings: Square (classic 8-bit), Saw (bright), Sine (soft), Triangle (round, retro), Noise (explosions, hits). Then use Low-pass to muffle, High-pass to thin it out.
**You'll learn:** Timbre: two sounds with the same pitch and envelope can feel completely different. A low-pass sweeping down makes explosions rumble away.
**Try it yourself:** Make one hit sound with Noise and one with Square. Which fits your game?
**Done when:** The sound fits your game's overall style.

## Step 6: A matching set
**Why it matters:** Sounds from one game should feel related: similar waves, similar loudness, no sound much louder than the rest.
**Build:** Make the rest of your list, reusing settings (Save, then tweak and save under a new name). Compare them back to back and even out the Volume.
**Done when:** Played one after another, they sound like one game.

## Step 7: Into the game
**Build:** Save each sound into assets/sounds; the Studio exports a .wav next to every .rsfx. Play it with an AudioStreamPlayer (AudioStreamPlayer2D or 3D for sounds that come from a place in the world), or ask Ember to hook it up to the action.
**You'll learn:** Small variations keep repeated sounds from getting tiring: a random pitch_scale between 0.9 and 1.1 on each play works wonders.
**Done when:** Your game plays your sounds when things happen.
