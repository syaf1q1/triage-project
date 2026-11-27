---
base_model: unsloth/Llama-3.1-8B-Instruct-unsloth-bnb-4bit
license: llama3.1
language:
  - en
  - ms
  - zh
  - ta
  - hi
  - es
  - fr
pipeline_tag: text-generation
library_name: peft
tags:
  - unsloth
  - lora
  - qlora
  - text-classification
  - customer-support
---

# Llama-3.1-8B-triage-syafiq11

**Built with Llama.**

## What it does
A QLoRA adapter for Llama 3.1 8B Instruct that triages customer messages for a (fictional) online shop in Malaysia. Given one message, it answers with only this JSON:

```json
{"category": "delivery", "urgency": "high", "needs_human": true}
```

- `category`: delivery, refund_return, product_fault, payment_billing, account_access, general_enquiry
- `urgency`: low, medium, high
- `needs_human`: true, false

## How to use it
Always use the system prompt in [`system_prompt.txt`](system_prompt.txt) and temperature 0.

```python
from unsloth import FastLanguageModel
from huggingface_hub import hf_hub_download

model, tokenizer = FastLanguageModel.from_pretrained(
    "syafiq11/Llama-3.1-8B-triage-syafiq11", max_seq_length=2048, load_in_4bit=True)
FastLanguageModel.for_inference(model)

system = open(hf_hub_download("syafiq11/Llama-3.1-8B-triage-syafiq11", "system_prompt.txt"), encoding="utf-8").read()
messages = [
    {"role": "system", "content": system},
    {"role": "user", "content": "My parcel never arrived and I was charged twice."},
]
inputs = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to(model.device)
output = model.generate(input_ids=inputs, max_new_tokens=64, do_sample=False)
print(tokenizer.decode(output[0][inputs.shape[1]:], skip_special_tokens=True))
```

Ollama (GGUF):
```bash
ollama run hf.co/syafiq11/Llama-3.1-8B-triage-syafiq11-GGUF:Q4_K_M
```

## Training data
994 chat examples: 207 class rows from the course (157 from `train_raw.jsonl`, 50 from `data_starter.xlsx`) and 787 rows added for this project. Languages: English, Malay and Manglish, Chinese, Tamil, Hindi/Hinglish, Spanish, French. No test or leaderboard message appears in the training data. Data and labelling rules: see the GitHub repository.

## Training
- **Method:** QLoRA (LoRA on a 4-bit base), supervised fine-tuning with Unsloth Studio. Chosen because the task is narrow and fixed-format, the data is under 1,000 examples, and training had to fit one rented GPU; the adapter is small and keeps the base model's general ability.
- **Settings:** rank 32, alpha 32, dropout 0.05, all linear layers; 3 epochs (357 steps); learning rate 1e-4, cosine, 20 warmup steps; batch 2 × 4 accumulation; AdamW 8-bit, weight decay 0.01; max length 2048; seed 3407.
- **Run:** 1795741468, 1 h 12 min, final training loss 0.0003; evaluation loss fell from about 0.020 (step 118) to about 0.003 (step 357) with no sign of overfitting.

## Evaluation
Course leaderboard test set: 100 held-out messages (24 standard, 76 hard).

| Model | All three correct | Category | Urgency | needs_human recall | JSON only |
|---|---|---|---|---|---|
| Llama 3.1 8B Instruct (untuned) | 31% | 84% | 40% | 95% | 9% |
| **This model** | see leaderboard (pending) | | | | |

## Limitations and risks
- Fewer training examples in Chinese, Tamil, Hindi, Spanish and French than in English and Malay; other languages are untested.
- Urgency often depends on date arithmetic and contact counts in the message, which can be wrong.
- Not for decisions without human review: a missed high-urgency safety message could cause harm.

## Licence
This model is built on Llama 3.1 and is licensed under the [Llama 3.1 Community License](LICENSE) (see also [`Notice`](Notice)). Use must follow the [Llama 3.1 Acceptable Use Policy](https://llama.meta.com/llama3_1/use-policy).

Code and project repository: https://github.com/syaf1q1/triage-project
