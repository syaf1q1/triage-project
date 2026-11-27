"""Checks the training and test data before you train. Standard library only.

    python check_dataset.py                       # checks ../data/train_raw.jsonl and ../data/test_raw.jsonl
    python check_dataset.py --train my_train.jsonl --test my_test.jsonl

Errors (exit code 1): bad label values, a message that appears twice, a test message that also
appears in the training data, and a label that breaks the rules in LABELING_GUIDE.md that can be
checked by code (high urgency must need a person; low urgency must not).
Warnings: near-duplicates between train and test, very small or very lopsided classes.
"""
import argparse, collections, difflib, json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
CATEGORIES = {"delivery", "refund_return", "product_fault", "payment_billing", "account_access", "general_enquiry"}
URGENCY = {"low", "medium", "high"}


def load(path):
    rows = []
    for n, line in enumerate(pathlib.Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                sys.exit(f"{path} line {n}: not valid JSON ({e})")
    return rows


def norm(text):
    return re.sub(r"[^a-z0-9 ]+", "", re.sub(r"\s+", " ", text.lower())).strip()


def check_labels(rows, name, errors):
    for r in rows:
        rid = r.get("id", "?")
        if r.get("category") not in CATEGORIES:
            errors.append(f"{name} {rid}: category {r.get('category')!r} is not one of {sorted(CATEGORIES)}")
        if r.get("urgency") not in URGENCY:
            errors.append(f"{name} {rid}: urgency {r.get('urgency')!r} is not low, medium or high")
        if not isinstance(r.get("needs_human"), bool):
            errors.append(f"{name} {rid}: needs_human must be true or false")
        if not str(r.get("message", "")).strip():
            errors.append(f"{name} {rid}: empty message")
        if r.get("urgency") == "high" and r.get("needs_human") is False:
            errors.append(f"{name} {rid}: high urgency must have needs_human true")
        if r.get("urgency") == "low" and r.get("needs_human") is True:
            errors.append(f"{name} {rid}: low urgency must have needs_human false")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default=str(HERE.parent / "data" / "train_raw.jsonl"))
    ap.add_argument("--test", default=str(HERE.parent / "data" / "test_raw.jsonl"))
    a = ap.parse_args()
    train, test = load(a.train), load(a.test)
    errors, warnings = [], []

    check_labels(train, "train", errors)
    check_labels(test, "test", errors)

    seen = {}
    for name, rows in (("train", train), ("test", test)):
        for r in rows:
            key = norm(r["message"])
            if key in seen:
                errors.append(f"{name} {r['id']}: same message as {seen[key]}")
            else:
                seen[key] = f"{name} {r['id']}"

    train_norm = [(r["id"], norm(r["message"])) for r in train]
    for r in test:
        t = norm(r["message"])
        for tid, tn in train_norm:
            if tn and difflib.SequenceMatcher(None, t, tn).ratio() >= 0.85 and t != tn:
                warnings.append(f"test {r['id']} is very close to train {tid} (a test case you have already seen is no test)")

    print(f"train: {len(train)} rows    test: {len(test)} rows")
    for label in ("category", "urgency", "needs_human"):
        for name, rows in (("train", train), ("test", test)):
            c = collections.Counter(str(r[label]) for r in rows if label in r)
            print(f"  {name:5} {label:12} " + "  ".join(f"{k}={v}" for k, v in sorted(c.items())))
            if name == "train":
                for k, v in c.items():
                    if v < 5:
                        warnings.append(f"train has only {v} rows with {label} = {k}")
                    if v > 0.8 * len(rows):
                        warnings.append(f"train: {label} = {k} is {v} of {len(rows)} rows (lopsided)")
    lens = sorted(len(r["message"]) for r in train)
    if lens:
        print(f"  train message length (characters): shortest {lens[0]}, median {lens[len(lens)//2]}, longest {lens[-1]}")
    if len(train) < 100:
        warnings.append(f"only {len(train)} training rows; the deck's rule of thumb for SFT is at least 100")

    for w in warnings:
        print("WARNING:", w)
    for e in errors:
        print("ERROR:  ", e)
    print("OK: no errors" if not errors else f"{len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
