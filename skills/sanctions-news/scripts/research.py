#!/usr/bin/env python3
"""Read invented local news fixtures. Script default; recorded model replay is offline."""

import argparse
from datetime import date
import importlib.util
import json
from pathlib import Path
import re
import sys


READINGS = ["same person", "different person", "not enough evidence"]
ENTITY_READINGS = ["same entity", "different entity", "not enough evidence"]
POSSIBLE_IDENTITY = "possible, not enough evidence"
RESULT_VALUES = {"finding": "possible hit", "no finding": "no hit",
                 "unavailable": "unavailable"}
STORY_FIELDS = {"part_in_story", "stage", "event_id"}
PARTS_IN_STORY = {"accused", "under investigation", "sanctioned", "sued someone",
                 "witness", "mentioned only", "not stated"}
STAGES = {"allegation", "investigation", "charge", "settlement", "designation or restriction",
          "case closed", "not stated"}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Repeated field: " + key)
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def read_article(path):
    """Parse the fixture's JSON-valued front matter, not general YAML."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("Missing front matter: " + path.name)
    end = lines.index("---", 1)
    pairs = []
    for line in lines[1:end]:
        key, value = line.split(": ", 1)
        pairs.append((key, json.loads(value)))
    meta = unique_object(pairs)
    base_fields = {"id", "source_id", "date", "headline", "subject_ids"}
    # All three fields are required together; the original schema remains valid
    # for frozen phase-3 replay. Never infer missing metadata from the body.
    if set(meta) not in (base_fields, base_fields | STORY_FIELDS):
        raise ValueError("Unexpected article fields: " + path.name)
    if STORY_FIELDS <= set(meta):
        if not isinstance(meta["part_in_story"], str) or meta["part_in_story"] not in PARTS_IN_STORY:
            raise ValueError("Invalid part_in_story: " + path.name)
        if not isinstance(meta["stage"], str) or meta["stage"] not in STAGES:
            raise ValueError("Invalid stage: " + path.name)
        if not isinstance(meta["event_id"], str) or not re.fullmatch(r"EVT-[0-9]{3}", meta["event_id"]):
            raise ValueError("Invalid event_id: " + path.name)
    if meta["id"] != path.stem:
        raise ValueError("Article id differs from filename: " + path.name)
    date.fromisoformat(meta["date"])
    return {**meta, "body": "\n".join(lines[end + 1:]).strip(),
            "fixture_file": "articles/" + path.name}


def sentences(text):
    """Keep company abbreviations intact in verbatim sample sentences.

    A final Ltd. ends a sentence at end of text or before a capitalized sentence;
    lowercase continuation (of/in/on) belongs to the same sentence.
    """
    protected = {m.end() - 1 for m in re.finditer(
        r"\b(?:Pte|Co)\.(?=\s*(?:,\s*)?Ltd\.)|\bLtd\.(?=\s+[a-z]|[,;:])", text)}
    result, start = [], 0
    for mark in re.finditer(r"[.!?]+", text):
        if mark.start() in protected:
            continue
        chunk = text[start:mark.end()].strip()
        if chunk:
            result.append(chunk)
        start = mark.end()
    if text[start:].strip():
        result.append(text[start:].strip())
    return result


def age_at(subject, article_date):
    """Compute completed years on publication, never return the input date."""
    birth = date.fromisoformat(subject["date_of_birth"])
    day = date.fromisoformat(article_date)
    if day < birth:
        raise ValueError("Article predates the subject")
    return str(day.year - birth.year - ((day.month, day.day) < (birth.month, birth.day)))


def stated_identity(subject, text):
    """Read only the supplied sample's explicit name and appositive grammar."""
    name = subject["name"]
    named = re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text)
    if not named:
        return None
    stated = {}
    if subject["type"] == "company":
        context = re.match(r", an? ([^,\n]+),", text[named.end():])
        if context:
            stated["profile"] = context[1]
        # Frozen phase-3 country grammar only. Current subjects have no place fields.
        elif "country" in subject:
            context = re.match(r"\s+of\s+([A-Z][\w-]*)", text[named.end():])
            if context:
                stated["country"] = context[1]
    else:
        clause = re.match(
            r",\s+(?:(\d{1,3}),\s+)?(?:an?\s+)?"
            r"((?:\bPte\.\s+Ltd\.|\bCo\.,\s+Ltd\.|[^,.\n])+)",
            text[named.end():])
        if clause:
            value = re.split(r"\s+on\s+\d{4}-\d{2}-\d{2}", clause[2])[0]
            value = value.split(" in ", 1)[0]  # Ignore legacy location prose.
            parts = re.fullmatch(r"(.+?)(?: at (.+))?", value)
            if parts:
                for field, found in zip(("role", "employer"), parts.groups()):
                    if found:
                        stated[field] = found.strip()
            if clause[1]:
                stated["age"] = clause[1]
    return stated


