# Art Path: your first low-poly prop (a chest, lantern, crate or barrel, in the Studio)
Your first model should be something small that your game needs: a treasure chest, a lantern, a sign, a barrel. Low-poly means few faces and flat colors, and that's a style, not a shortcut: games like A Short Hike and Superhot look great this way. You'll learn the core moves every 3D artist uses, in Blender and anywhere else.

## Step 1: Pick the prop and find references
**Design question:** Which object does your game actually need? What should it say about your world (old and worn, magical, cozy, industrial)?
**Why it matters:** Artists never model from memory. Two or three reference pictures (photos, your concept art, games you like) make every decision easier.
**Build:** Put a few reference images in design/concept (Add... > Concept Art) and tell Ember what you like about each one.
**You'll learn:** Looking at shapes instead of details: what is this object made of? (A chest is a box with a curved lid. A lantern is a cylinder inside a frame.)
**Done when:** You can describe your prop as 2-4 simple shapes.

## Step 2: Find your way around
**Build:** Open the Studio tab. Orbit with the middle mouse button (or Alt + left drag), pan with Shift, zoom with the wheel. Press Home to frame the model. Click faces in Faces mode (2), corners in Vertices mode (1).
**You'll learn:** The three selection modes and the hint line at the bottom, which always tells you what you can do next.
**Try it yourself:** Select the top face of the cube and press G, then Z, and move the mouse. Press Esc to cancel, or click to keep it.
**Done when:** Orbiting and selecting feel natural.

## Step 3: Block out the big shape
**Design question:** How big is it next to the player? (1 unit is about 1 meter: a chest is about 1 x 0.6 x 0.6.)
**Why it matters:** Blocking out means getting the overall shape and size right before any detail. Most beginner models go wrong here, not in the details.
**Build:** Start from New Shape (cube or cylinder). Use S (scale) with X, Y or Z to stretch it to the right proportions.
**You'll learn:** Scaling along one axis, typing exact numbers (S, Y, 0.6, Enter), snapping with Ctrl.
**Done when:** From a distance, the gray shape already reads as your object.

## Step 4: Extrude and inset
**Build:** Add the main features with E (extrude: pull a face out to build new sides) and I (inset: shrink a face inward, leaving a border). A lid: inset the top, extrude it up. A lantern window: inset a side face, extrude it inward slightly.
**You'll learn:** Extrude and inset are most of low-poly modeling. Insetting before extruding keeps an edge around the new part, like a frame.
**Try it yourself:** Inset the front face, then extrude it in a little to make a panel or a keyhole plate.
**Done when:** The prop has its 2-3 main features.

## Step 5: Shape the silhouette
**Design question:** If your prop were a black shadow, would people still recognize it?
**Why it matters:** The silhouette is what players read first, especially in a busy game scene. Strong, simple outlines beat lots of small detail.
**Build:** In Vertices mode (1), select corners and move them (G) to taper, bevel or tilt parts: a slightly wider lid, a bent sign post, a lantern that narrows at the top.
**You'll learn:** Moving vertices, box select (drag), how a few moved corners make a shape feel handmade instead of perfect.
**Done when:** It looks good from every side as a plain gray shape.

## Step 6: Color with a small palette
**Design question:** Which 3-5 colors? Pick a main color, a darker one for shadows or trim, and one accent that draws the eye (gold on a chest, warm light in a lantern).
**Why it matters:** Limited palettes look intentional and tie your whole game together. Contrast in brightness (value) matters more than hue.
**Build:** Select faces, pick a color, press P. Save the palette's colors in your Concept Journal so every prop uses the same ones.
**You'll learn:** Value contrast, accent colors, consistency across assets.
**Done when:** The accent color is the first thing you notice.

## Step 7: Into the game
**Build:** Save (Ctrl+S) into assets/models. The Studio exports a .glb next to it. Drag the .glb into a 3D scene, or ask Ember to place it and add a collision shape.
**You'll learn:** How a model becomes a game object: a scene with a mesh, plus a collision shape so the player can bump into it.
**Done when:** Your prop is standing in your game world.
