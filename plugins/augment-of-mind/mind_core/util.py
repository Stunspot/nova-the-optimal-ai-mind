"""Small deterministic helpers shared by Core modules."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from .errors import ValidationError

IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,254}\Z")
SHA256_HEX = re.compile(r"[0-9a-f]{64}\Z")


def require_identifier(value: object, field: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValidationError(f"{field} must be a stable identifier")
    return value


def require_text(value: object, field: str, *, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} must be non-empty text")
    if len(value) > maximum:
        raise ValidationError(f"{field} exceeds {maximum} characters")
    return value


def optional_text(value: object, field: str, *, maximum: int = 4096) -> str | None:
    if value is None:
        return None
    return require_text(value, field, maximum=maximum)


def require_sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or not SHA256_HEX.fullmatch(value.lower()):
        raise ValidationError(f"{field} must be a lowercase SHA-256 digest")
    return value.lower()


def parse_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be an RFC 3339 timestamp")
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError(f"{field} must be an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValidationError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def timestamp(value: datetime | None = None) -> str:
    current = value or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def require_interval(observed_at: object, expires_at: object) -> tuple[str, str]:
    observed = parse_timestamp(observed_at, "observed_at")
    expires = parse_timestamp(expires_at, "expires_at")
    if expires <= observed:
        raise ValidationError("expires_at must be later than observed_at")
    return timestamp(observed), timestamp(expires)


def require_bounded_interval(
    observed_at: str,
    expires_at: str,
    parent_observed_at: str,
    parent_expires_at: str,
    field: str,
) -> None:
    """Require a scoped observation to live entirely inside its parent session."""

    observed = parse_timestamp(observed_at, f"{field}.observed_at")
    expires = parse_timestamp(expires_at, f"{field}.expires_at")
    parent_observed = parse_timestamp(parent_observed_at, "session.observed_at")
    parent_expires = parse_timestamp(parent_expires_at, "session.expires_at")
    if expires <= observed:
        raise ValidationError(f"{field} expiry must be later than its observation")
    if observed < parent_observed or expires > parent_expires:
        raise ValidationError(f"{field} interval must be within the host session")


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def record_binding_hash(record: dict[str, Any]) -> str:
    """Hash one canonical record without its self-referential receipt pointer."""

    return sha256_text(
        canonical_json(
            {
                key: value
                for key, value in record.items()
                if key != "evidence_receipt_id"
            }
        )
    )


def new_id(prefix: str) -> str:
    require_identifier(prefix, "prefix")
    return f"{prefix}:{uuid.uuid4().hex}"


def is_fresh(expires_at: str, *, now: datetime | None = None) -> bool:
    return parse_timestamp(expires_at, "expires_at") > (now or datetime.now(timezone.utc))
