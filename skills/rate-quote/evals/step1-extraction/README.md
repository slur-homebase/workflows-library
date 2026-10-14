# Step 1 test runs: Haiku 5.5 reads the request into the form

Status: development evidence, 2026-10-13, branch `step1-haiku-extraction`. These runs do not count toward the six supervised runs. BH did not review a draft in any of them, and `runs/` was not touched.

## What was built

- `skills/rate-quote/scripts/extract_form.py`: step 1 of route A. Haiku 5.5 (`claude-haiku-5-5`, pinned by full id) reads the request text into the fixed form. Code then checks the shape and hands back at step 1 if the model flags a value as unclear, if a field has the wrong shape, if the call fails, or if any model other than the pinned one answered.
- Model choice: BH, 2026-10-13. Haiku 5.5 is for routing, classification and extraction steps. Step 1 is extraction.
- The model sees the email only. The fixture's `Case:` line is removed first, because it names the expected answer. The model never sees the rate sheet, calendars, margin or any computed value, has no tools, and does no arithmetic.
- The call goes through `claude -p` on BH's existing Claude login. No new paid service.
- `tests/test_extract_form.py`: 8 offline tests of the code around the model (no model call).
- `run_eval.py`: the harness for the runs below.

## Requests tested

- The five fixtures (REQ-001, 003, 004, 006, 007). Expected answer: the hand-written form in `fixtures/forms/`.
- Four harder synthetic cases in `cases/requests/`, expected answers in `cases/expected/`:
  - X-101: shorthand ("7.5mio", "60 BD", "2 Oct" with no year).
  - X-102: tenor "one month". The model must not convert it. Expected: hand back at step 1.
  - X-103: numeric date 01/10/2026 (day/month), "2.25 million", end date "20 Nov" with no year.
  - X-104: reply thread. The latest message corrects the amount in the quoted request (4,000,000 to 4,500,000).

## Results

A run is correct when every form field equals the expected form (or, for X-102, when step 1 hands back).

- Haiku 5.5, prompt v0.2, 3 runs per request: 26 of 27 correct. Median 4.5 s per call.
- Haiku 5.5, prompt v0.3, 3 runs per request: 27 of 27 correct. Median 4.0 s, max 5.3 s. About 2,100 input and 320 output tokens per call.
- Sonnet 5, prompt v0.3, 1 run per request (comparison): 9 of 9 correct. Median 7.4 s, max 9.4 s. About twice the input tokens.
- End to end on the five fixtures: in all 15 Haiku v0.3 runs, `quote.py` on the model's form gave the same outcome, the same rates and a byte-identical draft as on the hand-written form. REQ-006 (AUD) still hands back at step 4 with no rate.
- The four X cases have no margin row, so `quote.py` stops at step 8 by design. Steps 2 to 5 passed on every model form, so the grounding check accepted them.

## Failures found and prompt changes

- Prompt v0.1, REQ-003, 1 trial run: Haiku copied every value correctly but listed the "on maturity" date under `unclear`, so a clean request was handed back. Fix in v0.2: values filled by the copy rules are not unclear.
- Prompt v0.2, X-101, run 2 of 3: Haiku compared the value date with today's date and handed back. Date checks are code's job (step 6). Fix in v0.3: the model must not judge dates.
- Both failures were hand-backs, not wrong forms. No run produced a wrong number or date.

## Open items for BH (first batch)

1. Grounding gap shown by X-104. Closed in the second batch below (BH, 2026-10-13).
2. The prompt was tuned on these nine requests. Closed in the second batch: five unseen requests.
3. Four extra cases is a small sample. This shows the step works on clean and lightly messy synthetic emails. It does not show accuracy on real customer emails, and no real email may be used here.
4. Merged to `main` with BH's approval, commit `acf3cf8`.

## Second batch, 2026-10-13: thread rule and five unseen requests

BH approved two changes on 2026-10-13, branch `step3-thread-grounding`.

Thread rule in step 3 (`quote.py`, code, not the model):

- The grounding check reads the newest message only. Header lines (Request-ID, Case, Received, From) and quoted earlier messages are left out. The Subject line stays in, because the sender wrote it.
- If the email quotes an earlier message and the newest message corrects or changes it ("correction", "amend", "revised", "instead", "please ignore" and similar words), the request goes back to BH at step 3. No rate is computed.
- Tests: `tests/test_thread_grounding.py`, 7 tests. One of them checks the exact failure from X-104: a form with the old amount 4,000,000 is now stopped.

Five unseen requests, written after prompt v0.3 was fixed and run with no prompt change:

- U-201: two drawdowns in one email, one with a tenor and one with an end date.
- U-202: form-style layout (Ccy / Amount on separate lines), date 02-10-2026, amount 10,000,000.00.
- U-203: no facility reference anywhere. Expected: hand back.
- U-204: date written "October 1, 2026", plus noise numbers (a phone number, "ref 2026/117", "3 quotes last week").
- U-205: repayment only.

Results, Haiku 5.5, prompt v0.3, 3 runs per request, all 14 requests (`results/2026-10-13-haiku-5-5-prompt-v0.3-thread-rule/`):

- Step 1 correct: 42 of 42. Unseen requests: 15 of 15. Median 4.1 s per call.
- U-203: Haiku did not invent a facility reference. It handed back 3 of 3.
- The five fixtures: the quote draft was byte-identical to the hand-form draft in 15 of 15 runs. The thread rule did not change any fixture result.
- X-104: now stops at step 3 in 3 of 3 runs ("the newest message ... corrects or changes an earlier message").
- U-205: acknowledged, no rate, 3 of 3.

New finding (code, not the model):

- U-202: Haiku read the form-style email correctly in 3 of 3 runs, but step 3 handed it back each time: "form has 1 items but the newest message names only 0 currency amounts". The item-count check only counts a currency code written right next to an amount ("USD 10,000,000"). In this layout the code and the amount are on separate lines. This is a safe failure (a hand-back, not a wrong quote) and it existed before today's change. Loosening the check is BH's decision.

## How to repeat

```
python3 evals/step1-extraction/run_eval.py --model claude-haiku-5-5 --repeats 3 \
    --out evals/step1-extraction/results/<date>-haiku-5-5
```

Each run folder holds `step1/form.json`, `step1/extract-meta.json` (model used, prompt version, time, tokens, raw output) and the `quote.py` outputs. `results.json` in each results folder holds one row per run.

## Third change, 2026-10-13: item-count check loosened (BH)

- `quote.py` step 3 now counts a labelled amount line ("Amount: 10,000,000.00") as a currency amount when the same newest message has a labelled currency line ("Ccy: USD"). Amount lines in quoted messages never count.
- Tests: `tests/test_labelled_layout.py`, 5 tests, including a form with two items against an email with one amount line (still handed back) and an amount line with no currency line (still handed back).
- U-202, Haiku 5.5, 3 runs (`results/2026-10-13-haiku-5-5-U-202-loosened-check/`): step 1 correct 3 of 3, and step 3 now passes. The run stops at step 8 because U-202 has no margin row, by design.
