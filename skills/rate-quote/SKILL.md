---
name: rate-quote
description: Deterministic core of the interest-rate quoting skill (route A, script first). Takes a step-1 form for a customer drawdown, rollover or repayment request, checks it against the request text, validates dates against currency calendars and the T+2 rule, looks up cost of funds on the dated rate sheet (regular tenor, odd dates, or the forward rate file when the value date is later than T+2), adds the supplied margin, and writes one quote draft covering every item plus a pre-send check for human review. Synthetic fixtures only. No send capability.
version: 0.2
---

# rate-quote v0.2

## What it does

A customer asks for an all-in rate before a drawdown or rollover, sometimes alongside a repayment in the same message. This skill takes the fixed form that step 1 produces from the customer's request (hand-written in `fixtures/forms/` until Week 3), and runs every check and every number in plain code. It writes one draft email covering every item and a pre-send check for a human to review. It never sends anything.

Status: v0.2, built 2026-10-13 on branch `skill-v0.2-all-requests`. Covers steps 2 to 9 and 11 of the route below. Proven against all five fixture requests (REQ-001, REQ-003, REQ-004, REQ-006, REQ-007) and the stale-sheet check. The acceptance rule is still the draft in `docs/expected-answers-v0.2.md`; if the frozen rule changes a step, the rule wins.

What v0.2 added over v0.1:

- Forward rate path: a value date earlier or later than T+2 reads `forward_rate_calculator.csv` in the sheet folder and uses `fwd_fwd_pct` in place of TP.
- Bundled requests: a repayment and a quoted item in one form produce one draft, the repayment acknowledged with no rate, the other item quoted with its purpose named.
- End date given directly on a holiday: moved to the next business day, quoted on the moved date, and the draft tells the customer the original date, the new date and why. Outcome stays `quote_draft`.
- AUD hand-back reason names the Treasury/BBSW path in generic words.
- Stale-sheet check also recognises `--sheet-dir` pointing at a single sheet folder and names its date.

## Boundaries

- Synthetic fixtures only. Every request, rate sheet, calendar entry, margin, forward rate, facility reference and amount in this repository is invented or public.
- Nothing is deployed anywhere. The script is not connected to any mailbox, folder, facility system, terminal or network.
- No send capability. The approval gate is enforced by missing capability, not by instruction: the script has no code path that sends, posts, or writes anywhere except the `--out` folder.
- One model call, step 1 only, in `scripts/extract_form.py` (added 2026-10-13, branch `step1-haiku-extraction`): Haiku 5.5 (`claude-haiku-5-5`, pinned) reads the email into the form. BH's model rule: Haiku 5.5 for routing, classification and extraction. The model sees the email text only, has no tools and does no arithmetic. Any unclear value, wrong shape, failed call or other model answering is a step 1 hand-back. `quote.py` itself still makes no model call. Step 10 (smoothing the wording) is not built.
- Step 1 test runs (not supervised runs): `evals/step1-extraction/README.md`.
- Thread rule in step 3 (BH, 2026-10-13): grounding reads the newest message only; header lines and quoted earlier messages never ground a value. An email that quotes an earlier message and whose newest message corrects or changes it is handed back at step 3.
- Item-count check loosened (BH, 2026-10-13): a labelled amount line ("Amount: 10,000,000.00") counts as a currency amount when the same message has a labelled currency line ("Ccy: USD"). A form with more items than the email names still hands back.
- Supervised runs on the model route start from the request text: `python3 scripts/run_request.py --request fixtures/requests/REQ-XXX.txt --received ... --sheet-dir fixtures/rate_sheets --calendars fixtures/calendars --margins fixtures/margins.csv --out runs/RUN-.../output`.

## The twelve steps and who runs each

Copied from `docs/route-option-script-first.md`. This build covers the rows marked "code, built".

