#!/usr/bin/env python3
"""Ember's game design pattern library: why beloved games feel the way they do, and how to build it.

Each pattern: what the player FEELS, where it shows up, how it works (distilled from real
open-source game code where noted), the knobs that change the feel, and, for most, verified
godot-rust 0.5 code (verify_patterns.py builds and playtests every one).

These are reference material for understanding a creator's intent, never templates to impose:
Ember should ask which part of "feels like X" the creator means.
"""

PATTERNS = []


def pattern(**kw):
    PATTERNS.append(kw)


# ---------------------------------------------------------------------------------------------
pattern(
    name="Forgiving platformer jump (Celeste-style)",
    keywords="platformer jump coyote time jump buffer variable jump height game feel tight controls responsive celeste mario hollow knight",
    feel="Jumping feels responsive and fair: the game does what you meant, not exactly what you pressed. Players blame themselves, not the controls.",
    seen_in="Celeste, Super Meat Boy, Hollow Knight, most modern platformers.",
    how="""Four small rules, all visible in Celeste's Player.cs (MIT, released by its developer as a learning resource):
- Coyote time: you can still jump for 0.1 s after walking off a ledge (JumpGraceTime = 0.1).
- Jump buffering: a jump pressed slightly before landing still happens (Celeste's input buffer is about 0.08 s).
- Variable height: while the button is held the jump keeps its upward speed for up to 0.2 s (VarJumpTime); letting go cuts it short.
- Floaty apex: near the top of a held jump (vertical speed under 40 px/s in Celeste) gravity is halved, giving a moment of hang time to aim.
Running approaches top speed with acceleration rather than snapping to it, and air control is reduced (AirMult = 0.65).""",
    knobs="Coyote/buffer windows (0.05-0.15 s: bigger = more forgiving). Gravity vs jump speed (higher both = snappier). Air multiplier (lower = more committed jumps). Apex threshold (bigger = floatier).",
    base="CharacterBody2D", cls="Hero",
    code=r'''use godot::classes::{CharacterBody2D, ICharacterBody2D, Input};
use godot::prelude::*;

const COYOTE_TIME: f32 = 0.1; // can still jump this long after leaving a ledge
const BUFFER_TIME: f32 = 0.08; // a jump pressed this early before landing still counts
const VAR_JUMP_TIME: f32 = 0.2; // how long holding jump keeps you rising
const APEX_THRESHOLD: f32 = 120.0; // below this vertical speed, gravity is halved while holding jump

/// A platformer controller with Celeste's forgiveness rules (speeds scaled 3x from its 320x180 screen).
#[derive(GodotClass)]
#[class(base = CharacterBody2D)]
pub struct Hero {
    #[export]
    max_run: f32,
    #[export]
    run_accel: f32,
    #[export]
    air_mult: f32,
    #[export]
    gravity: f32,
    #[export]
    max_fall: f32,
    #[export]
    jump_speed: f32,
    coyote: f32,
    buffer: f32,
    var_jump: f32,
    base: Base<CharacterBody2D>,
}

fn approach(value: f32, target: f32, step: f32) -> f32 {
    if value < target { (value + step).min(target) } else { (value - step).max(target) }
}

#[godot_api]
impl ICharacterBody2D for Hero {
    fn init(base: Base<CharacterBody2D>) -> Self {
        Self { max_run: 270.0, run_accel: 3000.0, air_mult: 0.65, gravity: 2700.0, max_fall: 480.0,
               jump_speed: -315.0, coyote: 0.0, buffer: 0.0, var_jump: 0.0, base }
    }

    fn physics_process(&mut self, delta: f64) {
        let dt = delta as f32;
        let input = Input::singleton();
        let on_floor = self.base().is_on_floor();
        let mut velocity = self.base().get_velocity();

        // Forgiveness timers
        if on_floor { self.coyote = COYOTE_TIME; } else { self.coyote -= dt; }
        if input.is_action_just_pressed("ui_accept") { self.buffer = BUFFER_TIME; } else { self.buffer -= dt; }

        // Run toward top speed, with less grip in the air
        let grip = if on_floor { 1.0 } else { self.air_mult };
        let move_x = input.get_axis("ui_left", "ui_right");
        velocity.x = approach(velocity.x, self.max_run * move_x, self.run_accel * grip * dt);

        // Gravity, halved near the top of a held jump
        let holding = input.is_action_pressed("ui_accept");
        let gravity_mult = if velocity.y.abs() < APEX_THRESHOLD && holding { 0.5 } else { 1.0 };
        velocity.y = approach(velocity.y, self.max_fall, self.gravity * gravity_mult * dt);

        // Holding jump keeps you rising for a moment; letting go cuts the jump short
        if self.var_jump > 0.0 {
            self.var_jump -= dt;
            if holding { velocity.y = velocity.y.min(self.jump_speed); } else { self.var_jump = 0.0; }
        }

        // Jump: a buffered press while coyote time is left
        if self.buffer > 0.0 && self.coyote > 0.0 {
            velocity.y = self.jump_speed;
            self.var_jump = VAR_JUMP_TIME;
            self.buffer = 0.0;
            self.coyote = 0.0;
        }

        self.base_mut().set_velocity(velocity);
        self.base_mut().move_and_slide();
    }
}
''',
    source="Celeste Player.cs (github.com/NoelFB/Celeste, MIT)",
)