def identity(subject, text, article_date=None):
    stated = stated_identity(subject, text)
    if stated is None:
        return {"decision": "not named", "matched_fields": [], "stated_fields": {}}
    expected = dict(subject)
    if "age" in stated:
        if article_date is None:
            raise ValueError("Publication date required for stated age")
        expected["age"] = age_at(subject, article_date)
    return match_identity(expected, subject["name"], stated)


def identity_readings(subject):
    return list(ENTITY_READINGS if subject["type"] == "company" else READINGS)


def match_identity(subject, name, stated):
    """Apply the same identity rules to script-parsed or model-read fields."""
    if name.casefold() != subject["name"].casefold():
        return {"decision": "not named", "matched_fields": [], "stated_fields": {}}
    matched = ["name"]
    conflicts = [f for f, value in stated.items()
                 if str(value).casefold() != str(subject.get(f, "")).casefold()]
    matched += [f for f in stated if f not in conflicts]
    decision = "excluded" if conflicts else ("matched" if len(matched) > 1 else "insufficient")
    full = {"name", "role", "employer", "age"} <= set(matched)
    return {"decision": decision, "matched_fields": matched,
            "stated_fields": stated,
            "conflicting_fields": conflicts,
            "identity": ("matched on name, role, employer and age" if full else
                         "matched on " + ", ".join(matched)),
            "readings": identity_readings(subject) if not full and decision in {"matched", "insufficient"} else [],
            "chosen_reading": None}


def classify(quote):
    """Classify wording, never a subject id, headline or answer-key row."""
    lower = quote.casefold()
    if not re.search(r"\bsanctions?\b", lower):
        return "not a sanctions event"
    if re.search(r"\b(cleared|closed|delisted)\b", lower):
        return "delisting or case closed"
    if re.search(r"\b(fined|penalty|settlement|settled)\b", lower):
        return "penalty or settlement"
    if re.search(r"\b(investigating|investigation|inquiry)\b", lower):
        return "open investigation"
    if re.search(r"\b(designated|imposed|restriction)\b", lower):
        return "designation"
    return "not a sanctions event"


def evidence(article, quote, source):
    return {"article_id": article["id"], "source_id": source["id"],
            "source": source["name"], "fixture_file": article["fixture_file"],
            "date": article["date"], "quote": quote, **story_context(article)}


def story_context(article):
    """Copy source categories; locate supporting original lines, never classify.

    This deliberately small grammar covers the invented sample. A category with
    no supporting wording retains its source value but gets no invented quote.
    The legacy schema stays untouched, including historical model replay.
    """
    if not STORY_FIELDS <= set(article):
        return {}
    patterns = {
        "part_in_story": {
            "accused": r"\b(?:accused|alleged|alleges)\b",
            "under investigation": r"\b(?:is investigating|under investigation)\b|\bfaces\b.*\b(?:investigation|inquiry)\b",
            "sanctioned": r"\bdesignated\b|\bimposed\b.*\brestriction\b",
            "sued someone": r"\b(?:sued|filed a lawsuit|brought a claim)\b",
            "witness": r"\b(?:witness|testified)\b",
            "mentioned only": r"\b(?:opened|presented|showed|spoke|ran|updated|shared|donated|changed|prepared|planned|visited)\b",
        },
        "stage": {
            "allegation": r"\b(?:allegation|alleged|alleges|accused)\b",
            "investigation": r"\b(?:investigating|investigation|inquiry)\b",
            "charge": r"\b(?:charged|charges|indicted|indictment)\b",
            "settlement": r"\bagreed to settle\b",
            "designation or restriction": r"\b(?:designated|imposed)\b.*\brestriction\b",
            "case closed": r"\b(?:cleared|closed|delisted)\b",
        },
    }
    supporting = {}
    for field, choices in patterns.items():
        pattern = choices.get(article[field])
        supporting[field] = next(
            (line for line in article["body"].splitlines()
             if pattern and re.search(pattern, line, re.IGNORECASE)), None)
    return {**{field: article[field] for field in sorted(STORY_FIELDS)},
            "story_evidence": supporting}


