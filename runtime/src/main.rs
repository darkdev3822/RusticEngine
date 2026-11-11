//! ember-runtime: runs a GGUF model in-process (llama.cpp) and serves the part of Ollama's
//! native API that rustic-agent speaks, so Ember works with no separate Ollama install.
//!
//!   ember-runtime --model ember.gguf [--port 0] [--ctx 16384] [--gpu-layers 999] [--parent-pid N]
//!
//! Prints `{"ready": true, "port": N, "model": "..."}` on stdout once the model is loaded.
//! Endpoints: GET /api/tags, POST /api/chat (streamed NDJSON, tools via Qwen-style <tool_call> tags).
//! The prompt is built exactly like the Hugging Face Qwen3 chat template that Ember was trained with.
//! Only listens on 127.0.0.1. Serves one request at a time (one creator, one Ember).

use std::io::{BufRead, BufReader, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::num::NonZeroU32;
use std::path::PathBuf;
use std::time::Duration;

use llama_cpp_2::context::LlamaContext;
use llama_cpp_2::context::params::LlamaContextParams;
use llama_cpp_2::llama_backend::LlamaBackend;
use llama_cpp_2::llama_batch::LlamaBatch;
use llama_cpp_2::model::LlamaModel;
use llama_cpp_2::model::params::LlamaModelParams;
use llama_cpp_2::sampling::LlamaSampler;
use llama_cpp_2::token::LlamaToken;
use serde_json::{Value, json};

mod prompt;

struct Args {
    model: PathBuf,
    port: u16,
    ctx: u32,
    gpu_layers: u32,
    parent_pid: Option<u32>,
    verbose: bool,
}

fn parse_args() -> Result<Args, String> {
    let mut a = Args { model: PathBuf::new(), port: 0, ctx: 16384, gpu_layers: 999, parent_pid: None, verbose: false };
    let mut it = std::env::args().skip(1);
    while let Some(k) = it.next() {
        let mut val = || it.next().ok_or(format!("{k} needs a value"));
        match k.as_str() {
            "--model" => a.model = PathBuf::from(val()?),
            "--port" => a.port = val()?.parse().map_err(|_| "--port must be a number")?,
            "--ctx" => a.ctx = val()?.parse().map_err(|_| "--ctx must be a number")?,
            "--gpu-layers" => a.gpu_layers = val()?.parse().map_err(|_| "--gpu-layers must be a number")?,
            "--parent-pid" => a.parent_pid = Some(val()?.parse().map_err(|_| "--parent-pid must be a number")?),
            "--verbose" => a.verbose = true,
            // Print the prompt a chat request would produce, without loading any model (for checking the template).
            "--render" => {
                let path = val()?;
                let body: Value = serde_json::from_str(&std::fs::read_to_string(&path).map_err(|e| e.to_string())?)
                    .map_err(|e| e.to_string())?;
                let (m, t) = (body["messages"].as_array().map(|v| v.as_slice()).unwrap_or(&[]),
                              body["tools"].as_array().map(|v| v.as_slice()).unwrap_or(&[]));
                let think = body["think"].as_bool().unwrap_or(false);
                // With "template" in the request file, render that Jinja template instead (testing).
                match body["template"].as_str() {
                    Some(tpl) => match prompt::build_jinja(tpl, m, t, think, body["bos"].as_str().unwrap_or(""), body["eos"].as_str().unwrap_or("")) {
                        Ok(s) => print!("{s}"),
                        Err(e) => { eprintln!("{e}"); std::process::exit(1); }
                    },
                    None => print!("{}", prompt::build(m, t, think)),
                }
                std::process::exit(0);
            }
            "-h" | "--help" => {
                println!("ember-runtime --model FILE.gguf [--port 0] [--ctx 16384] [--gpu-layers 999] [--parent-pid N] [--verbose]");
                std::process::exit(0);
            }
            other => return Err(format!("unknown argument {other}")),
        }
    }
    if a.model.as_os_str().is_empty() { return Err("--model FILE.gguf is required".into()); }
    if !a.model.is_file() { return Err(format!("model file not found: {}", a.model.display())); }
    Ok(a)
}

fn main() {
    let args = match parse_args() {
        Ok(a) => a,
        Err(e) => { eprintln!("ember-runtime: {e}"); std::process::exit(2); }
    };
    // Quit when the agent that started us goes away, so no model stays loaded in the background.
    if let Some(pid) = args.parent_pid {
        std::thread::spawn(move || loop {
            std::thread::sleep(Duration::from_secs(2));
            if !std::path::Path::new(&format!("/proc/{pid}")).exists() { std::process::exit(0); }
        });
    }
    if let Err(e) = run(args) {
        eprintln!("ember-runtime: {e}");
        std::process::exit(1);
    }
}

fn run(args: Args) -> Result<(), String> {
    let mut backend = LlamaBackend::init().map_err(|e| e.to_string())?;
    if !args.verbose { backend.void_logs(); }
    let mparams = LlamaModelParams::default().with_n_gpu_layers(args.gpu_layers);
    let model = LlamaModel::load_from_file(&backend, &args.model, &mparams)
        .map_err(|e| format!("couldn't load {}: {e}", args.model.display()))?;
    let n_ctx = args.ctx.min(model.n_ctx_train()).max(2048);
    let threads = std::thread::available_parallelism().map(|n| n.get() as i32).unwrap_or(4).clamp(1, 16);
    let cparams = LlamaContextParams::default()
        .with_n_ctx(NonZeroU32::new(n_ctx))
        .with_n_batch(512)
        .with_n_threads(threads)
        .with_n_threads_batch(threads);
    let mut ctx = model.new_context(&backend, cparams).map_err(|e| format!("couldn't create context: {e}"))?;

    let listener = TcpListener::bind(("127.0.0.1", args.port)).map_err(|e| format!("couldn't listen: {e}"))?;
    let port = listener.local_addr().map_err(|e| e.to_string())?.port();
    let name = args.model.file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default();
    println!("{}", json!({"ready": true, "port": port, "model": name, "ctx": n_ctx,
                          "gpu": backend.supports_gpu_offload()}));
    let _ = std::io::stdout().flush();

    // Qwen3-style models get an empty <think></think> block when thinking is off (as in training);
    // older chat models (e.g. Qwen2.5) don't know that block at all.
    let template = model.meta_val_str("tokenizer.chat_template").unwrap_or_default();
    let thinking = template.is_empty() || template.contains("<think>");
    // Ember and other Qwen-style models get the exact hand-written format; others their own template.
    let qwen = prompt::is_qwen_style(&template);
    let vocab = model.vocab();
    let piece = |t| String::from_utf8_lossy(&vocab.token_to_piece(t, true, None)).into_owned();
    let (bos, eos) = (piece(vocab.bos()), piece(vocab.eos()));
    let mut state = Engine { model: &model, cache: Vec::new(), thinking, qwen, template, bos, eos };
    for stream in listener.incoming() {
        let Ok(stream) = stream else { continue };
        if let Err(e) = handle(stream, &mut state, &mut ctx, &name) {
            if args.verbose { eprintln!("ember-runtime: request failed: {e}"); }
        }
    }
    Ok(())
}

/// The model plus the tokens currently in the KV cache, so a follow-up request that shares the
/// same beginning (system prompt, earlier turns) only has to process the new part.
struct Engine<'m> {
    model: &'m LlamaModel,
    cache: Vec<LlamaToken>,
    thinking: bool,
    qwen: bool,
    template: String,
    bos: String,
    eos: String,
}