# ---------------------------------------------------------------------------------------------
pattern(
    name="Invincibility frames (i-frames) after getting hit",
    keywords="iframes invincibility invulnerable damage hit blink flash health knockback mercy hurt",
    feel="Getting hit is a setback, not a death spiral: you get a moment to recover, and the blinking tells you you're safe for now.",
    seen_in="Mega Man, Castlevania, Hollow Knight, Zelda, almost every action game with health.",
    how="After taking damage, ignore further damage for a short window (often 0.5-1.5 s) and make the character blink so the player can see it. Many games also knock the player back away from the hit so they aren't stuck inside the enemy.",
    knobs="Window length (longer = more forgiving). Blink rate. Knockback strength. Whether i-frames also apply to hazards like spikes.",
    base="Node", cls="Health",
    code=r'''use godot::classes::{INode, Node, Node2D};
use godot::prelude::*;

/// Health with a mercy window: add it as a child of the player (or an enemy).
#[derive(GodotClass)]
#[class(base = Node)]
pub struct Health {
    #[export]
    max_health: i32,
    #[export]
    invulnerable_time: f32,
    health: i32,
    invulnerable: f32,
    base: Base<Node>,
}

#[godot_api]
impl INode for Health {
    fn init(base: Base<Node>) -> Self {
        Self { max_health: 5, invulnerable_time: 1.0, health: 5, invulnerable: 0.0, base }
    }

    fn ready(&mut self) {
        self.health = self.max_health;
    }

    fn process(&mut self, delta: f64) {
        if self.invulnerable <= 0.0 {
            return;
        }
        self.invulnerable -= delta as f32;
        // Blink ten times a second while safe, and end visible
        let visible = self.invulnerable <= 0.0 || (self.invulnerable * 10.0) as i32 % 2 == 0;
        if let Some(mut owner) = self.base().get_parent().and_then(|p| p.try_cast::<Node2D>().ok()) {
            owner.set_visible(visible);
        }
    }
}

#[godot_api]
impl Health {
    #[signal]
    pub fn health_changed(health: i32);
    #[signal]
    pub fn died();

    /// Returns false if the hit was ignored (still invulnerable, or already dead).
    #[func]
    pub fn take_damage(&mut self, amount: i32) -> bool {
        if self.invulnerable > 0.0 || self.health <= 0 {
            return false;
        }
        self.health = (self.health - amount).max(0);
        self.invulnerable = self.invulnerable_time;
        let health = self.health;
        self.signals().health_changed().emit(health);
        if health == 0 {
            self.signals().died().emit();
        }
        true
    }
}
''',
    source="Common practice; described here from the design.",
)

# ---------------------------------------------------------------------------------------------
pattern(
    name="Stamina that gates actions (Souls-style)",
    keywords="stamina endurance fatigue souls dark souls elden ring bloodborne commitment attack dodge roll resource management combat",
    feel="Every attack and dodge is a decision. You can't mash: overcommitting leaves you exhausted and open, so fights become a rhythm of attack, retreat and recover.",
    seen_in="Dark Souls, Elden Ring, Sekiro (as posture), Monster Hunter; Morrowind's fatigue is an ancestor.",
    how="Actions cost stamina. In the Souls games an action is allowed while stamina is above zero even if it costs more than you have (so the last swing is always possible, but leaves you empty). Stamina regenerates only after a short delay since the last spend, which is what punishes button mashing. Blocking slows regeneration.",
    knobs="Regen delay (longer = more punishing). Regen rate. Whether an action needs the full cost or just any stamina. Costs per action (heavier weapon = more cost).",
    base="Node", cls="Stamina",
    code=r'''use godot::classes::{INode, Node};
use godot::prelude::*;

#[derive(GodotClass)]
#[class(base = Node)]
pub struct Stamina {
    #[export]
    max_stamina: f32,
    #[export]
    regen_per_second: f32,
    #[export]
    regen_delay: f32,
    stamina: f32,
    since_spent: f32,
    base: Base<Node>,
}

#[godot_api]
impl INode for Stamina {
    fn init(base: Base<Node>) -> Self {
        Self { max_stamina: 100.0, regen_per_second: 45.0, regen_delay: 0.6, stamina: 100.0, since_spent: 0.0, base }
    }

    fn process(&mut self, delta: f64) {
        self.since_spent += delta as f32;
        // Regenerate only after a pause: mashing keeps you empty
        if self.since_spent >= self.regen_delay && self.stamina < self.max_stamina {
            self.stamina = (self.stamina + self.regen_per_second * delta as f32).min(self.max_stamina);
            let value = self.stamina;
            self.signals().stamina_changed().emit(value);
        }
    }
}

#[godot_api]
impl Stamina {
    #[signal]
    pub fn stamina_changed(value: f32);

    /// Souls rule: allowed while you have ANY stamina, even if the cost is higher.
    #[func]
    pub fn try_spend(&mut self, cost: f32) -> bool {
        if self.stamina <= 0.0 {
            return false;
        }
        self.stamina = (self.stamina - cost).max(0.0);
        self.since_spent = 0.0;
        let value = self.stamina;
        self.signals().stamina_changed().emit(value);
        true
    }
}
''',
    source="Design described from the games; Morrowind's fatigue system in OpenMW (GPL-3.0) for comparison.",
)

