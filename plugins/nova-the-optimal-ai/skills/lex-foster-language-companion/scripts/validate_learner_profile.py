#!/usr/bin/env python3
"""Validate a Lex Foster learner profile without external dependencies."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


FORMAT = "lex-foster-learner-profile/v1"
EVIDENCE_STATES = {"new", "supported", "independent", "transferred"}
GOAL_STATES = {"active", "paused", "completed", "retired"}
PREFERENCE_VALUES = {
    "interruption": {"immediate", "natural-pauses", "end-of-turn"},
    "correction_focus": {"communication-first", "balanced", "fine-grained"},
    "explanation_depth": {"compact", "contrastive", "deep"},
    "challenge": {"supported", "stretch", "immersive"},
    "working_language_use": {"welcome", "minimal", "on-request"},
}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_datetime(value: Any) -> bool:
    if not _nonempty(value):
        return False
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return True


def validate_profile(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["profile must be a JSON object"]

    if data.get("format") != FORMAT:
        errors.append(f"format must be {FORMAT!r}")
    for key in ("profile_id", "working_language"):
        if not _nonempty(data.get(key)):
            errors.append(f"{key} must be a non-empty string")
    if not _valid_datetime(data.get("updated_at")):
        errors.append("updated_at must be an ISO 8601 date-time")

    targets = data.get("target_languages")
    if not isinstance(targets, list) or not targets:
        errors.append("target_languages must contain at least one entry")
    else:
        for index, target in enumerate(targets):
            if not isinstance(target, dict):
                errors.append(f"target_languages[{index}] must be an object")
                continue
            for key in ("language", "variety", "script"):
                if not _nonempty(target.get(key)):
                    errors.append(
                        f"target_languages[{index}].{key} must be a non-empty string"
                    )

    goals = data.get("goals")
    goal_ids: set[str] = set()
    if not isinstance(goals, list):
        errors.append("goals must be an array")
    else:
        for index, goal in enumerate(goals):
            if not isinstance(goal, dict):
                errors.append(f"goals[{index}] must be an object")
                continue
            goal_id = goal.get("id")
            if not _nonempty(goal_id):
                errors.append(f"goals[{index}].id must be a non-empty string")
            elif goal_id in goal_ids:
                errors.append(f"duplicate goal id: {goal_id}")
            else:
                goal_ids.add(goal_id)
            for key in ("situation", "success_evidence"):
                if not _nonempty(goal.get(key)):
                    errors.append(f"goals[{index}].{key} must be a non-empty string")
            if goal.get("status") not in GOAL_STATES:
                errors.append(
                    f"goals[{index}].status must be one of {sorted(GOAL_STATES)}"
                )

    preferences = data.get("preferences")
    if not isinstance(preferences, dict):
        errors.append("preferences must be an object")
    else:
        for key, allowed in PREFERENCE_VALUES.items():
            if preferences.get(key) not in allowed:
                errors.append(f"preferences.{key} must be one of {sorted(allowed)}")

    evidence = data.get("evidence")
    evidence_ids: set[str] = set()
    if not isinstance(evidence, list):
        errors.append("evidence must be an array")
    else:
        for index, item in enumerate(evidence):
            if not isinstance(item, dict):
                errors.append(f"evidence[{index}] must be an object")
                continue
            evidence_id = item.get("id")
            if not _nonempty(evidence_id):
                errors.append(f"evidence[{index}].id must be a non-empty string")
            elif evidence_id in evidence_ids:
                errors.append(f"duplicate evidence id: {evidence_id}")
            else:
                evidence_ids.add(evidence_id)
            if not _valid_datetime(item.get("observed_at")):
                errors.append(f"evidence[{index}].observed_at must be an ISO date-time")
            for key in ("target_language", "item", "task", "support"):
                if not _nonempty(item.get(key)):
                    errors.append(
                        f"evidence[{index}].{key} must be a non-empty string"
                    )
            if item.get("state") not in EVIDENCE_STATES:
                errors.append(
                    f"evidence[{index}].state must be one of {sorted(EVIDENCE_STATES)}"
                )

    queue = data.get("retrieval_queue")
    if not isinstance(queue, list):
        errors.append("retrieval_queue must be an array")
    else:
        for index, item in enumerate(queue):
            if not isinstance(item, dict):
                errors.append(f"retrieval_queue[{index}] must be an object")
                continue
            for key in ("evidence_id", "when", "variation"):
                if not _nonempty(item.get(key)):
                    errors.append(
                        f"retrieval_queue[{index}].{key} must be a non-empty string"
                    )
            if _nonempty(item.get("evidence_id")) and item["evidence_id"] not in evidence_ids:
                errors.append(
                    f"retrieval_queue[{index}].evidence_id references unknown evidence"
                )

    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_learner_profile.py <profile.json>", file=sys.stderr)
        return 2

    path = Path(argv[1])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL {path}: {exc}", file=sys.stderr)
        return 1

    errors = validate_profile(data)
    if errors:
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        print(f"FAIL {path}: {len(errors)} error(s)", file=sys.stderr)
        return 1

    print(
        f"PASS {path}: {len(data['target_languages'])} target language(s), "
        f"{len(data['evidence'])} evidence item(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
