---
name: release-check
description: Offline change-control gate for rate-quote. Fingerprints the parts under test, runs deterministic tests and frozen expected-answer cases, compares them with the last released manifest, applies the six-supervised-run reset rule, and writes a human-signable RELEASE, HOLD or BLOCK report. Python 3 standard library only; no model call unless explicitly requested.
---

# release-check v0.1

## What it does

`release-check` treats a skill change as a control change. It compares `rate-quote` with its last released manifest, runs its offline unittest suite and the seven cases frozen in acceptance rule v1.1, and writes one plain-language verdict:

- `RELEASE`: offline cases pass, no baseline regression exists, and the supervised-run gate is satisfied.
- `BLOCK`: a case that passed in the baseline now fails, or any current offline case fails.
- `HOLD`: offline cases pass, but code, prompt, template or model changed and fewer than six new supervised runs are logged. With no new qualifying run, the report says `supervised run count resets to 0 of 6`.

The checker fingerprints code, prompt, template, pinned model id, fixtures and the frozen acceptance rule. It lists changed parts and records pass or fail for every unittest and expected-answer case. It never fixes code, tags, pushes, publishes or signs a release.

## Who runs each step

| Step | Who | Action |
|---|---|---|
| 1 | Skill maintainer | Make the proposed change and run the checker from the repository root. |
| 2 | Code | Hash the parts under test and compare them with `skills/rate-quote/release/manifest.json`. |
| 3 | Code | Run the offline unittest suite and frozen expected-answer replay. |
| 4 | Code, optional | Run the step-1 extraction eval only when the maintainer supplies `--with-model`. This can call the pinned model. |
| 5 | Code | Apply regression and supervised-run rules, then write `skills/rate-quote/release/report-YYYY-MM-DD.md`. |
| 6 | Human reviewer | Read the report and source evidence, then sign or reject the release. The script cannot approve on the reviewer's behalf. |
| 7 | Skill maintainer | After a human-approved release, use `--record-release` to replace the manifest with that released state. |

## Run it

From the repository root:

```text
python3 skills/release-check/scripts/release_check.py skills/rate-quote
```

To create or update a released baseline after human approval:

```text
python3 skills/release-check/scripts/release_check.py skills/rate-quote --record-release
```

`--record-release` refuses to record `HOLD` or `BLOCK`. On first use, with no earlier manifest, a fully passing state can be recorded as the initial baseline. Add `--with-model` only when a model call is intended; it is off by default.

Exit codes are 0 for `RELEASE`, 2 for `HOLD`, and 1 for `BLOCK` or an execution error.

## Inputs and outputs

Inputs are local repository files only: `skills/rate-quote/`, `fixtures/`, acceptance rule v1.1, expected answers v0.2, `tests/`, and the synthetic supervised-run ledger. Default execution makes no network call.

The only persistent outputs are under `skills/rate-quote/release/`:

- `manifest.json`: the last state explicitly recorded as released, including fingerprints and case results.
- `report-YYYY-MM-DD.md`: the current comparison and unsigned human decision block.

All test and replay working folders are temporary and removed after the run.

## Limits

- The release gate supports `rate-quote`. The separate `sanctions-news` adapter checks offline packaging only, as described below. Other skills need their own declared test and replay adapter.
- It checks deterministic behavior and change-control evidence; it does not score wording quality.
- A `RELEASE` verdict is evidence for a person, not authorization to publish.
- The supervised-run count comes from synthetic entries marked `pass` and `yes` in `runs/runs.csv`. A run counts only when code, prompt, template, pinned model id and acceptance rule are identical at its `skill_commit` and in the current files under test, including uncommitted and untracked files; fixtures are excluded. The checker compares local Git file hashes with the current fingerprint. If Git or the commit is unavailable, the run does not count. A reset counts only qualifying run ids not present in the prior manifest.
- Within the latest eligible skill commit, each distinct run ID counts at most once. The checker removes duplicate IDs before selecting up to six runs, keeping first-seen order. The report names duplicate IDs in that eligible group, including IDs outside the selected six. Duplicates add no count and do not invalidate otherwise qualifying runs.
- The optional model eval can vary and requires the local model command and access. It is never run implicitly.
- All fixtures and outputs must follow `DATA-RULES.md`: synthetic only, no organization, department or customer data, and human approval for anything leaving the workflow.

## Sanctions-news offline package

Run `python3 skills/release-check/scripts/release_check.py skills/sanctions-news` from the repository root.
This adapter checks every demo file for external URLs, banned terms, local links and size under 2 MB.
It runs the bundled sample through `run.py` with a 60-second limit and compares every output byte with `demo/`.
The entry command also checks the optional bundled answer key. The expected demo file set must match the subjects.
Exit 0 and `PASS` mean the package checks passed, not a signed release or permission to publish.
Failure returns 1 and `BLOCKED`. No persistent report or manifest is written by this adapter.
It rejects `--with-model` and `--record-release`; it has no model or supervised-run path.
Run both unittest suites separately for full verification. Rate-quote behavior and its gate are unchanged.
