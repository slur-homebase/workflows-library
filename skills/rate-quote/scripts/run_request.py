#!/usr/bin/env python3
"""rate-quote, whole route A from the request text: step 1 then steps 2 to 11.

Runs extract_form.py (Haiku 5.5 reads the email into the form), then quote.py
on that form. This is the entry point for supervised runs on the model route.
Same boundaries as both scripts: synthetic fixtures only, no send capability,
writes only inside --out.

Usage (from the repository root):
  python3 skills/rate-quote/scripts/run_request.py \\
      --request fixtures/requests/REQ-007.txt --received 2026-09-29 \\
      --sheet-dir fixtures/rate_sheets --calendars fixtures/calendars \\
      --margins fixtures/margins.csv --out runs/RUN-YYYYMMDD-NN/output

Writes in --out:
  step1/form.json, step1/extract-meta.json   step 1 (model) output
  form.json                                   copy of the form quote.py read
  form-validated.json, result.json, quote-draft.txt, pre-send-check.txt
                                              steps 2 to 11, as quote.py writes them
If step 1 hands back, quote.py does not run, and quote-draft.txt and
pre-send-check.txt carry the step 1 hand-back reason.

Exit codes: 0 = draft or acknowledgement; 2 = hand back at any step; 1 = could not run.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import extract_form  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--request", required=True)
    ap.add_argument("--received", required=True)
    ap.add_argument("--sheet-dir", required=True)
    ap.add_argument("--calendars", required=True)
    ap.add_argument("--margins", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=extract_form.DEFAULT_MODEL)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    request = Path(args.request)

    meta = extract_form.run(request, out / "step1", args.model)
    print("step 1 (%s, prompt %s): %s" % (", ".join(meta.get("model_used") or [args.model]),
                                          meta["prompt_version"], meta["outcome"]))
    if meta["outcome"] != "form":
        note = "No quote drafted for %s.\nHand back at %s\n" % (request.stem, meta["hand_back_reason"])
        (out / "quote-draft.txt").write_text(note, encoding="utf-8")
        (out / "pre-send-check.txt").write_text(
            "PRE-SEND CHECK: %s\noutcome: hand_back\n%s\nsend capability: none. Nothing was sent.\n"
            % (request.stem, meta["hand_back_reason"]), encoding="utf-8")
        print(meta["hand_back_reason"])
        return 2

    shutil.copyfile(out / "step1" / "form.json", out / "form.json")
    proc = subprocess.run([sys.executable, str(HERE / "quote.py"), "--form", str(out / "form.json"),
                           "--received", args.received, "--sheet-dir", args.sheet_dir,
                           "--calendars", args.calendars, "--margins", args.margins,
                           "--requests", str(request.parent), "--out", str(out)])
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
