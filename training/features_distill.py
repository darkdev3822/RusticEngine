"""Gold features, round 3 ("distilled"): written to teach *how* to build, not recipes.
- Many different mechanics, each replayed only a few times (round 2 overfit on repeated templates).
- `lookups`: check the real API with class_info before using an unfamiliar class (Ember's main failure
  is inventing methods).
- Small `edits` instead of whole-file rewrites where that's what a careful developer would do.
Keep these clear of eval_agent.py's tasks.
"""

PLAYER_IMPORTS = "use godot::classes::{INode2D, Input, Node2D};"
PLAYER_MOVE_END = "        self.base_mut().set_position(position + step);\n    }"
BASE_SCENE_PLAYER = '''[gd_scene format=3]

[ext_resource type="Texture2D" path="res://icon.svg" id="1_icon"]
{subs}
[node name="Main" type="Node2D"]

[node name="Player" type="Player" parent="."]
position = Vector2(576, 324)

[node name="Sprite2D" type="Sprite2D" parent="Player"]
texture = ExtResource("1_icon")
'''


def scene(extra_nodes: str, subs: str = "") -> str:
    return BASE_SCENE_PLAYER.replace("{subs}", subs) + extra_nodes


FEATURES = {}

# ---------------------------------------------------------------- Timer created in code
BLINK = '''use godot::classes::{INode2D, Input, Node2D, Timer};
use godot::prelude::*;

/// Moves with the arrow keys and blinks on and off, driven by a Timer.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Player {
    #[export]
    speed: f32,
    /// Seconds between blinks.
    #[export]
    blink_every: f64,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Player {
    fn init(base: Base<Node2D>) -> Self {
        Self { speed: 300.0, blink_every: 0.5, base }
    }

    fn ready(&mut self) {
        // A Timer node fires its `timeout` signal every `wait_time` seconds.
        let mut timer = Timer::new_alloc();
        timer.set_wait_time(self.blink_every);
        timer.set_autostart(true);
        timer.signals().timeout().connect_other(&self.to_gd(), Self::blink);
        self.base_mut().add_child(&timer);
    }

    fn process(&mut self, delta: f64) {
        let input = Input::singleton();
        let direction = input.get_vector("ui_left", "ui_right", "ui_up", "ui_down");
        let step = direction * self.speed * delta as f32;
        let position = self.base().get_position();
        self.base_mut().set_position(position + step);
    }
}

#[godot_api]
impl Player {
    fn blink(&mut self) {
        let visible = self.base().is_visible();
        self.base_mut().set_visible(!visible);
    }
}
'''

FEATURES["blink_timer"] = dict(
    prompts=["make the player blink on and off", "I want my character to flash like it's invincible",
             "blinking player effect please", "can the player flicker every half second?"],
    lookups=[("Timer", "")],
    files={"rust/src/player.rs": BLINK}, run=2,
    intro=["Blinking! I'll use a Timer for that. Let me read the player first."],
    final=["The player now blinks every half second. I made a **Timer** in code: every time it runs out it fires `timeout`, "
           "and that calls a little `blink` function that flips `visible`.\n\nPress **Play** (F5) to see it. "
           "**Blink Every** in the Inspector changes the speed.\n\nIdea: blink only for two seconds after getting hit, like classic invincibility frames.",
           "Your player flickers now! A Timer ticks every 0.5 seconds and each tick hides or shows the player.\n\n"
           "Try it with **Play** (F5), and tweak **Blink Every** in the Inspector."],
)

# ---------------------------------------------------------------- input(): mouse button events
CLICK_PRINT_EDIT_IMPORT = (PLAYER_IMPORTS, "use godot::classes::{INode2D, Input, InputEvent, InputEventMouseButton, Node2D};\nuse godot::global::MouseButton;")
CLICK_PRINT_EDIT_BODY = (PLAYER_MOVE_END, PLAYER_MOVE_END + '''

    fn input(&mut self, event: Gd<InputEvent>) {
        // Only mouse-button events, only the moment the left button goes down.
        if let Ok(click) = event.try_cast::<InputEventMouseButton>() {
            if click.is_pressed() && click.get_button_index() == MouseButton::LEFT {
                godot_print!("You clicked at {}", click.get_position());
            }
        }
    }''')

FEATURES["click_print"] = dict(
    prompts=["print where I click in the output", "when I click the mouse, tell me the position",
             "log my mouse clicks", "I want to see the coordinates of each left click"],
    lookups=[("InputEventMouseButton", "")],
    edits=[("rust/src/player.rs",) + CLICK_PRINT_EDIT_IMPORT, ("rust/src/player.rs",) + CLICK_PRINT_EDIT_BODY], run=2,
    intro=["Handy for placing things! Let me look at the player code."],
    final=["Every left click now prints its position in the **Output** panel, like `You clicked at (412, 230)`. "
           "I added an `input` function: Godot calls it for every key press, click and mouse move, and I only react to left-button presses.\n\n"
           "Press **Play** (F5) and click around. Those numbers are handy when you want to place things in your scene!"],
)

# ---------------------------------------------------------------- input(): key events
ENTER_EDIT_IMPORT = (PLAYER_IMPORTS, "use godot::classes::{INode2D, Input, InputEvent, InputEventKey, Node2D};\nuse godot::global::Key;")
ENTER_EDIT_BODY = (PLAYER_MOVE_END, PLAYER_MOVE_END + '''

    fn input(&mut self, event: Gd<InputEvent>) {
        if let Ok(key) = event.try_cast::<InputEventKey>() {
            // is_echo() is true for the repeats you get while holding a key; skip those.
            if key.is_pressed() && !key.is_echo() && key.get_keycode() == Key::ENTER {
                let position = self.base().get_position();
                self.base_mut().set_position(position + Vector2::new(0.0, -80.0));
                godot_print!("Boing!");
            }
        }
    }''')

FEATURES["enter_hop_up"] = dict(
    prompts=["when I press enter, move the player up a bit", "make Enter push the player upward",
             "press enter to jump up 80 pixels", "Enter key = teleport up a little"],
    lookups=[("InputEventKey", "key")],
    edits=[("rust/src/player.rs",) + ENTER_EDIT_IMPORT, ("rust/src/player.rs",) + ENTER_EDIT_BODY], run=2,
    intro=["Sure! Let me check the player code first."],
    final=["Press **Enter** and the player pops up 80 pixels (and prints \"Boing!\"). I used an `input` function that "
           "listens for key events, and I ignore *echo* events so holding Enter only moves you once.\n\nTry it with **Play** (F5)."],
)

# ---------------------------------------------------------------- Camera2D
CAMERA_ZOOM = '''use godot::classes::{Camera2D, ICamera2D, Input};
use godot::global::Key;
use godot::prelude::*;

/// A camera that follows its parent and zooms with + and -.
#[derive(GodotClass)]
#[class(base = Camera2D)]
pub struct ZoomCamera {
    /// How fast holding + or - zooms.
    #[export]
    zoom_speed: f32,
    base: Base<Camera2D>,
}

#[godot_api]
impl ICamera2D for ZoomCamera {
    fn init(base: Base<Camera2D>) -> Self {
        Self { zoom_speed: 1.5, base }
    }

    fn process(&mut self, delta: f64) {
        let input = Input::singleton();
        let mut change = 0.0;
        if input.is_key_pressed(Key::EQUAL) { change += 1.0; } // the + key (shares a key with =)
        if input.is_key_pressed(Key::MINUS) { change -= 1.0; }
        if change != 0.0 {
            let zoom = self.base().get_zoom().x;
            let new_zoom = (zoom * (1.0 + change * self.zoom_speed * delta as f32)).clamp(0.5, 3.0);
            self.base_mut().set_zoom(Vector2::new(new_zoom, new_zoom));
        }
    }
}
'''

FEATURES["camera_zoom"] = dict(
    prompts=["add a camera that follows me and can zoom in and out", "I want to zoom with plus and minus",
             "camera zoom controls please", "follow camera with zoom"],
    lookups=[("Camera2D", "zoom")],
    new_nodes=[("ZoomCamera", "Camera2D")],
    files={"rust/src/zoom_camera.rs": CAMERA_ZOOM,
           "main.tscn": scene('\n[node name="ZoomCamera" type="ZoomCamera" parent="Player"]\n')}, run=2,
    intro=["A zoomable camera, nice. Let me look at the project first."],
    final=["You've got a camera now! It's a child of the Player, so it follows you everywhere. Hold **+** to zoom in and **-** to zoom out "
           "(it stops at 0.5x and 3x so you can't get lost).\n\nPress **Play** (F5) to try it. **Zoom Speed** in the Inspector changes how quickly it zooms.",
           "I added a **ZoomCamera** that rides along with the player. **+** zooms in, **-** zooms out.\n\n"
           "Press **Play** (F5). Since the camera follows you, your world can now be bigger than the screen!"],
)

