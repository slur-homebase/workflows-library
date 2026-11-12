"""Offline model-reader checks. Live Claude is never invoked by these tests."""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
EVIDENCE = ROOT / "evidence" / "phase-3"
# The recorded bodies/hashes and schema predate the approved name-only rename.
FIXTURES = EVIDENCE / "fixtures-v1"


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


research = module("model_test_research", "research.py")
with patch.dict(sys.modules, {"research": research}):
    reader = module("model_test_reader", "model_reader.py")
    checker = module("model_test_checker", "check_answer_key.py")
    with patch.dict(sys.modules, {"model_reader": reader, "check_answer_key": checker}):
        benchmark = module("model_test_benchmark", "benchmark_models.py")


class ValidatorTest(unittest.TestCase):
    def setUp(self):
        self.article = research.read_article(FIXTURES / "articles" / "ART-006.md")
        subject = research.read_json(FIXTURES / "subjects.json")["subjects"][1]
        # Hand-authored validator input, not presented as a model recording.
        self.form = {"name": "Tan Wei Quen", "role": "nominee director",
                     "employer": subject["employer"], "district": subject["city"], "country": None,
                     "event_type": "designation", "quote": research.sentences(self.article["body"])[0],
                     "event_date": "2026-10-23",
                     "authority": self.article["body"].split(" imposed a sanctions", 1)[0].removeprefix("The ")}

    def test_grounded_form_is_valid(self):
        self.assertEqual(reader.validate_record(self.article, self.form), [])

    def test_reject_non_verbatim_quote(self):
        self.form["quote"] = self.form["quote"].replace("restriction", "ban")
        self.assertIn("non-verbatim quote", reader.validate_record(self.article, self.form))

    def test_reject_truncated_quote_even_when_substring(self):
        self.form["quote"] = "Tan Wei Quen"
        self.assertIn("non-verbatim quote", reader.validate_record(self.article, self.form))

    def test_reject_invented_field(self):
        self.form["district"] = "Invented But Unstated District"
        self.assertIn("ungrounded field: district", reader.validate_record(self.article, self.form))

    def test_reject_date_absent_from_body_even_if_metadata_states_it(self):
        self.form["event_date"] = "2026-10-24"
        self.article["date"] = "2026-10-24"
        self.assertIn("ungrounded field: event_date", reader.validate_record(self.article, self.form))

    def test_reject_invalid_date_even_if_body_contains_it(self):
        self.article["body"] += " 2026-99-99"
        self.form["event_date"] = "2026-99-99"
        self.assertIn("invalid event date", reader.validate_record(self.article, self.form))

    def test_nullable_context_not_invented(self):
        for field in ("role", "employer", "district", "authority"):
            self.form[field] = None
        self.assertEqual(reader.validate_record(self.article, self.form), [])

    def test_reject_extra_judgement_key(self):
        self.form["disposition"] = "approved"
        self.assertEqual(reader.validate_record(self.article, self.form), ["invalid evidence schema"])

    def test_reject_invalid_types_without_crashing(self):
        for key in self.form:
            for value in ([], {}, 42, ""):
                with self.subTest(key=key, value=value):
                    form = {**self.form, key: value}
                    self.assertTrue(reader.validate_record(self.article, form))

    def test_reject_repeated_json_key(self):
        with self.assertRaisesRegex(ValueError, "Repeated field"):
            reader.parse_output({"subtype": "success", "result": '{"name":"A","name":"B"}'})

    def test_shared_matcher_keeps_possible_name_and_stated_conflict(self):
        subject = research.read_json(FIXTURES / "subjects.json")["subjects"][1]
        match = research.match_identity(subject, "Tan Wei Quen", {})
        self.assertEqual(match["decision"], "insufficient")
        self.assertIsNone(match["chosen_reading"])
        match = research.match_identity(subject, "Tan Wei Quen", {"role": "retired harbour clerk"})
        self.assertEqual(match["decision"], "excluded")


