from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from pathlib import Path

FORMAT = "answerlayer/reality-ledger/v1"
VERSION = "0.2.0"
STATUSES = {"candidate", "accepted_delta", "rejected_noise", "fuzz_unresolved", "patched", "superseded", "retired"}
AUTHORITIES = {"model_generated", "machine_validated", "human_reviewed", "human_approved", "executed", "verified"}
LISTS = ("sources", "candidates", "deltas", "rejections", "fuzz", "patches", "probes", "traps", "watch", "approvals")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def parse_date(value: str, field: str, errors: list[str]) -> date | None:
    if value in ("", "unknown", "not_applicable", None):
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        errors.append(f"{field}: expected YYYY-MM-DD or explicit unknown/not_applicable")
        return None


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["Native document must be a JSON object."]
    if data.get("format") != FORMAT:
        errors.append("format: unsupported ledger format")
    if data.get("product_version") not in ("0.1.2", VERSION):
        errors.append("product_version: expected 0.1.2 or 0.2.0")
    for key in ("ledger_id", "title", "owner", "scope", "decision_use", "created_at", "updated_at", "baseline", "publication") + LISTS:
        if key not in data:
            errors.append(f"missing: {key}")
    for key in ("ledger_id", "title", "owner", "scope", "decision_use"):
        if key in data and (not isinstance(data[key], str) or not data[key]):
            errors.append(f"{key}: expected nonempty string")
    for key in ("created_at", "updated_at"):
        if key in data and not isinstance(data[key], str):
            errors.append(f"{key}: expected string")
    collections: dict[str, list] = {}
    for key in LISTS:
        value = data.get(key, [])
        if not isinstance(value, list):
            errors.append(f"{key}: expected array")
            value = []
        collections[key] = value
    baseline = data.get("baseline", {})
    if not isinstance(baseline, dict):
        errors.append("baseline: expected object")
    else:
        for key in ("version", "status", "as_of", "text", "authority", "approved_by", "approved_at", "supersedes"):
            if key not in baseline:
                errors.append(f"baseline: missing {key}")
        if not isinstance(baseline.get("version"), int) or isinstance(baseline.get("version"), bool) or baseline.get("version", 0) < 1:
            errors.append("baseline.version: expected positive integer")
        if not isinstance(baseline.get("text"), str):
            errors.append("baseline.text: expected string")
        for key in ("approved_by", "approved_at"):
            if key in baseline and baseline[key] is not None and not isinstance(baseline[key], str):
                errors.append(f"baseline.{key}: expected string or null")
        if "supersedes" in baseline and baseline["supersedes"] is not None and (not isinstance(baseline["supersedes"], int) or isinstance(baseline["supersedes"], bool)):
            errors.append("baseline.supersedes: expected integer or null")
        if baseline.get("status") not in ("candidate", "patched", "superseded", "retired"):
            errors.append("baseline.status: invalid")
        if not isinstance(baseline.get("authority"), str) or baseline.get("authority") not in AUTHORITIES:
            errors.append("baseline.authority: invalid")
        parse_date(baseline.get("as_of"), "baseline.as_of", errors)
        if baseline.get("status") == "patched" and baseline.get("authority") != "human_approved":
            errors.append("baseline: patched state requires human_approved authority")
        if baseline.get("authority") == "human_approved" and not (baseline.get("approved_by") and baseline.get("approved_at")):
            errors.append("baseline: human approval requires approver and date")
    seen: dict[str, str] = {}
    for collection, rows in collections.items():
        for index, item in enumerate(rows):
            loc = f"{collection}[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{loc}: expected object")
                continue
            ident = item.get("id")
            if not isinstance(ident, str) or not ident:
                errors.append(f"{loc}: expected nonempty string id")
            elif ident in seen:
                errors.append(f"{loc}: duplicate id also used by {seen[ident]}")
            else:
                seen[ident] = loc
            if not isinstance(item.get("status"), str) or item.get("status") not in STATUSES:
                errors.append(f"{loc}: invalid status")
            required = {
                "candidates": ("claim", "source_ids", "answer_change", "mechanism", "event_date", "publication_date", "effective_date", "threshold_date", "classification", "confidence_basis", "counterfactual", "recheck"),
                "patches": ("before", "after", "mechanism", "source_ids", "counterfactual", "authority", "approved_by", "approved_at"),
                "watch": ("condition", "operator", "threshold", "observed", "triggered", "next_review"),
            }.get(collection, ())
            for key in required:
                if key not in item:
                    errors.append(f"{loc}: missing {key}")
            if collection == "patches" and "authority" in item and (not isinstance(item["authority"], str) or item["authority"] not in AUTHORITIES):
                errors.append(f"{loc}.authority: invalid")
    source_ids = {x.get("id") for x in collections["sources"] if isinstance(x, dict) and isinstance(x.get("id"), str)}
    for collection in ("candidates", "deltas", "patches"):
        for index, item in enumerate(collections[collection]):
            if not isinstance(item, dict):
                continue
            references = item.get("source_ids", [])
            if not isinstance(references, list):
                errors.append(f"{collection}[{index}].source_ids: expected array")
                continue
            for source_id in references:
                if not isinstance(source_id, str) or source_id not in source_ids:
                    errors.append(f"{collection}[{index}]: unknown source_id {source_id}")
    patch_ids = {x.get("id") for x in collections["patches"] if isinstance(x, dict) and isinstance(x.get("id"), str)}
    for index, item in enumerate(collections["approvals"]):
        if isinstance(item, dict) and item.get("object_id"):
            object_id = item["object_id"]
            if not isinstance(object_id, str) or object_id not in patch_ids:
                errors.append(f"approvals[{index}]: unknown patch {object_id}")
    publication = data.get("publication", {})
    if not isinstance(publication, dict):
        errors.append("publication: expected object")
    else:
        for key in ("status", "approved_by", "approved_at", "scope"):
            if key not in publication:
                errors.append(f"publication: missing {key}")
        if publication.get("status") not in ("not_authorized", "approved", "published", "retired"):
            errors.append("publication.status: invalid")
        for key in ("approved_by", "approved_at", "scope"):
            if key in publication and publication[key] is not None and not isinstance(publication[key], str):
                errors.append(f"publication.{key}: expected string or null")
        if publication.get("status") in ("approved", "published") and not (publication.get("approved_by") and publication.get("approved_at") and publication.get("scope")):
            errors.append("publication: approval requires approver, date, and scope")
    return errors


def qualify(candidate: dict) -> list[str]:
    errors: list[str] = []
    required = ("id", "claim", "source_ids", "answer_change", "mechanism", "event_date", "publication_date", "effective_date", "threshold_date", "classification", "confidence_basis", "counterfactual", "recheck")
    for key in required:
        if key not in candidate:
            errors.append(f"missing: {key}")
    if candidate.get("classification") not in {"regime_shift", "structural_event", "strong_signal", "rejected_noise", "watch"}:
        errors.append("classification: invalid")
    if not candidate.get("answer_change"):
        errors.append("answer_change: exact changed answer surface required")
    if not candidate.get("mechanism"):
        errors.append("mechanism: required")
    if not candidate.get("source_ids"):
        errors.append("source_ids: at least one source required")
    for key in ("event_date", "publication_date", "effective_date", "threshold_date"):
        parse_date(candidate.get(key), key, errors)
    return errors


def next_recheck(anchor: date, half_life_days: int) -> date:
    if half_life_days < 1:
        raise ValueError("half_life_days must be positive")
    return anchor + timedelta(days=half_life_days)


def utc_stamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
