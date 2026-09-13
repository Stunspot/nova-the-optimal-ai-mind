"""Pure Worldline occurrence, pointer and control-policy invariants."""
from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from eligibility_policy import contains_secret_data, parse_time_strict, sanitize_object
from schema_validation import SchemaCatalog
from workspace_runtime import ContinuityError

SCHEMAS = Path(__file__).resolve().parents[1] / "assets" / "schemas"
SENSITIVITY = {"ordinary": 0, "limited": 1, "sensitive": 2, "restricted": 3}


def _validate(value: Any, schema: str) -> None:
    errors = SchemaCatalog(SCHEMAS).validate(value, schema)
    if errors:
        raise ContinuityError("; ".join(errors[:5]), "schema_invalid")
    if contains_secret_data(value):
        raise ContinuityError("Worldline metadata contains secret-shaped data", "redaction_rejected")


def safe_locator(value: str) -> str:
    """Return a permitted locator byte-for-byte; never dereference it."""
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise ContinuityError("Source locator is empty or too long", "locator_invalid")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ContinuityError("Source locator contains control characters", "locator_invalid")
    if contains_secret_data(value):
        raise ContinuityError("Source locator contains secret-shaped data", "redaction_rejected")
    try:
        parsed = urlsplit(value)
        if parsed.scheme.casefold() in {"javascript", "data", "vbscript"}:
            raise ContinuityError("Executable source locator is not allowed", "locator_invalid")
        if parsed.username is not None or parsed.password is not None:
            raise ContinuityError("Source locator contains credentials", "redaction_rejected")
        if parsed.scheme.casefold() in {"http", "https"} and not parsed.hostname:
            raise ContinuityError("Web source locator has no host", "locator_invalid")
    except ValueError as exc:
        raise ContinuityError("Source locator is malformed", "locator_invalid") from exc
    return value


def validate_event(event: dict[str, Any]) -> None:
    _validate(event, "worldline-event-v2.schema.json")
    start, start_ok = parse_time_strict(event["occurred_at"], nullable=False)
    end, end_ok = parse_time_strict(event["ended_at"], nullable=True)
    if not start_ok or not end_ok or (end is not None and end <= start):
        raise ContinuityError("Occurrence interval is malformed", "event_time_invalid")
    if event["time_precision"] == "range" and end is None:
        raise ContinuityError("Range precision requires ended_at", "event_time_invalid")
    if event["time_precision"] == "unknown" and event["time_basis"] != "recorded":
        raise ContinuityError("Unknown occurrence time requires a recorded-time anchor", "event_time_invalid")
    if event["disposition"] == "retracted" and not event["supersedes"]:
        raise ContinuityError("Retraction requires a correction target", "correction_invalid")
    for source in event["sources"]:
        safe_locator(source["locator"])


def validate_policy(policy: dict[str, Any]) -> None:
    _validate(policy, "worldline-policy-v1.schema.json")
    safe_locator(policy["authority_source"])


def effective_policy(
    rows: list[dict[str, Any]], exact_scope: dict[str, Any], now: datetime
) -> dict[str, Any]:
    """Committed ledger order controls policy; timestamps do not order grants."""
    if any(exact_scope.get(key) in (None, "", "*") for key in ("user", "agent")):
        raise ContinuityError("Policy requires exact user and agent", "scope_denied")
    result: dict[str, Any] = {
        "mode": "unconfigured", "id": None, "authority": None, "authority_source": None
    }
    for row in rows:
        scope = row.get("scope") or {}
        if any(scope.get(key) != exact_scope.get(key) for key in ("user", "agent")):
            continue
        if scope.get("project") not in ("*", exact_scope.get("project")):
            continue
        if scope.get("thread") not in (None, "*", exact_scope.get("thread")):
            continue
        policy = row.get("worldline_policy")
        if not isinstance(policy, dict):
            continue
        validate_policy(policy)
        if row.get("type") != "permission":
            raise ContinuityError("Policy is not a permission episode", "workspace_invalid")
        authority = str((row.get("source") or {}).get("authority") or "")
        if not authority.casefold().startswith(("user", "human", "stunspot")):
            raise ContinuityError("Policy lacks recorded human authority", "workspace_invalid")
        expires, valid = parse_time_strict(row.get("expires_at"), nullable=True)
        if not valid:
            raise ContinuityError("Policy retention time is malformed", "workspace_invalid")
        if "forgotten" in row.get("tags", []) or (expires is not None and expires <= now):
            result = {"mode": "off", "id": row["id"], "authority": authority, "authority_source": None}
        else:
            result = {"mode": policy["mode"], "id": row["id"], "authority": authority,
                      "authority_source": policy["authority_source"]}
    return result


