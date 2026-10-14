"""REQ-007 end to end: end date given directly, between two regular tenors.
Expected values from docs/expected-answers-v0.2.md (REQ-007 line).

Run:  python3 -m unittest discover -s tests -v
"""

import unittest

from support import Run


class TestReq007(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.q = Run("REQ-007", "2026-09-29")
        cls.item = cls.q.items[0]

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
        self.assertEqual(self.item["item_outcome"], "quote")

    def test_value_date(self):
        self.assertEqual(self.item["value_date"], "2026-10-01")
        self.assertEqual(self.item["t_plus_2"], "2026-10-01")
        self.assertFalse(self.item["forward_rate_used"])

    def test_end_date_as_requested(self):
        self.assertEqual(self.item["end_date_requested"], "2026-11-20")
        self.assertEqual(self.item["end_date"], "2026-11-20")
        self.assertEqual(self.item["adjustments"], [])

    def test_num_days(self):
        self.assertEqual(self.item["num_days"], 50)

    def test_lookup_is_odd_dates_row_not_regular(self):
        lookup = self.item["lookup"]
        self.assertEqual(lookup["table"], "odd_dates")
        self.assertEqual(lookup["maturity_from"], "2026-11-17")
        self.assertEqual(lookup["maturity_to"], "2026-11-23")

    def test_tp_margin_and_all_in(self):
        self.assertEqual(self.item["tp_pct"], "4.2486")
        self.assertEqual(self.item["margin_pct"], "1.05")
        self.assertEqual(self.item["all_in_4dp"], "5.2986")

    def test_customer_rate_keeps_trailing_zero(self):
        self.assertEqual(self.item["customer_rate_2dp"], "5.30")
        self.assertEqual(self.item["customer_rate"], "5.30%")
        self.assertIn("5.30%", self.q.draft)

    def test_draft_names_the_rest(self):
        d = self.q.draft
        self.assertIn("USD 2,000,000", d)
        self.assertIn("1 October 2026", d)
        self.assertIn("20 November 2026", d)
        self.assertIn("USD drawdown\nAmount: USD 2,000,000", d)
        self.assertIn("Tenor: 50 days", d)
        self.assertNotIn("2026-09-29", d)
        self.assertNotIn("Please note:", d)

    def test_draft_check_passed(self):
        self.assertEqual(self.q.result["draft_check"]["status"], "pass")
        self.assertEqual(self.q.result["draft_check"]["problems"], [])

    def test_pre_send_check_prints_values_not_ticks(self):
        c = self.q.check
        self.assertIn("4.2486", c)
        self.assertIn("2026-11-17 to 2026-11-23", c)
        self.assertIn("1.05", c)
        self.assertIn("5.2986", c)
        self.assertIn("5.30%", c)
        self.assertIn("sheet date used: 2026-09-29", c)
        self.assertIn("num_days (sheet start_date to end date): 50", c)
        self.assertIn("forward rate used: no", c)
        for tick in ("✓", "✔", "[x]", "[X]", "PASS\n"):
            self.assertNotIn(tick, c)

    def test_no_send(self):
        self.assertFalse(self.q.result["send_attempted"])


if __name__ == "__main__":
    unittest.main()
