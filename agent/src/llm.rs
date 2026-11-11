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
        "local" => {
            let local = local::ensure(cfg)?;
            ollama(&local, system, history, tools, stop, on_text)
        }
        _ => ollama(cfg, system, history, tools, stop, on_text),
    }
}

// ---------------------------------------------------------------- Built-in runtime ("local")

/// Ember (or any Qwen-style GGUF) running inside RusticEngine via the bundled `ember-runtime`,
/// so creators don't need to install Ollama. `cfg.model` = path to a .gguf file, or empty for
/// the bundled Ember model. The runtime is started on first use and kept for the session.
pub mod local {
    use super::Config;
    use std::io::{BufRead, BufReader};
    use std::path::{Path, PathBuf};
    use std::process::{Child, Command, Stdio};
    use std::sync::Mutex;

    struct Running { model: PathBuf, ctx: u32, port: u16, child: Child }
    static RUNNING: Mutex<Option<Running>> = Mutex::new(None);

    fn exe_dir() -> PathBuf {
        std::env::current_exe().ok().and_then(|p| p.parent().map(Path::to_path_buf)).unwrap_or_default()
    }

    /// Where the bundled Ember model lives: next to the agent (bin/models/ember.gguf), or
    /// RUSTIC_EMBER_MODEL for development.
    pub fn default_model() -> PathBuf {
        if let Ok(p) = std::env::var("RUSTIC_EMBER_MODEL") { return PathBuf::from(p); }
        exe_dir().join("models").join("ember.gguf")
    }

    /// The Vulkan build (`ember-runtime`) runs on any graphics card and falls back to the processor.
    /// An optional CUDA build (`ember-runtime-cuda`) is ~10% faster on Nvidia cards, so it's preferred
    /// when it's installed and an Nvidia driver is loaded.
    fn runtime_binary() -> PathBuf {
        let exe = |n: &str| exe_dir().join(if cfg!(windows) { format!("{n}.exe") } else { n.to_string() });
        let cuda = exe("ember-runtime-cuda");
        let nvidia = if cfg!(target_os = "linux") { Path::new("/proc/driver/nvidia").exists() } else { cfg!(windows) };
        if std::env::var_os("RUSTIC_NO_CUDA").is_none() && nvidia && cuda.is_file() { cuda } else { exe("ember-runtime") }
    }

    pub fn ensure(cfg: &Config) -> Result<Config, String> {
        let model = if cfg.model.trim().is_empty() || cfg.model.starts_with("rustic-ember") {
            default_model()
        } else {
            PathBuf::from(cfg.model.trim())
        };
        if !model.is_file() {
            return Err(if cfg.model.trim().is_empty() || cfg.model.starts_with("rustic-ember") {
                format!("Ember's built-in model isn't installed (looked for {}).\n\
                         Pick another model in the AI Guide settings, or put ember.gguf there.", model.display())
            } else {
                format!("Couldn't find the model file {}. Pick a .gguf file in the AI Guide settings.", model.display())
            });
        }
        let ctx = if cfg.context > 0 { cfg.context } else { 16384 };
        let mut guard = RUNNING.lock().map_err(|_| "runtime lock poisoned".to_string())?;
        if let Some(r) = guard.as_mut() {
            let alive = matches!(r.child.try_wait(), Ok(None));
            if alive && r.model == model && r.ctx == ctx {
                return Ok(local_cfg(cfg, r.port));
            }
            let _ = r.child.kill();
            let _ = r.child.wait();
            *guard = None;
        }
        let runtime = runtime_binary();
        if !runtime.is_file() {
            return Err(format!("The built-in model runtime is missing ({}). Pick Ollama or a cloud model in the AI Guide settings.",
                               runtime.display()));
        }
        // A runtime from an earlier session may still be giving its graphics memory back,
        // so a failed load is retried a few times before giving up.
        let mut last_err = String::new();
        for attempt in 0..4 {
            if attempt > 0 { std::thread::sleep(std::time::Duration::from_millis(1500 * attempt)); }
            match start(&runtime, &model, ctx) {
                Ok((child, port)) => {
                    *guard = Some(Running { model, ctx, port, child });
                    return Ok(local_cfg(cfg, port));
                }
                Err(e) => last_err = e,
            }
        }
        Err(format!("The built-in model couldn't start: {last_err}\n\
                     If another program is using the graphics card's memory, close it and try again, or lower \
                     Context in the AI Guide settings."))
    }