# ---------------------------------------------------------------------------------------------
pattern(
    name="Readable, fair enemy AI (Doom-style)",
    keywords="enemy ai monster chase attack fair readable telegraph reaction time doom shooter behavior state",
    feel="Enemies feel dangerous but fair: they react a beat after seeing you, don't spam attacks, and move in committed bursts you can read and dodge.",
    seen_in="Doom (1993) and countless action games since.",
    how="""From Doom's A_Chase in p_enemy.c (GPL-2.0, released by id Software):
- reactiontime: a monster won't attack until a short delay after it notices you, giving you time to respond.
- MF_JUSTATTACKED: after attacking, the next think is spent moving, never attacking twice in a row.
- movecount: a monster commits to a direction for several steps before picking a new one, so movement is readable rather than jittery.
- P_CheckMissileRange: the chance to shoot falls with distance (and skips the check entirely when too far), so close range is more dangerous than far.""",
    knobs="Reaction time. Minimum time between attacks. How long it commits to a direction. Attack chance vs distance. Speed.",
    base="Node2D", cls="Monster",
    code=r'''use godot::classes::{INode2D, Node2D};
use godot::global::{randf, randf_range};
use godot::prelude::*;

#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct Monster {
    #[export]
    target: Option<Gd<Node2D>>,
    #[export]
    speed: f32,
    #[export]
    reaction_time: f32,
    reaction_left: f32,
    just_attacked: bool,
    think_timer: f32,
    move_left: f32,
    direction: Vector2,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for Monster {
    fn init(base: Base<Node2D>) -> Self {
        Self { target: None, speed: 120.0, reaction_time: 0.5, reaction_left: 0.5, just_attacked: false,
               think_timer: 0.0, move_left: 0.0, direction: Vector2::ZERO, base }
    }

    fn process(&mut self, delta: f64) {
        let dt = delta as f32;
        let Some(target) = self.target.clone() else { return };
        let me = self.base().get_global_position();
        let to_target = target.get_global_position() - me;

        self.reaction_left -= dt;
        self.think_timer -= dt;
        if self.think_timer <= 0.0 {
            self.think_timer = 0.25; // think four times a second, like Doom's tics
            self.think(to_target);
        }
        // Commit to the chosen direction for a while: readable movement
        if self.move_left > 0.0 {
            self.move_left -= dt;
            let step = self.direction * self.speed * dt;
            self.base_mut().set_global_position(me + step);
        }
    }
}

#[godot_api]
impl Monster {
    #[signal]
    pub fn attacked();

    fn think(&mut self, to_target: Vector2) {
        // Never attack twice in a row
        if self.just_attacked {
            self.just_attacked = false;
            self.pick_direction(to_target);
            return;
        }
        // Wait a beat after first noticing the player; closer means more likely to attack
        let distance = to_target.length();
        let chance = (1.0 - distance / 600.0).clamp(0.0, 0.8);
        if self.reaction_left <= 0.0 && distance < 600.0 && (randf() as f32) < chance {
            self.just_attacked = true;
            self.signals().attacked().emit();
            return;
        }
        if self.move_left <= 0.0 {
            self.pick_direction(to_target);
        }
    }

    fn pick_direction(&mut self, to_target: Vector2) {
        // Mostly toward the player, with some wobble so it isn't a perfect homing missile
        let wobble = randf_range(-0.6, 0.6) as f32;
        self.direction = to_target.normalized().rotated(wobble);
        self.move_left = randf_range(0.4, 1.0) as f32;
    }
}
''',
    source="DOOM linuxdoom-1.10 p_enemy.c (github.com/id-Software/DOOM, GPL-2.0)",
)

