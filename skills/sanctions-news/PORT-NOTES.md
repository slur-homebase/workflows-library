# Port notes

Copied on 2026-11-12 from source commit `6bbce51`. Files only, no history. Local branch only; publication remains blocked by the checks below.

- Layout: run from `skills/sanctions-news/`. The folder holds its own scripts, sample, demo, fixtures, tests and required historical evidence.
- Identical: `sample/`, `demo/`, `fixtures/` and all retained `evidence/` files are byte-identical to the pinned source. Seven of eight files in `scripts/` are byte-identical.
- Script path edit: `scripts/check_answer_key.py:15` changes `DEFAULT_FIXTURES` from repository-root `fixtures/sanctions-news/` to this skill's `fixtures/`. Both its command-line default and direct checker calls need this path. No research, checking or rendering rule changed.
- Tests: the nine source `tests/test_sanctions_news_*.py` files were copied into `tests/`. Only the path expressions listed below changed. Assertions, test methods and test data are unchanged.
- Skill instructions: `SKILL.md:122-129` now gives verification commands from this skill folder and selects the sanctions-news packaging tests explicitly. Other source text is unchanged.
- Root README: inserted the accepted section byte-for-byte after the rate-quote run log and before Data rules. This public baseline had no sanctions placeholder. All three relative links already resolve here, so none changed. Every pre-existing README byte is unchanged.
- Root data rules: added the exact source line containing the sanctions-news naming rule; existing rules are unchanged.
- Release checker: absent on public main, so all five source `skills/release-check/` files were copied unchanged. Its sanctions-news adapter works in this layout. Its older rate-quote integration suite still assumes private repository-root data.

## Test path edits

Line numbers refer to the public files; no lines were added or removed.

- `tests/test_sanctions_news_dashboard.py:16,17,311`: scripts, fixtures and phase-4 evidence.
- `tests/test_sanctions_news_fixtures.py:14`: fixtures.
- `tests/test_sanctions_news_model_reader.py:15,16,200`: scripts, phase-3 evidence and current article fixtures.
- `tests/test_sanctions_news_page.py:16,17`: fixtures and scripts.
- `tests/test_sanctions_news_round2_metadata.py:14,15,16`: fixtures, frozen evidence and scripts.
- `tests/test_sanctions_news_round3_dashboard.py:15,26,27,211,212`: frozen baseline, renderer, browser helper, research script and fixtures.
- `tests/test_sanctions_news_round3_links.py:13,14`: fixtures and scripts.
- `tests/test_sanctions_news_run.py:19,56`: skill root and fixtures.
- `tests/test_sanctions_news_skill.py:18,19`: fixtures and scripts.

## Retained and omitted evidence

- Retained 80 phase-3 files: frozen input fixtures, two recorded reader bundles, both sets of saved reports, scores, call ledger, run state and 32 recorded call outputs. Offline replay and cost-ledger tests read these files. No new model calls were made.
- Retained 19 phase-4 files: five round-3 JSON baselines, four browser helper modules required by imports, and ten stage-settlement JSON/Markdown reports required by the entry-command tests.
- Omitted 47 tracked source evidence files: the historical overview; phase-3 review, plan, prompt and verification files; round-3 screenshots, saved dashboard, duplicate reports, diff, logs and verification summaries; the stage-settlement log; and all timeline-navigation captures, scripts and logs. No copied test reads them. The tests exercise the current renderer and retained browser helpers directly.
- Not copied: private root planning/build notes, unrelated skill/showcase tests, receipts, backup files, generated caches or any untracked source files. No source `docs/` exists for this skill, so no placeholder docs folder was invented.

## Verification on the public layout

- `python3 -m unittest discover -s tests`: 236/236 pass, no skips.
- Count reconciliation: the private root discovers 367 tests: these 236, 113 rate-quote tests and 18 rate-quote showcase tests. The omitted 131 do not belong in this skill's nine test files. The existing public rate-quote suite separately passes 113/113; the showcase tests were not ported or run.
- Sample command: exit 0 in under 60 seconds; answer key 38/38; `diff -r` finds no differences across all 17 demo files. Output was placed in the session scratch folder rather than the requested system temporary path, to respect the build host's temporary-file boundary.
- Sanctions-news release checker: 4/4 package checks PASS, including exact 17-file replay.
- Sanctions-news packaging unittest suite: 13/13 pass.
- Full copied release-check suite: 34 run, 14 pass and 20 error. All 20 errors are in the rate-quote integration class setup at `skills/release-check/tests/test_release_check.py:69-70`, which expects repository-root `runs/runs.csv`. This public repository keeps it under `skills/rate-quote/runs/` and has no private release manifest. That separate gate was not changed to expand this port's scope.

## Publication blockers

The required whole-tree literal scan is not clean. Unchanged tests and guard code contain deny-list literals and model-command names. Retained source records also contain internal attribution, and an imported historical helper has a runtime-specific scratch constant. The accepted README includes a live demonstration URL, while the brief allows only a repository URL; tests and browser network-blocking declarations contain URL literals too.

