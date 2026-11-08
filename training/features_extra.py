"""More gold features for Ember's training data (round 2): broader mechanics, scene-only edits,
and scene mistakes the agent's .tscn checker catches. Deliberately avoids the eval_agent.py tasks
(hold-to-grow, second player, edge bounce, fade-in, pause, periodic print, shake, mouse follow).
"""

MOVE = '''        let input = Input::singleton();
        let direction = input.get_vector("ui_left", "ui_right", "ui_up", "ui_down");
        let step = direction * self.speed * delta as f32;
        let position = self.base().get_position();
        self.base_mut().set_position(position + step);'''

BASE_SCENE_HEAD = '''[gd_scene format=3]

[ext_resource type="Texture2D" path="res://icon.svg" id="1_icon"]

[node name="Main" type="Node2D"]

[node name="Player" type="Player" parent="."]
position = Vector2(576, 324)

[node name="Sprite2D" type="Sprite2D" parent="Player"]
texture = ExtResource("1_icon")
'''

RAINBOW = '''use godot::classes::{INode2D, Input, Node2D};
use godot::prelude::*;

/// Moves with the arrow keys and slowly cycles through the colors of the rainbow.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Player {
    #[export]
    speed: f32,
    /// Rainbow cycles per second.
    #[export]
    color_speed: f32,
    hue: f32,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Player {
    fn init(base: Base<Node2D>) -> Self {
        Self { speed: 300.0, color_speed: 0.25, hue: 0.0, base }
    }

    fn process(&mut self, delta: f64) {
''' + MOVE + '''

        // Hue goes 0 -> 1 around the color wheel, then wraps back to 0.
        self.hue = (self.hue + self.color_speed * delta as f32).fract();
        let color = Color::from_hsv(self.hue as f64, 0.6, 1.0);
        self.base_mut().set_modulate(color);
    }
}
'''

RAINBOW_MISTAKE = RAINBOW.replace("Color::from_hsv(self.hue as f64, 0.6, 1.0)", "Color::from_hsv(self.hue, 0.6, 1.0)")

SMOOTH = '''use godot::classes::{INode2D, Input, Node2D};
use godot::prelude::*;

/// Speeds up and slows down smoothly instead of starting and stopping instantly.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Player {
    /// Top speed in pixels per second.
    #[export]
    speed: f32,
    /// How quickly it reaches top speed (higher = snappier).
    #[export]
    acceleration: f32,
    velocity: Vector2,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Player {
    fn init(base: Base<Node2D>) -> Self {
        Self { speed: 300.0, acceleration: 900.0, velocity: Vector2::ZERO, base }
    }

    fn process(&mut self, delta: f64) {
        let dt = delta as f32;
        let direction = Input::singleton().get_vector("ui_left", "ui_right", "ui_up", "ui_down");
        let target = direction * self.speed;
        // Move the current velocity a little toward the target each frame.
        self.velocity = self.velocity.move_toward(target, self.acceleration * dt);
        let target_position = self.base().get_position() + self.velocity * dt;
        self.base_mut().set_position(target_position);
    }
}
'''

SMOOTH_MISTAKE = SMOOTH.replace("self.velocity.move_toward(target, self.acceleration * dt)",
                                "self.velocity.move_toward(target, self.acceleration * delta)")

GRID = '''use godot::classes::{INode2D, Input, Node2D};
use godot::prelude::*;

/// Moves one tile per key press, like a board game or a classic puzzle game.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Player {
    /// Size of one step in pixels.
    #[export]
    tile_size: f32,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Player {
    fn init(base: Base<Node2D>) -> Self {
        Self { tile_size: 64.0, base }
    }

    fn process(&mut self, _delta: f64) {
        let input = Input::singleton();
        let mut step = Vector2::ZERO;
        // "just pressed" is true only on the frame the key goes down, so holding it moves once.
        if input.is_action_just_pressed("ui_left") { step.x -= 1.0; }
        if input.is_action_just_pressed("ui_right") { step.x += 1.0; }
        if input.is_action_just_pressed("ui_up") { step.y -= 1.0; }
        if input.is_action_just_pressed("ui_down") { step.y += 1.0; }
        if step != Vector2::ZERO {
            // Work out the new spot first, then change the node (Rust won't let us do both at once).
            let target = self.base().get_position() + step * self.tile_size;
            self.base_mut().set_position(target);
        }
    }
}
'''

