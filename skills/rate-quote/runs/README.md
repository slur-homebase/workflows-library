# Run log — rate quoting skill

Purpose: keep one record per skill run, so anyone can check that the output was correct.
Each record holds what went in, what came out, the expected answer, and the human review.

Status: v0.1, 2026-10-06. Format only. No skill exists yet, so no run is logged.

## Rules

1. Log every run, including failed and rejected runs. A run that is not logged did not happen.
2. Never edit a closed run record. If a check was wrong, add a correction line at the bottom with the date.
3. Use synthetic fixtures only. Real emails, sheets, margins and customer data never enter this folder.
4. Put any file that must not be committed under `runs/<run_id>/raw/`. Git ignores that folder.
5. A run counts toward the six supervised runs only if `counts_toward_six` is `yes` in `runs.csv`.

## Folder layout

```
runs/
  README.md          this file
  runs.csv           index: one line per run
  _template/         copy this folder to start a run
  RUN-YYYYMMDD-NN/   one folder per run
    run.md           run record: inputs, versions, checks, review
    output/
      form.json      what the skill read from the email (step 1)
      draft.txt      the draft email the skill produced
      trace.txt      step-by-step output from the script (optional)
```

## How to log a run

1. Copy `_template/` to `RUN-YYYYMMDD-NN/` (NN = 01, 02 … for that day).
2. Before the run, fill in section 1 (versions) and section 2 (inputs) of `run.md`.
3. Run the skill. Save its output files in `output/` unchanged.
4. Fill in section 3 (checks): expected value, actual value, pass or fail for each line.
5. Fill in section 4 (human review) after BH reviews the draft.
6. Add one line to `runs.csv`. Commit the run folder and the CSV line together.

## Where the expected answers come from

- `docs/expected-answers-v0.2.md` until the acceptance rule is frozen.
- After the freeze, the frozen acceptance rule. Record its version in every run.

## Verdict values

- `pass`: every check passes, BH changed only wording, and the RM changed nothing except, sometimes, the margin (acceptance rule draft).
- `fail`: any check fails, or BH changed a number, date or outcome.
- `invalid`: the run cannot be judged (wrong fixture, wrong sheet, crash before output). Does not count.

## Counts of six

- Count 1: hand-written step-1 forms, skill `929d1d8`, acceptance rule v1.0. Closed at 2 of 6 (RUN-20261013-02, RUN-20261013-03) by owner decision 2026-10-13. These runs stay as proof of the rate maths. Their `counts_toward_six = yes` in `runs.csv` refers to count 1 only.
- Count 2: model route, step 1 by Haiku 5.5 (`claude-haiku-5-5`, prompt `step1-v0.3`), run with `skills/rate-quote/scripts/run_request.py`. Skill `3dc9a42` (merged to main as `069eb19`), acceptance rule v1.0, fixtures `9ea3601`. Started 2026-10-14. Closed at 1 of 6 (RUN-20261014-01) when BH locked template v0.4 on 2026-10-14.
- Count 3: model route as count 2, template v0.4 (option A: items headed "USD drawdown", no "Item N"). Skill `eadbd01` (merged to main as `eaee7ab`), Haiku 5.5 `claude-haiku-5-5`, prompt `step1-v0.3`, acceptance rule v1.0, fixtures `9ea3601`. Started 2026-10-14. A run counts toward count 3 only with this skill hash, model and prompt version. Any change to them starts a new count.
  - COMPLETE 2026-10-14: 6 of 6 passes (RUN-20261014-02 to -07: REQ-001, 003, 004, 007, 006, 003 repeat). Step 1 form correct on first pass 6 of 6. Every run accepted as drafted, no changes, 5 minutes of review each. No send attempted.

## Parked template changes (apply together after count 3)

- 2026-10-14, BH (RUN-20261014-03): label the customer tenor as calendar days, e.g. "Tenor: 139 calendar days". The number is already calendar days from the value date to the end date; only the label changes.
  - CLOSED 2026-10-14 by BH: "Don't need to label tenor as calendar days in the email draft template." Template v0.4 stays as is. No parked template changes remain.
