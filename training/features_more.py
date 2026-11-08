"""Gold features for Ember's training data, part 2: combat, polish, menus, saving and 3D."""
from features_core import (COIN_SCENE, ENEMY, ENEMY_MAIN_SCENE, GAME_WITH_HUD, HUD, HUD_MAIN_SCENE,
                           PLATFORMER_PLAYER, PLATFORMER_SCENE, TOPDOWN_PLAYER, TOPDOWN_SCENE)

FEATURES = {}

# ------------------------------------------------------------------ shooting
SHOOTER_PLAYER = '''use godot::classes::{CharacterBody2D, ICharacterBody2D, Input, PackedScene};
use godot::prelude::*;

use crate::bullet::Bullet;

/// Moves with the arrow keys and shoots with Space in the direction it last moved.
#[derive(GodotClass)]
#[class(base = CharacterBody2D)]
pub struct Player {
    #[export]
    speed: f32,
    /// The bullet scene to fire (bullet.tscn).
    #[export]
    bullet_scene: OnEditor<Gd<PackedScene>>,
    facing: Vector2,
    base: Base<CharacterBody2D>,
}

#[godot_api]
impl ICharacterBody2D for Player {
    fn init(base: Base<CharacterBody2D>) -> Self {
        Self { speed: 300.0, bullet_scene: OnEditor::default(), facing: Vector2::RIGHT, base }
    }

    fn physics_process(&mut self, _delta: f64) {
        let input = Input::singleton();
        let direction = input.get_vector("ui_left", "ui_right", "ui_up", "ui_down");
        if direction != Vector2::ZERO {
            self.facing = direction.normalized();
        }
        let velocity = direction * self.speed;
        self.base_mut().set_velocity(velocity);
        self.base_mut().move_and_slide();

        if input.is_action_just_pressed("ui_accept") {
            self.shoot();
        }
    }
}

impl Player {
    fn shoot(&mut self) {
        let mut bullet = self.bullet_scene.instantiate_as::<Bullet>();
        let start = self.base().get_global_position() + self.facing * 40.0;
        bullet.set_global_position(start);
        bullet.bind_mut().launch(self.facing);
        if let Some(mut parent) = self.base().get_parent() {
            parent.add_child(&bullet);
        }
    }
}
'''

BULLET = '''use godot::classes::{Area2D, IArea2D, Node2D};
use godot::prelude::*;

use crate::enemy::Enemy;

/// Flies in a straight line, removes any enemy it hits, and disappears after a while.
#[derive(GodotClass)]
#[class(base = Area2D)]
pub struct Bullet {
    #[export]
    speed: f32,
    direction: Vector2,
    life: f64,
    base: Base<Area2D>,
}

#[godot_api]
impl IArea2D for Bullet {
    fn init(base: Base<Area2D>) -> Self {
        Self { speed: 700.0, direction: Vector2::RIGHT, life: 1.5, base }
    }

    fn ready(&mut self) {
        self.signals().body_entered().connect_self(Self::on_body_entered);
    }

    fn process(&mut self, delta: f64) {
        let step = self.direction * self.speed * delta as f32;
        let position = self.base().get_position();
        self.base_mut().set_position(position + step);
        self.life -= delta;
        if self.life <= 0.0 {
            self.base_mut().queue_free();
        }
    }
}

#[godot_api]
impl Bullet {
    pub fn launch(&mut self, direction: Vector2) {
        self.direction = direction;
    }

    fn on_body_entered(&mut self, body: Gd<Node2D>) {
        if let Ok(mut enemy) = body.try_cast::<Enemy>() {
            enemy.queue_free();
            self.base_mut().queue_free();
        }
    }
}
'''

BULLET_SCENE = '''[gd_scene format=3]

[ext_resource type="Texture2D" path="res://icon.svg" id="1_icon"]

[sub_resource type="CircleShape2D" id="CircleShape2D_bullet"]
radius = 8.0

[node name="Bullet" type="Bullet"]

[node name="Sprite2D" type="Sprite2D" parent="."]
modulate = Color(1, 0.9, 0.4, 1)
scale = Vector2(0.12, 0.12)
texture = ExtResource("1_icon")

[node name="CollisionShape2D" type="CollisionShape2D" parent="."]
shape = SubResource("CircleShape2D_bullet")
'''

