# Art Path: a game-ready weapon in Blender (sword first, then axes, spears and maces)
A sword is the classic first weapon because it's symmetrical, made of a few clear parts (blade, guard, grip, pommel) and teaches mirroring, beveling, UVs and texturing. The same steps make axes, spears, maces and staffs. Do the Blender foundations path first if G/R/S, E, I and Ctrl+R aren't automatic yet.

## Step 1: Design and references
**Design question:** Who carries it, and what should it say about them? A knight's arming sword is plain and practical; a boss's greatsword exaggerates everything. How big is it next to the player? (A real longsword is about 1.1 m; one-handed arming swords are about 0.9 m; game weapons are often 10-20% oversized so they read on screen.)
**You'll learn:** The parts of a sword: blade (with an optional **fuller**, the groove that lightens it), **crossguard**, **grip** and **pommel**. Look up 'Longsword', 'Hilt' and 'Fuller' with blender_help for real references.
**Build:** Draw or collect a front and side picture (your concept art, or a photo of a real sword). In the RusticEngine sidebar tab press Add Reference Images, pick them and type the real length as the height. They line up by themselves. Look through them with Numpad 1 and 3.
**Done when:** You have the length, the silhouette and the parts decided.

## Step 2: Block out with primitives
**Build:** One object per part: a cube scaled flat for the blade (S X 0.03, S Y 0.008 with real numbers), a cube for the guard, a cylinder (8-12 sides) for the grip, a UV sphere or cylinder for the pommel. Shift+D duplicates, Ctrl+A > Scale applies scale on each part.
**You'll learn:** **Silhouette first.** At game distance players only see the outline. Check it in front view with the shading pie (Z) set to solid and the overlays off (Shift+Alt+Z): does it read as YOUR weapon in black?
**Done when:** The gray blockout matches the reference outline in front and side views.

## Step 3: Shape the blade
**Build:** Tab into the blade. Ctrl+R adds loops along the length. Select the tip vertices and merge them (M > At Center) for the point, or scale them on X (S X 0) for a chisel tip. For the edge bevel (the sharpened sides), select the two long side edges and scale them on Y (S Y 0) so the cross-section becomes a diamond. Add a Mirror modifier on X and Y if the blade is symmetrical, with Clipping on.
**You'll learn:** A blade's cross-section (diamond, lenticular, hollow-ground) is what makes light run along it. Low-poly blades need only 1-2 loops across; spend the vertices on the silhouette.
**Try it yourself:** A fuller: inset (I) a long thin strip of faces on the flat of the blade, then extrude it inward (E, -0.002).
**Done when:** The blade catches light along its edge in Material Preview (Z).

## Step 4: Guard, grip and pommel
**Build:** Guard: extrude (E) the ends of the guard cube and scale them to flare, or bevel (Ctrl+B, scroll for segments) for a rounded bar. Grip: loop-cut (Ctrl+R) the cylinder 6-10 times and scale alternate loops (Alt+click, S) for wrapped leather ridges. Pommel: a low-poly sphere scaled flat, or a cylinder beveled.
**You'll learn:** **Weld points**: parts may intersect each other instead of being joined; games don't care about hidden intersections, and separate parts are easier to texture. Join them at the end with Ctrl+J.
**Done when:** All four parts are in place and the whole thing still reads in silhouette.

## Step 5: Clean shading
**Build:** Add a Bevel modifier (Amount ~2 mm, Segments 2, Limit Method Angle) and a Weighted Normal modifier (turn on Keep Sharp), or use Object > Shade Auto Smooth. Check with Z > Material Preview.
**You'll learn:** Small bevels plus weighted normals make low-poly hard surfaces look high quality without a baked normal map. Watch the triangle count in the status bar (right-click it > Scene Statistics): a hero weapon in a modern game is 2,000-10,000 triangles; stylized ones 300-2,000.
**Done when:** No dark smudges on flat faces, and edges catch a highlight.

## Step 6: UV unwrap
**Build:** Mark seams where you'd cut the surface open to lay it flat: select edges, Ctrl+E > Mark Seam (along the blade's edges, around the grip, under the guard). Select all (A), U > Unwrap. Look at it in the UV Editing workspace tab. Give the material an image of the UV grid (Image Texture > New > Generated Type: UV Grid) to see stretching.
**You'll learn:** UVs map the 3D surface onto a 2D picture. Seams are cuts; hide them where players won't look. **Texel density**: every part should get roughly the same pixels per meter, or one part looks blurry next to another (the free Texel Density Checker extension measures it). Symmetrical parts can overlap in UV space to save texture room.
**Done when:** The checker squares are square and about the same size everywhere.

## Step 7: Materials and texture
**Build:** Separate materials for steel, leather and wood/brass, each a Principled BSDF: steel Metallic 1, Roughness 0.3-0.4; leather Roughness 0.7 with a Noise Texture into a Color Ramp for variation. RusticEngine rebuilds Noise, Checker, Gradient, Color Ramp, Math and Mix nodes as real shaders. Free CC0 metal and leather texture sets are on Poly Haven and ambientCG (ask Ember for one). For painted detail, use Texture Paint mode or follow the baking path.
**You'll learn:** **PBR**: base color, metallic, roughness and normal describe what the surface is, so it looks right under any light. Metal has no diffuse color; its color is in its reflections.
**Done when:** It looks like steel and leather in Material Preview, not plastic.

## Step 8: Ready for the game
**Build:** Put the origin where the hand holds it (select the grip's center in Edit Mode, Shift+S > Cursor to Selected, then in Object Mode Object > Set Origin > Origin to 3D Cursor). Point the blade along a consistent axis (e.g. +Y). Name it (F2). Export with Live Link on.
**You'll learn:** The origin is the attachment point: the engine attaches a weapon to the hand bone at the origin. A consistent orientation lets every weapon swap into the same socket.
**Done when:** The sword shows up in RusticEngine, and attaching it to a hand needs no rotation fixes.
