# Run RUN-20261014-04

## 1. Versions (fill in before the run)

- run_date: 2026-10-14
- operator: the orchestrator agent, at BH's instruction "Run 3" (count 3)
- skill_commit: `eadbd01` (skills/ tree, template v0.4; merged to main as `eaee7ab`). Fixed hash for count 3.
- acceptance_rule_version: `acceptance-rule-v1.0.md` (frozen 2026-10-13, commit `3c8753a`)
- fixture_commit: `9ea3601`
- route: A script-first, model route: step 1 by Haiku 5.5 via `skills/rate-quote/scripts/run_request.py`
- model: `claude-haiku-5-5`
- step1_prompt_version: `step1-v0.3`
- step1_model_used: `claude-haiku-5-5` (from `output/step1/extract-meta.json`)
- model_used_for_wording: no

## 2. Inputs

- request_id: REQ-004
- request_file: `fixtures/requests/REQ-004.txt`
- form_source: model, via `skills/rate-quote/scripts/run_request.py`
- step1_expected_form: `fixtures/forms/REQ-004.json`
- received_date: 2026-09-29
- rate_sheet_used: `rate_sheet_20260929`
- rate_sheet_date_matches_received_date: yes
- margin_supplied: 1.15 (RM)

## 3. Checks (expected vs actual)

Expected values come from the acceptance rule named in section 1.

| # | Check | Expected | Actual | Pass |
|---|---|---|---|---|
| 1 | Items found in email (count and type) | 1, drawdown | 1, drawdown | pass |
| 2 | Step 1 form fields correct on first pass | all fields | all fields; model form identical to `fixtures/forms/REQ-004.json` | pass |
| 3 | Grounding check result (step 3) | all form values found in the newest message | ok | pass |
| 4 | Route (quote, acknowledge, hand back) | quote with date-adjustment note | quote with note | pass |
| 5 | Sheet freshness check | sheet 2026-09-29 = received | sheet 2026-09-29 used | pass |
| 6 | Value date (after T+2 and holiday rules) | 2026-10-01 (= T+2) | 2026-10-01 | pass |
| 7 | End date (after holiday rules) | 2026-11-11 is a US holiday -> 2026-11-12 | 2026-11-12, moved from 2026-11-11 | pass |
| 8 | Days / tenor | 42 calendar days | 42 (customer tenor 42; 27 business days) | pass |
| 9 | Sheet row used (regular tenor, Odd_Dates or forward rate) | Odd_Dates 2026-11-10 to 2026-11-16 (40-46 days) | odd_dates.csv range 2026-11-10 to 2026-11-16 (40-46 days) | pass |
| 10 | Cost of funds (TP or forward rate, 4dp) | 4.2414 | 4.2414 | pass |
| 11 | Margin | 1.15 | 1.15 | pass |
| 12 | All-in rate, 4dp (audit line) | 5.3914 | 5.3914 | pass |
| 13 | All-in rate, 2dp, rounded half down (in draft) | 5.39% | 5.39% | pass |
| 14 | Draft does not name the sheet date; pre-send check does (rule v1.0) | no / yes | no in draft; yes in check | pass |
| 15 | Draft states purpose (drawdown or rollover) | drawdown | "USD drawdown" (template v0.4) | pass |
| 16 | Date-adjustment note to customer, if a date moved | original date, new date, reason (US holiday) | "Please note: The end date you asked for, 11 November 2026, is a US holiday, so this quote runs to the next business day, 12 November 2026." | pass |
| 17 | Draft check (step 11): numbers in draft equal script output | yes | pass, 4 dates and 3 numbers compared | pass |
| 18 | Model wording edit rejected by step 11 (n/a if no wording model) | no | n/a, no wording model | n/a |
| 19 | No send or external action attempted | none | none | pass |

Checks passed by script and the orchestrator agent: 18 / 18 applicable (check 18 n/a). Step 1 call: 3.6 s. Draft identical to `docs/template-v0.4-preview/REQ-004-draft.txt`. Output hashes (SHA-256, first 12): draft.txt `cdedfe03de41`, pre-send-check.txt `0cdcd0167a1b`, result.json `eefd6e3ce0ed`.

## 4. Human review

- bh_review_minutes: 5
- bh_changes: none
- rm_margin_change: none (synthetic)
- misread_found_by_bh_not_caught_by_code: none
- accepted: yes (BH, 2026-10-14)

## 5. Verdict

- verdict: pass
- counts_toward_six: yes. Count 3 (model route, template v0.4), run 3 of 6. Judged against acceptance-rule v1.0 (frozen), skill `eadbd01`, model `claude-haiku-5-5`, prompt `step1-v0.3`.
- reason: all 18 applicable checks pass; the Haiku 5.5 form matched the expected form on the first pass; end date moved off the US holiday and the customer told why; the owner accepted the draft as drafted, 5 minutes of review.

## 6. Corrections (append only, dated)

- 2026-10-14 (public copy only): agent and runtime names replaced with a general term ("the orchestrator agent"), BH decision 2026-10-14. The private source record is unchanged.
