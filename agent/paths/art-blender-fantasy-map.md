# Art Path: fantasy maps and cartography (world maps, region maps, in-game maps)
A good fantasy map is believable geography plus a clear, beautiful style. Blender can make the terrain, shade it like a real relief map, draw contour lines, and render it with a parchment look. Look up 'Fantasy map', 'Cartography', 'Terrain cartography', 'Contour line', 'Plate tectonics', 'Rain shadow' and 'Coastline paradox' with blender_help.

## Step 1: Believable geography
**You'll learn:** The rules readers subconsciously check:
- **Mountains** form in long ranges where tectonic plates collide, often near coasts. Single cone mountains are volcanoes.
- **Rivers** start in mountains and hills, flow downhill to the sea or a lake, and join as they go. They don't split on the way (except deltas at the sea), and they don't cross mountain ranges.
- **Rain shadow**: wind brings rain to one side of a range; the other side is dry (deserts sit behind mountains).
- **Biomes** follow latitude and rain: ice at the poles, forests in wet temperate areas, deserts around 30 degrees and in rain shadows, jungles at the wet equator.
- **Coastlines** are rough at every scale (the coastline paradox), so jagged, uneven coasts look real and smooth blobs don't.
- **Cities** sit on rivers, coasts and crossroads, because that's where trade and water are.
**Design question:** What story happens on this map? Put the important places first, then make the geography explain them (a fortress guards the only pass through the mountains).
**Done when:** You've sketched continents, ranges, rivers and the key places.

## Step 2: A head start (optional)
**Build:** Azgaar's Fantasy Map Generator (free, open source, MIT, runs in the browser) generates whole worlds with tectonics, rivers, biomes, cultures and states. Use it to explore ideas or as a base, then restyle in Blender. Export its heightmap as an image.
**You'll learn:** Generators are great for plausibility; the map becomes yours through your choices of places, names and style.
**Done when:** You have a base (generated or hand-drawn sketch).

## Step 3: Terrain from a heightmap or by hand
**Build:** Shift+A > Mesh > Grid (200 x 200 subdivisions). Add a Displace modifier: New texture, type Image (your heightmap) or Clouds/noise for a quick start, Strength to taste. Or sculpt it (terrain path, step 2). Sea level: a plane at height 0.
**You'll learn:** A map is a terrain seen from straight above, so the same heightmap can be your game's terrain AND its map.
**Done when:** Continents rise above the sea plane where you sketched them.

## Step 4: Color by height (hypsometric tints)
**Build:** Terrain material: Texture Coordinate (Object) or Geometry > Position > Separate XYZ > Z > Map Range (sea level to highest peak into 0-1) > Color Ramp: sand, green lowlands, yellow-brown hills, gray rock, white peaks. Water: the sea plane colored deep blue, lighter near the coast (a Color Ramp on the terrain height just below 0 under transparent water).
**You'll learn:** **Hypsometric tints** (color by elevation) are a real cartography technique; atlases use them because readers understand height instantly.
**Done when:** You can read high and low ground from color alone.

## Step 5: Hillshade and contour lines
**Build:** Hillshade: a Sun light from the northwest (top left) at a low angle, Eevee rendering, so slopes facing it are bright and the others dark. Contour lines: Z height > Math Multiply (e.g. 20 = one line every 1/20 of the height range) > Math Fraction > Math Less Than 0.05 > use as a mix factor for thin dark lines over the color.
**You'll learn:** **Hillshading** from the top left is a cartography convention: light from the bottom right makes mountains read as valleys. **Contour lines** connect points of equal height; close lines mean steep ground.
**Done when:** Mountains pop out of the page.

## Step 6: Style it like a map
**Build:** Camera straight down (Numpad 7, then Ctrl+Alt+Numpad 0 to put the camera there), Orthographic. Parchment: mix a large soft Noise into the colors (Mix Multiply, low factor) and a darker vignette at the edges. Rivers, borders and roads: draw them with Grease Pencil (Shift+A > Grease Pencil > Blank, then Draw mode) or as curves with a thin bevel. Labels: Shift+A > Text, Tab to type, a serif or hand-lettered font, curved along a path for ranges and seas. Compass rose and cartouche (the title frame): model or draw them, or use CC0 assets.
**You'll learn:** Style choices: painted atlas, old parchment, clean modern. **Map symbols** (little mountain icons, tree clusters) are often clearer than realistic shading for a fantasy world map; you can mix both.
**Done when:** F12 renders a map you'd want to hang on a wall.

## Step 7: Into the game
**Build:** Render at a high resolution (Output Properties: e.g. 4096 x 4096), save it into the project (assets/ui/map.png). In RusticEngine, show it in a map screen (a TextureRect inside a scrollable, zoomable panel), and ask Ember to add a player marker that follows the player's position (the map's scale is known from your terrain size).
**You'll learn:** If the map was rendered from the same terrain the game uses, positions convert directly: map pixel = world position x pixels per meter.
**Done when:** The player can open the map in the game and see where they are.
