//! Ember's Blender library (training/build_blender_kb.py -> examples/blender.jsonl): the Blender Manual
//! (Blender Documentation Team, CC BY-SA 4.0), concept articles from Wikipedia (CC BY-SA 4.0), Blender 5.2's
//! default keymap, free CC0 asset catalogues (Poly Haven, ambientCG) and free Blender extensions.
//! Every answer also carries the exact keyboard shortcuts that match, so Ember can drill them.
use std::collections::{HashMap, HashSet};
use std::sync::OnceLock;

use serde_json::Value;

use crate::examples::words;

const DATA: &str = include_str!("../examples/blender.jsonl");
const KEYS: &str = include_str!("../examples/blender_keys.json");

struct Entry { v: Value, name: HashSet<String>, kw: HashSet<String>, text: HashSet<String> }
struct Index { entries: Vec<Entry>, idf: HashMap<String, f64> }

const STOP: &[&str] = &["the", "a", "an", "of", "in", "to", "and", "or", "how", "do", "does", "is", "it", "my", "for", "with", "on", "what",
    "why", "can", "make", "use", "using", "blender", "i", "you", "way", "best", "good", "get", "into", "from", "this", "that", "be",
    "just", "those", "these", "have", "want", "need", "some", "them", "only", "should", "would", "could", "like", "thing", "things", "me", "am", "are"];

/// Beginners describe what they want, not Blender's word for it ("round off these edges" = Bevel).
/// Each phrase found in the question is swapped for the Blender terms; the first terms also pick the shortcuts.
const PLAIN: &[(&[&str], &str)] = &[
    (&["apply scale", "scale not applied", "uneven bevel", "bevel is uneven", "bevel looks stretched", "looks uneven", "uneven", "squashed bevel", "apply the scale", "apply transform"], "apply scale transform|menu apply"),
    (&["round off", "round the edge", "round edge", "rounded edge", "rounded corner", "round corner", "chamfer", "soften the edge", "smooth the edge", "smooth edge", "sharp edge", "bevel"], "bevel"),
    (&["add a loop", "more loops", "edge loop", "add an edge", "more edges", "split the face", "cut a loop", "loop cut"], "loop cut"),
    (&["pull out", "push out", "pull the face", "extend the face", "pull a face", "extrude"], "extrude"),
    (&["thicker", "thickness", "give it depth", "paper thin", "solidify"], "solidify modifier|solidify"),
    (&["fill the hole", "fill a hole", "close the hole", "close a hole", "hole in my", "cap the"], "fill face"),
    (&["weld", "merge", "join vertices", "join the vertices", "combine vertices", "collapse", "double vertices", "duplicate vertices"], "merge"),
    (&["symmetr", "mirror", "both sides", "other side", "other half"], "mirror modifier|mirror"),
    (&["faceted", "blocky", "looks low poly", "shade smooth", "smooth shading", "flat shading", "shading looks"], "shade smooth object|shade smooth"),
    (&["smoother", "rounder", "more detail", "subdivi"], "subdivision surface modifier|subdivision"),
    (&["inset", "face inside", "smaller face", "border inside"], "inset"),
    (&["cut a hole", "hole through", "boolean", "subtract", "carve"], "boolean modifier|boolean"),
    (&["unwrap", "texture is stretched", "texture stretch", "stretched texture", "uv map", "uvs"], "uv unwrap seam|uv mapping"),
    (&["origin", "pivot"], "set origin|origin"),
    (&["snap"], "snap"),
    (&["separate", "split into", "detach", "own object"], "separate"),
    (&["join object", "join the object", "combine object", "into one object"], "join"),
    (&["soft select", "proportional", "falloff"], "proportional editing|proportional"),
    (&["knife", "cut a line", "draw a cut", "cut across"], "knife"),
    (&["lathe", "revolve", "spin"], "spin tool|spin"),
    (&["in a row", "repeat", "array", "copies"], "array modifier|array"),
    (&["duplicate", "copy of"], "duplicate"),
    (&["inside out", "flip normal", "black face", "dark patch", "faces look dark", "normals"], "recalculate normals outside|recalculate"),
    (&["fewer polygon", "less polygon", "reduce polygon", "too many polygon", "too many faces", "reduce faces", "lower poly", "decimate", "polycount"], "decimate modifier|decimate"),
    (&["glow", "light up", "emissive", "emission"], "emission"),
    (&["see through", "see-through", "transparent", "glass"], "transparent transmission"),
    (&["isolate", "local view", "focus on", "only see"], "local view"),
];