FACE = '''use godot::classes::{INode2D, Input, Node2D};
use godot::prelude::*;

/// Moves with the arrow keys and turns to face the way it's going.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Player {
    #[export]
    speed: f32,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Player {
    fn init(base: Base<Node2D>) -> Self {
        Self { speed: 300.0, base }
    }

    fn process(&mut self, delta: f64) {
''' + MOVE + '''

        // Only turn while moving, so it keeps facing the last direction when you let go.
        if direction.length() > 0.0 {
            self.base_mut().set_rotation(direction.angle());
        }
    }
}
'''

RESTART = '''use godot::classes::{INode2D, Input, Node2D};
use godot::global::Key;
use godot::prelude::*;

#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Player {
    #[export]
    speed: f32,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Player {
    fn init(base: Base<Node2D>) -> Self {
        Self { speed: 300.0, base }
    }

    fn ready(&mut self) {
        godot_print!("Arrow keys to move, R to restart.");
    }

    fn process(&mut self, delta: f64) {
''' + MOVE + '''

        if input.is_key_pressed(Key::R) {
            // Start the whole scene over, exactly like pressing Play again.
            self.base().get_tree().reload_current_scene();
        }
    }
}
'''

RESTART_MISTAKE = RESTART.replace("self.base().get_tree().reload_current_scene();",
                                  "self.base().get_tree().unwrap().reload_current_scene();")

TELEPORT = '''use godot::classes::{INode2D, Input, Node2D};
use godot::global::{randf_range, Key};
use godot::prelude::*;

/// Press T to teleport somewhere random on the screen.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Player {
    #[export]
    speed: f32,
    t_was_down: bool,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Player {
    fn init(base: Base<Node2D>) -> Self {
        Self { speed: 300.0, t_was_down: false, base }
    }

    fn process(&mut self, delta: f64) {
''' + MOVE + '''

        // Teleport once per press: only when T goes from "up" to "down".
        let t_down = input.is_key_pressed(Key::T);
        if t_down && !self.t_was_down {
            let size = self.base().get_viewport_rect().size;
            let x = randf_range(0.0, size.x as f64) as f32;
            let y = randf_range(0.0, size.y as f64) as f32;
            self.base_mut().set_position(Vector2::new(x, y));
        }
        self.t_was_down = t_down;
    }
}
'''

TELEPORT_MISTAKE = TELEPORT.replace("let x = randf_range(0.0, size.x as f64) as f32;", "let x = randf_range(0.0, size.x);")

SLOWMO = '''use godot::classes::{Engine, INode2D, Input, Node2D};
use godot::global::Key;
use godot::prelude::*;

/// Hold Z for slow motion.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Player {
    #[export]
    speed: f32,
    /// 1.0 = normal speed, 0.3 = the world runs at 30%.
    #[export]
    slow_factor: f64,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Player {
    fn init(base: Base<Node2D>) -> Self {
        Self { speed: 300.0, slow_factor: 0.3, base }
    }

    fn process(&mut self, delta: f64) {
''' + MOVE + '''

        // time_scale slows down everything in the game, not just the player.
        let scale = if input.is_key_pressed(Key::Z) { self.slow_factor } else { 1.0 };
        Engine::singleton().set_time_scale(scale);
    }
}
'''

