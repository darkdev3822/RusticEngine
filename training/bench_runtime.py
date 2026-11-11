"""Benchmark ember-runtime builds (CUDA / Vulkan / CPU) on a realistic Ember request.

Usage: python3 bench_runtime.py RUNTIME_BINARY [MODEL.gguf] [--gpu-layers N]
Measures: load time, time to first token on a cold ~10k-token prompt (system prompt + tools),
generation speed, and time to first token on a follow-up turn (KV cache reuse).
"""
import json, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
binary = sys.argv[1]
model = next((a for a in sys.argv[2:] if a.endswith(".gguf")), str(ROOT / "engine/bin/models/ember.gguf"))
extra = sys.argv[sys.argv.index("--gpu-layers"):sys.argv.index("--gpu-layers") + 2] if "--gpu-layers" in sys.argv else []

agent = str(ROOT / "engine/bin/rustic-agent")
system = subprocess.run([agent, "--print-system", "--project", str(ROOT / "sandbox/hello")], capture_output=True, text=True).stdout
tools = json.loads(subprocess.run([agent, "--print-tools"], capture_output=True, text=True).stdout)

t0 = time.time()
p = subprocess.Popen([binary, "--model", model, "--ctx", "16384", *extra], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
ready = json.loads(p.stdout.readline())
load = time.time() - t0
url = f"http://127.0.0.1:{ready['port']}/api/chat"


def ask(messages):
    body = json.dumps({"model": "x", "messages": messages, "tools": tools, "stream": True,
                       "options": {"temperature": 0, "num_predict": 200}}).encode()
    start = time.time()
    first, text, final = None, "", {}
    with urllib.request.urlopen(urllib.request.Request(url, body, {"content-type": "application/json"})) as r:
        for line in r:
            v = json.loads(line)
            if v.get("error"): raise SystemExit(v["error"])
            c = v.get("message", {}).get("content", "")
            if c and first is None: first = time.time()
            text += c
            if v.get("done"): final = v
    end = time.time()
    first = first or end
    n = final.get("eval_count", 0)
    return {"prompt_tokens": final.get("prompt_eval_count"), "ttft_s": round(first - start, 2),
            "gen_tok_s": round(n / max(end - first, 1e-6), 1), "tokens": n}, text


try:
    msgs = [{"role": "system", "content": system},
            {"role": "user", "content": "Explain what delta time is and why my player moves faster on a fast computer. Keep it short."}]
    cold, reply = ask(msgs)
    msgs += [{"role": "assistant", "content": reply}, {"role": "user", "content": "Thanks! Where would I use it in my player code?"}]
    warm, _ = ask(msgs)
    print(json.dumps({"binary": Path(binary).parent.parent.name, "gpu": ready.get("gpu"), "ctx": ready.get("ctx"), "load_s": round(load, 1),
                      "cold": cold, "follow_up": warm}))
finally:
    p.kill()
