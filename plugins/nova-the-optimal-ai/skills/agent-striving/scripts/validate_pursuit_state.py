#!/usr/bin/env python3
"""Validate Agent Striving pursuit state without external dependencies."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


FORMAT = "cd-agent-striving-state/v1"
STATUSES = {
    "active",
    "completed",
    "partial-success",
    "awaiting-evidence",
    "awaiting-authority",
    "capability-limited",
    "budget-exhausted",
    "paused",
    "cancelled",
    "killed",
}
TERMINAL = {"completed", "cancelled", "killed"}
REQUIRED = {
    "format",
    "pursuit_id",
    "objective",
    "world_change",
    "acceptance_criteria",
    "status",
    "strategy",
    "progress",
    "next_move",
    "budgets",
    "authority",
    "completion_evidence",
    "reentry",
    "updated_at",
}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any, *, nonempty: bool = False) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) and (not nonempty or bool(item.strip())) for item in value
    )


def validate(state: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(state, dict):
        return ["root must be an object"]

    missing = sorted(REQUIRED - set(state))
    extra = sorted(set(state) - REQUIRED)
    if missing:
        errors.append(f"missing required fields: {', '.join(missing)}")
    if extra:
        errors.append(f"unexpected fields: {', '.join(extra)}")
    if missing:
        return errors

    if state["format"] != FORMAT:
        errors.append(f"format must be {FORMAT}")
    if not _nonempty(state["pursuit_id"]):
        errors.append("pursuit_id must be a non-empty string")
    if not _nonempty(state["world_change"]):
        errors.append("world_change must be a non-empty string")
    if not _string_list(state["acceptance_criteria"], nonempty=True) or not state["acceptance_criteria"]:
        errors.append("acceptance_criteria must contain at least one non-empty string")

    objective = state["objective"]
    if not isinstance(objective, dict) or set(objective) != {"statement", "source_authority", "source_refs"}:
        errors.append("objective must contain exactly statement, source_authority, and source_refs")
    else:
        if not _nonempty(objective["statement"]):
            errors.append("objective.statement must be a non-empty string")
        if not _nonempty(objective["source_authority"]):
            errors.append("objective.source_authority must be a non-empty string")
        if not _string_list(objective["source_refs"]):
            errors.append("objective.source_refs must be an array of strings")

    status = state["status"]
    if status not in STATUSES:
        errors.append(f"status must be one of: {', '.join(sorted(STATUSES))}")

    strategy = state["strategy"]
    if not isinstance(strategy, dict) or set(strategy) != {"current_hypothesis", "last_revision"}:
        errors.append("strategy must contain exactly current_hypothesis and last_revision")
    elif not _nonempty(strategy["current_hypothesis"]):
        errors.append("strategy.current_hypothesis must be a non-empty string")
    elif strategy["last_revision"] is not None and not _nonempty(strategy["last_revision"]):
        errors.append("strategy.last_revision must be null or a non-empty string")

    progress = state["progress"]
    progress_ok = isinstance(progress, dict) and set(progress) == {
        "verified_outcomes",
        "evidence_refs",
        "remaining",
        "stall_count",
    }
    if not progress_ok:
        errors.append("progress fields are invalid")
    else:
        if not _string_list(progress["verified_outcomes"], nonempty=True):
            errors.append("progress.verified_outcomes must be an array of non-empty strings")
        if not _string_list(progress["evidence_refs"]):
            errors.append("progress.evidence_refs must be an array of strings")
        if not _string_list(progress["remaining"], nonempty=True):
            errors.append("progress.remaining must be an array of non-empty strings")
        if not isinstance(progress["stall_count"], int) or isinstance(progress["stall_count"], bool) or progress["stall_count"] < 0:
            errors.append("progress.stall_count must be a non-negative integer")
        elif progress["stall_count"] >= 3 and isinstance(strategy, dict) and not strategy.get("last_revision"):
            errors.append("three or more stalled cycles require strategy.last_revision")

    next_move = state["next_move"]
    if not isinstance(next_move, dict) or set(next_move) != {"action", "rationale", "authority_required"}:
        errors.append("next_move fields are invalid")
    else:
        if not _nonempty(next_move["action"]):
            errors.append("next_move.action must be a non-empty string")
        if not isinstance(next_move["rationale"], str):
            errors.append("next_move.rationale must be a string")
        if not isinstance(next_move["authority_required"], bool):
            errors.append("next_move.authority_required must be boolean")

    budgets = state["budgets"]
    if not isinstance(budgets, dict) or set(budgets) != {"limits", "used", "exhausted_dimension"}:
        errors.append("budgets fields are invalid")
    else:
        if not isinstance(budgets["limits"], dict) or not isinstance(budgets["used"], dict):
            errors.append("budgets.limits and budgets.used must be objects")
        if budgets["exhausted_dimension"] is not None and not _nonempty(budgets["exhausted_dimension"]):
            errors.append("budgets.exhausted_dimension must be null or a non-empty string")
        if status == "budget-exhausted" and not budgets["exhausted_dimension"]:
            errors.append("budget-exhausted status requires budgets.exhausted_dimension")

    authority = state["authority"]
    if not isinstance(authority, dict) or set(authority) != {"allowed_actions", "gated_actions", "pending_gate"}:
        errors.append("authority fields are invalid")
    else:
        if not _string_list(authority["allowed_actions"]) or not _string_list(authority["gated_actions"]):
            errors.append("authority action fields must be arrays of strings")
        if authority["pending_gate"] is not None and not _nonempty(authority["pending_gate"]):
            errors.append("authority.pending_gate must be null or a non-empty string")
        if status == "awaiting-authority" and not authority["pending_gate"]:
            errors.append("awaiting-authority status requires authority.pending_gate")

    if not _string_list(state["completion_evidence"], nonempty=True):
        errors.append("completion_evidence must be an array of non-empty strings")
    if status == "completed":
        if progress_ok and progress["remaining"]:
            errors.append("completed pursuit cannot retain remaining work")
        if not state["completion_evidence"]:
            errors.append("completed pursuit requires completion_evidence")

    reentry = state["reentry"]
    if not isinstance(reentry, dict) or set(reentry) != {"condition", "next_actor"}:
        errors.append("reentry must contain exactly condition and next_actor")
    else:
        if not _nonempty(reentry["condition"]) or not _nonempty(reentry["next_actor"]):
            errors.append("reentry fields must be non-empty strings")

    if not _nonempty(state["updated_at"]):
        errors.append("updated_at must be a non-empty ISO 8601 string")
    else:
        try:
            parsed = datetime.fromisoformat(state["updated_at"].replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                errors.append("updated_at must include a timezone")
        except ValueError:
            errors.append("updated_at must be valid ISO 8601")

    if status in TERMINAL and isinstance(next_move, dict) and next_move.get("authority_required") is True:
        errors.append("terminal pursuit cannot require authority for a next move")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    try:
        payload = json.loads(args.state.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        result = {"valid": False, "errors": [str(exc)], "path": str(args.state)}
    else:
        errors = validate(payload)
        result = {"valid": not errors, "errors": errors, "path": str(args.state)}
    if args.as_json:
        print(json.dumps(result, indent=2))
    elif result["valid"]:
        print(f"VALID: {args.state}")
    else:
        for error in result["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
