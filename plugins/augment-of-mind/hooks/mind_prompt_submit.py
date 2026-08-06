"""Inject one MIND Arm's Reach field through Codex UserPromptSubmit."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PLUGIN_ROOT = Path(os.environ.get("PLUGIN_ROOT", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(PLUGIN_ROOT))

from mind_core.hook_delivery import HOOK_EVENT, prepare_event, write_receipt  # noqa: E402
from mind_core.util import canonical_json, timestamp  # noqa: E402


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
