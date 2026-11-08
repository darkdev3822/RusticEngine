use godot::classes::{CanvasLayer, ICanvasLayer, Label};
use godot::prelude::*;

/// On-screen score. Expects a child Label named "ScoreLabel".
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
