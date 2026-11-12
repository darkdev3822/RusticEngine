//! Starting code for new mechanics, one template per common kind. Each template is a complete,
//! working (compile-tested) example of its kind, so the model *edits* a mechanic that already runs
//! instead of writing Godot boilerplate from scratch (which is where an 8B model invents APIs).
//!
//! Placeholders: __NODE__ (node class), __TUNING__ (tuning class), __ID__ (folder id), __NAME__,
//! __SUMMARY__, __ACTION__ (input action name, abilities only).

pub struct Kind {
    pub id: &'static str,
    /// The family it belongs to (player_ability, trigger, mover, timer): the generic choice for that family
    /// is the variant whose id equals... the first variant listed in the family.
    pub group: &'static str,
    /// Words in a request that point to this variant.
    pub keywords: &'static [&'static str],
    /// Other mechanics it needs (they must be in the project).
    pub uses: &'static [&'static str],
    /// Godot base class of the node.
    pub base: &'static str,
    /// When to pick it (documentation; the tool description lists the same choices).
    #[allow(dead_code)]
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
        id: "dash",
        group: "player_ability",
        keywords: &["dash", "burst", "boost", "lunge"],
        uses: &[],
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
        group: "trigger",
        keywords: &["trigger", "zone", "area", "pressure plate", "goal", "touch"],
        uses: &[],
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
        id: "patrol",
        group: "mover",
        keywords: &["patrol", "back and forth", "walks between", "guard", "pace"],
        uses: &[],
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
        id: "countdown",
        group: "timer",
        keywords: &["countdown", "timer", "time limit", "seconds", "clock"],
        uses: &[],
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
    Kind {
        id: "double_jump",
        group: "player_ability",
        keywords: &["double jump", "air jump", "jump again", "jump twice", "triple jump", "extra jump"],
        uses: &[],
        base: "Node",
        when: "jump again in the air (double/triple jump)",
        tuning_fields: r#"    /// How fast the air jump launches the player upward, in meters per second (about 5 = a hop, 8 = a big leap).
    #[export(range = (0.0, 20.0, 0.1, or_greater, suffix = "m/s"))]
    #[init(val = 5.5)]
    pub jump_speed: f32,
    /// How many extra jumps the player gets before touching the ground again (1 = double jump, 2 = triple).
    #[export(range = (0.0, 5.0, 1.0, or_greater))]
    #[init(val = 1)]
    pub extra_jumps: i32,
"#,
        tres: "jump_speed = 5.5\nextra_jumps = 1\n",
        node_src: r#"//! __NAME__: __SUMMARY__
//! ```text
//! Player (FirstPersonController / ThirdPersonController, a CharacterBody3D)
//! └── __NODE__   <- this node: gives the player extra jumps in the air
//! ```
//! The player's own controller does the normal jump from the ground; this node only handles jumps in the air.

use godot::classes::{CharacterBody3D, INode, Input, Node};
use godot::prelude::*;

use super::tuning::__TUNING__;

const DEFAULT_TUNING: &str = "res://mechanics/__ID__/tuning.tres";
/// The same action the controller jumps with (Space by default).
const ACTION: &str = "jump";

#[derive(GodotClass)]
#[class(base = Node)]
pub struct __NODE__ {
    /// Leave empty to use the shared mechanics/__ID__/tuning.tres.
    #[export]
    tuning: Option<Gd<__TUNING__>>,
    /// Air jumps left before landing.
    jumps_left: i32,
    base: Base<Node>,
}

#[godot_api]
impl INode for __NODE__ {
    fn init(base: Base<Node>) -> Self {
        Self { tuning: None, jumps_left: 0, base }
    }

    fn ready(&mut self) {
        if self.tuning.is_none() {
            self.tuning = Some(try_load::<__TUNING__>(DEFAULT_TUNING).unwrap_or_else(|_| __TUNING__::new_gd()));
        }
    }

    fn physics_process(&mut self, _delta: f64) {
        let (jump_speed, extra_jumps) = {
            let t = self.tuning.clone().unwrap_or_else(__TUNING__::new_gd);
            let t = t.bind();
            (t.jump_speed, t.extra_jumps)
        };
        let Some(mut body) = self.player() else { return };
        // On the ground: refill the air jumps.
        if body.is_on_floor() {
            self.jumps_left = extra_jumps;
            return;
        }
        // In the air: a jump press uses one air jump and launches upward (replacing the fall speed).
        if Input::singleton().is_action_just_pressed(ACTION) && self.jumps_left > 0 {
            self.jumps_left -= 1;
            let mut velocity = body.get_velocity();
            velocity.y = jump_speed;
            body.set_velocity(velocity);
            self.signals().used().emit();
        }
    }
}

#[godot_api]
impl __NODE__ {
    /// Emitted on every air jump (play a whoosh, puff of dust...).
    #[signal]
    pub fn used();

    /// Air jumps left right now.
    #[func]
    pub fn jumps_left(&self) -> i32 {
        self.jumps_left
    }

    fn player(&self) -> Option<Gd<CharacterBody3D>> {
        self.base().get_parent()?.try_cast::<CharacterBody3D>().ok()
    }
}
"#,
        example: "It already works: in the air, pressing jump launches the player up again (extra_jumps times until they land). \
Adapt only what they asked for (more jumps = extra_jumps in tuning.tres; a different feel = jump_speed).",
    },
    Kind {
        id: "wall_jump",
        group: "player_ability",
        keywords: &["wall jump", "walljump", "jump off wall", "jump off the wall", "wall kick", "off walls"],
        uses: &[],
        base: "Node",
        when: "jump off walls",
        tuning_fields: r#"    /// How hard the jump pushes away from the wall, in meters per second.
    #[export(range = (0.0, 20.0, 0.1, or_greater, suffix = "m/s"))]
    #[init(val = 6.0)]
    pub push_away: f32,
    /// How fast the wall jump launches upward, in meters per second.
    #[export(range = (0.0, 20.0, 0.1, or_greater, suffix = "m/s"))]
    #[init(val = 6.0)]
    pub push_up: f32,
    /// Seconds before another wall jump. Stops climbing a single wall by mashing jump.
    #[export(range = (0.0, 2.0, 0.05, or_greater, suffix = "s"))]
    #[init(val = 0.3)]
    pub cooldown: f32,
"#,
        tres: "push_away = 6.0\npush_up = 6.0\ncooldown = 0.3\n",
        node_src: r#"//! __NAME__: __SUMMARY__
//! ```text
//! Player (FirstPersonController / ThirdPersonController, a CharacterBody3D)
//! └── __NODE__   <- this node: jump while touching a wall in the air to kick off it
//! ```

use godot::classes::{CharacterBody3D, INode, Input, Node};
use godot::prelude::*;

use super::tuning::__TUNING__;

const DEFAULT_TUNING: &str = "res://mechanics/__ID__/tuning.tres";
/// The same action the controller jumps with (Space by default).
const ACTION: &str = "jump";

#[derive(GodotClass)]
#[class(base = Node)]
pub struct __NODE__ {
    /// Leave empty to use the shared mechanics/__ID__/tuning.tres.
    #[export]
    tuning: Option<Gd<__TUNING__>>,
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
    }

    fn physics_process(&mut self, delta: f64) {
        let (push_away, push_up, cooldown) = {
            let t = self.tuning.clone().unwrap_or_else(__TUNING__::new_gd);
            let t = t.bind();
            (t.push_away, t.push_up, t.cooldown)
        };
        self.cooldown_left = (self.cooldown_left - delta as f32).max(0.0);
        let Some(mut body) = self.player() else { return };
        // Only in the air, only touching a wall, only when the jump key is pressed.
        if body.is_on_floor() || !body.is_on_wall() || self.cooldown_left > 0.0 {
            return;
        }
        if !Input::singleton().is_action_just_pressed(ACTION) {
            return;
        }
        // The wall's normal points out of the wall: push along it, and launch up.
        let mut away = body.get_wall_normal();
        away.y = 0.0;
        let away = if away.length() > 0.001 { away.normalized() } else { Vector3::ZERO };
        let mut velocity = body.get_velocity();
        velocity.x = away.x * push_away;
        velocity.z = away.z * push_away;
        velocity.y = push_up;
        body.set_velocity(velocity);
        self.cooldown_left = cooldown;
        self.signals().used().emit();
    }
}