struct Request {
    method: String,
    path: String,
    body: Vec<u8>,
}

fn read_request(stream: &mut TcpStream) -> Result<Request, String> {
    stream.set_read_timeout(Some(Duration::from_secs(30))).ok();
    let mut r = BufReader::new(stream.try_clone().map_err(|e| e.to_string())?);
    let mut line = String::new();
    r.read_line(&mut line).map_err(|e| e.to_string())?;
    let mut parts = line.split_whitespace();
    let method = parts.next().unwrap_or("").to_string();
    let path = parts.next().unwrap_or("").to_string();
    let mut len = 0usize;
    loop {
        let mut h = String::new();
        if r.read_line(&mut h).map_err(|e| e.to_string())? == 0 { break; }
        let h = h.trim_end();
        if h.is_empty() { break; }
        if let Some((k, v)) = h.split_once(':') {
            if k.eq_ignore_ascii_case("content-length") { len = v.trim().parse().unwrap_or(0); }
        }
    }
    if len > 64 << 20 { return Err("request too large".into()); }
    let mut body = vec![0; len];
    r.read_exact(&mut body).map_err(|e| e.to_string())?;
    Ok(Request { method, path, body })
}

fn respond(stream: &mut TcpStream, code: u16, ctype: &str, body: &str) -> Result<(), String> {
    let reason = match code { 200 => "OK", 400 => "Bad Request", 404 => "Not Found", _ => "Error" };
    write!(stream, "HTTP/1.1 {code} {reason}\r\nContent-Type: {ctype}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
           body.len()).map_err(|e| e.to_string())
}

