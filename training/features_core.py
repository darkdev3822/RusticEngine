"""Gold features for Ember's training data, part 1: core 2D gameplay.

Each feature is replayed against a real project by gen_traces.py, through the real agent tools,
so every file, build result and playtest output in the dataset is genuine.

Feature keys:
  requires  features applied silently first (their end state is the starting point)
  prompts   ways a user might ask for it (plain, excited, vague, typo'd, kid-like...)
  new_nodes [(ClassName, Base)] created with the new_rust_node tool
  files     {path: full content} written with write_file
  edits     [(path, old, new)] applied with edit_file
  run       playtest after building (seconds)
  intro     what Ember says before starting
  final     what Ember says after it works (plain explanation, what to try, a creative next idea)
  mistake   {path: buggy content} variant for error-recovery traces (written first, then fixed)
"""

TOPDOWN_PLAYER = '''use godot::classes::{CharacterBody2D, ICharacterBody2D, Input};
use godot::prelude::*;

/// The hero. Moves in all directions with the arrow keys and bumps into walls.
#[derive(GodotClass)]
#[class(base = CharacterBody2D)]
pub struct Player {
    /// Pixels per second.
    #[export]
    speed: f32,
    base: Base<CharacterBody2D>,
}

#[godot_api]
impl ICharacterBody2D for Player {
    fn init(base: Base<CharacterBody2D>) -> Self {
        Self { speed: 300.0, base }
    }

    fn physics_process(&mut self, _delta: f64) {
        let direction = Input::singleton().get_vector("ui_left", "ui_right", "ui_up", "ui_down");
        let velocity = direction * self.speed;
        self.base_mut().set_velocity(velocity);
        self.base_mut().move_and_slide();
    }
}
'''

TOPDOWN_SCENE = '''[gd_scene format=3]

[ext_resource type="Texture2D" path="res://icon.svg" id="1_icon"]

[sub_resource type="CircleShape2D" id="CircleShape2D_player"]
radius = 28.0

[node name="Main" type="Node2D"]

[node name="Player" type="Player" parent="."]
position = Vector2(576, 324)

[node name="Sprite2D" type="Sprite2D" parent="Player"]
scale = Vector2(0.5, 0.5)
texture = ExtResource("1_icon")

[node name="CollisionShape2D" type="CollisionShape2D" parent="Player"]
shape = SubResource("CircleShape2D_player")
'''

COIN = '''use godot::classes::{Area2D, IArea2D, Node2D};
use godot::prelude::*;

use crate::player::Player;

/// A coin that bobs up and down and vanishes when the player touches it.
#[derive(GodotClass)]
#[class(base = Area2D)]
pub struct Coin {
    #[export]
    value: i32,
    time: f64,
    start_y: f32,
    base: Base<Area2D>,
}

#[godot_api]
impl IArea2D for Coin {
    fn init(base: Base<Area2D>) -> Self {
        Self { value: 1, time: 0.0, start_y: 0.0, base }
    }

    fn ready(&mut self) {
        self.start_y = self.base().get_position().y;
        self.signals().body_entered().connect_self(Self::on_body_entered);
    }

    fn process(&mut self, delta: f64) {
        self.time += delta;
        let mut position = self.base().get_position();
        position.y = self.start_y + (self.time * 4.0).sin() as f32 * 6.0;
        self.base_mut().set_position(position);
    }
}

#[godot_api]
impl Coin {
    /// Tells the game a coin was picked up.
    #[signal]
    pub fn collected(value: i32);

    fn on_body_entered(&mut self, body: Gd<Node2D>) {
        if body.try_cast::<Player>().is_ok() {
            let value = self.value;
            self.signals().collected().emit(value);
            self.base_mut().queue_free();
        }
    }
}
'''

COIN_SCENE = '''[gd_scene format=3]

[ext_resource type="Texture2D" path="res://icon.svg" id="1_icon"]

[sub_resource type="CircleShape2D" id="CircleShape2D_coin"]
radius = 16.0

[node name="Coin" type="Coin"]

[node name="Sprite2D" type="Sprite2D" parent="."]
modulate = Color(1, 0.84, 0.2, 1)
scale = Vector2(0.25, 0.25)
texture = ExtResource("1_icon")

[node name="CollisionShape2D" type="CollisionShape2D" parent="."]
shape = SubResource("CircleShape2D_coin")
'''