#[godot_api]
impl __NODE__ {
    /// Emitted on every wall jump.
    #[signal]
    pub fn used();

    fn player(&self) -> Option<Gd<CharacterBody3D>> {
        self.base().get_parent()?.try_cast::<CharacterBody3D>().ok()
    }
}
"#,
        example: "It already works: jumping while touching a wall in the air kicks the player off it (push_away, push_up, cooldown). \
The sandbox has walls to try it. Adapt only what they asked for.",
    },
    Kind {
        id: "glide",
        group: "player_ability",
        keywords: &["glide", "parachute", "float down", "slow fall", "hover", "gliding"],
        uses: &[],
        base: "Node",
        when: "fall slowly while holding a key (glide, parachute)",
        tuning_fields: r#"    /// The fastest the player falls while gliding, in meters per second. Lower = floatier.
    #[export(range = (0.0, 20.0, 0.1, or_greater, suffix = "m/s"))]
    #[init(val = 1.5)]
    pub max_fall_speed: f32,
"#,
        tres: "max_fall_speed = 1.5\n",
        node_src: r#"//! __NAME__: __SUMMARY__
//! ```text
//! Player (FirstPersonController / ThirdPersonController, a CharacterBody3D)
//! └── __NODE__   <- this node: hold jump in the air to fall slowly
//! ```

use godot::classes::{CharacterBody3D, INode, Input, Node};
use godot::prelude::*;

use super::tuning::__TUNING__;

const DEFAULT_TUNING: &str = "res://mechanics/__ID__/tuning.tres";
/// Hold this action in the air to glide (the jump key, Space, by default).
const ACTION: &str = "jump";

#[derive(GodotClass)]
#[class(base = Node)]
pub struct __NODE__ {
    /// Leave empty to use the shared mechanics/__ID__/tuning.tres.
    #[export]
    tuning: Option<Gd<__TUNING__>>,
    gliding: bool,
    base: Base<Node>,
}

#[godot_api]
impl INode for __NODE__ {
    fn init(base: Base<Node>) -> Self {
        Self { tuning: None, gliding: false, base }
    }

    fn ready(&mut self) {
        if self.tuning.is_none() {
            self.tuning = Some(try_load::<__TUNING__>(DEFAULT_TUNING).unwrap_or_else(|_| __TUNING__::new_gd()));
        }
    }

    fn physics_process(&mut self, _delta: f64) {
        let max_fall = self.tuning.as_ref().map(|t| t.bind().max_fall_speed).unwrap_or(1.5);
        let Some(mut body) = self.player() else { return };
        let holding = Input::singleton().is_action_pressed(ACTION);
        let mut velocity = body.get_velocity();
        let glide = holding && !body.is_on_floor() && velocity.y < 0.0;
        if glide {
            // Cap the fall speed: gravity still pulls, but never faster than max_fall_speed.
            velocity.y = velocity.y.max(-max_fall);
            body.set_velocity(velocity);
        }
        if glide != self.gliding {
            self.gliding = glide;
            self.signals().gliding_changed().emit(glide);
        }
    }
}

#[godot_api]
impl __NODE__ {
    /// Gliding started (true) or stopped (false): open a parachute, play wind...
    #[signal]
    pub fn gliding_changed(gliding: bool);

    fn player(&self) -> Option<Gd<CharacterBody3D>> {
        self.base().get_parent()?.try_cast::<CharacterBody3D>().ok()
    }
}
"#,
        example: "It already works: holding jump while falling caps the fall speed at max_fall_speed. Adapt only what they asked for.",
    },
    Kind {
        id: "pickup_counter",
        group: "trigger",
        keywords: &["coin", "coins", "collect", "collectible", "gem", "pickup", "pick up", "counter", "star"],
        uses: &[],
        base: "Area3D",
        when: "things the player collects by touching them, with a running count (coins, gems, stars)",
        tuning_fields: r#"    /// How much one pickup adds to the count.
    #[export(range = (1.0, 100.0, 1.0, or_greater))]
    #[init(val = 1)]
    pub value: i32,
    /// How fast it spins so players notice it, in turns per second (0 = still).
    #[export(range = (0.0, 3.0, 0.05, or_greater, suffix = "turns/s"))]
    #[init(val = 0.5)]
    pub spin: f32,
"#,
        tres: "value = 1\nspin = 0.5\n",
        node_src: r#"//! __NAME__: __SUMMARY__
//! ```text
//! __NODE__ (Area3D)      <- this node: one collectible; touch it to collect it
//! ├── CollisionShape3D   <- added automatically if missing
//! └── Visual             <- what it looks like (a placeholder is added if missing); it spins
//! ```
//! The count lives on the player (metadata "__ID___count"), so every pickup adds to the same total.
//! Read it from anywhere with `__NODE__::count_of(&player)`.

use godot::classes::{Area3D, CollisionShape3D, CylinderMesh, IArea3D, MeshInstance3D, SphereShape3D};
use godot::prelude::*;

use super::tuning::__TUNING__;

const DEFAULT_TUNING: &str = "res://mechanics/__ID__/tuning.tres";
const COUNT_META: &str = "__ID___count";

#[derive(GodotClass)]
#[class(base = Area3D)]
pub struct __NODE__ {
    /// Leave empty to use the shared mechanics/__ID__/tuning.tres.
    #[export]
    tuning: Option<Gd<__TUNING__>>,
    angle: f32,
    base: Base<Area3D>,
}

#[godot_api]
impl IArea3D for __NODE__ {
    fn init(base: Base<Area3D>) -> Self {
        Self { tuning: None, angle: 0.0, base }
    }

    fn ready(&mut self) {
        if self.tuning.is_none() {
            self.tuning = Some(try_load::<__TUNING__>(DEFAULT_TUNING).unwrap_or_else(|_| __TUNING__::new_gd()));
        }
        self.ensure_shape();
        self.signals().body_entered().connect_self(Self::on_body_entered);
    }

    fn process(&mut self, delta: f64) {
        let spin = self.tuning.as_ref().map(|t| t.bind().spin).unwrap_or(0.5);
        self.angle += spin * std::f32::consts::TAU * delta as f32;
        if let Some(mut visual) = self.base().try_get_node_as::<Node3D>("Visual") {
            visual.set_rotation(Vector3::new(0.0, self.angle, 0.0));
        }
    }
}

#[godot_api]
impl __NODE__ {
    /// Collected: the new total on that player.
    #[signal]
    pub fn collected(total: i32);

    /// The player's total so far (0 if they haven't collected any).
    #[allow(dead_code)]
    pub fn count_of(player: &Gd<Node>) -> i32 {
        if player.has_meta(COUNT_META) { player.get_meta(COUNT_META).try_to::<i32>().unwrap_or(0) } else { 0 }
    }

    fn on_body_entered(&mut self, body: Gd<Node3D>) {
        if !body.is_in_group("player") {
            return;
        }
        let value = self.tuning.as_ref().map(|t| t.bind().value).unwrap_or(1);
        let mut player = body.upcast::<Node>();
        let total = Self::count_of(&player) + value;
        player.set_meta(COUNT_META, &total.to_variant());
        self.signals().collected().emit(total);
        godot_print!("Collected! Total: {total}");
        self.base_mut().queue_free();
    }

    fn ensure_shape(&mut self) {
        if self.base().try_get_node_as::<CollisionShape3D>("CollisionShape3D").is_none() {
            let mut shape = CollisionShape3D::new_alloc();
            shape.set_name("CollisionShape3D");
            let mut sphere = SphereShape3D::new_gd();
            sphere.set_radius(0.6);
            shape.set_shape(&sphere);
            self.base_mut().add_child(&shape);
        }
        if self.base().try_get_node_as::<Node3D>("Visual").is_none() {
            let mut visual = MeshInstance3D::new_alloc();
            visual.set_name("Visual");
            let mut disc = CylinderMesh::new_gd();
            disc.set_top_radius(0.3);
            disc.set_bottom_radius(0.3);
            disc.set_height(0.08);
            visual.set_mesh(&disc);
            visual.set_rotation(Vector3::new(std::f32::consts::FRAC_PI_2, 0.0, 0.0));
            self.base_mut().add_child(&visual);
        }
    }
}
"#,
        example: "It already works: touching it adds `value` to the player's total (metadata on the player, read with count_of), \
emits collected(total), prints the total and disappears. Duplicate the node in the sandbox to place more. To show the count on screen, \
the HUD can connect to `collected`. Adapt only what they asked for.",
    },
    Kind {
        id: "door",
        group: "trigger",
        keywords: &["door", "gate", "opens", "automatic door", "sliding door", "drawbridge"],
        uses: &[],
        base: "Area3D",
        when: "a door/gate that opens when the player comes near and closes after",
        tuning_fields: r#"    /// How high the door slides up when open, in meters.
    #[export(range = (0.0, 10.0, 0.05, or_greater, suffix = "m"))]
    #[init(val = 2.5)]
    pub open_height: f32,
    /// Seconds to open or close fully. Short = snappy, long = heavy.
    #[export(range = (0.05, 5.0, 0.05, or_greater, suffix = "s"))]
    #[init(val = 0.6)]
    pub open_time: f32,
    /// Seconds the door stays open after the player leaves.
    #[export(range = (0.0, 10.0, 0.1, or_greater, suffix = "s"))]
    #[init(val = 1.0)]
    pub close_delay: f32,
"#,
        tres: "open_height = 2.5\nopen_time = 0.6\nclose_delay = 1.0\n",
        node_src: r#"//! __NAME__: __SUMMARY__
//! ```text
//! __NODE__ (Area3D)      <- this node: the zone in front of the door that opens it
//! ├── CollisionShape3D   <- how close the player must be (added automatically if missing)
//! └── Door (StaticBody3D) <- the door itself, which slides up (a placeholder is added if missing)
//! ```

use godot::classes::{Area3D, BoxMesh, BoxShape3D, CollisionShape3D, IArea3D, MeshInstance3D, StaticBody3D};
use godot::prelude::*;

use super::tuning::__TUNING__;

const DEFAULT_TUNING: &str = "res://mechanics/__ID__/tuning.tres";

#[derive(GodotClass)]
#[class(base = Area3D)]
pub struct __NODE__ {
    /// Leave empty to use the shared mechanics/__ID__/tuning.tres.
    #[export]
    tuning: Option<Gd<__TUNING__>>,
    /// 0 = closed, 1 = fully open.
    openness: f32,
    player_inside: bool,
    /// Seconds since the player left.
    since_left: f32,
    /// Where the door sits when closed.
    closed_at: Vector3,
    base: Base<Area3D>,
}

#[godot_api]
impl IArea3D for __NODE__ {
    fn init(base: Base<Area3D>) -> Self {
        Self { tuning: None, openness: 0.0, player_inside: false, since_left: 999.0, closed_at: Vector3::ZERO, base }
    }

    fn ready(&mut self) {
        if self.tuning.is_none() {
            self.tuning = Some(try_load::<__TUNING__>(DEFAULT_TUNING).unwrap_or_else(|_| __TUNING__::new_gd()));
        }
        self.ensure_parts();
        if let Some(door) = self.base().try_get_node_as::<Node3D>("Door") {
            self.closed_at = door.get_position();
        }
        self.signals().body_entered().connect_self(Self::on_body_entered);
        self.signals().body_exited().connect_self(Self::on_body_exited);
    }

    fn physics_process(&mut self, delta: f64) {
        let (open_height, open_time, close_delay) = {
            let t = self.tuning.clone().unwrap_or_else(__TUNING__::new_gd);
            let t = t.bind();
            (t.open_height, t.open_time, t.close_delay)
        };
        if !self.player_inside {
            self.since_left += delta as f32;
        }
        let want_open = self.player_inside || self.since_left < close_delay;
        let target = if want_open { 1.0 } else { 0.0 };
        let step = delta as f32 / open_time.max(0.01);
        let before = self.openness;
        self.openness = if self.openness < target { (self.openness + step).min(1.0) } else { (self.openness - step).max(0.0) };
        if let Some(mut door) = self.base().try_get_node_as::<Node3D>("Door") {
            // Smoothstep: starts and stops gently instead of jerking.
            let s = self.openness * self.openness * (3.0 - 2.0 * self.openness);
            door.set_position(self.closed_at + Vector3::UP * open_height * s);
        }
        if before < 1.0 && self.openness >= 1.0 {
            self.signals().opened().emit();
        } else if before > 0.0 && self.openness <= 0.0 {
            self.signals().closed().emit();
        }
    }
}

#[godot_api]
impl __NODE__ {
    /// Fully open.
    #[signal]
    pub fn opened();
    /// Fully closed again.
    #[signal]
    pub fn closed();

    fn on_body_entered(&mut self, body: Gd<Node3D>) {
        if body.is_in_group("player") {
            self.player_inside = true;
        }
    }

    fn on_body_exited(&mut self, body: Gd<Node3D>) {
        if body.is_in_group("player") {
            self.player_inside = false;
            self.since_left = 0.0;
        }
    }

    /// A 4 x 3 x 4 m zone and a 2 x 2.5 m door slab, if the scene doesn't give its own.
    fn ensure_parts(&mut self) {
        if self.base().try_get_node_as::<CollisionShape3D>("CollisionShape3D").is_none() {
            let mut shape = CollisionShape3D::new_alloc();
            shape.set_name("CollisionShape3D");
            let mut zone = BoxShape3D::new_gd();
            zone.set_size(Vector3::new(4.0, 3.0, 4.0));
            shape.set_shape(&zone);
            shape.set_position(Vector3::new(0.0, 1.5, 0.0));
            self.base_mut().add_child(&shape);
        }
        if self.base().try_get_node_as::<Node3D>("Door").is_none() {
            let mut door = StaticBody3D::new_alloc();
            door.set_name("Door");
            door.set_position(Vector3::new(0.0, 1.25, 0.0));
            let mut slab = BoxShape3D::new_gd();
            slab.set_size(Vector3::new(2.0, 2.5, 0.2));
            let mut shape = CollisionShape3D::new_alloc();
            shape.set_shape(&slab);
            door.add_child(&shape);
            let mut mesh = BoxMesh::new_gd();
            mesh.set_size(Vector3::new(2.0, 2.5, 0.2));
            let mut visual = MeshInstance3D::new_alloc();
            visual.set_mesh(&mesh);
            door.add_child(&visual);
            self.base_mut().add_child(&door);
        }
    }
}
"#,
        example: "It already works: the player walking into the zone slides the Door child up (open_height over open_time) and it closes \
close_delay seconds after they leave; signals opened/closed. Adapt only what they asked for (e.g. swing instead of slide = set_rotation on the door).",
    },
    Kind {
        id: "checkpoint",
        group: "trigger",
        keywords: &["checkpoint", "respawn", "save point", "spawn point", "falling off", "fall off"],
        uses: &[],
        base: "Area3D",
        when: "checkpoints: touching one sets where the player respawns after falling off the map",
        tuning_fields: r#"    /// If the player falls below this height (meters), they respawn at the last checkpoint they touched.
    #[export(range = (-500.0, 0.0, 0.5, or_less, suffix = "m"))]
    #[init(val = -15.0)]
    pub fall_height: f32,
"#,
        tres: "fall_height = -15.0\n",
        node_src: r#"//! __NAME__: __SUMMARY__
//! ```text
//! __NODE__ (Area3D)      <- this node: touch it to make it the active checkpoint
//! ├── CollisionShape3D   <- added automatically if missing
//! └── Visual             <- a placeholder post is added if missing
//! ```
//! The active checkpoint is remembered on the player (metadata "respawn_point"). Every checkpoint watches
//! the player; only the active one brings them back when they fall below fall_height.

use godot::classes::{Area3D, BoxShape3D, CharacterBody3D, CollisionShape3D, CylinderMesh, IArea3D, MeshInstance3D};
use godot::prelude::*;

use super::tuning::__TUNING__;

const DEFAULT_TUNING: &str = "res://mechanics/__ID__/tuning.tres";
const RESPAWN_META: &str = "respawn_point";

#[derive(GodotClass)]
#[class(base = Area3D)]
pub struct __NODE__ {
    /// Leave empty to use the shared mechanics/__ID__/tuning.tres.
    #[export]
    tuning: Option<Gd<__TUNING__>>,
    base: Base<Area3D>,
}

#[godot_api]
impl IArea3D for __NODE__ {
    fn init(base: Base<Area3D>) -> Self {
        Self { tuning: None, base }
    }

    fn ready(&mut self) {
        if self.tuning.is_none() {
            self.tuning = Some(try_load::<__TUNING__>(DEFAULT_TUNING).unwrap_or_else(|_| __TUNING__::new_gd()));
        }
        self.ensure_shape();
        self.signals().body_entered().connect_self(Self::on_body_entered);
    }

    fn physics_process(&mut self, _delta: f64) {
        let fall_height = self.tuning.as_ref().map(|t| t.bind().fall_height).unwrap_or(-15.0);
        let Some(player) = self.base().get_tree().get_first_node_in_group("player") else { return };
        let Ok(mut body) = player.try_cast::<CharacterBody3D>() else { return };
        if body.get_global_position().y >= fall_height || !body.has_meta(RESPAWN_META) {
            return;
        }
        // Only the active checkpoint (the one stored on the player) does the respawn.
        let spot = body.get_meta(RESPAWN_META).try_to::<Vector3>().unwrap_or(Vector3::ZERO);
        let here = self.respawn_spot();
        if spot.distance_to(here) > 0.01 {
            return;
        }
        body.set_global_position(here);
        body.set_velocity(Vector3::ZERO);
        self.signals().respawned().emit();
    }
}

#[godot_api]
impl __NODE__ {
    /// The player touched this checkpoint (it's now the active one).
    #[signal]
    pub fn activated();
    /// The player fell and came back here.
    #[signal]
    pub fn respawned();

    /// Where the player reappears: just above the checkpoint.
    fn respawn_spot(&self) -> Vector3 {
        self.base().get_global_position() + Vector3::UP * 0.5
    }

    fn on_body_entered(&mut self, body: Gd<Node3D>) {
        if !body.is_in_group("player") {
            return;
        }
        let spot = self.respawn_spot();
        let mut player = body.upcast::<Node>();
        player.set_meta(RESPAWN_META, &spot.to_variant());
        self.signals().activated().emit();
        godot_print!("Checkpoint reached.");
    }

    fn ensure_shape(&mut self) {
        if self.base().try_get_node_as::<CollisionShape3D>("CollisionShape3D").is_none() {
            let mut shape = CollisionShape3D::new_alloc();
            shape.set_name("CollisionShape3D");
            let mut zone = BoxShape3D::new_gd();
            zone.set_size(Vector3::new(2.0, 3.0, 2.0));
            shape.set_shape(&zone);
            shape.set_position(Vector3::new(0.0, 1.5, 0.0));
            self.base_mut().add_child(&shape);
        }
        if self.base().try_get_node_as::<Node3D>("Visual").is_none() {
            let mut visual = MeshInstance3D::new_alloc();
            visual.set_name("Visual");
            let mut post = CylinderMesh::new_gd();
            post.set_top_radius(0.1);
            post.set_bottom_radius(0.1);
            post.set_height(1.5);
            visual.set_mesh(&post);
            visual.set_position(Vector3::new(0.0, 0.75, 0.0));
            self.base_mut().add_child(&visual);
        }
    }
}
"#,
        example: "It already works: touching it stores it as the player's respawn point; when the player falls below fall_height, the active \
checkpoint puts them back (velocity zeroed) and emits respawned. Walk off the sandbox floor's edge to try it. Adapt only what they asked for.",
    },
    Kind {
        id: "chase",
        group: "mover",
        keywords: &["chase", "chases", "follow the player", "follows the player", "hunt", "pursue", "comes after"],
        uses: &[],
        base: "CharacterBody3D",
        when: "something that chases the player when they come close",
        tuning_fields: r#"    /// How fast it runs after the player, in meters per second.
    #[export(range = (0.0, 20.0, 0.1, or_greater, suffix = "m/s"))]
    #[init(val = 3.0)]
    pub speed: f32,
    /// It notices the player closer than this, in meters.
    #[export(range = (0.0, 100.0, 0.5, or_greater, suffix = "m"))]
    #[init(val = 10.0)]
    pub detect_range: f32,
    /// It stops this close to the player, in meters (so it doesn't push into them).
    #[export(range = (0.0, 10.0, 0.1, or_greater, suffix = "m"))]
    #[init(val = 1.2)]
    pub stop_distance: f32,
"#,
        tres: "speed = 3.0\ndetect_range = 10.0\nstop_distance = 1.2\n",
        node_src: r#"//! __NAME__: __SUMMARY__
//! ```text
//! __NODE__ (CharacterBody3D)  <- this node: runs after the player when they're near
//! ├── CollisionShape3D        <- added automatically if missing
//! └── Visual                  <- a placeholder capsule is added if missing
//! ```

use godot::classes::{CapsuleMesh, CapsuleShape3D, CharacterBody3D, CollisionShape3D, ICharacterBody3D, MeshInstance3D, ProjectSettings};
use godot::prelude::*;

use super::tuning::__TUNING__;

const DEFAULT_TUNING: &str = "res://mechanics/__ID__/tuning.tres";

#[derive(GodotClass)]
#[class(base = CharacterBody3D)]
pub struct __NODE__ {
    /// Leave empty to use the shared mechanics/__ID__/tuning.tres.
    #[export]
    tuning: Option<Gd<__TUNING__>>,
    chasing: bool,
    base: Base<CharacterBody3D>,
}

#[godot_api]
impl ICharacterBody3D for __NODE__ {
    fn init(base: Base<CharacterBody3D>) -> Self {
        Self { tuning: None, chasing: false, base }
    }

    fn ready(&mut self) {
        if self.tuning.is_none() {
            self.tuning = Some(try_load::<__TUNING__>(DEFAULT_TUNING).unwrap_or_else(|_| __TUNING__::new_gd()));
        }
        self.ensure_body();
    }

    fn physics_process(&mut self, delta: f64) {
        let (speed, detect_range, stop_distance) = {
            let t = self.tuning.clone().unwrap_or_else(__TUNING__::new_gd);
            let t = t.bind();
            (t.speed, t.detect_range, t.stop_distance)
        };
        let mut velocity = self.base().get_velocity();
        if !self.base().is_on_floor() {
            velocity.y -= gravity() * delta as f32;
        }
        let me = self.base().get_global_position();
        let target = self.base().get_tree().get_first_node_in_group("player")
            .and_then(|p| p.try_cast::<Node3D>().ok())
            .map(|p| p.get_global_position());
        let mut to = target.map(|t| t - me).unwrap_or(Vector3::ZERO);
        to.y = 0.0;
        let distance = to.length();
        let chasing = target.is_some() && distance < detect_range;
        if chasing && distance > stop_distance {
            let dir = to / distance;
            velocity.x = dir.x * speed;
            velocity.z = dir.z * speed;
        } else {
            velocity.x = 0.0;
            velocity.z = 0.0;
        }
        if chasing != self.chasing {
            self.chasing = chasing;
            if chasing { self.signals().spotted_player().emit(); } else { self.signals().lost_player().emit(); }
        }
        self.base_mut().set_velocity(velocity);
        self.base_mut().move_and_slide();
    }
}

#[godot_api]
impl __NODE__ {
    /// The player came within detect_range.
    #[signal]
    pub fn spotted_player();
    /// The player got away.
    #[signal]
    pub fn lost_player();

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

fn gravity() -> f32 {
    ProjectSettings::singleton().get_setting("physics/3d/default_gravity").try_to::<f32>().unwrap_or(9.8)
}
"#,
        example: "It already works: when the player (group \"player\") is within detect_range it runs toward them, stopping at stop_distance; \
signals spotted_player/lost_player. Adapt only what they asked for.",
    },
    Kind {
        id: "regen",
        group: "timer",
        keywords: &["regen", "regenerat", "heal over time", "recover health", "health comes back", "slowly heal"],
        uses: &["stats"],
        base: "Node",
        when: "health regenerates after not being hurt for a while (uses Character Stats)",
        tuning_fields: r#"    /// Seconds without taking damage before healing starts.
    #[export(range = (0.0, 30.0, 0.1, or_greater, suffix = "s"))]
    #[init(val = 4.0)]
    pub delay: f32,
    /// Health healed per second once it starts.
    #[export(range = (0.0, 100.0, 0.5, or_greater, suffix = "hp/s"))]
    #[init(val = 5.0)]
    pub rate: f32,
"#,
        tres: "delay = 4.0\nrate = 5.0\n",
        node_src: r#"//! __NAME__: __SUMMARY__
//! ```text
//! Character (the player or an enemy)
//! ├── CharacterStats   <- its health (Character Stats mechanic)
//! └── __NODE__         <- this node: heals the stats after a quiet time
//! ```

use godot::classes::{INode, Node};
use godot::prelude::*;

use super::tuning::__TUNING__;
use crate::stats::find_stats;

const DEFAULT_TUNING: &str = "res://mechanics/__ID__/tuning.tres";

#[derive(GodotClass)]
#[class(base = Node)]
pub struct __NODE__ {
    /// Leave empty to use the shared mechanics/__ID__/tuning.tres.
    #[export]
    tuning: Option<Gd<__TUNING__>>,
    /// Seconds since health last went down.
    quiet: f32,
    /// Health last frame (to notice damage).
    last_health: f32,
    base: Base<Node>,
}

#[godot_api]
impl INode for __NODE__ {
    fn init(base: Base<Node>) -> Self {
        Self { tuning: None, quiet: 0.0, last_health: -1.0, base }
    }

    fn ready(&mut self) {
        if self.tuning.is_none() {
            self.tuning = Some(try_load::<__TUNING__>(DEFAULT_TUNING).unwrap_or_else(|_| __TUNING__::new_gd()));
        }
    }

    fn process(&mut self, delta: f64) {
        let (delay, rate) = {
            let t = self.tuning.clone().unwrap_or_else(__TUNING__::new_gd);
            let t = t.bind();
            (t.delay, t.rate)
        };
        let Some(parent) = self.base().get_parent() else { return };
        let Some(mut stats) = find_stats(&parent) else { return };
        let (health, max) = { let s = stats.bind(); (s.get_health(), s.get_max_health()) };
        if health < self.last_health {
            self.quiet = 0.0; // just got hurt: start waiting again
        } else {
            self.quiet += delta as f32;
        }
        if self.quiet >= delay && health > 0.0 && health < max {
            stats.bind_mut().heal(rate * delta as f32);
        }
        self.last_health = stats.bind().get_health();
    }
}

#[godot_api]
impl __NODE__ {
    /// True while it's healing.
    #[func]
    pub fn is_healing(&self) -> bool {
        let delay = self.tuning.as_ref().map(|t| t.bind().delay).unwrap_or(4.0);
        self.quiet >= delay
    }
}
"#,
        example: "It already works: put it next to a CharacterStats (same parent); after `delay` seconds without damage it heals `rate` hp per second \
until full (stops at 0 health). Adapt only what they asked for.",
    },
    Kind {
        id: "score",
        group: "timer",
        keywords: &["score", "points", "high score", "highscore", "combo"],
        uses: &[],
        base: "Node",
        when: "a score / points total that other things add to",
        tuning_fields: r#"    /// Points multiplier (2 = double points), for bonus rounds or difficulty.
    #[export(range = (0.0, 10.0, 0.1, or_greater, suffix = "x"))]
    #[init(val = 1.0)]
    pub multiplier: f32,
"#,
        tres: "multiplier = 1.0\n",
        node_src: r#"//! __NAME__: __SUMMARY__
//! Put one `__NODE__` in the scene. Anything can add points: find it with `__NODE__::find(&node)`
//! (it joins the "__ID__" group) and call add_points, or connect to `changed` to show the score.

use godot::classes::{INode, Node};
use godot::prelude::*;

use super::tuning::__TUNING__;

const DEFAULT_TUNING: &str = "res://mechanics/__ID__/tuning.tres";
const GROUP: &str = "__ID__";

#[derive(GodotClass)]
#[class(base = Node)]
pub struct __NODE__ {
    /// Leave empty to use the shared mechanics/__ID__/tuning.tres.
    #[export]
    tuning: Option<Gd<__TUNING__>>,
    total: i64,
    best: i64,
    base: Base<Node>,
}

#[godot_api]
impl INode for __NODE__ {
    fn init(base: Base<Node>) -> Self {
        Self { tuning: None, total: 0, best: 0, base }
    }

    fn ready(&mut self) {
        if self.tuning.is_none() {
            self.tuning = Some(try_load::<__TUNING__>(DEFAULT_TUNING).unwrap_or_else(|_| __TUNING__::new_gd()));
        }
        self.base_mut().add_to_group(GROUP);
    }
}

#[godot_api]
impl __NODE__ {
    /// The score changed: the new total and the best so far.
    #[signal]
    pub fn changed(total: i64, best: i64);

    /// Add points (times the multiplier). Returns the new total.
    #[func]
    pub fn add_points(&mut self, points: i64) -> i64 {
        let multiplier = self.tuning.as_ref().map(|t| t.bind().multiplier).unwrap_or(1.0);
        self.total += (points as f32 * multiplier).round() as i64;
        self.best = self.best.max(self.total);
        let (total, best) = (self.total, self.best);
        self.signals().changed().emit(total, best);
        total
    }

    /// Back to zero (the best score stays).
    #[func]
    pub fn reset(&mut self) {
        self.total = 0;
        let best = self.best;
        self.signals().changed().emit(0, best);
    }

    #[func]
    pub fn get_total(&self) -> i64 {
        self.total
    }

    /// The scene's score keeper, from any node.
    #[allow(dead_code)]
    pub fn find(node: &Gd<Node>) -> Option<Gd<__NODE__>> {
        node.get_tree().get_first_node_in_group(GROUP)?.try_cast::<__NODE__>().ok()
    }
}
"#,
        example: "It already works: add_points(n) adds n x multiplier and emits changed(total, best); reset(); find(&node) from anywhere. \
Adapt only what they asked for.",
    },
];

