# Sanctions news sample: answer-key review

The 365-day freshness limit is for this sample only.

Owner review of the synthetic sample. Synthetic sample only. Names are placeholders and events are invented. The sample is local in style only; no real place names are used.

The owner accepted the 12 answers on 2026-10-29 with two changes: a 365-day sample freshness limit and invented local context. Round 3 applies those changes. Review of this revision is complete.

Run date: 2026-10-28. The original baseline uses 20 supplied articles. Dashboard round 3 adds ART-021 through ART-029, so the expanded replay checks 29 articles. Source status uses three separate fields: execution (did the check run), result (what it found), freshness (how old the source snapshot is). A current planned date does not mean a failed check ran. Article age does not set source freshness.

For every subject, SRC-004 failed and SRC-005 was not attempted. Both results stay unavailable. SRC-003 is stale as of 2025-09-01. The rows below retain those gaps rather than give a clearance.

| Subject | What the tool must say | The quote | Why it is right |
|---|---|---|---|
| ABC Components Pte. Ltd. (SUB-001) | F-001: Report the invented export restriction dated 2026-10-20. Do not claim a real sanctions-list match. | ART-001 (2026-10-20): "The Trade Sanctions Office of Country X designated ABC Components Pte. Ltd., a distributor of electronic components, under the Controlled Components Order 2024 on 2026-10-20, imposing a sanctions restriction that blocks its assets and prohibits dealings with it." | The article matches the company name and stated profile and reports an authority, action date, legal ground and practical restriction. |
| ABC Components Pte. Ltd. (SUB-001) | F-002: Report a suspected sanctions-evasion investigation, not proven conduct. The outlet could not immediately confirm it; the company did not respond. No outcome is reported. | ART-002 (2026-10-22): "According to Business News A on 2026-10-22, the Customs Agency A is investigating ABC Components Pte. Ltd., a distributor of electronic components, on suspicion of sanctions evasion through dual-use components routed via a third-country distributor." | The article matches the company name and stated profile, attributes the investigation and states its verification limit and lack of company response. It does not report a denial. |
| Tan Wei Quen (SUB-002) | F-003: Report the invented travel restriction for the nominee director at JKL Trading Pte. Ltd. Do not attach the retired harbour clerk's sanctions inquiry. | ART-006 (2026-10-23): "The Sanctions Office of Country Y imposed a sanctions travel restriction under the Nominee Dealings Order 2025 on Tan Wei Quen, 39, nominee director at JKL Trading Pte. Ltd., on 2026-10-23 for lending his name to a designated beneficial owner." | The name, role, employer and age match the subject. The article supplies no birth date or nationality. |
| Tan Wei Quen (SUB-002) | T-001: Exclude the sanctions inquiry about the retired harbour clerk at PQR Port Services Pte. Ltd. This subject is the nominee director at JKL Trading Pte. Ltd. | ART-004 (2026-10-21): "According to Business News A on 2026-10-21, the Customs Agency A is investigating Tan Wei Quen, 67, a retired harbour clerk at PQR Port Services Pte. Ltd., on suspicion of sanctions circumvention through free-port permits." | The name is the same, but the reported role, employer and age differ. Matching the name alone attaches the inquiry to the wrong person. |
| DEF Ship Management Pte. Ltd. (SUB-003) | F-004: Keep the August allegation as history and say it was cleared on 2026-10-24. Do not show it as open. | ART-007 (2025-08-12): "According to Business News A on 2025-08-12, the Enforcement Agency C is investigating DEF Ship Management Pte. Ltd., a provider of vessel bunkering services, on suspicion of sanctions circumvention through bunkering a vessel linked to a designated owner under the Vessel Services Order 2024."<br>ART-009 (2026-10-24): "The Enforcement Agency C announced that it cleared DEF Ship Management Pte. Ltd., a provider of vessel bunkering services, on 2026-10-24 and closed the sanctions-circumvention case over vessel bunkering under the Vessel Services Order 2024 after confirming that the services were permitted, removing the company from its local restrictions register." | The authority closes the same vessel-bunkering sanctions case after confirming the services were permitted and removes the company from its local restrictions register. The company name and stated profile match; it is not preferred just because it is newer. |
| DEF Ship Management Pte. Ltd. (SUB-003) | T-002: Link the old allegation to the later clearing decision. Keep both dates and do not present the allegation as still open. | ART-007 (2025-08-12): "According to Business News A on 2025-08-12, the Enforcement Agency C is investigating DEF Ship Management Pte. Ltd., a provider of vessel bunkering services, on suspicion of sanctions circumvention through bunkering a vessel linked to a designated owner under the Vessel Services Order 2024."<br>ART-009 (2026-10-24): "The Enforcement Agency C announced that it cleared DEF Ship Management Pte. Ltd., a provider of vessel bunkering services, on 2026-10-24 and closed the sanctions-circumvention case over vessel bunkering under the Vessel Services Order 2024 after confirming that the services were permitted, removing the company from its local restrictions register." | ART-009 matches the company name and stated profile and explicitly closes the vessel-bunkering case first reported on 2025-08-12 in ART-007. |
| Ravi Selvam (SUB-004) | F-005: Report the suspected free-port sanctions-evasion investigation, not proven conduct. The outlet could not immediately confirm it; the commodity trader did not respond. No outcome is reported. | ART-010 (2026-10-25): "According to Shipping News B on 2026-10-25, the Customs Agency B is investigating Ravi Selvam, 46, a commodity trader, on suspicion of sanctions evasion through fuel cargo transhipment at Orlath free port." | The name and commodity-trader role match. The report states suspicion, its verification limit and no response, not a denial or finding of guilt. |
| Ravi Selvam (SUB-004) | F-006: Keep the dated maritime sanctions inquiry of 2025-08-19. No follow-up was found in any supplied source; status unknown. SRC-003 coverage stops at 2025-09-01. Do not infer that the inquiry is still open or closed. | ART-017 (2025-08-19): "According to Trade News C on 2025-08-19, the Maritime Agency D is investigating Ravi Selvam, a commodity trader, on suspicion of sanctions circumvention through fuel cargoes shipped from Nivren quay." | The name and role match. Only ART-017 reports the Nivren quay maritime case. The later free-port investigation concerns Orlath free port, not a development of this case. |
| Ravi Selvam (SUB-004) | T-004: SRC-003 is completed, finding, stale, as of 2025-09-01. Keep the dated sanctions inquiry; no follow-up was found in any supplied source and its status is unknown. | ART-017 (2025-08-19): "According to Trade News C on 2025-08-19, the Maritime Agency D is investigating Ravi Selvam, a commodity trader, on suspicion of sanctions circumvention through fuel cargoes shipped from Nivren quay." | The dated report has no later development in the supplied set. Silence does not establish whether the case is open or closed; the source's stale status remains separate. |
| GHI Family Imports Pte. Ltd. (SUB-005) | T-003: SRC-004 is failed, unavailable, current (planned date only, nothing read), as of 2026-10-28. Never say no finding for this failed check. Retry is still needed. | No article or quote: this source was not read. | An invented timeout returned no articles. The planned snapshot date is current, but no search was completed. |
| GHI Family Imports Pte. Ltd. (SUB-005) | T-005: No findings for GHI Family Imports Pte. Ltd. in the supplied articles from completed sources. SRC-004 failed; SRC-005 was not attempted; SRC-003 covers nothing after 2025-09-01. This is not a clearance. | ART-012 (2026-10-22): "GHI Family Imports Pte. Ltd., a family-run importer of kitchenware, ran a family import-business packing class on 2026-10-22."<br>ART-013 (2026-10-27): "GHI Family Imports Pte. Ltd., a family-run importer of kitchenware, updated its shop hours on 2026-10-27."<br>ART-018 (2025-08-28): "GHI Family Imports Pte. Ltd., a family-run importer of kitchenware, prepared an imported kitchenware display on 2025-08-28." | The only mentions are ordinary events. All 20 supplied articles were checked, not the whole news universe. Missing and stale coverage remain visible. |
| GHI Family Imports Pte. Ltd. (SUB-005) | T-006: SRC-005 is not attempted, unavailable, current (planned date only, nothing read), as of 2026-10-28. Do not present an unmade check as no finding. | No article or quote: this source was not read. | The source was in the plan but was not read. No article or quote exists for it. |

