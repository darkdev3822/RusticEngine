# Studio how-to recipes
# Each recipe: "## title", then "tool:" (model or sound), "keys:" (words people use), then the verified steps.
# Checked against the real Studio: typed numbers are a size factor for S and I (0.6 = 60%), degrees for R,
# distance for G and E (negative E pushes in). New Shape replaces the whole model.

## Pointy top (spike, peak, point)
tool: model
keys: pointy point spike peak sharp top tip pyramid fence post pencil horn tooth
1. Press 1 for Vertices and select all the corners at the top (drag a box around them from the side, or Shift+click each).
2. Press M to merge them into one point. The top becomes a pyramid.
3. With that point still selected, G then Y and move it up (or type 0.3, Enter) for a taller spike.
Why: merging corners is the quickest way to a point; moving the point controls how sharp it is.

## Taper (thinner or wider at one end)
tool: model
keys: taper thinner narrower wider thicker top bottom end trunk leg bottle cone shrink one end
1. Press 1 for Vertices and select the ring of corners at the end you want to change (box-select from the side).
2. Press S and move the mouse in to shrink, out to grow (or type 0.6, Enter for 60%).
Why: scaling just one end's corners tapers the shape while the rest stays put.

## Tilt or rotate the whole model
tool: model
keys: tilt rotate turn spin lean angle whole model sideways upside face direction
1. Press 3 for Object mode (the whole model).
2. Press R, then the axis to turn around: Z tilts left/right, X tilts forward/back, Y spins it.
3. Type the angle in degrees (for example 10) and press Enter. Hold Ctrl instead to snap in 15-degree steps.
Why: typing an angle gives exact, repeatable rotations.

## Rotate or bend one part
tool: model
keys: rotate part bend angle one face arm leg branch twist turn piece
1. In Faces (2) select the faces of that part (or corners in Vertices (1)).
2. Press R, an axis (X, Y or Z), type degrees, Enter.
Why: rotation turns around the center of what's selected, so select only the part that should move.

## Resize the whole model
tool: model
keys: bigger smaller resize scale size huge tiny whole model shrink grow
1. Press 3 for Object mode.
2. Press S and type a factor: 0.5 halves it, 2 doubles it. Enter.
Why: 1 unit is about 1 meter in Godot, so check it against your player's height.

## Exact size along one direction
tool: model
keys: exact size meters units wide tall deep long stretch width height length measure precise
1. Press 3 for Object mode (or select the part).
2. Press S, then X (width), Y (height) or Z (depth), type the factor, Enter. Example: a 2-wide wall made 4 wide is S, X, 2, Enter.
Why: locking to an axis stretches in one direction only; asset_info tells you the current size.

## Narrower or wider part (shoulders, hips, waist)
tool: model
keys: narrower wider shoulders hips waist too wide too thick too thin slimmer broader width part
1. Press 1 for Vertices and select the outer corners of that part (box-select from the front view, numpad 1).
2. Press S, then X, and type a factor (0.8 = 20% narrower), Enter. Or G, X and move them in.
Why: with Mirror X on, the other side follows automatically.

## Window, panel or recess in a face
tool: model
keys: window panel recess hole indent frame plate keyhole screen vent porthole lock slit arrow slit loophole opening in wall
1. In Faces (2) click the face.
2. Press I (inset) and move toward the center, or type 0.6, Enter (the new face is 60% of the size). A border stays around it.
3. Press E and type -0.05, Enter to push it in (a positive number pulls it out, like a plate).
4. Paint it darker with P: dark reads as glass or depth.
Why: inset then extrude keeps a clean frame around the new part.

## Door (an opening that reaches the ground)
tool: model
keys: door doorway entrance gate opening arch ground floor
1. In Faces (2) select the wall and press D (subdivide) to split it into 4.
2. Select one of the bottom pieces and press I to inset it a little.
3. Press 1 for Vertices, select the inner face's two bottom corners, G, Y and move them down to the ground.
4. Back in Faces (2): E, -0.05, Enter pushes the door in. Paint it with P.
Why: inset can't reach an edge, so you split the face first, then move the corners.

## Something sticking out of part of a face (chimney, button, nose)
tool: model
keys: chimney button nose bump knob handle stick out protrude antenna tower part of a face
1. In Faces (2) select the face and press D (subdivide) to get smaller faces.
2. Select one small face, press I and make it the size you want.
3. Press E and pull it out (type a distance, e.g. 0.4, Enter).
Why: subdivide gives you a smaller face to grow from, inset gives it a clean edge.

