# Run RUN-20261014-06

## 1. Versions (fill in before the run)

- run_date: 2026-10-14
- operator: the orchestrator agent, at BH's instruction "Run 5" (count 3)
- skill_commit: `eadbd01` (skills/ tree, template v0.4; merged to main as `eaee7ab`). Fixed hash for count 3.
- acceptance_rule_version: `acceptance-rule-v1.0.md` (frozen 2026-10-13, commit `3c8753a`)
- fixture_commit: `9ea3601`
- route: A script-first, model route: step 1 by Haiku 5.5 via `skills/rate-quote/scripts/run_request.py`
- model: `claude-haiku-5-5`
- step1_prompt_version: `step1-v0.3`
- step1_model_used: `claude-haiku-5-5` (from `output/step1/extract-meta.json`)
- model_used_for_wording: no

## 2. Inputs

- request_id: REQ-006
- request_file: `fixtures/requests/REQ-006.txt`
- form_source: model, via `skills/rate-quote/scripts/run_request.py`
- step1_expected_form: `fixtures/forms/REQ-006.json`
- received_date: 2026-09-29
- rate_sheet_used: none (stopped at step 4 before the sheet was read)
- rate_sheet_date_matches_received_date: n/a
- margin_supplied: none needed (AUD, hand back)

## 3. Checks (expected vs actual)

Expected values come from the acceptance rule named in section 1 (rule 10: an AUD request is handed back with no rate anywhere in any output file).

| # | Check | Expected | Actual | Pass |
|---|---|---|---|---|
| 1 | Items found in email (count and type) | 1, drawdown (AUD) | 1, drawdown (AUD) | pass |
| 2 | Step 1 form fields correct on first pass | all fields | all fields; model form identical to `fixtures/forms/REQ-006.json` | pass |
| 3 | Grounding check result (step 3) | all form values found in the newest message | ok | pass |
| 4 | Route (quote, acknowledge, hand back) | hand back, Treasury/BBSW path | hand back at step 4: "item 1 is AUD: the rate sheet cannot answer AUD, so no rate is computed; hand back for the Treasury/BBSW path" | pass |
| 5 | Sheet freshness check | n/a, stops before the sheet | sheet not read | n/a |
| 6 | Value date (after T+2 and holiday rules) | n/a | not computed | n/a |
| 7 | End date (after holiday rules) | n/a | not computed | n/a |
| 8 | Days / tenor | n/a | not computed | n/a |
| 9 | Sheet row used (regular tenor, Odd_Dates or forward rate) | none | none | n/a |
| 10 | Cost of funds (TP or forward rate, 4dp) | none in any output file | none (scan of every output file: no rate, TP, forward rate or margin value) | pass |
| 11 | Margin | none in any output file | none | pass |
| 12 | All-in rate, 4dp (audit line) | none in any output file | none | pass |
| 13 | All-in rate, 2dp, rounded half down (in draft) | none; no customer draft | none; output is a one-line hand-back note | pass |
| 14 | Draft does not name the sheet date; pre-send check does (rule v1.0) | n/a, no customer draft | n/a | n/a |
| 15 | Draft states purpose (drawdown or rollover) | n/a, no customer draft | n/a | n/a |
| 16 | Date-adjustment note to customer, if a date moved | n/a | n/a | n/a |
| 17 | Draft check (step 11): numbers in draft equal script output | n/a, no quote draft | not run (no quote draft) | n/a |
| 18 | Model wording edit rejected by step 11 (n/a if no wording model) | no | n/a, no wording model | n/a |
| 19 | No send or external action attempted | none | none (`send_attempted: false`) | pass |

Checks passed by script and the orchestrator agent: 9 / 9 applicable. Exit code 2 (hand back), as designed. Step 1 call: 3.53 s. Output hashes (SHA-256, first 12): draft.txt `f46065e8e9b9`, pre-send-check.txt `63c160fefc1c`, result.json `d663abf3a065`.

## 4. Human review

- bh_review_minutes: 5
- bh_changes: none
- rm_margin_change: none (synthetic)
- misread_found_by_bh_not_caught_by_code: none
- accepted: yes (BH, 2026-10-14)

## 5. Verdict

- verdict: pass
- counts_toward_six: yes. Count 3 (model route, template v0.4), run 5 of 6. Judged against acceptance-rule v1.0 (frozen), skill `eadbd01`, model `claude-haiku-5-5`, prompt `step1-v0.3`.
- reason: all 9 applicable checks pass; AUD handed back for the Treasury/BBSW path with no rate in any output file; the owner accepted the hand-back, 5 minutes of review.

## 6. Corrections (append only, dated)

- 2026-10-14 (public copy only): agent and runtime names replaced with a general term ("the orchestrator agent"), BH decision 2026-10-14. The private source record is unchanged.