/// Pick the starting code: an exact variant id; else the variant whose keywords match the request
/// (name/summary/id) inside the asked family; else the family's first variant; else by base class.
pub fn pick(kind: &str, base: &str, hint: &str) -> Option<&'static Kind> {
    let kind = kind.trim().to_lowercase().replace([' ', '-'], "_");
    if kind == "custom" {
        return None;
    }
    if let Some(k) = KINDS.iter().find(|k| k.id == kind) {
        // A generic family pick (e.g. "trigger") can still be refined by the request's words.
        let family_default = KINDS.iter().find(|f| f.group == k.group).map(|f| f.id) == Some(k.id);
        if !family_default {
            return Some(k);
        }
    }
    let group = KINDS.iter().find(|k| k.id == kind || k.group == kind).map(|k| k.group).or(match base.trim() {
        "Area3D" => Some("trigger"),
        "CharacterBody3D" => Some("mover"),
        _ => None,
    });
    let hint = hint.to_lowercase().replace('_', " ");
    let by_words = |k: &&Kind| k.keywords.iter().any(|w| hint.contains(w));
    match group {
        Some(g) => KINDS.iter().filter(|k| k.group == g).find(by_words).or_else(|| KINDS.iter().find(|k| k.group == g)),
        None => KINDS.iter().find(by_words),
    }
}

