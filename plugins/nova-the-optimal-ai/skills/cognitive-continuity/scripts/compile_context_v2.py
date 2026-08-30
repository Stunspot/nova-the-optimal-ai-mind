#!/usr/bin/env python3
"""Compile a bounded task context from a Cognitive Continuity workspace."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workspace_runtime import ContinuityError, atomic_new_json, atomic_new_bytes, read_json, read_jsonl, sha256_file, tree_digest, utc_now, workspace, validate_external_target
from schema_validation import SchemaCatalog
from eligibility_policy import POLICY_ID, contains_secret_data, evaluate as evaluate_policy, sanitize_text
from continuity_store_v2 import resolve_scope, scope_matches_query


KIND_ORDER = ["identity", "goal", "commitment", "belief", "decision", "relationship", "permission", "procedure", "failure", "user_model", "hypothesis"]
KIND_LABELS = {
    "identity": "Identity and role", "goal": "Active goals and agenda", "commitment": "Commitment ledger",
    "belief": "Beliefs and evidence", "decision": "Project decisions and rationale",
    "relationship": "Relationships and permissions", "permission": "Relationships and permissions",
    "procedure": "Useful procedures", "failure": "Known failures and overrides",
    "user_model": "User model", "hypothesis": "Live hypotheses",
}
PRIORITY = {"permission": 100, "commitment": 95, "failure": 90, "goal": 85, "decision": 80, "belief": 70, "identity": 65, "relationship": 60, "procedure": 55, "user_model": 45, "hypothesis": 25}
SENSITIVITY = {"ordinary": 0, "limited": 1, "sensitive": 2, "restricted": 3}


def words(text: str) -> set[str]:
    return {item for item in re.findall(r"[a-z0-9]+", text.lower()) if len(item) > 2}


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def eligible(record: dict[str, Any], scope: dict[str, Any], ceiling: str, now: datetime) -> bool:
    if record.get("status") not in (None, "current") or not scope_matches_query(record.get("scope"), scope):
        return False
    if "forgotten" in (record.get("tags") or []) or "source-unreachable" in (record.get("tags") or []):
        return False
    if SENSITIVITY.get(record.get("sensitivity", "restricted"), 99) > SENSITIVITY[ceiling]:
        return False
    valid_from = parse_time(record.get("valid_from"))
    valid_to = parse_time(record.get("valid_to"))
    expires = parse_time(record.get("expires_at"))
    if valid_from and valid_from > now:
        return False
    if valid_to and valid_to <= now:
        return False
    if expires and expires <= now:
        return False
    return True


def score(record: dict[str, Any], task_words: set[str], ranked: dict[str, int]) -> tuple[int, str, str]:
    overlap = len(task_words & words(record.get("content", "")))
    rank_bonus = max(0, 1000 - ranked[record["id"]]) if record["id"] in ranked else 0
    return (rank_bonus + PRIORITY.get(record.get("kind"), 0) + overlap * 15, record.get("recorded_at", ""), record["id"])


def render_record(record: dict[str, Any]) -> str:
    sources = ", ".join(record.get("source_ids", [])) or "none"
    flags = []
    if record.get("conflicts_with"):
        flags.append("conflict: " + ", ".join(record["conflicts_with"]))
    if record.get("valid_to"):
        flags.append("valid to " + record["valid_to"])
    suffix = f"; {'; '.join(flags)}" if flags else ""
    return f"- **{record['id']}** {record['content']}  \n  Source: {sources}; authority: {record.get('authority')}; entitlement: {record.get('confidence')}{suffix}"


def compile_packet(root: Path, task: str, budget: int, ceiling: str, recent_count: int,
                   ranked_ids: list[str], required_ids: list[str], project: str | None = None,
                   thread: str | None = None, environment: str | None = None,
                   environment_version: str | None = None,
                   unreachable_source_ids: list[str] | None = None) -> tuple[str, dict[str, Any]]:
    if contains_secret_data(task):
        raise ContinuityError("Task text was rejected by redaction policy", "redaction_rejected")
    task = sanitize_text(task)
    scope = resolve_scope(root, project, thread)
    manifest = read_json(root / "manifest.json")
    workspace_format = manifest.get("format")
    records = read_jsonl(root / "state" / "records.jsonl")
    episodes = read_jsonl(root / "episodes" / "events.jsonl")
    now = datetime.now(timezone.utc)
    catalog = SchemaCatalog(Path(__file__).resolve().parents[1] / "assets" / "schemas")
    episode_schema = "episode.schema.json" if workspace_format == "cd-cognitive-continuity/v1" else "episode-v2.schema.json"
    state_schema = "state-record.schema.json" if workspace_format == "cd-cognitive-continuity/v1" else "state-record-v2.schema.json"
    unreachable = set(unreachable_source_ids or [])
    omission_counts: dict[str, int] = {}

    def omitted(reason: str) -> None:
        omission_counts[reason] = omission_counts.get(reason, 0) + 1

    raw_episode_ids = {str(row.get("id")) for row in episodes if isinstance(row.get("id"), str)}
    eligible_episodes: list[dict[str, Any]] = []
    for row in episodes:
        schema_valid = not catalog.validate(row, episode_schema)
        allowed, reason, sanitized = evaluate_policy(
            row, scope=scope, ceiling=ceiling, now=now, environment=environment,
            environment_version=environment_version, episode_ids=raw_episode_ids,
            unreachable_source_ids=unreachable, allowed_statuses=(None, "current"), schema_valid=schema_valid,
        )
        if allowed and sanitized is not None:
            eligible_episodes.append(sanitized)
        else:
            omitted(reason)
    eligible_episode_ids = {str(row["id"]) for row in eligible_episodes}
    candidates: list[dict[str, Any]] = []
    conflicted: list[str] = []
    for row in records:
        schema_valid = not catalog.validate(row, state_schema)
        allowed, reason, sanitized = evaluate_policy(
            row, scope=scope, ceiling=ceiling, now=now, environment=environment,
            environment_version=environment_version, episode_ids=eligible_episode_ids,
            unreachable_source_ids=unreachable, allowed_statuses=("current",), schema_valid=schema_valid,
        )
        if allowed and sanitized is not None:
            candidates.append(sanitized)
        else:
            omitted(reason)
        if row.get("status") == "conflicted":
            conflict_allowed, conflict_reason, conflict_sanitized = evaluate_policy(
                row, scope=scope, ceiling=ceiling, now=now, environment=environment,
                environment_version=environment_version, episode_ids=eligible_episode_ids,
                unreachable_source_ids=unreachable, allowed_statuses=("conflicted",), schema_valid=schema_valid,
            )
            if conflict_allowed and conflict_sanitized is not None:
                conflicted.append(str(conflict_sanitized["id"]))
            else:
                omitted("conflicted_" + conflict_reason)
    by_id = {row["id"]: row for row in candidates}
    missing_required = sorted(set(required_ids) - set(by_id))
    if missing_required:
        raise ContinuityError("One or more required records failed deterministic eligibility", "required_record_ineligible")
    ranked = {value: index for index, value in enumerate(ranked_ids)}
    candidates.sort(key=lambda row: score(row, words(task), ranked), reverse=True)

    header = [
        "# Compiled Context", "", f"- **Task:** {task}",
        f"- **Scope:** user={scope['user']}; project={scope['project']}; agent={scope['agent']}; thread={scope.get('thread') or 'all'}",
        f"- **Environment:** {environment or 'unbound'}; version={environment_version or 'unbound'}",
        f"- **Created:** {utc_now()}", f"- **Budget:** {budget} characters",
        f"- **Compiler mode:** {'semantic-ranked' if ranked_ids else 'deterministic-degraded'}",
        f"- **Current capability limit:** {'none recorded' if ranked_ids else 'Semantic relevance ranking was not exercised.'}", "",
    ]
    used = len("\n".join(header))
    selected: list[dict[str, Any]] = []
    budget_omitted: list[str] = []
    sections: dict[str, list[str]] = {}
    required_set = set(required_ids)
    for record in candidates:
        rendered = render_record(record)
        label = KIND_LABELS.get(record.get("kind"), "Other continuity state")
        added_cost = len(rendered) + (len(label) + 5 if label not in sections else 0)
        if used + added_cost <= budget or record["id"] in required_set:
            sections.setdefault(label, []).append(rendered); selected.append(record); used += added_cost
        else:
            budget_omitted.append(record["id"])
    lines = header
    for label in dict.fromkeys(KIND_LABELS[kind] for kind in KIND_ORDER):
        if label in sections:
            lines.extend([f"## {label}", "", *sections[label], ""])
    recent = eligible_episodes[-recent_count:] if recent_count else []
    if recent:
        lines.extend(["## Recent episodes", "", "Source chronology only. These episodes do not override typed current state, permissions, or revocations.", ""])
        rendered_recent: list[dict[str, Any]] = []
        for episode in recent:
            rendered = f"- **{episode['id']}** [{episode['type']}] {episode['content']}"
            if len("\n".join(lines)) + len(rendered) + 1 <= budget:
                lines.append(rendered); rendered_recent.append(episode)
            else:
                budget_omitted.append(episode["id"])
        recent = rendered_recent
        lines.append("")
    lines.extend(["## Unresolved or omitted", "", f"- Eligible conflicted records: {', '.join(conflicted) if conflicted else 'none'}", f"- Eligible records omitted under budget: {', '.join(budget_omitted) if budget_omitted else 'none'}", "", "This packet is derived. Recompile when task, authority, environment, source reachability, or current state changes."])
    markdown = "\n".join(lines).rstrip() + "\n"
    metadata = {
        "format": "cd-compiled-context/v1", "created_at": utc_now(), "task": task, "scope": scope,
        "environment": {"name": environment, "version": environment_version},
        "character_budget": budget, "characters_used": len(markdown),
        "compiler_mode": "semantic-ranked" if ranked_ids else "deterministic-degraded",
        "selected_ids": [row["id"] for row in selected], "recent_episode_ids": [row["id"] for row in recent],
        "budget_omitted_ids": budget_omitted, "conflicted_ids": conflicted,
        "eligibility_policy": POLICY_ID, "eligibility_omission_counts": omission_counts,
    }
    if contains_secret_data(markdown) or contains_secret_data(metadata):
        raise ContinuityError("Derived output failed final redaction scan", "redaction_rejected")
    return markdown, metadata

def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace"); p.add_argument("--task", required=True); p.add_argument("--output", required=True)
    p.add_argument("--budget", type=int, default=12000); p.add_argument("--sensitivity", choices=list(SENSITIVITY), default="limited")
    p.add_argument("--recent", type=int, default=10); p.add_argument("--ranked-ids", default=""); p.add_argument("--required-ids", default="")
    p.add_argument("--project"); p.add_argument("--thread")
    p.add_argument("--environment"); p.add_argument("--environment-version")
    p.add_argument("--unreachable-source-ids", default="")
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        root = workspace(args.workspace)
        if args.budget < 1000:
            raise ContinuityError("Budget must be at least 1000 characters")
        output = validate_external_target(root, args.output, "Compiled context output", must_be_absent=True)
        metadata_output = validate_external_target(root, str(output.with_suffix(output.suffix + ".json")), "Compiled context metadata", must_be_absent=True)
        source_before = tree_digest(root)
        manifest = read_json(root / "manifest.json")
        structured_inputs = {
            "ranked_ids": [item for item in args.ranked_ids.split(",") if item],
            "required_ids": [item for item in args.required_ids.split(",") if item],
            "unreachable_source_ids": [item for item in args.unreachable_source_ids.split(",") if item],
            "environment": args.environment, "environment_version": args.environment_version,
        }
        if contains_secret_data(structured_inputs):
            raise ContinuityError("Structured compiler input was rejected by redaction policy", "redaction_rejected")
        environment = sanitize_text(args.environment) if args.environment else None
        environment_version = sanitize_text(args.environment_version) if args.environment_version else None
        markdown, metadata = compile_packet(
            root, args.task, args.budget, args.sensitivity, max(0, min(args.recent, 50)),
            structured_inputs["ranked_ids"], structured_inputs["required_ids"],
            args.project, args.thread, environment, environment_version,
            structured_inputs["unreachable_source_ids"],
        )
        metadata.update({
            "workspace_format": manifest.get("format"),
            "compatibility_mode": "v1_read_only" if manifest.get("format") == "cd-cognitive-continuity/v1" else "v2_native",
            "source_manifest_sha256": sha256_file(root / "manifest.json"), "source_tree_sha256_before": source_before,
            "canonical_source_changed": False,
        })
        if tree_digest(root) != source_before:
            raise ContinuityError("Source changed during context compilation", "source_changed")
        source_after = tree_digest(root)
        if source_after != source_before:
            raise ContinuityError("Source changed before query output publication", "source_changed")
        metadata["source_tree_sha256_after"] = source_after
        created: list[Path] = []
        try:
            atomic_new_bytes(output, markdown.encode("utf-8"))
            created.append(output)
            atomic_new_json(metadata_output, metadata)
            created.append(metadata_output)
        except BaseException as exc:
            if created:
                names = ", ".join(str(candidate) for candidate in created)
                raise ContinuityError(
                    f"Compiled context failed without race-unsafe cleanup; retained path(s): {names}",
                    "recovery_required",
                ) from exc
            raise
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
        return 0
    except ContinuityError as exc:
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
