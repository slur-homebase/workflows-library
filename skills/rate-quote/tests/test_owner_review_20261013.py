"""Owner review of supervised run RUN-20261013-01 (REQ-001), 2026-10-13.
Three template corrections, locked here so they cannot drift:
1. Tenor shown to the customer in calendar days (requested value date to end date).
2. The draft does not say where the margin came from; the reviewer confirms the
   margin before send, and the pre-send check says so.
3. No basis line (sheet date) in the customer draft. The sheet date stays in
   the pre-send check for the reviewer.
"""
import unittest
from support import Run


class TestOwnerReview20261013(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = {rid: Run(rid, rcv) for rid, rcv in
                    (("REQ-001", "2026-09-28"), ("REQ-003", "2026-09-29"),
                     ("REQ-004", "2026-09-29"), ("REQ-007", "2026-09-29"))}

    @classmethod
    def tearDownClass(cls):
        for r in cls.runs.values():
            r.cleanup()

    def test_tenor_in_calendar_days(self):
        for rid, days in (("REQ-001", 47), ("REQ-003", 139), ("REQ-004", 42), ("REQ-007", 50)):
            self.assertIn("Tenor: %d days" % days, self.runs[rid].draft, rid)
            self.assertNotIn("business days", self.runs[rid].draft, rid)

    def test_no_margin_source_in_draft(self):
        for rid, r in self.runs.items():
            low = r.draft.lower()
            self.assertNotIn("margin", low, rid)
            self.assertNotIn("relationship manager", low, rid)

    def test_reviewer_confirms_margin_in_pre_send_check(self):
        for rid, r in self.runs.items():
            self.assertIn("REVIEWER CONFIRMS the margin before send", r.check, rid)

    def test_no_basis_line_in_draft(self):
        for rid, r in self.runs.items():
            self.assertNotIn("Basis:", r.draft, rid)
            self.assertNotIn("rate sheet", r.draft.lower(), rid)
            self.assertIn(r.result["sheet"]["sheet_date"], r.check, rid)


if __name__ == "__main__":
    unittest.main()
