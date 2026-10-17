"""Canonical Commonplace record model and state-transition rules."""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import re
from typing import Any

from .runtime import ValidationError, canonical_json_bytes, utc_now, validate_timestamp


RECORD_SCHEMA = "nova-commonplace.record.v1"
RECORD_KINDS = frozenset({
    "note", "capture", "assertion", "procedure", "question",
    "source_packet", "reflection", "learning", "fragment", "promotion_proposal",
})
ORIGINS = frozenset({"user_authored", "quoted", "reported", "model_inferred"})
REVIEWS = frozenset({"unreviewed", "accepted", "verified"})
DISPUTES = frozenset({"undisputed", "challenged", "contradicted"})
LIFECYCLES = frozenset({"current", "superseded", "retracted"})
SENSITIVITIES = frozenset({"public", "personal", "private", "restricted"})
RIGHTS = frozenset({"self_authored", "quoted_excerpt", "licensed", "unknown"})
SOURCE_TYPES = frozenset(
    {"user", "url", "web", "file", "document", "conversation", "record", "other"}
)
RELATION_ORIGINS = frozenset({"deterministic", "model_inferred", "user_authored"})
STATE_FIELDS = frozenset({"review", "dispute", "lifecycle", "sensitivity", "rights", "time"})

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_RELATION_RE = re.compile(r"^[a-z][a-z0-9._:-]{0,63}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_RECORD_FIELDS = {
    "schema",
    "id",
    "kind",
    "title",
    "body",
    "created_at",
    "updated_at",
    "revision",
    "origin",
    "review",
    "dispute",
    "lifecycle",
    "sensitivity",
    "rights",
    "time",
    "provenance",
    "relations",
    "supersedes",
    "superseded_by",
    "metadata",
}
_RESERVED_METADATA_KEYS = {
    "authority",
    "authorization",
    "system_instruction",
    "tool_call",
    "control",
}


def validate_record_id(value: Any, *, field: str = "record.id") -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValidationError(
            f"{field} must be 1-128 characters using letters, digits, dot, underscore, colon, or hyphen"
        )
    if value in {".", ".."}:
        raise ValidationError(f"{field} is not safe")
    return value


def _enum(value: Any, options: frozenset[str], *, field: str) -> str:
    if not isinstance(value, str) or value not in options:
        raise ValidationError(f"{field} must be one of {sorted(options)}")
    return value


def _string(value: Any, *, field: str, required: bool = False, limit: int = 1_000_000) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    if required and not value.strip():
        raise ValidationError(f"{field} must not be blank")
    if len(value) > limit:
        raise ValidationError(f"{field} exceeds {limit} characters")
    return value


def _unique_ids(values: Any, *, field: str, self_id: str) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise ValidationError(f"{field} must be an array")
    result = sorted({validate_record_id(value, field=field) for value in values})
    if self_id in result:
        raise ValidationError(f"{field} cannot contain the record itself")
    return result


def normalize_time(value: Any) -> dict[str, str | None]:
    if value is None:
        value = {}
    if not isinstance(value, Mapping):
        raise ValidationError("record.time must be an object")
    allowed = {"observed_at", "valid_from", "valid_to", "as_of"}
    unknown = set(value) - allowed
    if unknown:
        raise ValidationError(f"record.time contains unsupported fields: {sorted(unknown)}")
    result = {
        field: validate_timestamp(value.get(field), field=f"record.time.{field}")
        for field in sorted(allowed)
    }
    if result["valid_from"] and result["valid_to"] and result["valid_from"] > result["valid_to"]:
        raise ValidationError("record.time.valid_from must not be after valid_to")
    return result


def evaluate_record_validity(
    record: Mapping[str, Any],
    *,
    at: str | None = None,
) -> dict[str, Any]:
    """Evaluate declared validity at one instant without claiming bitemporal truth.

    ``valid_from`` and ``valid_to`` are treated as inclusive bounds.  ``observed_at``
    and ``as_of`` are returned as epistemic context, not silently promoted into
    validity bounds.  An unbounded record is therefore ``unspecified`` rather than
    presumed eternally valid.
    """

    checked = normalize_record(
        record,
        now=(record.get("updated_at") if isinstance(record, Mapping) else None),
        allow_reviewed_model_inference=True,
    )
    evaluated_at = validate_timestamp(
        utc_now() if at is None else at, field="validity.at", optional=False
    )
    temporal = checked["time"]
    valid_from = temporal["valid_from"]
    valid_to = temporal["valid_to"]

    if valid_from is not None and evaluated_at < valid_from:
        status = "not_yet_valid"
        is_valid: bool | None = False
    elif valid_to is not None and evaluated_at > valid_to:
        status = "no_longer_valid"
        is_valid = False
    elif valid_from is not None or valid_to is not None:
        status = "valid"
        is_valid = True
    else:
        status = "unspecified"
        is_valid = None

    return {
        "status": status,
        "is_valid": is_valid,
        "evaluated_at": evaluated_at,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "observed_at": temporal["observed_at"],
        "as_of": temporal["as_of"],
        "interval_semantics": "inclusive",
        "temporal_model": "declared-validity.v1",
        "record_lifecycle": checked["lifecycle"],
        "bitemporal_complete": False,
    }


