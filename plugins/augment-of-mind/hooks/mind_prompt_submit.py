"""Inject one MIND Arm's Reach field through Codex UserPromptSubmit."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping


PLUGIN_ROOT = Path(os.environ.get("PLUGIN_ROOT", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(PLUGIN_ROOT))

from mind_core import MindCore  # noqa: E402
from mind_core.constants import PROTOCOL_VERSION  # noqa: E402
from mind_core.util import canonical_json, timestamp  # noqa: E402


DEFAULT_DATABASE = Path.home() / ".codex" / "data" / "stores" / "mind_core.sqlite"

MAX_ADDITIONAL_CONTEXT_UTF8_BYTES = 12_000
MAX_LEXICAL_HINTS = 16
MAX_HINT_CHARACTERS = 256
HOOK_EVENT = "UserPromptSubmit"
AGENT_INSTANCE_ID = "agent:mind-codex-prompt-hook"

_TOKEN = re.compile(r"\$?[A-Za-z0-9][A-Za-z0-9_$:+.-]*")


class HookUnavailable(RuntimeError):
    """The delivery plane could not compile a current reminder field."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class HookDeferred(HookUnavailable):
    """Pre-sampling recall correctly deferred until context can shape membranes."""


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _environment_path(environment: Mapping[str, str], name: str, default: Path) -> Path:
    raw = environment.get(name)
    return Path(raw).expanduser() if raw else default


def lexical_hints(text: str) -> list[str]:
    """Retain only explicit identity-shaped cues for pre-sampling recall."""

    originals = _TOKEN.findall(text)[:256]
    candidates: list[str] = []
    for original in originals:
        normalized = original.lower().lstrip("$").strip("._:+-")
        if not normalized:
            continue
        if (
            original.startswith("$")
            or "-" in original
            or ":" in original
            or (original.isupper() and len(original) >= 3)
            or any(character.isdigit() for character in original)
        ):
            candidates.append(normalized)

    result: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate = candidate[:MAX_HINT_CHARACTERS].strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            result.append(candidate)
        if len(result) == MAX_LEXICAL_HINTS:
            break
    return result


def _observation_hash(prefix: str, value: object) -> str:
    return sha256_text(f"{prefix}:{value!s}")


def compile_associative_field(
    event: Mapping[str, Any],
    *,
    environment: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any], str | None]:
    if environment is None:
        environment = os.environ
    prompt = event.get("prompt")
    if event.get("hook_event_name") != HOOK_EVENT:
        raise HookUnavailable("unexpected_hook_event")
    if not isinstance(prompt, str) or not prompt.strip():
        raise HookUnavailable("prompt_missing")

    database = _environment_path(environment, "MIND_CORE_DATABASE", DEFAULT_DATABASE)
    if not database.is_file():
        raise HookUnavailable("database_missing")

    hints = lexical_hints(prompt)
    if not hints:
        raise HookDeferred("contextual_membranes_required")

    try:
        with MindCore(database) as core:
            snapshot = core.reminders.active_snapshot_binding()
            if not snapshot["current"]:
                raise HookUnavailable("snapshot_stale")

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
                    "adapter_version": "1.0.0",
                    "protocol_version": PROTOCOL_VERSION,
                    "declared_conformance_level": "H0",
                    "catalog_snapshot_hash": snapshot["snapshot_digest"],
                    "catalog_snapshot_expires_at": timestamp(now + timedelta(minutes=5)),
                    "permission_observation_hash": _observation_hash(
                        "permission-mode", event.get("permission_mode", "unobserved")
                    ),
                    "authentication_observation_hash": _observation_hash(
                        "authentication", "not-observed"
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
                "anchor_id": "anchor:codex-prompt:" + sha256_text(prompt)[:24],
                "anchor_kind": "explicit_identity",
                "lexical_hints": hints,
            }
            result = core.reminders.neighborhood(
                token,
                snapshot["associative_index_snapshot_id"],
                [anchor],
            )
    except HookUnavailable:
        raise
    except Exception as error:
        raise HookUnavailable("core_query_failed") from error

    return result, None


