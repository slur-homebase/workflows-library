#!/usr/bin/env python3
"""rate-quote step 1: a cheap model reads the request text into the fixed form.

Route A, step 1 (docs/route.md): "Model (cheap). Read the
email into a fixed JSON form ... Form not valid, hand back."

Model choice (BH, 2026-10-13): Haiku 5.5 for routing, classification and
extraction steps. This step is extraction only, so it uses Haiku 5.5. The model
is pinned by its full id; the CLI alias "haiku" resolves to an older model.

What the model sees: the request text only, with the fixture's "Case:" line
removed (that line is a test note, not part of the email). It never sees the
rate sheet, the calendars, the margin or any computed value. It does no
arithmetic: no date counting, no tenor conversion, no rate.

What the code does after the model: checks the shape, removes empty optional
fields, and hands back at step 1 when the model says a value is unclear or the
form has the wrong shape. Steps 2 and 3 in quote.py then validate the form and
ground every amount and date against the request text.

The model call goes through the Claude Code CLI (`claude -p`) on BH's existing
login, so there is no new paid service (spend limit $0). No tools are enabled
for the model, no settings or MCP servers are loaded, and the session is not
saved. Synthetic fixtures only.

Usage:
  python3 skills/rate-quote/scripts/extract_form.py \\
      --request fixtures/requests/REQ-001.txt --out /tmp/req001-step1

Writes in --out:
  form.json          the step-1 form, ready for quote.py --form (only on success)
  extract-meta.json  model id, prompt version, timing, token use, raw model
                     output, and the outcome (form or hand_back with reason)

Exit codes: 0 = form written; 2 = hand back at step 1; 1 = could not run.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DEFAULT_MODEL = "claude-haiku-5-5"
PROMPT_VERSION = "step1-v0.3"
# v0.1 -> v0.2 (2026-10-13): on REQ-003 Haiku listed a correctly copied
# "on maturity" date under "unclear", so a clean request was handed back.
# Rule 11 now says that values filled by rules 1 to 10 are not unclear.
# v0.2 -> v0.3 (2026-10-13): on X-101 (1 run of 3) Haiku compared the value
# date with today's date and handed back. Date checks are code's job (step 6),
# so the prompt now says not to judge dates.

FORM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["request_id", "items", "unclear"],
    "properties": {
        "request_id": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["item_type", "currency", "amount", "value_date",
                             "tenor_business_days", "end_date", "facility_ref"],
                "properties": {
                    "item_type": {"type": "string", "enum": ["drawdown", "rollover", "repayment"]},
                    "currency": {"type": "string"},
                    "amount": {"type": "number"},
                    "value_date": {"type": "string"},
                    "tenor_business_days": {"type": ["integer", "null"]},
                    "end_date": {"type": ["string", "null"]},
                    "facility_ref": {"type": "string"},
                },
            },
        },
        "unclear": {"type": "array", "items": {"type": "string"}},
    },
}

SYSTEM_PROMPT = """You read one customer email that asks a bank for an interest rate quote, and you copy its facts into a fixed JSON form. You copy. You never calculate, convert or guess.

Rules:
1. request_id: the value after "Request-ID:" in the header.
2. One item per instruction in the latest message: each drawdown, rollover or repayment is its own item. Ignore earlier messages quoted below the latest one (lines starting with ">" or after "From:/Sent:/On ... wrote:"), unless the latest message says to use them.
3. item_type: "drawdown" (new money drawn), "rollover" (an existing amount continued for a new period), or "repayment" (money paid back).
4. currency: the three-letter code written next to the amount.
5. amount: the number in full units, no commas. "5mio", "5m", "5 million" = 5000000. "7.5mio" = 7500000.
6. value_date: the start date of that item, as YYYY-MM-DD. If the email gives day and month but no year, use the year from the "Received:" line. Numeric dates like 01/10/2026 are day/month/year (Singapore). A rollover or repayment "on maturity" uses the maturity date the email names.
7. tenor_business_days: only when the email states a tenor in business days ("30 business days", "60 BD"). Otherwise null.
8. end_date: only when the email states an end or maturity date for that item's new period, as YYYY-MM-DD. Otherwise null.
9. A drawdown or rollover needs exactly one of tenor_business_days or end_date. A repayment has both null.
10. facility_ref: the facility reference written in the email (for example FAC-SYN-0001).
11. unclear: a list of short sentences, one per thing you could not copy exactly. Examples: a tenor given in months, weeks or calendar days (do not convert it; set tenor_business_days and end_date to null and say so here); a missing currency, amount, date or facility; an ambiguous instruction; a date you are not sure of. Do not list a value you filled by following rules 1 to 10 (for example a repayment "on maturity" dated with the maturity date the email names, or a year taken from the Received line): that is copying, not unclear. If everything was copied, give an empty list.

Never judge a date: do not compare it with today, and do not check weekends, holidays or whether it is in the past. Code checks dates later. Never move a date to a business day. Never count days. Never add a rate, margin or any number that is not in the email."""


def email_text(raw):
    """The request as an email: drop the fixture's 'Case:' test note."""
    return "\n".join(line for line in raw.splitlines() if not line.startswith("Case:")) + "\n"


