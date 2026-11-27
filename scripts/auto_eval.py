"""Auto evaluation: send every test message to a served model and print its score.

The test file needs the same columns as data_starter.xlsx / train_raw.jsonl:
    id, message, category, urgency, needs_human          (.xlsx, .csv, .jsonl or a .json list)
Optional column: slice (standard or hard), used only to split the report.

Command line (the model must be served; pick ONE of the two connections):

    python auto_eval.py --test ..\\data\\test_raw.jsonl --ollama my-tuned-model
    python auto_eval.py --test my_cases.xlsx --openai-url http://localhost:8000/v1 --model my-tuned-model

    --pass-mark 0.70     the exact-match score needed to pass (default 0.70)
    --base-pred FILE     predictions of the untuned model (from an earlier run), to show base vs tuned
    --workers 4          send several messages at once (use 1 for Ollama unless it is set up for it)
    --limit 10           only the first 10 cases, for a quick try

From Python (for a model that only lives in your notebook): give it a function that takes the system
prompt and the message and returns the model's text:

    from auto_eval import load_cases, evaluate
    result = evaluate(my_generate, load_cases("my_cases.xlsx"))
    print(result["headline"])

Exit code: 0 pass, 1 below the pass mark, 2 could not run. Standard library only (openpyxl for .xlsx).
"""
import argparse, csv, json, pathlib, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

import score as scorer

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_SYSTEM = HERE.parent / "data" / "system_prompt.txt"
COLUMNS = ["id", "message", "category", "urgency", "needs_human"]


# ---------------------------------------------------------------- test data
def _truth(v):
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("true", "1", "yes", "y"):
        return True
    if s in ("false", "0", "no", "n"):
        return False
    raise ValueError(f"needs_human must be TRUE or FALSE, got {v!r}")


def load_cases(path):
    """Read a test file and return a list of validated cases. Raises ValueError with a clear message."""
    path = pathlib.Path(path)
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        from openpyxl import load_workbook
        ws = load_workbook(path, read_only=True, data_only=True).worksheets[0]
        it = ws.iter_rows(values_only=True)
        header = [str(h).strip().lower() if h is not None else "" for h in next(it)]
        raw = [dict(zip(header, r)) for r in it if any(c is not None and str(c).strip() for c in r)]
    elif suffix == ".csv":
        with open(path, encoding="utf-8-sig", newline="") as f:
            raw = [{k.strip().lower(): v for k, v in r.items()} for r in csv.DictReader(f)]
    elif suffix == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
    else:
        raw = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not raw:
        raise ValueError(f"{path.name}: no rows")
    missing = [c for c in COLUMNS if c not in raw[0] and not (c == "id")]
    if missing:
        raise ValueError(f"{path.name}: missing column(s) {missing}. Expected: {COLUMNS}")
    cases, seen = [], set()
    for n, r in enumerate(raw, 1):
        cid = str(r.get("id") or f"row{n}").strip()
        if cid in seen:
            raise ValueError(f"{path.name}: id {cid!r} appears twice")
        seen.add(cid)
        c = {"id": cid, "message": str(r["message"]).strip(),
             "category": str(r["category"]).strip().lower(), "urgency": str(r["urgency"]).strip().lower()}
        try:
            c["needs_human"] = _truth(r["needs_human"])
        except ValueError as e:
            raise ValueError(f"{path.name} {cid}: {e}")
        if c["category"] not in scorer.CATEGORIES:
            raise ValueError(f"{path.name} {cid}: category {c['category']!r} is not one of {sorted(scorer.CATEGORIES)}")
        if c["urgency"] not in scorer.URGENCY:
            raise ValueError(f"{path.name} {cid}: urgency {c['urgency']!r} is not low, medium or high")
        if not c["message"]:
            raise ValueError(f"{path.name} {cid}: empty message")
        sl = str(r.get("slice") or "").strip().lower()
        c["slice"] = sl if sl in ("standard", "hard") else "standard"
        cases.append(c)
    return cases


