use godot::classes::{Area2D, IArea2D, Node2D};
use godot::prelude::*;

use crate::player::Player;

/// A coin that bobs up and down and disappears when the player touches it.
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
        // Typed signal: call our method whenever a body enters the area.
        self.signals().body_entered().connect_self(Self::on_body_entered);
    }

    fn process(&mut self, delta: f64) {
        self.time += delta;
        let mut pos = self.base().get_position();
        pos.y = self.start_y + (self.time * 4.0).sin() as f32 * 6.0;
        self.base_mut().set_position(pos);
    }
}

#[godot_api]
impl Coin {
    #[signal]
    pub fn collected(value: i32);

    fn on_body_entered(&mut self, body: Gd<Node2D>) {
        // Only the player can collect coins.
        if body.try_cast::<Player>().is_ok() {
            let value = self.value;
            self.signals().collected().emit(value);
            self.base_mut().queue_free();
        }
    }
}