COINS_MAIN_SCENE = TOPDOWN_SCENE + '''
[node name="Coin1" parent="." instance=ExtResource("2_coin")]
position = Vector2(300, 200)

[node name="Coin2" parent="." instance=ExtResource("2_coin")]
position = Vector2(850, 220)

[node name="Coin3" parent="." instance=ExtResource("2_coin")]
position = Vector2(450, 500)

[node name="Coin4" parent="." instance=ExtResource("2_coin")]
position = Vector2(780, 470)
'''
COINS_MAIN_SCENE = COINS_MAIN_SCENE.replace(
    '[ext_resource type="Texture2D" path="res://icon.svg" id="1_icon"]\n',
    '[ext_resource type="Texture2D" path="res://icon.svg" id="1_icon"]\n'
    '[ext_resource type="PackedScene" path="res://coin.tscn" id="2_coin"]\n')

HUD = '''use godot::classes::{CanvasLayer, ICanvasLayer, Label};
use godot::prelude::*;

/// Shows the score in the corner of the screen. Needs a child Label called "ScoreLabel".
#[derive(GodotClass)]
#[class(base = CanvasLayer)]
pub struct Hud {
    score: i32,
    base: Base<CanvasLayer>,
}

#[godot_api]
impl ICanvasLayer for Hud {
    fn init(base: Base<CanvasLayer>) -> Self {
        Self { score: 0, base }
    }

    fn ready(&mut self) {
        self.refresh();
    }
}

#[godot_api]
impl Hud {
    #[func]
    pub fn add_score(&mut self, amount: i32) {
        self.score += amount;
        self.refresh();
    }

    fn refresh(&mut self) {
        let text = format!("Score: {}", self.score);
        let mut label = self.base().get_node_as::<Label>("ScoreLabel");
        label.set_text(&text);
    }
}
'''

GAME_WITH_HUD = '''use godot::classes::{INode2D, Node2D};
use godot::prelude::*;

use crate::coin::Coin;
use crate::hud::Hud;

/// The main scene's brain: connects every coin to the score display.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Game {
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Game {
    fn init(base: Base<Node2D>) -> Self {
        Self { base }
    }

    fn ready(&mut self) {
        let hud = self.base().get_node_as::<Hud>("Hud");
        for child in self.base().get_children().iter_shared() {
            if let Ok(coin) = child.try_cast::<Coin>() {
                coin.signals().collected().connect_other(&hud, Hud::add_score);
            }
        }
    }
}
'''

HUD_MAIN_SCENE = COINS_MAIN_SCENE.replace('[node name="Main" type="Node2D"]', '[node name="Main" type="Game"]') + '''
[node name="Hud" type="Hud" parent="."]

[node name="ScoreLabel" type="Label" parent="Hud"]
offset_left = 24.0
offset_top = 16.0
offset_right = 324.0
offset_bottom = 60.0
theme_override_font_sizes/font_size = 32
text = "Score: 0"
'''

PLATFORMER_PLAYER = '''use godot::classes::{CharacterBody2D, ICharacterBody2D, Input};
use godot::global::Key;
use godot::prelude::*;

/// A platformer hero: arrow keys to run, Space (or Up) to jump.
#[derive(GodotClass)]
#[class(base = CharacterBody2D)]
pub struct Player {
    #[export]
    speed: f32,
    #[export]
    jump_velocity: f32,
    #[export]
    gravity: f32,
    base: Base<CharacterBody2D>,
}

#[godot_api]
impl ICharacterBody2D for Player {
    fn init(base: Base<CharacterBody2D>) -> Self {
        Self { speed: 280.0, jump_velocity: -480.0, gravity: 1100.0, base }
    }

    fn physics_process(&mut self, delta: f64) {
        let input = Input::singleton();
        let mut velocity = self.base().get_velocity();
        let on_floor = self.base().is_on_floor();

        if !on_floor {
            velocity.y += self.gravity * delta as f32;
        }
        let wants_jump = input.is_key_pressed(Key::SPACE) || input.is_action_pressed("ui_up");
        if wants_jump && on_floor {
            velocity.y = self.jump_velocity;
        }
        velocity.x = input.get_axis("ui_left", "ui_right") * self.speed;

        self.base_mut().set_velocity(velocity);
        self.base_mut().move_and_slide();
    }
}
'''

