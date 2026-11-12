---
name: sanctions-news
description: Read invented sanctions news with dated source evidence.
version: 0.5
---

# sanctions-news

## What it does

Read invented subjects, a dated source plan and supplied local news articles.
Write evidence-backed findings, an offline findings page per subject and a comparison dashboard.
Keep source failures, missing checks, identity limits and the analyst's decisions separate from findings.

## Five-minute sample run

Use Python 3.9 or newer. Only the standard library is needed, with no install.
From this skill folder, run:

```sh
python3 scripts/run.py --subjects sample/subjects.json --articles sample/articles --out output
```

Open `output/dashboard.html` in a browser for comparisons and the timeline.
Open `output/index.html` for links to the five subjects' findings pages.
Use a new or empty output folder each time. Exit 0 means files were written, not approval of a subject.
The command prints one line for each research step, answer-key check and renderer.
Any failed step stops the command with a non-zero exit code before staged files are copied to output.

To read without running, open `demo/dashboard.html` or `demo/index.html`.
Regenerate the complete frozen sample, including its report files, with:

```sh
python3 scripts/run.py --demo
```

`--demo` uses only the bundled sample and writes only `demo/`.
It cannot be combined with custom input or output flags.
A browser needs JavaScript for dashboard interactions, but no server or connection.

## Inputs

- `--subjects`: invented subjects JSON, in the supplied sample format.
- `sources.json`: required beside the subjects file; contains snapshots, source statuses and the sample run date.
- `--articles`: Markdown articles with JSON-valued front matter in the supplied grammar.
- `answer-key.json`: optional beside subjects; when present, the existing checker replays research independently.
- `--out`: new or empty folder outside inputs, scripts and historical evidence.

The wrapper stages these files for the existing scripts. It moves no research or rendering rules.
Research never reads the key. With no key, the summary explicitly says that the check was skipped.
The bundled key has 38 checks, including the original twelve and added findings and relationships.
The bundled sample copies `fixtures/sanctions-news` at research baseline `bba5cde` without changing article bodies.

## Outputs

- `SUB-NNN.json`: evidence, summary, findings, possible matches, exclusions, source results, gaps, comparisons and links.
- `SUB-NNN.md`: the same report in readable text, including exact quotes, article ids and publication dates.
- `SUB-NNN.html`: the subject's offline findings page, with source limits and quoted evidence.
- `index.html`: links to all findings pages and one headline answer per subject.
- `dashboard.html`: side-by-side subject/article fields, full supplied articles, dated timeline and local analyst choices.
- `dashboard.html` is the news timeline, linked from the landing and findings pages.

The five-subject sample produces 17 files. `demo/` contains the identical set, under 2 MB.
HTML uses inline styles and scripts with no external loads.
Findings-page footers pin research provenance to full commit `bba5cde0e17e29c48f995be6b47f6f078b95a641`.
They use portable `reports/SUB-NNN.json` paths, not machine paths or the current packaging commit.
This keeps outputs byte-identical after moving folders or committing the demo.
The four scripts remain independently callable:

```sh
python3 scripts/research.py --subject SUB-001 --fixtures sample --out one-subject
python3 scripts/check_answer_key.py --fixtures sample
python3 scripts/render_page.py --all one-subject
python3 scripts/render_dashboard.py --reports one-subject --out one-subject/dashboard.html
```

The standalone page renderer uses local Git provenance unless `--commit-id` is supplied.
The skill version remains 0.5 because research rules and findings are unchanged.

## Evidence and two-tier links

A finding copies the source, article id, exact quote and publication date.
Name-only mentions stay possible matches; missing context is not a conflict.
Stated identity conflicts remain exclusions. Findings are not sanctions-list matches.
Each source has independent execution, result and freshness labels with dates.
Failed and unmade checks remain unavailable, even when their planned date is current.
A stale no-hit result is not current coverage. Nothing found is not a clearance.

`CONFIRMED` links require an explicit later reference to the earlier matter under the existing rule.
`SUGGESTED` links require matched identities, the same written authority, a later publication date,
and the same legal order or enough shared matter words under the frozen sample rule.
Suggestions have dashed edges labelled `suggested, analyst to confirm` and show their reasons.
Confirm or Reject requires the analyst's reason. Analyst confirmation is labelled separately.
Neither choice changes findings, counts, summaries or closure status.
Only an algorithm-confirmed relationship supplies a case-closed lane ending.
A settlement of potential liability is not a clearance or a conviction.

## Analyst decision rule

Read the exact article, identity context and coverage gaps before deciding.
Role and employer differences alone are weak; age or hard-identifier differences are stronger.
This sample displays no hard identifiers. Do not turn a missing cell into an invented fact.
The frozen research rule can exclude a stated role/employer conflict; that is not a new automatic human disposition.
For each article choose `Not our person`, `Our person, not relevant`, `Need more info` or `Investigate`.
Saving requires a reason. Identity-cell marks and link reviews are separate choices.
Browser localStorage keeps choices for this sample and file origin; storage errors are shown.
`Copy my decisions` exports choices with reasons and evidence snapshots, with a text fallback.
No choice changes the original evidence or the researcher's verdict.

## Data rules and limits

Use invented inputs only. Never use employer, bank or client data, real subjects or secrets.
All names are placeholders. Use no real place, regulator, sanctions list, outlet or publicly known person's name.
Reports omit birth dates, registration numbers and nationality fields.
There is no live search, network call, runtime model call, general adverse-media review or sanctions-list screening.
The parser handles this supplied grammar, not arbitrary news prose. A missed phrase proves nothing about a subject.
The sanctions packet join is deferred. The tool never chooses clear or escalate, sends or publishes.
Human review and separate approval remain required. Nothing is deployed or connected to an employer system.

## Verification and historical evidence

From this skill folder:

```sh
python3 scripts/check_answer_key.py --fixtures sample
python3 -m unittest discover -s tests
python3 -m unittest discover -s ../release-check/tests -p test_sanctions_news_package.py
python3 ../release-check/scripts/release_check.py .
```

The sanctions-news release check verifies the offline package, banned terms, size and exact demo replay.
Its `PASS` is not a signed release or supervised human acceptance; the rate-quote gate is unchanged.
`evidence/phase-3/` is frozen historical model-reader evidence, not the current sample or runtime route.
Never refresh it with a model call. `evidence/phase-4/` retains round-3 and stage-settlement proof only.
Public README case-study text is pending Kiba.