fn handle(mut stream: TcpStream, eng: &mut Engine, ctx: &mut LlamaContext, name: &str) -> Result<(), String> {
    let req = read_request(&mut stream)?;
    match (req.method.as_str(), req.path.split('?').next().unwrap_or("")) {
        ("GET", "/") => respond(&mut stream, 200, "text/plain", "Ember runtime is running"),
        ("GET", "/api/tags") => respond(&mut stream, 200, "application/json",
            &json!({"models": [{"name": name, "model": name}]}).to_string()),
        ("POST", "/api/chat") => {
            let body: Value = match serde_json::from_slice(&req.body) {
                Ok(v) => v,
                Err(e) => return respond(&mut stream, 400, "application/json", &json!({"error": format!("bad JSON: {e}")}).to_string()),
            };
            chat(&mut stream, eng, ctx, &body)
        }
        _ => respond(&mut stream, 404, "application/json", &json!({"error": "not found"}).to_string()),
    }
}

fn send_line(stream: &mut TcpStream, v: &Value) -> bool {
    let mut s = v.to_string();
    s.push('\n');
    stream.write_all(s.as_bytes()).and_then(|_| stream.flush()).is_ok()
}

fn chat(stream: &mut TcpStream, eng: &mut Engine, ctx: &mut LlamaContext, body: &Value) -> Result<(), String> {
    // `think: true` lets the model reason first; otherwise thinking models get the empty block.
    let think = body["think"].as_bool().unwrap_or(false) || !eng.thinking;
    let messages = body["messages"].as_array().map(|v| v.as_slice()).unwrap_or(&[]);
    let tools = body["tools"].as_array().map(|v| v.as_slice()).unwrap_or(&[]);
    let text = if eng.qwen {
        prompt::build(messages, tools, think)
    } else {
        match prompt::build_jinja(&eng.template, messages, tools, body["think"].as_bool().unwrap_or(false), &eng.bos, &eng.eos) {
            Ok(t) => t,
            Err(e) => {
                write!(stream, "HTTP/1.1 200 OK\r\nContent-Type: application/x-ndjson\r\nConnection: close\r\n\r\n").map_err(|e| e.to_string())?;
                send_line(stream, &json!({"error": format!("This model can't be used: {e}")}));
                return Ok(());
            }
        }
    };
    // (Templates that write the BOS token's text get the real token: specials are parsed when tokenizing.)
    let opts = &body["options"];
    let temperature = opts["temperature"].as_f64().unwrap_or(0.6) as f32;
    let top_k = opts["top_k"].as_i64().unwrap_or(20) as i32;
    let top_p = opts["top_p"].as_f64().unwrap_or(0.95) as f32;
    let max_new = opts["num_predict"].as_i64().filter(|n| *n > 0).unwrap_or(8192) as usize;
    let stream_mode = body["stream"].as_bool().unwrap_or(true);

    let vocab = eng.model.vocab();
    let tokens = vocab.tokenize(text.as_bytes(), false, true);
    let n_ctx = ctx.n_ctx() as usize;
    if tokens.len() + 64 > n_ctx {
        let msg = format!("The conversation is too long for the model's memory ({} of {} tokens). Start a new chat or raise the context size.",
                          tokens.len(), n_ctx);
        write!(stream, "HTTP/1.1 200 OK\r\nContent-Type: application/x-ndjson\r\nConnection: close\r\n\r\n").map_err(|e| e.to_string())?;
        send_line(stream, &json!({"error": msg}));
        return Ok(());
    }
    write!(stream, "HTTP/1.1 200 OK\r\nContent-Type: application/x-ndjson\r\nConnection: close\r\n\r\n").map_err(|e| e.to_string())?;

    // Reuse the KV cache for the part of the prompt we've already processed.
    let mut keep = eng.cache.iter().zip(&tokens).take_while(|(a, b)| a == b).count();
    if keep == tokens.len() { keep -= 1; } // always decode at least one token to get fresh logits
    if ctx.clear_kv_cache_seq(Some(0), Some(keep as u32), None).ok() != Some(true) {
        ctx.clear_kv_cache();
        keep = 0;
    }
    eng.cache.truncate(keep);

    let n_batch = 512usize;
    let mut batch = LlamaBatch::new(n_batch, 1);
    let mut pos = keep;
    while pos < tokens.len() {
        batch.clear();
        let end = (pos + n_batch).min(tokens.len());
        for (i, t) in tokens[pos..end].iter().enumerate() {
            let p = pos + i;
            batch.add(*t, p as i32, &[0], p == tokens.len() - 1).map_err(|e| e.to_string())?;
        }
        ctx.decode(&mut batch).map_err(|e| { eng.cache.clear(); format!("decode: {e}") })?;
        eng.cache.extend_from_slice(&tokens[pos..end]);
        pos = end;
    }

    let mut sampler = if temperature <= 0.0 {
        LlamaSampler::greedy()
    } else {
        LlamaSampler::chain_simple([
            LlamaSampler::top_k(top_k),
            LlamaSampler::top_p(top_p, 1),
            LlamaSampler::temp(temperature),
            LlamaSampler::dist(rand_seed()),
        ])
    };
    let mut out = Streamer::default();
    let mut bytes: Vec<u8> = Vec::new();
    let mut last_idx = batch.n_tokens() - 1;
    let mut n_new = 0;
    let mut alive = true;
    let mut done_reason = "stop";
    while n_new < max_new {
        let tok = sampler.sample(ctx, last_idx);
        sampler.accept(tok);
        if vocab.is_eog(tok) { break; }
        bytes.extend(vocab.token_to_piece(tok, false, None));
        // Only hand over complete UTF-8; a character can be split across tokens.
        let valid = match std::str::from_utf8(&bytes) { Ok(s) => s.len(), Err(e) => e.valid_up_to() };
        if valid > 0 {
            let piece = String::from_utf8_lossy(&bytes[..valid]).into_owned();
            bytes.drain(..valid);
            if piece.contains("<|im_end|>") || piece.contains("<|im_start|>") { break; }
            if let Some(delta) = out.push(&piece) {
                if stream_mode && !send_line(stream, &json!({"message": {"role": "assistant", "content": delta}, "done": false})) {
                    alive = false; // the agent hung up (the creator pressed Stop)
                }
            }
        }
        if !alive { break; }
        batch.clear();
        batch.add(tok, (tokens.len() + n_new) as i32, &[0], true).map_err(|e| e.to_string())?;
        ctx.decode(&mut batch).map_err(|e| { eng.cache.clear(); format!("decode: {e}") })?;
        eng.cache.push(tok);
        last_idx = 0;
        n_new += 1;
        if tokens.len() + n_new + 1 >= n_ctx { done_reason = "length"; break; }
    }
    if n_new >= max_new { done_reason = "length"; }
    if !alive { return Ok(()); }

    let (mut content, mut calls, sent) = out.finish();
    if calls.is_empty() && !eng.qwen {
        calls = other_tool_calls(&content);
        if !calls.is_empty() { content.clear(); }
    }
    // When streaming, whatever wasn't streamed yet (e.g. a tool call we couldn't parse) goes in the last line.
    let content = if stream_mode { content.get(sent..).unwrap_or("").to_string() } else { content };
    let calls: Vec<Value> = calls.into_iter()
        .map(|(name, args)| json!({"function": {"name": name, "arguments": args}})).collect();
    let mut msg = json!({"role": "assistant", "content": content});
    if !calls.is_empty() { msg["tool_calls"] = Value::Array(calls); }
    send_line(stream, &json!({"message": msg, "done": true, "done_reason": done_reason,
                              "prompt_eval_count": tokens.len() - keep, "eval_count": n_new}));
    Ok(())
}