# ---------------------------------------------------------------------------------------------
pattern(
    name="Skills that grow by using them (Bethesda-style)",
    keywords="skill leveling learn by doing use based progression elder scrolls skyrim morrowind oblivion rpg character growth experience",
    feel="You become what you do: sneak a lot and you get sneaky. Progress feels earned and personal, and players shape their character through play instead of menus.",
    seen_in="The Elder Scrolls (Morrowind, Oblivion, Skyrim), RuneScape, Final Fantasy II.",
    how="""From OpenMW's NpcStats (GPL-3.0), the open reimplementation of Morrowind:
- Each use of a skill adds progress (different actions give different amounts).
- A skill levels up when progress reaches (1 + current level) x a class factor, so higher skills take longer: major skills use a factor below 1 (faster), miscellaneous skills above 1 (slower).
- Raising your important skills enough times raises your overall character level.""",
    knobs="Progress per use. The growth curve (linear here; steeper curves slow late game). Which skills count as 'major'. Caps.",
    base="Node", cls="Skills",
    code=r'''use std::collections::HashMap;

use godot::classes::{INode, Node};
use godot::prelude::*;

#[derive(GodotClass)]
#[class(base = Node)]
pub struct Skills {
    levels: HashMap<String, i32>,
    progress: HashMap<String, f32>,
    base: Base<Node>,
}

#[godot_api]
impl INode for Skills {
    fn init(base: Base<Node>) -> Self {
        Self { levels: HashMap::new(), progress: HashMap::new(), base }
    }
}

#[godot_api]
impl Skills {
    #[signal]
    pub fn skill_up(skill: GString, level: i32);

    /// Call whenever the player does something, e.g. use_skill("sneak", 1.0, true).
    #[func]
    pub fn use_skill(&mut self, skill: GString, amount: f32, major: bool) {
        let key = skill.to_string();
        let level = *self.levels.get(&key).unwrap_or(&5);
        let progress = self.progress.get(&key).copied().unwrap_or(0.0) + amount;
        // Morrowind's rule: needs (1 + level) x factor progress; major skills grow faster
        let factor = if major { 0.75 } else { 1.25 };
        let needed = (1 + level) as f32 * factor;
        if progress >= needed {
            self.levels.insert(key.clone(), level + 1);
            self.progress.insert(key, 0.0);
            self.signals().skill_up().emit(&skill, level + 1);
        } else {
            self.progress.insert(key, progress);
        }
    }

    #[func]
    pub fn level_of(&self, skill: GString) -> i32 {
        *self.levels.get(&skill.to_string()).unwrap_or(&5)
    }
}
''',
    source="OpenMW apps/openmw/mwmechanics/npcstats.cpp (github.com/OpenMW/openmw, GPL-3.0)",
)

# ---------------------------------------------------------------------------------------------
pattern(
    name="Camera that looks ahead",
    keywords="camera follow lookahead smooth platformer view framing deadzone camera2d",
    feel="You can see where you're going, not where you've been. The camera feels calm instead of glued to the player.",
    seen_in="Super Mario World, SuperTux, Sonic, most side-scrollers.",
    how="SuperTux's camera.cpp (GPL-3.0) shifts the view toward the direction the player is moving (lookahead) and eases into it rather than snapping. Godot's Camera2D already does smoothing and drag margins (a dead zone the player can move inside without the camera moving); a lookahead offset on top makes the view lead the player.",
    knobs="Lookahead distance. How quickly the offset eases. Position smoothing speed. Drag margins (dead zone size).",
    base="Camera2D", cls="LookaheadCamera",
    code=r'''use godot::classes::{Camera2D, ICamera2D, Node2D};
use godot::prelude::*;

#[derive(GodotClass)]
#[class(base = Camera2D)]
pub struct LookaheadCamera {
    #[export]
    target: Option<Gd<Node2D>>,
    #[export]
    lookahead: f32,
    last_position: Vector2,
    base: Base<Camera2D>,
}

#[godot_api]
impl ICamera2D for LookaheadCamera {
    fn init(base: Base<Camera2D>) -> Self {
        Self { target: None, lookahead: 120.0, last_position: Vector2::ZERO, base }
    }

    fn ready(&mut self) {
        self.base_mut().set_position_smoothing_enabled(true);
        self.base_mut().set_position_smoothing_speed(6.0);
    }

    fn process(&mut self, delta: f64) {
        let Some(target) = self.target.clone() else { return };
        let position = target.get_global_position();
        let moved = position - self.last_position;
        self.last_position = position;
        // Lead in the direction of travel, easing so it never jerks
        let wanted = if moved.length() > 0.5 { moved.normalized() * self.lookahead } else { Vector2::ZERO };
        let offset = self.base().get_offset();
        let eased = offset.lerp(wanted, (3.0 * delta as f32).min(1.0));
        self.base_mut().set_offset(eased);
        self.base_mut().set_global_position(position);
    }
}
''',
    source="SuperTux src/object/camera.cpp (github.com/SuperTux/supertux, GPL-3.0)",
)

