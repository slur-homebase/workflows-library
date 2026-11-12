#!/usr/bin/env python3
"""Replay original answer rows followed by additive round-3 fixture checks."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from research import RESULT_VALUES, identity_readings, render, read_article, sentences


DEFAULT_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SCRIPT = Path(__file__).with_name("research.py")


def forbidden_output(report, markdown, fixtures):
    """Return true on prohibited identifiers, invented denial or real-name tokens."""
    output = json.dumps(report) + markdown
    if re.search(r"(?i)registration[_ ]number|SYN-[A-Z]+-\d+|date[_ ]of[_ ]birth|\bdob\b|\bborn\b|nationality|national of", output):
        return True
    subjects = json.loads((fixtures / "subjects.json").read_text(encoding="utf-8"))["subjects"]
    for subject in subjects:
        if any(subject[field] in output for field in ("registration_number", "date_of_birth") if field in subject):
            return True
    articles = [read_article(p) for p in sorted((fixtures / "articles").glob("*.md"))]
    quoted = list(report["findings"]) + [f["resolution"] for f in report["findings"] if "resolution" in f]
    for word in ("denied", "admitted", "convicted", "exonerated"):
        grounded = any(re.search(r"(?i)\b" + word + r"\b", finding["quote"])
                       and any(finding["quote"] in article["body"] for article in articles)
                       for finding in quoted)
        if re.search(r"(?i)\b" + word + r"\b", output) and not grounded:
            return True
    if not report["findings"] and re.search(
            r"(?i)\b(?:clear|cleared|clearance)\b", output.replace("This is not a clearance.", "")):
        return True
    # Encoded deny-list from the owner brief. These are not fixture names.
    tokens = ("4d4153", "4d6f6e657461727920417574686f72697479", "4f464143", "4f465349", "554e",
              "53696e6761706f7265", "4d616c6179736961", "496e646f6e65736961", "4a6f686f72",
              "53696e6761706f726520437573746f6d73", "53696e6761706f726520506f6c696365",
              "436f6d6d65726369616c2041666661697273", "41435241", "53747261746567696320476f6f6473",
              "52657574657273", "537472616974732054696d6573", "427573696e6573732054696d6573",
              "426c6f6f6d62657267", "4a75726f6e67", "576f6f646c616e6473", "54756173", "50617369722050616e6a616e67")
    return any(re.search(r"(?i)(?<!\w)" + re.escape(bytes.fromhex(t).decode("ascii")) + r"(?!\w)", output)
               for t in tokens)


def reference_matches(expected, observed, markdown):
    return all(observed.get(k) == expected[k] for k in ("article_id", "quote", "date")) and all(
        expected[k] in markdown for k in ("article_id", "quote", "date"))


def statuses_match(expected, report, markdown):
    actual = {s["source_id"]: s for s in report["sources"]}
    if set(actual) != {s["source_id"] for s in expected["expected_source_statuses"]}:
        return False
    for source in expected["expected_source_statuses"]:
        found = actual[source["source_id"]]
        if any(found.get(f) != source[f] for f in ("execution", "freshness", "as_of", "article_ids_checked")):
            return False
        if found.get("result") != RESULT_VALUES[source["result"]]:
            return False
        if found.get("sample_result") != source["result"]:
            return False
        for field in ("execution", "result", "freshness"):
            if found.get("field_as_of", {}).get(field) != source["as_of"]:
                return False
            if field + ": " + found[field] + " | as_of: " + source["as_of"] not in markdown:
                return False
    gaps = {s["source_id"] for s in report["not_covered"]}
    return gaps == {s["source_id"] for s in expected["not_covered"] if s["source_id"]}


def check_finding(expected, report, markdown, fixtures=DEFAULT_FIXTURES):
    hits = [f for f in report["findings"] if f["article_id"] == expected["article_id"]]
    if len(hits) != 1:
        return False
    hit = hits[0]
    if not reference_matches(expected, hit, markdown):
        return False
    if hit.get("type") != expected["type"] or hit.get("state") != expected["state"]:
        return False
    if "event" in expected and hit.get("event") != expected["event"]:
        return False
    if hit["assessment"] not in markdown:
        return False
    article = read_article(fixtures / hit["fixture_file"])
    if "stage" in expected:
        stage_line = hit.get("story_evidence", {}).get("stage")
        if (hit.get("stage") != expected["stage"] or not stage_line
                or stage_line != expected["quote"] or stage_line not in article["body"].splitlines()):
            return False
    if any(line not in sentences(article["body"]) for line in hit.get("article_context", [])):
        return False
    if expected.get("kind") == "finding":
        context = [line for line in sentences(article["body"])
                   if any(phrase in line for phrase in
                          ("could not immediately confirm", "did not respond", "declined to comment"))]
        if hit.get("article_context") != context:
            return False
    match = hit["identity_check"]
    if match["decision"] != "matched" or len(match["matched_fields"]) < 2:
        return False
    if set(match["matched_fields"]) == {"name", "role", "employer", "age"}:
        if match["identity"] != "matched on name, role, employer and age":
            return False
    elif match["readings"] != identity_readings(report["subject"]) or match["chosen_reading"] is not None:
        return False
    elif "Three readings: " + " / ".join(identity_readings(report["subject"])) + ". Tool chooses none." not in markdown:
        return False
    # must_say is an instruction, not text to paste. Assert its factual and
    # forbidden-output requirements using the key's state and nested evidence.
    instruction = expected["must_say"].casefold()
    if "resolution" in expected:
        if not reference_matches(expected["resolution"], hit.get("resolution", {}), markdown):
            return False
        if "cleared on " + expected["resolution"]["date"] not in hit["assessment"]:
            return False
        if hit["event"] != "historical investigation":
            return False
    if "not proven conduct" in instruction:
        context = " ".join(hit.get("article_context", []))
        if not all(s in hit["assessment"] for s in ("not proven conduct", "No outcome is reported")):
            return False
        if not all(s in context for s in ("could not immediately confirm", "did not respond")):
            return False
    if "status unknown" in instruction:
        if "Dated finding, no follow-up found in supplied sources, status unknown." != hit["assessment"]:
            return False
        source = next(s for s in report["sources"] if s["source_id"] == hit["source_id"])
        if source["as_of"] not in markdown:
            return False
    return True


def check_trap(trap, report, markdown):
    kind = trap["type"]
    if kind == "same_name_different_person":
        excluded = {r["article_id"]: r for r in report["excluded_articles"]}
        findings = {f["article_id"] for f in report["findings"]}
        return all(e["article_id"] not in findings and e["article_id"] in excluded
                   and e["article_id"] not in {p["article_id"] for p in report["possible_matches"]}
                   and not any(e["article_id"] in (link["article_id"], link["to_article_id"])
                               for link in report.get("links", []))
                   and not excluded[e["article_id"]].get("links")
                   and not excluded[e["article_id"]].get("link")
                   and reference_matches(e, excluded[e["article_id"]], markdown)
                   and excluded[e["article_id"]]["identity_check"]["decision"] == "excluded"
                   and set(excluded[e["article_id"]]["identity_check"]["conflicting_fields"])
                   == {"role", "employer", "age"}
                   for e in trap["evidence"])
    if kind == "old_story_cleared":
        old, newer = trap["evidence"]
        hits = [f for f in report["findings"] if f["article_id"] == old["article_id"]]
        return len(hits) == 1 and hits[0]["state"] == "cleared" and reference_matches(
            old, hits[0], markdown) and reference_matches(newer, hits[0].get("resolution", {}), markdown)
    if kind in {"failed_source", "not_attempted_source", "stale_source"}:
        source = next(s for s in report["sources"] if s["source_id"] == trap["source_id"])
        if kind == "stale_source":
            hits = [f for f in report["findings"] if f["source_id"] == source["source_id"]]
            return (source["execution"], source["sample_result"], source["freshness"]) == (
                "completed", "finding", "stale") and bool(hits) and all(
                f["state"] == "historical status unknown" and "status unknown" in f["assessment"]
                and "no follow-up found in supplied sources" in f["assessment"] for f in hits)
        execution = "failed" if kind == "failed_source" else "not attempted"
        return source["execution"] == execution and source["result"] == "unavailable" and not source[
            "article_ids_checked"] and source["date_basis"] == "planned date only, nothing read"
    if kind == "nothing_found_with_gaps":
        remaining = (json.dumps(report) + markdown).replace("This is not a clearance.", "")
        return (not report["findings"] and report["summary"] == trap["must_say"]
                and trap["must_say"] in markdown
                and not re.search(r"\b(?:clear|cleared|clearance)\b", remaining, re.I))
    return False


def expected_findings(key, subject):
    """Keep the twelve baseline rows in place; add findings without moving them."""
    return subject["expected_findings"] + [
        row for row in key.get("round3_rows", [])
        if row["subject_id"] == subject["subject_id"] and row["kind"] == "finding"]


def canonical_links(links):
    """Only ordering of pairs is irrelevant; tiers and ordered reason lists are exact."""
    return sorted(links, key=lambda link: (link["article_id"], link["to_article_id"]))


def record_links(record):
    if "links" in record:
        return record["links"]
    return [record["link"]] if record.get("link") else []


def check_links(expected, report, markdown):
    """Reject missing/extra pairs, changed tiers/reasons and lost row attachments."""
    wanted = expected["expected_links"]
    actual = report.get("links")
    if not isinstance(actual, list) or canonical_links(actual) != canonical_links(wanted):
        return False
    pairs = [(link["article_id"], link["to_article_id"]) for link in actual]
    if len(set(pairs)) != len(pairs):
        return False
    for link in wanted:
        if link["tier"] not in markdown or not all(reason in markdown for reason in link["reasons"]):
            return False
    for group in ("findings", "comparisons"):
        records = report.get(group, [])
        if group == "findings":
            records = records + [record["resolution"] for record in records if "resolution" in record]
        for link in wanted:
            records_for_article = [record for record in records if record["article_id"] == link["article_id"]]
            if not records_for_article or not all(link in record_links(record) for record in records_for_article):
                return False
        for record in records:
            outgoing = [link for link in wanted if link["article_id"] == record["article_id"]]
            if canonical_links(record_links(record)) != canonical_links(outgoing):
                return False
            if outgoing and record.get('link') != {
                    key: value for key, value in outgoing[0].items() if key != 'article_id'}:
                return False
    for record in report["excluded_articles"] + report["possible_matches"]:
        if record_links(record):
            return False
    return True


def evaluate(fixtures, out, reader="script", records=None):
    key = json.loads((fixtures / "answer-key.json").read_text(encoding="utf-8"))
    rows, results = [], {}
    for expected in key["subjects"]:
        sid = expected["subject_id"]
        command = [sys.executable, str(SCRIPT), "--subject", sid, "--fixtures", str(fixtures),
                   "--out", str(out), "--reader", reader]
        if records is not None:
            command += ["--records", str(records)]
        proc = subprocess.run(command, capture_output=True, text=True)
        report, markdown = None, ""
        if proc.returncode == 0:
            report = json.loads((out / (sid + ".json")).read_text(encoding="utf-8"))
            markdown = (out / (sid + ".md")).read_text(encoding="utf-8")
        common = report is not None and not report.get("rejected_records") and statuses_match(expected, report, markdown)
        if report is not None:
            common = common and markdown == render(report)
            common = common and not forbidden_output(report, markdown, fixtures)
            common = common and sorted(f["article_id"] for f in report["findings"]) == sorted(
                f["article_id"] for f in expected_findings(key, expected))
        results[sid] = (common, report, markdown)
        for item in expected["expected_findings"] + expected["traps"]:
            passed = common and (check_finding(item, report, markdown, fixtures) if "state" in item
                                 else check_trap(item, report, markdown))
            rows.append({"row": item["id"], "subject": sid, "status": "PASS" if passed else "FAIL"})
        if proc.returncode:
            print(proc.stderr.strip(), file=sys.stderr)
    # Append only after all baseline rows, retaining their original global order.
    for item in key.get("round3_rows", []):
        sid = item["subject_id"]
        common, report, markdown = results[sid]
        if item["kind"] == "finding":
            passed = common and check_finding(item, report, markdown, fixtures)
        elif item["kind"] == "trap":
            passed = common and check_trap(item, report, markdown)
        elif item["kind"] == "link":
            expected = next(group for group in key['relationship_checks']
                            if group['subject_id'] == sid)
            passed = (common and check_links(expected, report, markdown)
                      and item['expected_link'] in report.get('links', []))
        else:
            passed = False
        rows.append({"row": item["id"], "subject": sid, "status": "PASS" if passed else "FAIL"})
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--out", type=Path, help="keep replay reports here")
    parser.add_argument("--reader", choices=("script", "model"), default="script")
    parser.add_argument("--records", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.out:
            rows = evaluate(args.fixtures, args.out, args.reader, args.records)
        else:
            with tempfile.TemporaryDirectory(prefix="sanctions-news-check-") as tmp:
                rows = evaluate(args.fixtures, Path(tmp), args.reader, args.records)
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print("Answer-key check failed: " + str(exc), file=sys.stderr)
        return 1
    print("Row    Subject  Result")
    for row in rows:
        print("{row:6} {subject:8} {status}".format(**row))
    passed = sum(r["status"] == "PASS" for r in rows)
    print(str(passed) + "/" + str(len(rows)) + " rows passed")
    key = json.loads((args.fixtures / "answer-key.json").read_text(encoding="utf-8"))
    expected_count = sum(len(subject["expected_findings"]) + len(subject["traps"])
                         for subject in key["subjects"]) + len(key.get("round3_rows", []))
    return 0 if expected_count > 0 and len(rows) == expected_count and passed == expected_count else 1


if __name__ == "__main__":
    sys.exit(main())