SHOOTER_SCENE = ENEMY_MAIN_SCENE.replace(
    '[ext_resource type="Texture2D" path="res://icon.svg" id="1_icon"]\n',
    '[ext_resource type="Texture2D" path="res://icon.svg" id="1_icon"]\n'
    '[ext_resource type="PackedScene" path="res://bullet.tscn" id="2_bullet"]\n').replace(
    '[node name="Player" type="Player" parent="."]\nposition = Vector2(576, 324)\n',
    '[node name="Player" type="Player" parent="."]\nposition = Vector2(576, 324)\nbullet_scene = ExtResource("2_bullet")\n')

SHOOTER_MISTAKE = SHOOTER_PLAYER.replace('        bullet.bind_mut().launch(self.facing);\n',
                                         '        bullet.launch(self.facing);\n')

FEATURES["shoot"] = dict(
    requires=["topdown_body", "enemy"],
    prompts=[
        "Let the player shoot at the enemy with space",
        "I want to shoot bullets!",
        "add shooting",
        "can my guy fire lasers at the bad guy",
        "pew pew when I press space please",
    ],
    new_nodes=[("Bullet", "Area2D")],
    files={"rust/src/bullet.rs": BULLET, "bullet.tscn": BULLET_SCENE,
           "rust/src/player.rs": SHOOTER_PLAYER, "main.tscn": SHOOTER_SCENE},
    run=3,
    intro=["Pew pew! Let me look at the player and the enemy first.", "Time to fight back! Checking the project."],
    final=["Press **Space** to fire! Bullets fly the way you last moved, and an enemy hit by one disappears.\n\nI made a `Bullet` node (its own little scene, `bullet.tscn`) and the player creates a fresh copy each time you shoot.\n\nPress **Play** (F5) and take aim. Idea: enemies could take three hits, flashing white each time!"],
    mistake={"rust/src/player.rs": SHOOTER_MISTAKE},
    mistake_note="Almost! `launch` lives on our own Rust `Bullet` struct, and to reach our Rust data through the node handle we first ask for it with `bind_mut()` (think of it as borrowing the bullet's keys). Fixing that.",
)

# ------------------------------------------------------------------ health & damage
HEALTH_PLAYER = '''use godot::classes::{CharacterBody2D, ICharacterBody2D, Input, Label};
use godot::prelude::*;

/// The hero: moves with the arrow keys and has a few hearts of health.
#[derive(GodotClass)]
#[class(base = CharacterBody2D)]
pub struct Player {
    #[export]
    speed: f32,
    #[export]
    max_health: i32,
    health: i32,
    base: Base<CharacterBody2D>,
}

#[godot_api]
impl ICharacterBody2D for Player {
    fn init(base: Base<CharacterBody2D>) -> Self {
        Self { speed: 300.0, max_health: 3, health: 3, base }
    }

    fn ready(&mut self) {
        self.health = self.max_health;
        self.show_health();
    }

    fn physics_process(&mut self, _delta: f64) {
        let direction = Input::singleton().get_vector("ui_left", "ui_right", "ui_up", "ui_down");
        let velocity = direction * self.speed;
        self.base_mut().set_velocity(velocity);
        self.base_mut().move_and_slide();
    }
}

#[godot_api]
impl Player {
    #[func]
    pub fn take_damage(&mut self, amount: i32) {
        self.health -= amount;
        godot_print!("Ouch! Health: {}", self.health);
        self.show_health();
        if self.health <= 0 {
            godot_print!("Game over! Restarting...");
            self.base().get_tree().reload_current_scene();
        }
    }

    fn show_health(&mut self) {
        if let Some(mut label) = self.base().try_get_node_as::<Label>("../Hud/HealthLabel") {
            let hearts = "♥ ".repeat(self.health.max(0) as usize);
            label.set_text(&format!("Health: {}", hearts));
        }
    }
}
'''

HEALTH_ENEMY = ENEMY.replace('''    wander: Vector2,
    base: Base<CharacterBody2D>,
}''', '''    wander: Vector2,
    /// Seconds until it can hurt the player again.
    cooldown: f64,
    base: Base<CharacterBody2D>,
}''').replace(
    'Self { speed: 140.0, chase_distance: 300.0, wander: Vector2::ZERO, base }',
    'Self { speed: 140.0, chase_distance: 300.0, wander: Vector2::ZERO, cooldown: 0.0, base }').replace(
    '''    fn physics_process(&mut self, _delta: f64) {
        let my_position = self.base().get_global_position();''', '''    fn physics_process(&mut self, delta: f64) {
        self.cooldown -= delta;
        let my_position = self.base().get_global_position();''').replace(
    '''            if my_position.distance_to(player_position) < self.chase_distance {
                direction = (player_position - my_position).normalized();
            }
        }''', '''            if my_position.distance_to(player_position) < self.chase_distance {
                direction = (player_position - my_position).normalized();
            }
            // Touching the player hurts it, at most once per second.
            if my_position.distance_to(player_position) < 56.0 && self.cooldown <= 0.0 {
                self.cooldown = 1.0;
                let mut player = player;
                player.bind_mut().take_damage(1);
            }
        }''')

