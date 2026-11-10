//! Verified Studio how-to recipes (studio/recipes.md), matched to the creator's question.
//! The model is good at explaining but invents keys and menus, so the agent hands it the real steps.

const RECIPES: &str = include_str!("../studio/recipes.md");

struct Recipe {
    title: &'static str,
    tool: &'static str,
    words: Vec<String>,
    body: String,
}

fn words(s: &str) -> Vec<String> {
    const STOP: &[&str] = &["the", "and", "how", "can", "make", "this", "that", "with", "for", "you", "your", "want", "into",
        "from", "what", "does", "look", "looks", "sound", "sounds", "more", "less", "bit", "way", "too", "very", "get", "its", "it's", "are", "is", "my"];
    s.to_lowercase().split(|c: char| !c.is_alphanumeric() && c != '-').filter(|w| w.len() >= 3 && !STOP.contains(w)).map(String::from).collect()
}

fn recipes() -> Vec<Recipe> {
    let mut out = vec![];
    for block in RECIPES.split("\n## ").skip(1) {
        let mut lines = block.lines();
        let title = lines.next().unwrap_or("").trim();
        let (mut tool, mut keys, mut body) = ("", String::new(), vec![]);
        for l in lines {
            if let Some(t) = l.strip_prefix("tool:") { tool = t.trim(); }
            else if let Some(k) = l.strip_prefix("keys:") { keys = k.to_string(); }
            else if !l.trim().is_empty() { body.push(l.trim_end()); }
        }
        let tool: &'static str = match tool { "sound" => "sound", "pixel" => "pixel", _ => "model" };
        out.push(Recipe { title, tool, words: words(&format!("{title} {keys}")), body: body.join("\n") });
    }
    out
}

fn matches(q: &str, k: &str) -> bool {
    q == k || (q.len() >= 4 && k.len() >= 4 && (q.starts_with(k) || k.starts_with(q)) && q[..4] == k[..4])
}

/// The best 1-2 recipes for a question about the model ("model") or sound ("sound") that's open.
pub fn lookup(question: &str, tool: &str) -> Vec<String> {
    let q = words(question);
    let mut scored: Vec<(usize, Recipe)> = recipes().into_iter().filter(|r| r.tool == tool).map(|r| {
        let s = q.iter().filter(|w| r.words.iter().any(|k| matches(w, k))).count();
        (s, r)
    }).filter(|(s, _)| *s > 0).collect();
    scored.sort_by(|a, b| b.0.cmp(&a.0));
    let top = scored.first().map(|x| x.0).unwrap_or(0);
    scored.into_iter().take(2).filter(|(s, _)| *s * 3 >= top * 2).map(|(_, r)| format!("### {}\n{}", r.title, r.body)).collect()
}

/// The Studio's own names for tools, buttons and settings (from the reference cards). A reply that
/// teaches a recipe should name at least one of the ones the recipe uses.
const UI_TERMS: &[&str] = &[
    // Pixel Art
    "pencil", "eraser", "fill", "line (l)", "rectangle", "ellipse", "pick color", "mirror", "onion skin", "tile view", "grid", "canvas menu",
    "flip left/right", "flip upside down", "shift by half", "replace left color", "copy", "play", "fps", "color box", "+ color", "swatch",
    "starter 16", "forest", "dungeon", "grayscale", "four greens", "hframes", "nearest", "texture filter", "sprite2d", "flip h", "1:1", "2:1", "shift",
    // 3D modeler and Sound Effects maker (their probes pass already; listed so grounded() is meaningful for them too)
    "extrude", "inset", "merge", "subdivide", "scale", "rotate", "paint", "mirror x", "low-pass", "high-pass", "decay", "attack", "sustain",
    "punch", "start pitch", "slide", "pitch jump", "vibrato", "volume", "mutate", "stop below", "phaser", "square duty", "wave",
];

/// Does the reply name any Studio tool or setting that this recipe uses?
pub fn grounded(reply: &str, recipe: &str) -> bool {
    let (r, body) = (reply.to_lowercase(), recipe.to_lowercase());
    let used: Vec<&&str> = UI_TERMS.iter().filter(|t| body.contains(**t)).collect();
    used.is_empty() || used.iter().any(|t| r.contains(**t))
}

#[cfg(test)]
mod tests {
    use super::lookup;
    fn first(q: &str, tool: &str) -> String { lookup(q, tool).first().cloned().unwrap_or_default() }
    #[test]
    fn finds_the_right_recipe() {
        assert!(first("how do I give this fence post a pointy top?", "model").contains("Pointy top"));
        assert!(first("can I tilt the whole rock a bit?", "model").contains("Tilt"));
        assert!(first("how do I make my grass tile repeat without seams?", "pixel").contains("Seamless"));
        assert!(first("my character looks blurry in the game", "pixel").contains("Use the sprite"));
        assert!(first("how do I make him walk?", "pixel").contains("Animation"));
        assert!(first("the lines look jagged", "pixel").contains("jaggies"));
        assert!(first("how do I add shadows so it looks less flat", "pixel").contains("Shading"));
        assert!(lookup("how do I extrude a face", "pixel").iter().all(|r| !r.contains("Extrude")));
        assert!(first("how can I make the coin spin?", "pixel").contains("Animation"));
        assert!(first("I want a blue version of this slime too", "pixel").contains("palette"));
        let blurry = first("the coin looks blurry when i run the game", "pixel");
        assert!(!super::grounded("It looks blurry because the game draws it as a normal image.", &blurry));
        assert!(super::grounded("Set Default Texture Filter to Nearest in Project Settings.", &blurry));
        assert!(first("the shoulders look too wide, how do I fix it", "model").contains("Narrower"));
        assert!(first("I want a crossguard on my sword, how?", "model").contains("crossguard"));
        assert!(first("how do I make the walls a different color than the roof", "model").contains("Paint"));
        assert!(first("can I make the leaves have two layers, like a pine tree?", "model").contains("Layers"));
        assert!(first("my sound is way too quiet", "sound").contains("Louder"));
        assert!(first("how do I make this footstep sound softer, less harsh?", "sound").contains("Softer"));
        assert!(first("I want an arrow slit in my tower wall", "model").contains("Window"));
        assert!(first("my barrel is way too tall", "model").contains("size"), "{}", first("my barrel is way too tall", "model"));
        assert!(first("this laser goes on forever", "sound").contains("Shorter") || first("this laser goes on forever", "sound").contains("Longer"));
        assert!(first("make it sound like the explosion is underwater", "sound").contains("Distant"), "{}", first("make it sound like the explosion is underwater", "sound"));
        assert!(lookup("hello there", "model").is_empty());
    }
}