# ---------------------------------------------------------------------------------------------
pattern(
    name="Escalating enemy waves",
    keywords="waves spawner tower defense survival horde difficulty ramp escalation vampire survivors mindustry",
    feel="Tension builds steadily: each wave is a little harder than the last, with breathers in between to plan and recover.",
    seen_in="Mindustry, Plants vs. Zombies, Vampire Survivors, tower defense games, horde modes.",
    how="Mindustry (GPL-3.0) defines waves as groups of enemies that start at some wave, grow by a fixed amount per wave, and stop growing at a cap; a countdown between waves gives players time to build. The core loop: count grows each wave, the break between waves gives a rhythm of tension and release.",
    knobs="Starting count. Growth per wave. Cap. Time between waves. Spawn spread within a wave.",
    base="Node2D", cls="WaveSpawner",
    code=r'''use godot::classes::{INode2D, Node2D, PackedScene};
use godot::global::randf_range;
use godot::prelude::*;

#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct WaveSpawner {
    #[export]
    enemy_scene: Option<Gd<PackedScene>>,
    #[export]
    first_wave_size: i32,
    #[export]
    growth_per_wave: i32,
    #[export]
    max_wave_size: i32,
    #[export]
    time_between_waves: f32,
    wave: i32,
    countdown: f32,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for WaveSpawner {
    fn init(base: Base<Node2D>) -> Self {
        Self { enemy_scene: None, first_wave_size: 3, growth_per_wave: 2, max_wave_size: 30,
               time_between_waves: 8.0, wave: 0, countdown: 2.0, base }
    }

    fn process(&mut self, delta: f64) {
        self.countdown -= delta as f32;
        if self.countdown <= 0.0 {
            self.countdown = self.time_between_waves;
            self.start_wave();
        }
    }
}

#[godot_api]
impl WaveSpawner {
    #[signal]
    pub fn wave_started(wave: i32, size: i32);

    fn start_wave(&mut self) {
        self.wave += 1;
        let size = (self.first_wave_size + (self.wave - 1) * self.growth_per_wave).min(self.max_wave_size);
        let wave = self.wave;
        self.signals().wave_started().emit(wave, size);
        let Some(scene) = self.enemy_scene.clone() else { return };
        for _ in 0..size {
            if let Some(mut enemy) = scene.instantiate().and_then(|n| n.try_cast::<Node2D>().ok()) {
                let spot = Vector2::new(randf_range(-300.0, 300.0) as f32, randf_range(-200.0, 200.0) as f32);
                enemy.set_position(spot);
                self.base_mut().add_child(&enemy);
            }
        }
    }
}
''',
    source="Mindustry core/src/mindustry/game/SpawnGroup.java (github.com/Anuken/Mindustry, GPL-3.0)",
)

# ---------------------------------------------------------------------------------------------
pattern(
    name="Weighted loot tables",
    keywords="loot drop random rarity weighted chance items treasure diablo roguelike reward",
    feel="Rewards feel exciting because rare things are rare: most drops are ordinary, so the occasional rare one is a thrill.",
    seen_in="Diablo, Borderlands, Shattered Pixel Dungeon, every loot game.",
    how="Give each possible drop a weight; pick a random number up to the total weight and walk the list. Shattered Pixel Dungeon's Generator (GPL-3.0) goes further: after an item category drops, its weight is reduced so you don't get five of the same kind in a row, and it recovers over time (a 'deck' feel that avoids streaks).",
    knobs="Weights per rarity. Whether drops 'remember' recent results (streak protection). Pity timers (a guaranteed rare after N misses).",
    base="Node", cls="LootTable",
    code=r'''use godot::classes::{INode, Node};
use godot::global::randf;
use godot::prelude::*;

#[derive(GodotClass)]
#[class(base = Node)]
pub struct LootTable {
    entries: Vec<(String, f32)>,
    base: Base<Node>,
}

#[godot_api]
impl INode for LootTable {
    fn init(base: Base<Node>) -> Self {
        let entries = vec![("coin".to_string(), 60.0), ("potion".to_string(), 30.0), ("gem".to_string(), 9.0), ("crown".to_string(), 1.0)];
        Self { entries, base }
    }
}

#[godot_api]
impl LootTable {
    #[func]
    pub fn add(&mut self, item: GString, weight: f32) {
        self.entries.push((item.to_string(), weight));
    }

    /// Picks one item; the chance of each is its weight divided by the total.
    #[func]
    pub fn roll(&mut self) -> GString {
        let total: f32 = self.entries.iter().map(|(_, w)| w).sum();
        let mut pick = randf() as f32 * total;
        for (item, weight) in &self.entries {
            if pick < *weight {
                return GString::from(item.as_str());
            }
            pick -= weight;
        }
        GString::new()
    }
}
''',
    source="Shattered Pixel Dungeon items/Generator.java (github.com/00-Evan/shattered-pixel-dungeon, GPL-3.0)",
)

