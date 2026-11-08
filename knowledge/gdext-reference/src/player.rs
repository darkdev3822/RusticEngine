use godot::classes::{CharacterBody2D, ICharacterBody2D, Input};
use godot::global::Key;
use godot::prelude::*;

/// A platformer character: arrow keys to run, Space to jump.
#[derive(GodotClass)]
#[class(base = CharacterBody2D)]
pub struct Player {
    #[export]
    speed: f32,
    #[export]
    jump_velocity: f32,
    #[export]
    gravity: f32,
    health: i32,
    base: Base<CharacterBody2D>,
}

#[godot_api]
impl ICharacterBody2D for Player {
    fn init(base: Base<CharacterBody2D>) -> Self {
        Self { speed: 250.0, jump_velocity: -420.0, gravity: 980.0, health: 3, base }
    }

    fn physics_process(&mut self, delta: f64) {
        let input = Input::singleton();
        let mut velocity = self.base().get_velocity();

        if !self.base().is_on_floor() {
            velocity.y += self.gravity * delta as f32;
        }
        if input.is_key_pressed(Key::SPACE) && self.base().is_on_floor() {
            velocity.y = self.jump_velocity;
        }
        let direction = input.get_axis("ui_left", "ui_right");
        velocity.x = direction * self.speed;

        self.base_mut().set_velocity(velocity);
        self.base_mut().move_and_slide();
    }
}

#[godot_api]
impl Player {
    /// Emitted when health changes, so the HUD can update.
    #[signal]
    pub fn health_changed(new_health: i32);

    #[signal]
    pub fn died();

    /// `#[func]` makes a method callable from the editor, signals and other languages.
    #[func]
    pub fn take_damage(&mut self, amount: i32) {
        self.health -= amount;
        let health = self.health;
        self.signals().health_changed().emit(health);
        if self.health <= 0 {
            self.signals().died().emit();
        }
    }

    pub fn health(&self) -> i32 {
        self.health
    }
}
