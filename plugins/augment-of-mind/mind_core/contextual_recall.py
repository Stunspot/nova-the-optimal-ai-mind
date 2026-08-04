"""Context-derived associative recall over the active MIND capability estate."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from .constants import PROTOCOL_VERSION
from .contextual_field import contextual_neighborhood
from .contextual_geometry import POSITIVE_VIEW_KINDS, composite_vector
from .core import MindCore
from .errors import ValidationError
from .util import canonical_json, timestamp


DEFAULT_DATABASE = Path.home() / ".codex" / "data" / "stores" / "mind_core.sqlite"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_EMBED_TIMEOUT_SECONDS = 15.0
MAX_MEMBRANES = 6
MAX_SIGIL_CHARACTERS = 64
MAX_FACET_CHARACTERS = 512
MAX_COMPLETE_RING_MEMBERS = 16
MAX_COMPLETE_BATCH_MEMBERS = 48
AGENT_INSTANCE_ID = "agent:nova"
POSITIVE_FACETS = (
    ("shard", "transformation"),
    ("situation", "situation"),
    ("cues", "positive_cue"),
    ("example", "example"),
)

Embedder = Callable[[list[str], str, str, float], list[list[float]]]
CoreFactory = Callable[[Path], MindCore]


class RecallUnavailable(RuntimeError):
    """The contextual recall surface could not compile a current field."""


def _exact_fields(
    value: object,
    *,
    required: frozenset[str],
    optional: frozenset[str] = frozenset(),
    field: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{field} must be an object")
    missing = required - set(value)
    unknown = set(value) - required - optional
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append("missing=" + ",".join(sorted(missing)))
        if unknown:
            details.append("unsupported=" + ",".join(sorted(unknown)))
        raise ValidationError(f"invalid {field}: " + "; ".join(details))
    return value


def _bounded_text(value: object, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be text")
    result = value.strip()
    if not result or len(result) > maximum:
        raise ValidationError(f"{field} must contain between 1 and {maximum} characters")
    if any(ord(character) < 32 and character not in "\t\n\r" for character in result):
        raise ValidationError(f"{field} contains unsupported control characters")
    return result


def validate_membranes(value: object) -> list[dict[str, Any]]:
    """Validate legacy or structured disposable contextual bearings."""

    if not isinstance(value, list) or not value or len(value) > MAX_MEMBRANES:
        raise ValidationError(
            f"membranes must contain between 1 and {MAX_MEMBRANES} items"
        )
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    structured_fields = {"situation", "cues", "example"}
    for index, candidate in enumerate(value):
        item = _exact_fields(
            candidate,
            required=frozenset({"sigil", "shard"}),
            optional=frozenset(structured_fields | {"boundary"}),
            field=f"membranes[{index}]",
        )
        supplied = structured_fields & set(item)
        if supplied and supplied != structured_fields:
            raise ValidationError(
                f"membranes[{index}] must supply situation, cues, and example together"
            )
        structured = supplied == structured_fields
        if item.get("boundary") is not None and not structured:
            raise ValidationError(
                f"membranes[{index}].boundary requires the structured membrane fields"
            )
        sigil = _bounded_text(
            item["sigil"], f"membranes[{index}].sigil", MAX_SIGIL_CHARACTERS
        )
        if not (sigil.startswith("⟨") and sigil.endswith("⟩")):
            raise ValidationError(
                f"membranes[{index}].sigil must be wrapped in ⟨ and ⟩"
            )
        if not sigil[1:-1].strip():
            raise ValidationError(f"membranes[{index}].sigil must contain a bearing")
        parsed: dict[str, Any] = {
            "sigil": sigil,
            "shard": _bounded_text(
                item["shard"], f"membranes[{index}].shard", MAX_FACET_CHARACTERS
            ),
            "_structured": structured,
        }
        for field in ("situation", "cues", "example"):
            parsed[field] = (
                _bounded_text(
                    item[field], f"membranes[{index}].{field}", MAX_FACET_CHARACTERS
                )
                if structured
                else None
            )
        raw_boundary = item.get("boundary")
        parsed["boundary"] = (
            _bounded_text(
                raw_boundary,
                f"membranes[{index}].boundary",
                MAX_FACET_CHARACTERS,
            )
            if raw_boundary is not None
            else None
        )
        identity = hashlib.sha256(
            canonical_json(parsed).encode("utf-8")
        ).hexdigest()
        if identity in seen:
            raise ValidationError("membranes must be distinct")
        seen.add(identity)
        result.append(parsed)
    return result


def embed_membranes(
    texts: list[str], model: str, url: str, timeout_seconds: float
) -> list[list[float]]:
    """Batch-embed contextual bearings through a local Ollama endpoint."""

    body = json.dumps({"model": model, "input": texts}).encode("utf-8")
    request = urllib.request.Request(
        url.rstrip("/") + "/api/embed",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        payload = json.load(response)
    vectors = payload.get("embeddings")
    if (
        not isinstance(vectors, list)
        or len(vectors) != len(texts)
        or any(not isinstance(vector, list) for vector in vectors)
    ):
        raise RecallUnavailable("embedding response does not match the membrane batch")
    return vectors


def _observation_hash(prefix: str, value: object) -> str:
    return hashlib.sha256(f"{prefix}:{value!s}".encode("utf-8")).hexdigest()


def _membrane_id(membrane: dict[str, str | None]) -> str:
    digest = hashlib.sha256(canonical_json(membrane).encode("utf-8")).hexdigest()
    return "membrane:" + digest[:24]


def _cluster_counts(members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(
        (member["cluster"]["handle"], member["cluster"]["name"])
        for member in members
    )
    return [
        {"handle": handle, "name": name, "member_count": count}
        for (handle, name), count in sorted(counts.items())
    ]


def _project_member(member: dict[str, Any]) -> dict[str, Any]:
    return {
        "handle": member["handle"],
        "compact_projection": member["compact_projection"],
        "boundaries": member["boundaries"],
        "cluster": member["cluster"],
        "presentation": member["presentation"],
        "associations": member["associations"],
    }


def _project_ring(
    membrane: dict[str, Any], field: dict[str, Any]
) -> dict[str, Any]:
    members = field["members"]
    direct_count = sum(
        any(path["basis"] != "relation" for path in member["associations"])
        for member in members
    )
    relation_only_count = len(members) - direct_count
    saturated = len(members) > MAX_COMPLETE_RING_MEMBERS
    public_membrane = {
        key: membrane[key]
        for key in ("sigil", "shard", "situation", "cues", "example", "boundary")
        if membrane.get(key) is not None
    }
    result: dict[str, Any] = {
        "membrane_id": _membrane_id(membrane),
        **public_membrane,
        "retrieval_mode": (
            "contextual_composite" if membrane["_structured"] else "legacy_single_shard"
        ),
        "status": "saturated" if saturated else ("empty" if not members else "complete"),
        "member_count": len(members),
        "direct_member_count": direct_count,
        "relation_only_member_count": relation_only_count,
        "clusters": _cluster_counts(members),
        "field_id": field["field_id"],
        "membership_manifest_digest": field["membership_manifest_digest"],
    }
    if saturated:
        result["refinement"] = (
            "Derive one or more narrower contextual membranes from this meaning and "
            "query again; this ring is reported as saturated rather than truncated."
        )
    else:
        result["members"] = [_project_member(member) for member in members]
    return result


def _embedding_plan(
    membranes: list[dict[str, Any]],
) -> tuple[list[str], list[tuple[int, str]]]:
    texts: list[str] = []
    plan: list[tuple[int, str]] = []
    for index, membrane in enumerate(membranes):
        if membrane["_structured"]:
            for field, _view_kind in POSITIVE_FACETS:
                texts.append(str(membrane[field]))
                plan.append((index, field))
            if membrane["boundary"] is not None:
                texts.append(str(membrane["boundary"]))
                plan.append((index, "boundary"))
        else:
            texts.append(str(membrane["shard"]))
            plan.append((index, "shard"))
    return texts, plan


def associate(
    membranes: object,
    *,
    environment: Mapping[str, str] | None = None,
    embedder: Embedder = embed_membranes,
    core_factory: CoreFactory = MindCore,
) -> dict[str, Any]:
    """Compile independent contextual-composite neighborhoods for membranes."""

    if environment is None:
        environment = os.environ
    parsed = validate_membranes(membranes)
    database = Path(
        environment.get("MIND_CORE_DATABASE", str(DEFAULT_DATABASE))
    ).expanduser()
    if not database.is_file():
        raise RecallUnavailable("MIND Core database is unavailable")
    try:
        timeout_seconds = float(
            environment.get(
                "MIND_ASSOCIATE_EMBED_TIMEOUT_SECONDS",
                str(DEFAULT_EMBED_TIMEOUT_SECONDS),
            )
        )
    except ValueError as error:
        raise ValidationError("embedding timeout must be numeric") from error
    if timeout_seconds <= 0 or timeout_seconds > 60:
        raise ValidationError("embedding timeout must be greater than 0 and at most 60")
    ollama_url = environment.get("MIND_OLLAMA_URL", DEFAULT_OLLAMA_URL)

    try:
        with core_factory(database) as core:
            snapshot = core.reminders.active_snapshot_binding()
            if not snapshot["current"]:
                raise RecallUnavailable("active associative snapshot is stale")
            texts, plan = _embedding_plan(parsed)
            embedded = embedder(
                texts,
                snapshot["model_id"],
                ollama_url,
                timeout_seconds,
            )
            if len(embedded) != len(plan):
                raise RecallUnavailable("embedding response does not match the membrane batch")
            vectors: list[dict[str, list[float]]] = [dict() for _ in parsed]
            for (index, field), vector in zip(plan, embedded, strict=True):
                vectors[index][field] = vector

            now = datetime.now(timezone.utc)
            host_session_id = "session:mind-associate:" + uuid.uuid4().hex
            core.hosts.handshake(
                {
                    "agent_instance_id": AGENT_INSTANCE_ID,
                    "host_session_id": host_session_id,
                    "host_id": "host:codex-local-association",
                    "external_session_id": host_session_id,
                    "session_epoch": 1,
                    "persona_id": None,
                    "profile_id": "profile:mind-associative-h0",
                    "adapter_id": "adapter:mind-contextual-association-local",
                    "adapter_version": "2.0.0",
                    "protocol_version": PROTOCOL_VERSION,
                    "declared_conformance_level": "H0",
                    "catalog_snapshot_hash": snapshot["snapshot_digest"],
                    "catalog_snapshot_expires_at": timestamp(
                        now + timedelta(minutes=5)
                    ),
                    "permission_observation_hash": _observation_hash(
                        "permission", "query-only"
                    ),
                    "authentication_observation_hash": _observation_hash(
                        "authentication", "local-process"
                    ),
                    "observed_at": timestamp(now),
                    "expires_at": timestamp(now + timedelta(minutes=5)),
                }
            )
            token = core.reminders.issue_session_capability(
                AGENT_INSTANCE_ID,
                host_session_id,
                exposure_scope="public_and_agent_private",
            )["session_capability"]
            rings: list[dict[str, Any]] = []
            for index, membrane in enumerate(parsed):
                anchor_id = "anchor:" + _membrane_id(membrane).split(":", 1)[1]
                if membrane["_structured"]:
                    positive = composite_vector(
                        {
                            view_kind: vectors[index][field]
                            for field, view_kind in POSITIVE_FACETS
                        },
                        POSITIVE_VIEW_KINDS,
                        field=f"membranes[{index}].positive",
                    )
                    field = contextual_neighborhood(
                        core.reminders,
                        token,
                        snapshot["associative_index_snapshot_id"],
                        anchor_id=anchor_id,
                        positive_vector=positive,
                        boundary_vector=vectors[index].get("boundary"),
                    )
                else:
                    field = core.reminders.neighborhood(
                        token,
                        snapshot["associative_index_snapshot_id"],
                        [
                            {
                                "anchor_id": anchor_id,
                                "anchor_kind": "semantic_membrane",
                                "vector": vectors[index]["shard"],
                            }
                        ],
                    )
                rings.append(_project_ring(membrane, field))
    except (RecallUnavailable, ValidationError):
        raise
    except (OSError, TimeoutError, urllib.error.URLError, ValueError) as error:
        raise RecallUnavailable("local membrane embedding is unavailable") from error
    except Exception as error:
        raise RecallUnavailable("MIND contextual association failed") from error

    complete_member_total = sum(
        ring["member_count"] for ring in rings if ring["status"] != "saturated"
    )
    batch_saturated = complete_member_total > MAX_COMPLETE_BATCH_MEMBERS
    if batch_saturated:
        for ring in rings:
            ring.pop("members", None)
            if ring["status"] != "saturated":
                ring["status"] = "batch_saturated"
        batch_refinement = (
            "Query fewer membranes per call or refine their semantic boundaries; "
            "the complete batch is reported without a partial member sample."
        )
    else:
        batch_refinement = None

    return {
        "format": (
            "mind-contextual-association/v2"
            if any(membrane["_structured"] for membrane in parsed)
            else "mind-contextual-association/v1"
        ),
        "snapshot_id": snapshot["associative_index_snapshot_id"],
        "embedding_profile_id": snapshot["embedding_profile_id"],
        "status": (
            "saturated"
            if batch_saturated or any(ring["status"] == "saturated" for ring in rings)
            else "complete"
        ),
        "rings": rings,
        **({"refinement": batch_refinement} if batch_refinement else {}),
        "claim_boundary": (
            "Each ring declares its retrieval mode. Structured membranes contain every "
            "visible card inside both the robust local-contrast membrane and the active "
            "profile's absolute semantic radius; legacy membranes preserve the earlier "
            "complete all-view radius behavior. Both include explicit one-hop relations. "
            "Positive and boundary geometry are separate for structured membranes, and a "
            "boundary match wins presentation. Saturated rings are counted and withheld "
            "rather than truncated. Proximity is associative recall, not ranking, selection, "
            "activation, fitness, authority, or permission. Sigils are not embedded, and "
            "membranes and raw task text are not persisted by this query surface."
        ),
    }
