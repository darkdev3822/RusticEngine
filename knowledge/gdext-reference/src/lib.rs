//! Verified godot-rust 0.5 / Godot 4.7 patterns. Every snippet here compiles; it is the
//! ground truth for Ember's system prompt and for the training data.
use godot::prelude::*;

mod coin;
mod enemy;
mod hud;
mod main_game;
mod player;

struct Reference;

#[gdextension]
unsafe impl ExtensionLibrary for Reference {}
