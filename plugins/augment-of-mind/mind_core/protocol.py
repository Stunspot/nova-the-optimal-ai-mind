"""Length-prefixed, bounded JSON framing for the local H0 IPC surface."""

from __future__ import annotations

import json
import struct
from typing import Any, BinaryIO

from .errors import ProtocolError
from .util import canonical_json

MAX_FRAME_BYTES = 1_048_576
_HEADER = struct.Struct(">I")


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_nonstandard_constant(value: str) -> None:
    raise ProtocolError(f"non-standard JSON constant is forbidden: {value}")


def _read_exact(
    stream: BinaryIO,
    length: int,
    *,
    clean_eof_allowed: bool = False,
) -> bytes | None:
    chunks: list[bytes] = []
    remaining = length
    while remaining:
        chunk = stream.read(remaining)
        if chunk in (b"", None):
            if clean_eof_allowed and not chunks:
                return None
            raise ProtocolError("truncated frame")
        if not isinstance(chunk, bytes):
            raise ProtocolError("binary frame stream returned non-bytes data")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_frame(
    stream: BinaryIO, *, maximum_bytes: int = MAX_FRAME_BYTES
) -> dict[str, Any] | None:
    """Read one complete request; return None only for clean end-of-stream."""

    header = _read_exact(stream, _HEADER.size, clean_eof_allowed=True)
    if header is None:
        return None
    (length,) = _HEADER.unpack(header)
    if length == 0:
        raise ProtocolError("empty frames are forbidden")
    if length > maximum_bytes:
        raise ProtocolError(
            f"frame length {length} exceeds maximum {maximum_bytes}"
        )
    payload = _read_exact(stream, length)
    assert payload is not None
    try:
        decoded = payload.decode("utf-8", errors="strict")
        value = json.loads(
            decoded,
            object_pairs_hook=_object_without_duplicates,
            parse_constant=_reject_nonstandard_constant,
        )
    except UnicodeDecodeError as exc:
        raise ProtocolError("frame payload is not valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ProtocolError("frame payload is not valid JSON") from exc
    except RecursionError as exc:
        raise ProtocolError("frame payload exceeds JSON nesting limits") from exc
    if not isinstance(value, dict):
        raise ProtocolError("frame payload must be a JSON object")
    return value


def encode_frame(
    value: dict[str, Any], *, maximum_bytes: int = MAX_FRAME_BYTES
) -> bytes:
    try:
        payload = canonical_json(value).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise ProtocolError("response is not representable as bounded JSON") from exc
    if not payload:
        raise ProtocolError("empty frames are forbidden")
    if len(payload) > maximum_bytes:
        raise ProtocolError(
            f"encoded frame length {len(payload)} exceeds maximum {maximum_bytes}"
        )
    return _HEADER.pack(len(payload)) + payload


def write_frame(
    stream: BinaryIO,
    value: dict[str, Any],
    *,
    maximum_bytes: int = MAX_FRAME_BYTES,
) -> None:
    stream.write(encode_frame(value, maximum_bytes=maximum_bytes))
    stream.flush()
