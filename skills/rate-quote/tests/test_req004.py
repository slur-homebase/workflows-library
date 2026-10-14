"""REQ-004 end to end: end date given directly, lands on a US holiday, moved.
Expected values from docs/expected-answers-v0.2.md (REQ-004 line).

Run:  python3 -m unittest discover -s tests -v
"""

import unittest

from support import Run


class TestReq004(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.q = Run("REQ-004", "2026-09-29")
        cls.item = cls.q.items[0]

    @classmethod
    def tearDownClass(cls):
        cls.q.cleanup()

    def test_script_ran_cleanly(self):
        self.assertEqual(self.q.proc.returncode, 0, self.q.proc.stderr)
        for name in ("form-validated.json", "result.json", "quote-draft.txt", "pre-send-check.txt"):
            self.assertTrue((self.q.out / name).is_file(), name)

    def test_outcome_is_quote_draft_not_revision(self):
        self.assertEqual(self.q.result["outcome"], "quote_draft")
        self.assertIsNone(self.q.result["hand_back_reason"])
        self.assertEqual(self.item["item_outcome"], "quote")

    def test_value_date(self):
        self.assertEqual(self.item["value_date"], "2026-10-01")
        self.assertEqual(self.item["t_plus_2"], "2026-10-01")
        self.assertFalse(self.item["forward_rate_used"])

    def test_end_date_moved_off_us_holiday(self):
        self.assertEqual(self.item["end_date_requested"], "2026-11-11")
        self.assertEqual(self.item["end_date"], "2026-11-12")
        self.assertEqual(len(self.item["adjustments"]), 1)
        adj = self.item["adjustments"][0]
        self.assertEqual(adj["field"], "end_date")
        self.assertEqual(adj["from"], "2026-11-11")
        self.assertEqual(adj["to"], "2026-11-12")
        self.assertIn("US holiday", adj["reason"])
        self.assertIn("11 November 2026", adj["reason"])
        self.assertIn("12 November 2026", adj["reason"])

    def test_num_days_to_adjusted_end(self):
        self.assertEqual(self.item["num_days"], 42)

    def test_lookup_is_odd_dates_row(self):
        lookup = self.item["lookup"]
        self.assertEqual(lookup["table"], "odd_dates")
        self.assertEqual(lookup["maturity_from"], "2026-11-10")
        self.assertEqual(lookup["maturity_to"], "2026-11-16")

    def test_tp_margin_and_all_in(self):
        self.assertEqual(self.item["tp_pct"], "4.2414")
        self.assertEqual(self.item["margin_pct"], "1.15")
        self.assertEqual(self.item["all_in_4dp"], "5.3914")

    def test_customer_rate(self):
        self.assertEqual(self.item["customer_rate"], "5.39%")
        self.assertIn("5.39%", self.q.draft)

    def test_draft_tells_customer_original_date_new_date_and_why(self):
        d = self.q.draft
        self.assertIn("USD 1,500,000", d)
        self.assertIn("1 October 2026", d)
        self.assertIn("End date: 12 November 2026", d)
        self.assertIn("Please note:", d)
        self.assertIn("11 November 2026", d)
        self.assertIn("US holiday", d)
        self.assertIn("12 November 2026", d)
        self.assertIn("Tenor: 42 days", d)
        self.assertNotIn("2026-09-29", d)

    def test_draft_check_passed(self):
        self.assertEqual(self.q.result["draft_check"]["status"], "pass")
        self.assertEqual(self.q.result["draft_check"]["problems"], [])

    def test_pre_send_check_prints_values_not_ticks(self):
        c = self.q.check
        self.assertIn("4.2414", c)
        self.assertIn("2026-11-10 to 2026-11-16", c)
        self.assertIn("1.15", c)
        self.assertIn("5.3914", c)
        self.assertIn("5.39%", c)
        self.assertIn("sheet date used: 2026-09-29", c)
        self.assertIn("end date: 2026-11-12 (requested 2026-11-11; moved)", c)
        self.assertIn("num_days (sheet start_date to end date): 42", c)
        self.assertIn("forward rate used: no", c)
        for tick in ("✓", "✔", "[x]", "[X]", "PASS\n"):
            self.assertNotIn(tick, c)

    def test_no_send(self):
        self.assertFalse(self.q.result["send_attempted"])


if __name__ == "__main__":
    unittest.main()