def family_ids(rows: list[dict[str, Any]], selected: set[str]) -> set[str]:
    """Expand revisions and exact policy history; associations are not dependency."""
    result = set(selected)
    policy_scopes = [row.get("scope") for row in rows
                     if row.get("id") in selected and row.get("worldline_policy") is not None]
    result.update(row["id"] for row in rows if row.get("worldline_policy") is not None
                  and row.get("scope") in policy_scopes)
    changed = True
    while changed:
        changed = False
        for row in rows:
            event = row.get("worldline_event")
            if not isinstance(event, dict):
                continue
            connected = {str(row["id"]), *event.get("supersedes", [])}
            if result & connected and not connected <= result:
                result.update(connected)
                changed = True
    return result


def sever_associations(row: dict[str, Any], removed: set[str]) -> dict[str, Any]:
    event = row.get("worldline_event")
    if not isinstance(event, dict) or not (set(event.get("related_ids", [])) & removed):
        return row
    value = copy.deepcopy(row)
    value["worldline_event"]["related_ids"] = [
        key for key in event.get("related_ids", []) if key not in removed
    ]
    return value


def sanitize_export_row(row: dict[str, Any]) -> dict[str, Any]:
    """Retain validated event metadata and source identity through export."""
    value = sanitize_object(row)
    event = row.get("worldline_event")
    if isinstance(event, dict):
        validate_event(event)
        value["worldline_event"] = copy.deepcopy(event)
        value["id"] = row["id"]
        value["content"] = row["content"]
        value["scope"] = copy.deepcopy(row["scope"])
        value["source"] = copy.deepcopy(row["source"])
        safe_locator(value["source"]["locator"])
    return value


def validate_episode_graph(rows: list[dict[str, Any]]) -> None:
    """Check native metadata, pointers, related boundaries and linear revisions."""
    by_id = {str(row.get("id")): row for row in rows}
    children: dict[str, str] = {}
    for row in rows:
        event = row.get("worldline_event")
        policy = row.get("worldline_policy")
        if event is not None and policy is not None:
            raise ContinuityError("An episode cannot be event and policy", "workspace_invalid")
        if policy is not None:
            validate_policy(policy)
            source = row.get("source") or {}
            if source.get("locator") != policy["authority_source"] or source.get("kind") != "user":
                raise ContinuityError("Policy directive provenance disagrees", "workspace_invalid")
            if not str(source.get("authority") or "").casefold().startswith(("user", "human", "stunspot")):
                raise ContinuityError("Policy lacks human authority", "authority_denied")
            if row.get("type") != "permission" or row.get("expires_at") is not None:
                raise ContinuityError("Policy must be a nonexpiring permission episode", "workspace_invalid")
        if event is None:
            continue
        validate_event(event)
        if row.get("content") != event["title"]:
            raise ContinuityError("Event recognition title and content disagree", "workspace_invalid")
        if (row.get("source") or {}).get("locator") != event["sources"][0]["locator"]:
            raise ContinuityError("Event source pointer and locator disagree", "workspace_invalid")
        for reference in [*event["related_ids"], *event["supersedes"]]:
            target = by_id.get(reference)
            if target is None or "forgotten" in target.get("tags", []):
                raise ContinuityError("Event references absent or forgotten evidence", "source_unreachable")
            if any((target.get("scope") or {}).get(key) != (row.get("scope") or {}).get(key)
                   for key in ("user", "agent")):
                raise ContinuityError("Event relation crosses owner boundary", "scope_denied")
        if event["supersedes"]:
            if row.get("type") != "correction" or not str((row.get("source") or {}).get("authority") or "").casefold().startswith(("user", "human", "stunspot")):
                raise ContinuityError("Correction lacks explicit human provenance", "authority_denied")
            parent = event["supersedes"][0]
            target = by_id[parent]
            if target.get("worldline_event") is None or target.get("scope") != row.get("scope"):
                raise ContinuityError("Correction crosses event or scope boundary", "correction_invalid")
            if parent in children:
                raise ContinuityError("Correction history branches", "correction_conflict")
            children[parent] = str(row["id"])
    for start in children:
        visited: set[str] = set()
        at = start
        while at in children:
            if at in visited:
                raise ContinuityError("Correction history cycles", "correction_invalid")
            visited.add(at)
            at = children[at]

