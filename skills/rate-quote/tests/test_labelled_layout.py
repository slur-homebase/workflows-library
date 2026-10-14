"""Step 3 item-count check, loosened for form-style layouts (BH, 2026-10-13).

"Ccy: USD" on one line and "Amount: 10,000,000.00" on another now count as one
currency amount. The check still stops a form with more items than the email names.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import quote  # noqa: E402

CASES = Path(__file__).resolve().parent.parent / "evals" / "step1-extraction" / "cases"
HEAD = "Request-ID: L-1\nReceived: 2026-09-29 10:15 SGT\nFrom: [CUSTOMER_L]\nSubject: Rollover instruction\n\n"


def item(n, amount, end):
    return {"item_no": n, "item_type": "rollover", "currency": "USD", "amount": str(amount),
            "value_date": "2026-10-02", "end_date": end, "facility_ref": "FAC-SYN-0202"}


class LabelledLayoutTest(unittest.TestCase):
    def test_u202_layout_now_passes_grounding(self):
        text = (CASES / "requests" / "U-202.txt").read_text()
        expected = json.loads((CASES / "expected" / "U-202.json").read_text())
        form = {"request_id": "U-202", "items": [dict(expected["items"][0], item_no=1, amount="10000000")]}
        report = quote.ground_form(form, text)
        self.assertEqual(report["currency_amounts_in_text"], 1)

    def test_two_items_but_one_amount_line_still_hands_back(self):
        text = HEAD + "Facility: FAC-SYN-0202\nCcy: USD\nAmount: 10,000,000.00\nRollover date: 02-10-2026\nNew maturity: 4 January 2027\n"
        form = {"request_id": "L-1", "items": [item(1, 10000000, "2027-01-04"), item(2, 10000000, "2027-01-04")]}
        with self.assertRaises(quote.HandBack) as cm:
            quote.ground_form(form, text)
        self.assertIn("names only 1 currency amounts", cm.exception.reason)

    def test_amount_line_without_a_currency_line_does_not_count(self):
        text = HEAD + "Facility: FAC-SYN-0202\nAmount: 10,000,000.00\nRollover date: 02-10-2026\nNew maturity: 4 January 2027\nIn USD please.\n"
        form = {"request_id": "L-1", "items": [item(1, 10000000, "2027-01-04")]}
        with self.assertRaises(quote.HandBack):
            quote.ground_form(form, text)

    def test_amount_line_with_its_own_currency_is_counted_once(self):
        msg = "Ccy: USD\nAmount: USD 10,000,000.00\n"
        self.assertEqual(quote.count_currency_amounts(msg), 1)

    def test_labelled_lines_in_a_quoted_message_do_not_count(self):
        text = HEAD + "Please roll as below.\n\n> Ccy: USD\n> Amount: 10,000,000.00\n"
        newest, _ = quote.split_request(text)
        self.assertEqual(quote.count_currency_amounts(newest), 0)


if __name__ == "__main__":
    unittest.main()
