from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ledgerlib import (
    LedgerBusyError,
    LedgerLockCleanupError,
    LedgerWriteConflictError,
    exclusive_ledger_lock,
    load_with_digest,
    save,
    validate,
)


class PromotionRejected(ValueError):
    """Raised when the requested canon transition is not allowed."""


class PromotionValidationError(ValueError):
    """Raised when source or proposed ledger state is invalid."""


def _objects_contradict(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_claims = set(left.get("claims", []))
    left_contradicts = set(left.get("contradicts", []))
    right_claims = set(right.get("claims", []))
    right_contradicts = set(right.get("contradicts", []))
    return bool((left_claims & right_contradicts) or (left_contradicts & right_claims))


def promote_object(
    ledger_path: Path,
    object_id: str,
    *,
    asserted_by: str,
    at: str | None = None,
) -> dict[str, Any]:
    """Promote one object under an exclusive, digest-checked ledger update."""
    ledger_path = Path(ledger_path)
    with exclusive_ledger_lock(ledger_path):
        data, source_digest = load_with_digest(ledger_path)
        source_errors = validate(data)
        if source_errors:
            raise PromotionValidationError("ledger is invalid before promotion: " + "; ".join(source_errors))

        matches = [
            obj for obj in data.get("objects", [])
            if isinstance(obj, dict) and obj.get("id") == object_id
        ]
        if len(matches) != 1:
            raise PromotionRejected("exactly one matching object is required")
        obj = matches[0]
        if obj.get("status") not in {"proposed", "disputed"}:
            raise PromotionRejected("only proposed or disputed objects may be promoted")
        active_objects = [
            other for other in data.get("objects", [])
            if isinstance(other, dict) and other.get("status") == "active_canon"
        ]
        for index, left in enumerate(active_objects):
            if any(_objects_contradict(left, right) for right in active_objects[index + 1:]):
                raise PromotionRejected("ledger already contains an unresolved active-canon contradiction")
        if any(_objects_contradict(other, obj) for other in active_objects):
            raise PromotionRejected("unresolved active-canon contradiction")

        obj["status"] = "active_canon"
        obj["authority"] = "gm_approved"
        approval = {
            "object_id": object_id,
            "action": "promote_canon",
            "at": at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "asserted_by": asserted_by,
        }
        data.setdefault("approvals", []).append(approval)
        errors = validate(data)
        if errors:
            raise PromotionValidationError("promotion would invalidate ledger: " + "; ".join(errors))

        # The reservation serializes Ludis writers. The digest check also fails
        # closed if an editor or other uncoordinated process changed the source.
        save(ledger_path, data, expected_sha256=source_digest)
        return approval


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote one explicit proposal or dispute to active canon.")
    parser.add_argument("ledger", type=Path)
    parser.add_argument("object_id")
    parser.add_argument("--gm-approved", action="store_true", help="Assert that the GM approved this exact transition.")
    parser.add_argument("--asserted-by", default="local GM via --gm-approved", help="Unauthenticated local operator label.")
    args = parser.parse_args()
    if not args.gm_approved:
        print("FAIL: exact object and --gm-approved required")
        return 2
    try:
        promote_object(args.ledger, args.object_id, asserted_by=args.asserted_by)
    except PromotionValidationError as exc:
        print(f"FAIL: {exc}")
        return 1
    except (PromotionRejected, LedgerBusyError, LedgerLockCleanupError, LedgerWriteConflictError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 2
    print(f"PASS: promoted {args.object_id}")
    print("AUTHORITY: unauthenticated local operator attestation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