/// Swap plain phrases for Blender terms. Returns (query for searching, Blender terms found).
fn translate(query: &str) -> (String, Vec<&'static str>) {
    let mut q = query.to_lowercase();
    let mut found = vec![];
    for (phrases, term) in PLAIN {
        for p in phrases.iter() {
            if let Some(i) = q.find(p) {
                // remove the whole word(s) the phrase starts in ("symmetr" takes "symmetrical")
                let end = q[i + p.len()..].find(|c: char| !c.is_alphanumeric()).map_or(q.len(), |e| i + p.len() + e);
                q.replace_range(i..end, " ");
                if !found.contains(term) { found.push(*term); }
                break;
            }
        }
    }
    let search: Vec<&str> = found.iter().map(|t| t.split('|').next().unwrap_or(t)).collect();
    (format!("{} {q}", search.join(" ")), found)
}

/// Light stemming so bake/baking/baked, map/maps/mapping meet: strip -ing/-ed/-es/-s, a doubled end consonant, a final e.
fn stem(w: &str) -> String {
    let mut w = w.to_string();
    for suf in ["ing", "ed", "es", "s"] {
        if w.len() > suf.len() + 2 && w.ends_with(suf) && !w.ends_with("ss") { w.truncate(w.len() - suf.len()); break; }
    }
    let b = w.as_bytes();
    if b.len() > 3 && b[b.len() - 1] == b[b.len() - 2] && !b"aeiouls".contains(&b[b.len() - 1]) { w.pop(); }
    if w.len() > 3 && w.ends_with('e') { w.pop(); }
    w
}

fn terms(s: &str) -> Vec<String> { words(s).into_iter().map(|w| stem(&w)).collect() }
fn set(s: &str) -> HashSet<String> { terms(s).into_iter().collect() }

fn index() -> &'static Index {
    static I: OnceLock<Index> = OnceLock::new();
    I.get_or_init(|| {
        let entries: Vec<Entry> = DATA.lines().filter_map(|l| serde_json::from_str::<Value>(l).ok()).map(|v| {
            let s = |k: &str| v[k].as_str().unwrap_or("").to_string();
            Entry { name: set(&s("name")), kw: set(&s("keywords")), text: set(&s("text")), v }
        }).collect();
        let mut df: HashMap<String, f64> = HashMap::new();
        for e in &entries {
            for w in e.name.union(&e.kw).chain(e.text.iter()).collect::<HashSet<_>>() { *df.entry(w.clone()).or_default() += 1.0; }
        }
        let n = entries.len() as f64;
        let idf = df.into_iter().map(|(w, d)| (w, ((n - d + 0.5) / (d + 0.5) + 1.0).ln())).collect();
        Index { entries, idf }
    })
}

fn keys() -> &'static Vec<Vec<String>> {
    static K: OnceLock<Vec<Vec<String>>> = OnceLock::new();
    K.get_or_init(|| serde_json::from_str(KEYS).unwrap_or_default())
}