PLATFORMER_SCENE = '''[gd_scene format=3]

[ext_resource type="Texture2D" path="res://icon.svg" id="1_icon"]

[sub_resource type="RectangleShape2D" id="RectangleShape2D_player"]
size = Vector2(56, 60)

[sub_resource type="RectangleShape2D" id="RectangleShape2D_floor"]
size = Vector2(1152, 40)

[sub_resource type="RectangleShape2D" id="RectangleShape2D_ledge"]
size = Vector2(240, 24)

[node name="Main" type="Node2D"]

[node name="Player" type="Player" parent="."]
position = Vector2(200, 500)

[node name="Sprite2D" type="Sprite2D" parent="Player"]
scale = Vector2(0.5, 0.5)
texture = ExtResource("1_icon")

[node name="CollisionShape2D" type="CollisionShape2D" parent="Player"]
shape = SubResource("RectangleShape2D_player")

[node name="Floor" type="StaticBody2D" parent="."]
position = Vector2(576, 628)

[node name="CollisionShape2D" type="CollisionShape2D" parent="Floor"]
shape = SubResource("RectangleShape2D_floor")

[node name="ColorRect" type="ColorRect" parent="Floor"]
offset_left = -576.0
offset_top = -20.0
offset_right = 576.0
offset_bottom = 20.0
color = Color(0.36, 0.25, 0.2, 1)

[node name="Ledge" type="StaticBody2D" parent="."]
position = Vector2(640, 470)

[node name="CollisionShape2D" type="CollisionShape2D" parent="Ledge"]
shape = SubResource("RectangleShape2D_ledge")

[node name="ColorRect" type="ColorRect" parent="Ledge"]
offset_left = -120.0
offset_top = -12.0
offset_right = 120.0
offset_bottom = 12.0
color = Color(0.55, 0.35, 0.2, 1)
'''

ENEMY = '''use godot::classes::{CharacterBody2D, ICharacterBody2D};
use godot::global::randf_range;
use godot::prelude::*;

use crate::player::Player;

/// Wanders around, and chases the player when it gets close.
#[derive(GodotClass)]
#[class(base = CharacterBody2D)]
pub struct Enemy {
    #[export]
    speed: f32,
    #[export]
    chase_distance: f32,
    wander: Vector2,
    base: Base<CharacterBody2D>,
}

#[godot_api]
impl ICharacterBody2D for Enemy {
    fn init(base: Base<CharacterBody2D>) -> Self {
        Self { speed: 140.0, chase_distance: 300.0, wander: Vector2::ZERO, base }
    }

    fn ready(&mut self) {
        let angle = randf_range(0.0, std::f64::consts::TAU) as f32;
        self.wander = Vector2::from_angle(angle);
    }

    fn physics_process(&mut self, _delta: f64) {
        let my_position = self.base().get_global_position();
        let mut direction = self.wander;
        if let Some(player) = self.base().try_get_node_as::<Player>("../Player") {
            let player_position = player.get_global_position();
            if my_position.distance_to(player_position) < self.chase_distance {
                direction = (player_position - my_position).normalized();
            }
        }
        let velocity = direction * self.speed;
        self.base_mut().set_velocity(velocity);
        self.base_mut().move_and_slide();
        if self.base().is_on_wall() {
            self.wander = -self.wander;
        }
    }
}
'''

ENEMY_MAIN_SCENE = TOPDOWN_SCENE.replace(
    '[sub_resource type="CircleShape2D" id="CircleShape2D_player"]',
    '[sub_resource type="CircleShape2D" id="CircleShape2D_enemy"]\nradius = 24.0\n\n'
    '[sub_resource type="CircleShape2D" id="CircleShape2D_player"]') + '''
[node name="Enemy" type="Enemy" parent="."]
position = Vector2(900, 150)

[node name="Sprite2D" type="Sprite2D" parent="Enemy"]
modulate = Color(1, 0.35, 0.3, 1)
scale = Vector2(0.4, 0.4)
texture = ExtResource("1_icon")

[node name="CollisionShape2D" type="CollisionShape2D" parent="Enemy"]
shape = SubResource("CircleShape2D_enemy")
'''

