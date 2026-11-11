//! Builds the prompt text exactly like Hugging Face's Qwen3 chat template (the one Ember was
//! fine-tuned with via `tokenizer.apply_chat_template(..., enable_thinking=False)`).
//! Messages arrive in Ollama's shape: {role, content, tool_calls:[{function:{name, arguments}}]}.
//! Checked against the real template by training/check_runtime_prompt.py.

use serde_json::Value;

/// JSON the way Python's json.dumps writes it (", " and ": " separators, non-ASCII kept),
/// which is what the template's `tojson` filter produced at training time.
pub fn py_json(v: &Value, out: &mut String) {
    match v {
        Value::Object(m) => {
            out.push('{');
            for (i, (k, v)) in m.iter().enumerate() {
                if i > 0 { out.push_str(", "); }
                out.push_str(&Value::String(k.clone()).to_string());
                out.push_str(": ");
                py_json(v, out);
            }
            out.push('}');
        }
        Value::Array(a) => {
            out.push('[');
            for (i, v) in a.iter().enumerate() {
                if i > 0 { out.push_str(", "); }
                py_json(v, out);
            }
            out.push(']');
        }
        Value::Number(n) => {
            // Python prints floats like 1.0, serde like 1.0 as well; integers the same.
            out.push_str(&n.to_string())
        }
        other => out.push_str(&other.to_string()),
    }
}

/// json.dumps(v, indent=n): one item per line, "," + newline between items, ": " after keys.
fn py_json_indent(v: &Value, n: usize, depth: usize, out: &mut String) {
    let pad = |d: usize, out: &mut String| { out.push('\n'); out.push_str(&" ".repeat(n * d)); };
    match v {
        Value::Object(m) if !m.is_empty() => {
            out.push('{');
            for (i, (k, v)) in m.iter().enumerate() {
                if i > 0 { out.push(','); }
                pad(depth + 1, out);
                out.push_str(&Value::String(k.clone()).to_string());
                out.push_str(": ");
                py_json_indent(v, n, depth + 1, out);
            }
            pad(depth, out);
            out.push('}');
        }
        Value::Array(a) if !a.is_empty() => {
            out.push('[');
            for (i, v) in a.iter().enumerate() {
                if i > 0 { out.push(','); }
                pad(depth + 1, out);
                py_json_indent(v, n, depth + 1, out);
            }
            pad(depth, out);
            out.push(']');
        }
        other => py_json(other, out),
    }
}

fn sorted(v: &Value) -> Value {
    match v {
        Value::Object(m) => {
            let mut keys: Vec<&String> = m.keys().collect();
            keys.sort();
            Value::Object(keys.into_iter().map(|k| (k.clone(), sorted(&m[k]))).collect())
        }
        Value::Array(a) => Value::Array(a.iter().map(sorted).collect()),
        other => other.clone(),
    }
}

fn content(m: &Value) -> String {
    match &m["content"] {
        Value::String(s) => s.clone(),
        Value::Null => String::new(),
        other => other.to_string(),
    }
}

pub fn build(messages: &[Value], tools: &[Value], think: bool) -> String {
    let mut s = String::new();
    let first_system = messages.first().filter(|m| m["role"] == "system");
    if !tools.is_empty() {
        s.push_str("<|im_start|>system\n");
        if let Some(m) = first_system {
            s.push_str(&content(m));
            s.push_str("\n\n");
        }
        s.push_str("# Tools\n\nYou may call one or more functions to assist with the user query.\n\n\
                    You are provided with function signatures within <tools></tools> XML tags:\n<tools>");
        for t in tools {
            s.push('\n');
            // Tool definitions were alphabetized in Ember's training data (they came from rustic-agent's
            // --print-tools before key order was preserved); arguments keep the model's own order.
            py_json(&sorted(t), &mut s);
        }
        s.push_str("\n</tools>\n\nFor each function call, return a json object with function name and arguments within \
                    <tool_call></tool_call> XML tags:\n<tool_call>\n{\"name\": <function-name>, \"arguments\": <args-json-object>}\n</tool_call><|im_end|>\n");
    } else if let Some(m) = first_system {
        s.push_str("<|im_start|>system\n");
        s.push_str(&content(m));
        s.push_str("<|im_end|>\n");
    }

    // The last real user question (tool results are sent as user turns wrapped in <tool_response>).
    let last_query = messages.iter().enumerate().rev()
        .find(|(_, m)| {
            m["role"] == "user" && {
                let c = content(m);
                !(c.starts_with("<tool_response>") && c.ends_with("</tool_response>"))
            }
        })
        .map(|(i, _)| i);

    let n = messages.len();
    for (i, m) in messages.iter().enumerate() {
        let role = m["role"].as_str().unwrap_or("");
        match role {
            "system" if i == 0 => {}
            "user" | "system" => {
                s.push_str(&format!("<|im_start|>{role}\n{}<|im_end|>\n", content(m)));
            }
            "assistant" => {
                let mut c = content(m);
                let mut reasoning = m["thinking"].as_str().unwrap_or("").to_string();
                if let Some(idx) = c.rfind("</think>") {
                    let before = &c[..idx];
                    reasoning = before.rsplit("<think>").next().unwrap_or("").trim_matches('\n').to_string();
                    c = c[idx + "</think>".len()..].trim_start_matches('\n').to_string();
                }
                let after_query = last_query.is_none_or(|q| i > q);
                if after_query && (i == n - 1 || !reasoning.is_empty()) {
                    s.push_str(&format!("<|im_start|>assistant\n<think>\n{}\n</think>\n\n{}",
                                        reasoning.trim_matches('\n'), c.trim_start_matches('\n')));
                } else {
                    s.push_str("<|im_start|>assistant\n");
                    s.push_str(&c);
                }
                if let Some(calls) = m["tool_calls"].as_array() {
                    for (j, call) in calls.iter().enumerate() {
                        if (j == 0 && !c.is_empty()) || j > 0 { s.push('\n'); }
                        let f = if call["function"].is_object() { &call["function"] } else { call };
                        s.push_str("<tool_call>\n{\"name\": \"");
                        s.push_str(f["name"].as_str().unwrap_or(""));
                        s.push_str("\", \"arguments\": ");
                        match &f["arguments"] {
                            Value::String(a) => s.push_str(a),
                            Value::Null => s.push_str("{}"),
                            other => py_json(other, &mut s),
                        }
                        s.push_str("}\n</tool_call>");
                    }
                }
                s.push_str("<|im_end|>\n");
            }
            "tool" => {
                let prev_tool = i > 0 && messages[i - 1]["role"] == "tool";
                let next_tool = i + 1 < n && messages[i + 1]["role"] == "tool";
                if !prev_tool { s.push_str("<|im_start|>user"); }
                s.push_str("\n<tool_response>\n");
                s.push_str(&content(m));
                s.push_str("\n</tool_response>");
                if !next_tool { s.push_str("<|im_end|>\n"); }
            }
            _ => {}
        }
    }
    s.push_str("<|im_start|>assistant\n");
    if !think { s.push_str("<think>\n\n</think>\n\n"); }
    s
}

