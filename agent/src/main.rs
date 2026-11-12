//! rustic-agent: Ember, the AI guide behind RusticEngine's AI Guide dock.
//!
//! The editor starts this program and talks to it with JSON lines.
//!   editor -> agent: {"type":"config", "provider", "base_url", "model", "api_key", "context", "mode", "vision_model"}
//!                    {"type":"user", "text", "context"}  {"type":"reset"}  {"type":"stop"}
//!   agent -> editor: {"type":"ready"} {"type":"text","delta"} {"type":"tool_start","name","summary"}
//!                    {"type":"tool_end","name","ok","summary"} {"type":"files_changed","path"}
//!                    {"type":"rust_built"} {"type":"mode","mode"} {"type":"done"} {"type":"error","message"}
//!
//! Also usable from a terminal for testing:
//!   rustic-agent --project DIR --engine PATH --provider ollama --model qwen2.5-coder:7b --ask "make the player jump"
//!   rustic-agent --mcp --project DIR    (MCP server over stdio for Claude Code, Codex and other agents)
mod assets;
mod design;
mod examples;
mod paths;
mod llm;
mod mcp;
mod mechanic_kinds;
mod mechanics;
mod studio;
mod tools;

use std::io::{BufRead, Write};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex, mpsc};

use serde_json::{Value, json};

use llm::{Config, Msg};

const SYSTEM_PROMPT: &str = include_str!("../prompt/ember.md");
const MODE_LEARNING: &str = include_str!("../prompt/mode_learning.md");
const MODE_AUTONOMOUS: &str = include_str!("../prompt/mode_autonomous.md");
const DEFAULT_VISION_MODEL: &str = "qwen3-vl:8b";
const MAX_STEPS: usize = 30;
/// Rough history budget in characters (~4 chars per token), leaving room for the system prompt and reply.
const HISTORY_BUDGET_CHARS: usize = 48_000;

static OUT: Mutex<()> = Mutex::new(());

pub(crate) fn emit(v: Value) {
    let _guard = OUT.lock().unwrap();
    let mut out = std::io::stdout().lock();
    let _ = writeln!(out, "{v}");
    let _ = out.flush();
}

fn arg(args: &[String], name: &str) -> Option<String> {
    args.iter().position(|a| a == name).and_then(|i| args.get(i + 1).cloned())
}

fn msg_len(m: &Msg) -> usize {
    match m {
        Msg::User(t) => t.len(),
        Msg::Assistant { text, calls } => text.len() + calls.iter().map(|c| c.args.to_string().len()).sum::<usize>(),
        Msg::Tool { content, .. } => content.len(),
    }
}

/// A mechanic's logic files (every .rs in its src/ except mod.rs and tuning.rs), to tell whether the
/// starting code was actually changed.
fn logic_snapshot(src: &std::path::Path) -> Vec<(String, String)> {
    let mut v: Vec<(String, String)> = std::fs::read_dir(src).into_iter().flatten().flatten()
        .filter_map(|e| {
            let name = e.file_name().to_string_lossy().to_string();
            (name.ends_with(".rs") && name != "mod.rs" && name != "tuning.rs")
                .then(|| (name, std::fs::read_to_string(e.path()).unwrap_or_default()))
        }).collect();
    v.sort();
    v
}

/// The key a request names for an ability: "pressing Shift", "on Q", "with the F key".
fn named_key(text: &str) -> Option<String> {
    let t = format!(" {} ", text.to_lowercase().replace(|c: char| !c.is_alphanumeric(), " "));
    for k in ["shift", "ctrl", "control", "alt", "space", "tab"] {
        if t.contains(&format!(" {k} ")) && mechanic_kinds::key_const(k).is_some() {
            return Some(k.to_string());
        }
    }
    // Single letters only right after a cue word ("press q", "the f key"), never on their own.
    for cue in ["press ", "pressing ", "hit ", "hold ", "on ", "the "] {
        for (i, _) in t.match_indices(cue) {
            let rest = &t[i + cue.len()..];
            let word: String = rest.chars().take_while(|c| c.is_alphanumeric()).collect();
            let after = rest[word.len()..].trim_start();
            if word.len() == 1 && mechanic_kinds::key_const(&word).is_some() && (cue != "the " || after.starts_with("key")) {
                return Some(word);
            }
        }
    }
    None
}

/// Drop the oldest exchanges until the history fits. Always cut at a user message, so tool calls
/// and their results stay paired.
fn trim_history(history: &mut Vec<Msg>) {
    let budget = std::env::var("RUSTIC_AGENT_HISTORY_CHARS").ok().and_then(|s| s.parse().ok()).unwrap_or(HISTORY_BUDGET_CHARS);
    while history.iter().map(msg_len).sum::<usize>() > budget {
        let next_user = history.iter().skip(1).position(|m| matches!(m, Msg::User(_))).map(|i| i + 1);
        match next_user {
            Some(i) => { history.drain(..i); }
            None => {
                // One huge exchange: shrink the biggest tool results and runaway replies instead. Each message is
                // trimmed at most once (the marker), so this always ends: re-trimming a trimmed message looped forever.
                const MARK: &str = "\n...(trimmed to save memory)";
                let mut shrunk = false;
                for m in history.iter_mut() {
                    let (t, keep) = match m {
                        Msg::Tool { content, .. } => (content, 2000),
                        Msg::Assistant { text, .. } => (text, 4000),
                        Msg::User(_) => continue,
                    };
                    if t.len() > keep + MARK.len() && !t.ends_with(MARK) {
                        *t = format!("{}{MARK}", &t[..t.floor_char_boundary(keep)]);
                        shrunk = true;
                    }
                }
                if !shrunk { break; }
            }
        }
    }
}

