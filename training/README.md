# Optional LogicForge LoRA tuning

This is real supervised fine-tuning of an open-weight model with a LoRA adapter. It does **not** modify GitHub Copilot's hosted models. LogicForge does not silently save prompts; only place examples you reviewed and chose to include in `data/approved.jsonl`.

The checked-in `approved.jsonl` currently has no examples. The trainer intentionally refuses to run until it has at least 20 approved records. That minimum only protects against an accidental empty/tiny run; it is not enough to establish quality. Start with 100+ varied, carefully reviewed examples, keep a separate held-out test set, and compare the base model with the tuned model on the same prompts before relying on an adapter.

## Prepare examples

Use one JSON object per line, each with a `messages` array. Include the user's rough logic and a high-quality LogicForge answer with the code, preserved identifiers, and useful explanation. Use examples you have rights to use. Start with at least 20 for the script's guardrail; 100 or more varied and carefully reviewed examples are a better starting point. Reserve separate examples for evaluation. Do not train on generated answers without reviewing them.

```json
{"messages":[{"role":"user","content":"When key w is down set move_forward true and move the character by speed * delta_time."},{"role":"assistant","content":"```python\ndef handle_keyboard_input(event):\n    move_forward = event.key == 'w'\n    if move_forward:\n        calculate_character_movement(move_forward)\n```\n\nIntent match\nYES ..."}]}
```

## Train

Use a separate Python environment with a supported PyTorch build. Training requires downloading the base model and enough RAM/VRAM; CPU training can be very slow. GPU setup varies by hardware, so install the matching PyTorch build from its official instructions before installing this file's remaining requirements.

```powershell
cd training
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python finetune_lora.py --data data/approved.jsonl --output output
```

The script uses TRL `SFTTrainer` and PEFT LoRA, creates a deterministic 90/10 train/evaluation split, and saves the adapter under `output/adapter`. Review evaluation loss and test the adapter on held-out examples; low training loss alone does not establish quality.

## Serve through Ollama

Use the exact same base model family and revision used for training. Install Ollama, pull the matching supported base model, then create a `Modelfile` in this folder:

```text
FROM qwen2.5-coder:1.5b
ADAPTER ./output/adapter
```

Create and test the Ollama model:

```powershell
ollama create logicforge-tuned -f Modelfile
ollama run logicforge-tuned
```

In a second terminal, configure LogicForge before starting it:

```powershell
$env:LOGICFORGE_PROVIDER = "ollama"
$env:OLLAMA_CHAT_MODEL = "logicforge-tuned"
python app.py
```

The app calls Ollama locally for generation, independent review, and a conditional repair pass. RAG embeddings also use local Ollama (`nomic-embed-text`) when available. Without that embedding model running, retrieval falls back to built-in local TF-IDF. To return to Copilot, use `$env:LOGICFORGE_PROVIDER = "copilot"` or unset the variable. Ollama's `ADAPTER` support expects the adapter to match its `FROM` base; mismatched bases can produce erratic behavior.