| # | Who | Step | On failure | v0.2 |
|---|---|---|---|---|
| 0 | Human | BH checks available credit covers the amount | Stop before any draft | human |
| 1 | Model (cheap) | Read the email into a fixed JSON form: one record per item, with currency, amount, start date, end date or tenor, item type (drawdown, rollover, repayment) | Form not valid, hand back | `extract_form.py`, Haiku 5.5; hand-written forms in `fixtures/forms/` stay as the expected answers |
| 2 | Code | Validate the form: required fields present, currency in allowed list, dates parse | Hand back with the missing field named | code, built |
| 3 | Code | Grounding check: every amount and date in the form must appear in the email text (format-tolerant match). Item count must match the count of amounts in the email | Mismatch, hand back; never guess | code, built |
| 4 | Code | Route: AUD or anything the sheet cannot answer, hand back for the Treasury/BBSW path. Repayment, acknowledge, no quote | none | code, built |
| 5 | Code | Sheet freshness: sheet date in filename = today | Stop; name the stale date | code, built |
| 6 | Code | Date checks: weekends; holiday calendars (USD: US + SG; JPY: JP + SG); value date T+2; cut-off time; minimum amount and tenor; blackout maturity dates | Build the customer revision-email draft instead of a quote | code, built for weekends, holidays and T+2 only |
| 7 | Code | Compute maturity date; read the regular-tenor row on exact match, else the Odd_Dates row whose range contains it; value date later than T+2 reads the forward rate file instead | No row, hand back | code, built |
| 8 | Code | Rate = cost of funds + RM-supplied margin, owner rounding rule (see `expected-answers-v0.2.md`) | none | code, built |
| 9 | Code | Fill the quote template; state the sheet date used | none | code, built |
| 10 | Model (optional) | Smooth the wording only | Skip if not needed | skipped |
| 11 | Code | Draft check: every number and date in the final draft equals step 8/9 output exactly | Any change, reject the model version, keep the template version | code, built |
| 12 | Human | RM confirms or changes the margin; BH reviews and sends | none | human |

## How to run it

From the `skills/rate-quote/` folder (in workflows-lib):

```
python3 scripts/quote.py \
  --form fixtures/forms/REQ-003.json \
  --received 2026-09-29 \
  --sheet-dir fixtures/rate_sheets \
  --calendars fixtures/calendars \
  --margins fixtures/margins.csv \
  --out /tmp/req003
```

Python 3 standard library only (tested on 3.9). No packages to install.

Inputs:

- `--form`: the step-1 form. Shape is documented in `fixtures/forms/README.md`. A quoted item gives either `tenor_business_days` or `end_date`, never both.
- `--received`: the date the request arrived. The script uses the rate sheet folder dated this day and nothing else.
- `--sheet-dir`: folder holding one `rate_sheet_YYYYMMDD` folder per sheet date, each with `transfer_pricing.csv`, `odd_dates.csv` and, when a forward value date is to be quoted, `forward_rate_calculator.csv`.
- `--calendars`: folder with `US.txt`, `SG.txt`, `JP.txt`, `AU.txt`, one holiday date per line.
- `--margins`: CSV with `request_id, margin_pct, supplied_by`. The margin is never changed by the script.
- `--requests` (optional): folder holding `<request_id>.txt`. Defaults to the `requests` folder beside the form's folder, so with the layout above it finds `fixtures/requests/`.
- `--out`: the only place the script writes.

Outputs in `--out`:

- `form-validated.json`: the normalised form, or the validation error.
- `result.json`: the outcome and every computed value (dates, adjustments, sheet row or forward rate row, cost of funds and its source, margin, 4-decimal and 2-decimal rates, draft check result).
- `quote-draft.txt`: the customer draft from `references/quote-template.md`, one draft covering every item, or a one-line hand-back note.
- `pre-send-check.txt`: the source values a reviewer needs, also printed to the terminal.

Exit code 0 when a draft or acknowledgement was produced, 2 when the outcome is `hand_back`, 1 when the script could not run at all.

## Outcomes

- `quote_draft`: at least one item was quoted, the draft was filled, and the step 11 check passed. A moved value date or end date does not change this outcome; the draft tells the customer why the date moved (rule from `expected-answers-v0.2.md`). A bundled request with a repayment and a quoted item is a `quote_draft` whose draft also acknowledges the repayment.
- `acknowledge`: every item was a repayment. The draft acknowledges them. No rate.
- `hand_back`: something the script will not guess at. The reason and the step number are in `result.json` and in the pre-send check. Causes: a form field missing or malformed; a form value not found in the request text; a currency other than USD (AUD names the Treasury/BBSW path); no rate sheet dated the received date; no sheet row covering the end date; a sheet row whose own day count disagrees with the computed days; a value date later than T+2 with no forward rate file, or no forward rate row for that currency, value date and maturity date; no margin for the request; the step 11 draft check rejecting the draft. A hand-back writes no rate anywhere.
- `revision_draft`: reserved for the step 6 checks not yet built (cut-off time, minimum amount and tenor, blackout dates). Not produced.