/// Find `{"name": "<tool>", "arguments": {...}}` objects written in plain text (also inside
/// ```json fences or <tool_call> tags) and turn them into tool calls.
fn parse_text_calls(text: &str, defs: &[llm::ToolDef]) -> Vec<llm::ToolCall> {
    let mut calls = vec![];
    let mut i = 0;
    while let Some(off) = text[i..].find('{') {
        let start = i + off;
        let mut stream = serde_json::Deserializer::from_str(&text[start..]).into_iter::<Value>();
        match stream.next() {
            Some(Ok(v)) => {
                let consumed = stream.byte_offset();
                let name = v["name"].as_str().unwrap_or("");
                let args = if v.get("arguments").is_some() { v["arguments"].clone() } else { v["parameters"].clone() };
                if defs.iter().any(|d| d.name == name) && (args.is_object() || args.is_null()) {
                    let args = if args.is_null() { json!({}) } else { args };
                    calls.push(llm::ToolCall { id: format!("text_call_{}", calls.len()), name: name.to_string(), args });
                }
                i = start + consumed.max(1);
            }
            _ => i = start + 1,
        }
    }
    calls
}

/// Does this reply tell the user something was changed in their project?
fn claims_change(text: &str) -> bool {
    let t = text.to_lowercase().replace('\u{2019}', "'");
    const VERBS: [&str; 14] = ["added", "made", "changed", "updated", "created", "turned", "gave", "fixed", "set up", "written", "wrote",
        "built", "implemented", "coded"];
    let says_i = VERBS.iter().any(|v| t.contains(&format!("i {v} ")) || t.contains(&format!("i've {v} ")) || t.contains(&format!("i have {v} ")));
    const DONE: [&str; 5] = ["is now part of", "is now in the", "now lets the player", "is ready to try", "it's ready to try"];
    says_i || DONE.iter().any(|d| t.contains(d)) || t.contains("press **play**") || t.contains("press play")
}

/// "I've saved it to your journal" without a journal call.
const STUDIO_MODEL: &str = include_str!("../prompt/studio_model.md");
const STUDIO_SFX: &str = include_str!("../prompt/studio_sfx.md");
const STUDIO_PIXEL: &str = include_str!("../prompt/studio_pixel.md");
const STUDIO_MUSIC: &str = include_str!("../prompt/studio_music.md");
const STUDIO_SKY: &str = include_str!("../prompt/studio_sky.md");
const STUDIO_UI: &str = include_str!("../prompt/studio_ui.md");
const MECHANICS_CARD: &str = include_str!("../prompt/mechanics.md");

/// The exact Studio tools for what's open, so Ember names real keys instead of inventing menus.
fn studio_card(context: &str) -> Option<&'static str> {
    if context.contains("in the Studio's 3D modeler") {
        Some(STUDIO_MODEL.trim())
    } else if context.contains("in the Studio's Sound Effects maker") {
        Some(STUDIO_SFX.trim())
    } else if context.contains("in the Studio's Pixel Art painter") {
        Some(STUDIO_PIXEL.trim())
    } else if context.contains("in the Studio's Music maker") {
        Some(STUDIO_MUSIC.trim())
    } else if context.contains("in the Studio's Sky maker") {
        Some(STUDIO_SKY.trim())
    } else if context.contains("in the Studio's UI Kit maker") {
        Some(STUDIO_UI.trim())
    } else {
        None
    }
}

/// Tidy a Studio reply before showing it: the model sometimes leaks reasoning tags, narrates looking
/// again and again, or offers to change the art itself (it can't; the art is the creator's).
fn clean_studio_reply(text: &str) -> String {
    let mut t = text.to_string();
    while let (Some(a), Some(b)) = (t.find("<think>"), t.find("</think>")) {
        if b < a { break; }
        t.replace_range(a..b + 8, "");
    }
    let t = t.replace("</think>", "").replace("<think>", "").replace("<tools>", "").replace("</tools>", "");
    const DROP: &[&str] = &["let me look", "i'll look", "i look at", "let me check", "i'll check", "one moment", "just to be sure",
        "want me to", "should i do it", "shall i", "i'll change it", "i'll do it", "i can do it for you", "do it for you", "for you?",
        "change it for you", "tweak it for you", "let me look it up", "i'll make it", "let me change", "let me make",
        "i've made", "i made it", "i've changed", "i changed", "i've added", "i added", "i've set", "build successful", "let me build",
        "playtest", "(f5)", "look_at_image", "asset_info", "it looks great", "i'll make those changes", "i'll start by", "i'll change", "i'll add", "i'll set", "i'll make sure"];
    let mut seen = std::collections::HashMap::<String, usize>::new();
    let mut lines = vec![];
    for line in t.lines() {
        let mut kept = vec![];
        let mut rest = line;
        loop {
            // One sentence at a time (ends at ". ", "? " or "! "), so a single bad sentence doesn't take the line with it.
            let cut = rest.char_indices().find(|&(i, c)| matches!(c, '.' | '?' | '!') && rest[i + 1..].starts_with(' ')).map(|(i, _)| i + 1);
            let (sentence, next) = match cut { Some(i) => (&rest[..i], &rest[i + 1..]), None => (rest, "") };
            let low = sentence.trim().to_lowercase().replace('\u{2019}', "'");
            // Ember can show and explain, but never act on the art: drop "I'll ..." / "Let me ..." unless it's teaching.
            let acting = ["i'll ", "i will ", "let me ", "now i'll "].iter().any(|p| low.trim_start_matches(|c: char| !c.is_alphanumeric()).starts_with(p))
                && !["show", "explain", "walk", "help", "tell", "break it down", "go through"].iter().any(|w| low.contains(w));
            let bad = acting || DROP.iter().any(|d| low.contains(d));
            // Drop repeats (the model can loop on a phrase); short ones like "Done." may appear twice.
            let n = { let c = seen.entry(low.clone()).or_insert(0); *c += 1; *c };
            if !sentence.trim().is_empty() && !bad && (n == 1 || (low.len() < 12 && n <= 2)) {
                kept.push(sentence.trim());
            }
            if next.is_empty() { break; }
            rest = next;
        }
        let l = kept.join(" ");
        if !l.is_empty() || lines.last().map(|x: &String| !x.is_empty()).unwrap_or(false) {
            lines.push(if line.starts_with(char::is_whitespace) && !l.is_empty() { format!("  {l}") } else { l });
        }
    }
    lines.join("\n").trim().to_string()
}

