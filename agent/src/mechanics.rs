//! Mechanics: self-contained game mechanics, one folder each (res://mechanics/<id>/): mechanic.toml,
//! src/*.rs (compiled into the crate through a #[path] module in lib.rs), tuning.tres, sandbox.tscn,
//! HOW_IT_WORKS.md. This gives Ember the same picture the Mechanics tab shows, and scaffolds new
//! mechanics in the right shape so the model only has to write the logic.
use std::fs;
use std::path::Path;

/// The starters that ship with RusticEngine (Mechanics tab > Add Mechanic).
pub const STARTERS: &[(&str, &str, &str)] = &[
    ("first_person", "First-Person Controller", "walk, sprint, jump, mouse look"),
    ("third_person", "Third-Person Controller", "follow camera that avoids walls, camera-relative movement"),
    ("stats", "Character Stats", "health, stamina, strength, carrying capacity, worth, with signals"),
    ("combat", "Attack & Damage", "melee cone hits, cooldown, stamina cost, hurtboxes, knockback (uses stats)"),
    ("inventory", "Inventory", "items as .tres, stacking, weight limit from strength, selling (uses stats)"),
    ("hud", "HUD", "health/stamina bars with damage trail, worth, message feed (uses stats)"),
];

struct Manifest {
    name: String,
    summary: String,
    node: String,
    uses: Vec<String>,
    parts: Vec<String>,
}

fn quoted(s: &str) -> Vec<String> {
    let mut out = vec![];
    let mut rest = s;
    while let Some(a) = rest.find('"') {
        let after = &rest[a + 1..];
        let Some(b) = after.find('"') else { break };
        out.push(after[..b].to_string());
        rest = &after[b + 1..];
    }
    out
}

fn parse(text: &str) -> Manifest {
    let mut m = Manifest { name: String::new(), summary: String::new(), node: String::new(), uses: vec![], parts: vec![] };
    let mut lines = text.lines();
    while let Some(line) = lines.next() {
        let l = line.trim();
        if l.starts_with('#') || !l.contains('=') {
            continue;
        }
        let (k, v) = l.split_once('=').unwrap();
        let (k, mut v) = (k.trim(), v.trim().to_string());
        if v.starts_with('[') {
            while !v.trim_end().ends_with(']') {
                match lines.next() { Some(n) => { v.push('\n'); v.push_str(n); } None => break }
            }
            match k { "uses" => m.uses = quoted(&v), "parts" => m.parts = quoted(&v), _ => {} }
            continue;
        }
        let v = v.trim_matches('"').to_string();
        match k { "name" => m.name = v, "summary" => m.summary = v, "node" => m.node = v, _ => {} }
    }
    m
}

/// Installed mechanics, and the starters that aren't installed yet.
pub fn list(root: &Path) -> String {
    let dir = root.join("mechanics");
    let mut installed = vec![];
    if let Ok(rd) = fs::read_dir(&dir) {
        let mut ids: Vec<String> = rd.flatten().filter(|e| e.path().join("mechanic.toml").exists())
            .map(|e| e.file_name().to_string_lossy().to_string()).collect();
        ids.sort();
        for id in ids {
            let m = parse(&fs::read_to_string(dir.join(&id).join("mechanic.toml")).unwrap_or_default());
            let uses = if m.uses.is_empty() { String::new() } else { format!(" (uses {})", m.uses.join(", ")) };
            installed.push(format!("- {id}: {} - {}{uses}", m.name, m.summary));
        }
    }
    let mut out = if installed.is_empty() { "No mechanics in this project yet.\n".to_string() }
        else { format!("Mechanics in this project (res://mechanics/<id>/):\n{}\n", installed.join("\n")) };
    let missing: Vec<String> = STARTERS.iter().filter(|(id, _, _)| !dir.join(id).exists())
        .map(|(id, name, what)| format!("- {name} ({id}): {what}")).collect();
    if !missing.is_empty() {
        out += &format!("Starters the creator can add from the Mechanics tab (Add Mechanic):\n{}\n", missing.join("\n"));
    }
    out + "Use mechanic with action info and an id for one mechanic's parts, tuning values and ideas."
}