def validate_evidence(article, quote, fields):
    """Ground copied fields in body text, not metadata or model claims."""
    errors = []
    if not isinstance(quote, str) or quote not in sentences(article["body"]):
        errors.append("non-verbatim quote")
    for field, value in fields.items():
        if value is not None and (not isinstance(value, str) or not value
                                  or value not in article["body"]):
            errors.append("ungrounded field: " + field)
    return errors


def article_context(article):
    """Copy verification limits and responses without inventing a denial."""
    return [s for s in sentences(article["body"])
            if "could not immediately confirm" in s
            or "did not respond" in s or "declined to comment" in s]


def same_case(earlier, later):
    """Require an affirmative case reference, same authority, topic and order."""
    old, new = earlier["quote"], later["quote"]
    authority = re.search(r", the (.+?) is investigating\b", old)
    closing = re.match(r"The (.+?) announced that\b", new)
    old_order = re.search(r"under the (.+? Order \d{4})", old)
    new_order = re.search(r"under the (.+? Order \d{4})", new)
    link = re.search(
        r"The announcement identified the ([\w -]+) inquiry first reported by "
        + re.escape(earlier["source"]) + " on " + re.escape(earlier["date"]) + r"\.",
        later["body"])
    topic = re.search(r"case over (.+?) under the", new)
    old_words = set(re.findall(r"\b[a-z]{4,}\b", old.casefold()))
    shared_topic = (set(re.findall(r"\b[a-z]{4,}\b", topic[1].casefold())) & old_words
                    if topic else set())
    return bool(earlier["date"] < later["date"]
                and link and len(shared_topic) >= 2
                and authority and closing and authority[1] == closing[1]
                and old_order and new_order and old_order[1] == new_order[1])


MATTER_STOP_WORDS = frozenset("""
according after against agreed agency also announced apparent article before
being business case civil comment company concerning could country date dated
declined delisted described designated following from further imposed inquiry investigating investigation
liability lifted matter name news office order outlet over potential publication reported
report reports said same sanctions settle settlement source stated subject suspicion
that their them then there these they this through under violations were when
which while with words would year
""".split())


def written_authority(quote):
    """Copy the authority before a sample action, preserving spelling and case."""
    match = re.search(
        r"\b[Tt]he ([A-Z][A-Za-z -]+?) "
        r"(?=is investigating\b|announced that\b|said\b|imposed\b|designated\b|delisted\b)",
        quote)
    return match[1] if match else None


def written_orders(quote):
    return set(re.findall(r"\b(?:under the|of the) ([A-Z][A-Za-z -]+? Order \d{4})", quote))


def matter_words(record, subject, outlet_names):
    """Reproducible lexical evidence from the exact finding sentence only.

    Remove subject/outlet tokens wherever they occur, and authority/order words,
    so a shared legal citation or reporter boilerplate cannot pass the word gate.
    No stemming, synonym expansion, event metadata or answer key is used.
    """
    tokens = lambda text: set(re.findall(r"\b[a-z]{4,}\b", text.casefold()))
    excluded = tokens(subject["name"])
    for name in outlet_names:
        excluded.update(tokens(name))
    authority = written_authority(record["quote"])
    if authority:
        excluded.update(tokens(authority))
    for order in written_orders(record["quote"]):
        excluded.update(tokens(order))
    return tokens(record["quote"]) - excluded - MATTER_STOP_WORDS


