#!/usr/bin/env python3
"""Turn out/ember-merged (fp16 safetensors) into out/ember.gguf for Ollama.

Ollama 0.40 dropped LoRA ADAPTER support and its own quantizer needs MLX (not on Linux),
and cloning llama.cpp isn't an option here. So: reuse every metadata key + the tokenizer
from the stock qwen3:8b GGUF (same architecture, same vocab), and write our merged weights
quantized with gguf-py's numpy quantizers:
  attention q/k/o, ffn_down -> Q5_0 ; ffn_gate/up, token_embd -> Q4_0 ; output -> Q8_0 ;
  norms F32, attn_v F16 (as in the stock file).  ~5.5 GB, fits a 10 GB card at 16k ctx.

Usage: .venv/bin/python to_gguf.py [TEMPLATE_GGUF]   (default: qwen3:8b's blob)
"""
import json, subprocess, sys
from pathlib import Path

import numpy as np
import gguf
from safetensors import safe_open

HERE = Path(__file__).resolve().parent
SRC = HERE / "out/ember-merged"
OUT = HERE / "out/ember.gguf"
Q = gguf.GGMLQuantizationType


def template_path():
    if len(sys.argv) > 1:
        return sys.argv[1]
    mf = subprocess.run(["ollama", "show", "--modelfile", "qwen3:8b"], capture_output=True, text=True, check=True).stdout
    return next(l.split(None, 1)[1].strip() for l in mf.splitlines() if l.startswith("FROM "))


def pick(name: str, stock: "Q") -> "Q":
    if stock in (Q.F32, Q.F16):
        return stock
    if name == "output.weight":
        return Q.Q8_0
    if any(s in name for s in ("ffn_gate", "ffn_up", "token_embd")):
        return Q.Q4_0
    return Q.Q5_0


def main():
    tpl = gguf.GGUFReader(template_path())
    w = gguf.GGUFWriter(str(OUT), arch="qwen3")
    for key, f in tpl.fields.items():
        if key.startswith("GGUF.") or key == "general.architecture":
            continue
        val = f.contents()
        if key == "general.name":
            val = "Rustic Ember 8B"
        if key == "general.file_type":
            val = int(gguf.LlamaFileType.MOSTLY_Q4_0)
        vtype = f.types[0]
        sub = f.types[-1] if vtype == gguf.GGUFValueType.ARRAY else None
        w.add_key_value(key, val, vtype, sub_type=sub)

    index = json.load(open(SRC / "model.safetensors.index.json"))["weight_map"]
    nmap = gguf.get_tensor_name_map(gguf.MODEL_ARCH.QWEN3, 36)
    hf_for = {}
    for hf in index:
        g = nmap.get_name(hf, try_suffixes=(".weight", ".bias"))
        assert g, f"no GGUF name for {hf}"
        hf_for[g] = hf
    stock = {t.name: t.tensor_type for t in tpl.tensors}
    assert set(stock) == set(hf_for), set(stock) ^ set(hf_for)

    handles = {}
    total = 0
    for i, t in enumerate(tpl.tensors):  # keep the stock tensor order
        hf = hf_for[t.name]
        fn = index[hf]
        h = handles.get(fn) or handles.setdefault(fn, safe_open(str(SRC / fn), "np"))
        x = h.get_tensor(hf)
        qt = pick(t.name, t.tensor_type)
        if qt == Q.F32:
            data = x.astype(np.float32)
        elif qt == Q.F16:
            data = x.astype(np.float16)
        else:
            data = gguf.quants.quantize(x.astype(np.float32), qt)
        w.add_tensor(t.name, data, raw_dtype=qt)
        total += data.nbytes
        if i % 40 == 0:
            print(f"{i:3d}/{len(tpl.tensors)} {t.name:28s} {qt.name:5s} {total/2**30:.2f} GiB", flush=True)

    w.write_header_to_file()
    w.write_kv_data_to_file()
    w.write_tensors_to_file(progress=False)
    w.close()
    print(f"wrote {OUT} ({OUT.stat().st_size/2**30:.2f} GiB)")


if __name__ == "__main__":
    main()
