"""Shared model-facing context contract for delivered capability reminders."""

from __future__ import annotations


MODEL_CONTEXT_HEADER = "**Vector-near semantically related capabilities below**: surfaced from RAG memory for this turn as associative presentation of surveyed capabilities. Consider such reminders as suggested subset of available praxis affordances, not suggested courses of action. Assess contextual relevance and likely utility to task. Integrate with capabilities already present in assembled context. Surveyed memory may extend beyond the current harness."
LEGACY_FIELD_HEADER = (
    "MIND · ARM'S REACH\n"
    "Notice the nearby handles; treat proximity as memory, not verdict. "
    "Open only the transformation the work actually needs."
)


class ModelContextError(ValueError):
    """Raised when a reminder representation cannot become model context."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def model_context_text(value: object) -> str:
    """Apply the model-facing preface to one reminder representation."""

    if not isinstance(value, str):
        raise ModelContextError("field_representation_invalid")
    body = value
    if body.startswith(LEGACY_FIELD_HEADER):
        body = body[len(LEGACY_FIELD_HEADER) :]
    body = body.lstrip("\n")
    return MODEL_CONTEXT_HEADER + ("\n\n" + body if body else "")
