# Art Path: your first pixel art sprite (in the Studio's Pixel Art painter)
Pixel art is the friendliest way into game art: a 16x16 character is 256 decisions, and you can see every one. You'll draw a character or item for your game, give it a small animation, and learn the ideas pixel artists use everywhere: silhouette, limited palettes, shading with hue shifts, clean lines and readable animation.

## Step 1: Decide what it is and how big
**Design question:** What does the player need to recognize at a glance: the hero, an enemy, a coin, a floor tile? How big is it on screen next to everything else?
**Why it matters:** Size sets the style. 16x16 is the classic size for characters, items and tiles: small enough to finish, big enough for personality. Everything in one game should share one pixel size so it looks like it belongs together.
**Build:** Open the Studio tab, choose Pixel Art, and pick New > 16x16 (or 16x24 for a taller character). Note the size in your Concept Journal.
**Done when:** You have an empty canvas of the size your game will use.

## Step 2: Silhouette first
**Design question:** If your sprite were a solid shadow, could you still tell what it is?
**Why it matters:** Players read shapes before details. A strong silhouette (big head, a hat, a weapon sticking out, a clear stance) is what makes a sprite recognizable at a glance.
**Build:** Pick one dark color. Block in the whole shape with Rectangle and Ellipse (hold Shift for filled), then fix the edges with Pencil. Turn on Mirror (M) for a front-facing character so both halves match.
**You'll learn:** Blocking in: big shapes first, details last. Every artist works this way.
**Try it yourself:** Turn Mirror off and break the symmetry a little (a sword in one hand, hair to one side) so it looks alive.
**Done when:** The solid shape alone reads as what it is in the Preview.

## Step 3: A limited palette
**Design question:** What is the mood: bright and cheerful, dark and grim, natural and calm?
**Why it matters:** Fewer colors make pixel art clearer and more consistent. Most great sprites use 4-8 colors. Each pixel stores a palette slot, so changing a slot recolors the sprite everywhere.
**Build:** Try the palette presets (Starter 16, Forest, Dungeon, Four Greens) and watch the sprite recolor. Change single colors with the color box. Fill areas with Fill (G).
**You'll learn:** Indexed color, the way classic consoles and pixel tools work, and why palette swaps make new enemies for free.
**Done when:** The sprite has its base colors: one per material (skin, cloth, metal, hair).

## Step 4: Light and shadow
**Design question:** Where is the light coming from? Pick one direction (top-left is the convention) and stick to it.
**Why it matters:** Shading gives volume. Two or three shades per material is enough: base, shadow, highlight.
**Build:** For each material, add a darker color on the side away from the light and a lighter one facing it. Make shadows a bit bluer or purpler and highlights a bit yellower instead of only darker or lighter (hue shifting).
**You'll learn:** Ramps and hue shifting, plus why "pillow shading" (darkening every edge evenly) looks flat.
**Done when:** It looks lit from one direction.

## Step 5: Outline and clean lines
**Design question:** Should the sprite pop against busy backgrounds (dark outline) or blend softly (colored or no outline)?
**Why it matters:** Outlines keep small sprites readable. Clean lines go in equal steps (1:1, 2:1, 3:1); uneven steps look jagged ("jaggies"). Also remove "orphan" pixels that stick out alone.
**Build:** Use Line (L) and Pencil to tidy the outline; zoom in with the scroll wheel and Grid on. Try a dark color for the outline, or a darker shade of each area's own color (selective outline).
**Done when:** The edges look intentional at actual size in the Preview.

## Step 6: A small animation
**Design question:** What does it do most: idle, walk, spin, flicker? Two to four frames are enough to start.
**Why it matters:** Even a 1-pixel bounce makes a sprite feel alive. Pixel art usually animates at 6-12 fps.
**Build:** Press Copy under Frames, change a few pixels (move the body down 1 pixel, swap the legs), turn on Onion Skin to see the previous frame, and press Play. Adjust fps.
**You'll learn:** Key poses, timing, and why you move only what changes.
**Done when:** The loop plays smoothly without popping.

## Step 7: Into the game
**Build:** Save. The Studio writes your .rpix and a .png next to it (all frames side by side). Ask Ember to put it in a scene: a Sprite2D with Hframes set to the frame count, animated by changing Frame. Set Project Settings > Rendering > Textures > Canvas Textures > Default Texture Filter to Nearest so pixels stay sharp.
**You'll learn:** Sprite sheets, the format every 2D engine uses.
**Done when:** Your sprite is moving in your game.
