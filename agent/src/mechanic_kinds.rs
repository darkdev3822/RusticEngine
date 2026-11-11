//! Starting code for new mechanics, one template per common kind. Each template is a complete,
//! working (compile-tested) example of its kind, so the model *edits* a mechanic that already runs
//! instead of writing Godot boilerplate from scratch (which is where an 8B model invents APIs).
//!
//! Placeholders: __NODE__ (node class), __TUNING__ (tuning class), __ID__ (folder id), __NAME__,
//! __SUMMARY__, __ACTION__ (input action name, abilities only).

pub struct Kind {
    pub id: &'static str,
    /// Godot base class of the node.
    pub base: &'static str,
    /// For the model: when to pick this kind.
    pub when: &'static str,
    /// tuning.rs fields (inside the struct, before `base`).
    pub tuning_fields: &'static str,
    /// The [resource] lines of tuning.tres.
    pub tres: &'static str,
    /// The node's source file.
    pub node_src: &'static str,
    /// What the example does, told to the model after scaffolding.
    pub example: &'static str,
}

pub const KINDS: &[Kind] = &[
    Kind {
        id: "player_ability",
        base: "Node",
        when: "something the PLAYER can do on a key press: dash, double jump, wall jump, glide, ground pound (a child node of the player)",
        tuning_fields: r#"    /// How hard the ability pushes the player, in meters per second. More = a bigger, faster burst.
    #[export(range = (0.0, 50.0, 0.5, or_greater, suffix = "m/s"))]
    #[init(val = 14.0)]
    pub strength: f32,
    /// Seconds before it can be used again. Short = spammable; long = a move you have to time.
    #[export(range = (0.0, 10.0, 0.05, or_greater, suffix = "s"))]
    #[init(val = 1.0)]
    pub cooldown: f32,
"#,
        tres: "strength = 14.0\ncooldown = 1.0\n",
        node_src: r#"//! __NAME__: __SUMMARY__
//! ```text
//! Player (FirstPersonController / ThirdPersonController, a CharacterBody3D)
//! └── __NODE__   <- this node; it changes its parent's velocity when the key is pressed
//! ```
//! The player's own movement keeps running; this node only adds to its velocity.

use godot::classes::{CharacterBody3D, INode, Input, InputEventKey, InputMap, Node};
use godot::global::Key;
use godot::prelude::*;

use super::tuning::__TUNING__;

const DEFAULT_TUNING: &str = "res://mechanics/__ID__/tuning.tres";
/// The input action that triggers the ability, and its default key (Project Settings > Input Map overrides it).
const ACTION: &str = "__ACTION__";
const DEFAULT_KEY: Key = Key::E;

#[derive(GodotClass)]
#[class(base = Node)]
pub struct __NODE__ {
    /// Leave empty to use the shared mechanics/__ID__/tuning.tres.
    #[export]
    tuning: Option<Gd<__TUNING__>>,
    /// Seconds until it can be used again.
    cooldown_left: f32,
    base: Base<Node>,
}

#[godot_api]
impl INode for __NODE__ {
    fn init(base: Base<Node>) -> Self {
        Self { tuning: None, cooldown_left: 0.0, base }
    }

    fn ready(&mut self) {
        if self.tuning.is_none() {
            self.tuning = Some(try_load::<__TUNING__>(DEFAULT_TUNING).unwrap_or_else(|_| __TUNING__::new_gd()));
        }
        ensure_action(ACTION, DEFAULT_KEY);
    }

    fn physics_process(&mut self, delta: f64) {
        // Read the tuning every frame, so changes in the Mechanics tab apply immediately.
        let (strength, cooldown) = {
            let t = self.tuning.clone().unwrap_or_else(__TUNING__::new_gd);
            let t = t.bind();
            (t.strength, t.cooldown)
        };
        self.cooldown_left = (self.cooldown_left - delta as f32).max(0.0);
        let Some(mut body) = self.player() else { return };
        if !Input::singleton().is_action_just_pressed(ACTION) || self.cooldown_left > 0.0 {
            return;
        }
        // The ability. Example: a burst in the direction the player is facing (-Z is forward in Godot).
        let mut forward = -body.get_global_transform().basis.col_c();
        forward.y = 0.0;
        let push = if forward.length() > 0.001 { forward.normalized() * strength } else { Vector3::ZERO };
        let velocity = body.get_velocity();
        body.set_velocity(velocity + push);
        self.cooldown_left = cooldown;
        self.signals().used().emit();
    }
}

#[godot_api]
impl __NODE__ {
    /// Emitted each time the ability is used (play a sound, show an effect...).
    #[signal]
    pub fn used();

    /// True when the ability can be used right now.
    #[func]
    pub fn is_ready(&self) -> bool {
        self.cooldown_left <= 0.0
    }

    /// The player this ability belongs to: its parent, if that's a CharacterBody3D.
    fn player(&self) -> Option<Gd<CharacterBody3D>> {
        self.base().get_parent()?.try_cast::<CharacterBody3D>().ok()
    }
}

/// Adds the input action with a default key, unless the project already has it.
fn ensure_action(name: &str, key: Key) {
    let mut map = InputMap::singleton();
    if map.has_action(name) {
        return;
    }
    map.add_action(name);
    let mut ev = InputEventKey::new_gd();
    ev.set_physical_keycode(key);
    map.action_add_event(name, &ev);
}
"#,
        example: "The example pushes the player forward when the __ACTION__ action is pressed (key E), with a cooldown. \
Change the marked block in physics_process for this ability: e.g. double jump = set velocity.y when !body.is_on_floor(); \
wall jump = when body.is_on_wall(), push along body.get_wall_normal() plus up. Change DEFAULT_KEY if asked (Key::SHIFT is sprint).",
    },
    Kind {
        id: "trigger",
        base: "Area3D",
        when: "something that happens when the player TOUCHES or ENTERS a place or object: coin/pickup, door, checkpoint, kill zone, pressure plate, goal",
        tuning_fields: r#"    /// Seconds before it can trigger again after the player leaves. 0 = every time they enter.
    #[export(range = (0.0, 30.0, 0.1, or_greater, suffix = "s"))]
    #[init(val = 0.5)]
    pub rearm_time: f32,
    /// Remove this object after the player touches it (coins and pickups do; doors and checkpoints don't).
    #[export]
    #[init(val = false)]
    pub one_shot: bool,
"#,
        tres: "rearm_time = 0.5\none_shot = false\n",
        node_src: r#"//! __NAME__: __SUMMARY__
//! ```text
//! __NODE__ (Area3D)      <- this node: notices the player entering and leaving
//! ├── CollisionShape3D   <- the area that counts (added automatically if missing)
//! └── Visual (optional)  <- what it looks like
//! ```
//! The player is anything in the "player" group (the First- and Third-Person Controllers join it).

use godot::classes::{Area3D, BoxMesh, BoxShape3D, CollisionShape3D, IArea3D, MeshInstance3D};
use godot::prelude::*;

use super::tuning::__TUNING__;

const DEFAULT_TUNING: &str = "res://mechanics/__ID__/tuning.tres";

#[derive(GodotClass)]
#[class(base = Area3D)]
pub struct __NODE__ {
    /// Leave empty to use the shared mechanics/__ID__/tuning.tres.
    #[export]
    tuning: Option<Gd<__TUNING__>>,
    /// Seconds until it can trigger again.
    rearm_left: f32,
    /// True while the player is inside.
    player_inside: bool,
    base: Base<Area3D>,
}

#[godot_api]
impl IArea3D for __NODE__ {
    fn init(base: Base<Area3D>) -> Self {
        Self { tuning: None, rearm_left: 0.0, player_inside: false, base }
    }

    fn ready(&mut self) {
        if self.tuning.is_none() {
            self.tuning = Some(try_load::<__TUNING__>(DEFAULT_TUNING).unwrap_or_else(|_| __TUNING__::new_gd()));
        }
        self.ensure_shape();
        self.signals().body_entered().connect_self(Self::on_body_entered);
        self.signals().body_exited().connect_self(Self::on_body_exited);
    }

    fn physics_process(&mut self, delta: f64) {
        if !self.player_inside {
            self.rearm_left = (self.rearm_left - delta as f32).max(0.0);
        }
    }
}

#[godot_api]
impl __NODE__ {
    /// The player came in (and the trigger was armed).
    #[signal]
    pub fn triggered();
    /// The player left.
    #[signal]
    pub fn player_left();

    fn on_body_entered(&mut self, body: Gd<Node3D>) {
        if !body.is_in_group("player") {
            return;
        }
        self.player_inside = true;
        if self.rearm_left > 0.0 {
            return;
        }
        let (rearm, one_shot) = {
            let t = self.tuning.clone().unwrap_or_else(__TUNING__::new_gd);
            let t = t.bind();
            (t.rearm_time, t.one_shot)
        };
        self.rearm_left = rearm;
        // What happens. Example: just tell everyone (a sound, a counter, a door listening to `triggered`).
        self.signals().triggered().emit();
        if one_shot {
            self.base_mut().queue_free();
        }
    }

    fn on_body_exited(&mut self, body: Gd<Node3D>) {
        if body.is_in_group("player") {
            self.player_inside = false;
            self.signals().player_left().emit();
        }
    }

    /// An Area3D needs a shape to notice anything: add a 2 m box (and a visible box) if it has none.
    fn ensure_shape(&mut self) {
        if self.base().try_get_node_as::<CollisionShape3D>("CollisionShape3D").is_some() {
            return;
        }
        let mut shape = CollisionShape3D::new_alloc();
        shape.set_name("CollisionShape3D");
        let mut box_shape = BoxShape3D::new_gd();
        box_shape.set_size(Vector3::new(2.0, 2.0, 2.0));
        shape.set_shape(&box_shape);
        self.base_mut().add_child(&shape);
        if self.base().try_get_node_as::<Node3D>("Visual").is_none() {
            let mut visual = MeshInstance3D::new_alloc();
            visual.set_name("Visual");
            let mut mesh = BoxMesh::new_gd();
            mesh.set_size(Vector3::new(0.5, 0.5, 0.5));
            visual.set_mesh(&mesh);
            self.base_mut().add_child(&visual);
        }
    }
}
"#,
        example: "The example emits `triggered` when a node in the \"player\" group enters (once per rearm_time) and can remove itself (one_shot). \
Put the mechanic's effect where it says 'What happens': e.g. a coin = one_shot + count it; a checkpoint = remember self.base().get_global_position(); \
a door = move or hide a child node; a kill zone = move the player back. The `body` is the player (cast with body.try_cast::<CharacterBody3D>() to move it).",
    },
    Kind {
        id: "mover",
        base: "CharacterBody3D",
        when: "something in the world that MOVES BY ITSELF with physics: a patrolling enemy, a wandering animal, a chaser",
        tuning_fields: r#"    /// How fast it walks, in meters per second.
    #[export(range = (0.0, 20.0, 0.1, or_greater, suffix = "m/s"))]
    #[init(val = 2.0)]
    pub speed: f32,
    /// How far it walks each way from where it starts, in meters.
    #[export(range = (0.0, 50.0, 0.1, or_greater, suffix = "m"))]
    #[init(val = 4.0)]
    pub distance: f32,
"#,
        tres: "speed = 2.0\ndistance = 4.0\n",
        node_src: r#"//! __NAME__: __SUMMARY__
//! ```text
//! __NODE__ (CharacterBody3D)  <- this node: moves itself every physics frame
//! ├── CollisionShape3D        <- its body (a capsule is added automatically if missing)
//! └── Visual (optional)       <- what it looks like
//! ```

use godot::classes::{
    CapsuleMesh, CapsuleShape3D, CharacterBody3D, CollisionShape3D, ICharacterBody3D, MeshInstance3D, ProjectSettings,
};
use godot::prelude::*;

use super::tuning::__TUNING__;

const DEFAULT_TUNING: &str = "res://mechanics/__ID__/tuning.tres";

#[derive(GodotClass)]
#[class(base = CharacterBody3D)]
pub struct __NODE__ {
    /// Leave empty to use the shared mechanics/__ID__/tuning.tres.
    #[export]
    tuning: Option<Gd<__TUNING__>>,
    /// Where it started (its patrol is centered here).
    start: Vector3,
    /// +1 or -1: which way it's walking.
    direction: f32,
    base: Base<CharacterBody3D>,
}

#[godot_api]
impl ICharacterBody3D for __NODE__ {
    fn init(base: Base<CharacterBody3D>) -> Self {
        Self { tuning: None, start: Vector3::ZERO, direction: 1.0, base }
    }

    fn ready(&mut self) {
        if self.tuning.is_none() {
            self.tuning = Some(try_load::<__TUNING__>(DEFAULT_TUNING).unwrap_or_else(|_| __TUNING__::new_gd()));
        }
        self.start = self.base().get_global_position();
        self.ensure_body();
    }

    fn physics_process(&mut self, delta: f64) {
        // Read the tuning every frame, so changes in the Mechanics tab apply immediately.
        let (speed, distance) = {
            let t = self.tuning.clone().unwrap_or_else(__TUNING__::new_gd);
            let t = t.bind();
            (t.speed, t.distance)
        };
        let mut velocity = self.base().get_velocity();
        if !self.base().is_on_floor() {
            velocity.y -= gravity() * delta as f32;
        }
        // The movement. Example: walk back and forth along X, `distance` meters each way from the start.
        let offset = self.base().get_global_position().x - self.start.x;
        if offset > distance && self.direction > 0.0 {
            self.direction = -1.0;
            self.signals().turned().emit();
        } else if offset < -distance && self.direction < 0.0 {
            self.direction = 1.0;
            self.signals().turned().emit();
        }
        velocity.x = self.direction * speed;
        velocity.z = 0.0;
        self.base_mut().set_velocity(velocity);
        self.base_mut().move_and_slide();
    }
}

#[godot_api]
impl __NODE__ {
    /// Emitted when it turns around.
    #[signal]
    pub fn turned();

    /// Give it a capsule body (and a visible capsule) if it has no shape yet.
    fn ensure_body(&mut self) {
        if self.base().try_get_node_as::<CollisionShape3D>("CollisionShape3D").is_some() {
            return;
        }
        let mut shape = CollisionShape3D::new_alloc();
        shape.set_name("CollisionShape3D");
        shape.set_shape(&CapsuleShape3D::new_gd());
        shape.set_position(Vector3::new(0.0, 1.0, 0.0));
        self.base_mut().add_child(&shape);
        if self.base().try_get_node_as::<Node3D>("Visual").is_none() {
            let mut visual = MeshInstance3D::new_alloc();
            visual.set_name("Visual");
            visual.set_mesh(&CapsuleMesh::new_gd());
            visual.set_position(Vector3::new(0.0, 1.0, 0.0));
            self.base_mut().add_child(&visual);
        }
    }
}

/// The project's gravity (Project Settings > Physics > 3D > Default Gravity).
fn gravity() -> f32 {
    ProjectSettings::singleton()
        .get_setting("physics/3d/default_gravity")
        .try_to::<f32>()
        .unwrap_or(9.8)
}
"#,
        example: "The example falls with gravity and walks back and forth along X (speed, distance), emitting `turned`. \
Change the marked block for this mechanic: e.g. chase the player = direction toward \
self.base().get_tree().get_first_node_in_group(\"player\") (try_cast::<Node3D>() for its position).",
    },
    Kind {
        id: "timer",
        base: "Node",
        when: "RULES OVER TIME or bookkeeping with no body: countdown, health regeneration, score, day/night clock, spawner",
        tuning_fields: r#"    /// How long it lasts, in seconds.
    #[export(range = (0.0, 3600.0, 0.5, or_greater, suffix = "s"))]
    #[init(val = 60.0)]
    pub duration: f32,
    /// Start counting as soon as the scene starts (off = wait until something calls start()).
    #[export]
    #[init(val = true)]
    pub autostart: bool,
"#,
        tres: "duration = 60.0\nautostart = true\n",
        node_src: r#"//! __NAME__: __SUMMARY__
//! Put a `__NODE__` anywhere in the scene (it has no body). Other nodes listen to its signals
//! or call its #[func] methods.

use godot::classes::{INode, Node};
use godot::prelude::*;

use super::tuning::__TUNING__;

const DEFAULT_TUNING: &str = "res://mechanics/__ID__/tuning.tres";

#[derive(GodotClass)]
#[class(base = Node)]
pub struct __NODE__ {
    /// Leave empty to use the shared mechanics/__ID__/tuning.tres.
    #[export]
    tuning: Option<Gd<__TUNING__>>,
    /// Seconds since it started.
    elapsed: f32,
    running: bool,
    base: Base<Node>,
}

#[godot_api]
impl INode for __NODE__ {
    fn init(base: Base<Node>) -> Self {
        Self { tuning: None, elapsed: 0.0, running: false, base }
    }

    fn ready(&mut self) {
        if self.tuning.is_none() {
            self.tuning = Some(try_load::<__TUNING__>(DEFAULT_TUNING).unwrap_or_else(|_| __TUNING__::new_gd()));
        }
        let autostart = self.tuning.as_ref().map(|t| t.bind().autostart).unwrap_or(true);
        if autostart {
            self.start();
        }
    }

    fn process(&mut self, delta: f64) {
        if !self.running {
            return;
        }
        // Read the tuning every frame, so changes in the Mechanics tab apply immediately.
        let duration = self.tuning.as_ref().map(|t| t.bind().duration).unwrap_or(60.0);
        // The rule. Example: count up to `duration`, then stop and announce it.
        self.elapsed += delta as f32;
        if self.elapsed >= duration {
            self.running = false;
            self.signals().finished().emit();
        }
    }
}

#[godot_api]
impl __NODE__ {
    /// Emitted once when the time is up.
    #[signal]
    pub fn finished();

    /// Start (or restart) from zero.
    #[func]
    pub fn start(&mut self) {
        self.elapsed = 0.0;
        self.running = true;
    }

    /// Pause it.
    #[func]
    pub fn stop(&mut self) {
        self.running = false;
    }

    /// Seconds left (0 when finished).
    #[func]
    pub fn time_left(&self) -> f32 {
        let duration = self.tuning.as_ref().map(|t| t.bind().duration).unwrap_or(60.0);
        (duration - self.elapsed).max(0.0)
    }
}
"#,
        example: "The example counts up to `duration` then emits `finished`, with start/stop/time_left methods. \
Change the marked block for this rule: e.g. health regen = after a quiet time, call crate::stats::find_stats(&player) and heal it \
(read mechanics/stats/src/stats.rs for the real method names first); a score = a #[func] add_points that emits changed(new_total).",
    },
];

/// Pick a kind: the one asked for, else the one matching the base class.
pub fn pick(kind: &str, base: &str) -> Option<&'static Kind> {
    let kind = kind.trim().to_lowercase().replace([' ', '-'], "_");
    if let Some(k) = KINDS.iter().find(|k| k.id == kind) {
        return Some(k);
    }
    match base.trim() {
        "Area3D" => KINDS.iter().find(|k| k.id == "trigger"),
        "CharacterBody3D" => KINDS.iter().find(|k| k.id == "mover"),
        _ => None,
    }
}

/// For the tool description: the kinds and when to use each.
pub fn menu() -> String {
    KINDS.iter().map(|k| format!("'{}' ({}): {}", k.id, k.base, k.when)).collect::<Vec<_>>().join("; ")
}

pub fn fill(t: &str, node: &str, tuning: &str, id: &str, name: &str, summary: &str) -> String {
    t.replace("__NODE__", node).replace("__TUNING__", tuning).replace("__ID__", id)
        .replace("__NAME__", name).replace("__SUMMARY__", summary).replace("__ACTION__", id)
}