# ---------------------------------------------------------------- Tween on a child node
HOP = '''use godot::classes::{INode2D, Input, Node2D, Sprite2D};
use godot::global::Key;
use godot::prelude::*;

/// Press J for a little hop: the sprite jumps up and lands, while the player itself stays put.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Player {
    #[export]
    speed: f32,
    j_was_down: bool,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Player {
    fn init(base: Base<Node2D>) -> Self {
        Self { speed: 300.0, j_was_down: false, base }
    }

    fn process(&mut self, delta: f64) {
        let input = Input::singleton();
        let direction = input.get_vector("ui_left", "ui_right", "ui_up", "ui_down");
        let step = direction * self.speed * delta as f32;
        let position = self.base().get_position();
        self.base_mut().set_position(position + step);

        let j_down = input.is_key_pressed(Key::J);
        if j_down && !self.j_was_down {
            self.hop();
        }
        self.j_was_down = j_down;
    }
}

impl Player {
    fn hop(&mut self) {
        let sprite = self.base().get_node_as::<Sprite2D>("Sprite2D");
        // A Tween animates a property over time. Steps run one after another: up, then back down.
        let mut tween = self.base_mut().create_tween();
        tween.tween_property(&sprite, "position", &Vector2::new(0.0, -40.0).to_variant(), 0.15);
        tween.tween_property(&sprite, "position", &Vector2::ZERO.to_variant(), 0.2);
    }
}
'''

FEATURES["tween_hop"] = dict(
    prompts=["press J to make the player do a little hop", "add a cute bounce animation on J",
             "I want a hop animation when I press a key", "make the sprite jump up and down when I hit J"],
    lookups=[("Tween", "tween_property")],
    files={"rust/src/player.rs": HOP}, run=2,
    intro=["A hop! I'll animate it with a Tween. Let me read the player code."],
    final=["Press **J** and the player does a little hop! I used a **Tween**, Godot's built-in animator: it moves the "
           "Sprite2D up 40 pixels in 0.15 seconds, then back down. Only the picture hops, so your movement isn't affected.\n\n"
           "Press **Play** (F5) and try it. Idea: tweens can animate almost anything, like color, size or rotation!"],
)

# ---------------------------------------------------------------- exported node reference via NodePath
PET = '''use godot::classes::{INode2D, Node2D};
use godot::prelude::*;

/// A little pet that follows a target node, lagging behind a bit.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Pet {
    /// Who to follow (drag a node here in the Inspector).
    #[export]
    target: Option<Gd<Node2D>>,
    /// Higher = keeps up more closely.
    #[export]
    follow_speed: f32,
    /// How close it gets before it stops.
    #[export]
    keep_distance: f32,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Pet {
    fn init(base: Base<Node2D>) -> Self {
        Self { target: None, follow_speed: 3.0, keep_distance: 60.0, base }
    }

    fn process(&mut self, delta: f64) {
        let Some(goal) = self.target.as_ref().map(|t| t.get_global_position()) else { return };
        let here = self.base().get_global_position();
        if here.distance_to(goal) > self.keep_distance {
            // Move part of the way there each frame: fast when far, gentle when close.
            let weight = (self.follow_speed * delta as f32).min(1.0);
            self.base_mut().set_global_position(here.lerp(goal, weight));
        }
    }
}
'''

FEATURES["pet_follow"] = dict(
    prompts=["add a little pet that follows me around", "I want a companion that trails behind the player",
             "make a buddy that follows my character", "can I have a sidekick that chases after me?"],
    new_nodes=[("Pet", "Node2D")],
    files={"rust/src/pet.rs": PET, "main.tscn": scene('''
[node name="Pet" type="Pet" parent="." node_paths=PackedStringArray("target")]
position = Vector2(480, 324)
target = NodePath("../Player")

[node name="Sprite2D" type="Sprite2D" parent="Pet"]
modulate = Color(1, 0.8, 0.4, 1)
scale = Vector2(0.4, 0.4)
texture = ExtResource("1_icon")
''')}, run=3,
    intro=["A pet! Let me look around the project first.", "Every hero needs a sidekick. Let me check the project."],
    final=["Meet your pet: the small orange one! It follows the Player, lagging behind a little, and stops when it's close. "
           "It uses `lerp`, which means \"move part of the way there\" each frame.\n\nPress **Play** (F5) and run around. "
           "In the Inspector, **Target** is who it follows (try dragging a different node there!), and **Follow Speed** makes it keep up better."],
)

# ---------------------------------------------------------------- DisplayServer + Engine
TITLE_EDIT_IMPORT = (PLAYER_IMPORTS, "use godot::classes::{DisplayServer, Engine, INode2D, Input, Node2D};")
TITLE_EDIT_BODY = (PLAYER_MOVE_END, '''        self.base_mut().set_position(position + step);

        // Show the frames per second in the window title.
        let fps = Engine::singleton().get_frames_per_second();
        DisplayServer::singleton().window_set_title(&format!("My Rust Game - {fps:.0} FPS"));
    }''')

FEATURES["window_title_fps"] = dict(
    prompts=["show the FPS in the window title", "change the window title to my game's name with the fps",
             "how fast is my game running? put fps in the title bar"],
    lookups=[("DisplayServer", "title"), ("Engine", "frames")],
    edits=[("rust/src/player.rs",) + TITLE_EDIT_IMPORT, ("rust/src/player.rs",) + TITLE_EDIT_BODY], run=2,
    intro=["Good idea for checking performance! Let me look at the player code."],
    final=["The window title now says **My Rust Game - 60 FPS** (or whatever your speed is). `Engine` knows the frame rate, "
           "and `DisplayServer` controls the window.\n\nPress **Play** (F5) and look at the title bar. Want your own game name there? "
           "Change the text in `rust/src/player.rs`."],
)

# ---------------------------------------------------------------- DisplayServer window mode
FULLSCREEN = '''use godot::classes::display_server::WindowMode;
use godot::classes::{DisplayServer, INode2D, Input, Node2D};
use godot::global::Key;
use godot::prelude::*;

#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Player {
    #[export]
    speed: f32,
    f11_was_down: bool,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Player {
    fn init(base: Base<Node2D>) -> Self {
        Self { speed: 300.0, f11_was_down: false, base }
    }

    fn process(&mut self, delta: f64) {
        let input = Input::singleton();
        let direction = input.get_vector("ui_left", "ui_right", "ui_up", "ui_down");
        let step = direction * self.speed * delta as f32;
        let position = self.base().get_position();
        self.base_mut().set_position(position + step);

        let f11_down = input.is_key_pressed(Key::F11);
        if f11_down && !self.f11_was_down {
            let mut display = DisplayServer::singleton();
            let mode = if display.window_get_mode() == WindowMode::FULLSCREEN { WindowMode::WINDOWED } else { WindowMode::FULLSCREEN };
            display.window_set_mode(mode);
        }
        self.f11_was_down = f11_down;
    }
}
'''

FEATURES["fullscreen_toggle"] = dict(
    prompts=["F11 should toggle fullscreen", "let me go fullscreen", "add a fullscreen button", "how do I make the game fullscreen?"],
    lookups=[("DisplayServer", "window_set_mode")],
    files={"rust/src/player.rs": FULLSCREEN}, run=2,
    intro=["Fullscreen coming up. Let me read the player code first."],
    final=["Press **F11** to switch between fullscreen and a window. `DisplayServer` is Godot's window manager, and "
           "`WindowMode` lists the options (windowed, maximized, fullscreen...).\n\nTry it with **Play** (F5). "
           "Tip: you can also set the starting window mode in **Project > Project Settings > Display > Window**."],
)

# ---------------------------------------------------------------- SceneTree::quit
QUIT_EDIT_IMPORT = (PLAYER_IMPORTS, "use godot::classes::{INode2D, Input, Node2D};\nuse godot::global::Key;")
QUIT_EDIT_BODY = (PLAYER_MOVE_END, '''        self.base_mut().set_position(position + step);

        if input.is_key_pressed(Key::ESCAPE) {
            // Closes the game window (like pressing Stop in the editor).
            self.base().get_tree().quit();
        }
    }''')

FEATURES["quit_escape"] = dict(
    prompts=["Escape should close the game", "add a quit key", "let me press esc to exit", "make escape quit"],
    edits=[("rust/src/player.rs",) + QUIT_EDIT_IMPORT, ("rust/src/player.rs",) + QUIT_EDIT_BODY], run=2,
    intro=["Easy one! Let me look at the player code."],
    final=["Press **Escape** and the game closes. It's two small additions: importing `Key`, and calling `get_tree().quit()` "
           "when Escape is held.\n\nTry it with **Play** (F5). Later, this is a nice spot for a \"Are you sure?\" menu instead!"],
)

