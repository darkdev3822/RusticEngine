//! Game design knowledge: why beloved games feel the way they do (training/design_patterns.py,
//! verified code), what players love about specific games (Wikipedia, CC BY-SA 4.0), and how
//! modeling techniques work (Blender Manual by the Blender Documentation Team, CC BY-SA 4.0).
//! Ember uses it to understand what a creator means by "like Dark Souls", never to copy a game.
use std::sync::OnceLock;

use serde_json::Value;

use crate::examples::words;

const DATA: &str = include_str!("../examples/design.jsonl");

fn entries() -> &'static Vec<(Value, Vec<String>)> {
    static E: OnceLock<Vec<(Value, Vec<String>)>> = OnceLock::new();
    E.get_or_init(|| {
        DATA.lines().filter_map(|l| serde_json::from_str::<Value>(l).ok()).map(|v| {
            let text = if v["kind"] == "pattern" {
                format!("{} {} {}", v["name"], v["keywords"], v["seen_in"])
            } else if v["kind"] == "manual" {
                format!("{} {}", v["name"], v["keywords"])
            } else {
                format!("{} {}", v["name"], v["name"])
            };
            let w = words(&text);
            (v, w)
        }).collect()
    })
}

fn section(v: &Value, prefix: &str, max: usize) -> Option<String> {
    let secs = v["sections"].as_object()?;
    let (k, t) = secs.iter().find(|(k, _)| k.to_lowercase().starts_with(prefix))?;
    let t = t.as_str()?;
    let cut: String = t.chars().take(max).collect();
    Some(format!("{k}: {cut}{}", if t.len() > cut.len() { "..." } else { "" }))
}

const STOP: &[&str] = &["the", "a", "an", "of", "like", "game", "games", "feel", "feels", "style", "and", "to", "in", "my", "i", "want", "it"];

pub fn search(query: &str) -> String {
    let q: Vec<String> = words(query).into_iter().filter(|w| !STOP.contains(&w.as_str())).collect();
    if q.is_empty() { return "Give a game name or a design idea, e.g. 'Dark Souls', 'coyote time', 'cozy'.".into(); }
    let mut scored: Vec<(f64, &Value)> = entries().iter().filter_map(|(v, w)| {
        let hits = q.iter().filter(|t| w.binary_search(t).is_ok()).count();
        if hits == 0 { return None; }
        let mut s = hits as f64 / q.len() as f64;
        if v["kind"] == "game" && hits == q.len() { s += 0.5; } // an exact game name wins
        Some((s, v))
    }).collect();
    scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap());
    if scored.is_empty() { return format!("Nothing about {query} in the design library. Ask the creator what they love about it."); }
    let mut out = String::new();
    for (i, (_, v)) in scored.into_iter().take(2).enumerate() {
        if v["kind"] == "pattern" {
            let s = |k: &str| v[k].as_str().unwrap_or("").to_string();
            out += &format!("## {}\nFeel: {}\nSeen in: {}\nHow it works: {}\nKnobs: {}\n", s("name"), s("feel"), s("seen_in"), s("how"), s("knobs"));
            if i == 0 && !s("code").is_empty() {
                out += &format!("Verified godot-rust code:\n```rust\n{}\n```\n", s("code"));
            }
            out += &format!("(Source: {})\n\n", s("source"));
        } else if v["kind"] == "manual" {
            let s = |k: &str| v[k].as_str().unwrap_or("").to_string();
            let text: String = s("text").chars().take(if i == 0 { 1600 } else { 600 }).collect();
            out += &format!("## {}\n{text}\n(Source: {})\n\n", s("name"), s("source"));
        } else {
            out += &format!("## {} (Wikipedia, CC BY-SA)\n", v["name"].as_str().unwrap_or(""));
            for (p, n) in [("intro", 500), ("gameplay", 1800), ("development", 700), ("design", 700), ("reception", 500)] {
                if let Some(t) = section(v, p, n) { out += &format!("{t}\n"); }
            }
            out += "\n";
        }
    }
    if out.contains("(Blender)") {
        return out + "The Studio's 3D modeler has: G move, R rotate, S scale (X/Y/Z to lock an axis, type a number), E extrude, I inset, \
                      D subdivide, F fill, M merge, Flip, Delete, Mirror X, P paint. Explain the idea in Studio terms, step by step, and say \
                      plainly if the Studio can't do something yet (then Blender, which is free, can).";
    }
    out + "Use this to understand what the creator means, then ASK which part they want. Their game should be theirs, not a copy."
}
