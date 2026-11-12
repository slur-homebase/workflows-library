#!/usr/bin/env python3
"""Offline rate-quote release gate and sanctions-news packaging checks.

The checker fingerprints the parts under test, runs the repository's unittest
suite, replays the frozen expected answers, and compares the results with the
last manifest in the subject skill's release folder. It has no network path;
the model extraction eval runs only when --with-model is supplied.
"""

import argparse
import ast
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path


SCHEMA_VERSION = 1
REQUIRED_SUPERVISED_RUNS = 6
RESET_PARTS = {"code", "prompt", "template", "model", "acceptance_rule"}
EXPECTED = {
    "REQ-001": {"received": "2026-09-28", "outcome": "quote_draft",
                "rates": ["5.36%"], "end_dates": ["2026-11-16"]},
    "REQ-003": {"received": "2026-09-29", "outcome": "quote_draft",
                "rates": [None, "5.56%"], "end_dates": [None, "2027-02-18"]},
    "REQ-004": {"received": "2026-09-29", "outcome": "quote_draft",
                "rates": ["5.39%"], "end_dates": ["2026-11-12"]},
    "REQ-006": {"received": "2026-09-29", "outcome": "hand_back",
                "rates": [None], "end_dates": [None]},
    "REQ-007": {"received": "2026-09-29", "outcome": "quote_draft",
                "rates": ["5.30%"], "end_dates": ["2026-11-20"]},
    "REQ-008": {"received": "2026-09-29", "outcome": "quote_draft",
                "rates": ["5.43%"], "end_dates": ["2026-11-02"]},
    "REQ-009": {"received": "2026-09-29", "outcome": "quote_draft",
                "rates": ["6.15%"], "end_dates": ["2026-11-16"]},
}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def combined_digest(entries):
    payload = "".join("%s\0%s\n" % (item["path"], item["sha256"])
                      for item in entries).encode("utf-8")
    return sha256_bytes(payload)


def file_entries(repo, paths):
    entries = []
    for path in sorted(set(Path(p) for p in paths)):
        if path.is_file():
            entries.append({"path": path.relative_to(repo).as_posix(),
                            "sha256": sha256_bytes(path.read_bytes())})
    return entries


def literal_assignments_text(text, names, filename):
    tree = ast.parse(text, filename=filename)
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in names:
                values[target.id] = ast.literal_eval(node.value)
    missing = names - set(values)
    if missing:
        raise ValueError("missing constants in %s: %s" % (filename, ", ".join(sorted(missing))))
    return values


def literal_assignments(path, names):
    return literal_assignments_text(path.read_text(encoding="utf-8"), names, str(path))


def virtual_part(name, values):
    raw = json.dumps(values, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"sha256": sha256_bytes(raw), "files": [], "values": values,
            "source": name}


def is_os_junk(path):
    return path.name in {".DS_Store", "Thumbs.db", "desktop.ini"} or path.name.startswith("._")


def fingerprint(repo, subject):
    scripts = sorted(p for p in (subject / "scripts").rglob("*.py") if not is_os_junk(p))
    templates = sorted(p for p in (subject / "references").rglob("*") if not is_os_junk(p))
    fixtures = sorted(p for p in (repo / "fixtures").rglob("*")
                      if p.is_file() and not is_os_junk(p))
    acceptance = [repo / "docs" / "acceptance-rule-v1.1.md",
                  repo / "docs" / "expected-answers-v0.2.md"]
    extract = subject / "scripts" / "extract_form.py"
    constants = literal_assignments(extract, {"DEFAULT_MODEL", "PROMPT_VERSION", "SYSTEM_PROMPT"})

    parts = {}
    for name, paths in (("code", scripts), ("template", templates),
                        ("fixtures", fixtures), ("acceptance_rule", acceptance)):
        entries = file_entries(repo, paths)
        parts[name] = {"sha256": combined_digest(entries), "files": entries}
    parts["prompt"] = virtual_part(
        str(extract.relative_to(repo)),
        {"prompt_version": constants["PROMPT_VERSION"],
         "system_prompt": constants["SYSTEM_PROMPT"]})
    parts["model"] = virtual_part(
        str(extract.relative_to(repo)), {"model_id": constants["DEFAULT_MODEL"]})
    overall = sha256_bytes(json.dumps(
        {key: value["sha256"] for key, value in sorted(parts.items())},
        sort_keys=True).encode("utf-8"))
    return {"sha256": overall, "parts": parts}