HEALTH_SCENE = ENEMY_MAIN_SCENE + '''
[node name="Hud" type="CanvasLayer" parent="."]

[node name="HealthLabel" type="Label" parent="Hud"]
offset_left = 24.0
offset_top = 16.0
offset_right = 424.0
offset_bottom = 60.0
theme_override_font_sizes/font_size = 32
text = "Health:"
'''

FEATURES["health"] = dict(
    requires=["topdown_body", "enemy"],
    prompts=[
        "The enemy should hurt me when it touches me, and I should have 3 lives",
        "add health to the player",
        "I want hearts and the game restarts when I lose them all",
        "make the enemy do damage",
        "should touching the enemy cost a life? yes!",
    ],
    files={"rust/src/player.rs": HEALTH_PLAYER, "rust/src/enemy.rs": HEALTH_ENEMY, "main.tscn": HEALTH_SCENE},
    run=4,
    intro=["Now there's real danger! Let me look at the player and the enemy."],
    final=["You now have **3 hearts**, shown in the top-left. Each time the enemy touches you, you lose one (at most once per second, so you get a chance to escape). Lose them all and the level restarts.\n\nPress **Play** (F5) and try to survive! You can change **Max Health** in the Inspector.\n\nIdea: heart pickups that heal you, scattered around the map?"],
)

# ------------------------------------------------------------------ camera follow (scene only)
CAMERA_SCENE = TOPDOWN_SCENE + '''
[node name="Camera2D" type="Camera2D" parent="Player"]
position_smoothing_enabled = true
position_smoothing_speed = 6.0
'''

FEATURES["camera_follow"] = dict(
    requires=["topdown_body"],
    prompts=[
        "Make the camera follow the player",
        "the camera should move with my character",
        "i want a following camera, smooth",
        "camera follow pls",
    ],
    files={"main.tscn": CAMERA_SCENE},
    run=2,
    intro=["A following camera makes the world feel bigger! Let me check the scene."],
    final=["The camera now follows the player smoothly. I added a **Camera2D** as a child of the player, so wherever the player goes, the camera goes too, with a little easing.\n\nNo Rust needed for this one: it's all in the scene. Press **Play** (F5) and explore!\n\nIdea: now the level can be bigger than the screen. Want me to build a larger maze to explore?"],
)

# ------------------------------------------------------------------ particle trail (scene only)
TRAIL_SCENE = TOPDOWN_SCENE + '''
[node name="Trail" type="CPUParticles2D" parent="Player"]
amount = 40
lifetime = 0.6
local_coords = false
gravity = Vector2(0, 0)
initial_velocity_min = 10.0
initial_velocity_max = 30.0
scale_amount_min = 3.0
scale_amount_max = 6.0
color = Color(1, 0.6, 0.25, 0.8)
'''

FEATURES["trail"] = dict(
    requires=["topdown_body"],
    prompts=[
        "Make the player leave a glowing trail behind it",
        "add a sparkly trail",
        "particles behind my character!",
        "can it leave a fire trail when it moves",
    ],
    files={"main.tscn": TRAIL_SCENE},
    run=2,
    intro=["A glowing trail, gorgeous! Let me look at the scene."],
    final=["Your player now leaves a trail of warm orange sparks. I added a **CPUParticles2D** node to the player that keeps emitting little glowing dots; they stay where they were born, so they stream out behind you.\n\nPress **Play** (F5) and zoom around! You can change the color, amount and lifetime in the Inspector when you select **Trail**."],
)