No tests were weakened, evidence rewritten, names encoded, or accepted prose changed to hide these conflicts. Resolve the scan policy and any approved public-copy edits before publication. The passing package check covers the demo, not this whole source tree, and is not publication approval.

## Public-copy corrections, 2026-11-12 (round 2)

The sections above record round 1 at `8d2d717`. This section supersedes its blocked scan policy, byte-identity claims for the specific files below, and release-suite setup result. The owner approved these five fixes and the expected literals below. No private source files changed. This is a local correction, not publication approval.

Paths below are relative to `skills/sanctions-news/` unless they start with `skills/`.

- F1: `evidence/phase-4/round-3/support/dashboard/capture_browser.py:16` now uses `Path(tempfile.gettempdir())`. The historical helper follows the active temporary directory instead of one profile's home folder. No browser action changed. This code edit postdates the recorded runs; it does not refresh historical browser evidence.
- F2: `evidence/phase-3/fixtures-v1/answer-key.json:3`, `sources.json:3` and `subjects.json:3` use `Invented for an offline sample.`. Only the attribution changed; all remaining bytes and invented values are retained.
- F3: `fixtures/ANSWER-KEY-REVIEW.md:5,7` uses neutral owner-review wording and records the revision review as complete, as directed. The 12 accepted answers, date, sample limits, table and all strings asserted by tests remain intact.
- F4: `SKILL.md:135` now points to the case study in the library README, rather than an obsolete pending-writing step. The accepted README is unchanged.
- F5: `skills/release-check/tests/test_release_check.py:71-74` reads and stages `skills/rate-quote/runs/runs.csv` inside its isolated test repository. Lines 48-49 skip the integration setup when its private release manifest is absent. No test assertions or release rules changed. The missing manifest was confirmed after the ledger-path fix; no replacement manifest was invented or copied.

No other evidence, fixture, sample or demo file changed from round 1. All public-copy edits are enumerated above. The scratch-only temporary-directory regression failed before F1 with a distinct active temporary directory and passed after F1.

### Expected literals

These are permitted source/test/sample literals, not publication blockers:

- Deny-list words at `skills/release-check/scripts/sanctions_news.py:14-15`, in `scripts/check_answer_key.py` and in test files are intentional checker definitions or assertions. Keep them.
- Invented subject fields `registration_number`, `date_of_birth` and `nationality`, including `SYN-` sample values, remain in fixtures, sample and historical evidence. They are not real identity data.
- Model IDs beginning `claude-haiku-` or `claude-sonnet-` remain in `evidence/phase-3/`. `Claude Code` is already in the root README on public main.
- The root README live-demo link `https://poppy-maple-75y9.here.now/` is retained verbatim, accepted by the owner on 2026-11-05.
- The home-path rejection assertion at `tests/test_sanctions_news_run.py:104` remains unchanged under the explicit test-assertion exception. No actual home path is permitted.

### Round-2 verification

Fresh terminal checks with an explicit session temporary directory:

- Sanctions-news suite: `Ran 236 tests in 12.999s`, `OK`, no skips.
- Sample entry command: exit 0, answer key `38/38 rows passed`; `diff -r` against `demo/` emitted nothing, exit 0.
- Full release-check suite: `Ran 34 tests in 2.507s`, `OK (skipped=20)`. Fourteen passed; the twenty integration methods below did not run.
- Direct `sanctions_news.py` invocation: exit 0, no output. It defines the adapter but has no command-line entry point. The actual `release_check.py skills/sanctions-news` entry point also ran: four package checks PASS, 17 files compared, verdict PASS (offline package only; human sign-off not given).

### Named skips

All methods below belong to `test_release_check.ReleaseCheckTest` and share the reason `Private rate-quote release manifest is not included in the public layout`. Each depends on that manifest through `setUp`; these are not passed tests and do not establish a public rate-quote release gate.

- `test_broken_rounding_case_is_block`
- `test_default_check_preserves_manifest_on_hold`
- `test_default_run_does_not_call_model`
- `test_duplicate_run_id_counts_once_and_is_reported`
- `test_duplicates_do_not_crowd_out_distinct_run_ids`
- `test_invalid_run_ids_never_count_and_are_named`
- `test_manifest_records_all_fingerprint_parts`
- `test_matching_baseline_cannot_make_old_runs_current`
- `test_no_change_is_release`
- `test_normalized_distinct_valid_run_ids_still_count`
- `test_normalized_duplicate_run_ids_count_once_before_and_after_reset`
- `test_os_junk_does_not_change_fingerprint_or_run_version`
- `test_reset_excludes_normalized_prior_manifest_ids`
- `test_run_version_checks_uncommitted_parts`
- `test_run_version_checks_untracked_code`
- `test_run_version_separates_prompt_model_and_ordinary_code`
- `test_runs_on_old_commit_with_changed_code_are_hold`
- `test_template_edit_with_green_tests_is_hold_and_resets_count`
- `test_unchanged_version_with_too_few_runs_does_not_claim_reset`
- `test_unicode_digit_lookalikes_never_count_and_are_named`
