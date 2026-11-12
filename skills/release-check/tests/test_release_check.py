"""End-to-end offline tests for release-check."""

import csv
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SOURCE_REPO = Path(__file__).resolve().parents[3]
SCRIPT = SOURCE_REPO / "skills" / "release-check" / "scripts" / "release_check.py"
SPEC = importlib.util.spec_from_file_location("release_check", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class UnittestOutputTest(unittest.TestCase):

    def test_case_keys_match_on_python39_and_python311(self):
        expected = {"example.Case.test_ok": "pass", "example.Case.test_fail": "fail",
                    "example.Case.test_error": "fail", "example.Case.test_skip": "skip"}
        for include_method in (False, True):
            with self.subTest(include_method=include_method):
                lines = []
                for method, result in (("test_ok", "ok"), ("test_fail", "FAIL"),
                                       ("test_error", "ERROR"), ("test_skip", "skipped 'synthetic'")):
                    owner = "example.Case" + ("." + method if include_method else "")
                    lines.append("%s (%s) ... %s" % (method, owner, result))
                output = "\n".join(lines) + "\nRan 4 tests in 0.001s\n"
                proc = subprocess.CompletedProcess([], 1, stdout="", stderr=output)
                with patch.object(CHECKER.subprocess, "run", return_value=proc):
                    tests = CHECKER.run_unittests(SOURCE_REPO)
                self.assertEqual(tests["cases"], expected)
                self.assertEqual(tests["count"], 4)
                self.assertEqual(tests["passed"], 1)


class ReleaseCheckTest(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="release-check-test-")
        self.repo = Path(self.temp.name) / "repo"
        tracked = subprocess.run(["git", "ls-files", "-z"], cwd=str(SOURCE_REPO),
                                 capture_output=True, text=True, check=True)
        for name in tracked.stdout.split("\0"):
            if not name or "release" in Path(name).parts:
                continue
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE_REPO / name, target)
        self.script = self.repo / "skills" / "release-check" / "scripts" / "release_check.py"
        self.git("init")
        self.git("config", "gc.auto", "0")
        self.git("config", "maintenance.auto", "false")
        self.git("config", "user.email", "release-check@example.invalid")
        self.git("config", "user.name", "Release Check Test")
        self.git("add", ".")
        self.git("commit", "-m", "version under test")
        skill_commit = self.git("rev-parse", "--short", "HEAD")
        self.skill_commit = skill_commit
        self.subject = self.repo / "skills" / "rate-quote"
        runs = self.repo / "runs" / "runs.csv"
        runs.write_text(runs.read_text(encoding="utf-8").replace("eadbd01", skill_commit),
                        encoding="utf-8")
        self.git("add", "runs/runs.csv")
        self.git("commit", "-m", "point runs at version under test")
        # Seed an isolated test fixture, never invoke the release-recording CLI.
        manifest = json.loads((SOURCE_REPO / "skills" / "rate-quote" / "release" /
                               "manifest.json").read_text(encoding="utf-8"))
        manifest["fingerprint"] = CHECKER.fingerprint(self.repo, self.subject)
        evidence = CHECKER.qualifying_runs(self.repo, self.subject, manifest["fingerprint"])
        self.assertEqual(len(evidence["run_ids"]), 6)
        manifest["supervised_runs"] = {"count": 6, "required": 6,
                                       "run_ids": evidence["run_ids"],
                                       "skill_commit": skill_commit}
        release = self.subject / "release"
        release.mkdir()
        (release / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def run_check(self, *extra):
        return subprocess.run(
            [sys.executable, str(self.script), "skills/rate-quote"] + list(extra),
            cwd=str(self.repo), capture_output=True, text=True)

    def git(self, *args):
        proc = subprocess.run(["git"] + list(args), cwd=str(self.repo),
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout.strip()

    def report(self):
        reports = sorted((self.repo / "skills" / "rate-quote" / "release").glob("report-*.md"))
        return reports[-1].read_text(encoding="utf-8")

    def test_no_change_is_release(self):
        manifest = self.subject / "release" / "manifest.json"
        before = manifest.read_bytes()
        proc = self.run_check()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Verdict: RELEASE", proc.stdout)
        self.assertIn("Supervised runs: 6/6", proc.stdout)
        self.assertIn("Changed parts: none", self.report())
        self.assertEqual(manifest.read_bytes(), before)

    def write_supervised_runs(self, run_ids, skill_commit):
        # Replace only the isolated temporary repo's synthetic ledger.
        with (self.repo / "runs" / "runs.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "run_id", "skill_commit", "verdict", "counts_toward_six"])
            writer.writeheader()
            writer.writerows({"run_id": run_id, "skill_commit": skill_commit,
                              "verdict": "pass", "counts_toward_six": "yes"}
                             for run_id in run_ids)

    def test_duplicate_run_id_counts_once_and_is_reported(self):
        for reset in (False, True):
            with self.subTest(reset=reset):
                if reset:
                    template = self.subject / "references" / "quote-template.md"
                    template.write_text(template.read_text(encoding="utf-8") + "\n",
                                        encoding="utf-8")
                    self.git("add", str(template.relative_to(self.repo)))
                    self.git("commit", "-m", "synthetic template change")
                skill_commit = self.git("rev-parse", "--short", "HEAD")
                self.write_supervised_runs(["RUN-20261026-01"] * 6, skill_commit)
                proc = self.run_check()
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertIn("Verdict: HOLD", proc.stdout)
                self.assertIn("Supervised runs: 1/6", proc.stdout)
                self.assertIn("Duplicate supervised run IDs (counted at most once): RUN-20261026-01",
                              self.report())

    def test_duplicates_do_not_crowd_out_distinct_run_ids(self):
        self.write_supervised_runs(["RUN-20261026-%02d" % number for number in range(1, 7)] +
                                   ["RUN-20261026-06"] * 6, self.skill_commit)
        current = CHECKER.fingerprint(self.repo, self.subject)
        evidence = CHECKER.qualifying_runs(self.repo, self.subject, current)
        self.assertEqual(evidence["run_ids"], ["RUN-20261026-%02d" % number for number in range(1, 7)])
        proc = self.run_check()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Supervised runs: 6/6", proc.stdout)
        self.assertIn("Duplicate supervised run IDs (counted at most once): RUN-20261026-06",
                      self.report())

    def test_normalized_duplicate_run_ids_count_once_before_and_after_reset(self):
        aliases = ["RUN-20261026-01", "RUN-20261026-01 ", " RUN-20261026-01",
                   "run-20261026-01", "RUN-20261026-01\t", "Run-20261026-01"]
        for reset in (False, True):
            with self.subTest(reset=reset):
                if reset:
                    template = self.subject / "references" / "quote-template.md"
                    template.write_text(template.read_text(encoding="utf-8") + "\n",
                                        encoding="utf-8")
                    self.git("add", str(template.relative_to(self.repo)))
                    self.git("commit", "-m", "synthetic template change")
                self.write_supervised_runs(aliases, self.git("rev-parse", "--short", "HEAD"))
                proc = self.run_check()
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertIn("Supervised runs: 1/6", proc.stdout)
                self.assertIn("Duplicate supervised run IDs (counted at most once): RUN-20261026-01",
                              self.report())

    def test_normalized_distinct_valid_run_ids_still_count(self):
        ids = ["RUN-20261026-%02d" % number for number in range(1, 7)]
        self.write_supervised_runs([" \t" + run_id.lower() + "\t " for run_id in ids],
                                   self.skill_commit)
        current = CHECKER.fingerprint(self.repo, self.subject)
        self.assertEqual(CHECKER.qualifying_runs(self.repo, self.subject, current)["run_ids"], ids)
        proc = self.run_check()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Supervised runs: 6/6", proc.stdout)

    def test_invalid_run_ids_never_count_and_are_named(self):
        groups = [["RUN-Y", "RUN-Y ", " RUN-Y", "run-y", "RUN-Y\t", "Run-Y"],
                  ["", "RUN-20261026-1", "RUN-2026102-01", "RUN-20261026-001",
                   "RUN-20261026-01-extra", "RUN-20261026-01\nextra"]]
        for ids in groups:
            with self.subTest(ids=ids):
                self.write_supervised_runs(ids, self.skill_commit)
                proc = self.run_check()
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertIn("Supervised runs: 0/6", proc.stdout)
                report = self.report()
                self.assertIn("Invalid supervised run IDs (not counted):", report)
                for run_id in ids:
                    self.assertIn(repr(run_id), report)

    def test_unicode_digit_lookalikes_never_count_and_are_named(self):
        run_id = "RUN-20261026-01"
        lookalikes = [run_id.translate(str.maketrans("0123456789", digits))
                      for digits in ("０１２３４５６７８９", "٠١٢٣٤٥٦٧٨٩",
                                     "০১২৩৪৫৬৭৮৯", "०१२३४५६७८९")]
        lookalikes.append("RUN-20261026-０1")
        for ids, count in (([run_id] + lookalikes, 1), (lookalikes, 0)):
            with self.subTest(count=count):
                self.write_supervised_runs(ids, self.skill_commit)
                proc = self.run_check()
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertIn("Supervised runs: %d/6" % count, proc.stdout)
                report = self.report()
                self.assertIn("Invalid supervised run IDs (not counted):", report)
                for invalid in lookalikes:
                    self.assertIn(repr(invalid), report)

    def test_unchanged_version_with_too_few_runs_does_not_claim_reset(self):
        for ids in ([], ["RUN-20261026-01"]):
            with self.subTest(ids=ids):
                self.write_supervised_runs(ids, self.skill_commit)
                proc = self.run_check()
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                report = self.report()
                self.assertIn("Changed parts: none", report)
                self.assertIn("fewer than six supervised runs", report)
                self.assertNotIn("reset", report)

    def test_reset_excludes_normalized_prior_manifest_ids(self):
        manifest_path = self.subject / "release" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        ids = manifest["supervised_runs"]["run_ids"]
        aliases = [" \t" + run_id.lower() + "\t " for run_id in ids]
        template = self.subject / "references" / "quote-template.md"
        template.write_text(template.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        self.git("add", str(template.relative_to(self.repo)))
        self.git("commit", "-m", "synthetic template change")
        for old_ids, logged_ids in ((aliases, ids), (ids, aliases)):
            with self.subTest(old_ids=old_ids):
                manifest["supervised_runs"]["run_ids"] = old_ids
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                self.write_supervised_runs(logged_ids, self.git("rev-parse", "--short", "HEAD"))
                proc = self.run_check()
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertIn("Supervised runs: 0/6", proc.stdout)

    def test_os_junk_does_not_change_fingerprint_or_run_version(self):
        before = CHECKER.fingerprint(self.repo, self.subject)
        for folder in (self.subject / "scripts", self.subject / "references",
                       self.repo / "fixtures" / "forms"):
            for name in (".DS_Store", "._quote-template.md", "._quote.py", "Thumbs.db", "desktop.ini"):
                (folder / name).write_bytes(b"synthetic OS metadata")
        self.git("add", "-f", "skills/rate-quote/scripts", "skills/rate-quote/references", "fixtures/forms")
        self.git("commit", "-m", "synthetic OS metadata")
        current = CHECKER.fingerprint(self.repo, self.subject)
        self.assertEqual(current, before)
        for commit in (self.skill_commit, self.git("rev-parse", "--short", "HEAD")):
            evidence = CHECKER.run_version_evidence(self.repo, self.subject, commit, current)
            self.assertEqual(evidence["changed_parts"], [])
            self.assertIsNone(evidence["error"])
        proc = self.run_check()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Changed parts: none", self.report())
        # Do not broadly ignore hidden files or ordinary non-code inputs.
        for folder in (self.subject / "references", self.repo / "fixtures" / "forms"):
            (folder / ".synthetic-input").write_bytes(b"synthetic real input")
        changes = CHECKER.changed_parts({"fingerprint": current},
                                        CHECKER.fingerprint(self.repo, self.subject))
        self.assertEqual(changes, ["fixtures", "template"])

    def test_broken_rounding_case_is_block(self):
        quote = self.repo / "skills" / "rate-quote" / "scripts" / "quote.py"
        text = quote.read_text(encoding="utf-8")
        text = text.replace("ROUND_HALF_DOWN", "ROUND_HALF_UP")
        quote.write_text(text, encoding="utf-8")
        proc = self.run_check()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("Verdict: BLOCK", proc.stdout)
        report = self.report()
        self.assertIn("test_exact_half_rounds_down", report)
        self.assertIn("expected answer: REQ-003", report)

    def test_template_edit_with_green_tests_is_hold_and_resets_count(self):
        template = self.repo / "skills" / "rate-quote" / "references" / "quote-template.md"
        template.write_text(template.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        proc = self.run_check()
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("Verdict: HOLD", proc.stdout)
        report = self.report()
        self.assertIn("Changed parts: template", report)
        count = re.search(r"(?m)^([0-9]+) of \1 passed\.$", report)
        if count is None:
            self.fail(report)
        self.assertGreaterEqual(int(count.group(1)), 113)
        self.assertIn("Expected-answer replay: 7/7 passed", proc.stdout)
        self.assertIn("Supervised runs: 0/6", proc.stdout)
        self.assertIn("supervised run count resets to 0 of 6", report)
        self.assertIn("a change under test reset the supervised-run gate", report)

    def test_manifest_records_all_fingerprint_parts(self):
        manifest = json.loads((self.repo / "skills" / "rate-quote" / "release" / "manifest.json").read_text())
        self.assertEqual(set(manifest["fingerprint"]["parts"]),
                         {"code", "prompt", "template", "model", "fixtures", "acceptance_rule"})
        self.assertEqual(manifest["tests"]["count"], 113)
        self.assertEqual(manifest["expected_answer_replay"]["count"], 7)

    def test_default_run_does_not_call_model(self):
        proc = self.run_check()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Not run. It is off by default", self.report())

    def test_default_check_preserves_manifest_on_hold(self):
        template = self.repo / "skills" / "rate-quote" / "references" / "quote-template.md"
        template.write_text(template.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        before = (self.repo / "skills" / "rate-quote" / "release" / "manifest.json").read_bytes()
        proc = self.run_check()
        after = (self.repo / "skills" / "rate-quote" / "release" / "manifest.json").read_bytes()
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(before, after)
        self.assertIn("Verdict: HOLD", proc.stdout)

    def test_run_version_checks_uncommitted_parts(self):
        paths = {"code": self.subject / "scripts" / "quote.py",
                 "template": self.subject / "references" / "quote-template.md",
                 "acceptance_rule": self.repo / "docs" / "acceptance-rule-v1.1.md"}
        for part, path in paths.items():
            with self.subTest(part=part):
                original = path.read_bytes()
                try:
                    path.write_bytes(original + b"\n")
                    current = CHECKER.fingerprint(self.repo, self.subject)
                    evidence = CHECKER.run_version_evidence(
                        self.repo, self.subject, self.skill_commit, current)
                    self.assertIsNone(evidence["error"])
                    self.assertEqual(evidence["changed_parts"], [part])
                finally:
                    path.write_bytes(original)

    def test_run_version_separates_prompt_model_and_ordinary_code(self):
        extract = self.subject / "scripts" / "extract_form.py"
        original = extract.read_text(encoding="utf-8")
        constants = CHECKER.literal_assignments(extract, {"DEFAULT_MODEL", "PROMPT_VERSION"})
        edits = [(original + "\n# synthetic code-only edit\n", ["code"]),
                 (original.replace(constants["DEFAULT_MODEL"], "synthetic-test-model"),
                  ["code", "model"]),
                 (original.replace(constants["PROMPT_VERSION"], "synthetic-test-prompt"),
                  ["code", "prompt"])]
        for text, parts in edits:
            with self.subTest(parts=parts):
                try:
                    extract.write_text(text, encoding="utf-8")
                    current = CHECKER.fingerprint(self.repo, self.subject)
                    evidence = CHECKER.run_version_evidence(
                        self.repo, self.subject, self.skill_commit, current)
                    self.assertIsNone(evidence["error"])
                    self.assertEqual(evidence["changed_parts"], parts)
                finally:
                    extract.write_text(original, encoding="utf-8")

    def test_run_version_checks_untracked_code(self):
        extra = self.subject / "scripts" / "new_helper.py"
        extra.write_text("# synthetic test helper\n", encoding="utf-8")
        current = CHECKER.fingerprint(self.repo, self.subject)
        evidence = CHECKER.run_version_evidence(
            self.repo, self.subject, self.skill_commit, current)
        self.assertIsNone(evidence["error"])
        self.assertEqual(evidence["changed_parts"], ["code"])

    def test_matching_baseline_cannot_make_old_runs_current(self):
        quote = self.subject / "scripts" / "quote.py"
        quote.write_text(quote.read_text(encoding="utf-8") + "\n# synthetic edit\n",
                         encoding="utf-8")
        # Reproduce a baseline matching today's files but runs on older code.
        manifest_path = self.subject / "release" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["fingerprint"] = CHECKER.fingerprint(self.repo, self.subject)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        proc = self.run_check()
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("Verdict: HOLD", proc.stdout)
        self.assertIn("Supervised runs: 0/6", proc.stdout)
        self.assertIn("Changed parts: none", self.report())
        self.assertIn("Parts changed since that commit: code", self.report())
        self.assertIn("(reset: the logged runs were on an earlier version)", self.report())
        self.assertNotIn("(reset by this change)", self.report())

    def test_runs_on_old_commit_with_changed_code_are_hold(self):
        old_commit = self.git("rev-parse", "--short", "HEAD~1")

        quote = self.repo / "skills" / "rate-quote" / "scripts" / "quote.py"
        quote.write_text(quote.read_text(encoding="utf-8") + "\n# current version\n",
                         encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-m", "current version")

        proc = self.run_check()

        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("Verdict: HOLD", proc.stdout)
        self.assertIn("Supervised runs: 0/6", proc.stdout)
        report = self.report()
        self.assertIn("Counted runs used commit: `%s`" % old_commit, report)
        self.assertIn("Parts changed since that commit: code", report)
        self.assertIn("counted runs were on an earlier version; supervised run count is 0 of 6 for the current version", report)


if __name__ == "__main__":
    unittest.main()
