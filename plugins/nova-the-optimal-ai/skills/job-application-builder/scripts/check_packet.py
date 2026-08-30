#!/usr/bin/env python3
"""Check structural and evidence-ledger consistency of an application packet."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

REQUIRED_FILES = (
    "role-match-brief.md",
    "resume.md",
    "cover-letter.md",
    "application-answers.md",
    "evidence-claim-matrix.csv",
    "work-sample-guidance.md",
    "unresolved-claims.md",
    "submission-checklist.md",
    "source-register.md",
)
MATRIX_HEADERS = (
    "criterion_id", "criterion_text", "criterion_type", "importance",
    "evidence_id", "evidence_source", "evidence_strength", "proposed_claim",
    "support_status", "destinations", "confirmation_status", "risk_note",
)
SOURCE_HEADERS = (
    "source_id", "source_type", "title_or_identity", "path_or_url", "source_date",
    "retrieved_at", "custody", "use", "notes",
)
ALLOWED_SUPPORT = {
    "documented", "user-confirmed", "reasonable-paraphrase",
    "confirmation-needed", "unsupported",
}
ALLOWED_CRITERION_TYPES = {
    "required", "preferred", "responsibility", "context", "administrative",
}
ALLOWED_IMPORTANCE = {"high", "medium", "low"}
ALLOWED_STRENGTH = {"direct", "adjacent", "self-report", "none"}
ALLOWED_CONFIRMATION = {"confirmed", "confirmation-needed", "unresolved", "not-applicable"}
ALLOWED_DESTINATIONS = {
    "resume", "cover-letter", "application-answers", "work-sample-guidance",
}
SUPPORTED = {"documented", "user-confirmed", "reasonable-paraphrase"}
FINAL_PROSE = ("resume.md", "cover-letter.md", "application-answers.md")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def normalize(value: str | None) -> str:
    return (value or "").strip()


def tokens(value: str | None) -> list[str]:
    return [item.strip() for item in re.split(r"[;,]", value or "") if item.strip()]


def read_csv(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return tuple(reader.fieldnames or ()), list(reader)


def checked(text: str, label: str) -> bool:
    return bool(re.search(rf"^-\s*\[[xX]\]\s*{re.escape(label)}\s*$", text, re.MULTILINE))


def check_packet(packet: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    if not packet.is_dir():
        return {"ok": False, "errors": [f"not a directory: {packet}"], "warnings": []}

    missing = [name for name in REQUIRED_FILES if not (packet / name).is_file()]
    errors.extend(f"missing required artifact: {name}" for name in missing)
    if missing:
        return {"ok": False, "errors": errors, "warnings": warnings}

    source_headers, source_rows = read_csv(packet / "source-register.md")
    absent_source_headers = [name for name in SOURCE_HEADERS if name not in source_headers]
    errors.extend(f"source register missing header: {name}" for name in absent_source_headers)
    if absent_source_headers:
        return {"ok": False, "errors": errors, "warnings": warnings}

    source_ids: set[str] = set()
    for index, row in enumerate(source_rows, start=2):
        source_id = normalize(row.get("source_id"))
        if not source_id:
            errors.append(f"source row {index}: missing source_id")
            continue
        if not re.fullmatch(r"SRC-[0-9]{3}", source_id):
            errors.append(f"source row {index}: source_id must look like SRC-001")
        if source_id in source_ids:
            errors.append(f"source row {index}: duplicate source_id {source_id}")
        source_ids.add(source_id)
        if not normalize(row.get("title_or_identity")):
            errors.append(f"source row {index}: missing title_or_identity")
        if not normalize(row.get("custody")):
            errors.append(f"source row {index}: missing custody")
        if not normalize(row.get("use")):
            errors.append(f"source row {index}: missing use")
    if not source_rows:
        warnings.append("source register has no rows")

    headers, rows = read_csv(packet / "evidence-claim-matrix.csv")
    absent_headers = [name for name in MATRIX_HEADERS if name not in headers]
    errors.extend(f"matrix missing header: {name}" for name in absent_headers)
    if absent_headers:
        return {"ok": False, "errors": errors, "warnings": warnings}

    unresolved_text = read_text(packet / "unresolved-claims.md").lower()
    final_text = "\n".join(read_text(packet / name) for name in FINAL_PROSE).lower()
    evidence_bindings: dict[str, tuple[tuple[str, ...], str]] = {}
    criterion_texts: dict[str, str] = {}
    seen_rows: set[tuple[str, str, str]] = set()

    if not rows:
        warnings.append("evidence matrix has no rows")

    for index, row in enumerate(rows, start=2):
        criterion_id = normalize(row.get("criterion_id"))
        criterion_text = normalize(row.get("criterion_text"))
        criterion_type = normalize(row.get("criterion_type")).lower()
        importance = normalize(row.get("importance")).lower()
        evidence_id = normalize(row.get("evidence_id"))
        evidence_sources = tuple(tokens(row.get("evidence_source")))
        strength = normalize(row.get("evidence_strength")).lower()
        status = normalize(row.get("support_status")).lower()
        claim = normalize(row.get("proposed_claim"))
        destinations = tuple(tokens(row.get("destinations")))
        confirmation = normalize(row.get("confirmation_status")).lower()

        if not criterion_id or not re.fullmatch(r"[A-Za-z]+-[0-9]{3}", criterion_id):
            errors.append(f"matrix row {index}: criterion_id must look like REQ-001")
        if not criterion_text:
            errors.append(f"matrix row {index}: missing criterion_text")
        elif criterion_id in criterion_texts and criterion_texts[criterion_id] != criterion_text:
            errors.append(f"matrix row {index}: criterion_id {criterion_id} has conflicting text")
        else:
            criterion_texts[criterion_id] = criterion_text
        if criterion_type not in ALLOWED_CRITERION_TYPES:
            errors.append(f"matrix row {index}: invalid criterion_type {criterion_type!r}")
        if importance not in ALLOWED_IMPORTANCE:
            errors.append(f"matrix row {index}: invalid importance {importance!r}")
        if status not in ALLOWED_SUPPORT:
            errors.append(f"matrix row {index}: invalid support_status {status!r}")
        if strength not in ALLOWED_STRENGTH:
            errors.append(f"matrix row {index}: invalid evidence_strength {strength!r}")
        if confirmation not in ALLOWED_CONFIRMATION:
            errors.append(f"matrix row {index}: invalid confirmation_status {confirmation!r}")

        row_key = (criterion_id, evidence_id, claim.lower())
        if row_key in seen_rows:
            errors.append(f"matrix row {index}: duplicate criterion/evidence/claim row")
        seen_rows.add(row_key)

        unknown_destinations = sorted(set(destinations) - ALLOWED_DESTINATIONS)
        if unknown_destinations:
            errors.append(f"matrix row {index}: invalid destinations {unknown_destinations}")

        if status in SUPPORTED:
            if not evidence_id or not re.fullmatch(r"EVD-[0-9]{3}", evidence_id):
                errors.append(f"matrix row {index}: supported claim requires evidence_id like EVD-001")
            if not evidence_sources:
                errors.append(f"matrix row {index}: supported claim requires source-register IDs")
            if not claim:
                errors.append(f"matrix row {index}: supported row lacks proposed_claim")
            if not destinations:
                errors.append(f"matrix row {index}: supported row lacks destinations")
        elif evidence_id and not re.fullmatch(r"EVD-[0-9]{3}", evidence_id):
            errors.append(f"matrix row {index}: evidence_id must look like EVD-001")

        for source_id in evidence_sources:
            if source_id not in source_ids:
                errors.append(f"matrix row {index}: unknown source-register ID {source_id}")

        if evidence_id:
            binding = (evidence_sources, strength)
            prior = evidence_bindings.get(evidence_id)
            if prior is not None and prior != binding:
                errors.append(f"matrix row {index}: evidence_id {evidence_id} changes source or strength")
            else:
                evidence_bindings[evidence_id] = binding

        if status == "confirmation-needed" and criterion_id.lower() not in unresolved_text:
            errors.append(f"matrix row {index}: confirmation-needed {criterion_id} is absent from unresolved-claims.md")
        if status in {"confirmation-needed", "unsupported"} and claim and claim.lower() in final_text:
            errors.append(f"matrix row {index}: {status} proposed claim appears in final application prose")

    checklist = read_text(packet / "submission-checklist.md").lower()
    pending = checked(checklist, "submission is still pending.")
    submitted = checked(checklist, "submission occurred through an authorized action.")
    if pending and submitted:
        errors.append("checklist marks submission both pending and completed")
    if not pending and not submitted:
        warnings.append("checklist does not state whether submission is pending or completed")

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    result = check_packet(args.packet.resolve())
    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for message in result["errors"]:
            print(f"ERROR: {message}")
        for message in result["warnings"]:
            print(f"WARNING: {message}")
        print("PASS" if result["ok"] else "FAIL")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