# ---------------------------------------------------------------- custom drawing
RING = '''use godot::classes::{INode2D, Node2D};
use godot::prelude::*;

/// Draws a ring. Put it under a node to circle it.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Ring {
    #[export]
    radius: f32,
    #[export]
    color: Color,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Ring {
    fn init(base: Base<Node2D>) -> Self {
        Self { radius: 80.0, color: Color::from_rgba(0.4, 1.0, 0.6, 0.8), base }
    }

    // Godot calls draw() when the node needs painting; call queue_redraw() to ask for it again.
    fn draw(&mut self) {
        let (radius, color) = (self.radius, self.color);
        self.base_mut().draw_arc(Vector2::ZERO, radius, 0.0, std::f32::consts::TAU, 64, color);
    }
}
'''

FEATURES["draw_ring"] = dict(
    prompts=["draw a circle around my player", "I want a ring around the character", "show a range circle around the player",
             "can you draw a green circle outline around me?"],
    lookups=[("CanvasItem", "draw_arc")],
    new_nodes=[("Ring", "Node2D")],
    files={"rust/src/ring.rs": RING, "main.tscn": scene('\n[node name="Ring" type="Ring" parent="Player"]\n')}, run=2,
    intro=["Drawing shapes with code is fun. Let me look at the project."],
    final=["There's a green ring around your player now. The new **Ring** node paints itself with `draw_arc` in its `draw` function, "
           "and because it's a child of the Player it moves with you.\n\nPress **Play** (F5) to see it. Change **Radius** and **Color** in the Inspector.\n\n"
           "Idea: use it as an attack range, and make enemies inside it take damage!"],
)

# ---------------------------------------------------------------- physics, scene only
BALL_SUBS = '''
[sub_resource type="CircleShape2D" id="CircleShape2D_ball"]
radius = 32.0

[sub_resource type="RectangleShape2D" id="RectangleShape2D_floor"]
size = Vector2(1152, 40)
'''
BALL_NODES = '''
[node name="Ball" type="RigidBody2D" parent="."]
position = Vector2(300, 80)

[node name="Sprite2D" type="Sprite2D" parent="Ball"]
scale = Vector2(0.5, 0.5)
texture = ExtResource("1_icon")

[node name="CollisionShape2D" type="CollisionShape2D" parent="Ball"]
shape = SubResource("CircleShape2D_ball")

[node name="Floor" type="StaticBody2D" parent="."]
position = Vector2(576, 628)

[node name="ColorRect" type="ColorRect" parent="Floor"]
offset_left = -576.0
offset_top = -20.0
offset_right = 576.0
offset_bottom = 20.0
color = Color(0.3, 0.25, 0.2, 1)

[node name="CollisionShape2D" type="CollisionShape2D" parent="Floor"]
shape = SubResource("RectangleShape2D_floor")
'''

FEATURES["falling_ball"] = dict(
    prompts=["add a ball that falls with gravity and lands on a floor", "I want real physics, like a ball dropping",
             "drop something from the sky onto the ground", "add a floor and a bouncy physics ball"],
    files={"main.tscn": scene(BALL_NODES, BALL_SUBS)}, run=3,
    intro=["Physics! Godot can do this without any code. Let me look at the scene."],
    final=["I added a **Ball** that falls and lands on a brown **Floor**, no code needed! The ball is a `RigidBody2D` "
           "(Godot simulates gravity and collisions for it) and the floor is a `StaticBody2D` (solid, never moves). Both need a collision shape.\n\n"
           "Press **Play** (F5) and watch it drop. Want it bouncier? Select **Ball** and set a **Physics Material** with **Bounce** in the Inspector."],
)

CHAINS = [
    ["explain_starter", "tween_hop"],
]


# ================================================================ batch 2
from features_core import TOPDOWN_SCENE  # noqa: E402

UI_LAYER = '\n[node name="UI" type="CanvasLayer" parent="."]\n'

STAR = '''use godot::classes::{INode2D, Node2D, Sprite2D, Texture2D};
use godot::prelude::*;

/// A star that falls down the screen and removes itself when it's gone.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Star {
    #[export]
    fall_speed: f32,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Star {
    fn init(base: Base<Node2D>) -> Self {
        Self { fall_speed: 150.0, base }
    }

    fn ready(&mut self) {
        // Give the star a picture, made in code.
        let mut sprite = Sprite2D::new_alloc();
        sprite.set_texture(&load::<Texture2D>("res://icon.svg"));
        sprite.set_scale(Vector2::new(0.25, 0.25));
        sprite.set_modulate(Color::from_rgb(1.0, 0.95, 0.4));
        self.base_mut().add_child(&sprite);
    }

    fn process(&mut self, delta: f64) {
        let fall = self.fall_speed * delta as f32;
        let position = self.base().get_position() + Vector2::new(0.0, fall);
        self.base_mut().set_position(position);
        if position.y > 800.0 {
            self.base_mut().queue_free(); // off the bottom of the screen: delete it
        }
    }
}
'''

STAR_SPAWNER = '''use godot::classes::{INode2D, Node2D, Timer};
use godot::global::randf_range;
use godot::prelude::*;

use crate::star::Star;

/// Drops a new Star from a random spot at the top every few moments.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct StarSpawner {
    /// Seconds between stars.
    #[export]
    every: f64,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for StarSpawner {
    fn init(base: Base<Node2D>) -> Self {
        Self { every: 0.8, base }
    }

    fn ready(&mut self) {
        let mut timer = Timer::new_alloc();
        timer.set_wait_time(self.every);
        timer.set_autostart(true);
        timer.signals().timeout().connect_other(&self.to_gd(), Self::spawn);
        self.base_mut().add_child(&timer);
    }
}

#[godot_api]
impl StarSpawner {
    fn spawn(&mut self) {
        let mut star = Star::new_alloc();
        let x = randf_range(40.0, 1112.0) as f32;
        star.set_position(Vector2::new(x, -40.0));
        self.base_mut().add_child(&star);
    }
}
'''

FEATURES["star_spawner"] = dict(
    prompts=["make stars fall from the sky", "spawn things that drop from the top of the screen",
             "I want falling objects to dodge", "rain down little stars every second"],
    lookups=[("Timer", "wait_time")],
    new_nodes=[("Star", "Node2D"), ("StarSpawner", "Node2D")],
    files={"rust/src/star.rs": STAR, "rust/src/star_spawner.rs": STAR_SPAWNER,
           "main.tscn": scene('\n[node name="StarSpawner" type="StarSpawner" parent="."]\n')}, run=3,
    intro=["Falling stars! Let me look at the project first."],
    final=["Stars are falling! There are two new Rust nodes:\n- **Star** falls straight down and deletes itself (`queue_free`) once it's off the screen, so they don't pile up.\n"
           "- **StarSpawner** uses a Timer to create a new Star at a random spot along the top every 0.8 seconds.\n\n"
           "Press **Play** (F5) to watch. Change **Every** on StarSpawner for more or fewer stars.\n\nNext idea: make touching a star give you a point, or cost you a life!"],
)

HEALTH_BAR = '''use godot::classes::{IProgressBar, Input, ProgressBar};
use godot::global::Key;
use godot::prelude::*;

/// A health bar: K hurts, L heals. (A ProgressBar is a Range: it has a min, a max and a value.)
#[derive(GodotClass)]
#[class(base = ProgressBar)]
pub struct HealthBar {
    k_was_down: bool,
    l_was_down: bool,
    base: Base<ProgressBar>,
}

#[godot_api]
impl IProgressBar for HealthBar {
    fn init(base: Base<ProgressBar>) -> Self {
        Self { k_was_down: false, l_was_down: false, base }
    }

    fn ready(&mut self) {
        self.base_mut().set_max(100.0);
        self.base_mut().set_value(100.0);
    }

    fn process(&mut self, _delta: f64) {
        let input = Input::singleton();
        let (k, l) = (input.is_key_pressed(Key::K), input.is_key_pressed(Key::L));
        if k && !self.k_was_down { self.change(-10.0); }
        if l && !self.l_was_down { self.change(10.0); }
        self.k_was_down = k;
        self.l_was_down = l;
    }
}

impl HealthBar {
    fn change(&mut self, amount: f64) {
        let value = self.base().get_value() + amount; // the bar clamps it between 0 and 100 for us
        self.base_mut().set_value(value);
        if self.base().get_value() <= 0.0 {
            godot_print!("Game over!");
        }
    }
}
'''