SPIN_PLAYER = '''use godot::classes::{INode2D, Input, Node2D};
use godot::prelude::*;

/// Your first Rust node: it moves with the arrow keys and spins as it goes.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Player {
    /// Pixels per second.
    #[export]
    speed: f32,
    /// Turns per second (1.0 = one full spin every second).
    #[export]
    spin_speed: f32,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Player {
    fn init(base: Base<Node2D>) -> Self {
        Self { speed: 300.0, spin_speed: 0.25, base }
    }

    fn ready(&mut self) {
        godot_print!("spinning!");
    }

    fn process(&mut self, delta: f64) {
        let input = Input::singleton();
        let direction = input.get_vector("ui_left", "ui_right", "ui_up", "ui_down");
        let step = direction * self.speed * delta as f32;
        let position = self.base().get_position();
        self.base_mut().set_position(position + step);

        let angle = self.spin_speed * std::f32::consts::TAU * delta as f32;
        self.base_mut().rotate(angle);
    }
}
'''

SPIN_MISTAKE = SPIN_PLAYER.replace(
    '        let position = self.base().get_position();\n        self.base_mut().set_position(position + step);',
    '        self.base_mut().set_position(self.base().get_position() + step);')

SPEED_BOOST_PLAYER = '''use godot::classes::{INode2D, Input, Node2D};
use godot::global::Key;
use godot::prelude::*;

/// Moves with the arrow keys. Hold Shift to sprint!
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Player {
    /// Normal speed, in pixels per second.
    #[export]
    speed: f32,
    /// How many times faster sprinting is.
    #[export]
    sprint_multiplier: f32,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Player {
    fn init(base: Base<Node2D>) -> Self {
        Self { speed: 300.0, sprint_multiplier: 2.0, base }
    }

    fn process(&mut self, delta: f64) {
        let input = Input::singleton();
        let direction = input.get_vector("ui_left", "ui_right", "ui_up", "ui_down");
        let mut speed = self.speed;
        if input.is_key_pressed(Key::SHIFT) {
            speed *= self.sprint_multiplier;
        }
        let step = direction * speed * delta as f32;
        let position = self.base().get_position();
        self.base_mut().set_position(position + step);
    }
}
'''

SPEED_BOOST_MISTAKE = SPEED_BOOST_PLAYER.replace('        let step = direction * speed * delta as f32;',
                                                 '        let step = direction * speed * delta;')

WRAP_PLAYER = '''use godot::classes::{INode2D, Input, Node2D};
use godot::prelude::*;

/// Moves with the arrow keys. Leave one side of the screen and you come back on the other!
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
        let input = Input::singleton();
        let direction = input.get_vector("ui_left", "ui_right", "ui_up", "ui_down");
        let screen = self.base().get_viewport_rect().size;
        let mut position = self.base().get_position() + direction * self.speed * delta as f32;

        // Wrap around the edges, like the old arcade games.
        if position.x < 0.0 { position.x += screen.x; }
        if position.x > screen.x { position.x -= screen.x; }
        if position.y < 0.0 { position.y += screen.y; }
        if position.y > screen.y { position.y -= screen.y; }

        self.base_mut().set_position(position);
    }
}
'''

FLASH_PLAYER = '''use godot::classes::{INode2D, Input, Node2D};
use godot::global::{Key, randf_range};
use godot::prelude::*;

/// Moves with the arrow keys. Press Space to change into a random color!
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Player {
    #[export]
    speed: f32,
    space_was_down: bool,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Player {
    fn init(base: Base<Node2D>) -> Self {
        Self { speed: 300.0, space_was_down: false, base }
    }

    fn process(&mut self, delta: f64) {
        let input = Input::singleton();
        let direction = input.get_vector("ui_left", "ui_right", "ui_up", "ui_down");
        let step = direction * self.speed * delta as f32;
        let position = self.base().get_position();
        self.base_mut().set_position(position + step);

        // Only react on the moment Space goes down, not every frame it's held.
        let space_down = input.is_key_pressed(Key::SPACE);
        if space_down && !self.space_was_down {
            let color = Color::from_rgb(
                randf_range(0.3, 1.0) as f32,
                randf_range(0.3, 1.0) as f32,
                randf_range(0.3, 1.0) as f32,
            );
            self.base_mut().set_modulate(color);
        }
        self.space_was_down = space_down;
    }
}
'''