HIDE = '''use godot::classes::{INode2D, Input, Node2D};
use godot::global::Key;
use godot::prelude::*;

/// Press H to hide or show the player (like a ghost mode).
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Player {
    #[export]
    speed: f32,
    h_was_down: bool,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Player {
    fn init(base: Base<Node2D>) -> Self {
        Self { speed: 300.0, h_was_down: false, base }
    }

    fn process(&mut self, delta: f64) {
''' + MOVE + '''

        let h_down = input.is_key_pressed(Key::H);
        if h_down && !self.h_was_down {
            let visible = self.base().is_visible();
            self.base_mut().set_visible(!visible);
        }
        self.h_was_down = h_down;
    }
}
'''

PULSE = '''use godot::classes::{INode2D, Input, Node2D};
use godot::prelude::*;

/// Moves with the arrow keys and gently "breathes": growing and shrinking a little, forever.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Player {
    #[export]
    speed: f32,
    /// How much bigger it gets at the top of a breath (0.1 = 10%).
    #[export]
    pulse_amount: f32,
    /// Breaths per second.
    #[export]
    pulse_speed: f32,
    time: f32,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Player {
    fn init(base: Base<Node2D>) -> Self {
        Self { speed: 300.0, pulse_amount: 0.1, pulse_speed: 1.0, time: 0.0, base }
    }

    fn process(&mut self, delta: f64) {
''' + MOVE + '''

        self.time += delta as f32;
        // sin() swings between -1 and 1, so the size swings between 90% and 110%.
        let wave = (self.time * self.pulse_speed * std::f32::consts::TAU).sin();
        let size = 1.0 + wave * self.pulse_amount;
        self.base_mut().set_scale(Vector2::new(size, size));
    }
}
'''

NAME_TAG_SCENE = BASE_SCENE_HEAD + '''
[node name="NameTag" type="Label" parent="Player"]
offset_left = -60.0
offset_top = -90.0
offset_right = 60.0
offset_bottom = -64.0
text = "Hero"
horizontal_alignment = 1
'''
NAME_TAG_SCENE_MISTAKE = NAME_TAG_SCENE.replace('parent="Player"]\noffset_left', 'parent="Main/Player"]\noffset_left')

MOON = '''use godot::classes::{INode2D, Node2D};
use godot::prelude::*;

/// Circles around its parent node, like a moon around a planet.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Moon {
    /// Distance from the center in pixels.
    #[export]
    radius: f32,
    /// Turns per second (negative = the other way).
    #[export]
    orbit_speed: f32,
    angle: f32,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Moon {
    fn init(base: Base<Node2D>) -> Self {
        Self { radius: 90.0, orbit_speed: 0.5, angle: 0.0, base }
    }

    fn process(&mut self, delta: f64) {
        self.angle += self.orbit_speed * std::f32::consts::TAU * delta as f32;
        // A child's position is relative to its parent, so this circles the player.
        let offset = Vector2::from_angle(self.angle) * self.radius;
        self.base_mut().set_position(offset);
    }
}
'''

MOON_SCENE = BASE_SCENE_HEAD + '''
[node name="Moon" type="Moon" parent="Player"]

[node name="Sprite2D" type="Sprite2D" parent="Player/Moon"]
modulate = Color(0.8, 0.85, 1, 1)
scale = Vector2(0.3, 0.3)
texture = ExtResource("1_icon")
'''
MOON_SCENE_MISTAKE = MOON_SCENE.replace('texture = ExtResource("1_icon")\n', 'texture = ExtResource("2_moon")\n', 2).replace(
    'texture = ExtResource("2_moon")\n', 'texture = ExtResource("1_icon")\n', 1)

STOPWATCH = '''use godot::classes::{ILabel, Label};
use godot::prelude::*;

/// A label that counts up the seconds since the game started.
#[derive(GodotClass)]
#[class(base = Label)]
pub struct Stopwatch {
    time: f64,
    base: Base<Label>,
}

#[godot_api]
impl ILabel for Stopwatch {
    fn init(base: Base<Label>) -> Self {
        Self { time: 0.0, base }
    }

    fn process(&mut self, delta: f64) {
        self.time += delta;
        // {:.1} shows one digit after the decimal point: "Time: 12.3"
        let text = format!("Time: {:.1}", self.time);
        self.base_mut().set_text(&text);
    }
}
'''