def render_additional_context(result: Mapping[str, Any], vector_state: str | None) -> str:
    representations = result["representations"]
    for representation in ("canonical", "compact"):
        metadata = (
            "MIND H0 \u00b7 ARM'S REACH \u00b7 additionalContext prepared only; "
            "provider receipt, attention, use, activation, and H1 unobserved \u00b7 "
            f"field={result['field_id']} \u00b7 snapshot={result['snapshot_id']} \u00b7 "
            f"mode={result['mode']} \u00b7 representation={representation}"
        )
        if vector_state:
            metadata += " \u00b7 vector=unavailable; lexical recall remains active"
        candidate = metadata + "\n\n" + representations[representation]["text"]
        if len(candidate.encode("utf-8")) <= MAX_ADDITIONAL_CONTEXT_UTF8_BYTES:
            return candidate
    raise HookUnavailable("field_exceeds_delivery_budget")


def degraded_context(code: str, run_id: str) -> str:
    return (
        "MIND \u00b7 ARM'S REACH UNAVAILABLE\n"
        f"Receipt {run_id} records delivery-plane state `{code}`. "
        "Continue from capabilities exposed by the host and label this turn's "
        "associative reminder field unavailable."
    )


def deferred_context() -> str:
    return (
        "MIND · CONTEXTUAL ASSOCIATION DEFERRED\n"
        "No pre-sampling field was inferred from the raw prompt. Continue through "
        "the host's normal skill-discovery and filesystem skill-loading paths. "
        "Do not treat the unavailable reminder field as evidence that installed "
        "skills are absent."
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
    compiler: Callable[..., tuple[dict[str, Any], str | None]] = compile_associative_field,
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
        result, vector_state = compiler(event, environment=environment)
        additional_context = render_additional_context(result, vector_state)
        receipt = {
            **receipt_base,
            "evidence_state": "prepared",
            "claimed_boundary": (
                "additionalContext response prepared; hook stdout not yet written"
            ),
            "field_id": result["field_id"],
            "snapshot_id": result["snapshot_id"],
            "membership_manifest_digest": result["membership_manifest_digest"],
            "mode": result["mode"],
            "additional_context_hash": sha256_text(additional_context),
        }
    except HookDeferred as error:
        additional_context = deferred_context()
        receipt = {
            **receipt_base,
            "evidence_state": "prepared_deferred",
            "claimed_boundary": (
                "no pre-sampling field inferred; ordinary host skill routing requested; "
                "hook stdout not yet written"
            ),
            "deferred_code": error.code,
            "additional_context_hash": sha256_text(additional_context),
        }
    except HookUnavailable as error:
        additional_context = degraded_context(error.code, run_id)
        receipt = {
            **receipt_base,
            "evidence_state": "prepared_degraded",
            "claimed_boundary": (
                "degraded additionalContext response prepared; "
                "hook stdout not yet written"
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
                "degraded additionalContext response prepared; "
                "hook stdout not yet written"
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
    compiler: Callable[..., tuple[dict[str, Any], str | None]] = compile_associative_field,
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


def _configure_standard_streams() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def main() -> int:
    _configure_standard_streams()
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            raise ValueError("hook input must be an object")
    except (json.JSONDecodeError, ValueError):
        event = {"hook_event_name": HOOK_EVENT, "prompt": "", "turn_id": ""}
    output, receipt = prepare_event(event)
    if not write_receipt(receipt):
        output["systemMessage"] = (
            "MIND prepared this reminder field, but its delivery receipt "
            "could not be persisted."
        )
    try:
        print(canonical_json(output), flush=True)
    except Exception:
        receipt["evidence_state"] = "execution_failed"
        receipt["claimed_boundary"] = "hook stdout write did not complete"
        receipt["failure_code"] = "stdout_write_failed"
        receipt["completed_at"] = timestamp()
        write_receipt(receipt)
        return 1
    degraded = "failure_code" in receipt
    receipt["evidence_state"] = (
        "tool_returned_degraded" if degraded else "tool_returned"
    )
    receipt["claimed_boundary"] = (
        ("degraded " if degraded else "")
        + "additionalContext JSON written and flushed to hook stdout"
    )
    receipt["completed_at"] = timestamp()
    write_receipt(receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