# ---------------------------------------------------------------------------------------------
pattern(
    name="Hit stop and screen shake (game juice)",
    keywords="juice game feel hit stop freeze frame screen shake impact feedback punchy combat polish",
    feel="Hits feel heavy and impactful. A tiny freeze on impact plus a short shake makes the player FEEL the blow, even with simple art.",
    seen_in="Celeste, Hollow Knight, Street Fighter, Vlambeer games (Nuclear Throne), Hades.",
    how="Hit stop: on a strong hit, slow time almost to zero for a few hundredths of a second (Celeste freezes the whole game for ~0.05 s on dashes and hits). Screen shake: offset the camera by a random amount that decays quickly. Both must be SHORT; too much feels sluggish or nauseating. Use real time for the freeze, since game time is what you're slowing.",
    knobs="Freeze length (0.03-0.1 s). Shake strength and decay. Only on important hits, or it stops meaning anything.",
    base="Camera2D", cls="JuiceCamera",
    code=r'''use godot::classes::{Camera2D, Engine, ICamera2D, Time};
use godot::global::randf_range;
use godot::prelude::*;

#[derive(GodotClass)]
#[class(base = Camera2D)]
pub struct JuiceCamera {
    shake: f32,
    freeze_until_ms: u64,
    base: Base<Camera2D>,
}

#[godot_api]
impl ICamera2D for JuiceCamera {
    fn init(base: Base<Camera2D>) -> Self {
        Self { shake: 0.0, freeze_until_ms: 0, base }
    }

    fn process(&mut self, delta: f64) {
        // End the freeze using real time (game time is what we slowed down)
        if self.freeze_until_ms > 0 && Time::singleton().get_ticks_msec() >= self.freeze_until_ms {
            self.freeze_until_ms = 0;
            Engine::singleton().set_time_scale(1.0);
        }
        if self.shake > 0.1 {
            let s = self.shake;
            let offset = Vector2::new(randf_range(-1.0, 1.0) as f32, randf_range(-1.0, 1.0) as f32) * s;
            self.base_mut().set_offset(offset);
            self.shake *= (1.0 - 12.0 * delta as f32).max(0.0); // decays fast
        } else {
            self.shake = 0.0;
            self.base_mut().set_offset(Vector2::ZERO);
        }
    }
}

#[godot_api]
impl JuiceCamera {
    #[func]
    pub fn add_shake(&mut self, strength: f32) {
        self.shake = self.shake.max(strength);
    }

    #[func]
    pub fn hit_stop(&mut self, seconds: f32) {
        Engine::singleton().set_time_scale(0.05);
        self.freeze_until_ms = Time::singleton().get_ticks_msec() + (seconds * 1000.0) as u64;
    }
}
''',
    source="Common practice; Celeste's freeze frames in Player.cs (MIT).",
)

# ---------------------------------------------------------------------------------------------
pattern(
    name="Rest points / bonfires",
    keywords="checkpoint bonfire save point rest respawn souls dark souls elden ring grace hollow knight bench",
    feel="Relief and dread at once: reaching one feels like safety and progress, but resting brings enemies back, so every trip out is a risk you choose.",
    seen_in="Dark Souls (bonfires), Elden Ring (sites of grace), Hollow Knight (benches), Resident Evil (typewriters).",
    how="A rest point sets where you respawn, restores health and healing items, and (in Souls games) resets the world's enemies. The spacing between them is the real difficulty dial: the run from the last bonfire to the boss IS part of the challenge. Shortcuts that loop back to a rest point are the reward for exploring.",
    knobs="Distance between rest points. What resting restores. Whether resting respawns enemies. Whether dying costs something (Souls drops your currency where you died, so you can win it back).",
    base="Area2D", cls="RestPoint",
    code=r'''use godot::classes::{Area2D, IArea2D, Node2D};
use godot::prelude::*;

/// Touch it to rest: it remembers itself as the respawn point and tells the game to heal and reset.
#[derive(GodotClass)]
#[class(base = Area2D)]
pub struct RestPoint {
    base: Base<Area2D>,
}

#[godot_api]
impl IArea2D for RestPoint {
    fn init(base: Base<Area2D>) -> Self {
        Self { base }
    }

    fn ready(&mut self) {
        self.signals().body_entered().connect_self(Self::on_body_entered);
    }
}

#[godot_api]
impl RestPoint {
    /// Listen to this from your game: heal the player, refill items, respawn enemies.
    #[signal]
    pub fn rested(respawn_at: Vector2);

    fn on_body_entered(&mut self, body: Gd<Node2D>) {
        if body.is_in_group("player") {
            let here = self.base().get_global_position();
            self.signals().rested().emit(here);
        }
    }
}
''',
    source="Design described from the games.",
)

