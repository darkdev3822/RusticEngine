//! Chat with a language model through one of three API dialects, streaming text as it arrives.
//! - `ollama`:    Ollama's native /api/chat (lets us raise the context window for local models)
//! - `openai`:    any OpenAI-compatible /chat/completions (OpenAI, OpenRouter, llama.cpp, LM Studio, vLLM...)
//! - `anthropic`: Anthropic's /v1/messages
use std::io::{BufRead, BufReader};
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

use serde_json::{Value, json};

#[derive(Clone, Debug, Default)]
pub struct Config {
    pub provider: String,
    pub base_url: String,
    pub model: String,
    pub api_key: String,
    pub context: u32,
}

#[derive(Clone, Debug)]
pub struct ToolCall {
    pub id: String,
    pub name: String,
    pub args: Value,
}

#[derive(Clone, Debug)]
pub enum Msg {
    User(String),
    Assistant { text: String, calls: Vec<ToolCall> },
    Tool { id: String, name: String, content: String },
}

pub struct Turn {
    pub text: String,
    pub calls: Vec<ToolCall>,
}

pub struct ToolDef {
    pub name: &'static str,
    pub description: &'static str,
    pub schema: Value,
}

pub fn chat(
    cfg: &Config,
    system: &str,
    history: &[Msg],
    tools: &[ToolDef],
    stop: &AtomicBool,
    on_text: &mut dyn FnMut(&str),
) -> Result<Turn, String> {
    match cfg.provider.as_str() {
        "anthropic" => anthropic(cfg, system, history, tools, stop, on_text),
        "openai" => openai(cfg, system, history, tools, stop, on_text),
        _ => ollama(cfg, system, history, tools, stop, on_text),
    }
}

fn agent() -> ureq::Agent {
    ureq::AgentBuilder::new()
        .timeout_connect(Duration::from_secs(10))
        .timeout_read(Duration::from_secs(600))
        .build()
}

fn post(req: ureq::Request, body: &Value, what: &str) -> Result<ureq::Response, String> {
    match req.set("content-type", "application/json").send_string(&body.to_string()) {
        Ok(r) => Ok(r),
        Err(ureq::Error::Status(code, r)) => {
            let text = r.into_string().unwrap_or_default();
            Err(format!("{what} answered HTTP {code}: {}", text.chars().take(600).collect::<String>()))
        }
        Err(e) => Err(format!("Couldn't reach {what}: {e}")),
    }
}

fn url(base: &str, path: &str) -> String {
    format!("{}/{}", base.trim_end_matches('/'), path.trim_start_matches('/'))
}

fn new_id(n: usize) -> String {
    format!("call_{}_{}", std::process::id(), n)
}

// ---------------------------------------------------------------- Ollama (native)

fn ollama(cfg: &Config, system: &str, history: &[Msg], tools: &[ToolDef], stop: &AtomicBool,
          on_text: &mut dyn FnMut(&str)) -> Result<Turn, String> {
    let mut messages = vec![json!({"role": "system", "content": system})];
    for m in history {
        match m {
            Msg::User(t) => messages.push(json!({"role": "user", "content": t})),
            Msg::Assistant { text, calls } => {
                let mut msg = json!({"role": "assistant", "content": text});
                if !calls.is_empty() {
                    msg["tool_calls"] = calls.iter()
                        .map(|c| json!({"function": {"name": c.name, "arguments": c.args}}))
                        .collect();
                }
                messages.push(msg);
            }
            Msg::Tool { name, content, .. } => {
                messages.push(json!({"role": "tool", "tool_name": name, "content": content}))
            }
        }
    }
    let tools: Vec<Value> = tools.iter().map(|t| json!({"type": "function", "function": {
        "name": t.name, "description": t.description, "parameters": t.schema}})).collect();
    let base = if cfg.base_url.is_empty() { "http://localhost:11434" } else { cfg.base_url.trim_end_matches("/v1") };
    let body = json!({
        "model": cfg.model, "messages": messages, "tools": tools, "stream": true,
        "options": {"num_ctx": if cfg.context > 0 { cfg.context } else { 16384 }, "temperature": 0.4},
    });
    let resp = post(agent().post(&url(base, "api/chat")), &body, "Ollama")
        .map_err(|e| if e.contains("Couldn't reach") {
            format!("{e}\nIs Ollama running? Start it with `ollama serve`, or pick another model in the AI Guide settings.")
        } else { e })?;

    let mut turn = Turn { text: String::new(), calls: vec![] };
    for line in BufReader::new(resp.into_reader()).lines() {
        if stop.load(Ordering::Relaxed) { break; }
        let line = line.map_err(|e| e.to_string())?;
        let Ok(v) = serde_json::from_str::<Value>(&line) else { continue };
        if let Some(err) = v["error"].as_str() { return Err(format!("Ollama: {err}")); }
        if let Some(t) = v["message"]["content"].as_str() {
            if !t.is_empty() { turn.text.push_str(t); on_text(t); }
        }
        if let Some(calls) = v["message"]["tool_calls"].as_array() {
            for c in calls {
                let args = match &c["function"]["arguments"] {
                    Value::String(s) => serde_json::from_str(s).unwrap_or(json!({})),
                    other => other.clone(),
                };
                turn.calls.push(ToolCall { id: new_id(turn.calls.len()),
                    name: c["function"]["name"].as_str().unwrap_or("").to_string(), args });
            }
        }
        if v["done"].as_bool() == Some(true) { break; }
    }
    Ok(turn)
}

