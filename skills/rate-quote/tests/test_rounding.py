"""Customer figure rounding: 2 decimals, half down (owner decision 2026-10-05).
An exact 5 in the third decimal rounds down. Decimal, not float."""

import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import quote  # noqa: E402


class TestHalfDownRounding(unittest.TestCase):

    def test_exact_half_rounds_down(self):
        self.assertEqual(quote.round_half_down_2dp(Decimal("5.5650")), Decimal("5.56"))

    def test_above_half_rounds_up(self):
        self.assertEqual(quote.round_half_down_2dp(Decimal("5.3574")), Decimal("5.36"))

    def test_below_half_rounds_down(self):
        self.assertEqual(quote.round_half_down_2dp(Decimal("5.2986")), Decimal("5.30"))

    def test_string_form_keeps_trailing_zero(self):
        self.assertEqual(str(quote.round_half_down_2dp(Decimal("5.2986"))), "5.30")

    def test_other_halves(self):
        for raw, expected in (("4.0050", "4.00"), ("4.0051", "4.01"), ("4.0049", "4.00"),
                              ("1.1150", "1.11"), ("0.0050", "0.00")):
            with self.subTest(raw=raw):
                self.assertEqual(str(quote.round_half_down_2dp(Decimal(raw))), expected)


if __name__ == "__main__":
    unittest.main()