# ------------------------------------------------------------------ dash
DASH_PLAYER = '''use godot::classes::{CharacterBody2D, ICharacterBody2D, Input};
use godot::global::Key;
use godot::prelude::*;

/// Moves with the arrow keys. Tap Shift to dash!
#[derive(GodotClass)]
#[class(base = CharacterBody2D)]
pub struct Player {
    #[export]
    speed: f32,
    #[export]
    dash_speed: f32,
    dash_time_left: f64,
    cooldown: f64,
    dash_direction: Vector2,
    shift_was_down: bool,
    base: Base<CharacterBody2D>,
}

#[godot_api]
impl ICharacterBody2D for Player {
    fn init(base: Base<CharacterBody2D>) -> Self {
        Self {
            speed: 300.0,
            dash_speed: 1100.0,
            dash_time_left: 0.0,
            cooldown: 0.0,
            dash_direction: Vector2::RIGHT,
            shift_was_down: false,
            base,
        }
    }

    fn physics_process(&mut self, delta: f64) {
        let input = Input::singleton();
        let direction = input.get_vector("ui_left", "ui_right", "ui_up", "ui_down");
        self.cooldown -= delta;
        self.dash_time_left -= delta;

        let shift_down = input.is_key_pressed(Key::SHIFT);
        if shift_down && !self.shift_was_down && self.cooldown <= 0.0 && direction != Vector2::ZERO {
            self.dash_direction = direction.normalized();
            self.dash_time_left = 0.15;
            self.cooldown = 0.8;
        }
        self.shift_was_down = shift_down;

        let velocity = if self.dash_time_left > 0.0 {
            self.dash_direction * self.dash_speed
        } else {
            direction * self.speed
        };
        self.base_mut().set_velocity(velocity);
        self.base_mut().move_and_slide();
    }
}
'''

FEATURES["dash"] = dict(
    requires=["topdown_body"],
    prompts=[
        "Add a dash when I tap shift",
        "I want a quick dash move",
        "dodge roll / dash ability",
        "make the player dash forward fast",
    ],
    files={"rust/src/player.rs": DASH_PLAYER},
    run=2,
    intro=["A dash! That makes movement feel so good. Looking at the player code."],
    final=["Tap **Shift** while moving to dash: a quick burst in that direction for 0.15 seconds. There's a short cooldown (0.8 s) so it stays special.\n\nPress **Play** (F5) and dash around! Try changing **Dash Speed** in the Inspector.\n\nIdea: make the player invincible during the dash, so you can dash *through* enemies."],
)

# ------------------------------------------------------------------ double jump
DOUBLE_JUMP_PLAYER = '''use godot::classes::{CharacterBody2D, ICharacterBody2D, Input};
use godot::prelude::*;

/// A platformer hero with a double jump: Space or Up to jump, and again in mid-air!
#[derive(GodotClass)]
#[class(base = CharacterBody2D)]
pub struct Player {
    #[export]
    speed: f32,
    #[export]
    jump_velocity: f32,
    #[export]
    gravity: f32,
    #[export]
    max_jumps: i32,
    jumps_left: i32,
    base: Base<CharacterBody2D>,
}

#[godot_api]
impl ICharacterBody2D for Player {
    fn init(base: Base<CharacterBody2D>) -> Self {
        Self { speed: 280.0, jump_velocity: -480.0, gravity: 1100.0, max_jumps: 2, jumps_left: 2, base }
    }

    fn physics_process(&mut self, delta: f64) {
        let input = Input::singleton();
        let mut velocity = self.base().get_velocity();

        if self.base().is_on_floor() {
            self.jumps_left = self.max_jumps;
        } else {
            velocity.y += self.gravity * delta as f32;
        }
        // "just pressed" fires once per key press, so holding the key doesn't use up every jump.
        let jump = input.is_action_just_pressed("ui_accept") || input.is_action_just_pressed("ui_up");
        if jump && self.jumps_left > 0 {
            velocity.y = self.jump_velocity;
            self.jumps_left -= 1;
        }
        velocity.x = input.get_axis("ui_left", "ui_right") * self.speed;

        self.base_mut().set_velocity(velocity);
        self.base_mut().move_and_slide();
    }
}
'''

FEATURES["double_jump"] = dict(
    requires=["platformer"],
    prompts=[
        "Give the player a double jump",
        "can I jump again in the air?",
        "double jump!!",
        "I want to jump twice",
    ],
    files={"rust/src/player.rs": DOUBLE_JUMP_PLAYER},
    run=3,
    intro=["Double jump, a classic! Let me look at how jumping works now."],
    final=["You can now jump a second time in mid-air! Jumps refill whenever you land. Press **Play** (F5) and try reaching higher.\n\nWant a triple jump? Set **Max Jumps** to 3 in the Inspector. Idea: a wall jump next?"],
)