/// The project-relative path of the model or sound open in the Studio, from the editor context.
fn studio_file(context: &str) -> Option<String> {
    let i = context.find("res://")?;
    let path: String = context[i + 6..].chars().take_while(|c| !c.is_whitespace() && *c != ':' && *c != ',' && *c != ')').collect();
    [".rmodel", ".rsfx", ".rpix", ".rmusic", ".rsky", ".rui"].iter().any(|e| path.ends_with(e)).then_some(path)
}

/// The mechanic the creator is looking at in the Mechanics tab, or one their message points to by folder.
fn mechanic_in_context(context: &str, text: &str) -> Option<String> {
    for src in [text, context] {
        if let Some(i) = src.find("res://mechanics/") {
            let id: String = src[i + 16..].chars().take_while(|c| c.is_ascii_alphanumeric() || *c == '_').collect();
            if !id.is_empty() {
                return Some(id);
            }
        }
    }
    None
}

/// "Make me a double jump", "add a dash": the creator wants something built (full tool loop).
fn wants_build(text: &str) -> bool {
    let t = text.to_lowercase();
    ["make me", "create", "build", "add a", "add an", "new mechanic", "write", "implement", "code a", "make a"].iter().any(|w| t.contains(w))
}

fn wants_explanation(text: &str) -> bool {
    let t = text.to_lowercase();
    ["explain", "how does", "how do", "how it works", "how is", "what does", "why", "understand", "teach", "walk me through"].iter().any(|w| t.contains(w))
}

fn claims_journal_save(text: &str) -> bool {
    let t = text.to_lowercase().replace('\u{2019}', "'");
    t.contains("design/journal/") || (t.contains("journal") && ["i've saved", "i saved", "saved it", "i've added", "i added", "i've noted", "i noted", "i've written", "i wrote"].iter().any(|v| t.contains(v)))
}

/// The reply ends on a promise to look something up ("Let me check...") instead of doing it.
/// "I'll start by creating the mechanic." / "First, I'll write the code." - a promise to build, not a build.
fn promises_action(text: &str) -> bool {
    let t = text.trim_end().to_lowercase().replace('\u{2019}', "'");
    if t.ends_with('?') {
        return false;
    }
    let body = t.trim_end_matches(['.', ':', '!', '\u{2026}']);
    let last = body.rsplit(['.', '\n']).next().unwrap_or(body).trim();
    let last = ["first, ", "now ", "next, ", "ok, ", "okay, ", "sure, ", "great, ", "then "].iter().fold(last, |s, p| s.strip_prefix(p).unwrap_or(s));
    let rest = ["let me ", "i'll ", "i will ", "i'm going to ", "i am going to "].iter().find_map(|p| last.strip_prefix(p));
    const DO: [&str; 12] = ["start", "create", "write", "make", "build", "add", "set up", "begin", "implement", "code", "put", "go ahead"];
    rest.is_some_and(|r| DO.iter().any(|v| r.starts_with(v)))
}

fn promises_lookup(text: &str) -> bool {
    let t = text.trim_end().to_lowercase().replace('\u{2019}', "'");
    let line = t.rsplit('\n').next().unwrap_or("").trim();
    if line.contains('?') || !(line.ends_with(':') || line.ends_with('.') || line.ends_with('\u{2026}')) {
        return false;
    }
    // The last sentence of the last line: "First, I'll look at the file." / "Let me check."
    let body = line.trim_end_matches(['.', ':', '\u{2026}']);
    let last = body.rsplit(". ").next().unwrap_or(body).trim();
    let last = ["first, ", "now ", "next, ", "ok, ", "okay, ", "sure, ", "great, "].iter()
        .fold(last, |s, p| s.strip_prefix(p).unwrap_or(s));
    if last.starts_with("one moment") {
        return true;
    }
    let rest = ["let me ", "i'll ", "i will "].iter().find_map(|p| last.strip_prefix(p));
    const LOOKUP: [&str; 11] = ["look", "check", "read", "open", "search", "find", "see ", "take a look", "pull up", "find out", "inspect"];
    rest.is_some_and(|r| LOOKUP.iter().any(|v| r.starts_with(v) || r.starts_with(&format!("quickly {v}")) || r.starts_with(&format!("first {v}"))))
}