class BillingGuardTest(unittest.TestCase):
    def setUp(self):
        # The approved forty-call benchmark is frozen to its original twenty
        # articles. These tests mock every call and never launch a new run.
        context = patch.object(benchmark, 'DEFAULT_FIXTURES', FIXTURES)
        context.start()
        self.addCleanup(context.stop)

    def test_required_command_and_disabled_disk_context(self):
        for model in ("haiku", "sonnet"):
            command = reader.model_command(model)
            self.assertEqual(command[:11], ["env", "-u", "ANTHROPIC_API_KEY", "-u",
                                          "ANTHROPIC_AUTH_TOKEN", "claude", "-p", "--model",
                                          model, "--output-format", "json"])
            for flag in ("--safe-mode", "--strict-mcp-config", "--disable-slash-commands",
                         "--no-session-persistence"):
                self.assertIn(flag, command)
            self.assertEqual(command[command.index("--tools") + 1], "")
            self.assertEqual(command[command.index("--setting-sources") + 1], "")
            self.assertNotIn("--bare", command)
            self.assertNotIn("--fallback-model", command)
        with self.assertRaises(ValueError):
            reader.model_command("opus")

    def test_non_subscription_auth_blocks_before_model_call(self):
        for method in ("api_key", None, "other"):
            completed = subprocess.CompletedProcess([], 0, json.dumps({"loggedIn": True, "authMethod": method}), "")
            with patch.object(reader.subprocess, "run", return_value=completed) as run:
                with self.assertRaisesRegex(ValueError, "Billing guard"):
                    reader.subscription_auth()
                self.assertEqual(run.call_args.args[0], ["claude", "auth", "status"])
                self.assertEqual(run.call_count, 1)

    def test_call_sends_body_only_without_reading_repo(self):
        article = research.read_article(FIXTURES / "articles" / "ART-001.md")
        completed = subprocess.CompletedProcess([], 0, json.dumps({"subtype": "success", "result": "{}"}), "")
        with patch.object(reader.subprocess, "run", return_value=completed) as run:
            reader.call_article(article, "haiku")
        sent = run.call_args.kwargs["input"]
        self.assertEqual(sent, reader.INSTRUCTIONS + article["body"])
        self.assertNotIn("subject_ids:", sent)
        self.assertNotIn("answer-key", sent)
        self.assertNotIn("ANTHROPIC_API_KEY", run.call_args.kwargs["env"])
        self.assertNotIn("ANTHROPIC_AUTH_TOKEN", run.call_args.kwargs["env"])
        self.assertNotEqual(Path(run.call_args.kwargs["cwd"]), ROOT)

    def test_ledger_prevents_a_second_live_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "plan.json").write_text('{"call_cap":40}')
            (out / "calls.jsonl").write_text("")
            with patch.object(benchmark, "subscription_auth", return_value="claude.ai"), \
                    patch.object(benchmark, "call_article") as call:
                with self.assertRaises(FileExistsError):
                    benchmark.live(out)
                call.assert_not_called()

    def test_failed_call_retried_once_then_stops_and_counts_both(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "plan.json").write_text('{"call_cap":40}')
            failure = {"cli": {}, "wall_seconds": 0, "failure": "mock failure"}
            with patch.object(benchmark, "subscription_auth", return_value="claude.ai"), \
                    patch.object(benchmark, "call_article", return_value=failure) as call, \
                    patch("builtins.print"):
                self.assertFalse(benchmark.live(out))
            self.assertEqual(call.call_count, 2)
            self.assertEqual(research.read_json(out / "run.json")["call_count"], 2)
            self.assertEqual(len((out / "calls.jsonl").read_text().splitlines()), 2)

    def test_cap_counts_retry_and_never_launches_call_41(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "plan.json").write_text('{"call_cap":40}')
            success = {"cli": {}, "wall_seconds": 0}
            failure = {"cli": {}, "wall_seconds": 0, "failure": "mock failure"}
            # One recovered first call needs 41 total invocations to finish. Stop at 40.
            with patch.object(benchmark, "subscription_auth", return_value="claude.ai"), \
                    patch.object(benchmark, "call_article", side_effect=[failure] + [success] * 40) as call, \
                    patch("builtins.print"):
                self.assertFalse(benchmark.live(out))
            self.assertEqual(call.call_count, 40)
            self.assertEqual(research.read_json(out / "run.json")["call_count"], 40)


