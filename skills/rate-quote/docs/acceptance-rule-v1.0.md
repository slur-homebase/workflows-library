# Acceptance rule v1.0 (frozen)

Status: FROZEN by owner decision on 2026-10-13 ("Freeze"). From this commit, a supervised run counts toward the six only when it is judged against this file, unchanged. Any change to this rule is a new version (v1.1, v2.0) and restarts the count for runs judged under it.

Sources: `acceptance-rule-draft.md` (map section 9, 2026-09-30), `expected-answers-v0.2.md` (2026-10-05), owner decisions of 2026-10-05 and 2026-10-13. All data synthetic.

## 1. The rule

A run passes when all of the following hold.

1. Dates are validated against the fixture calendars: value date not before T+2 from the received date, and not on a weekend or holiday; end date not on a weekend or holiday. A moved date is moved to the next business day and the customer is told the original date, the new date and why.
2. Tenor in business days matches the manual count on the fixture calendars.
3. Cost of funds matches the row in the sheet dated the day the request was received: the regular tenor row when the end date equals a maturity date; else the Odd_Dates row whose range contains the end date; the Forward Rate Calculator row when the requested value date is later than T+2.
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

## 4. Verdicts

- pass: every applicable check passes and the reviewer accepted the draft as drafted (wording-only edits allowed).
- fail: any check fails, or the reviewer changed a number, date, outcome or what the draft states.
- invalid: the run cannot be judged. Does not count.

## 5. Change log

- v1.0, 2026-10-13: frozen. Content as above.