# ------------------------------------------------------------------ moving platform
MOVING_PLATFORM = '''use godot::classes::{AnimatableBody2D, IAnimatableBody2D};
use godot::prelude::*;

/// A platform that glides back and forth. The player rides along when standing on it.
#[derive(GodotClass)]
#[class(base = AnimatableBody2D)]
pub struct MovingPlatform {
    /// How far it travels to each side, in pixels.
    #[export]
    distance: f32,
    /// How fast it moves back and forth.
    #[export]
    speed: f32,
    start: Vector2,
    time: f32,
    base: Base<AnimatableBody2D>,
}

#[godot_api]
impl IAnimatableBody2D for MovingPlatform {
    fn init(base: Base<AnimatableBody2D>) -> Self {
        Self { distance: 160.0, speed: 1.2, start: Vector2::ZERO, time: 0.0, base }
    }

    fn ready(&mut self) {
        self.start = self.base().get_position();
    }

    fn physics_process(&mut self, delta: f64) {
        self.time += delta as f32;
        let offset = (self.time * self.speed).sin() * self.distance;
        let position = self.start + Vector2::new(offset, 0.0);
        self.base_mut().set_position(position);
    }
}
'''

MOVING_PLATFORM_SCENE = PLATFORMER_SCENE.replace(
    '[sub_resource type="RectangleShape2D" id="RectangleShape2D_ledge"]',
    '[sub_resource type="RectangleShape2D" id="RectangleShape2D_moving"]\nsize = Vector2(180, 24)\n\n'
    '[sub_resource type="RectangleShape2D" id="RectangleShape2D_ledge"]') + '''
[node name="MovingPlatform" type="MovingPlatform" parent="."]
position = Vector2(860, 360)

[node name="CollisionShape2D" type="CollisionShape2D" parent="MovingPlatform"]
shape = SubResource("RectangleShape2D_moving")

[node name="ColorRect" type="ColorRect" parent="MovingPlatform"]
offset_left = -90.0
offset_top = -12.0
offset_right = 90.0
offset_bottom = 12.0
color = Color(0.85, 0.5, 0.2, 1)
'''

FEATURES["moving_platform"] = dict(
    requires=["platformer"],
    prompts=[
        "Add a platform that moves back and forth",
        "moving platforms please",
        "I want a platform that slides left and right",
        "make a floating platform that moves",
    ],
    new_nodes=[("MovingPlatform", "AnimatableBody2D")],
    files={"rust/src/moving_platform.rs": MOVING_PLATFORM, "main.tscn": MOVING_PLATFORM_SCENE},
    run=3,
    intro=["Moving platforms add so much life to a level! Let me look around."],
    final=["There's now an orange platform gliding left and right above the ledge. It's an **AnimatableBody2D**, a solid body that moves by code, so the player rides along when standing on it.\n\nPress **Play** (F5), jump onto the ledge and hop across! Tune **Distance** and **Speed** in the Inspector.\n\nIdea: a platform that only starts moving once you land on it."],
)

# ------------------------------------------------------------------ countdown
COUNTDOWN = '''use godot::classes::{CanvasLayer, ICanvasLayer, Label};
use godot::prelude::*;

/// Counts down from a number of seconds and shows "Time's up!" at zero.
#[derive(GodotClass)]
#[class(base = CanvasLayer)]
pub struct Countdown {
    #[export]
    seconds: f64,
    finished: bool,
    base: Base<CanvasLayer>,
}

#[godot_api]
impl ICanvasLayer for Countdown {
    fn init(base: Base<CanvasLayer>) -> Self {
        Self { seconds: 60.0, finished: false, base }
    }

    fn process(&mut self, delta: f64) {
        if self.finished {
            return;
        }
        self.seconds -= delta;
        let mut label = self.base().get_node_as::<Label>("TimeLabel");
        if self.seconds <= 0.0 {
            self.finished = true;
            label.set_text("Time's up!");
            godot_print!("Time's up!");
            self.base().get_tree().set_pause(true);
        } else {
            label.set_text(&format!("Time: {}", self.seconds.ceil() as i32));
        }
    }
}
'''

COUNTDOWN_SCENE = TOPDOWN_SCENE + '''
[node name="Countdown" type="Countdown" parent="."]
seconds = 2.0

[node name="TimeLabel" type="Label" parent="Countdown"]
offset_left = 900.0
offset_top = 16.0
offset_right = 1130.0
offset_bottom = 60.0
theme_override_font_sizes/font_size = 32
text = "Time:"
horizontal_alignment = 2
'''

