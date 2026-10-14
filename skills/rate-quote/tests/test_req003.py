"""REQ-003 end to end: bundled repayment plus rollover, forward rate path.
Expected values from docs/expected-answers-v0.2.md (REQ-003 line).

Run:  python3 -m unittest discover -s tests -v
"""

import re
import shutil
import tempfile
import unittest
from pathlib import Path

from support import FIXTURES, Run


class TestReq003(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.q = Run("REQ-003", "2026-09-29")
        cls.item1, cls.item2 = cls.q.items

    @classmethod
    def tearDownClass(cls):
        cls.q.cleanup()

    def test_script_ran_cleanly(self):
        self.assertEqual(self.q.proc.returncode, 0, self.q.proc.stderr)
        for name in ("form-validated.json", "result.json", "quote-draft.txt", "pre-send-check.txt"):
            self.assertTrue((self.q.out / name).is_file(), name)

    def test_outcome_is_quote_draft(self):
        self.assertEqual(self.q.result["outcome"], "quote_draft")
        self.assertIsNone(self.q.result["hand_back_reason"])
        self.assertEqual(len(self.q.items), 2)

    def test_item1_acknowledged_no_rate(self):
        self.assertEqual(self.item1["item_type"], "repayment")
        self.assertEqual(self.item1["item_outcome"], "acknowledge")
        self.assertEqual(self.item1["value_date"], "2026-10-02")
        for key in ("tp_pct", "forward_rate_pct", "all_in_4dp", "customer_rate", "customer_rate_2dp", "lookup"):
            self.assertNotIn(key, self.item1)

    def test_item2_forward_rate(self):
        self.assertEqual(self.item2["item_type"], "rollover")
        self.assertEqual(self.item2["item_outcome"], "quote")
        self.assertTrue(self.item2["forward_rate_used"])
        self.assertEqual(self.item2["forward_rate_pct"], "4.3150")
        self.assertEqual(self.item2["cost_of_funds_pct"], "4.3150")
        self.assertIsNone(self.item2["tp_pct"])
        self.assertEqual(self.item2["lookup"]["file"], "forward_rate_calculator.csv")
        self.assertEqual(self.item2["lookup"]["value_date"], "2026-10-02")
        self.assertEqual(self.item2["lookup"]["maturity_date"], "2027-02-18")

    def test_item2_dates(self):
        self.assertEqual(self.item2["value_date"], "2026-10-02")
        self.assertEqual(self.item2["t_plus_2"], "2026-10-01")
        self.assertEqual(self.item2["adjustments"], [])
        self.assertEqual(self.item2["tenor_business_days"], 90)
        self.assertEqual(self.item2["end_date"], "2027-02-18")

    def test_item2_margin_and_all_in(self):
        self.assertEqual(self.item2["margin_pct"], "1.25")
        self.assertEqual(self.item2["all_in_4dp"], "5.5650")
        self.assertEqual(self.item2["customer_rate_2dp"], "5.56")
        self.assertEqual(self.item2["customer_rate"], "5.56%")

    def test_item2_purpose_is_rollover(self):
        self.assertEqual(self.item2["purpose"], "rollover")
        self.assertIn("USD rollover\nAmount: USD 3,000,000", self.q.draft)

    def test_sheet_date_used(self):
        self.assertEqual(self.q.result["sheet"]["sheet_date"], "2026-09-29")
        self.assertIn("2026-09-29", self.q.check)
        self.assertNotIn("2026-09-29", self.q.draft)

    def test_one_draft_covers_both_items(self):
        d = self.q.draft
        self.assertIn("USD repayment\nWe note your repayment of USD 2,000,000", d)
        self.assertIn("USD 2,000,000", d)
        self.assertIn("No rate applies to this item", d)
        self.assertIn("USD rollover\nAmount: USD 3,000,000", d)
        self.assertIn("USD 3,000,000", d)
        self.assertIn("2 October 2026", d)
        self.assertIn("18 February 2027", d)
        self.assertIn("Tenor: 139 days", d)  # requested value date to end date, calendar days
        self.assertIn("5.56%", d)
        # exactly one rate figure in the draft: item 1 carries none
        self.assertEqual(re.findall(r"\d+\.\d+%", d), ["5.56%"])
        self.assertLess(d.index("USD repayment\nWe note your repayment of USD 2,000,000"), d.index("USD rollover\nAmount: USD 3,000,000"))

    def test_no_item_numbering_template_v04(self):
        # owner decision 2026-10-14, option A
        self.assertNotIn("Item ", self.q.draft)
        self.assertNotIn("Currency and amount", self.q.draft)

    def test_draft_check_passed(self):
        self.assertEqual(self.q.result["draft_check"]["status"], "pass")
        self.assertEqual(self.q.result["draft_check"]["problems"], [])

    def test_pre_send_check_names_forward_rate_file_and_row(self):
        c = self.q.check
        self.assertIn("forward rate used: yes, 4.3150", c)
        self.assertIn("forward_rate_calculator.csv row 2", c)
        self.assertIn("rate_sheet_20260929", c)
        self.assertIn("value_date 2026-10-02, maturity_date 2027-02-18", c)
        self.assertIn("all-in 4 dp: 5.5650", c)
        self.assertIn("customer figure 2 dp, rounded half down: 5.56%", c)
        self.assertIn("repayment acknowledged on 2026-10-02; no rate", c)
        self.assertIn("sheet date used: 2026-09-29", c)
        for tick in ("✓", "✔", "[x]", "[X]", "PASS\n"):
            self.assertNotIn(tick, c)
        self.assertIn("forward rate used: yes, 4.3150", self.q.proc.stdout)

    def test_no_send(self):
        self.assertFalse(self.q.result["send_attempted"])


class TestReq003NoForwardRow(unittest.TestCase):
    """The forward rate file missing or lacking the row = hand back naming it."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        sheets = Path(cls.tmp.name) / "sheets"
        shutil.copytree(FIXTURES / "rate_sheets" / "rate_sheet_20260929", sheets / "rate_sheet_20260929")
        (sheets / "rate_sheet_20260929" / "forward_rate_calculator.csv").unlink()
        cls.q = Run("REQ-003", "2026-09-29", sheet_dir=sheets)

    @classmethod
    def tearDownClass(cls):
        cls.q.cleanup()
        cls.tmp.cleanup()

    def test_hand_back_names_the_missing_file(self):
        self.assertEqual(self.q.proc.returncode, 2)
        self.assertEqual(self.q.result["outcome"], "hand_back")
        self.assertEqual(self.q.result["hand_back_step"], 7)
        self.assertIn("forward_rate_calculator.csv", self.q.result["hand_back_reason"])
        self.assertIn("later than T+2", self.q.result["hand_back_reason"])
        self.assertEqual(self.q.items[0]["item_outcome"], "acknowledge")
        self.assertEqual(self.q.items[1]["item_outcome"], "hand_back")
        self.assertNotRegex(self.q.draft, r"\d+\.\d+%")
        self.assertFalse(self.q.result["send_attempted"])


if __name__ == "__main__":
    unittest.main()


class TestReq003OwnerDecisions20261013(unittest.TestCase):
    """Owner decisions 2026-10-13: the customer draft never mentions the forward
    rate; the pre-send check counts num_days from the sheet start_date (same
    basis as every other request) and flags the forward path with the
    requested value date, for ease of human review."""

    @classmethod
    def setUpClass(cls):
        cls.q = Run("REQ-003", "2026-09-29")
        cls.item1, cls.item2 = cls.q.items

    @classmethod
    def tearDownClass(cls):
        cls.q.cleanup()

    def test_customer_draft_does_not_mention_forward_rate(self):
        draft = self.q.draft.lower()
        self.assertNotIn("forward", draft)
        self.assertNotIn("fwd", draft)

    def test_num_days_from_sheet_start_date(self):
        # sheet start_date 2026-10-01 to end date 2027-02-18 = 140 calendar days
        self.assertEqual(self.item2["num_days"], 140)
        self.assertIn("sheet start_date 2026-10-01", self.item2["num_days_basis"])

    def test_pre_send_check_flags_forward_path_with_requested_value_date(self):
        c = self.q.check
        self.assertIn("FORWARD RATE PATH", c)
        self.assertIn("requested value date 2026-10-02", c)
        self.assertIn("num_days (sheet start_date 2026-10-01 to end date; FORWARD RATE PATH: requested value date 2026-10-02 is later than T+2): 140", c)

    def test_forward_rate_tenor_reported(self):
        self.assertEqual(self.item2["forward_tenor_days"], 139)
        self.assertIn("forward rate tenor: 139 calendar days (requested value date 2026-10-02 to end date 2027-02-18)", self.q.check)
