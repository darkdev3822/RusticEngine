# Art Path: buildings in Blender (a modular kit you can snap together)
Games don't model each house as one object. They build a **modular kit**: walls, corners, doors, windows, floors and roof pieces on a shared grid, and assemble buildings from them in the editor. Learn the kit, and one afternoon of modeling gives you a whole village. Look up 'Timber framing', 'Medieval architecture', 'Masonry' and 'Roof' with blender_help for real-world references.

## Step 1: Style and grid
**Design question:** What era and culture? What does the player do in these buildings (enter them? only see them from outside?) That decides how much interior you need.
**You'll learn:** **The grid is everything.** Pick a module size and never break it: e.g. walls 2 m wide and 3 m tall, floors 2 x 2 m, door openings 1 x 2.2 m. Make the module fit your character: doors need room for the camera.
**Build:** Snapping: Shift+Tab toggles snapping, Ctrl+Shift+Tab chooses what to snap to (Increment, with "Absolute Grid Snap" on, so things land on the grid). Set the grid in the Overlays panel if you want 0.5 m steps.
**Done when:** You've written the module sizes down.

## Step 2: The first wall piece
**Build:** Add a plane, scale it to exactly 2 x 3 m with typed numbers (S X 2... or edit vertices with snapping), Solidify for thickness (0.2-0.3 m), apply scale (Ctrl+A). Put the origin on a bottom corner (Shift+S > Cursor to Selected on that vertex, Object > Set Origin > Origin to 3D Cursor).
**You'll learn:** Corner origins make pieces snap edge to edge in the engine with whole-number positions.
**Done when:** Two copies (Shift+D, X 2, Enter) meet with no gap and no overlap.

## Step 3: The kit
**Build:** From the wall: wall with door (cut the opening with loop cuts Ctrl+R and delete faces, or a Boolean with a box: Bool Tool extension makes this quick), wall with window, corner piece (outer and inner), floor tile, stairs, roof slope and roof end. Keep all of them on the grid.
**You'll learn:** About 8-12 pieces build almost any building. Variation comes from combining them, not from more pieces.
**Done when:** You can build a small house from the kit in Blender by snapping alone.

## Step 4: Shape and age
**Build:** Break perfect lines: move a few vertices on the roof ridge (G with proportional editing, O, scroll to change its radius), add timber beams (thin boxes) along the edges of the wall, bevel the stone corners. Keep the outer edges of each piece on the grid so pieces still fit.
**You'll learn:** **Proportional editing** moves nearby vertices with a falloff, which makes sagging roofs and bent beams in one move. Age is in the silhouette: a dead-straight roof looks like a toy.
**Done when:** It looks built by people, not by a computer.

## Step 5: Trim sheets and tiling textures
**Build:** Use tiling textures for big areas (stone, plaster, wood planks: free CC0 sets on Poly Haven and ambientCG) and a **trim sheet** for edges and beams. UVs: walls use a cube-like projection so stones are the same size everywhere; select faces and U > Cube Projection, or Smart UV Project. The free Texel Density Checker extension keeps scale consistent across pieces.
**You'll learn:** **Tiling** textures repeat seamlessly, so a 2 m wall and a 20 m wall use the same 1 texture with UVs that extend past 0-1. Matching texel density is what makes pieces look like one building.
**Done when:** Stones are the same size on every piece and no seams show where pieces meet.

## Step 6: Into the engine
**Build:** Export the kit (each piece a separate object with a clear name: wall_2x3, wall_door, corner_out...) with Live Link on. In RusticEngine, snap them on the grid (use the same module size for grid snapping in the editor).
**You'll learn:** Gameplay stays in the engine: colliders, doors that open and lights are added there and are kept when you update the kit in Blender.
**Done when:** You assemble a building in RusticEngine from the kit.

## Step 7: Optional: generated buildings
**You'll learn:** The free Archimesh extension generates rooms, doors and windows from parameters, and Geometry Nodes can place kit pieces along a floor plan automatically. Try them once the kit idea makes sense; they don't replace knowing the grid.
**Done when:** You know which buildings you'd model by hand and which you'd generate.
