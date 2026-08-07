"""Portable, persona-neutral delivery envelope for one compiled reminder field."""

from __future__ import annotations

from typing import Any

from .errors import ValidationError
from .model_context import ModelContextError, model_context_text
from .util import (
    canonical_json,
    require_identifier,
    require_sha256,
    require_text,
    sha256_text,
)


DELIVERY_FORMAT = "mind-associative-field-delivery/v1"
DELIVERY_REPRESENTATIONS = frozenset({"canonical", "compact"})
VECTOR_BACKED_MODES = frozenset({"vector_current", "hybrid_current"})


def compile_delivery(
    field: dict[str, Any], *, representation: str
) -> dict[str, Any]:
    """Reduce a neighborhood response to one exact hash-bound transient payload."""

    if representation not in DELIVERY_REPRESENTATIONS:
        raise ValidationError("delivery representation must be canonical or compact")
    try:
        selected = field["representations"][representation]
        membership_digest = require_sha256(
            field["membership_manifest_digest"], "membership_manifest_digest"
        )
        raw_text = require_text(selected["text"], "delivery text", maximum=1_000_000)
        raw_body_sha256 = require_sha256(selected["body_sha256"], "body_sha256")
        raw_utf8_bytes = selected["utf8_bytes"]
        selected_membership_digest = require_sha256(
            selected["membership_manifest_digest"],
            "representation membership_manifest_digest",
        )
    except (KeyError, TypeError):
        raise ValidationError("reminder field is missing a delivery binding") from None
    if (
        not isinstance(raw_utf8_bytes, int)
        or isinstance(raw_utf8_bytes, bool)
        or raw_utf8_bytes < 1
    ):
        raise ValidationError("utf8_bytes must be a positive integer")
    if sha256_text(raw_text) != raw_body_sha256:
        raise ValidationError("delivery text does not match body_sha256")
    if len(raw_text.encode("utf-8")) != raw_utf8_bytes:
        raise ValidationError("delivery text does not match utf8_bytes")
    if selected_membership_digest != membership_digest:
        raise ValidationError("delivery representation changed field membership")

    mode = require_identifier(field.get("mode"), "mode")
    if mode not in VECTOR_BACKED_MODES:
        raise ValidationError("model-facing delivery requires a vector-backed field")
    try:
        text = model_context_text(raw_text)
    except ModelContextError as error:
        raise ValidationError(error.code) from error
    body_sha256 = sha256_text(text)
    utf8_bytes = len(text.encode("utf-8"))

    envelope = {
        "format": DELIVERY_FORMAT,
        "field_id": require_identifier(field.get("field_id"), "field_id"),
        "snapshot_id": require_identifier(field.get("snapshot_id"), "snapshot_id"),
        "scoped_estate_digest": require_sha256(
            field.get("scoped_estate_digest"), "scoped_estate_digest"
        ),
        "membership_manifest_digest": membership_digest,
        "mode": mode,
        "representation": representation,
        "text": text,
        "body_sha256": body_sha256,
        "utf8_bytes": utf8_bytes,
    }
    envelope["delivery_digest"] = sha256_text(canonical_json(envelope))
    return envelope
