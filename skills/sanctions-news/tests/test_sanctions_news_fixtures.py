"""Check the invented sanctions-news answer key, not a researcher implementation.

Standard library only. Read local fixtures; never call a model or the network.
"""

from datetime import date
import json
import hashlib
from pathlib import Path
import re
import unittest


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
STATUS_VALUES = {
    "execution": {"completed", "failed", "not attempted"},
    "result": {"finding", "no finding", "unavailable"},
    "freshness": {"current", "stale"},
}
REQUIRED_TRAPS = {
    "same_name_different_person", "old_story_cleared", "failed_source",
    "stale_source", "nothing_found_with_gaps",
}
READER_INSTRUCTIONS = (
    "search subject", "readers must", "keep that", "cannot establish", "unrelated to",
)
RISK_WORDS = re.compile(
    r"alleg|accus|sanction|restrict|investigat|complaint|inquiry|cleared|open|launder|fraud",
    re.IGNORECASE,
)
# Key: (article id, exact sentence). Value: one-line reason it is not a finding.
# Never allow an entire article or a substring of a sentence.
RISK_SENTENCE_ALLOW_LIST = {
    ("ART-003", "ABC Components Pte. Ltd., a distributor of electronic components, opened a training room on 2026-10-25."):
        "Opened describes a training-room opening, not an open sanctions case.",
}


def body_sentences(body):
    """Independent risk guard: protect suffix dots, never import the researcher."""
    # Mask by position, then slice the original text so evidence cannot change.
    masked = list(body)
    flags = re.IGNORECASE if body.isupper() else 0
    for match in re.finditer(
            r"\b(?:Pte|Co)\.(?=\s*(?:,\s*)?Ltd\.)|\bLtd\.(?=\s+[a-z]|[,;:])", body, flags):
        masked[match.end() - 1] = " "
    result = []
    for match in re.finditer(r"[^.!?]+(?:[.!?]+|$)", "".join(masked)):
        sentence = " ".join(body[match.start():match.end()].split())
        if sentence:
            result.append(sentence)
    return result


def unkeyed_risk_sentences(body, names, quotes, allowed=()):
    """Require whole-sentence evidence; an approved substring is not enough."""
    return [s for s in body_sentences(body)
            if any(name.casefold() in s.casefold() for name in names)
            and RISK_WORDS.search(s) and s not in quotes and s not in allowed]


def unique_object(pairs):
    """Reject repeated JSON keys instead of silently keeping the last value."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Repeated field: " + key)
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def read_article(path):
    """Read this fixture's JSON-valued YAML subset, not arbitrary YAML."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("Missing opening front matter: " + path.name)
    end = lines.index("---", 1)
    pairs = []
    for line in lines[1:end]:
        key, value = line.split(": ", 1)
        pairs.append((key, json.loads(value)))
    return unique_object(pairs), "\n".join(lines[end + 1:])


def quote_references(node):
    """Include findings, clearing decisions and every nested trap quote."""
    if isinstance(node, dict):
        if "quote" in node:
            yield node
        for value in node.values():
            yield from quote_references(value)
    elif isinstance(node, list):
        for value in node:
            yield from quote_references(value)


class SanctionsNewsFixturesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.subject_data = read_json(FIXTURES / "subjects.json")
        cls.source_data = read_json(FIXTURES / "sources.json")
        cls.key = read_json(FIXTURES / "answer-key.json")
        cls.subjects = {s["id"]: s for s in cls.subject_data["subjects"]}
        cls.sources = {s["id"]: s for s in cls.source_data["sources"]}
        cls.expected = {s["subject_id"]: s for s in cls.key["subjects"]}
        cls.articles = {}
        for path in sorted((FIXTURES / "articles").glob("*.md")):
            meta, body = read_article(path)
            if meta["id"] in cls.articles:
                raise ValueError("Repeated article id: " + meta["id"])
            cls.articles[meta["id"]] = {"meta": meta, "body": body, "filename": path.stem}
        cls.review = (FIXTURES / "ANSWER-KEY-REVIEW.md").read_text(encoding="utf-8")

    def assert_status(self, status):
        for field, allowed in STATUS_VALUES.items():
            self.assertIn(field, status)
            self.assertIn(status[field], allowed, (field, status))
        date.fromisoformat(status["as_of"])
        if status["execution"] != "completed":
            self.assertEqual(status["result"], "unavailable")
        else:
            self.assertNotEqual(status["result"], "unavailable")

    def findings(self, expected):
        return expected["expected_findings"] + [
            row for row in self.key["round3_rows"]
            if row["subject_id"] == expected["subject_id"] and row["kind"] == "finding"]

    def traps(self, kind):
        return [(expected, trap) for expected in self.key["subjects"]
                for trap in expected["traps"] if trap["type"] == kind]

    def test_subject_count_identifiers_and_unique_ids(self):
        records = self.subject_data["subjects"]
        self.assertTrue(4 <= len(records) <= 6)
        self.assertEqual(len(self.subjects), len(records))
        self.assertEqual(len({s["name"] for s in records}), len(records))
        self.assertEqual({s["type"] for s in records}, {"person", "company"})
        for subject in records:
            with self.subTest(subject=subject["id"]):
                self.assertTrue(subject["id"])
                self.assertTrue(subject["name"])
                if subject["type"] == "person":
                    date.fromisoformat(subject["date_of_birth"])
                    self.assertIsNone(subject.get("nationality"))

                else:
                    self.assertTrue(subject["registration_number"].startswith("SYN-SG-"))
                    self.assertNotIn("country", subject)
                self.assertTrue(subject['profile'])
                self.assertNotIn('city', subject)
                self.assertNotIn('district', subject)

    def test_sources_have_separate_allowed_statuses(self):
        records = self.source_data["sources"]
        self.assertTrue(3 <= len(records) <= 5)
        self.assertEqual(len(self.sources), len(records))
        self.assertEqual(len({s["name"] for s in records}), len(records))
        for source in records:
            with self.subTest(source=source["id"]):
                self.assertTrue(source["name"])
                self.assertTrue(source["coverage"])
                self.assert_status(source)
        self.assertTrue(any(s.get("execution") == "failed" for s in records))
        self.assertTrue(any(s.get("freshness") == "stale" for s in records))

    def test_sample_freshness_limit_is_365_days(self):
        self.assertEqual(self.source_data["freshness_rule"]["max_age_days"], 365)

    def test_freshness_uses_snapshot_date_not_article_age(self):
        run_date = date.fromisoformat(self.source_data["run_date"])
        self.assertEqual(self.key["run_date"], self.source_data["run_date"])
        limit = self.source_data["freshness_rule"]["max_age_days"]
        self.assertEqual(limit, 365)  # Invented sample rule, not a regulatory limit.
        for source in self.sources.values():
            age = (run_date - date.fromisoformat(source["as_of"])).days
            self.assertGreaterEqual(age, 0)
            self.assertEqual(source["freshness"], "stale" if age > limit else "current")
        self.assertTrue(any(
            (run_date - date.fromisoformat(a["meta"]["date"])).days > limit
            and self.sources[a["meta"]["source_id"]]["freshness"] == "current"
            for a in self.articles.values()))

    def test_twenty_nine_articles_have_valid_front_matter_and_references(self):
        self.assertEqual(len(self.articles), 29)
        for article_id, article in self.articles.items():
            with self.subTest(article=article_id):
                meta = article["meta"]
                self.assertEqual(set(meta), {"id", "source_id", "date", "headline", "subject_ids",
                                             "part_in_story", "stage", "event_id"})
                self.assertEqual(article_id, article["filename"])
                self.assertIn(meta["source_id"], self.sources)
                source = self.sources[meta["source_id"]]
                self.assertEqual(source["execution"], "completed")
                self.assertLessEqual(date.fromisoformat(meta["date"]), date.fromisoformat(source["as_of"]))
                self.assertIsInstance(meta["headline"], str)
                self.assertTrue(meta["headline"].strip())
                self.assertIsInstance(meta["subject_ids"], list)
                self.assertTrue(meta["subject_ids"])
                self.assertEqual(len(meta["subject_ids"]), len(set(meta["subject_ids"])))
                self.assertLessEqual(set(meta["subject_ids"]), set(self.subjects))
                mentioned = {sid for sid, s in self.subjects.items() if s["name"] in article["body"]}
                self.assertEqual(set(meta["subject_ids"]), mentioned)

    def test_article_bodies_have_no_reader_instructions(self):
        leaks = [(aid, phrase) for aid, article in self.articles.items()
                 for phrase in READER_INSTRUCTIONS if phrase in article["body"].casefold()]
        self.assertEqual(leaks, [], "Article bodies must report news, not supply answers")

    def test_every_named_risk_sentence_is_keyed_or_explicitly_allowed(self):
        used = set()
        for aid, article in self.articles.items():
            quotes = {r["quote"] for r in quote_references(self.key) if r["article_id"] == aid}
            allowed = set()
            for (article_id, sentence), reason in RISK_SENTENCE_ALLOW_LIST.items():
                self.assertTrue(reason.strip())
                self.assertNotIn("\n", reason)
                if article_id == aid:
                    self.assertIn(sentence, body_sentences(article["body"]))
                    self.assertTrue(RISK_WORDS.search(sentence))
                    self.assertTrue(any(s["name"].casefold() in sentence.casefold()
                                        for s in self.subjects.values()))
                    allowed.add(sentence)
                    used.add((aid, sentence))
            with self.subTest(article=aid):
                self.assertEqual(unkeyed_risk_sentences(
                    article["body"], [s["name"] for s in self.subjects.values()], quotes, allowed), [])
        self.assertEqual(used, set(RISK_SENTENCE_ALLOW_LIST), "Remove stale allow-list entries")

    def test_risk_guard_rejects_new_sentences_and_extensions_of_quotes(self):
        sentence = "A fictional regulator alleged GHI Family Imports Pte. Ltd. laundered funds on 2026-10-27."
        body = self.articles["ART-013"]["body"]
        names = [s["name"] for s in self.subjects.values()]
        quotes = {r["quote"] for r in quote_references(self.key) if r["article_id"] == "ART-013"}
        self.assertEqual(unkeyed_risk_sentences(body, names, quotes), [])
        for separator in ("\n", " ", ""):
            with self.subTest(separator=separator):
                self.assertEqual(unkeyed_risk_sentences(body.rstrip() + separator + sentence,
                                                       names, quotes), [sentence])
        self.assertEqual(unkeyed_risk_sentences(sentence.upper(), names, quotes), [sentence.upper()])
        quote = next(iter(quotes))
        extended = quote[:-1] + " and faced sanctions."
        self.assertEqual(unkeyed_risk_sentences(extended, names, quotes), [extended])
        self.assertEqual(unkeyed_risk_sentences(sentence, names, quotes, {sentence}), [])

    def test_independent_guard_preserves_dotted_suffix_and_real_sentence_end(self):
        for suffix in ("Pte. Ltd.", "Co., Ltd."):
            first = "ABC " + suffix + " faced a sanctions inquiry."
            second = "The notice named ABC " + suffix
            third = "Another sentence follows."
            self.assertEqual(body_sentences(first + " " + second + " " + third), [first, second, third])
            self.assertEqual(unkeyed_risk_sentences(first, ["ABC " + suffix], set()), [first])
            self.assertEqual(unkeyed_risk_sentences(first, ["ABC " + suffix], {first}), [])

    def test_profiles_and_placeholder_notice_replace_places(self):
        self.assertTrue(all(s['profile'] for s in self.subjects.values()))
        notice = self.subject_data["data_notice"]
        self.assertIn('local in style only', notice)
        self.assertIn('All names are placeholders', notice)

    def test_fixtures_exclude_real_names_and_places(self):
        output = "\n".join(path.read_text(encoding="utf-8") for path in FIXTURES.rglob("*") if path.is_file())
        encoded = ("4d4153", "4d6f6e657461727920417574686f72697479", "4f464143", "4f465349", "554e",
                   "53696e6761706f7265", "53696e6761706f726520437573746f6d73",
                   "53696e6761706f726520506f6c696365", "436f6d6d65726369616c2041666661697273", "41435241",
                   "52657574657273", "537472616974732054696d6573", "427573696e6573732054696d6573",
                   "426c6f6f6d62657267", "4d616c6179736961", "496e646f6e65736961", "4a6f686f72",
                   "4a75726f6e67", "576f6f646c616e6473", "54756173", "50617369722050616e6a616e67")
        for token in encoded:
            term = bytes.fromhex(token).decode("ascii")
            self.assertNotRegex(output, r"(?i)(?<!\w)" + re.escape(term) + r"(?!\w)")

    def test_articles_use_news_identifiers_and_only_sanctions_risk(self):
        for aid, article in self.articles.items():
            with self.subTest(article=aid):
                self.assertNotRegex(article["body"], r"SYN-|\bborn\b|date of birth|national of")
                self.assertNotRegex(article["body"].casefold(),
                                    r"fraud|launder|complaint|invoice|tender|deposit")
                for sid in article["meta"]["subject_ids"]:
                    subject = self.subjects[sid]
                    if subject["type"] == "company":
                        self.assertIn(subject["profile"], article["body"])

    def test_answer_key_covers_every_subject_once(self):
        self.assertEqual(len(self.expected), len(self.key["subjects"]))
        self.assertEqual(set(self.expected), set(self.subjects))
        for expected in self.key["subjects"]:
            self.assertTrue(expected["summary"])
            self.assertTrue(expected["not_covered"])
            self.assertIsInstance(expected["expected_findings"], list)
            self.assertIsInstance(expected["traps"], list)

    def test_every_quote_matches_named_article_body_and_date_exactly(self):
        references = list(quote_references(self.key))
        self.assertTrue(references)
        for reference in references:
            with self.subTest(article=reference["article_id"], quote=reference["quote"]):
                self.assertIn(reference["article_id"], self.articles)
                article = self.articles[reference["article_id"]]
                self.assertIsInstance(reference["quote"], str)
                self.assertTrue(reference["quote"].strip())
                self.assertIn(reference["quote"], article["body"])
                self.assertEqual(reference["date"], article["meta"]["date"])

    def test_findings_have_types_states_and_matching_subjects(self):
        finding_ids = []
        seen_types = set()
        for expected in self.key["subjects"]:
            for finding in self.findings(expected):
                with self.subTest(finding=finding["id"]):
                    finding_ids.append(finding["id"])
                    seen_types.add(finding["type"])
                    self.assertEqual(finding["type"], "sanctions")
                    self.assertIn(finding["state"], {
                        "reported restriction", "reported settlement", "reported delisting", "allegation unresolved", "cleared", "historical status unknown"})
                    self.assertTrue(finding["must_say"])
                    self.assertTrue(finding["why"])
                    for reference in quote_references(finding):
                        self.assertIn(expected["subject_id"], self.articles[reference["article_id"]]["meta"]["subject_ids"])
        self.assertTrue(finding_ids)
        self.assertEqual(len(finding_ids), len(set(finding_ids)))
        self.assertEqual(seen_types, {"sanctions"})

    def test_per_subject_statuses_cover_all_sources_without_hiding_gaps(self):
        for expected in self.key["subjects"]:
            statuses = expected["expected_source_statuses"]
            self.assertEqual(len(statuses), len(self.sources))
            self.assertEqual({s["source_id"] for s in statuses}, set(self.sources))
            for status in statuses:
                with self.subTest(subject=expected["subject_id"], source=status["source_id"]):
                    self.assert_status(status)
                    source = self.sources[status["source_id"]]
                    for field in ("execution", "freshness", "as_of"):
                        self.assertEqual(status[field], source[field])
                    checked = [aid for aid, a in self.articles.items() if a["meta"]["source_id"] == source["id"]]
                    self.assertEqual(sorted(status["article_ids_checked"]), sorted(checked))
                    self.assertTrue(status["coverage"])
                    findings = [f for f in self.findings(expected)
                                if self.articles[f["article_id"]]["meta"]["source_id"] == source["id"]]
                    if status["execution"] == "completed":
                        self.assertEqual(status["result"], "finding" if findings else "no finding")
            gap_ids = {g["source_id"] for g in expected["not_covered"] if g["source_id"] is not None}
            required_gaps = {s["id"] for s in self.sources.values()
                             if s["execution"] != "completed" or s["freshness"] == "stale"}
            self.assertEqual(gap_ids, required_gaps)
            for gap in expected["not_covered"]:
                self.assertTrue(gap["reason"])
            self.assertTrue(any(g["source_id"] is None for g in expected["not_covered"]))

    def test_source_level_results_match_findings_for_any_subject(self):
        finding_sources = {self.articles[f["article_id"]]["meta"]["source_id"]
                           for s in self.key["subjects"] for f in self.findings(s)}
        for source in self.sources.values():
            if source["execution"] == "completed":
                self.assertEqual(source["result"], "finding" if source["id"] in finding_sources else "no finding")

    def test_required_traps_exist_with_unique_ids_and_valid_references(self):
        traps = [t for s in self.key["subjects"] for t in s["traps"]]
        self.assertLessEqual(REQUIRED_TRAPS, {t["type"] for t in traps})
        self.assertEqual(len(traps), len({t["id"] for t in traps}))
        for expected in self.key["subjects"]:
            for trap in expected["traps"]:
                self.assertTrue(trap["must_say"])
                self.assertTrue(trap["why"])
                if "source_id" in trap:
                    self.assertIn(trap["source_id"], self.sources)
                for reference in quote_references(trap):
                    self.assertIn(expected["subject_id"], self.articles[reference["article_id"]]["meta"]["subject_ids"])

    def test_namesake_differs_by_reported_role_employer_and_age_not_birth_date(self):
        for expected, trap in self.traps("same_name_different_person"):
            subject = self.subjects[expected["subject_id"]]
            other = trap["other_person"]
            self.assertEqual(set(other), {"name", "role", "employer", "age"})
            self.assertEqual(other["name"], subject["name"])
            for evidence in trap["evidence"]:
                for field in ("role", "employer"):
                    self.assertNotEqual(other[field], subject[field])
                    self.assertIn(other[field], evidence["quote"])
                    self.assertNotIn(subject[field], evidence["quote"])
                    for finding in expected["expected_findings"]:
                        self.assertIn(subject[field], finding["quote"])
                born = date.fromisoformat(subject['date_of_birth'])
                day = date.fromisoformat(evidence['date'])
                age = str(day.year - born.year - ((day.month, day.day) < (born.month, born.day)))
                self.assertNotEqual(other['age'], age)
                self.assertIn(', ' + other['age'] + ',', evidence['quote'])
                self.assertNotIn(evidence["article_id"], {f["article_id"] for f in expected["expected_findings"]})

    def test_old_allegation_is_retained_with_later_clearing_proof(self):
        for expected, trap in self.traps("old_story_cleared"):
            old, newer = trap["evidence"]
            self.assertLess(date.fromisoformat(old["date"]), date.fromisoformat(newer["date"]))
            self.assertIn("cleared", newer["quote"])
            self.assertIn("closed", newer["quote"])
            self.assertIn(old["date"], self.articles[newer["article_id"]]["body"])
            subject = self.subjects[expected["subject_id"]]
            for reference in (old, newer):
                self.assertIn(subject["name"], reference["quote"])
                self.assertIn(subject["profile"], reference["quote"])
                self.assertIn("Vessel Services Order 2024", reference["quote"])
            findings = [f for f in expected["expected_findings"] if f["article_id"] == old["article_id"]]
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["state"], "cleared")
            self.assertEqual(findings[0]["resolution"], newer)

    def test_failed_and_unattempted_sources_have_no_invented_evidence(self):
        for source in self.sources.values():
            if source["execution"] != "completed":
                self.assertEqual(source["result"], "unavailable")
                self.assertFalse(any(a["meta"]["source_id"] == source["id"] for a in self.articles.values()))
        for kind, execution in (("failed_source", "failed"), ("not_attempted_source", "not attempted")):
            self.assertTrue(self.traps(kind))
            for expected, trap in self.traps(kind):
                source = self.sources[trap["source_id"]]
                self.assertEqual(source["execution"], execution)
                self.assertEqual(trap["evidence"], [])
                status = next(s for s in expected["expected_source_statuses"] if s["source_id"] == source["id"])
                self.assertEqual(status["result"], "unavailable")

    def test_stale_source_keeps_history_without_claiming_current_status(self):
        for expected, trap in self.traps("stale_source"):
            source = self.sources[trap["source_id"]]
            self.assertEqual(source["freshness"], "stale")
            self.assertEqual(source["execution"], "completed")
            findings = [f for f in expected["expected_findings"]
                        if self.articles[f["article_id"]]["meta"]["source_id"] == source["id"]]
            self.assertTrue(findings)
            for finding in findings:
                self.assertEqual(finding["state"], "historical status unknown")
                self.assertIn(source["as_of"], finding["must_say"])
                self.assertIn("No follow-up was found in any supplied source", finding["must_say"])
                self.assertIn("status unknown", finding["must_say"])
                # BH row 9: silence in the supplied set, not a statement in the news.
                for article in self.articles.values():
                    self.assertNotRegex(article["body"].casefold(),
                                        r"archive|snapshot|no decision was available|no follow-up|reporting stopped")
                    if article["meta"]["date"] > finding["date"]:
                        self.assertNotRegex(article["body"], r"Nivren quay|Maritime Agency D")

    def test_planned_freshness_is_not_read_coverage_and_open_findings_are_not_history(self):
        for expected, trap in self.traps("failed_source") + self.traps("not_attempted_source"):
            self.assertIn("current (planned date only, nothing read)", trap["must_say"])
        for subject_id in ("SUB-001", "SUB-002"):
            status = self.expected[subject_id]["expected_source_statuses"][0]
            self.assertEqual(status["source_id"], "SRC-001")
            self.assertIn("Current sanctions", status["coverage"])
            self.assertNotIn("only as history", status["coverage"])

    def test_nothing_found_is_limited_to_completed_articles_with_gaps(self):
        for expected, trap in self.traps("nothing_found_with_gaps"):
            self.assertEqual(expected["expected_findings"], [])
            completed = [s for s in expected["expected_source_statuses"] if s["execution"] == "completed"]
            self.assertTrue(completed)
            self.assertTrue(all(s["result"] == "no finding" for s in completed))
            checked = {aid for s in completed for aid in s["article_ids_checked"]}
            self.assertEqual(checked, set(self.articles))
            mentions = {aid for aid, a in self.articles.items() if expected["subject_id"] in a["meta"]["subject_ids"]}
            self.assertEqual({e["article_id"] for e in trap["evidence"]}, mentions)
            self.assertIn("not a clearance", expected["summary"])
            for status in expected["expected_source_statuses"]:
                if status["execution"] != "completed" or status["freshness"] == "stale":
                    self.assertIn(status["source_id"], trap["must_say"])

    def test_review_table_has_one_exact_row_per_finding_and_trap(self):
        self.assertEqual(sum(line.startswith("|---") for line in self.review.splitlines()), 1)
        rows = [line for line in self.review.splitlines() if line.startswith("| ")]
        self.assertEqual(rows[0], "| Subject | What the tool must say | The quote | Why it is right |")
        rows = [line.split(" | ") for line in rows[1:]]
        items = [(s, item) for s in self.key["subjects"] for item in s["expected_findings"] + s["traps"]]
        self.assertEqual(len(rows), len(items))
        for (expected, item), row in zip(items, rows):
            self.assertEqual(len(row), 4)
            self.assertEqual(row[0], "| " + self.subjects[expected["subject_id"]]["name"] + " (" + expected["subject_id"] + ")")
            self.assertEqual(row[1], item["id"] + ": " + item["must_say"])
            self.assertEqual(row[3], item["why"] + " |")
            references = list(quote_references(item))
            if not references:
                self.assertEqual(row[2], "No article or quote: this source was not read.")
            for reference in references:
                self.assertIn(reference["article_id"] + " (" + reference["date"] + "): \"" + reference["quote"] + "\"", row[2])

    def test_original_twenty_article_bytes_and_source_plan_stay_frozen(self):
        expected = {'ART-001': 'b784974be647dfcd2784703f7304838073e62d85f4896c2b2d194455a1e38cbf',
         'ART-002': '62b80a88e6011f8478c19de1cc484b504f7d184d9f83fc46ead6f2bf296b4097',
         'ART-003': '2125d0c1809d12ad7a3a2486cd0d7ac2c47eccc2f7dcdd5a6995d1881ee9c5e7',
         'ART-004': '9bd4a9c0e40d0e70c4b062201b9bddae9d8a0d5d94f3010b33205ed31743ce58',
         'ART-005': '6fcf5d7999f52ce12692a6bb827f84ed5359d63130566836a932557660f4d0ca',
         'ART-006': 'c184c2dcdcc404d669773eeaca154b88ba199b548dd5b6ad27ba32ce3d679f70',
         'ART-007': '8695004ddd6918edd553a5a97c63ba068eb79dd0522d74a79e7425eba10ede62',
         'ART-008': '69b54bc3f3fb9e5a121567e864961e27f83263d98d67bf5e6d59cfc55f904b20',
         'ART-009': '9e4ef11a00e2d021ef0660c52b99624dc05d5bdf30c36fea9c5b569d0c2adcb0',
         'ART-010': '76ba73a6baac5adeb504ff28efda63810d1477160577ab7ffc88ccc6000d9df5',
         'ART-011': '801fe16d408984e68a46267dfa5545530d23b88f79378e30e54f5e795cfc4d09',
         'ART-012': '8cf065171361d91d68e072acc49b83d46fa17892266d27d5e84453e6b0b247e6',
         'ART-013': '02b0259902dcb852e78ad1656969b74e1d90eb94f51a5f77b877df84e766b4d3',
         'ART-014': '3c53a8c0bcbd0aa7605f1ec3915fd21bfdaf33b09a39d0c315a82f4ba3a89008',
         'ART-015': '9c6ce313e0615a165809a9903c5824083699ef88671d148ebaee07ee58155283',
         'ART-016': 'bebb0b75012c99e715a84d23ce08925d9c308346971b63d3b316341d1243b9bb',
         'ART-017': '56f7025b0dd85af713f8c27156a608f829711ecab0afda49da7e59e3904145e8',
         'ART-018': '7c9747b33ea37c342f5abbe8b7163b49da23b6bbb6e6036228a51d0ecee0351c',
         'ART-019': '3fa2a4cd2bb3786aef55941de1dbfc8d028bf0539c024db8eab287a87e861160',
         'ART-020': 'c75f06a9ac1cf38ff96dee567fb49fe2b293c209f7a5d737b06aae77ab1dd430'}
        for aid, digest in expected.items():
            with self.subTest(article=aid):
                self.assertEqual(hashlib.sha256((FIXTURES / "articles" / (aid + ".md")).read_bytes()).hexdigest(), digest)
        self.assertEqual(hashlib.sha256((FIXTURES / "sources.json").read_bytes()).hexdigest(),
                         "3d86843afd49c886be38b3f951c3a6d554ec2cd79226aa23a20b92236ab5361d")

    def test_original_twelve_answer_objects_and_global_order_stay_frozen(self):
        original = [(subject["subject_id"], subject["expected_findings"], subject["traps"])
                    for subject in self.key["subjects"]]
        digest = hashlib.sha256(json.dumps(original, sort_keys=True).encode()).hexdigest()
        self.assertEqual(digest, "d6f4479dac6613b27f98b27a3e12f5f3c3e1faf6d0af160ca483dbd73d941406")
        self.assertEqual(sum(len(s["expected_findings"]) + len(s["traps"])
                             for s in self.key["subjects"]), 12)

    def test_round3_additive_rows_have_unique_ids_and_line_evidence(self):
        rows = self.key["round3_rows"]
        self.assertEqual(len(rows), 26)
        original_ids = {item["id"] for subject in self.key["subjects"]
                        for item in subject["expected_findings"] + subject["traps"]}
        self.assertEqual(len({row["id"] for row in rows}), len(rows))
        self.assertFalse(original_ids & {row["id"] for row in rows})
        self.assertEqual(sum(row["kind"] == "finding" for row in rows), 8)
        self.assertEqual(sum(row["kind"] == "trap" for row in rows), 1)
        self.assertEqual(sum(row["kind"] == "link" for row in rows), 17)
        for number, row in enumerate(rows, 13):
            with self.subTest(row=row["id"]):
                self.assertIn(row["subject_id"], self.subjects)
                self.assertIn(row["kind"], {"finding", "trap", "link"})
                self.assertTrue(row["must_say"])
                self.assertTrue(row["why"])
                section = self.review.split("### " + str(number) + ". " + row["id"], 1)[1].split("\n### ", 1)[0]
                self.assertIn(row["must_say"], section)
                self.assertIn(row["why"], section)
                for ref in quote_references(row):
                    self.assertIn(ref["article_id"] + ".md:12", section)
                    self.assertIn(ref["quote"], section)

    def test_round3_texts_supply_relationship_evidence_without_backreferences(self):
        new = [self.articles["ART-%03d" % n] for n in range(21, 30)]
        for article in new:
            body = article["body"]
            self.assertNotRegex(body, r"first reported|earlier report|previous report|ART-[0-9]|202[0-9]-[0-9]{2}-[0-9]{2}")
            self.assertNotRegex(body.casefold(), r"\b(?:denied|admitted|convicted|exonerated)\b")
            self.assertIn("According to ", body.splitlines()[1])
        for aid in ("ART-022", "ART-028"):
            article = self.articles[aid]
            self.assertIn("agreed to settle potential civil liability for apparent violations", article["body"])
            self.assertEqual(article["meta"]["part_in_story"], "not stated")
            self.assertEqual(article["meta"]["stage"], "settlement")
        routing, decoy = self.articles["ART-021"], self.articles["ART-023"]
        self.assertIn("Customs Agency A", routing["body"])
        self.assertIn("Customs Agency A", decoy["body"])
        self.assertIn("Dual-Use Routing Order 2025", routing["body"])
        self.assertIn("Bonded Storage Order 2026", decoy["body"])
        self.assertIn("false inventory descriptions", decoy["body"])
        self.assertNotEqual(routing["meta"]["event_id"], decoy["meta"]["event_id"])
        self.assertNotIn("Maritime Agency D", "\n".join(a["body"] for a in new))

    def test_round3_expected_links_are_exact_chronological_pairs_not_event_id_matches(self):
        for row in self.key["relationship_checks"]:
            self.assertTrue(row["expected_links"])
            self.assertEqual([{field: link[field] for field in ("article_id", "to_article_id", "tier")}
                              for link in row["expected_links"]], row["reviewed_pair_tiers"])
            if row["subject_id"] == "SUB-001":
                self.assertEqual({(d["article_id"], d["to_article_id"], d["decision"])
                                  for d in row["expected_human_decisions"]},
                                 {("ART-023", aid, "Reject") for aid in ("ART-002", "ART-021", "ART-022")})
            pairs = set()
            for link in row["expected_links"]:
                self.assertEqual(set(link), {"article_id", "to_article_id", "tier", "reasons"})
                a, b = self.articles[link["article_id"]], self.articles[link["to_article_id"]]
                self.assertLess(b["meta"]["date"], a["meta"]["date"])
                self.assertIn(row["subject_id"], a["meta"]["subject_ids"])
                self.assertIn(row["subject_id"], b["meta"]["subject_ids"])
                self.assertIn(link["tier"], {"SUGGESTED", "CONFIRMED"})
                self.assertTrue(link["reasons"])
                self.assertTrue(all(isinstance(reason, str) and reason for reason in link["reasons"]))
                self.assertFalse({link["article_id"], link["to_article_id"]} & {"ART-004", "ART-026", "ART-017"})
                pair = (link["article_id"], link["to_article_id"])
                self.assertNotIn(pair, pairs)
                pairs.add(pair)
                if link["article_id"] == "ART-023":
                    self.assertEqual(link["tier"], "SUGGESTED")
        grouped = [link for row in self.key['relationship_checks'] for link in row['expected_links']]
        individual = [row['expected_link'] for row in self.key['round3_rows'] if row['kind'] == 'link']
        self.assertEqual(grouped, individual)
        decoys = [row for row in self.key['round3_rows']
                  if row.get('expected_link', {}).get('article_id') == 'ART-023']
        self.assertEqual(len(decoys), 3)
        for row in decoys:
            self.assertEqual(row['expected_human_decision']['decision'], 'Reject')
            self.assertIn('Different Bonded Storage Order 2026', row['expected_human_decision']['reason'])

    def test_synthetic_notice_is_present_in_all_data_files(self):
        for data in (self.subject_data, self.source_data, self.key):
            self.assertIn("Invented for an offline sample.", data["data_notice"])
            self.assertIn("All names are placeholders", data["data_notice"])
            self.assertIn("local in style only", data["data_notice"])
        for article in self.articles.values():
            self.assertIn("Names are placeholders and events are invented. Local in style only; no real place names are used.",
                          article["body"])
        self.assertIn("Synthetic sample only", self.review)


if __name__ == "__main__":
    unittest.main()
