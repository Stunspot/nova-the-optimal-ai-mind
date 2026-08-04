"""Normative identifiers and bounded MIND Core state vocabularies."""

from __future__ import annotations

APPLICATION_ID = 0x4D494E44  # MIND
SCHEMA_VERSION = 2
PROTOCOL_VERSION = "mind-core/0.2"
RUNTIME_VERSION = "0.2.0"
MAX_CONFORMANCE_LEVEL = "H0"

CAPABILITY_EXPOSURE_POLICIES = frozenset({"public_safe", "agent_private"})

CONFORMANCE_LEVELS = frozenset({"H0", "H1", "H2", "H3"})
COVERAGE_STATES = frozenset(
    {"enforced", "cooperative", "advisory_only", "unobservable"}
)
PHASE1_EFFECTIVE_COVERAGE = frozenset({"advisory_only", "unobservable"})
TIMING_STATES = frozenset({"pre_action", "post_action", "next_turn", "unobservable"})

EVIDENCE_STATES = frozenset(
    {
        "reported",
        "attempted",
        "tool_returned",
        "observed",
        "reconciled",
        "independently_verified",
        "inferred",
        "unavailable",
    }
)

REGISTRATION_STATES = frozenset({"registered", "known_unregistered"})
AVAILABILITY_STATES = frozenset(
    {
        "READY_CURRENT",
        "READ_ONLY_CURRENT",
        "STALE_SNAPSHOT",
        "MOUNT_ABSENT",
        "BACKEND_UNAVAILABLE",
        "DENIED_SCOPE",
        "INTEGRITY_FAILED",
        "PARTIAL",
        "AUTHORITATIVE_EMPTY",
        "BROKER_UNAVAILABLE",
    }
)

LIFECYCLE_STATES: dict[str, tuple[str, ...]] = {
    "custody": (
        "conceived",
        "source-located",
        "canonical-constructed",
        "superseded",
        "retired",
    ),
    "distribution": (
        "not-generated",
        "generated",
        "structurally-verified",
        "released",
    ),
    "host_presence": ("not-observed", "installed", "discovered", "injected"),
    "runtime_use": (
        "selected",
        "resources-loaded",
        "operationally-bound",
        "invoked",
        "receipt-returned",
    ),
    "fitness": (
        "untested",
        "package-qualified",
        "behavior-qualified",
        "fresh-host-qualified",
        "healthy",
        "degraded",
    ),
    "governance": ("candidate", "approved", "deprecated", "blocked"),
}

GLOBAL_LIFECYCLE_AXES = frozenset({"custody", "distribution", "governance"})
SESSION_LIFECYCLE_AXES = frozenset({"host_presence", "runtime_use", "fitness"})

FORBIDDEN_PHASE1_TABLE_TERMS = frozenset(
    {
        "embedding",
        "vector",
        "chunk",
        "prompt_content",
        "person_record",
        "continuity_record",
        "action_gate",
        "operation_admission",
        "raw_payload",
    }
)
