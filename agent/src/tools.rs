//! The tools Ember can use on a RusticEngine project. All paths stay inside the project folder.
use std::fs;
use std::io::Read;
use std::path::{Component, Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

use serde_json::{Value, json};

use crate::llm::ToolDef;

pub struct Project {
    pub root: PathBuf,
    pub engine: Option<PathBuf>,
    pub cache_dir: PathBuf,
}

pub struct Outcome {
    pub ok: bool,
    pub content: String,
    pub files_changed: bool,
    pub rust_built: bool,
    /// Full compiler output (build_rust only; not shown to the model).
    pub raw: String,
}

fn with_fixes(mut o: Outcome, fixed: &[String]) -> Outcome {
    if !fixed.is_empty() {
        o.content = format!("(Auto-fixed missing imports: {}.)\n{}", fixed.join("; "), o.content);
        o.files_changed = true;
    }
    o
}

const MAX_RESULT: usize = 12_000;

const RUST_ERRORS: &str = include_str!("../examples/rust_errors.json");

/// The official rustc explanation for each error code in the output (at most 3, once each).
fn error_explanations(raw: &str) -> Vec<String> {
    let table: Value = serde_json::from_str(RUST_ERRORS).unwrap_or(json!({}));
    let mut seen = vec![];
    for line in raw.lines() {
        if let Some(rest) = line.strip_prefix("error[E") {
            let code = format!("E{}", rest.chars().take_while(|c| c.is_ascii_digit()).collect::<String>());
            if !seen.contains(&code) && seen.len() < 3 { seen.push(code); }
        }
    }
    seen.iter().filter_map(|c| table[c].as_str().map(|t| format!("{c}: {t}"))).collect()
}

/// Mistakes that come up again and again with godot-rust, and what actually fixes them.
fn godot_rust_hints(raw: &str) -> Vec<String> {
    const H: &[(&str, &str)] = &[
        ("found for struct `__godot_Signals_", "`self.signals()` only has your class's own `#[signal]`s and its base class's signals. \
          A Button's `pressed` lives on the Button: `button.signals().pressed().connect_other(&self.to_gd(), Self::on_pressed)`."),
        ("already mutably borrowed", "Two borrows of the same object overlap: finish with `self.base()` before calling `self.base_mut()`, \
          and don't call `bind_mut()` on yourself while inside one of your own methods."),
        ("already borrowed", "Two borrows of the same object overlap: read values into local variables first, then call `base_mut()`/`bind_mut()`."),
        ("cannot find type `ProcessMode`", "It's `godot::classes::node::ProcessMode` (enums live in a module named after their class, in snake_case)."),
        ("cannot find type `MouseMode`", "It's `godot::classes::input::MouseMode`."),
        ("cannot find type `WindowMode`", "It's `godot::classes::display_server::WindowMode`."),
        ("casting `bool` as `f32` is invalid", "Rust won't turn a bool into a number: write `if pressed { 1.0 } else { 0.0 }`, \
          or use `Input::singleton().get_axis(\"ui_left\", \"ui_right\")`."),
        ("found for struct `Gd<label::Label>`", "You have your own class or module called `Label`, which hides Godot's Label. Rename yours, \
          or write `godot::classes::Label` in full."),
        ("is not an iterator", "Godot arrays iterate with `.iter_shared()`: `for node in array.iter_shared() { ... }`."),
        ("expected `f32`, found `f64`", "`delta` is an f64 but Godot vectors use f32: write `delta as f32`."),
        ("expected `f64`, found `f32`", "This Godot method takes an f64: convert with `value as f64`."),
        ("expected `&str`, found `String`", "Pass a reference: `&my_string`."),
        ("no method named `unwrap` found for struct `Gd<", "That method already returns `Gd<T>` (not an Option), so there's nothing to unwrap: remove `.unwrap()`."),
        ("no method named `get_tree` found", "Call it through the base: `self.base().get_tree()`."),
        ("no method named `get_node_as` found", "Call it through the base: `self.base().get_node_as::<Label>(\"Path\")`."),
    ];
    H.iter().filter(|(pat, _)| raw.contains(pat)).map(|(_, h)| h.to_string()).take(3).collect()
}

pub fn definitions() -> Vec<ToolDef> {
    vec![
        ToolDef { name: "list_files", description: "List the project's files and folders (skips build output).",
            schema: json!({"type": "object", "properties": {
                "path": {"type": "string", "description": "Folder to list, relative to the project. Default: the whole project."}}}) },
        ToolDef { name: "read_file", description: "Read a text file from the project (Rust code, scenes, settings).",
            schema: json!({"type": "object", "properties": {
                "path": {"type": "string", "description": "For example rust/src/player.rs or main.tscn"}}, "required": ["path"]}) },
        ToolDef { name: "write_file", description: "Create or overwrite a text file in the project with the full new content.",
            schema: json!({"type": "object", "properties": {
                "path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}) },
        ToolDef { name: "edit_file", description: "Replace one exact, unique piece of text in a file. Read the file first.",
            schema: json!({"type": "object", "properties": {
                "path": {"type": "string"},
                "old_text": {"type": "string", "description": "Text to find; must appear exactly once."},
                "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}) },
        ToolDef { name: "new_rust_node", description: "Create a new Rust node class file from a starter template and register it in lib.rs.",
            schema: json!({"type": "object", "properties": {
                "name": {"type": "string", "description": "Class name in PascalCase, e.g. Enemy"},
                "base": {"type": "string", "description": "Godot base class, e.g. Node2D, CharacterBody2D, Area2D, RigidBody2D, Sprite2D, Control, CanvasLayer, Node3D"}},
                "required": ["name", "base"]}) },
        ToolDef { name: "build_rust", description: "Compile the project's Rust code with cargo. Returns errors and warnings, or success.",
            schema: json!({"type": "object", "properties": {}}) },
        ToolDef { name: "run_game", description: "Build, then playtest the main scene without a window for a few seconds of game time. Returns what the game printed and any errors.",
            schema: json!({"type": "object", "properties": {
                "seconds": {"type": "number", "description": "Game seconds to simulate (1-30, default 5)"}}}) },
        ToolDef { name: "class_info", description: "Look up a Godot class: its parent, methods, properties and signals. Use the same names in Rust (snake_case).",
            schema: json!({"type": "object", "properties": {
                "class_name": {"type": "string", "description": "e.g. CharacterBody2D, Label, Timer"},
                "filter": {"type": "string", "description": "Optional word to only show matching members, e.g. velocity"}},
                "required": ["class_name"]}) },
        ToolDef { name: "find_example", description: "Search a library of real, working godot-rust 0.5 code for how to do something. Use it before writing an API you're not sure about.",
            schema: json!({"type": "object", "properties": {
                "query": {"type": "string", "description": "Class, method or idea, e.g. 'Timer timeout connect', 'Tween tween_property', 'get_overlapping_bodies'"}}, "required": ["query"]}) },
        ToolDef { name: "game_design", description: "Look up game design knowledge: what players love about a game (e.g. 'Dark Souls', 'Stardew Valley') or how a design idea works and feels (e.g. 'coyote time', 'stamina', 'roguelite'). Use it to understand what the creator means, then ask them.",
            schema: json!({"type": "object", "properties": {
                "query": {"type": "string", "description": "A game name or a design idea"}}, "required": ["query"]}) },
        ToolDef { name: "journal", description: "The creator's Concept Journal (design/journal/): search it for their ideas, or add a new entry when they ask you to save an idea. Never change their existing entries without asking.",
            schema: json!({"type": "object", "properties": {
                "action": {"type": "string", "enum": ["search", "add"]},
                "query": {"type": "string", "description": "search: words to look for"},
                "title": {"type": "string", "description": "add: the entry's title"},
                "text": {"type": "string", "description": "add: the entry, in the creator's words"}}, "required": ["action"]}) },
        ToolDef { name: "game_path", description: "Game Paths and Art Paths: step-by-step courses for making a kind of game (open-world RPG, souls-like, platformer, survival, roguelike, cozy farming, metroidvania, tower defense, turn-based RPG) or making 3D models in the Studio (a prop, a character, an environment kit). No arguments lists them; a path opens its overview; a path and step opens that step.",
            schema: json!({"type": "object", "properties": {
                "path": {"type": "string", "description": "e.g. open-world-rpg"},
                "step": {"type": "integer", "description": "Step number, starting at 1"}}}) },
        ToolDef { name: "asset_info", description: "Describe a file the creator added: an image's size and whether it looks like a sprite sheet, a 3D model's parts and animations, a sound's length, a scene's nodes. Works on folders too.",
            schema: json!({"type": "object", "properties": {
                "path": {"type": "string", "description": "e.g. assets/hero.png or design/concept"}}, "required": ["path"]}) },
        ToolDef { name: "look_at_image", description: "Look at an image (concept art, a sprite, a screenshot) and get a description of what it shows. Ask a specific question when you have one.",
            schema: json!({"type": "object", "properties": {
                "path": {"type": "string", "description": "e.g. design/concept/forest.png"},
                "question": {"type": "string", "description": "Optional: what to look for, e.g. 'What colors and mood does this have?'"}}, "required": ["path"]}) },
        ToolDef { name: "set_mode", description: "Switch how you work with the creator: 'learning' (teach them as you build together) or 'autonomous' (you build, they direct). Only when they ask for it.",
            schema: json!({"type": "object", "properties": {
                "mode": {"type": "string", "enum": ["learning", "autonomous"]}}, "required": ["mode"]}) },
    ]
}

pub fn summary(name: &str, args: &Value) -> String {
    let p = args["path"].as_str().unwrap_or("");
    match name {
        "list_files" => "Looking around the project".into(),
        "read_file" => format!("Reading {p}"),
        "write_file" => format!("Writing {p}"),
        "edit_file" => format!("Editing {p}"),
        "new_rust_node" => format!("Creating Rust node {} ({})", args["name"].as_str().unwrap_or("?"), args["base"].as_str().unwrap_or("?")),
        "build_rust" => "Building the Rust code".into(),
        "run_game" => format!("Playtesting the game ({} s)", args["seconds"].as_f64().unwrap_or(5.0)),
        "class_info" => format!("Looking up {}", args["class_name"].as_str().unwrap_or("?")),
        "asset_info" => format!("Inspecting {p}"),
        "find_example" => format!("Finding examples of {}", args["query"].as_str().unwrap_or("?")),
        "journal" => if args["action"] == "add" { format!("Saving \"{}\" to the journal", args["title"].as_str().unwrap_or("idea")) }
                     else { format!("Searching the journal for {}", args["query"].as_str().unwrap_or("?")) },
        "game_path" => match (args["path"].as_str(), args["step"].as_u64()) {
            (None, _) => "Looking at the Game Paths".into(),
            (Some(p), None) => format!("Opening the {p} path"),
            (Some(p), Some(n)) => format!("Opening step {n} of the {p} path"),
        },
        "game_design" => format!("Studying the design of {}", args["query"].as_str().unwrap_or("?")),
        "look_at_image" => format!("Looking at {p}"),
        "set_mode" => format!("Switching to {} mode", args["mode"].as_str().unwrap_or("?")),
        other => format!("Using {other}"),
    }
}

fn ok(content: impl Into<String>) -> Outcome {
    Outcome { ok: true, content: content.into(), files_changed: false, rust_built: false, raw: String::new() }
}
fn fail(content: impl Into<String>) -> Outcome {
    Outcome { ok: false, content: content.into(), files_changed: false, rust_built: false, raw: String::new() }
}
fn truncate(s: &str, max: usize) -> String {
    if s.len() <= max { return s.to_string(); }
    let mut cut = s.len() - max;
    while !s.is_char_boundary(cut) { cut += 1; }
    format!("...(earlier output trimmed)...\n{}", &s[cut..])
}

impl Project {
    fn journal(&self, args: &Value) -> Outcome {
        if args["action"] != "add" {
            return ok(crate::assets::journal_search(&self.root, args["query"].as_str().unwrap_or("")));
        }
        let title = args["title"].as_str().unwrap_or("").trim();
        let text = args["text"].as_str().unwrap_or("").trim();
        if title.is_empty() || text.is_empty() { return fail("Give the entry a title and some text."); }
        let slug: String = title.to_lowercase().chars().map(|c| if c.is_alphanumeric() { c } else { '-' }).collect();
        let slug = slug.split('-').filter(|s| !s.is_empty()).collect::<Vec<_>>().join("-");
        let dir = self.root.join("design/journal");
        let _ = fs::create_dir_all(&dir);
        let mut name = format!("{}.md", if slug.is_empty() { "idea" } else { &slug });
        let mut n = 2;
        while dir.join(&name).exists() { name = format!("{slug}-{n}.md"); n += 1; }  // never overwrite their entries
        match fs::write(dir.join(&name), format!("# {title}\n\n{text}\n")) {
            Ok(()) => Outcome { files_changed: true, ..ok(format!("Saved to design/journal/{name}.")) },
            Err(e) => fail(format!("Couldn't save: {e}")),
        }
    }

    /// Load an image for look_at_image: (mime type, base64 data).
    pub fn image(&self, path: &str) -> Result<(&'static str, String), String> {
        let mime = crate::assets::mime_of(path).ok_or_else(|| format!("{path} isn't a PNG, JPG, WebP or GIF image."))?;
        let p = self.resolve(path, false)?;
        let b = fs::read(&p).map_err(|e| format!("Can't read {path}: {e}"))?;
        if b.len() > 20 << 20 { return Err(format!("{path} is over 20 MB; save a smaller copy to look at.")); }
        Ok((mime, crate::llm::base64(&b)))
    }

    pub fn run(&self, name: &str, args: &Value) -> Outcome {
        let path = args["path"].as_str().unwrap_or("");
        let mut out = self.run_inner(name, args, path);
        // A hand-written scene that references something it never defines won't load; say so right away.
        if out.files_changed && path.ends_with(".tscn") {
            if let Ok(text) = self.resolve(path, false).and_then(|p| fs::read_to_string(p).map_err(|e| e.to_string())) {
                let problems = scene_problems(&text);
                if !problems.is_empty() {
                    out.ok = false;
                    out.content = format!("{}\nBut {path} won't load - fix it now:\n- {}", out.content, problems.join("\n- "));
                }
            }
        }
        out
    }

    fn run_inner(&self, name: &str, args: &Value, path: &str) -> Outcome {
        match name {
            "list_files" => self.list_files(path),
            "journal" => self.journal(args),
            "game_path" => match args["path"].as_str().filter(|p| !p.is_empty()) {
                None => ok(crate::paths::list()),
                Some(p) => match crate::paths::open(&self.root, p, args["step"].as_u64().map(|n| n as usize)) {
                    Ok((t, changed)) => Outcome { files_changed: changed, ..ok(t) },
                    Err(e) => fail(e),
                },
            },
            "game_design" => ok(crate::design::search(args["query"].as_str().unwrap_or(""))),
            "find_example" => ok(crate::examples::search(args["query"].as_str().unwrap_or(""), 2)),
            "asset_info" => match self.resolve(path, false) {
                Ok(p) => match crate::assets::info(&p, path) { Ok(t) => ok(t), Err(e) => fail(e) },
                Err(e) => fail(e),
            },
            "read_file" => match self.resolve(path, false) {
                Ok(p) => match fs::read_to_string(&p) {
                    Ok(t) => ok(truncate(&t, MAX_RESULT)),
                    Err(e) => fail(format!("Can't read {path}: {e}")),
                },
                Err(e) => fail(e),
            },
            "write_file" => {
                let content = args["content"].as_str().unwrap_or("");
                match self.resolve(path, true) {
                    Ok(p) => {
                        if let Some(dir) = p.parent() { let _ = fs::create_dir_all(dir); }
                        match fs::write(&p, content) {
                            Ok(()) => Outcome { files_changed: true, ..ok(format!("Wrote {path} ({} lines).", content.lines().count())) },
                            Err(e) => fail(format!("Can't write {path}: {e}")),
                        }
                    }
                    Err(e) => fail(e),
                }
            }
            "edit_file" => self.edit_file(path, args["old_text"].as_str().unwrap_or(""), args["new_text"].as_str().unwrap_or("")),
            "new_rust_node" => self.new_rust_node(args["name"].as_str().unwrap_or(""), args["base"].as_str().unwrap_or("Node2D")),
            "build_rust" => self.build_rust(),
            "run_game" => self.run_game(args["seconds"].as_f64().unwrap_or(5.0)),
            "class_info" => self.class_info(args["class_name"].as_str().unwrap_or(""), args["filter"].as_str().unwrap_or("")),
            other => fail(format!("Unknown tool {other}.")),
        }
    }

    /// Map a project-relative (or res://) path to an absolute one, refusing anything outside the project.
    fn resolve(&self, path: &str, writing: bool) -> Result<PathBuf, String> {
        let rel = path.trim().trim_start_matches("res://").trim_start_matches("./");
        let rel_path = Path::new(rel);
        if rel.is_empty() || rel_path.is_absolute() || rel_path.components().any(|c| matches!(c, Component::ParentDir)) {
            return Err(format!("'{path}' isn't a path inside the project. Use a relative path like rust/src/player.rs."));
        }
        if writing && (rel.starts_with(".godot") || rel.starts_with("rust/target") || rel.ends_with(".gdextension")) {
            return Err(format!("{path} is managed by the engine; don't change it."));
        }
        Ok(self.root.join(rel_path))
    }

    fn list_files(&self, path: &str) -> Outcome {
        let start = if path.is_empty() || path == "." || path == "res://" { self.root.clone() } else {
            match self.resolve(path, false) { Ok(p) => p, Err(e) => return fail(e) }
        };
        let mut out = String::new();
        fn walk(dir: &Path, root: &Path, depth: usize, out: &mut String) {
            let Ok(rd) = fs::read_dir(dir) else { return };
            let mut entries: Vec<_> = rd.flatten().collect();
            entries.sort_by_key(|e| e.file_name());
            for e in entries {
                let name = e.file_name().to_string_lossy().to_string();
                if name.starts_with('.') && name != ".gdignore" || name == "target" || name.ends_with(".import") || name.ends_with(".uid") {
                    continue;
                }
                let rel = e.path().strip_prefix(root).unwrap_or(&e.path()).to_string_lossy().to_string();
                if e.path().is_dir() {
                    out.push_str(&format!("{}{}/\n", "  ".repeat(depth), rel));
                    if depth < 5 { walk(&e.path(), root, depth + 1, out); }
                } else if name != ".gdignore" {
                    out.push_str(&format!("{}{}\n", "  ".repeat(depth), rel));
                }
            }
        }
        walk(&start, &self.root, 0, &mut out);
        ok(if out.is_empty() { "(empty)".to_string() } else { truncate(&out, MAX_RESULT) })
    }

    fn edit_file(&self, path: &str, old: &str, new: &str) -> Outcome {
        let p = match self.resolve(path, true) { Ok(p) => p, Err(e) => return fail(e) };
        let text = match fs::read_to_string(&p) { Ok(t) => t, Err(e) => return fail(format!("Can't read {path}: {e}")) };
        if old.is_empty() { return fail("old_text is empty. Use write_file to create a file."); }
        match text.matches(old).count() {
            0 => match fuzzy_replace(&text, old, new) {
                Some(updated) => match fs::write(&p, updated) {
                    Ok(()) => Outcome { files_changed: true, ..ok(format!("Edited {path} (matched ignoring indentation).")) },
                    Err(e) => fail(format!("Can't write {path}: {e}")),
                },
                None => fail(format!("old_text wasn't found in {path}. Here is the current file; copy the text exactly from it:\n{}",
                                     truncate(&text, 6000))),
            },
            1 => match fs::write(&p, text.replacen(old, new, 1)) {
                Ok(()) => Outcome { files_changed: true, ..ok(format!("Edited {path}.")) },
                Err(e) => fail(format!("Can't write {path}: {e}")),
            },
            n => fail(format!("old_text appears {n} times in {path}; include more surrounding lines so it is unique.")),
        }
    }

    fn new_rust_node(&self, name: &str, base: &str) -> Outcome {
        let class: String = name.split(|c: char| !c.is_ascii_alphanumeric()).filter(|w| !w.is_empty())
            .map(|w| { let mut c = w.chars(); c.next().map(|f| f.to_ascii_uppercase().to_string() + c.as_str()).unwrap_or_default() })
            .collect();
        if class.is_empty() || !class.chars().next().unwrap().is_ascii_alphabetic() {
            return fail(format!("'{name}' isn't a valid class name. Use something like Enemy or PowerUp."));
        }
        if !base.chars().all(|c| c.is_ascii_alphanumeric()) || base.is_empty() {
            return fail(format!("'{base}' isn't a Godot class name."));
        }
        let mut module = String::new();
        for (i, ch) in class.chars().enumerate() {
            if ch.is_ascii_uppercase() && i > 0 { module.push('_'); }
            module.push(ch.to_ascii_lowercase());
        }
        let file = self.root.join("rust/src").join(format!("{module}.rs"));
        let lib = self.root.join("rust/src/lib.rs");
        if file.exists() { return fail(format!("rust/src/{module}.rs already exists.")); }
        let Ok(lib_text) = fs::read_to_string(&lib) else { return fail("rust/src/lib.rs is missing. Is this a Rust project?") };

        let code = format!(r#"use godot::classes::{{I{base}, {base}}};
use godot::prelude::*;

/// {class}: describe what this node does here!
#[derive(GodotClass)]
#[class(base = {base})]
pub struct {class} {{
    base: Base<{base}>,
}}

#[godot_api]
impl I{base} for {class} {{
    fn init(base: Base<{base}>) -> Self {{
        Self {{ base }}
    }}

    fn ready(&mut self) {{
        // Runs once, when this node enters the scene.
    }}

    fn process(&mut self, delta: f64) {{
        // Runs every frame. `delta` is the time since the last frame, in seconds.
        let _ = delta;
    }}
}}
"#);
        if let Err(e) = fs::write(&file, code) { return fail(format!("Can't create the file: {e}")); }
        let mut lines: Vec<String> = lib_text.lines().map(String::from).collect();
        let after = lines.iter().rposition(|l| l.starts_with("mod ") || l.starts_with("pub mod "))
            .or_else(|| lines.iter().position(|l| l.contains("use godot::prelude")))
            .map(|i| i + 1).unwrap_or(0);
        lines.insert(after, format!("mod {module};"));
        let _ = fs::write(&lib, lines.join("\n") + "\n");
        Outcome { files_changed: true, ..ok(format!(
            "Created rust/src/{module}.rs with class {class} (base {base}) and added `mod {module};` to lib.rs. Edit it, then build_rust.")) }
    }

    pub fn build_rust(&self) -> Outcome {
        // Missing `use` lines for Godot types are the most common small-model mistake, and purely
        // mechanical: fix them here (up to twice) instead of spending the user's time on it.
        let mut fixed: Vec<String> = vec![];
        for _ in 0..2 {
            let o = self.build_once();
            if o.rust_built { return with_fixes(o, &fixed); }
            let more = self.fix_imports(&o.raw);
            if more.is_empty() { return with_fixes(self.add_hints(o), &fixed); }
            fixed.extend(more);
        }
        let o = self.build_once();
        with_fixes(if o.rust_built { o } else { self.add_hints(o) }, &fixed)
    }

    fn add_hints(&self, mut o: Outcome) -> Outcome {
        let mut hints = self.method_hints(&o.raw);
        hints.extend(godot_rust_hints(&o.raw));
        hints.extend(error_explanations(&o.raw));
        if !hints.is_empty() { o.content += &format!("\nHints:\n- {}", hints.join("\n- ")); }
        o
    }

    /// For "no method named X" errors, look up what Godot actually offers on that class (and its parents).
    fn method_hints(&self, raw: &str) -> Vec<String> {
        let Ok(api) = self.api() else { return vec![] };
        let classes = api["classes"].as_array().cloned().unwrap_or_default();
        let class = |n: &str| classes.iter().find(|c| c["name"].as_str() == Some(n));
        let methods_of = |n: &str| -> Vec<String> {
            let mut out = vec![];
            let mut cur = Some(n.to_string());
            while let Some(c) = cur.and_then(|n| class(&n)) {
                out.extend(c["methods"].as_array().into_iter().flatten().filter_map(|m| m["name"].as_str().map(String::from)));
                cur = c["inherits"].as_str().map(String::from);
            }
            out
        };
        const SYN: [(&str, &str); 6] = [("opacity", "modulate"), ("alpha", "modulate"), ("color", "modulate"),
                                        ("transparency", "modulate"), ("size", "scale"), ("angle", "rotation")];
        let words = |m: &str| -> Vec<String> {
            let mut w: Vec<String> = m.split('_').filter(|t| !["get", "set", "is", "to", ""].contains(t)).map(String::from).collect();
            for (a, b) in SYN { if w.iter().any(|x| x == a) { w.push(b.to_string()) } }
            w
        };
        let mut hints = vec![];
        for line in raw.lines().filter(|l| l.starts_with("error[E0599]: no method named")) {
            let t: Vec<&str> = line.split('`').skip(1).step_by(2).collect();
            let (Some(method), Some(ty)) = (t.first(), t.get(1)) else { continue };
            // Gd<Input> -> Input; BaseMut<'_, Player> -> the Rust class's Godot base
            let inner = ty.split('<').nth(1).unwrap_or("").trim_end_matches('>').rsplit(", ").next().unwrap_or("").trim();
            if inner.is_empty() { continue } // a builtin like NodePath/Vector2, not a Godot class
            let godot_class = if class(inner).is_some() { inner.to_string() } else { self.rust_base_of(inner).unwrap_or_default() };
            if godot_class.is_empty() { continue }
            let own = methods_of(&godot_class);
            let w = words(method);
            let mut similar: Vec<&String> = own.iter().filter(|m| words(m).iter().any(|x| w.contains(x))).collect();
            similar.sort(); similar.dedup(); similar.truncate(8);
            let elsewhere: Vec<&str> = classes.iter().filter(|c| c["methods"].as_array().into_iter().flatten()
                .any(|m| m["name"].as_str() == Some(method))).filter_map(|c| c["name"].as_str()).take(4).collect();
            let mut h = format!("`{method}` doesn't exist on {godot_class} (or its parent classes).");
            if !similar.is_empty() { h += &format!(" Real {godot_class} methods that look related: {}.", similar.iter().map(|s| s.as_str()).collect::<Vec<_>>().join(", ")); }
            if !elsewhere.is_empty() { h += &format!(" A method with that exact name exists on: {}.", elsewhere.join(", ")); }
            h += &format!(" Use class_info(\"{godot_class}\") to see everything.");
            if !hints.contains(&h) { hints.push(h) }
        }
        hints
    }

    /// `pub struct Player` with `#[class(base = Node2D)]` -> "Node2D"
    fn rust_base_of(&self, rust_class: &str) -> Option<String> {
        let dir = self.root.join("rust/src");
        for e in fs::read_dir(dir).ok()?.flatten() {
            let Ok(src) = fs::read_to_string(e.path()) else { continue };
            if rust_class.is_empty() { return None }
            let Some(at) = src.find(&format!("pub struct {rust_class} ")).or_else(|| src.find(&format!("struct {rust_class} "))) else { continue };
            let before = &src[..at];
            let attr = before.rfind("#[class(")?;
            let base = before[attr..].split("base").nth(1)?.trim_start_matches([' ', '=']).split([',', ')']).next()?.trim().to_string();
            return Some(base);
        }
        None
    }

    /// Add/repair `use` lines for Godot classes, class traits (IFoo) and global enums (Key...) rustc says are missing.
    fn fix_imports(&self, raw: &str) -> Vec<String> {
        let Ok(api) = self.api() else { return vec![] };
        let classes: std::collections::HashSet<String> = api["classes"].as_array().into_iter().flatten()
            .filter_map(|c| c["name"].as_str().map(String::from)).collect();
        let enums: std::collections::HashSet<String> = api["global_enums"].as_array().into_iter().flatten()
            .filter_map(|c| c["name"].as_str().map(String::from)).filter(|n| !n.contains('.')).collect();
        let path_for = |name: &str| -> Option<String> {
            if enums.contains(name) { return Some(format!("godot::global::{name}")); }
            if classes.contains(name) { return Some(format!("godot::classes::{name}")); }
            if name.len() > 1 && name.starts_with('I') && classes.contains(&name[1..]) { return Some(format!("godot::classes::{name}")); }
            None
        };
        let mut fixes = vec![];
        let lines: Vec<&str> = raw.lines().collect();
        for (i, line) in lines.iter().enumerate() {
            let Some(rest) = line.strip_prefix("error") else { continue };
            let ticked: Vec<&str> = rest.split('`').skip(1).step_by(2).collect();
            let Some(file) = lines[i + 1..].iter().take(4).find_map(|l| l.trim_start().strip_prefix("--> "))
                .and_then(|l| l.split(':').next()) else { continue };
            let path = self.root.join("rust").join(file);
            let Ok(src) = fs::read_to_string(&path) else { continue };
            let new_src = if rest.contains("unresolved import") {
                // e.g. `godot::classes::Key` -> `godot::global::Key`
                let Some(bad) = ticked.first() else { continue };
                let name = bad.rsplit("::").next().unwrap_or("");
                match path_for(name) {
                    Some(good) if bad.starts_with("godot::") && good != *bad => {
                        if src.contains(bad) { src.replace(bad, &good) } else {
                            // Grouped: `use godot::classes::{Input, Key};` -> drop it from the group, import it on its own.
                            let module = &bad[..bad.len() - name.len() - 2];
                            let mut done = false;
                            let mut out: Vec<String> = src.lines().map(|l| {
                                let t = l.trim();
                                if !done && t.starts_with(&format!("use {module}::{{")) {
                                    let inner = t.trim_start_matches(&format!("use {module}::{{")).trim_end_matches("};");
                                    let kept: Vec<&str> = inner.split(',').map(str::trim).filter(|x| !x.is_empty() && *x != name).collect();
                                    if kept.len() < inner.split(',').filter(|x| !x.trim().is_empty()).count() {
                                        done = true;
                                        return format!("use {module}::{{{}}};\nuse {good};", kept.join(", "));
                                    }
                                }
                                l.to_string()
                            }).collect();
                            if !done { continue }
                            out.push(String::new());
                            out.join("\n")
                        }
                    }
                    _ => continue,
                }
            } else if rest.contains("cannot find") || rest.contains("undeclared type") {
                let Some(name) = ticked.first() else { continue };
                let Some(good) = path_for(name) else { continue };
                let use_line = format!("use {good};");
                if src.contains(&use_line) { continue }
                let mut out: Vec<&str> = src.lines().collect();
                let at = out.iter().rposition(|l| l.starts_with("use ")).map(|p| p + 1).unwrap_or(0);
                out.insert(at, &use_line);
                out.join("\n") + "\n"
            } else { continue };
            if new_src != src && fs::write(&path, &new_src).is_ok() {
                fixes.push(format!("rust/{file}: {}", if rest.contains("unresolved import") {
                    format!("corrected the import of `{}`", ticked[0].rsplit("::").next().unwrap_or("")) } else {
                    format!("added `use {};`", path_for(ticked[0]).unwrap_or_default()) }));
            }
        }
        fixes.dedup();
        fixes
    }

    fn build_once(&self) -> Outcome {
        let manifest = self.root.join("rust/Cargo.toml");
        if !manifest.exists() { return fail("This project has no Rust code (rust/Cargo.toml is missing)."); }
        let out = Command::new(cargo_path())
            .args(["build", "--color=never", "--manifest-path"]).arg(&manifest)
            .stdin(Stdio::null()).output();
        let out = match out {
            Ok(o) => o,
            Err(e) => return fail(format!("Couldn't run cargo ({e}). Is Rust installed? See https://rustup.rs")),
        };
        let text = String::from_utf8_lossy(&out.stderr).to_string() + &String::from_utf8_lossy(&out.stdout);
        let detail = diagnostics(&text, !out.status.success());
        let mut o = if out.status.success() {
            ok(if detail.is_empty() { "Build succeeded.".to_string() } else { format!("Build succeeded with warnings:\n{detail}") })
        } else {
            fail(format!("Build FAILED. Fix these errors, then build again:\n{detail}"))
        };
        o.rust_built = out.status.success();
        o.raw = text;
        if o.rust_built && self.install_gdextension() {
            o.files_changed = true;
        }
        o
    }

    /// New projects keep their .gdextension in rust/gdextension.template until the library exists.
    fn install_gdextension(&self) -> bool {
        let template = self.root.join("rust/gdextension.template");
        let Ok(toml) = fs::read_to_string(self.root.join("rust/Cargo.toml")) else { return false };
        let Some(name) = toml.lines().find(|l| l.trim_start().starts_with("name"))
            .and_then(|l| l.split('"').nth(1)).map(|n| n.replace('-', "_")) else { return false };
        let target = self.root.join(format!("{name}.gdextension"));
        let mut installed = false;
        if !target.exists() && template.exists() {
            installed = fs::copy(&template, &target).is_ok();
        }
        // The starter scene also waits for the first build (it uses the Rust classes).
        let scene = self.root.join("main.tscn");
        let scene_template = self.root.join("rust/main.tscn.template");
        if scene_template.exists() {
            if !scene.exists() && fs::copy(&scene_template, &scene).is_ok() {
                installed = true;
                // Make it the scene that runs on Play, now that it exists.
                let settings_path = self.root.join("project.godot");
                if let Ok(settings) = fs::read_to_string(&settings_path) {
                    if !settings.contains("run/main_scene") {
                        let line = "run/main_scene=\"res://main.tscn\"\n";
                        let updated = if settings.contains("[application]\n") {
                            settings.replacen("[application]\n", &format!("[application]\n\n{line}"), 1)
                        } else {
                            format!("{settings}\n[application]\n\n{line}")
                        };
                        let _ = fs::write(&settings_path, updated);
                    }
                }
            }
            let _ = fs::remove_file(&scene_template);
        }
        installed
    }

    fn run_game(&self, seconds: f64) -> Outcome {
        let build = self.build_rust();
        if !build.ok { return build; }
        let Some(engine) = &self.engine else { return fail("The engine path is unknown, so the game can't be run from here.") };
        // A project that was never opened in the editor has no import cache, and without its
        // extension list the engine won't load the Rust library. Import it once, headless.
        let ext_list = fs::read_to_string(self.root.join(".godot/extension_list.cfg")).unwrap_or_default();
        if !ext_list.contains(".gdextension") {
            // The import can hang on some projects; never let it block the conversation.
            if let Ok(mut c) = Command::new(engine).arg("--path").arg(&self.root).args(["--headless", "--import"])
                .stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null()).spawn() {
                let t = Instant::now();
                while matches!(c.try_wait(), Ok(None)) {
                    if t.elapsed() > Duration::from_secs(120) { let _ = c.kill(); break; }
                    std::thread::sleep(Duration::from_millis(200));
                }
                let _ = c.wait();
            }
        }
        let frames = (seconds.clamp(1.0, 30.0) * 60.0) as u32;
        let child = Command::new(engine)
            .arg("--path").arg(&self.root)
            .args(["--headless", "--fixed-fps", "60", "--quit-after"]).arg(frames.to_string())
            .stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn();
        let mut child = match child { Ok(c) => c, Err(e) => return fail(format!("Couldn't start the game: {e}")) };
        let mut stdout = child.stdout.take().unwrap();
        let mut stderr = child.stderr.take().unwrap();
        let t_out = std::thread::spawn(move || { let mut s = String::new(); let _ = stdout.read_to_string(&mut s); s });
        let t_err = std::thread::spawn(move || { let mut s = String::new(); let _ = stderr.read_to_string(&mut s); s });
        let start = Instant::now();
        let mut timed_out = false;
        loop {
            match child.try_wait() {
                Ok(Some(_)) => break,
                Ok(None) if start.elapsed() > Duration::from_secs(90) => { let _ = child.kill(); timed_out = true; break; }
                Ok(None) => std::thread::sleep(Duration::from_millis(100)),
                Err(_) => break,
            }
        }
        let status = child.wait().ok();
        let out = t_out.join().unwrap_or_default();
        let err = t_err.join().unwrap_or_default();
        let log: Vec<&str> = out.lines().chain(err.lines())
            .filter(|l| !l.trim().is_empty() && !l.starts_with("RusticEngine v") && !l.starts_with("Initialize godot-rust"))
            .collect();
        // Shutdown bookkeeping from the headless run (e.g. audio still loaded when time ran out) isn't the game's fault.
        let mut log: Vec<&str> = log;
        let mut i = 0;
        while i < log.len() {
            let l = log[i];
            if l.contains("instances were leaked at exit") || l.contains("resources still in use at exit") {
                log.remove(i);
                if i < log.len() && log[i].trim_start().starts_with("at: ") { log.remove(i); }
            } else {
                i += 1;
            }
        }
        let has_errors = log.iter().any(|l| l.contains("ERROR") || l.contains("panicked") || l.contains("SCRIPT ERROR"));
        let crashed = status.map(|s| !s.success()).unwrap_or(true);
        let mut report = format!("Simulated {seconds:.0} s of game time. ");
        report += if timed_out { "The game froze and was stopped.\n" } else if crashed { "The game exited with an error.\n" }
                  else if has_errors { "It ran, but reported errors.\n" } else { "It ran without errors.\n" };
        report += if log.is_empty() { "(The game printed nothing.)".to_string() } else { format!("Game output:\n{}", truncate(&log.join("\n"), MAX_RESULT)) }.as_str();
        Outcome { ok: !(timed_out || crashed || has_errors), content: report, files_changed: false, rust_built: true, raw: String::new() }
    }

    fn api(&self) -> Result<Value, String> {
        let path = self.cache_dir.join("extension_api.json");
        if !path.exists() {
            let engine = self.engine.as_ref().ok_or("The engine path is unknown, so classes can't be looked up.")?;
            let _ = fs::create_dir_all(&self.cache_dir);
            Command::new(engine).args(["--headless", "--dump-extension-api"]).current_dir(&self.cache_dir)
                .stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null()).status()
                .map_err(|e| format!("Couldn't ask the engine for its class list: {e}"))?;
        }
        let text = fs::read_to_string(&path).map_err(|e| format!("Class list unavailable: {e}"))?;
        serde_json::from_str(&text).map_err(|e| e.to_string())
    }

    fn class_info(&self, class: &str, filter: &str) -> Outcome {
        let api = match self.api() { Ok(a) => a, Err(e) => return fail(e) };
        let classes = api["classes"].as_array().cloned().unwrap_or_default();
        let find = |n: &str| classes.iter().find(|c| c["name"].as_str().map(|s| s.eq_ignore_ascii_case(n)).unwrap_or(false)).cloned();
        let Some(c) = find(class) else {
            let close: Vec<&str> = classes.iter().filter_map(|c| c["name"].as_str())
                .filter(|n| n.to_lowercase().contains(&class.to_lowercase())).take(10).collect();
            return fail(format!("No class named {class}. Similar: {}", close.join(", ")));
        };
        let f = filter.to_lowercase();
        let keep = |n: &str| f.is_empty() || n.to_lowercase().contains(&f);
        let mut chain = vec![c["name"].as_str().unwrap_or("").to_string()];
        let mut parent = c["inherits"].as_str().map(String::from);
        while let Some(p) = parent {
            chain.push(p.clone());
            parent = find(&p).and_then(|pc| pc["inherits"].as_str().map(String::from));
        }
        let mut out = format!("{}\n", chain.join(" -> "));
        let ty = |v: &Value| v["type"].as_str().unwrap_or("?").replace("typedarray::", "Array[").to_string();
        if let Some(methods) = c["methods"].as_array() {
            let lines: Vec<String> = methods.iter().filter(|m| !m["is_virtual"].as_bool().unwrap_or(false))
                .filter(|m| keep(m["name"].as_str().unwrap_or("")))
                .map(|m| {
                    let args: Vec<String> = m["arguments"].as_array().map(|a| a.iter()
                        .map(|x| format!("{}: {}", x["name"].as_str().unwrap_or(""), ty(x))).collect()).unwrap_or_default();
                    let ret = m["return_value"].get("type").map(|_| format!(" -> {}", ty(&m["return_value"]))).unwrap_or_default();
                    format!("  {}({}){}", m["name"].as_str().unwrap_or(""), args.join(", "), ret)
                }).collect();
            if !lines.is_empty() { out += &format!("methods:\n{}\n", lines.join("\n")); }
        }
        if let Some(props) = c["properties"].as_array() {
            let lines: Vec<String> = props.iter().filter(|p| keep(p["name"].as_str().unwrap_or("")))
                .map(|p| format!("  {}: {} (get_{} / set_{})", p["name"].as_str().unwrap_or(""), ty(p),
                                 p["name"].as_str().unwrap_or(""), p["name"].as_str().unwrap_or(""))).collect();
            if !lines.is_empty() { out += &format!("properties:\n{}\n", lines.join("\n")); }
        }
        if let Some(sigs) = c["signals"].as_array() {
            let lines: Vec<String> = sigs.iter().filter(|s| keep(s["name"].as_str().unwrap_or("")))
                .map(|s| {
                    let args: Vec<String> = s["arguments"].as_array().map(|a| a.iter()
                        .map(|x| format!("{}: {}", x["name"].as_str().unwrap_or(""), ty(x))).collect()).unwrap_or_default();
                    format!("  {}({})  -> self.signals().{}()", s["name"].as_str().unwrap_or(""), args.join(", "), s["name"].as_str().unwrap_or(""))
                }).collect();
            if !lines.is_empty() { out += &format!("signals:\n{}\n", lines.join("\n")); }
        }
        if chain.len() > 1 && f.is_empty() {
            out += &format!("(Inherited members from {} also work.)\n", chain[1..].join(", "));
        }
        ok(truncate(&out, MAX_RESULT))
    }
}

/// Keep rustc's diagnostic blocks (message, location, code excerpt, `help:`/`note:` hints), drop progress noise.
/// When the build failed, warnings are dropped so the errors get the space.
fn diagnostics(text: &str, failed: bool) -> String {
    let mut blocks: Vec<String> = vec![];
    let mut cur: Option<String> = None;
    for line in text.lines() {
        let t = line.trim_start();
        let starts_block = line.starts_with("error") || line.starts_with("warning");
        if starts_block {
            if let Some(b) = cur.take() { blocks.push(b); }
            let summary = line.contains("generated") && line.contains("warning") || line.starts_with("error: could not compile");
            if !summary { cur = Some(line.to_string()); }
        } else if t.starts_with("Compiling") || t.starts_with("Finished") || t.starts_with("Checking") || t.starts_with("Updating")
            || t.starts_with("Downloaded") || t.starts_with("Downloading") || t.starts_with("Locking") || t.starts_with("Adding") {
            if let Some(b) = cur.take() { blocks.push(b); }
        } else if let Some(b) = cur.as_mut() {
            b.push('\n');
            b.push_str(line);
        }
    }
    if let Some(b) = cur.take() { blocks.push(b); }
    let keep: Vec<String> = blocks.into_iter()
        .filter(|b| !failed || b.starts_with("error"))
        .map(|b| b.trim_end().to_string()).collect();
    let mut out = String::new();
    for b in keep {
        if out.len() + b.len() > MAX_RESULT { out.push_str("\n...(more diagnostics trimmed; fix these first)"); break; }
        out.push_str(&b);
        out.push_str("\n\n");
    }
    out.trim_end().to_string()
}

/// Replace `old` in `text` when it only differs by indentation/trailing spaces, if the match is unique.
fn fuzzy_replace(text: &str, old: &str, new: &str) -> Option<String> {
    let norm = |s: &str| s.trim().to_string();
    let old_lines: Vec<String> = old.lines().map(norm).filter(|l| !l.is_empty()).collect();
    if old_lines.is_empty() { return None; }
    let lines: Vec<&str> = text.lines().collect();
    let mut found = None;
    let mut i = 0;
    while i < lines.len() {
        // match old_lines against lines starting at i, skipping blank lines in the file
        let (mut j, mut k) = (i, 0);
        while j < lines.len() && k < old_lines.len() {
            if lines[j].trim().is_empty() { j += 1; continue; }
            if norm(lines[j]) != old_lines[k] { break; }
            j += 1; k += 1;
        }
        if k == old_lines.len() && !lines[i].trim().is_empty() {
            if found.is_some() { return None; } // ambiguous
            found = Some((i, j));
        }
        i += 1;
    }
    let (start, end) = found?;
    // Re-indent the replacement to the indentation of the first matched line.
    let indent: String = lines[start].chars().take_while(|c| c.is_whitespace()).collect();
    let new_indent: String = new.lines().find(|l| !l.trim().is_empty())
        .map(|l| l.chars().take_while(|c| c.is_whitespace()).collect()).unwrap_or_default();
    let replaced: Vec<String> = new.lines().map(|l| {
        if l.trim().is_empty() { String::new() }
        else { format!("{indent}{}", l.strip_prefix(new_indent.as_str()).unwrap_or(l.trim_start())) }
    }).collect();
    let mut out: Vec<String> = lines[..start].iter().map(|s| s.to_string()).collect();
    out.extend(replaced);
    out.extend(lines[end..].iter().map(|s| s.to_string()));
    Some(out.join("\n") + if text.ends_with('\n') { "\n" } else { "" })
}

fn cargo_path() -> PathBuf {
    if let Ok(c) = std::env::var("CARGO") { return c.into(); }
    let home = std::env::var("HOME").or_else(|_| std::env::var("USERPROFILE")).unwrap_or_default();
    let rustup = Path::new(&home).join(".cargo/bin/cargo");
    if rustup.exists() { rustup } else { "cargo".into() }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fuzzy_matches_different_indentation() {
        let text = "fn a() {\n    let x = 1;\n    let y = 2;\n}\n";
        let out = fuzzy_replace(text, "let x = 1;\nlet y = 2;", "let x = 10;\nlet y = 20;").unwrap();
        assert_eq!(out, "fn a() {\n    let x = 10;\n    let y = 20;\n}\n");
    }

    #[test]
    fn fuzzy_refuses_ambiguous() {
        let text = "a\n  b\nc\n  b\n";
        assert!(fuzzy_replace(text, "b", "z").is_none());
    }

    #[test]
    fn fuzzy_keeps_relative_indent() {
        let text = "impl X {\n    fn f() {\n        old();\n    }\n}\n";
        let out = fuzzy_replace(text, "fn f() {\n    old();\n}", "fn f() {\n    new();\n    more();\n}").unwrap();
        assert_eq!(out, "impl X {\n    fn f() {\n        new();\n        more();\n    }\n}\n");
    }

    #[test]
    fn diagnostics_keep_help_and_drop_noise() {
        let log = "   Compiling game v0.1.0\nerror[E0599]: no method named `rotation` found\n  --> src/player.rs:29:25\n   |\n29 |  self.base_mut().rotation(1.0);\n   |                  ^^^^^^^^\nhelp: there is a method `rotate` with a similar name\n\nwarning: unused variable\n --> src/a.rs:1:1\n\nerror: could not compile `game`\n";
        let d = diagnostics(log, true);
        assert!(d.contains("help: there is a method `rotate`"));
        assert!(d.contains("src/player.rs:29:25"));
        assert!(!d.contains("Compiling"));
        assert!(!d.contains("unused variable"));
        assert!(!d.contains("could not compile"));
    }
}

/// Static checks for a .tscn: every SubResource/ExtResource used is declared, every parent path exists.
pub fn scene_problems(text: &str) -> Vec<String> {
    fn attr<'a>(line: &'a str, key: &str) -> Option<&'a str> {
        let i = line.find(&format!("{key}=\""))? + key.len() + 2;
        line[i..].split('"').next()
    }
    fn refs(text: &str, kind: &str) -> Vec<String> {
        let pat = format!("{kind}(");
        text.match_indices(&pat).filter_map(|(i, _)| {
            let rest = &text[i + pat.len()..];
            Some(rest[..rest.find(')')?].trim().trim_matches('"').to_string())
        }).collect()
    }
    let (mut subs, mut exts, mut nodes) = (vec![], vec![], vec![]);
    let mut problems = vec![];
    let mut has_root = false;
    for line in text.lines().map(str::trim) {
        if line.starts_with("[sub_resource") { if let Some(id) = attr(line, "id") { subs.push(id.to_string()) } }
        if line.starts_with("[ext_resource") { if let Some(id) = attr(line, "id") { exts.push(id.to_string()) } }
        if line.starts_with("[node") {
            let name = attr(line, "name").unwrap_or("").to_string();
            match attr(line, "parent") {
                None => { if has_root { problems.push(format!("node \"{name}\" has no parent=, but the scene already has a root node")) } has_root = true; }
                Some(".") => nodes.push(name),
                Some(p) => {
                    if !nodes.iter().any(|n| n == p) { problems.push(format!("node \"{name}\" has parent=\"{p}\", but no node is at that path (paths are relative to the root, e.g. \".\" or \"Player\")")) }
                    nodes.push(format!("{p}/{name}"));
                }
            }
        }
    }
    for id in refs(text, "SubResource") {
        if !subs.contains(&id) { problems.push(format!("SubResource(\"{id}\") is used but there is no [sub_resource ... id=\"{id}\"] above it")) }
    }
    for id in refs(text, "ExtResource") {
        if !exts.contains(&id) { problems.push(format!("ExtResource(\"{id}\") is used but there is no [ext_resource ... id=\"{id}\"]")) }
    }
    problems.dedup();
    problems
}
