#!/usr/bin/env python3
"""Merge out/ember-lora into the already-downloaded 4-bit base and write fp16 safetensors
to out/ember-merged, for `ollama create --quantize`. Works layer by layer, so it never needs
the 16 GB full-precision base download or more than ~1 GB of GPU memory at a time.

Usage: HF_HOME=hf-cache HF_HUB_OFFLINE=1 .venv/bin/python merge.py
"""
import json, shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
LORA = HERE / "out/ember-lora"
OUT = HERE / "out/ember-merged"


def main():
    import torch
    from unsloth import FastLanguageModel
    import bitsandbytes.functional as bnbf
    from safetensors.torch import save_file

    model, tok = FastLanguageModel.from_pretrained(str(LORA), max_seq_length=2048, load_in_4bit=True, dtype=None)
    cfg = json.load(open(LORA / "adapter_config.json"))
    scale = cfg["lora_alpha"] / cfg["r"]
    base = model.get_base_model() if hasattr(model, "get_base_model") else model

    def weight_of(mod):
        w = mod.weight
        if getattr(w, "quant_state", None) is not None:
            return bnbf.dequantize_4bit(w.data, w.quant_state).to(torch.float16)
        return w.data.to(torch.float16)

    OUT.mkdir(parents=True, exist_ok=True)
    shard, shard_bytes, n, index = {}, 0, 0, {}

    def flush():
        nonlocal shard, shard_bytes, n
        if not shard:
            return
        n += 1
        name = f"model-{n:05d}.safetensors"
        save_file(shard, str(OUT / name), metadata={"format": "pt"})
        for k in shard:
            index[k] = name
        shard, shard_bytes = {}, 0

    def put(key, t):
        nonlocal shard_bytes
        t = t.detach().to("cpu", torch.float16).contiguous()
        shard[key] = t
        shard_bytes += t.numel() * 2
        if shard_bytes > 2 << 30:
            flush()

    merged = 0
    done = set()
    for name, mod in base.named_modules():
        if hasattr(mod, "lora_A") and hasattr(mod, "base_layer"):
            W = weight_of(mod.base_layer).float()
            A = mod.lora_A["default"].weight.float()
            B = mod.lora_B["default"].weight.float()
            W += scale * (B @ A)
            key = name.replace("base_model.model.", "") + ".weight"
            put(key, W)
            if mod.base_layer.bias is not None:
                put(key[:-7] + ".bias", mod.base_layer.bias)
            done.add(name)
            merged += 1
            del W
    # Everything else (embeddings, norms, lm_head, non-LoRA linears).
    for name, mod in base.named_modules():
        if any(name == d or name.startswith(d + ".") for d in done):
            continue
        for pname, p in mod.named_parameters(recurse=False):
            key = (name + "." + pname).replace("base_model.model.", "")
            if pname == "weight" and getattr(p, "quant_state", None) is not None:
                put(key, weight_of(mod))
            else:
                put(key, p)
    flush()
    json.dump({"metadata": {}, "weight_map": index}, open(OUT / "model.safetensors.index.json", "w"), indent=1)
    base.config.torch_dtype = "float16"
    base.config.quantization_config = None
    cfgd = base.config.to_dict()
    cfgd.pop("quantization_config", None)
    cfgd.pop("dtype", None)
    cfgd.update(architectures=["Qwen3ForCausalLM"], model_type="qwen3", torch_dtype="float16")  # Unsloth leaves these out
    json.dump(cfgd, open(OUT / "config.json", "w"), indent=2)
    tok.save_pretrained(str(OUT))
    for f in ("generation_config.json",):
        src = next((HERE / "hf-cache/hub").glob(f"models--unsloth--Qwen3-8B-unsloth-bnb-4bit/snapshots/*/{f}"), None)
        if src:
            shutil.copy(src, OUT / f)
    print(f"merged {merged} LoRA layers; {len(index)} tensors in {n} shards -> {OUT}")


if __name__ == "__main__":
    main()
