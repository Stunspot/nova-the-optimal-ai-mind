"""Portable, persona-neutral delivery envelope for one compiled reminder field."""

from __future__ import annotations

from typing import Any

from .errors import ValidationError
from .util import (
    canonical_json,
    require_identifier,
    require_sha256,
    require_text,
    sha256_text,
)


DELIVERY_FORMAT = "mind-associative-field-delivery/v1"
DELIVERY_REPRESENTATIONS = frozenset({"canonical", "compact"})


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
        text = require_text(selected["text"], "delivery text", maximum=1_000_000)
        body_sha256 = require_sha256(selected["body_sha256"], "body_sha256")
        utf8_bytes = selected["utf8_bytes"]
        selected_membership_digest = require_sha256(
            selected["membership_manifest_digest"],
            "representation membership_manifest_digest",
        )
    except (KeyError, TypeError):
        raise ValidationError("reminder field is missing a delivery binding") from None
    if not isinstance(utf8_bytes, int) or isinstance(utf8_bytes, bool) or utf8_bytes < 1:
        raise ValidationError("utf8_bytes must be a positive integer")
    if sha256_text(text) != body_sha256:
        raise ValidationError("delivery text does not match body_sha256")
    if len(text.encode("utf-8")) != utf8_bytes:
        raise ValidationError("delivery text does not match utf8_bytes")
    if selected_membership_digest != membership_digest:
        raise ValidationError("delivery representation changed field membership")

    envelope = {
        "format": DELIVERY_FORMAT,
        "field_id": require_identifier(field.get("field_id"), "field_id"),
        "snapshot_id": require_identifier(field.get("snapshot_id"), "snapshot_id"),
        "scoped_estate_digest": require_sha256(
            field.get("scoped_estate_digest"), "scoped_estate_digest"
        ),
        "membership_manifest_digest": membership_digest,
        "mode": require_identifier(field.get("mode"), "mode"),
        "representation": representation,
        "text": text,
        "body_sha256": body_sha256,
        "utf8_bytes": utf8_bytes,
    }
    envelope["delivery_digest"] = sha256_text(canonical_json(envelope))
    return envelope
