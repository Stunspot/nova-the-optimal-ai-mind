#!/usr/bin/env python3
"""Faultline occurrence, governed-pattern, and Error Neighborhood service."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from schema_validation import SchemaCatalog, SchemaError
from eligibility_policy import contains_secret_data, evaluate as evaluate_policy, parse_time_strict
from workspace_runtime import (
    ContinuityError, IdempotentReplay, atomic_json, dump_canonical, find_idempotent_receipt,
    new_id, read_json, read_jsonl, request_digest, transaction, utc_now,
    open_workspace, validate_external_target,
)

SENSITIVITY = {"ordinary": 0, "limited": 1, "sensitive": 2, "restricted": 3}
POLICY_VERSION = "cd-continuity-eligibility/v2"
REDACTION_VERSION = "cd-fault-redaction/v1"
FINGERPRINT_VERSION = "cd-fault-fingerprint/v1"
MATCHER_VERSION = "cd-fault-matcher/v1"
SECRET_PATTERNS = (
    re.compile(r"(?i)authorization\s*:\s*(?:bearer|basic)\s+\S+"),
    re.compile(r"(?i)\b(?:access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd|cookie|api[_-]?key)\b\s*[:=]\s*\S+"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{12,}"),
)
TOKEN_RE = re.compile(r"[a-z0-9]+")
SAFE_LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")
REFERENCE_RE = re.compile(r"^(?:EP|ST|PR|RC|AR|OP|TX|CCW|ENV)-[A-Za-z0-9-]{1,96}$")


def safe_label(value: str | None, label: str, *, nullable: bool = False) -> str | None:
    if value is None or not str(value).strip():
        if nullable:
            return None
        raise ContinuityError(f"{label} is required", "workspace_invalid")
    raw = str(value).strip()
    if contains_secret_data(raw) or not SAFE_LABEL_RE.fullmatch(raw):
        raise ContinuityError(f"{label} failed structured identifier policy", "redaction_rejected")
    return raw


def external_identity(value: str | None, label: str, *, nullable: bool = False) -> str | None:
    if value is None or not str(value).strip():
        if nullable:
            return None
        raise ContinuityError(f"{label} is required", "workspace_invalid")
    raw = str(value).strip()
    if contains_secret_data(raw):
        raise ContinuityError(f"{label} failed structured identifier policy", "redaction_rejected")
    return "XID-" + hashlib.sha256((label + "\0" + raw).encode("utf-8")).hexdigest()[:32]


def safe_reference(value: str | None, label: str) -> str:
    raw = str(value or "").strip()
    if contains_secret_data(raw) or not REFERENCE_RE.fullmatch(raw):
        raise ContinuityError(f"{label} failed canonical-reference policy", "redaction_rejected")
    return raw


def safe_references(value: str | None, label: str) -> list[str]:
    return list(dict.fromkeys(safe_reference(item, label) for item in parse_csv(value)))


def safe_tags(value: str | None) -> list[str]:
    return list(dict.fromkeys(str(safe_label(item, "tag")) for item in parse_csv(value)))


def schema_catalog() -> SchemaCatalog:
    return SchemaCatalog(Path(__file__).resolve().parents[1] / "assets" / "schemas")


def validate_or_raise(value: Any, schema: str) -> None:
    errors = schema_catalog().validate(value, schema)
    if errors:
        raise ContinuityError("Schema validation failed: " + "; ".join(errors[:6]), "workspace_invalid")


def parse_time(value: str | None, label: str = "time") -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ContinuityError(f"Invalid {label}", "workspace_invalid") from exc


def parse_csv(value: str | None) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in (value or "").split(",") if item.strip()))


def words(value: str | None) -> set[str]:
    return {token for token in TOKEN_RE.findall((value or "").lower()) if len(token) > 2}


def require_authority(value: str | None) -> str:
    try:
        return str(safe_label(value, "authority"))
    except ContinuityError as exc:
        if exc.code == "workspace_invalid":
            raise ContinuityError("Explicit authority is required", "authority_denied") from exc
        raise


def require_human_authority(value: str | None) -> str:
    authority = require_authority(value)
    if not authority.lower().startswith(("user", "human", "stunspot")):
        raise ContinuityError("Pattern governance requires recorded human authority", "authority_denied")
    return authority

def contains_secret(value: str | None) -> bool:
    return contains_secret_data(value)


def reject_secret_material(value: Any) -> None:
    if contains_secret_data(value):
        raise ContinuityError("Structured Faultline input was rejected by redaction policy", "redaction_rejected")


def safe_text(value: str, *, max_length: int = 500) -> str:
    if contains_secret(value):
        raise ContinuityError("Failure evidence was rejected by redaction policy", "redaction_rejected")
    text = re.sub(r"(?i)\b[A-F0-9]{24,}\b", "<opaque-id>", value)
    text = re.sub(r"[A-Za-z]:\\(?:[^\\\s]+\\)+[^\\\s]+", "<path>", text)
    text = re.sub(r"/(?:home|Users|var|tmp)/\S+", "<path>", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        raise ContinuityError("Redacted evidence is empty", "redaction_rejected")
    return text[:max_length]


def manifest_scope(root: Path) -> dict[str, Any]:
    return dict(read_json(root / "manifest.json")["scope"])


def scope_within_manifest(candidate: Any, manifest: dict[str, Any]) -> bool:
    if not isinstance(candidate, dict) or any(not candidate.get(k) for k in ("user", "project", "agent")):
        return False
    for key in ("user", "agent"):
        if manifest.get(key) != "*" and candidate.get(key) != manifest.get(key):
            return False
    if manifest.get("project") != "*" and candidate.get("project") != manifest.get("project"):
        return False
    return manifest.get("thread") in (None, "*") or candidate.get("thread") == manifest.get("thread")


def resolve_scope(root: Path, project: str | None, thread: str | None) -> dict[str, Any]:
    manifest = manifest_scope(root)
    scope = dict(manifest)
    if project is not None:
        scope["project"] = project
    if thread is not None:
        scope["thread"] = thread
    if not scope_within_manifest(scope, manifest):
        raise ContinuityError("Requested scope is outside workspace boundary", "scope_denied")
    return scope


def scope_matches_query(record_scope: Any, query_scope: dict[str, Any]) -> bool:
    if not isinstance(record_scope, dict):
        return False
    if any(record_scope.get(key) != query_scope.get(key) for key in ("user", "agent")):
        return False
    rp, qp = record_scope.get("project"), query_scope.get("project")
    if qp == "*":
        if rp != "*":
            return False
    elif rp not in ("*", qp):
        return False
    rt, qt = record_scope.get("thread"), query_scope.get("thread")
    return rt is None if qt in (None, "*") else rt in (None, qt)


def eligibility_result(
    row: dict[str, Any], scope: dict[str, Any], ceiling: str, now: datetime, *,
    environment_name: str | None, environment_version: str | None,
    episode_ids: set[str], unreachable_source_ids: set[str],
) -> tuple[bool, str]:
    schema = "episode-v2.schema.json" if row.get("type") is not None else "state-record-v2.schema.json"
    schema_valid = not schema_catalog().validate(row, schema)
    allowed_statuses = (None, "current") if row.get("type") is not None else ("current", "conflicted")
    allowed, reason, _ = evaluate_policy(
        row, scope=scope, ceiling=ceiling, now=now,
        environment=environment_name, environment_version=environment_version,
        episode_ids=episode_ids, unreachable_source_ids=unreachable_source_ids,
        allowed_statuses=allowed_statuses, schema_valid=schema_valid,
    )
    return allowed, reason


def eligible(
    row: dict[str, Any], scope: dict[str, Any], ceiling: str, now: datetime, *,
    environment_name: str | None = None, environment_version: str | None = None,
    episode_ids: set[str] | None = None, unreachable_source_ids: set[str] | None = None,
) -> bool:
    allowed, _ = eligibility_result(
        row, scope, ceiling, now, environment_name=environment_name,
        environment_version=environment_version, episode_ids=episode_ids or set(),
        unreachable_source_ids=unreachable_source_ids or set(),
    )
    return allowed

def environment(args: argparse.Namespace) -> dict[str, str | None]:
    return {
        "name": safe_label(args.environment, "environment", nullable=True),
        "version": safe_label(args.environment_version, "environment version", nullable=True),
        "os": safe_label(args.os, "os", nullable=True),
        "runtime": safe_label(args.runtime, "runtime", nullable=True),
    }


def fault_workspace(path_value: str | None, *, writable: bool) -> tuple[Path, str]:
    root, selector = open_workspace(path_value, writable=False)
    observed = read_json(root / "manifest.json").get("format")
    if observed != "cd-cognitive-continuity/v2":
        if observed == "cd-cognitive-continuity/v1":
            raise ContinuityError("Faultline is unavailable on v1; copy-migrate to a new v2 workspace", "operation_unsupported_v1")
        raise ContinuityError("Faultline requires a supported v2 workspace", "version_unsupported")
    return root, selector

def occurrence_fingerprint(data: dict[str, Any]) -> str:
    fields = {key: data.get(key) for key in ("producer", "tool", "provider", "operation_family", "error_code", "error_class", "message_template", "environment")}
    return hashlib.sha256(dump_canonical(fields).encode("utf-8")).hexdigest()


def _identity_facets(occurrence: dict[str, Any]) -> dict[str, Any]:
    return {key: occurrence.get(key) for key in ("producer", "tool", "provider", "operation_family", "environment")}


def _capture_disposition(rows: list[dict[str, Any]], occurrence: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    for existing in rows:
        if existing.get("type") != "failure_occurrence" or not isinstance(existing.get("occurrence"), dict):
            continue
        prior = existing["occurrence"]
        same_source = (
            prior.get("source_event_id") == occurrence.get("source_event_id")
            and prior.get("producer") == occurrence.get("producer")
        )
        if same_source:
            if prior.get("fingerprint") == occurrence.get("fingerprint") and prior.get("retry_of") == occurrence.get("retry_of"):
                return "duplicate", existing
            return "source_event_identity_conflict", existing
        operation_id = occurrence.get("operation_id")
        if operation_id and prior.get("operation_id") == operation_id:
            if _identity_facets(prior) != _identity_facets(occurrence):
                return "operation_identity_conflict", existing
            if prior.get("fingerprint") == occurrence.get("fingerprint"):
                return "duplicate", existing
            # One operation can emit more than one distinct compatible failure; preserve it.
    return None


def cmd_capture(args: argparse.Namespace) -> dict[str, Any]:
    root, selector = fault_workspace(args.workspace, writable=True)
    authority = require_authority(args.authority)
    message = safe_text(args.message)
    source_pointer = safe_text(args.source_pointer, max_length=300)
    operation_id = external_identity(args.operation_id, "operation-id", nullable=True)
    source_event_id = str(external_identity(args.source_event_id, "source-event-id"))
    observed_at = args.observed_at or utc_now()
    parse_time(observed_at, "observed_at")
    tags = safe_tags(args.tags)
    occurrences_before = occurrence_rows(root)
    retry_of = safe_reference(args.retry_of, "retry-of") if args.retry_of else None
    if retry_of and retry_of not in {row.get("id") for row in occurrences_before}:
        raise ContinuityError("retry-of must name an existing failure occurrence", "source_unreachable")
    occurrence = {
        "format": "cd-fault-occurrence/v1", "operation_id": operation_id,
        "source_event_id": source_event_id, "producer": safe_label(args.producer, "producer"),
        "tool": safe_label(args.tool, "tool", nullable=True),
        "provider": safe_label(args.provider, "provider", nullable=True),
        "operation_family": safe_label(args.operation_family, "operation-family"),
        "error_code": safe_label(args.error_code, "error-code", nullable=True),
        "error_class": safe_label(args.error_class, "error-class"),
        "message_template": message, "environment": environment(args),
        "observed_at": observed_at, "source_pointer": source_pointer,
        "correction_ids": safe_references(args.correction_ids, "correction-id"),
        "outcome_ids": safe_references(args.outcome_ids, "outcome-id"),
        "retry_of": retry_of, "fingerprint": "", "fingerprint_version": FINGERPRINT_VERSION,
        "redaction_policy_version": REDACTION_VERSION, "identity_uncertain": operation_id is None,
    }
    occurrence["fingerprint"] = occurrence_fingerprint(occurrence)
    request_payload = {
        "occurrence": {**occurrence, "observed_at": args.observed_at},
        "scope": resolve_scope(root, args.project, args.thread), "sensitivity": args.sensitivity,
        "retention": args.retention, "expires_at": args.expires_at, "tags": tags,
    }
    reject_secret_material({"request": request_payload, "idempotency_key": args.idempotency_key, "authority": authority})
    validate_or_raise(occurrence, "failure-occurrence.schema.json")
    now = utc_now()
    row = {
        "id": new_id("EP"), "type": "failure_occurrence", "recorded_at": now,
        "valid_from": now, "valid_to": None, "expires_at": args.expires_at,
        "scope": request_payload["scope"],
        "source": {"kind": "tool", "locator": source_pointer, "authority": authority},
        "content": f"{occurrence['error_class']}: {message}",
        "sensitivity": args.sensitivity, "retention": args.retention,
        "tags": tags, "occurrence": occurrence,
    }
    validate_or_raise(row, "episode-v2.schema.json")
    digest = request_digest("fault-capture", request_payload)
    duplicate = find_idempotent_receipt(root, args.idempotency_key, digest, "fault-capture")
    if duplicate:
        return duplicate
    disposition = _capture_disposition(occurrences_before, occurrence)
    if disposition:
        kind, existing = disposition
        if kind != "duplicate":
            raise ContinuityError(f"Capture identity conflicts with {existing.get('id')}", kind)
        return {"status": "duplicate_observation", "occurrence_id": existing["id"], "fingerprint": occurrence["fingerprint"], "observed_generation": read_json(root / "manifest.json")["generation"]}
    with transaction(root, "fault-capture", expected_generation=args.expected_generation, selector=selector,
                     authority=authority, idempotency_key=args.idempotency_key,
                     request_payload=request_payload, source_ids=[source_event_id]) as tx:
        fresh = occurrence_rows(root)
        disposition = _capture_disposition(fresh, occurrence)
        if disposition:
            kind, existing = disposition
            if kind != "duplicate":
                raise ContinuityError(f"Capture identity conflicts with {existing.get('id')}", kind)
            return {"status": "duplicate_observation", "occurrence_id": existing["id"], "fingerprint": occurrence["fingerprint"], "observed_generation": tx.generation_before}
        rows = read_jsonl(root / "episodes" / "events.jsonl")
        rows.append(row)
        tx.write_jsonl(root / "episodes" / "events.jsonl", rows)
        return tx.finish("failure-occurrence-captured", {"occurrence_id": row["id"], "fingerprint": occurrence["fingerprint"], "identity_uncertain": occurrence["identity_uncertain"], "redaction_policy_version": REDACTION_VERSION})

def occurrence_rows(root: Path) -> list[dict[str, Any]]:
    return [row for row in read_jsonl(root / "episodes" / "events.jsonl") if row.get("type") == "failure_occurrence" and isinstance(row.get("occurrence"), dict)]

def require_occurrences(root: Path, ids: list[str]) -> list[dict[str, Any]]:
    by_id = {row["id"]: row for row in occurrence_rows(root)}
    missing = sorted(set(ids) - set(by_id))
    if missing:
        raise ContinuityError("Unknown failure occurrence IDs: " + ", ".join(missing), "source_unreachable")
    return [by_id[item] for item in ids]

def max_sensitivity(rows: list[dict[str, Any]]) -> str:
    return max((str(row.get("sensitivity", "restricted")) for row in rows), key=lambda item: SENSITIVITY.get(item, 99))

def require_source_eligibility(
    root: Path, rows: list[dict[str, Any]], scope: dict[str, Any], ceiling: str, *,
    environment_name: str | None, environment_version: str | None,
    unreachable_source_ids: set[str],
) -> None:
    episode_ids = {str(row.get("id")) for row in read_jsonl(root / "episodes" / "events.jsonl") if row.get("id")}
    now = datetime.now(timezone.utc)
    for row in rows:
        allowed, reason = eligibility_result(
            row, scope, ceiling, now, environment_name=environment_name,
            environment_version=environment_version, episode_ids=episode_ids,
            unreachable_source_ids=unreachable_source_ids,
        )
        if not allowed:
            code = reason if reason in {"source_unreachable", "environment_mismatch", "environment_version_mismatch", "redaction_rejected"} else "source_ineligible"
            raise ContinuityError(f"Source {row.get('id')} failed eligibility: {reason}", code)


def _strict_future_expiry(value: str | None, now: datetime) -> str:
    expires, valid = parse_time_strict(value, nullable=False)
    if not valid or expires is None:
        raise ContinuityError("Accepted advice requires a finite timezone-aware expires-at", "authority_denied")
    if expires <= now:
        raise ContinuityError("Accepted advice expiry must be in the future", "authority_denied")
    return expires.isoformat().replace("+00:00", "Z")

def proposed_advice(text: str) -> dict[str, Any]:
    return {
        "text": text, "accepted": False, "authority_record_id": None, "authority": None,
        "accepted_at": None, "evidence_ids": [], "policy_id": "cd-error-neighborhood-advice/v1",
        "valid_from": None, "expires_at": None, "accepted_independent_of_cause": False,
        "survives_regression": False,
    }


def pattern_from_args(args: argparse.Namespace, occurrence_ids: list[str]) -> dict[str, Any]:
    return {
        "format": "cd-failure-pattern/v1", "pattern_revision": 0, "lifecycle_state": "proposed",
        "trigger": safe_text(args.trigger, max_length=500), "symptom": safe_text(args.symptom, max_length=500),
        "advice": {
            "avoid": proposed_advice(safe_text(args.avoid, max_length=500)),
            "do": proposed_advice(safe_text(args.do, max_length=500)),
            "verify": proposed_advice(safe_text(args.verify, max_length=500)),
        },
        "occurrence_ids": occurrence_ids, "causal_state": args.causal_state, "causal_evidence_ids": [],
        "resolution_state": "unresolved", "outcome_evidence_ids": [], "pattern_tags": safe_tags(args.tags),
        "matcher_facets": {
            "producer": safe_label(args.producer, "producer facet", nullable=True),
            "tool": safe_label(args.tool, "tool facet", nullable=True),
            "provider": safe_label(args.provider, "provider facet", nullable=True),
            "operation_family": safe_label(args.operation_family, "operation-family facet", nullable=True),
            "error_code": safe_label(args.error_code, "error-code facet", nullable=True),
            "error_class": safe_label(args.error_class, "error-class facet", nullable=True),
            "environment": safe_label(args.environment, "environment facet", nullable=True),
        },
        "correction_history": [],
    }


def cmd_pattern_propose(args: argparse.Namespace) -> dict[str, Any]:
    root, selector = fault_workspace(args.workspace, writable=True)
    authority = require_authority(args.authority)
    occurrence_ids = safe_references(args.occurrence_ids, "occurrence-id")
    if not occurrence_ids:
        raise ContinuityError("At least one occurrence ID is required", "source_unreachable")
    occurrences = require_occurrences(root, occurrence_ids)
    scope = resolve_scope(root, args.project, args.thread)
    unreachable = set(safe_references(args.unreachable_source_ids, "unreachable-source-id"))
    require_source_eligibility(
        root, occurrences, scope, args.sensitivity_ceiling,
        environment_name=args.environment, environment_version=args.environment_version,
        unreachable_source_ids=unreachable,
    )
    pattern = pattern_from_args(args, occurrence_ids)
    reject_secret_material({"pattern": pattern, "idempotency_key": args.idempotency_key, "authority": authority})
    validate_or_raise(pattern, "failure-pattern.schema.json")
    proposal = {
        "id": new_id("PR"), "created_at": utc_now(), "origin": "faultline", "operation": "add",
        "scope": scope, "target_id": None, "kind": "failure", "content": pattern["symptom"],
        "source_ids": occurrence_ids, "rationale": safe_text(args.rationale, max_length=800),
        "authority_required": safe_label(args.authority_required, "authority-required"), "risk": args.risk,
        "status": "proposed", "waking_review_id": None, "applied_record_id": None,
        "failure_pattern": pattern,
    }
    validate_or_raise(proposal, "proposal-v2.schema.json")
    reject_secret_material(proposal)
    payload = {
        "pattern": pattern, "scope": scope, "risk": args.risk,
        "rationale": proposal["rationale"], "authority_required": proposal["authority_required"],
    }
    digest = request_digest("fault-pattern-propose", payload)
    duplicate = find_idempotent_receipt(root, args.idempotency_key, digest, "fault-pattern-propose")
    if duplicate:
        return duplicate
    with transaction(root, "fault-pattern-propose", expected_generation=args.expected_generation,
                     selector=selector, authority=authority, idempotency_key=args.idempotency_key,
                     request_payload=payload, source_ids=occurrence_ids) as tx:
        # CAS under the lock guarantees the source snapshot rechecked above is unchanged.
        proposals = read_jsonl(root / "proposals" / "proposals.jsonl")
        proposals.append(proposal)
        tx.write_jsonl(root / "proposals" / "proposals.jsonl", proposals)
        return tx.finish("failure-pattern-proposed", {"proposal_id": proposal["id"], "causal_state": pattern["causal_state"], "resolution_state": pattern["resolution_state"], "advice_authorized": False})

def _accept_advice(pattern: dict[str, Any], args: argparse.Namespace, authority: str, evidence_ids: list[str], now: str) -> list[str]:
    accepted: list[str] = []
    choices = {"avoid": args.accept_avoid, "do": args.accept_do, "verify": args.accept_verify}
    for field, allowed in choices.items():
        value = pattern["advice"][field]
        if not allowed:
            continue
        value.update({
            "accepted": True, "authority_record_id": new_id("AR"), "authority": authority,
            "accepted_at": now, "evidence_ids": list(evidence_ids), "policy_id": "cd-error-neighborhood-advice/v1",
            "valid_from": now, "expires_at": args.expires_at,
            "accepted_independent_of_cause": bool(args.actions_independent_of_cause) if field in {"avoid", "do"} else True,
            "survives_regression": bool(args.avoid_survives_regression) if field == "avoid" else False,
        })
        accepted.append(field)
    return accepted


def cmd_pattern_apply(args: argparse.Namespace) -> dict[str, Any]:
    root, selector = fault_workspace(args.workspace, writable=True)
    authority = require_human_authority(args.authority)
    proposals = read_jsonl(root / "proposals" / "proposals.jsonl")
    proposal_id = safe_reference(args.proposal_id, "proposal-id")
    proposal = next((row for row in proposals if row.get("id") == proposal_id), None)
    if not proposal or proposal.get("origin") != "faultline" or proposal.get("kind") != "failure":
        raise ContinuityError("Unknown Faultline pattern proposal", "source_unreachable")
    if proposal.get("status") != "proposed":
        if proposal.get("status") == "accepted":
            return {"status": "duplicate_committed", "proposal_id": proposal["id"], "record_id": proposal.get("applied_record_id"), "observed_generation": read_json(root / "manifest.json")["generation"]}
        raise ContinuityError("Pattern proposal is not pending", "authority_denied")
    pattern = json.loads(json.dumps(proposal.get("failure_pattern")))
    validate_or_raise(pattern, "failure-pattern.schema.json")
    reject_secret_material({"proposal": proposal, "idempotency_key": args.idempotency_key, "authority": authority})
    if pattern.get("causal_state") == "verified":
        raise ContinuityError("A proposal cannot self-promote a verified cause", "authority_denied")
    occurrences = require_occurrences(root, list(proposal["source_ids"]))
    unreachable = set(safe_references(args.unreachable_source_ids, "unreachable-source-id"))
    require_source_eligibility(
        root, occurrences, proposal["scope"], args.sensitivity_ceiling,
        environment_name=args.environment, environment_version=args.environment_version,
        unreachable_source_ids=unreachable,
    )
    expected_environment = (pattern.get("matcher_facets") or {}).get("environment")
    if expected_environment and (not args.environment or str(expected_environment).casefold() != str(args.environment).casefold()):
        raise ContinuityError("Pattern environment is absent or mismatched at apply", "environment_mismatch")
    expiry = _strict_future_expiry(args.expires_at, datetime.now(timezone.utc))
    request_payload = {
        "proposal_id": proposal["id"], "accept_avoid": bool(args.accept_avoid),
        "accept_do": bool(args.accept_do), "accept_verify": bool(args.accept_verify),
        "actions_independent_of_cause": bool(args.actions_independent_of_cause),
        "avoid_survives_regression": bool(args.avoid_survives_regression),
        "retention": args.retention, "expires_at": expiry, "authority": authority,
        "environment": args.environment, "environment_version": args.environment_version,
        "sensitivity_ceiling": args.sensitivity_ceiling,
    }
    reject_secret_material({"request": request_payload, "idempotency_key": args.idempotency_key})
    digest = request_digest("fault-pattern-apply", request_payload)
    duplicate = find_idempotent_receipt(root, args.idempotency_key, digest, "fault-pattern-apply")
    if duplicate:
        return duplicate
    now = utc_now()
    args.expires_at = expiry
    pattern["pattern_revision"] = 1
    pattern["lifecycle_state"] = "accepted"
    accepted_fields = _accept_advice(pattern, args, authority, list(proposal["source_ids"]), now)
    record = {
        "id": new_id("ST"), "kind": "failure", "status": "current", "scope": proposal["scope"],
        "content": proposal["content"], "recorded_at": now, "valid_from": now, "valid_to": None,
        "source_ids": proposal["source_ids"], "source_class": "failure-occurrence-linked",
        "authority": authority, "confidence": "governed-pattern", "sensitivity": max_sensitivity(occurrences),
        "retention": args.retention, "expires_at": expiry,
        "supersedes": [], "conflicts_with": [], "derived_from": [], "tags": pattern.get("pattern_tags", []),
        "governance": {"operation": "proposal-applied", "authority": authority, "at": now, "proposal_id": proposal["id"]},
        "failure_pattern": pattern,
    }
    validate_or_raise(pattern, "failure-pattern.schema.json")
    validate_or_raise(record, "state-record-v2.schema.json")
    reject_secret_material(record)
    proposal["status"] = "accepted"
    proposal["applied_record_id"] = record["id"]
    validate_or_raise(proposal, "proposal-v2.schema.json")
    with transaction(root, "fault-pattern-apply", expected_generation=args.expected_generation,
                     selector=selector, authority=authority, idempotency_key=args.idempotency_key,
                     request_payload=request_payload, source_ids=proposal["source_ids"]) as tx:
        records = read_jsonl(root / "state" / "records.jsonl")
        records.append(record)
        tx.write_jsonl(root / "state" / "records.jsonl", records)
        tx.maybe_fail("pattern-after-state")
        tx.write_jsonl(root / "proposals" / "proposals.jsonl", proposals)
        return tx.finish("failure-pattern-applied", {"proposal_id": proposal["id"], "record_id": record["id"], "causal_state": pattern["causal_state"], "resolution_state": pattern["resolution_state"], "accepted_advice_fields": accepted_fields})

def cmd_pattern_transition(args: argparse.Namespace) -> dict[str, Any]:
    root, selector = fault_workspace(args.workspace, writable=True)
    authority = require_human_authority(args.authority)
    records = read_jsonl(root / "state" / "records.jsonl")
    pattern_id = safe_reference(args.pattern_id, "pattern-id")
    prior = next((row for row in records if row.get("id") == pattern_id and row.get("kind") == "failure"), None)
    if not prior or prior.get("status") not in {"current", "conflicted"}:
        raise ContinuityError("Pattern is not transitionable", "source_unreachable")
    pattern = json.loads(json.dumps(prior["failure_pattern"]))
    reject_secret_material({"pattern_record": prior, "idempotency_key": args.idempotency_key, "authority": authority})
    unreachable = set(safe_references(args.unreachable_source_ids, "unreachable-source-id"))
    require_source_eligibility(
        root, [prior], prior["scope"], args.sensitivity_ceiling,
        environment_name=args.environment, environment_version=args.environment_version,
        unreachable_source_ids=unreachable,
    )
    expected_environment = (pattern.get("matcher_facets") or {}).get("environment")
    if expected_environment and (not args.environment or str(expected_environment).casefold() != str(args.environment).casefold()):
        raise ContinuityError("Pattern environment is absent or mismatched at transition", "environment_mismatch")
    causal_ids = safe_references(args.causal_evidence_ids, "causal-evidence-id")
    outcome_ids = safe_references(args.outcome_evidence_ids, "outcome-evidence-id")
    evidence_ids = list(dict.fromkeys(causal_ids + outcome_ids))
    episode_rows = read_jsonl(root / "episodes" / "events.jsonl")
    episodes_by_id = {row.get("id"): row for row in episode_rows}
    missing = sorted(set(evidence_ids) - set(episodes_by_id))
    if missing:
        raise ContinuityError("Unknown transition evidence IDs: " + ", ".join(missing), "source_unreachable")
    if evidence_ids:
        require_source_eligibility(
            root, [episodes_by_id[item] for item in evidence_ids], prior["scope"], args.sensitivity_ceiling,
            environment_name=args.environment, environment_version=args.environment_version,
            unreachable_source_ids=unreachable,
        )
    new_causal = args.causal_state or pattern["causal_state"]
    new_resolution = args.resolution_state or pattern["resolution_state"]
    new_lifecycle = args.lifecycle_state or "accepted"
    if new_causal == "verified" and (not args.human_approved or not causal_ids):
        raise ContinuityError("Verified cause requires human approval and named causal evidence", "authority_denied")
    if new_resolution in {"resolved", "regressed"} and (not args.human_approved or not outcome_ids):
        raise ContinuityError("Resolution or regression requires human approval and named outcome evidence", "authority_denied")
    request_payload = {
        "pattern_id": prior["id"], "lifecycle_state": new_lifecycle,
        "causal_state": new_causal, "resolution_state": new_resolution,
        "causal_evidence_ids": causal_ids, "outcome_evidence_ids": outcome_ids,
        "human_approved": bool(args.human_approved), "authority": authority,
        "environment": args.environment, "environment_version": args.environment_version,
        "sensitivity_ceiling": args.sensitivity_ceiling,
    }
    reject_secret_material({"request": request_payload, "idempotency_key": args.idempotency_key})
    digest = request_digest("fault-pattern-transition", request_payload)
    duplicate = find_idempotent_receipt(root, args.idempotency_key, digest, "fault-pattern-transition")
    if duplicate:
        return duplicate
    pattern["pattern_revision"] = int(pattern.get("pattern_revision", 1)) + 1
    pattern["lifecycle_state"] = new_lifecycle
    pattern["causal_state"] = new_causal
    pattern["causal_evidence_ids"] = list(dict.fromkeys(pattern.get("causal_evidence_ids", []) + causal_ids))
    pattern["resolution_state"] = new_resolution
    pattern["outcome_evidence_ids"] = list(dict.fromkeys(pattern.get("outcome_evidence_ids", []) + outcome_ids))
    now = utc_now()
    pattern.setdefault("correction_history", []).append({"at": now, "authority": authority, "from": {"lifecycle_state": prior["failure_pattern"].get("lifecycle_state", "accepted"), "causal_state": prior["failure_pattern"]["causal_state"], "resolution_state": prior["failure_pattern"]["resolution_state"]}, "to": {"lifecycle_state": new_lifecycle, "causal_state": new_causal, "resolution_state": new_resolution}, "evidence_ids": evidence_ids})
    validate_or_raise(pattern, "failure-pattern.schema.json")
    replacement = json.loads(json.dumps(prior))
    replacement_status = "conflicted" if new_lifecycle == "conflicted" else (new_lifecycle if new_lifecycle in {"expired", "tombstoned"} else "current")
    replacement.update({"id": new_id("ST"), "status": replacement_status, "recorded_at": now, "valid_from": now, "valid_to": now if replacement_status in {"expired", "tombstoned"} else None, "source_ids": list(dict.fromkeys(prior["source_ids"] + evidence_ids)), "supersedes": [prior["id"]], "derived_from": list(dict.fromkeys(prior.get("derived_from", []) + [prior["id"]])), "authority": authority, "governance": {"operation": "failure-pattern-transition", "authority": authority, "at": now, "proposal_id": None}, "failure_pattern": pattern})
    validate_or_raise(replacement, "state-record-v2.schema.json")
    reject_secret_material(replacement)
    with transaction(root, "fault-pattern-transition", expected_generation=args.expected_generation,
                     selector=selector, authority=authority, idempotency_key=args.idempotency_key,
                     request_payload=request_payload, source_ids=evidence_ids) as tx:
        prior["status"] = "superseded"
        prior["valid_to"] = now
        records.append(replacement)
        tx.write_jsonl(root / "state" / "records.jsonl", records)
        return tx.finish("failure-pattern-transitioned", {"prior_record_id": prior["id"], "record_id": replacement["id"], "lifecycle_state": new_lifecycle, "causal_state": new_causal, "resolution_state": new_resolution})

def recurrence_lower_bound(rows: list[dict[str, Any]]) -> int:
    """Conservative lower bound over reliable operation/retry identity.

    Explicit operation identities and retry links may collapse observations. Any
    number of otherwise unlinked identity-uncertain observations proves only one
    additional occurrence, never one occurrence per row.
    """
    identifiers = [str(row.get("id")) for row in rows if row.get("id")]
    if not identifiers:
        return 0
    parent = {identifier: identifier for identifier in identifiers}

    def find(value: str) -> str:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: str, right: str) -> None:
        a, b = find(left), find(right)
        if a != b:
            parent[b] = a

    by_operation: dict[str, str] = {}
    for row in rows:
        identifier = str(row.get("id"))
        if identifier not in parent:
            continue
        occurrence = row.get("occurrence") or {}
        operation_id = occurrence.get("operation_id")
        if operation_id:
            key = str(operation_id)
            if key in by_operation:
                union(identifier, by_operation[key])
            else:
                by_operation[key] = identifier
        retry_of = occurrence.get("retry_of")
        if retry_of and str(retry_of) in parent:
            union(identifier, str(retry_of))

    components: dict[str, list[dict[str, Any]]] = {}
    by_id = {str(row.get("id")): row for row in rows if row.get("id")}
    for identifier in identifiers:
        components.setdefault(find(identifier), []).append(by_id[identifier])
    reliable = sum(
        1 for members in components.values()
        if any((member.get("occurrence") or {}).get("operation_id") for member in members)
    )
    uncertain_bucket = any(
        not any((member.get("occurrence") or {}).get("operation_id") for member in members)
        for members in components.values()
    )
    return max(1, reliable)

def query_facets(args: argparse.Namespace) -> dict[str, str | None]:
    return {"producer": safe_label(args.producer, "producer query", nullable=True), "tool": safe_label(args.tool, "tool query", nullable=True), "provider": safe_label(args.provider, "provider query", nullable=True), "operation_family": safe_label(args.operation_family, "operation-family query", nullable=True), "error_code": safe_label(args.error_code, "error-code query", nullable=True), "error_class": safe_label(args.error_class, "error-class query", nullable=True), "environment": safe_label(args.environment, "environment query", nullable=True)}


def facet_score(pattern: dict[str, Any], query: dict[str, str | None], task_words: set[str]) -> tuple[int, bool, list[str]]:
    facets = pattern.get("matcher_facets") or {}
    score = 0
    reasons: list[str] = []
    weights = {"operation_family": 80, "error_code": 60, "error_class": 40, "provider": 30, "tool": 25, "producer": 20, "environment": 20}
    for key, weight in weights.items():
        expected, observed = facets.get(key), query.get(key)
        if expected and observed and str(expected).casefold() != str(observed).casefold():
            if key in {"provider", "environment", "error_code", "error_class"}:
                return 0, False, []
            continue
        if expected and observed:
            score += weight
            reasons.append(f"same {key.replace('_', ' ')}")
    overlap = task_words & words(" ".join([str(pattern.get("trigger", "")), str(pattern.get("symptom", "")), " ".join(pattern.get("pattern_tags", []))]))
    score += len(overlap) * 6
    if overlap:
        reasons.append("task overlap: " + ", ".join(sorted(overlap)[:4]))
    return score, bool(score), reasons


def occurrence_score(row: dict[str, Any], query: dict[str, str | None], task_words: set[str]) -> tuple[int, bool, list[str]]:
    occurrence = row["occurrence"]
    synthetic = {"matcher_facets": {"producer": occurrence.get("producer"), "tool": occurrence.get("tool"), "provider": occurrence.get("provider"), "operation_family": occurrence.get("operation_family"), "error_code": occurrence.get("error_code"), "error_class": occurrence.get("error_class"), "environment": occurrence.get("environment", {}).get("name")}, "trigger": occurrence.get("operation_family"), "symptom": occurrence.get("message_template"), "pattern_tags": row.get("tags", [])}
    return facet_score(synthetic, query, task_words)
SAFE_PROBE_POLICY = "cd-fault-neutral-probe/v1"
ADVICE_POLICY = "cd-error-neighborhood-advice/v1"


def card_field(
    text: str, claim_state: str, provenance_kind: str, *, policy_id: str,
    pattern_id: str | None = None, pattern_revision: int | None = None,
    authority_record_id: str | None = None, evidence_ids: list[str] | None = None,
    valid_from: str | None = None, expires_at: str | None = None,
    survives_regression: bool | None = None,
) -> dict[str, Any]:
    value = {
        "text": text, "claim_state": claim_state, "provenance_kind": provenance_kind,
        "pattern_id": pattern_id, "pattern_revision": pattern_revision,
        "authority_record_id": authority_record_id, "evidence_ids": list(dict.fromkeys(evidence_ids or [])),
        "policy_id": policy_id, "valid_from": valid_from, "expires_at": expires_at,
    }
    if survives_regression is not None:
        value["survives_regression"] = survives_regression
    return value


def neutral_probe(evidence_ids: list[str], valid_from: str, expires_at: str) -> dict[str, Any]:
    return card_field(
        "Read the linked source pointer and compare operation identity, provider, tool, error code, and environment before choosing an action.",
        "neutral_probe", "neutral_probe_policy", policy_id=SAFE_PROBE_POLICY,
        evidence_ids=evidence_ids, valid_from=valid_from, expires_at=expires_at,
    )


def _cause_claim(pattern: dict[str, Any]) -> str:
    return {"unknown": "governed_unknown_cause", "hypothesis": "governed_hypothesis", "verified": "governed_verified"}.get(str(pattern.get("causal_state")), "governed_unknown_cause")


def governed_advice_field(row: dict[str, Any], name: str, now: datetime) -> dict[str, Any] | None:
    pattern = row.get("failure_pattern") or {}
    field = (pattern.get("advice") or {}).get(name)
    if not isinstance(field, dict) or not field.get("accepted"):
        return None
    required = ("text", "authority_record_id", "authority", "policy_id", "valid_from", "evidence_ids")
    if any(field.get(key) in (None, "") for key in required) or not isinstance(field.get("evidence_ids"), list) or not field["evidence_ids"]:
        return None
    valid_from, valid_from_ok = parse_time_strict(field.get("valid_from"), nullable=False)
    expires, expires_ok = parse_time_strict(field.get("expires_at"), nullable=False)
    if not valid_from_ok or valid_from is None or not expires_ok or expires is None:
        return None
    if valid_from > now or expires <= now:
        return None
    return card_field(
        str(field["text"]), _cause_claim(pattern), "governed_pattern_field",
        policy_id=str(field["policy_id"]), pattern_id=str(row["id"]),
        pattern_revision=int(pattern.get("pattern_revision", 0)),
        authority_record_id=str(field["authority_record_id"]), evidence_ids=list(field["evidence_ids"]),
        valid_from=str(field["valid_from"]), expires_at=field.get("expires_at") or row.get("expires_at"),
        survives_regression=bool(field.get("survives_regression")) if name == "avoid" else None,
    )


def _pattern_card(
    row: dict[str, Any], linked: list[dict[str, Any]], reasons: list[str], query: dict[str, str | None],
    now: datetime, view_expires: str,
) -> tuple[int, dict[str, Any], list[str]]:
    pattern = row["failure_pattern"]
    lifecycle = pattern.get("lifecycle_state", "accepted")
    resolution = pattern.get("resolution_state", "unresolved")
    cause = pattern.get("causal_state", "unknown")
    source_ids = list(dict.fromkeys([row["id"]] + [item["id"] for item in linked]))
    recurrence = recurrence_lower_bound(linked)
    claim = _cause_claim(pattern)
    card: dict[str, Any] = {
        "kind": "governed-pattern", "pattern_id": row["id"], "pattern_revision": int(pattern.get("pattern_revision", 0)),
        "lifecycle_state": lifecycle,
        "why_now": card_field("; ".join(reasons) or "eligible governed trigger", "observed", "deterministic_match", policy_id=MATCHER_VERSION, pattern_id=row["id"], pattern_revision=int(pattern.get("pattern_revision", 0)), authority_record_id=row["id"], evidence_ids=source_ids, valid_from=row.get("valid_from"), expires_at=row.get("expires_at") or view_expires),
        "recurrence": card_field(f"At least {recurrence} distinct operation identities matched; missing operation IDs retain identity uncertainty and this lower bound does not establish cause.", "lower_bound", "occurrence_evidence", policy_id=POLICY_VERSION, pattern_id=row["id"], pattern_revision=int(pattern.get("pattern_revision", 0)), authority_record_id=row["id"], evidence_ids=[item["id"] for item in linked], valid_from=min((item.get("valid_from") or item.get("recorded_at") for item in linked), default=row.get("valid_from")), expires_at=row.get("expires_at") or view_expires),
        "uncertainty": card_field(f"Cause is {cause}; resolution is {resolution}; recurrence is observational and advice authority is field-specific.", claim, "governed_pattern_field", policy_id=ADVICE_POLICY, pattern_id=row["id"], pattern_revision=int(pattern.get("pattern_revision", 0)), authority_record_id=row["id"], evidence_ids=list(dict.fromkeys(pattern.get("causal_evidence_ids", []) + pattern.get("outcome_evidence_ids", []) + [item["id"] for item in linked])), valid_from=row.get("valid_from"), expires_at=row.get("expires_at") or view_expires),
        "causal_state": card_field(str(cause), claim, "governed_pattern_field", policy_id=ADVICE_POLICY, pattern_id=row["id"], pattern_revision=int(pattern.get("pattern_revision", 0)), authority_record_id=row["id"], evidence_ids=list(pattern.get("causal_evidence_ids") or [item["id"] for item in linked]), valid_from=row.get("valid_from"), expires_at=row.get("expires_at") or view_expires),
        "resolution_state": card_field(str(resolution), claim, "governed_pattern_field", policy_id=ADVICE_POLICY, pattern_id=row["id"], pattern_revision=int(pattern.get("pattern_revision", 0)), authority_record_id=row["id"], evidence_ids=list(pattern.get("outcome_evidence_ids") or [item["id"] for item in linked]), valid_from=row.get("valid_from"), expires_at=row.get("expires_at") or view_expires),
        "source_ids": source_ids,
    }
    rejections: list[str] = []
    avoid = governed_advice_field(row, "avoid", now)
    do = governed_advice_field(row, "do", now)
    verify = governed_advice_field(row, "verify", now)
    cause_allows_actions = cause == "verified"
    if cause in {"unknown", "hypothesis"}:
        advice = pattern.get("advice") or {}
        cause_allows_avoid = bool((advice.get("avoid") or {}).get("accepted_independent_of_cause"))
        cause_allows_do = bool((advice.get("do") or {}).get("accepted_independent_of_cause"))
    else:
        cause_allows_avoid = cause_allows_actions
        cause_allows_do = cause_allows_actions
    environment_expected = (pattern.get("matcher_facets") or {}).get("environment")
    environment_current = not environment_expected or (query.get("environment") and str(environment_expected).casefold() == str(query.get("environment")).casefold())
    if lifecycle == "conflicted" or row.get("status") == "conflicted":
        card["verify"] = neutral_probe(source_ids, row.get("valid_from"), view_expires)
        rejections.extend(["conflicted_withheld_avoid", "conflicted_withheld_do"])
    elif resolution == "regressed":
        if avoid and avoid.get("survives_regression"):
            card["avoid"] = avoid
        else:
            rejections.append("regression_withheld_avoid")
        rejections.append("regression_withheld_do")
        card["verify"] = neutral_probe(source_ids, row.get("valid_from"), view_expires)
    else:
        if avoid and cause_allows_avoid:
            card["avoid"] = avoid
        elif avoid:
            rejections.append("cause_state_withheld_avoid")
        if do and cause_allows_do and (resolution != "resolved" or environment_current):
            card["do"] = do
        elif do:
            rejections.append("cause_or_environment_withheld_do")
        if verify:
            card["verify"] = verify
        else:
            card["verify"] = neutral_probe(source_ids, row.get("valid_from"), view_expires)
    rank = 100
    if resolution == "regressed":
        rank += 160
    elif resolution in {"unresolved", "mitigated"}:
        rank += 100
    elif resolution == "resolved":
        rank -= 50
    if lifecycle == "conflicted":
        rank += 40
    return rank, card, rejections


def _occurrence_card(rows: list[dict[str, Any]], reasons: list[str], view_expires: str) -> dict[str, Any]:
    representative = rows[-1]
    ids = [row["id"] for row in rows]
    recurrence = recurrence_lower_bound(rows)
    valid_from = min((row.get("valid_from") or row.get("recorded_at") for row in rows))
    return {
        "kind": "observed-candidate", "pattern_id": None, "pattern_revision": None, "lifecycle_state": "occurrence_only",
        "why_now": card_field(("; ".join(reasons) or "similar observed failure") + "; selection explains similarity, not cause", "observed", "deterministic_match", policy_id=MATCHER_VERSION, evidence_ids=ids, valid_from=valid_from, expires_at=view_expires),
        "recurrence": card_field(f"At least {recurrence} distinct operation identities matched; retry chains are collapsed, missing operation IDs retain identity uncertainty, and the count does not establish cause.", "lower_bound", "occurrence_evidence", policy_id=POLICY_VERSION, evidence_ids=ids, valid_from=valid_from, expires_at=view_expires),
        "uncertainty": card_field("Observed recurrence only; no reusable cause, avoidance, or repair has been accepted.", "observed", "occurrence_evidence", policy_id=ADVICE_POLICY, evidence_ids=ids, valid_from=valid_from, expires_at=view_expires),
        "causal_state": card_field("unknown", "observed", "occurrence_evidence", policy_id=ADVICE_POLICY, evidence_ids=ids, valid_from=valid_from, expires_at=view_expires),
        "resolution_state": card_field("unresolved", "observed", "occurrence_evidence", policy_id=ADVICE_POLICY, evidence_ids=ids, valid_from=valid_from, expires_at=view_expires),
        "verify": neutral_probe(ids, valid_from, view_expires),
        "source_ids": ids,
    }


def compile_neighborhood(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    started = time.monotonic()
    deadline_at = None if args.deadline_ms is None else started + max(0.0, float(args.deadline_ms)) / 1000.0

    def deadline_hit() -> bool:
        return deadline_at is not None and time.monotonic() >= deadline_at

    manifest = read_json(root / "manifest.json")
    if manifest.get("format") != "cd-cognitive-continuity/v2":
        raise ContinuityError("Error Neighborhood is unavailable on v1; copy-migrate for Faultline", "operation_unsupported_v1")
    scope = resolve_scope(root, args.project, args.thread)
    now = datetime.now(timezone.utc)
    created = now
    view_expires = (created + timedelta(minutes=args.expires_minutes)).isoformat().replace("+00:00", "Z")
    query = query_facets(args)
    environment_version = safe_label(args.environment_version, "environment-version query", nullable=True)
    task_words = words(safe_text(args.task, max_length=1000))
    unreachable = set(safe_references(args.unreachable_source_ids, "unreachable-source-id"))

    def deadline_view(candidate_count: int, eligible_count: int, omissions: dict[str, int]) -> dict[str, Any]:
        result = {
            "format": "cd-error-neighborhood/v1", "view_id": new_id("ENV"),
            "workspace_id": manifest["workspace_id"], "observed_generation": int(manifest["generation"]),
            "policy_version": POLICY_VERSION, "advice_policy_version": ADVICE_POLICY, "matcher_version": MATCHER_VERSION,
            "created_at": created.isoformat().replace("+00:00", "Z"), "expires_at": view_expires,
            "scope": scope, "candidate_count": candidate_count, "eligible_count": eligible_count,
            "selected_count": 0, "cards": [],
            "degradation": sorted(set(["deadline_exceeded"] + [f"eligibility:{key}:{count}" for key, count in omissions.items()])),
            "empty_means": "No eligible matching history was selected; this is not proof of safety or absence.",
            "value_boundary": "Compilation proves eligible evidence processing, not model attention, compliance, repair success, learning, or user value.",
        }
        if contains_secret_data(result):
            raise ContinuityError("Error Neighborhood failed final recursive redaction scan", "redaction_rejected")
        validate_or_raise(result, "error-neighborhood.schema.json")
        return result

    if deadline_hit():
        return deadline_view(0, 0, {})
    all_episodes = read_jsonl(root / "episodes" / "events.jsonl")
    raw_episode_ids = {str(row.get("id")) for row in all_episodes if row.get("id")}
    eligibility_omissions: dict[str, int] = {}

    def omit(reason: str) -> None:
        eligibility_omissions[reason] = eligibility_omissions.get(reason, 0) + 1

    eligible_episodes: list[dict[str, Any]] = []
    for row in all_episodes:
        if deadline_hit():
            return deadline_view(len(all_episodes), len(eligible_episodes), eligibility_omissions)
        allowed, reason = eligibility_result(
            row, scope, args.sensitivity, now, environment_name=query["environment"],
            environment_version=environment_version, episode_ids=raw_episode_ids,
            unreachable_source_ids=unreachable,
        )
        if allowed:
            eligible_episodes.append(row)
        else:
            omit(reason)
    eligible_episode_ids = {str(row["id"]) for row in eligible_episodes}
    eligible_occurrences = [row for row in eligible_episodes if row.get("type") == "failure_occurrence" and isinstance(row.get("occurrence"), dict)]
    eligible_occurrence_ids = {str(row["id"]) for row in eligible_occurrences}
    if deadline_hit():
        return deadline_view(len(all_episodes), len(eligible_episodes), eligibility_omissions)
    records = read_jsonl(root / "state" / "records.jsonl")
    failure_records = [row for row in records if row.get("kind") == "failure"]
    eligible_patterns: list[dict[str, Any]] = []
    for row in failure_records:
        if deadline_hit():
            return deadline_view(len(all_episodes) + len(failure_records), len(eligible_episodes) + len(eligible_patterns), eligibility_omissions)
        allowed, reason = eligibility_result(
            row, scope, args.sensitivity, now, environment_name=query["environment"],
            environment_version=environment_version, episode_ids=eligible_episode_ids,
            unreachable_source_ids=unreachable,
        )
        lifecycle = (row.get("failure_pattern") or {}).get("lifecycle_state", "accepted")
        if allowed and lifecycle not in {"proposed", "superseded", "expired", "tombstoned"}:
            eligible_patterns.append(row)
        else:
            omit(reason if not allowed else "lifecycle_ineligible")
    if deadline_hit():
        return deadline_view(len(all_episodes) + len(failure_records), len(eligible_episodes) + len(eligible_patterns), eligibility_omissions)
    proposals = [row for row in read_jsonl(root / "proposals" / "proposals.jsonl") if row.get("origin") == "faultline" and row.get("status") == "proposed"]
    candidate_count = len(failure_records) + len([row for row in all_episodes if row.get("type") == "failure_occurrence"]) + len(proposals)
    scored: list[tuple[int, str, dict[str, Any]]] = []
    covered_occurrences: set[str] = set()
    degradation: list[str] = []
    for row in eligible_patterns:
        if deadline_hit():
            return deadline_view(candidate_count, len(eligible_patterns) + len(eligible_occurrences), eligibility_omissions)
        pattern = row.get("failure_pattern") or {}
        occurrence_ids = list(pattern.get("occurrence_ids") or [])
        if not occurrence_ids or not set(occurrence_ids).issubset(eligible_occurrence_ids):
            omit("pattern_source_ineligible")
            continue
        score, matched, reasons = facet_score(pattern, query, task_words)
        if not matched:
            continue
        linked = [item for item in eligible_occurrences if item.get("id") in occurrence_ids]
        covered_occurrences.update(str(item["id"]) for item in linked)
        lifecycle_rank, card, rejections = _pattern_card(row, linked, reasons, query, now, view_expires)
        degradation.extend(rejections)
        scored.append((score + lifecycle_rank, str(row.get("recorded_at", "")), card))
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in eligible_occurrences:
        if deadline_hit():
            return deadline_view(candidate_count, len(eligible_patterns) + len(eligible_occurrences), eligibility_omissions)
        if str(row["id"]) not in covered_occurrences:
            groups.setdefault(str(row["occurrence"]["fingerprint"]), []).append(row)
    for rows in groups.values():
        if deadline_hit():
            return deadline_view(candidate_count, len(eligible_patterns) + len(eligible_occurrences), eligibility_omissions)
        representative = rows[-1]
        score, matched, reasons = occurrence_score(representative, query, task_words)
        if matched:
            scored.append((score, str(representative.get("recorded_at", "")), _occurrence_card(rows, reasons, view_expires)))
    scored.sort(key=lambda item: (item[0], item[1], dump_canonical(item[2])), reverse=True)
    if deadline_hit():
        return deadline_view(candidate_count, len(eligible_patterns) + len(eligible_occurrences), eligibility_omissions)
    selected = [item[2] for item in scored[: args.max_cards]]
    result = {
        "format": "cd-error-neighborhood/v1", "view_id": new_id("ENV"),
        "workspace_id": manifest["workspace_id"], "observed_generation": int(manifest["generation"]),
        "policy_version": POLICY_VERSION, "advice_policy_version": ADVICE_POLICY, "matcher_version": MATCHER_VERSION,
        "created_at": created.isoformat().replace("+00:00", "Z"), "expires_at": view_expires,
        "scope": scope, "candidate_count": candidate_count, "eligible_count": len(eligible_patterns) + len(eligible_occurrences),
        "selected_count": len(selected), "cards": selected,
        "degradation": sorted(set(degradation + [f"eligibility:{key}:{count}" for key, count in eligibility_omissions.items()])),
        "empty_means": "No eligible matching history was selected; this is not proof of safety or absence.",
        "value_boundary": "Compilation proves eligible evidence processing, not model attention, compliance, repair success, learning, or user value.",
    }
    if contains_secret_data(result):
        raise ContinuityError("Error Neighborhood failed final recursive redaction scan", "redaction_rejected")
    validate_or_raise(result, "error-neighborhood.schema.json")
    return result

def cmd_neighborhood(args: argparse.Namespace) -> dict[str, Any]:
    root, _ = fault_workspace(args.workspace, writable=False)
    before = read_json(root / "manifest.json")["generation"]
    result = compile_neighborhood(root, args)
    after = read_json(root / "manifest.json")["generation"]
    if before != after:
        result = compile_neighborhood(root, args)
        final = read_json(root / "manifest.json")["generation"]
        if result["observed_generation"] != final:
            raise ContinuityError("Workspace changed during both read attempts", "snapshot_changed")
    if args.output:
        output = validate_external_target(root, args.output, "Error Neighborhood output", must_be_absent=True)
        atomic_json(output, result)
    return result

def add_workspace(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("workspace", nargs="?", help="explicit workspace; omitted uses registry-anchored NOVA_CONTINUITY_HOME")

def add_generation(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--expected-generation", type=int, required=True)
    parser.add_argument("--idempotency-key", required=True)

def add_scope(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project")
    parser.add_argument("--thread")

def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    subs = root.add_subparsers(dest="command", required=True)
    capture = subs.add_parser("capture", help="Capture one redacted failure occurrence")
    add_workspace(capture); add_scope(capture); add_generation(capture)
    capture.add_argument("--operation-id")
    capture.add_argument("--source-event-id", required=True)
    capture.add_argument("--producer", required=True); capture.add_argument("--tool"); capture.add_argument("--provider")
    capture.add_argument("--operation-family", required=True); capture.add_argument("--error-code"); capture.add_argument("--error-class", required=True)
    capture.add_argument("--message", required=True); capture.add_argument("--source-pointer", required=True)
    capture.add_argument("--environment"); capture.add_argument("--environment-version"); capture.add_argument("--os"); capture.add_argument("--runtime")
    capture.add_argument("--observed-at"); capture.add_argument("--retry-of"); capture.add_argument("--correction-ids"); capture.add_argument("--outcome-ids")
    capture.add_argument("--authority", required=True); capture.add_argument("--sensitivity", choices=list(SENSITIVITY), default="limited")
    capture.add_argument("--retention", default="until-user-changes"); capture.add_argument("--expires-at"); capture.add_argument("--tags")
    capture.set_defaults(func=cmd_capture)

    propose = subs.add_parser("pattern-propose", help="Propose, but do not promote, a reusable failure pattern")
    add_workspace(propose); add_scope(propose); add_generation(propose)
    propose.add_argument("--occurrence-ids", required=True); propose.add_argument("--trigger", required=True); propose.add_argument("--symptom", required=True)
    propose.add_argument("--avoid", required=True); propose.add_argument("--do", required=True); propose.add_argument("--verify", required=True)
    propose.add_argument("--causal-state", choices=["unknown", "hypothesis"], default="unknown")
    propose.add_argument("--producer"); propose.add_argument("--tool"); propose.add_argument("--provider"); propose.add_argument("--operation-family"); propose.add_argument("--error-code"); propose.add_argument("--error-class"); propose.add_argument("--environment")
    propose.add_argument("--tags"); propose.add_argument("--rationale", required=True); propose.add_argument("--authority-required", default="human-review")
    propose.add_argument("--risk", choices=["low", "consequential", "sensitive", "irreversible"], default="consequential")
    propose.add_argument("--authority", required=True); propose.add_argument("--sensitivity-ceiling", choices=list(SENSITIVITY), default="limited")
    propose.add_argument("--environment-version"); propose.add_argument("--unreachable-source-ids")
    propose.set_defaults(func=cmd_pattern_propose)

    apply = subs.add_parser("pattern-apply", help="Apply one human-governed failure pattern proposal")
    add_workspace(apply); add_generation(apply)
    apply.add_argument("--proposal-id", required=True); apply.add_argument("--authority", required=True)
    apply.add_argument("--accept-avoid", action="store_true"); apply.add_argument("--accept-do", action="store_true"); apply.add_argument("--accept-verify", action="store_true")
    apply.add_argument("--actions-independent-of-cause", action="store_true")
    apply.add_argument("--avoid-survives-regression", action="store_true")
    apply.add_argument("--retention", default="until-user-changes"); apply.add_argument("--expires-at", required=True)
    apply.add_argument("--environment"); apply.add_argument("--environment-version")
    apply.add_argument("--sensitivity-ceiling", choices=list(SENSITIVITY), default="limited"); apply.add_argument("--unreachable-source-ids")
    apply.set_defaults(func=cmd_pattern_apply)

    transition = subs.add_parser("pattern-transition", help="Supersede a pattern with governed cause/resolution state")
    add_workspace(transition); add_generation(transition)
    transition.add_argument("--pattern-id", required=True); transition.add_argument("--authority", required=True); transition.add_argument("--human-approved", action="store_true")
    transition.add_argument("--causal-state", choices=["unknown", "hypothesis", "verified"])
    transition.add_argument("--resolution-state", choices=["unresolved", "mitigated", "resolved", "regressed"])
    transition.add_argument("--lifecycle-state", choices=["accepted", "conflicted", "expired", "tombstoned"])
    transition.add_argument("--causal-evidence-ids"); transition.add_argument("--outcome-evidence-ids")
    transition.add_argument("--environment"); transition.add_argument("--environment-version")
    transition.add_argument("--sensitivity-ceiling", choices=list(SENSITIVITY), default="limited"); transition.add_argument("--unreachable-source-ids")
    transition.set_defaults(func=cmd_pattern_transition)

    neighborhood = subs.add_parser("neighborhood", help="Compile zero to three expiring failure cards")
    add_workspace(neighborhood); add_scope(neighborhood)
    neighborhood.add_argument("--task", required=True); neighborhood.add_argument("--producer"); neighborhood.add_argument("--tool"); neighborhood.add_argument("--provider")
    neighborhood.add_argument("--operation-family"); neighborhood.add_argument("--error-code"); neighborhood.add_argument("--error-class"); neighborhood.add_argument("--environment"); neighborhood.add_argument("--environment-version")
    neighborhood.add_argument("--unreachable-source-ids")
    neighborhood.add_argument("--sensitivity", choices=list(SENSITIVITY), default="limited")
    neighborhood.add_argument("--max-cards", type=int, choices=[1, 2, 3], default=3)
    neighborhood.add_argument("--expires-minutes", type=int, choices=range(1, 61), default=10)
    neighborhood.add_argument("--deadline-ms", type=float); neighborhood.add_argument("--output")
    neighborhood.set_defaults(func=cmd_neighborhood)
    return root

def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        print(json.dumps(args.func(args), ensure_ascii=False, indent=2))
        return 0
    except IdempotentReplay as replay:
        print(json.dumps(replay.receipt, ensure_ascii=False, indent=2))
        return 0
    except (ContinuityError, SchemaError) as exc:
        code = exc.code if isinstance(exc, ContinuityError) else "workspace_invalid"
        print(json.dumps({"status": "error", "error": code, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())