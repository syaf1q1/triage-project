"""Scores a model's answers on the held-out test set. Standard library only.

A predictions file has one JSON object per line:   {"id": "X001", "output": "<exactly what the model wrote>"}

    python score.py --pred base=base.jsonl
    python score.py --pred base=base.jsonl --pred tuned=tuned.jsonl --out .

With two or more predictions files the report puts them side by side, so you can see what the tuning changed.
An answer that is not valid JSON, has the wrong keys, or uses a value outside the allowed lists counts as wrong on every field.
Writes report.md and report.json to --out (default: next to this script).
"""
import argparse, collections, json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
CATEGORIES = {"delivery", "refund_return", "product_fault", "payment_billing", "account_access", "general_enquiry"}
URGENCY = ["low", "medium", "high"]
KEYS = {"category", "urgency", "needs_human"}


def load(path):
    return [json.loads(l) for l in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def parse(output):
    """Return (answer dict, None) if the output is a valid triage record, else (None, reason)."""
    text = (output or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)        # a fenced block is tolerated, but counted below
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        return None, "no JSON object"
    try:
        obj = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None, "not valid JSON"
    if not isinstance(obj, dict) or set(obj) != KEYS:
        return None, "wrong keys"
    if obj["category"] not in CATEGORIES or obj["urgency"] not in URGENCY or not isinstance(obj["needs_human"], bool):
        return None, "value not allowed"
    return obj, None


def clean_output(output):
    """True if the whole output is only the JSON object (no talk around it, no code fence)."""
    t = (output or "").strip()
    return t.startswith("{") and t.endswith("}")


def score(gold, preds):
    by_id = {p["id"]: p.get("output", "") for p in preds}
    res = {"n": len(gold), "missing": [g["id"] for g in gold if g["id"] not in by_id]}
    counters = collections.defaultdict(lambda: collections.Counter())
    reasons = collections.Counter()
    urg_conf = collections.Counter()
    per_case = []
    for g in gold:
        out = by_id.get(g["id"], "")
        obj, why = parse(out)
        cats = ["all", g.get("slice", "standard")]
        ok_c = ok_u = ok_n = False
        if obj is None:
            reasons[why] += 1
        else:
            ok_c, ok_u, ok_n = obj["category"] == g["category"], obj["urgency"] == g["urgency"], obj["needs_human"] == g["needs_human"]
            urg_conf[(g["urgency"], obj["urgency"])] += 1
        for s in cats:
            c = counters[s]
            c["n"] += 1
            c["valid"] += obj is not None
            c["clean"] += obj is not None and clean_output(out)
            c["category"] += ok_c
            c["urgency"] += ok_u
            c["needs_human"] += ok_n
            c["exact"] += ok_c and ok_u and ok_n
            if g["needs_human"]:
                c["nh_gold_true"] += 1
                c["nh_caught"] += bool(obj and obj["needs_human"])
            if obj and obj["needs_human"]:
                c["nh_said_true"] += 1
                c["nh_said_true_right"] += bool(g["needs_human"])
        per_case.append({"id": g["id"], "slice": g.get("slice"), "gold": [g["category"], g["urgency"], g["needs_human"]],
                         "got": None if obj is None else [obj["category"], obj["urgency"], obj["needs_human"]],
                         "problem": why, "message": g["message"]})
    summary = {}
    for s, c in counters.items():
        n = c["n"]
        summary[s] = {
            "n": n,
            "valid_json": c["valid"] / n,
            "json_only": c["clean"] / n,
            "category_acc": c["category"] / n,
            "urgency_acc": c["urgency"] / n,
            "needs_human_acc": c["needs_human"] / n,
            "needs_human_recall": (c["nh_caught"] / c["nh_gold_true"]) if c["nh_gold_true"] else None,
            "needs_human_precision": (c["nh_said_true_right"] / c["nh_said_true"]) if c["nh_said_true"] else None,
            "exact_match": c["exact"] / n,
        }
    res.update(summary=summary, invalid_reasons=dict(reasons), urgency_confusion={f"{a}->{b}": v for (a, b), v in sorted(urg_conf.items())}, cases=per_case)
    return res


def pct(x):
    return "n/a" if x is None else f"{100 * x:.0f}%"


METRICS = [("valid_json", "Valid JSON in the right shape"), ("json_only", "Only the JSON, no extra text"),
           ("category_acc", "Category correct"), ("urgency_acc", "Urgency correct"),
           ("needs_human_acc", "needs_human correct"), ("needs_human_recall", "needs_human recall (missed a case that needs a person?)"),
           ("needs_human_precision", "needs_human precision"), ("exact_match", "All three fields correct")]


def report(results, gold):
    names = list(results)
    L = ["# Triage score report", "", f"Test cases: {len(gold)} (standard {sum(g.get('slice') == 'standard' for g in gold)}, hard {sum(g.get('slice') == 'hard' for g in gold)}).",
         "Wrong or unreadable answers count as wrong. Recall matters most for `needs_human`: a missed case reaches no person.", ""]
    for sl, title in (("all", "All test cases"), ("standard", "Standard cases"), ("hard", "Hard cases (Malay, two issues, tone, an order inside the message)")):
        L += [f"## {title}", "", "| Measure | " + " | ".join(names) + (" | change |" if len(names) == 2 else " |"),
              "|---|" + "---|" * len(names) + ("---|" if len(names) == 2 else "")]
        for key, label in METRICS:
            vals = [results[n]["summary"].get(sl, {}).get(key) for n in names]
            row = f"| {label} | " + " | ".join(pct(v) for v in vals)
            if len(names) == 2:
                d = None if None in vals else vals[1] - vals[0]
                row += " | " + ("n/a" if d is None else f"{100 * d:+.0f} points")
            L.append(row + " |")
        L.append("")
    for n in names:
        r = results[n]
        L += [f"## {n}: where it went wrong", ""]
        if r["missing"]:
            L.append(f"- No answer in the file for {len(r['missing'])} test case(s): {', '.join(r['missing'][:10])}")
        if r["invalid_reasons"]:
            L.append("- Unreadable answers: " + ", ".join(f"{k} ({v})" for k, v in r["invalid_reasons"].items()))
        if r["urgency_confusion"]:
            miss = ", ".join(f"{k} x{v}" for k, v in r["urgency_confusion"].items() if k.split("->")[0] != k.split("->")[1])
            L.append("- Urgency mistakes, gold->answer: " + (miss or "none"))
        wrong = [c for c in r["cases"] if c["got"] != c["gold"]]
        L += ["", f"First wrong cases ({min(8, len(wrong))} of {len(wrong)}):", ""]
        for c in wrong[:8]:
            L.append(f"- {c['id']} ({c['slice']}): gold {c['gold']}, got {c['got'] if c['got'] else c['problem']}. \"{c['message'][:90]}\"")
        L.append("")
    L += ["## Read this before you trust a number", "",
          f"- {len(gold)} test cases is small: one case is {100 / len(gold):.0f} points. A change of a few points is noise, not a result.",
          "- Do not tune on these cases. If you read them to change your training data, they are no longer a test.",
          "- Run the base model and the tuned model with the same prompt and the same settings.", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default=str(HERE.parent / "data" / "test_raw.jsonl"))
    ap.add_argument("--pred", action="append", required=True, metavar="NAME=FILE", help="repeat for each model")
    ap.add_argument("--out", default=str(HERE))
    a = ap.parse_args()
    gold = load(a.gold)
    results = {}
    for item in a.pred:
        if "=" not in item:
            sys.exit("--pred needs NAME=FILE, for example base=base.jsonl")
        name, path = item.split("=", 1)
        results[name] = score(gold, load(path))
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    md = report(results, gold)
    (out / "report.md").write_text(md, encoding="utf-8")
    (out / "report.json").write_text(json.dumps({n: {k: v for k, v in r.items() if k != "cases"} for n, r in results.items()}, indent=2), encoding="utf-8")
    for n, r in results.items():
        s = r["summary"]["all"]
        print(f"{n}: valid {pct(s['valid_json'])}  category {pct(s['category_acc'])}  urgency {pct(s['urgency_acc'])}  "
              f"needs_human {pct(s['needs_human_acc'])} (recall {pct(s['needs_human_recall'])})  exact {pct(s['exact_match'])}")
    print(f"wrote {out / 'report.md'}")


if __name__ == "__main__":
    main()
