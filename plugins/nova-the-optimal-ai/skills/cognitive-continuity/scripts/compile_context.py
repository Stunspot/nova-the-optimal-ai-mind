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

from continuity_store import ContinuityError, atomic_json, read_jsonl, resolve_scope, scope_matches_query, utc_now, workspace


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
    if record.get("status") != "current" or not scope_matches_query(record.get("scope"), scope):
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
                   thread: str | None = None) -> tuple[str, dict[str, Any]]:
    scope = resolve_scope(root, project, thread)
    records = read_jsonl(root / "state" / "records.jsonl")
    episodes = read_jsonl(root / "episodes" / "events.jsonl")
    now = datetime.now(timezone.utc)
    candidates = [row for row in records if eligible(row, scope, ceiling, now)]
    by_id = {row["id"]: row for row in candidates}
    missing_required = sorted(set(required_ids) - set(by_id))
    if missing_required:
        raise ContinuityError(f"Required current records are unavailable: {', '.join(missing_required)}")
    ranked = {value: index for index, value in enumerate(ranked_ids)}
    candidates.sort(key=lambda row: score(row, words(task), ranked), reverse=True)

    header = [
        "# Compiled Context", "", f"- **Task:** {task}",
        f"- **Scope:** user={scope['user']}; project={scope['project']}; agent={scope['agent']}; thread={scope.get('thread') or 'all'}",
        f"- **Created:** {utc_now()}", f"- **Budget:** {budget} characters",
        f"- **Compiler mode:** {'semantic-ranked' if ranked_ids else 'deterministic-degraded'}",
        f"- **Current capability limit:** {'none recorded' if ranked_ids else 'Semantic relevance ranking was not exercised.'}", "",
    ]
    used = len("\n".join(header))
    selected: list[dict[str, Any]] = []
    omitted: list[str] = []
    sections: dict[str, list[str]] = {}

    required_set = set(required_ids)
    for record in candidates:
        text = render_record(record)
        label = KIND_LABELS.get(record.get("kind"), "Other continuity state")
        added_cost = len(text) + (len(label) + 5 if label not in sections else 0)
        if used + added_cost <= budget or record["id"] in required_set:
            sections.setdefault(label, []).append(text)
            selected.append(record)
            used += added_cost
        else:
            omitted.append(record["id"])

    lines = header
    for label in dict.fromkeys(KIND_LABELS[kind] for kind in KIND_ORDER):
        if label in sections:
            lines.extend([f"## {label}", "", *sections[label], ""])

    recent = [row for row in episodes if scope_matches_query(row.get("scope"), scope)][-recent_count:] if recent_count else []
    if recent:
        lines.extend(["## Recent episodes", "", "Source chronology only. These episodes do not override typed current state, permissions, or revocations.", ""])
        for episode in recent:
            text = f"- **{episode['id']}** [{episode['type']}] {episode['content']}"
            if len("\n".join(lines)) + len(text) + 1 <= budget:
                lines.append(text)
            else:
                omitted.append(episode["id"])
        lines.append("")

    conflicts = [row["id"] for row in records if row.get("status") == "conflicted" and scope_matches_query(row.get("scope"), scope)]
    lines.extend(["## Unresolved or omitted", "", f"- Conflicted records: {', '.join(conflicts) if conflicts else 'none'}", f"- Eligible records omitted under budget: {', '.join(omitted) if omitted else 'none'}", "", "This packet is derived. Recompile when the task, authority, or current state changes."])
    markdown = "\n".join(lines).rstrip() + "\n"
    metadata = {
        "format": "cd-compiled-context/v1", "created_at": utc_now(), "task": task, "scope": scope,
        "character_budget": budget, "characters_used": len(markdown),
        "compiler_mode": "semantic-ranked" if ranked_ids else "deterministic-degraded",
        "selected_ids": [row["id"] for row in selected], "omitted_ids": omitted, "conflicted_ids": conflicts,
    }
    return markdown, metadata


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace"); p.add_argument("--task", required=True); p.add_argument("--output", required=True)
    p.add_argument("--budget", type=int, default=12000); p.add_argument("--sensitivity", choices=list(SENSITIVITY), default="limited")
    p.add_argument("--recent", type=int, default=10); p.add_argument("--ranked-ids", default=""); p.add_argument("--required-ids", default="")
    p.add_argument("--project"); p.add_argument("--thread")
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        root = workspace(args.workspace)
        if args.budget < 1000:
            raise ContinuityError("Budget must be at least 1000 characters")
        output = Path(args.output).expanduser().resolve()
        markdown, metadata = compile_packet(
            root, args.task, args.budget, args.sensitivity, max(0, min(args.recent, 50)),
            [item for item in args.ranked_ids.split(",") if item],
            [item for item in args.required_ids.split(",") if item],
            args.project, args.thread,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown, encoding="utf-8", newline="\n")
        atomic_json(output.with_suffix(output.suffix + ".json"), metadata)
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
        return 0
    except ContinuityError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
