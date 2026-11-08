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
mod assets;
mod llm;
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

fn emit(v: Value) {
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

/// Drop the oldest exchanges until the history fits. Always cut at a user message, so tool calls
/// and their results stay paired.
fn trim_history(history: &mut Vec<Msg>) {
    let budget = std::env::var("RUSTIC_AGENT_HISTORY_CHARS").ok().and_then(|s| s.parse().ok()).unwrap_or(HISTORY_BUDGET_CHARS);
    while history.iter().map(msg_len).sum::<usize>() > budget {
        let next_user = history.iter().skip(1).position(|m| matches!(m, Msg::User(_))).map(|i| i + 1);
        match next_user {
            Some(i) => { history.drain(..i); }
            None => {
                // One huge exchange: shrink the largest tool results instead.
                let mut shrunk = false;
                for m in history.iter_mut() {
                    if let Msg::Tool { content, .. } = m {
                        if content.len() > 2000 {
                            *content = format!("{}\n...(trimmed to save memory)", &content[..content.floor_char_boundary(2000)]);
                            shrunk = true;
                        }
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
    const VERBS: [&str; 9] = ["added", "made", "changed", "updated", "created", "turned", "gave", "fixed", "set up"];
    let says_i = VERBS.iter().any(|v| t.contains(&format!("i {v} ")) || t.contains(&format!("i've {v} ")) || t.contains(&format!("i have {v} ")));
    says_i || t.contains("press **play**") || t.contains("press play")
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
        let content = if context.is_empty() { text.to_string() } else { format!("{text}\n\n[Editor context: {context}]") };
        self.history.push(Msg::User(content));
        let defs = tools::definitions();
        let mut rust_dirty = false;
        let mut auto_checks = 0;
        let mut changed_any = false;
        let mut claim_checked = false;

        for _ in 0..MAX_STEPS {
            trim_history(&mut self.history);
            let mut on_text = |d: &str| emit(json!({"type": "text", "delta": d}));
            let system = self.system_prompt();
            let turn = match llm::chat(&self.cfg, &system, &self.history, &defs, &self.stop, &mut on_text) {
                Ok(t) => t,
                Err(e) => {
                    emit(json!({"type": "error", "message": e}));
                    // Keep the history valid: the user message stays, nothing half-written is added.
                    break;
                }
            };
            let mut turn = turn;
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
                if !changed_any && !claim_checked && claims_change(&last) {
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
            for call in calls {
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
                self.history.push(Msg::Tool { id: call.id, name: call.name, content: outcome.content });
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
    let home = std::env::var("HOME").or_else(|_| std::env::var("USERPROFILE")).unwrap_or_default();
    let project = tools::Project {
        root,
        engine: arg(&args, "--engine").map(PathBuf::from),
        cache_dir: PathBuf::from(home).join(".cache/rusticengine"),
    };
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
        let o = session.project.run(&tool, &tool_args);
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
