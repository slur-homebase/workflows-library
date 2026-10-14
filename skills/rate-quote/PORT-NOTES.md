# Port notes

Copied on 2026-10-14 from the private build repository at commit `fd7b57d` (BH: "SOUL yes, 1", 2026-10-14). Files only, no history.

- `references/` is byte-identical to the source. `scripts/` is identical except one docstring line in each of two files (see below).
- The six counted runs (`runs/RUN-20261014-02` to `-07`) ran on skill commit `eadbd01` in the source repository. The current `scripts/quote.py` adds the acceptance rule v1.1 path for a value date earlier than T+2, proven by edge cases REQ-008 and REQ-009 (`evals/edge-cases/2026-10-14/`), not by a counted run.
- Layout: the skill folder holds its own `fixtures/`, `tests/`, `runs/`, `docs/` and `evals/`. Run every command from `skills/rate-quote/`. Test path constants and the `SKILL.md` run commands were changed for this layout; nothing else.
- Not copied: planning notes, the manual timing log, build notes and eval result folders. Synthetic test workbooks (.xlsx) were not copied; the scripts read the CSV sheets.
- Tests: 113 of 113 pass from this folder (`python3 -m unittest discover -s tests`).

## Public-copy edits (BH decisions 2026-10-14)

- Agent and runtime names replaced with "the orchestrator agent" in run records and docs (BH: "change to a general term").
- A local home-folder path removed from `output/result.json` in runs RUN-20261013-01 to -03 (BH: "remove").
- The chat channel name replaced with "chat" in the owner-correction note (BH: "replace").
- Each edited run record carries a dated line in its corrections section. The private source records are unchanged.
- `scripts/extract_form.py` now runs the model call in the system temp folder instead of a runtime cache folder (BH approved 2026-10-14). Changed in both repositories, so the scripts stay identical (source commit `fa1d550`). This changes skill code after the six counted runs; it only sets the working folder of the model call. Live check 2026-10-14: REQ-001 read by `claude-haiku-5-5`, form identical to `fixtures/forms/REQ-001.json`.
- `docs/route.md` is a public summary of the route step table, written for this copy (BH decision 2026-10-14, option 1). The planning note it replaces was not copied. Four references point to it: `SKILL.md`, `fixtures/forms/README.md`, and the docstrings of `scripts/quote.py` and `scripts/extract_form.py`. Those two docstring lines are the only difference between these scripts and the source scripts.