STOPWATCH_SCENE = BASE_SCENE_HEAD + '''
[node name="UI" type="CanvasLayer" parent="."]

[node name="Stopwatch" type="Stopwatch" parent="UI"]
offset_left = 20.0
offset_top = 16.0
offset_right = 220.0
offset_bottom = 48.0
theme_override_font_sizes/font_size = 24
text = "Time: 0.0"
'''
STOPWATCH_SCENE_MISTAKE = STOPWATCH_SCENE.replace('[node name="UI" type="CanvasLayer" parent="."]\n\n', '')

SPIKES = '''use godot::classes::{Area2D, IArea2D, Node2D};
use godot::prelude::*;

use crate::player::Player;

/// Touching this sends the player back to the start.
#[derive(GodotClass)]
#[class(base = Area2D)]
pub struct Spikes {
    base: Base<Area2D>,
}

#[godot_api]
impl IArea2D for Spikes {
    fn init(base: Base<Area2D>) -> Self {
        Self { base }
    }

    fn ready(&mut self) {
        self.signals().body_entered().connect_self(Self::on_body_entered);
    }
}

#[godot_api]
impl Spikes {
    fn on_body_entered(&mut self, body: Gd<Node2D>) {
        if body.try_cast::<Player>().is_ok() {
            godot_print!("Ouch! Back to the start.");
            // Restart after the physics step finishes; changing scenes in the middle of it isn't allowed.
            self.base().get_tree().call_deferred("reload_current_scene", &[]);
        }
    }
}
'''

SPIKES_SCENE = '''[gd_scene format=3]

[ext_resource type="Texture2D" path="res://icon.svg" id="1_icon"]

[sub_resource type="CircleShape2D" id="CircleShape2D_player"]
radius = 28.0

[sub_resource type="RectangleShape2D" id="RectangleShape2D_spikes"]
size = Vector2(120, 40)

[node name="Main" type="Node2D"]

[node name="Player" type="Player" parent="."]
position = Vector2(576, 324)

[node name="Sprite2D" type="Sprite2D" parent="Player"]
scale = Vector2(0.5, 0.5)
texture = ExtResource("1_icon")

[node name="CollisionShape2D" type="CollisionShape2D" parent="Player"]
shape = SubResource("CircleShape2D_player")

[node name="Spikes" type="Spikes" parent="."]
position = Vector2(900, 500)

[node name="ColorRect" type="ColorRect" parent="Spikes"]
offset_left = -60.0
offset_top = -20.0
offset_right = 60.0
offset_bottom = 20.0
color = Color(0.85, 0.2, 0.2, 1)

[node name="CollisionShape2D" type="CollisionShape2D" parent="Spikes"]
shape = SubResource("RectangleShape2D_spikes")
'''
SPIKES_SCENE_MISTAKE = SPIKES_SCENE.replace('''[sub_resource type="RectangleShape2D" id="RectangleShape2D_spikes"]
size = Vector2(120, 40)

''', '')

TINT = '''use godot::classes::{INode2D, Input, Node2D};
use godot::prelude::*;

#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Player {
    #[export]
    speed: f32,
    /// Pick the player's color in the Inspector.
    #[export]
    tint: Color,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Player {
    fn init(base: Base<Node2D>) -> Self {
        Self { speed: 300.0, tint: Color::from_rgb(0.4, 0.8, 1.0), base }
    }

    fn ready(&mut self) {
        let tint = self.tint;
        self.base_mut().set_modulate(tint);
    }

    fn process(&mut self, delta: f64) {
''' + MOVE + '''
    }
}
'''

FEATURES = {}