FEATURES["countdown"] = dict(
    requires=["topdown_body"],
    prompts=[
        "Add a timer that counts down and ends the game",
        "I want a 60 second time limit",
        "countdown clock in the corner",
        "make it a race against time",
    ],
    new_nodes=[("Countdown", "CanvasLayer")],
    files={"rust/src/countdown.rs": COUNTDOWN, "main.tscn": COUNTDOWN_SCENE},
    run=4,
    intro=["A race against the clock, exciting! Let me look at the project."],
    final=["There's now a countdown in the top-right corner. When it reaches zero it shows **Time's up!** and freezes the game.\n\nI set it to 2 seconds so you can see it end right away; change **Seconds** on the **Countdown** node in the Inspector to 60 for a real round.\n\nPress **Play** (F5)! Idea: coins could add 3 seconds to the clock when collected."],
)

# ------------------------------------------------------------------ title screen
TITLE_SCREEN = '''use godot::classes::{Button, Control, IControl};
use godot::prelude::*;

/// The first thing players see. The Start button loads the game.
#[derive(GodotClass)]
#[class(base = Control)]
pub struct TitleScreen {
    base: Base<Control>,
}

#[godot_api]
impl IControl for TitleScreen {
    fn init(base: Base<Control>) -> Self {
        Self { base }
    }

    fn ready(&mut self) {
        let button = self.base().get_node_as::<Button>("StartButton");
        button.signals().pressed().connect_other(&self.to_gd(), Self::on_start_pressed);
    }
}

#[godot_api]
impl TitleScreen {
    fn on_start_pressed(&mut self) {
        self.base().get_tree().change_scene_to_file("res://main.tscn");
    }
}
'''

TITLE_SCENE = '''[gd_scene format=3]

[node name="TitleScreen" type="TitleScreen"]
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0

[node name="Background" type="ColorRect" parent="."]
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
color = Color(0.12, 0.09, 0.08, 1)

[node name="Title" type="Label" parent="."]
anchors_preset = 10
anchor_right = 1.0
offset_top = 180.0
offset_bottom = 280.0
theme_override_colors/font_color = Color(0.85, 0.5, 0.2, 1)
theme_override_font_sizes/font_size = 72
text = "My Awesome Game"
horizontal_alignment = 1

[node name="StartButton" type="Button" parent="."]
anchors_preset = 8
anchor_left = 0.5
anchor_top = 0.5
anchor_right = 0.5
anchor_bottom = 0.5
offset_left = -110.0
offset_top = 40.0
offset_right = 110.0
offset_bottom = 110.0
theme_override_font_sizes/font_size = 36
text = "Start"
'''

FEATURES["title_screen"] = dict(
    prompts=[
        "Make a title screen with a start button",
        "I want a main menu",
        "add a start menu before the game",
        "title screen please! with my game's name",
    ],
    new_nodes=[("TitleScreen", "Control")],
    files={"rust/src/title_screen.rs": TITLE_SCREEN, "title.tscn": TITLE_SCENE},
    edits=[("project.godot", 'run/main_scene="res://main.tscn"', 'run/main_scene="res://title.tscn"')],
    run=2,
    intro=["A title screen makes it feel like a real game! Let me look around first."],
    final=["Your game now opens on a title screen with a big **Start** button; clicking it loads the game. I made `title.tscn` the first scene that runs.\n\nPress **Play** (F5) to see it. To rename the game, select the **Title** label and change its text in the Inspector.\n\nWhat's your game called? I'd love to put the real name on it!"],
)

# ------------------------------------------------------------------ coin spawner
SPAWNER_GAME = '''use godot::classes::{INode2D, Node2D, PackedScene, Timer};
use godot::global::randf_range;
use godot::prelude::*;

use crate::coin::Coin;
use crate::hud::Hud;

/// The main scene's brain: spawns a new coin every few seconds and hooks it to the score.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Game {
    /// The coin scene to spawn (coin.tscn).
    #[export]
    coin_scene: OnEditor<Gd<PackedScene>>,
    /// Seconds between new coins.
    #[export]
    spawn_every: f64,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Game {
    fn init(base: Base<Node2D>) -> Self {
        Self { coin_scene: OnEditor::default(), spawn_every: 1.5, base }
    }

    fn ready(&mut self) {
        let hud = self.base().get_node_as::<Hud>("Hud");
        for child in self.base().get_children().iter_shared() {
            if let Ok(coin) = child.try_cast::<Coin>() {
                coin.signals().collected().connect_other(&hud, Hud::add_score);
            }
        }

        let mut timer = Timer::new_alloc();
        timer.set_wait_time(self.spawn_every);
        timer.set_autostart(true);
        timer.signals().timeout().connect_other(&self.to_gd(), Self::spawn_coin);
        self.base_mut().add_child(&timer);
    }
}

#[godot_api]
impl Game {
    fn spawn_coin(&mut self) {
        let mut coin = self.coin_scene.instantiate_as::<Coin>();
        let x = randf_range(60.0, 1090.0) as f32;
        let y = randf_range(60.0, 590.0) as f32;
        coin.set_position(Vector2::new(x, y));
        let hud = self.base().get_node_as::<Hud>("Hud");
        coin.signals().collected().connect_other(&hud, Hud::add_score);
        self.base_mut().add_child(&coin);
    }
}
'''

