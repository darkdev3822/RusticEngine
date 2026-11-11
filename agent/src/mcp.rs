//! MCP server: `rustic-agent --mcp --project DIR` lets any MCP client (Claude Code, Codex, Cursor...)
//! work on a RusticEngine project with the same tools Ember uses. Speaks JSON-RPC 2.0 over stdio,
//! one message per line. Tools only (plus server instructions); no sampling, no resources.

use std::io::{BufRead, Write};

use serde_json::{Value, json};

use crate::tools::{self, Project};

const INSTRUCTIONS_HEAD: &str = include_str!("../prompt/mcp.md");
const EMBER: &str = include_str!("../prompt/ember.md");
const GUIDES: [(&str, &str, &str); 7] = [
    ("mechanics", "Mechanics: what they are, how the panel and tuning work", include_str!("../prompt/mechanics.md")),
    ("studio_model", "Studio 3D Model maker: exact keys, tools and workflow", include_str!("../prompt/studio_model.md")),
    ("studio_sfx", "Studio Sound Effects maker", include_str!("../prompt/studio_sfx.md")),
    ("studio_pixel", "Studio Pixel Art painter", include_str!("../prompt/studio_pixel.md")),
    ("studio_music", "Studio Music maker", include_str!("../prompt/studio_music.md")),
    ("studio_sky", "Studio Sky maker", include_str!("../prompt/studio_sky.md")),
    ("studio_ui", "Studio UI Kit maker", include_str!("../prompt/studio_ui.md")),
];
/// Ember-only tools that make no sense for an outside agent.
const HIDDEN: [&str; 1] = ["set_mode"];

fn instructions() -> String {
    // The technical half of Ember's prompt (project layout, verified godot-rust 0.5 rules, scene files).
    let tech = EMBER.find("# Project layout").map(|i| &EMBER[i..]).unwrap_or("");
    format!("{INSTRUCTIONS_HEAD}\n{tech}")
}

fn tool_list() -> Vec<Value> {
    let mut out: Vec<Value> = tools::definitions().iter()
        .filter(|t| !HIDDEN.contains(&t.name))
        .map(|t| {
            let desc = if t.name == "look_at_image" {
                "Look at an image in the project (concept art, a sprite, a Studio picture in design/studio/). Returns the image itself."
            } else { t.description };
            json!({"name": t.name, "description": desc, "inputSchema": t.schema})
        })
        .collect();
    let topics: Vec<&str> = GUIDES.iter().map(|g| g.0).collect();
    let about: Vec<String> = GUIDES.iter().map(|g| format!("{}: {}", g.0, g.1)).collect();
    out.push(json!({
        "name": "rustic_guide",
        "description": format!("RusticEngine reference cards (exact controls and rules), for guiding the creator. Topics: {}", about.join("; ")),
        "inputSchema": {"type": "object", "properties": {"topic": {"type": "string", "enum": topics}}, "required": ["topic"]},
    }));
    out
}

fn call(project: &Project, name: &str, args: &Value) -> Value {
    let text = |t: String, err: bool| json!({"content": [{"type": "text", "text": t}], "isError": err});
    match name {
        "rustic_guide" => {
            let topic = args["topic"].as_str().unwrap_or("");
            match GUIDES.iter().find(|g| g.0 == topic) {
                Some(g) => text(g.2.to_string(), false),
                None => text(format!("Unknown topic {topic:?}."), true),
            }
        }
        "look_at_image" => match project.image(args["path"].as_str().unwrap_or("")) {
            Ok((mime, b64)) => json!({"content": [{"type": "image", "data": b64, "mimeType": mime}], "isError": false}),
            Err(e) => text(e, true),
        },
        n if HIDDEN.contains(&n) || !tools::definitions().iter().any(|t| t.name == n) => text(format!("Unknown tool {n:?}."), true),
        _ => {
            let o = project.run(name, args);
            text(o.content, !o.ok)
        }
    }
}

pub fn serve(project: Project) {
    let stdin = std::io::stdin();
    let mut out = std::io::stdout();
    for line in stdin.lock().lines() {
        let Ok(line) = line else { break };
        if line.trim().is_empty() { continue; }
        let msg: Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(e) => {
                reply(&mut out, json!({"jsonrpc": "2.0", "id": null, "error": {"code": -32700, "message": format!("parse error: {e}")}}));
                continue;
            }
        };
        let Some(id) = msg.get("id").cloned() else { continue }; // a notification: nothing to answer
        let method = msg["method"].as_str().unwrap_or("");
        let result = match method {
            "initialize" => Ok(json!({
                "protocolVersion": msg["params"]["protocolVersion"].as_str().unwrap_or("2025-06-18"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "rusticengine", "title": "RusticEngine", "version": env!("CARGO_PKG_VERSION")},
                "instructions": instructions(),
            })),
            "ping" => Ok(json!({})),
            "tools/list" => Ok(json!({"tools": tool_list()})),
            "tools/call" => {
                let p = &msg["params"];
                Ok(call(&project, p["name"].as_str().unwrap_or(""), p.get("arguments").unwrap_or(&json!({}))))
            }
            _ => Err(json!({"code": -32601, "message": format!("method not found: {method}")})),
        };
        reply(&mut out, match result {
            Ok(r) => json!({"jsonrpc": "2.0", "id": id, "result": r}),
            Err(e) => json!({"jsonrpc": "2.0", "id": id, "error": e}),
        });
    }
}

fn reply(out: &mut std::io::Stdout, v: Value) {
    let _ = writeln!(out, "{v}");
    let _ = out.flush();
}
