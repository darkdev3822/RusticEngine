# Art Path: terrain and nature in Blender (landscapes, rivers, lakes, trees, grass)
Terrain is sculpted on a grid, painted with blended materials, and filled with nature that's **scattered**, not placed by hand. Blender has strong free tools for all of it. Look up 'Heightmap', 'Erosion', 'Drainage basin', 'Meander', 'L-system' and 'Biome' with blender_help.

## Step 1: Plan the land
**Design question:** What does the player do here, and where should their eye go? A landmark (mountain, tower, giant tree) visible from far away is how open worlds guide players without arrows.
**You'll learn:** Land follows rules: mountains form in ranges, valleys are cut by rivers, rivers flow downhill and join (they almost never split, except in deltas near the sea), lakes sit in low basins. Players feel when terrain breaks these rules.
**Done when:** You've sketched where the high ground, water and paths go.

## Step 2: Make the ground
**Build:** Shift+A > Mesh > Grid (e.g. 100 x 100 subdivisions, size 100 m), or the free A.N.T. Landscape extension (Get Extensions > search "A.N.T. Landscape") which generates noise landscapes with erosion settings. Shape it by hand in Sculpt Mode (Ctrl+Tab > Sculpt): G grab for big shapes, C clay strips to build up, S smooth, Ctrl+click to dig instead of raise, F to change brush size.
**You'll learn:** A **heightmap** is terrain stored as a grayscale image (white = high). Noise with several layers (fBM) looks like land because real terrain is self-similar: a rock looks like a small mountain. **Erosion** carves the believable details (valleys, ridges).
**Done when:** The big shapes match your plan when seen from the player's height.

## Step 3: Rivers and lakes
**Build:** Carve the riverbed into the terrain (sculpt with Ctrl+drag, or a curve with a Shrinkwrap'd strip, then lower it). Rivers meander (curve back and forth) more on flat ground and run straight and fast in steep valleys. Add the water surfaces from the water path: a flat plane for the lake at one height, a strip for the river that steps down.
**You'll learn:** Water surfaces are always level across a lake; rivers drop in steps (rapids, falls) between level stretches. A lake with a sloped surface looks wrong instantly.
**Done when:** Water fits the ground with no floating or sunken edges.

## Step 4: Ground materials
**Build:** Blend materials by masks (procedural texturing path): rock on steep slopes (Geometry > Normal, Separate Z, Color Ramp: steep = rock), grass on flat ground, sand/mud near water (Position Z below a height), and paint the rest with a vertex color or painted mask. Free CC0 ground textures: Poly Haven and ambientCG (grass, rock, mud, forest floor).
**You'll learn:** Slope and height masks texture a whole landscape automatically, then hand painting adds paths and story. This is exactly how game engine terrain systems work too.
**Done when:** Rock, grass and sand fall where nature would put them.

## Step 5: Trees and plants
**Build:** Free tree generators: Sapling Tree Gen (parametric trees with leaves, bones and wind) or Modular Tree (node-based), both in Get Extensions. IvyGen grows ivy over meshes. Make 3-5 tree variants, each low-poly with leaf cards (planes with a leaf texture with transparency). Free CC0 plant models: Poly Haven Models.
**You'll learn:** **L-systems** and branching rules make trees: each branch splits into smaller branches. Games use **leaf cards** (textured planes) instead of modeled leaves, and **LODs** (lower-detail versions far away), down to a flat **billboard** image at a distance.
**Done when:** You have a few tree variants with a sensible triangle count (game trees: 2,000-15,000 triangles).

## Step 6: Scatter
**Build:** Geometry Nodes: on the terrain add a Geometry Nodes modifier, then Distribute Points on Faces (density by your grass mask) > Instance on Points (your grass clumps / rocks / trees from a collection, Pick Instance on) > Realize only if needed. Randomize rotation (Random Value into Rotation) and scale. Or the free Scatter Objects extension.
**You'll learn:** Scattering with masks (no trees on steep rock, grass thinning on paths) makes nature believable at scale. In the game, scattered copies should stay **instances**, not one giant mesh.
**Done when:** A forest edge looks natural, denser in valleys and thinner on slopes.

## Step 7: Into the engine
**Build:** Export the terrain mesh and the hero pieces (rocks, landmark trees) with Live Link. For big worlds, split the terrain into chunks (e.g. 64 x 64 m tiles) so the engine can stream and cull them.
**You'll learn:** Gameplay stays in RusticEngine (paths, colliders, spawn points) and is kept when you update terrain from Blender.
**Done when:** You can walk your landscape in the game.
