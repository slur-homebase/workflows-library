# Expected answers — fixtures v0.2

Status: frozen by reference from `acceptance-rule-v1.0.md` on 2026-10-13 (one amendment there: the draft does not name the sheet date). Do not edit; a change is a new version.
Process source: owner's logic-extraction sheet, tab "Interest rate quote (USD drawdown)", draft v0.2 (steps 1–22).
This file supersedes the per-request answers in `acceptance-rule-draft.md`, which were written for the v0.1 map.

## What changed from v0.1 fixtures
1. SG calendar: 2026-03-23 removed (Hari Raya Puasa falls on Sat 21 Mar 2026; Monday in lieu applies only to Sunday holidays).
2. US calendar: 2026-07-03 removed (owner decision 2026-10-05).
3. Calendars extended to 2027 (SG from MOM 18 Jun 2026 release; US from New York Fed schedule; JP national holidays). AU not extended: AUD is handed back.
4. Rate sheets rebuilt in the real workbook shape: one folder per sheet date with `transfer_pricing.csv` (13 regular tenors 1W–12M, maturity date, calendar days from start date, TP) and `odd_dates.csv` (maturity From/To and days From/To ranges, TP). Old business-day grid files removed. New sheet dated 2026-09-29 added because four requests arrive that day. All rates invented.
5. `forward_rate_calculator.csv` added to the 2026-09-29 sheet: one invented forward rate for REQ-003.
6. REQ-007 added: an end date between two regular tenors.
7. REQ-002 and REQ-005 (JPY) removed with their margins (owner decision 2026-10-05). JPY calendar and JPY sheet blocks kept, because the real sheet has them.

## Rules applied (from the sheet)
- Business day = weekday and not a holiday in either calendar (USD: US + SG; JPY: JP + SG).
- Value date before T+2 or on a holiday → move to T+2 / next business day and tell the customer (step 7).
- End date on a weekend or holiday → move to the next business day and tell the customer (step 7).
- Value date = T+2 → regular tenor row if the end date equals a Mat Date, else the Odd_Dates row whose range contains it (steps 11–12).
- Value date later than T+2 → Forward Rate Calculator (step 10).
- The sheet used must be dated the day the request is received (step 9).
- All-in rate = TP or forward rate + margin from `margins.csv` (step 16). Margin is never changed.
- The customer email shows the all-in rate to 2 decimal places, rounded half down: an exact 5 in the third decimal rounds down (owner decision 2026-10-05). Checks compare the 2-decimal figure; the 4-decimal figure is kept for the audit line.
- A rollover uses the same skill and calculation as a drawdown. Only the purpose on the drawdown notice differs (owner decision 2026-10-05). The draft names the purpose.

## Per request
- **REQ-001** USD, received 2026-09-28, sheet 2026-09-28. Value 2026-09-30 (= T+2). 30 business days → end 2026-11-16 (Mon), 47 days. Odd_Dates row 2026-11-14 to 2026-11-20 (45–51 days), TP 4.2574. All-in 4.2574 + 1.10 = 5.3574 → **5.36%**. Outcome `quote_draft`.
- **REQ-003** USD bundled, received 2026-09-29, sheet 2026-09-29. Item 1 (repay USD 2,000,000): acknowledged, no rate. Item 2 (roll USD 3,000,000): value 2026-10-02 is later than T+2 (2026-10-01), so Forward Rate Calculator: 4.3150. 90 business days → end 2027-02-18 (Thu). All-in 4.3150 + 1.25 = 5.5650 → **5.56%** (exact half, rounded down). Forward rate used: Yes, 4.3150. Outcome `quote_draft` for item 2, purpose stated as rollover.
- **REQ-004** USD, received 2026-09-29, sheet 2026-09-29. Value 2026-10-01 (= T+2). End 2026-11-11 is a US holiday → moved to 2026-11-12 (Thu), 42 days; customer told why. Odd_Dates row 2026-11-10 to 2026-11-16 (40–46 days), TP 4.2414. All-in 4.2414 + 1.15 = 5.3914 → **5.39%**. Outcome `quote_draft` with a date-adjustment note (was `revision_draft` under v0.1).
- **REQ-006** AUD. Outcome `hand_back`. No rate. Unchanged.
- **REQ-007** USD, received 2026-09-29, sheet 2026-09-29. Value 2026-10-01 (= T+2). End 2026-11-20 (Fri), 50 days, between 1M and 2M. Odd_Dates row 2026-11-17 to 2026-11-23 (47–53 days), TP 4.2486. All-in 4.2486 + 1.05 = 5.2986 → **5.30%**. Outcome `quote_draft`.

## Stale-sheet check
Any request received on 2026-09-29 run against the 2026-09-28 or 2026-09-21 sheet must stop and wait (step 9).

## Owner decisions 2026-10-05
1. Rounding: 2 decimal places; an exact 5 in the third decimal rounds down (half down).
2. Rollover items are quoted by the USD drawdown skill; purpose differs only.
3. JPY requests removed for now.