    fn start(runtime: &Path, model: &Path, ctx: u32) -> Result<(Child, u16), String> {
        let mut cmd = Command::new(runtime);
        cmd.arg("--model").arg(model)
            .arg("--ctx").arg(ctx.to_string())
            .arg("--parent-pid").arg(std::process::id().to_string())
            .stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::piped());
        #[cfg(target_os = "linux")]
        unsafe {
            // Have the kernel stop the runtime the moment this agent dies, even if it's killed,
            // so the model's graphics memory is freed right away. (Linux sends this when the spawning
            // *thread* exits: models are called from the agent's main thread, so that's the process.)
            use std::os::unix::process::CommandExt;
            unsafe extern "C" { fn prctl(option: i32, arg2: u64, arg3: u64, arg4: u64, arg5: u64) -> i32; }
            const PR_SET_PDEATHSIG: i32 = 1;
            const SIGTERM: u64 = 15;
            cmd.pre_exec(|| { prctl(PR_SET_PDEATHSIG, SIGTERM, 0, 0, 0); Ok(()) });
        }
        let mut child = cmd.spawn().map_err(|e| format!("couldn't run {}: {e}", runtime.display()))?;
        // First line on stdout: {"ready": true, "port": N, ...} once the model is loaded.
        let mut line = String::new();
        let _ = BufReader::new(child.stdout.take().unwrap()).read_line(&mut line);
        let ready: serde_json::Value = serde_json::from_str(line.trim()).unwrap_or_default();
        if let Some(port) = ready["port"].as_u64() {
            return Ok((child, port as u16));
        }
        let _ = child.kill();
        let _ = child.wait();
        let mut err = String::new();
        if let Some(e) = child.stderr.take() { let _ = std::io::Read::read_to_string(&mut BufReader::new(e), &mut err); }
        Err(err.trim().lines().last().unwrap_or("it exited without saying why (out of memory?)")
            .trim_start_matches("ember-runtime: ").to_string())
    }

    fn local_cfg(cfg: &Config, port: u16) -> Config {
        Config { provider: "ollama".into(), base_url: format!("http://127.0.0.1:{port}"),
                 // "rustic-ember" makes the ollama path ask for non-thinking replies, as Ember was trained.
                 model: "rustic-ember".into(), api_key: String::new(), context: cfg.context }
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
    let mut body = json!({
        "model": cfg.model, "messages": messages, "tools": tools, "stream": true,
        "options": {"num_ctx": if cfg.context > 0 { cfg.context } else { 16384 }, "temperature": 0.4,
                    // A local model that starts repeating itself would otherwise generate forever.
                    "num_predict": 8192},
    });
    // Ember is trained in Qwen3's non-thinking mode; qwen3 models otherwise spend a long time "thinking".
    let m = cfg.model.to_lowercase();
    if m.starts_with("rustic-ember") || m.starts_with("qwen3") {
        body["think"] = json!(false);
    }
    let resp = post(agent().post(&url(base, "api/chat")), &body, "Ollama")
        .map_err(|e| if e.contains("Couldn't reach") {
            format!("{e}\nIs Ollama running? Start it with `ollama serve`, or pick another model in the AI Guide settings.")
        } else if e.contains("HTTP 404") && e.contains("not found") {
            if m.starts_with("rustic-ember") {
                format!("Ember's model isn't installed in Ollama yet.\n\
                    While it's on its way, open the AI Guide settings and pick \"Ollama: any local model\" with qwen3:8b \
                    (run `ollama pull qwen3:8b` first) - it works with Ember's tools too, just a bit less sure-footed.\n({e})")
            } else {
                format!("Ollama doesn't have the model \"{}\". Download it with `ollama pull {}`, or pick another in the AI Guide settings.\n({e})",
                        cfg.model, cfg.model)
            }
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

// ---------------------------------------------------------------- Looking at images

/// Ask a vision-capable model about one image (concept art, a sprite, a screenshot).
/// Ollama uses a separate local vision model; cloud providers use the chosen model itself.
pub fn describe_image(cfg: &Config, vision_model: &str, mime: &str, b64: &str, question: &str) -> Result<String, String> {
    match cfg.provider.as_str() {
        "anthropic" => {
            let body = json!({"model": cfg.model, "max_tokens": 1500, "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
                {"type": "text", "text": question}]}]});
            let base = if cfg.base_url.is_empty() { "https://api.anthropic.com" } else { &cfg.base_url };
            let req = agent().post(&url(base, "v1/messages")).set("x-api-key", &cfg.api_key).set("anthropic-version", "2023-06-01");
            let v: Value = post(req, &body, "the AI service")?.into_json().map_err(|e| e.to_string())?;
            Ok(v["content"].as_array().map(|a| a.iter().filter_map(|b| b["text"].as_str()).collect::<Vec<_>>().join("")).unwrap_or_default())
        }
        "openai" => {
            let body = json!({"model": cfg.model, "messages": [{"role": "user", "content": [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": format!("data:{mime};base64,{b64}")}}]}]});
            let base = if cfg.base_url.is_empty() { "https://api.openai.com/v1" } else { &cfg.base_url };
            let mut req = agent().post(&url(base, "chat/completions"));
            if !cfg.api_key.is_empty() { req = req.set("authorization", &format!("Bearer {}", cfg.api_key)); }
            let v: Value = post(req, &body, "the AI service")?.into_json().map_err(|e| e.to_string())?;
            Ok(v["choices"][0]["message"]["content"].as_str().unwrap_or("").to_string())
        }
        _ => {
            let base = if cfg.base_url.is_empty() { "http://localhost:11434" } else { cfg.base_url.trim_end_matches("/v1") };
            let body = json!({"model": vision_model, "stream": false, "think": false, "keep_alive": "30s",
                "messages": [{"role": "user", "content": question, "images": [b64]}],
                "options": {"num_ctx": 8192, "temperature": 0.2, "num_predict": 1200}});
            let v: Value = post(agent().post(&url(base, "api/chat")), &body, "Ollama")
                .map_err(|e| if e.contains("HTTP 404") {
                    format!("The image model {vision_model} isn't installed. Install it with `ollama pull {vision_model}`.")
                } else { e })?
                .into_json().map_err(|e| e.to_string())?;
            Ok(v["message"]["content"].as_str().unwrap_or("").trim().to_string())
        }
    }
}

pub fn base64(data: &[u8]) -> String {
    const T: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::with_capacity(data.len().div_ceil(3) * 4);
    for c in data.chunks(3) {
        let n = (c[0] as u32) << 16 | (*c.get(1).unwrap_or(&0) as u32) << 8 | *c.get(2).unwrap_or(&0) as u32;
        for i in 0..4 {
            if i <= c.len() { out.push(T[(n >> (18 - 6 * i) & 63) as usize] as char); } else { out.push('='); }
        }
    }
    out
}