/// The sections of HOW_IT_WORKS.md whose headings contain any of `wanted` (all, if empty).
pub fn how_it_works(root: &Path, id: &str, wanted: &[&str], max_chars: usize) -> String {
    let text = fs::read_to_string(root.join("mechanics").join(id).join("HOW_IT_WORKS.md")).unwrap_or_default();
    let mut out = String::new();
    for section in text.split("\n## ").skip(1) {
        let heading = section.lines().next().unwrap_or("").to_lowercase();
        if wanted.is_empty() || wanted.iter().any(|w| heading.contains(w)) {
            out += &format!("## {}\n", section.trim_end());
            out.push('\n');
        }
    }
    if out.len() > max_chars {
        let mut cut = max_chars;
        while !out.is_char_boundary(cut) { cut -= 1; }
        out.truncate(cut);
        out += "\n[...]";
    }
    out
}

/// The current tuning values (name = value lines from tuning.tres).
fn tuning_values(root: &Path, id: &str) -> Vec<String> {
    let text = fs::read_to_string(root.join("mechanics").join(id).join("tuning.tres")).unwrap_or_default();
    text.split("[resource]").nth(1).unwrap_or("").lines().map(str::trim)
        .filter(|l| l.contains(" = ") && !l.starts_with("script")).map(String::from).collect()
}

/// One mechanic: what it is, its parts, what it uses, its current tuning, and the main ideas.
pub fn info(root: &Path, id: &str) -> Result<String, String> {
    let id = id.trim().trim_start_matches("res://").trim_start_matches("mechanics/").trim_end_matches('/');
    let dir = root.join("mechanics").join(id);
    let Ok(toml) = fs::read_to_string(dir.join("mechanic.toml")) else {
        return Err(format!("There's no mechanic '{id}' in this project.\n{}", list(root)));
    };
    let m = parse(&toml);
    let mut out = format!("Mechanic {} (res://mechanics/{id}/): {}\n", m.name, m.summary);
    if !m.node.is_empty() {
        out += &format!("Node to add to a scene: {}\n", m.node);
    }
    out += &format!("Uses: {}\n", if m.uses.is_empty() { "nothing else".to_string() } else { m.uses.join(", ") });
    if !m.parts.is_empty() {
        out += &format!("Parts:\n{}\n", m.parts.iter().map(|p| format!("- {p}")).collect::<Vec<_>>().join("\n"));
    }
    let values = tuning_values(root, id);
    if !values.is_empty() {
        out += &format!("Current tuning (mechanics/{id}/tuning.tres; the creator changes these in the Mechanics tab, live while the game runs):\n{}\n", values.join(", "));
    }
    let ideas = how_it_works(root, id, &["the idea", "one frame", "one attack", "adding an item"], 2600);
    if !ideas.is_empty() {
        out += &format!("From HOW_IT_WORKS.md:\n{ideas}");
    }
    Ok(out)
}