struct Session {
    cfg: Config,
    project: tools::Project,
    history: Vec<Msg>,
    stop: Arc<AtomicBool>,
    /// "learning" or "autonomous".
    mode: String,
    vision_model: String,
}

impl Session {
    /// The base prompt, plus how this creator wants to work, plus what they've told us about their game.
    fn system_prompt(&self) -> String {
        let mode = if self.mode == "learning" { MODE_LEARNING } else { MODE_AUTONOMOUS };
        format!("{SYSTEM_PROMPT}\n{mode}\n# This project\n{}", assets::design_context(&self.project.root))
    }

    fn look_at_image(&self, args: &Value) -> tools::Outcome {
        let path = args["path"].as_str().unwrap_or("");
        let fail = |m: String| tools::Outcome { ok: false, content: m, files_changed: false, rust_built: false, raw: String::new() };
        let (mime, b64) = match self.project.image(path) { Ok(x) => x, Err(e) => return fail(e) };
        let q = args["question"].as_str().filter(|q| !q.trim().is_empty()).unwrap_or(
            "Describe this image for a game developer: what it shows, the art style, the main colors (as hex codes), \
             the mood, shapes and proportions, and anything that hints at gameplay or setting.");
        let q = format!("{q}\nDescribe only what you can actually see. Be concrete and brief (under 200 words).");
        match llm::describe_image(&self.cfg, &self.vision_model, mime, &b64, &q) {
            Ok(t) if !t.trim().is_empty() => tools::Outcome { ok: true, content: format!("What {path} shows:\n{t}"),
                files_changed: false, rust_built: false, raw: String::new() },
            Ok(_) => fail("The image model gave no answer.".into()),
            Err(e) => fail(e),
        }
    }