def run_unittests(repo):
    cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
    proc = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True)
    output = proc.stdout + proc.stderr
    cases = {}
    line_re = re.compile(r"^(\S+) \(([^)]+)\) \.\.\. (ok|FAIL|ERROR|skipped.*)$")
    for line in output.splitlines():
        match = line_re.match(line.strip())
        if match:
            method, owner, result = match.groups()
            status = "pass" if result == "ok" else ("skip" if result.startswith("skipped") else "fail")
            # Python 3.11+ includes the method in the parenthesized test id.
            key = owner if owner.endswith("." + method) else owner + "." + method
            cases[key] = status
    summary = re.search(r"Ran (\d+) tests?", output)
    count = int(summary.group(1)) if summary else len(cases)
    if proc.returncode != 0 and not any(value == "fail" for value in cases.values()):
        cases["test command"] = "fail"
    return {"command": cmd, "returncode": proc.returncode, "count": count,
            "passed": sum(value == "pass" for value in cases.values()),
            "cases": dict(sorted(cases.items())), "output": output[-4000:]}


def replay_expected(repo, subject):
    quote = subject / "scripts" / "quote.py"
    fixtures = repo / "fixtures"
    cases = {}
    with tempfile.TemporaryDirectory(prefix="release-check-replay-") as tmp:
        for request_id, expected in sorted(EXPECTED.items()):
            out = Path(tmp) / request_id
            cmd = [sys.executable, str(quote), "--form", str(fixtures / "forms" / (request_id + ".json")),
                   "--received", expected["received"], "--sheet-dir", str(fixtures / "rate_sheets"),
                   "--calendars", str(fixtures / "calendars"), "--margins", str(fixtures / "margins.csv"),
                   "--out", str(out)]
            proc = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True)
            observed = {"outcome": "script_error", "rates": [], "end_dates": []}
            result_file = out / "result.json"
            if result_file.is_file():
                result = json.loads(result_file.read_text(encoding="utf-8"))
                observed = {"outcome": result.get("outcome"),
                            "rates": [item.get("customer_rate") for item in result.get("items", [])],
                            "end_dates": [item.get("end_date") for item in result.get("items", [])]}
            passed = observed == {key: expected[key] for key in ("outcome", "rates", "end_dates")}
            cases[request_id] = {"status": "pass" if passed else "fail",
                                 "expected": {key: expected[key] for key in ("outcome", "rates", "end_dates")},
                                 "observed": observed, "returncode": proc.returncode}
    return {"count": len(cases), "passed": sum(v["status"] == "pass" for v in cases.values()),
            "cases": cases}


def run_model_eval(repo, model):
    runner = repo / "evals" / "step1-extraction" / "run_eval.py"
    with tempfile.TemporaryDirectory(prefix="release-check-model-") as tmp:
        cmd = [sys.executable, str(runner), "--model", model, "--repeats", "1", "--out", tmp]
        proc = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True)
        results_file = Path(tmp) / "results.json"
        rows = json.loads(results_file.read_text(encoding="utf-8")) if results_file.is_file() else []
    cases = {}
    for row in rows:
        key = "%s run%s" % (row.get("request"), row.get("run"))
        cases[key] = "pass" if row.get("step1_correct") else "fail"
    if proc.returncode != 0 and not cases:
        cases["model eval command"] = "fail"
    return {"command": cmd, "returncode": proc.returncode, "count": len(cases),
            "passed": sum(v == "pass" for v in cases.values()), "cases": dict(sorted(cases.items())),
            "output": (proc.stdout + proc.stderr)[-4000:]}


def git_run(repo, args, text=True):
    try:
        return subprocess.run(["git"] + args, cwd=str(repo), capture_output=True, text=text)
    except OSError:
        return None


