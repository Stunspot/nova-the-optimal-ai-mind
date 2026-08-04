"""Dependency-free MCP stdio surface for MIND contextual association."""

from __future__ import annotations

import json
import sys
from typing import Any, BinaryIO, Callable

from .contextual_recall import RecallUnavailable, associate
from .errors import ValidationError
from .protocol import MAX_FRAME_BYTES
from .util import canonical_json


SERVER_NAME = "mind-associative-recall"
SERVER_VERSION = "1.1.0"
SUPPORTED_PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")

AssociateHandler = Callable[[object], dict[str, Any]]

ASSOCIATE_TOOL = {
    "name": "associate_capabilities",
    "title": "Associate MIND capabilities",
    "description": (
        "Bring capabilities within arm's reach through contextual association. "
        "The existing sigil and semantic shard contract remains valid. For the "
        "higher-discrimination composite path, also supply situation, cues, and "
        "example as genuinely distinct facets; supply boundary only when the live "
        "meaning itself activates a stop, correction, or prohibited condition. "
        "The ad hoc sigil is only a mental handle and is never embedded. Use separate "
        "membranes for separate meanings. Returned fields are complete threshold "
        "neighborhoods and reminders, never rankings or permission to activate anything."
    ),
    "inputSchema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["membranes"],
        "properties": {
            "membranes": {
                "type": "array",
                "minItems": 1,
                "maxItems": 6,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["sigil", "shard"],
                    "properties": {
                        "sigil": {
                            "type": "string",
                            "minLength": 3,
                            "maxLength": 64,
                            "description": (
                                "A contextual sigil wrapped in ⟨ and ⟩, derived ad hoc "
                                "for this task and never embedded or chosen from a vocabulary."
                            ),
                        },
                        "shard": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 512,
                            "description": "The specific before-to-after transformation.",
                        },
                        "situation": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 512,
                            "description": "Optional composite facet: discriminating circumstances.",
                        },
                        "cues": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 512,
                            "description": "Optional composite facet: concrete high-signal phrases.",
                        },
                        "example": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 512,
                            "description": "Optional composite facet: one distinctive concrete instance.",
                        },
                        "boundary": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 512,
                            "description": (
                                "Optional active stop, correction, or prohibited condition; "
                                "valid only with all three composite facets."
                            ),
                        },
                    },
                },
            }
        },
    },
}


def _error(request_id: object, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _result(request_id: object, result: object) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _tool_result(payload: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "content": [{"type": "text", "text": canonical_json(payload)}],
        "structuredContent": payload,
    }
    if is_error:
        result["isError"] = True
    return result


class MindMcpServer:
    """Small MCP request router with one contextual recall tool."""

    def __init__(self, associate_handler: AssociateHandler | None = None) -> None:
        self.associate_handler = associate_handler or (
            lambda membranes: associate(membranes)
        )
        self.initialized = False

    @staticmethod
    def _valid_request_id(value: object) -> bool:
        return value is None or (
            isinstance(value, (str, int)) and not isinstance(value, bool)
        )

    def handle(self, request: object) -> dict[str, Any] | None:
        if not isinstance(request, dict):
            return _error(None, -32600, "request must be an object")
        request_id = request.get("id")
        notification = "id" not in request
        if not notification and not self._valid_request_id(request_id):
            return _error(None, -32600, "invalid request id")
        if request.get("jsonrpc") != "2.0":
            return None if notification else _error(request_id, -32600, "invalid request")
        method = request.get("method")
        if not isinstance(method, str):
            return None if notification else _error(request_id, -32600, "method must be text")
        params = request.get("params", {})
        if not isinstance(params, dict):
            return None if notification else _error(request_id, -32602, "params must be an object")

        if method == "initialize":
            if notification:
                return None
            requested = params.get("protocolVersion")
            protocol = requested if requested in SUPPORTED_PROTOCOLS else SUPPORTED_PROTOCOLS[0]
            self.initialized = True
            return _result(
                request_id,
                {
                    "protocolVersion": protocol,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                    "instructions": (
                        "Derive contextual membrane facets only after reading the live task. "
                        "Treat every returned field as associative recall rather than selection."
                    ),
                },
            )
        if method in {
            "notifications/initialized",
            "notifications/cancelled",
            "notifications/roots/list_changed",
        }:
            return None
        if notification:
            return None
        if method == "ping":
            return _result(request_id, {})
        if method == "tools/list":
            return _result(request_id, {"tools": [ASSOCIATE_TOOL]})
        if method == "tools/call":
            if not self.initialized:
                return _error(request_id, -32002, "server is not initialized")
            unknown = set(params) - {"name", "arguments", "_meta"}
            if unknown or not isinstance(params.get("name"), str):
                return _error(request_id, -32602, "invalid tool call parameters")
            if params["name"] != ASSOCIATE_TOOL["name"]:
                return _error(request_id, -32602, "unknown tool")
            arguments = params.get("arguments", {})
            if not isinstance(arguments, dict) or set(arguments) != {"membranes"}:
                return _error(request_id, -32602, "arguments must contain only membranes")
            try:
                payload = self.associate_handler(arguments["membranes"])
            except (ValidationError, RecallUnavailable) as error:
                return _result(
                    request_id,
                    _tool_result(
                        {
                            "format": "mind-contextual-association-error/v1",
                            "error": str(error),
                            "claim_boundary": "No associative field was returned.",
                        },
                        is_error=True,
                    ),
                )
            except Exception:
                return _result(
                    request_id,
                    _tool_result(
                        {
                            "format": "mind-contextual-association-error/v1",
                            "error": "MIND contextual association failed",
                            "claim_boundary": "No associative field was returned.",
                        },
                        is_error=True,
                    ),
                )
            return _result(request_id, _tool_result(payload))
        return _error(request_id, -32601, "method not found")


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_nonstandard_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def serve(
    reader: BinaryIO,
    writer: BinaryIO,
    *,
    server: MindMcpServer | None = None,
) -> int:
    """Serve newline-delimited MCP JSON-RPC until clean EOF."""

    active = server or MindMcpServer()
    while True:
        line = reader.readline(MAX_FRAME_BYTES + 1)
        if line in (b"", None):
            return 0
        if not line.strip():
            continue
        if len(line) > MAX_FRAME_BYTES:
            writer.write(
                (canonical_json(_error(None, -32700, "request exceeds maximum size")) + "\n").encode("utf-8")
            )
            writer.flush()
            return 2
        try:
            request = json.loads(
                line.decode("utf-8", errors="strict"),
                object_pairs_hook=_object_without_duplicates,
                parse_constant=_reject_nonstandard_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):
            response = _error(None, -32700, "invalid JSON")
        else:
            response = active.handle(request)
        if response is not None:
            writer.write((canonical_json(response) + "\n").encode("utf-8"))
            writer.flush()


def main() -> int:
    return serve(sys.stdin.buffer, sys.stdout.buffer)


if __name__ == "__main__":
    raise SystemExit(main())
