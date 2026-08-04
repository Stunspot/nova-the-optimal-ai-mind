"""Deterministic geometry and lexical predicates for associative disclosure."""

from __future__ import annotations

import math
import re
import struct
import unicodedata
from collections.abc import Sequence

from .errors import ValidationError


MAX_VECTOR_DIMENSIONS = 4096
MAX_LEXICAL_HINT_CHARACTERS = 256
LEXICAL_PROFILE_ID = "nfkc-casefold-contiguous-token-v1"
LEXICAL_TOKEN_PATTERN = r"\w+(?:[.:/-]\w+)*"
LEXICAL_UNICODE_TOKEN_GRAMMAR = (
    rf"{LEXICAL_TOKEN_PATTERN} under Python Unicode semantics"
)
LEXICAL_CUE_MEMBERSHIP_CONTRACT = (
    "Complete contiguous hint-token sequence; exhaustive over visible approved surfaces."
)

_TOKEN_PATTERN = re.compile(LEXICAL_TOKEN_PATTERN, re.UNICODE)


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{field} must contain only finite numbers")
    result = float(value)
    if not math.isfinite(result):
        raise ValidationError(f"{field} must contain only finite numbers")
    return result


def coerce_float32_vector(
    value: object,
    *,
    dimensions: int,
    field: str,
) -> tuple[float, ...]:
    """Validate a vector and round every component to the stored float32 oracle."""

    if (
        not isinstance(dimensions, int)
        or isinstance(dimensions, bool)
        or dimensions < 1
        or dimensions > MAX_VECTOR_DIMENSIONS
    ):
        raise ValidationError(
            f"dimensions must be between 1 and {MAX_VECTOR_DIMENSIONS}"
        )
    if not isinstance(value, (list, tuple)):
        raise ValidationError(f"{field} must be an array of {dimensions} numbers")
    if len(value) != dimensions:
        raise ValidationError(f"{field} must contain exactly {dimensions} numbers")
    source = tuple(
        _finite_number(component, f"{field}[{index}]")
        for index, component in enumerate(value)
    )
    try:
        packed = struct.pack(f"<{dimensions}f", *source)
        rounded = struct.unpack(f"<{dimensions}f", packed)
    except (OverflowError, struct.error) as exc:
        raise ValidationError(f"{field} is not representable as float32") from exc
    if not all(math.isfinite(component) for component in rounded):
        raise ValidationError(f"{field} is not representable as finite float32")
    if math.fsum(component * component for component in rounded) == 0.0:
        raise ValidationError(f"{field} must have non-zero norm")
    return tuple(rounded)


def pack_float32_vector(vector: Sequence[float]) -> bytes:
    if not vector:
        raise ValidationError("vector must not be empty")
    return struct.pack(f"<{len(vector)}f", *vector)


def unpack_float32_vector(
    payload: object,
    *,
    dimensions: int,
    field: str = "stored_vector",
) -> tuple[float, ...]:
    if not isinstance(payload, bytes) or len(payload) != dimensions * 4:
        raise ValidationError(
            f"{field} must contain exactly {dimensions} little-endian float32 values"
        )
    values = struct.unpack(f"<{dimensions}f", payload)
    if not all(math.isfinite(component) for component in values):
        raise ValidationError(f"{field} contains a non-finite component")
    if math.fsum(component * component for component in values) == 0.0:
        raise ValidationError(f"{field} must have non-zero norm")
    return tuple(values)


def exact_cosine_distance(
    left: Sequence[float], right: Sequence[float]
) -> float:
    """Reference cosine distance with stable dimension order and fsum accumulation."""

    if len(left) != len(right) or not left:
        raise ValidationError("cosine vectors must have equal non-zero dimensions")
    dot = math.fsum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(math.fsum(component * component for component in left))
    right_norm = math.sqrt(math.fsum(component * component for component in right))
    if left_norm == 0.0 or right_norm == 0.0:
        raise ValidationError("cosine vectors must have non-zero norm")
    cosine = dot / (left_norm * right_norm)
    cosine = min(1.0, max(-1.0, cosine))
    return 1.0 - cosine


def within_radius(distance: float, radius: float, tolerance: float) -> bool:
    values = (distance, radius, tolerance)
    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in values):
        raise ValidationError("distance, radius, and tolerance must be finite")
    if radius < 0.0 or radius > 2.0:
        raise ValidationError("radius must be between 0 and 2")
    if tolerance < 0.0 or tolerance > 0.001:
        raise ValidationError("comparison_tolerance must be between 0 and 0.001")
    return distance <= radius + tolerance


def normalize_lexical(
    value: object,
    field: str = "lexical_value",
    *,
    maximum: int = 4096,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} must be non-empty text")
    if len(value) > maximum:
        raise ValidationError(f"{field} exceeds {maximum} characters")
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def lexical_tokens(
    value: object,
    field: str = "lexical_value",
    *,
    maximum: int = 4096,
) -> tuple[str, ...]:
    normalized = normalize_lexical(value, field, maximum=maximum)
    tokens = tuple(_TOKEN_PATTERN.findall(normalized))
    if not tokens:
        raise ValidationError(f"{field} contains no searchable tokens")
    return tokens


def contains_contiguous_tokens(
    haystack: Sequence[str], needle: Sequence[str]
) -> bool:
    if not needle or len(needle) > len(haystack):
        return False
    width = len(needle)
    target = tuple(needle)
    return any(
        tuple(haystack[index : index + width]) == target
        for index in range(len(haystack) - width + 1)
    )
