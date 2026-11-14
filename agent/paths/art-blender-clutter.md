# Art Path: clutter and props in Blender (crates, barrels, sacks, bottles, books)
Clutter makes a world feel lived in. The skill here is speed and consistency: lots of small props that share a style, a texture and a sense of scale, with variations made cheaply. Look up 'Set dressing' and 'Environmental storytelling' with blender_help.

## Step 1: Decide the set
**Design question:** What does this place say about who lives here? A tavern has mugs, barrels and spilled cards; a crypt has candles, bones and dust. Pick 5-8 props that tell that story.
**You'll learn:** Clutter is storytelling. A knocked-over chair says more than a tidy room.
**Done when:** You have a list of props and their real sizes (barrel ~0.9 m tall, crate 0.6 m, mug 0.12 m, book 0.25 m).

## Step 2: One style sheet
**Build:** Decide polycount and bevel size once: e.g. cylinders with 12 sides, bevels of 1 cm, all props share one material with a small texture atlas (or the same 3-4 materials). Make the first prop (a crate: cube, inset I, extrude E; foundations path step 4).
**You'll learn:** Consistency matters more than detail: a scene where every prop uses the same bevel size and texel density looks designed.
**Done when:** The first prop sets the rules.

## Step 3: Fast primitives
**Build:** Barrel: cylinder (12-16 sides), Ctrl+R for 4 loops, scale the middle ones out (Alt+click, S), inset the top (I) and extrude it down (E) for the lid, select two loops and extrude along normals (Alt+E > Extrude Faces Along Normals) for metal bands. Sack: a cube with Subdivision (Ctrl+2), then sculpt or use the Cloth modifier dropped on the floor. Bottle: a cylinder, profile shaped by scaling loops, or a Screw/Spin from a half outline.
**You'll learn:** Most props are a primitive plus 2-3 operations. Spin/Screw turn a 2D profile into anything round (bottles, vases, goblets).
**Done when:** You've made 3 props in under 10 minutes each.

## Step 4: Variations without new work
**Build:** Alt+D makes a linked duplicate (shares the mesh; edit one and they all change). For variation, rotate and scale copies, swap a material, or use Geometry Nodes to randomize rotation and scale. Use Shift+D when you want a copy you'll change.
**You'll learn:** **Instancing**: linked duplicates cost almost nothing in memory, and the engine can draw many copies of one mesh cheaply. Ten crates should be one crate placed ten times.
**Done when:** A pile of 10 props uses 2-3 actual meshes.

## Step 5: Share one texture
**Build:** UV-unwrap every prop (U > Unwrap or Smart UV Project) into ONE texture: a **trim sheet** or atlas with wood planks, metal bands, cloth and labels. Pack islands (UV > Pack Islands), then move each prop's islands onto the matching strip. Free CC0 wood and metal sets: Poly Haven, ambientCG.
**You'll learn:** One material for many props means fewer draw calls, which is what keeps games fast with lots of objects. **Texel density** must match across props.
**Done when:** All props use one material and look consistent next to each other.

## Step 6: Origins, placement, export
**Build:** Origin at the bottom center of each prop (Edit Mode: select bottom face, Shift+S > Cursor to Selected; Object Mode: Object > Set Origin > Origin to 3D Cursor). Name each one (F2). Put each prop in its own .blend or export them as one file the engine can split.
**You'll learn:** Origins at the bottom let props sit on the floor when dropped into the editor and rotate around their base.
**Done when:** Every prop drops onto the floor correctly in RusticEngine.
