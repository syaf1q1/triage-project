# Training settings (Unsloth Studio)

- Run: 1795741468 (Unsloth Studio, PEFT 0.18.1)
- Base: unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit (4-bit QLoRA)
- LoRA: rank 32, alpha 32, dropout 0.05, all linear layers (q,k,v,o,gate,up,down)
- Epochs: 3, 357 steps (checkpoint every 118 steps) | LR 0.0001 cosine, 20 warmup | seed 3407
- Batch 2 x grad-accum 4 (effective 8) | AdamW 8-bit, weight decay 0.01 | max_seq_length 2048
- Dataset: data/train_chat_v6_merged.jsonl (994 examples)
- Result: final training loss 0.0003, elapsed 1 h 12 min 24 s, 427,416 tokens
