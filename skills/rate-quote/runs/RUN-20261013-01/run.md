# Run RUN-20261013-01

## 1. Versions (fill in before the run)

- run_date: 2026-10-13
- operator: the orchestrator agent, at BH's instruction "Proceed with week 4"
- skill_commit: `1dccdc0` (main `c7d4af1`); NOT a frozen hash: the acceptance rule is not yet frozen (KR2 freeze 13 Nov)
- acceptance_rule_version: `expected-answers-v0.2` (draft, not frozen)
- fixture_commit: `9ea3601`
- route: A script-first (step 1 form hand-written stand-in, `fixtures/forms/REQ-001.json`; no model call)
- model: none
- model_used_for_wording: no

## 2. Inputs

- request_id: REQ-001
- request_file: `fixtures/requests/REQ-001.txt`
- received_date: 2026-09-28
- rate_sheet_used: `rate_sheet_20260928`
- rate_sheet_date_matches_received_date: yes
- margin_supplied: 1.10 (RM)

## 3. Checks (expected vs actual)

Expected values come from the acceptance rule named in section 1.

| # | Check | Expected | Actual | Pass |
|---|---|---|---|---|
| 1 | Items found in email (count and type) | 1, drawdown | 1, drawdown | pass |
| 2 | Step 1 form fields correct on first pass | all fields | all fields (hand-written form; no model) | pass (n/a model) |
| 3 | Grounding check result (step 3) | all form values found in email | amount, value date, tenor, currency all found | pass |
| 4 | Route (quote, acknowledge, hand back) | quote | quote | pass |
| 5 | Sheet freshness check | sheet 2026-09-28 = received | sheet 2026-09-28 used | pass |
| 6 | Value date (after T+2 and holiday rules) | 2026-09-30 | 2026-09-30 (no adjustment) | pass |
| 7 | End date (after holiday rules) | 2026-11-16 | 2026-11-16 | pass |
| 8 | Days / tenor | 30 business days; 47 calendar days | 30; 47 | pass |
| 9 | Sheet row used (regular tenor, Odd_Dates or forward rate) | Odd_Dates 2026-11-14 to 2026-11-20 | odd_dates.csv range 2026-11-14 to 2026-11-20 (45-51 days) | pass |
| 10 | Cost of funds (TP or forward rate, 4dp) | 4.2574 | 4.2574 | pass |
| 11 | Margin | 1.10 | 1.10 | pass |
| 12 | All-in rate, 4dp (audit line) | 5.3574 | 5.3574 | pass |
| 13 | All-in rate, 2dp, rounded half down (in draft) | 5.36% | 5.36% | pass |
| 14 | Draft names the sheet date | yes | yes, "rate sheet dated 2026-09-28" | pass |
| 15 | Draft states purpose (drawdown or rollover) | drawdown | "Item 1 - Drawdown" | pass |
| 16 | Date-adjustment note to customer, if a date moved | none needed | none | pass |
| 17 | Draft check (step 11): numbers in draft equal script output | yes | pass, 3 dates and 4 numbers compared | pass |
| 18 | Model wording edit rejected by step 11 (n/a if no wording model) | no | n/a, no wording model | n/a |
| 19 | No send or external action attempted | none | none (script has no send capability; nothing outside fixtures read) | pass |

Checks passed by script and the orchestrator agent: 18 / 18 applicable (check 18 n/a). Output hashes (SHA-256): draft.txt `dd8e0069…7929`, pre-send-check.txt `c82c680f…7357`, result.json `ecd4ac74…e521`.

## 4. Human review

- bh_review_minutes: not stated (read on Discord, same evening)
- bh_changes: three template changes before sending: (1) tenor to be shown in calendar days, 47, not "30 business days"; (2) remove the sentence saying the margin was supplied by the relationship manager, the reviewer confirms the margin before send; (3) remove the basis line naming the sheet date. Rate 5.36%, value date, end date unchanged.
- rm_margin_change: none
- misread_found_by_bh_not_caught_by_code: none in the numbers; the template said things a customer email should not say (margin source, sheet basis) and showed the tenor on the wrong basis
- accepted: no, as drafted

## 5. Verdict

- verdict: fail
- counts_toward_six: no. Two reasons: the owner changed the draft (fail by the verdict rule), and the acceptance rule was not frozen at run time.
- reason: every computed value matched the expected answer; the owner rejected the draft wording and tenor basis. Template corrected in commit `929d1d8` (v0.3) with tests; run 2 is the next supervised run on the corrected skill.

## 6. Corrections (append only, dated)

- 2026-10-13: owner review applied to the template (commit `929d1d8`). This run's output files are unchanged and still show the v0.2 template.
- 2026-10-14 (public copy only): agent and runtime names replaced with a general term ("the orchestrator agent"), BH decision 2026-10-14. The private source record is unchanged.
- 2026-10-14 (public copy only): a local home-folder path removed from output/result.json, BH decision 2026-10-14. Values are otherwise unchanged.
