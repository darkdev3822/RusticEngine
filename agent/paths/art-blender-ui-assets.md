# Art Path: UI art with Blender (icons, item renders, frames and buttons)
Blender is a great UI art tool: model an item once and render it as an inventory icon from any angle, in a consistent style, at any size, in seconds. Frames, buttons and health bars can be rendered too. Look up 'Icon (computing)', 'Skeuomorphism', 'Flat design' and '9-slice scaling' with blender_help.

## Step 1: Style and sizes
**Design question:** What style does your interface have: painted, flat, pixel, metal and stone, sci-fi? What size are icons on screen (64, 128, 256 px)?
**You'll learn:** UI art is read in a fraction of a second. Silhouette and one strong color matter more than detail. All icons must share the same angle, light and outline to read as a set.
**Done when:** You have the icon size and 2-3 reference games or images.

## Step 2: An icon studio scene
**Build:** A camera looking at the origin at a fixed angle (e.g. 30 degrees down, 45 around), set to Orthographic in its properties. Output size square (Properties > Output: 256 x 256). Film > Transparent so the background is empty. Lights: one key light, one rim light behind, low ambient. Save this as icon_studio.blend.
**You'll learn:** **Three-point lighting** (key, fill, rim). The rim light separates the item from any background, which is what makes icons pop.
**Done when:** F12 renders a placeholder cube as a crisp icon with a transparent background.

## Step 3: Render your items
**Build:** Append the item (File > Append, pick the object from its .blend) or link it, frame it (select camera, Numpad 0 to look through it, adjust the orthographic scale), F12 to render, Image > Save As (Shift+Alt+S in the image editor). Batch it: one collection per item, toggle visibility, render each.
**You'll learn:** Ortho cameras keep every item the same apparent size. Eevee renders in a second; use the same settings for every icon.
**Done when:** You have 3 icons that clearly belong to the same set.

## Step 4: Outlines and style
**Build:** Outline: Properties > View Layer > enable Freestyle, or add a Solidify modifier with Flip Normals and a dark emission material (the "inverted hull" outline). Flat style: an Emission material with a Color Ramp (Constant) on light direction for a toon look.
**You'll learn:** The inverted hull trick (a slightly bigger copy, flipped inside out) is also how many games draw character outlines in real time.
**Done when:** Your icons have a consistent outline and shading style.

## Step 5: Frames and buttons (9-slice)
**Build:** Model a frame (a beveled border around an empty middle), render it straight on with the ortho camera. In RusticEngine use it as a 9-slice: a StyleBoxTexture or NinePatchRect with margins equal to the border width, so the corners stay sharp at any size.
**You'll learn:** **9-slice scaling**: corners never stretch, edges stretch in one direction, the middle in both. One rendered frame then fits every window size.
**Done when:** One frame image fits a small tooltip and a big inventory window without distortion.

## Step 6: Into the game
**Build:** Save renders into the project (e.g. assets/ui/icons/). In RusticEngine they import as textures. The Studio's UI Kit can use them, and Ember can wire them into the inventory.
**Done when:** Your icons show in the game's UI.