/// Tool calls in the other common formats: Mistral's `[TOOL_CALLS][{...}]` and Llama 3's bare
/// `{"name": ..., "parameters": {...}}` reply.
fn other_tool_calls(text: &str) -> Vec<(String, Value)> {
    let t = text.trim();
    let t = t.strip_prefix("<|python_tag|>").unwrap_or(t).trim();
    let json_part = t.find("[TOOL_CALLS]").map(|i| t[i + "[TOOL_CALLS]".len()..].trim()).unwrap_or(t);
    let Ok(v) = serde_json::from_str::<Value>(json_part) else { return vec![] };
    let items = match v { Value::Array(a) => a, o @ Value::Object(_) => vec![o], _ => return vec![] };
    items.into_iter().filter_map(|c| {
        let name = c["name"].as_str()?.to_string();
        let args = match c.get("arguments").or_else(|| c.get("parameters")) {
            Some(Value::String(s)) => serde_json::from_str(s).unwrap_or(json!({})),
            Some(o @ Value::Object(_)) => o.clone(),
            _ => json!({}),
        };
        Some((name, args))
    }).collect()
}

fn rand_seed() -> u32 {
    std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.subsec_nanos() ^ d.as_secs() as u32).unwrap_or(42)
}

/// Splits the model's output into plain text (streamed as it comes) and <tool_call> blocks
/// (held back, parsed at the end). Text that might be the start of a tag is held until it's clear.
#[derive(Default)]
struct Streamer {
    all: String,
    sent: usize,
    in_calls: bool,
}

