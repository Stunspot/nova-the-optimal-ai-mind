#!/usr/bin/env python3
"""Initialize, validate, and summarize OMNARA research campaign vaults."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

TIERS = {"focused", "deep", "exhaustive"}
PHASES = {
    "framing", "mapping", "breadth-sweep", "depth-reading", "reconciliation",
    "gap-fill", "synthesis", "citation-audit", "review", "complete", "halted",
}
STATUSES = {
    "active", "complete", "awaiting-evidence", "awaiting-authority",
    "capability-limited", "budget-exhausted", "partial-success", "paused",
}
SOURCE_STATES = {
    "discovered", "inspected", "opened", "deeply-read", "excluded",
    "duplicate", "inaccessible", "cited",
}

STATE_PREREQUISITES = {
    "inspected": {"discovered"},
    "opened": {"discovered", "inspected"},
    "deeply-read": {"discovered", "inspected", "opened"},
    "cited": {"discovered", "inspected", "opened", "deeply-read"},
}
TERMINAL_STATES = {"excluded", "duplicate", "inaccessible"}
COMPLETE_ARTIFACTS = {
    "research-brief.md": (80, ("State what the report must make knowable",)),
    "coverage-matrix.md": (25, ("| unmapped |",)),
    "evidence-digest.md": (40, ("Organize the corpus by mechanisms",)),
    "outline.md": (25, ("Allocate every major section a purpose",)),
    "campaign-summary.md": (60, ("- Scope and evidence cutoff:\n- Current status:",)),
    "citation-audit.md": (35, ("Not run.",)),
    "report.md": (100, ("Report assembly has not run.",)),
}


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def note_is_substantive(path: Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8").strip()
    return word_count(text) >= 30 and "Preserve bounded source assertions" not in text


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        raise ValueError(f"missing {path.name}")
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number}: expected object")
        rows.append(value)
    return rows


def validate(directory: Path) -> list[str]:
    errors: list[str] = []
    try:
        campaign = read_json(directory / "campaign.json")
    except Exception as exc:
        return [str(exc)]

    if campaign.get("format") != "omnara-research-campaign/v1":
        errors.append("campaign.json: unsupported format")
    if campaign.get("tier") not in TIERS:
        errors.append("campaign.json: invalid tier")
    if campaign.get("phase") not in PHASES:
        errors.append("campaign.json: invalid phase")
    if campaign.get("status") not in STATUSES:
        errors.append("campaign.json: invalid status")
    if not str(campaign.get("canonical_inquiry", "")).strip():
        errors.append("campaign.json: canonical_inquiry is empty")
    if not str(campaign.get("resume_point", "")).strip():
        errors.append("campaign.json: resume_point is empty")

    sources: list[dict] = []
    source_ids: set[str] = set()
    state_counts: Counter = Counter()
    claims: list[dict] = []
    try:
        sources = read_jsonl(directory / "source-ledger.jsonl")
        for index, row in enumerate(sources, 1):
            source_id = row.get("id")
            if not isinstance(source_id, str) or not source_id.startswith("S"):
                errors.append(f"source row {index}: invalid id")
            elif source_id in source_ids:
                errors.append(f"source row {index}: duplicate id {source_id}")
            else:
                source_ids.add(source_id)
            states = row.get("states", [])
            if not isinstance(states, list) or any(state not in SOURCE_STATES for state in states):
                errors.append(f"source row {index}: invalid states")
                states = []
            else:
                state_set = set(states)
                if len(state_set) != len(states):
                    errors.append(f"source row {index}: duplicate state")
                for state in states:
                    state_counts[state] += 1
                for state, prerequisites in STATE_PREREQUISITES.items():
                    if state in state_set and not prerequisites.issubset(state_set):
                        missing = ", ".join(sorted(prerequisites - state_set))
                        errors.append(f"source row {index}: {state} missing prerequisite states: {missing}")
                if state_set & TERMINAL_STATES and state_set & {"opened", "deeply-read", "cited"}:
                    errors.append(f"source row {index}: terminal state conflicts with opened, deeply-read, or cited")
                if "deeply-read" in state_set and isinstance(source_id, str):
                    note = directory / "notes" / f"{source_id}.md"
                    if not note_is_substantive(note):
                        errors.append(f"source row {index}: deeply-read source requires a substantive evidence note")
            if not row.get("url") and not row.get("identifier"):
                errors.append(f"source row {index}: url or identifier required")

        claims = read_jsonl(directory / "claim-ledger.jsonl")
        claim_ids: set[str] = set()
        for index, row in enumerate(claims, 1):
            claim_id = row.get("id")
            if not isinstance(claim_id, str) or not claim_id.startswith("C"):
                errors.append(f"claim row {index}: invalid id")
            elif claim_id in claim_ids:
                errors.append(f"claim row {index}: duplicate id {claim_id}")
            else:
                claim_ids.add(claim_id)
            if not str(row.get("claim", "")).strip():
                errors.append(f"claim row {index}: claim is empty")
            links = row.get("source_ids", [])
            if not isinstance(links, list):
                errors.append(f"claim row {index}: source_ids must be an array")
            else:
                for source_id in links:
                    if source_id not in source_ids:
                        errors.append(f"claim row {index}: unknown source {source_id}")
        queries = read_jsonl(directory / "query-ledger.jsonl")
        for index, row in enumerate(queries, 1):
            result_ids = row.get("result_ids", [])
            if not isinstance(result_ids, list):
                errors.append(f"query row {index}: result_ids must be an array")
            else:
                for source_id in result_ids:
                    if source_id not in source_ids:
                        errors.append(f"query row {index}: unknown result source {source_id}")

        counters = campaign.get("counters")
        if not isinstance(counters, dict):
            errors.append("campaign.json: counters must be an object")
        else:
            expected_counts = {state.replace("-", "_"): state_counts[state] for state in SOURCE_STATES}
            expected_counts["queries"] = len(queries)
            for key, expected in sorted(expected_counts.items()):
                if counters.get(key) != expected:
                    errors.append(f"campaign.json: counter {key}={counters.get(key)!r} does not match ledger count {expected}")
    except Exception as exc:
        errors.append(str(exc))

    for name in ("research-brief.md", "coverage-matrix.md", "contradictions.md"):
        if not (directory / name).is_file():
            errors.append(f"missing {name}")
    if campaign.get("phase") == "complete":
        for name, (minimum_words, placeholders) in COMPLETE_ARTIFACTS.items():
            path = directory / name
            if not path.is_file():
                errors.append(f"complete campaign missing {name}")
                continue
            text = path.read_text(encoding="utf-8")
            if word_count(text) < minimum_words:
                errors.append(f"complete campaign {name} has fewer than {minimum_words} words")
            for placeholder in placeholders:
                if placeholder in text:
                    errors.append(f"complete campaign {name} still contains template instructions")
        report_path = directory / "report.md"
        markers = re.findall(r"\[(S\d{3,})\]", report_path.read_text(encoding="utf-8")) if report_path.is_file() else []
        cited_source_ids = {
            row.get("id")
            for row in sources
            if "cited" in set(row.get("states", [])) and isinstance(row.get("id"), str)
        }
        linked_claims = [
            row
            for row in claims
            if isinstance(row.get("source_ids"), list) and row.get("source_ids")
        ]
        if not markers:
            errors.append("complete campaign report contains no citation markers")
        if not cited_source_ids:
            errors.append("complete campaign has no cited sources")
        if not linked_claims:
            errors.append("complete campaign has no source-linked claims")

        audit_path = directory / "citation-audit-structural.json"
        if not audit_path.is_file():
            errors.append("complete campaign missing citation-audit-structural.json")
        else:
            try:
                audit = read_json(audit_path)
                expected_hashes = {
                    "report.md": file_sha256(report_path),
                    "source-ledger.jsonl": file_sha256(directory / "source-ledger.jsonl"),
                    "claim-ledger.jsonl": file_sha256(directory / "claim-ledger.jsonl"),
                }
                if audit.get("format") != "omnara-citation-integrity/v1":
                    errors.append("complete campaign structural citation audit has unsupported format")
                if audit.get("result") != "pass" or audit.get("errors"):
                    errors.append("complete campaign structural citation audit did not pass")
                if audit.get("report_markers") != len(markers):
                    errors.append("complete campaign structural citation audit marker count is stale")
                if audit.get("unique_cited_sources") != len(set(markers)):
                    errors.append("complete campaign structural citation audit cited-source count is stale")
                if audit.get("inputs_sha256") != expected_hashes:
                    errors.append("complete campaign structural citation audit does not match current evidence files")
            except Exception as exc:
                errors.append(f"complete campaign structural citation audit is invalid: {exc}")
    return errors


def source_counts(directory: Path) -> Counter:
    counts: Counter = Counter()
    for row in read_jsonl(directory / "source-ledger.jsonl"):
        for state in row.get("states", []):
            counts[state] += 1
    return counts


def initialize(template: Path, destination: Path, title: str, query: str, tier: str) -> None:
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(f"destination is not empty: {destination}")
    shutil.copytree(template, destination, dirs_exist_ok=True)
    campaign_path = destination / "campaign.json"
    campaign = read_json(campaign_path)
    now = datetime.now(timezone.utc).isoformat()
    campaign.update({
        "title": title,
        "canonical_inquiry": query,
        "tier": tier,
        "created_at": now,
        "updated_at": now,
    })
    campaign_path.write_text(json.dumps(campaign, indent=2) + "\n", encoding="utf-8")
    brief = destination / "research-brief.md"
    brief.write_text(brief.read_text(encoding="utf-8").replace(
        "Preserve the user's wording verbatim.", query
    ), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    init_parser = sub.add_parser("init")
    init_parser.add_argument("destination", type=Path)
    init_parser.add_argument("--title", required=True)
    init_parser.add_argument("--query", required=True)
    init_parser.add_argument("--tier", choices=sorted(TIERS), default="deep")
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("directory", type=Path)
    summary_parser = sub.add_parser("summary")
    summary_parser.add_argument("directory", type=Path)
    args = parser.parse_args()

    try:
        if args.command == "init":
            template = Path(__file__).resolve().parents[1] / "assets" / "campaign-vault"
            initialize(template, args.destination, args.title, args.query, args.tier)
            print(f"INITIALIZED: {args.destination}")
            return 0
        errors = validate(args.directory)
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        if args.command == "validate":
            print(f"VALID: {args.directory}")
            return 0
        campaign = read_json(args.directory / "campaign.json")
        counts = source_counts(args.directory)
        print(json.dumps({
            "title": campaign["title"],
            "tier": campaign["tier"],
            "phase": campaign["phase"],
            "status": campaign["status"],
            "source_counts": dict(sorted(counts.items())),
            "resume_point": campaign["resume_point"],
        }, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
