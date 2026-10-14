#!/usr/bin/env python3
"""Test runs for step 1 (model extraction). Development evidence only.

These runs do NOT count toward the six supervised runs: BH does not review a
draft here, and the run log in runs/ is not touched.

For each request (the five fixtures in fixtures/requests/ and the harder
synthetic cases in evals/step1-extraction/cases/requests/), and for each
repeat, this script:
  1. runs extract_form.py with the given model,
  2. compares the model's form with the expected form field by field
     (fixtures: the hand-written form in fixtures/forms/; cases: cases/expected/),
  3. runs quote.py on the model's form and, for the fixtures, on the
     hand-written form too, and compares outcome, rates and draft text.

Usage (from the repository root):
  python3 evals/step1-extraction/run_eval.py --model claude-haiku-5-5 --repeats 3 \
      --out evals/step1-extraction/results/2026-10-13-haiku
"""

import argparse
import json
import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EXTRACT = REPO / "scripts" / "extract_form.py"
QUOTE = REPO / "scripts" / "quote.py"
FIX = REPO / "fixtures"
CASES = Path(__file__).resolve().parent / "cases"
FIELDS = ("item_type", "currency", "amount", "value_date", "tenor_business_days", "end_date", "facility_ref")


def requests():
    for p in sorted((FIX / "requests").glob("*.txt")):
        yield p, json.loads((FIX / "forms" / (p.stem + ".json")).read_text()), True
    for p in sorted((CASES / "requests").glob("*.txt")):
        yield p, json.loads((CASES / "expected" / (p.stem + ".json")).read_text()), False


def received_date(text):
    m = re.search(r"^Received:\s*(\d{4}-\d{2}-\d{2})", text, re.M)
    if not m:
        raise SystemExit("no Received: line")
    return m.group(1)


def norm(v, key):
    if v is None:
        return None
    return Decimal(str(v)) if key == "amount" else str(v)


def compare(model_form, expected):
    """List of field differences. Empty list = exact match."""
    diffs = []
    if model_form["request_id"] != expected["request_id"]:
        diffs.append("request_id %r != %r" % (model_form["request_id"], expected["request_id"]))
    m, e = model_form["items"], expected["items"]
    if len(m) != len(e):
        return diffs + ["item count %d != %d" % (len(m), len(e))]
    for i, (mi, ei) in enumerate(zip(m, e), start=1):
        for k in FIELDS:
            if norm(mi.get(k), k) != norm(ei.get(k), k):
                diffs.append("item %d %s: model %r, expected %r" % (i, k, mi.get(k), ei.get(k)))
    return diffs


def quote(form_path, received, out, requests_dir):
    subprocess.run([sys.executable, str(QUOTE), "--form", str(form_path), "--received", received,
                    "--sheet-dir", str(FIX / "rate_sheets"), "--calendars", str(FIX / "calendars"),
                    "--margins", str(FIX / "margins.csv"), "--requests", str(requests_dir), "--out", str(out)],
                   capture_output=True, text=True, cwd=str(REPO))
    res = json.loads((out / "result.json").read_text())
    return {"outcome": res["outcome"], "hand_back_step": res["hand_back_step"],
            "hand_back_reason": res["hand_back_reason"],
            "rates": [it.get("customer_rate") for it in res["items"]],
            "draft": (out / "quote-draft.txt").read_text()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="", help="run only requests whose id starts with this, e.g. U-")
    args = ap.parse_args()
    out_root = (REPO / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for req, expected, is_fixture in requests():
        if args.only and not req.stem.startswith(args.only):
            continue
        text = req.read_text()
        received = received_date(text)
        baseline = None
        if is_fixture:
            baseline = quote(FIX / "forms" / (req.stem + ".json"), received, out_root / req.stem / "hand-form-quote", req.parent)
        for r in range(1, args.repeats + 1):
            run_dir = out_root / req.stem / ("run%d" % r)
            subprocess.run([sys.executable, str(EXTRACT), "--request", str(req), "--out", str(run_dir / "step1"),
                            "--model", args.model], capture_output=True, text=True, cwd=str(REPO))
            meta = json.loads((run_dir / "step1" / "extract-meta.json").read_text())
            row = {"request": req.stem, "fixture": is_fixture, "run": r, "model": args.model,
                   "model_used": meta.get("model_used"), "seconds": meta.get("seconds"),
                   "tokens": meta.get("tokens"), "prompt_version": meta.get("prompt_version"), "step1_outcome": meta["outcome"],
                   "step1_reason": meta["hand_back_reason"]}
            if expected.get("expect") == "hand_back":
                # Correct when step 1 hands back, or when the model's form is
                # stopped by code at step 2 or 3 before any rate is computed.
                row["expected"] = "hand_back at step 1, 2 or 3"
                row["step1_correct"] = meta["outcome"] == "hand_back"
                if meta["outcome"] == "form":
                    row["model_form"] = json.loads((run_dir / "step1" / "form.json").read_text())
                    q = quote(run_dir / "step1" / "form.json", received, run_dir / "quote", req.parent)
                    row["quote_outcome"] = q["outcome"]
                    row["quote_hand_back"] = ("step %s: %s" % (q["hand_back_step"], q["hand_back_reason"])
                                              if q["outcome"] == "hand_back" else None)
                    row["step1_correct"] = q["outcome"] == "hand_back" and q["hand_back_step"] in (2, 3)
            else:
                row["expected"] = "form"
                if meta["outcome"] == "form":
                    form = json.loads((run_dir / "step1" / "form.json").read_text())
                    row["field_diffs"] = compare(form, expected)
                    row["step1_correct"] = not row["field_diffs"]
                    q = quote(run_dir / "step1" / "form.json", received, run_dir / "quote", req.parent)
                    row["quote_outcome"] = q["outcome"]
                    row["quote_hand_back"] = ("step %s: %s" % (q["hand_back_step"], q["hand_back_reason"])
                                              if q["outcome"] == "hand_back" else None)
                    row["rates"] = q["rates"]
                    if baseline:
                        row["same_as_hand_form"] = (q["outcome"] == baseline["outcome"]
                                                    and q["rates"] == baseline["rates"]
                                                    and q["draft"] == baseline["draft"])
                else:
                    row["step1_correct"] = False
            rows.append(row)
            print(json.dumps({k: row.get(k) for k in ("request", "run", "step1_outcome", "step1_correct",
                                                       "quote_outcome", "same_as_hand_form", "seconds")}))
            sys.stdout.flush()
    (out_root / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
    ok = sum(1 for r in rows if r["step1_correct"])
    print("step 1 correct: %d of %d runs" % (ok, len(rows)))


if __name__ == "__main__":
    main()