## Limb (arm, leg, branch, tail)
tool: model
keys: arm leg branch tail limb neck wing foot hand add legs add arms
1. In Faces (2) select the face it grows from (side of the body for arms, bottom for legs).
2. Press I and inset it to limb size (type 0.5, Enter).
3. Press E and pull it out (type 0.3, Enter). Press E again for the next segment: two segments give an elbow or knee.
Why: extrude-move-extrude is how all limbs are built. With Mirror X on, build only one side.

## Side pieces on a thin object (sword crossguard, wings, ears)
tool: model
keys: crossguard guard hilt sword wings ears side pieces fins both sides
1. In Faces (2) select one narrow side face and press D to split it, then select the piece where the guard goes.
2. Press E and type 0.15, Enter.
3. Do the same on the other side separately. (Extruding two opposite faces at once cancels out; or turn on Mirror X and build one side.)
Why: the guard is just a short extrude from each side.

## Pointed roof (gable)
tool: model
keys: roof gable pointy roof slope house top attic ridge
1. In Faces (2) select the top face and press D (subdivide).
2. Press 1 for Vertices and select the middle line of points (front middle, center, back middle).
3. G, Y, move up (or type 0.8, Enter).
Why: lifting the middle line makes two slopes, a classic roof.

## Overhang, lip or brim
tool: model
keys: overhang lip brim ledge lid rim stick out on all sides roof edge hat table top
1. In Faces (2) select the top face, press E, type 0, Enter (a copy right in place).
2. Press S, type 1.1, Enter (the ring grows 10%: that's the lip).
3. Press E and type the height (e.g. 0.25), Enter.
Why: extrude always builds sides between old and new edges, so scaling in between makes a ledge.

## Paint colors
tool: model
keys: color colour paint different color walls roof parts palette recolor
1. In Faces (2) select the faces (Shift+click to add, or drag a box).
2. Click the color button in the toolbar and pick a color.
3. Press P.
Why: colors are per face. Keep 3-5 colors and use brightness contrast so parts read clearly.

## Natural, old or handmade look
tool: model
keys: natural old worn weathered rough organic irregular realistic boring perfect computer made rock random
1. Press 1 for Vertices, select a corner, G and nudge it a little. Repeat on a few corners, each a different amount.
2. Use duller, darker colors with P.
Why: small uneven changes read as natural; perfect symmetry reads as computer-made.

## Rounder shapes
tool: model
keys: round rounder smooth curved ball sphere soft circle
1. In Faces (2) select the faces and press D (subdivide).
2. In Vertices (1) select the new middle points and S to push them out a little.
Why: low-poly roundness comes from more sides. The Studio has no smooth shading yet; Blender (free) does.

## Layers or a waist (pine tree tiers, hourglass)
tool: model
keys: layers tiers pine two layers waist hourglass stacked rings bands levels
1. In Faces (2) select the side faces of that part and press D (subdivide): a ring of new points appears halfway up.
2. Press 1 for Vertices and box-select that middle ring from the side (numpad 3).
3. S, type 0.6, Enter pulls it in, so the shape looks like two stacked layers.
Why: subdivide adds the ring, scaling it in creates the step between layers.

## Fill a hole
tool: model
keys: hole missing face gap fill close open see through
1. Press 1 for Vertices and Shift+click the 3 or 4 corners around the hole, in order around the edge (numbers show the order).
2. Press F.
Why: Fill makes a face from the corners in the order you clicked.

## Face looks see-through or dark from outside
tool: model
keys: see through invisible inside out flipped wrong side dark face disappears
1. In Faces (2) select the face and click Flip in the toolbar.
2. If there's no face at all, fill the hole instead (Vertices, click corners in order, F).
Why: faces have a front and a back; a flipped face is invisible from outside.

## Join corners
tool: model
keys: join merge weld corners points vertices together combine connect
1. Press 1 for Vertices, Shift+click the corners.
2. Press M: they become one point in the middle.

## Delete part of the model
tool: model
keys: delete remove erase get rid cut off
1. Select faces (2) or corners (1), press X or Delete.
2. This leaves a hole; to close it, Vertices, click the corners in order, F.

## Symmetry with Mirror X
tool: model
keys: mirror symmetric symmetry both sides half character left right same
1. Turn on Mirror X in the toolbar and work only on the right half (X above 0).
2. Don't leave faces on the middle (X = 0): the halves join there.
Why: everything you do on one side appears on the other, in the viewport and the exported .glb.

## Selecting
tool: model
keys: select selection several many multiple all faces at once deselect box
- Shift+click adds to the selection. Drag a box on empty space to box-select what you can see. A selects all, Alt+A deselects.
- 1 Vertices, 2 Faces, 3 Object switches what you're selecting.

## Camera and views
tool: model
keys: camera view look around front side top orbit pan zoom see lost frame
- Middle mouse drag (or Alt + left drag) orbits, Shift + middle drag pans, wheel zooms, Home frames the model.
- Numpad 1 front, 3 side, 7 top: straight views are best for checking proportions.

## Undo and cancel
tool: model
keys: undo mistake messed up broke go back oops cancel redo
- Ctrl+Z undoes (100 steps), Ctrl+Shift+Z redoes. During G, R, S, E or I: Esc or right-click cancels.

## Starting shapes and adding parts
tool: model
keys: new shape start over cylinder sphere cone cube plane add another shape second part separate object
- New Shape (cube, cylinder, cone, sphere, plane) replaces the whole model: use it to start a new one.
- To add a part to this model, grow it from a face (I then E). For a separate object, save this model and make another; place both in your scene.

## Use the model in the game
tool: model
keys: game use export glb save scene place level put in
1. Ctrl+S saves the .rmodel and exports a .glb next to it.
2. Drag the .glb into a 3D scene. For collisions it needs a collision shape (Ember can set that up in code).

## Missing tools (bevel, loop cut, smooth, textures, animation)
tool: model
keys: bevel loop cut smooth shading texture uv animation rig bones sculpt boolean
- The Studio doesn't have these yet. Close substitutes: a small inset + extrude instead of a bevel, D (subdivide) instead of a loop cut.
- Blender (free) has all of them, and its .glb files import the same way.

## Louder or quieter
tool: sound
keys: loud louder quiet quieter volume hear barely too loud
1. Raise or lower Volume (0 to 1).
2. Punch (0.3-0.6) makes it feel louder at the start without raising the whole sound.
3. Watch the peak % next to Play: under about 90% avoids distortion.
Why: in the game, keep sounds at similar loudness and fine-tune with the AudioStreamPlayer's volume_db.

## Softer, less harsh
tool: sound
keys: soft softer harsh less harsh gentle smooth mellow muffled annoying piercing sharp
1. Low-pass to about 2000 Hz (lower = softer).
2. Lower Punch, and try a Sine or Triangle wave instead of Square or Saw.
3. For noise sounds (steps, hits), a lower Start pitch makes them deeper and less hissy.
Why: harshness is mostly high frequencies; the low-pass removes them.

## Shorter or snappier
tool: sound
keys: short shorter snappy snappier quick fast too long drags tight responsive goes on forever endless never ends
1. Decay down (0.05-0.1 s) and Sustain down.
2. For falling sounds, raise Stop below so it ends before the low part.
Why: sounds for frequent actions should end before they can repeat.

## Longer, ringing tail
tool: sound
keys: longer ring tail echo sustain last linger bell boom rumble
1. Decay up (0.5-1 s) for a tail; Sustain up to hold full volume longer.

## Higher or lower pitch
tool: sound
keys: pitch higher lower deeper bigger smaller heavier lighter bass squeaky
1. Start pitch: lower Hz sounds bigger and heavier, higher sounds smaller and lighter. Doubling the Hz is one octave up.

## Rising or falling sound
tool: sound
keys: rise rising fall falling slide up down sweep jump powerup laser drop
1. Slide: positive rises (jumps, power-ups), negative falls (lasers, hits, losing). In octaves per second.
2. Slide curve bends it; Stop below ends a falling sound at a pitch.

## Coin or reward "ding"
tool: sound
keys: coin ding reward collect pickup sparkle satisfying chime
1. Pitch jump +7 or +12 semitones, Jump after about 0.05 s.
2. Short Sustain, Decay around 0.2-0.3 s, a little Punch.
Why: +7 and +12 sound musical; the jump up feels like a reward.

## Distant, muffled or underwater
tool: sound
keys: distant far away muffled underwater behind wall dull
1. Low-pass around 800 Hz; Low-pass sweep negative (e.g. -2) for a rumble that fades away.
2. Less Punch.

## Thin, tiny or radio-like
tool: sound
keys: thin tiny small radio phone tinny ui click less bass
1. High-pass (300-1000 Hz) removes the low end.

## Wobble, alarm or trill
tool: sound
keys: wobble vibrato alarm siren trill warble shake tremble repeat
1. Vibrato depth (semitones) and speed (Hz): 5-7 Hz is singer-like, 15+ is an alarm.
2. Repeat every (0.05-0.2 s) restarts the pitch over and over for trills and power-ups.

## Fade in or swell
tool: sound
keys: fade in swell slow start build up magic wind charge
1. Attack up (0.1-0.5 s): it fades in instead of starting instantly.

## Punchy impact
tool: sound
keys: punchy impact hit hard strong weak powerful
1. Attack 0, Punch 0.4-0.8, short Decay.
2. Noise or Square wave, Start pitch lower for heavier hits.

## Footsteps
tool: sound
keys: footstep footsteps step walking walk run steps
1. Noise wave, Start pitch 300-900 Hz, Sustain about 0.02 s, Decay 0.06-0.1 s.
2. Low-pass around 3000 Hz to soften it.
Why: in the game, a random pitch_scale (0.9-1.1) on each step stops it sounding robotic.

## Variations and trying ideas
tool: sound
keys: variation different another random new idea mutate presets start over
- Press a preset again for another variation, Mutate for small random changes, Undo to go back.

## Retro or smooth character
tool: sound
keys: retro 8-bit chiptune nes smooth modern wave square saw sine triangle noise duty
- Square is classic 8-bit (Square duty below 0.5 sounds thinner, NES-like), Saw bright, Sine soft, Triangle round, Noise for hits and explosions.

## Distorted or crackling
tool: sound
keys: distorted distortion crackle clipping crunchy broken loud peak
1. Lower Volume or Punch until the peak % is under about 90%.

## Use the sound in the game
tool: sound
keys: game use wav save export play hook up player
1. Save writes the .rsfx and a .wav next to it.
2. Play the .wav with an AudioStreamPlayer (2D/3D for sounds from a place in the world). Ember can hook it up in code.

## Start a new sprite or tile
tool: pixel
keys: new start begin size canvas blank empty 16x16 32x32 character item tile icon
1. New, then pick a size: 16x16 for characters, items and tiles (the classic size), 8x8 for tiny icons, 16x24 for a taller character, 32x32 when you need more detail.
2. Keep one pixel size for the whole game so everything looks like it belongs together.

## Make the canvas bigger or smaller
tool: pixel
keys: resize bigger smaller canvas size room space expand grow shrink
1. Canvas menu, then a size (8x8 up to 128x128). Your art stays in the middle.
2. Undo (Ctrl+Z) if it cut something off.

## Draw and erase
tool: pixel
keys: draw paint pencil erase eraser delete remove pixel pixels mistake undo
1. Pencil (B): left mouse draws with your left color, right mouse with your right color. The right color starts transparent, so right-drag erases.
2. Eraser (E) makes pixels transparent with either button.
3. Undo is Ctrl+Z, Redo is Ctrl+Shift+Z.

## Pick and change colors
tool: pixel
keys: color colour change pick choose swatch palette edit hue recolor picker eyedropper
1. Left-click a swatch for the left-mouse color, right-click one for the right-mouse color. The checkered slot is transparent.
2. Click the color box under the swatches to change the selected color: every pixel that uses it changes too.
3. Pick Color (I), or Alt-click with any tool, grabs a color from the canvas.
4. + Color adds a copy of the selected color to change.

## Try a different palette or recolor the whole sprite
tool: pixel
keys: palette preset recolor swap mood dark bright forest dungeon gameboy grayscale enemy variant variation version team blue red green yellow purple pink orange
1. Choose a palette in the list under Palette (Starter 16, Forest, Dungeon, Grayscale, Four Greens). The sprite keeps its pixels and takes the new colors.
2. For an enemy variant, Save, then change a few colors with the color box and Save under a new name.

## Fill an area
tool: pixel
keys: fill bucket flood area inside color in paint whole region
1. Fill (G), then click inside an area: it fills the connected pixels of that one color (not through diagonal gaps).
2. If it leaks out, the outline has a gap: Undo, close the gap with Pencil, fill again.
3. Shift-click with Fill replaces that color everywhere in every frame.

## Straight lines, boxes and circles
tool: pixel
keys: line straight rectangle box square circle ellipse oval round shape filled head body ball eye eyes
1. Line (L), Rectangle (R) or Ellipse (O): drag from one corner to the other.
2. Hold Shift while dragging for a filled rectangle or ellipse.
3. Small circles look best with odd sizes (5, 7, 9 pixels across) because they have a center pixel.

## Clean lines and jaggies
tool: pixel
keys: jaggies jagged messy lines clean smooth stairs steps edges rough
1. Clean pixel lines go in equal steps: 1:1 (diagonal), 2:1, 3:1. Uneven steps (2, then 1, then 3) look jagged.
2. Zoom in (scroll wheel) with Grid on and fix steps with Pencil; right-drag erases the extra pixels.
3. Remove lone pixels that stick out of a line ("orphan" pixels).

## Symmetry with Mirror
tool: pixel
keys: mirror symmetry symmetric both sides half same left right
1. Turn on Mirror (M): everything you draw is copied to the other half, around the line in the middle.
2. When the base is done, turn Mirror off and add small differences so it doesn't look stiff.

## Shading and volume
tool: pixel
keys: shading shade shadow highlight light volume flat 3d depth lighting
1. Pick one light direction (top-left is the convention).
2. For each material use 2-3 colors: base, a darker shadow on the side away from the light, a lighter highlight facing it.
3. Shift the hue: shadows a bit bluer or purpler, highlights a bit yellower. Change slots with the color box or add some with + Color.
4. Avoid darkening every edge evenly ("pillow shading"); it looks flat.

## Outline
tool: pixel
keys: outline border edge pop readable background stand out contrast
1. A dark outline keeps small sprites readable on busy backgrounds: trace the edge with Pencil or Line in your darkest color.
2. For a softer look, outline each part with a darker shade of its own color instead (selective outline).

## Make it readable (silhouette)
tool: pixel
keys: readable silhouette shape recognize tell unclear blob confusing small
1. Check the Preview at actual size: if it's hard to tell what it is, fix the shape before the details.
2. Exaggerate what identifies it: a bigger head, a hat, a weapon sticking out, a clear pose.
3. Use fewer colors with stronger contrast between neighbors.

## Flip or face the other way
tool: pixel
keys: flip mirror face facing direction turn left right upside down reverse
1. Canvas menu > Flip Left/Right flips the current frame (Flip Upside Down for vertical).
2. In the game you can also flip a Sprite2D with its Flip H property instead of drawing both directions.

## Animation frames
tool: pixel
keys: animate animation frames frame walk idle bounce move cycle onion play fps speed spin spinning flicker blink sparkle wave flap run
1. Copy (under Frames) duplicates the frame; change only what moves (body 1 pixel down, legs swapped).
2. Turn on Onion Skin to see the previous frame faintly while you draw.
3. Press Play to watch it; set fps (6-12 is typical for pixel art). Reorder with < and >, remove with Delete.
4. 2-4 frames are enough for an idle bounce or a simple walk.

## Seamless tiles
tool: pixel
keys: tile tiles seamless repeat repeating floor wall ground grass seam tileset pattern
1. Turn on Tile View to see copies around the canvas.
2. Canvas menu > Shift by Half moves the edges into the middle: paint over any seam you see, then Shift by Half again.
3. Avoid strong single details that make the repeat obvious.

## Use the sprite in the game
tool: pixel
keys: game use png save export scene sprite2d hframes animatedsprite tileset blurry blur sharp nearest filter
1. Save writes the .rpix and a .png next to it, with all frames side by side.
2. In a 2D scene use a Sprite2D with that .png; for animation set Hframes to the frame count and change Frame (Ember can write the code).
3. If it looks blurry, set Project Settings > Rendering > Textures > Canvas Textures > Default Texture Filter to Nearest.

## Missing tools (layers, selection, brushes, dithering)
tool: pixel
keys: layer layers select selection copy paste move brush size dither dithering gradient text rotate
1. The Pixel Art painter has no layers, selection, brush sizes or rotation yet.
2. Workarounds: Shift by Half moves everything (wrapping), Flip mirrors, Copy duplicates a frame. Dithering is a checker pattern of two colors, drawn with Pencil.
3. For bigger jobs, free tools like Pixelorama or LibreSprite work, and their .png files import straight into the project.
