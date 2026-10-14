"""Step 3 thread rule (BH, 2026-10-13).

Ground the form against the newest message only, and hand back any thread whose
newest message corrects or changes an earlier one.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import quote  # noqa: E402

HEADER = "Request-ID: T-1\nCase: test note 9 October 2026 USD 9,000,000\nReceived: 2026-09-29 17:10 SGT\nFrom: [CUSTOMER_T]\nSubject: RE: Drawdown quote\n\n"
OLD = ("> From: [CUSTOMER_T]\n> Sent: 28 September 2026\n>\n"
       "> Please quote a USD 4,000,000 drawdown under FAC-SYN-0901, value date 1 October 2026, tenor 30 business days.\n")


def form(amount, value_date="2026-10-01", tenor=30):
    return {"request_id": "T-1", "items": [{
        "item_no": 1, "item_type": "drawdown", "currency": "USD", "amount": str(amount),
        "value_date": value_date, "tenor_business_days": tenor, "facility_ref": "FAC-SYN-0901"}]}


class ThreadGroundingTest(unittest.TestCase):
    def test_correction_thread_hands_back_even_with_the_right_values(self):
        text = HEADER + "Correction to my note below: the amount is USD 4,500,000, not USD 4,000,000. Everything else unchanged.\n\n" + OLD
        with self.assertRaises(quote.HandBack) as cm:
            quote.ground_form(form(4500000), text)
        self.assertEqual(cm.exception.step, 3)
        self.assertIn("corrects or changes", cm.exception.reason)

    def test_correction_thread_hands_back_with_the_old_value(self):
        # The failure the rule exists for: the old amount is also in the text.
        text = HEADER + "Correction to my note below: the amount is USD 4,500,000, not USD 4,000,000. Everything else unchanged.\n\n" + OLD
        with self.assertRaises(quote.HandBack):
            quote.ground_form(form(4000000), text)

    def test_value_only_in_quoted_message_is_not_grounded(self):
        text = HEADER + "Hi team, please go ahead as per my note below.\n\n" + OLD
        with self.assertRaises(quote.HandBack) as cm:
            quote.ground_form(form(4000000), text)
        self.assertEqual(cm.exception.step, 3)
        self.assertIn("newest message", cm.exception.reason)

    def test_newest_message_with_every_value_passes_beside_a_quote(self):
        text = (HEADER + "Please quote a USD 4,000,000 drawdown under FAC-SYN-0901, value date 1 October 2026, "
                "tenor 30 business days.\n\n" + OLD)
        report = quote.ground_form(form(4000000), text)
        self.assertTrue(report["quoted_text_ignored"])

    def test_header_lines_never_ground_a_value(self):
        # 9 October 2026 and USD 9,000,000 appear only in the Case: header line.
        text = HEADER + "Please quote a USD 4,000,000 drawdown under FAC-SYN-0901, value date 1 October 2026, tenor 30 business days.\n"
        with self.assertRaises(quote.HandBack):
            quote.ground_form(form(9000000), text)
        with self.assertRaises(quote.HandBack):
            quote.ground_form(form(4000000, value_date="2026-10-09"), text)

    def test_subject_line_still_grounds(self):
        # REQ-003 names its maturity date in the Subject line as well as the body.
        newest, quoted = quote.split_request("Request-ID: X\nSubject: 2 Oct maturity\n\nHi\n")
        self.assertIn("2 Oct maturity", newest)
        self.assertEqual(quoted, "")

    def test_x104_end_to_end_hands_back_at_step_3(self):
        cases = Path(__file__).resolve().parent.parent / "evals" / "step1-extraction" / "cases"
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "X-104.json"
            f.write_text(json.dumps(json.loads((cases / "expected" / "X-104.json").read_text())))
            out = Path(tmp) / "out"
            subprocess.run([sys.executable, str(quote.__file__), "--form", str(f), "--received", "2026-09-29",
                            "--sheet-dir", "fixtures/rate_sheets", "--calendars", "fixtures/calendars",
                            "--margins", "fixtures/margins.csv", "--requests", str(cases / "requests"),
                            "--out", str(out)], capture_output=True, text=True,
                           cwd=str(Path(__file__).resolve().parent.parent))
            result = json.loads((out / "result.json").read_text())
        self.assertEqual(result["outcome"], "hand_back")
        self.assertEqual(result["hand_back_step"], 3)
        self.assertNotIn("customer_rate", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
