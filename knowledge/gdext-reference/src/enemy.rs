use godot::classes::{CharacterBody2D, ICharacterBody2D};
use godot::global::randf_range;
use godot::prelude::*;

use crate::player::Player;

/// An enemy that wanders, and chases the player when it gets close.
#[derive(GodotClass)]
#[class(base = CharacterBody2D)]
pub struct Enemy {
    #[export]
    speed: f32,
    #[export]
    chase_distance: f32,
    /// The node path to the player, set in the Inspector.
    #[export]
    target: Option<Gd<Player>>,
    wander: Vector2,
    base: Base<CharacterBody2D>,
}

#[godot_api]
impl ICharacterBody2D for Enemy {
    fn init(base: Base<CharacterBody2D>) -> Self {
        Self { speed: 120.0, chase_distance: 250.0, target: None, wander: Vector2::ZERO, base }
    }

    fn ready(&mut self) {
        let angle = randf_range(0.0, std::f64::consts::TAU) as f32;
        self.wander = Vector2::from_angle(angle);
    }

    fn physics_process(&mut self, _delta: f64) {
        let my_pos = self.base().get_global_position();
        let mut direction = self.wander;
        if let Some(player) = &self.target {
            let player_pos = player.get_global_position();
            if my_pos.distance_to(player_pos) < self.chase_distance {
                direction = (player_pos - my_pos).normalized();
            }
        }
        let velocity = direction * self.speed;
        self.base_mut().set_velocity(velocity);
        self.base_mut().move_and_slide();

        // Bounce off walls.
        if self.base().is_on_wall() {
            self.wander = -self.wander;
        }
    }
}
