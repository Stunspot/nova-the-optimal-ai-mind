#!/usr/bin/env python3
"""Validate Privacy Redline case invariants without claiming privacy efficacy."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ALLOWED_STATES = {
    "intake", "stabilized", "mapped", "active", "review", "maintained",
    "escalated", "paused-safe",
}
RECEIPT_RESULTS = {"verified", "failed", "partial", "not-tested", "expired"}
EVIDENCE_STATES = {
    "known", "reported", "assumed", "unknown", "current-source-needed", "verified",
}
BANNED_KEY_FRAGMENTS = {
    "password", "passphrase", "recovery_code", "seed_phrase", "private_key",
    "auth_token", "access_token", "secret_key", "full_ssn", "card_number",
}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def walk(value: Any, path: str = "$"):
    if isinstance(value, dict):
        for key, child in value.items():
            yield f"{path}.{key}", key, child
            yield from walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, f"{path}[{index}]")


def validate_case(data: Any) -> list[str]:
    errors: list[str] = []
    require(isinstance(data, dict), "root must be an object", errors)
    if not isinstance(data, dict):
        return errors

    required = {
        "format", "case_id", "title", "status", "purpose", "pressure", "map",
        "ledger", "queue", "receipts", "logbook", "triggers", "last_safe_checkpoint",
        "updated_at",
    }
    for key in sorted(required - data.keys()):
        errors.append(f"missing required field: {key}")

    require(data.get("format") == "privacy-redline/case-v1", "format must be privacy-redline/case-v1", errors)
    require(data.get("status") in ALLOWED_STATES, "status is not an allowed lifecycle state", errors)
    require(isinstance(data.get("case_id"), str) and len(data.get("case_id", "")) >= 3, "case_id must be a non-empty identifier", errors)
    require(isinstance(data.get("title"), str) and bool(data.get("title", "").strip()), "title must be non-empty", errors)
    require(isinstance(data.get("updated_at"), str) and DATE_RE.match(data.get("updated_at", "")) is not None, "updated_at must be YYYY-MM-DD", errors)

    for key in ("map", "ledger", "pressure"):
        require(isinstance(data.get(key), dict), f"{key} must be an object", errors)
    for key in ("queue", "receipts", "logbook", "triggers"):
        require(isinstance(data.get(key), list), f"{key} must be an array", errors)

    for path, key, _ in walk(data):
        normalized = key.lower().replace("-", "_").replace(" ", "_")
        if any(fragment in normalized for fragment in BANNED_KEY_FRAGMENTS):
            errors.append(f"sensitive field is forbidden in ordinary case records: {path}")

    ledger = data.get("ledger") if isinstance(data.get("ledger"), dict) else {}
    for index, assumption in enumerate(ledger.get("assumptions", [])):
        if not isinstance(assumption, dict):
            errors.append(f"ledger.assumptions[{index}] must be an object")
            continue
        require(assumption.get("evidence_state") in EVIDENCE_STATES, f"ledger.assumptions[{index}].evidence_state is invalid", errors)

    for index, redline in enumerate(ledger.get("redlines", [])):
        if not isinstance(redline, dict):
            errors.append(f"ledger.redlines[{index}] must be an object")
            continue
        for field in ("id", "outcome", "owner", "survival_control", "evidence_required"):
            require(bool(redline.get(field)), f"ledger.redlines[{index}].{field} is required", errors)

    for index, item in enumerate(data.get("queue", []) if isinstance(data.get("queue"), list) else []):
        if not isinstance(item, dict):
            errors.append(f"queue[{index}] must be an object")
            continue
        for field in ("id", "action", "broken_failure_path", "horizon", "reversible", "confirmation_gate", "verification", "status"):
            require(field in item and item.get(field) not in (None, ""), f"queue[{index}].{field} is required", errors)
        require(isinstance(item.get("reversible"), bool), f"queue[{index}].reversible must be boolean", errors)

    for index, receipt in enumerate(data.get("receipts", []) if isinstance(data.get("receipts"), list) else []):
        if not isinstance(receipt, dict):
            errors.append(f"receipts[{index}] must be an object")
            continue
        for field in ("control_id", "claim", "owner", "observed_at", "environment", "evidence_type", "result", "residual_exposure", "rollback", "next_review"):
            require(field in receipt and receipt.get(field) not in (None, ""), f"receipts[{index}].{field} is required", errors)
        require(receipt.get("result") in RECEIPT_RESULTS, f"receipts[{index}].result is invalid", errors)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("--json", action="store_true", help="Emit a JSON result")
    args = parser.parse_args()

    try:
        data = json.loads(args.case.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result = {"valid": False, "errors": [f"unable to read valid JSON: {exc}"]}
        print(json.dumps(result, indent=2) if args.json else result["errors"][0])
        return 2

    errors = validate_case(data)
    result = {"valid": not errors, "errors": errors}
    if args.json:
        print(json.dumps(result, indent=2))
    elif errors:
        for error in errors:
            print(f"ERROR: {error}")
    else:
        print("PASS: Privacy Redline case structural invariants satisfied")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