## Round-3 additions (rows 13 onward)

The original twelve table rows above are retained unchanged as the accepted baseline. Their article-count wording describes that baseline; all 29 articles are now checked for every subject. The existing source-plan bytes remain unchanged. Exact checked-ID lists in the answer key and replay reports define the expanded supplied coverage.

These additional rows distinguish attributed pickup coverage from independent evidence. A relationship is not a disposition: the original allegation remains a historical report, settlement does not imply an admission or exoneration, and delisting does not itself establish innocence. No new article explicitly names an earlier report or its date.

### 13. F-007 — SUB-001

**What the tool must say:** Report an attributed pickup of the suspected components-routing sanctions investigation, not proven conduct. Preserve the outlet verification limit and company non-response.

**Why:** The same company name and electronic-components profile are repeated. Customs Agency A and the routing conduct match ART-002; the legal order is supplied here without naming an earlier report or date.

**Article evidence:** `articles/ART-021.md:12` (2026-10-23)

> According to Business News A, the Customs Agency A is investigating ABC Components Pte. Ltd., a distributor of electronic components, on suspicion of sanctions evasion through dual-use components routed via a third-country distributor under the Dual-Use Routing Order 2025.

### 14. F-008 — SUB-001

**What the tool must say:** Report the civil settlement of potential liability for apparent violations. The stated settlement sets stage settlement, but is not an admission, conviction or clearance. Keep the settlement separate from the original investigation article.