def run_version_evidence(repo, subject, skill_commit, current_fingerprint):
    """Compare a run's committed parts with the actual files under test."""
    evidence = {"skill_commit": skill_commit, "changed_parts": [], "error": None}
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", skill_commit or ""):
        evidence["error"] = "invalid or missing skill commit"
        return evidence

    exists = git_run(repo, ["cat-file", "-e", skill_commit + "^{commit}"])
    if exists is None:
        evidence["error"] = "git is unavailable"
        return evidence
    if exists.returncode != 0:
        evidence["error"] = "commit is unavailable"
        return evidence

    relative_subject = subject.relative_to(repo).as_posix()
    extract_path = relative_subject + "/scripts/extract_form.py"
    acceptance_paths = {"docs/acceptance-rule-v1.1.md", "docs/expected-answers-v0.2.md"}
    listing = git_run(repo, ["ls-tree", "-r", "--name-only", "-z", skill_commit, "--",
                           relative_subject + "/scripts", relative_subject + "/references"] +
                      sorted(acceptance_paths))
    if listing is None or listing.returncode != 0:
        evidence["error"] = "git could not read the run commit"
        return evidence
    historical_files = {}
    for path in filter(None, listing.stdout.split("\0")):
        if path.startswith(relative_subject + "/scripts/") and (
                not path.endswith(".py") or is_os_junk(Path(path))):
            continue
        if path.startswith(relative_subject + "/references/") and is_os_junk(Path(path)):
            continue
        blob = git_run(repo, ["show", "%s:%s" % (skill_commit, path)], text=False)
        if blob is None or blob.returncode != 0:
            evidence["error"] = "git could not read a run file"
            return evidence
        historical_files[path] = blob.stdout

    changed = []
    for part, prefix in (("code", relative_subject + "/scripts/"),
                         ("template", relative_subject + "/references/"),
                         ("acceptance_rule", None)):
        entries = [{"path": path, "sha256": sha256_bytes(data)}
                   for path, data in sorted(historical_files.items())
                   if (path.startswith(prefix) if prefix else path in acceptance_paths)]
        if combined_digest(entries) != current_fingerprint["parts"][part]["sha256"]:
            changed.append(part)

    # Compare literal values separately so a code-only edit does not claim
    # that the pinned prompt or model changed too.
    virtual_names = {"prompt": {"PROMPT_VERSION", "SYSTEM_PROMPT"},
                     "model": {"DEFAULT_MODEL"}}
    for part, names in virtual_names.items():
        try:
            old_values = literal_assignments_text(
                historical_files[extract_path].decode("utf-8"), names, extract_path)
        except (KeyError, SyntaxError, ValueError, UnicodeError):
            changed.append(part)
            continue
        current_values = current_fingerprint["parts"][part]["values"]
        normalized = ({"prompt_version": old_values["PROMPT_VERSION"],
                       "system_prompt": old_values["SYSTEM_PROMPT"]}
                      if part == "prompt" else {"model_id": old_values["DEFAULT_MODEL"]})
        if normalized != current_values:
            changed.append(part)

    evidence["changed_parts"] = sorted(changed)
    return evidence


def normalize_run_id(run_id):
    return (run_id or "").strip().upper()


def qualifying_runs(repo, subject, current_fingerprint):
    path = repo / "runs" / "runs.csv"
    if not path.is_file():
        return {"skill_commit": None, "candidate_run_ids": [], "run_ids": [],
                "duplicate_run_ids": [], "invalid_run_ids": [], "changed_parts": [], "error": None}
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    invalid_ids = []
    valid_rows = []
    for row in rows:
        raw_id = row.get("run_id") or ""
        run_id = normalize_run_id(raw_id)
        if not re.fullmatch(r"RUN-[0-9]{8}-[0-9]{2}", run_id):
            invalid_ids.append(raw_id)
            continue
        row["run_id"] = run_id
        valid_rows.append(row)
    rows = valid_rows
    eligible = [row for row in rows if row.get("verdict") == "pass" and row.get("counts_toward_six") == "yes"]
    if not eligible:
        return {"skill_commit": None, "candidate_run_ids": [], "run_ids": [],
                "duplicate_run_ids": [], "invalid_run_ids": sorted(set(invalid_ids)),
                "changed_parts": [], "error": None}
    latest_generation = eligible[-1].get("skill_commit")
    run_counts = {}
    for row in eligible:
        if row.get("skill_commit") == latest_generation:
            run_id = row["run_id"]
            run_counts[run_id] = run_counts.get(run_id, 0) + 1
    candidate_ids = list(run_counts)[-REQUIRED_SUPERVISED_RUNS:]
    evidence = run_version_evidence(repo, subject, latest_generation, current_fingerprint)
    evidence["invalid_run_ids"] = sorted(set(invalid_ids))
    evidence["duplicate_run_ids"] = sorted(run_id for run_id, count in run_counts.items() if count > 1)
    evidence["candidate_run_ids"] = candidate_ids
    evidence["run_ids"] = (candidate_ids if not evidence["changed_parts"] and not evidence["error"] else [])
    return evidence


def changed_parts(baseline, current):
    if not baseline:
        return []
    old = baseline["fingerprint"]["parts"]
    return sorted(name for name, part in current["parts"].items()
                  if name not in old or old[name].get("sha256") != part.get("sha256"))


