"""Deterministic geometry for context-derived capability membranes."""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence

from .errors import ValidationError


POSITIVE_VIEW_KINDS = (
    "transformation",
    "situation",
    "positive_cue",
    "example",
)
BOUNDARY_VIEW_KINDS = (
    "error_or_correction",
    "negative_boundary",
)
ROBUST_NORMAL_SCALE = 1.4826
MIN_SCALE = 1e-12


def normalized(vector: Sequence[float], *, field: str) -> list[float]:
    if not vector:
        raise ValidationError(f"{field} must not be empty")
    values = [float(value) for value in vector]
    if any(not math.isfinite(value) for value in values):
        raise ValidationError(f"{field} must contain only finite values")
    magnitude = math.sqrt(math.fsum(value * value for value in values))
    if magnitude <= 0.0:
        raise ValidationError(f"{field} must not be a zero vector")
    return [value / magnitude for value in values]


def composite_vector(
    vectors_by_kind: Mapping[str, Sequence[float]],
    required_kinds: Sequence[str],
    *,
    field: str,
) -> list[float]:
    if set(vectors_by_kind) != set(required_kinds):
        raise ValidationError(
            f"{field} must contain exactly {','.join(required_kinds)}"
        )
    components = [
        normalized(vectors_by_kind[kind], field=f"{field}.{kind}")
        for kind in required_kinds
    ]
    dimensions = {len(vector) for vector in components}
    if len(dimensions) != 1:
        raise ValidationError(f"{field} vectors must share one dimension")
    averaged = [
        math.fsum(vector[index] for vector in components) / len(components)
        for index in range(len(components[0]))
    ]
    return normalized(averaged, field=f"{field}.composite")


def robust_contrasts(distances: Sequence[float]) -> list[float]:
    if not distances:
        return []
    values = [float(value) for value in distances]
    if any(not math.isfinite(value) for value in values):
        raise ValidationError("contextual distances must be finite")
    center = statistics.median(values)
    mad = statistics.median(abs(value - center) for value in values)
    scale = ROBUST_NORMAL_SCALE * mad
    if scale <= MIN_SCALE:
        scale = statistics.pstdev(values)
    if scale <= MIN_SCALE:
        return [0.0 for _ in values]
    return [(center - value) / scale for value in values]


def complete_neighborhood(
    distances: Sequence[float],
    *,
    contrast_radius: float,
    absolute_radius: float,
    comparison_tolerance: float,
) -> list[int]:
    if not math.isfinite(contrast_radius) or contrast_radius <= 0.0:
        raise ValidationError("contextual contrast radius must be positive")
    if not math.isfinite(absolute_radius) or absolute_radius <= 0.0:
        raise ValidationError("contextual absolute radius must be positive")
    if not math.isfinite(comparison_tolerance) or comparison_tolerance < 0.0:
        raise ValidationError("contextual comparison tolerance must be nonnegative")
    contrasts = robust_contrasts(distances)
    return [
        index
        for index, (distance, contrast) in enumerate(zip(distances, contrasts, strict=True))
        if distance <= absolute_radius + comparison_tolerance
        and contrast + comparison_tolerance >= contrast_radius
    ]
