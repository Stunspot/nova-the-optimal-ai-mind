#!/usr/bin/env python3
"""Validate the required structure and controlled states of a Beryl IT case."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED = {
    "case_id", "updated_at", "status", "device", "complaint", "custody",
    "evidence", "hypotheses", "tests", "changes", "sources", "verification", "next_move",
}
STATUSES = {
    "reported", "observed", "measured", "retrieved", "assumed", "hypothesis",
    "test-planned", "test-run", "supported", "falsified", "confirmed",
    "change-authorized", "change-applied", "rollback-ready", "verification-passed",
    "verification-failed", "deferred", "referred",
}
DISPOSITIONS = {
    "verified-resolved", "improved-unresolved", "workaround-only", "awaiting-observation",
    "awaiting-authority", "referred", "unsafe/incomplete",
}


def fail(message: str) -> None:
    raise ValueError(message)


def validate(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        fail("top level must be an object")
    missing = sorted(REQUIRED - data.keys())
    if missing:
        fail(f"missing required keys: {', '.join(missing)}")
    if data["status"] not in STATUSES:
        fail(f"invalid status: {data['status']}")
    for key in ("evidence", "hypotheses", "tests", "changes", "sources"):
        if not isinstance(data[key], list):
            fail(f"{key} must be an array")
    verification = data["verification"]
    if not isinstance(verification, dict):
        fail("verification must be an object")
    if verification.get("disposition") not in DISPOSITIONS:
        fail(f"invalid verification disposition: {verification.get('disposition')}")
    if not isinstance(verification.get("original_envelope_retested"), bool):
        fail("verification.original_envelope_retested must be boolean")
    if not isinstance(data["next_move"], dict) or not data["next_move"].get("action"):
        fail("next_move.action must be populated")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_case_file.py <case.json>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    try:
        validate(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL {path}: {exc}", file=sys.stderr)
        return 1
    print(f"PASS {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