/// Shortcut rows whose action matches every word of the query (minus filler), best editors first.
pub fn shortcuts(query: &str, max: usize) -> Vec<String> {
    let q: Vec<String> = words(query).into_iter()
        .filter(|w| !STOP.contains(&w.as_str()) && !["shortcut", "shortcuts", "key", "keys", "hotkey", "keyboard", "press"].contains(&w.as_str()))
        .map(|w| stem(&w)).collect();
    if q.is_empty() { return vec![]; }
    let pref = ["Mesh", "Object Mode", "3D View", "Sculpt", "Node Editor", "UV Editor", "Window", "Screen", "3D View Generic", "Curve", "Armature", "Pose"];
    let mut hits: Vec<(usize, String)> = keys().iter().filter(|r| r.len() >= 5).filter_map(|r| {
        let hay = set(&format!("{} {} {}", r[2], r[3], r[4]));
        if !q.iter().all(|w| hay.contains(w) || hay.iter().any(|h| (h.starts_with(w.as_str()) && w.len() >= 4) || (w.starts_with(h.as_str()) && h.len() >= 4))) { return None; }
        let rank = pref.iter().position(|p| *p == r[0]).unwrap_or(pref.len());
        let extra = match r[4].as_str() {
            "" => String::new(),
            "affect=EDGES" => " (rounds edges)".into(),
            "affect=VERTICES" => " (rounds single vertices/corners, not edges)".into(),
            p => format!(" [{p}]"),
        };
        Some((rank, format!("{}: {}{} (in {})", r[1], r[2], extra, r[0])))
    }).collect();
    hits.sort();
    let mut seen = HashSet::new();
    hits.into_iter().map(|(_, s)| s).filter(|s| seen.insert(s.clone())).take(max).collect()
}

pub fn search(query: &str, kind: Option<&str>) -> String {
    let (plain, found) = translate(query);
    let q: Vec<String> = words(&plain).into_iter().filter(|w| !STOP.contains(&w.as_str())).map(|w| stem(&w)).collect();
    if q.is_empty() { return "Ask about a Blender technique, concept, shortcut or free resource, e.g. 'loop cut', 'normal map baking', 'tree', 'rusty metal texture'.".into(); }
    let ix = index();
    let node_q = q.iter().any(|w| w.starts_with("node") || w == "geometry");
    let mut scored: Vec<(f64, &Entry)> = ix.entries.iter().filter(|e| kind.map_or(true, |k| e.v["kind"] == k)).filter_map(|e| {
        let mut s = 0.0;
        let mut matched = 0;
        for w in &q {
            let idf = ix.idf.get(w).copied().unwrap_or(0.0);
            let m = if e.name.contains(w) { 3.0 } else if e.kw.contains(w) { 2.0 } else if e.text.contains(w) { 1.0 } else { 0.0 };
            if m > 0.0 { matched += 1; }
            s += m * idf;
        }
        if matched == 0 { return None; }
        s *= (matched as f64 / q.len() as f64).powi(2); // prefer entries covering the whole question
        // Geometry-node pages share names with modeling tools (Set Shade Smooth, UV Unwrap): only when asked about nodes.
        if !node_q && e.v["source"].as_str().is_some_and(|u| u.contains("/geometry_nodes/")) { s *= 0.4; }
        s *= match e.v["kind"].as_str() { Some("manual") => 1.2, Some("guide") => 1.3, Some("extension") => 0.6, Some("keymap") => 0.8, _ => 1.0 };
        Some((s, e))
    }).collect();
    scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap());
    let mut out = String::new();
    for (i, (_, e)) in scored.iter().take(3).enumerate() {
        let s = |k: &str| e.v[k].as_str().unwrap_or("").to_string();
        let text: String = s("text").chars().take(if i == 0 { 1800 } else { 700 }).collect();
        out += &format!("## {}\n{text}\n(Source: {})\n\n", s("name"), s("source"));
    }
    let mut keys: Vec<String> = vec![];
    for t in &found { keys.extend(shortcuts(t.split('|').last().unwrap_or(t), 4)); }
    if keys.is_empty() { keys = shortcuts(query, 6); }
    keys.dedup();
    keys.truncate(6);
    if !keys.is_empty() {
        out += &format!("Shortcuts (Blender 5.2 defaults):\n- {}\n\n", keys.join("\n- "));
    }
    if out.is_empty() {
        return format!("Nothing about '{query}' in the Blender library. Say so honestly, and suggest the Blender Manual (docs.blender.org).");
    }
    if !found.is_empty() {
        let names: Vec<&str> = found.iter().map(|t| t.split('|').next().unwrap_or(t)).collect();
        out = format!("In Blender this is: {}\n\n{out}", names.join(", "));
    }
    out + "Teach it: explain the idea behind it first (what happens to the vertices/faces/pixels), then the shortcut, and have the creator press it themselves."
}

