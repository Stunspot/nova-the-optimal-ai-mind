#!/usr/bin/env python3
"""Deterministic local store for Cognitive Continuity v0.1.

Uses only the Python standard library. It owns file integrity and receipts, not
semantic truth. Run with --help for commands.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


FORMAT = "cd-cognitive-continuity/v1"
EXPORT_FORMAT = "cd-cognitive-continuity-export/v1"
PACKAGE_VERSION = "0.1.0"
DIRS = ("episodes", "state", "proposals", "contexts", "dreams", "receipts", "exports", "quarantine")


class ContinuityError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def dump_canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContinuityError(f"Cannot read valid JSON from {path}: {exc}") from exc


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ContinuityError(f"{path}:{line_no} is not a JSON object")
                rows.append(value)
    except (OSError, json.JSONDecodeError) as exc:
        raise ContinuityError(f"Cannot read valid JSONL from {path}: {exc}") from exc
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(dump_canonical(row) + "\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(dump_canonical(row) + "\n")


def workspace(path_value: str) -> Path:
    root = Path(path_value).expanduser().resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ContinuityError(f"Not an initialized continuity workspace: {root}")
    manifest = read_json(manifest_path)
    if manifest.get("format") != FORMAT:
        raise ContinuityError(f"Unsupported continuity format in {manifest_path}")
    return root


def manifest_scope(root: Path) -> dict[str, Any]:
    return read_json(root / "manifest.json")["scope"]


def scope_within_manifest(candidate: Any, manifest: dict[str, Any]) -> bool:
    """Return whether a record scope belongs inside the workspace boundary.

    A ``*`` project makes the workspace harness-global: records may still carry
    narrower project and thread scopes. A null manifest thread contains all
    threads in the admitted project boundary.
    """
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
    if manifest_thread not in (None, "*") and candidate.get("thread") != manifest_thread:
        return False
    return True


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
    """Match global, project, and thread state visible to one task scope."""
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


def parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def require_sources(root: Path, source_ids: list[str]) -> None:
    episode_ids = {row["id"] for row in read_jsonl(root / "episodes" / "events.jsonl")}
    missing = sorted(set(source_ids) - episode_ids)
    if missing:
        raise ContinuityError(f"Unknown source episode IDs: {', '.join(missing)}")


def write_receipt(root: Path, kind: str, details: dict[str, Any]) -> dict[str, Any]:
    receipt = {"format": "cd-continuity-receipt/v1", "id": new_id("RC"), "kind": kind, "at": utc_now(), **details}
    atomic_json(root / "receipts" / f"{receipt['id']}.json", receipt)
    return receipt


def cmd_init(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.workspace).expanduser().resolve()
    if root.exists() and any(root.iterdir()) and not (root / "manifest.json").exists():
        raise ContinuityError(f"Refusing to initialize non-empty unrecognized directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    for name in DIRS:
        (root / name).mkdir(exist_ok=True)
    manifest_path = root / "manifest.json"
    if manifest_path.exists() and not args.force:
        raise ContinuityError(f"Workspace already initialized: {root}")
    now = utc_now()
    manifest = {
        "format": FORMAT,
        "version": PACKAGE_VERSION,
        "workspace_id": new_id("CCW"),
        "created_at": now,
        "updated_at": now,
        "scope": {"user": args.user, "project": args.project, "agent": args.agent, "thread": args.thread},
        "policies": {
            "storage": "local-only",
            "default_sensitivity": args.sensitivity,
            "default_retention": args.retention,
            "semantic_retrieval": False,
            "background_consolidation": False,
        },
        "capabilities": {"filesystem": True, "deterministic_scripts": True, "semantic_ranking": False, "scheduler": False},
        "last_consolidated_episode": None,
    }
    atomic_json(manifest_path, manifest)
    for path in (root / "episodes" / "events.jsonl", root / "state" / "records.jsonl", root / "proposals" / "proposals.jsonl"):
        path.touch(exist_ok=True)
    return write_receipt(root, "initialized", {"workspace_id": manifest["workspace_id"], "scope": manifest["scope"]})


def cmd_episode(args: argparse.Namespace) -> dict[str, Any]:
    root = workspace(args.workspace)
    now = utc_now()
    row = {
        "id": new_id("EP"),
        "type": args.type,
        "recorded_at": now,
        "valid_from": args.valid_from or now,
        "valid_to": None,
        "scope": resolve_scope(root, args.project, args.thread),
        "source": {"kind": args.source_kind, "locator": args.locator, "authority": args.authority},
        "content": args.content,
        "sensitivity": args.sensitivity,
        "retention": args.retention,
        "tags": parse_csv(args.tags),
    }
    append_jsonl(root / "episodes" / "events.jsonl", row)
    return write_receipt(root, "episode-appended", {"episode_id": row["id"], "type": row["type"]})


def make_state_record(root: Path, *, kind: str, content: str, source_ids: list[str], authority: str,
                      confidence: str, sensitivity: str, retention: str, supersedes: list[str] | None = None,
                      conflicts: list[str] | None = None, derived: list[str] | None = None,
                      proposal_id: str | None = None, valid_from: str | None = None,
                      scope: dict[str, Any] | None = None) -> dict[str, Any]:
    require_sources(root, source_ids)
    now = utc_now()
    return {
        "id": new_id("ST"), "kind": kind, "status": "current", "scope": scope or manifest_scope(root),
        "content": content, "recorded_at": now, "valid_from": valid_from or now, "valid_to": None,
        "source_ids": source_ids, "source_class": "episode-linked", "authority": authority,
        "confidence": confidence, "sensitivity": sensitivity, "retention": retention,
        "expires_at": None, "supersedes": supersedes or [], "conflicts_with": conflicts or [],
        "derived_from": derived or [], "tags": [],
        "governance": {"operation": "recorded", "authority": authority, "at": now, "proposal_id": proposal_id},
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
    root = workspace(args.workspace)
    records = read_jsonl(root / "state" / "records.jsonl")
    supersedes = parse_csv(args.supersedes)
    if supersedes:
        supersede_targets(records, supersedes, utc_now())
    row = make_state_record(
        root, kind=args.kind, content=args.content, source_ids=parse_csv(args.source_ids),
        authority=args.authority, confidence=args.confidence, sensitivity=args.sensitivity,
        retention=args.retention, supersedes=supersedes, conflicts=parse_csv(args.conflicts),
        derived=parse_csv(args.derived_from), valid_from=args.valid_from,
        scope=resolve_scope(root, args.project, args.thread),
    )
    records.append(row)
    write_jsonl(root / "state" / "records.jsonl", records)
    return write_receipt(root, "state-recorded", {"record_id": row["id"], "kind": row["kind"], "supersedes": supersedes})


def cmd_propose(args: argparse.Namespace) -> dict[str, Any]:
    root = workspace(args.workspace)
    source_ids = parse_csv(args.source_ids)
    require_sources(root, source_ids)
    row = {
        "id": new_id("PR"), "created_at": utc_now(), "origin": args.origin, "operation": args.operation,
        "scope": resolve_scope(root, args.project, args.thread),
        "target_id": args.target_id, "kind": args.kind, "content": args.content, "source_ids": source_ids,
        "rationale": args.rationale, "authority_required": args.authority_required, "risk": args.risk,
        "status": "proposed", "waking_review_id": args.waking_review_id, "applied_record_id": None,
    }
    append_jsonl(root / "proposals" / "proposals.jsonl", row)
    return write_receipt(root, "proposal-created", {"proposal_id": row["id"], "origin": row["origin"], "operation": row["operation"]})


def cmd_apply(args: argparse.Namespace) -> dict[str, Any]:
    root = workspace(args.workspace)
    proposals = read_jsonl(root / "proposals" / "proposals.jsonl")
    proposal = next((row for row in proposals if row["id"] == args.proposal_id), None)
    if not proposal:
        raise ContinuityError(f"Unknown proposal ID: {args.proposal_id}")
    if proposal["status"] != "proposed":
        raise ContinuityError(f"Proposal is not pending: {proposal['status']}")
    if proposal["origin"] == "dream" and (not args.waking_approved or not proposal.get("waking_review_id")):
        raise ContinuityError("DREAM proposal requires a recorded waking review and --waking-approved")
    if not args.authority:
        raise ContinuityError("Applying a proposal requires explicit --authority")

    records = read_jsonl(root / "state" / "records.jsonl")
    operation = proposal["operation"]
    applied_id: str | None = None
    now = utc_now()
    if operation in {"add", "supersede"}:
        targets = [proposal["target_id"]] if operation == "supersede" and proposal.get("target_id") else []
        if operation == "supersede" and not targets:
            raise ContinuityError("Supersede proposal requires target_id")
        if targets:
            supersede_targets(records, targets, now)
        row = make_state_record(
            root, kind=proposal["kind"], content=proposal["content"], source_ids=proposal["source_ids"],
            authority=args.authority, confidence=args.confidence, sensitivity=args.sensitivity,
            retention=args.retention, supersedes=targets, proposal_id=proposal["id"],
            scope=proposal.get("scope") or manifest_scope(root),
        )
        records.append(row)
        applied_id = row["id"]
    elif operation in {"expire", "tombstone"}:
        target = proposal.get("target_id")
        matched = False
        for row in records:
            if row["id"] == target:
                row["status"] = "expired" if operation == "expire" else "tombstoned"
                row["valid_to"] = now
                matched = True
        if not matched:
            raise ContinuityError(f"Unknown target state ID: {target}")
        applied_id = target
    elif operation != "noop":
        raise ContinuityError(f"Unsupported proposal operation: {operation}")

    write_jsonl(root / "state" / "records.jsonl", records)
    proposal["status"] = "accepted"
    proposal["applied_record_id"] = applied_id
    write_jsonl(root / "proposals" / "proposals.jsonl", proposals)
    return write_receipt(root, "proposal-applied", {"proposal_id": proposal["id"], "record_id": applied_id, "authority": args.authority, "waking_approved": bool(args.waking_approved)})


def references_any(row: dict[str, Any], ids: set[str]) -> bool:
    for key in ("source_ids", "supersedes", "conflicts_with", "derived_from"):
        values = row.get(key) or []
        if any(value in ids for value in values):
            return True
    for key in ("target_id", "applied_record_id", "waking_review_id"):
        if row.get(key) in ids:
            return True
    return False


def cmd_forget(args: argparse.Namespace) -> dict[str, Any]:
    root = workspace(args.workspace)
    episodes_path = root / "episodes" / "events.jsonl"
    state_path = root / "state" / "records.jsonl"
    proposals_path = root / "proposals" / "proposals.jsonl"
    episodes = read_jsonl(episodes_path)
    records = read_jsonl(state_path)
    proposals = read_jsonl(proposals_path)
    all_ids = {row["id"] for row in episodes + records + proposals}
    removed = set(parse_csv(args.ids))
    missing = sorted(removed - all_ids)
    if missing:
        raise ContinuityError(f"Unknown IDs: {', '.join(missing)}")
    changed = True
    while changed:
        changed = False
        for row in records + proposals:
            if row["id"] not in removed and references_any(row, removed):
                removed.add(row["id"])
                changed = True

    kept_episodes = [row for row in episodes if row["id"] not in removed]
    kept_records = [row for row in records if row["id"] not in removed]
    kept_proposals = [row for row in proposals if row["id"] not in removed]
    write_jsonl(episodes_path, kept_episodes)
    write_jsonl(state_path, kept_records)
    write_jsonl(proposals_path, kept_proposals)

    removed_files: list[str] = []
    needles = tuple(removed)
    for dirname in ("contexts", "dreams", "exports"):
        for path in (root / dirname).rglob("*"):
            if path.is_file():
                try:
                    content = path.read_text(encoding="utf-8-sig")
                except (OSError, UnicodeError):
                    continue
                if any(item in content for item in needles):
                    path.unlink()
                    removed_files.append(str(path.relative_to(root)))

    counts = {
        "episodes": len(episodes) - len(kept_episodes),
        "state": len(records) - len(kept_records),
        "proposals": len(proposals) - len(kept_proposals),
        "derived_files": len(removed_files),
    }
    return write_receipt(root, "forgotten", {
        "requested_ids_sha256": hashlib.sha256("\n".join(sorted(parse_csv(args.ids))).encode()).hexdigest(),
        "removed_id_count": len(removed), "counts": counts, "validator_required": True,
        "external_boundaries": ["git-history", "backups", "host-or-provider-logs", "screenshots", "recipient-copies", "copies-outside-workspace"],
    })


def cmd_export(args: argparse.Namespace) -> dict[str, Any]:
    root = workspace(args.workspace)
    manifest = read_json(root / "manifest.json")
    bundle = {
        "format": EXPORT_FORMAT, "package_version": PACKAGE_VERSION, "exported_at": utc_now(),
        "source_workspace_id": manifest["workspace_id"], "scope": manifest["scope"],
        "episodes": read_jsonl(root / "episodes" / "events.jsonl"),
        "state": read_jsonl(root / "state" / "records.jsonl"),
        "proposals": read_jsonl(root / "proposals" / "proposals.jsonl"),
        "capability_boundary": "Package-controlled continuity records only; external copies and host telemetry excluded.",
        "checksum": None,
    }
    bundle["checksum"] = hashlib.sha256(dump_canonical(bundle).encode("utf-8")).hexdigest()
    output = Path(args.output).expanduser().resolve()
    atomic_json(output, bundle)
    return write_receipt(root, "exported", {"output": str(output), "checksum": bundle["checksum"], "counts": {"episodes": len(bundle["episodes"]), "state": len(bundle["state"]), "proposals": len(bundle["proposals"])}})


def cmd_import(args: argparse.Namespace) -> dict[str, Any]:
    root = workspace(args.workspace)
    source = Path(args.input).expanduser().resolve()
    bundle = read_json(source)
    if bundle.get("format") != EXPORT_FORMAT:
        raise ContinuityError("Unsupported export format")
    supplied = bundle.get("checksum")
    check = dict(bundle)
    check["checksum"] = None
    actual = hashlib.sha256(dump_canonical(check).encode("utf-8")).hexdigest()
    if supplied != actual:
        raise ContinuityError("Export checksum mismatch")
    destination = root / "quarantine" / f"import-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{source.name}"
    shutil.copy2(source, destination)
    return write_receipt(root, "import-quarantined", {"source": str(source), "quarantine": str(destination.relative_to(root)), "checksum": supplied, "canonical_state_changed": False})


def parser() -> argparse.ArgumentParser:
    common_sensitivity = ["ordinary", "limited", "sensitive", "restricted"]
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Initialize a transparent continuity workspace")
    init.add_argument("workspace"); init.add_argument("--user", required=True); init.add_argument("--project", required=True); init.add_argument("--agent", required=True)
    init.add_argument("--thread"); init.add_argument("--sensitivity", choices=common_sensitivity, default="ordinary"); init.add_argument("--retention", default="until-user-changes"); init.add_argument("--force", action="store_true"); init.set_defaults(func=cmd_init)

    episode = sub.add_parser("episode", help="Append a source episode")
    episode.add_argument("workspace"); episode.add_argument("--type", required=True, choices=["message", "assertion", "decision", "permission", "commitment", "correction", "tool_action", "tool_result", "outcome", "import"])
    episode.add_argument("--content", required=True); episode.add_argument("--source-kind", required=True, choices=["user", "agent", "tool", "file", "import", "system"]); episode.add_argument("--authority", required=True)
    episode.add_argument("--locator"); episode.add_argument("--valid-from"); episode.add_argument("--project"); episode.add_argument("--thread"); episode.add_argument("--sensitivity", choices=common_sensitivity, default="ordinary"); episode.add_argument("--retention", default="until-user-changes"); episode.add_argument("--tags"); episode.set_defaults(func=cmd_episode)

    record = sub.add_parser("record", help="Record explicit authorized typed state")
    record.add_argument("workspace"); record.add_argument("--kind", required=True, choices=["identity", "user_model", "relationship", "permission", "goal", "commitment", "belief", "decision", "procedure", "failure", "hypothesis"])
    record.add_argument("--content", required=True); record.add_argument("--source-ids", required=True); record.add_argument("--authority", required=True); record.add_argument("--confidence", default="source-supported")
    record.add_argument("--sensitivity", choices=common_sensitivity, default="ordinary"); record.add_argument("--retention", default="until-user-changes"); record.add_argument("--valid-from"); record.add_argument("--project"); record.add_argument("--thread"); record.add_argument("--supersedes"); record.add_argument("--conflicts"); record.add_argument("--derived-from"); record.set_defaults(func=cmd_record)

    propose = sub.add_parser("propose", help="Create a non-canonical state proposal")
    propose.add_argument("workspace"); propose.add_argument("--origin", required=True, choices=["capture", "consolidation", "dream", "import", "manual"]); propose.add_argument("--operation", required=True, choices=["add", "supersede", "expire", "tombstone", "noop"])
    propose.add_argument("--target-id"); propose.add_argument("--kind", required=True); propose.add_argument("--content", required=True); propose.add_argument("--source-ids", required=True); propose.add_argument("--rationale", required=True); propose.add_argument("--authority-required", required=True); propose.add_argument("--risk", required=True, choices=["low", "consequential", "sensitive", "irreversible"]); propose.add_argument("--waking-review-id"); propose.add_argument("--project"); propose.add_argument("--thread"); propose.set_defaults(func=cmd_propose)

    apply_p = sub.add_parser("apply", help="Apply an authorized proposal")
    apply_p.add_argument("workspace"); apply_p.add_argument("--proposal-id", required=True); apply_p.add_argument("--authority", required=True); apply_p.add_argument("--waking-approved", action="store_true"); apply_p.add_argument("--confidence", default="source-supported"); apply_p.add_argument("--sensitivity", choices=common_sensitivity, default="ordinary"); apply_p.add_argument("--retention", default="until-user-changes"); apply_p.set_defaults(func=cmd_apply)

    forget = sub.add_parser("forget", help="Remove named records and package-derived references")
    forget.add_argument("workspace"); forget.add_argument("--ids", required=True, help="Comma-separated exact IDs"); forget.set_defaults(func=cmd_forget)
    export = sub.add_parser("export", help="Create a portable JSON export"); export.add_argument("workspace"); export.add_argument("--output", required=True); export.set_defaults(func=cmd_export)
    import_p = sub.add_parser("import", help="Validate and quarantine a portable export"); import_p.add_argument("workspace"); import_p.add_argument("--input", required=True); import_p.set_defaults(func=cmd_import)
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        result = args.func(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ContinuityError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