# ---------------------------------------------------------------- connections
def _post(url, body, headers=None, timeout=300):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def ollama_generate(model, host="http://localhost:11434"):
    def gen(system, message):
        data = _post(f"{host.rstrip('/')}/api/chat", {
            "model": model, "stream": False, "options": {"temperature": 0, "seed": 1},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": message}]})
        return data["message"]["content"]
    return gen


def openai_generate(base_url, model, api_key="none"):
    def gen(system, message):
        data = _post(f"{base_url.rstrip('/')}/chat/completions", {
            "model": model, "temperature": 0, "max_tokens": 120,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": message}]},
            headers={"Authorization": f"Bearer {api_key}"})
        return data["choices"][0]["message"]["content"]
    return gen


# ---------------------------------------------------------------- evaluation
def evaluate(generate, cases, system=None, pass_mark=0.70, workers=1, progress=None, base_preds=None):
    """Run every case through `generate(system, message) -> str`; return the scored result.

    result keys: preds, errors, scored (score.score output), headline, passed, pass_mark, report_md, seconds
    """
    system = system if system is not None else DEFAULT_SYSTEM.read_text(encoding="utf-8").strip()
    errors = {}
    t0 = time.time()

    def one(case):
        try:
            out = generate(system, case["message"])
        except Exception as e:                      # keep going: one bad call must not stop the run
            errors[case["id"]] = f"{type(e).__name__}: {e}"
            out = ""
        return {"id": case["id"], "output": out}

    preds = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for p in pool.map(one, cases):          # progress is reported from the calling thread (Streamlit needs that)
            preds.append(p)
            if progress:
                progress(len(preds), len(cases))
    if len(errors) == len(cases):
        raise RuntimeError("every call failed; first error: " + next(iter(errors.values())))
    scored = scorer.score(cases, preds)
    s = scored["summary"]["all"]
    results = {"tuned": scored}
    if base_preds is not None:
        results = {"base": scorer.score(cases, base_preds), "tuned": scored}
    return {
        "preds": preds, "errors": errors, "scored": scored, "summary": s, "pass_mark": pass_mark,
        "passed": s["exact_match"] >= pass_mark, "seconds": time.time() - t0,
        "report_md": scorer.report(results, cases),
        "headline": f"Score {100 * s['exact_match']:.0f}% ({round(s['exact_match'] * len(cases))} of {len(cases)} cases fully correct)",
    }


def print_summary(res, name="model"):
    s, sl = res["summary"], res["scored"]["summary"]
    pm = lambda x: scorer.pct(x)
    print()
    print(f"  {res['headline']}   pass mark {100 * res['pass_mark']:.0f}%   ->  {'PASS' if res['passed'] else 'FAIL'}")
    print(f"  Category correct         {pm(s['category_acc'])}")
    print(f"  Urgency correct          {pm(s['urgency_acc'])}")
    print(f"  needs_human correct      {pm(s['needs_human_acc'])}   (recall {pm(s['needs_human_recall'])}, precision {pm(s['needs_human_precision'])})")
    print(f"  Only the JSON, no extra  {pm(s['json_only'])}")
    print(f"  Valid JSON, right shape  {pm(s['valid_json'])}")
    for part in ("standard", "hard"):
        if part in sl and sl["all"]["n"] != sl[part]["n"]:
            print(f"  {part:8} cases: {sl[part]['n']:>3}   all three correct {pm(sl[part]['exact_match'])}")
    if res["errors"]:
        print(f"  {len(res['errors'])} call(s) failed and count as wrong. First: {next(iter(res['errors'].values()))}")
    print(f"  ({res['seconds']:.0f} seconds)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", required=True, help="test file: .xlsx, .csv, .jsonl or .json")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ollama", metavar="MODEL", help="model name served by Ollama")
    g.add_argument("--openai-url", metavar="URL", help="an OpenAI-compatible endpoint, e.g. http://localhost:8000/v1")
    ap.add_argument("--model", help="model name for --openai-url")
    ap.add_argument("--api-key", default="none")
    ap.add_argument("--host", default="http://localhost:11434", help="Ollama address")
    ap.add_argument("--system", default=str(DEFAULT_SYSTEM), help="file with the system prompt")
    ap.add_argument("--pass-mark", type=float, default=0.70)
    ap.add_argument("--base-pred", help="predictions file of the untuned model, to show base versus tuned")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", default=".", help="folder for predictions.jsonl, report.md, report.json")
    a = ap.parse_args()
    try:
        cases = load_cases(a.test)
        if a.limit:
            cases = cases[:a.limit]
        if a.ollama:
            gen = ollama_generate(a.ollama, a.host)
        else:
            if not a.model:
                ap.error("--openai-url needs --model")
            gen = openai_generate(a.openai_url, a.model, a.api_key)
        base = scorer.load(a.base_pred) if a.base_pred else None
        system = pathlib.Path(a.system).read_text(encoding="utf-8").strip()
        print(f"{len(cases)} test cases from {a.test}")
        res = evaluate(gen, cases, system, a.pass_mark, a.workers, base_preds=base,
                       progress=lambda d, n: print(f"\r  asked {d}/{n}", end="", flush=True))
    except (ValueError, RuntimeError, OSError, urllib.error.URLError) as e:
        print(f"\nCould not run: {e}", file=sys.stderr)
        return 2
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "predictions.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for p in res["preds"]:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    (out / "report.md").write_text(res["report_md"], encoding="utf-8")
    (out / "report.json").write_text(json.dumps({k: v for k, v in res["scored"].items() if k != "cases"}, indent=2), encoding="utf-8")
    print_summary(res)
    print(f"  wrote {out / 'predictions.jsonl'}, {out / 'report.md'}, {out / 'report.json'}")
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