def article_links(candidates, subject, outlet_names):
    """Annotate relationships only. Never merge findings or infer a closure."""
    result = []
    ordered = sorted(candidates, key=lambda c: (c["date"], c["article_id"], c["quote"]))
    seen = set()
    for later in ordered:
        for earlier in ordered:
            pair = (later["article_id"], earlier["article_id"])
            if pair in seen or earlier["date"] >= later["date"]:
                continue
            if any(c["identity_check"]["decision"] != "matched" for c in (earlier, later)):
                continue
            authority = written_authority(earlier["quote"])
            if not authority or authority != written_authority(later["quote"]):
                continue
            orders = sorted(written_orders(earlier["quote"]) & written_orders(later["quote"]))
            shared = sorted(matter_words(earlier, subject, outlet_names)
                            & matter_words(later, subject, outlet_names))
            confirmed = (earlier["event"] == "open investigation"
                         and later["event"] == "delisting or case closed"
                         and same_case(earlier, later))
            if not confirmed and not orders and len(shared) < 3:
                continue
            reasons = ["Matched subject identity: " + subject["name"],
                       "Same authority: " + authority,
                       "Publication date order: " + earlier["date"] + " < " + later["date"]]
            reasons += ["Same legal order: " + order for order in orders]
            if len(shared) >= 3:
                reasons.append("Shared matter words: " + ", ".join(shared))
            if confirmed:
                reasons.append("Explicit earlier-report reference: " + earlier["source"]
                               + " on " + earlier["date"])
            result.append({"article_id": later["article_id"], "to_article_id": earlier["article_id"],
                           "tier": "CONFIRMED" if confirmed else "SUGGESTED", "reasons": reasons})
            seen.add(pair)
    return sorted(result, key=lambda link: (link["article_id"], link["to_article_id"]))


