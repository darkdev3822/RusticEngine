//! Game Paths: step-by-step courses for making a kind of game (open-world RPG, souls-like,
//! platformer...). Each step pairs a design question with a buildable milestone. The creator's
//! place in a path is kept in design/path.md.
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
];

fn title(text: &str) -> &str {
    text.lines().next().unwrap_or("").trim_start_matches('#').trim()
}

fn steps(text: &str) -> Vec<&str> {
    text.split("\n## ").skip(1).collect()
}

pub fn list() -> String {
    let mut out = String::from("Game Paths (step-by-step courses; each step is a design question plus something to build):\n");
    for (id, text) in PATHS {
        out += &format!("- {id}: {} ({} steps)\n", title(text), steps(text).len());
    }
    out + "Ask which one fits the game they want to make (or which is closest), then open it."
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
            let note = format!("# Game Path\nPath: {id} ({})\nCurrent step: {n} of {}: {}\n", title(text), all.len(), s.lines().next().unwrap_or(""));
            let _ = fs::write(root.join("design/path.md"), note);
            let next = if n < all.len() { format!("\n(Next is step {}.)", n + 1) } else { "\n(This is the last step.)".into() };
            Ok((format!("## {s}{next}\n\nAdapt this step to THEIR game (design/vision.md, journal). Start with the design question: ask it, listen, then build together."), true))
        }
    }
}
