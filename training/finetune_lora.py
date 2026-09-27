"""Optional supervised LoRA tuning for a local LogicForge model.

Expected JSONL record: {"messages":[{"role":"user","content":"..."},
{"role":"assistant","content":"..."}]}. Only human-approved examples
belong in this dataset; this script never collects app requests.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_records(path: Path) -> list[dict]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        record = json.loads(line)
        messages = record.get("messages")
        if not isinstance(messages, list) or len(messages) < 2:
            raise ValueError(f"Line {line_number}: expected at least user and assistant messages")
        if messages[-1].get("role") != "assistant" or not messages[-1].get("content", "").strip():
            raise ValueError(f"Line {line_number}: final message must be a non-empty assistant answer")
        if not any(m.get("role") == "user" and m.get("content", "").strip() for m in messages):
            raise ValueError(f"Line {line_number}: add a non-empty user message")
        rows.append({"messages": messages})
    if len(rows) < 20:
        raise ValueError(f"Need at least 20 reviewed examples; found {len(rows)}. Aim for 100+ varied examples and hold out test cases.")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path(__file__).parent / "data" / "approved.jsonl")
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-Coder-1.5B-Instruct")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "output")
    parser.add_argument("--epochs", type=float, default=2.0)
    args = parser.parse_args()

    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    rows = load_records(args.data)
    split = Dataset.from_list(rows).train_test_split(test_size=max(1, round(len(rows) * 0.1)), seed=42)
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    model = AutoModelForCausalLM.from_pretrained(args.base_model, device_map="auto")
    peft_config = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
        target_modules="all-linear",
    )
    training_args = SFTConfig(
        output_dir=str(args.output / "checkpoints"), num_train_epochs=args.epochs,
        per_device_train_batch_size=1, gradient_accumulation_steps=8,
        learning_rate=2e-4, logging_steps=5, eval_strategy="epoch",
        save_strategy="epoch", load_best_model_at_end=True,
        report_to="none", max_length=4096, assistant_only_loss=True,
    )
    trainer = SFTTrainer(
        model=model, args=training_args, train_dataset=split["train"],
        eval_dataset=split["test"], processing_class=tokenizer, peft_config=peft_config,
    )
    trainer.train()
    args.output.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(args.output / "adapter"))
    tokenizer.save_pretrained(str(args.output / "adapter"))
    print(f"Saved LoRA adapter to {args.output / 'adapter'}; inspect eval metrics before using it.")


if __name__ == "__main__":
    main()