def research(subject_id, fixtures, reader="script", records=None, compute_links=True):
    fixtures = Path(fixtures)
    subjects = read_json(fixtures / "subjects.json")["subjects"]
    subject = next((s for s in subjects if s["id"] == subject_id), None)
    if subject is None:
        raise ValueError("Unknown subject id")
    plan = read_json(fixtures / "sources.json")
    run_day = date.fromisoformat(plan["run_date"])
    limit = plan["freshness_rule"]["max_age_days"]
    sources = {s["id"]: s for s in plan["sources"]}
    if len(sources) != len(plan["sources"]):
        raise ValueError("Repeated source id")
    for source in sources.values():
        age = (run_day - date.fromisoformat(source["as_of"])).days
        if age < 0 or source["freshness"] != ("stale" if age > limit else "current"):
            raise ValueError("Snapshot freshness disagrees with rule: " + source["id"])
        if source["execution"] not in {"completed", "failed", "not attempted"}:
            raise ValueError("Invalid execution: " + source["id"])
        if source["execution"] != "completed" and source["result"] != "unavailable":
            raise ValueError("Unavailable source has a result: " + source["id"])
    articles = [read_article(p) for p in sorted((fixtures / "articles").glob("*.md"))]
    if len({a["id"] for a in articles}) != len(articles):
        raise ValueError("Repeated article id")
    for article in articles:
        source = sources[article["source_id"]]
        if article["date"] > source["as_of"]:
            raise ValueError("Article newer than snapshot: " + article["id"])
    model_records = None
    rejected = []
    if reader == "model":
        if records is None:
            raise ValueError("Model reader requires --records; research never makes live calls")
        from model_reader import load_records
        model_records, rejected = load_records(records, articles)
    elif reader != "script":
        raise ValueError("Unknown reader")
    checked = {sid: [] for sid in sources}
    candidates, possible_matches, exclusions, non_events = [], [], [], []
    for article in articles:
        source = sources[article["source_id"]]
        if source["execution"] != "completed":
            continue
        checked[source["id"]].append(article["id"])
        if model_records is None:
            readings = [(quote, identity(subject, quote, article["date"]), classify(quote))
                        for quote in sentences(article["body"])]
        else:
            reading = model_records.get(article["id"])
            if reading is None:
                continue
            if subject["type"] == "company":
                fields = {"country": reading["country"]} if reading["country"] is not None else {}
            else:
                fields = {f: reading[f] for f in ("role", "employer") if reading[f] is not None}
            readings = [(reading["quote"], match_identity(subject, reading["name"], fields),
                         reading["event_type"])]
        for quote, match, event in readings:
            if match["decision"] == "not named":
                continue
            record = {**evidence(article, quote, source), "identity_check": match}
            if match["decision"] == "insufficient":
                possible_matches.append({**record, "type": "sanctions", "event": event,
                                         "state": "identity unconfirmed",
                                         "assessment": "Human review required.",
                                         "identity_status": POSSIBLE_IDENTITY,
                                         "article_context": article_context(article)})
            elif match["decision"] == "excluded":
                record["reason"] = "Exclude this sanctions inquiry: the stated identity fields differ."
                exclusions.append(record)
            elif event == "not a sanctions event":
                non_events.append({**record, "classification": event})
            else:
                candidates.append({**record, "event": event, "body": article["body"]})
    findings = []
    linked = set()
    for candidate in candidates:
        if candidate["event"] == "delisting or case closed":
            continue
        finding = {k: v for k, v in candidate.items() if k != "body"}
        finding["type"] = "sanctions"
        if candidate["event"] == "open investigation":
            resolutions = [c for c in candidates if c["event"] == "delisting or case closed"
                           and same_case(candidate, c)]
            if resolutions:
                resolution = max(resolutions, key=lambda c: (c["date"], c["article_id"]))
                finding["resolution"] = {k: v for k, v in resolution.items() if k != "body"}
                finding["state"] = "cleared"
                finding["event"] = "historical investigation"
                finding["assessment"] = "Historical allegation; case was cleared on " + resolution["date"] + "."
                linked.add(resolution["article_id"])
            elif (run_day - date.fromisoformat(candidate["date"])).days > limit:
                finding["state"] = "historical status unknown"
                finding["event"] = "historical investigation"
                finding["assessment"] = "Dated finding, no follow-up found in supplied sources, status unknown."
            else:
                finding["state"] = "allegation unresolved"
                finding["assessment"] = "Suspected investigation, not proven conduct. No outcome is reported in supplied sources."
        elif candidate['event'] == 'penalty or settlement':
            finding['state'] = 'reported settlement'
            finding['assessment'] = 'Sanctions settlement reported on ' + candidate['date'] + '. See the exact terms in the article.'
        else:
            finding["state"] = "reported restriction"
            finding["assessment"] = "Invented sanctions event reported on " + candidate["date"] + "."
        finding["article_context"] = article_context(candidate)
        findings.append(finding)
    for candidate in candidates:
        if candidate["event"] == "delisting or case closed" and candidate["article_id"] not in linked:
            findings.append({**{k: v for k, v in candidate.items() if k != "body"},
                             "type": "sanctions", "state": "reported delisting",
                             "assessment": "Delisting reported on " + candidate["date"]
                                           + "; no confirmed earlier-case link.",
                             "article_context": article_context(candidate)})
    findings.sort(key=lambda f: (f["article_id"], f["quote"]))
    possible_matches.sort(key=lambda f: (f["article_id"], f["quote"]))
    statuses, gaps = [], []
    for sid, source in sources.items():
        rejected_ids = [r["article_id"] for r in rejected
                        if any(a["id"] == r["article_id"] and a["source_id"] == sid for a in articles)]
        coverage = source["coverage"]
        if rejected_ids:
            coverage += " Model reading incomplete: " + ", ".join(rejected_ids) + ". Result unavailable, not no hit."
        sample_result = ("finding" if any(f["source_id"] == sid for f in findings) else "no finding")
        if source["execution"] != "completed" or rejected_ids:
            sample_result = "unavailable"
        status = {"source_id": sid, "source": source["name"],
                  "execution": source["execution"], "result": RESULT_VALUES[sample_result],
                  "sample_result": sample_result, "freshness": source["freshness"],
                  "as_of": source["as_of"],
                  "field_as_of": {f: source["as_of"] for f in ("execution", "result", "freshness")},
                  "date_basis": ("supplied snapshot" if source["execution"] == "completed" else
                                 "planned date only, nothing read"),
                  "article_ids_checked": checked[sid], "coverage": coverage}
        statuses.append(status)
        if source["execution"] != "completed" or source["freshness"] == "stale" or rejected_ids:
            gaps.append({"source_id": sid, "execution": source["execution"],
                         "freshness": source["freshness"], "as_of": source["as_of"],
                         "reason": coverage})
    gap_summary = []
    for status in statuses:
        if status["execution"] == "failed":
            gap_summary.append(status["source_id"] + " failed")
        elif status["execution"] == "not attempted":
            gap_summary.append(status["source_id"] + " was not attempted")
    for status in statuses:
        if status["freshness"] == "stale":
            gap_summary.append(status["source_id"] + " covers nothing after " + status["as_of"])
    if findings:
        summary = "Sanctions findings in supplied articles. Coverage remains incomplete."
    else:
        summary = ("No confirmed findings for " if possible_matches else "No findings for ")
        summary += subject["name"] + " in the supplied articles from completed sources. "
        if possible_matches:
            count = len(possible_matches)
            summary += str(count) + (" possible match needs" if count == 1 else " possible matches need") + " human review. "
        summary += ("; ".join(gap_summary) + ". " if gap_summary else "") + "This is not a clearance."
    # Whitelist report identity fields. Never copy the full subject record.
    safe_subject = {k: subject[k] for k in ("id", "name", "type", "role", "employer", "profile", "key_people", "country")
                    if k in subject}
    version = "0.5" if articles and all(STORY_FIELDS <= set(a) for a in articles) else "0.3"
    report = {"schema_version": 1, "skill_version": version, "subject": safe_subject,
            "as_of": plan["run_date"], "summary": summary, "findings": findings,
            "possible_matches": possible_matches,
            "sources": statuses, "excluded_articles": exclusions, "non_events": non_events,
            "not_covered": gaps,
            "scope": "Supplied invented articles only. No live news search or sanctions-list check.",
            "decision": "Human review required; tool chooses no disposition."}
    if model_records is not None:
        report["reader"] = "model"
        report["rejected_records"] = rejected
        if rejected:
            report["summary"] += " Model reading incomplete: " + str(len(rejected)) + " rejected records."
    elif "profile" in subject:
        spec = importlib.util.spec_from_file_location("compare_media", Path(__file__).with_name("compare_media.py"))
        assert spec is not None and spec.loader is not None
        comparison = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(comparison)
        report["comparisons"] = comparison.comparisons(
            subject, articles, report, sentences, stated_identity, age_at, story_context)
    if compute_links and reader == "script":
        report["links"] = article_links(candidates, subject, [s["name"] for s in sources.values()])
        for record in report["findings"] + report.get("comparisons", []):
            links = [link for link in report["links"] if link["article_id"] == record["article_id"]]
            if links:
                record["links"] = links
                record["link"] = {key: value for key, value in links[0].items() if key != "article_id"}
            if record.get("resolution"):
                resolution = record["resolution"]
                links = [link for link in report["links"] if link["article_id"] == resolution["article_id"]]
                if links:
                    resolution["links"] = links
                    resolution["link"] = {key: value for key, value in links[0].items() if key != "article_id"}
    return report


