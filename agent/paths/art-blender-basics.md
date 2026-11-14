# Art Path: Blender foundations (mesh anatomy, navigation and the shortcuts that make modeling fast)
Before weapons, buildings or terrain, three ideas make everything else easy: what a mesh actually is, how to move around without thinking, and doing almost everything from the keyboard. Professionals aren't faster because they know secret tools; they press keys instead of hunting through menus. Every step here ends with a drill. All shortcuts are Blender 5.2 defaults (left-click select). F3 searches every command by name, and the search result shows its shortcut: use it to learn new ones.

## Step 1: What a mesh is
**You'll learn:** A mesh is a list of **vertices** (points in space), **edges** (lines joining two vertices) and **faces** (flat surfaces filled in between 3 or more edges). Faces with 3 sides are triangles, 4 are **quads**, more are **n-gons**. The game engine only draws triangles, but quads are easier to work with because edge loops flow through them (Step 5). Each face has a **normal**: an arrow pointing out of its front side. Lighting uses normals, and faces seen from behind can turn invisible in games (back-face culling), so normals must point outward.
**Build:** Add a cube (Shift+A > Mesh > Cube). Press Tab for Edit Mode, then 1 (vertices), 2 (edges), 3 (faces). Open the Overlays menu (top right of the viewport) and turn on Face Orientation: blue is the front of a face, red is the back.
**Try it yourself:** Select one face (3, click it) and press Alt+N > Flip. It turns red. Press Shift+N (Recalculate Outside) to fix it. That's the fix for most "my model has holes in the game" problems.
**Done when:** You can say how many vertices, edges and faces a cube has (8, 12, 6) and what a red face means.

