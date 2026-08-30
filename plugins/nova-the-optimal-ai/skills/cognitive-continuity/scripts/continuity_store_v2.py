#!/usr/bin/env python3
"""Governed local store for Cognitive Continuity workspace schema v2."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from schema_validation import SchemaCatalog, SchemaError
from eligibility_policy import contains_secret_data, evaluate as evaluate_policy, parse_time_strict, sanitize_object, POLICY_ID
from workspace_runtime import (
    EXPORT_FORMAT,
    FORMAT,
    MEMBERS,
    IMPLEMENTATION_VERSION,
    LEGACY_FORMAT,
    ContinuityError,
    IdempotentReplay,
    atomic_json,
    atomic_bytes,
    atomic_new_json,
    atomic_new_bytes,
    dump_canonical,
    initialize_workspace,
    migrate_copy,
    new_id,
    read_json,
    read_jsonl,
    sha256_file,
    tree_digest,
    request_digest,
    find_idempotent_receipt,
    transaction,
    utc_now,
    workspace,
    workspace_selector,
    generation_path,
    open_snapshot,
    open_snapshot_identity,
    open_workspace,
    recover_transactions,
    validate_external_target,
    workspace_lock,
    revalidate_resolution,
    ResolutionToken,
    _has_reparse_component,
    _fsync_directory,
    _move_path_write_through,
    _directory_identity,
    _file_identity,
    _publish_directory,
    _read_direct_file_bytes,
    mutation_filesystem_support,
    _filesystem_qualification_witness,
    _loads,
)

PACKAGE_VERSION = IMPLEMENTATION_VERSION
LEGACY_EXPORT_FORMAT = "cd-cognitive-continuity-export/v1"
SENSITIVITY = {"ordinary": 0, "limited": 1, "sensitive": 2, "restricted": 3}
STATE_KINDS = (
    "identity", "user_model", "relationship", "permission", "goal",
    "commitment", "belief", "decision", "procedure", "failure", "hypothesis",
)
EPISODE_TYPES = (
    "message", "assertion", "decision", "permission", "commitment",
    "correction", "tool_action", "tool_result", "outcome", "import",
)
DERIVATIVE_DIRS = ("contexts", "projections", "dreams", "exports")
REFERENCE_KEYS = {
    "source_ids", "supersedes", "conflicts_with", "derived_from",
    "occurrence_ids", "evidence_ids", "selected_ids", "omitted_ids", "pattern_ids",
}
SINGLE_REFERENCE_KEYS = {
    "target_id", "applied_record_id", "waking_review_id", "retry_of", "superseded_by",
    "record_id", "episode_id", "proposal_id", "occurrence_id", "prior_record_id", "receipt_id",
}


def parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return list(dict.fromkeys(item.strip() for item in value.split(",") if item.strip()))


def parse_time(value: str | None, label: str = "time") -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ContinuityError(f"Invalid {label}: {value}") from exc


def manifest_scope(root: Path) -> dict[str, Any]:
    return read_json(root / "manifest.json")["scope"]


def scope_within_manifest(candidate: Any, manifest: dict[str, Any]) -> bool:
    if not isinstance(candidate, dict):
        return False
    if any(not candidate.get(key) for key in ("user", "project", "agent")):
        return False
    for key in ("user", "agent"):
        if manifest.get(key) != "*" and candidate.get(key) != manifest.get(key):
            return False
    if manifest.get("project") != "*" and candidate.get("project") != manifest.get("project"):
        return False
    manifest_thread = manifest.get("thread")
    return manifest_thread in (None, "*") or candidate.get("thread") == manifest_thread


def resolve_scope(root: Path, project: str | None = None, thread: str | None = None) -> dict[str, Any]:
    manifest = manifest_scope(root)
    scope = dict(manifest)
    if project is not None:
        scope["project"] = project
    if thread is not None:
        scope["thread"] = thread
    if not scope_within_manifest(scope, manifest):
        raise ContinuityError(f"Requested scope is outside workspace boundary: {scope}")
    return scope


def scope_matches_query(record_scope: Any, query_scope: dict[str, Any]) -> bool:
    if not isinstance(record_scope, dict):
        return False
    if any(record_scope.get(key) != query_scope.get(key) for key in ("user", "agent")):
        return False
    query_project = query_scope.get("project")
    record_project = record_scope.get("project")
    if query_project == "*":
        if record_project != "*":
            return False
    elif record_project not in ("*", query_project):
        return False
    query_thread = query_scope.get("thread")
    record_thread = record_scope.get("thread")
    if query_thread in (None, "*"):
        return record_thread is None
    return record_thread in (None, query_thread)


def time_and_sensitivity_eligible(
    row: dict[str, Any],
    ceiling: str,
    now: datetime,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
) -> bool:
    if SENSITIVITY.get(str(row.get("sensitivity", "restricted")), 99) > SENSITIVITY[ceiling]:
        return False
    valid_from = parse_time(row.get("valid_from"), "valid_from")
    valid_to = parse_time(row.get("valid_to"), "valid_to")
    expires_at = parse_time(row.get("expires_at"), "expires_at")
    if valid_from and valid_from > now:
        return False
    if valid_to and valid_to <= now:
        return False
    if expires_at and expires_at <= now:
        return False
    recorded = parse_time(row.get("recorded_at") or row.get("created_at"), "recorded_at")
    if start and (not recorded or recorded < start):
        return False
    if end and (not recorded or recorded >= end):
        return False
    return True


def require_authority(value: str | None) -> str:
    if not value or not value.strip():
        raise ContinuityError("This operation requires non-empty --authority")
    return value.strip()


def require_human_authority(value: str | None) -> str:
    authority = require_authority(value)
    if not authority.lower().startswith(("user", "human", "stunspot")):
        raise ContinuityError("This operation requires recorded human authority", "authority_denied")
    return authority

def require_sources(root: Path, source_ids: list[str]) -> None:
    episode_ids = {row.get("id") for row in read_jsonl(root / "episodes" / "events.jsonl")}
    missing = sorted(set(source_ids) - episode_ids)
    if missing:
        raise ContinuityError(f"Unknown source episode IDs: {', '.join(missing)}")


def cmd_init(args: argparse.Namespace) -> dict[str, Any]:
    _, receipt = initialize_workspace(
        args.workspace,
        user=args.user,
        project=args.project,
        agent=args.agent,
        thread=args.thread,
        sensitivity=args.sensitivity,
        retention=args.retention,
    )
    return receipt


def cmd_migrate_copy(args: argparse.Namespace) -> dict[str, Any]:
    return migrate_copy(
        args.source,
        args.destination,
        authority=require_human_authority(args.authority),
        expected_source_tree_sha256=args.source_tree_sha256,
        destination_mode=args.destination_mode,
        grant_id=args.destination_grant_id,
        expected_selector_registry_sha256=args.expected_selector_registry_sha256,
        expected_destination_sha256=args.expected_destination_path_sha256,
    )


def _open(args: argparse.Namespace, *, writable: bool) -> tuple[Path, str]:
    return open_workspace(args.workspace, writable=writable)


def reject_secret_input(value: Any) -> None:
    if contains_secret_data(value):
        raise ContinuityError("Input was rejected by recursive redaction policy", "redaction_rejected")


def cmd_episode(args: argparse.Namespace) -> dict[str, Any]:
    root, selector = _open(args, writable=True)
    authority = require_authority(args.authority)
    scope = resolve_scope(root, args.project, args.thread)
    tags = parse_csv(args.tags)
    request_payload = {
        "type": args.type, "content": args.content, "source_kind": args.source_kind,
        "locator": args.locator, "authority": authority, "valid_from": args.valid_from,
        "expires_at": args.expires_at, "scope": scope, "sensitivity": args.sensitivity,
        "retention": args.retention, "tags": tags,
    }
    reject_secret_input({"request": request_payload, "idempotency_key": args.idempotency_key})
    digest = request_digest("episode", request_payload)
    duplicate = find_idempotent_receipt(root, args.idempotency_key, digest, "episode")
    if duplicate:
        return duplicate
    now = utc_now()
    row = {
        "id": new_id("EP"), "type": args.type, "recorded_at": now,
        "valid_from": args.valid_from or now, "valid_to": None, "expires_at": args.expires_at,
        "scope": scope, "source": {"kind": args.source_kind, "locator": args.locator, "authority": authority},
        "content": args.content, "sensitivity": args.sensitivity, "retention": args.retention, "tags": tags,
    }
    _schema(row, "episode-v2.schema.json")
    reject_secret_input(row)
    with transaction(root, "episode", expected_generation=args.expected_generation, selector=selector,
                     authority=authority, idempotency_key=args.idempotency_key,
                     request_payload=request_payload) as tx:
        rows = read_jsonl(root / "episodes" / "events.jsonl")
        rows.append(row)
        tx.write_jsonl(root / "episodes" / "events.jsonl", rows)
        return tx.finish("episode-appended", {"episode_id": row["id"], "type": row["type"]})

def make_state_record(
    root: Path,
    *,
    kind: str,
    content: str,
    source_ids: list[str],
    authority: str,
    confidence: str,
    sensitivity: str,
    retention: str,
    supersedes: list[str] | None = None,
    conflicts: list[str] | None = None,
    derived: list[str] | None = None,
    proposal_id: str | None = None,
    valid_from: str | None = None,
    expires_at: str | None = None,
    scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    require_sources(root, source_ids)
    now = utc_now()
    return {
        "id": new_id("ST"), "kind": kind, "status": "current",
        "scope": scope or manifest_scope(root), "content": content,
        "recorded_at": now, "valid_from": valid_from or now, "valid_to": None,
        "source_ids": source_ids, "source_class": "episode-linked",
        "authority": authority, "confidence": confidence,
        "sensitivity": sensitivity, "retention": retention,
        "expires_at": expires_at, "supersedes": supersedes or [],
        "conflicts_with": conflicts or [], "derived_from": derived or [], "tags": [],
        "governance": {
            "operation": "recorded", "authority": authority, "at": now,
            "proposal_id": proposal_id,
        },
    }


def supersede_targets(records: list[dict[str, Any]], target_ids: list[str], at: str) -> None:
    available = {row["id"] for row in records}
    missing = sorted(set(target_ids) - available)
    if missing:
        raise ContinuityError(f"Unknown state IDs to supersede: {', '.join(missing)}")
    for row in records:
        if row["id"] in target_ids:
            row["status"] = "superseded"
            row["valid_to"] = at


def cmd_record(args: argparse.Namespace) -> dict[str, Any]:
    root, selector = _open(args, writable=True)
    authority = require_authority(args.authority)
    records = read_jsonl(root / "state" / "records.jsonl")
    supersedes = parse_csv(args.supersedes)
    if supersedes:
        supersede_targets(records, supersedes, utc_now())
    source_ids = parse_csv(args.source_ids)
    scope = resolve_scope(root, args.project, args.thread)
    request_payload = {
        "kind": args.kind, "content": args.content, "source_ids": source_ids,
        "authority": authority, "confidence": args.confidence, "sensitivity": args.sensitivity,
        "retention": args.retention, "supersedes": supersedes, "conflicts": parse_csv(args.conflicts),
        "derived_from": parse_csv(args.derived_from), "valid_from": args.valid_from,
        "expires_at": args.expires_at, "scope": scope,
    }
    reject_secret_input({"request": request_payload, "idempotency_key": args.idempotency_key})
    digest = request_digest("record", request_payload)
    duplicate = find_idempotent_receipt(root, args.idempotency_key, digest, "record")
    if duplicate:
        return duplicate
    row = make_state_record(
        root, kind=args.kind, content=args.content, source_ids=source_ids, authority=authority,
        confidence=args.confidence, sensitivity=args.sensitivity, retention=args.retention,
        supersedes=supersedes, conflicts=request_payload["conflicts"], derived=request_payload["derived_from"],
        valid_from=args.valid_from, expires_at=args.expires_at, scope=scope,
    )
    _schema(row, "state-record-v2.schema.json")
    reject_secret_input(row)
    with transaction(root, "record", expected_generation=args.expected_generation, selector=selector,
                     authority=authority, idempotency_key=args.idempotency_key,
                     request_payload=request_payload, source_ids=source_ids) as tx:
        records.append(row)
        tx.write_jsonl(root / "state" / "records.jsonl", records)
        return tx.finish("state-recorded", {"record_id": row["id"], "kind": row["kind"], "supersedes": supersedes})

def cmd_propose(args: argparse.Namespace) -> dict[str, Any]:
    root, selector = _open(args, writable=True)
    authority = require_authority(args.authority)
    source_ids = parse_csv(args.source_ids)
    require_sources(root, source_ids)
    scope = resolve_scope(root, args.project, args.thread)
    request_payload = {
        "origin": args.origin, "operation": args.operation, "scope": scope,
        "target_id": args.target_id, "kind": args.kind, "content": args.content,
        "source_ids": source_ids, "rationale": args.rationale,
        "authority_required": args.authority_required, "risk": args.risk,
        "waking_review_id": args.waking_review_id, "authority": authority,
    }
    reject_secret_input({"request": request_payload, "idempotency_key": args.idempotency_key})
    digest = request_digest("propose", request_payload)
    duplicate = find_idempotent_receipt(root, args.idempotency_key, digest, "propose")
    if duplicate:
        return duplicate
    row = {
        "id": new_id("PR"), "created_at": utc_now(), "origin": args.origin,
        "operation": args.operation, "scope": scope, "target_id": args.target_id,
        "kind": args.kind, "content": args.content, "source_ids": source_ids,
        "rationale": args.rationale, "authority_required": args.authority_required,
        "risk": args.risk, "status": "proposed", "waking_review_id": args.waking_review_id,
        "applied_record_id": None,
    }
    _schema(row, "proposal-v2.schema.json")
    reject_secret_input(row)
    with transaction(root, "propose", expected_generation=args.expected_generation, selector=selector,
                     authority=authority, idempotency_key=args.idempotency_key,
                     request_payload=request_payload, source_ids=source_ids) as tx:
        rows = read_jsonl(root / "proposals" / "proposals.jsonl")
        rows.append(row)
        tx.write_jsonl(root / "proposals" / "proposals.jsonl", rows)
        return tx.finish("proposal-created", {"proposal_id": row["id"], "origin": row["origin"], "operation": row["operation"]})

def cmd_apply(args: argparse.Namespace) -> dict[str, Any]:
    root, selector = _open(args, writable=True)
    authority = require_authority(args.authority)
    proposals = read_jsonl(root / "proposals" / "proposals.jsonl")
    proposal = next((row for row in proposals if row.get("id") == args.proposal_id), None)
    if not proposal:
        raise ContinuityError(f"Unknown proposal ID: {args.proposal_id}", "source_unreachable")
    if proposal.get("status") != "proposed":
        raise ContinuityError(f"Proposal is not pending: {proposal.get('status')}", "authority_denied")
    if proposal.get("origin") == "dream" and (not args.waking_approved or not proposal.get("waking_review_id")):
        raise ContinuityError("DREAM proposal requires a recorded waking review and --waking-approved", "authority_denied")
    request_payload = {
        "proposal_id": args.proposal_id, "authority": authority,
        "waking_approved": bool(args.waking_approved), "confidence": args.confidence,
        "sensitivity": args.sensitivity, "retention": args.retention,
    }
    reject_secret_input({"request": request_payload, "idempotency_key": args.idempotency_key, "proposal": proposal})
    digest = request_digest("apply", request_payload)
    duplicate = find_idempotent_receipt(root, args.idempotency_key, digest, "apply")
    if duplicate:
        return duplicate
    records = read_jsonl(root / "state" / "records.jsonl")
    operation = proposal["operation"]
    applied_id: str | None = None
    now = utc_now()
    if operation in {"add", "supersede"}:
        targets = [proposal["target_id"]] if operation == "supersede" and proposal.get("target_id") else []
        if operation == "supersede" and not targets:
            raise ContinuityError("Supersede proposal requires target_id", "source_unreachable")
        if targets:
            supersede_targets(records, targets, now)
        row = make_state_record(
            root, kind=proposal["kind"], content=proposal["content"], source_ids=proposal["source_ids"],
            authority=authority, confidence=args.confidence, sensitivity=args.sensitivity,
            retention=args.retention, supersedes=targets, proposal_id=proposal["id"],
            scope=proposal.get("scope") or manifest_scope(root),
        )
        _schema(row, "state-record-v2.schema.json")
        reject_secret_input(row)
        records.append(row)
        applied_id = row["id"]
    elif operation in {"expire", "tombstone"}:
        target = proposal.get("target_id")
        matched = False
        for row in records:
            if row.get("id") == target:
                row["status"] = "expired" if operation == "expire" else "tombstoned"
                row["valid_to"] = now
                matched = True
        if not matched:
            raise ContinuityError(f"Unknown target state ID: {target}", "source_unreachable")
        applied_id = target
    elif operation != "noop":
        raise ContinuityError(f"Unsupported proposal operation: {operation}", "workspace_invalid")
    proposal["status"] = "accepted"
    proposal["applied_record_id"] = applied_id
    _schema(proposal, "proposal-v2.schema.json")
    with transaction(root, "apply", expected_generation=args.expected_generation, selector=selector,
                     authority=authority, idempotency_key=args.idempotency_key,
                     request_payload=request_payload, source_ids=proposal.get("source_ids") or []) as tx:
        tx.write_jsonl(root / "state" / "records.jsonl", records)
        tx.maybe_fail("apply-after-state")
        tx.write_jsonl(root / "proposals" / "proposals.jsonl", proposals)
        return tx.finish("proposal-applied", {"proposal_id": proposal["id"], "record_id": applied_id, "authority": authority, "waking_approved": bool(args.waking_approved)})

def _references_any(value: Any, ids: set[str]) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in SINGLE_REFERENCE_KEYS and isinstance(child, str) and child in ids:
                return True
            if key in REFERENCE_KEYS and isinstance(child, list) and any(item in ids for item in child):
                return True
            if _references_any(child, ids):
                return True
    elif isinstance(value, list):
        return any(_references_any(item, ids) for item in value)
    return False


def _collections(root: Path) -> dict[str, tuple[Path, list[dict[str, Any]]]]:
    mapping = {
        "episodes": root / "episodes" / "events.jsonl",
        "state": root / "state" / "records.jsonl",
        "proposals": root / "proposals" / "proposals.jsonl",
    }
    return {name: (path, read_jsonl(path)) for name, path in mapping.items()}


def _derivative_references(path: Path, ids: set[str]) -> bool:
    try:
        if path.suffix.casefold() == ".json":
            return _references_any(read_json(path), ids)
        if path.suffix.casefold() == ".jsonl":
            return any(_references_any(row, ids) or row.get("id") in ids for row in read_jsonl(path))
        text = _read_direct_file_bytes(path, boundary=path.parent)[0].decode("utf-8-sig")
        return any(identifier in text for identifier in ids)
    except (ContinuityError, OSError, UnicodeError) as exc:
        raise ContinuityError(f"Derivative cannot be safely traversed: {path}: {exc}", "derivative_custody_unresolved") from exc


def _active_canonical_rows(root: Path) -> dict[str, list[dict[str, Any]]]:
    manifest = read_json(root / "manifest.json")
    rows = {name: values for name, (_, values) in _collections(root).items()}
    if manifest.get("format") == FORMAT:
        stable, _ = open_snapshot(root)
        bundle = generation_path(root, stable)
        rows["receipts"] = read_jsonl(bundle / "receipts.jsonl")
        rows["idempotency"] = read_jsonl(bundle / "idempotency.jsonl")
    else:
        rows["receipts"] = []
        rows["idempotency"] = []
    return rows


def _artifact_nodes(root: Path, ids: set[str], known_backups: list[str], known_export_receipts: list[str]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    manifest = read_json(root / "manifest.json")
    active = manifest.get("active_generation_path")
    generations = root / "generations"
    if generations.is_dir():
        for directory in sorted(item for item in generations.iterdir() if item.is_dir()):
            if directory.relative_to(root).as_posix() == active:
                continue
            hit = False
            for member in ("episodes.jsonl", "state.jsonl", "proposals.jsonl", "receipts.jsonl", "idempotency.jsonl"):
                path = directory / member
                if path.is_file() and any(row.get("id") in ids or _references_any(row, ids) for row in read_jsonl(path)):
                    hit = True
            if hit:
                nodes.append({"class": "prior_generation", "path": directory.relative_to(root).as_posix(), "owner": "continuity", "disposition": "retained_policy_bound", "proof": "canonical-row-traversal", "artifact_sha256": tree_digest(directory)})
    transactions = root / "transactions"
    if transactions.is_dir():
        for directory in sorted(item for item in transactions.iterdir() if item.is_dir()):
            matching = any(
                _derivative_references(path, ids)
                for path in sorted(item for item in directory.rglob("*") if item.is_file())
            )
            if matching:
                nodes.append({
                    "class": "transaction_journal",
                    "path": directory.relative_to(root).as_posix(),
                    "owner": "continuity",
                    "disposition": "retained_policy_bound",
                    "proof": "whole-finalized-transaction-content-traversal",
                    "artifact_sha256": tree_digest(directory),
                })
    quarantine = root / "quarantine"
    if quarantine.is_dir():
        for path in sorted(item for item in quarantine.rglob("*") if item.is_file()):
            if _derivative_references(path, ids):
                nodes.append({
                    "class": "quarantine",
                    "path": path.relative_to(root).as_posix(),
                    "owner": "continuity",
                    "disposition": "retained_policy_bound",
                    "proof": "content-traversal",
                    "artifact_sha256": sha256_file(path),
                })
    for raw, node_class in [(item, "known_backup") for item in known_backups] + [(item, "known_export") for item in known_export_receipts]:
        path = _outside_source(root, raw, node_class, require_mutation=False)
        if not path.exists():
            raise ContinuityError(f"Known lifecycle artifact is unreachable: {path}", "source_unreachable")
        digest = tree_digest(path) if path.is_dir() else sha256_file(path)
        nodes.append({"class": node_class, "path": str(path), "owner": "named-external-custody", "disposition": "retained_policy_bound", "proof": digest, "artifact_sha256": digest})
    return nodes


def _historical_canonical_ids(root: Path) -> set[str]:
    identifiers: set[str] = set()
    manifest = read_json(root / "manifest.json")
    if manifest.get("format") != FORMAT:
        return identifiers
    active = str(manifest.get("active_generation_path"))
    generations = root / "generations"
    if not generations.is_dir():
        return identifiers
    for directory in generations.iterdir():
        if not directory.is_dir() or directory.relative_to(root).as_posix() == active:
            continue
        for member in ("episodes.jsonl", "state.jsonl", "proposals.jsonl", "receipts.jsonl"):
            path = directory / member
            if path.is_file():
                identifiers.update(str(row["id"]) for row in read_jsonl(path) if row.get("id"))
    return identifiers

def build_forget_plan(
    root: Path, requested_ids: list[str], *, known_backups: list[str] | None = None,
    known_export_receipts: list[str] | None = None,
) -> dict[str, Any]:
    canonical = _active_canonical_rows(root)
    identifiable_rows = [row for name, rows in canonical.items() if name != "idempotency" for row in rows]
    all_ids = {str(row.get("id")) for row in identifiable_rows if row.get("id")} | _historical_canonical_ids(root)
    affected = set(requested_ids)
    missing = sorted(affected - all_ids)
    if missing:
        raise ContinuityError(f"Unknown IDs: {', '.join(missing)}", "source_unreachable")
    changed = True
    while changed:
        changed = False
        for row in identifiable_rows:
            identifier = row.get("id")
            if identifier and identifier not in affected and _references_any(row, affected):
                affected.add(str(identifier))
                changed = True
    idempotency_identities: list[str] = []
    for row in canonical["idempotency"]:
        if row.get("receipt_id") in affected or _references_any(row, affected):
            idempotency_identities.append(f"{row.get('operation_family')}:{row.get('idempotency_key')}")
    derivatives: list[str] = []
    for dirname in DERIVATIVE_DIRS:
        base = root / dirname
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and _derivative_references(path, affected):
                derivatives.append(path.relative_to(root).as_posix())
    nodes: list[dict[str, Any]] = []
    for name, rows in canonical.items():
        if name == "idempotency":
            for row in rows:
                identity = f"{row.get('operation_family')}:{row.get('idempotency_key')}"
                if identity in idempotency_identities:
                    nodes.append({"class": "active_idempotency", "identity": identity, "owner": "continuity", "disposition": "removed", "proof": "reference-traversal"})
            continue
        for row in rows:
            if row.get("id") in affected:
                nodes.append({"class": f"active_{name}", "identity": row.get("id"), "owner": "continuity", "disposition": "removed", "proof": "identity-or-reference-traversal"})
    nodes.extend({"class": "active_derivative", "path": path, "owner": "continuity", "disposition": "removed", "proof": "content-traversal"} for path in derivatives)
    nodes.extend(_artifact_nodes(root, affected, known_backups or [], known_export_receipts or []))
    for boundary in ("raw_source_evidence", "repository_history", "host_provider_logs", "os_snapshots", "protected_mind", "unknown_recipient_copies"):
        nodes.append({"class": boundary, "owner": "other-custody", "disposition": "unreachable", "proof": "boundary-declaration"})
    counts = {name: sum(1 for row in rows if row.get("id") in affected) for name, rows in canonical.items() if name != "idempotency"}
    counts["idempotency"] = len(idempotency_identities)
    counts["derived_files"] = len(derivatives)
    graph_digest = hashlib.sha256(dump_canonical(nodes).encode("utf-8")).hexdigest()
    return {
        "requested_ids": sorted(requested_ids), "removed_ids": sorted(affected),
        "idempotency_identities": sorted(idempotency_identities),
        "derivative_paths": derivatives, "counts": counts, "target_graph": nodes,
        "target_graph_sha256": graph_digest, "ambiguity": False,
        "known_backups": sorted(known_backups or []),
        "known_export_receipts": sorted(known_export_receipts or []),
    }

def _schema(value: Any, name: str) -> None:
    errors = SchemaCatalog(Path(__file__).resolve().parents[1] / "assets" / "schemas").validate(value, name)
    if errors:
        raise ContinuityError("Schema validation failed: " + "; ".join(errors[:8]), "workspace_invalid")


def _outside_source(
    root: Path, value: str, label: str, *, must_be_absent: bool = False, require_mutation: bool = True,
) -> Path:
    return validate_external_target(
        root, value, label, must_be_absent=must_be_absent, require_mutation=require_mutation,
    )

def _plan_digest(plan: dict[str, Any]) -> str:
    value = dict(plan)
    value["plan_digest"] = None
    return hashlib.sha256(dump_canonical(value).encode("utf-8")).hexdigest()


def cmd_forget_plan(args: argparse.Namespace) -> dict[str, Any]:
    root = workspace(args.workspace, writable=False)
    authority = require_human_authority(args.authority)
    requested = parse_csv(args.ids)
    if not requested:
        raise ContinuityError("forget-plan requires at least one exact ID", "source_unreachable")
    if args.mode == "physical-erase":
        raise ContinuityError("Physical erasure is outside the qualified v2 lifecycle adapter", "physical_erasure_unsupported")
    output = _outside_source(root, args.plan_output, "Forget plan output", must_be_absent=True)
    source_before = _workspace_evidence_digest(root)
    manifest = read_json(root / "manifest.json")
    observed_format = manifest.get("format")
    if observed_format not in {FORMAT, LEGACY_FORMAT}:
        raise ContinuityError("Unsupported workspace format", "version_unsupported")
    planned = build_forget_plan(root, requested, known_backups=parse_csv(args.known_backups), known_export_receipts=parse_csv(args.known_export_receipts))
    created = datetime.now(timezone.utc)
    generation = int(manifest.get("generation", 0))
    outcomes = {
        "corrected": False,
        "logically_forgotten": True,
        "removed_from_active_canon": args.mode == "active-remove",
        "deleted_from_named_continuity_custody": False,
        "physical_erasure_not_established": True,
    }
    target_sensitivity_classes = sorted({
        str(row.get("sensitivity", "restricted"))
        for _, rows in _collections(root).values()
        for row in rows if row.get("id") in set(planned["removed_ids"])
    })
    blocking_reasons: list[str] = []
    if observed_format != FORMAT:
        blocking_reasons.append("copy_migrate_to_v2")
    if planned.get("ambiguity"):
        blocking_reasons.append("resolve_target_graph_ambiguity")
    if planned.get("derivative_paths"):
        blocking_reasons.append("delete_named_derivatives_with_governed_adapter")
    if {"sensitive", "restricted"}.intersection(target_sensitivity_classes) or args.encryption_disposition != "not-required":
        blocking_reasons.append("install_verified_backup_encryption_adapter")
    apply_supported = not blocking_reasons
    plan = {
        "format": "cd-continuity-forget-plan/v2",
        "id": new_id("FGP"),
        "created_at": created.isoformat().replace("+00:00", "Z"),
        "expires_at": (created + timedelta(minutes=args.plan_minutes)).isoformat().replace("+00:00", "Z"),
        "authority": authority,
        "workspace_id": manifest.get("workspace_id"),
        "workspace_format": observed_format,
        "compatibility_mode": "v1_read_only" if observed_format == LEGACY_FORMAT else "v2_native",
        "source_manifest_sha256": sha256_file(root / "manifest.json"),
        "source_tree_sha256": source_before,
        "active_generation_manifest_sha256": manifest.get("active_generation_manifest_sha256"),
        "generation_before_plan": generation,
        "execute_generation": generation if observed_format == FORMAT else None,
        "result_generation": generation + 1 if observed_format == FORMAT else None,
        "apply_supported": apply_supported,
        "required_action": None if apply_supported else blocking_reasons[0],
        "blocking_reasons": blocking_reasons,
        "mode": args.mode,
        "requested_ids_sha256": hashlib.sha256("\n".join(sorted(requested)).encode("utf-8")).hexdigest(),
        "plan_digest": "",
        "status": "planned",
        **planned,
        "backup_policy": {
            "required": True,
            "custody": "external_to_active_workspace",
            "retention_until": args.retention_until,
            "destruction_owner": args.destruction_owner, "access_owner": args.access_owner,
        "encryption_disposition": args.encryption_disposition,
            "restore_test": "required_before_mutation",
        },
        "target_sensitivity_classes": target_sensitivity_classes,
        "expected_outcomes": outcomes,
        "external_boundaries": [
            "prior-immutable-generations", "external-forget-backup", "git-history", "host-or-provider-logs",
            "screenshots", "recipient-copies", "copies-outside-named-continuity-custody",
        ],
    }
    plan["plan_digest"] = _plan_digest(plan)
    _schema(plan, "forget-plan-v2.schema.json")
    if _workspace_evidence_digest(root) != source_before:
        raise ContinuityError("Source changed while the read-only plan was compiled", "source_changed")
    atomic_new_json(output, plan)
    if _workspace_evidence_digest(root) != source_before:
        raise ContinuityError(
            f"Source changed after plan publication; retained output: {output}",
            "recovery_required",
        )
    return {
        "format": "cd-continuity-forget-plan-result/v2", "status": "planned_external",
        "plan_output": str(output), "plan_id": plan["id"], "plan_digest": plan["plan_digest"],
        "compatibility_mode": plan["compatibility_mode"], "apply_supported": plan["apply_supported"],
        "blocking_reasons": plan["blocking_reasons"],
        "source_mutated": False, "counts": plan["counts"], "expected_outcomes": outcomes,
    }


def _workspace_evidence_digest(root: Path) -> str:
    """Digest direct workspace evidence while excluding transient lock metadata."""
    digest = hashlib.sha256()
    try:
        items = list(root.rglob("*"))
    except OSError as exc:
        raise ContinuityError("Workspace evidence cannot be enumerated", "custody_denied") from exc
    files: list[Path] = []
    for item in items:
        if _has_reparse_component(item, root):
            raise ContinuityError(
                f"Workspace evidence contains an indirect entry: {item}",
                "custody_reparse_escape",
            )
        if item.is_file():
            files.append(item)
    for path in sorted(files, key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if relative in {"locks/workspace-owner.json", "locks/workspace.lock"}:
            continue
        digest.update(relative.encode("utf-8") + b"\0" + bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()

def _jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return "".join(dump_canonical(row) + "\n" for row in rows).encode("utf-8")


def _load_backup_auth_key(root: Path, value: str) -> tuple[bytes, str]:
    path = validate_external_target(
        root, value, "Backup authentication key", must_be_absent=False, require_mutation=False,
    )
    if not path.is_file():
        raise ContinuityError("Backup authentication key is unavailable", "backup_authentication_required")
    key, _ = _read_direct_file_bytes(path, boundary=path.parent)
    if len(key) < 32:
        raise ContinuityError("Backup authentication key must contain at least 32 bytes", "backup_authentication_required")
    return key, hashlib.sha256(key).hexdigest()


def _backup_mac(metadata: dict[str, Any], key: bytes) -> str:
    value = json.loads(json.dumps(metadata))
    value.setdefault("authentication", {})["mac"] = None
    return hmac.new(key, dump_canonical(value).encode("utf-8"), hashlib.sha256).hexdigest()


def _create_external_backup(root: Path, plan: dict[str, Any], output: Path, authority: str, key: bytes, key_id: str) -> dict[str, Any]:
    """Build a fully synced sibling tree, then publish it atomically without clobber."""
    if output.exists():
        checked_root, metadata, _, _ = _load_backup(
            root, str(output), key, key_id, require_mutation=True,
        )
        if (
            checked_root != output
            or metadata.get("plan_id") != plan.get("id")
            or metadata.get("plan_digest") != plan.get("plan_digest")
            or metadata.get("authority") != authority
        ):
            raise ContinuityError(
                "Existing backup destination is not the requested completed backup",
                "protected_target_denied",
            )
        result = dict(metadata)
        result["backup_tree_sha256"] = tree_digest(output)
        return result

    manifest, _ = open_snapshot(root)
    bundle = generation_path(root, manifest)
    construction = output.parent / f".{output.name}.cc-backup-{plan['id']}"
    if construction.exists():
        try:
            checked_root, metadata, _, _ = _load_backup(
                root, str(construction), key, key_id, require_mutation=True,
            )
        except ContinuityError as exc:
            raise ContinuityError(
                f"Incomplete external backup construction requires explicit disposition; retained path: {construction}",
                "recovery_required",
            ) from exc
        if (
            checked_root != construction
            or metadata.get("plan_id") != plan.get("id")
            or metadata.get("plan_digest") != plan.get("plan_digest")
            or metadata.get("authority") != authority
        ):
            raise ContinuityError(
                f"External backup construction identity disagrees; retained path: {construction}",
                "recovery_required",
            )
        if output.exists():
            raise ContinuityError("External backup destination appeared", "protected_target_denied")
        try:
            _publish_directory(construction, output)
        except OSError as exc:
            raise ContinuityError(
                f"External backup publication is unconfirmed; retained path: {output if output.exists() else construction}",
                "recovery_required",
            ) from exc
        result = dict(metadata)
        result["backup_tree_sha256"] = tree_digest(output)
        return result

    construction_created = False
    try:
        construction.mkdir(parents=False, exist_ok=False)
        construction_created = True
        if _directory_identity(construction) is None:
            raise ContinuityError(
                f"External backup construction identity is unavailable; retained path: {construction}",
                "recovery_required",
            )
        snapshot = construction / "snapshot"
        active_relative = Path(str(manifest["active_generation_path"]))
        snapshot_bundle = snapshot / active_relative
        snapshot_bundle.mkdir(parents=True, exist_ok=False)
        files: list[dict[str, Any]] = []
        manifest_copy = snapshot / "manifest.json"
        manifest_bytes, _ = _read_direct_file_bytes(root / "manifest.json", boundary=root)
        atomic_new_bytes(manifest_copy, manifest_bytes)
        files.append({
            "path": "snapshot/manifest.json",
            "sha256": sha256_file(manifest_copy),
            "bytes": len(manifest_bytes),
        })
        for name in ("generation.json", *MEMBERS):
            source = bundle / name
            source_bytes, _ = _read_direct_file_bytes(source, boundary=root)
            destination = snapshot_bundle / name
            atomic_new_bytes(destination, source_bytes)
            files.append({
                "path": destination.relative_to(construction).as_posix(),
                "sha256": sha256_file(destination),
                "bytes": len(source_bytes),
            })
        with tempfile.TemporaryDirectory(prefix="continuity-restore-check-") as temporary:
            check = Path(temporary).resolve() / "workspace"
            shutil.copytree(snapshot, check)
            restored_manifest, _ = open_snapshot(check)
            if restored_manifest.get("workspace_id") != manifest.get("workspace_id") or restored_manifest.get("generation") != manifest.get("generation"):
                raise ContinuityError("Disposable full-workspace restore identity mismatch", "restore_failed")
        metadata = {
            "format": "cd-continuity-forget-backup/v2", "id": new_id("FB"), "created_at": utc_now(),
            "workspace_id": manifest.get("workspace_id"), "source_generation": manifest.get("generation"),
            "source_manifest_sha256": sha256_file(root / "manifest.json"),
            "source_active_generation_manifest_sha256": manifest.get("active_generation_manifest_sha256"),
            "source_tree_sha256": plan.get("source_tree_sha256"),
            "snapshot_tree_sha256": tree_digest(snapshot),
            "plan_id": plan["id"], "plan_digest": plan["plan_digest"], "authority": authority,
            "retention_until": plan["backup_policy"]["retention_until"],
            "destruction_owner": plan["backup_policy"]["destruction_owner"],
            "access_owner": plan["backup_policy"]["access_owner"],
            "encryption_disposition": plan["backup_policy"]["encryption_disposition"],
            "target_sensitivity_classes": plan.get("target_sensitivity_classes") or [],
            "restore_verified": True, "restore_verification": "disposable-open_snapshot-full-bundle/v1",
            "files": files,
            "authentication": {"algorithm": "hmac-sha256", "key_id": key_id, "mac": None},
            "media_erasure_limit": "Application-level lifecycle only; filesystem remanence and provider snapshots are unproven.",
        }
        metadata["authentication"]["mac"] = _backup_mac(metadata, key)
        atomic_new_json(construction / "backup.json", metadata)
        for directory in sorted(
            (item for item in construction.rglob("*") if item.is_dir()),
            key=lambda item: len(item.parts),
            reverse=True,
        ):
            _fsync_directory(directory)
        _fsync_directory(construction)
        if output.exists():
            raise ContinuityError("External backup destination appeared", "protected_target_denied")
        _publish_directory(construction, output)
        checked_root, checked, _, _ = _load_backup(
            root, str(output), key, key_id, require_mutation=True,
        )
        if checked_root != output or checked.get("id") != metadata.get("id"):
            raise ContinuityError(
                f"Published external backup verification failed; retained path: {output}",
                "recovery_required",
            )
        result = dict(checked)
        result["backup_tree_sha256"] = tree_digest(output)
        return result
    except BaseException as exc:
        retained = output if output.exists() else construction if construction_created else None
        if retained is not None:
            raise ContinuityError(
                f"External backup failed without race-unsafe cleanup; retained path: {retained}",
                "recovery_required",
            ) from exc
        raise
def _forgotten_pattern(pattern: dict[str, Any]) -> dict[str, Any]:
    value = json.loads(json.dumps(pattern))
    value["trigger"] = "[forgotten]"
    value["symptom"] = "[forgotten]"
    for field in ("avoid", "do", "verify"):
        advice = (value.setdefault("advice", {})).setdefault(field, {})
        advice.update({
            "text": "[forgotten]", "accepted": False,
            "authority_record_id": None, "authority": None, "accepted_at": None,
            "evidence_ids": [], "policy_id": "cd-error-neighborhood-advice/v1",
            "valid_from": None, "expires_at": None,
            "accepted_independent_of_cause": False, "survives_regression": False,
        })
    # Preserve schema shape, never source identity.
    value["occurrence_ids"] = ["EP-forgotten"]
    value["causal_state"] = "unknown"
    value["causal_evidence_ids"] = []
    value["resolution_state"] = "unresolved"
    value["outcome_evidence_ids"] = []
    value["pattern_tags"] = ["forgotten"]
    value["matcher_facets"] = {
        "producer": None, "tool": None, "provider": None,
        "operation_family": None, "error_code": None,
        "error_class": None, "environment": None,
    }
    value["correction_history"] = []
    return value

def _tombstone(row: dict[str, Any], at: str) -> dict[str, Any]:
    value = json.loads(json.dumps(row))
    value.pop("legacy_content_provenance", None)
    value["content"] = "[forgotten]"
    value["tags"] = list(dict.fromkeys(list(value.get("tags") or []) + ["forgotten"]))
    if value.get("type") == "failure_occurrence":
        old = value.get("occurrence") or {}
        value["occurrence"] = {
            "format": "cd-fault-occurrence/v1", "operation_id": None,
            "source_event_id": "forgotten", "producer": "forgotten", "tool": None, "provider": None,
            "operation_family": "forgotten", "error_code": None, "error_class": "forgotten",
            "message_template": "[forgotten]", "environment": {"name": None, "version": None, "os": None, "runtime": None},
            "observed_at": old.get("observed_at") or at, "source_pointer": "forgotten",
            "correction_ids": [], "outcome_ids": [], "retry_of": None,
            "fingerprint": hashlib.sha256(b"forgotten").hexdigest(),
            "fingerprint_version": "cd-fault-fingerprint/v1", "redaction_policy_version": "cd-fault-redaction/v1",
            "identity_uncertain": True,
        }
        if isinstance(value.get("source"), dict):
            value["source"]["locator"] = None
    if value.get("kind"):
        value["status"] = "tombstoned"
        value["valid_to"] = at
        if value.get("kind") == "failure" and value.get("failure_pattern"):
            value["failure_pattern"] = _forgotten_pattern(value["failure_pattern"])
    if value.get("origin"):
        value["status"] = "rejected"
        value["rationale"] = "[forgotten]"
        if value.get("failure_pattern"):
            value["failure_pattern"] = _forgotten_pattern(value["failure_pattern"])
    return value


def _load_plan(root: Path, path_value: str, supplied_digest: str) -> tuple[Path, dict[str, Any]]:
    plan_path = _outside_source(root, path_value, "Forget plan", require_mutation=False)
    plan = read_json(plan_path)
    if not isinstance(plan, dict) or plan.get("format") != "cd-continuity-forget-plan/v2" or plan.get("status") != "planned":
        raise ContinuityError("Forget plan is not executable", "plan_stale")
    actual = _plan_digest(plan)
    if plan.get("plan_digest") != actual or supplied_digest != actual:
        raise ContinuityError("Forget plan digest mismatch", "plan_stale")
    _schema(plan, "forget-plan-v2.schema.json")
    return plan_path, plan


def cmd_forget(args: argparse.Namespace) -> dict[str, Any]:
    root, selector = _open(args, writable=False)
    manifest = read_json(root / "manifest.json")
    if manifest.get("format") == LEGACY_FORMAT:
        raise ContinuityError("forget.apply is unavailable on v1; copy-migrate to a new v2 workspace", "migration_required_for_mutation")
    authority = require_human_authority(args.authority)
    _, plan = _load_plan(root, args.plan, args.plan_digest)
    if plan.get("workspace_id") != manifest.get("workspace_id") or plan.get("workspace_format") != FORMAT:
        raise ContinuityError("Forget plan belongs to another workspace or format", "plan_stale")
    backup_output = _outside_source(
        root,
        args.backup_output,
        "Forget backup",
        must_be_absent=False,
    )
    backup_policy = plan.get("backup_policy") or {}
    if (
        args.retention_until != backup_policy.get("retention_until")
        or args.destruction_owner != backup_policy.get("destruction_owner")
        or args.access_owner != backup_policy.get("access_owner")
        or args.encryption_disposition != backup_policy.get("encryption_disposition")
    ):
        raise ContinuityError(
            "Backup custody policy does not match the reviewed plan",
            "authority_denied",
        )
    key, key_id = _load_backup_auth_key(root, args.backup_auth_key_file)
    removed = set(plan["removed_ids"])
    idempotency_removed = set(plan.get("idempotency_identities") or [])
    payload = {
        "plan_id": plan["id"],
        "plan_digest": plan["plan_digest"],
        "mode": plan["mode"],
        "backup_destination_sha256": hashlib.sha256(str(backup_output).encode("utf-8")).hexdigest(),
        "backup_auth_key_id": key_id,
        "retention_until": args.retention_until,
        "destruction_owner": args.destruction_owner,
        "access_owner": args.access_owner,
        "encryption_disposition": args.encryption_disposition,
    }
    reject_secret_input({"request": payload, "idempotency_key": args.idempotency_key})
    digest = request_digest("forget", payload)
    duplicate = find_idempotent_receipt(root, args.idempotency_key, digest, "forget")
    if duplicate:
        return duplicate
    if not plan.get("apply_supported"):
        raise ContinuityError("Forget plan has unresolved blockers: " + ", ".join(plan.get("blocking_reasons") or []), "plan_blocked")
    plan_expiry = parse_time(plan.get("expires_at"), "plan expiry")
    if plan_expiry is None or plan_expiry <= datetime.now(timezone.utc):
        raise ContinuityError("Forget plan has expired", "plan_stale")
    if plan.get("source_manifest_sha256") != sha256_file(root / "manifest.json"):
        raise ContinuityError("Workspace manifest changed since planning", "plan_stale")
    if plan.get("source_tree_sha256") != _workspace_evidence_digest(root):
        raise ContinuityError("Workspace target graph changed since planning", "plan_stale")
    if int(plan.get("execute_generation", -1)) != args.expected_generation or int(manifest.get("generation", -1)) != args.expected_generation:
        raise ContinuityError("Forget plan generation is stale", "plan_stale")
    if plan.get("ambiguity"):
        raise ContinuityError("Ambiguous target graph cannot be applied", "plan_ambiguous")
    if plan.get("mode") == "physical-erase":
        raise ContinuityError("Physical erasure is outside the qualified v2 lifecycle adapter", "physical_erasure_unsupported")
    if plan.get("derivative_paths"):
        raise ContinuityError("Named derivative references require a transactional custody adapter", "derivative_custody_unresolved")
    recomputed = build_forget_plan(
        root, list(plan.get("requested_ids") or []),
        known_backups=list(plan.get("known_backups") or []),
        known_export_receipts=list(plan.get("known_export_receipts") or []),
    )
    if recomputed.get("target_graph_sha256") != plan.get("target_graph_sha256"):
        raise ContinuityError("Forget target traversal changed since planning", "plan_stale")
    retention_until = parse_time(args.retention_until, "retention-until")
    if retention_until is None or retention_until <= datetime.now(timezone.utc):
        raise ContinuityError("Backup retention-until must be a future time", "authority_denied")
    sensitive_targets = {"sensitive", "restricted"}.intersection(set(plan.get("target_sensitivity_classes") or []))
    if sensitive_targets or args.encryption_disposition != "not-required":
        raise ContinuityError("No verified artifact-encryption or encrypted-volume adapter is installed", "backup_encryption_unsupported")

    backup: dict[str, Any] | None = None
    tx = None
    try:
        with transaction(
            root, "forget", expected_generation=args.expected_generation, selector=selector,
            authority=authority, idempotency_key=args.idempotency_key, request_payload=payload, source_ids=removed,
        ) as tx:
            # The lock is held and the structured selector token has just been revalidated.
            if _workspace_evidence_digest(root) != plan["source_tree_sha256"]:
                raise ContinuityError("Workspace changed before backup creation", "plan_stale")
            under_lock = build_forget_plan(
                root, list(plan.get("requested_ids") or []),
                known_backups=list(plan.get("known_backups") or []),
                known_export_receipts=list(plan.get("known_export_receipts") or []),
            )
            if under_lock.get("target_graph_sha256") != plan.get("target_graph_sha256"):
                raise ContinuityError("Forget target traversal changed under lock", "plan_stale")
            canonical = _active_canonical_rows(root)
            backup = _create_external_backup(root, plan, backup_output, authority, key, key_id)
            now = utc_now()
            for name in ("episodes", "state", "proposals"):
                rows = canonical[name]
                if plan["mode"] == "active-remove":
                    result_rows = [row for row in rows if row.get("id") not in removed]
                else:
                    result_rows = [_tombstone(row, now) if row.get("id") in removed else row for row in rows]
                tx.write_member({"episodes": "episodes.jsonl", "state": "state.jsonl", "proposals": "proposals.jsonl"}[name], result_rows)
            tx.write_member("receipts.jsonl", [row for row in canonical["receipts"] if row.get("id") not in removed])
            tx.write_member("idempotency.jsonl", [row for row in canonical["idempotency"] if f"{row.get('operation_family')}:{row.get('idempotency_key')}" not in idempotency_removed])
            outcomes = {
                "corrected": False, "logically_forgotten": True,
                "removed_from_active_canon": plan["mode"] == "active-remove",
                "deleted_from_named_continuity_custody": False,
                "physical_erasure_not_established": True,
            }
            result = tx.finish("forgotten", {
                "plan_id": plan["id"], "plan_digest": plan["plan_digest"],
                "backup_id": backup["id"],
                "backup_destination_sha256": payload["backup_destination_sha256"],
                "backup_tree_sha256": backup["backup_tree_sha256"],
                "backup_retention_until": args.retention_until, "backup_destruction_owner": args.destruction_owner,
                "backup_access_owner": args.access_owner, "backup_encryption_disposition": args.encryption_disposition,
                "backup_authentication": {"algorithm": "hmac-sha256", "key_id": key_id},
                "backup_restore_verified": True, "mode": plan["mode"], "affected_id_count": len(removed),
                "counts": plan["counts"], "lifecycle_outcomes": outcomes,
                "prior_generations_retained": True, "recovery_backup_retained": True,
                "named_custody_deletion": "separate_governed_command_required",
                "physical_erasure": "not_established", "external_boundaries": plan["external_boundaries"],
            })
        return result
    except BaseException as exc:
        try:
            committed = find_idempotent_receipt(
                root,
                args.idempotency_key,
                digest,
                "forget",
            )
        except ContinuityError:
            committed = None
        if committed:
            return committed
        if backup is not None and backup_output.exists():
            raise ContinuityError(
                f"Forget did not prove commit; recovery backup retained for disposition: {backup_output}",
                "recovery_required",
            ) from exc
        raise

def _load_backup(
    root: Path,
    value: str,
    key: bytes,
    key_id: str,
    *,
    require_mutation: bool = False,
) -> tuple[Path, dict[str, Any], Path, dict[str, list[dict[str, Any]]]]:
    """Authenticate and consume one stable direct snapshot of every backup member."""
    backup_root = _outside_source(
        root,
        value,
        "Forget backup",
        require_mutation=require_mutation,
    )
    metadata = read_json(backup_root / "backup.json")
    if not isinstance(metadata, dict) or metadata.get("format") != "cd-continuity-forget-backup/v2" or not metadata.get("restore_verified"):
        raise ContinuityError("Forget backup metadata is invalid", "restore_failed")
    authentication = metadata.get("authentication") or {}
    supplied_mac = authentication.get("mac")
    if authentication.get("algorithm") != "hmac-sha256" or authentication.get("key_id") != key_id or not isinstance(supplied_mac, str):
        raise ContinuityError("Forget backup authentication identity is invalid", "backup_authentication_failed")
    if not hmac.compare_digest(supplied_mac, _backup_mac(metadata, key)):
        raise ContinuityError("Forget backup authentication failed", "backup_authentication_failed")
    manifest = read_json(root / "manifest.json")
    if metadata.get("workspace_id") != manifest.get("workspace_id"):
        raise ContinuityError("Forget backup belongs to another workspace", "restore_failed")

    records = metadata.get("files") or []
    if not isinstance(records, list):
        raise ContinuityError("Forget backup file inventory is invalid", "restore_failed")
    expected_records: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ContinuityError("Forget backup file inventory is invalid", "restore_failed")
        relative = Path(str(record.get("path")))
        if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
            raise ContinuityError("Backup member path is invalid", "restore_failed")
        key_name = relative.as_posix()
        if key_name in expected_records:
            raise ContinuityError("Backup member inventory is duplicated", "restore_failed")
        expected_records[key_name] = record

    snapshot = backup_root / "snapshot"
    actual_bytes: dict[str, bytes] = {}
    try:
        items = list(snapshot.rglob("*"))
    except OSError as exc:
        raise ContinuityError("Backup snapshot cannot be enumerated", "restore_failed") from exc
    for item in items:
        if _has_reparse_component(item, backup_root):
            raise ContinuityError("Backup snapshot contains indirect custody", "restore_failed")
        if item.is_dir():
            continue
        relative = item.relative_to(backup_root).as_posix()
        if relative not in expected_records:
            raise ContinuityError("Backup snapshot contains an unbound file", "restore_failed")
        try:
            value_bytes, _ = _read_direct_file_bytes(item, boundary=backup_root)
        except OSError as exc:
            raise ContinuityError("Backup member is missing or indirect", "restore_failed") from exc
        record = expected_records[relative]
        if (
            hashlib.sha256(value_bytes).hexdigest() != record.get("sha256")
            or len(value_bytes) != record.get("bytes")
        ):
            raise ContinuityError("Backup member is missing or corrupt", "restore_failed")
        actual_bytes[relative] = value_bytes
    if set(actual_bytes) != set(expected_records):
        raise ContinuityError("Backup member inventory is incomplete", "restore_failed")

    snapshot_digest = hashlib.sha256()
    for relative, value_bytes in sorted(
        (
            (Path(name).relative_to("snapshot").as_posix(), value)
            for name, value in actual_bytes.items()
            if Path(name).parts and Path(name).parts[0] == "snapshot"
        ),
        key=lambda item: item[0],
    ):
        snapshot_digest.update(
            relative.encode("utf-8")
            + b"\0"
            + hashlib.sha256(value_bytes).digest()
        )
    if snapshot_digest.hexdigest() != metadata.get("snapshot_tree_sha256"):
        raise ContinuityError("Backup snapshot tree digest mismatch", "restore_failed")

    manifest_bytes = actual_bytes.get("snapshot/manifest.json")
    if manifest_bytes is None:
        raise ContinuityError("Backup snapshot manifest is missing", "restore_failed")
    try:
        restored_manifest = _loads(manifest_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ContinuityError("Backup snapshot manifest is invalid", "restore_failed") from exc
    if (
        restored_manifest.get("format") != FORMAT
        or restored_manifest.get("workspace_id") != metadata.get("workspace_id")
        or restored_manifest.get("generation") != metadata.get("source_generation")
    ):
        raise ContinuityError("Backup snapshot identity mismatch", "restore_failed")
    active_relative = Path(str(restored_manifest.get("active_generation_path") or ""))
    if (
        active_relative.is_absolute()
        or any(part in {"", ".", ".."} for part in active_relative.parts)
        or len(active_relative.parts) != 2
        or active_relative.parts[0] != "generations"
    ):
        raise ContinuityError("Backup active generation path is invalid", "restore_failed")
    snapshot_bundle = snapshot / active_relative
    generation_key = (Path("snapshot") / active_relative / "generation.json").as_posix()
    generation_bytes = actual_bytes.get(generation_key)
    if generation_bytes is None or hashlib.sha256(generation_bytes).hexdigest() != restored_manifest.get("active_generation_manifest_sha256"):
        raise ContinuityError("Backup generation metadata digest mismatch", "restore_failed")
    try:
        generation_metadata = _loads(generation_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ContinuityError("Backup generation metadata is invalid", "restore_failed") from exc
    if (
        generation_metadata.get("workspace_id") != restored_manifest.get("workspace_id")
        or generation_metadata.get("generation") != restored_manifest.get("generation")
    ):
        raise ContinuityError("Backup generation identity mismatch", "restore_failed")

    restored_rows: dict[str, list[dict[str, Any]]] = {}
    members = generation_metadata.get("members") or {}
    for member in MEMBERS:
        member_key = (Path("snapshot") / active_relative / member).as_posix()
        member_bytes = actual_bytes.get(member_key)
        if member_bytes is None or hashlib.sha256(member_bytes).hexdigest() != (members.get(member) or {}).get("sha256"):
            raise ContinuityError(f"Backup canonical member is corrupt: {member}", "restore_failed")
        rows: list[dict[str, Any]] = []
        try:
            for line in member_bytes.decode("utf-8-sig").splitlines():
                if not line.strip():
                    continue
                row = _loads(line)
                if not isinstance(row, dict):
                    raise ValueError("row is not an object")
                rows.append(row)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ContinuityError(f"Backup canonical member is invalid: {member}", "restore_failed") from exc
        restored_rows[member] = rows
    return backup_root, metadata, snapshot_bundle, restored_rows

def cmd_restore_forget(args: argparse.Namespace) -> dict[str, Any]:
    root, selector = _open(args, writable=True)
    authority = require_human_authority(args.authority)
    key, key_id = _load_backup_auth_key(root, args.backup_auth_key_file)
    backup_root, metadata, snapshot_bundle, restored_rows = _load_backup(
        root, args.backup, key, key_id, require_mutation=False,
    )
    payload = {
        "backup_id": metadata["id"], "plan_id": metadata.get("plan_id"),
        "snapshot_tree_sha256": metadata.get("snapshot_tree_sha256"), "backup_auth_key_id": key_id,
    }
    reject_secret_input({"request": payload, "idempotency_key": args.idempotency_key})
    digest = request_digest("restore-forget", payload)
    duplicate = find_idempotent_receipt(root, args.idempotency_key, digest, "restore-forget")
    if duplicate:
        return duplicate
    manifest = read_json(root / "manifest.json")
    source_generation = int(metadata.get("source_generation", -2))
    if int(manifest.get("generation", -1)) != source_generation + 1 or args.expected_generation != source_generation + 1:
        raise ContinuityError("Intervening generation blocks exact forget restore", "restore_generation_conflict")
    active_receipts = _active_canonical_rows(root)["receipts"]
    matching_forget = [row for row in active_receipts if row.get("kind") == "forgotten" and row.get("backup_id") == metadata.get("id") and row.get("plan_id") == metadata.get("plan_id") and row.get("generation_after") == manifest.get("generation")]
    if len(matching_forget) != 1:
        raise ContinuityError("Current generation is not the exact forget result bound to this backup", "restore_generation_conflict")
    with transaction(root, "restore-forget", expected_generation=args.expected_generation,
                     selector=selector, authority=authority, idempotency_key=args.idempotency_key,
                     request_payload=payload) as tx:
        for member, rows in restored_rows.items():
            tx.write_member(member, rows)
        return tx.finish("forget-restored", {
            "backup_id": metadata["id"],
            "backup_destination_sha256": hashlib.sha256(str(backup_root).encode("utf-8")).hexdigest(),
            "plan_id": metadata.get("plan_id"), "restored_members": sorted(restored_rows),
            "backup_authentication": {"algorithm": "hmac-sha256", "key_id": key_id},
            "authority": authority,
            "lifecycle_outcomes": {"corrected": True, "logically_forgotten": False, "removed_from_active_canon": False, "deleted_from_named_continuity_custody": False, "physical_erasure_not_established": True},
        })
def _export_filter(
    rows: list[dict[str, Any]], *, kind: str, schema_name: str, scope: dict[str, Any],
    ceiling: str, now: datetime, start: datetime | None, end: datetime | None,
    environment: str | None, environment_version: str | None,
    episode_ids: set[str], unreachable_source_ids: set[str],
    episode_sensitivity: dict[str, str], omission_counts: dict[str, int],
) -> list[dict[str, Any]]:
    catalog = SchemaCatalog(Path(__file__).resolve().parents[1] / "assets" / "schemas")
    selected: list[dict[str, Any]] = []
    for row in rows:
        schema_valid = not catalog.validate(row, schema_name)
        candidate = row
        allowed_statuses: Iterable[Any]
        if kind == "proposal":
            source_ids = [str(item) for item in row.get("source_ids") or []]
            inferred = max((episode_sensitivity.get(item, "restricted") for item in source_ids), key=lambda item: SENSITIVITY.get(item, 99), default="restricted")
            candidate = {**row, "sensitivity": inferred, "valid_from": row.get("created_at"), "valid_to": None, "expires_at": None, "tags": []}
            allowed_statuses = ("proposed", "accepted", "conflicted")
        elif kind == "state":
            allowed_statuses = ("current", "conflicted")
        else:
            allowed_statuses = (None, "current")
        allowed, reason, _ = evaluate_policy(
            candidate, scope=scope, ceiling=ceiling, now=now,
            environment=environment, environment_version=environment_version,
            episode_ids=episode_ids, unreachable_source_ids=unreachable_source_ids,
            allowed_statuses=allowed_statuses, schema_valid=schema_valid,
        )
        recorded, recorded_ok = parse_time_strict(row.get("recorded_at") or row.get("created_at"), nullable=False)
        if allowed and (not recorded_ok or recorded is None):
            allowed, reason = False, "time_malformed"
        if allowed and start and recorded < start:
            allowed, reason = False, "time_before_range"
        if allowed and end and recorded >= end:
            allowed, reason = False, "time_after_range"
        if allowed and not contains_secret_data(row):
            selected.append(sanitize_object(row))
        else:
            if allowed:
                reason = "redaction_rejected"
            omission_counts[reason] = omission_counts.get(reason, 0) + 1
    return selected

def _stable_export_source(root: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]], str]:
    for _ in range(2):
        before = (root / "manifest.json").read_bytes()
        manifest = json.loads(before.decode("utf-8-sig"))
        if manifest.get("format") == FORMAT:
            stable, _ = open_snapshot(root)
            bundle = generation_path(root, stable)
            rows = {
                "episodes": read_jsonl(bundle / "episodes.jsonl"),
                "state": read_jsonl(bundle / "state.jsonl"),
                "proposals": read_jsonl(bundle / "proposals.jsonl"),
            }
        elif manifest.get("format") == LEGACY_FORMAT:
            rows = {
                "episodes": read_jsonl(root / "episodes" / "events.jsonl"),
                "state": read_jsonl(root / "state" / "records.jsonl"),
                "proposals": read_jsonl(root / "proposals" / "proposals.jsonl"),
            }
        else:
            raise ContinuityError("Unsupported export source format", "version_unsupported")
        after = (root / "manifest.json").read_bytes()
        if before == after:
            return manifest, rows, hashlib.sha256(before).hexdigest()
    raise ContinuityError("Workspace changed during both export snapshot attempts", "snapshot_changed")


def _export_snapshot(root: Path, args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest, rows, manifest_digest = _stable_export_source(root)
    scope = resolve_scope(root, args.project, args.thread)
    start = parse_time(args.from_time, "from")
    end = parse_time(args.to_time, "to")
    if start and end and start >= end:
        raise ContinuityError("Export --from must be earlier than --to", "scope_denied")
    now = datetime.now(timezone.utc)
    unreachable = set(parse_csv(args.unreachable_source_ids))
    v1 = manifest.get("format") == LEGACY_FORMAT
    omission_counts: dict[str, int] = {}
    raw_episode_ids = {str(row.get("id")) for row in rows["episodes"] if row.get("id")}
    eligible_episodes = _export_filter(
        rows["episodes"], kind="episode", schema_name="episode.schema.json" if v1 else "episode-v2.schema.json",
        scope=scope, ceiling=args.sensitivity, now=now, start=start, end=end,
        environment=args.environment, environment_version=args.environment_version,
        episode_ids=raw_episode_ids, unreachable_source_ids=unreachable,
        episode_sensitivity={}, omission_counts=omission_counts,
    )
    eligible_episode_ids = {str(row["id"]) for row in eligible_episodes}
    episode_sensitivity = {str(row["id"]): str(row.get("sensitivity", "restricted")) for row in eligible_episodes}
    selected = {
        "episodes": [] if args.exclude_episodes else eligible_episodes,
        "state": [] if args.exclude_state else _export_filter(
            rows["state"], kind="state", schema_name="state-record.schema.json" if v1 else "state-record-v2.schema.json",
            scope=scope, ceiling=args.sensitivity, now=now, start=start, end=end,
            environment=args.environment, environment_version=args.environment_version,
            episode_ids=eligible_episode_ids, unreachable_source_ids=unreachable,
            episode_sensitivity=episode_sensitivity, omission_counts=omission_counts,
        ),
        "proposals": [] if args.exclude_proposals else _export_filter(
            rows["proposals"], kind="proposal", schema_name="proposal.schema.json" if v1 else "proposal-v2.schema.json",
            scope=scope, ceiling=args.sensitivity, now=now, start=start, end=end,
            environment=args.environment, environment_version=args.environment_version,
            episode_ids=eligible_episode_ids, unreachable_source_ids=unreachable,
            episode_sensitivity=episode_sensitivity, omission_counts=omission_counts,
        ),
    }
    included_ids = sorted(str(row.get("id")) for values in selected.values() for row in values if row.get("id"))
    included_set = set(included_ids)
    excluded_ids = sorted(str(row.get("id")) for values in rows.values() for row in values if row.get("id") and str(row.get("id")) not in included_set)
    counts = {name: len(values) for name, values in selected.items()}
    excluded_counts = {name: max(0, len(rows[name]) - counts[name]) for name in rows}
    bundle = {
        "format": EXPORT_FORMAT, "implementation_version": IMPLEMENTATION_VERSION,
        "exported_at": utc_now(), "source_workspace_id": manifest.get("workspace_id"),
        "source_format": manifest.get("format"),
        "compatibility_mode": "v1_read_only" if v1 else "v2_native",
        "observed_generation": int(manifest.get("generation", 0)),
        "source_manifest_sha256": manifest_digest,
        "source_active_generation_manifest_sha256": manifest.get("active_generation_manifest_sha256"),
        "scope": scope,
        "selection": {
            "from": args.from_time, "to": args.to_time, "sensitivity_ceiling": args.sensitivity,
            "environment": args.environment, "environment_version": args.environment_version,
            "unreachable_source_ids_sha256": hashlib.sha256("\n".join(sorted(unreachable)).encode("utf-8")).hexdigest(),
            "episodes": not args.exclude_episodes, "state": not args.exclude_state,
            "proposals": not args.exclude_proposals, "eligibility_policy": POLICY_ID,
            "omission_counts": omission_counts,
        },
        "episodes": selected["episodes"], "state": selected["state"], "proposals": selected["proposals"],
        "included": {"counts": counts, "ids_sha256": hashlib.sha256("\n".join(included_ids).encode("utf-8")).hexdigest()},
        "excluded": {"counts": excluded_counts, "ids_sha256": hashlib.sha256("\n".join(excluded_ids).encode("utf-8")).hexdigest()},
        "capability_boundary": "Continuity-owned rows passing schema, scope, sensitivity, status/time/expiry, environment/version, source reachability, and recursive redaction; external telemetry and copies excluded.",
        "checksum": None,
    }
    if contains_secret_data(bundle):
        raise ContinuityError("Export failed final recursive redaction scan", "redaction_rejected")
    bundle["checksum"] = hashlib.sha256(dump_canonical(bundle).encode("utf-8")).hexdigest()
    _schema(bundle, "export-v2.schema.json")
    evidence = {"manifest": manifest, "manifest_digest": manifest_digest, "included_ids": included_ids, "excluded_ids": excluded_ids}
    return bundle, evidence

def cmd_export(args: argparse.Namespace) -> dict[str, Any]:
    root = workspace(args.workspace, writable=False)
    authority = require_human_authority(args.authority)
    output = _outside_source(root, args.output, "Export destination", must_be_absent=True)
    receipt_path = _outside_source(
        root,
        str(Path(str(output) + ".receipt.json")),
        "Export receipt destination",
        must_be_absent=True,
    )
    source_digest_before = tree_digest(root)
    bundle, evidence = _export_snapshot(root, args)
    if tree_digest(root) != source_digest_before:
        raise ContinuityError("Source workspace changed during export compilation", "source_changed")
    source_digest_after = tree_digest(root)
    if source_digest_after != source_digest_before:
        raise ContinuityError("Source workspace changed before export publication", "source_changed")
    created: list[Path] = []
    try:
        artifact_digest = hashlib.sha256(
            (json.dumps(bundle, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        ).hexdigest()
        receipt = {
            "format": "cd-continuity-export-receipt/v2", "id": new_id("EXR"), "created_at": utc_now(),
            "authority": authority, "source_workspace_id": bundle["source_workspace_id"],
            "source_format": bundle["source_format"], "compatibility_mode": bundle["compatibility_mode"],
            "observed_generation": bundle["observed_generation"],
            "source_manifest_sha256": evidence["manifest_digest"],
            "source_active_generation_manifest_sha256": evidence["manifest"].get("active_generation_manifest_sha256"),
            "source_tree_sha256_before": source_digest_before,
            "source_tree_sha256_after": source_digest_after,
            "request_policy": {"scope": bundle["scope"], "selection": bundle["selection"], "runtime_version": IMPLEMENTATION_VERSION},
            "included": bundle["included"], "excluded": bundle["excluded"],
            "artifact": {"path_sha256": hashlib.sha256(os.path.normcase(str(output)).encode("utf-8")).hexdigest(), "sha256": artifact_digest, "checksum": bundle["checksum"]},
            "external_boundaries": ["recipient-copies", "provider-or-host-logs", "screenshots", "other-custody-exports"],
            "source_mutated": False,
        }
        atomic_new_json(output, bundle)
        created.append(output)
        if sha256_file(output) != artifact_digest:
            raise ContinuityError("Published export artifact digest disagrees", "recovery_required")
        atomic_new_json(receipt_path, receipt)
        created.append(receipt_path)
        return {
            "format": "cd-continuity-export-result/v2", "status": "exported", "output": str(output),
            "receipt_output": str(receipt_path), "artifact_sha256": artifact_digest, "checksum": bundle["checksum"],
            "observed_generation": bundle["observed_generation"], "compatibility_mode": bundle["compatibility_mode"],
            "source_mutated": False, "counts": bundle["included"]["counts"], "excluded_counts": bundle["excluded"]["counts"],
        }
    except BaseException as exc:
        if created:
            names = ", ".join(str(path) for path in created)
            raise ContinuityError(
                f"Export failed without race-unsafe cleanup; retained path(s): {names}",
                "recovery_required",
            ) from exc
        raise


def cmd_import(args: argparse.Namespace) -> dict[str, Any]:
    root, selector = _open(args, writable=True)
    authority = require_authority(args.authority)
    source = _outside_source(root, args.input, "Import source", require_mutation=False)
    source_bytes, _ = _read_direct_file_bytes(source, boundary=source.parent)
    try:
        bundle = _loads(source_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ContinuityError("Import source is not valid direct JSON", "workspace_invalid") from exc
    observed_format = bundle.get("format") if isinstance(bundle, dict) else None
    if observed_format not in {EXPORT_FORMAT, LEGACY_EXPORT_FORMAT}:
        raise ContinuityError("Unsupported export format", "version_unsupported")
    supplied = bundle.get("checksum")
    check = dict(bundle); check["checksum"] = None
    actual = hashlib.sha256(dump_canonical(check).encode("utf-8")).hexdigest()
    if supplied != actual:
        raise ContinuityError("Export checksum mismatch", "workspace_invalid")
    schema_name = "export-v2.schema.json" if observed_format == EXPORT_FORMAT else "export.schema.json"
    _schema(bundle, schema_name)
    destination = _outside_source(
        root,
        args.quarantine_output,
        "Import quarantine",
        must_be_absent=False,
    )
    payload = {
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "checksum": supplied,
        "quarantine_output_sha256": hashlib.sha256(os.path.normcase(str(destination)).encode("utf-8")).hexdigest(),
    }
    digest = request_digest("import", payload)
    duplicate = find_idempotent_receipt(root, args.idempotency_key, digest, "import")
    if duplicate:
        return duplicate
    intent_path = destination.with_name(
        f".{destination.name}.import-{digest[:16]}.intent.json"
    )
    intent = {
        "format": "cd-continuity-import-intent/v1",
        "request_digest": digest,
        "idempotency_key_sha256": hashlib.sha256(
            str(args.idempotency_key).encode("utf-8")
        ).hexdigest(),
        "expected_generation": args.expected_generation,
        "source_sha256": payload["source_sha256"],
        "checksum": supplied,
        "quarantine_output_sha256": payload["quarantine_output_sha256"],
        "created_at": utc_now(),
    }
    if intent_path.exists():
        observed_intent = read_json(intent_path)
        immutable = (
            "format",
            "request_digest",
            "idempotency_key_sha256",
            "expected_generation",
            "source_sha256",
            "checksum",
            "quarantine_output_sha256",
        )
        if not isinstance(observed_intent, dict) or any(
            observed_intent.get(field) != intent.get(field) for field in immutable
        ):
            raise ContinuityError(
                "Import recovery intent disagrees with the request",
                "recovery_required",
            )
    else:
        if os.path.lexists(destination):
            raise ContinuityError(
                "Import quarantine destination is occupied without matching intent",
                "protected_target_denied",
            )
        atomic_new_json(intent_path, intent)
    if os.path.lexists(destination):
        try:
            destination_bytes, _ = _read_direct_file_bytes(
                destination,
                boundary=destination.parent,
            )
        except OSError as exc:
            raise ContinuityError(
                "Import quarantine recovery artifact is indirect",
                "recovery_required",
            ) from exc
        if hashlib.sha256(destination_bytes).hexdigest() != payload["source_sha256"]:
            raise ContinuityError(
                "Import quarantine recovery artifact disagrees with the source snapshot",
                "recovery_required",
            )
    else:
        atomic_new_bytes(destination, source_bytes)
    try:
        with transaction(root, "import", expected_generation=args.expected_generation, selector=selector, authority=authority, idempotency_key=args.idempotency_key, request_payload=payload) as tx:
            return tx.finish("import-quarantined", {"source_sha256": payload["source_sha256"], "external_quarantine_sha256": payload["quarantine_output_sha256"], "checksum": supplied, "canonical_state_changed": False, "authority": authority})
    except BaseException as exc:
        try:
            committed = find_idempotent_receipt(
                root,
                args.idempotency_key,
                digest,
                "import",
            )
        except ContinuityError:
            committed = None
        if committed:
            return committed
        raise ContinuityError(
            f"Import did not prove commit; intent and quarantine retained for recovery: {intent_path}, {destination}",
            "recovery_required",
        ) from exc


def _artifact_digest(path: Path) -> str:
    return tree_digest(path) if path.is_dir() else sha256_file(path)


def _lifecycle_artifact_identity_sha256(path: Path) -> str:
    if _has_reparse_component(path, path.parent):
        raise ContinuityError("Lifecycle artifact is indirect", "recovery_required")
    identity = _directory_identity(path) if path.is_dir() else _file_identity(path)
    if identity is None:
        raise ContinuityError(
            "Lifecycle artifact lacks a stable direct filesystem identity",
            "recovery_required",
        )
    material = f"{identity[0]}:{identity[1]}".encode("ascii")
    return hashlib.sha256(material).hexdigest()


def _emit_lifecycle_receipt(path: Path, receipt: dict[str, Any]) -> tuple[int, int]:
    """Publish one immutable lifecycle phase record."""
    receipt["updated_at"] = utc_now()
    _schema(receipt, "lifecycle-receipt-v1.schema.json")
    reject_secret_input(receipt)
    return atomic_new_json(path, receipt)


def _lifecycle_fail(point: str) -> None:
    if os.environ.get("CONTINUITY_LIFECYCLE_FAIL_POINT") == point:
        raise ContinuityError(f"Injected lifecycle failure at {point}", "injected_lifecycle_failure")


def _delete_application_artifact(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _resolve_named_plan_target(
    root: Path,
    plan: dict[str, Any],
    target_class: str,
    target_value: str,
    *,
    require_exists: bool = True,
) -> tuple[Path, dict[str, Any]]:
    supported = {"prior_generation", "transaction_journal", "quarantine", "known_export"}
    if target_class not in supported:
        raise ContinuityError("Named target class is outside the qualified adapter", "named_custody_target_unsupported")
    matches = [
        node
        for node in plan.get("target_graph") or []
        if node.get("class") == target_class
        and os.path.normcase(str(node.get("path"))) == os.path.normcase(str(target_value))
    ]
    if len(matches) != 1:
        raise ContinuityError("Exact named target is not uniquely present in the reviewed graph", "plan_ambiguous")
    node = matches[0]
    if target_class == "known_export":
        target = _outside_source(root, str(node["path"]), "Named export target")
    else:
        relative = Path(str(node["path"]))
        if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
            raise ContinuityError("Named internal target path is invalid", "protected_target_denied")
        lexical = root / relative
        if _has_reparse_component(lexical, root):
            raise ContinuityError("Named target crosses an unverified reparse edge", "custody_reparse_escape")
        target = lexical.resolve()
        try:
            target.relative_to(root.resolve())
        except ValueError as exc:
            raise ContinuityError("Named target escapes Continuity custody", "protected_target_denied") from exc
        prefix = {
            "prior_generation": "generations",
            "transaction_journal": "transactions",
            "quarantine": "quarantine",
        }[target_class]
        if not relative.parts or relative.parts[0].casefold() != prefix:
            raise ContinuityError("Named target class/path mismatch", "protected_target_denied")
    if require_exists and not target.exists():
        raise ContinuityError("Named target is absent", "source_unreachable")
    manifest = read_json(root / "manifest.json")
    if target == root.resolve() or target == generation_path(root, manifest) or target in {
        root / "manifest.json",
        root / "manifest.next",
        root / "locks",
        root / "transactions",
        root / "generations",
        root / "quarantine",
    }:
        raise ContinuityError("Active or protected Continuity target cannot be deleted", "protected_target_denied")
    if target_class == "transaction_journal" and target.exists():
        if not target.is_dir():
            raise ContinuityError(
                "Finalized transaction custody must be deleted as a whole directory",
                "protected_target_denied",
            )
        journal_path = target / "journal.json"
        journal = read_json(journal_path)
        if journal.get("state") not in {"finalized", "aborted"}:
            raise ContinuityError("Unfinished transaction evidence cannot be deleted", "recovery_required")
    return target, node


def _lifecycle_receipt_id(
    *,
    operation: str,
    authority: str,
    workspace_id: str,
    target: Path,
    receipt_output: Path,
) -> str:
    material = {
        "operation": operation,
        "authority": authority,
        "workspace_id": workspace_id,
        "target_path_sha256": hashlib.sha256(
            os.path.normcase(str(target)).encode("utf-8")
        ).hexdigest(),
        "receipt_output_sha256": hashlib.sha256(
            os.path.normcase(str(receipt_output)).encode("utf-8")
        ).hexdigest(),
    }
    return "LCR-" + hashlib.sha256(dump_canonical(material).encode("utf-8")).hexdigest()[:16]


def _lifecycle_receipt_base(
    *,
    operation: str,
    authority: str,
    workspace_id: str,
    plan_id: str | None,
    plan_digest: str | None,
    target_class: str,
    target: Path,
    target_digest: str,
    receipt_output: Path,
    retention_until: str | None = None,
    destruction_owner: str | None = None,
    backup_id: str | None = None,
    backup_authentication_key_id: str | None = None,
) -> dict[str, Any]:
    now = utc_now()
    return {
        "format": "cd-continuity-lifecycle-receipt/v1",
        "id": _lifecycle_receipt_id(
            operation=operation,
            authority=authority,
            workspace_id=workspace_id,
            target=target,
            receipt_output=receipt_output,
        ),
        "operation": operation,
        "status": "intent_recorded",
        "created_at": now,
        "updated_at": now,
        "authority": authority,
        "workspace_id": workspace_id,
        "plan_id": plan_id,
        "plan_digest": plan_digest,
        "target_class": target_class,
        "target_identity_sha256": _lifecycle_artifact_identity_sha256(target),
        "target_content_sha256": target_digest,
        "stage_identity_sha256": None,
        "backup_id": backup_id,
        "backup_authentication_key_id": backup_authentication_key_id,
        "retention_until": retention_until,
        "destruction_owner": destruction_owner,
        "lifecycle_outcomes": {
            "deleted_from_named_continuity_custody": False,
            "physical_erasure_not_established": True,
        },
        "physical_erasure": "not_established",
        "external_boundaries": [
            "filesystem-remanence",
            "os-or-provider-snapshots",
            "repository-history",
            "copies-outside-named-custody",
        ],
        "error_code": None,
    }


def _lifecycle_phase_paths(receipt_path: Path, receipt_id: str) -> tuple[Path, Path]:
    intent = receipt_path.with_name(f".{receipt_path.name}.{receipt_id}.intent.json")
    quarantined = receipt_path.with_name(
        f".{receipt_path.name}.{receipt_id}.quarantined.json"
    )
    return intent, quarantined


def _validate_lifecycle_phase(
    observed: Any,
    expected: dict[str, Any],
    *,
    status: str,
) -> dict[str, Any]:
    if not isinstance(observed, dict):
        raise ContinuityError("Lifecycle phase evidence is not an object", "recovery_required")
    _schema(observed, "lifecycle-receipt-v1.schema.json")
    immutable = (
        "format",
        "id",
        "operation",
        "authority",
        "workspace_id",
        "plan_id",
        "plan_digest",
        "target_class",
        "target_identity_sha256",
        "target_content_sha256",
        "backup_id",
        "backup_authentication_key_id",
        "retention_until",
        "destruction_owner",
        "physical_erasure",
    )
    if observed.get("status") != status or any(
        observed.get(field) != expected.get(field) for field in immutable
    ):
        raise ContinuityError(
            "Lifecycle phase evidence disagrees with the authorized operation",
            "recovery_required",
        )
    return observed


def _lifecycle_paths_overlap(target: Path, receipt_path: Path) -> bool:
    target_absolute = Path(os.path.abspath(str(target)))
    receipt_absolute = Path(os.path.abspath(str(receipt_path)))
    return (
        target_absolute == receipt_absolute
        or target_absolute in receipt_absolute.parents
        or receipt_absolute in target_absolute.parents
    )


def _execute_lifecycle_delete(
    target: Path,
    receipt_path: Path,
    receipt: dict[str, Any],
) -> dict[str, Any]:
    stage = target.with_name(f".{target.name}.cd-lifecycle-{receipt['id']}")
    intent_path, quarantined_path = _lifecycle_phase_paths(receipt_path, receipt["id"])

    if any(os.path.lexists(path) for path in (intent_path, quarantined_path, receipt_path, stage)):
        raise ContinuityError(
            "Existing lifecycle phase evidence requires human disposition; automatic resume is disabled",
            "recovery_required",
        )
    if not os.path.lexists(target):
        raise ContinuityError("Lifecycle target is absent", "source_unreachable")
    if (
        _lifecycle_artifact_identity_sha256(target) != receipt["target_identity_sha256"]
        or _artifact_digest(target) != receipt["target_content_sha256"]
    ):
        raise ContinuityError("Lifecycle target changed before intent", "plan_stale")

    _emit_lifecycle_receipt(intent_path, receipt)
    _lifecycle_fail("after_intent")

    if (
        _lifecycle_artifact_identity_sha256(target) != receipt["target_identity_sha256"]
        or _artifact_digest(target) != receipt["target_content_sha256"]
    ):
        raise ContinuityError("Lifecycle target changed before quarantine", "recovery_required")
    try:
        _move_path_write_through(target, stage, replace_existing=False)
    except OSError as exc:
        if not os.path.lexists(target) and os.path.lexists(stage):
            try:
                _fsync_directory(stage.parent)
            except OSError as sync_exc:
                raise ContinuityError(
                    "Lifecycle quarantine is visible but durability is unconfirmed",
                    "recovery_required",
                ) from sync_exc
        else:
            raise ContinuityError("Lifecycle target quarantine failed", "recovery_required") from exc
    if os.path.lexists(target) or not os.path.lexists(stage):
        raise ContinuityError("Lifecycle quarantine state is not recoverable", "recovery_required")
    stage_identity = _lifecycle_artifact_identity_sha256(stage)
    if stage_identity != receipt["target_identity_sha256"] or _artifact_digest(stage) != receipt["target_content_sha256"]:
        raise ContinuityError("Lifecycle stage is not the authorized target object", "recovery_required")
    quarantined = json.loads(json.dumps(receipt))
    quarantined["status"] = "quarantined"
    quarantined["stage_identity_sha256"] = stage_identity
    _emit_lifecycle_receipt(quarantined_path, quarantined)
    _lifecycle_fail("after_quarantine")

    if os.path.lexists(target):
        raise ContinuityError("Lifecycle target reappeared after quarantine", "recovery_required")
    if (
        not os.path.lexists(stage)
        or _lifecycle_artifact_identity_sha256(stage) != stage_identity
        or _artifact_digest(stage) != receipt["target_content_sha256"]
    ):
        raise ContinuityError("Lifecycle stage changed before application deletion", "recovery_required")
    try:
        _delete_application_artifact(stage)
        _fsync_directory(stage.parent)
    except OSError as exc:
        raise ContinuityError(
            f"Application-level lifecycle deletion failed; retained stage: {stage}",
            "application_delete_failed",
        ) from exc
    if os.path.lexists(stage):
        raise ContinuityError(
            f"Application-level lifecycle deletion is unconfirmed; retained stage: {stage}",
            "recovery_required",
        )

    final = json.loads(json.dumps(quarantined))
    final["status"] = "application_deleted"
    final["lifecycle_outcomes"]["deleted_from_named_continuity_custody"] = True
    final["error_code"] = None
    _emit_lifecycle_receipt(receipt_path, final)
    _lifecycle_fail("after_delete")
    return final


def cmd_delete_named_custody(args: argparse.Namespace) -> dict[str, Any]:
    root, selector = _open(args, writable=False)
    authority = require_human_authority(args.authority)
    _, plan = _load_plan(root, args.plan, args.plan_digest)
    manifest = read_json(root / "manifest.json")
    if (
        plan.get("workspace_id") != manifest.get("workspace_id")
        or plan.get("source_manifest_sha256") != sha256_file(root / "manifest.json")
    ):
        raise ContinuityError(
            "Named-custody plan is stale or belongs to another workspace",
            "plan_stale",
        )
    owner = str((plan.get("backup_policy") or {}).get("destruction_owner") or "")
    if owner != authority:
        raise ContinuityError(
            "Named-custody destruction owner does not match authority",
            "authority_denied",
        )
    target, node = _resolve_named_plan_target(
        root,
        plan,
        args.target_class,
        args.target,
        require_exists=False,
    )
    receipt_path = _outside_source(
        root,
        args.receipt_output,
        "Lifecycle receipt output",
        must_be_absent=False,
    )
    expected_digest = str(node.get("artifact_sha256") or "")
    receipt_id = _lifecycle_receipt_id(
        operation="delete-named-custody",
        authority=authority,
        workspace_id=str(manifest["workspace_id"]),
        target=target,
        receipt_output=receipt_path,
    )
    intent_path, quarantined_path = _lifecycle_phase_paths(receipt_path, receipt_id)
    if any(os.path.lexists(path) for path in (intent_path, quarantined_path, receipt_path)):
        raise ContinuityError(
            "Existing lifecycle phase evidence requires human disposition; automatic resume is disabled",
            "recovery_required",
        )
    if not os.path.lexists(target):
        raise ContinuityError("Named target is absent", "source_unreachable")
    actual = _artifact_digest(target)
    if actual != args.target_sha256 or expected_digest != actual:
        raise ContinuityError(
            "Named target digest differs from the reviewed graph",
            "plan_stale",
        )
    receipt = _lifecycle_receipt_base(
        operation="delete-named-custody",
        authority=authority,
        workspace_id=str(manifest["workspace_id"]),
        plan_id=str(plan["id"]),
        plan_digest=str(plan["plan_digest"]),
        target_class=args.target_class,
        target=target,
        target_digest=actual,
        receipt_output=receipt_path,
        retention_until=(plan.get("backup_policy") or {}).get("retention_until"),
        destruction_owner=owner,
    )
    resuming = False
    if not resuming:
        expiry = parse_time(plan.get("expires_at"), "plan expiry")
        if expiry is None or expiry <= datetime.now(timezone.utc):
            raise ContinuityError("Named-custody plan is expired", "plan_stale")
        retention = parse_time(
            (plan.get("backup_policy") or {}).get("retention_until"),
            "retention-until",
        )
        if retention is None or retention > datetime.now(timezone.utc):
            raise ContinuityError(
                "Named-custody deletion is blocked until the reviewed recovery window ends",
                "retention_active",
            )
        if not target.exists():
            raise ContinuityError("Named target is absent", "source_unreachable")
        migrated_from = manifest.get("migrated_from") or {}
        if (
            args.target_class == "prior_generation"
            and "legacy_oversize_content_provenance_count" in migrated_from
        ):
            raise ContinuityError(
                "Retained generation history is required by the legacy content provenance contract",
                "protected_target_denied",
            )
    if _lifecycle_paths_overlap(target, receipt_path):
        raise ContinuityError(
            "Lifecycle receipt output must not equal, contain, or be contained by the deletion target",
            "protected_target_denied",
        )

    lexical_root = Path(selector.selected_lexical) if isinstance(selector, ResolutionToken) else root
    with workspace_lock(
        root,
        0.0,
        transaction_id=receipt["id"],
        lexical_root=lexical_root,
    ) as lock_owner:
        if isinstance(selector, ResolutionToken):
            revalidate_resolution(selector, root)
        if _filesystem_qualification_witness(
            root,
            lexical_root=lexical_root,
            perform_capability_probe=False,
        ) != lock_owner["filesystem_witness"]:
            raise ContinuityError(
                "Filesystem identity changed before lifecycle deletion",
                "filesystem_identity_changed",
            )
        if not resuming:
            if (
                _workspace_evidence_digest(root) != plan.get("source_tree_sha256")
                or sha256_file(root / "manifest.json") != plan.get("source_manifest_sha256")
            ):
                raise ContinuityError(
                    "Named-custody plan changed before deletion",
                    "plan_stale",
                )
            if not target.exists() or _artifact_digest(target) != actual:
                raise ContinuityError(
                    "Named target changed before deletion",
                    "plan_stale",
                )
        return _execute_lifecycle_delete(target, receipt_path, receipt)


def cmd_backup_destroy(args: argparse.Namespace) -> dict[str, Any]:
    root, selector = _open(args, writable=False)
    authority = require_human_authority(args.authority)
    key, key_id = _load_backup_auth_key(root, args.backup_auth_key_file)
    backup_root = _outside_source(
        root,
        args.backup,
        "Forget backup",
        require_mutation=True,
    )
    receipt_output_value = getattr(
        args,
        "receipt_output",
        str(Path(args.backup).with_name(Path(args.backup).name + ".destruction-receipt.json")),
    )
    receipt_path = _outside_source(
        root,
        receipt_output_value,
        "Backup destruction receipt",
        must_be_absent=False,
    )
    manifest = read_json(root / "manifest.json")
    receipt_id = _lifecycle_receipt_id(
        operation="backup-destroy",
        authority=authority,
        workspace_id=str(manifest["workspace_id"]),
        target=backup_root,
        receipt_output=receipt_path,
    )
    intent_path, quarantined_path = _lifecycle_phase_paths(receipt_path, receipt_id)
    if any(os.path.lexists(path) for path in (intent_path, quarantined_path, receipt_path)):
        raise ContinuityError(
            "Existing backup-destruction phase evidence requires human disposition; automatic resume is disabled",
            "recovery_required",
        )
    backup_root, metadata, _, _ = _load_backup(
        root,
        args.backup,
        key,
        key_id,
        require_mutation=True,
    )
    retention = parse_time(metadata.get("retention_until"), "backup retention-until")
    if retention is None or retention > datetime.now(timezone.utc):
        raise ContinuityError("Backup retention window is still active", "retention_active")
    if metadata.get("destruction_owner") != authority:
        raise ContinuityError(
            "Backup destruction owner does not match authority",
            "authority_denied",
        )
    actual = _artifact_digest(backup_root)
    if actual != args.backup_sha256:
        raise ContinuityError(
            "Backup digest does not match the authorized target",
            "plan_stale",
        )
    metadata_id = metadata.get("id")
    receipt = _lifecycle_receipt_base(
        operation="backup-destroy",
        authority=authority,
        workspace_id=str(manifest["workspace_id"]),
        plan_id=str(metadata.get("plan_id")) if metadata.get("plan_id") else None,
        plan_digest=str(metadata.get("plan_digest")) if metadata.get("plan_digest") else None,
        target_class="recovery_backup",
        target=backup_root,
        target_digest=actual,
        receipt_output=receipt_path,
        retention_until=metadata.get("retention_until"),
        destruction_owner=str(metadata.get("destruction_owner")),
        backup_id=str(metadata_id),
        backup_authentication_key_id=key_id,
    )
    resuming = False
    if _lifecycle_paths_overlap(backup_root, receipt_path):
        raise ContinuityError(
            "Lifecycle receipt output must not equal, contain, or be contained by the deletion target",
            "protected_target_denied",
        )

    lexical_root = Path(selector.selected_lexical) if isinstance(selector, ResolutionToken) else root
    with workspace_lock(
        root,
        0.0,
        transaction_id=receipt["id"],
        lexical_root=lexical_root,
    ) as lock_owner:
        if isinstance(selector, ResolutionToken):
            revalidate_resolution(selector, root)
        if _filesystem_qualification_witness(
            root,
            lexical_root=lexical_root,
            perform_capability_probe=False,
        ) != lock_owner["filesystem_witness"]:
            raise ContinuityError(
                "Filesystem identity changed before lifecycle deletion",
                "filesystem_identity_changed",
            )
        if not resuming:
            checked_root, checked, _, _ = _load_backup(
                root,
                args.backup,
                key,
                key_id,
                require_mutation=True,
            )
            if (
                checked_root != backup_root
                or checked.get("id") != metadata_id
                or _artifact_digest(backup_root) != actual
            ):
                raise ContinuityError(
                    "Backup changed before destruction",
                    "plan_stale",
                )
        return _execute_lifecycle_delete(backup_root, receipt_path, receipt)

def cmd_recover(args: argparse.Namespace) -> dict[str, Any]:
    authority = require_human_authority(args.authority)
    root, selector = _open(args, writable=False)
    before = tree_digest(root)
    manifest = read_json(root / "manifest.json")
    if manifest.get("format") == LEGACY_FORMAT:
        result = {
            "format": "cd-continuity-recovery/v2",
            "compatibility_mode": "v1_read_only",
            "status": "guidance_only",
            "authority": authority,
            "recovered_transaction_ids": [],
            "source_mutated": False,
            "guidance": "Validate the v1 workspace and copy-migrate to a distinct v2 workspace; this command never repairs or rewrites v1.",
        }
        if tree_digest(root) != before:
            raise ContinuityError("v1 recovery guidance changed source bytes", "source_changed")
        return result
    root, selector = _open(args, writable=True)
    recovered, generation_before, generation_after = recover_transactions(
        root,
        lock_timeout=args.lock_timeout_seconds,
        selector=selector,
        include_generation_interval=True,
    )
    return {
        "format": "cd-continuity-recovery/v2",
        "compatibility_mode": "v2_native",
        "status": "recovered" if recovered else "clean",
        "authority": authority,
        "recovered_transaction_ids": recovered,
        "generation_before": generation_before,
        "generation_after": generation_after,
        "source_mutated": bool(recovered),
    }


def workspace_access_support(root: Path, selector: ResolutionToken, observed_format: str) -> dict[str, Any]:
    filesystem = mutation_filesystem_support(root, lexical_root=Path(selector.selected_lexical))
    read = {
        "status": "supported",
        "adapter": "stable-manifest-snapshot-read/v1",
        "mutation_qualification_required": False,
    }
    if observed_format == LEGACY_FORMAT:
        mutation = {
            "status": "unsupported",
            "reason_code": "migration_required_for_mutation",
            "filesystem_qualification": filesystem,
        }
    else:
        mutation = filesystem
    return {"read": read, "mutation": mutation}


def cmd_open(args: argparse.Namespace) -> dict[str, Any]:
    root, selector = open_workspace(args.workspace, writable=False)
    manifest = read_json(root / "manifest.json")
    observed = manifest.get("format")
    if observed == FORMAT:
        manifest, _, manifest_sha256 = open_snapshot_identity(root)
        observed = manifest.get("format")
    else:
        manifest_sha256 = sha256_file(root / "manifest.json")
    access_support = workspace_access_support(root, selector, observed)
    if observed == LEGACY_FORMAT:
        capabilities = {
            "open_read": "supported", "validate": "supported_with_known_limits", "context_compile": "supported_d07_policy",
            "worldline_read_views": "supported_typed_degradation", "error_neighborhood": "operation_unsupported_v1",
            "capture": "migration_required_for_mutation", "correct": "migration_required_for_mutation",
            "fault_capture": "operation_unsupported_v1", "failure_pattern_governance": "operation_unsupported_v1",
            "export": "supported_source_read_only", "forget_plan": "supported_inspection_only",
            "forget_apply": "migration_required_for_mutation", "recover": "v1_guidance_only", "migrate": "copy_only",
        }
        mode = "v1_read_only"
    else:
        capabilities = {name: "supported" for name in (
            "open_read", "validate", "context_compile", "worldline_read_views", "error_neighborhood", "forget_plan",
        )}
        mutation_status = access_support["mutation"]["status"]
        if mutation_status == "qualified":
            mutation_value = "supported"
        elif mutation_status == "preflight_supported":
            mutation_value = "supported_with_transaction_probe"
        else:
            mutation_value = access_support["mutation"]["reason_code"]
        capabilities.update({name: mutation_value for name in (
            "capture", "correct", "fault_capture", "failure_pattern_governance", "forget_apply", "recover",
        )})
        capabilities["export"] = "supported_with_qualified_destination"
        capabilities["migrate_copy_from_v1"] = "supported_with_qualified_destination"
        mode = "v2_native"
    return {
        "format": "cd-continuity-open/v2",
        "workspace_format": observed,
        "manifest_identity": {
            "workspace_id": manifest.get("workspace_id"),
            "generation": manifest.get("generation"),
            "manifest_sha256": manifest_sha256,
        },
        "compatibility_mode": mode,
        "access_support": access_support,
        "capabilities": capabilities,
        "source_mutated": False,
    }

def add_workspace_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "workspace", nargs="?",
        help="workspace path; defaults to NOVA_CONTINUITY_HOME when omitted",
    )


def add_generation(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--expected-generation", type=int, required=True)
    parser.add_argument("--idempotency-key", required=True)


def parser() -> argparse.ArgumentParser:
    common_sensitivity = list(SENSITIVITY)
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)

    open_parser = sub.add_parser("open", help="Probe workspace major format and capability map without writes")
    add_workspace_argument(open_parser)
    open_parser.set_defaults(func=cmd_open)

    recover = sub.add_parser(
        "recover",
        help="Reconcile provable v2 transactions or return read-only v1 guidance",
    )
    add_workspace_argument(recover)
    recover.add_argument("--authority", required=True)
    recover.add_argument("--lock-timeout-seconds", type=float, default=0.0)
    recover.set_defaults(func=cmd_recover)

    init = sub.add_parser("init", help="Initialize a new v2 continuity workspace")
    add_workspace_argument(init)
    init.add_argument("--user", required=True)
    init.add_argument("--project", required=True)
    init.add_argument("--agent", required=True)
    init.add_argument("--thread")
    init.add_argument("--sensitivity", choices=common_sensitivity, default="ordinary")
    init.add_argument("--retention", default="until-user-changes")
    init.set_defaults(func=cmd_init)

    migrate = sub.add_parser(
        "migrate-copy", help="Copy a legacy v1 workspace into a distinct v2 workspace"
    )
    migrate.add_argument("source")
    migrate.add_argument("destination")
    migrate.add_argument("--authority", required=True)
    migrate.add_argument("--source-tree-sha256", required=True)
    migrate.add_argument(
        "--destination-mode",
        choices=["generic_external", "nova_guarded_successor"],
        default="generic_external",
    )
    migrate.add_argument("--destination-grant-id")
    migrate.add_argument("--expected-selector-registry-sha256")
    migrate.add_argument("--expected-destination-path-sha256")
    migrate.set_defaults(func=cmd_migrate_copy)

    episode = sub.add_parser("episode", help="Append a source episode")
    add_workspace_argument(episode)
    episode.add_argument("--type", required=True, choices=EPISODE_TYPES)
    episode.add_argument("--content", required=True)
    episode.add_argument(
        "--source-kind", required=True,
        choices=["user", "agent", "tool", "file", "import", "system"],
    )
    episode.add_argument("--authority", required=True)
    episode.add_argument("--locator")
    episode.add_argument("--valid-from")
    episode.add_argument("--expires-at")
    episode.add_argument("--project")
    episode.add_argument("--thread")
    episode.add_argument("--sensitivity", choices=common_sensitivity, default="ordinary")
    episode.add_argument("--retention", default="until-user-changes")
    episode.add_argument("--tags")
    add_generation(episode)
    episode.set_defaults(func=cmd_episode)

    record = sub.add_parser("record", help="Record explicit authorized typed state")
    add_workspace_argument(record)
    record.add_argument("--kind", required=True, choices=STATE_KINDS)
    record.add_argument("--content", required=True)
    record.add_argument("--source-ids", required=True)
    record.add_argument("--authority", required=True)
    record.add_argument("--confidence", default="source-supported")
    record.add_argument("--sensitivity", choices=common_sensitivity, default="ordinary")
    record.add_argument("--retention", default="until-user-changes")
    record.add_argument("--valid-from")
    record.add_argument("--expires-at")
    record.add_argument("--project")
    record.add_argument("--thread")
    record.add_argument("--supersedes")
    record.add_argument("--conflicts")
    record.add_argument("--derived-from")
    add_generation(record)
    record.set_defaults(func=cmd_record)

    propose = sub.add_parser("propose", help="Create a non-canonical state proposal")
    add_workspace_argument(propose)
    propose.add_argument(
        "--origin", required=True,
        choices=["capture", "consolidation", "dream", "import", "manual"],
    )
    propose.add_argument(
        "--operation", required=True,
        choices=["add", "supersede", "expire", "tombstone", "noop"],
    )
    propose.add_argument("--target-id")
    propose.add_argument("--kind", required=True)
    propose.add_argument("--content", required=True)
    propose.add_argument("--source-ids", required=True)
    propose.add_argument("--rationale", required=True)
    propose.add_argument("--authority-required", required=True)
    propose.add_argument("--authority", required=True)
    propose.add_argument(
        "--risk", required=True,
        choices=["low", "consequential", "sensitive", "irreversible"],
    )
    propose.add_argument("--waking-review-id")
    propose.add_argument("--project")
    propose.add_argument("--thread")
    add_generation(propose)
    propose.set_defaults(func=cmd_propose)

    apply_parser = sub.add_parser("apply", help="Apply an authorized proposal")
    add_workspace_argument(apply_parser)
    apply_parser.add_argument("--proposal-id", required=True)
    apply_parser.add_argument("--authority", required=True)
    apply_parser.add_argument("--waking-approved", action="store_true")
    apply_parser.add_argument("--confidence", default="source-supported")
    apply_parser.add_argument(
        "--sensitivity", choices=common_sensitivity, default="ordinary"
    )
    apply_parser.add_argument("--retention", default="until-user-changes")
    add_generation(apply_parser)
    apply_parser.set_defaults(func=cmd_apply)

    forget_plan = sub.add_parser(
        "forget-plan", help="Emit a source-read-only, externally custodied exact-ID lifecycle plan"
    )
    add_workspace_argument(forget_plan)
    forget_plan.add_argument("--ids", required=True)
    forget_plan.add_argument("--authority", required=True)
    forget_plan.add_argument("--mode", choices=["tombstone", "active-remove", "physical-erase"], default="tombstone")
    forget_plan.add_argument("--plan-output", required=True)
    forget_plan.add_argument("--plan-minutes", type=int, default=15)
    forget_plan.add_argument("--retention-until", required=True)
    forget_plan.add_argument("--destruction-owner", required=True)
    forget_plan.add_argument("--access-owner", required=True)
    forget_plan.add_argument("--encryption-disposition", choices=["not-required", "verified-encrypted-volume", "artifact-encrypted"], default="not-required")
    forget_plan.add_argument("--known-backups")
    forget_plan.add_argument("--known-export-receipts")
    forget_plan.set_defaults(func=cmd_forget_plan)

    forget = sub.add_parser(
        "forget", help="Apply one reviewed plan as one immutable-generation transaction"
    )
    add_workspace_argument(forget)
    forget.add_argument("--plan", required=True)
    forget.add_argument("--authority", required=True)
    forget.add_argument("--plan-digest", required=True)
    forget.add_argument("--backup-output", required=True)
    forget.add_argument("--backup-auth-key-file", required=True)
    forget.add_argument("--retention-until", required=True)
    forget.add_argument("--destruction-owner", required=True)
    forget.add_argument("--access-owner", required=True)
    forget.add_argument("--encryption-disposition", choices=["not-required", "verified-encrypted-volume", "artifact-encrypted"], required=True)
    forget.add_argument("--idempotency-key", required=True)
    forget.add_argument("--expected-generation", type=int, required=True)
    forget.set_defaults(func=cmd_forget)

    restore = sub.add_parser(
        "restore-forget", help="Restore active ledgers from an externally custodied verified backup"
    )
    add_workspace_argument(restore)
    restore.add_argument("--backup", required=True)
    restore.add_argument("--backup-auth-key-file", required=True)
    restore.add_argument("--authority", required=True)
    restore.add_argument("--idempotency-key", required=True)
    restore.add_argument("--expected-generation", type=int, required=True)
    restore.set_defaults(func=cmd_restore_forget)

    named_delete = sub.add_parser("delete-named-custody", help="Delete one exact plan-named Continuity custody artifact after retention")
    add_workspace_argument(named_delete)
    named_delete.add_argument("--authority", required=True)
    named_delete.add_argument("--plan", required=True)
    named_delete.add_argument("--plan-digest", required=True)
    named_delete.add_argument("--target-class", choices=["prior_generation", "transaction_journal", "quarantine", "known_export"], required=True)
    named_delete.add_argument("--target", required=True)
    named_delete.add_argument("--target-sha256", required=True)
    named_delete.add_argument("--receipt-output", required=True)
    named_delete.set_defaults(func=cmd_delete_named_custody)

    backup_destroy = sub.add_parser("backup-destroy", help="Destroy one authenticated recovery backup after retention")
    add_workspace_argument(backup_destroy)
    backup_destroy.add_argument("--authority", required=True)
    backup_destroy.add_argument("--backup", required=True)
    backup_destroy.add_argument("--backup-auth-key-file", required=True)
    backup_destroy.add_argument("--backup-sha256", required=True)
    backup_destroy.add_argument("--receipt-output", required=True)
    backup_destroy.set_defaults(func=cmd_backup_destroy)
    export = sub.add_parser("export", help="Create a scoped export plus destination-custodied receipt")
    add_workspace_argument(export)
    export.add_argument("--output", required=True)
    export.add_argument("--authority", required=True)
    export.add_argument("--project")
    export.add_argument("--thread")
    export.add_argument("--from", dest="from_time")
    export.add_argument("--to", dest="to_time")
    export.add_argument("--sensitivity", choices=common_sensitivity, default="limited")
    export.add_argument("--environment")
    export.add_argument("--environment-version")
    export.add_argument("--unreachable-source-ids")
    export.add_argument("--exclude-episodes", action="store_true")
    export.add_argument("--exclude-state", action="store_true")
    export.add_argument("--exclude-proposals", action="store_true")
    export.set_defaults(func=cmd_export)

    import_parser = sub.add_parser(
        "import", help="Validate an export and bind an external quarantine artifact"
    )
    add_workspace_argument(import_parser)
    import_parser.add_argument("--input", required=True)
    import_parser.add_argument("--quarantine-output", required=True)
    import_parser.add_argument("--authority", required=True)
    add_generation(import_parser)
    import_parser.set_defaults(func=cmd_import)
    return root


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        result = args.func(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except IdempotentReplay as replay:
        print(json.dumps(replay.receipt, ensure_ascii=False, indent=2))
        return 0
    except (ContinuityError, SchemaError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        error = ContinuityError(
            f"Native filesystem operation failed without a stronger classification: {exc}",
            "filesystem_semantics_unsupported",
        )
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())