def render(report):
    lines = ["# Sanctions news: " + report["subject"]["id"], "", report["subject"]["name"],
             "As of: " + report["as_of"], "", report["summary"], "", report["scope"],
             report["decision"], "", "## Findings", ""]

    def show_evidence(record):
        lines.extend([record["source_id"] + " | " + record["source"] + " | "
                      + record["article_id"] + " | " + record["date"],
                      "Fixture: " + record["fixture_file"], "> " + record["quote"]])

    for finding in report["findings"]:
        lines.extend(["### " + finding["article_id"] + ": " + finding["event"], finding["assessment"]])
        show_evidence(finding)
        check = finding["identity_check"]
        lines.append("Identity: " + check["identity"])
        lines.append("Matched fields: " + ", ".join(check["matched_fields"]))
        if check["readings"]:
            lines.append("Three readings: " + " / ".join(check["readings"]) + ". Tool chooses none.")
        lines.extend(finding["article_context"])
        if "resolution" in finding:
            lines.append("Linked authority decision:")
            show_evidence(finding["resolution"])
        lines.append("")
    if report.get("links"):
        lines.extend(["## Article relationships (not applied to findings)", ""])
        for link in report["links"]:
            lines.append(link["article_id"] + " -> " + link["to_article_id"] + " | " + link["tier"])
            lines.extend("- " + reason for reason in link["reasons"])
            if link["tier"] == "SUGGESTED":
                lines.append("Suggested, analyst to confirm. Findings and status unchanged.")
            lines.append("")
    lines.extend(["## Possible matches (not enough evidence)", ""])
    for possible in report["possible_matches"]:
        lines.append("### " + possible["article_id"] + ": " + possible["event"])
        show_evidence(possible)
        lines.append("Identity: " + possible["identity_status"]
                     + ". Name matches; the article states too little context to confirm or rule out.")
        lines.append("Three readings: " + " / ".join(possible["identity_check"]["readings"])
                     + ". Tool chooses none.")
        lines.extend(possible["article_context"])
        lines.extend([possible["assessment"], ""])
    lines.extend(["## Excluded articles", ""])
    for excluded in report["excluded_articles"]:
        show_evidence(excluded)
        lines.append(excluded["reason"])
        conflicts = excluded["identity_check"]["conflicting_fields"]
        if conflicts:
            lines.append("Conflicting fields: " + ", ".join(conflicts))
    lines.extend(["", "## Not a sanctions event", ""])
    for non_event in report["non_events"]:
        show_evidence(non_event)
        lines.append(non_event["classification"])
    lines.extend(["", "## Source statuses", ""])
    for source in report["sources"]:
        lines.append("### " + source["source_id"] + " | " + source["source"])
        for field in ("execution", "result", "freshness"):
            lines.append(field + ": " + source[field] + " | as_of: " + source["field_as_of"][field])
        lines.append("Date basis: " + source["date_basis"])
        lines.append("Sample wording: " + source["source_id"] + " is " + source["execution"]
                     + ", " + source["sample_result"] + ", " + source["freshness"]
                     + (" (planned date only, nothing read)" if source["execution"] != "completed" else "")
                     + ", as of " + source["as_of"] + ".")
        lines.append("Articles checked: " + (", ".join(source["article_ids_checked"]) or "none"))
        lines.extend([source["coverage"], ""])
    lines.extend(["## What was not covered", ""])
    for gap in report["not_covered"]:
        lines.append(gap["source_id"] + " | " + gap["execution"] + " | " + gap["freshness"]
                     + " | as_of: " + gap["as_of"] + " | " + gap["reason"])
    lines.append(report["scope"])
    if report.get("rejected_records"):
        lines.extend(["", "## Rejected model records", "Model reading incomplete; not a no-hit result."])
        for rejected in report["rejected_records"]:
            lines.append(rejected["article_id"] + ": " + "; ".join(rejected["errors"]))
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--fixtures", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--reader", choices=("script", "model"), default="script")
    parser.add_argument("--records", type=Path, help="recorded model output JSON, never live inference")
    args = parser.parse_args(argv)
    try:
        report = research(args.subject, args.fixtures, args.reader, args.records)
        markdown = render(report)
        # Keep accidental output inside the input tree from changing the frozen fixtures.
        out = args.out.resolve()
        fixture_root = args.fixtures.resolve()
        if out == fixture_root or fixture_root in out.parents:
            raise ValueError("Output must be outside fixtures")
        args.out.mkdir(parents=True, exist_ok=True)
        stem = report["subject"]["id"]
        (args.out / (stem + ".json")).write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (args.out / (stem + ".md")).write_text(markdown, encoding="utf-8")
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print("Research failed: " + str(exc), file=sys.stderr)
        return 1
    print(stem + ": " + str(len(report["findings"])) + " findings; "
          + str(len(report["sources"])) + " sources; human review required")
    return 0


if __name__ == "__main__":
    sys.exit(main())