**Stage:** `settlement`

**Why:** The same company, profile, Customs Agency A and dual-use routing conduct appear with the Dual-Use Routing Order 2025. A settlement supplies a later development, not proof of guilt or a clearance.

**Article evidence:** `articles/ART-022.md:12` (2026-10-26)

> According to Business News A, the Customs Agency A said ABC Components Pte. Ltd., a distributor of electronic components, agreed to settle potential civil liability for apparent violations of the Dual-Use Routing Order 2025 in a sanctions settlement concerning dual-use components routed via a third-country distributor.

### 15. F-009 — SUB-001

**What the tool must say:** Report this suspected bonded-storage inquiry as a separate matter. Reject the suggested relationship to the components-routing matter after human review; do not merge the legal orders or conduct.

**Why:** The company and authority match and generic components/distributor wording overlaps. Bonded Storage Order 2026 and false inventory descriptions concern storage, unlike the Dual-Use Routing Order 2025 routing matter. Metadata uses its own EVT-020.

**Article evidence:** `articles/ART-023.md:12` (2026-10-27)

> According to Shipping News B, the Customs Agency A is investigating ABC Components Pte. Ltd., a distributor of electronic components, on suspicion of sanctions evasion involving false inventory descriptions for electronic components routed into distributor storage under the Bonded Storage Order 2026.

### 16. F-010 — SUB-002

**What the tool must say:** Report an attributed pickup of the nominee-director travel restriction, preserving the role, employer and age. Do not merge the retired clerk.

**Why:** The same Sanctions Office of Country Y, Nominee Dealings Order 2025, travel restriction and designated-beneficial-owner conduct match ART-006. Role, employer and age match the nominee director.

**Article evidence:** `articles/ART-024.md:12` (2026-10-24)

> According to Business News A, the Sanctions Office of Country Y imposed a sanctions travel restriction under the Nominee Dealings Order 2025 on Tan Wei Quen, 39, nominee director at JKL Trading Pte. Ltd., for lending his name to a designated beneficial owner.

### 17. F-011 — SUB-002

**What the tool must say:** Report the lifting and delisting of the nominee-director travel restriction. Do not call this an exoneration or transfer it to the retired clerk.

**Why:** The same Sanctions Office of Country Y and Nominee Dealings Order 2025 lift the named nominee director's travel restriction. No earlier report/date is named, so the relationship must be grounded in authority and matter rather than an explicit back-reference.

**Article evidence:** `articles/ART-025.md:12` (2026-10-27)

> According to Business News A, the Sanctions Office of Country Y delisted Tan Wei Quen, 39, nominee director at JKL Trading Pte. Ltd., under the Nominee Dealings Order 2025 and lifted the sanctions travel restriction concerning lending his name to a designated beneficial owner.

### 18. T-007 — SUB-002

**What the tool must say:** Exclude the retired harbour clerk follow-up from the nominee-director findings and from every suggested or confirmed link. Preserve all three identity conflicts.

**Why:** The same-name follow-up repeats age 67, retired harbour clerk and PQR Port Services Pte. Ltd. It concerns ART-004's different person, not the age-39 nominee director.

**Article evidence:** `articles/ART-026.md:12` (2026-10-25)

> According to Business News A, the Customs Agency A is investigating Tan Wei Quen, 67, a retired harbour clerk at PQR Port Services Pte. Ltd., on suspicion of sanctions circumvention through free-port permits.

### 19. F-012 — SUB-004

**What the tool must say:** Report an attributed pickup of the suspected fuel-cargo free-port investigation. Preserve uncertainty and non-response; do not develop or link the stale maritime inquiry.

**Why:** Customs Agency B, the fuel cargo transhipment conduct, the free port, age and commodity-trader role match ART-010. No Maritime Agency D, quay matter or outcome is reported.

**Article evidence:** `articles/ART-027.md:12` (2026-10-26)

> According to Shipping News B, the Customs Agency B is investigating Ravi Selvam, 46, a commodity trader, on suspicion of sanctions evasion through fuel cargo transhipment at Orlath free port.

### 20. F-013 — SUB-001

**What the tool must say:** Report the second outlet's attributed civil-settlement pickup without treating it as independent confirmation. The stated settlement sets stage settlement, but is not an admission, conviction or clearance.

**Stage:** `settlement`

**Why:** The quoted settlement has the same company, profile, Customs Agency A, legal order and routing conduct as ART-022. Attribution remains visible; this is pickup coverage, not new independent evidence.

**Article evidence:** `articles/ART-028.md:12` (2026-10-27)

> According to Business News A, the Customs Agency A said ABC Components Pte. Ltd., a distributor of electronic components, agreed to settle potential civil liability for apparent violations of the Dual-Use Routing Order 2025 in a sanctions settlement concerning dual-use components routed via a third-country distributor.

