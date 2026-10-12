# workflows-lib

Reusable agent skills for regulated back-office workflows, built and tested in public.

Status: in build. First skill launches 15 Nov 2026. Supervised runs logged so far: 0.

## What this is

One working skill at a time, each with synthetic test data, a run log and a case study. The point is that a reader can run the skill and check the answer, not read a claim about it.

## Skills

| Skill | What it does | Supervised runs | Status |
|---|---|---|---|
| rate-quote | Turns a customer's drawdown request into an indicative interest-rate quote draft, with deterministic date and lookup checks and a human approval before anything is sent | 0 | in build |

## How a skill is laid out

```
skills/<skill>/
  SKILL.md        what the skill does, step by step, and who runs each step
  references/     rules the skill follows, in plain words
  fixtures/       synthetic inputs and expected answers
  runs/           one file per supervised run: input, expected, actual, pass/fail, reviewer note
```

## How to run

To be written with the first skill.

## Run log

`runs/runs.csv` lists every supervised run. If a run is not in the log, it did not happen.

## Case study

To be written after the first supervised run. It will state what was measured, what passed, what did not, and where a person had to step in.

## Data rules

See [DATA-RULES.md](DATA-RULES.md). Everything here is synthetic and nothing is deployed anywhere.

## Licence

MIT. See [LICENSE](LICENSE).