FEATURES["health_bar"] = dict(
    prompts=["add a health bar", "I need an HP bar at the top of the screen", "show the player's health as a bar",
             "make a life bar I can test with keys"],
    lookups=[("ProgressBar", ""), ("Range", "value")],
    new_nodes=[("HealthBar", "ProgressBar")],
    files={"rust/src/health_bar.rs": HEALTH_BAR, "main.tscn": scene(UI_LAYER + '''
[node name="HealthBar" type="HealthBar" parent="UI"]
offset_left = 20.0
offset_top = 20.0
offset_right = 260.0
offset_bottom = 47.0
''')}, run=2,
    intro=["A health bar! Let me look at the scene first."],
    final=["There's a health bar in the top-left now. To test it, press **K** to take 10 damage and **L** to heal 10. "
           "At zero it prints \"Game over!\" in the Output panel.\n\nIt's a `ProgressBar`, which Godot keeps between its min (0) and max (100) for you. "
           "Press **Play** (F5) to try it.\n\nNext step: hook it up to real damage, like an enemy touching you!"],
)

CAVE_ZONE = '''use godot::classes::{Area2D, IArea2D, Node2D};
use godot::prelude::*;

use crate::player::Player;

/// An invisible area that notices when the player walks in or out.
#[derive(GodotClass)]
#[class(base = Area2D)]
pub struct CaveZone {
    base: Base<Area2D>,
}

#[godot_api]
impl IArea2D for CaveZone {
    fn init(base: Base<Area2D>) -> Self {
        Self { base }
    }

    fn ready(&mut self) {
        self.signals().body_entered().connect_self(Self::on_enter);
        self.signals().body_exited().connect_self(Self::on_exit);
    }
}

#[godot_api]
impl CaveZone {
    fn on_enter(&mut self, body: Gd<Node2D>) {
        if body.try_cast::<Player>().is_ok() {
            godot_print!("You entered the dark cave...");
            self.base_mut().set_modulate(Color::from_rgb(0.5, 0.5, 0.7));
        }
    }

    fn on_exit(&mut self, body: Gd<Node2D>) {
        if body.try_cast::<Player>().is_ok() {
            godot_print!("Back in the sunlight!");
            self.base_mut().set_modulate(Color::WHITE);
        }
    }
}
'''

CAVE_SCENE = TOPDOWN_SCENE.replace('''[node name="Main" type="Node2D"]''', '''[sub_resource type="RectangleShape2D" id="RectangleShape2D_cave"]
size = Vector2(300, 200)

[node name="Main" type="Node2D"]''') + '''
[node name="CaveZone" type="CaveZone" parent="."]
position = Vector2(250, 200)

[node name="ColorRect" type="ColorRect" parent="CaveZone"]
offset_left = -150.0
offset_top = -100.0
offset_right = 150.0
offset_bottom = 100.0
color = Color(0.2, 0.2, 0.3, 0.6)

[node name="CollisionShape2D" type="CollisionShape2D" parent="CaveZone"]
shape = SubResource("RectangleShape2D_cave")
'''

FEATURES["cave_zone"] = dict(
    requires=["topdown_body"],
    prompts=["make an area that says something when I walk into it", "add a zone that detects the player entering and leaving",
             "I want a cave area that gets darker when I'm inside", "trigger area for the player"],
    lookups=[("Area2D", "body")],
    new_nodes=[("CaveZone", "Area2D")],
    files={"rust/src/cave_zone.rs": CAVE_ZONE, "main.tscn": CAVE_SCENE}, run=2,
    intro=["Trigger zones are super useful. Let me look at the project first."],
    final=["I added a dark **CaveZone** in the top-left. It's an `Area2D`: it doesn't block you, it just notices bodies. "
           "Walk in and it prints \"You entered the dark cave...\" and gets darker; walk out and it says \"Back in the sunlight!\"\n\n"
           "Press **Play** (F5) and walk into it. Zones like this are great for checkpoints, doors, or starting a boss fight!"],
)

SPEED_BUTTON = '''use godot::classes::{Button, IButton};
use godot::prelude::*;

use crate::player::Player;

/// A button that makes the player faster every time it's clicked.
#[derive(GodotClass)]
#[class(base = Button)]
pub struct SpeedButton {
    /// The player to speed up (set in the Inspector).
    #[export]
    player: Option<Gd<Player>>,
    base: Base<Button>,
}

#[godot_api]
impl IButton for SpeedButton {
    fn init(base: Base<Button>) -> Self {
        Self { player: None, base }
    }

    fn ready(&mut self) {
        self.signals().pressed().connect_self(Self::on_pressed);
    }
}

#[godot_api]
impl SpeedButton {
    fn on_pressed(&mut self) {
        let Some(player) = self.player.as_mut() else { return };
        // bind_mut() opens the Rust side of another node so we can change its fields.
        let speed = {
            let mut p = player.bind_mut();
            p.speed *= 1.5;
            p.speed
        };
        self.base_mut().set_text(&format!("Faster! ({speed:.0})"));
    }
}
'''

FEATURES["speed_button"] = dict(
    prompts=["add a button on screen that makes the player faster", "I want a clickable button that speeds me up",
             "make a UI button that changes the player's speed", "put a Faster button in the corner"],
    lookups=[("BaseButton", "pressed")],
    new_nodes=[("SpeedButton", "Button")],
    edits=[("rust/src/player.rs", "    speed: f32,\n", "    pub speed: f32,\n")],
    files={"rust/src/speed_button.rs": SPEED_BUTTON, "main.tscn": scene(UI_LAYER + '''
[node name="SpeedButton" type="SpeedButton" parent="UI" node_paths=PackedStringArray("player")]
offset_left = 20.0
offset_top = 20.0
offset_right = 180.0
offset_bottom = 60.0
text = "Faster!"
player = NodePath("../../Player")
''')}, run=2,
    intro=["A button! Let me look at the player and the scene."],
    final=["There's a **Faster!** button in the top-left. Each click multiplies the player's speed by 1.5 and shows the new speed on the button.\n\n"
           "Two things made it work: I made the player's `speed` **pub** (so other Rust code can change it), and the button uses `bind_mut()` to reach into the Player. "
           "In the scene, the button's **Player** slot points at your Player node.\n\nPress **Play** (F5), click it a few times, and zoom!"],
)

WANDER = '''use godot::classes::{INode2D, Node2D};
use godot::global::randf_range;
use godot::prelude::*;

/// Wanders around on its own, picking a new random direction every couple of seconds.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Wanderer {
    #[export]
    speed: f32,
    /// Seconds before picking a new direction.
    #[export]
    change_every: f32,
    direction: Vector2,
    timer: f32,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Wanderer {
    fn init(base: Base<Node2D>) -> Self {
        Self { speed: 80.0, change_every: 2.0, direction: Vector2::ZERO, timer: 0.0, base }
    }

    fn process(&mut self, delta: f64) {
        let dt = delta as f32;
        self.timer -= dt;
        if self.timer <= 0.0 {
            let angle = randf_range(0.0, std::f64::consts::TAU) as f32;
            self.direction = Vector2::from_angle(angle);
            self.timer = self.change_every;
        }
        let next = self.base().get_position() + self.direction * self.speed * dt;
        self.base_mut().set_position(next);
    }
}
'''

FEATURES["wander_npc"] = dict(
    prompts=["add a villager that walks around randomly", "make an NPC that wanders", "I want a creature that roams on its own",
             "add a little guy who strolls around aimlessly"],
    new_nodes=[("Wanderer", "Node2D")],
    files={"rust/src/wanderer.rs": WANDER, "main.tscn": scene('''
[node name="Wanderer" type="Wanderer" parent="."]
position = Vector2(800, 300)

[node name="Sprite2D" type="Sprite2D" parent="Wanderer"]
modulate = Color(0.6, 1, 0.6, 1)
scale = Vector2(0.6, 0.6)
texture = ExtResource("1_icon")
''')}, run=3,
    intro=["A wandering villager, love it. Let me look around first."],
    final=["Say hi to the green **Wanderer**! Every 2 seconds it picks a random direction (`Vector2::from_angle` turns an angle into a direction) and strolls that way.\n\n"
           "Press **Play** (F5) to watch it roam. **Speed** and **Change Every** in the Inspector change its personality: try a fast, jittery one!"],
)

SPARKLE_NODES = '''
[node name="Sparkles" type="CPUParticles2D" parent="Player"]
amount = 40
lifetime = 0.8
emission_shape = 1
emission_sphere_radius = 24.0
gravity = Vector2(0, 40)
initial_velocity_min = 10.0
initial_velocity_max = 40.0
scale_amount_min = 2.0
scale_amount_max = 4.0
color = Color(1, 0.9, 0.4, 1)
'''

FEATURES["sparkles"] = dict(
    prompts=["make my player sparkle", "add particles around the character", "I want glitter coming off the player",
             "particle effect on the player please"],
    files={"main.tscn": scene(SPARKLE_NODES)}, run=2,
    intro=["Sparkles! Godot has a particle node for this, so it's just a scene change. Let me look at the scene."],
    final=["Your player sparkles now! I added a `CPUParticles2D` node called **Sparkles** under the Player. It sprays 40 little golden dots that drift down and fade.\n\n"
           "Press **Play** (F5) to see it. Select **Sparkles** in the Scene panel to play with it: **Amount**, **Lifetime**, **Gravity** and **Color** are fun ones to tweak, no code needed."],
)

