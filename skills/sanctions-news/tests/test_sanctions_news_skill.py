"""Offline proof on invented news only. No model, network or new packages."""

import copy
from datetime import date, timedelta
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
SCRIPTS = ROOT / "scripts"
SPEC = importlib.util.spec_from_file_location("sanctions_research", SCRIPTS / "research.py")
assert SPEC is not None and SPEC.loader is not None
research = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(research)
# Load the checker without changing production imports or global test paths.
with patch.dict(sys.modules, {"research": research}):
    SPEC = importlib.util.spec_from_file_location("sanctions_answer_check", SCRIPTS / "check_answer_key.py")
    assert SPEC is not None and SPEC.loader is not None
    checker = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(checker)


class SanctionsNewsSkillTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.subjects = research.read_json(FIXTURES / "subjects.json")["subjects"]
        cls.key = research.read_json(FIXTURES / "answer-key.json")
        cls.reports = {s["id"]: research.research(s["id"], FIXTURES) for s in cls.subjects}
        cls.markdown = {sid: research.render(report) for sid, report in cls.reports.items()}
        cls.output = "\n".join(json.dumps(r) + cls.markdown[sid] for sid, r in cls.reports.items())

    def copy_fixtures(self, folder, original_only=False):
        target = Path(folder) / "fixtures"
        ignored = ["answer-key.json", "ANSWER-KEY-REVIEW.md"]
        if original_only:
            ignored += ["ART-02[1-9].md"]
        shutil.copytree(FIXTURES, target, ignore=shutil.ignore_patterns(*ignored))
        return target

    def mutate_article(self, fixtures, article_id, old, new):
        path = fixtures / "articles" / (article_id + ".md")
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new), encoding="utf-8")

    def name_only_report(self, quote=None):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = self.copy_fixtures(tmp, original_only=True)
            if quote is None:
                self.mutate_article(fixtures, "ART-006",
                                    ", 39, nominee director at JKL Trading Pte. Ltd.,", "")
            else:
                article = research.read_article(fixtures / "articles" / "ART-006.md")
                self.mutate_article(fixtures, "ART-006", research.sentences(article["body"])[0], quote)
            return research.research("SUB-002", fixtures)

    def test_original_plus_round3_cli_reproduction(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = checker.evaluate(FIXTURES, Path(tmp))
        self.assertEqual(len(rows), 12 + len(self.key["round3_rows"]))
        original = [item["id"] for subject in self.key["subjects"]
                    for item in subject["expected_findings"] + subject["traps"]]
        self.assertEqual([row["row"] for row in rows[:12]], original)
        self.assertEqual([row["row"] for row in rows[12:]],
                         [row["id"] for row in self.key["round3_rows"]])
        self.assertEqual([r for r in rows if r["status"] != "PASS"], [])

    def test_check_answer_key_cli_prints_full_row_table(self):
        proc = subprocess.run([sys.executable, str(SCRIPTS / "check_answer_key.py")],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        count = 12 + len(self.key["round3_rows"])
        self.assertIn(str(count) + "/" + str(count) + " rows passed", proc.stdout)
        self.assertEqual(len(re.findall(r"^[FTL]-\d{3}.*PASS$", proc.stdout, re.M)), count)

    def test_research_does_not_read_answer_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = self.copy_fixtures(tmp)
            self.assertEqual(research.research("SUB-004", fixtures), self.reports["SUB-004"])

    def test_all_findings_have_exact_grounded_evidence(self):
        for report in self.reports.values():
            for finding in report["findings"]:
                with self.subTest(article=finding["article_id"]):
                    article = research.read_article(FIXTURES / finding["fixture_file"])
                    self.assertIn(finding["quote"], article["body"])
                    self.assertEqual(finding["date"], article["date"])
                    self.assertEqual(finding["source_id"], article["source_id"])
                    self.assertEqual(finding["type"], "sanctions")
                    self.assertIn("name", finding["identity_check"]["matched_fields"])

    def test_no_registration_number_or_field(self):
        self.assertNotIn("registration_number", self.output)
        self.assertNotRegex(self.output, r"registration number|SYN-[A-Z]+-\d+")
        for subject in self.subjects:
            if "registration_number" in subject:
                self.assertNotIn(subject["registration_number"], self.output)

    def test_no_birth_date_or_field(self):
        self.assertNotRegex(self.output.casefold(), r"date_of_birth|date of birth|\bdob\b|\bborn\b")
        for subject in self.subjects:
            if "date_of_birth" in subject:
                self.assertNotIn(subject["date_of_birth"], self.output)

    def test_no_nationality_line(self):
        self.assertNotRegex(self.output.casefold(), r"nationality|national of")

    def test_no_invented_denial(self):
        self.assertNotRegex(self.output.casefold(), r"\bdenied\b")

    def test_no_clear_words_for_nothing_found(self):
        output = json.dumps(self.reports["SUB-005"]) + self.markdown["SUB-005"]
        self.assertIn("This is not a clearance.", output)
        self.assertNotRegex(output.replace("This is not a clearance.", ""),
                            r"(?i)\b(?:clear|cleared|clearance)\b")
        expected = next(s for s in self.key["subjects"] if s["subject_id"] == "SUB-005")
        self.assertEqual(self.reports["SUB-005"]["summary"], expected["summary"])

    def test_no_prohibited_real_names_from_owner_brief(self):
        # Encoded deny-list tokens, not names used as invented test data.
        encoded = (
            "4d4153", "4d6f6e657461727920417574686f72697479", "4f464143", "4f465349", "554e",
            "53696e6761706f7265", "4d616c6179736961", "496e646f6e65736961", "4a6f686f72",
            "53696e6761706f726520437573746f6d73", "53696e6761706f726520506f6c696365",
            "436f6d6d65726369616c2041666661697273", "41435241", "53747261746567696320476f6f6473",
            "52657574657273", "537472616974732054696d6573", "427573696e6573732054696d6573",
            "426c6f6f6d62657267", "4a75726f6e67", "576f6f646c616e6473", "54756173", "50617369722050616e6a616e67",
        )
        for token in encoded:
            term = bytes.fromhex(token).decode("ascii")
            self.assertNotRegex(self.output, r"(?i)(?<!\w)" + re.escape(term) + r"(?!\w)")

    def test_crafted_name_with_different_role_is_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = self.copy_fixtures(tmp, original_only=True)
            self.mutate_article(fixtures, "ART-006", "nominee director", "harbour clerk")
            result = research.research("SUB-002", fixtures)
        self.assertEqual(result["findings"], [])
        record = next(e for e in result["excluded_articles"] if e["article_id"] == "ART-006")
        self.assertEqual(record["identity_check"]["conflicting_fields"], ["role"])

    def test_crafted_different_employer_or_age_is_excluded(self):
        for old, new, field in (("JKL Trading Pte. Ltd.", "PQR Port Services Pte. Ltd.", "employer"),
                                (", 39,", ", 67,", "age")):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                fixtures = self.copy_fixtures(tmp, original_only=True)
                self.mutate_article(fixtures, "ART-006", old, new)
                result = research.research("SUB-002", fixtures)
                self.assertEqual(result["findings"], [])

    def test_name_alone_is_never_a_match(self):
        subject = self.subjects[1]
        result = research.identity(subject, subject["name"] + " faces a sanctions investigation.")
        self.assertEqual(result["decision"], "insufficient")
        self.assertEqual(result["matched_fields"], ["name"])
        report = self.name_only_report()
        self.assertEqual(len(report["possible_matches"]), 1)
        possible = report["possible_matches"][0]
        self.assertEqual(possible["article_id"], "ART-006")
        self.assertEqual(possible["identity_status"], "possible, not enough evidence")
        self.assertEqual(possible["identity_check"]["readings"], research.READINGS)
        self.assertIsNone(possible["identity_check"]["chosen_reading"])
        self.assertNotIn("ART-006", [e["article_id"] for e in report["excluded_articles"]])
        self.assertLessEqual(set(self.reports["SUB-002"]["findings"][0]), set(possible))
        markdown = research.render(report)
        section = markdown.split("## Possible matches (not enough evidence)\n", 1)[1].split(
            "## Excluded articles", 1)[0]
        self.assertLess(markdown.index("## Findings"), markdown.index("## Possible matches"))
        self.assertIn("SRC-001 | Business News A | ART-006 | 2026-10-23", section)
        self.assertIn("Fixture: articles/ART-006.md", section)
        self.assertIn("> " + possible["quote"], section)
        self.assertIn("Identity: possible, not enough evidence. Name matches; the article states "
                      "too little context to confirm or rule out.", section)
        self.assertIn("Three readings: same person / different person / not enough evidence. "
                      "Tool chooses none.", section)
        self.assertIn("Human review required.", section)

    def test_possible_match_does_not_count_as_a_finding_or_source_hit(self):
        report = self.name_only_report()
        self.assertEqual(report["findings"], [])
        for source in report["sources"]:
            if source["execution"] == "completed":
                self.assertEqual(source["sample_result"], "no finding")
                self.assertEqual(source["result"], "no hit")
        findings_section = research.render(report).split("## Findings\n", 1)[1].split(
            "## Possible matches", 1)[0]
        self.assertNotIn("ART-006", findings_section)

    def test_no_findings_summary_counts_possible_matches_and_preserves_gaps(self):
        quote = "Tan Wei Quen faces a sanctions investigation."
        for count in (1, 2):
            with self.subTest(count=count):
                report = self.name_only_report(" ".join([quote] * count))
                expected = ("No confirmed findings for Tan Wei Quen in the supplied articles from "
                            "completed sources. " + str(count)
                            + (" possible match needs" if count == 1 else " possible matches need")
                            + " human review. "
                            "SRC-004 failed; SRC-005 was not attempted; "
                            "SRC-003 covers nothing after 2025-09-01. This is not a clearance.")
                self.assertEqual(report["summary"], expected)
                self.assertIn(expected, research.render(report))

    def test_possible_matches_keep_classified_event_and_grounded_evidence(self):
        for wording, event in (("was designated under sanctions", "designation"),
                               ("paid a sanctions penalty", "penalty or settlement"),
                               ("faces a sanctions investigation", "open investigation"),
                               ("was delisted from sanctions", "delisting or case closed")):
            with self.subTest(event=event):
                quote = "Tan Wei Quen " + wording + "."
                report = self.name_only_report(quote)
                self.assertEqual(report["findings"], [])
                possible = report["possible_matches"][0]
                self.assertEqual(possible["event"], event)
                self.assertEqual(possible["quote"], quote)
                self.assertEqual(possible["date"], "2026-10-23")
                self.assertEqual(possible["type"], "sanctions")
                self.assertIn(": " + event, research.render(report))

    def test_no_report_prints_an_empty_conflicting_fields_line(self):
        reports = list(self.reports.values()) + [self.name_only_report()]
        for report in reports:
            self.assertNotRegex(research.render(report), r"(?m)^Conflicting fields:\s*$")
        report = copy.deepcopy(self.reports["SUB-002"])
        for record in report["excluded_articles"]:
            record["identity_check"]["conflicting_fields"] = []
        self.assertNotIn("Conflicting fields:", research.render(report))

    def test_subject_metadata_does_not_force_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = self.copy_fixtures(tmp, original_only=True)
            self.mutate_article(fixtures, "ART-006", 'subject_ids: ["SUB-002"]', 'subject_ids: ["SUB-005"]')
            self.assertEqual(len(research.research("SUB-002", fixtures)["findings"]), 1)

    def test_dotted_company_suffix_is_not_a_sentence_boundary(self):
        for suffix in ("Pte. Ltd.", "Co., Ltd."):
            with self.subTest(suffix=suffix):
                first = "The invented office designated ABC " + suffix + " under sanctions."
                second = "The company did not respond."
                self.assertEqual(research.sentences(first + " " + second), [first, second])
                ending = "The sanctions notice names ABC " + suffix
                self.assertEqual(research.sentences(ending + " " + second), [ending, second])

    def test_dotted_employer_is_copied_in_full_and_conflicts_are_preserved(self):
        subject = self.subjects[1]
        for suffix in ("Pte. Ltd.", "Co., Ltd."):
            employer = "JKL Trading " + suffix
            local_subject = {**subject, "employer": employer}
            quote = ("The office designated Tan Wei Quen, nominee director at " + employer
                     + ", on 2026-10-23 under sanctions.")
            check = research.identity(local_subject, quote)
            self.assertEqual(check["decision"], "matched")
            self.assertEqual(check["stated_fields"],
                             {"role": "nominee director", "employer": employer})
            conflict = research.identity(local_subject, quote.replace('nominee director', 'harbour clerk'))
            self.assertEqual(conflict["conflicting_fields"], ["role"])
            self.assertEqual(conflict["stated_fields"]["employer"], employer)

    def test_company_profile_is_safe_and_matched_including_resolution(self):
        report = self.reports["SUB-003"]
        self.assertEqual(report["subject"]["profile"], "provider of vessel bunkering services")
        self.assertNotIn("country", report["subject"])
        finding = report["findings"][0]
        for record in (finding, finding["resolution"]):
            check = record["identity_check"]
            self.assertEqual(check["stated_fields"], {"profile": "provider of vessel bunkering services"})
            self.assertEqual(check["matched_fields"], ["name", "profile"])
            self.assertEqual(check["identity"], "matched on name, profile")
            article = research.read_article(FIXTURES / record["fixture_file"])
            self.assertEqual(record["quote"], article["body"].split("\n\n")[0])

    def test_company_profile_conflict_excludes(self):
        subject = self.subjects[0]
        result = research.identity(subject, subject["name"] + ", a supplier of wooden models, faces sanctions.")
        self.assertEqual(result["decision"], "excluded")
        self.assertEqual(result["stated_fields"], {"profile": "supplier of wooden models"})
        self.assertEqual(result["conflicting_fields"], ["profile"])

    def test_company_readings_use_entity_for_partial_and_name_only_matches(self):
        for sid in ("SUB-001", "SUB-003"):
            for finding in self.reports[sid]["findings"]:
                self.assertEqual(finding["identity_check"]["readings"], research.ENTITY_READINGS)
                self.assertIn("same entity / different entity / not enough evidence", self.markdown[sid])
        subject = self.subjects[0]
        match = research.identity(subject, subject["name"] + " faces a sanctions inquiry.")
        self.assertEqual(match["readings"], research.ENTITY_READINGS)
        self.assertIsNone(match["chosen_reading"])

    def test_same_name_trap_has_conflicts_and_no_finding(self):
        report = self.reports["SUB-002"]
        self.assertNotIn("ART-004", [f["article_id"] for f in report["findings"]])
        record = next(e for e in report["excluded_articles"] if e["article_id"] == "ART-004")
        self.assertEqual(record["identity_check"]["conflicting_fields"], ["role", "employer", "age"])
        self.assertNotIn("ART-004", [p["article_id"] for p in report["possible_matches"]])
        self.assertIn("Conflicting fields: role, employer, age", self.markdown["SUB-002"])
        self.assertEqual(record["identity_check"]["stated_fields"],
                         {"role": "retired harbour clerk", "employer": "PQR Port Services Pte. Ltd.",
                          "age": "67"})
        matched = report["findings"][0]["identity_check"]
        self.assertEqual(matched["stated_fields"],
                         {"role": "nominee director", "employer": "JKL Trading Pte. Ltd.", "age": "39"})

    def test_full_identity_names_all_matched_fields(self):
        finding = self.reports["SUB-002"]["findings"][0]
        self.assertEqual(finding["identity_check"]["identity"], "matched on name, role, employer and age")
        self.assertIn("matched on name, role, employer and age", self.markdown["SUB-002"])

    def test_partial_identity_gives_three_readings_without_choice(self):
        for finding in self.reports["SUB-004"]["findings"]:
            check = finding["identity_check"]
            self.assertEqual(check["matched_fields"], ['name', 'role', 'age'] if finding['article_id'] in ('ART-010', 'ART-027') else ['name', 'role'])
            self.assertEqual(check["readings"], ["same person", "different person", "not enough evidence"])
            self.assertIsNone(check["chosen_reading"])
            self.assertIn("Tool chooses none.", self.markdown["SUB-004"])

    def test_closure_is_linked_with_both_dates_and_no_open_assessment(self):
        findings = self.reports["SUB-003"]["findings"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["date"], "2025-08-12")
        self.assertEqual(findings[0]["resolution"]["date"], "2026-10-24")
        self.assertEqual(findings[0]["state"], "cleared")
        self.assertNotIn("open", findings[0]["assessment"])
        self.assertIn("case was cleared on 2026-10-24", self.markdown["SUB-003"])
        self.assertEqual(findings[0]["event"], "historical investigation")
        self.assertNotIn(": open investigation", self.markdown["SUB-003"])

    def test_newer_unrelated_closure_cannot_clear_old_case(self):
        for old, new in (("Vessel Services Order 2024", "Quay Services Order 2024"),
                         ("Enforcement Agency C", "Customs Agency B"),
                         ("2025-08-12", "2025-08-13")):
            with self.subTest(old=old), tempfile.TemporaryDirectory() as tmp:
                fixtures = self.copy_fixtures(tmp)
                self.mutate_article(fixtures, "ART-009", old, new)
                finding = next(f for f in research.research("SUB-003", fixtures)["findings"]
                               if f["article_id"] == "ART-007")
                self.assertNotIn("resolution", finding)
                self.assertEqual(finding["state"], "historical status unknown")

    def test_no_follow_up_never_infers_open_or_closed(self):
        finding = next(f for f in self.reports["SUB-004"]["findings"] if f["article_id"] == "ART-017")
        self.assertEqual(finding["state"], "historical status unknown")
        self.assertEqual(finding["assessment"],
                         "Dated finding, no follow-up found in supplied sources, status unknown.")
        self.assertNotRegex(finding["assessment"], r"\b(open|closed)\b")
        self.assertNotIn("resolution", finding)
        self.assertEqual(finding["event"], "historical investigation")

    def test_incidental_prior_date_does_not_link_unrelated_closure(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = self.copy_fixtures(tmp)
            self.mutate_article(fixtures, "ART-009", "case over vessel bunkering", "case over free-port permits")
            self.mutate_article(fixtures, "ART-009",
                                "The announcement identified the vessel-service inquiry first reported by",
                                "The separate vessel-service inquiry remains unresolved, as first reported by")
            finding = next(f for f in research.research("SUB-003", fixtures)["findings"]
                           if f["article_id"] == "ART-007")
            self.assertEqual(finding["state"], "historical status unknown")
            self.assertNotIn("resolution", finding)

    def test_three_source_fields_always_printed_with_dates(self):
        for sid, report in self.reports.items():
            self.assertEqual(len(report["sources"]), 5)
            md = self.markdown[sid]
            for source in report["sources"]:
                block = md.split("### " + source["source_id"] + " | ", 1)[1].split("### ")[0]
                for field in ("execution", "result", "freshness"):
                    self.assertIn(field + ": " + source[field] + " | as_of: " + source["as_of"], block)
                    self.assertEqual(source["field_as_of"][field], source["as_of"])

    def test_packet_result_values_and_fixture_translation(self):
        for report in self.reports.values():
            for source in report["sources"]:
                self.assertIn(source["result"], {"no hit", "possible hit", "unavailable"})
                self.assertEqual(source["result"], research.RESULT_VALUES[source["sample_result"]])

    def test_failed_unattempted_and_stale_gaps_remain_visible(self):
        for sid, report in self.reports.items():
            gaps = {g["source_id"]: g for g in report["not_covered"]}
            self.assertEqual(set(gaps), {"SRC-003", "SRC-004", "SRC-005"})
            block = self.markdown[sid].split("## What was not covered\n", 1)[1]
            for gap in gaps.values():
                self.assertIn(gap["source_id"], block)
                self.assertIn(gap["as_of"], block)
            self.assertEqual(gaps["SRC-003"]["as_of"], "2025-09-01")
            for source in report["sources"]:
                if source["execution"] != "completed":
                    self.assertEqual(source["result"], "unavailable")
                    self.assertEqual(source["article_ids_checked"], [])
                    self.assertEqual(source["date_basis"], "planned date only, nothing read")

    def test_all_twenty_nine_articles_checked_once_per_subject(self):
        for report in self.reports.values():
            checked = [a for s in report["sources"] for a in s["article_ids_checked"]]
            self.assertEqual(sorted(checked), ["ART-%03d" % n for n in range(1, 30)])

    def test_failed_source_articles_are_never_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = self.copy_fixtures(tmp)
            self.mutate_article(fixtures, "ART-001", 'source_id: "SRC-001"', 'source_id: "SRC-004"')
            report = research.research("SUB-001", fixtures)
        self.assertNotIn("ART-001", [f["article_id"] for f in report["findings"]])

    def test_snapshot_age_not_old_article_drives_freshness(self):
        sources = {s["source_id"]: s for s in self.reports["SUB-003"]["sources"]}
        self.assertEqual(sources["SRC-001"]["freshness"], "current")
        self.assertIn("ART-007", sources["SRC-001"]["article_ids_checked"])
        self.assertEqual(sources["SRC-003"]["freshness"], "stale")

    def test_freshness_boundary_is_365_days(self):
        plan = research.read_json(FIXTURES / "sources.json")
        for age, expected in ((365, "current"), (366, "stale")):
            with self.subTest(age=age), tempfile.TemporaryDirectory() as tmp:
                fixtures = self.copy_fixtures(tmp)
                changed = copy.deepcopy(plan)
                source = changed["sources"][0]
                source["as_of"] = (date.fromisoformat(plan["run_date"]) - timedelta(days=age)).isoformat()
                source["freshness"] = expected
                # Use a source with no articles so the boundary tests only snapshot age.
                source = changed["sources"][3]
                source["as_of"] = changed["sources"][0]["as_of"]
                source["freshness"] = expected
                changed["sources"][0] = plan["sources"][0]
                (fixtures / "sources.json").write_text(json.dumps(changed), encoding="utf-8")
                result = research.research("SUB-005", fixtures)
                self.assertEqual(result["sources"][3]["freshness"], expected)

    def test_classification_by_wording_covers_all_allowed_event_types(self):
        examples = {
            "The invented office designated an invented company under a sanctions restriction.": "designation",
            "The invented office fined an invented company for sanctions evasion.": "penalty or settlement",
            "The invented office reached a sanctions settlement.": "penalty or settlement",
            "The invented office is investigating an invented company for sanctions evasion.": "open investigation",
            "The invented office closed a sanctions case.": "delisting or case closed",
            "The invented office delisted an invented company from sanctions restrictions.": "delisting or case closed",
            "The invented company opened a training room.": "not a sanctions event",
            "The invented company held a sanctions training course.": "not a sanctions event",
        }
        for text, expected in examples.items():
            self.assertEqual(research.classify(text), expected)

    def test_ordinary_mentions_are_not_findings(self):
        self.assertEqual(len(self.reports["SUB-005"]["non_events"]), 3)
        self.assertEqual(self.reports["SUB-005"]["findings"], [])

    def test_determinism_two_cli_runs_identical_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            for sid in self.reports:
                outputs = []
                for run in ("one", "two"):
                    out = Path(tmp) / run
                    proc = subprocess.run([sys.executable, str(SCRIPTS / "research.py"), "--subject", sid,
                                           "--fixtures", str(FIXTURES), "--out", str(out)],
                                          capture_output=True, text=True)
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    outputs.append([(out / (sid + ext)).read_bytes() for ext in (".json", ".md")])
                self.assertEqual(outputs[0], outputs[1])

    def test_unknown_subject_fails_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            proc = subprocess.run([sys.executable, str(SCRIPTS / "research.py"), "--subject", "../SUB-999",
                                   "--fixtures", str(FIXTURES), "--out", str(out)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("Unknown subject id", proc.stderr)
            self.assertFalse(out.exists())

    def test_cannot_write_into_frozen_fixtures(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = self.copy_fixtures(tmp)
            proc = subprocess.run([sys.executable, str(SCRIPTS / "research.py"), "--subject", "SUB-001",
                                   "--fixtures", str(fixtures), "--out", str(fixtures / "out")],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("outside fixtures", proc.stderr)
            self.assertFalse((fixtures / "out").exists())

    def test_repeated_front_matter_fields_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = self.copy_fixtures(tmp)
            self.mutate_article(fixtures, "ART-001", 'id: "ART-001"', 'id: "ART-001"\nid: "ART-002"')
            with self.assertRaisesRegex(ValueError, "Repeated field"):
                research.research("SUB-001", fixtures)

    def test_checker_validates_exact_link_pairs_tiers_reasons_and_row_attachments(self):
        for expected in self.key["relationship_checks"]:
            sid = expected["subject_id"]
            original = self.reports[sid]
            self.assertTrue(checker.check_links(expected, original, self.markdown[sid]), sid)
            for mutation in ("missing", "extra", "tier", "reason", "finding_attachment", "comparison_attachment"):
                with self.subTest(subject=sid, mutation=mutation):
                    report = copy.deepcopy(original)
                    link = report["links"][0]
                    if mutation == "missing":
                        report["links"].pop()
                    elif mutation == "extra":
                        report["links"].append(copy.deepcopy(link))
                    elif mutation == "tier":
                        link["tier"] = "SUGGESTED" if link["tier"] == "CONFIRMED" else "CONFIRMED"
                    elif mutation == "reason":
                        link["reasons"][0] = "Unsupported reason"
                    else:
                        group = report["findings"] if mutation == "finding_attachment" else report["comparisons"]
                        group = group + [record["resolution"] for record in group if "resolution" in record]
                        record = next(record for record in group if record["article_id"] == link["article_id"])
                        record.pop("link", None)
                        record.pop("links", None)
                    self.assertFalse(checker.check_links(expected, report, research.render(report)))

    def test_checker_rejects_excluded_follow_up_in_findings_or_relationships(self):
        expected = next(row for row in self.key["round3_rows"] if row["id"] == "T-007")
        original = self.reports["SUB-002"]
        self.assertTrue(checker.check_trap(expected, original, self.markdown["SUB-002"]))
        for mutation in ("finding", "link", "possible", "lost_conflict"):
            with self.subTest(mutation=mutation):
                report = copy.deepcopy(original)
                excluded = next(record for record in report["excluded_articles"] if record["article_id"] == "ART-026")
                if mutation == "finding":
                    report["findings"].append(excluded)
                elif mutation == "link":
                    report.setdefault("links", []).append({"article_id": "ART-026", "to_article_id": "ART-006",
                                            "tier": "SUGGESTED", "reasons": ["Same name only"]})
                elif mutation == "possible":
                    report["possible_matches"].append(excluded)
                else:
                    excluded["identity_check"]["conflicting_fields"].remove("age")
                self.assertFalse(checker.check_trap(expected, report, self.markdown["SUB-002"]))

    def test_checker_round3_findings_reject_lost_verification_or_response_context(self):
        for expected in self.key["round3_rows"]:
            if expected["kind"] != "finding":
                continue
            report = copy.deepcopy(self.reports[expected["subject_id"]])
            hit = next(finding for finding in report["findings"] if finding["article_id"] == expected["article_id"])
            self.assertTrue(hit["article_context"], expected["id"])
            hit["article_context"] = []
            self.assertFalse(checker.check_finding(expected, report, research.render(report)))

    def test_checker_rejects_missing_finding_or_changed_quote(self):
        expected = self.key["subjects"][0]["expected_findings"][0]
        for mutation in ("missing", "quote", "state"):
            report = copy.deepcopy(self.reports["SUB-001"])
            if mutation == "missing":
                report["findings"] = []
            else:
                report["findings"][0][mutation] = "incorrect"
            self.assertFalse(checker.check_finding(expected, report, research.render(report)))

    def test_checker_rejects_invented_denial_context_or_lost_resolution(self):
        expected = self.key["subjects"][0]["expected_findings"][1]
        report = copy.deepcopy(self.reports["SUB-001"])
        report["findings"][1]["article_context"] = []
        self.assertFalse(checker.check_finding(expected, report, research.render(report)))
        report = copy.deepcopy(self.reports["SUB-001"])
        report["findings"][1]["article_context"].append("The company denied sanctions evasion.")
        self.assertFalse(checker.check_finding(expected, report, research.render(report)))
        self.assertTrue(checker.forbidden_output(report, research.render(report), FIXTURES))
        expected = self.key["subjects"][2]["expected_findings"][0]
        report = copy.deepcopy(self.reports["SUB-003"])
        report["findings"][0].pop("resolution")
        self.assertFalse(checker.check_finding(expected, report, research.render(report)))

    def test_checker_rejects_contradictory_markdown(self):
        expected = self.key["subjects"][2]["expected_findings"][0]
        report = self.reports["SUB-003"]
        markdown = self.markdown["SUB-003"].replace(report["findings"][0]["assessment"],
                                                    "The allegation is still open.")
        self.assertFalse(checker.check_finding(expected, report, markdown))

    def test_removed_place_names_are_rejected_by_output_guard(self):
        report = self.reports["SUB-001"]
        for term in ('Jurong', 'Woodlands', 'Tuas', 'Pasir Panjang', 'Singapore'):
            for variant in (term, term.swapcase()):
                with self.subTest(term=variant):
                    self.assertTrue(checker.forbidden_output(report, self.markdown['SUB-001'] + variant, FIXTURES))

    def test_expanded_deny_list_is_rejected_case_insensitively(self):
        encoded = ("4d4153", "4d6f6e657461727920417574686f72697479", "4f464143", "4f465349",
                   "53696e6761706f7265", "53696e6761706f726520437573746f6d73",
                   "53696e6761706f726520506f6c696365", "436f6d6d65726369616c2041666661697273",
                   "41435241", "52657574657273", "537472616974732054696d6573",
                   "427573696e6573732054696d6573", "426c6f6f6d62657267",
                   "4d616c6179736961", "496e646f6e65736961", "4a6f686f72")
        report = self.reports["SUB-001"]
        for token in encoded:
            term = bytes.fromhex(token).decode("ascii")
            for variant in (term, term.swapcase()):
                with self.subTest(term=variant):
                    self.assertTrue(checker.forbidden_output(report, self.markdown["SUB-001"] + " " + variant, FIXTURES))

    def test_checker_forbidden_output_guards_fire(self):
        for sid, text in (("SUB-001", "registration_number"), ("SUB-001", "date_of_birth"),
                          ("SUB-001", "nationality"), ("SUB-005", "The subject is clear."),
                          ("SUB-001", "The company admitted the apparent violations."),
                          ("SUB-001", "The company was convicted."),
                          ("SUB-001", "The company was exonerated."),
                          ("SUB-001", bytes.fromhex("4f464143").decode("ascii"))):
            report = self.reports[sid]
            self.assertTrue(checker.forbidden_output(report, self.markdown[sid] + text, FIXTURES))


if __name__ == "__main__":
    unittest.main()