### 21. F-014 — SUB-002

**What the tool must say:** Report the attributed delisting pickup for the nominee director without implying independent verification or exoneration.

**Why:** The same office, order, identity and lifted travel restriction match ART-025. The second outlet states that it could not immediately confirm the delisting.

**Article evidence:** `articles/ART-029.md:12` (2026-10-28)

> According to Business News A, the Sanctions Office of Country Y delisted Tan Wei Quen, 39, nominee director at JKL Trading Pte. Ltd., under the Nominee Dealings Order 2025 and lifted the sanctions travel restriction concerning lending his name to a designated beneficial owner.

### 22. L-001 — SUB-001

**What the tool must say:** Show ART-021 -> ART-002 as SUGGESTED with the exact text-grounded reasons. Analyst must confirm or reject; do not change findings or status.

**Why:** Relationship evidence is the matched identity, increasing publication date, explicit authority, and matching legal order or sufficiently specific shared matter wording. Generic overlap is only a suggestion and requires human review.

**Article evidence:** `articles/ART-002.md:12` (2026-10-22)

> According to Business News A on 2026-10-22, the Customs Agency A is investigating ABC Components Pte. Ltd., a distributor of electronic components, on suspicion of sanctions evasion through dual-use components routed via a third-country distributor.

**Article evidence:** `articles/ART-021.md:12` (2026-10-23)

> According to Business News A, the Customs Agency A is investigating ABC Components Pte. Ltd., a distributor of electronic components, on suspicion of sanctions evasion through dual-use components routed via a third-country distributor under the Dual-Use Routing Order 2025.

**Expected tier:** SUGGESTED

**Exact reasons:**

- Matched subject identity: ABC Components Pte. Ltd.
- Same authority: Customs Agency A
- Publication date order: 2026-10-22 < 2026-10-23
- Shared matter words: distributor, electronic, evasion, routed, third

### 23. L-002 — SUB-001

**What the tool must say:** Show ART-022 -> ART-002 as SUGGESTED with the exact text-grounded reasons. Analyst must confirm or reject; do not change findings or status.

**Why:** Relationship evidence is the matched identity, increasing publication date, explicit authority, and matching legal order or sufficiently specific shared matter wording. Generic overlap is only a suggestion and requires human review.

**Article evidence:** `articles/ART-002.md:12` (2026-10-22)

> According to Business News A on 2026-10-22, the Customs Agency A is investigating ABC Components Pte. Ltd., a distributor of electronic components, on suspicion of sanctions evasion through dual-use components routed via a third-country distributor.

**Article evidence:** `articles/ART-022.md:12` (2026-10-26)

> According to Business News A, the Customs Agency A said ABC Components Pte. Ltd., a distributor of electronic components, agreed to settle potential civil liability for apparent violations of the Dual-Use Routing Order 2025 in a sanctions settlement concerning dual-use components routed via a third-country distributor.

**Expected tier:** SUGGESTED

**Exact reasons:**

- Matched subject identity: ABC Components Pte. Ltd.
- Same authority: Customs Agency A
- Publication date order: 2026-10-22 < 2026-10-26
- Shared matter words: distributor, electronic, routed, third

### 24. L-003 — SUB-001

**What the tool must say:** Show ART-022 -> ART-021 as SUGGESTED with the exact text-grounded reasons. Analyst must confirm or reject; do not change findings or status.

**Why:** Relationship evidence is the matched identity, increasing publication date, explicit authority, and matching legal order or sufficiently specific shared matter wording. Generic overlap is only a suggestion and requires human review.

**Article evidence:** `articles/ART-021.md:12` (2026-10-23)

> According to Business News A, the Customs Agency A is investigating ABC Components Pte. Ltd., a distributor of electronic components, on suspicion of sanctions evasion through dual-use components routed via a third-country distributor under the Dual-Use Routing Order 2025.

**Article evidence:** `articles/ART-022.md:12` (2026-10-26)

> According to Business News A, the Customs Agency A said ABC Components Pte. Ltd., a distributor of electronic components, agreed to settle potential civil liability for apparent violations of the Dual-Use Routing Order 2025 in a sanctions settlement concerning dual-use components routed via a third-country distributor.

**Expected tier:** SUGGESTED

**Exact reasons:**

- Matched subject identity: ABC Components Pte. Ltd.
- Same authority: Customs Agency A
- Publication date order: 2026-10-23 < 2026-10-26
- Same legal order: Dual-Use Routing Order 2025
- Shared matter words: distributor, electronic, routed, third

### 25. L-004 — SUB-001

**What the tool must say:** Show ART-023 -> ART-002 as SUGGESTED with the exact text-grounded reasons. Analyst must reject this different-matter decoy.

