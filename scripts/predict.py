"""Run a served model on test messages that have NO answers, and write a predictions file for the leaderboard.

    python predict.py --questions ../data/leaderboard_test_100_messages.xlsx --ollama triage --out ../results/leaderboard_predictions.jsonl

The questions file can be .xlsx (columns: ID, Customer message), .tsv/.txt (id<TAB>message per line)
or .jsonl (keys id and message). The output has one line per message: {"id": "Q001", "output": "..."},
the same format auto_eval.py writes, so it can be uploaded to the class leaderboard.
Uses the same prompt and settings as auto_eval.py (data/system_prompt.txt, temperature 0).
"""
import argparse, json, pathlib, sys

import auto_eval


def load_questions(path):
    path = pathlib.Path(path)
    rows = []
    if path.suffix.lower() == ".xlsx":
        from openpyxl import load_workbook
        it = load_workbook(path, read_only=True, data_only=True).worksheets[0].iter_rows(values_only=True)
        next(it)  # header row
        for r in it:
            if r and r[0] and r[1]:
                rows.append((str(r[0]).strip(), str(r[1]).strip()))
    elif path.suffix.lower() == ".jsonl":
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                o = json.loads(line)
                rows.append((str(o["id"]), o["message"]))
    else:
        for line in path.read_text(encoding="utf-8").splitlines():
            if "\t" in line:
                i, m = line.split("\t", 1)
                rows.append((i.strip(), m.strip()))
    if not rows:
        sys.exit(f"No questions found in {path}")
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--questions", required=True)
    ap.add_argument("--ollama", required=True, help="Ollama model name, e.g. triage")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--system", default=str(auto_eval.DEFAULT_SYSTEM))
    ap.add_argument("--out", default="../results/leaderboard_predictions.jsonl")
    a = ap.parse_args()

    system = pathlib.Path(a.system).read_text(encoding="utf-8").strip()
    gen = auto_eval.ollama_generate(a.ollama, a.host)
    rows = load_questions(a.questions)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for n, (qid, msg) in enumerate(rows, 1):
            try:
                text = gen(system, msg)
            except Exception as e:  # keep going; a missing answer is scored as wrong
                print(f"  {qid}: no answer ({e})")
                text = ""
            f.write(json.dumps({"id": qid, "output": text}, ensure_ascii=False) + "\n")
            print(f"  {n}/{len(rows)} {qid}: {text.strip()[:80]}")
    print(f"wrote {len(rows)} predictions to {out}")


if __name__ == "__main__":
    main()