// ---------------------------------------------------------------- OpenAI-compatible

fn openai(cfg: &Config, system: &str, history: &[Msg], tools: &[ToolDef], stop: &AtomicBool,
          on_text: &mut dyn FnMut(&str)) -> Result<Turn, String> {
    let mut messages = vec![json!({"role": "system", "content": system})];
    for m in history {
        match m {
            Msg::User(t) => messages.push(json!({"role": "user", "content": t})),
            Msg::Assistant { text, calls } => {
                let mut msg = json!({"role": "assistant", "content": if text.is_empty() { Value::Null } else { json!(text) }});
                if !calls.is_empty() {
                    msg["tool_calls"] = calls.iter().map(|c| json!({"id": c.id, "type": "function",
                        "function": {"name": c.name, "arguments": c.args.to_string()}})).collect();
                }
                messages.push(msg);
            }
            Msg::Tool { id, content, .. } => {
                messages.push(json!({"role": "tool", "tool_call_id": id, "content": content}))
            }
        }
    }
    let tools: Vec<Value> = tools.iter().map(|t| json!({"type": "function", "function": {
        "name": t.name, "description": t.description, "parameters": t.schema}})).collect();
    let body = json!({"model": cfg.model, "messages": messages, "tools": tools, "stream": true});
    let base = if cfg.base_url.is_empty() { "https://api.openai.com/v1" } else { &cfg.base_url };
    let mut req = agent().post(&url(base, "chat/completions"));
    if !cfg.api_key.is_empty() {
        req = req.set("authorization", &format!("Bearer {}", cfg.api_key));
    }
    let resp = post(req, &body, "the model server")?;

    let mut turn = Turn { text: String::new(), calls: vec![] };
    let mut partial: Vec<(String, String, String)> = vec![]; // (id, name, arguments json text)
    for line in BufReader::new(resp.into_reader()).lines() {
        if stop.load(Ordering::Relaxed) { break; }
        let line = line.map_err(|e| e.to_string())?;
        let Some(data) = line.strip_prefix("data:") else { continue };
        let data = data.trim();
        if data == "[DONE]" { break; }
        let Ok(v) = serde_json::from_str::<Value>(data) else { continue };
        if let Some(msg) = v["error"]["message"].as_str() { return Err(msg.to_string()); }
        let delta = &v["choices"][0]["delta"];
        if let Some(t) = delta["content"].as_str() {
            if !t.is_empty() { turn.text.push_str(t); on_text(t); }
        }
        if let Some(calls) = delta["tool_calls"].as_array() {
            for c in calls {
                let i = c["index"].as_u64().unwrap_or(partial.len() as u64) as usize;
                while partial.len() <= i { partial.push(Default::default()); }
                if let Some(id) = c["id"].as_str() { partial[i].0 = id.to_string(); }
                if let Some(n) = c["function"]["name"].as_str() { partial[i].1.push_str(n); }
                if let Some(a) = c["function"]["arguments"].as_str() { partial[i].2.push_str(a); }
            }
        }
    }
    for (n, (id, name, args)) in partial.into_iter().enumerate() {
        if name.is_empty() { continue; }
        turn.calls.push(ToolCall {
            id: if id.is_empty() { new_id(n) } else { id },
            name,
            args: serde_json::from_str(if args.trim().is_empty() { "{}" } else { &args }).unwrap_or(json!({})),
        });
    }
    Ok(turn)
}

