# Art Path: armour pieces in Blender (pauldron, helmet, chestplate)
Armour is shaped around a body, so it teaches modeling on a curved surface, thickness, mirroring and how to make plates feel heavy. Start with one pauldron (shoulder plate), then a helmet. Real armour is great reference: look up 'Plate armour', 'Pauldron', 'Components of medieval armour' and 'Chain mail' with blender_help.

## Step 1: Design and the body underneath
**Design question:** Heavy plate, scale, leather or fantasy? Which silhouette should the character have from far away (big shoulders read as strong; a tall helmet crest reads as rank)?
**Build:** Armour must fit a body. Use your character, or a free CC0 human base mesh (Blender Studio's Human Base Meshes bundle is CC0). Add front and side references with Add Reference Images, entering the character's height.
**You'll learn:** Armour is built in layers over the body with a small gap (5-15 mm), so it doesn't poke through when animated.
**Done when:** The body is in place and you know which pieces you'll make.

## Step 2: Shape a plate from the body
**Build:** Select the shoulder faces of the body in Edit Mode (3, then click or C for circle select), Shift+D to duplicate them, P > Selection to separate them into their own object. Now the plate already has the body's curve. Scale it out slightly (Alt+S, shrink/fatten, moves along normals).
**You'll learn:** Starting from the surface you're covering is far easier than bending a flat plane. Alt+S pushes along normals, which is how you add the gap evenly.
**Done when:** A shell sits just above the shoulder.

## Step 3: Clean the outline
**Build:** Delete faces to get the plate's outline (X > Faces), then tidy the border: select the boundary edge loop (Alt+click) and smooth or straighten it. Add a Mirror modifier if the piece is symmetrical (pauldrons are mirrored left/right as separate objects; helmets are mirrored down the middle).
**You'll learn:** **Shape language**: rounded plates feel protective and friendly, sharp flared edges aggressive. Keep plate edges smooth curves; bumpy outlines read as cheap.
**Done when:** The silhouette matches your design from front, side and top.

## Step 4: Thickness and rolled edges
**Build:** Add a Solidify modifier (thickness 3-6 mm, a little exaggerated for games), then Bevel (Limit Method Angle). For the rolled edge on real armour, select the border loop, extrude it outward (E), and roll it under with R. Overlapping lames (the bands of a pauldron): duplicate the plate (Shift+D), scale each copy slightly smaller and stack them.
**You'll learn:** Thickness on the edges is what makes armour look like metal rather than paper, and only the edges show it, so a Solidify modifier gives you both without modeling it.
**Done when:** It looks heavy from the side.

## Step 5: Details that read
**Build:** Rivets: a small UV sphere duplicated along the edge with an Array + Curve modifier, or placed by hand with snapping (Shift+Tab, snap to Face). Straps: a thin strip of faces separated from the body (Step 2) and given thickness. Trim: inset (I) a border on the plate and extrude it slightly.
**You'll learn:** Detail density: put detail where the eye goes (edges, the face, the chest) and leave big plates calm. Rivets and straps also explain how the armour holds together, which makes it believable.
**Done when:** A player could guess how it's worn.

## Step 6: UVs, materials, wear
**Build:** Seams along the hidden underside and inner edges (Ctrl+E > Mark Seam), U > Unwrap. Materials: steel (Metallic 1, Roughness 0.35), leather straps, brass rivets. Edge wear: in RusticEngine-friendly nodes, a Noise Texture into a Color Ramp mixed over the base color. For true edge-only wear, bake curvature/AO (baking path).
**You'll learn:** Wear goes where things rub: edges, raised parts, where the arm moves. Dirt goes in crevices. That logic sells a material more than any texture.
**Done when:** It looks used, not new.

## Step 7: Fit for animation and export
**Build:** If the character is rigged, parent the armour to the armature (Ctrl+P > With Automatic Weights for flexible pieces, or parent to a single bone for rigid plates: select armature, Pose Mode, select the bone, Ctrl+P > Bone). Test by posing the arm. Export with Live Link.
**You'll learn:** Rigid plates follow one bone; cloth and leather bend with several. Plates that intersect when the arm lifts need to be cut into overlapping lames.
**Done when:** Raising the arm doesn't tear or clip the armour badly.
