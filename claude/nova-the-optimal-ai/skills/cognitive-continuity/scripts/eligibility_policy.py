#!/usr/bin/env python3
"""Deterministic cd-continuity-eligibility/v2 gate shared by derived views."""
from __future__ import annotations
import copy
import re
from datetime import datetime, timezone
from typing import Any, Iterable

POLICY_ID = "cd-continuity-eligibility/v2"
SENSITIVITY = {"ordinary": 0, "limited": 1, "sensitive": 2, "restricted": 3}
SECRET_KEYS = {
    "authorization", "proxy_authorization", "x_api_key", "api_key", "apikey", "access_token", "refresh_token",
    "client_secret", "password", "passwd", "cookie", "set_cookie", "private_key", "secret", "nonce",
}
SECRET_PATTERNS = (
    re.compile(r"(?i)(?:authorization|proxy-authorization|x-api-key)\s*:\s*\S+"),
    re.compile(r"(?i)\b(?:access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd|cookie|api[_-]?key|nonce)\b\s*[:=]\s*[^\s&]+"),
    re.compile(r"(?i)[?&](?:access_token|refresh_token|api_key|apikey|client_secret|nonce)=[^&#\s]+"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{8,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\b(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{8,}\b", re.I),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b", re.I),
    re.compile(r"\bAKIA[A-Z0-9]{12,}\b"),
)
PATH_PATTERNS = (
    re.compile(r"[A-Za-z]:\\(?:[^\\\s]+\\)+[^\\\s]+"),
    re.compile(r"/(?:home|Users|var|tmp)/\S+"),
)


def _normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _secret_bearing_key(value: str) -> bool:
    normalized = _normalized_key(value)
    if normalized in SECRET_KEYS:
        return True
    padded = f"_{normalized}_"
    return any(
        padded.startswith(f"_{secret}_") or padded.endswith(f"_{secret}_") or f"_{secret}_" in padded
        for secret in SECRET_KEYS
    )

def contains_secret_data(value: Any, parent_key: str | None = None) -> bool:
    if parent_key and _secret_bearing_key(parent_key) and value not in (None, "", [], {}):
        return True
    if isinstance(value, dict):
        return any(contains_secret_data(child, str(key)) for key, child in value.items())
    if isinstance(value, list):
        return any(contains_secret_data(child, parent_key) for child in value)
    if isinstance(value, str):
        return any(pattern.search(value) for pattern in SECRET_PATTERNS)
    return False


def sanitize_text(value: str) -> str:
    text = value
    for pattern in PATH_PATTERNS:
        text = pattern.sub("<path>", text)
    text = re.sub(r"\b[A-Fa-f0-9]{24,}\b", "<opaque-id>", text)
    return text


def sanitize_object(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: sanitize_object(child) for key, child in value.items()}
    if isinstance(value, list):
        return [sanitize_object(child) for child in value]
    if isinstance(value, str):
        return sanitize_text(value)
    return copy.deepcopy(value)


def parse_time_strict(value: Any, *, nullable: bool) -> tuple[datetime | None, bool]:
    if value is None:
        return (None, nullable)
    if not isinstance(value, str) or not value:
        return None, False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None, False
        return parsed.astimezone(timezone.utc), True
    except ValueError:
        return None, False


def scope_matches(record_scope: Any, query_scope: dict[str, Any]) -> bool:
    if not isinstance(record_scope, dict):
        return False
    if any(record_scope.get(key) != query_scope.get(key) for key in ("user", "agent")):
        return False
    rp, qp = record_scope.get("project"), query_scope.get("project")
    if qp == "*":
        if rp != "*": return False
    elif rp not in ("*", qp):
        return False
    rt, qt = record_scope.get("thread"), query_scope.get("thread")
    return rt is None if qt in (None, "*") else rt in (None, qt)


def environment_predicate(row: dict[str, Any]) -> tuple[str | None, str | None]:
    occurrence = row.get("occurrence") if isinstance(row.get("occurrence"), dict) else {}
    environment = occurrence.get("environment") if isinstance(occurrence.get("environment"), dict) else {}
    if environment:
        return environment.get("name"), environment.get("version")
    pattern = row.get("failure_pattern") if isinstance(row.get("failure_pattern"), dict) else {}
    facets = pattern.get("matcher_facets") if isinstance(pattern.get("matcher_facets"), dict) else {}
    if facets.get("environment"):
        return str(facets["environment"]), None
    predicate = row.get("environment_predicate") if isinstance(row.get("environment_predicate"), dict) else {}
    if predicate:
        return predicate.get("name"), predicate.get("version")
    name = version = None
    for tag in row.get("tags") or []:
        if isinstance(tag, str) and tag.startswith("environment:"):
            name = tag.split(":", 1)[1]
        if isinstance(tag, str) and tag.startswith("environment-version:"):
            version = tag.split(":", 1)[1]
    return name, version


def evaluate(
    row: dict[str, Any], *, scope: dict[str, Any], ceiling: str, now: datetime,
    environment: str | None, environment_version: str | None, episode_ids: set[str],
    unreachable_source_ids: set[str], allowed_statuses: Iterable[Any] = (None, "current"),
    schema_valid: bool = True,
) -> tuple[bool, str, dict[str, Any] | None]:
    if not schema_valid:
        return False, "schema_invalid", None
    if not scope_matches(row.get("scope"), scope):
        return False, "scope_mismatch", None
    sensitivity = str(row.get("sensitivity", "restricted"))
    if SENSITIVITY.get(sensitivity, 99) > SENSITIVITY.get(ceiling, -1):
        return False, "sensitivity_denied", None
    if row.get("status") not in set(allowed_statuses):
        return False, "status_ineligible", None
    valid_from, valid_from_ok = parse_time_strict(row.get("valid_from"), nullable=False)
    valid_to, valid_to_ok = parse_time_strict(row.get("valid_to"), nullable=True)
    expires, expires_ok = parse_time_strict(row.get("expires_at"), nullable=True)
    if not (valid_from_ok and valid_to_ok and expires_ok):
        return False, "time_malformed", None
    if valid_from and valid_from > now:
        return False, "not_yet_valid", None
    if valid_to and valid_to <= now:
        return False, "validity_ended", None
    if expires and expires <= now:
        return False, "expired", None
    expected_environment, expected_version = environment_predicate(row)
    if expected_environment and (not environment or expected_environment.casefold() != environment.casefold()):
        return False, "environment_mismatch", None
    if expected_version and (not environment_version or expected_version.casefold() != environment_version.casefold()):
        return False, "environment_version_mismatch", None
    tags = {str(item).casefold() for item in row.get("tags") or []}
    if tags & {"forgotten", "source-unreachable"}:
        return False, "source_unreachable", None
    source_ids = set(str(item) for item in row.get("source_ids") or [])
    if row.get("id") in unreachable_source_ids or source_ids & unreachable_source_ids:
        return False, "source_unreachable", None
    if source_ids and not source_ids.issubset(episode_ids):
        return False, "source_unreachable", None
    if row.get("kind") is not None and not source_ids:
        return False, "source_unreachable", None
    if contains_secret_data(row):
        return False, "redaction_rejected", None
    return True, "eligible", sanitize_object(row)