CLICK_TELEPORT_PLAYER = '''use godot::classes::{INode2D, Input, InputEvent, InputEventMouseButton, Node2D};
use godot::global::MouseButton;
use godot::prelude::*;

/// Moves with the arrow keys, and teleports wherever you click!
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
        let direction = Input::singleton().get_vector("ui_left", "ui_right", "ui_up", "ui_down");
        let step = direction * self.speed * delta as f32;
        let position = self.base().get_position();
        self.base_mut().set_position(position + step);
    }

    fn input(&mut self, event: Gd<InputEvent>) {
        if let Ok(click) = event.try_cast::<InputEventMouseButton>() {
            if click.is_pressed() && click.get_button_index() == MouseButton::LEFT {
                let target = self.base().get_global_mouse_position();
                self.base_mut().set_global_position(target);
            }
        }
    }
}
'''

BACKGROUND_GAME = '''use godot::classes::{INode2D, Node2D, RenderingServer};
use godot::prelude::*;

/// Slowly cycles the background through warm sunset colors.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Background {
    time: f32,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Background {
    fn init(base: Base<Node2D>) -> Self {
        Self { time: 0.0, base }
    }

    fn process(&mut self, delta: f64) {
        self.time += delta as f32;
        let wave = (self.time * 0.3).sin() * 0.5 + 0.5; // goes 0 -> 1 -> 0
        let dusk = Color::from_rgb(0.18, 0.12, 0.25);
        let sunset = Color::from_rgb(0.85, 0.42, 0.25);
        RenderingServer::singleton().set_default_clear_color(dusk.lerp(sunset, wave as f64));
    }
}
'''

BACKGROUND_SCENE_EDIT = ('main.tscn', '[node name="Main" type="Node2D"]', '[node name="Main" type="Background"]')

FEATURES = {}

FEATURES["spin"] = dict(
    prompts=[
        "Make the player spin slowly while it moves.",
        "can my guy spin around?",
        "I want the player to rotate all the time, like a little tornado",
        "Make it spin! And print 'spinning!' when the game starts.",
        "how do i make the character turn in circles",
        "add rotation to the player pls",
    ],
    files={"rust/src/player.rs": SPIN_PLAYER},
    run=3,
    intro=["A spinning player, love it! Let me look at the player code first.",
           "Ooh, a little tornado! Let me check how the player works right now."],
    final=["Done! Your player now spins a quarter turn every second while it moves, and says \"spinning!\" in the Output panel when the game starts.\n\nPress **Play** (F5) and use the arrow keys. Want it faster? Change **Spin Speed** in the Inspector.\n\nIdea: what if it spun faster the quicker you moved, like a spinning top picking up speed?",
           "It spins! I added a `spin_speed` setting (a quarter turn per second) and rotate the player a tiny bit every frame.\n\nPress **Play** (F5) to watch it twirl. You can tweak **Spin Speed** in the Inspector without touching code.\n\nNext, maybe it could spin the other way when you move left?"],
    mistake={"rust/src/player.rs": SPIN_MISTAKE},
    mistake_note="Rust stopped me there, and it's a good lesson: I tried to *read* the player's position and *change* it in the same line. Rust doesn't allow looking at something and changing it at the exact same moment, which prevents a whole family of bugs. The fix is to do it in two steps: read first, then change.",
)

FEATURES["speed_boost"] = dict(
    prompts=[
        "Let me hold shift to run faster",
        "add a sprint button",
        "I want a speed boost when I press shift",
        "can the player go zoom when holding shift??",
        "make shift = run",
    ],
    files={"rust/src/player.rs": SPEED_BOOST_PLAYER},
    run=2,
    intro=["Sprinting coming up! Let me peek at the player code.", "Zoom mode! Let me see how movement works now."],
    final=["Hold **Shift** to sprint: you now move twice as fast while it's held. Press **Play** (F5) to try it.\n\nYou can change how fast sprinting is with **Sprint Multiplier** in the Inspector.\n\nIdea: a stamina bar that drains while you sprint, so you have to choose when to run!",
           "Sprinting works! While **Shift** is held, your speed is multiplied by 2.\n\nTry it with **Play** (F5). Next we could leave a little dust trail behind you while sprinting. Want to try that?"],
    mistake={"rust/src/player.rs": SPEED_BOOST_MISTAKE},
    mistake_note="A tiny slip: `delta` is a 64-bit decimal number (`f64`), but movement uses 32-bit ones (`f32`). Rust wants us to say exactly how to convert, so I'll add `as f32`.",
)

