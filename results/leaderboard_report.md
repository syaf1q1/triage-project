# Triage score report

Test cases: 100 course leaderboard messages. Labels: our own, written with the course labelling guide (`data/leaderboard_labels_ours.jsonl`), not the instructor's official answer key. Check: with these labels the base model's answers score exactly the official baseline scorecard (31% / 84% / 40% / 59% / 95% / 58% / 99% / 9%).
Wrong or unreadable answers count as wrong. Recall matters most for `needs_human`: a missed case reaches no person.

## All test cases

| Measure | base | tuned | change |
|---|---|---|---|
| Valid JSON in the right shape | 99% | 99% | +0 points |
| Only the JSON, no extra text | 9% | 99% | +90 points |
| Category correct | 84% | 92% | +8 points |
| Urgency correct | 40% | 90% | +50 points |
| needs_human correct | 59% | 79% | +20 points |
| needs_human recall (missed a case that needs a person?) | 95% | 73% | -22 points |
| needs_human precision | 58% | 87% | +29 points |
| All three fields correct | 31% | 71% | +40 points |


## Hard cases (Malay, two issues, tone, an order inside the message)

| Measure | base | tuned | change |
|---|---|---|---|
| Valid JSON in the right shape | n/a | n/a | n/a |
| Only the JSON, no extra text | n/a | n/a | n/a |
| Category correct | n/a | n/a | n/a |
| Urgency correct | n/a | n/a | n/a |
| needs_human correct | n/a | n/a | n/a |
| needs_human recall (missed a case that needs a person?) | n/a | n/a | n/a |
| needs_human precision | n/a | n/a | n/a |
| All three fields correct | n/a | n/a | n/a |

## base: where it went wrong

- Unreadable answers: not valid JSON (1)
- Urgency mistakes, gold->answer: high->low x5, low->high x1, low->medium x1, medium->high x50, medium->low x2

First wrong cases (8 of 69):

- Q001 (None): gold ['refund_return', 'medium', True], got not valid JSON. "三件事：我想改邮箱，我的退款已经晚了三个星期，还有网站一直打不开。"
- Q003 (None): gold ['product_fault', 'medium', False], got ['product_fault', 'high', True]. "Earlier I wrote about a broken zip on my bag and you fixed it, thank you. Now the handle o"
- Q004 (None): gold ['product_fault', 'medium', False], got ['product_fault', 'high', True]. "Tadi saya cakap periuk nasi berasap, tapi rupa-rupanya cuma wap. Penutupnya longgar."
- Q005 (None): gold ['product_fault', 'medium', False], got ['product_fault', 'low', False]. "Scrap what I said about a fire, it was steam from the kettle lid. The lid no longer fits p"
- Q006 (None): gold ['delivery', 'medium', False], got ['delivery', 'high', True]. "Ini kali pertama saya menghubungi anda tentang parcel yang lewat. Belum ada sebarang jawap"
- Q007 (None): gold ['product_fault', 'medium', False], got ['product_fault', 'medium', True]. "第一次联系你们：我的行李箱轮子坏了，想问怎么保修。"
- Q008 (None): gold ['refund_return', 'medium', True], got ['refund_return', 'high', True]. "退款已经晚了两个星期零两天。"
- Q009 (None): gold ['payment_billing', 'medium', False], got ['payment_billing', 'high', True]. "Thank you for the lovely packaging, the thank-you card was a nice touch. Unfortunately RM6"

## tuned: where it went wrong

- Unreadable answers: not valid JSON (1)
- Urgency mistakes, gold->answer: high->medium x3, low->medium x1, medium->high x5

First wrong cases (8 of 29):

- Q001 (None): gold ['refund_return', 'medium', True], got not valid JSON. "三件事：我想改邮箱，我的退款已经晚了三个星期，还有网站一直打不开。"
- Q009 (None): gold ['payment_billing', 'medium', False], got ['payment_billing', 'high', True]. "Thank you for the lovely packaging, the thank-you card was a nice touch. Unfortunately RM6"
- Q017 (None): gold ['payment_billing', 'medium', False], got ['payment_billing', 'high', True]. "என் அட்டையிலிருந்து இரண்டு முறை பணம் எடுக்கப்பட்டுள்ளது, ஆனால் நான் ஒரே ஒரு ஆர்டர் தான் செ"
- Q026 (None): gold ['general_enquiry', 'low', False], got ['delivery', 'low', False]. "I love the sparkling finish on the vase. It arrived perfectly wrapped, thank you."
- Q028 (None): gold ['delivery', 'high', True], got ['delivery', 'medium', False]. "Mera parcel kal tak chahiye shaadi ke liye, abhi bhi warehouse mein hai."
- Q030 (None): gold ['refund_return', 'medium', True], got ['refund_return', 'medium', False]. "My refund is two weeks and one day late."
- Q031 (None): gold ['refund_return', 'medium', True], got ['refund_return', 'medium', False]. "Wang pulangan saya sudah lewat tiga minggu."
- Q037 (None): gold ['refund_return', 'medium', True], got ['refund_return', 'medium', False]. "Mon remboursement devait arriver avant le 5 mars. Nous sommes le 24 mars et je n'ai toujou"

## Read this before you trust a number

- 100 test cases is small: one case is 1 points. A change of a few points is noise, not a result.
- Do not tune on these cases. If you read them to change your training data, they are no longer a test.
- Run the base model and the tuned model with the same prompt and the same settings.