    fn handle_user(&mut self, text: &str, context: &str) {
        self.stop.store(false, Ordering::Relaxed);
        let mut studio_how: Vec<String> = vec![];
        let mut content = if context.is_empty() { text.to_string() } else { format!("{text}\n\n[Editor context: {context}]") };
        if let Some(card) = studio_card(context) {
            // Ground the advice in their real file: inspect what's open in the Studio up front.
            if let Some(rel) = studio_file(context) {
                if let Ok(info) = assets::info(&self.project.root.join(&rel), &rel) {
                    content += &format!("\n\n[What's open, from asset_info on {rel}: {info}]");
                }
            }
            content += &format!("\n\n[Studio reference: {card}]");
            let tool = if context.contains("Sound Effects maker") { "sound" } else if context.contains("Pixel Art painter") { "pixel" }
                else if context.contains("Music maker") { "music" } else if context.contains("Sky maker") { "sky" }
                else if context.contains("UI Kit maker") { "ui" } else { "model" };
            let how = studio::lookup(text, tool);
            studio_how = how.clone();
            if !how.is_empty() {
                content += &format!("\n\n[Verified Studio steps for this question. Teach these, in your own words, with the same keys and values; \
                                     add nothing that isn't here or in the reference:\n{}]", how.join("\n\n"));
            }
        }
        let mut mech_how: Vec<String> = vec![];
        let mechanic_id = mechanic_in_context(context, text);
        if let Some(id) = mechanic_id.clone() {
            // Ground answers in the real mechanic: its parts and values, and for explanations its ideas.
            content += &format!("\n\n[Mechanics reference: {}]", MECHANICS_CARD.trim());
            if let Ok(info) = mechanics::info(&self.project.root, &id) {
                content += &format!("\n\n[What's open, from mechanic info on {id}: {info}]\n[You already have this mechanic's parts, current tuning values and ideas above: answer from them directly. \
                                     Name tuning values exactly as written there (e.g. walk_speed). Only use tools for a file that isn't shown here.]");
            }
            mech_how = mechanics::tuning_matches(&self.project.root, &id, text);
            if !mech_how.is_empty() && !wants_build(text) {
                content += &format!("\n\n[Tuning values that match this question (name = current value: what it does). Suggest the right one by its exact name, \
                                     a number to try and why; the creator changes it in the Mechanics tab:\n{}]", mech_how.join("\n"));
            }
            if wants_explanation(text) {
                let ideas = mechanics::how_it_works(&self.project.root, &id, &["problem", "one frame", "why", "what is", "two ", "frame-rate", "camera rig", "signals", "data vs", "firm and"], 4500);
                if !ideas.is_empty() {
                    content += &format!("\n\n[More of HOW_IT_WORKS.md for {id}. Teach from it in your own words: the idea first, then one frame step by step, \
                                         then where it is in the code; finish with one predict-then-test question for the sandbox:\n{ideas}]");
                }
            }
        }
        self.history.push(Msg::User(content));
        let defs = tools::definitions();
        let mut rust_dirty = false;
        let mut auto_checks = 0;
        let mut changed_any = false;
        let mut claim_checked = false;
        // Studio and Mechanics questions get one round of tools, a buffered reply and a cleanup; requests
        // to build something keep the full tool loop.
        let in_mech = mechanic_id.is_some() && !wants_build(text);
        let in_studio = studio_card(context).is_some() || in_mech;
        let mut journal_saved = false;
        let mut promise_checked = false;
        // A new mechanic is only a skeleton until its src/ gets real logic.
        let mut scaffolded: Option<String> = None;
        let mut logic_written = false;
        let mut scaffold_snapshot: Vec<(String, String)> = vec![];
        let mut scaffold_nudges = 0u8;
        let mut mechanic_checked = false;
        // In the Studio the open file is already inspected above, so Ember gets one round of tools at most,
        // and its reply is held back and cleaned (no reasoning tags, no "let me look again", no offers to do the art).
        let no_tools: Vec<_> = vec![];
        let mut studio_text = String::new();

        for step in 0..MAX_STEPS {
            trim_history(&mut self.history);
            let mut held = String::new();
            let mut on_text = |d: &str| if in_studio { held.push_str(d) } else { emit(json!({"type": "text", "delta": d})) };
            let system = self.system_prompt();
            let round_defs = if in_studio && step > 0 { &no_tools } else { &defs };
            let turn = match llm::chat(&self.cfg, &system, &self.history, round_defs, &self.stop, &mut on_text) {
                Ok(t) => t,
                Err(e) => {
                    emit(json!({"type": "error", "message": e}));
                    // Keep the history valid: the user message stays, nothing half-written is added.
                    break;
                }
            };
            let mut turn = turn;
            if in_studio {
                studio_text = held;
            }
            if turn.calls.is_empty() {
                // Some local models write tool calls as JSON text instead of using the tool API.
                turn.calls = parse_text_calls(&turn.text, &defs);
            }
            let calls = turn.calls.clone();
            self.history.push(Msg::Assistant { text: turn.text, calls: turn.calls });
            if self.stop.load(Ordering::Relaxed) {
                break;
            }
            if calls.is_empty() {
                // Never let a turn end on code that doesn't compile.
                if rust_dirty && auto_checks < 3 {
                    auto_checks += 1;
                    emit(json!({"type": "tool_start", "name": "build_rust", "summary": "Checking that the code builds"}));
                    let b = self.project.build_rust();
                    emit(json!({"type": "tool_end", "name": "build_rust", "ok": b.ok, "summary": "Checking that the code builds"}));
                    if b.ok {
                        rust_dirty = false;
                        emit(json!({"type": "rust_built"}));
                    } else {
                        emit(json!({"type": "text", "delta": "\n\nHold on, the code doesn't build yet. Fixing it...\n\n"}));
                        self.history.push(Msg::User(format!(
                            "[Automatic check] You changed Rust code but it doesn't compile. Fix these errors (read the file first), \
                             build again, and only then tell me it's done.\n{}", b.content)));
                        rust_dirty = true;
                        continue;
                    }
                }
                if rust_dirty {
                    // Out of automatic fix attempts: never leave the user believing broken code works.
                    emit(json!({"type": "text", "delta": "\n\n**Heads up:** I couldn't get the code to build yet, so this change won't work as-is. \
                        Say \"keep trying\" and I'll have another go, or tell me what you'd like to do instead."}));
                    break;
                }
                // Small models sometimes describe a change they never made. Catch that once.
                let last = match self.history.last() { Some(Msg::Assistant { text, .. }) => text.clone(), _ => String::new() };
                if !journal_saved && !changed_any && !claim_checked && claims_journal_save(&last) {
                    emit(json!({"type": "guard", "name": "journal_claim"}));
                    claim_checked = true;
                    self.history.push(Msg::User(
                        "[Automatic check] Your reply says you saved this to the Concept Journal, but nothing was saved. \
                         Call the journal tool now (action \"add\", a short title, and their idea in their own words as text), \
                         then reply in one or two sentences.".into()));
                    continue;
                }
                if !promise_checked && promises_lookup(&last) {
                    emit(json!({"type": "guard", "name": "lookup_promise"}));
                    promise_checked = true;
                    self.history.push(Msg::User(
                        "[Automatic check] You said you'd look something up but didn't call a tool. Call it now \
                         (journal, game_path, game_design, find_example, read_file...), then answer.".into()));
                    continue;
                }
                if wants_build(text) && !changed_any && !promise_checked && promises_action(&last) {
                    emit(json!({"type": "guard", "name": "build_promise"}));
                    promise_checked = true;
                    self.history.push(Msg::User(
                        "[Automatic check] You said what you'll build but didn't build it. Do it now with the tools \
                         (for a new mechanic: `mechanic` action new, then edit_file its src/, then build_rust), and only then reply.".into()));
                    continue;
                }
                if let (Some(id), false, true) = (scaffolded.clone(), logic_written, scaffold_nudges < 2) {
                    emit(json!({"type": "guard", "name": "empty_mechanic"}));
                    scaffold_nudges += 1;
                    // Second time: name the exact next tool call (small models follow that more reliably).
                    let msg = if scaffold_nudges == 1 {
                        format!("[Automatic check] The {id} mechanic still only has the starting code from `mechanic` new: you haven't written \
                                 what makes it the mechanic they asked for. Read its node file in mechanics/{id}/src/, change the example block \
                                 with edit_file (put every new tunable number in tuning.rs as an #[export(range = ...)] field with a /// comment, \
                                 and in tuning.tres), build_rust, and only then say it's done.")
                    } else {
                        format!("[Automatic check] Still nothing written. Your next step is a tool call, not text: call read_file on the \
                                 node file listed in mechanics/{id}/src/ (not tuning.rs or mod.rs), then edit_file it.")
                    };
                    self.history.push(Msg::User(msg));
                    continue;
                }
                if let (Some(id), false) = (scaffolded.clone(), logic_written) {
                    // Out of nudges: never let the creator believe the starting example is their mechanic.
                    emit(json!({"type": "guard", "name": "template_left"}));
                    emit(json!({"type": "text", "delta": format!("\n\n**Heads up:** mechanics/{id} still runs the starting example code, \
                        not the mechanic you asked for yet. Say \"keep going\" and I'll write its logic, or press Try It to see the example.")}));
                    break;
                }
                // Everything Ember said this turn (a claim can sit in an earlier message than the last).
                let said: String = self.history.iter().rev()
                    .take_while(|m| !matches!(m, Msg::User(u) if !u.starts_with("[Automatic check]")))
                    .filter_map(|m| match m { Msg::Assistant { text, .. } => Some(text.as_str()), _ => None })
                    .collect::<Vec<_>>().join("\n");
                // Not when they want to be asked first, or when Ember just asked them something (collaborating, not stalling).
                let asks_first = text.to_lowercase().contains("ask me") || last.trim_end().ends_with('?');
                if wants_build(text) && text.to_lowercase().contains("mechanic") && !asks_first && scaffolded.is_none() && !changed_any && !mechanic_checked {
                    emit(json!({"type": "guard", "name": "no_mechanic"}));
                    mechanic_checked = true;
                    self.history.push(Msg::User(
                        "[Automatic check] They asked for a new mechanic and nothing was created. Your next step is a tool call: \
                         `mechanic` with action new, an id, a name, a one-sentence summary and the closest kind. Then adapt it and build.".into()));
                    continue;
                }
                if !in_studio && !changed_any && !claim_checked && (claims_change(&last) || claims_change(&said)) {
                    emit(json!({"type": "guard", "name": "change_claim"}));
                    claim_checked = true;
                    emit(json!({"type": "text", "delta": "\n\nWait - I haven't actually saved that change yet. Doing it now...\n\n"}));
                    self.history.push(Msg::User(
                        "[Automatic check] Your reply says you made a change, but no files were changed. \
                         Make the change now with the tools (read the file first, then write_file/edit_file/new_rust_node), \
                         build it, and only then tell me it's done.".into()));
                    continue;
                }
                break;
            }
            for mut call in calls {
                // A key the creator named ("pressing Shift") but the model left out of `mechanic` new.
                if call.name == "mechanic" && call.args["action"].as_str() == Some("new")
                    && call.args["key"].as_str().unwrap_or("").trim().is_empty() {
                    if let Some(k) = named_key(text) {
                        call.args["key"] = json!(k);
                    }
                }
                let summary = tools::summary(&call.name, &call.args);
                emit(json!({"type": "tool_start", "name": call.name, "summary": summary}));
                let outcome = if self.stop.load(Ordering::Relaxed) {
                    tools::Outcome { ok: false, content: "Stopped by the user.".into(), files_changed: false, rust_built: false, raw: String::new() }
                } else if call.name == "look_at_image" {
                    self.look_at_image(&call.args)
                } else if call.name == "set_mode" {
                    let m = if call.args["mode"].as_str() == Some("learning") { "learning" } else { "autonomous" };
                    self.mode = m.to_string();
                    emit(json!({"type": "mode", "mode": m}));
                    tools::Outcome { ok: true, content: format!("Now in {m} mode."), files_changed: false, rust_built: false, raw: String::new() }
                } else {
                    self.project.run(&call.name, &call.args)
                };
                emit(json!({"type": "tool_end", "name": call.name, "ok": outcome.ok, "summary": summary}));
                let touched = call.args["path"].as_str().unwrap_or("");
                if call.name == "mechanic" && call.args["action"].as_str() == Some("new") && outcome.ok {
                    scaffolded = call.args["id"].as_str().map(|s| s.trim().to_lowercase().replace(|c: char| !c.is_ascii_alphanumeric(), "_"));
                    if let Some(id) = &scaffolded {
                        scaffold_snapshot = logic_snapshot(&self.project.root.join("mechanics").join(id).join("src"));
                        let a = |k: &str| call.args[k].as_str().unwrap_or("").to_string();
                        let hint = format!("{} {} {} {}", a("id"), a("name"), a("summary"), text);
                        // A variant that already is what they asked for may stay as it is.
                        if mechanic_kinds::exact_fit(&a("kind"), &a("base"), &hint) {
                            scaffold_snapshot.clear();
                        }
                    }
                }
                if let Some(id) = &scaffolded {
                    // Written = its logic files differ from the starting code (edits to tuning or docs alone don't count).
                    logic_written = logic_snapshot(&self.project.root.join("mechanics").join(id).join("src")) != scaffold_snapshot;
                }
                if outcome.files_changed && (call.name == "new_rust_node" || touched.ends_with(".rs") || touched.ends_with("Cargo.toml")) {
                    rust_dirty = true;
                }
                if outcome.rust_built && outcome.ok {
                    rust_dirty = false;
                } else if call.name == "build_rust" && !outcome.ok {
                    rust_dirty = true;
                }
                if outcome.files_changed {
                    changed_any = true;
                    let path = call.args["path"].as_str().unwrap_or("").trim_start_matches("res://").to_string();
                    emit(json!({"type": "files_changed", "path": path}));
                }
                if outcome.rust_built { emit(json!({"type": "rust_built"})); }
                if call.name == "journal" && call.args["action"] == "add" && outcome.ok { journal_saved = true; }
                self.history.push(Msg::Tool { id: call.id, name: call.name, content: outcome.content });
            }
        }
        if in_studio {
            let mut clean = clean_studio_reply(&studio_text);
            if !studio_how.is_empty() && clean.len() >= 120 && !studio::grounded(&clean, &studio_how[0]) {
                // A fluent answer that never names the real tool for this: add the verified steps after it.
                clean = format!("{clean}\n\nIn the Studio, exactly:\n\n{}", studio_how[0].lines().skip(1).collect::<Vec<_>>().join("\n"));
            }
            if clean.len() < 120 && !studio_how.is_empty() {
                // Nothing useful survived (the model tried to do it itself): give the verified steps directly.
                clean = format!("{}{}Here's how you can do it:\n\n{}", clean, if clean.is_empty() { "" } else { "\n\n" },
                    studio_how.iter().map(|h| h.lines().skip(1).collect::<Vec<_>>().join("\n")).collect::<Vec<_>>().join("\n\nOr:\n"));
            }
            if in_mech && !mech_how.is_empty() {
                let names: Vec<String> = mech_how.iter().filter_map(|m| m.trim_start_matches("- ").split(" = ").next().map(String::from)).collect();
                let low = clean.to_lowercase();
                let named = names.iter().any(|n| low.contains(n) || low.contains(&n.replace('_', " ")));
                if clean.len() < 120 {
                    clean = format!("{}{}The values for this are in the Mechanics tab:\n{}", clean, if clean.is_empty() { "" } else { "\n\n" }, mech_how.join("\n"));
                } else if !named {
                    clean = format!("{clean}\n\nIn the Mechanics tab, the values for this:\n{}", mech_how.join("\n"));
                }
            }
            if !clean.is_empty() {
                emit(json!({"type": "text", "delta": clean}));
            }
        }
        emit(json!({"type": "done"}));
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--print-prompt") {
        print!("{SYSTEM_PROMPT}\n{}", if arg(&args, "--mode").as_deref() == Some("learning") { MODE_LEARNING } else { MODE_AUTONOMOUS });
        return;
    }
    let root = PathBuf::from(arg(&args, "--project").unwrap_or_else(|| ".".into()));
    let root = root.canonicalize().unwrap_or(root);
    if args.iter().any(|a| a == "--print-system") {
        // The full system prompt the model sees for this project and mode (used to build training data).
        let mode = if arg(&args, "--mode").as_deref() == Some("learning") { MODE_LEARNING } else { MODE_AUTONOMOUS };
        print!("{SYSTEM_PROMPT}\n{mode}\n# This project\n{}", assets::design_context(&root));
        return;
    }
    let home = std::env::var("HOME").or_else(|_| std::env::var("USERPROFILE")).unwrap_or_default();
    let project = tools::Project {
        root,
        engine: arg(&args, "--engine").map(PathBuf::from),
        cache_dir: PathBuf::from(home).join(".cache/rusticengine"),
    };
    if args.iter().any(|a| a == "--mcp") {
        // MCP server for outside agents (Claude Code, Codex...). Find the editor next to us if not given.
        let mut project = project;
        if project.engine.is_none() {
            project.engine = std::env::current_exe().ok().and_then(|e| e.parent().map(|d| d.to_path_buf()))
                .and_then(|d| std::fs::read_dir(d).ok())
                .and_then(|rd| rd.flatten().map(|e| e.path()).find(|p| {
                    let n = p.file_name().and_then(|n| n.to_str()).unwrap_or("");
                    // "rusticengine" in release downloads, godot.<platform>.editor.<arch> in development builds.
                    n == "rusticengine" || n == "rusticengine.exe" || (n.starts_with("godot") && n.contains("editor"))
                }));
        }
        mcp::serve(project);
        return;
    }
    let cfg = Config {
        provider: arg(&args, "--provider").unwrap_or_else(|| "ollama".into()),
        base_url: arg(&args, "--base-url").unwrap_or_default(),
        model: arg(&args, "--model").unwrap_or_else(|| "rustic-ember".into()),
        api_key: std::env::var("RUSTIC_AI_KEY").unwrap_or_default(),
        context: arg(&args, "--context").and_then(|s| s.parse().ok()).unwrap_or(16384),
    };
    let stop = Arc::new(AtomicBool::new(false));
    let mode = arg(&args, "--mode").unwrap_or_else(|| "autonomous".into());
    let vision_model = arg(&args, "--vision-model").unwrap_or_else(|| DEFAULT_VISION_MODEL.into());
    let mut session = Session { cfg, project, history: vec![], stop: stop.clone(), mode, vision_model };

