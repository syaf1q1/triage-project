# Triage score report

Test cases: 50 (standard 30, hard 20).
Wrong or unreadable answers count as wrong. Recall matters most for `needs_human`: a missed case reaches no person.

## All test cases

| Measure | tuned |
|---|---|
| Valid JSON in the right shape | 100% |
| Only the JSON, no extra text | 100% |
| Category correct | 100% |
| Urgency correct | 94% |
| needs_human correct | 96% |
| needs_human recall (missed a case that needs a person?) | 95% |
| needs_human precision | 95% |
| All three fields correct | 94% |

## Standard cases

| Measure | tuned |
|---|---|
| Valid JSON in the right shape | 100% |
| Only the JSON, no extra text | 100% |
| Category correct | 100% |
| Urgency correct | 93% |
| needs_human correct | 97% |
| needs_human recall (missed a case that needs a person?) | 91% |
| needs_human precision | 100% |
| All three fields correct | 93% |

## Hard cases (Malay, two issues, tone, an order inside the message)

| Measure | tuned |
|---|---|
| Valid JSON in the right shape | 100% |
| Only the JSON, no extra text | 100% |
| Category correct | 100% |
| Urgency correct | 95% |
| needs_human correct | 95% |
| needs_human recall (missed a case that needs a person?) | 100% |
| needs_human precision | 89% |
| All three fields correct | 95% |

## tuned: where it went wrong

- Urgency mistakes, gold->answer: high->medium x1, medium->high x1, medium->low x1

First wrong cases (3 of 3):

- X017 (standard): gold ['payment_billing', 'high', True], got ['payment_billing', 'medium', False]. "My card was charged but the order page says payment failed and there is no order in my his"
- X021 (standard): gold ['account_access', 'medium', False], got ['account_access', 'low', False]. "I forgot which email I used to register. Can you look it up with my phone number?"
- X048 (hard): gold ['refund_return', 'medium', False], got ['refund_return', 'high', True]. "I will leave a 1-star review everywhere unless my refund of RM60 is processed."

## Read this before you trust a number

- 50 test cases is small: one case is 2 points. A change of a few points is noise, not a result.
- Do not tune on these cases. If you read them to change your training data, they are no longer a test.
- Run the base model and the tuned model with the same prompt and the same settings.
