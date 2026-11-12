#!/usr/bin/env python3
"""Approved phase-3 benchmark. Offline scoring by default; --live is single-use."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

from check_answer_key import DEFAULT_FIXTURES, evaluate
from model_reader import (COPY_FIELDS, INSTRUCTIONS, PROMPT_VERSION, SYSTEM_PROMPT,
                          body_hash, call_article, model_command, parse_output,
                          subscription_auth, validate_record)
from research import classify, read_article, read_json, sentences


EVIDENCE = Path(__file__).resolve().parents[1] / "evidence" / "phase-3"
CAP = 40
MODELS = ("haiku", "sonnet")


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".pending")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def live(evidence=EVIDENCE):
    """No resuming or second run: the exclusive ledger protects the phase-wide cap."""
    plan = read_json(evidence / "plan.json")
    if plan.get("call_cap") != CAP:
        raise ValueError("Missing predeclared 40-call plan")
    auth = subscription_auth()
    articles = [read_article(p) for p in sorted((DEFAULT_FIXTURES / "articles").glob("*.md"))]
    if len(articles) != 20:
        raise ValueError("Expected exactly 20 invented articles")
    # 'x' prevents a second invocation from spending a second phase budget.
    with (evidence / "calls.jsonl").open("x", encoding="utf-8") as ledger:
        run = {"authMethod": auth, "call_count": 0, "call_cap": CAP,
               "started_at": datetime.now(timezone.utc).isoformat(),
               "billing": "API-equivalent, not paid; subscription only; API spend US$0",
               "prompt_version": PROMPT_VERSION, "status": "running"}
        save(evidence / "run.json", run)
        save(evidence / "prompt.json", {"version": PROMPT_VERSION, "system": SYSTEM_PROMPT,
                                        "instructions": INSTRUCTIONS,
                                        "commands": {m: model_command(m) for m in MODELS}})
        start = time.monotonic()
        for model in MODELS:
            bundle = {"prompt_version": PROMPT_VERSION, "model_alias": model, "articles": {}}
            for article in articles:
                for attempt in (1, 2):
                    if run["call_count"] >= CAP:
                        run["status"] = "BLOCKED"
                        run["blocker"] = "40-call cap reached before completion"
                        save(evidence / "run.json", run)
                        return False
                    run["call_count"] += 1
                    reservation = {"call": run["call_count"], "model": model,
                                   "article_id": article["id"], "attempt": attempt,
                                   "body_sha256": body_hash(article["body"])}
                    ledger.write(json.dumps(reservation) + "\n")
                    ledger.flush()
                    os.fsync(ledger.fileno())
                    save(evidence / "run.json", run)
                    entry = call_article(article, model)
                    save(evidence / ("call-%02d.json" % run["call_count"]), {**reservation, **entry})
                    bundle["articles"][article["id"]] = entry
                    save(evidence / (model + ".json"), bundle)
                    print(model, article["id"], "call", run["call_count"],
                          entry.get("failure", "recorded"), flush=True)
                    if "failure" not in entry:
                        break
                    if attempt == 2:
                        run["status"] = "BLOCKED"
                        run["blocker"] = "CLI failed twice for " + model + " " + article["id"]
                        save(evidence / "run.json", run)
                        return False
        run["status"] = "complete"
        run["wall_seconds"] = time.monotonic() - start
        run["finished_at"] = datetime.now(timezone.utc).isoformat()
        save(evidence / "run.json", run)
        return True


def score(evidence=EVIDENCE):
    """Score immutable recordings. Never call a model or use an answer key as input."""
    articles = [read_article(p) for p in sorted((DEFAULT_FIXTURES / "articles").glob("*.md"))]
    run = read_json(evidence / "run.json")
    calls = [json.loads(line) for line in (evidence / "calls.jsonl").read_text().splitlines()]
    if len(calls) != run["call_count"] or len(calls) > CAP:
        raise ValueError("Call ledger count disagrees with run")
    results = {}
    for model in MODELS:
        path = evidence / (model + ".json")
        if not path.exists():
            continue
        bundle = read_json(path)
        metrics = {"articles": len(bundle["articles"]), "verbatim_quotes": 0,
                   "invented_fields": 0, "wrong_event_types": 0, "rejected_records": 0,
                   "missing_records": 0, "unscorable_records": 0,
                   "unobserved_reserved_calls": 0, "diagnostic_fence_unwraps": 0,
                   "calls_reserved": 0,
                   "wall_seconds": 0, "api_equivalent_usd_not_paid": 0,
                   "input_tokens": 0, "output_tokens": 0,
                   "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0,
                   "resolved_models": [], "errors": []}
        # Include failed attempts and retry costs/time, not just the final entry per article.
        for call in calls:
            if call["model"] != model:
                continue
            metrics["calls_reserved"] += 1
            call_file = evidence / ("call-%02d.json" % call["call"])
            if not call_file.exists():
                metrics["unobserved_reserved_calls"] += 1
                continue
            entry = read_json(call_file)
            metrics["wall_seconds"] += entry["wall_seconds"]
            cli = entry["cli"]
            metrics["api_equivalent_usd_not_paid"] += cli.get("total_cost_usd", 0)
            for field in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
                metrics[field] += cli.get("usage", {}).get(field, 0)
            metrics["resolved_models"] += list(cli.get("modelUsage", {}))
        metrics["resolved_models"] = sorted(set(metrics["resolved_models"]))
        for article in articles:
            entry = bundle["articles"].get(article["id"], {})
            if not entry:
                metrics["missing_records"] += 1
                metrics["errors"].append({"article_id": article["id"], "errors": ["missing recorded output"]})
                continue
            try:
                try:
                    record = parse_output(entry.get("cli", {}))
                    validation_errors = validate_record(article, record)
                except (ValueError, KeyError, TypeError):
                    validation_errors = ["invalid model JSON or failed CLI result"]
                    # Diagnostics ONLY. Never accept fenced JSON in production replay.
                    # Keep the original strict JSON-only contract and count its failure.
                    text = entry.get("cli", {}).get("result", "").strip()
                    if text.startswith("```json\n") and text.endswith("\n```"):
                        record = json.loads(text[len("```json\n"):-len("\n```")])
                        metrics["diagnostic_fence_unwraps"] += 1
                    else:
                        raise ValueError("unscorable output")
                errors = list(validation_errors)
                if entry.get("body_sha256") != body_hash(article["body"]):
                    errors.append("recorded article hash differs")
                if errors:
                    metrics["rejected_records"] += 1
                if isinstance(record, dict):
                    if record.get("quote") in sentences(article["body"]):
                        metrics["verbatim_quotes"] += 1
                    inventions = [k for k in COPY_FIELDS if record.get(k) is not None
                                  and (not isinstance(record[k], str) or not record[k]
                                       or record[k] not in article["body"])]
                    metrics["invented_fields"] += len(inventions)
                    # Frozen fixtures have one main event sentence each. This is a narrow
                    # baseline label, not a general semantic oracle for arbitrary news.
                    expected_event = classify(sentences(article["body"])[0])
                    if record.get("event_type") != expected_event:
                        metrics["wrong_event_types"] += 1
                        errors.append("wrong event type: expected " + expected_event)
                else:
                    metrics["wrong_event_types"] += 1
            except (ValueError, KeyError, TypeError):
                errors = ["invalid model JSON; fields and event type unscorable"]
                metrics["rejected_records"] += 1
                metrics["unscorable_records"] += 1
            if errors:
                metrics["errors"].append({"article_id": article["id"], "errors": errors})
        rows = evaluate(DEFAULT_FIXTURES, evidence / (model + "-reports"), "model", path)
        metrics["replay_rows"] = rows
        metrics["rows_passed"] = sum(r["status"] == "PASS" for r in rows)
        metrics["quote_rate"] = metrics["verbatim_quotes"] / len(articles)
        metrics["returned_quote_rate"] = (metrics["verbatim_quotes"] / metrics["articles"]
                                          if metrics["articles"] else None)
        metrics["api_equivalent_per_article_usd_not_paid"] = (
            metrics["api_equivalent_usd_not_paid"] / metrics["articles"] if metrics["articles"] else None)
        metrics["cost_complete"] = metrics["articles"] == 20 and not metrics["unobserved_reserved_calls"]
        metrics["full_run_api_equivalent_usd_not_paid"] = (
            metrics["api_equivalent_usd_not_paid"] if metrics["cost_complete"] else None)
        metrics["qualifies"] = (metrics["articles"] == 20 and metrics["rows_passed"] == 12
                                and metrics["invented_fields"] == 0 and metrics["wrong_event_types"] == 0
                                and metrics["unscorable_records"] == 0 and metrics["rejected_records"] == 0
                                and metrics["cost_complete"])
        results[model] = metrics
    eligible = [m for m in results if results[m]["qualifies"]]
    choice = min(eligible, key=lambda m: results[m]["api_equivalent_usd_not_paid"]) if eligible else "script-first"
    summary = {"call_count": len(calls), "models": results, "proposed_model": choice,
               "status": run["status"], "comparison_complete": run["status"] == "complete",
               "decision_rule": read_json(evidence / "plan.json")["decision_rule"],
               "consistency": "NOT yet measured: one pass per model, no repeats",
               "api_spend_usd": 0, "cost_label": "API-equivalent, not paid"}
    save(evidence / "scores.json", summary)
    print(json.dumps(summary, indent=2))
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="spend the approved single 40-call phase budget")
    args = parser.parse_args(argv)
    try:
        if args.live and not live():
            return 2
        score()
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print("Benchmark blocked: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
