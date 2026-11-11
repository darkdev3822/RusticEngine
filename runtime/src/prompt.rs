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
