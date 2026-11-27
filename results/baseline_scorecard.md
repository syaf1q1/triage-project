# Baseline scorecard (untuned model)

- **Model:** llama3.1:latest (8B, 4-bit), not fine-tuned
- **Run with:** Ollama, temperature 0, the project's system prompt, no examples
- **Test set:** 100 messages: 24 standard, 76 hard

| Measure | All (100) | Standard (24) | Hard (76) |
|---|---|---|---|
| All three fields correct | 31% | 33% | 30% |
| Category correct | 84% | 71% | 88% |
| Urgency correct | 40% | 38% | 41% |
| needs_human correct | 59% | 58% | 59% |
| needs_human recall | 95% | 87% | 98% |
| needs_human precision | 58% | 62% | 57% |
| Valid JSON in the right shape | 99% | 100% | 99% |
| Only the JSON, no extra text | 9% | 8% | 9% |

A missing or unreadable answer counts as wrong on every field. The model's full responses are in `baseline_scorecard.xlsx` (sheet *Baseline responses*).