FEATURES["wrap"] = dict(
    prompts=[
        "When the player goes off the edge of the screen, make it come back on the other side",
        "screen wrap like asteroids",
        "my player keeps leaving the screen and getting lost",
        "can the world loop around like pac-man's tunnel?",
    ],
    files={"rust/src/player.rs": WRAP_PLAYER},
    run=2,
    intro=["Classic arcade wrap-around, great choice! Checking the player first.",
           "Let's stop your player from getting lost. Looking at the movement code."],
    final=["Now the screen loops: leave on the right and you pop back in on the left, same for top and bottom. Press **Play** (F5) and run off an edge!\n\nIdea: this would make a great asteroid-dodging game. Want some space rocks drifting across the screen?",
           "Done! The player now wraps around the screen edges, just like Asteroids or Pac-Man's tunnel. Try it with **Play** (F5)."],
)

FEATURES["color_flash"] = dict(
    prompts=[
        "When I press space, change the player's color randomly",
        "make the player change colors",
        "press space = new color!!",
        "I want my character to flash a random colour",
    ],
    files={"rust/src/player.rs": FLASH_PLAYER},
    run=2,
    intro=["Color magic! Let me look at the player.", "A color-changing hero, fun! Checking the code first."],
    final=["Press **Space** and the player turns a random bright color each time. I made it react only to the moment you press, so holding Space doesn't make it flicker.\n\nPress **Play** (F5) to try it.\n\nIdea: the player could change color to match whatever it touches, like a chameleon!",
           "Each press of **Space** now paints the player a new random color. Give it a try with **Play** (F5)!"],
)

FEATURES["click_teleport"] = dict(
    prompts=[
        "Make the player teleport to where I click",
        "click to move the player instantly",
        "I want to click on the screen and have my guy appear there",
        "mouse click teleport",
    ],
    files={"rust/src/player.rs": CLICK_TELEPORT_PLAYER},
    run=2,
    intro=["Teleporting, very cool! Let me see the player code.", "Click-to-teleport, coming up. Checking how input works right now."],
    final=["Click anywhere with the **left mouse button** and the player teleports there instantly. The arrow keys still work too.\n\nPress **Play** (F5) to try it.\n\nIdea: add a short cooldown and a puff effect so teleporting feels like a magic power.",
           "Done! Your player now jumps to wherever you left-click. I used the `input` callback, which Godot calls whenever something like a click or key press happens."],
)

FEATURES["background"] = dict(
    prompts=[
        "Make the background slowly change colors like a sunset",
        "the grey background is boring",
        "can the sky change colour over time",
        "make the background pretty",
    ],
    new_nodes=[("Background", "Node2D")],
    files={"rust/src/background.rs": BACKGROUND_GAME},
    edits=[BACKGROUND_SCENE_EDIT],
    run=2,
    intro=["A sunset sky, beautiful idea! Let me look at the project.", "Let's give your game some atmosphere. First a look around."],
    final=["Your background now drifts between dusk purple and sunset orange. I made the main scene's root node a `Background` node that updates the sky color every frame.\n\nPress **Play** (F5) and watch the sky.\n\nIdea: the sky could get darker as the game goes on, like night falling!",
           "Done! The background slowly breathes between purple and orange. You can change the two colors at the top of `background.rs`."],
)

FEATURES["topdown_body"] = dict(
    prompts=[
        "I want the player to bump into walls instead of going through things",
        "make the player a physics body with collisions",
        "turn the player into a CharacterBody2D",
        "the player should be solid",
    ],
    files={"rust/src/player.rs": TOPDOWN_PLAYER, "main.tscn": TOPDOWN_SCENE},
    run=2,
    intro=["Good thinking: solid objects make a game feel real. Let me look at the player and the scene."],
    final=["Your player is now a **CharacterBody2D**: a body that moves with `move_and_slide()` and stops at anything solid. I also gave it a round collision shape in the scene.\n\nPress **Play** (F5): it moves the same, but now it can collide. Next we could add some walls or coins to bump into!"],
)