**Why:** The bonded-storage order and false-inventory conduct differ from the dual-use routing matter. Generic word overlap is not proof of one matter.

**Article evidence:** `articles/ART-002.md:12` (2026-10-22)

> According to Business News A on 2026-10-22, the Customs Agency A is investigating ABC Components Pte. Ltd., a distributor of electronic components, on suspicion of sanctions evasion through dual-use components routed via a third-country distributor.

**Article evidence:** `articles/ART-023.md:12` (2026-10-27)

> According to Shipping News B, the Customs Agency A is investigating ABC Components Pte. Ltd., a distributor of electronic components, on suspicion of sanctions evasion involving false inventory descriptions for electronic components routed into distributor storage under the Bonded Storage Order 2026.

**Expected tier:** SUGGESTED

**Exact reasons:**

- Matched subject identity: ABC Components Pte. Ltd.
- Same authority: Customs Agency A
- Publication date order: 2026-10-22 < 2026-10-27
- Shared matter words: distributor, electronic, evasion, routed

**Correct action:** Reject. Different Bonded Storage Order 2026 and false-inventory storage conduct; not the Dual-Use Routing Order 2025 routing matter.

### 26. L-005 — SUB-001

**What the tool must say:** Show ART-023 -> ART-021 as SUGGESTED with the exact text-grounded reasons. Analyst must reject this different-matter decoy.

**Why:** The bonded-storage order and false-inventory conduct differ from the dual-use routing matter. Generic word overlap is not proof of one matter.

**Article evidence:** `articles/ART-021.md:12` (2026-10-23)

> According to Business News A, the Customs Agency A is investigating ABC Components Pte. Ltd., a distributor of electronic components, on suspicion of sanctions evasion through dual-use components routed via a third-country distributor under the Dual-Use Routing Order 2025.

**Article evidence:** `articles/ART-023.md:12` (2026-10-27)

> According to Shipping News B, the Customs Agency A is investigating ABC Components Pte. Ltd., a distributor of electronic components, on suspicion of sanctions evasion involving false inventory descriptions for electronic components routed into distributor storage under the Bonded Storage Order 2026.

**Expected tier:** SUGGESTED

**Exact reasons:**

- Matched subject identity: ABC Components Pte. Ltd.
- Same authority: Customs Agency A
- Publication date order: 2026-10-23 < 2026-10-27
- Shared matter words: distributor, electronic, evasion, routed

**Correct action:** Reject. Different Bonded Storage Order 2026 and false-inventory storage conduct; not the Dual-Use Routing Order 2025 routing matter.

### 27. L-006 — SUB-001

**What the tool must say:** Show ART-023 -> ART-022 as SUGGESTED with the exact text-grounded reasons. Analyst must reject this different-matter decoy.

**Why:** The bonded-storage order and false-inventory conduct differ from the dual-use routing matter. Generic word overlap is not proof of one matter.

**Article evidence:** `articles/ART-022.md:12` (2026-10-26)

> According to Business News A, the Customs Agency A said ABC Components Pte. Ltd., a distributor of electronic components, agreed to settle potential civil liability for apparent violations of the Dual-Use Routing Order 2025 in a sanctions settlement concerning dual-use components routed via a third-country distributor.

**Article evidence:** `articles/ART-023.md:12` (2026-10-27)

> According to Shipping News B, the Customs Agency A is investigating ABC Components Pte. Ltd., a distributor of electronic components, on suspicion of sanctions evasion involving false inventory descriptions for electronic components routed into distributor storage under the Bonded Storage Order 2026.

**Expected tier:** SUGGESTED

**Exact reasons:**

- Matched subject identity: ABC Components Pte. Ltd.
- Same authority: Customs Agency A
- Publication date order: 2026-10-26 < 2026-10-27
- Shared matter words: distributor, electronic, routed

**Correct action:** Reject. Different Bonded Storage Order 2026 and false-inventory storage conduct; not the Dual-Use Routing Order 2025 routing matter.

### 28. L-007 — SUB-001

**What the tool must say:** Show ART-028 -> ART-002 as SUGGESTED with the exact text-grounded reasons. Analyst must confirm or reject; do not change findings or status.

**Why:** Relationship evidence is the matched identity, increasing publication date, explicit authority, and matching legal order or sufficiently specific shared matter wording. Generic overlap is only a suggestion and requires human review.

**Article evidence:** `articles/ART-002.md:12` (2026-10-22)

> According to Business News A on 2026-10-22, the Customs Agency A is investigating ABC Components Pte. Ltd., a distributor of electronic components, on suspicion of sanctions evasion through dual-use components routed via a third-country distributor.

**Article evidence:** `articles/ART-028.md:12` (2026-10-27)

> According to Business News A, the Customs Agency A said ABC Components Pte. Ltd., a distributor of electronic components, agreed to settle potential civil liability for apparent violations of the Dual-Use Routing Order 2025 in a sanctions settlement concerning dual-use components routed via a third-country distributor.