## Step 2: Moving the view without thinking
**Build:** Middle mouse drag orbits, Shift+middle drag pans, the wheel zooms. Numpad . frames the selection (Home frames everything). Numpad 1 front, 3 right, 7 top (Ctrl+ the same number for the opposite side), Numpad 5 switches perspective/orthographic. The ` key (left of 1) opens a view pie menu. No numpad? Edit > Preferences > Input > Emulate Numpad, or use the view gizmo in the top right.
**You'll learn:** Orthographic views have no perspective, so lengths and angles are true. Model the shape in ortho front/side/top, then check it in perspective.
**Try it yourself (drill):** Without the mouse: front (1), side (3), top (7), back (Ctrl+1), frame selected (Numpad .), toggle ortho (5). Do it three times in a row.
**Done when:** You never reach for the view gizmo.

## Step 3: The transform keys G, R, S
**Build:** Select something and press G (grab/move), R (rotate) or S (scale). While moving, press X, Y or Z to lock to that axis (Shift+Z locks to everything except Z), type a number for an exact value (G Z 0.5 Enter), hold Ctrl to snap, Shift for fine control. Right click or Esc cancels. Pressing G twice on a vertex or edge slides it along the surface.
**You'll learn:** These three keys plus axis locks and numbers are about 40% of all modeling. Typed numbers make models clean and exact.
**Try it yourself (drill):** Make a box 2 m long, 0.5 m wide and 1 m tall from the default cube, using only S, X/Y/Z and typed numbers. Then press Ctrl+A > Scale. "Apply scale" bakes the size into the mesh. Bevels, modifiers and the game engine expect a scale of 1, so always apply scale before modeling details.
**Done when:** The N panel (press N) shows Dimensions 2 x 0.5 x 1 and Scale 1, 1, 1.

## Step 4: Extrude, inset, bevel
**Build:** In Edit Mode, face select (3): E extrudes (pulls the face out, building new side faces), I insets (shrinks a face inward, leaving a ring of faces), Ctrl+B bevels edges (rounds or chamfers them), and Ctrl+Shift+B bevels vertices. Scroll the mouse wheel during a bevel to add segments. After any tool, press F9 (or open the panel in the bottom left) to change its settings afterwards.
**You'll learn:** Almost any hard object is a box that has been extruded, inset and beveled. Bevels matter even on low-poly models: real objects never have perfectly sharp edges, and a small bevel catches light and makes the shape read.
**Try it yourself (drill):** Turn a cube into a simple crate: inset all six faces (select all with A, press I, then I again for individual faces), then extrude the insets inward (E, -0.05).
**Done when:** You can do the crate in under a minute, without menus.

## Step 5: Edge loops and topology
**Build:** Ctrl+R adds a loop cut: hover over an edge, scroll to add more cuts, click, then slide or right-click to center. Alt+click an edge selects its whole loop; Ctrl+Alt+click selects a ring. K is the knife, J connects two selected vertices with an edge, M merges vertices, X deletes (and asks what), Ctrl+X dissolves without leaving a hole.
**You'll learn:** **Topology** is how the faces flow across the surface. Edge loops are rings of quads around a shape, like the lines of latitude on a globe. They decide where a model can bend (joints need loops), how it smooths (Subdivision Surface follows loops), and how easy it is to select and change. Triangles and n-gons stop loops, so keep them on flat areas where nothing bends.
**Try it yourself (drill):** Loop-cut a cylinder 4 times, select one loop (Alt+click) and scale it (S) to make a waist. Add Subdivision with Ctrl+2 in Object Mode and watch how the loops control the shape. Ctrl+0 removes it again.
**Done when:** You can explain why a joint needs extra loops.

## Step 6: Modifiers (non-destructive modeling)
**Build:** Properties > Modifiers (wrench) > Add Modifier. Mirror (model half, it copies the other side; turn on Clipping so the middle vertices stay joined), Bevel (rounds every edge without changing the mesh), Solidify (gives thickness to a flat surface), Array (repeats it), Subdivision Surface (Ctrl+1 to Ctrl+5 in Object Mode), Weighted Normal (makes beveled low-poly shading look clean). Ctrl+A > Apply when you're sure.
**You'll learn:** Modifiers are a stack of recipes applied on top of your mesh, top to bottom. Order matters: Mirror before Bevel bevels the joined result. The RusticEngine Link exports the result with every modifier applied, so you can keep them live in Blender.
**Done when:** You've built something with Mirror + Bevel + Weighted Normal and switched each one off and on to see what it does.

## Step 7: Shading, smoothness and the look
**Build:** Z opens the shading pie (Wireframe, Solid, Material Preview, Rendered). Alt+Z is X-ray (select through the model). Object > Shade Auto Smooth smooths curved faces but keeps sharp edges sharp (it adds a Smooth by Angle modifier).
**You'll learn:** Flat vs smooth shading only changes how normals are averaged, not the geometry. A "smooth" low-poly cylinder still has 16 sides; the lighting hides them. That's why normals also matter for baking later.
**Done when:** You can make a cylinder look round with only 12-16 sides.

## Step 8: Get it into the game
**Build:** Open the RusticEngine tab in the sidebar (N), set your project once, press Export to RusticEngine, then tick Live Link. From now on Ctrl+S in Blender updates the game. Keep the .blend file outside the project folder.
**You'll learn:** 1 Blender unit = 1 meter = 1 unit in the engine. Apply scale (Ctrl+A) and put the origin where the object should stand (Object > Set Origin) before export.
**Done when:** Your crate is in your game, and changing it in Blender updates it there.

## Step 9: Light it once, in Blender
**Design question:** What time of day is your scene, and where does the light come from?
**Build:** Add a Sun (Shift+A > Light > Sun) and rotate it (R) until the shadows fall the way you want; Strength 3-5 is daylight. Add Point or Spot lights for lamps and torches (Watts in the Light properties), Area lights for windows. Set the world: World properties > Color for a plain sky, or an HDRI (Environment Texture, free CC0 skies on Poly Haven) for real outdoor light. Check it in Rendered view (Z > Rendered) with Cycles.
**You'll learn:** Light has units: a sun is measured per square meter (it's the same everywhere), a lamp in watts (it fades with the square of the distance: twice as far = a quarter as bright). RusticEngine rebuilds Blender's sun, point, spot and area lights with the same brightness, plus the world sky and your color management (AgX/Filmic and Exposure in Render properties > Color Management), when Send World is on in the RusticEngine panel. Area lights become soft spot lights (games have no true area lights). Turn Send World off for props, so only the level brings its sky.
**Try it yourself:** Move a point light twice as far from a wall and predict how much darker it gets before you look.
**Done when:** The scene looks the same in Blender's Rendered view and in your game.

## Step 10: Make it solid (collision)
**Design question:** What should the player bump into, stand on, push, or walk through to trigger something?
**Build:** Select an object and, in the RusticEngine panel's Collision box, pick **Static** (floors, walls, rocks: never moves), **Physics** (crates, barrels: falls and gets pushed) or **Trigger** (a zone that notices the player: checkpoints, doors, traps). This is Blender's own Rigid Body (Physics properties): choose the **Shape** there, and for physics objects the Mass, Friction and Bounciness. Tick **Collision Only** on a simple box placed around a detailed statue to make an invisible, cheap collider (then turn off collision on the statue). Press Space in Blender to drop your physics objects and watch them fall: the game behaves the same way.
**You'll learn:** The physics engine never touches your detailed mesh: it uses a simple stand-in shape. Cheapest to most expensive: Sphere, Box, Capsule/Cylinder, Convex Hull (shrink-wrap with no dents), Mesh (exact, dents included). Mesh is only for things that never move (floors, terrain); moving objects need a convex shape. In the game, each one becomes a body named after the object, with the visible mesh as a child named Mesh. (Godot's naming also works: an object named Wall-col gets exact static collision, Wall-colonly becomes invisible collision.)
**Try it yourself:** Give a crate Convex Hull, then Box, and predict which one rolls when it lands on its corner before you press Space.
**Done when:** You can walk on your floor, push your crate, and a trigger zone reports the player entering.