FEATURES["rainbow"] = dict(
    prompts=["make my player change colors like a rainbow", "can the character cycle through colors?",
             "rainbow mode for the player pls", "I want the player to glow different colors over time",
             "make the player colorful, slowly changing color"],
    files={"rust/src/player.rs": RAINBOW}, run=2,
    intro=["Rainbow mode, yes! Let me check the player code first.", "Ooh, colorful! Let me look at how the player works now."],
    final=["Your player now slowly travels around the color wheel: red, yellow, green, blue, purple, and back to red. "
           "I used `set_modulate`, which tints a node and everything inside it.\n\nPress **Play** (F5) to see it. "
           "Change **Color Speed** in the Inspector to make it faster or calmer.\n\nIdea: what if it only went rainbow while you held a key, like a power-up?",
           "Rainbow mode is on! Every frame the player's hue moves a little further around the color wheel.\n\n"
           "Press **Play** (F5) and watch. **Color Speed** in the Inspector controls how fast the colors change."],
    mistake={"rust/src/player.rs": RAINBOW_MISTAKE},
    mistake_note="Rust caught a type mix-up: `hue` is an `f32`, but `Color::from_hsv` wants `f64` numbers. I'll convert it with `as f64`.",
)

FEATURES["smooth_movement"] = dict(
    prompts=["the movement feels stiff, can it speed up and slow down smoothly?", "add acceleration to the player",
             "make the player slide a bit like it's on ice", "movement should feel smoother",
             "I want momentum when I move"],
    files={"rust/src/player.rs": SMOOTH}, run=2,
    intro=["Smooth movement makes a huge difference in how a game feels. Let me see the current code.",
           "Good call, momentum feels great. Let me look at the player."],
    final=["Now the player has momentum: it speeds up when you press a key and glides to a stop when you let go. "
           "I keep a `velocity` and nudge it toward the target speed each frame with `move_toward`.\n\n"
           "Press **Play** (F5) to feel it. Lower **Acceleration** in the Inspector for an icy, slidey feel, or raise it for snappy controls.",
           "Movement is smooth now! Instead of jumping straight to full speed, the player builds up speed and slows down gradually.\n\n"
           "Try it with **Play** (F5), then play with **Acceleration** in the Inspector until it feels just right."],
    mistake={"rust/src/player.rs": SMOOTH_MISTAKE},
    mistake_note="Small slip: `delta` is an `f64`, but the vector math uses `f32`. I already made `dt` (the `f32` version), so I'll use that.",
)

FEATURES["grid_move"] = dict(
    prompts=["make the player move one square at a time", "tile based movement like a board game",
             "I want grid movement, one step per key press", "the player should jump one tile per arrow press"],
    files={"rust/src/player.rs": GRID}, run=2,
    intro=["Grid movement, classic! Let me look at the player first.", "One step at a time, like a puzzle game. Let me check the code."],
    final=["Now each arrow press moves the player exactly one tile (64 pixels). Holding a key doesn't keep moving: "
           "`is_action_just_pressed` is only true on the frame the key goes down.\n\nPress **Play** (F5) and tap the arrows. "
           "Change **Tile Size** in the Inspector to make the steps bigger or smaller.\n\nIdea: add walls on the grid and you've got the start of a puzzle game!"],
)

FEATURES["face_direction"] = dict(
    prompts=["make the player turn to face where it's moving", "the player should point in the direction it goes",
             "rotate the character toward its movement", "can it look where it's going?"],
    files={"rust/src/player.rs": FACE}, run=2,
    intro=["Facing the way you move makes it feel alive. Let me look at the code."],
    final=["The player now turns to face the direction it's moving. `direction.angle()` gives the angle of the arrow-key direction, "
           "and I only update it while you're moving, so it keeps facing the same way when you stop.\n\nPress **Play** (F5) and steer around!"],
)

