"""Stale-sheet check (route step 5, expected-answers v0.2 "Stale-sheet check"):
a request received 2026-09-29 run against a folder holding only the
2026-09-28 sheet must stop and name the missing date. No rate anywhere.

Run:  python3 -m unittest discover -s tests -v
"""

import re
import shutil
import tempfile
import unittest
from pathlib import Path

from support import FIXTURES, Run

RATE_FIGURE = re.compile(r"\d+\.\d+\s?%")


class StaleSheetMixin:

    def test_stopped_with_hand_back(self):
        self.assertEqual(self.q.proc.returncode, 2, self.q.proc.stderr)
        self.assertEqual(self.q.result["outcome"], "hand_back")
        self.assertEqual(self.q.result["hand_back_step"], 5)
        self.assertIsNone(self.q.result["sheet"])

    def test_reason_names_the_missing_date(self):
        reason = self.q.result["hand_back_reason"]
        self.assertIn("no rate sheet dated %s" % self.MISSING, reason)
        self.assertIn("Stop and wait for the %s sheet" % self.MISSING, reason)
        self.assertIn(reason, self.q.check)
        self.assertIn(reason, self.q.draft)

    def test_no_rate_anywhere(self):
        for text in (self.q.draft, self.q.check, self.q.result_text):
            self.assertIsNone(RATE_FIGURE.search(text))
        self.assertEqual(self.q.items, [])

    def test_no_send(self):
        self.assertFalse(self.q.result["send_attempted"])


class TestOnlyYesterdaysSheetPresent(StaleSheetMixin, unittest.TestCase):
    """Brief item 6: a temporary folder that contains only the 20260928 sheet."""

    MISSING = "2026-09-29"

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.sheets = Path(cls.tmp.name) / "rate_sheets"
        shutil.copytree(FIXTURES / "rate_sheets" / "rate_sheet_20260928", cls.sheets / "rate_sheet_20260928")
        cls.q = Run("REQ-007", "2026-09-29", sheet_dir=cls.sheets)

    @classmethod
    def tearDownClass(cls):
        cls.q.cleanup()
        cls.tmp.cleanup()

    def test_reason_names_the_stale_sheet_present(self):
        self.assertIn("sheets present: rate_sheet_20260928", self.q.result["hand_back_reason"])


class TestSingleSheetFolderPassedAsSheetDir(StaleSheetMixin, unittest.TestCase):
    """--sheet-dir pointing at the 2026-09-28 folder itself, not at its parent."""

    MISSING = "2026-09-29"

    @classmethod
    def setUpClass(cls):
        cls.q = Run("REQ-004", "2026-09-29",
                      sheet_dir=FIXTURES / "rate_sheets" / "rate_sheet_20260928")

    @classmethod
    def tearDownClass(cls):
        cls.q.cleanup()

    def test_reason_names_the_stale_date_found(self):
        self.assertIn("dated 2026-09-28", self.q.result["hand_back_reason"])


class TestReceivedDateWithNoSheet(StaleSheetMixin, unittest.TestCase):
    """A received date with no matching folder among all three fixture sheets."""

    MISSING = "2026-09-27"

    @classmethod
    def setUpClass(cls):
        cls.q = Run("REQ-001", "2026-09-27")

    @classmethod
    def tearDownClass(cls):
        cls.q.cleanup()

    def test_reason_lists_the_sheets_present(self):
        reason = self.q.result["hand_back_reason"]
        for name in ("rate_sheet_20260921", "rate_sheet_20260928", "rate_sheet_20260929"):
            self.assertIn(name, reason)


if __name__ == "__main__":
    unittest.main()
