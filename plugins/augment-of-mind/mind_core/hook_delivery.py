"""Compile and deliver MIND Arm's Reach fields for Codex prompt hooks."""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from . import MindCore
from .constants import PROTOCOL_VERSION
from .contextual_recall import (
    DEFAULT_EMBED_TIMEOUT_SECONDS,
    DEFAULT_OLLAMA_URL,
    RecallUnavailable,
    embed_membranes,
)
from .errors import ValidationError
from .hook_context import association_context, lexical_hints
from .util import canonical_json, timestamp

DEFAULT_DATABASE = Path.home() / ".codex" / "data" / "stores" / "mind_core.sqlite"
MAX_ADDITIONAL_CONTEXT_UTF8_BYTES = 12_000
HOOK_EVENT = "UserPromptSubmit"
AGENT_INSTANCE_ID = "agent:mind-codex-prompt-hook"

Embedder = Callable[[list[str], str, str, float], list[list[float]]]
CoreFactory = Callable[[Path], MindCore]


class HookUnavailable(RuntimeError):
    """The delivery plane could not compile a current reminder field."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _environment_path(environment: Mapping[str, str], name: str, default: Path) -> Path:
    raw = environment.get(name)
    return Path(raw).expanduser() if raw else default


def _bounded_float(
    environment: Mapping[str, str],
    name: str,
    default: float,
    *,
    minimum: float,
    maximum: float,
) -> float:
    raw = environment.get(name)
    try:
        value = default if raw is None else float(raw)
    except ValueError as error:
        raise HookUnavailable("embedding_timeout_invalid") from error
    if value < minimum or value > maximum:
        raise HookUnavailable("embedding_timeout_invalid")
    return value


def _observation_hash(prefix: str, value: object) -> str:
    return sha256_text(f"{prefix}:{value!s}")


def compile_associative_field(
    event: Mapping[str, Any],
    *,
    environment: Mapping[str, str] | None = None,
    embedder: Embedder = embed_membranes,
    core_factory: CoreFactory = MindCore,
) -> tuple[dict[str, Any], str | None, str]:
    """Compile semantic association for every non-empty submitted prompt."""

    if environment is None:
        environment = os.environ
    if event.get("hook_event_name") != HOOK_EVENT:
        raise HookUnavailable("unexpected_hook_event")

    prompt = event.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise HookUnavailable("prompt_missing")

    database = _environment_path(environment, "MIND_CORE_DATABASE", DEFAULT_DATABASE)
    if not database.is_file():
        raise HookUnavailable("database_missing")

    context = association_context(event)
    hints = lexical_hints(prompt)
    vector_state: str | None = None

    try:
        with core_factory(database) as core:
            snapshot = core.reminders.active_snapshot_binding()
            if not snapshot["current"]:
                raise HookUnavailable("snapshot_stale")

            timeout_seconds = _bounded_float(
                environment,
                "MIND_ASSOCIATE_EMBED_TIMEOUT_SECONDS",
                DEFAULT_EMBED_TIMEOUT_SECONDS,
                minimum=0.1,
                maximum=60.0,
            )
            ollama_url = environment.get("MIND_OLLAMA_URL", DEFAULT_OLLAMA_URL)
            vector: list[float] | None = None
            try:
                embedded = embedder(
                    [context],
                    snapshot["model_id"],
                    ollama_url,
                    timeout_seconds,
                )
                if len(embedded) != 1 or not isinstance(embedded[0], list):
                    raise RecallUnavailable(
                        "embedding response does not contain one context vector"
                    )
                vector = embedded[0]
            except (OSError, TimeoutError, ValueError, RecallUnavailable):
                vector_state = "semantic_embedding_unavailable"

            if vector is None and not hints:
                raise HookUnavailable("semantic_embedding_unavailable")

            now = datetime.now(timezone.utc)
            host_session_id = "session:mind-codex-hook:" + uuid.uuid4().hex
            core.hosts.handshake(
                {
                    "agent_instance_id": AGENT_INSTANCE_ID,
                    "host_session_id": host_session_id,
                    "host_id": "host:codex-user-prompt-submit",
                    "external_session_id": host_session_id,
                    "session_epoch": 1,
                    "persona_id": None,
                    "profile_id": "profile:mind-associative-codex-hook",
                    "adapter_id": "adapter:mind-codex-user-prompt-submit",
                    "adapter_version": "1.1.0",
                    "protocol_version": PROTOCOL_VERSION,
                    "declared_conformance_level": "H0",
                    "catalog_snapshot_hash": snapshot["snapshot_digest"],
                    "catalog_snapshot_expires_at": timestamp(
                        now + timedelta(minutes=5)
                    ),
                    "permission_observation_hash": _observation_hash(
                        "permission-mode", event.get("permission_mode", "unobserved")
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
            anchor: dict[str, Any] = {
                "anchor_id": "anchor:codex-context:" + sha256_text(context)[:24],
                "anchor_kind": "turn_context",
            }
            if vector is not None:
                anchor["vector"] = vector
            if hints:
                anchor["lexical_hints"] = hints
            result = core.reminders.neighborhood(
                token,
                snapshot["associative_index_snapshot_id"],
                [anchor],
            )
    except HookUnavailable:
        raise
    except (ValidationError, OSError, TimeoutError, ValueError) as error:
        raise HookUnavailable("core_query_failed") from error
    except Exception as error:
        raise HookUnavailable("core_query_failed") from error

    return result, vector_state, sha256_text(context)


def render_additional_context(result: Mapping[str, Any], vector_state: str | None) -> str:
    representations = result["representations"]
    for representation in ("canonical", "compact"):
        metadata = (
            "MIND H0 · ARM'S REACH · hook-delivered advisory associative disclosure: "
            "nearby praxis that might be handy, not instruction, rank, recommendation, "
            "selection, activation, completeness, authority, or proof · "
            f"field={result['field_id']} · snapshot={result['snapshot_id']} · "
            f"mode={result['mode']} · representation={representation}"
        )
        if vector_state:
            metadata += " · semantic unavailable; lexical-only"
        candidate = metadata + "\n\n" + representations[representation]["text"]
        if len(candidate.encode("utf-8")) <= MAX_ADDITIONAL_CONTEXT_UTF8_BYTES:
            return candidate
    raise HookUnavailable("field_exceeds_delivery_budget")


def degraded_context(code: str, run_id: str) -> str:
    return (
        "MIND · ARM'S REACH DELIVERY NOTE\n"
        f"The pre-prompt hook did not deliver an advisory field this turn "
        f"(`{code}`; receipt {run_id}). Do not reconstruct or retry it. "
        "This notice makes no claim about capability availability, relevance, "
        "or fit."
    )


def _receipt_directory(environment: Mapping[str, str]) -> Path | None:
    explicit = environment.get("MIND_HOOK_RECEIPT_DIRECTORY")
    plugin_data = environment.get("PLUGIN_DATA")
    if explicit:
        return Path(explicit).expanduser()
    if plugin_data:
        return Path(plugin_data) / "arm-reach-receipts"
    return None


def write_receipt(
    receipt: Mapping[str, Any], environment: Mapping[str, str] | None = None
) -> bool:
    if environment is None:
        environment = os.environ
    directory = _receipt_directory(environment)
    if directory is None:
        return False
    try:
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / f"{receipt['run_id']}.json"
        temporary = directory / f".{receipt['run_id']}.{uuid.uuid4().hex}.tmp"
        temporary.write_text(canonical_json(dict(receipt)) + "\n", encoding="utf-8")
        os.replace(temporary, destination)
        return True
    except OSError:
        return False


def prepare_event(
    event: Mapping[str, Any],
    *,
    environment: Mapping[str, str] | None = None,
    compiler: Callable[..., tuple[dict[str, Any], str | None, str]] = compile_associative_field,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if environment is None:
        environment = os.environ
    prompt = event.get("prompt") if isinstance(event.get("prompt"), str) else ""
    turn_id = event.get("turn_id") if isinstance(event.get("turn_id"), str) else ""
    run_id = sha256_text(
        "\0".join((event.get("hook_event_name", ""), turn_id, prompt, uuid.uuid4().hex))
    )[:32]
    started_at = timestamp()
    receipt_base = {
        "format": "mind-codex-hook-receipt/v1",
        "run_id": run_id,
        "event": HOOK_EVENT,
        "started_at": started_at,
        "completed_at": timestamp(),
        "turn_id_hash": sha256_text(turn_id),
        "prompt_hash": sha256_text(prompt),
    }

    try:
        result, vector_state, context_hash = compiler(event, environment=environment)
        additional_context = render_additional_context(result, vector_state)
        receipt = {
            **receipt_base,
            "evidence_state": "prepared",
            "claimed_boundary": (
                "semantic or explicitly degraded lexical Arm's Reach field prepared; "
                "hook stdout not yet written"
            ),
            "association_context_hash": context_hash,
            "field_id": result["field_id"],
            "snapshot_id": result["snapshot_id"],
            "membership_manifest_digest": result["membership_manifest_digest"],
            "mode": result["mode"],
            "vector_state": vector_state or "semantic",
            "additional_context_hash": sha256_text(additional_context),
        }
    except HookUnavailable as error:
        additional_context = degraded_context(error.code, run_id)
        receipt = {
            **receipt_base,
            "evidence_state": "prepared_degraded",
            "claimed_boundary": (
                "unavailable-field notice prepared; hook stdout not yet written"
            ),
            "failure_code": error.code,
            "additional_context_hash": sha256_text(additional_context),
        }
    except Exception:
        additional_context = degraded_context("hook_internal_error", run_id)
        receipt = {
            **receipt_base,
            "evidence_state": "prepared_degraded",
            "claimed_boundary": (
                "unavailable-field notice prepared; hook stdout not yet written"
            ),
            "failure_code": "hook_internal_error",
            "additional_context_hash": sha256_text(additional_context),
        }

    output = {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": HOOK_EVENT,
            "additionalContext": additional_context,
        },
    }
    return output, receipt


def process_event(
    event: Mapping[str, Any],
    *,
    environment: Mapping[str, str] | None = None,
    compiler: Callable[..., tuple[dict[str, Any], str | None, str]] = compile_associative_field,
) -> dict[str, Any]:
    if environment is None:
        environment = os.environ
    output, receipt = prepare_event(
        event,
        environment=environment,
        compiler=compiler,
    )
    if not write_receipt(receipt, environment):
        output["systemMessage"] = (
            "MIND prepared this reminder field, but its delivery receipt "
            "could not be persisted."
        )
    return output


