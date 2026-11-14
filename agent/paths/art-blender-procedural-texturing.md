# Art Path: procedural texturing in Blender (wood, stone, rust, dirt, without painting a pixel)
Procedural textures are built from math (noise, gradients, patterns) in the Shader Editor instead of painted images. They never blur, tile endlessly, and every setting can be changed later. RusticEngine rebuilds many of these node setups as real game shaders, so they stay procedural in the game. Look up 'Procedural texture', 'Perlin noise', 'Worley noise' and 'Physically based rendering' with blender_help.

## Step 1: The Shader Editor
**Build:** Open the Shading workspace tab. Every material is a node graph that ends in Material Output. Shift+A adds nodes, drag between sockets to connect them, Ctrl+right-drag cuts links, M mutes a node, Ctrl+G groups nodes, Ctrl+H hides unused sockets, and Ctrl+Shift+click on any node previews its output in the viewport (the Viewer): use it constantly.
**You'll learn:** Nodes are a flow: coordinates in, patterns, then colors, then the shader. Read graphs left to right.
**Done when:** You can preview any node's output.

## Step 2: Coordinates and noise
**Build:** Texture Coordinate (Object or Generated) > Mapping > Noise Texture > Color Ramp > Base Color. Change Noise Scale, Detail, Roughness and watch. Stretch the noise with the Mapping node's Scale (e.g. X 1, Y 1, Z 20 = stretched along Z).
**You'll learn:** **Noise** is smooth randomness (Perlin noise, layered with fBM: more Detail adds finer layers). A **Color Ramp** turns the 0-1 noise values into colors or sharp masks. Stretched noise is already wood grain or brushed metal.
**Done when:** You've made brushed metal by stretching noise.

## Step 3: Wood and stone
**Build:** Grain: stretched Noise (Step 2) into a Color Ramp with two browns. Rings: Texture Coordinate (Object) > Separate XYZ > Combine XYZ using only X and Y (Z = 0) > Vector Math Length (distance from the trunk's center) > Math Multiply 20 (ring count) > Math Fraction (0-1 repeating) > Color Ramp (light to dark brown). Add a little noise to the coordinates before Separate XYZ (Vector Math Add) to make the rings wobble like real wood. Shortcut once you understand it: a Wave Texture set to Rings (Z axis, Distortion 3-5, Detail 3) does the same in one node. Stone: Voronoi Texture (F1) Color gives each stone its own shade; a second Voronoi set to Distance to Edge into a sharp Color Ramp draws the mortar and cracks; Brick Texture builds walls directly (Offset and Squash for irregular courses).
**You'll learn:** Most natural patterns are 1 base pattern + 1 distortion (add noise to the coordinates) + 1 color ramp.
**Done when:** It reads as wood (or stone) from a few meters away.

## Step 4: Masks: dirt, rust, moss
**Build:** Build a mask (black/white) and use it as the Factor of a Mix node between two materials' colors (and roughness). Masks from: Noise with a sharp Color Ramp (patches), Geometry > Normal Z (up-facing surfaces: moss, snow, dust), Separate XYZ of Position Z (grime near the ground), Ambient Occlusion node (crevices: dirt).
**You'll learn:** Real wear follows logic: rust where water sits, moss on top, dirt in corners, wear on edges. Encode the logic, not random spots.
**Done when:** A crate has dirt in its corners and moss on top only.

## Step 5: What survives into the game
**You'll learn:** RusticEngine rebuilds: Principled BSDF, Image Texture, Noise (all five types: fBM, Multifractal, Hetero Terrain, Hybrid and Ridged, 2D/3D), Voronoi (every feature and distance, 2D/3D, with Detail), Wave, Brick, Magic, Checker, Gradient, White Noise, Mapping, Color Ramp, Math, Vector Math, Mix, RGB Curves, Map Range, Clamp, Separate/Combine, Bump, Normal Map, Texture Coordinate (UV, Object, Generated). Not yet: 1D/4D Noise and Voronoi (the W input), the Ambient Occlusion node, Geometry > Pointiness. Those materials come in plain (Ember can tell you exactly which node stopped it: ask about the .glb).
**Build:** Use asset_info on your exported .glb (or ask Ember "why does my crate look flat?") to see which materials were rebuilt. For the rest, bake (baking path) or swap the node for a supported one.
**Done when:** Your material shows as rebuilt in the import report, or is baked.

## Step 6: Reuse
**Build:** Group a finished setup (Ctrl+G), expose the colors and scale as group inputs, and mark the material as an Asset (right-click it > Mark as Asset). Now it's in the Asset Browser for every project.
**You'll learn:** A personal library of 10 good materials (wood, stone, metal, cloth, dirt mask) covers most props.
**Done when:** You've reused a material on 3 different props.
