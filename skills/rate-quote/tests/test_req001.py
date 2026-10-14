"""REQ-001 end to end: the script must reproduce the expected answer in
docs/expected-answers-v0.2.md (REQ-001 line). Standard library only.

Run:  python3 -m unittest discover -s tests -v
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "quote.py"


class TestReq001(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "req001"
        cls.proc = subprocess.run(
            [sys.executable, str(SCRIPT),
             "--form", str(REPO / "fixtures" / "forms" / "REQ-001.json"),
             "--received", "2026-09-28",
             "--sheet-dir", str(REPO / "fixtures" / "rate_sheets"),
             "--calendars", str(REPO / "fixtures" / "calendars"),
             "--margins", str(REPO / "fixtures" / "margins.csv"),
             "--out", str(cls.out)],
            capture_output=True, text=True, cwd=str(REPO))
        cls.result = json.loads((cls.out / "result.json").read_text())
        cls.item = cls.result["items"][0]
        cls.draft = (cls.out / "quote-draft.txt").read_text()
        cls.check = (cls.out / "pre-send-check.txt").read_text()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_script_ran_cleanly(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)
        for name in ("form-validated.json", "result.json", "quote-draft.txt", "pre-send-check.txt"):
            self.assertTrue((self.out / name).is_file(), name)

    def test_outcome_is_quote_draft(self):
        self.assertEqual(self.result["outcome"], "quote_draft")
        self.assertIsNone(self.result["hand_back_reason"])
        self.assertEqual(self.item["item_outcome"], "quote")

    def test_value_date(self):
        self.assertEqual(self.item["value_date"], "2026-09-30")
        self.assertEqual(self.item["adjustments"], [])

    def test_end_date(self):
        self.assertEqual(self.item["end_date"], "2026-11-16")
        self.assertEqual(self.item["tenor_business_days"], 30)

    def test_num_days(self):
        self.assertEqual(self.item["num_days"], 47)

    def test_lookup_is_odd_dates_row(self):
        lookup = self.item["lookup"]
        self.assertEqual(lookup["table"], "odd_dates")
        self.assertEqual(lookup["maturity_from"], "2026-11-14")
        self.assertEqual(lookup["maturity_to"], "2026-11-20")

    def test_tp_margin_and_all_in(self):
        self.assertEqual(self.item["tp_pct"], "4.2574")
        self.assertEqual(self.item["margin_pct"], "1.10")
        self.assertEqual(self.item["all_in_4dp"], "5.3574")

    def test_customer_rate(self):
        self.assertEqual(self.item["customer_rate"], "5.36%")
        self.assertIn("5.36%", self.draft)

    def test_sheet_date_used(self):
        self.assertEqual(self.result["sheet"]["sheet_date"], "2026-09-28")
        self.assertIn("2026-09-28", self.check)
        self.assertNotIn("2026-09-28", self.draft)  # owner 2026-10-13: no basis line in the customer draft

    def test_draft_names_the_rest(self):
        self.assertIn("Tenor: 47 days", self.draft)  # owner 2026-10-13: calendar days
        self.assertIn("USD 5,000,000", self.draft)
        self.assertIn("30 September 2026", self.draft)
        self.assertIn("16 November 2026", self.draft)
        self.assertNotIn("business days", self.draft)  # owner 2026-10-13: calendar days only
        self.assertIn("USD drawdown\nAmount: USD 5,000,000", self.draft)

    def test_draft_check_passed(self):
        self.assertEqual(self.result["draft_check"]["status"], "pass")
        self.assertEqual(self.result["draft_check"]["problems"], [])

    def test_pre_send_check_prints_values_not_ticks(self):
        self.assertIn("4.2574", self.check)
        self.assertIn("2026-11-14 to 2026-11-20", self.check)
        self.assertIn("1.10", self.check)
        self.assertIn("5.3574", self.check)
        self.assertIn("5.36%", self.check)
        self.assertIn("sheet date used: 2026-09-28", self.check)
        self.assertIn("num_days (sheet start_date to end date): 47", self.check)
        self.assertIn("forward rate used: no", self.check)
        for tick in ("✓", "✔", "[x]", "[X]", "PASS\n"):
            self.assertNotIn(tick, self.check)
        # the same text is printed to stdout
        self.assertIn("TP value: 4.2574", self.proc.stdout)

    def test_no_send(self):
        self.assertFalse(self.result["send_attempted"])


if __name__ == "__main__":
    unittest.main()
