# workflows-library

## What this is

This repository holds AI-assisted workflow skills built on synthetic data. Its first skill, rate-quote, comes with test data, offline tests, a log of every supervised run and the answers it should give, so a reader can run it and check each answer.

It was tested the way a control owner would test it: answer key first, 1 fixed version under test, a person reviewing every result, failures recorded.

## The first skill: rate-quote

rate-quote turns a customer's emailed request for a loan drawdown or rollover into a draft rate quote email. A drawdown is new borrowing under an agreed facility; a rollover renews an existing loan for a new period.

A small AI model, Haiku 5.5, reads the email into a fixed form, the same set of fields every time. Code does every check and every number: dates, holidays, the rate sheet row, the margin, rounding and the draft. A person keeps the credit check, the margin and the decision to send. The skill has no way to send anything.

The 13 steps, numbered 0 to 12, are listed in skills/rate-quote/docs/route.md: 2 human steps, 1 model step that reads the email, 1 optional model wording step that is not built, and 9 code steps.

## How it was proven

Before any counted run, I froze a written answer key, the acceptance rule: a check list of what a correct quote looks like. A run counts only if it passes that key and I accept the draft without changing a number, date or outcome. A change to the template, model, prompt or code under test starts a new count of 6.

Before the counted runs, the reading step was tested on 14 made-up emails, 3 times each. It read 42 of 42 correctly, including 15 of 15 on 5 emails it had never seen. The code is covered by 113 offline tests.

10 supervised runs are logged. The first failed: the numbers were right, but I rejected the email layout. The count restarted twice, when the AI reading step was added and when the email layout changed, so the final 6 runs tested 1 fixed version. All 6 passed, including 1 correct hand-back of a request in AUD, outside the rate sheet. I accepted each of their drafts as written, in about 5 minutes of review each. Nothing was sent.

## What went wrong and what caught it

First, the model twice handed back emails it had read correctly, once by judging a date, which is code's job. Both came back to me and neither reached a draft. A prompt change fixed them.

Second, a check compared the form with the whole email, so in a reply thread an old amount in the quoted message would have passed. The check now reads only the newest message, and a thread that corrects an earlier message goes back to a person.

Third, while designing an extra test, I found an error in the acceptance rule. A start date earlier than the standard 2 business days should keep its date and be priced from the forward rate (the rate for a start date other than the standard one), not be moved. No run had used that part of the acceptance rule. I corrected it in acceptance rule v1.1, and 2 edge cases matched answers frozen before they were run.

## Limits

The 6 counted runs ran on an earlier version of the code. Since then, the early start date path has changed to follow acceptance rule v1.1, proven by the 2 edge cases rather than a counted run, and the folder the model call runs in has changed, but the current code still reproduces every expected answer.

This is a synthetic workflow rebuilt at home from memory, with made-up customers, facilities and rates. Nothing is deployed anywhere. Real use would need an approved model and data route.

The review time of about 5 minutes per draft is an estimate, not a measured time, and no time saving is claimed.

## How a skill is laid out

The rate-quote folder is laid out as follows.

```
skills/rate-quote/
  SKILL.md       what the skill does and who runs each step
  scripts/       extract_form.py (step 1, model), quote.py (steps 2 to 11, code), run_request.py (both)
  references/    the quote email template
  fixtures/      synthetic emails, forms, rate sheets, holiday calendars and margins
  tests/         113 offline tests
  runs/          one record per supervised run, and runs.csv
  docs/          the route, the frozen acceptance rules and the owner correction
  evals/         tests of the reading step and two edge cases
```

## How to run

Step 1 needs the Claude Code command line tool, signed in with access to Haiku 5.5. Steps 2 to 11 need only Python 3 and its standard library, with no network.

The first command runs the tests, the second runs the code steps on a hand-written form with no model, and the third runs the full route, including the model.

```
cd skills/rate-quote
python3 -m unittest discover -s tests

python3 scripts/quote.py --form fixtures/forms/REQ-001.json --received 2026-09-28 \
  --sheet-dir fixtures/rate_sheets --calendars fixtures/calendars \
  --margins fixtures/margins.csv --out /tmp/req001

python3 scripts/run_request.py --request fixtures/requests/REQ-001.txt --received 2026-09-28 \
  --sheet-dir fixtures/rate_sheets --calendars fixtures/calendars \
  --margins fixtures/margins.csv --out /tmp/req001-model
```

Each run writes a quote draft and a pre-send check for the reviewer into the --out folder.

## Expected answers

Results the current code should return. Use the Received date as --received. All 7 matched on 14 October 2026.

| Request | Received | Expected result |
|---|---|---|
| REQ-001 | 2026-09-28 | 5.36%, end date 16 Nov 2026 |
| REQ-003 | 2026-09-29 | repayment acknowledged; rollover 5.56%, end date 18 Feb 2027 |
| REQ-004 | 2026-09-29 | 5.39%, end date moved from 11 Nov to 12 Nov 2026 (US holiday), customer told |
| REQ-006 | 2026-09-29 | handed back: AUD is outside the rate sheet (exit code 2) |
| REQ-007 | 2026-09-29 | 5.30%, end date 20 Nov 2026 |
| REQ-008 | 2026-09-29 | 5.43%, end date 2 Nov 2026 |
| REQ-009 | 2026-09-29 | 6.15%, end date 16 Nov 2026 (start date earlier than the standard two days, forward rate) |

## Run log

skills/rate-quote/runs/runs.csv lists every supervised run, and a run not in the log did not happen. Each run has its own record under runs/.

| Run | Request | Count | Outcome | Checks | Verdict |
|---|---|---|---|---|---|
| RUN-20261013-01 | REQ-001 | before count 1 | quote draft | 18/18 | fail: owner rejected the email layout |
| RUN-20261013-02 | REQ-003 | count 1 | quote draft | 18/18 | pass |
| RUN-20261013-03 | REQ-004 | count 1 | quote draft | 18/18 | pass |
| RUN-20261014-01 | REQ-001 | count 2 | quote draft | 17/17 | pass |
| RUN-20261014-02 | REQ-001 | count 3, run 1 | quote draft | 17/17 | pass |
| RUN-20261014-03 | REQ-003 | count 3, run 2 | quote draft | 17/17 | pass |
| RUN-20261014-04 | REQ-004 | count 3, run 3 | quote draft | 18/18 | pass |
| RUN-20261014-05 | REQ-007 | count 3, run 4 | quote draft | 17/17 | pass |
| RUN-20261014-06 | REQ-006 | count 3, run 5 | hand back | 9/9 | pass |
| RUN-20261014-07 | REQ-003 | count 3, run 6 | quote draft | 17/17 | pass |

## Data rules

All data here is made up. See DATA-RULES.md for the data rules.

## Licence

MIT. See LICENSE.
