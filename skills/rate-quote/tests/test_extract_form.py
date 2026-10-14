"""Step 1 (extract_form.py) code checks. No model call: call_model is replaced.

The model's own accuracy is measured in evals/step1-extraction/, not here.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import extract_form as ef  # noqa: E402

REQ = Path(__file__).resolve().parent.parent / "fixtures" / "requests" / "REQ-003.txt"

GOOD = {"request_id": "REQ-003", "unclear": [], "items": [
    {"item_type": "repayment", "currency": "usd", "amount": 2000000.0, "value_date": "2026-10-02",
     "tenor_business_days": None, "end_date": None, "facility_ref": "FAC-SYN-0003"},
    {"item_type": "rollover", "currency": "USD", "amount": 3000000, "value_date": "2026-10-02",
     "tenor_business_days": 90, "end_date": None, "facility_ref": "FAC-SYN-0003"}]}


def fake_model(output, used=("claude-haiku-5-5",)):
    def call(text, model, timeout):
        fake_model.seen_text = text
        return {"structured_output": output, "usage": {"input_tokens": 1, "output_tokens": 1}}, 0.1, list(used)
    return call


class ExtractFormTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.real = ef.call_model

    def tearDown(self):
        ef.call_model = self.real
        self.tmp.cleanup()

    def test_default_model_is_pinned_haiku_5_5(self):
        self.assertEqual(ef.DEFAULT_MODEL, "claude-haiku-5-5")

    def test_case_line_never_reaches_the_model(self):
        ef.call_model = fake_model(GOOD)
        ef.run(REQ, self.out)
        self.assertNotIn("Case:", fake_model.seen_text)
        self.assertIn("Request-ID: REQ-003", fake_model.seen_text)

    def test_good_output_becomes_the_quote_form(self):
        ef.call_model = fake_model(GOOD)
        meta = ef.run(REQ, self.out)
        self.assertEqual(meta["outcome"], "form")
        form = json.loads((self.out / "form.json").read_text())
        self.assertEqual(form, json.loads((REQ.parent.parent / "forms" / "REQ-003.json").read_text()))

    def test_unclear_hands_back_and_writes_no_form(self):
        bad = dict(GOOD, unclear=["tenor given in months"])
        ef.call_model = fake_model(bad)
        meta = ef.run(REQ, self.out)
        self.assertEqual(meta["outcome"], "hand_back")
        self.assertIn("tenor given in months", meta["hand_back_reason"])
        self.assertFalse((self.out / "form.json").exists())

    def test_both_tenor_and_end_date_hands_back(self):
        bad = json.loads(json.dumps(GOOD))
        bad["items"][1]["end_date"] = "2026-11-20"
        ef.call_model = fake_model(bad)
        meta = ef.run(REQ, self.out)
        self.assertEqual(meta["outcome"], "hand_back")
        self.assertIn("exactly one", meta["hand_back_reason"])

    def test_non_iso_date_hands_back(self):
        bad = json.loads(json.dumps(GOOD))
        bad["items"][0]["value_date"] = "2 October 2026"
        ef.call_model = fake_model(bad)
        self.assertEqual(ef.run(REQ, self.out)["outcome"], "hand_back")

    def test_other_model_answering_hands_back(self):
        ef.call_model = fake_model(GOOD, used=("claude-haiku-4-5-20251001",))
        meta = ef.run(REQ, self.out)
        self.assertEqual(meta["outcome"], "hand_back")
        self.assertIn("not the pinned", meta["hand_back_reason"])

    def test_failed_call_hands_back(self):
        def boom(text, model, timeout):
            raise RuntimeError("no login")
        ef.call_model = boom
        meta = ef.run(REQ, self.out)
        self.assertEqual(meta["outcome"], "hand_back")
        self.assertIn("model call failed", meta["hand_back_reason"])


if __name__ == "__main__":
    unittest.main()