FEATURES["restart_key"] = dict(
    prompts=["press R to restart the game", "add a restart button on R", "I want to reset the level with a key",
             "how can I start over without stopping the game? make R restart"],
    files={"rust/src/player.rs": RESTART}, run=2,
    intro=["A restart key is super handy while testing. Let me look at the player."],
    final=["Press **R** at any time to restart: it reloads the whole scene, just like starting fresh.\n\n"
           "Press **Play** (F5), move around, then hit **R**. Later, when the player can lose, we can call the same restart automatically."],
    mistake={"rust/src/player.rs": RESTART_MISTAKE},
    mistake_note="In this version of godot-rust, `get_tree()` gives the tree directly instead of an `Option`, so there's nothing to `unwrap()`. Removing it.",
)

FEATURES["teleport_key"] = dict(
    prompts=["press T to teleport somewhere random", "add a random teleport", "teleport the player to a random spot when I hit T",
             "I want a blink ability that warps me somewhere random"],
    files={"rust/src/player.rs": TELEPORT}, run=2,
    intro=["Teleporting! Let me peek at the player code.", "A blink ability, nice. Let me see how the player works."],
    final=["Press **T** and the player warps to a random spot on the screen. I remember whether T was already down last frame, "
           "so holding it teleports only once.\n\nPress **Play** (F5) and try it!\n\nIdea: leave a puff of color where you teleported from?"],
    mistake={"rust/src/player.rs": TELEPORT_MISTAKE},
    mistake_note="`randf_range` works with `f64` numbers, but the screen size is `f32`. I need to convert going in and coming out.",
)

FEATURES["slow_motion"] = dict(
    prompts=["hold Z for slow motion", "add bullet time", "make everything slow down when I hold a key",
             "slow-mo button please!"],
    files={"rust/src/player.rs": SLOWMO}, run=2,
    intro=["Bullet time! Let me look at the player first."],
    final=["Hold **Z** and the whole game runs at 30% speed; let go and it's back to normal. I used Godot's `Engine` time scale, "
           "which slows down *everything*, so enemies and timers will slow down too once you have them.\n\n"
           "Press **Play** (F5) and try it. **Slow Factor** in the Inspector sets how slow it gets."],
)

FEATURES["toggle_hide"] = dict(
    prompts=["press H to make the player invisible", "ghost mode toggle", "let me hide and show the player with a key",
             "make H turn the player invisible and back"],
    files={"rust/src/player.rs": HIDE}, run=2,
    intro=["Ghost mode! Let me look at the player code."],
    final=["Press **H** to hide the player and **H** again to bring it back. It's a toggle: each press flips `visible`.\n\n"
           "Press **Play** (F5) to try it. Idea: make enemies unable to see you while you're hidden!"],
)

FEATURES["pulse"] = dict(
    prompts=["make the player breathe, growing and shrinking a little", "add a pulsing effect to the player",
             "can the character throb gently like a heartbeat", "idle animation: slowly get bigger and smaller"],
    files={"rust/src/player.rs": PULSE}, run=2,
    intro=["A breathing effect, lovely. Let me look at the player."],
    final=["The player now gently breathes: its size swings between 90% and 110% once a second using a sine wave.\n\n"
           "Press **Play** (F5) to see it. Tweak **Pulse Amount** and **Pulse Speed** in the Inspector for a calm breath or a fast heartbeat."],
)

FEATURES["name_tag"] = dict(
    prompts=["put a name above my player", "add a label that says Hero over the character",
             "show the player's name floating above it", "I want text above the player's head"],
    files={"main.tscn": NAME_TAG_SCENE}, run=2,
    intro=["A name tag! That's a scene change, no code needed. Let me look at the scene."],
    final=["Your player now has a **Hero** name tag floating above it. It's a `Label` that is a child of the Player, so it moves along automatically.\n\n"
           "Press **Play** (F5) to see it. To change the name, click **NameTag** in the Scene panel and edit **Text** in the Inspector."],
    scene_mistake={"main.tscn": NAME_TAG_SCENE_MISTAKE},
    scene_mistake_note="Oops, parent paths in a scene are relative to the root node, so it should be `Player`, not `Main/Player`. Fixing it.",
)