    // Run a single tool and print its outcome (used to generate training data from real runs).
    if let Some(tool) = arg(&args, "--tool") {
        let tool_args: Value = serde_json::from_str(&arg(&args, "--args").unwrap_or_else(|| "{}".into())).unwrap_or(json!({}));
        let o = if tool == "look_at_image" { session.look_at_image(&tool_args) } else { session.project.run(&tool, &tool_args) };
        println!("{}", json!({"ok": o.ok, "content": o.content, "files_changed": o.files_changed, "rust_built": o.rust_built}));
        return;
    }
    if args.iter().any(|a| a == "--print-tools") {
        let defs: Vec<Value> = tools::definitions().iter().map(|t| json!({"type": "function", "function": {
            "name": t.name, "description": t.description, "parameters": t.schema}})).collect();
        println!("{}", Value::from(defs));
        return;
    }

    // One-shot mode for terminal testing.
    if let Some(question) = arg(&args, "--ask") {
        session.handle_user(&question, "");
        return;
    }

    // Read stdin on a thread so "stop" is seen while a turn is running.
    let (tx, rx) = mpsc::channel::<Value>();
    std::thread::spawn(move || {
        for line in std::io::stdin().lock().lines() {
            let Ok(line) = line else { break };
            let Ok(v) = serde_json::from_str::<Value>(&line) else { continue };
            if v["type"] == "stop" {
                stop.store(true, Ordering::Relaxed);
            } else if tx.send(v).is_err() {
                break;
            }
        }
    });

