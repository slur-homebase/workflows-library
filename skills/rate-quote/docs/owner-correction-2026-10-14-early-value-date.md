# Owner correction 2026-10-14: value date earlier than T+2

Source: BH in chat, 2026-10-14: "Value date too early should also use the forward rate. This is the correction for edge case 2."

## What changes

- Current rule (acceptance rule v1.0, rule 1; `expected-answers-v0.2.md`): a value date before T+2 is moved to T+2 and the customer is told.
- BH's correction: a value date earlier than T+2 is priced from the forward rate (Forward Rate Calculator), the same way as a value date later than T+2.
- Current code (`quote.py` step 6) still moves an early value date to T+2. Not changed yet.

## Open details (BH to confirm before any code change)

1. The quote keeps the customer's value date (for example 30 Sep) and reads the forward rate row for that value date and end date. No date-move note to the customer.
2. A value date on a weekend or holiday is still moved to the next business day first; if the moved date is not T+2, the forward rate applies.
3. A value date before the received date is handed back.
4. Versioning: this is acceptance rule v1.1. Count 3 (6 of 6 under v1.0) is unaffected: no run in it had an early value date.
5. The forward rate number for the REQ-009 fixture.

## BH's answers (2026-10-14)

1. Yes. 2. Yes. 3. Yes. 4. Yes. 5. Forward rate 4.8531 (synthetic, BH-supplied) for REQ-009.

## Status

- Code: `quote.py` step 6 and 7 changed on branch `fixtures-edge-cases`; tests `tests/test_early_value_date.py`.
- Rule: `acceptance-rule-v1.1.md`, frozen 2026-10-14 on BH's approval.
- Fixture: row added to `fixtures/rate_sheets/rate_sheet_20260929/forward_rate_calculator.csv` (USD, value 2026-09-30, maturity = 30 business days later, 4.8531). The SYNTHETIC .xlsx workbook is not updated; the CSV is what the script reads.
