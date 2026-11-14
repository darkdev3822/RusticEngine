# Art Path: an animated character in Blender (rig, skin, animate, play it in the game)
A character is a mesh moved by a skeleton. The skeleton (an **armature** made of **bones**) is the puppet's wooden frame, the mesh is the cloth over it, and **weights** say how strongly each bone pulls each vertex. Animations (Blender **actions**) are bone poses over time. RusticEngine brings all of it over: bones, skinning, every action as an animation (looping when the action is Cyclic), and shape keys for faces. Look up 'Skeletal animation', 'Inverse kinematics', 'Morph target animation' and 'Walk cycle' with blender_help. Free CC0 characters to study: Quaternius and Kenney (rigged and animated, no credit needed).

## Step 1: A body that bends well
**Design question:** What does your character do most: walk, swing a sword, talk? Joints that move a lot need geometry ready to bend.
**Build:** Model in a T-pose or A-pose (arms out, A-pose bends shoulders better), facing -Y (Blender's front view, numpad 1), feet on the ground at the origin. Use a Mirror modifier and model one half. Put **edge loops** around every joint: at least 3 around elbows and knees (Ctrl+R), more at shoulders and hips. Apply scale (Ctrl+A > Scale).
**You'll learn:** A joint bends by moving its loops; with one loop it collapses like a bent straw, with three it keeps its volume. Loops that follow the muscles deform naturally. Polygon budget for a game character: 2k-15k triangles.
**Try it yourself:** Before rigging, guess where your mesh will crease when the elbow bends 90 degrees. Check it in Step 4.
**Done when:** Every joint has 3+ loops and the character stands at the origin with scale 1.

## Step 2: The skeleton
**Build:** Shift+A > Armature (one bone). Tab into Edit Mode and grow the skeleton from the hips: select a bone's tip and press **E** to extrude the next bone (spine, chest, neck, head; then from the chest, shoulder, upper arm, forearm, hand; hips to thigh, shin, foot, toe). Name every bone (F2) with .L/.R suffixes (upper_arm.L), build one side, then select its bones and Armature > Symmetrize. Shift+N recalculates bone roll if arms twist oddly. In Object Data properties > Viewport Display, In Front shows bones through the mesh.
**You'll learn:** Bones form a hierarchy: moving a parent moves its children (the hand follows the forearm). The .L/.R names are what lets Blender mirror poses and weights. Roll is the twist of a bone around its length; consistent rolls make rotations predictable.
**Done when:** The skeleton fits inside the mesh with joints at the elbows and knees, and the names mirror.

## Step 3: Skinning (bind the mesh to the bones)
**Build:** Object Mode: click the mesh, Shift+click the armature (armature last = active), **Ctrl+P > With Automatic Weights**. Then select the armature, Ctrl+Tab (mode pie) > Pose Mode, and rotate bones (R) to test. To fix bad areas: Object Mode, click the armature, Shift+click the mesh (mesh active), Ctrl+Tab > Weight Paint. Ctrl+click a bone to pick its group; paint with left click, Ctrl+click subtracts, Shift+click smooths, Shift+X samples a weight. Turn on X-Mirror in the tool header to paint both sides.
**You'll learn:** Each vertex stores a weight per bone (0-1); its final position is the weighted mix of where each bone would take it. Games limit this to 4 bones per vertex; Weights > Limit Total (4) keeps it game-ready. Red = fully follows, blue = ignores.
**Try it yourself:** Paint a vertex half on the forearm and half on the upper arm, predict where it sits when the elbow bends, then bend it.
**Done when:** Bending each joint 90 degrees has no spikes, no torn faces and no collapsed elbows.

## Step 4: Posing
**Build:** In Pose Mode: G/R/S move bones, Alt+G / Alt+R / Alt+S clear them back to rest. Copy a pose with Ctrl+C and paste it mirrored with Ctrl+Shift+V (that's why the .L/.R names matter). For legs and arms, add an IK constraint (Bone Constraint properties > Inverse Kinematics) on the shin with a target bone at the foot: move the foot and the knee follows.
**You'll learn:** **FK** (forward kinematics) rotates each bone down the chain; **IK** (inverse kinematics) solves the chain from where the end should be. Feet planted on the ground need IK. Helper bones like IK targets don't need to deform the mesh: untick Deform in their Bone properties.
**Done when:** You can pose a believable crouch and a reach without the mesh breaking.

## Step 5: Your first animation: an idle
**Build:** Open the Animation workspace (tab at the top). Select all bones (A), press **I** to key the rest pose at frame 1. Go to frame 30, move the chest down a little and the arms slightly, press I. Copy frame 1's keys to frame 60 (in the Dope Sheet: select the column, Ctrl+C, go to 60, Ctrl+V). Play with Space. In the Dope Sheet's Action editor, name the action Idle, and in the Action properties tick Manual Frame Range and **Cyclic Animation**.
**You'll learn:** Keys are poses; Blender fills the frames between them (interpolation curves, seen in the Graph Editor). A loop's last pose must equal its first. Cyclic Animation is Blender's own loop flag, and RusticEngine reads it: the animation loops in the game (the RusticEngine panel shows a Loop box per action too).
**Done when:** The idle loops with no visible jump.

## Step 6: A walk cycle
**Build:** New action (the + next to the action name), named Walk, 24 frames. Key the 4 classic poses: **contact** (frame 1: heel down in front, other foot behind), **down** (frame 4: weight sinks), **passing** (frame 7: legs pass, body highest), **up** (frame 10), then the mirror of the first half from frame 13 (Ctrl+C a pose, Ctrl+Shift+V paste flipped). Frame 25 = frame 1. Arms swing opposite to the legs. Tick Cyclic Animation.
**You'll learn:** A walk is a controlled fall: the body is lowest just after contact and highest at passing. Animate it in place: the game moves the character, and the animation's speed must match the movement speed (stride length per cycle) or the feet slide.
**Try it yourself:** Before playing it, predict which frame the head is highest.
**Done when:** It loops smoothly and the planted foot doesn't slide backwards in place.

## Step 7: Faces with shape keys
**Build:** Select the head mesh, Object Data properties > Shape Keys > + (Basis first, then e.g. Smile, Blink.L). Pick Smile, Tab, move the mouth corners, Tab back; its Value slider blends it in. Key the slider (hover, I) to animate it.
**You'll learn:** A shape key is a whole copy of the vertex positions; the engine blends between them (blend shapes / morph targets). Good for faces and squash, bad for big motions (that's what bones are for). Keep the vertex count the same once you have shape keys.
**Done when:** A blink and a smile blend in and out.

## Step 8: Into the game
**Build:** Export to RusticEngine (or Live Link + Ctrl+S). Keep Deform Bones Only on in the RusticEngine panel: the game gets just the bones that move the mesh, and IK and controls are baked into the animation. Ask Ember about the .glb: it lists bones, shape keys and which animations loop. In the game, the model's AnimationPlayer child plays them by name ("Walk", "Idle").
**You'll learn:** Animations arrive at your scene's frame rate starting at 0 seconds, and the engine sets looping from Blender's Cyclic flag. For blending between idle, walk and run, add the **Animated Character** starter (Mechanics tab > Add Mechanic): put its CharacterAnimator under your character and it plays Idle/Walk/Run/Fall by itself, blended by how fast the body really moves. Give your walk and run **root motion** (a root bone that travels forward; Root Motion in the panel's Animations box) and it measures their speeds itself, so the feet never slide. Blender's front (-Y) faces +Z in the game: turn the model 180 degrees under the player (or face +Y in Blender).
**Done when:** Your character idles in the game and walks when you play Walk.