def call_model(text, model, timeout):
    cmd = ["claude", "-p", "--model", model, "--output-format", "json",
           "--tools", "", "--system-prompt", SYSTEM_PROMPT,
           "--json-schema", json.dumps(FORM_SCHEMA),
           "--no-session-persistence", "--setting-sources", "", "--strict-mcp-config"]
    started = time.time()
    proc = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=timeout,
                          cwd=tempfile.gettempdir())
    seconds = round(time.time() - started, 2)
    if proc.returncode != 0:
        raise RuntimeError("claude -p exited %d: %s" % (proc.returncode, proc.stderr.strip()[:500]))
    envelope = json.loads(proc.stdout)
    if envelope.get("is_error"):
        raise RuntimeError("model call returned an error: %s" % envelope.get("result"))
    used = list((envelope.get("modelUsage") or {}).keys())
    return envelope, seconds, used


def check_shape(out):
    """Shape problems that make the form unusable. Field-level checks stay in quote.py step 2."""
    problems = []
    if not isinstance(out, dict):
        return ["model output is not a JSON object"]
    if not isinstance(out.get("items"), list) or not out["items"]:
        problems.append("no items")
    for i, it in enumerate(out.get("items") or [], start=1):
        quoted = it.get("item_type") in ("drawdown", "rollover")
        has_tenor = it.get("tenor_business_days") is not None
        has_end = it.get("end_date") not in (None, "")
        if quoted and has_tenor == has_end:
            problems.append("item %d: needs exactly one of tenor_business_days or end_date" % i)
        if it.get("item_type") == "repayment" and (has_tenor or has_end):
            problems.append("item %d: a repayment carries no tenor or end date" % i)
        for key in ("value_date", "end_date"):
            v = it.get(key)
            if v not in (None, "") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v)):
                problems.append("item %d: %s is not YYYY-MM-DD: %r" % (i, key, v))
    return problems


def to_form(out):
    """Model output -> the form quote.py reads. Drop nulls; whole amounts as integers."""
    items = []
    for it in out["items"]:
        item = {"item_type": it["item_type"], "currency": it["currency"].strip().upper()}
        amount = it["amount"]
        item["amount"] = int(amount) if float(amount).is_integer() else amount
        item["value_date"] = it["value_date"]
        if it.get("tenor_business_days") is not None:
            item["tenor_business_days"] = it["tenor_business_days"]
        if it.get("end_date") not in (None, ""):
            item["end_date"] = it["end_date"]
        item["facility_ref"] = it["facility_ref"]
        items.append(item)
    return {"request_id": out["request_id"].strip(), "items": items}


def run(request_path, out_dir, model=DEFAULT_MODEL, timeout=120):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    text = email_text(Path(request_path).read_text(encoding="utf-8"))
    meta = {"step": 1, "prompt_version": PROMPT_VERSION, "model_requested": model,
            "request_file": str(request_path), "outcome": None, "hand_back_reason": None}
    try:
        envelope, seconds, used = call_model(text, model, timeout)
    except (RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        meta.update(outcome="hand_back", hand_back_reason="step 1: model call failed: %s" % exc)
        write_json(out_dir / "extract-meta.json", meta)
        return meta
    out = envelope.get("structured_output")
    usage = envelope.get("usage") or {}
    meta.update(model_used=used, seconds=seconds, raw_output=out,
                tokens={"input": usage.get("input_tokens", 0)
                        + usage.get("cache_read_input_tokens", 0)
                        + usage.get("cache_creation_input_tokens", 0),
                        "output": usage.get("output_tokens", 0)})
    if used and used != [model]:
        meta.update(outcome="hand_back", hand_back_reason="step 1: model used %s, not the pinned %s" % (used, model))
    elif out is None:
        meta.update(outcome="hand_back", hand_back_reason="step 1: no structured output from the model")
    else:
        problems = check_shape(out)
        if out.get("unclear"):
            meta.update(outcome="hand_back",
                        hand_back_reason="step 1: model could not copy every value: " + "; ".join(out["unclear"]))
        elif problems:
            meta.update(outcome="hand_back", hand_back_reason="step 1: form not valid: " + "; ".join(problems))
        else:
            form = to_form(out)
            write_json(out_dir / "form.json", form)
            meta.update(outcome="form", form_file=str(out_dir / "form.json"))
    write_json(out_dir / "extract-meta.json", meta)
    return meta


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--request", required=True, help="request text, e.g. fixtures/requests/REQ-001.txt")
    parser.add_argument("--out", required=True, help="output folder; the only place the script writes")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="model id (default %s)" % DEFAULT_MODEL)
    args = parser.parse_args(argv)
    if not Path(args.request).is_file():
        parser.error("--request %s is not a file" % args.request)
    meta = run(args.request, args.out, args.model)
    print("step 1 outcome: %s" % meta["outcome"])
    if meta["hand_back_reason"]:
        print(meta["hand_back_reason"])
    print("outputs written to %s" % args.out)
    return 0 if meta["outcome"] == "form" else 2


if __name__ == "__main__":
    sys.exit(main())