# ---------------------------------------------------------------------------------------------
pattern(
    name="Saving and loading progress",
    keywords="save load progress persist high score settings config file continue",
    feel="Players trust the game with their time. Losing progress is one of the fastest ways to lose a player.",
    seen_in="Every game longer than a few minutes.",
    how="Godot's ConfigFile reads and writes simple sections of key=value pairs to user://, which is the player's own save folder on any platform. Save at natural moments (rest points, level ends) and also when quitting.",
    knobs="When to save (autosave vs manual). How many slots. What to store (only what you can't recompute).",
    base="Node", cls="SaveGame",
    code=r'''use godot::classes::{ConfigFile, INode, Node};
use godot::global::Error;
use godot::prelude::*;

const SAVE_PATH: &str = "user://save.cfg";

#[derive(GodotClass)]
#[class(base = Node)]
pub struct SaveGame {
    base: Base<Node>,
}

#[godot_api]
impl INode for SaveGame {
    fn init(base: Base<Node>) -> Self {
        Self { base }
    }
}

#[godot_api]
impl SaveGame {
    #[func]
    pub fn save_progress(&self, level: i32, coins: i32) -> bool {
        let mut file = ConfigFile::new_gd();
        file.set_value("progress", "level", &level.to_variant());
        file.set_value("progress", "coins", &coins.to_variant());
        file.save(SAVE_PATH) == Error::OK
    }

    /// Returns 1 (the first level) when there's no save yet.
    #[func]
    pub fn load_level(&self) -> i32 {
        let mut file = ConfigFile::new_gd();
        if file.load(SAVE_PATH) != Error::OK {
            return 1;
        }
        file.get_value("progress", "level").try_to::<i32>().unwrap_or(1)
    }
}
''',
    source="Godot ConfigFile API.",
)

# ---------------------------------------------------------------------------------------------
pattern(
    name="Turns by time spent (speed-based turn order)",
    keywords="turn based roguelike turn order initiative speed time scheduler tactics actors energy",
    feel="Speed matters in a turn-based game: a fast rat gets two moves for your one, a slowed enemy falls behind, and players can reason about it.",
    seen_in="Shattered Pixel Dungeon, NetHack, Final Fantasy's ATB, many tactics games.",
    how="In Shattered Pixel Dungeon's Actor.java (GPL-3.0), every actor has a 'time'. Acting spends time (a normal move costs 1 TICK; a slow actor spends more, a hasted one less). The scheduler always lets the actor with the LOWEST time act next. There is no global 'round': speed differences fall out naturally.",
    knobs="Base action cost. Speed modifiers. Tie-breaking (SPD gives the player priority on equal time).",
    base="Node", cls="TurnClock",
    code=r'''use godot::classes::{INode, Node};
use godot::prelude::*;

/// Who acts next? Everyone has a clock; acting moves your clock forward by how long the action took.
#[derive(GodotClass)]
#[class(base = Node)]
pub struct TurnClock {
    actors: Vec<(String, f32)>,
    base: Base<Node>,
}

#[godot_api]
impl INode for TurnClock {
    fn init(base: Base<Node>) -> Self {
        Self { actors: Vec::new(), base }
    }
}

#[godot_api]
impl TurnClock {
    #[func]
    pub fn add_actor(&mut self, name: GString) {
        self.actors.push((name.to_string(), 0.0));
    }

    /// The actor whose clock is lowest goes next.
    #[func]
    pub fn next_actor(&self) -> GString {
        let next = self.actors.iter().min_by(|a, b| a.1.total_cmp(&b.1));
        next.map(|(n, _)| GString::from(n.as_str())).unwrap_or_default()
    }

    /// Call after an actor acts: a normal action costs 1.0, a slow one more, a fast one less.
    #[func]
    pub fn spend(&mut self, name: GString, time: f32) {
        let name = name.to_string();
        if let Some(actor) = self.actors.iter_mut().find(|(n, _)| *n == name) {
            actor.1 += time;
        }
    }
}
''',
    source="Shattered Pixel Dungeon actors/Actor.java (github.com/00-Evan/shattered-pixel-dungeon, GPL-3.0)",
)