WHEEL_EDIT_IMPORT = (PLAYER_IMPORTS, "use godot::classes::{INode2D, Input, InputEvent, InputEventMouseButton, Node2D};\nuse godot::global::MouseButton;")
WHEEL_EDIT_BODY = (PLAYER_MOVE_END, PLAYER_MOVE_END + '''

    fn input(&mut self, event: Gd<InputEvent>) {
        let Ok(wheel) = event.try_cast::<InputEventMouseButton>() else { return };
        if !wheel.is_pressed() { return }
        let button = wheel.get_button_index();
        if button == MouseButton::WHEEL_UP {
            self.speed = (self.speed + 25.0).min(1000.0);
        } else if button == MouseButton::WHEEL_DOWN {
            self.speed = (self.speed - 25.0).max(25.0);
        } else {
            return;
        }
        godot_print!("Speed: {}", self.speed);
    }''')

FEATURES["wheel_speed"] = dict(
    prompts=["use the mouse wheel to change how fast I move", "scroll up to go faster, scroll down to go slower",
             "mouse wheel controls speed", "let me adjust speed with the scroll wheel"],
    lookups=[("InputEventMouseButton", "button")],
    edits=[("rust/src/player.rs",) + WHEEL_EDIT_IMPORT, ("rust/src/player.rs",) + WHEEL_EDIT_BODY], run=2,
    intro=["Scroll-wheel speed control, nice and handy. Let me read the player."],
    final=["Scroll **up** to speed up and **down** to slow down (in steps of 25, between 25 and 1000). The new speed is printed in the Output panel each time.\n\n"
           "In Godot the scroll wheel counts as mouse *buttons* (`WHEEL_UP` and `WHEEL_DOWN`), which is why it's handled like a click. Press **Play** (F5) and scroll!"],
)

DAY_NIGHT = '''use godot::classes::{CanvasModulate, ICanvasModulate};
use godot::prelude::*;

/// Tints everything on screen, slowly going from day to night and back.
#[derive(GodotClass)]
#[class(base = CanvasModulate)]
pub struct DayNight {
    /// Seconds for a full day.
    #[export]
    day_length: f32,
    time: f32,
    base: Base<CanvasModulate>,
}

#[godot_api]
impl ICanvasModulate for DayNight {
    fn init(base: Base<CanvasModulate>) -> Self {
        Self { day_length: 20.0, time: 0.0, base }
    }

    fn process(&mut self, delta: f64) {
        self.time += delta as f32;
        let phase = self.time / self.day_length * std::f32::consts::TAU;
        let daylight = phase.cos() * 0.5 + 0.5; // 1 = noon, 0 = midnight
        let night = Color::from_rgb(0.25, 0.25, 0.5);
        let color = night.lerp(Color::WHITE, daylight as f64);
        self.base_mut().set_color(color);
    }
}
'''

FEATURES["day_night"] = dict(
    prompts=["add a day and night cycle", "make the whole screen get darker like night, then light again",
             "I want time of day in my game", "night falls slowly then morning comes"],
    lookups=[("CanvasModulate", "")],
    new_nodes=[("DayNight", "CanvasModulate")],
    files={"rust/src/day_night.rs": DAY_NIGHT, "main.tscn": scene('\n[node name="DayNight" type="DayNight" parent="."]\n')}, run=2,
    intro=["A day/night cycle adds so much mood. Let me look at the project."],
    final=["Your world now has days! The new **DayNight** node is a `CanvasModulate`, which tints everything drawn on screen. "
           "Over 20 seconds it fades from bright day to a blue night and back.\n\nPress **Play** (F5) and wait for nightfall. "
           "**Day Length** in the Inspector sets how long a day lasts.\n\nIdea: spawn spooky enemies only at night!"],
)

TYPEWRITER = '''use godot::classes::{ILabel, Label};
use godot::prelude::*;

/// Reveals its text one letter at a time, like a typewriter.
#[derive(GodotClass)]
#[class(base = Label)]
pub struct Typewriter {
    #[export]
    letters_per_second: f32,
    shown: f32,
    base: Base<Label>,
}

#[godot_api]
impl ILabel for Typewriter {
    fn init(base: Base<Label>) -> Self {
        Self { letters_per_second: 20.0, shown: 0.0, base }
    }

    fn ready(&mut self) {
        self.base_mut().set_visible_characters(0);
    }

    fn process(&mut self, delta: f64) {
        self.shown += self.letters_per_second * delta as f32;
        let count = self.shown as i32;
        self.base_mut().set_visible_characters(count);
    }
}
'''

FEATURES["typewriter"] = dict(
    prompts=["show a story message that types itself out letter by letter", "add an intro text with a typewriter effect",
             "I want dialogue text that appears one letter at a time", "typewriter text at the top of the screen"],
    lookups=[("Label", "visible_characters")],
    new_nodes=[("Typewriter", "Label")],
    files={"rust/src/typewriter.rs": TYPEWRITER, "main.tscn": scene(UI_LAYER + '''
[node name="Typewriter" type="Typewriter" parent="UI"]
offset_left = 40.0
offset_top = 30.0
offset_right = 1112.0
offset_bottom = 70.0
theme_override_font_sizes/font_size = 26
text = "Long ago, a brave hero set out on an adventure..."
''')}, run=2,
    intro=["A typewriter effect, very story-like. Let me look at the scene first."],
    final=["Your intro message now types itself out at the top of the screen. The **Typewriter** label has all the text from the start, "
           "but `visible_characters` hides everything past a growing count.\n\nPress **Play** (F5) to read it. "
           "To change the message, select **Typewriter** and edit **Text** in the Inspector; **Letters Per Second** sets the typing speed."],
)

CHAINS += [
]


# ================================================================ batch 3
ROCKS = '''use godot::classes::{CollisionShape2D, ColorRect, INode2D, Node2D, RectangleShape2D, StaticBody2D};
use godot::global::randf_range;
use godot::prelude::*;

/// Scatters solid rocks around the level when the game starts, all built in code.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct RockField {
    #[export]
    count: i32,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for RockField {
    fn init(base: Base<Node2D>) -> Self {
        Self { count: 8, base }
    }

    fn ready(&mut self) {
        for _ in 0..self.count {
            let size = Vector2::new(randf_range(40.0, 100.0) as f32, randf_range(40.0, 100.0) as f32);
            let mut rock = StaticBody2D::new_alloc();
            rock.set_position(Vector2::new(randf_range(60.0, 1092.0) as f32, randf_range(60.0, 588.0) as f32));

            // Solid shape for physics...
            let mut shape = RectangleShape2D::new_gd();
            shape.set_size(size);
            let mut collision = CollisionShape2D::new_alloc();
            collision.set_shape(&shape);
            rock.add_child(&collision);

            // ...and a gray box so we can see it (ColorRects start at their top-left corner).
            let mut look = ColorRect::new_alloc();
            look.set_size(size);
            look.set_position(-size / 2.0);
            look.set_color(Color::from_rgb(0.45, 0.42, 0.4));
            rock.add_child(&look);

            self.base_mut().add_child(&rock);
        }
    }
}
'''

ROCKS_SCENE = TOPDOWN_SCENE + '''
[node name="RockField" type="RockField" parent="."]
'''

FEATURES["rock_field"] = dict(
    requires=["topdown_body"],
    prompts=["scatter some random rocks around the map that I can't walk through", "generate obstacles randomly",
             "place random walls in the level every time it starts", "add random solid blocks to bump into"],
    lookups=[("StaticBody2D", ""), ("RectangleShape2D", "size")],
    new_nodes=[("RockField", "Node2D")],
    files={"rust/src/rock_field.rs": ROCKS, "main.tscn": ROCKS_SCENE}, run=2,
    intro=["Random obstacles make every run different. Let me look at the project first."],
    final=["Every time the game starts, **RockField** scatters 8 gray rocks of random sizes. Each one is built in code: a `StaticBody2D` (solid), "
           "a `CollisionShape2D` with a rectangle, and a `ColorRect` so you can see it.\n\nPress **Play** (F5) a few times: the layout changes each run, "
           "and your player bumps into the rocks. **Count** in the Inspector sets how many."],
)

TURRET = '''use godot::classes::{INode2D, Node2D};
use godot::prelude::*;

/// Always turns to face its target.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Turret {
    #[export]
    target: Option<Gd<Node2D>>,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Turret {
    fn init(base: Base<Node2D>) -> Self {
        Self { target: None, base }
    }

    fn process(&mut self, _delta: f64) {
        if let Some(goal) = self.target.as_ref().map(|t| t.get_global_position()) {
            // look_at points the node's right side (+x) at a spot in the world.
            self.base_mut().look_at(goal);
        }
    }
}
'''