SPAWNER_SCENE = HUD_MAIN_SCENE.replace('[node name="Main" type="Game"]\n',
                                       '[node name="Main" type="Game"]\ncoin_scene = ExtResource("2_coin")\n')

FEATURES["coin_spawner"] = dict(
    requires=["topdown_body", "coins", "score_hud"],
    prompts=[
        "Make new coins keep appearing at random spots",
        "spawn coins every couple seconds",
        "more coins!! they should keep popping up",
        "coins should spawn faster and faster... or at least keep spawning",
    ],
    files={"rust/src/game.rs": SPAWNER_GAME, "main.tscn": SPAWNER_SCENE},
    run=4,
    intro=["Endless coins, the frantic race begins! Let me look at the game code."],
    final=["New coins now pop up at random spots every 1.5 seconds, and each one adds to your score. I added a **Timer** in code that calls `spawn_coin` again and again.\n\nPress **Play** (F5) and see how many you can grab! Change **Spawn Every** on the Main node to speed it up.\n\nIdea: coins that vanish after a few seconds if you don't catch them!"],
)

# ------------------------------------------------------------------ high score saving
HIGHSCORE_HUD = '''use godot::classes::file_access::ModeFlags;
use godot::classes::{CanvasLayer, FileAccess, ICanvasLayer, Label};
use godot::prelude::*;

const SAVE_PATH: &str = "user://best_score.txt";

/// Shows the score and the best score ever, which is saved between games.
#[derive(GodotClass)]
#[class(base = CanvasLayer)]
pub struct Hud {
    score: i32,
    best: i32,
    base: Base<CanvasLayer>,
}

#[godot_api]
impl ICanvasLayer for Hud {
    fn init(base: Base<CanvasLayer>) -> Self {
        Self { score: 0, best: 0, base }
    }

    fn ready(&mut self) {
        self.best = load_best();
        self.refresh();
    }
}

#[godot_api]
impl Hud {
    #[func]
    pub fn add_score(&mut self, amount: i32) {
        self.score += amount;
        if self.score > self.best {
            self.best = self.score;
            save_best(self.best);
        }
        self.refresh();
    }

    fn refresh(&mut self) {
        let text = format!("Score: {}   Best: {}", self.score, self.best);
        let mut label = self.base().get_node_as::<Label>("ScoreLabel");
        label.set_text(&text);
    }
}

/// Reads the saved best score (0 if there is none yet).
fn load_best() -> i32 {
    match FileAccess::open(SAVE_PATH, ModeFlags::READ) {
        Some(file) => file.get_as_text().to_string().trim().parse().unwrap_or(0),
        None => 0,
    }
}

fn save_best(best: i32) {
    if let Some(mut file) = FileAccess::open(SAVE_PATH, ModeFlags::WRITE) {
        file.store_string(&best.to_string());
    }
}
'''

FEATURES["high_score"] = dict(
    requires=["topdown_body", "coins", "score_hud"],
    prompts=[
        "Save my best score so it's still there next time",
        "add a high score that saves",
        "I want to see my best score ever",
        "remember the high score between games",
    ],
    files={"rust/src/hud.rs": HIGHSCORE_HUD},
    run=3,
    intro=["A high score gives players a reason to come back! Let me look at the score code."],
    final=["Your best score is now saved! The corner shows **Score** and **Best**, and whenever you beat your best it's written to a small file in your game's save folder (`user://best_score.txt`), so it survives closing the game.\n\nPress **Play** (F5), collect some coins, then play again to see your best score waiting for you.\n\nIdea: show a little \"New record!\" message when you beat it."],
)