/// Is this the Qwen-style ChatML + <tool_call> format? Then `build` reproduces it exactly
/// (byte-for-byte what Ember was trained on). Anything else goes through the model's own template.
pub fn is_qwen_style(template: &str) -> bool {
    // Qwen3 and its fine-tunes (like Ember). Qwen2.5 looks similar but lays the prompt out differently,
    // so it uses its own template like any other model.
    template.is_empty() || (template.contains("<|im_start|>") && template.contains("<tool_call>") && template.contains("enable_thinking"))
}

/// Render the model's own Jinja chat template (stored in the GGUF), the way Hugging Face's
/// apply_chat_template does: messages in OpenAI shape, tools, add_generation_prompt.
pub fn build_jinja(template: &str, messages: &[Value], tools: &[Value], think: bool,
                   bos: &str, eos: &str) -> Result<String, String> {
    let mut env = minijinja::Environment::new();
    minijinja_contrib::add_to_environment(&mut env);
    env.set_unknown_method_callback(minijinja_contrib::pycompat::unknown_method_callback);
    env.add_function("raise_exception", |msg: String| -> Result<String, minijinja::Error> {
        Err(minijinja::Error::new(minijinja::ErrorKind::InvalidOperation, msg))
    });
    // Python's json.dumps style, like Hugging Face's tojson (minijinja's own is compact and HTML-escaped).
    env.add_filter("tojson", |v: minijinja::Value, kwargs: minijinja::value::Kwargs| -> Result<String, minijinja::Error> {
        let indent: Option<usize> = kwargs.get("indent")?;
        let _: Option<bool> = kwargs.get("ensure_ascii")?;
        let _: Option<bool> = kwargs.get("sort_keys")?;
        kwargs.assert_all_used()?;
        let j = serde_json::to_value(&v).map_err(|e| minijinja::Error::new(minijinja::ErrorKind::InvalidOperation, e.to_string()))?;
        let mut out = String::new();
        match indent {
            Some(n) => py_json_indent(&j, n, 0, &mut out),
            None => py_json(&j, &mut out),
        }
        Ok(out)
    });
    env.add_function("strftime_now", |_fmt: String| -> String { "26 Jul 2026".to_string() });
    env.add_template("chat", template).map_err(|e| format!("the model's chat template doesn't parse: {e}"))?;

    // OpenAI-style messages: arguments as objects (most templates call |tojson on them),
    // and ids that link tool results to their calls (some templates require them).
    let mut n = 0;
    let mut pending: Vec<String> = vec![];
    let msgs: Vec<Value> = messages.iter().map(|m| {
        let mut m = m.clone();
        if let Some(calls) = m["tool_calls"].as_array_mut() {
            for c in calls.iter_mut() {
                n += 1;
                let id = format!("call{n:06}");
                pending.push(id.clone());
                let f = if c["function"].is_object() { c["function"].clone() } else { c.clone() };
                *c = serde_json::json!({"id": id, "type": "function", "function": f});
            }
        }
        if m["role"] == "tool" && m.get("tool_call_id").is_none() && !pending.is_empty() {
            m["tool_call_id"] = Value::String(pending.remove(0));
        }
        if m["content"].is_null() { m["content"] = Value::String(String::new()); }
        m
    }).collect();
    let ctx = minijinja::context! {
        messages => minijinja::Value::from_serialize(&msgs),
        tools => if tools.is_empty() { minijinja::Value::from(()) } else { minijinja::Value::from_serialize(tools) },
        add_generation_prompt => true,
        enable_thinking => think,
        bos_token => bos,
        eos_token => eos,
    };
    env.get_template("chat").unwrap().render(ctx).map_err(|e| format!("the model's chat template failed: {e}"))
}
