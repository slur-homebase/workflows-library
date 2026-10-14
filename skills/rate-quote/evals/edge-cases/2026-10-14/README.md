# Edge-case tests, 2026-10-14 (outside the six; not supervised runs)

Code on branch `fixtures-edge-cases` (owner correction 2026-10-14 applied). Haiku 5.5 `claude-haiku-5-5`, prompt `step1-v0.3`, via `run_request.py`. Expected answers frozen in `docs/acceptance-rule-v1.1.md` before these runs.

| Request | Expected | Actual | Match |
|---|---|---|---|
| REQ-008 step 1 form | `fixtures/forms/REQ-008.json` | identical | yes |
| REQ-008 path | regular 1M row, TP 4.2300 | transfer_pricing 1M, 4.2300 | yes |
| REQ-008 dates | value 2026-10-01, end 2026-11-02, 32 days, no note | same | yes |
| REQ-008 rate | 5.4300 -> 5.43% | 5.4300 -> 5.43% | yes |
| REQ-009 step 1 form | `fixtures/forms/REQ-009.json` | identical | yes |
| REQ-009 path | forward rate, value date kept (earlier than T+2) | forward_rate_calculator, 4.8531, value 2026-09-30 kept | yes |
| REQ-009 dates | end 2026-11-16, 47 days, no note | same | yes |
| REQ-009 rate | 6.1531 -> 6.15% (BH hand calc) | 6.1531 -> 6.15% | yes |

Both drafts passed step 11. Nothing was sent. BH approved 2026-10-14 ("Yes"); full drafts shown to BH in chat after approval at his request.
