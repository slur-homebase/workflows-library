"""Shared runner for the per-request tests. Not a test module itself.

Runs skills/rate-quote/scripts/quote.py as a subprocess, the way a reviewer
would run it, and reads back the four output files. Standard library only.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "quote.py"
FIXTURES = REPO / "fixtures"


class Run:
    """One completed run of the script and everything it wrote."""

    def __init__(self, request_id, received, sheet_dir=None, form=None):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / request_id.lower()
        self.proc = subprocess.run(
            [sys.executable, str(SCRIPT),
             "--form", str(form or FIXTURES / "forms" / ("%s.json" % request_id)),
             "--received", received,
             "--sheet-dir", str(sheet_dir or FIXTURES / "rate_sheets"),
             "--calendars", str(FIXTURES / "calendars"),
             "--margins", str(FIXTURES / "margins.csv"),
             "--out", str(self.out)],
            capture_output=True, text=True, cwd=str(REPO))
        self.result = json.loads((self.out / "result.json").read_text())
        self.result_text = (self.out / "result.json").read_text()
        self.items = self.result["items"]
        self.draft = (self.out / "quote-draft.txt").read_text()
        self.check = (self.out / "pre-send-check.txt").read_text()

    def cleanup(self):
        self.tmp.cleanup()