/// The tuning values whose names or descriptions match a question ("feels slow", "floaty jumps"),
/// with their current values and what they do (the /// comments in tuning.rs). Best first.
pub fn tuning_matches(root: &Path, id: &str, question: &str) -> Vec<String> {
    const STOP: &[&str] = &["the", "and", "how", "can", "make", "this", "that", "with", "for", "you", "your", "want", "feels", "feel", "way",
        "too", "very", "really", "kind", "like", "what", "does", "why", "when", "are", "is", "it's", "its", "my", "can't", "cant", "don't", "much", "more", "less"];
    let words = |s: &str| -> Vec<String> {
        s.to_lowercase().split(|c: char| !c.is_alphanumeric()).filter(|w| w.len() >= 3 && !STOP.contains(w))
            .map(|w| w.trim_end_matches('s').to_string()).filter(|w| w.len() >= 3).collect()
    };
    let q = words(question);
    let src = fs::read_to_string(root.join("mechanics").join(id).join("src/tuning.rs")).unwrap_or_default();
    let values: std::collections::HashMap<String, String> = tuning_values(root, id).iter()
        .filter_map(|l| l.split_once(" = ").map(|(k, v)| (k.to_string(), v.to_string()))).collect();
    let mut doc = String::new();
    let mut attrs = String::new();
    let mut found: Vec<(usize, String)> = vec![];
    for line in src.lines() {
        let l = line.trim();
        if let Some(d) = l.strip_prefix("///") {
            doc.push_str(d.trim());
            doc.push(' ');
        } else if l.starts_with("#[") {
            attrs.push_str(l);
        } else if let Some(rest) = l.strip_prefix("pub ") {
            if let Some((name, _)) = rest.split_once(':') {
                let name = name.trim();
                if name != "base" && !doc.is_empty() {
                    let hay = words(&format!("{} {}", name.replace('_', " "), doc));
                    let score = q.iter().filter(|w| hay.iter().any(|h| h == *w || (w.len() >= 5 && h.len() >= 5 && h[..5] == w[..5]))).count();
                    if score > 0 {
                        let unit = attrs.split("suffix = \"").nth(1).and_then(|s| s.split('"').next()).unwrap_or("");
                        let now = values.get(name).cloned().unwrap_or_else(|| "?".into());
                        found.push((score, format!("- {name} = {now}{}{}: {}", if unit.is_empty() { "" } else { " " }, unit, doc.trim())));
                    }
                }
            }
            doc.clear();
            attrs.clear();
        } else if l.is_empty() || l.starts_with("//") {
            continue;
        } else {
            doc.clear();
            attrs.clear();
        }
    }
    found.sort_by(|a, b| b.0.cmp(&a.0));
    let top = found.first().map(|f| f.0).unwrap_or(0);
    found.into_iter().filter(|f| f.0 * 3 >= top * 2).take(3).map(|f| f.1).collect()
}

fn pascal(s: &str) -> String {
    s.split(|c: char| !c.is_ascii_alphanumeric()).filter(|w| !w.is_empty())
        .map(|w| { let mut c = w.chars(); c.next().map(|f| f.to_ascii_uppercase().to_string() + c.as_str()).unwrap_or_default() })
        .collect()
}

fn snake(s: &str) -> String {
    let mut out = String::new();
    for (i, ch) in s.chars().enumerate() {
        if ch.is_ascii_uppercase() && i > 0 { out.push('_'); }
        out.push(ch.to_ascii_lowercase());
    }
    out
}

