# Run RUN-20261014-01

## 1. Versions (fill in before the run)

- run_date: 2026-10-14
- operator: the orchestrator agent, at BH's instruction "1" (2026-10-13: new count of six on the model route)
- skill_commit: `3dc9a42` (skills/ tree; merged to main as `069eb19`). Fixed hash for count 2.
- acceptance_rule_version: `acceptance-rule-v1.0.md` (frozen 2026-10-13, commit `3c8753a`)
- fixture_commit: `9ea3601`
- route: A script-first, model route: step 1 by Haiku 5.5 via `skills/rate-quote/scripts/run_request.py`
- model: `claude-haiku-5-5`
- step1_prompt_version: `step1-v0.3`
- step1_model_used: `claude-haiku-5-5` (from `output/step1/extract-meta.json`)
- model_used_for_wording: no

## 2. Inputs

- request_id: REQ-001
- request_file: `fixtures/requests/REQ-001.txt`
- form_source: model, via `skills/rate-quote/scripts/run_request.py`
- step1_expected_form: `fixtures/forms/REQ-001.json`
- received_date: 2026-09-28
- rate_sheet_used: `rate_sheet_20260928`
- rate_sheet_date_matches_received_date: yes
- margin_supplied: 1.10 (RM)

## 3. Checks (expected vs actual)

Expected values come from the acceptance rule named in section 1.

| # | Check | Expected | Actual | Pass |
|---|---|---|---|---|
| 1 | Items found in email (count and type) | 1, drawdown | 1, drawdown | pass |
| 2 | Step 1 form fields correct on first pass | all fields | all fields; model form identical to `fixtures/forms/REQ-001.json` | pass |
| 3 | Grounding check result (step 3) | all form values found in the newest message | ok | pass |
| 4 | Route (quote, acknowledge, hand back) | quote | quote | pass |
| 5 | Sheet freshness check | sheet 2026-09-28 = received | sheet 2026-09-28 used | pass |
| 6 | Value date (after T+2 and holiday rules) | 2026-09-30 (= T+2) | 2026-09-30 | pass |
| 7 | End date (after holiday rules) | 2026-11-16 | 2026-11-16 | pass |
| 8 | Days / tenor | 30 business days; 47 calendar days in draft | 30 business days; "Tenor: 47 days" | pass |
| 9 | Sheet row used (regular tenor, Odd_Dates or forward rate) | Odd_Dates row containing 2026-11-16 | odd_dates.csv range 2026-11-14 to 2026-11-20 (45-51 days) | pass |
| 10 | Cost of funds (TP or forward rate, 4dp) | 4.2574 | 4.2574 | pass |
| 11 | Margin | 1.10 | 1.10 | pass |
| 12 | All-in rate, 4dp (audit line) | 5.3574 | 5.3574 | pass |
| 13 | All-in rate, 2dp, rounded half down (in draft) | 5.36% | 5.36% | pass |
| 14 | Draft does not name the sheet date; pre-send check does (rule v1.0) | no / yes | no in draft; yes in check | pass |
| 15 | Draft states purpose (drawdown or rollover) | drawdown | "Item 1 - Drawdown" | pass |
| 16 | Date-adjustment note to customer, if a date moved | n/a, no date moved | none | n/a |
| 17 | Draft check (step 11): numbers in draft equal script output | yes | pass, 2 dates and 4 numbers compared | pass |
| 18 | Model wording edit rejected by step 11 (n/a if no wording model) | no | n/a, no wording model | n/a |
| 19 | No send or external action attempted | none | none | pass |

Checks passed by script and the orchestrator agent: 17 / 17 applicable (checks 16 and 18 n/a). Step 1 call: 3.56 s. Output hashes (SHA-256): draft.txt `121dffd8…f6e167`, pre-send-check.txt `61f16007…aeb673`, result.json `22551a9a…ae0e`.

## 4. Human review

- bh_review_minutes: 5
- bh_changes: none ("items are correct"; "No for the calculation")
- rm_margin_change: none (synthetic)
- misread_found_by_bh_not_caught_by_code: none
- accepted: yes ("Yes accept as draft for this mvp", BH, 2026-10-14)
- note: BH first asked for the email to look like the drafts of earlier runs. the orchestrator agent showed the full draft: it uses the same template v0.3 as RUN-20261013-02 and -03 (only the item block had been shown in chat). BH then accepted it as drafted for the MVP. Any later change to the email layout is a template change: a new skill version and a new count.

## 5. Verdict

- verdict: pass
- counts_toward_six: yes. Count 2 (model route), run 1 of 6. Judged against acceptance-rule v1.0 (frozen), skill `3dc9a42`, model `claude-haiku-5-5`, prompt `step1-v0.3`.
- reason: all 17 applicable checks pass; the Haiku 5.5 form matched the expected form on the first pass; the owner accepted the draft as drafted, 5 minutes of review.

## 6. Corrections (append only, dated)

- 2026-10-14: count 2 (skill `3dc9a42`, template v0.3) closed at 1 of 6 when BH locked template v0.4 ("Lock"). This run stays a pass in count 2 and does not count toward count 3. Recorded by the orchestrator agent.
- 2026-10-14 (public copy only): agent and runtime names replaced with a general term ("the orchestrator agent"), BH decision 2026-10-14. The private source record is unchanged.