const OPEN: &str = "<tool_call>";

impl Streamer {
    fn push(&mut self, piece: &str) -> Option<String> {
        self.all.push_str(piece);
        if self.in_calls { return None; }
        let rest = &self.all[self.sent..];
        let upto = if let Some(i) = rest.find(OPEN) {
            self.in_calls = true;
            i
        } else {
            // Hold back a trailing "<tool_c..." that could still become the tag.
            let mut cut = rest.len();
            for k in (1..OPEN.len()).rev() {
                if rest.len() >= k && rest.is_char_boundary(rest.len() - k) && OPEN.starts_with(&rest[rest.len() - k..]) {
                    cut = rest.len() - k;
                    break;
                }
            }
            cut
        };
        if upto == 0 { return None; }
        let delta = rest[..upto].to_string();
        self.sent += upto;
        Some(delta)
    }

    /// (full visible text, parsed tool calls). Unparseable tool calls stay in the text, where the
    /// agent's own text-tool-call fallback can still pick them up.
    fn finish(self) -> (String, Vec<(String, Value)>, usize) {
        let sent = self.sent;
        let Some(start) = self.all.find(OPEN) else { return (self.all, vec![], sent) };
        let mut text = self.all[..start].trim_end().to_string();
        let mut calls = Vec::new();
        let mut rest = &self.all[start..];
        while let Some(i) = rest.find(OPEN) {
            let after = &rest[i + OPEN.len()..];
            let (inner, next) = match after.find("</tool_call>") {
                Some(j) => (&after[..j], &after[j + "</tool_call>".len()..]),
                None => (after, ""),
            };
            match serde_json::from_str::<Value>(inner.trim()) {
                Ok(v) if v["name"].is_string() => {
                    let args = match &v["arguments"] {
                        Value::String(s) => serde_json::from_str(s).unwrap_or(json!({})),
                        Value::Null => json!({}),
                        other => other.clone(),
                    };
                    calls.push((v["name"].as_str().unwrap().to_string(), args));
                }
                _ => { text.push_str(&rest[i..]); return (text, calls, sent); }
            }
            rest = next;
        }
        let tail = rest.trim();
        if !tail.is_empty() { text.push_str("\n"); text.push_str(tail); }
        (text, calls, sent)
    }
}