FEATURES["turret_look"] = dict(
    prompts=["add a turret that always aims at me", "make something that watches the player and turns toward it",
             "I want a cannon that follows me with its barrel", "an eye that keeps looking at the player"],
    lookups=[("Node2D", "look_at")],
    new_nodes=[("Turret", "Node2D")],
    files={"rust/src/turret.rs": TURRET, "main.tscn": scene('''
[node name="Turret" type="Turret" parent="." node_paths=PackedStringArray("target")]
position = Vector2(150, 150)
target = NodePath("../Player")

[node name="Base" type="ColorRect" parent="Turret"]
offset_left = -24.0
offset_top = -24.0
offset_right = 24.0
offset_bottom = 24.0
color = Color(0.35, 0.35, 0.4, 1)

[node name="Barrel" type="ColorRect" parent="Turret"]
offset_top = -6.0
offset_right = 60.0
offset_bottom = 6.0
color = Color(0.8, 0.3, 0.3, 1)
''')}, run=2,
    intro=["A turret! Let me check the project first."],
    final=["There's a **Turret** in the top-left now, and its red barrel follows you wherever you go. It uses `look_at`, which turns a node so its right side points at a position.\n\n"
           "Press **Play** (F5) and walk around it. Next step could be making it shoot when you're close!"],
)

LEVEL2 = '''[gd_scene format=3]

[node name="Level2" type="Node2D"]

[node name="Label" type="Label" parent="."]
offset_left = 420.0
offset_top = 280.0
offset_right = 732.0
offset_bottom = 340.0
theme_override_font_sizes/font_size = 40
text = "Level 2!"
horizontal_alignment = 1
'''
NEXT_LEVEL_EDIT_IMPORT = (PLAYER_IMPORTS, "use godot::classes::{INode2D, Input, Node2D};\nuse godot::global::Key;")
NEXT_LEVEL_EDIT_BODY = (PLAYER_MOVE_END, '''        self.base_mut().set_position(position + step);

        if input.is_key_pressed(Key::N) {
            // Swap the whole running scene for another .tscn file.
            self.base().get_tree().change_scene_to_file("res://level2.tscn");
        }
    }''')

FEATURES["next_level"] = dict(
    prompts=["make a second level and go there when I press N", "how do I switch to another scene? add a level 2",
             "I want a new level that loads when I press N", "add level 2"],
    lookups=[("SceneTree", "change_scene")],
    files={"level2.tscn": LEVEL2},
    edits=[("rust/src/player.rs",) + NEXT_LEVEL_EDIT_IMPORT, ("rust/src/player.rs",) + NEXT_LEVEL_EDIT_BODY], run=2,
    intro=["Levels! Let me look at the project first."],
    final=["I made a new scene, **level2.tscn**, which just says \"Level 2!\" for now. Pressing **N** swaps to it with `change_scene_to_file`.\n\n"
           "Press **Play** (F5), then **N**. To build out level 2, double-click `level2.tscn` in the FileSystem panel and add things to it like any scene."],
)

FLOATING = '''use godot::classes::{ILabel, Label};
use godot::prelude::*;

/// Text that floats upward, shrinks away and deletes itself. Spawn one with FloatingText::spawn.
#[derive(GodotClass)]
#[class(base = Label)]
pub struct FloatingText {
    life: f32,
    base: Base<Label>,
}

#[godot_api]
impl ILabel for FloatingText {
    fn init(base: Base<Label>) -> Self {
        Self { life: 1.0, base }
    }

    fn process(&mut self, delta: f64) {
        let dt = delta as f32;
        self.life -= dt;
        if self.life <= 0.0 {
            self.base_mut().queue_free();
            return;
        }
        let up = self.base().get_position() + Vector2::new(0.0, -60.0 * dt);
        let size = self.life.max(0.0);
        self.base_mut().set_position(up);
        self.base_mut().set_scale(Vector2::new(size, size));
    }
}

impl FloatingText {
    pub fn spawn(parent: &mut Gd<Node>, text: &str, at: Vector2) {
        let mut label = FloatingText::new_alloc();
        label.set_text(text);
        label.set_position(at);
        parent.add_child(&label);
    }
}
'''
FLOAT_EDIT_IMPORT = (PLAYER_IMPORTS, "use godot::classes::{INode2D, Input, Node2D};\nuse godot::global::Key;\n\nuse crate::floating_text::FloatingText;")
FLOAT_EDIT_FIELDS = ("    speed: f32,\n", "    speed: f32,\n    x_was_down: bool,\n")
FLOAT_EDIT_INIT = ("Self { speed: 300.0, base }", "Self { speed: 300.0, x_was_down: false, base }")
FLOAT_EDIT_BODY = (PLAYER_MOVE_END, '''        self.base_mut().set_position(position + step);

        let x_down = input.is_key_pressed(Key::X);
        if x_down && !self.x_was_down {
            // Add the text to the scene's root, so it doesn't move along with the player.
            let mut root = self.base().get_tree().get_current_scene().expect("a scene is running");
            let at = self.base().get_global_position() + Vector2::new(-20.0, -70.0);
            FloatingText::spawn(&mut root, "+1", at);
        }
        self.x_was_down = x_down;
    }''')

FEATURES["floating_text"] = dict(
    prompts=["show a little +1 that floats up when I press X", "floating damage numbers effect",
             "pop up text above the player that rises and disappears", "make X spawn floating text"],
    new_nodes=[("FloatingText", "Label")],
    files={"rust/src/floating_text.rs": FLOATING},
    edits=[("rust/src/player.rs",) + FLOAT_EDIT_IMPORT, ("rust/src/player.rs",) + FLOAT_EDIT_FIELDS,
           ("rust/src/player.rs",) + FLOAT_EDIT_INIT, ("rust/src/player.rs",) + FLOAT_EDIT_BODY], run=2,
    intro=["Floating text is so satisfying. Let me look around the project."],
    final=["Press **X** and a little **+1** pops out above the player, floats up, shrinks away, and deletes itself after a second.\n\n"
           "The new **FloatingText** label does the floating; the player just spawns one with `FloatingText::spawn`. "
           "I add it to the scene's root rather than the player, so it stays where it appeared instead of following you.\n\n"
           "Press **Play** (F5) and tap X. Later we can use it for real points or damage numbers!"],
)

FEATURES["start_position"] = dict(
    prompts=["make the player start in the bottom left corner", "change where the player spawns",
             "the player should start near the left edge", "move the starting point to the bottom left"],
    edits=[("main.tscn", "position = Vector2(576, 324)", "position = Vector2(100, 560)")], run=2,
    intro=["That's a one-line scene change. Let me look at the scene."],
    final=["Done: the player now starts in the bottom-left at (100, 560). The screen is 1152 x 648 pixels and (0, 0) is the **top**-left, so bigger y numbers go further down.\n\n"
           "Press **Play** (F5) to check. You can also just drag the Player around in the 2D view and save the scene."],
)

FEATURES["rename_game"] = dict(
    prompts=["rename my game to Star Chaser", "change the game's name to Star Chaser", "I want my game called Star Chaser"],
    edits=[("project.godot", 'config/name="Agent Test"', 'config/name="Star Chaser"')],
    intro=["Great name! It lives in the project settings. Let me look."],
    final=["Your game is now called **Star Chaser**. The name is stored in `project.godot` (the project settings file) and shows up in the window title and the Project Manager.\n\n"
           "You can also change it any time in **Project > Project Settings > Application > Config > Name**."],
)

FEATURES["ask_button_signals"] = dict(
    answer=True,
    prompts=["what signals does a Button have?", "how do I know when a button is clicked?", "what events can a button send?"],
    lookups=[("BaseButton", "")],
    intro=["Let me check the real list in the Godot API."],
    final=["A Button gets its signals from **BaseButton**:\n- `pressed()`: the one you'll use most, fired when it's clicked.\n- `button_down()` / `button_up()`: the moment it's pushed and released.\n"
           "- `toggled(toggled_on)`: for buttons with **Toggle Mode** on, like a checkbox.\n\nIn Rust you'd connect it in `ready`, for example:\n"
           "```rust\nself.signals().pressed().connect_self(Self::on_pressed);\n```\nWant me to add a button to your game?"],
)

FEATURES["ask_timer"] = dict(
    answer=True,
    prompts=["how does a Timer work in Godot?", "what can I do with a Timer node?", "explain timers to me"],
    lookups=[("Timer", "")],
    intro=["Let me pull up Timer in the API so I give you the real details."],
    final=["A **Timer** counts down and then fires its `timeout` signal. The main settings:\n- `wait_time`: how many seconds it counts.\n"
           "- `one_shot`: fire once, or keep repeating.\n- `autostart`: start by itself when it enters the scene.\n\nYou can also `start()`, `stop()`, and check `time_left`.\n\n"
           "It's perfect for things like spawning enemies every few seconds, cooldowns, or a countdown. Want me to use one in your game?"],
)

