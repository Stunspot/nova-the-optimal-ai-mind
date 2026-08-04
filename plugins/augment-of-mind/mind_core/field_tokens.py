"""Opaque authenticated tokens for field-bound progressive disclosure."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from typing import Any

from .errors import NotFoundError
from .util import canonical_json


MAX_VISIBILITY_TOKEN_BYTES = 8192


def _encode_base64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_base64(value: str) -> bytes:
    if not value or "=" in value:
        raise binascii.Error("non-canonical base64url")
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise binascii.Error("non-ASCII base64url") from exc
    padding = "=" * (-len(value) % 4)
    decoded = base64.b64decode(
        encoded + padding.encode("ascii"), altchars=b"-_", validate=True
    )
    if _encode_base64(decoded) != value:
        raise binascii.Error("non-canonical base64url")
    return decoded


def sign_visibility_token(payload: dict[str, Any], key: bytes) -> str:
    body = canonical_json(payload).encode("utf-8")
    signature = hmac.new(key, body, hashlib.sha256).digest()
    return f"{_encode_base64(body)}.{_encode_base64(signature)}"


def verify_visibility_token(token: object, key: bytes) -> dict[str, Any]:
    """Verify one self-issued token without revealing which predicate failed."""

    if not isinstance(token, str) or not token or len(token.encode("utf-8")) > MAX_VISIBILITY_TOKEN_BYTES:
        raise NotFoundError("reminder card is unavailable")
    try:
        encoded_body, encoded_signature = token.split(".", 1)
        body = _decode_base64(encoded_body)
        signature = _decode_base64(encoded_signature)
        expected = hmac.new(key, body, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature mismatch")
        payload = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeError, json.JSONDecodeError, binascii.Error):
        raise NotFoundError("reminder card is unavailable") from None
    if not isinstance(payload, dict):
        raise NotFoundError("reminder card is unavailable")
    return payload