**Expected tier:** SUGGESTED

**Exact reasons:**

- Matched subject identity: ABC Components Pte. Ltd.
- Same authority: Customs Agency A
- Publication date order: 2026-10-22 < 2026-10-27
- Shared matter words: distributor, electronic, routed, third

### 29. L-008 — SUB-001

**What the tool must say:** Show ART-028 -> ART-021 as SUGGESTED with the exact text-grounded reasons. Analyst must confirm or reject; do not change findings or status.

**Why:** Relationship evidence is the matched identity, increasing publication date, explicit authority, and matching legal order or sufficiently specific shared matter wording. Generic overlap is only a suggestion and requires human review.

**Article evidence:** `articles/ART-021.md:12` (2026-10-23)

> According to Business News A, the Customs Agency A is investigating ABC Components Pte. Ltd., a distributor of electronic components, on suspicion of sanctions evasion through dual-use components routed via a third-country distributor under the Dual-Use Routing Order 2025.

**Article evidence:** `articles/ART-028.md:12` (2026-10-27)

> According to Business News A, the Customs Agency A said ABC Components Pte. Ltd., a distributor of electronic components, agreed to settle potential civil liability for apparent violations of the Dual-Use Routing Order 2025 in a sanctions settlement concerning dual-use components routed via a third-country distributor.

**Expected tier:** SUGGESTED

**Exact reasons:**

- Matched subject identity: ABC Components Pte. Ltd.
- Same authority: Customs Agency A
- Publication date order: 2026-10-23 < 2026-10-27
- Same legal order: Dual-Use Routing Order 2025
- Shared matter words: distributor, electronic, routed, third

### 30. L-009 — SUB-001

**What the tool must say:** Show ART-028 -> ART-022 as SUGGESTED with the exact text-grounded reasons. Analyst must confirm or reject; do not change findings or status.

**Why:** Relationship evidence is the matched identity, increasing publication date, explicit authority, and matching legal order or sufficiently specific shared matter wording. Generic overlap is only a suggestion and requires human review.

**Article evidence:** `articles/ART-022.md:12` (2026-10-26)

> According to Business News A, the Customs Agency A said ABC Components Pte. Ltd., a distributor of electronic components, agreed to settle potential civil liability for apparent violations of the Dual-Use Routing Order 2025 in a sanctions settlement concerning dual-use components routed via a third-country distributor.

**Article evidence:** `articles/ART-028.md:12` (2026-10-27)

> According to Business News A, the Customs Agency A said ABC Components Pte. Ltd., a distributor of electronic components, agreed to settle potential civil liability for apparent violations of the Dual-Use Routing Order 2025 in a sanctions settlement concerning dual-use components routed via a third-country distributor.

**Expected tier:** SUGGESTED

**Exact reasons:**

- Matched subject identity: ABC Components Pte. Ltd.
- Same authority: Customs Agency A
- Publication date order: 2026-10-26 < 2026-10-27
- Same legal order: Dual-Use Routing Order 2025
- Shared matter words: distributor, electronic, routed, third

### 31. L-010 — SUB-002

**What the tool must say:** Show ART-024 -> ART-006 as SUGGESTED with the exact text-grounded reasons. Analyst must confirm or reject; do not change findings or status.

**Why:** Relationship evidence is the matched identity, increasing publication date, explicit authority, and matching legal order or sufficiently specific shared matter wording. Generic overlap is only a suggestion and requires human review.

**Article evidence:** `articles/ART-006.md:12` (2026-10-23)

> The Sanctions Office of Country Y imposed a sanctions travel restriction under the Nominee Dealings Order 2025 on Tan Wei Quen, 39, nominee director at JKL Trading Pte. Ltd., on 2026-10-23 for lending his name to a designated beneficial owner.

**Article evidence:** `articles/ART-024.md:12` (2026-10-24)

> According to Business News A, the Sanctions Office of Country Y imposed a sanctions travel restriction under the Nominee Dealings Order 2025 on Tan Wei Quen, 39, nominee director at JKL Trading Pte. Ltd., for lending his name to a designated beneficial owner.

**Expected tier:** SUGGESTED

**Exact reasons:**

- Matched subject identity: Tan Wei Quen
- Same authority: Sanctions Office of Country Y
- Publication date order: 2026-10-23 < 2026-10-24
- Same legal order: Nominee Dealings Order 2025
- Shared matter words: beneficial, director, lending, owner, restriction, trading, travel

### 32. L-011 — SUB-002

**What the tool must say:** Show ART-025 -> ART-006 as SUGGESTED with the exact text-grounded reasons. Analyst must confirm or reject; do not change findings or status.

**Why:** Relationship evidence is the matched identity, increasing publication date, explicit authority, and matching legal order or sufficiently specific shared matter wording. Generic overlap is only a suggestion and requires human review.

