#!/usr/bin/env python3
"""Evaluate a recorded quota snapshot and complete metered test plan."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sys
from typing import Any


FORMAT = "testforge-metered-verification/v1"
PROCEED_OUTCOMES = {"PROCEED"}
MAX_SNAPSHOT_AGE = timedelta(minutes=60)


class PlanError(ValueError):
    """Raised when a capacity snapshot or run plan is malformed."""


def decimal_field(value: Any, field: str, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise PlanError(f"{field} must be a number")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise PlanError(f"{field} must be a number") from error
    if not number.is_finite() or number < 0 or (positive and number == 0):
        qualifier = "positive" if positive else "non-negative"
        raise PlanError(f"{field} must be a finite {qualifier} number")
    return number


def integer_field(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise PlanError(f"{field} must be a positive integer")
    return value


def json_number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)


def timestamp_field(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise PlanError(f"{field} must be a non-empty ISO 8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise PlanError(f"{field} must be a valid ISO 8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PlanError(f"{field} must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlanError(f"{field} must be a non-empty string")
    return value.strip()


def assess(plan: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    if plan.get("format") != FORMAT:
        raise PlanError(f"format must be {FORMAT}")
    provider = nonempty_string(plan.get("provider"), "provider")
    execution_id = nonempty_string(plan.get("execution_id"), "execution_id")
    evidence_source = nonempty_string(plan.get("evidence_source"), "evidence_source")
    capacity_scope = nonempty_string(plan.get("capacity_billing_scope"), "capacity_billing_scope")
    execution_scope = nonempty_string(plan.get("execution_billing_scope"), "execution_billing_scope")
    if capacity_scope != execution_scope:
        raise PlanError("capacity_billing_scope must exactly match execution_billing_scope")

    observed_at = timestamp_field(plan.get("observed_at"), "observed_at")
    valid_until = timestamp_field(plan.get("valid_until"), "valid_until")
    refresh_at = timestamp_field(plan.get("refresh_at"), "refresh_at")
    evaluated_at = now or datetime.now(timezone.utc)
    if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
        raise PlanError("evaluation time must include a UTC offset")
    evaluated_at = evaluated_at.astimezone(timezone.utc)
    if valid_until < observed_at or valid_until - observed_at > MAX_SNAPSHOT_AGE:
        raise PlanError("valid_until must be within 60 minutes after observed_at")
    if refresh_at <= observed_at:
        raise PlanError("refresh_at must follow observed_at")
    if observed_at > evaluated_at:
        raise PlanError("capacity snapshot cannot be future-dated")
    if evaluated_at > valid_until:
        raise PlanError("capacity snapshot has expired")
    if evaluated_at >= refresh_at:
        raise PlanError("capacity snapshot crossed its refresh boundary")

    capacity_status = plan.get("capacity_status")
    if capacity_status not in {"observed", "unavailable", "unknown"}:
        raise PlanError("capacity_status must be observed, unavailable, or unknown")

    reserve = decimal_field(plan.get("reserve_minutes", 0), "reserve_minutes")
    remaining_value = plan.get("remaining_minutes")
    if capacity_status == "observed" and remaining_value is None:
        raise PlanError("remaining_minutes is required when capacity_status is observed")
    remaining = None if remaining_value is None else decimal_field(remaining_value, "remaining_minutes")

    paid_available = plan.get("paid_overage_available")
    if paid_available is not True and paid_available is not False and paid_available is not None:
        raise PlanError("paid_overage_available must be true, false, or null")
    forbidden_authority_fields = {
        "paid_overage_authorization",
        "consumed_authorization_ids",
    } & plan.keys()
    if forbidden_authority_fields:
        raise PlanError(
            "the assessor cannot accept or grant spend authority; remove: "
            + ", ".join(sorted(forbidden_authority_fields))
        )

    planned_runs = plan.get("planned_runs")
    if not isinstance(planned_runs, list) or not planned_runs:
        raise PlanError("planned_runs must be a non-empty list")
    total = Decimal(0)
    run_estimates: list[dict[str, Any]] = []
    for run_index, run in enumerate(planned_runs):
        if not isinstance(run, dict):
            raise PlanError(f"planned_runs[{run_index}] must be an object")
        name = run.get("name")
        jobs = run.get("jobs")
        if not isinstance(name, str) or not name.strip():
            raise PlanError(f"planned_runs[{run_index}].name must be a non-empty string")
        if not isinstance(jobs, list) or not jobs:
            raise PlanError(f"planned_runs[{run_index}].jobs must be a non-empty list")
        run_total = Decimal(0)
        for job_index, job in enumerate(jobs):
            if not isinstance(job, dict):
                raise PlanError(f"{name}.jobs[{job_index}] must be an object")
            prefix = f"{name}.jobs[{job_index}]"
            ceiling = decimal_field(job.get("ceiling_minutes"), f"{prefix}.ceiling_minutes", positive=True)
            count = integer_field(job.get("count", 1), f"{prefix}.count")
            attempts = integer_field(job.get("attempts", 1), f"{prefix}.attempts")
            multiplier = decimal_field(job.get("billing_multiplier", 1), f"{prefix}.billing_multiplier", positive=True)
            run_total += ceiling * count * attempts * multiplier
        total += run_total
        run_estimates.append({"name": name, "estimated_minutes": json_number(run_total)})

    required_with_reserve = total + reserve
    paid_minutes_required = Decimal(0)
    if remaining is not None:
        included_available_after_reserve = max(remaining - reserve, Decimal(0))
        paid_minutes_required = max(total - included_available_after_reserve, Decimal(0))

    if capacity_status == "unavailable":
        outcome = "HOLD_PROVIDER_UNAVAILABLE"
    elif capacity_status == "unknown" or remaining is None:
        outcome = "HOLD_UNKNOWN"
    elif remaining >= required_with_reserve:
        outcome = "PROCEED"
    elif paid_available is True:
        outcome = "AUTHORITY_REQUIRED_PAID"
    elif remaining >= total:
        outcome = "HOLD_RESERVE"
    else:
        outcome = "HOLD_INSUFFICIENT"

    return {
        "format": FORMAT,
        "provider": provider,
        "execution_id": execution_id,
        "observed_at": observed_at.isoformat(),
        "valid_until": valid_until.isoformat(),
        "evidence_source": evidence_source,
        "refresh_at": refresh_at.isoformat(),
        "capacity_billing_scope": capacity_scope,
        "execution_billing_scope": execution_scope,
        "capacity_status": capacity_status,
        "remaining_minutes": None if remaining is None else json_number(remaining),
        "reserve_minutes": json_number(reserve),
        "estimated_minutes": json_number(total),
        "required_with_reserve_minutes": json_number(required_with_reserve),
        "paid_minutes_required": json_number(paid_minutes_required),
        "run_estimates": run_estimates,
        "paid_overage_available": paid_available,
        "paid_overage_authorized": False,
        "outcome": outcome,
        "automatic_invocation_permitted": outcome in PROCEED_OUTCOMES,
        "paid_dispatch_permitted": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path, help="JSON capacity snapshot and expanded run plan")
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.plan.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise PlanError("plan root must be an object")
        result = assess(data)
    except (OSError, json.JSONDecodeError, PlanError) as error:
        print(json.dumps({"ok": False, "error": str(error)}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["automatic_invocation_permitted"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