FEATURES["orbiting_moon"] = dict(
    prompts=["add a little moon that circles around my player", "make something orbit the player",
             "I want a buddy that spins around me", "add a satellite orbiting the character"],
    new_nodes=[("Moon", "Node2D")],
    files={"rust/src/moon.rs": MOON, "main.tscn": MOON_SCENE}, run=2,
    scene_mistake={"main.tscn": MOON_SCENE_MISTAKE},
    scene_mistake_note="I pointed the moon's sprite at a texture I never declared. The project's only image is `icon.svg` (`1_icon`), so I'll use that.",
    intro=["A little moon, how fun! Let me look around the project first."],
    final=["Your player now has a moon! The new **Moon** node is a child of the Player, so it follows you, and it moves around in a circle using `Vector2::from_angle`.\n\n"
           "Press **Play** (F5) to watch it orbit. Change **Radius** and **Orbit Speed** in the Inspector (negative speed = the other way).\n\n"
           "Idea: give it a collision shape and it could knock enemies away!"],
)

FEATURES["stopwatch"] = dict(
    prompts=["show a timer counting up on screen", "add a stopwatch to the corner", "display how long I've been playing",
             "I want a clock that shows the seconds"],
    new_nodes=[("Stopwatch", "Label")],
    files={"rust/src/stopwatch.rs": STOPWATCH, "main.tscn": STOPWATCH_SCENE}, run=2,
    intro=["A timer on screen, great for speedruns! Let me look around first."],
    final=["There's a stopwatch in the top-left corner now: **Time: 0.0**, counting up. It's a Rust `Label` that adds `delta` every frame. "
           "I put it inside a `CanvasLayer` so it stays put on screen even if a camera moves.\n\nPress **Play** (F5) to see it tick."],
    scene_mistake={"main.tscn": STOPWATCH_SCENE_MISTAKE},
    scene_mistake_note="I forgot to add the `UI` CanvasLayer that the stopwatch sits in. Adding it.",
)

FEATURES["spikes"] = dict(
    requires=["topdown_body"],
    prompts=["add spikes that send me back to the start", "make a hazard that restarts the level when I touch it",
             "add a red danger zone", "I need something deadly to avoid"],
    new_nodes=[("Spikes", "Area2D")],
    files={"rust/src/spikes.rs": SPIKES, "main.tscn": SPIKES_SCENE}, run=2,
    intro=["Danger! Let me look at the project first."],
    final=["I added red **Spikes** in the bottom right. They're an `Area2D`: when the player's body enters, the level restarts. "
           "The restart is deferred until the physics step finishes, because Godot doesn't allow swapping scenes in the middle of it.\n\n"
           "Press **Play** (F5) and touch the red block. Want more spikes? Select **Spikes** in the Scene panel and duplicate it with Ctrl+D."],
    scene_mistake={"main.tscn": SPIKES_SCENE_MISTAKE},
    scene_mistake_note="I used a collision shape in the scene without defining it. Adding the `RectangleShape2D` sub-resource.",
)

FEATURES["tint_color"] = dict(
    prompts=["let me choose the player's color in the inspector", "make the player blue", "can I change the player's color?",
             "tint the character a different color"],
    files={"rust/src/player.rs": TINT}, run=2,
    intro=["Sure! Let me look at the player code."],
    final=["The player now has a **Tint** setting: it's light blue to start, and you can pick any color in the Inspector. "
           "The tint is applied with `set_modulate` when the game starts.\n\nPress **Play** (F5) to see it, then select **Player** and click the **Tint** color box to choose your own."],
)

CHAINS = [
    ["explain_starter", "rainbow"],
    ["explain_starter", "grid_move"],
    ["explain_starter", "name_tag"],
    ["smooth_movement", "stopwatch"],
    ["orbiting_moon", "name_tag"],
    ["topdown_body", "spikes"],
]