**Article evidence:** `articles/ART-006.md:12` (2026-10-23)

> The Sanctions Office of Country Y imposed a sanctions travel restriction under the Nominee Dealings Order 2025 on Tan Wei Quen, 39, nominee director at JKL Trading Pte. Ltd., on 2026-10-23 for lending his name to a designated beneficial owner.

**Article evidence:** `articles/ART-025.md:12` (2026-10-27)

> According to Business News A, the Sanctions Office of Country Y delisted Tan Wei Quen, 39, nominee director at JKL Trading Pte. Ltd., under the Nominee Dealings Order 2025 and lifted the sanctions travel restriction concerning lending his name to a designated beneficial owner.

**Expected tier:** SUGGESTED

**Exact reasons:**

- Matched subject identity: Tan Wei Quen
- Same authority: Sanctions Office of Country Y
- Publication date order: 2026-10-23 < 2026-10-27
- Same legal order: Nominee Dealings Order 2025
- Shared matter words: beneficial, director, lending, owner, restriction, trading, travel

### 33. L-012 — SUB-002

**What the tool must say:** Show ART-025 -> ART-024 as SUGGESTED with the exact text-grounded reasons. Analyst must confirm or reject; do not change findings or status.

**Why:** Relationship evidence is the matched identity, increasing publication date, explicit authority, and matching legal order or sufficiently specific shared matter wording. Generic overlap is only a suggestion and requires human review.

**Article evidence:** `articles/ART-024.md:12` (2026-10-24)

> According to Business News A, the Sanctions Office of Country Y imposed a sanctions travel restriction under the Nominee Dealings Order 2025 on Tan Wei Quen, 39, nominee director at JKL Trading Pte. Ltd., for lending his name to a designated beneficial owner.

**Article evidence:** `articles/ART-025.md:12` (2026-10-27)

> According to Business News A, the Sanctions Office of Country Y delisted Tan Wei Quen, 39, nominee director at JKL Trading Pte. Ltd., under the Nominee Dealings Order 2025 and lifted the sanctions travel restriction concerning lending his name to a designated beneficial owner.

**Expected tier:** SUGGESTED

**Exact reasons:**

- Matched subject identity: Tan Wei Quen
- Same authority: Sanctions Office of Country Y
- Publication date order: 2026-10-24 < 2026-10-27
- Same legal order: Nominee Dealings Order 2025
- Shared matter words: beneficial, director, lending, owner, restriction, trading, travel

### 34. L-013 — SUB-002

**What the tool must say:** Show ART-029 -> ART-006 as SUGGESTED with the exact text-grounded reasons. Analyst must confirm or reject; do not change findings or status.

**Why:** Relationship evidence is the matched identity, increasing publication date, explicit authority, and matching legal order or sufficiently specific shared matter wording. Generic overlap is only a suggestion and requires human review.

**Article evidence:** `articles/ART-006.md:12` (2026-10-23)

> The Sanctions Office of Country Y imposed a sanctions travel restriction under the Nominee Dealings Order 2025 on Tan Wei Quen, 39, nominee director at JKL Trading Pte. Ltd., on 2026-10-23 for lending his name to a designated beneficial owner.

**Article evidence:** `articles/ART-029.md:12` (2026-10-28)

> According to Business News A, the Sanctions Office of Country Y delisted Tan Wei Quen, 39, nominee director at JKL Trading Pte. Ltd., under the Nominee Dealings Order 2025 and lifted the sanctions travel restriction concerning lending his name to a designated beneficial owner.

**Expected tier:** SUGGESTED

**Exact reasons:**

- Matched subject identity: Tan Wei Quen
- Same authority: Sanctions Office of Country Y
- Publication date order: 2026-10-23 < 2026-10-28
- Same legal order: Nominee Dealings Order 2025
- Shared matter words: beneficial, director, lending, owner, restriction, trading, travel

### 35. L-014 — SUB-002

**What the tool must say:** Show ART-029 -> ART-024 as SUGGESTED with the exact text-grounded reasons. Analyst must confirm or reject; do not change findings or status.

**Why:** Relationship evidence is the matched identity, increasing publication date, explicit authority, and matching legal order or sufficiently specific shared matter wording. Generic overlap is only a suggestion and requires human review.

**Article evidence:** `articles/ART-024.md:12` (2026-10-24)

> According to Business News A, the Sanctions Office of Country Y imposed a sanctions travel restriction under the Nominee Dealings Order 2025 on Tan Wei Quen, 39, nominee director at JKL Trading Pte. Ltd., for lending his name to a designated beneficial owner.

**Article evidence:** `articles/ART-029.md:12` (2026-10-28)

