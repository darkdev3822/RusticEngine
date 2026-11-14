# Art Path: baking textures in Blender (normal maps, AO, and turning any material into images)
**Baking** saves something expensive into an image the game can show cheaply: the detail of a high-poly model into a normal map on a low-poly one, shadows in crevices into an ambient occlusion map, or a complex procedural material into plain textures. Look up 'Normal mapping', 'Ambient occlusion', 'Texture atlas' and 'Texture mapping' with blender_help.

## Step 1: Why bake
**You'll learn:** A game model needs few triangles, but players love detail. A **normal map** stores, per pixel, which way the surface faces, so a flat low-poly face lights up as if it had the high-poly bumps and grooves. It only fakes lighting; the silhouette stays low-poly. **AO** (ambient occlusion) stores how hidden each point is from the sky: crevices get darker.
**Done when:** You can explain why a normal map can't change a model's outline.

## Step 2: High and low poly
**Build:** Two objects in the same place: the high poly (subdivided, sculpted, with every bevel and detail, millions of triangles is fine) and the low poly (the game mesh, clean UVs with no overlaps for baking). Same origin and position.
**You'll learn:** Work order: block out, high poly detail, then **retopology** (building the clean low poly over it; the Shrinkwrap modifier or snapping to Face helps), then UVs, then bake.
**Done when:** Both models sit on top of each other in Edit Mode with X-ray (Alt+Z).

## Step 3: Set up the bake
**Build:** Render Properties: Render Engine Cycles (baking only exists in Cycles). On the LOW poly's material, add an Image Texture node with a new image (2048 px, Non-Color for normal maps), select that node but DON'T connect it: the selected image node is the bake target. Select the high poly, then Shift+click the low poly (active last). Bake panel: type Normal, Selected to Active on, Extrusion ~0.02-0.05 m (or a Cage), click Bake.
**You'll learn:** Baking shoots rays from the low poly outward and inward (Extrusion / Max Ray Distance) to find the high poly. Too small misses detail; too big grabs the wrong part. Errors look like smears and holes: adjust distance or use a cage.
**Done when:** The normal map shows blue-purple with your details visible.

## Step 4: Use and check it
**Build:** Image Texture (your baked map, Non-Color) > Normal Map node > Normal of the Principled BSDF. Save the image (Image > Save As in the Image Editor). Compare low poly with normal map next to the high poly.
**You'll learn:** RusticEngine and Blender both use the same normal map direction (OpenGL style), so maps work as baked. The engine rebuilds the Normal Map node from the export.
**Done when:** From game distance you can't tell low from high.

## Step 5: AO and other maps
**Build:** Same setup, bake type Ambient Occlusion (from the high poly with Selected to Active, or from the low poly alone). Multiply AO into the base color with a Mix node (Multiply), subtly.
**You'll learn:** AO, curvature and thickness maps are also masks: dirt in AO, wear on curvature. Bake once, reuse as masks.
**Done when:** Crevices are darker and your dirt mask uses the AO.

## Step 6: Bake a procedural material to images
**Build:** The RusticEngine add-on does this for you: with Auto-Bake on (RusticEngine tab, N panel), materials the engine couldn't rebuild are baked into images on the next export, and 'Always bake' does it for any material (heavy node setups run faster as images). Do it by hand once anyway, so you know what it does: for materials RusticEngine can't rebuild (the AO node, Pointiness, 4D/animated noise...), bake each output to an image on the low poly: bake type Diffuse with only Color ticked for base color (or route the color into an Emission shader and bake Emit for exact colors), Roughness for roughness, Normal for bumps. Then make a simple material using the baked images.
**You'll learn:** Baking is the universal escape hatch: anything Blender can render, the game can show as an image.
**Done when:** The baked material looks the same in RusticEngine as the procedural one in Blender.
