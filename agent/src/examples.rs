//! A small library of real, working godot-rust 0.5 code (from the godot-rust book, demo projects
//! and gdext's own tests; MPL-2.0, see examples/NOTICE). Ember searches it before writing
//! unfamiliar API calls, so it copies real usage instead of guessing.
use std::collections::HashMap;
use std::sync::OnceLock;

use serde_json::Value;

const DATA: &str = include_str!("../examples/examples.jsonl");

struct Example {
    src: String,
    title: String,
    code: String,
    terms: Vec<String>,
}

fn words(s: &str) -> Vec<String> {
    let mut out = vec![];
    for w in s.split(|c: char| !c.is_alphanumeric() && c != '_') {
        if w.len() < 2 { continue; }
        let lower = w.to_lowercase();
        // Also index the parts of snake_case and CamelCase names.
        let mut parts: Vec<String> = lower.split('_').filter(|p| p.len() > 1).map(String::from).collect();
        let mut cur = String::new();
        for ch in w.chars() {
            if ch.is_uppercase() && !cur.is_empty() { parts.push(cur.to_lowercase()); cur.clear(); }
            if ch != '_' { cur.push(ch); }
        }
        if cur.len() > 1 { parts.push(cur.to_lowercase()); }
        out.push(lower);
        out.extend(parts);
    }
    out.sort();
    out.dedup();
    out
}

fn library() -> &'static (Vec<Example>, HashMap<String, f64>) {
    static LIB: OnceLock<(Vec<Example>, HashMap<String, f64>)> = OnceLock::new();
    LIB.get_or_init(|| {
        let mut ex = vec![];
        let mut df: HashMap<String, usize> = HashMap::new();
        for line in DATA.lines() {
            let Ok(v) = serde_json::from_str::<Value>(line) else { continue };
            let s = |k: &str| v[k].as_str().unwrap_or("").to_string();
            let terms = words(&format!("{} {}", s("title"), s("code")));
            for t in &terms { *df.entry(t.clone()).or_default() += 1; }
            ex.push(Example { src: s("src"), title: s("title"), code: s("code"), terms });
        }
        let n = ex.len() as f64;
        let idf = df.into_iter().map(|(t, d)| (t, (n / d as f64).ln())).collect();
        (ex, idf)
    })
}

const STOP: &[&str] = &["the", "how", "to", "a", "an", "of", "in", "for", "and", "with", "use", "using", "do", "make", "is", "it", "my", "on"];

pub fn search(query: &str, max: usize) -> String {
    let (ex, idf) = library();
    let q: Vec<String> = words(query).into_iter().filter(|w| !STOP.contains(&w.as_str())).collect();
    if q.is_empty() { return "Give some words to search for, e.g. 'timer timeout signal' or 'get_overlapping_bodies'.".into(); }
    let mut scored: Vec<(f64, &Example)> = ex.iter().filter_map(|e| {
        let mut s = 0.0;
        let mut hits = 0;
        for t in &q {
            if e.terms.binary_search(t).is_ok() { s += idf.get(t).copied().unwrap_or(1.0); hits += 1; }
        }
        if hits == 0 { return None; }
        // Prefer examples that match more of the query, are short, and come from teaching material.
        s *= hits as f64 / q.len() as f64;
        if !e.src.contains("itest") { s *= 1.6; }
        if e.code.contains("assert") { s *= 0.8; }
        s /= 1.0 + (e.code.lines().count() as f64 / 40.0);
        Some((s, e))
    }).collect();
    scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap());
    if scored.is_empty() { return format!("No examples mention {query}. Try class_info instead."); }
    let mut out = String::new();
    for (_, e) in scored.into_iter().take(max) {
        let code: Vec<&str> = e.code.lines().take(30).collect();
        out += &format!("--- {} ({})\n{}\n\n", e.title, e.src, code.join("\n"));
    }
    out + "These are real, compiling godot-rust 0.5 snippets (tests use helper functions you don't have: copy the API usage, not the test scaffolding)."
}