    emit(json!({"type": "ready"}));
    for v in rx {
        match v["type"].as_str().unwrap_or("") {
            "config" => {
                let s = |k: &str| v[k].as_str().unwrap_or("").to_string();
                session.cfg = Config {
                    provider: s("provider"),
                    base_url: s("base_url"),
                    model: s("model"),
                    api_key: s("api_key"),
                    context: v["context"].as_u64().unwrap_or(16384) as u32,
                };
                if let Some(m) = v["mode"].as_str().filter(|m| !m.is_empty()) { session.mode = m.to_string(); }
                if let Some(m) = v["vision_model"].as_str().filter(|m| !m.is_empty()) { session.vision_model = m.to_string(); }
            }
            "user" => session.handle_user(v["text"].as_str().unwrap_or(""), v["context"].as_str().unwrap_or("")),
            "reset" => session.history.clear(),
            _ => {}
        }
    }
}

#[cfg(test)]
mod guard_tests {
    #[test]
    fn studio_reply_cleanup() {
        let raw = "Let me look at the model first.\nI'll look at the picture too.\n</think>\n\n1. Press **1** for Vertices. Select the top corners.\n2. Press **M**.\n\nWhy: merging makes a point. Want me to do it for you?";
        let c = super::clean_studio_reply(raw);
        assert_eq!(c, "1. Press **1** for Vertices. Select the top corners.\n2. Press **M**.\n\nWhy: merging makes a point.");
        let dup = "The top is flat. Let me look again.\nThe top is flat, so merge it. The top is flat, so merge it.";
        assert_eq!(super::clean_studio_reply(dup), "The top is flat.\nThe top is flat, so merge it.");
        let looped = "That's a classic look! One second. That's a classic look! One second. That's a classic look! One second. Use Ellipse.";
        assert_eq!(super::clean_studio_reply(looped), "That's a classic look! One second. One second. Use Ellipse.");
    }

