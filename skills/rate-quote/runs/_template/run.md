# Run RUN-YYYYMMDD-NN

## 1. Versions (fill in before the run)

- run_date:
- operator: (who started the run)
- skill_commit: (git commit of `skills/` used; must be a frozen hash for counted runs)
- acceptance_rule_version: (e.g. `expected-answers-v0.2` or frozen rule commit)
- fixture_commit: (git commit of `fixtures/`)
- route: (A script-first | B no model | C one agent)
- model: (model name for step 1, or `none`; model route: `claude-haiku-5-5`)
- step1_prompt_version: (from `output/step1/extract-meta.json`, e.g. `step1-v0.3`; `n/a` if no model)
- step1_model_used: (from `extract-meta.json` `model_used`; must equal `model`)
- model_used_for_wording: (yes | no)

## 2. Inputs

- request_id: (e.g. REQ-001)
- request_file: `fixtures/requests/REQ-XXX.txt`
- form_source: (model, via `skills/rate-quote/scripts/run_request.py` | hand-written `fixtures/forms/REQ-XXX.json`)
- step1_expected_form: `fixtures/forms/REQ-XXX.json` (check 2 compares the model form with it field by field)
- received_date:
- rate_sheet_used: (folder name, e.g. `rate_sheet_20260928`)
- rate_sheet_date_matches_received_date: (yes | no)
- margin_supplied: (from `fixtures/margins.csv`)

## 3. Checks (expected vs actual)

Expected values come from the acceptance rule named in section 1.

| # | Check | Expected | Actual | Pass |
|---|---|---|---|---|
| 1 | Items found in email (count and type) | | | |
| 2 | Step 1 form fields correct on first pass | all fields | | |
| 3 | Grounding check result (step 3) | | | |
| 4 | Route (quote, acknowledge, hand back) | | | |
| 5 | Sheet freshness check | | | |
| 6 | Value date (after T+2 and holiday rules) | | | |
| 7 | End date (after holiday rules) | | | |
| 8 | Days / tenor | | | |
| 9 | Sheet row used (regular tenor, Odd_Dates or forward rate) | | | |
| 10 | Cost of funds (TP or forward rate, 4dp) | | | |
| 11 | Margin | | | |
| 12 | All-in rate, 4dp (audit line) | | | |
| 13 | All-in rate, 2dp, rounded half down (in draft) | | | |
| 14 | Draft names the sheet date | yes | | |
| 15 | Draft states purpose (drawdown or rollover) | | | |
| 16 | Date-adjustment note to customer, if a date moved | | | |
| 17 | Draft check (step 11): numbers in draft equal script output | yes | | |
| 18 | Model wording edit rejected by step 11 (n/a if no wording model) | no | | |
| 19 | No send or external action attempted | none | | |

Checks passed: __ / __

## 4. Human review

- bh_review_minutes:
- bh_changes: (none | wording only | list every number, date or outcome changed)
- rm_margin_change: (none | old → new; synthetic runs: none)
- misread_found_by_bh_not_caught_by_code: (none | describe)
- accepted: (yes | no)

## 5. Verdict

- verdict: (pass | fail | invalid)
- counts_toward_six: (yes | no, and why)
- reason:

## 6. Corrections (append only, dated)

-