## Rules the code applies

- Business day: a weekday that is not in the US or the SG calendar (USD).
- T+2: two business days after the received date. The rate sheet's `start_date` must equal it.
- Value date before the received date: hand back. Value date on a non-business day: moved to the next business day and the customer is told. Then: equal to T+2, the sheet tables; earlier or later than T+2, the forward rate path, see below (owner correction 2026-10-14; earlier dates are no longer moved to T+2).
- End date from a tenor: counted forward in business days from the value date, so it lands on a business day. End date given directly: moved to the next business day if needed, and the customer is told the original date, the new date and the reason (weekend, or which calendar's holiday).
- Days for the lookup: calendar days from the sheet's `start_date` to the end date. Regular row if the end date equals a `mat_date`; otherwise the `odd_dates.csv` row whose maturity range contains the end date.
- Forward rate path: the row of `forward_rate_calculator.csv` in the same sheet folder whose `currency`, `value_date` and `maturity_date` equal the item's currency, value date and computed end date. Its `fwd_fwd_pct` is used in place of TP. The row's `sheet_date` must equal the received date. Days reported for this path run from the value date to the end date, and the pre-send check says so. No file or no row: hand back naming the currency, value date and maturity date looked for and the rows the file holds.
- Rate: cost of funds (TP or forward rate) plus margin, kept to 4 decimals for the audit line. Customer figure: 2 decimals rounded half down, so an exact 5 in the third decimal rounds down (owner decision 2026-10-05). All arithmetic uses `Decimal`.
- Rollover: same calculation as a drawdown; the draft names the purpose (owner decision 2026-10-05).
- Repayment: acknowledged in the draft with its amount and date. No rate, no sheet read for it.
- Step 11: every date and number in the draft must be one of the computed values, and every computed value that matters (amount, value date, end date, tenor, 2-decimal rate, sheet date) must appear. Anything else rejects the draft.
- Pre-send check prints source values, not ticks (owner decision 2026-10-08): sheet date used, table and row read, TP or forward rate, margin, 4-decimal sum, 2-decimal figure, value date and end date with any adjustment reason, days, and "forward rate used: yes, <value>" naming the file and row, or "forward rate used: no".

## Tests

```
python3 -m unittest discover -s tests -v
```

One file per request, each asserting the values on that request's line of `docs/expected-answers-v0.2.md`:

- `tests/test_req001.py`: clean USD drawdown, odd-dates row (unchanged from v0.1).
- `tests/test_req003.py`: bundled repayment plus rollover, forward rate path; also the hand-back when the forward rate file is missing.
- `tests/test_req004.py`: end date on a US holiday, moved, customer told, still `quote_draft`.
- `tests/test_req006.py`: AUD hand-back with no rate in any output file.
- `tests/test_req007.py`: end date between two regular tenors, odd-dates row, trailing zero kept in "5.30%".
- `tests/test_stale_sheet.py`: a request received 2026-09-29 run against a folder holding only the 2026-09-28 sheet stops and names the missing date; also a single sheet folder passed as `--sheet-dir`, and a received date with no sheet at all.
- `tests/test_rounding.py`: half-down rounding on the published cases.
- `tests/support.py`: the shared subprocess runner the request tests use; not a test.

## Files

```
skills/rate-quote/
  SKILL.md                         this file
  BUILD-NOTES.md                   what was built, test output, open items (v0.1 and v0.2 sections)
  scripts/quote.py                 the script (steps 2-9 and 11)
  scripts/extract_form.py          step 1: Haiku 5.5 reads the email into the form
  scripts/run_request.py           whole route from the request text: step 1, then quote.py
  references/quote-template.md     the customer draft template
```