    #[test]
    fn studio_file_from_context() {
        use super::studio_file;
        assert_eq!(studio_file("in the Studio's 3D modeler: res://assets/models/house.rmodel (8 vertices, 6 faces)").as_deref(), Some("assets/models/house.rmodel"));
        assert_eq!(studio_file("in the Studio's Sound Effects maker: res://assets/sounds/boom.rsfx (unsaved changes): noise").as_deref(), Some("assets/sounds/boom.rsfx"));
        assert_eq!(studio_file("in the Studio's Sound Effects maker: unsaved sound: noise wave"), None);
        assert_eq!(studio_file("in the Studio's Pixel Art painter: res://assets/art/hero.rpix (unsaved changes): 16x16 px").as_deref(), Some("assets/art/hero.rpix"));
        assert_eq!(studio_file("in the Studio's Music maker: res://assets/music/town.rmusic: 120 BPM").as_deref(), Some("assets/music/town.rmusic"));
        assert_eq!(super::mechanic_in_context("in the Mechanics tab, looking at the HUD mechanic (res://mechanics/hud, The on-screen display)", "hi").as_deref(), Some("hud"));
        assert!(super::wants_explanation("Explain the First-Person Controller mechanic to me"));
        assert!(super::promises_action("It'll need to know about the jump. I'll start by creating the new mechanic, Double Jump, and then I'll write the code."));
        assert!(!super::promises_action("Done: the double jump works. Want me to add a sound?"));
    }

    use super::*;
    #[test]
    fn detects_fake_journal_saves() {
        assert!(claims_journal_save("I've saved it in **design/journal/lighthouse.md**. What would you call it?"));
        assert!(claims_journal_save("I saved that to your journal."));
        assert!(!claims_journal_save("Want me to save this to your journal?"));
    }
    #[test]
    fn detects_dangling_promises() {
        assert!(promises_lookup("Let me look at your Concept Journal, the place where we save ideas."));
        assert!(promises_lookup("Great idea!\nI'll check the Game Paths..."));
        assert!(!promises_lookup("Let me know which one you like?"));
        assert!(!promises_lookup("Let me know what you think."));
        assert!(promises_lookup("I'll change that.\n\nFirst, I'll look at the model's file to find the lid's face."));
        assert!(promises_lookup("The top is flat. Let me check the picture."));
        assert!(!promises_lookup("Press E to extrude. I'll be here if you get stuck."));
        assert!(!promises_lookup("Here's what I found. Want to start?"));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn finds_named_keys() {
        assert_eq!(named_key("a dash. Pressing Shift gives a burst").as_deref(), Some("shift"));
        assert_eq!(named_key("dash when I press Q").as_deref(), Some("q"));
        assert_eq!(named_key("use the F key to glide").as_deref(), Some("f"));
        assert_eq!(named_key("make a dash with a cooldown"), None);
        assert_eq!(named_key("a door on the wall"), None);
    }

    #[test]
    fn trim_history_ends_with_one_huge_exchange() {
        // A runaway 40k-char reply plus big tool results, with no later user message to cut at:
        // this used to re-trim the same results forever.
        let tool = |c: char| Msg::Tool { id: "1".into(), name: "read_file".into(), content: c.to_string().repeat(30_000) };
        let mut h = vec![Msg::User("make a dash".into()), Msg::Assistant { text: "word ".repeat(8000), calls: vec![] }, tool('x'), tool('y')];
        trim_history(&mut h);
        assert!(h.iter().map(msg_len).sum::<usize>() < 20_000);
    }
}
