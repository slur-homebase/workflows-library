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