> According to Business News A, the Sanctions Office of Country Y delisted Tan Wei Quen, 39, nominee director at JKL Trading Pte. Ltd., under the Nominee Dealings Order 2025 and lifted the sanctions travel restriction concerning lending his name to a designated beneficial owner.

**Expected tier:** SUGGESTED

**Exact reasons:**

- Matched subject identity: Tan Wei Quen
- Same authority: Sanctions Office of Country Y
- Publication date order: 2026-10-24 < 2026-10-28
- Same legal order: Nominee Dealings Order 2025
- Shared matter words: beneficial, director, lending, owner, restriction, trading, travel

### 36. L-015 — SUB-002

**What the tool must say:** Show ART-029 -> ART-025 as SUGGESTED with the exact text-grounded reasons. Analyst must confirm or reject; do not change findings or status.

**Why:** Relationship evidence is the matched identity, increasing publication date, explicit authority, and matching legal order or sufficiently specific shared matter wording. Generic overlap is only a suggestion and requires human review.

**Article evidence:** `articles/ART-025.md:12` (2026-10-27)

> According to Business News A, the Sanctions Office of Country Y delisted Tan Wei Quen, 39, nominee director at JKL Trading Pte. Ltd., under the Nominee Dealings Order 2025 and lifted the sanctions travel restriction concerning lending his name to a designated beneficial owner.

**Article evidence:** `articles/ART-029.md:12` (2026-10-28)

> According to Business News A, the Sanctions Office of Country Y delisted Tan Wei Quen, 39, nominee director at JKL Trading Pte. Ltd., under the Nominee Dealings Order 2025 and lifted the sanctions travel restriction concerning lending his name to a designated beneficial owner.

**Expected tier:** SUGGESTED

**Exact reasons:**

- Matched subject identity: Tan Wei Quen
- Same authority: Sanctions Office of Country Y
- Publication date order: 2026-10-27 < 2026-10-28
- Same legal order: Nominee Dealings Order 2025
- Shared matter words: beneficial, director, lending, owner, restriction, trading, travel

### 37. L-016 — SUB-003

**What the tool must say:** Show ART-009 -> ART-007 as CONFIRMED with the exact text-grounded reasons. Explicit reference confirms the relationship.

**Why:** Relationship evidence is the matched identity, increasing publication date, explicit authority, and matching legal order or sufficiently specific shared matter wording. Generic overlap is only a suggestion and requires human review.

**Article evidence:** `articles/ART-007.md:12` (2025-08-12)

> According to Business News A on 2025-08-12, the Enforcement Agency C is investigating DEF Ship Management Pte. Ltd., a provider of vessel bunkering services, on suspicion of sanctions circumvention through bunkering a vessel linked to a designated owner under the Vessel Services Order 2024.

**Article evidence:** `articles/ART-009.md:12` (2026-10-24)

> The Enforcement Agency C announced that it cleared DEF Ship Management Pte. Ltd., a provider of vessel bunkering services, on 2026-10-24 and closed the sanctions-circumvention case over vessel bunkering under the Vessel Services Order 2024 after confirming that the services were permitted, removing the company from its local restrictions register.

**Expected tier:** CONFIRMED

**Exact reasons:**

- Matched subject identity: DEF Ship Management Pte. Ltd.
- Same authority: Enforcement Agency C
- Publication date order: 2025-08-12 < 2026-10-24
- Same legal order: Vessel Services Order 2024
- Shared matter words: bunkering, circumvention, provider
- Explicit earlier-report reference: Business News A on 2025-08-12

### 38. L-017 — SUB-004

**What the tool must say:** Show ART-027 -> ART-010 as SUGGESTED with the exact text-grounded reasons. Analyst must confirm or reject; do not change findings or status.

**Why:** Relationship evidence is the matched identity, increasing publication date, explicit authority, and matching legal order or sufficiently specific shared matter wording. Generic overlap is only a suggestion and requires human review.

**Article evidence:** `articles/ART-010.md:12` (2026-10-25)

> According to Shipping News B on 2026-10-25, the Customs Agency B is investigating Ravi Selvam, 46, a commodity trader, on suspicion of sanctions evasion through fuel cargo transhipment at Orlath free port.

**Article evidence:** `articles/ART-027.md:12` (2026-10-26)

> According to Shipping News B, the Customs Agency B is investigating Ravi Selvam, 46, a commodity trader, on suspicion of sanctions evasion through fuel cargo transhipment at Orlath free port.

**Expected tier:** SUGGESTED

**Exact reasons:**

- Matched subject identity: Ravi Selvam
- Same authority: Customs Agency B
- Publication date order: 2026-10-25 < 2026-10-26
- Shared matter words: cargo, commodity, evasion, free, fuel, orlath, port, trader, transhipment

ART-004 and ART-026 remain excluded on age, role and employer. ART-017 remains unlinked: no supplied development for its Maritime Agency D quay inquiry; status unknown. Suggestions do not change counts, summary or case status.
