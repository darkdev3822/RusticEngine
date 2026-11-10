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