def regressions(baseline, tests, replay, model_eval):
    if not baseline:
        return []
    found = []
    old_tests = baseline.get("tests", {}).get("cases", {})
    for key, old_status in old_tests.items():
        if old_status == "pass" and tests["cases"].get(key) != "pass":
            found.append("offline test: " + key)
    old_replay = baseline.get("expected_answer_replay", {}).get("cases", {})
    for key, old_case in old_replay.items():
        old_status = old_case.get("status") if isinstance(old_case, dict) else old_case
        new_case = replay["cases"].get(key, {})
        if old_status == "pass" and new_case.get("status") != "pass":
            found.append("expected answer: " + key)
    old_model = baseline.get("model_eval") or {}
    if model_eval and old_model:
        for key, old_status in old_model.get("cases", {}).items():
            if old_status == "pass" and model_eval["cases"].get(key) != "pass":
                found.append("model eval: " + key)
    return found


def report_markdown(subject_name, day, verdict, changes, regressions_found,
                    tests, replay, model_eval, supervised_count, reset, run_evidence):
    reset_note = ""
    if reset:
        reset_note = (" (reset by this change)" if RESET_PARTS.intersection(changes) else
                      " (reset: the logged runs were on an earlier version)")
    lines = ["# Release check: %s" % subject_name, "", "Date: %s" % day,
             "Verdict: **%s**" % verdict, "Human sign-off: **NOT SIGNED**", "",
             "## Plain-language result", ""]
    if verdict == "RELEASE":
        lines.append("All offline checks passed, no baseline regression was found, and the supervised-run gate is satisfied. A person must still sign the release.")
    elif verdict == "HOLD":
        if reset:
            lines.append("All offline checks passed, but a change under test reset the supervised-run gate. Do not release until six new supervised runs pass and a person signs.")
        else:
            lines.append("All offline checks passed, but fewer than six supervised runs qualify. Do not release until six supervised runs pass and a person signs.")
    else:
        lines.append("At least one offline case regressed or failed. Do not release.")
    lines += ["", "## Change control", "",
              "Changed parts: %s" % (", ".join(changes) if changes else "none"),
              "Regressions: %s" % (", ".join(regressions_found) if regressions_found else "none"),
              "Supervised run count: %d of %d%s" % (
                  supervised_count, REQUIRED_SUPERVISED_RUNS,
                  reset_note), ""]
    if run_evidence["invalid_run_ids"]:
        lines.append("Invalid supervised run IDs (not counted): %s" %
                     ", ".join(repr(run_id) for run_id in run_evidence["invalid_run_ids"]))
        lines.append("")
    if run_evidence["duplicate_run_ids"]:
        lines.append("Duplicate supervised run IDs (counted at most once): %s" %
                     ", ".join(run_evidence["duplicate_run_ids"]))
        lines.append("")
    if run_evidence["skill_commit"]:
        lines.append("Counted runs used commit: `%s`" % run_evidence["skill_commit"])
        run_changes = run_evidence["changed_parts"]
        changed_text = ("unavailable (%s)" % run_evidence["error"]
                        if run_evidence["error"] else
                        (", ".join(run_changes) if run_changes else "none"))
        lines.append("Parts changed since that commit: %s" % changed_text)
        if run_evidence["error"]:
            lines.append("Run-version check: %s; these runs do not count." % run_evidence["error"])
        lines.append("")
    earlier_version = bool(run_evidence["candidate_run_ids"] and
                           (run_evidence["changed_parts"] or run_evidence["error"]))
    if earlier_version:
        lines.append("counted runs were on an earlier version; supervised run count is 0 of 6 for the current version")
        lines.append("")
    if reset and supervised_count == 0:
        lines.append("supervised run count resets to 0 of 6")
        lines.append("")
    lines += ["## Offline test suite", "",
              "%d of %d passed." % (tests["passed"], tests["count"]), "",
              "| Case | Result |", "|---|---|"]
    for key, status in tests["cases"].items():
        lines.append("| `%s` | %s |" % (key.replace("|", "\\|"), status.upper()))
    lines += ["", "## Expected-answer replay", "",
              "%d of %d passed." % (replay["passed"], replay["count"]), "",
              "| Case | Result |", "|---|---|"]
    for key, item in replay["cases"].items():
        lines.append("| `%s` | %s |" % (key, item["status"].upper()))
    lines += ["", "## Step-1 model eval", ""]
    if model_eval is None:
        lines.append("Not run. It is off by default; use `--with-model` to call the pinned model.")
    else:
        lines += ["%d of %d passed." % (model_eval["passed"], model_eval["count"]), "",
                  "| Case | Result |", "|---|---|"]
        for key, status in model_eval["cases"].items():
            lines.append("| `%s` | %s |" % (key, status.upper()))
    lines += ["", "## Human release decision", "",
              "Decision: ____________________", "",
              "Name/date: ____________________", ""]
    return "\n".join(lines)


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(str(temp), str(path))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill", help="skill folder to check, for example skills/rate-quote")
    parser.add_argument("--record-release", action="store_true",
                        help="record the passing current state as the released manifest")
    parser.add_argument("--with-model", action="store_true",
                        help="also run the networked step-1 model eval (off by default)")
    args = parser.parse_args(argv)

    subject = Path(args.skill).resolve()
    if not subject.is_dir():
        parser.error("skill folder does not exist: %s" % args.skill)
    repo = subject.parent.parent
    if subject.name == "sanctions-news":
        if args.with_model or args.record_release:
            parser.error("sanctions-news checks offline packaging only; no model or release-recording flags")
        from sanctions_news import check_package
        return check_package(subject)
    if subject.name != "rate-quote":
        parser.error("this release-check version supports rate-quote and sanctions-news only")
    release = subject / "release"
    manifest_path = release / "manifest.json"
    baseline = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else None

    current_fingerprint = fingerprint(repo, subject)
    tests = run_unittests(repo)
    replay = replay_expected(repo, subject)
    model_id = current_fingerprint["parts"]["model"]["values"]["model_id"]
    model_eval = run_model_eval(repo, model_id) if args.with_model else None
    changes = changed_parts(baseline, current_fingerprint)
    found = regressions(baseline, tests, replay, model_eval)

    current_failures = ["offline test: " + key for key, value in tests["cases"].items() if value == "fail"]
    current_failures += ["expected answer: " + key for key, value in replay["cases"].items()
                         if value["status"] == "fail"]
    if model_eval:
        current_failures += ["model eval: " + key for key, value in model_eval["cases"].items()
                             if value == "fail"]
    found = sorted(set(found + current_failures))

    reset = bool(RESET_PARTS.intersection(changes))
    run_evidence = qualifying_runs(repo, subject, current_fingerprint)
    run_ids = run_evidence["run_ids"]
    version_mismatch = bool(run_evidence["candidate_run_ids"] and
                            (run_evidence["changed_parts"] or run_evidence["error"]))
    reset = reset or version_mismatch
    if reset:
        old_ids = {normalize_run_id(run_id) for run_id in
                   baseline.get("supervised_runs", {}).get("run_ids", [])} if baseline else set()
        run_ids = [run_id for run_id in run_ids if normalize_run_id(run_id) not in old_ids]
    supervised_count = min(len(run_ids), REQUIRED_SUPERVISED_RUNS)
    if found or tests["returncode"] != 0:
        verdict = "BLOCK"
    elif supervised_count < REQUIRED_SUPERVISED_RUNS:
        verdict = "HOLD"
    else:
        verdict = "RELEASE"

    day = date.today().isoformat()
    report = report_markdown(subject.name, day, verdict, changes, found, tests, replay,
                             model_eval, supervised_count, reset, run_evidence)
    release.mkdir(parents=True, exist_ok=True)
    report_path = release / ("report-%s.md" % day)
    report_path.write_text(report, encoding="utf-8")

    if args.record_release:
        if verdict != "RELEASE":
            print("Refusing to record a %s result as released." % verdict, file=sys.stderr)
        else:
            manifest = {"schema_version": SCHEMA_VERSION, "skill": subject.name,
                        "released_on": day, "fingerprint": current_fingerprint,
                        "tests": {key: tests[key] for key in ("command", "returncode", "count", "passed", "cases")},
                        "expected_answer_replay": replay, "model_eval": model_eval,
                        "supervised_runs": {"count": supervised_count,
                                            "required": REQUIRED_SUPERVISED_RUNS,
                                            "run_ids": run_ids,
                                            "skill_commit": run_evidence["skill_commit"],
                                            "changed_parts_since": run_evidence["changed_parts"],
                                            "version_matches_current": not version_mismatch}}
            atomic_json(manifest_path, manifest)
            print("Recorded released manifest: %s" % manifest_path.relative_to(repo))

    print("Verdict: %s" % verdict)
    print("Offline tests: %d/%d passed" % (tests["passed"], tests["count"]))
    print("Expected-answer replay: %d/%d passed" % (replay["passed"], replay["count"]))
    print("Supervised runs: %d/%d" % (supervised_count, REQUIRED_SUPERVISED_RUNS))
    print("Report: %s" % report_path.relative_to(repo))
    return 0 if verdict == "RELEASE" else (2 if verdict == "HOLD" else 1)


if __name__ == "__main__":
    sys.exit(main())