CHAINS += [
    ["rename_game", "start_position"],
    ["turret_look", "floating_text"],
    ["ask_timer", "blink_timer"],
]


# ================================================================ batch 4
PUB_SPEED = ("rust/src/player.rs", "    speed: f32,\n", "    pub speed: f32,\n")


def topdown_with(subs: str, nodes: str) -> str:
    return TOPDOWN_SCENE.replace('[node name="Main" type="Node2D"]', subs.strip() + '\n\n[node name="Main" type="Node2D"]') + nodes


GOLD_KEY = '''use godot::classes::{Area2D, IArea2D, Node2D};
use godot::prelude::*;

use crate::player::Player;

/// A key on the ground. Walking over it gives the player the key.
#[derive(GodotClass)]
#[class(base = Area2D)]
pub struct GoldKey {
    base: Base<Area2D>,
}

#[godot_api]
impl IArea2D for GoldKey {
    fn init(base: Base<Area2D>) -> Self {
        Self { base }
    }

    fn ready(&mut self) {
        self.signals().body_entered().connect_self(Self::on_body_entered);
    }
}

#[godot_api]
impl GoldKey {
    fn on_body_entered(&mut self, body: Gd<Node2D>) {
        if let Ok(mut player) = body.try_cast::<Player>() {
            player.bind_mut().has_key = true;
            godot_print!("You found a key!");
            self.base_mut().queue_free();
        }
    }
}
'''

DOOR = '''use godot::classes::{Area2D, IStaticBody2D, Node2D, StaticBody2D};
use godot::prelude::*;

use crate::player::Player;

/// A solid door. Its "Sensor" Area2D notices the player; if they have the key, the door disappears.
#[derive(GodotClass)]
#[class(base = StaticBody2D)]
pub struct Door {
    base: Base<StaticBody2D>,
}

#[godot_api]
impl IStaticBody2D for Door {
    fn init(base: Base<StaticBody2D>) -> Self {
        Self { base }
    }

    fn ready(&mut self) {
        let sensor = self.base().get_node_as::<Area2D>("Sensor");
        sensor.signals().body_entered().connect_other(&self.to_gd(), Self::on_touch);
    }
}

#[godot_api]
impl Door {
    fn on_touch(&mut self, body: Gd<Node2D>) {
        let Ok(player) = body.try_cast::<Player>() else { return };
        if player.bind().has_key {
            godot_print!("The door creaks open!");
            self.base_mut().queue_free();
        } else {
            godot_print!("Locked. Maybe there's a key somewhere...");
        }
    }
}
'''

KEY_DOOR_SCENE = topdown_with('''
[sub_resource type="CircleShape2D" id="CircleShape2D_key"]
radius = 20.0

[sub_resource type="RectangleShape2D" id="RectangleShape2D_door"]
size = Vector2(40, 160)

[sub_resource type="RectangleShape2D" id="RectangleShape2D_sensor"]
size = Vector2(80, 180)
''', '''
[node name="GoldKey" type="GoldKey" parent="."]
position = Vector2(200, 520)

[node name="ColorRect" type="ColorRect" parent="GoldKey"]
offset_left = -14.0
offset_top = -14.0
offset_right = 14.0
offset_bottom = 14.0
color = Color(1, 0.85, 0.2, 1)

[node name="CollisionShape2D" type="CollisionShape2D" parent="GoldKey"]
shape = SubResource("CircleShape2D_key")

[node name="Door" type="Door" parent="."]
position = Vector2(900, 324)

[node name="ColorRect" type="ColorRect" parent="Door"]
offset_left = -20.0
offset_top = -80.0
offset_right = 20.0
offset_bottom = 80.0
color = Color(0.5, 0.3, 0.15, 1)

[node name="CollisionShape2D" type="CollisionShape2D" parent="Door"]
shape = SubResource("RectangleShape2D_door")

[node name="Sensor" type="Area2D" parent="Door"]

[node name="CollisionShape2D" type="CollisionShape2D" parent="Door/Sensor"]
shape = SubResource("RectangleShape2D_sensor")
''')

FEATURES["key_door"] = dict(
    requires=["topdown_body"],
    prompts=["add a locked door and a key to open it", "I want a key that unlocks a door",
             "make a door that only opens if I have the key", "key and door puzzle please"],
    lookups=[("Area2D", "body_entered")],
    new_nodes=[("GoldKey", "Area2D"), ("Door", "StaticBody2D")],
    edits=[("rust/src/player.rs", "    speed: f32,\n", "    pub speed: f32,\n    /// Has the player picked up the key?\n    pub has_key: bool,\n"),
           ("rust/src/player.rs", "Self { speed: 300.0, base }", "Self { speed: 300.0, has_key: false, base }")],
    files={"rust/src/gold_key.rs": GOLD_KEY, "rust/src/door.rs": DOOR, "main.tscn": KEY_DOOR_SCENE}, run=2,
    intro=["A key-and-door puzzle! Let me look at the player and the scene."],
    final=["Your first puzzle! There's a yellow **key** in the bottom-left and a brown **door** on the right.\n- Walk into the door without the key: \"Locked.\"\n"
           "- Grab the key, then touch the door: it opens (disappears).\n\nHow it fits together: the Player now has a `has_key` flag, the key sets it with `bind_mut()`, "
           "and the door's **Sensor** (a slightly bigger Area2D) checks it with `bind()`.\n\nPress **Play** (F5) and try it!"],
)

SPAWNER_RAMP = STAR_SPAWNER.replace('''    every: f64,
    base: Base<Node2D>,''', '''    every: f64,
    /// Never spawn faster than this.
    #[export]
    fastest: f64,
    timer: Option<Gd<Timer>>,
    base: Base<Node2D>,''').replace('''Self { every: 0.8, base }''', '''Self { every: 0.8, fastest: 0.2, timer: None, base }''').replace(
    '''        self.base_mut().add_child(&timer);''', '''        self.base_mut().add_child(&timer);
        self.timer = Some(timer); // keep it, so we can speed it up later''').replace('''        self.base_mut().add_child(&star);''', '''        self.base_mut().add_child(&star);

        // Each star makes the next one come a little sooner: 5% faster every time.
        let fastest = self.fastest;
        if let Some(timer) = self.timer.as_mut() {
            let wait = (timer.get_wait_time() * 0.95).max(fastest);
            timer.set_wait_time(wait);
        }''')

FEATURES["stars_speed_up"] = dict(
    requires=["star_spawner"],
    prompts=["make the stars come faster and faster over time", "the game should get harder the longer I play",
             "increase the spawn rate as time goes on", "ramp up the difficulty"],
    files={"rust/src/star_spawner.rs": SPAWNER_RAMP}, run=3,
    intro=["Rising difficulty, that's how you keep it exciting. Let me read the spawner."],
    final=["The stars now speed up! Every time a star spawns, the next one comes 5% sooner, until it hits the limit of one every 0.2 seconds.\n\n"
           "To do that, the spawner now *keeps* its Timer in a field (`timer: Option<Gd<Timer>>`) instead of forgetting it after `ready`, so it can change `wait_time` later.\n\n"
           "Press **Play** (F5) and watch it get busier. **Fastest** in the Inspector sets the limit."],
)

CLEAR_STARS_EDIT_GROUP = ("rust/src/star.rs", "        self.base_mut().add_child(&sprite);\n",
                          "        self.base_mut().add_child(&sprite);\n        // Groups are tags: later we can find (or remove) every star at once.\n        self.base_mut().add_to_group(\"stars\");\n")
CLEAR_STARS_EDIT_IMPORT = ("rust/src/player.rs", PLAYER_IMPORTS, PLAYER_IMPORTS + "\nuse godot::global::Key;")
CLEAR_STARS_EDIT_BODY = ("rust/src/player.rs", PLAYER_MOVE_END, '''        self.base_mut().set_position(position + step);

        if input.is_key_pressed(Key::BACKSPACE) {
            // Call queue_free on every node tagged "stars".
            self.base().get_tree().call_group("stars", "queue_free", &[]);
        }
    }''')

FEATURES["clear_stars"] = dict(
    requires=["star_spawner"],
    prompts=["let me press backspace to clear all the stars", "add a bomb key that removes every star",
             "how do I delete all the falling stars at once?", "wipe the screen of stars with backspace"],
    lookups=[("SceneTree", "group")],
    edits=[CLEAR_STARS_EDIT_GROUP, CLEAR_STARS_EDIT_IMPORT, CLEAR_STARS_EDIT_BODY], run=3,
    intro=["A screen-clearing bomb! Let me look at the star and player code."],
    final=["Press **Backspace** and every star on screen vanishes! Each Star now joins a **group** called `stars` when it appears (groups are like tags), "
           "and the player calls `call_group(\"stars\", \"queue_free\", ...)` to remove them all at once.\n\nPress **Play** (F5) and try it. "
           "Idea: limit it to 3 bombs per game, shown in the corner!"],
)

