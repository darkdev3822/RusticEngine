# Art Path: a low-poly character (in the Studio, with mirroring)
Characters are the hardest thing to model and the most rewarding: they carry your game's personality. Low-poly characters (think early PlayStation games, or modern indies like A Short Hike) rely on proportions, silhouette and color, not detail. You'll model one half and let Mirror X build the other.

## Step 1: Who are they, and what's their shape?
**Design question:** What's the character's personality in three words? Should they be round and friendly, tall and elegant, or blocky and tough?
**Why it matters:** Shape language: circles feel friendly, squares feel sturdy, triangles feel dangerous or dynamic. Players feel this before they see any detail.
**Build:** Add concept art or reference images (front and side views help most) and write the three words in your Concept Journal.
**Done when:** You can sketch (or describe) the character as a few simple shapes.

## Step 2: Proportions
**Design question:** How many "heads" tall? Realistic people are about 7-8 heads tall; cute, readable game characters are often 2-4.
**Why it matters:** Proportion is the biggest part of style. A big head and small body reads as cute and makes faces visible from a game camera.
**Build:** Start from a cube, turn on Mirror X, and scale it into the torso. Keep the character around 1.5-2 units tall, standing on the grid.
**You'll learn:** Why game characters are built standing at the origin, facing +Z (the direction Godot expects imported models to face).
**Done when:** The torso has the right size for your proportions.

## Step 3: Legs and arms by extruding
**Build:** In Faces mode, select the bottom face on the right half, inset it to make room, then extrude it down for a leg. Do the same from a side face for an arm. Mirror X builds the other side as you go.
**You'll learn:** Extrude chains (extrude, move, extrude again) to make limbs with joints; why limbs come out of insets.
**Try it yourself:** Extrude the arm in two steps so it has an elbow you could bend later.
**Done when:** The character stands with arms and legs, even if it looks blocky.

## Step 4: The head
**Design question:** What's the most important feature of their face or head? (Big eyes, a hat, ears, a helmet.)
**Build:** Extrude up from the top of the torso for a neck and head, or make the head a separate shape. Use subdivide (D) on a face where you need more detail, then move the new corners.
**Done when:** The head reads clearly at a small size on screen.

## Step 5: Silhouette and pose
**Why it matters:** Seen as a shadow, every character should be recognizable. Hats, hair, tools and asymmetry (on purpose) make silhouettes memorable.
**Build:** Orbit around and fix anything that looks flat. Taper arms and legs, widen shoulders or hips to match the personality.
**Done when:** Your three personality words are visible in the gray shape alone.

## Step 6: Colors
**Build:** Paint skin, clothes and one strong accent. Keep the palette to about 4-6 colors. Use a darker shade for the underside of clothes and shoes to fake shadow.
**Patterns:** Look at your Concept Journal palette so the character matches your world.
**Done when:** The character stands out from your game's background colors.

## Step 7: Into the game, and what's next
**Build:** Save into assets/models and use the .glb as the visual of a CharacterBody3D (ask Ember to set it up with a collision capsule).
**Good to know:** The Studio doesn't do skeletons or animation yet. You can animate simply in Godot by making arms and legs separate models and rotating them in code, or learn rigging in Blender (free) and import the .glb.
**Done when:** You're walking around your world as a character you made.
