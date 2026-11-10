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
        let tool: &'static str = if tool == "sound" { "sound" } else { "model" };
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

#[cfg(test)]
mod tests {
    use super::lookup;
    fn first(q: &str, tool: &str) -> String { lookup(q, tool).first().cloned().unwrap_or_default() }
    #[test]
    fn finds_the_right_recipe() {
        assert!(first("how do I give this fence post a pointy top?", "model").contains("Pointy top"));
        assert!(first("can I tilt the whole rock a bit?", "model").contains("Tilt"));
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