# ------------------------------------------------------------------ design-only philosophy notes
pattern(
    name="Interconnected world with shortcuts (Souls-style level design)",
    keywords="level design shortcuts interconnected world metroidvania dark souls hollow knight one way door unlock loop exploration",
    feel="'Oh, it's THAT door!' Opening a shortcut back to somewhere familiar is a burst of relief and understanding: the world clicks together in your head.",
    seen_in="Dark Souls (Firelink Shrine, the Undead Parish elevator), Hollow Knight, Super Metroid, Resident Evil's mansion.",
    how="Areas loop back on themselves. Shortcuts are usually one-way: locked from the safe side, opened from the dangerous side after you've pushed through (a door that only opens from one side, a ladder you kick down, an elevator). This rewards pushing forward and shortens the run back to the rest point, so difficulty drops as mastery of the space grows. Landmarks visible from far away let players plan routes.",
    knobs="How far you push before a shortcut appears. How many loops lead back to the same hub. Whether the map is shown or left to memory.",
    source="Design described from the games.",
)
pattern(
    name="Emergent simulation and radiant worlds (Bethesda-style)",
    keywords="open world sandbox emergent simulation radiant ai npc schedules physics skyrim fallout oblivion immersive sim systems",
    feel="The world feels alive and goes on without you: NPCs have routines, systems collide in unscripted ways, and players tell their own stories ('a giant launched me into the sky').",
    seen_in="Skyrim, Oblivion (Radiant AI), Fallout, Breath of the Wild (chemistry engine), immersive sims like Deus Ex and Prey.",
    how="Instead of scripting every event, give objects and characters simple rules (NPCs follow daily schedules, fire spreads to grass, items have physics) and let them interact. Quests can be generated from templates ('clear a random cave', 'deliver to a random NPC'). The design work is in choosing rules that combine interestingly and giving players tools that touch many systems. The trade-off: less control over pacing and more bugs, which players often forgive (or love) when the freedom is real.",
    knobs="How many systems interact. How much is scripted vs emergent. How much the world reacts to the player's reputation and choices.",
    source="Design described from the games.",
)
pattern(
    name="Easy to learn, hard to master",
    keywords="depth simple rules mastery skill ceiling tetris chess elegant design accessible competitive",
    feel="Anyone can start playing in seconds, but experts keep finding new depth for years.",
    seen_in="Tetris, Pac-Man, Rocket League, Super Smash Bros., chess.",
    how="A tiny set of rules, explained by playing, with consequences that combine deeply. In Tetris, the rules fit in a sentence, but speed, stacking strategy and T-spins create an enormous skill range. Design moves: few inputs, consistent physics or rules with no exceptions, and a difficulty that ramps (Tetris gets faster) so the game meets every player at their level.",
    knobs="Number of verbs/inputs. How fast difficulty ramps. Whether advanced techniques are taught or discovered.",
    source="Design described from the games.",
)
pattern(
    name="Death as progress (roguelite loop)",
    keywords="roguelike roguelite permadeath run based meta progression hades dead cells binding of isaac slay the spire replayability",
    feel="Dying stings but never wastes your time: every run teaches you something or unlocks something, so 'one more run' is irresistible.",
    seen_in="Hades, Dead Cells, Slay the Spire, The Binding of Isaac, Rogue Legacy.",
    how="Short runs with randomized layouts and rewards, so every attempt is different. Permanent unlocks or story progress carried between runs (Hades advances its story when you die). Builds come from combining random upgrades, so players learn synergies. Hades' key insight: making death a narrative event turns failure into content.",
    knobs="Run length. How much carries over (none = roguelike, some = roguelite). How random vs. chosen the upgrades are.",
    source="Design described from the games.",
)
pattern(
    name="Cozy games: low pressure, high comfort",
    keywords="cozy wholesome relaxing farming life sim stardew animal crossing no fail calm daily routine",
    feel="Safe, warm and unhurried. Players come back to relax, not to be challenged; small daily goals and gentle progress feel rewarding.",
    seen_in="Stardew Valley, Animal Crossing, A Short Hike, Unpacking.",
    how="No harsh failure states (at worst you lose a day or some time). Clear, small goals with a daily rhythm. Collections and customization that reflect the player. Characters who remember you. Soft colors, gentle sounds, and the freedom to ignore any goal. Stardew grew from its developer's love of Harvest Moon, rebuilt to fix what frustrated him.",
    knobs="How much time pressure (energy, seasons). How many systems to juggle. How much the world responds to the player.",
    source="Design described from the games.",
)
pattern(
    name="Teaching without tutorials (level 1-1 design)",
    keywords="tutorial onboarding teach player level design first level mario 1-1 show dont tell learning curve",
    feel="Players feel clever: they figure things out themselves instead of reading instructions.",
    seen_in="Super Mario Bros. World 1-1, Portal's test chambers, Celeste's early screens, Hollow Knight.",
    how="Introduce one idea at a time in a safe space, then test it with a small twist, then combine it with something learned earlier. In World 1-1 the first Goomba walks toward you on open ground where jumping is the obvious answer; the first mushroom bounces into a pipe so you can't miss it. Portal introduces each mechanic alone in a chamber before mixing them.",
    knobs="How safe the first encounter is. How quickly ideas get combined. Whether there's any text at all.",
    source="Design described from the games.",
)


if __name__ == "__main__":
    print(len(PATTERNS), "patterns,", sum(1 for p in PATTERNS if p.get("code")), "with code")