# ------------------------------------------------------------------ first 3D scene
SPINNER_3D = '''use godot::classes::{IMeshInstance3D, MeshInstance3D};
use godot::prelude::*;

/// A 3D object that slowly spins and bobs, like a treasure on display.
#[derive(GodotClass)]
#[class(base = MeshInstance3D)]
pub struct Spinner {
    /// Turns per second.
    #[export]
    spin_speed: f32,
    time: f32,
    base: Base<MeshInstance3D>,
}

#[godot_api]
impl IMeshInstance3D for Spinner {
    fn init(base: Base<MeshInstance3D>) -> Self {
        Self { spin_speed: 0.3, time: 0.0, base }
    }

    fn process(&mut self, delta: f64) {
        let dt = delta as f32;
        self.time += dt;
        let angle = self.spin_speed * std::f32::consts::TAU * dt;
        self.base_mut().rotate_y(angle);
        let mut position = self.base().get_position();
        position.y = (self.time * 2.0).sin() * 0.2;
        self.base_mut().set_position(position);
    }
}
'''

WORLD_3D_SCENE = '''[gd_scene format=3]

[sub_resource type="StandardMaterial3D" id="StandardMaterial3D_rust"]
albedo_color = Color(0.72, 0.36, 0.16, 1)
metallic = 0.6
roughness = 0.45

[sub_resource type="BoxMesh" id="BoxMesh_cube"]
material = SubResource("StandardMaterial3D_rust")

[sub_resource type="PlaneMesh" id="PlaneMesh_floor"]
size = Vector2(10, 10)

[node name="World" type="Node3D"]

[node name="Camera3D" type="Camera3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 0.94, 0.34, 0, -0.34, 0.94, 0, 1.4, 3.2)

[node name="Sun" type="DirectionalLight3D" parent="."]
transform = Transform3D(0.87, -0.25, 0.43, 0, 0.87, 0.5, -0.5, -0.43, 0.75, 0, 4, 0)
shadow_enabled = true

[node name="Spinner" type="Spinner" parent="."]
mesh = SubResource("BoxMesh_cube")

[node name="Floor" type="MeshInstance3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, -0.8, 0)
mesh = SubResource("PlaneMesh_floor")
'''

FEATURES["first_3d"] = dict(
    prompts=[
        "Can I make something in 3D?",
        "show me a 3D scene",
        "I want to try 3D, maybe a spinning cube",
        "make a 3d object that rotates",
    ],
    new_nodes=[("Spinner", "MeshInstance3D")],
    files={"rust/src/spinner.rs": SPINNER_3D, "world.tscn": WORLD_3D_SCENE},
    edits=[("project.godot", 'run/main_scene="res://main.tscn"', 'run/main_scene="res://world.tscn"')],
    run=2,
    intro=["Yes, let's go 3D! RusticEngine does both. Let me look at the project first."],
    final=["Welcome to 3D! I made a new scene, `world.tscn`, with a rusty metal cube that spins and gently bobs above a floor, plus a camera and a sun that casts shadows. It's now the scene that runs when you press Play.\n\nPress **Play** (F5) to see it. Open `world.tscn` and switch to the **3D** view at the top to look around it in the editor.\n\nYour 2D game is still safe in `main.tscn`. Idea: a little 3D character that walks around the floor?"],
)

# ------------------------------------------------------------------ explain the starter project
FEATURES["explain_starter"] = dict(
    prompts=[
        "Explain how my project works, simply",
        "what's in my project?",
        "I'm new, what am I looking at",
        "how does this starter game work",
        "can you walk me through the files",
    ],
    explain=["main.tscn", "rust/src/player.rs", "rust/src/lib.rs"],
    intro=["Happy to! Let me look through your project.", "Great question. Let me peek at the files first."],
    final=["Here's your game in a nutshell:\n\n"
           "- **`main.tscn`** is the level (a *scene*). It holds a **Player** node with a **Sprite2D** child, the picture you see.\n"
           "- **`rust/src/player.rs`** is the Player's brain. Every frame, `process` reads the arrow keys and moves the player by `speed` pixels per second. "
           "`ready` runs once at the start and prints a hello.\n"
           "- **`rust/src/lib.rs`** is the front door of your Rust code: each `mod` line plugs in one file.\n\n"
           "When you press **Play**, RusticEngine builds the Rust code and starts `main.tscn`.\n\n"
           "Want to try a first change? We could make the player spin, sprint with Shift, or wrap around the screen edges.",
           "Your project has three important pieces:\n\n"
           "1. **The scene** (`main.tscn`): the level, with a Player and its picture (a Sprite2D).\n"
           "2. **The player code** (`rust/src/player.rs`): it reads the arrow keys in `process` and moves the player. The `speed` value is marked `#[export]`, so you can change it in the Inspector.\n"
           "3. **`lib.rs`**: lists your Rust files so the engine can find them.\n\n"
           "Press **Play** (F5) to run it. What would you like the player to do next?"],
)
