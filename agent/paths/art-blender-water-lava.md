# Art Path: water and lava (stylized and realistic, for games)
Liquids in games are mostly an illusion: a simple surface mesh plus a clever shader that moves. Real fluid simulation (Blender's Mantaflow) makes beautiful renders but produces heavy mesh sequences that games can't afford, so it's for cinematics and reference only. Look up 'Refraction', 'Fresnel equations', 'Caustic (optics)', 'Trochoidal wave', 'Lava' and 'Black-body radiation' with blender_help.

## Step 1: What makes water look like water
**You'll learn:** Four things, in order of importance: **reflection** that gets stronger at grazing angles (Fresnel: look across a lake and it's a mirror; look down and you see through it), **transparency/depth color** (shallow water shows the bottom, deep water turns blue-green), **moving normals** (small waves only change lighting, not geometry), and **foam/edges** where water meets objects. Lava is the opposite: opaque, self-lit (emission) and slow.
**Done when:** You can point to each of the four in a reference photo or a game you like.

## Step 2: The water surface mesh
**Build:** A plane for lakes and seas (Shift+A > Mesh > Plane), a curved strip for rivers (draw a Bezier curve along the riverbed, then a plane with Array + Curve modifiers to follow it, or extrude edges along the path). Subdivide only if the game will move vertices (big waves); otherwise keep it low-poly. UVs for rivers should run along the flow (U > Follow Active Quads on a quad strip), so the engine can scroll a texture downstream.
**You'll learn:** For rivers, the UV direction IS the flow direction. Waterfalls are just steep river strips.
**Done when:** You have a lake plane and a river strip with UVs running downstream.

## Step 3: Stylized water material
**Build:** Principled BSDF: Base Color deep blue-green, Roughness 0.05, Transmission 1 (or Alpha 0.6-0.8 with Blend Mode Alpha Blend in the material settings for the game). Waves: Noise Texture (Scale 5-20) > Bump node > Normal. Material Preview (Z) shows it.
**You'll learn:** In-game water usually uses alpha transparency rather than real refraction, because refraction is expensive. RusticEngine rebuilds the Noise + Bump; animated motion (scrolling the noise over time) is added in the engine's shader, since a Blender material doesn't know about game time. Ask Ember to make it flow.
**Done when:** The water reads as water in the viewport.

## Step 4: Shorelines and foam
**Build:** Foam where water meets land: paint a vertex color mask on the water mesh along the shores (Vertex Paint mode, white = foam) and mix a white color by it. In the game, foam can also come from depth (the engine can compare water depth to the ground behind it).
**You'll learn:** Shore foam and a darker depth color are what make stylized water look finished, even in very simple games.
**Done when:** The shoreline has a soft foam band.

## Step 5: Lava
**Build:** Opaque, mostly Emission. Noise Texture (Detail 8) > Color Ramp from black (crust) through deep red and orange to yellow-white (hottest) > Emission Color, Emission Strength 2-10. Use the same ramp's dark part as Base Color with high Roughness for the cooled crust. Make cracks sharper by squeezing the Color Ramp stops together.
**You'll learn:** **Black-body radiation**: hot things glow from dark red through orange and yellow to white as they heat up. Lava colors follow that order, so the brightest parts are yellow-white, never pure red. Slow motion sells lava: it flows like honey, and the crust drifts.
**Done when:** It glows like the black-body color order.

## Step 6: Realistic oceans and simulations (for renders and reference)
**Build:** Ocean modifier on a plane gives realistic wave shapes (and foam data), good for a still shoreline or a cinematic. Mantaflow (Physics > Fluid, a Domain plus a Flow object) simulates pouring, splashing liquid; bake it and render it for trailers, or study it as reference for timing.
**You'll learn:** Simulations are too heavy for gameplay. For a game, either bake a short simulation into a texture/flipbook or recreate the look with the shader approach above.
**Done when:** You know which of your liquids are shaders and which (if any) are pre-rendered effects.
