"""Query-only JSON-RPC-like service for MIND Core."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, BinaryIO, Callable

from .constants import MAX_CONFORMANCE_LEVEL, PROTOCOL_VERSION, SCHEMA_VERSION
from .core import MindCore
from .errors import (
    ConflictError,
    MindCoreError,
    NotFoundError,
    ProtocolError,
    ScopeError,
    ValidationError,
)
from .protocol import read_frame, write_frame


@dataclass(frozen=True)
class _Method:
    handler: Callable[..., Any]
    required: frozenset[str]
    optional: frozenset[str] = frozenset()


class QueryService:
    """Expose bounded Core reads without event ingest or action dispatch."""

    def __init__(self, core: MindCore):
        self.core = core
        self.methods: dict[str, _Method] = {
            "core.status": _Method(core.query_status, frozenset()),
            "core.schema": _Method(
                lambda: {"tables": core.schema_tables()}, frozenset()
            ),
            "host.session": _Method(
                core.hosts.session,
                frozenset({"host_session_id", "agent_instance_id"}),
                frozenset({"require_fresh"}),
            ),
            "coverage.get": _Method(
                core.hosts.coverage,
                frozenset({"host_session_id", "agent_instance_id"}),
            ),
            "estate.resolve": _Method(
                core.reminders.estate_resolve,
                frozenset({"handle_or_alias"}),
                frozenset({"session_capability"}),
            ),
            "estate.capability": _Method(
                core.reminders.estate_capability,
                frozenset({"capability_id"}),
                frozenset({"session_capability"}),
            ),
            "mount.catalog": _Method(
                core.mounts.catalog,
                frozenset({"host_session_id", "agent_instance_id"}),
            ),
            "mount.observation": _Method(
                core.mounts.observation,
                frozenset(
                    {"mount_id", "host_session_id", "agent_instance_id"}
                ),
            ),
            "receipt.get": _Method(
                core.receipts.get,
                frozenset({"receipt_id"}),
                frozenset({"agent_instance_id", "host_session_id"}),
            ),
            "reminder.neighborhood": _Method(
                core.reminders.neighborhood,
                frozenset({"session_capability", "snapshot_id", "anchors"}),
            ),
            "reminder.card": _Method(
                core.reminders.card,
                frozenset(
                    {
                        "session_capability",
                        "field_id",
                        "membership_manifest_digest",
                        "visibility_token",
                    }
                ),
            ),
        }

    @staticmethod
    def _valid_request_id(value: object) -> bool:
        return value is None or (
            isinstance(value, (str, int)) and not isinstance(value, bool)
        )

    @staticmethod
    def _meta(params: dict[str, Any] | None = None) -> dict[str, Any]:
        values = params or {}
        return {
            "protocol_version": PROTOCOL_VERSION,
            "schema_version": SCHEMA_VERSION,
            "maximum_host_conformance": MAX_CONFORMANCE_LEVEL,
            "scope": {
                "agent_instance_id": values.get("agent_instance_id"),
                "host_session_id": values.get("host_session_id"),
            },
            "claim_boundary": (
                "H0 query result only; no automatic event or reminder-field delivery, "
                "capability activation, result interception, or dispatch gating is claimed."
            ),
        }

    def _error(
        self,
        request_id: str | int | None,
        code: int,
        message: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
            "meta": self._meta(params),
        }

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        request_id = request.get("id")
        if not self._valid_request_id(request_id):
            return self._error(None, -32600, "invalid request id")
        unknown_envelope = set(request) - {"jsonrpc", "id", "method", "params"}
        if unknown_envelope:
            return self._error(
                request_id,
                -32600,
                "unsupported request fields: " + ",".join(sorted(unknown_envelope)),
            )
        if request.get("jsonrpc") != "2.0" or "id" not in request:
            return self._error(request_id, -32600, "invalid request envelope")
        method_name = request.get("method")
        if not isinstance(method_name, str):
            return self._error(request_id, -32600, "method must be text")
        method = self.methods.get(method_name)
        if method is None:
            return self._error(request_id, -32601, "method not found")
        params = request.get("params", {})
        if not isinstance(params, dict):
            return self._error(request_id, -32602, "params must be an object")
        missing = method.required - set(params)
        unknown = set(params) - method.required - method.optional
        if missing or unknown:
            details: list[str] = []
            if missing:
                details.append("missing=" + ",".join(sorted(missing)))
            if unknown:
                details.append("unsupported=" + ",".join(sorted(unknown)))
            return self._error(
                request_id,
                -32602,
                "invalid params: " + "; ".join(details),
                params=params,
            )
        try:
            result = method.handler(**params)
        except NotFoundError as exc:
            return self._error(request_id, -32004, str(exc), params=params)
        except ScopeError as exc:
            return self._error(request_id, -32003, str(exc), params=params)
        except ConflictError as exc:
            return self._error(request_id, -32009, str(exc), params=params)
        except ValidationError as exc:
            return self._error(request_id, -32602, str(exc), params=params)
        except MindCoreError as exc:
            return self._error(request_id, -32000, str(exc), params=params)
        except Exception:
            return self._error(request_id, -32603, "internal error", params=params)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
            "meta": self._meta(params),
        }


def serve(
    core: MindCore,
    reader: BinaryIO,
    writer: BinaryIO,
) -> int:
    """Serve complete frames until EOF; terminate after an unsafe frame boundary."""

    service = QueryService(core)
    while True:
        try:
            request = read_frame(reader)
        except ProtocolError as exc:
            write_frame(writer, service._error(None, -32700, str(exc)))
            return 2
        if request is None:
            return 0
        write_frame(writer, service.handle(request))