// ---------------------------------------------------------------- Anthropic

fn anthropic(cfg: &Config, system: &str, history: &[Msg], tools: &[ToolDef], stop: &AtomicBool,
             on_text: &mut dyn FnMut(&str)) -> Result<Turn, String> {
    let mut messages: Vec<Value> = vec![];
    for m in history {
        match m {
            Msg::User(t) => messages.push(json!({"role": "user", "content": t})),
            Msg::Assistant { text, calls } => {
                let mut blocks = vec![];
                if !text.is_empty() { blocks.push(json!({"type": "text", "text": text})); }
                for c in calls {
                    blocks.push(json!({"type": "tool_use", "id": c.id, "name": c.name, "input": c.args}));
                }
                if blocks.is_empty() { blocks.push(json!({"type": "text", "text": "(no reply)"})); }
                messages.push(json!({"role": "assistant", "content": blocks}));
            }
            Msg::Tool { id, content, .. } => {
                let block = json!({"type": "tool_result", "tool_use_id": id, "content": content});
                // Consecutive tool results belong in one user message.
                match messages.last_mut() {
                    Some(last) if last["role"] == "user" && last["content"].is_array() => {
                        last["content"].as_array_mut().unwrap().push(block)
                    }
                    _ => messages.push(json!({"role": "user", "content": [block]})),
                }
            }
        }
    }
    let tools: Vec<Value> = tools.iter().map(|t| json!({
        "name": t.name, "description": t.description, "input_schema": t.schema})).collect();
    let body = json!({"model": cfg.model, "max_tokens": 8192, "system": system,
                      "messages": messages, "tools": tools, "stream": true});
    let base = if cfg.base_url.is_empty() { "https://api.anthropic.com" } else { &cfg.base_url };
    let req = agent().post(&url(base, "v1/messages"))
        .set("x-api-key", &cfg.api_key)
        .set("anthropic-version", "2023-06-01");
    let resp = post(req, &body, "Anthropic")?;

    let mut turn = Turn { text: String::new(), calls: vec![] };
    let mut current: Option<(String, String, String)> = None; // tool_use being streamed
    for line in BufReader::new(resp.into_reader()).lines() {
        if stop.load(Ordering::Relaxed) { break; }
        let line = line.map_err(|e| e.to_string())?;
        let Some(data) = line.strip_prefix("data:") else { continue };
        let Ok(v) = serde_json::from_str::<Value>(data.trim()) else { continue };
        match v["type"].as_str().unwrap_or("") {
            "content_block_start" if v["content_block"]["type"] == "tool_use" => {
                current = Some((v["content_block"]["id"].as_str().unwrap_or("").into(),
                                v["content_block"]["name"].as_str().unwrap_or("").into(), String::new()));
            }
            "content_block_delta" => {
                if let Some(t) = v["delta"]["text"].as_str() { turn.text.push_str(t); on_text(t); }
                if let (Some(p), Some(cur)) = (v["delta"]["partial_json"].as_str(), current.as_mut()) {
                    cur.2.push_str(p);
                }
            }
            "content_block_stop" => {
                if let Some((id, name, args)) = current.take() {
                    turn.calls.push(ToolCall { id, name,
                        args: serde_json::from_str(if args.is_empty() { "{}" } else { &args }).unwrap_or(json!({})) });
                }
            }
            "error" => return Err(v["error"]["message"].as_str().unwrap_or("Anthropic error").to_string()),
            "message_stop" => break,
            _ => {}
        }
    }
    Ok(turn)
}
