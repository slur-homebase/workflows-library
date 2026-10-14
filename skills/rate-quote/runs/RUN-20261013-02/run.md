# Run RUN-20261013-02

## 1. Versions (fill in before the run)

- run_date: 2026-10-13
- operator: the orchestrator agent, at BH's instruction "Run 2"
- skill_commit: `929d1d8` (template v0.3; main `8b8f3ba`); acceptance rule not yet frozen
- acceptance_rule_version: `acceptance-rule-v1.0.md` (frozen 2026-10-13, same session as this run; it carries expected-answers v0.2 plus the check-14 amendment, and nothing in it differs from what this run was judged against)
- fixture_commit: `9ea3601`
- route: A script-first (step 1 form hand-written stand-in, `fixtures/forms/REQ-003.json`; no model call)
- model: none
- model_used_for_wording: no

## 2. Inputs

- request_id: REQ-003
- request_file: `fixtures/requests/REQ-003.txt`
- received_date: 2026-09-29
- rate_sheet_used: `rate_sheet_20260929`
- rate_sheet_date_matches_received_date: yes
- margin_supplied: 1.25 (RM), item 2 only

## 3. Checks (expected vs actual)

Expected values come from the acceptance rule named in section 1.

| # | Check | Expected | Actual | Pass |
|---|---|---|---|---|
| 1 | Items found in email (count and type) | 2: repayment, rollover | 2: repayment, rollover | pass |
| 2 | Step 1 form fields correct on first pass | all fields | all fields (hand-written form; no model) | pass (n/a model) |
| 3 | Grounding check result (step 3) | all form values found in email | ok | pass |
| 4 | Route (quote, acknowledge, hand back) | item 1 acknowledge; item 2 quote | item 1 acknowledge; item 2 quote | pass |
| 5 | Sheet freshness check | sheet 2026-09-29 = received | sheet 2026-09-29 used | pass |
| 6 | Value date (after T+2 and holiday rules) | 2026-10-02 (later than T+2 2026-10-01, forward path) | 2026-10-02, forward path flagged | pass |
| 7 | End date (after holiday rules) | 2027-02-18 | 2027-02-18 | pass |
| 8 | Days / tenor | 90 business days; customer tenor 139 calendar days; num_days 140 (sheet basis) | 90; 139; 140 | pass |
| 9 | Sheet row used (regular tenor, Odd_Dates or forward rate) | forward rate calculator, USD 2026-10-02 to 2027-02-18 | forward_rate_calculator.csv row 2 | pass |
| 10 | Cost of funds (TP or forward rate, 4dp) | 4.3150 (forward) | 4.3150 | pass |
| 11 | Margin | 1.25 | 1.25 | pass |
| 12 | All-in rate, 4dp (audit line) | 5.5650 | 5.5650 | pass |
| 13 | All-in rate, 2dp, rounded half down (in draft) | 5.56% | 5.56% | pass |
| 14 | Draft names the sheet date | no (owner decision 2026-10-13; sheet date in pre-send check) | no in draft; yes in check | pass |
| 15 | Draft states purpose (drawdown or rollover) | rollover | "Item 2 - Rollover" | pass |
| 16 | Date-adjustment note to customer, if a date moved | none needed | none | pass |
| 17 | Draft check (step 11): numbers in draft equal script output | yes | pass, 3 dates and 6 numbers compared | pass |
| 18 | Model wording edit rejected by step 11 (n/a if no wording model) | no | n/a, no wording model | n/a |
| 19 | No send or external action attempted | none | none | pass |

Checks passed by script and the orchestrator agent: 18 / 18 applicable (check 18 n/a). Output hashes (SHA-256): draft.txt `5db2db2a…f15c`, pre-send-check.txt `8d3b11d5…30a6`, result.json `3d4b7150…40f7`. 

## 4. Human review

- bh_review_minutes: under 5
- bh_changes: none
- rm_margin_change: none
- misread_found_by_bh_not_caught_by_code: none
- accepted: yes

## 5. Verdict

- verdict: pass
- counts_toward_six: yes. Judged against acceptance-rule v1.0, frozen by the owner in the same session; skill commit `929d1d8` is a fixed hash. Run 1 of 6.
- reason: all 18 applicable checks pass; the owner accepted the draft as drafted with no changes, under 5 minutes of review.

## 6. Corrections (append only, dated)

- 2026-10-14: count 1 (hand-written forms, skill `929d1d8`) closed at 2 of 6 by owner decision 2026-10-13 (option 1). This run stays a pass in count 1 and does not count toward count 2 (model route, skill `3dc9a42`). Recorded by the orchestrator agent.
- 2026-10-14 (public copy only): agent and runtime names replaced with a general term ("the orchestrator agent"), BH decision 2026-10-14. The private source record is unchanged.
- 2026-10-14 (public copy only): a local home-folder path removed from output/result.json, BH decision 2026-10-14. Values are otherwise unchanged.
