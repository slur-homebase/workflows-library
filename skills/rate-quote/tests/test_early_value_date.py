"""Value date earlier than T+2 (owner correction 2026-10-14, acceptance rule v1.1).

The quote keeps the customer's value date and reads the forward rate row for
that value date and end date. No date-move note. A value date before the
received date goes back to BH. Final figures for REQ-009 are asserted only
after BH's hand calculation is frozen; these tests check the path.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from support import Run

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "quote.py"


class EarlyValueDateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.q = Run("REQ-009", "2026-09-29")
        cls.item = cls.q.items[0]

    @classmethod
    def tearDownClass(cls):
        cls.q.cleanup()

    def test_outcome_is_quote_draft(self):
        self.assertEqual(self.q.result["outcome"], "quote_draft")

    def test_value_date_kept_not_moved_to_t_plus_2(self):
        self.assertEqual(self.item["t_plus_2"], "2026-10-01")
        self.assertEqual(self.item["value_date"], "2026-09-30")
        self.assertEqual(self.item["value_date_requested"], "2026-09-30")
        self.assertEqual(self.item["adjustments"], [])
        self.assertNotIn("Please note", self.q.draft)

    def test_forward_rate_path_used(self):
        self.assertTrue(self.item["forward_rate_used"])
        self.assertEqual(self.item["lookup"]["file"], "forward_rate_calculator.csv")
        self.assertEqual(self.item["lookup"]["value_date"], "2026-09-30")
        self.assertEqual(self.item["forward_rate_pct"], "4.8531")
        self.assertIsNone(self.item["tp_pct"])
        self.assertIn("earlier than T+2", self.item["value_date_basis"])
        self.assertIn("earlier than T+2, forward rate path", self.q.check)

    def test_rate_is_forward_plus_margin(self):
        self.assertEqual(Decimal(self.item["all_in_4dp"]),
                         Decimal(self.item["forward_rate_pct"]) + Decimal(self.item["margin_pct"]))

    def test_draft_check_passed(self):
        self.assertEqual(self.q.result["draft_check"]["status"], "pass")


class BeforeReceivedDateTest(unittest.TestCase):
    def test_value_date_before_received_hands_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "requests").mkdir()
            (tmp / "forms").mkdir()
            (tmp / "requests" / "T-EARLY.txt").write_text(
                "Request-ID: T-EARLY\nReceived: 2026-09-29 09:00 SGT\nSubject: Drawdown\n\n"
                "Please quote USD 1,000,000 under FAC-SYN-0901, value date 28 September 2026, tenor 30 business days.\n")
            (tmp / "forms" / "T-EARLY.json").write_text(json.dumps({"request_id": "T-EARLY", "items": [{
                "item_type": "drawdown", "currency": "USD", "amount": 1000000, "value_date": "2026-09-28",
                "tenor_business_days": 30, "facility_ref": "FAC-SYN-0901"}]}))
            (tmp / "margins.csv").write_text("request_id,margin_pct,supplied_by\nT-EARLY,1.00,RM\n")
            out = tmp / "out"
            subprocess.run([sys.executable, str(SCRIPT), "--form", str(tmp / "forms" / "T-EARLY.json"),
                            "--received", "2026-09-29", "--sheet-dir", str(REPO / "fixtures" / "rate_sheets"),
                            "--calendars", str(REPO / "fixtures" / "calendars"), "--margins", str(tmp / "margins.csv"),
                            "--out", str(out)], capture_output=True, text=True, cwd=str(REPO))
            result = json.loads((out / "result.json").read_text())
        self.assertEqual(result["outcome"], "hand_back")
        self.assertEqual(result["hand_back_step"], 6)
        self.assertIn("before the received date", result["hand_back_reason"])


if __name__ == "__main__":
    unittest.main()