FEATURES["coins"] = dict(
    requires=["topdown_body"],
    prompts=[
        "Add coins the player can collect",
        "I want collectible coins!",
        "make some coins that disappear when I touch them",
        "Can we add stuff to pick up?",
        "coins pls",
        "Make the player collect coins that pop up around the screen",
    ],
    new_nodes=[("Coin", "Area2D")],
    files={"rust/src/coin.rs": COIN, "coin.tscn": COIN_SCENE, "main.tscn": COINS_MAIN_SCENE},
    run=3,
    intro=["Coins! Every good game needs something shiny to grab. Let me see what we have.",
           "Collectibles are so satisfying. First, a look around the project."],
    final=["I added four golden coins that gently bob up and down. Touch one and it disappears.\n\nHow it works: each coin is an **Area2D**, which notices when a body enters it, and the coin checks that it was the player.\n\nPress **Play** (F5) and go collect them! Next, want a score counter in the corner?",
           "Coins are in! There are four of them in the level, bobbing up and down. Run into one and it vanishes. Each coin also sends out a `collected` signal, so we can hook up a score display next.\n\nPress **Play** (F5) to try it."],
)

FEATURES["score_hud"] = dict(
    requires=["topdown_body", "coins"],
    prompts=[
        "Show a score that goes up when I collect coins",
        "add a score counter",
        "I want to see how many coins I got",
        "put the score in the corner",
        "score!!",
    ],
    new_nodes=[("Hud", "CanvasLayer"), ("Game", "Node2D")],
    files={"rust/src/hud.rs": HUD, "rust/src/game.rs": GAME_WITH_HUD, "main.tscn": HUD_MAIN_SCENE},
    run=3,
    intro=["A score counter, yes! Let me look at how the coins work first."],
    final=["Now there's a **Score** in the top-left corner that goes up by one for each coin.\n\nHow it fits together: each coin sends a `collected` signal, and the new `Game` node connects every coin's signal to the score display (`Hud`). Signals are like doorbells: the coin rings, the HUD answers.\n\nPress **Play** (F5) and collect them all! Idea: coins could spawn faster and faster, so it becomes a frantic race."],
)

FEATURES["platformer"] = dict(
    prompts=[
        "Turn the player into a platformer hero that can jump",
        "I want to make a platformer",
        "add gravity and jumping",
        "make it like mario, with jumping",
        "my guy should be able to jump on platforms",
    ],
    files={"rust/src/player.rs": PLATFORMER_PLAYER, "main.tscn": PLATFORMER_SCENE},
    run=3,
    intro=["A platformer, my favorite! Let me look at the player and the scene.",
           "Jumping time! First I'll check how the project is set up."],
    final=["You've got a platformer! The player falls with gravity, runs with the arrow keys and jumps with **Space** (or Up). I added a floor and a ledge to jump onto.\n\nPress **Play** (F5) and hop onto the ledge.\n\nYou can tune **Jump Velocity** and **Gravity** in the Inspector until the jump feels just right. Idea: a double jump, or coins floating above the ledge?",
           "Platformer mode is on! Gravity pulls the player down, **Space** jumps, and there's a floor plus a ledge to land on. Try it with **Play** (F5), then tweak **Gravity** and **Jump Velocity** in the Inspector to change how floaty it feels."],
)

FEATURES["enemy"] = dict(
    requires=["topdown_body"],
    prompts=[
        "Add an enemy that chases me",
        "I need a bad guy",
        "make an enemy that follows the player when it gets close",
        "add a monster that wanders around",
        "enemy that hunts you",
    ],
    new_nodes=[("Enemy", "CharacterBody2D")],
    files={"rust/src/enemy.rs": ENEMY, "main.tscn": ENEMY_MAIN_SCENE},
    run=3,
    intro=["A chaser! Things are getting exciting. Let me look around first."],
    final=["Meet your enemy: the red one in the top right. It wanders in a random direction, and when you come within 300 pixels it starts chasing you.\n\nPress **Play** (F5) and see if you can escape!\n\nYou can make it scarier with **Speed** or **Chase Distance** in the Inspector. Idea: should touching it cost the player a life?"],
)
