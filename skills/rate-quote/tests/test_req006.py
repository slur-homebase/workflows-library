"""REQ-006 end to end: AUD request is handed back with no rate anywhere.
Expected outcome from docs/expected-answers-v0.2.md (REQ-006 line).

Run:  python3 -m unittest discover -s tests -v
"""

import json
import re
import unittest

from support import Run

RATE_FIGURE = re.compile(r"\d+\.\d+\s?%")


class TestReq006(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.q = Run("REQ-006", "2026-09-29")
        cls.item = cls.q.items[0]

    @classmethod
    def tearDownClass(cls):
        cls.q.cleanup()

    def test_script_completed_with_hand_back_exit_code(self):
        self.assertEqual(self.q.proc.returncode, 2, self.q.proc.stderr)
        for name in ("form-validated.json", "result.json", "quote-draft.txt", "pre-send-check.txt"):
            self.assertTrue((self.q.out / name).is_file(), name)

    def test_outcome_is_hand_back(self):
        self.assertEqual(self.q.result["outcome"], "hand_back")
        self.assertEqual(self.q.result["hand_back_step"], 4)
        self.assertEqual(self.item["item_outcome"], "hand_back")

    def test_reason_present_and_names_the_path_generically(self):
        reason = self.q.result["hand_back_reason"]
        self.assertTrue(reason)
        self.assertIn("AUD", reason)
        self.assertIn("Treasury/BBSW", reason)
        self.assertEqual(self.item["hand_back_reason"], reason)
        self.assertIn(reason, self.q.check)
        self.assertIn(reason, self.q.draft)

    def test_no_rate_in_quote_draft(self):
        self.assertNotIn("%", self.q.draft)
        self.assertIsNone(RATE_FIGURE.search(self.q.draft))

    def test_no_rate_fields_in_result(self):
        for key in ("tp_pct", "forward_rate_pct", "cost_of_funds_pct", "all_in_4dp",
                    "customer_rate", "customer_rate_2dp", "margin_pct", "lookup"):
            self.assertNotIn(key, self.item)
        self.assertIsNone(self.q.result["sheet"])
        self.assertIsNone(self.q.result["draft_check"])
        self.assertIsNone(RATE_FIGURE.search(self.q.result_text))

    def test_no_rate_in_pre_send_check(self):
        self.assertIsNone(RATE_FIGURE.search(self.q.check))
        self.assertIn("sheet date used: none", self.q.check)

    def test_form_was_grounded_before_the_hand_back(self):
        self.assertEqual(self.q.result["grounding"]["status"], "ok")

    def test_no_send(self):
        self.assertFalse(self.q.result["send_attempted"])


if __name__ == "__main__":
    unittest.main()
