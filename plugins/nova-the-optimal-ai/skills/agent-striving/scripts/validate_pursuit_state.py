#!/usr/bin/env python3
"""Validate a sparse Agent Striving portable handoff without dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


FORMAT = "cd-agent-striving-handoff/v2"
REQUIRED = {
    "format",
    "pursuit_ref",
    "authority_source",
    "current_direction",
    "disposition",
    "continuity",
    "updated_at",
}
OPTIONAL = {"current_state_ref", "foreground", "supersedes"}
DISPOSITIONS = ("live", "resting", "released")
PERSISTENCE = ("confirmed", "prepared", "unavailable")
REACTIVATION = ("confirmed", "manual", "unavailable")
FOREGROUND_FIELDS = {"settled", "actual_state", "blockers", "likely_continuation"}
CONTINUITY_FIELDS = {
    "persistence",
    "persistence_receipt",
    "reactivation",
    "reactivation_cue",
    "lost_guarantee",
}
TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nullable_nonempty(value: Any) -> bool:
    return value is None or _nonempty(value)


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_nonempty(item) for item in value)


class JsonInputError(ValueError):
    """Raised when JSON uses ambiguous or nonstandard constructs."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise JsonInputError(f"duplicate object key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise JsonInputError(f"nonstandard JSON constant: {value}")


def load_payload(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8-sig"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )


def validate(state: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(state, dict):
        return ["root must be an object"]

    allowed = REQUIRED | OPTIONAL
    missing = sorted(REQUIRED - set(state))
    extra = sorted(set(state) - allowed)
    if missing:
        errors.append(f"missing required fields: {', '.join(missing)}")
    if extra:
        errors.append(f"unexpected fields: {', '.join(extra)}")

    if "format" in state and state["format"] != FORMAT:
        errors.append(f"format must be {FORMAT}")
    for field in ("pursuit_ref", "authority_source", "current_direction"):
        if field in state and not _nonempty(state[field]):
            errors.append(f"{field} must be a non-empty string")

    disposition = state.get("disposition")
    if "disposition" in state and (
        not isinstance(disposition, str) or disposition not in DISPOSITIONS
    ):
        errors.append(f"disposition must be one of: {', '.join(DISPOSITIONS)}")

    for field in ("current_state_ref", "supersedes"):
        if field in state and not _nonempty(state[field]):
            errors.append(f"{field} must be a non-empty string when present")

    foreground = state.get("foreground")
    if "foreground" in state:
        if (
            not isinstance(foreground, dict)
            or not foreground
            or not set(foreground).issubset(FOREGROUND_FIELDS)
        ):
            errors.append(
                "foreground must contain one or more of: settled, actual_state, blockers, likely_continuation"
            )
        else:
            if "settled" in foreground and not _string_list(foreground["settled"]):
                errors.append("foreground.settled must be an array of non-empty strings")
            if "actual_state" in foreground and not _nonempty(foreground["actual_state"]):
                errors.append("foreground.actual_state must be a non-empty string")
            if "blockers" in foreground and not _string_list(foreground["blockers"]):
                errors.append("foreground.blockers must be an array of non-empty strings")
            if (
                "likely_continuation" in foreground
                and not _nonempty(foreground["likely_continuation"])
            ):
                errors.append("foreground.likely_continuation must be a non-empty string")
            if disposition == "released" and "likely_continuation" in foreground:
                errors.append("released pursuit cannot retain a likely continuation")

    continuity = state.get("continuity")
    if "continuity" in state:
        if not isinstance(continuity, dict) or set(continuity) != CONTINUITY_FIELDS:
            errors.append(
                "continuity must contain exactly persistence, persistence_receipt, reactivation, reactivation_cue, and lost_guarantee"
            )
        else:
            persistence = continuity["persistence"]
            reactivation = continuity["reactivation"]
            receipt = continuity["persistence_receipt"]
            cue = continuity["reactivation_cue"]
            lost = continuity["lost_guarantee"]

            if not isinstance(persistence, str) or persistence not in PERSISTENCE:
                errors.append(f"continuity.persistence must be one of: {', '.join(PERSISTENCE)}")
            if not isinstance(reactivation, str) or reactivation not in REACTIVATION:
                errors.append(f"continuity.reactivation must be one of: {', '.join(REACTIVATION)}")
            if not _nullable_nonempty(receipt):
                errors.append("continuity.persistence_receipt must be null or a non-empty string")
            if not _nullable_nonempty(cue):
                errors.append("continuity.reactivation_cue must be null or a non-empty string")
            if not _nullable_nonempty(lost):
                errors.append("continuity.lost_guarantee must be null or a non-empty string")

            persistence_confirmed = persistence == "confirmed"
            reactivation_available = reactivation in ("confirmed", "manual")
            if persistence_confirmed and not _nonempty(receipt):
                errors.append("confirmed persistence requires a persistence_receipt")
            if not persistence_confirmed and receipt is not None:
                errors.append("unconfirmed persistence cannot claim a persistence_receipt")
            if reactivation_available and not _nonempty(cue):
                errors.append("available reactivation requires a reactivation_cue")
            if not reactivation_available and cue is not None:
                errors.append("unavailable reactivation cannot claim a reactivation_cue")
            if persistence_confirmed and reactivation_available:
                if lost is not None:
                    errors.append("durable continuity must not claim a lost guarantee")
            elif not _nonempty(lost):
                errors.append("incomplete continuity requires a lost_guarantee")

    if "updated_at" in state:
        updated_at = state["updated_at"]
        if not _nonempty(updated_at) or not TIMESTAMP_RE.fullmatch(updated_at):
            errors.append("updated_at must be an RFC 3339 date-time with a timezone")
        else:
            try:
                datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except ValueError:
                errors.append("updated_at must be a real calendar date-time")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    try:
        payload = load_payload(args.state)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
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