TELEPORTER = '''use godot::classes::{Area2D, IArea2D, Marker2D, Node2D};
use godot::prelude::*;

use crate::player::Player;

/// Step on it and you're sent to the destination marker.
#[derive(GodotClass)]
#[class(base = Area2D)]
pub struct Teleporter {
    #[export]
    destination: Option<Gd<Marker2D>>,
    base: Base<Area2D>,
}

#[godot_api]
impl IArea2D for Teleporter {
    fn init(base: Base<Area2D>) -> Self {
        Self { destination: None, base }
    }

    fn ready(&mut self) {
        self.signals().body_entered().connect_self(Self::on_body_entered);
    }
}

#[godot_api]
impl Teleporter {
    fn on_body_entered(&mut self, body: Gd<Node2D>) {
        let Some(to) = self.destination.as_ref().map(|d| d.get_global_position()) else { return };
        if let Ok(mut player) = body.try_cast::<Player>() {
            player.set_global_position(to);
            godot_print!("Whoosh!");
        }
    }
}
'''

TELEPORT_SCENE = topdown_with('''
[sub_resource type="CircleShape2D" id="CircleShape2D_pad"]
radius = 30.0
''', '''
[node name="Teleporter" type="Teleporter" parent="." node_paths=PackedStringArray("destination")]
position = Vector2(200, 500)
destination = NodePath("../Exit")

[node name="ColorRect" type="ColorRect" parent="Teleporter"]
offset_left = -30.0
offset_top = -30.0
offset_right = 30.0
offset_bottom = 30.0
color = Color(0.6, 0.3, 1, 0.8)

[node name="CollisionShape2D" type="CollisionShape2D" parent="Teleporter"]
shape = SubResource("CircleShape2D_pad")

[node name="Exit" type="Marker2D" parent="."]
position = Vector2(950, 150)
''')

FEATURES["teleport_pad"] = dict(
    requires=["topdown_body"],
    prompts=["add a teleporter pad that sends me across the map", "make a portal", "I want a warp pad",
             "stepping on a purple pad should teleport me somewhere else"],
    new_nodes=[("Teleporter", "Area2D")],
    files={"rust/src/teleporter.rs": TELEPORTER, "main.tscn": TELEPORT_SCENE}, run=2,
    intro=["Portals! Let me check the project first."],
    final=["Step on the purple pad in the bottom-left and you'll warp to the top-right! The pad is a **Teleporter** (an `Area2D`), and its **Destination** "
           "is a `Marker2D` called **Exit**: an invisible point you can drag anywhere in the 2D view.\n\nPress **Play** (F5) and try it. "
           "Want a two-way portal? Add a second Teleporter at the exit, pointing back (just place its exit marker a bit beside the pad so you don't bounce forever!)."],
)

RANDOM_START_IMPORT = ("rust/src/player.rs", PLAYER_IMPORTS, PLAYER_IMPORTS + "\nuse godot::global::randf_range;")
RANDOM_START_READY = ("rust/src/player.rs", '''        godot_print!("Hello from Rust! Use the arrow keys to move.");''', '''        godot_print!("Hello from Rust! Use the arrow keys to move.");

        // Start somewhere random on the screen (staying 50 pixels away from the edges).
        let size = self.base().get_viewport_rect().size;
        let x = randf_range(50.0, (size.x - 50.0) as f64) as f32;
        let y = randf_range(50.0, (size.y - 50.0) as f64) as f32;
        self.base_mut().set_position(Vector2::new(x, y));''')

FEATURES["random_start"] = dict(
    prompts=["start the player at a random spot each time", "randomize where I spawn", "spawn the player somewhere random"],
    edits=[RANDOM_START_IMPORT, RANDOM_START_READY], run=2,
    intro=["Sure! Let me look at the player code."],
    final=["Each time you press Play, the player starts at a random spot (at least 50 pixels from the edges). It happens in `ready`, which runs once when the player appears.\n\n"
           "Press **Play** (F5) a few times to see it move around."],
)

INVERT = '''use godot::classes::{INode2D, Input, Node2D};
use godot::global::Key;
use godot::prelude::*;

/// Press I to flip the controls: left is right, up is down. Press again to flip back.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Player {
    #[export]
    speed: f32,
    inverted: bool,
    i_was_down: bool,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Player {
    fn init(base: Base<Node2D>) -> Self {
        Self { speed: 300.0, inverted: false, i_was_down: false, base }
    }

    fn process(&mut self, delta: f64) {
        let input = Input::singleton();

        let i_down = input.is_key_pressed(Key::I);
        if i_down && !self.i_was_down {
            self.inverted = !self.inverted;
            godot_print!("Controls inverted: {}", self.inverted);
        }
        self.i_was_down = i_down;

        let mut direction = input.get_vector("ui_left", "ui_right", "ui_up", "ui_down");
        if self.inverted {
            direction = -direction;
        }
        let step = direction * self.speed * delta as f32;
        let position = self.base().get_position();
        self.base_mut().set_position(position + step);
    }
}
'''

FEATURES["invert_controls"] = dict(
    prompts=["press I to make the controls backwards", "add a confusion mode where the arrows are reversed",
             "invert the controls when I press I", "make a backwards-controls toggle"],
    files={"rust/src/player.rs": INVERT}, run=2,
    intro=["Confusion mode, sneaky! Let me read the player first."],
    final=["Press **I** and the arrows flip: left goes right, up goes down. Press **I** again to go back to normal. It's a true/false flag (`inverted`) that flips on each press, and when it's on the direction is simply negated.\n\n"
           "Press **Play** (F5) and try to steer! Idea: make a potion that confuses you for 5 seconds."],
)

MUD = '''use godot::classes::{Area2D, IArea2D, Node2D};
use godot::prelude::*;

use crate::player::Player;

/// Slows the player down while they're inside it.
#[derive(GodotClass)]
#[class(base = Area2D)]
pub struct MudZone {
    /// 0.4 = move at 40% speed.
    #[export]
    slowdown: f32,
    base: Base<Area2D>,
}

#[godot_api]
impl IArea2D for MudZone {
    fn init(base: Base<Area2D>) -> Self {
        Self { slowdown: 0.4, base }
    }

    fn ready(&mut self) {
        self.signals().body_entered().connect_self(Self::on_enter);
        self.signals().body_exited().connect_self(Self::on_exit);
    }
}

#[godot_api]
impl MudZone {
    fn on_enter(&mut self, body: Gd<Node2D>) {
        if let Ok(mut player) = body.try_cast::<Player>() {
            player.bind_mut().speed *= self.slowdown;
        }
    }

    fn on_exit(&mut self, body: Gd<Node2D>) {
        if let Ok(mut player) = body.try_cast::<Player>() {
            player.bind_mut().speed /= self.slowdown; // undo exactly what we did
        }
    }
}
'''

FEATURES["mud_zone"] = dict(
    requires=["topdown_body"],
    prompts=["add mud that slows me down", "make a swamp area where the player moves slower",
             "slow zone please", "I want sticky ground that makes you slow"],
    new_nodes=[("MudZone", "Area2D")],
    edits=[PUB_SPEED],
    files={"rust/src/mud_zone.rs": MUD, "main.tscn": topdown_with('''
[sub_resource type="RectangleShape2D" id="RectangleShape2D_mud"]
size = Vector2(400, 220)
''', '''
[node name="MudZone" type="MudZone" parent="."]
position = Vector2(850, 450)

[node name="ColorRect" type="ColorRect" parent="MudZone"]
offset_left = -200.0
offset_top = -110.0
offset_right = 200.0
offset_bottom = 110.0
color = Color(0.4, 0.28, 0.15, 0.7)

[node name="CollisionShape2D" type="CollisionShape2D" parent="MudZone"]
shape = SubResource("RectangleShape2D_mud")
''')}, run=2,
    intro=["Mud! Let me look at the player and the scene."],
    final=["There's a brown **mud** patch in the bottom-right. Walk into it and you slow to 40% speed; walk out and you're back to normal. "
           "The MudZone multiplies the player's `speed` when you enter and divides it back when you leave (I made `speed` **pub** so it's allowed to).\n\n"
           "Press **Play** (F5) and wade through it. **Slowdown** in the Inspector sets how sticky it is."],
)

CHAINS += [
    ["star_spawner", "stars_speed_up", "clear_stars"],
    ["topdown_body", "key_door"],
    ["quit_escape", "random_start"],
]