def normalize_span(value: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field} must be an object")
    allowed = {"start", "end", "quote", "selector"}
    unknown = set(value) - allowed
    if unknown:
        raise ValidationError(f"{field} contains unsupported fields: {sorted(unknown)}")
    if "start" not in value or "end" not in value:
        raise ValidationError(f"{field} requires start and end offsets")
    start, end = value["start"], value["end"]
    if isinstance(start, bool) or not isinstance(start, int) or start < 0:
        raise ValidationError(f"{field}.start must be a non-negative integer")
    if isinstance(end, bool) or not isinstance(end, int) or end <= start:
        raise ValidationError(f"{field}.end must be greater than start")
    result: dict[str, Any] = {"start": start, "end": end}
    if "quote" in value:
        result["quote"] = _string(value["quote"], field=f"{field}.quote", limit=100_000)
    if "selector" in value:
        result["selector"] = _string(
            value["selector"], field=f"{field}.selector", required=True, limit=4_096
        )
    return result


def normalize_provenance(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError("record.provenance must be an array")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        field = f"record.provenance[{index}]"
        if not isinstance(item, Mapping):
            raise ValidationError(f"{field} must be an object")
        allowed = {
            "source_type",
            "source_ref",
            "retrieved_at",
            "content_sha256",
            "span",
            "note",
        }
        unknown = set(item) - allowed
        if unknown:
            raise ValidationError(f"{field} contains unsupported fields: {sorted(unknown)}")
        source_type = _enum(item.get("source_type"), SOURCE_TYPES, field=f"{field}.source_type")
        source_ref = _string(
            item.get("source_ref"), field=f"{field}.source_ref", required=True, limit=16_384
        )
        if source_type == "record":
            validate_record_id(source_ref, field=f"{field}.source_ref")
        entry: dict[str, Any] = {
            "source_type": source_type,
            "source_ref": source_ref,
            "retrieved_at": validate_timestamp(
                item.get("retrieved_at"), field=f"{field}.retrieved_at"
            ),
        }
        digest = item.get("content_sha256")
        if digest is not None:
            if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
                raise ValidationError(f"{field}.content_sha256 must be lowercase SHA-256")
            entry["content_sha256"] = digest
        if "span" in item:
            entry["span"] = normalize_span(item["span"], field=f"{field}.span")
        if "note" in item:
            entry["note"] = _string(item["note"], field=f"{field}.note", limit=16_384)
        result.append(entry)
    return result


def normalize_relations(value: Any, *, self_id: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError("record.relations must be an array")
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, item in enumerate(value):
        field = f"record.relations[{index}]"
        if not isinstance(item, Mapping):
            raise ValidationError(f"{field} must be an object")
        allowed = {"type", "target_id", "origin", "review", "confidence"}
        unknown = set(item) - allowed
        if unknown:
            raise ValidationError(f"{field} contains unsupported fields: {sorted(unknown)}")
        relation_type = item.get("type")
        if not isinstance(relation_type, str) or not _RELATION_RE.fullmatch(relation_type):
            raise ValidationError(f"{field}.type is invalid")
        target_id = validate_record_id(item.get("target_id"), field=f"{field}.target_id")
        if target_id == self_id:
            raise ValidationError(f"{field}.target_id cannot refer to itself")
        origin = _enum(
            item.get("origin", "deterministic"),
            RELATION_ORIGINS,
            field=f"{field}.origin",
        )
        review = _enum(item.get("review", "unreviewed"), REVIEWS, field=f"{field}.review")
        if origin == "model_inferred" and review != "unreviewed":
            raise ValidationError(
                f"{field} model_inferred relations must remain unreviewed; "
                "a human-approved edge must be re-authored as user_authored"
            )
        confidence = item.get("confidence")
        if confidence is not None:
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                raise ValidationError(f"{field}.confidence must be a number")
            confidence = float(confidence)
            if not 0.0 <= confidence <= 1.0:
                raise ValidationError(f"{field}.confidence must be between 0 and 1")
        key = (relation_type, target_id, origin)
        if key in seen:
            raise ValidationError(f"{field} duplicates another relation")
        seen.add(key)
        relation: dict[str, Any] = {
            "type": relation_type,
            "target_id": target_id,
            "origin": origin,
            "review": review,
        }
        if confidence is not None:
            relation["confidence"] = confidence
        result.append(relation)
    return sorted(result, key=lambda item: (item["type"], item["target_id"], item["origin"]))


def normalize_metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValidationError("record.metadata must be an object")
    result = deepcopy(dict(value))
    blocked = _RESERVED_METADATA_KEYS.intersection(result)
    if blocked:
        raise ValidationError(
            "record.metadata cannot confer authority or execution control: " + ", ".join(sorted(blocked))
        )
    canonical_json_bytes(result)
    return result


def normalize_record(
    value: Any,
    *,
    now: str | None = None,
    allow_reviewed_model_inference: bool = False,
) -> dict[str, Any]:
    """Validate and canonicalize a complete record object."""
    if not isinstance(value, Mapping):
        raise ValidationError("record must be an object")
    record = dict(value)
    unknown = set(record) - _RECORD_FIELDS
    if unknown:
        raise ValidationError(f"record contains unsupported fields: {sorted(unknown)}")
    if record.get("schema", RECORD_SCHEMA) != RECORD_SCHEMA:
        raise ValidationError(f"record.schema must be {RECORD_SCHEMA}")
    record_id = validate_record_id(record.get("id"))
    kind = _enum(record.get("kind"), RECORD_KINDS, field="record.kind")
    body = _string(record.get("body"), field="record.body", required=True)
    title = _string(record.get("title", ""), field="record.title", limit=4_096)
    timestamp = validate_timestamp(now or utc_now(), field="now", optional=False)
    created_at = validate_timestamp(
        record.get("created_at", timestamp), field="record.created_at", optional=False
    )
    updated_at = validate_timestamp(
        record.get("updated_at", created_at), field="record.updated_at", optional=False
    )
    if updated_at < created_at:
        raise ValidationError("record.updated_at must not precede created_at")
    revision = record.get("revision", 1)
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise ValidationError("record.revision must be a positive integer")
    origin = _enum(record.get("origin", "user_authored"), ORIGINS, field="record.origin")
    review = _enum(record.get("review", "unreviewed"), REVIEWS, field="record.review")
    provenance = normalize_provenance(record.get("provenance"))
    if kind in {"capture", "source_packet"} and not provenance:
        raise ValidationError("capture and source_packet records require provenance")
    if kind == "assertion" and origin in {"quoted", "reported", "model_inferred"} and not provenance:
        raise ValidationError(f"{origin} assertion records require provenance")
    if review == "verified" and not provenance:
        raise ValidationError("review=verified requires named provenance evidence")
    if origin == "model_inferred" and review != "unreviewed" and not allow_reviewed_model_inference:
        raise ValidationError(
            "new model_inferred records must remain review=unreviewed until an explicit state update"
        )
    normalized = {
        "schema": RECORD_SCHEMA,
        "id": record_id,
        "kind": kind,
        "title": title,
        "body": body,
        "created_at": created_at,
        "updated_at": updated_at,
        "revision": revision,
        "origin": origin,
        "review": review,
        "dispute": _enum(
            record.get("dispute", "undisputed"), DISPUTES, field="record.dispute"
        ),
        "lifecycle": _enum(
            record.get("lifecycle", "current"), LIFECYCLES, field="record.lifecycle"
        ),
        "sensitivity": _enum(
            record.get("sensitivity", "personal"),
            SENSITIVITIES,
            field="record.sensitivity",
        ),
        "rights": _enum(record.get("rights", "self_authored"), RIGHTS, field="record.rights"),
        "time": normalize_time(record.get("time")),
        "provenance": provenance,
        "relations": normalize_relations(record.get("relations"), self_id=record_id),
        "supersedes": _unique_ids(
            record.get("supersedes"), field="record.supersedes", self_id=record_id
        ),
        "superseded_by": _unique_ids(
            record.get("superseded_by"), field="record.superseded_by", self_id=record_id
        ),
        "metadata": normalize_metadata(record.get("metadata")),
    }
    if normalized["lifecycle"] == "superseded" and not normalized["superseded_by"]:
        raise ValidationError("superseded records must identify at least one replacement")
    canonical_json_bytes(normalized)
    return normalized


_REVIEW_TRANSITIONS = {
    "unreviewed": {"unreviewed", "accepted"},
    "accepted": {"accepted", "verified"},
    "verified": {"verified"},
}
_DISPUTE_TRANSITIONS = {
    "undisputed": {"undisputed", "challenged", "contradicted"},
    "challenged": {"challenged", "contradicted"},
    "contradicted": {"contradicted"},
}
_LIFECYCLE_TRANSITIONS = {
    "current": {"current", "superseded", "retracted"},
    "superseded": {"superseded", "retracted"},
    "retracted": {"retracted"},
}


def apply_state_changes(record: Mapping[str, Any], changes: Any, *, now: str | None = None) -> dict[str, Any]:
    if not isinstance(changes, Mapping) or not changes:
        raise ValidationError("state changes must be a non-empty object")
    unknown = set(changes) - STATE_FIELDS
    if unknown:
        raise ValidationError(f"state changes contain unsupported fields: {sorted(unknown)}")
    result = deepcopy(dict(record))
    if "review" in changes:
        proposed = _enum(changes["review"], REVIEWS, field="state.review")
        if proposed not in _REVIEW_TRANSITIONS[result["review"]]:
            raise ValidationError(f"invalid review transition {result['review']} -> {proposed}")
        if proposed == "verified" and not result.get("provenance"):
            raise ValidationError("review=verified requires named provenance evidence")
        result["review"] = proposed
    if "dispute" in changes:
        proposed = _enum(changes["dispute"], DISPUTES, field="state.dispute")
        if proposed not in _DISPUTE_TRANSITIONS[result["dispute"]]:
            raise ValidationError(
                f"invalid dispute transition {result['dispute']} -> {proposed}; "
                "resolve a contradiction with a new assertion, supersession, or retraction"
            )
        result["dispute"] = proposed
    if "lifecycle" in changes:
        proposed = _enum(changes["lifecycle"], LIFECYCLES, field="state.lifecycle")
        if proposed not in _LIFECYCLE_TRANSITIONS[result["lifecycle"]]:
            raise ValidationError(
                f"invalid lifecycle transition {result['lifecycle']} -> {proposed}"
            )
        if proposed == "superseded" and not result.get("superseded_by"):
            raise ValidationError("use supersede() so a superseded record names its replacement")
        result["lifecycle"] = proposed
    if "sensitivity" in changes:
        result["sensitivity"] = _enum(
            changes["sensitivity"], SENSITIVITIES, field="state.sensitivity"
        )
    if "rights" in changes:
        result["rights"] = _enum(changes["rights"], RIGHTS, field="state.rights")
    if "time" in changes:
        result["time"] = normalize_time(changes["time"])
    result["revision"] = int(result["revision"]) + 1
    result["updated_at"] = validate_timestamp(
        now or utc_now(), field="now", optional=False
    )
    return normalize_record(
        result, now=result["updated_at"], allow_reviewed_model_inference=True
    )


def record_provenance_dependencies(record: Mapping[str, Any]) -> set[str]:
    return {
        entry["source_ref"]
        for entry in record.get("provenance", [])
        if entry.get("source_type") == "record"
    }


def sanitize_references(record: Mapping[str, Any], removed_ids: set[str], *, now: str) -> dict[str, Any]:
    """Remove non-content references to forgotten records from a survivor."""
    result = deepcopy(dict(record))
    result["relations"] = [
        relation for relation in result.get("relations", []) if relation["target_id"] not in removed_ids
    ]
    result["supersedes"] = [value for value in result.get("supersedes", []) if value not in removed_ids]
    result["superseded_by"] = [
        value for value in result.get("superseded_by", []) if value not in removed_ids
    ]
    if result.get("lifecycle") == "superseded" and not result["superseded_by"]:
        # The replacement was forgotten.  Do not silently revive the record; retain
        # the terminal epistemic state as a retraction.
        result["lifecycle"] = "retracted"
    if result != dict(record):
        result["revision"] = int(result["revision"]) + 1
        result["updated_at"] = now
    return normalize_record(result, now=now, allow_reviewed_model_inference=True)
