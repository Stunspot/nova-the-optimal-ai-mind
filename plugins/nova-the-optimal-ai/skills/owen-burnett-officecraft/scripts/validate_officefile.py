#!/usr/bin/env python3
"""Validate Officefile state and artifact claims using only the standard library."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from inspect_office_artifacts import inspect_csv, inspect_markdown, inspect_ooxml, inspect_pdf
from officefile_safety import member_path, safe_relative, walk_officefile_files


STATES = {"intake", "shaped", "production", "inspection", "reviewable", "handed_off"}
ARTIFACT_STATUSES = {"planned", "working", "produced", "inspected", "reviewed", "approved", "blocked"}
REVIEW_STATUSES = {"not_run", "PASS", "PASS_WITH_CONDITIONS", "REVISE", "BLOCKED"}
SOURCE_TYPES = {"notes", "document", "presentation", "spreadsheet", "csv", "pdf", "image", "template", "url", "other"}
SOURCE_CUSTODY_STATUSES = {"user_supplied", "verified", "illustrative", "stale", "conflicted", "missing"}
SOURCE_CONTENT_STATUSES = {"authoritative", "supporting", "illustrative", "unresolved", "conflicted"}
LEDGER_KINDS = {"fact", "name", "date", "metric", "unit", "claim", "decision", "risk", "action", "term"}
LEDGER_SOURCE_STATUSES = {"sourced", "inferred", "illustrative", "unresolved", "conflicted"}
ARTIFACT_FORMATS = {"DOCX", "PPTX", "XLSX", "CSV", "PDF", "MD", "OTHER"}
ARTIFACT_ROLES = {"canonical_source", "editable_source", "derivative", "handoff", "specification"}
FORMAT_SUFFIXES = {"DOCX": ".docx", "PPTX": ".pptx", "XLSX": ".xlsx", "CSV": ".csv", "PDF": ".pdf", "MD": ".md"}
STRUCTURAL_FORMATS = {"DOCX": "word/document.xml", "PPTX": "ppt/presentation.xml", "XLSX": "xl/workbook.xml"}
DIRECTLY_CHECKED_FORMATS = set(STRUCTURAL_FORMATS) | {"PDF", "CSV", "MD"}
REQUIRED = {
    "sources/manifest.json": "officecraft-source-manifest/v1",
    "state/brief.json": "officecraft-brief/v1",
    "state/content-ledger.json": "officecraft-content-ledger/v1",
    "state/artifact-register.json": "officecraft-artifact-register/v1",
    "review/officecraft-review.json": "officecraft-review/v1",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def in_enum(value: object, allowed: set[str]) -> bool:
    return isinstance(value, str) and value in allowed


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, errors: list[str], label: str) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{label}: invalid JSON ({exc})")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label}: expected a JSON object")
        return None
    return value


def require_fields(value: dict[str, Any], fields: set[str], label: str, errors: list[str]) -> None:
    for field in sorted(fields - set(value)):
        errors.append(f"{label}: missing required field {field}")


def credible_source(source: dict[str, Any]) -> bool:
    return in_enum(source.get("custody_status"), {"user_supplied", "verified"}) and in_enum(source.get("content_status"), {"authoritative", "supporting"})


def direct_structural_inspection(artifact_path: Path, artifact_format: str) -> bool:
    if artifact_format == "PDF":
        result = inspect_pdf(artifact_path)
        return result.get("structurally_plausible") is True
    if artifact_format in STRUCTURAL_FORMATS:
        result = inspect_ooxml(artifact_path, artifact_format)
        return result.get("structurally_plausible") is True
    if artifact_format == "CSV":
        return inspect_csv(artifact_path).get("structurally_plausible") is True
    if artifact_format == "MD":
        return inspect_markdown(artifact_path).get("structurally_plausible") is True
    return False


def credible_structural_evidence(root: Path, artifact_relative: str, artifact_path: Path, artifact_format: str, evidence: object, label: str, errors: list[str]) -> bool:
    if artifact_format not in DIRECTLY_CHECKED_FORMATS:
        errors.append(f"{label}: no defined structural checker exists for {artifact_format}")
        return False
    if not direct_structural_inspection(artifact_path, artifact_format):
        errors.append(f"{label}: current artifact fails direct bounded structural inspection")
        return False
    if not isinstance(evidence, list):
        return False
    artifact_relative = artifact_relative.replace("\\", "/")
    for index, record in enumerate(evidence):
        evidence_label = f"{label} check_evidence[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{evidence_label}: expected evidence object")
            continue
        evidence_relative = record.get("path")
        evidence_path = member_path(root, evidence_relative)
        if not isinstance(evidence_relative, str) or evidence_path is None or not evidence_path.is_file():
            errors.append(f"{evidence_label}: missing or unsafe inspection evidence path")
            continue
        report = load_json(evidence_path, errors, evidence_relative)
        if report is None or report.get("format") != "officecraft-artifact-inspection/v1":
            errors.append(f"{evidence_label}: not an Officecraft inspection report")
            continue
        if report.get("errors") != []:
            errors.append(f"{evidence_label}: inspection report contains errors")
            continue
        inspected = report.get("artifacts")
        if not isinstance(inspected, list):
            errors.append(f"{evidence_label}: inspection report artifacts must be an array")
            continue
        for item in inspected:
            if not isinstance(item, dict) or item.get("path") != artifact_relative:
                continue
            if item.get("sha256") != hash_file(artifact_path):
                errors.append(f"{evidence_label}: inspection digest does not match artifact")
                break
            inspection = item.get("inspection")
            if not isinstance(inspection, dict):
                errors.append(f"{evidence_label}: inspection detail is missing")
                break
            if artifact_format == "PDF":
                if inspection.get("kind") == "PDF" and inspection.get("structurally_plausible") is True:
                    return True
            elif artifact_format in STRUCTURAL_FORMATS and inspection.get("kind") == artifact_format and inspection.get("structurally_plausible") is True:
                return True
            elif artifact_format in {"CSV", "MD"} and inspection.get("kind") == artifact_format and inspection.get("structurally_plausible") is True:
                return True
            errors.append(f"{evidence_label}: inspection is not credible structural evidence for {artifact_format}")
            break
        else:
            errors.append(f"{evidence_label}: report has no matching artifact entry")
    return False


def review_supports_artifact(review: dict[str, Any], officefile_state: object, artifact_id: str, artifact_digest: str) -> bool:
    if not isinstance(officefile_state, str):
        return False
    for field in ("operator_review", "independent_review"):
        entry = review.get(field)
        if not isinstance(entry, dict) or not in_enum(entry.get("status"), {"PASS", "PASS_WITH_CONDITIONS"}) or entry.get("officefile_state") != officefile_state:
            continue
        reviewed = entry.get("reviewed_artifacts")
        if isinstance(reviewed, list) and any(isinstance(item, dict) and item.get("artifact_id") == artifact_id and item.get("sha256") == artifact_digest for item in reviewed):
            return True
    return False


def valid_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.astimezone(timezone.utc) <= datetime.now(timezone.utc) + timedelta(minutes=5)


def approval_supports_artifact(review: dict[str, Any], approval_owner: object, artifact_id: str, artifact_digest: str) -> bool:
    if not isinstance(approval_owner, str) or not approval_owner:
        return False
    records = review.get("approval_records")
    if not isinstance(records, list):
        return False
    return any(
        isinstance(record, dict)
        and record.get("artifact_id") == artifact_id
        and record.get("sha256") == artifact_digest
        and record.get("approval_owner") == approval_owner
        and in_enum(record.get("authority_kind"), {"user", "accountable_owner"})
        and nonempty_string(record.get("approved_use"))
        and valid_timestamp(record.get("approved_at"))
        for record in records
    )


def validate_officefile(root_value: str | Path) -> dict[str, Any]:
    root, files, errors = walk_officefile_files(root_value)
    warnings: list[str] = []
    if root is None:
        return {"format": "officecraft-validation/v1", "officefile": str(Path(root_value).absolute()), "checked_at": utc_now(), "valid": False, "errors": errors, "warnings": []}
    file_relatives = {path.relative_to(root).as_posix(): path for path in files}
    documents: dict[str, dict[str, Any]] = {}
    for relative, expected_format in REQUIRED.items():
        path = file_relatives.get(relative)
        if path is None:
            errors.append(f"missing required file: {relative}")
            continue
        value = load_json(path, errors, relative)
        if value is None:
            continue
        documents[relative] = value
        if value.get("format") != expected_format:
            errors.append(f"{relative}: expected format {expected_format}")

    decisions = file_relatives.get("state/decisions.jsonl")
    if decisions is None:
        errors.append("missing required file: state/decisions.jsonl")
    else:
        try:
            for line_number, line in enumerate(decisions.read_text(encoding="utf-8-sig").splitlines(), 1):
                if line.strip():
                    json.loads(line)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"state/decisions.jsonl:{locals().get('line_number', 0)}: invalid JSON ({exc})")

    brief = documents.get("state/brief.json", {})
    require_fields(brief, {"project_id", "state", "title", "audience", "purpose", "requested_outcomes", "constraints", "external_delivery_authorized"}, "state/brief.json", errors)
    for field in ("project_id", "title"):
        if brief and not nonempty_string(brief.get(field)):
            errors.append(f"state/brief.json: {field} must be a non-empty string")
    for field in ("audience", "purpose"):
        if brief and not isinstance(brief.get(field), str):
            errors.append(f"state/brief.json: {field} must be a string")
    requested_outcomes = brief.get("requested_outcomes")
    if brief and (not isinstance(requested_outcomes, list) or any(not isinstance(item, str) for item in requested_outcomes)):
        errors.append("state/brief.json: requested_outcomes must be an array of strings")
    if brief and not isinstance(brief.get("constraints"), dict):
        errors.append("state/brief.json: constraints must be an object")
    if brief.get("approval_owner") is not None and not nonempty_string(brief.get("approval_owner")):
        errors.append("state/brief.json: approval_owner must be null or a non-empty string")
    if brief and not in_enum(brief.get("state"), STATES):
        errors.append("state/brief.json: invalid Officefile state")
    if brief and not isinstance(brief.get("external_delivery_authorized"), bool):
        errors.append("state/brief.json: external_delivery_authorized must be boolean")

    manifest = documents.get("sources/manifest.json", {})
    sources_by_id: dict[str, dict[str, Any]] = {}
    if manifest:
        sources = manifest.get("sources")
        if not isinstance(sources, list):
            errors.append("sources/manifest.json: sources must be an array")
        else:
            for index, source in enumerate(sources):
                label = f"sources/manifest.json sources[{index}]"
                if not isinstance(source, dict):
                    errors.append(f"{label}: expected object")
                    continue
                require_fields(source, {"source_id", "path", "source_type", "custody_status", "content_status"}, label, errors)
                source_id = source.get("source_id")
                if not nonempty_string(source_id) or source_id in sources_by_id:
                    errors.append(f"{label}: source_id must be unique and non-empty")
                else:
                    sources_by_id[source_id] = source
                path_value = source.get("path")
                path = member_path(root, path_value)
                if not isinstance(path_value, str) or path is None:
                    errors.append(f"{label}: unsafe source path")
                elif source.get("custody_status") != "missing" and not path.is_file():
                    errors.append(f"{label}: declared source file is missing")
                if not in_enum(source.get("source_type"), SOURCE_TYPES):
                    errors.append(f"{label}: invalid source_type")
                if not in_enum(source.get("custody_status"), SOURCE_CUSTODY_STATUSES):
                    errors.append(f"{label}: invalid custody_status")
                if not in_enum(source.get("content_status"), SOURCE_CONTENT_STATUSES):
                    errors.append(f"{label}: invalid content_status")
                digest = source.get("sha256")
                if digest is not None:
                    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
                        errors.append(f"{label}: sha256 must be lowercase hex")
                    elif path is not None and path.is_file() and digest != hash_file(path):
                        errors.append(f"{label}: sha256 does not match source file")

    ledger = documents.get("state/content-ledger.json", {})
    ledger_ids: set[str] = set()
    if ledger:
        items = ledger.get("items")
        if not isinstance(items, list):
            errors.append("state/content-ledger.json: items must be an array")
        else:
            for index, item in enumerate(items):
                label = f"state/content-ledger.json items[{index}]"
                if not isinstance(item, dict):
                    errors.append(f"{label}: expected object")
                    continue
                require_fields(item, {"item_id", "kind", "value", "source_ids", "source_status"}, label, errors)
                item_id = item.get("item_id")
                if not nonempty_string(item_id) or item_id in ledger_ids:
                    errors.append(f"{label}: item_id must be unique and non-empty")
                else:
                    ledger_ids.add(item_id)
                if not nonempty_string(item.get("value")):
                    errors.append(f"{label}: value must be a non-empty string")
                item_sources = item.get("source_ids")
                references_valid = isinstance(item_sources, list) and all(isinstance(source_id, str) and source_id in sources_by_id for source_id in item_sources)
                if not isinstance(item_sources, list):
                    errors.append(f"{label}: source_ids must be an array")
                elif not references_valid:
                    errors.append(f"{label}: references unknown or non-string source_id")
                elif item.get("source_status") == "sourced" and not item_sources:
                    errors.append(f"{label}: sourced item needs at least one source_id")
                elif item.get("source_status") == "sourced" and any(not credible_source(sources_by_id[source_id]) for source_id in item_sources):
                    errors.append(f"{label}: sourced item depends on missing, unresolved, conflicted, or illustrative source")
                if not in_enum(item.get("kind"), LEDGER_KINDS):
                    errors.append(f"{label}: invalid kind")
                if not in_enum(item.get("source_status"), LEDGER_SOURCE_STATUSES):
                    errors.append(f"{label}: invalid source_status")

    review = documents.get("review/officecraft-review.json", {})
    register = documents.get("state/artifact-register.json", {})
    artifacts: dict[str, dict[str, Any]] = {}
    if register:
        records = register.get("artifacts")
        if not isinstance(records, list):
            errors.append("state/artifact-register.json: artifacts must be an array")
        else:
            for index, artifact in enumerate(records):
                label = f"state/artifact-register.json artifacts[{index}]"
                if not isinstance(artifact, dict):
                    errors.append(f"{label}: expected object")
                    continue
                require_fields(artifact, {"artifact_id", "path", "format", "role", "status", "editable", "check_evidence"}, label, errors)
                artifact_id = artifact.get("artifact_id")
                if not nonempty_string(artifact_id) or artifact_id in artifacts:
                    errors.append(f"{label}: artifact_id must be unique and non-empty")
                    continue
                artifacts[artifact_id] = artifact
                path_value = artifact.get("path")
                artifact_path = member_path(root, path_value)
                if not isinstance(path_value, str) or artifact_path is None:
                    errors.append(f"{label}: unsafe artifact path")
                status = artifact.get("status")
                artifact_format = artifact.get("format")
                if not in_enum(status, ARTIFACT_STATUSES):
                    errors.append(f"{label}: invalid artifact status")
                if not in_enum(artifact_format, ARTIFACT_FORMATS):
                    errors.append(f"{label}: invalid artifact format")
                elif artifact_format in FORMAT_SUFFIXES and isinstance(path_value, str) and Path(path_value).suffix.lower() != FORMAT_SUFFIXES[artifact_format]:
                    errors.append(f"{label}: artifact format does not match path suffix")
                if not in_enum(artifact.get("role"), ARTIFACT_ROLES):
                    errors.append(f"{label}: invalid artifact role")
                if not isinstance(artifact.get("editable"), bool):
                    errors.append(f"{label}: editable must be boolean")
                evidence = artifact.get("check_evidence")
                if not isinstance(evidence, list):
                    errors.append(f"{label}: check_evidence must be an array")
                strong_status = in_enum(status, {"produced", "inspected", "reviewed", "approved"})
                if strong_status and (artifact_path is None or not artifact_path.is_file()):
                    errors.append(f"{label}: {status} artifact has no file")
                elif strong_status and artifact_path.stat().st_size == 0:
                    errors.append(f"{label}: {status} artifact is empty")
                artifact_digest = hash_file(artifact_path) if strong_status and artifact_path is not None and artifact_path.is_file() else None
                if in_enum(status, {"inspected", "reviewed", "approved"}):
                    if not evidence:
                        errors.append(f"{label}: {status} artifact needs check evidence")
                    elif artifact_path is not None and artifact_path.is_file() and isinstance(artifact_format, str) and not credible_structural_evidence(root, path_value, artifact_path, artifact_format, evidence, label, errors):
                        errors.append(f"{label}: {status} artifact lacks credible structural inspection evidence")
                if in_enum(status, {"reviewed", "approved"}) and (artifact_digest is None or not review_supports_artifact(review, brief.get("state"), artifact_id, artifact_digest)):
                    errors.append(f"{label}: {status} artifact lacks a current digest-bound PASS or PASS_WITH_CONDITIONS review")
                if status == "approved" and (artifact_digest is None or not approval_supports_artifact(review, brief.get("approval_owner"), artifact_id, artifact_digest)):
                    errors.append(f"{label}: approved artifact lacks matching accountable-owner approval scope and timestamp")
                if status == "planned" and artifact_path is not None and artifact_path.exists():
                    warnings.append(f"{label}: planned artifact already exists; update status only after observed production")

    for artifact_id, artifact in artifacts.items():
        source_id = artifact.get("canonical_source_id")
        if source_id is not None and (not isinstance(source_id, str) or source_id not in artifacts):
            errors.append(f"artifact {artifact_id}: canonical_source_id references unknown artifact")

    if review:
        for field in ("operator_review", "independent_review"):
            entry = review.get(field)
            if not isinstance(entry, dict):
                errors.append(f"review/officecraft-review.json: {field} must be an object")
            elif not in_enum(entry.get("status"), REVIEW_STATUSES):
                errors.append(f"review/officecraft-review.json: {field} has invalid status")
            elif entry.get("status") in {"PASS", "PASS_WITH_CONDITIONS"}:
                if not in_enum(entry.get("officefile_state"), STATES):
                    errors.append(f"review/officecraft-review.json: {field} PASS disposition needs officefile_state")
                elif entry.get("officefile_state") != brief.get("state"):
                    errors.append(f"review/officecraft-review.json: {field} PASS disposition does not match current brief state")
                reviewed_artifacts = entry.get("reviewed_artifacts")
                if not isinstance(reviewed_artifacts, list) or not reviewed_artifacts or any(not isinstance(item, dict) or not nonempty_string(item.get("artifact_id")) or not isinstance(item.get("sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", item["sha256"]) for item in reviewed_artifacts):
                    errors.append(f"review/officecraft-review.json: {field} PASS disposition needs digest-bound reviewed_artifacts")
                else:
                    for index, reviewed_item in enumerate(reviewed_artifacts):
                        reviewed_label = f"review/officecraft-review.json: {field} reviewed_artifacts[{index}]"
                        current = artifacts.get(reviewed_item["artifact_id"])
                        current_path = member_path(root, current.get("path")) if isinstance(current, dict) else None
                        if not isinstance(current, dict) or not in_enum(current.get("status"), {"produced", "inspected", "reviewed", "approved"}) or current_path is None or not current_path.is_file():
                            errors.append(f"{reviewed_label}: does not identify a current registered produced file")
                        elif hash_file(current_path) != reviewed_item["sha256"]:
                            errors.append(f"{reviewed_label}: digest does not match current registered file")
        approval_records = review.get("approval_records", [])
        if not isinstance(approval_records, list):
            errors.append("review/officecraft-review.json: approval_records must be an array")
        else:
            for index, record in enumerate(approval_records):
                label = f"review/officecraft-review.json approval_records[{index}]"
                if not isinstance(record, dict):
                    errors.append(f"{label}: expected approval object")
                    continue
                if not nonempty_string(record.get("artifact_id")) or not isinstance(record.get("sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", record["sha256"]):
                    errors.append(f"{label}: artifact_id and sha256 are required")
                if not nonempty_string(record.get("approval_owner")) or not in_enum(record.get("authority_kind"), {"user", "accountable_owner"}):
                    errors.append(f"{label}: accountable approval authority is required")
                if not nonempty_string(record.get("approved_use")) or not valid_timestamp(record.get("approved_at")):
                    errors.append(f"{label}: approved_use and timezone-aware approved_at are required")
    if brief.get("state") == "handed_off" and "HANDOFF.md" not in file_relatives:
        errors.append("handed_off Officefile requires HANDOFF.md")

    return {"format": "officecraft-validation/v1", "officefile": str(root), "checked_at": utc_now(), "valid": not errors, "errors": errors, "warnings": warnings, "artifact_count": len(artifacts), "source_count": len(sources_by_id), "ledger_item_count": len(ledger_ids)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("officefile")
    parser.add_argument("--output", help="optional JSON evidence file; must not already exist")
    args = parser.parse_args(argv)
    report = validate_officefile(args.officefile)
    if args.output:
        output = Path(args.output).resolve()
        if output.exists():
            print(json.dumps({"format": "officecraft-validation/v1", "valid": False, "errors": [f"Refusing to overwrite output: {output}"], "warnings": []}), file=sys.stderr)
            return 2
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