/// Create a new mechanic folder in the standard shape and register its code in lib.rs.
pub fn scaffold(root: &Path, id: &str, name: &str, summary: &str, node: &str, base: &str, uses: &[String]) -> Result<String, String> {
    let id: String = id.trim().to_lowercase().chars().map(|c| if c.is_ascii_alphanumeric() { c } else { '_' }).collect();
    if id.is_empty() || !id.chars().next().unwrap().is_ascii_alphabetic() {
        return Err("Give the mechanic an id in snake_case, like stamina or double_jump.".into());
    }
    let dir = root.join("mechanics").join(&id);
    if dir.exists() {
        return Err(format!("mechanics/{id} already exists. Use mechanic info to see it, then edit its files."));
    }
    let lib_path = root.join("rust/src/lib.rs");
    let Ok(lib) = fs::read_to_string(&lib_path) else { return Err("rust/src/lib.rs is missing. Is this a Rust project?".into()) };
    for u in uses {
        if !root.join("mechanics").join(u).exists() {
            return Err(format!("It uses '{u}', which isn't in this project. Ask the creator to add it first (Mechanics tab > Add Mechanic), or leave it out."));
        }
    }
    let node = if node.trim().is_empty() { pascal(&id) } else { pascal(node) };
    let base = if base.trim().is_empty() { "Node".to_string() } else { base.trim().to_string() };
    if !base.chars().all(|c| c.is_ascii_alphanumeric()) {
        return Err(format!("'{base}' isn't a Godot class name."));
    }
    let tuning = format!("{node}Tuning");
    let node_mod = snake(&node);
    let name = if name.trim().is_empty() { node.clone() } else { name.trim().to_string() };
    let summary = if summary.trim().is_empty() { "TODO: one sentence about what this mechanic does.".to_string() } else { summary.trim().replace('"', "'") };
    fs::create_dir_all(dir.join("src")).map_err(|e| e.to_string())?;
    let uses_toml = uses.iter().map(|u| format!("\"{u}\"")).collect::<Vec<_>>().join(", ");
    let files: Vec<(String, String)> = vec![
        ("mechanic.toml".into(), format!(
"# A Mechanic: everything one game mechanic needs, in one folder.
name = \"{name}\"
id = \"{id}\"
summary = \"{summary}\"
version = \"1.0\"
uses = [{uses_toml}]
node = \"{node}\"
tuning = \"tuning.tres\"
sandbox = \"sandbox.tscn\"
parts = [
  \"src/tuning.rs: the dials (every value the creator can tune)\",
  \"src/{node_mod}.rs: the node (put it in a scene; it runs the mechanic every frame)\",
]
")),
        ("src/mod.rs".into(), format!(
"//! # {name} (a RusticEngine Mechanic)
//!
//! {summary}
//! - `tuning.rs` the dials: every value the creator can tune (saved in tuning.tres)
//! - `{node_mod}.rs` the node: put a `{node}` in a scene

mod tuning;
mod {node_mod};

#[allow(unused_imports)]
pub use tuning::{tuning};
#[allow(unused_imports)]
pub use {node_mod}::{node};
")),
        ("src/tuning.rs".into(), format!(
"//! The dials for {name}. Saved in `tuning.tres`, shown in the Mechanics tab, read every frame.
//! Add a value: a `pub` field with #[export(range = (min, max, step, suffix = \"unit\"))], #[init(val = default)]
//! and a /// comment saying what it does and how it feels (that comment becomes its tooltip).

use godot::prelude::*;

#[derive(GodotClass)]
#[class(base = Resource, init, tool)]
pub struct {tuning} {{
    /// An example value: how fast something happens, per second. Replace it with this mechanic's real dials.
    #[export(range = (0.0, 100.0, 0.1, or_greater, suffix = \"/s\"))]
    #[init(val = 1.0)]
    pub speed: f32,

    base: Base<Resource>,
}}
")),
        (format!("src/{node_mod}.rs"), format!(
"//! The node for {name}: put a `{node}` in a scene. {summary}

use godot::classes::{{I{base}, {base}}};
use godot::prelude::*;

use super::tuning::{tuning};

const DEFAULT_TUNING: &str = \"res://mechanics/{id}/tuning.tres\";

#[derive(GodotClass)]
#[class(base = {base})]
pub struct {node} {{
    /// Leave empty to use the shared mechanics/{id}/tuning.tres.
    #[export]
    tuning: Option<Gd<{tuning}>>,
    base: Base<{base}>,
}}

#[godot_api]
impl I{base} for {node} {{
    fn init(base: Base<{base}>) -> Self {{
        Self {{ tuning: None, base }}
    }}

    fn ready(&mut self) {{
        if self.tuning.is_none() {{
            self.tuning = Some(try_load::<{tuning}>(DEFAULT_TUNING).unwrap_or_else(|_| {tuning}::new_gd()));
        }}
    }}

    fn process(&mut self, delta: f64) {{
        // Read the tuning every frame, so changes in the Mechanics tab apply immediately.
        let t = self.tuning.clone().unwrap_or_else({tuning}::new_gd);
        let speed = t.bind().speed;
        let _ = (speed, delta);
        // TODO: the mechanic's logic.
    }}
}}

#[godot_api]
impl {node} {{
    // Signals tell other mechanics what happened (the HUD, sounds...). Example:
    // #[signal]
    // pub fn changed(value: f32);
}}
")),
        ("tuning.tres".into(), format!("[gd_resource type=\"{tuning}\" format=3]\n\n[resource]\nspeed = 1.0\n")),
        ("sandbox.tscn".into(), sandbox_scene(&node, &base)),
        ("HOW_IT_WORKS.md".into(), format!(
"# How {name} works

## The problem
TODO: what problem this solves for the player, in plain words.

## The idea, as parts of a machine
| Part | Like... | Its job |
|---|---|---|
| **Tuning** (`tuning.rs`, `tuning.tres`) | the dials | Every value the creator can change. |
| **{node}** (`{node_mod}.rs`) | the driver | Runs the mechanic every frame. |

## One frame, step by step
1. Read the tuning.
2. TODO

## The tuning values
| Value | Default | Feel |
|---|---|---|
| Speed | 1 | TODO |

## Try it: predict, then test
- TODO: a question to predict, then a value to change in the sandbox.

## The map to the code
| Concept | Where |
|---|---|
| All tunable values | `src/tuning.rs` (saved in `tuning.tres`) |
| The per-frame logic | `src/{node_mod}.rs` |
")),
    ];
    for (rel, content) in &files {
        fs::write(dir.join(rel), content).map_err(|e| format!("Can't write mechanics/{id}/{rel}: {e}"))?;
    }
    let header = "// Mechanics: each one lives in its own folder under res://mechanics/ (see the Mechanics tab).";
    let mut lib = lib.trim_end().to_string();
    if !lib.contains(header) {
        lib += &format!("\n\n{header}");
    }
    lib += &format!("\n#[path = \"../../mechanics/{id}/src/mod.rs\"]\nmod {id};\n");
    fs::write(&lib_path, lib).map_err(|e| e.to_string())?;
    let list: Vec<String> = files.iter().map(|(r, _)| format!("mechanics/{id}/{r}")).collect();
    // Working code to copy patterns from, if those starters are in the project.
    const EXAMPLES: [(&str, &str); 5] = [
        ("first_person/src/controller.rs", "input actions, moving a CharacterBody3D, jump timing, emitting signals"),
        ("first_person/src/jump.rs", "pure Rust rules with tests"),
        ("stats/src/stats.rs", "signals with values, #[func] methods other mechanics call, find_stats()"),
        ("combat/src/hurtbox.rs", "groups, calling into another mechanic's node (crate::stats), knockback"),
        ("hud/src/hud.rs", "building UI in code, optional connection to another mechanic by name"),
    ];
    let examples: Vec<String> = EXAMPLES.iter().filter(|(f, _)| root.join("mechanics").join(f).exists())
        .map(|(f, what)| format!("- mechanics/{f}: {what}")).collect();
    let examples = if examples.is_empty() { String::new() } else { format!("\nWorking code to read before writing (same rules, known to compile):\n{}", examples.join("\n")) };
    Ok(format!(
        "Created the {name} mechanic and registered it in rust/src/lib.rs:\n{}\nNext: put the logic in mechanics/{id}/src/{node_mod}.rs, replace the example `speed` dial in tuning.rs (and tuning.tres) with the real values, \
         build_rust, then fill in HOW_IT_WORKS.md together with the creator. Other mechanics' code is reachable as crate::<id>::... (e.g. crate::stats::find_stats).{examples}",
        list.join("\n")))
}

fn sandbox_scene(node: &str, base: &str) -> String {
    if base.ends_with("3D") {
        format!("[gd_scene format=3]

[sub_resource type=\"Environment\" id=\"Environment_1\"]
background_mode = 1
background_color = Color(0.45, 0.55, 0.65, 1)
ambient_light_source = 2
ambient_light_color = Color(0.6, 0.6, 0.6, 1)

[sub_resource type=\"BoxShape3D\" id=\"BoxShape3D_1\"]
size = Vector3(40, 1, 40)

[sub_resource type=\"BoxMesh\" id=\"BoxMesh_1\"]
size = Vector3(40, 1, 40)

[node name=\"Sandbox\" type=\"Node3D\"]

[node name=\"WorldEnvironment\" type=\"WorldEnvironment\" parent=\".\"]
environment = SubResource(\"Environment_1\")

[node name=\"Sun\" type=\"DirectionalLight3D\" parent=\".\"]
transform = Transform3D(0.866025, -0.353553, 0.353553, 0, 0.707107, 0.707107, -0.5, -0.612372, 0.612372, 0, 10, 0)
shadow_enabled = true

[node name=\"Floor\" type=\"StaticBody3D\" parent=\".\"]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, -0.5, 0)

[node name=\"Shape\" type=\"CollisionShape3D\" parent=\"Floor\"]
shape = SubResource(\"BoxShape3D_1\")

[node name=\"Mesh\" type=\"MeshInstance3D\" parent=\"Floor\"]
mesh = SubResource(\"BoxMesh_1\")

[node name=\"Camera3D\" type=\"Camera3D\" parent=\".\"]
transform = Transform3D(1, 0, 0, 0, 0.939693, 0.34202, 0, -0.34202, 0.939693, 0, 4, 8)

[node name=\"{node}\" type=\"{node}\" parent=\".\"]
")
    } else if base.ends_with("2D") {
        format!("[gd_scene format=3]

[node name=\"Sandbox\" type=\"Node2D\"]

[node name=\"Camera2D\" type=\"Camera2D\" parent=\".\"]

[node name=\"{node}\" type=\"{node}\" parent=\".\"]
")
    } else {
        format!("[gd_scene format=3]

[node name=\"Sandbox\" type=\"Control\"]
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0

[node name=\"{node}\" type=\"{node}\" parent=\".\"]
")
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn parses_manifest_arrays() {
        let m = parse("name = \"Inventory\"\nuses = [\"stats\", \"first_person\"]\nparts = [\n  \"a: b\",\n  \"c: d\",\n]\nnode = \"Inventory\"\n");
        assert_eq!(m.name, "Inventory");
        assert_eq!(m.uses, vec!["stats", "first_person"]);
        assert_eq!(m.parts.len(), 2);
        assert_eq!(m.node, "Inventory");
    }
    #[test]
    fn matches_tuning_to_questions() {
        let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../engine/modules/rustic");
        let first = |id: &str, q: &str| tuning_matches(&root, id, q).first().cloned().unwrap_or_default();
        assert!(first("first_person", "the player feels really slow").contains("walk_speed = 4.5 m/s"), "{}", first("first_person", "the player feels really slow"));
        assert!(first("first_person", "jumping feels floaty, like on the moon").contains("gravity"));
        assert!(first("third_person", "the character turns way too slowly").contains("turn_speed"));
        assert!(first("combat", "players can spam attacks way too fast").contains("attack_cooldown"));
        assert!(first("combat", "my sword hits enemies way off to the side").contains("arc"));
    }

    #[test]
    fn scaffold_makes_a_registered_mechanic() {
        let root = std::env::temp_dir().join(format!("mech_scaffold_{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(root.join("rust/src")).unwrap();
        fs::write(root.join("rust/src/lib.rs"), "use godot::prelude::*;\nmod player;\n").unwrap();
        let msg = scaffold(&root, "Double Jump", "Double Jump", "Jump again in the air.", "", "Node3D", &[]).unwrap();
        assert!(msg.contains("mechanics/double_jump/src/double_jump.rs"));
        let lib = fs::read_to_string(root.join("rust/src/lib.rs")).unwrap();
        assert!(lib.contains("#[path = \"../../mechanics/double_jump/src/mod.rs\"]\nmod double_jump;"));
        let info = info(&root, "double_jump").unwrap();
        assert!(info.contains("DoubleJump") && info.contains("speed = 1.0"));
        assert!(scaffold(&root, "double_jump", "", "", "", "Node", &[]).is_err());
        assert!(scaffold(&root, "x", "", "", "", "Node", &["stats".into()]).is_err());
        let _ = fs::remove_dir_all(&root);
    }
}
