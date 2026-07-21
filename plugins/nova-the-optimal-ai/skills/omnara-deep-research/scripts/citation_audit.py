#!/usr/bin/env python3
"""Audit structural citation integrity for an OMNARA campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

MARKER = re.compile(r"\[(S\d{3,})\]")
WORD = re.compile(r"\b[\w'-]+\b")


def note_is_substantive(path: Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8").strip()
    return len(WORD.findall(text)) >= 30 and "Preserve bounded source assertions" not in text


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number}: expected object")
        rows.append(value)
    return rows


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(directory: Path) -> dict:
    report_path = directory / "report.md"
    report = report_path.read_text(encoding="utf-8")
    markers = MARKER.findall(report)
    sources = read_jsonl(directory / "source-ledger.jsonl")
    claims = read_jsonl(directory / "claim-ledger.jsonl")
    source_map = {row.get("id"): row for row in sources}
    errors: list[str] = []
    warnings: list[str] = []
    claim_source_ids = {
        source_id
        for claim in claims
        for source_id in claim.get("source_ids", [])
        if isinstance(source_id, str)
    }

    if len(source_map) != len(sources):
        errors.append("source IDs are not unique")
    if not markers:
        errors.append("report contains no citation markers")
    if not sources:
        errors.append("source ledger is empty")
    if not claims:
        errors.append("claim ledger is empty")
    for source_id in sorted(set(markers)):
        source = source_map.get(source_id)
        if source is None:
            errors.append(f"report marker has no source record: {source_id}")
            continue
        states = set(source.get("states", []))
        if "duplicate" in states or "inaccessible" in states:
            errors.append(f"cited source has unusable state: {source_id}")
        note = directory / "notes" / f"{source_id}.md"
        if "deeply-read" not in states:
            errors.append(f"cited source is not deeply-read: {source_id}")
        if "cited" not in states:
            errors.append(f"report marker source is not ledgered as cited: {source_id}")
        if not note.is_file():
            errors.append(f"cited source has no evidence note: {source_id}")
        elif not note_is_substantive(note):
            errors.append(f"cited source has no substantive evidence note: {source_id}")
        if source_id not in claim_source_ids:
            errors.append(f"report marker is not linked from the claim ledger: {source_id}")

    for claim in claims:
        claim_id = claim.get("id", "UNKNOWN")
        source_ids = claim.get("source_ids", [])
        importance = claim.get("importance", "supporting")
        if not str(claim.get("claim", "")).strip():
            errors.append(f"claim text is empty: {claim_id}")
        if not source_ids:
            errors.append(f"claim has no sources: {claim_id}")
        for source_id in source_ids:
            if source_id not in source_map:
                errors.append(f"claim {claim_id} links unknown source {source_id}")
            if source_id not in markers:
                warnings.append(f"claim {claim_id} source not present in report: {source_id}")

    return {
        "format": "omnara-citation-integrity/v1",
        "result": "pass" if not errors else "fail",
        "report_markers": len(markers),
        "unique_cited_sources": len(set(markers)),
        "errors": errors,
        "warnings": sorted(set(warnings)),
        "semantic_entailment": "not established by this deterministic audit",
        "inputs_sha256": {
            "report.md": file_sha256(report_path),
            "source-ledger.jsonl": file_sha256(directory / "source-ledger.jsonl"),
            "claim-ledger.jsonl": file_sha256(directory / "claim-ledger.jsonl"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = audit(args.directory)
    output = args.directory / "citation-audit-structural.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