/// Does the starting code already fit the request (a specific variant, by its id or by the request's words)?
/// Then leaving it unchanged is fine; only a generic family example must be adapted.
pub fn exact_fit(kind: &str, base: &str, hint: &str) -> bool {
    let Some(k) = pick(kind, base, hint) else { return false };
    let hint = hint.to_lowercase().replace('_', " ");
    let family_default = KINDS.iter().find(|f| f.group == k.group).map(|f| f.id) == Some(k.id);
    !family_default || k.keywords.iter().any(|w| hint.contains(w))
}

pub fn fill(t: &str, node: &str, tuning: &str, id: &str, name: &str, summary: &str) -> String {
    t.replace("__NODE__", node).replace("__TUNING__", tuning).replace("__ID__", id)
        .replace("__NAME__", name).replace("__SUMMARY__", summary).replace("__ACTION__", id)
}

/// "Shift", "E", "q", "space"... -> the Key constant name used in the templates.
pub fn key_const(name: &str) -> Option<&'static str> {
    let n = name.trim().to_lowercase();
    const KEYS: &[(&str, &str)] = &[("shift", "SHIFT"), ("ctrl", "CTRL"), ("control", "CTRL"), ("alt", "ALT"), ("space", "SPACE"),
        ("tab", "TAB"), ("enter", "ENTER"), ("q", "Q"), ("e", "E"), ("r", "R"), ("f", "F"), ("c", "C"), ("v", "V"), ("x", "X"),
        ("z", "Z"), ("g", "G"), ("t", "T"), ("1", "KEY_1"), ("2", "KEY_2"), ("3", "KEY_3")];
    KEYS.iter().find(|(k, _)| *k == n).map(|(_, c)| *c)
}
