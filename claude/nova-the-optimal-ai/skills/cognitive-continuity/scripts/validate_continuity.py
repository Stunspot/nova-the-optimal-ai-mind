#!/usr/bin/env python3
"""Validate Cognitive Continuity package workspaces without external dependencies."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from continuity_store import FORMAT, ContinuityError, read_json, read_jsonl, scope_within_manifest, workspace


STATE_KINDS = {"identity", "user_model", "relationship", "permission", "goal", "commitment", "belief", "decision", "procedure", "failure", "hypothesis"}
STATUSES = {"current", "proposed", "conflicted", "superseded", "expired", "tombstoned"}
SENSITIVITY = {"ordinary", "limited", "sensitive", "restricted"}


def iso(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def cycle(nodes: dict[str, list[str]]) -> list[str] | None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def walk(node: str, path: list[str]) -> list[str] | None:
        if node in visiting:
            start = path.index(node) if node in path else 0
            return path[start:] + [node]
        if node in visited:
            return None
        visiting.add(node)
        for nxt in nodes.get(node, []):
            found = walk(nxt, path + [node])
            if found:
                return found
        visiting.remove(node)
        visited.add(node)
        return None

    for node in nodes:
        found = walk(node, [])
        if found:
            return found
    return None


def validate(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    capability_notes: list[str] = []
    manifest = read_json(root / "manifest.json")
    if manifest.get("format") != FORMAT:
        errors.append("manifest.format is not cd-cognitive-continuity/v1")
    for key in ("workspace_id", "created_at", "scope", "policies", "capabilities"):
        if key not in manifest:
            errors.append(f"manifest missing {key}")
    scope = manifest.get("scope")
    if not isinstance(scope, dict) or any(not scope.get(key) for key in ("user", "project", "agent")):
        errors.append("manifest scope requires user, project, and agent")

    episodes = read_jsonl(root / "episodes" / "events.jsonl")
    records = read_jsonl(root / "state" / "records.jsonl")
    proposals = read_jsonl(root / "proposals" / "proposals.jsonl")
    all_rows = episodes + records + proposals
    ids = [row.get("id") for row in all_rows]
    if any(not isinstance(value, str) or not value for value in ids):
        errors.append("every episode, state record, and proposal needs a non-empty id")
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    if duplicates:
        errors.append("duplicate IDs: " + ", ".join(duplicates))
    episode_ids = {row.get("id") for row in episodes}
    record_ids = {row.get("id") for row in records}
    proposal_ids = {row.get("id") for row in proposals}

    for row in episodes:
        rid = row.get("id", "<missing>")
        for key in ("type", "recorded_at", "valid_from", "scope", "source", "content", "sensitivity", "retention"):
            if key not in row:
                errors.append(f"{rid} missing {key}")
        if not scope_within_manifest(row.get("scope"), scope):
            errors.append(f"{rid} crosses manifest scope")
        if not iso(row.get("recorded_at")) or not iso(row.get("valid_from")):
            errors.append(f"{rid} has invalid time")
        if row.get("sensitivity") not in SENSITIVITY:
            errors.append(f"{rid} has invalid sensitivity")

    graph: dict[str, list[str]] = {}
    tombstoned: set[str] = set()
    for row in records:
        rid = row.get("id", "<missing>")
        if row.get("kind") not in STATE_KINDS:
            errors.append(f"{rid} has invalid kind")
        if row.get("status") not in STATUSES:
            errors.append(f"{rid} has invalid status")
        if not scope_within_manifest(row.get("scope"), scope):
            errors.append(f"{rid} crosses manifest scope")
        if not iso(row.get("recorded_at")) or not iso(row.get("valid_from")):
            errors.append(f"{rid} has invalid time")
        sources = row.get("source_ids") or []
        missing_sources = sorted(set(sources) - episode_ids)
        if missing_sources:
            errors.append(f"{rid} has missing source episodes: {', '.join(missing_sources)}")
        graph[rid] = list(row.get("supersedes") or [])
        for target in graph[rid]:
            if target not in record_ids:
                errors.append(f"{rid} supersedes unknown state {target}")
        for target in row.get("conflicts_with") or []:
            if target not in record_ids:
                errors.append(f"{rid} conflicts with unknown state {target}")
        if row.get("status") == "tombstoned":
            tombstoned.add(rid)
    found_cycle = cycle(graph)
    if found_cycle:
        errors.append("supersession cycle: " + " -> ".join(found_cycle))

    for row in proposals:
        rid = row.get("id", "<missing>")
        for key in ("origin", "operation", "kind", "content", "source_ids", "authority_required", "risk", "status"):
            if key not in row:
                errors.append(f"{rid} missing {key}")
        if row.get("scope") is not None and not scope_within_manifest(row.get("scope"), scope):
            errors.append(f"{rid} crosses manifest scope")
        missing_sources = sorted(set(row.get("source_ids") or []) - episode_ids)
        if missing_sources:
            errors.append(f"{rid} has missing source episodes: {', '.join(missing_sources)}")
        target = row.get("target_id")
        if target and target not in record_ids:
            errors.append(f"{rid} targets unknown state {target}")
        applied = row.get("applied_record_id")
        if applied and applied not in record_ids:
            errors.append(f"{rid} names unknown applied record {applied}")
        if row.get("origin") == "dream" and row.get("status") == "accepted" and not row.get("waking_review_id"):
            errors.append(f"{rid} is an accepted DREAM proposal without waking review")

    if tombstoned:
        for dirname in ("contexts", "exports"):
            for path in (root / dirname).rglob("*"):
                if path.is_file():
                    try:
                        text = path.read_text(encoding="utf-8-sig")
                    except (OSError, UnicodeError):
                        continue
                    leaked = sorted(item for item in tombstoned if item in text)
                    if leaked:
                        errors.append(f"{path.relative_to(root)} contains tombstoned IDs: {', '.join(leaked)}")

    for path in (root / "contexts").glob("*.md.json"):
        metadata = read_json(path)
        if metadata.get("characters_used", 0) > metadata.get("character_budget", 0):
            errors.append(f"{path.relative_to(root)} exceeds its context budget")
        selected = set(metadata.get("selected_ids") or [])
        unknown = sorted(selected - record_ids)
        if unknown:
            errors.append(f"{path.relative_to(root)} selects unknown records: {', '.join(unknown)}")

    if not records:
        warnings.append("workspace has no typed state records")
    if manifest.get("capabilities", {}).get("semantic_ranking") is False:
        capability_notes.append("semantic ranking is unavailable or disabled; deterministic compilation remains valid, and packets without caller-supplied ranked IDs record semantic relevance as unexercised")

    return {
        "format": "cd-continuity-validation/v1", "workspace": str(root),
        "status": "valid" if not errors else "invalid", "errors": errors, "warnings": warnings,
        "capability_notes": capability_notes,
        "counts": {"episodes": len(episodes), "state": len(records), "proposals": len(proposals), "receipts": len(list((root / "receipts").glob("*.json")))},
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace"); p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        report = validate(workspace(args.workspace))
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"{report['status'].upper()}: {report['workspace']}")
            for item in report["errors"]:
                print(f"ERROR: {item}")
            for item in report["warnings"]:
                print(f"WARNING: {item}")
            for item in report["capability_notes"]:
                print(f"CAPABILITY NOTE: {item}")
            print("COUNTS: " + json.dumps(report["counts"], sort_keys=True))
        return 0 if report["status"] == "valid" else 1
    except ContinuityError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
