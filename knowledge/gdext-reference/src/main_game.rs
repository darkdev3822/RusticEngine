use godot::classes::{INode2D, Node2D, PackedScene, Timer};
use godot::global::randf_range;
use godot::prelude::*;

use crate::coin::Coin;
use crate::hud::Hud;
use crate::player::Player;

/// The main scene: spawns coins on a timer and wires everything together.
#[derive(GodotClass)]
#[class(base = Node2D)]
pub struct MainGame {
    /// Drag coin.tscn here in the Inspector.
    #[export]
    coin_scene: OnEditor<Gd<PackedScene>>,
    base: Base<Node2D>,
}

#[godot_api]
impl INode2D for MainGame {
    fn init(base: Base<Node2D>) -> Self {
        Self { coin_scene: OnEditor::default(), base }
    }

    fn ready(&mut self) {
        // A timer created from code: spawn a coin every 2 seconds.
        let mut timer = Timer::new_alloc();
        timer.set_wait_time(2.0);
        timer.set_autostart(true);
        timer.signals().timeout().connect_other(&self.to_gd(), Self::spawn_coin);
        self.base_mut().add_child(&timer);

        let player = self.base().get_node_as::<Player>("Player");
        player.signals().died().connect_other(&self.to_gd(), Self::on_player_died);
    }
}

#[godot_api]
impl MainGame {
    fn spawn_coin(&mut self) {
        let mut coin = self.coin_scene.instantiate_as::<Coin>();
        let x = randf_range(50.0, 1100.0) as f32;
        coin.set_position(Vector2::new(x, 100.0));
        let hud = self.base().get_node_as::<Hud>("Hud");
        coin.signals().collected().connect_other(&hud, Hud::add_score);
        self.base_mut().add_child(&coin);
    }

    fn on_player_died(&mut self) {
        godot_print!("Game over!");
        self.base().get_tree().reload_current_scene();
    }

    /// Loading a scene by path instead of exporting it.
    #[allow(dead_code)]
    fn load_example(&mut self) {
        let scene = load::<PackedScene>("res://coin.tscn");
        let node = scene.instantiate_as::<Node2D>();
        self.base_mut().add_child(&node);
    }
}
