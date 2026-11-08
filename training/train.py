#!/usr/bin/env python3
"""Fine-tune Ember: QLoRA on Qwen3-8B with Unsloth, on data/train.jsonl.

Only Ember's own turns are learned (user messages and tool results are masked out).
Output: out/ember-lora (LoRA adapter + tokenizer)

Usage: HF_HOME=hf-cache .venv/bin/python train.py [--epochs N] [--max-len N] [--check]
"""
import argparse, json, os
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = "unsloth/Qwen3-8B-unsloth-bnb-4bit"


def load(path):
    return [json.loads(l) for l in open(path)]


def render(tok, sample):
    msgs = []
    for m in sample["messages"]:
        m = dict(m)
        if m["role"] == "tool":
            m.pop("name", None)
        if m["role"] == "assistant" and not m.get("tool_calls"):
            m.pop("tool_calls", None)
        msgs.append(m)
    return tok.apply_chat_template(msgs, tools=sample["tools"], tokenize=False, enable_thinking=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--max-len", type=int, default=6144)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--resume", action="store_true", help="continue from the last checkpoint in out/checkpoints")
    ap.add_argument("--check", action="store_true", help="only render + measure the dataset")
    args = ap.parse_args()

    # Ollama keeps models in VRAM for a while after use; training needs the whole card.
    import subprocess
    ps = subprocess.run(["ollama", "ps"], capture_output=True, text=True).stdout.splitlines()[1:]
    for line in ps:
        if line.split():
            subprocess.run(["ollama", "stop", line.split()[0]], capture_output=True)

    from unsloth import FastLanguageModel  # noqa: E402  (must import before transformers)
    from unsloth.chat_templates import train_on_responses_only
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer

    model, tok = FastLanguageModel.from_pretrained(BASE, max_seq_length=args.max_len, load_in_4bit=True,
                                                   dtype=None) if not args.check else (None, None)
    if args.check:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(BASE)

    train = load(HERE / "data/train.jsonl")
    evals = load(HERE / "data/eval.jsonl")
    tr_texts = [render(tok, s) for s in train]
    ev_texts = [render(tok, s) for s in evals]
    lens = sorted(len(tok(t).input_ids) for t in tr_texts)
    print(f"train {len(tr_texts)} samples; tokens: median {lens[len(lens)//2]}, p95 {lens[int(len(lens)*.95)]}, max {lens[-1]}, "
          f"total {sum(lens)}; over max-len: {sum(l > args.max_len for l in lens)}")
    if args.check:
        print(tr_texts[0][-2500:])
        return

    # Drop anything that wouldn't fit rather than training on a cut-off conversation.
    keep = [t for t in tr_texts if len(tok(t).input_ids) <= args.max_len]
    ev_keep = [t for t in ev_texts if len(tok(t).input_ids) <= args.max_len]

    model = FastLanguageModel.get_peft_model(
        model, r=args.rank, lora_alpha=args.rank, lora_dropout=0, bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth", random_state=3407)

    trainer = SFTTrainer(
        model=model, tokenizer=tok,
        train_dataset=Dataset.from_dict({"text": keep}),
        args=SFTConfig(
            dataset_text_field="text", max_seq_length=args.max_len, packing=False,
            per_device_train_batch_size=1, gradient_accumulation_steps=8,
            num_train_epochs=args.epochs, learning_rate=args.lr, lr_scheduler_type="cosine", warmup_ratio=0.05,
            weight_decay=0.01, optim="adamw_8bit", bf16=True, logging_steps=5,
            eval_strategy="no", save_strategy="steps", save_steps=20, save_total_limit=2,  # eval pass OOMs on 10 GB
            output_dir=str(HERE / "out/checkpoints"), report_to="none", seed=3407),
    )
    # Learn only Ember's turns: everything after "<|im_start|>assistant\n" up to the next user/tool turn.
    trainer = train_on_responses_only(trainer, instruction_part="<|im_start|>user\n",
                                      response_part="<|im_start|>assistant\n")
    stats = trainer.train(resume_from_checkpoint=args.resume or None)
    print(stats)
    out = HERE / "out/ember-lora"
    model.save_pretrained(str(out))
    tok.save_pretrained(str(out))
    print("saved", out)


if __name__ == "__main__":
    main()
