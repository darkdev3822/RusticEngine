//! Game Paths: step-by-step courses for making a kind of game (open-world RPG, souls-like,
//! platformer...). Each step pairs a design question with a buildable milestone. The creator's
//! place in a path is kept in design/path.md (Art Paths: design/art_path.md).
use std::fs;
use std::path::Path;

const PATHS: &[(&str, &str)] = &[
    ("open-world-rpg", include_str!("../paths/open-world-rpg.md")),
    ("souls-like", include_str!("../paths/souls-like.md")),
    ("platformer", include_str!("../paths/platformer.md")),
    ("survival", include_str!("../paths/survival.md")),
    ("roguelike", include_str!("../paths/roguelike.md")),
    ("cozy-farming", include_str!("../paths/cozy-farming.md")),
    ("metroidvania", include_str!("../paths/metroidvania.md")),
    ("tower-defense", include_str!("../paths/tower-defense.md")),
    ("turn-based-rpg", include_str!("../paths/turn-based-rpg.md")),
    ("art-low-poly-prop", include_str!("../paths/art-low-poly-prop.md")),
    ("art-low-poly-character", include_str!("../paths/art-low-poly-character.md")),
    ("art-low-poly-environment", include_str!("../paths/art-low-poly-environment.md")),
    ("art-sound-effects", include_str!("../paths/art-sound-effects.md")),
];

fn title(text: &str) -> &str {
    text.lines().next().unwrap_or("").trim_start_matches('#').trim()
}

fn steps(text: &str) -> Vec<&str> {
    text.split("\n## ").skip(1).collect()
}

pub fn list() -> String {
    let mut out = String::from("Game Paths (step-by-step courses for making a kind of game; each step is a design question plus something to build):\n");
    for (id, text) in PATHS.iter().filter(|(id, _)| !id.starts_with("art-")) {
        out += &format!("- {id}: {} ({} steps)\n", title(text), steps(text).len());
    }
    out += "Art Paths (making assets yourself in the Studio tab):\n";
    for (id, text) in PATHS.iter().filter(|(id, _)| id.starts_with("art-")) {
        out += &format!("- {id}: {} ({} steps)\n", title(text).trim_start_matches("Art Path: "), steps(text).len());
    }
    out + "Ask which one fits what they want to make (or which is closest), then open it."
}

/// Open a path (overview + step list) or one step. Records progress in design/path.md.
pub fn open(root: &Path, id: &str, step: Option<usize>) -> Result<(String, bool), String> {
    let id = id.trim().to_lowercase().replace(' ', "-");
    let Some((id, text)) = PATHS.iter().find(|(p, _)| *p == id || p.contains(id.as_str())) else {
        return Err(format!("No path called {id}.\n{}", list()));
    };
    let all = steps(text);
    match step {
        None | Some(0) => {
            let intro: &str = text.split("\n## ").next().unwrap_or("");
            let list: Vec<String> = all.iter().map(|s| format!("- {}", s.lines().next().unwrap_or(""))).collect();
            Ok((format!("{intro}\n\nSteps:\n{}\n\nStart with step 1 together.", list.join("\n")), false))
        }
        Some(n) => {
            let s = all.get(n - 1).ok_or(format!("{} has {} steps.", title(text), all.len()))?;
            let _ = fs::create_dir_all(root.join("design"));
            // Game and Art Paths are tracked separately: someone can be learning both at once.
            let (heading, file) = if id.starts_with("art-") { ("# Art Path", "design/art_path.md") } else { ("# Game Path", "design/path.md") };
            let note = format!("{heading}\nPath: {id} ({})\nCurrent step: {n} of {}: {}\n", title(text), all.len(), s.lines().next().unwrap_or(""));
            let _ = fs::write(root.join(file), note);
            let next = if n < all.len() { format!("\n(Next is step {}.)", n + 1) } else { "\n(This is the last step.)".into() };
            Ok((format!("## {s}{next}\n\nAdapt this step to THEIR game (design/vision.md, journal). Start with the design question: ask it, listen, then build together."), true))
        }
    }
}
