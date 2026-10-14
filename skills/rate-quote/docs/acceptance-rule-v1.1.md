# Acceptance rule v1.1 (frozen)

Status: FROZEN by owner approval on 2026-10-14 ("Yes", after the REQ-008 and REQ-009 edge-case runs). Same as v1.0 except rules 1 and 3 (owner correction 2026-10-14, `owner-correction-2026-10-14-early-value-date.md`). Owner decision 2026-10-14 (answer 4): count 3 (6 of 6 under v1.0) stays valid because none of its runs had a value date earlier than T+2; the new path is proven by edge case REQ-009, not a fresh six.

Sources: `acceptance-rule-draft.md` (map section 9, 2026-09-30), `expected-answers-v0.2.md` (2026-10-05), owner decisions of 2026-10-05 and 2026-10-13. All data synthetic.

## 1. The rule

A run passes when all of the following hold.

1. Dates are validated against the fixture calendars. A value date before the received date is handed back. A value date or end date on a weekend or holiday is moved to the next business day, and the customer is told the original date, the new date and why. A value date earlier than T+2 is not moved: it keeps the customer's date and is priced from the forward rate (rule 3), with no date-move note.
2. Tenor in business days matches the manual count on the fixture calendars.
3. Cost of funds matches the row in the sheet dated the day the request was received: the regular tenor row when the end date equals a maturity date; else the Odd_Dates row whose range contains the end date; the Forward Rate Calculator row when the value date (after any weekend or holiday move) is earlier or later than T+2; no row for that value date and end date is a hand back.
4. All-in rate = cost of funds + the margin supplied in `margins.csv`, to 4 decimal places. The customer figure is the all-in rate to 2 decimal places, rounded half down (an exact 5 in the third decimal rounds down). The margin is never changed by the skill.
5. The customer draft shows: purpose (drawdown or rollover), currency and amount, value date, end date, tenor in **calendar days from the requested value date to the end date**, and the 2-decimal all-in rate. Nothing else numeric.
6. The customer draft does **not** name the rate sheet date, the source of the margin, the cost of funds or the forward rate. These appear in the pre-send check for the reviewer only. (Owner decision 2026-10-13; this replaces the draft rule's "draft names the sheet date".)
7. The pre-send check prints the source values: sheet date and folder, table and row read, cost of funds, margin with the line "REVIEWER CONFIRMS the margin before send", all-in rate to 4 and 2 decimals, value date, end date, business-day tenor, num_days from the sheet start date (flagged FORWARD RATE PATH with the requested value date when the forward rate applies), forward rate used and its tenor. Ticks alone are not a check.
8. Step 11 passes: every number and date in the draft equals a computed value, and every required computed value is in the draft.
9. A bundled request produces one draft covering every item; a repayment item is acknowledged with no rate; a dropped item is a fail.
10. An AUD request is handed back with no rate anywhere in any output file. A request received on a date with no sheet of that date stops and names the missing date.
11. No send and no action outside the fixture files.
12. The reviewer (BH) accepts the draft as drafted. Wording-only edits are allowed; any change to a number, date, outcome or to what the draft states is a fail.

## 2. The 19 checks

The checks in `runs/_template/run.md`, with check 14 read as: "Draft does not name the sheet date; the pre-send check does." Check 18 is n/a while no wording model is used.

## 3. Expected answers

`expected-answers-v0.2.md`, per-request section, with the single amendment in rule 6 above. Values: REQ-001 5.36% end 2026-11-16; REQ-003 item 1 acknowledged, item 2 5.56% forward rate 4.3150 end 2027-02-18; REQ-004 end moved 2026-11-11 to 2026-11-12, 5.39%, customer told; REQ-006 hand back, no rate; REQ-007 5.30% end 2026-11-20.

Edge-case expected answers (frozen 2026-10-14, before the model runs):

- **REQ-008** USD drawdown, received 2026-09-29, sheet 2026-09-29. Value 2026-10-01 (= T+2). End 2026-11-02 (Mon, business day) equals the 1M mat_date, so the regular row: 1M, 32 days, TP 4.2300. All-in 4.2300 + 1.20 = 5.4300 -> **5.43%**. Customer tenor 32 days. No date note. Outcome `quote_draft`. Source: the orchestrator agent's independent check at BH's request (BH, 2026-10-14: "Can you do your checking for req 8"); not an owner hand calculation.
- **REQ-009** USD drawdown, received 2026-09-29, sheet 2026-09-29. Value 2026-09-30 is a business day, after the received date and earlier than T+2 (2026-10-01): kept, forward rate path (rule 1 and 3, v1.1). 30 business days from 2026-09-30, skipping 2026-10-12 (US), 2026-11-09 (SG) and 2026-11-11 (US): end **2026-11-16**. Customer tenor 47 days. Forward rate 4.8531 (BH-supplied, synthetic). All-in 4.8531 + 1.30 = 6.1531 -> **6.15%**. No date note. Outcome `quote_draft`. Source: BH's hand calculation of the rate (6.15%, 2026-10-14); dates checked by the orchestrator agent.

## 4. Verdicts

- pass: every applicable check passes and the reviewer accepted the draft as drafted (wording-only edits allowed).
- fail: any check fails, or the reviewer changed a number, date, outcome or what the draft states.
- invalid: the run cannot be judged. Does not count.

## 5. Change log

- v1.0, 2026-10-13: frozen.
- v1.1, 2026-10-14, frozen: rules 1 and 3 changed for a value date earlier than T+2 (forward rate, date kept, no note) and a value date before the received date (hand back). Owner correction 2026-10-14. Expected answers for REQ-008 and REQ-009 to be added from BH's hand calculation.