class RecordedReplayTest(unittest.TestCase):
    def test_frozen_country_schema_and_historical_identity_remain_supported(self):
        self.assertEqual(reader.FIELDS,
                         {"name", "role", "employer", "district", "country", "event_type",
                          "quote", "event_date", "authority"})
        subject = research.read_json(FIXTURES / "subjects.json")["subjects"][0]
        self.assertIn("country", subject)
        report = research.research(subject["id"], FIXTURES)
        self.assertEqual(report["subject"]["country"], subject["country"])
        for record in report["findings"]:
            self.assertEqual(record["identity_check"]["matched_fields"], ["name", "country"])

    def test_renamed_bodies_cannot_replay_old_recordings(self):
        current = ROOT / "fixtures" / "articles"
        articles = [research.read_article(p) for p in sorted(current.glob("*.md"))]
        valid, rejected = reader.load_records(EVIDENCE / "haiku.json", articles)
        self.assertEqual(valid, {})
        self.assertEqual(len(rejected), 29)
        self.assertEqual(sum(r['errors'] == ['recorded article hash differs'] for r in rejected), 20)
        self.assertEqual({r['article_id'] for r in rejected
                          if r['errors'] != ['recorded article hash differs']},
                         {'ART-%03d' % n for n in range(21, 30)})

    def test_recorded_outputs_reproduce_saved_reports_without_model_call(self):
        articles = [research.read_article(p) for p in sorted((FIXTURES / "articles").glob("*.md"))]
        with patch.object(reader, "call_article", side_effect=AssertionError("offline only")):
            for model in ("haiku", "sonnet"):
                records = EVIDENCE / (model + ".json")
                valid, rejected = reader.load_records(records, articles)
                self.assertEqual(len(valid) + len(rejected), 20)
                self.assertFalse(any("recorded article hash differs" in r["errors"] for r in rejected))
                for n in range(1, 6):
                    sid = "SUB-%03d" % n
                    with patch.dict(sys.modules, {"model_reader": reader}):
                        report = research.research(sid, FIXTURES, "model", records)
                    saved = research.read_json(EVIDENCE / (model + "-reports") / (sid + ".json"))
                    # Keep phase 3 files frozen. Normalize only the approved
                    # version, company readings and possible-match grammar.
                    self.assertEqual(saved["skill_version"], "0.2")
                    self.assertEqual(report["skill_version"], "0.3")
                    saved["skill_version"] = report["skill_version"]
                    # Current reports omit obsolete place fields even on offline replay.
                    saved['subject'].pop('city', None)
                    markdown = (EVIDENCE / (model + "-reports") / (sid + ".md")).read_text()
                    if saved["subject"]["type"] == "company":
                        for record in saved["findings"] + saved["possible_matches"]:
                            check = record["identity_check"]
                            if check["readings"]:
                                self.assertEqual(check["readings"], research.READINGS)
                                check["readings"] = research.ENTITY_READINGS
                        markdown = markdown.replace("same person / different person", "same entity / different entity")
                    count = len(saved["possible_matches"])
                    old_words = str(count) + " possible match(es) need"
                    new_words = str(count) + (" possible match needs" if count == 1 else " possible matches need")
                    saved["summary"] = saved["summary"].replace(old_words, new_words)
                    markdown = markdown.replace(old_words, new_words)
                    markdown = markdown.replace(
                        'Name matches; the article states no role, employer or district to confirm or rule out.',
                        'Name matches; the article states too little context to confirm or rule out.')
                    self.assertEqual(report, saved)
                    self.assertEqual(research.render(report), markdown)

    def test_recorded_row_scores_are_reproducible_via_cli(self):
        scores = research.read_json(EVIDENCE / "scores.json")
        for model in ("haiku", "sonnet"):
            with tempfile.TemporaryDirectory() as tmp:
                rows = checker.evaluate(FIXTURES, Path(tmp), "model", EVIDENCE / (model + ".json"))
            self.assertEqual(rows, scores["models"][model]["replay_rows"])

    def test_changed_article_hash_is_rejected(self):
        article = research.read_article(FIXTURES / "articles" / "ART-001.md")
        article["body"] += " A new invented sentence."
        valid, rejected = reader.load_records(EVIDENCE / "haiku.json", [article] + [
            research.read_article(p) for p in sorted((FIXTURES / "articles").glob("*.md")) if p.stem != "ART-001"])
        self.assertNotIn("ART-001", valid)
        self.assertIn("recorded article hash differs", rejected[0]["errors"])

    def test_missing_model_records_never_fall_back_to_script(self):
        with self.assertRaisesRegex(ValueError, "requires --records"):
            research.research("SUB-001", FIXTURES, "model")

    def test_rejected_output_is_visible_and_replay_fails_closed(self):
        bundle = copy.deepcopy(research.read_json(EVIDENCE / "haiku.json"))
        bundle["articles"]["ART-001"]["cli"]["result"] = "not JSON"
        with tempfile.TemporaryDirectory() as tmp:
            records = Path(tmp) / "records.json"
            records.write_text(json.dumps(bundle))
            with patch.dict(sys.modules, {"model_reader": reader}):
                report = research.research("SUB-001", FIXTURES, "model", records)
            self.assertIn("Model reading incomplete", report["summary"])
            self.assertIn("ART-001", research.render(report).split("## Rejected model records")[1])
            self.assertNotIn("ART-001", [f["article_id"] for f in report["findings"]])
            source = next(s for s in report["sources"] if s["source_id"] == "SRC-001")
            self.assertEqual(source["execution"], "completed")
            self.assertEqual(source["result"], "unavailable")
            self.assertIn("SRC-001", [g["source_id"] for g in report["not_covered"]])
            rows = checker.evaluate(FIXTURES, Path(tmp) / "reports", "model", records)
            self.assertTrue(any(r["status"] == "FAIL" for r in rows))

    def test_real_ledger_and_reported_cost_totals_match(self):
        calls = [json.loads(line) for line in (EVIDENCE / "calls.jsonl").read_text().splitlines()]
        run = research.read_json(EVIDENCE / "run.json")
        scores = research.read_json(EVIDENCE / "scores.json")
        self.assertEqual(run["authMethod"], "claude.ai")
        self.assertLessEqual(len(calls), 40)
        self.assertEqual(run["call_count"], len(calls))
        self.assertEqual(scores["call_count"], len(calls))
        observed_count = 0
        for model in ("haiku", "sonnet"):
            selected = [c for c in calls if c["model"] == model]
            self.assertEqual(len(selected), scores["models"][model]["calls_reserved"])
            observed = [c for c in selected if (EVIDENCE / ("call-%02d.json" % c["call"])).exists()]
            observed_count += len(observed)
            total = sum(research.read_json(EVIDENCE / ("call-%02d.json" % c["call"]))["cli"]["total_cost_usd"]
                        for c in observed)
            self.assertAlmostEqual(scores["models"][model]["api_equivalent_usd_not_paid"], total)
        if run["status"] == "complete":
            self.assertEqual(len(calls), 40)
            self.assertEqual(observed_count, 40)
        else:
            self.assertEqual(run["status"], "BLOCKED")
            self.assertEqual(observed_count, run["completed_outputs"])
            self.assertFalse(scores["comparison_complete"])
        self.assertEqual(scores["api_spend_usd"], 0)


if __name__ == "__main__":
    unittest.main()