/// Problems visible in the Blender scene line that matter for this question, checked in code and shown to the
/// creator as written (a small model skips notes like these): unapplied scale, a modifier already doing the job,
/// nothing selected, the wrong mode.
pub fn watchouts(context: &str, question: &str) -> Vec<String> {
    let q = question.to_lowercase();
    let (plain, found) = translate(question);
    let about = |ws: &[&str]| ws.iter().any(|w| q.contains(w) || plain.contains(w));
    let object = context.split("active object ").nth(1).and_then(|s| s.split(" (").next()).unwrap_or("your object");
    let mut out = vec![];
    if context.contains("Object Mode") && found.iter().any(|t| ["bevel", "loop cut", "extrude", "inset", "merge", "fill face", "knife", "recalculate"].iter().any(|k| t.starts_with(k))) {
        out.push("You're in Object Mode, and this tool works in Edit Mode: press **Tab** first.".to_string());
    }
    if context.contains("scale not applied") && about(&["bevel", "solidify", "array", "uv", "texture", "modifier", "thick", "round", "uneven", "stretch", "export", "game"]) {
        out.push(format!("{object}'s scale isn't applied, so bevels, Solidify and textures come out uneven (squashed along the scaled axis). \
                  Fix it first: **Tab** to Object Mode, **Ctrl+A** > **Scale**, then **Tab** back."));
    }
    if context.contains("(Bevel)") && found.iter().any(|t| t.starts_with("bevel")) {
        out.push(format!("{object} already has a **Bevel modifier**, which rounds every edge it's allowed to (Limit Method: Angle). \
                  To round only chosen edges either bevel them for real with **Ctrl+B** in Edit Mode (and remove the modifier), \
                  or keep the modifier, set its Limit Method to **Weight** and give just those edges a bevel weight (**Ctrl+E** > Edge Bevel Weight)."));
    }
    if context.contains("Edit Mode") && context.contains("selected 0 vertices") && !found.is_empty() {
        out.push("Nothing is selected yet: select what to change first (click, **Shift**+click to add more, **A** for all).".to_string());
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn plain_words_become_blender_terms() {
        assert_eq!(translate("How do I round off the edges I have selected?").1, vec!["bevel"]);
        assert_eq!(translate("my bevel looks uneven").1[0], "apply scale transform|menu apply");
        assert_eq!(translate("make the other half match").1, vec!["mirror modifier|mirror"]);
        assert!(translate("the shield is too thin").1.is_empty() || !translate("the shield is too thin").1.contains(&"bevel"));
        assert!(search("round off these edges", None).contains("Ctrl + B: Bevel (rounds edges)"));
        assert!(search("loop cut", None).contains("Ctrl + R"));
    }
    #[test]
    fn scene_watchouts() {
        let ctx = "in Blender 5.2: x.blend; Edit Mode (edge select); active object Crate (MESH, selected 4 vertices, scale not applied (1.00, 1.00, 0.50), modifiers: Bevel (Bevel))";
        let w = watchouts(ctx, "round off these edges");
        assert!(w.iter().any(|s| s.contains("**Ctrl+A** > **Scale**") && s.starts_with("Crate")));
        assert!(w.iter().any(|s| s.contains("Bevel modifier")));
        let w = watchouts("in Blender 5.2: x.blend; Object Mode; active object Cube (MESH)", "how do I loop cut");
        assert!(w.iter().any(|s| s.contains("press **Tab** first")));
        assert!(!w.iter().any(|s| s.contains("Scale")));
    }
}
