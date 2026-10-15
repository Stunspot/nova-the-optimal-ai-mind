#!/usr/bin/env python3
"""Validate CD Agent Swarm Plan v1 structure and orchestration invariants."""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
from itertools import combinations
from pathlib import Path
from typing import Any


REQUIRED_TOP = {
    "format",
    "plan_id",
    "updated_at",
    "mission",
    "acceptance",
    "authority",
    "regime",
    "admission_basis",
    "root",
    "workers",
    "budgets",
    "merge",
    "status",
    "next_move",
}
OPTIONAL_TOP = {"outcome"}
REGIMES = {"direct", "enlist", "assemble", "chain", "recover"}
PLAN_STATUSES = {
    "planned",
    "active",
    "recovering",
    "awaiting_evidence",
    "awaiting_authority",
    "closed",
    "cancelled",
}
WORKER_STATUSES = {
    "planned",
    "dispatched",
    "working",
    "returned",
    "reconciled",
    "failed",
    "interrupted",
    "cancelled",
    "closed",
}
TERMINAL_WORKER_STATUSES = {"reconciled", "failed", "interrupted", "cancelled", "closed"}
ACCEPTED_DEPENDENCY_STATUSES = {"reconciled"}
STARTED_WORKER_STATUSES = {"dispatched", "working", "returned", "reconciled"}
RUNNING_WORKER_STATUSES = {"dispatched", "working"}
OPEN_WRITE_STATUSES = WORKER_STATUSES - {"reconciled", "closed"}
TERMINAL_CLOSURE_NEXT_MOVES = {"none", "no further action", "closed", "cancelled"}
EVIDENCE_PLACEHOLDER_IDENTITIES = {"none", "n a", "not required", "no evidence required", "not applicable"}


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any, *, nonempty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (not nonempty or bool(value))
        and all(_nonempty_string(item) for item in value)
    )


def _surface_identity(value: str) -> str:
    normalized = posixpath.normpath(value.strip().replace("\\", "/"))
    components = [
        component if component in {"", ".", ".."} else component.rstrip(" .")
        for component in normalized.split("/")
    ]
    return posixpath.normpath("/".join(components)).casefold()


def _evidence_identity(value: str) -> str:
    return re.sub(r"[\W_]+", " ", value.strip().casefold()).strip()


def _terminal_next_move_is_valid(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized.endswith("."):
        normalized = normalized[:-1].rstrip()
    if normalized in TERMINAL_CLOSURE_NEXT_MOVES:
        return True
    return bool(re.fullmatch(r"re(?:-|\s)?entry only if \S(?:.*\S)?", normalized))


def _authority_identity(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _concrete_evidence(value: Any) -> bool:
    return _string_list(value, nonempty=True) and all(
        _evidence_identity(item) not in EVIDENCE_PLACEHOLDER_IDENTITIES for item in value
    )


def _surfaces_overlap(left: str, right: str) -> bool:
    if left == right:
        return True
    # Dot reserves this workspace; absolute roots and opaque external-object names
    # still require a consistent owner-assigned namespace.
    if left == "." or right == ".":
        return True
    return left.startswith(right.rstrip("/") + "/") or right.startswith(left.rstrip("/") + "/")


def _holds_write(worker: dict[str, Any]) -> bool:
    if worker["status"] == "reconciled":
        return False
    if worker["status"] in TERMINAL_WORKER_STATUSES:
        if worker["started"] is False:
            return False
        if worker["readback_state"] == "reconciled":
            return False
    return True


def _validate_outcome(plan: dict[str, Any], workers: dict[str, Any], errors: list[str]) -> None:
    outcome = plan["outcome"]
    if not isinstance(outcome, dict) or set(outcome) != {"state", "checks", "unresolved"}:
        errors.append("outcome must contain only state, checks, and unresolved")
        return
    state = outcome["state"] if isinstance(outcome["state"], str) else None
    if state not in {"unverified", "partial", "accepted", "cancelled"}:
        errors.append("outcome.state is invalid")
    if not _string_list(outcome["unresolved"]):
        errors.append("outcome.unresolved must be an array of non-empty strings")
    if not isinstance(outcome["checks"], list):
        errors.append("outcome.checks must be an array")
        return
    criteria = plan["acceptance"] if _string_list(plan["acceptance"]) else []
    seen = []
    passing = []
    for index, check in enumerate(outcome["checks"]):
        label = f"outcome.checks[{index}]"
        if not isinstance(check, dict) or set(check) != {"criterion", "result", "evidence"}:
            errors.append(f"{label} must contain only criterion, result, and evidence")
            continue
        criterion = check["criterion"]
        result = check["result"] if isinstance(check["result"], str) else None
        if not _nonempty_string(criterion) or criterion not in criteria:
            errors.append(f"{label}.criterion must match a plan acceptance criterion exactly")
        elif criterion in seen:
            errors.append(f"{label}.criterion duplicates an earlier check")
        else:
            seen.append(criterion)
        if result not in {"passed", "failed", "not-run"}:
            errors.append(f"{label}.result must be passed, failed, or not-run")
        if not _string_list(check["evidence"]):
            errors.append(f"{label}.evidence must be an array of non-empty strings")
        elif result in {"passed", "failed"} and not _concrete_evidence(check["evidence"]):
            errors.append(f"{label} observed result requires concrete evidence references")
        if result == "passed":
            passing.append(criterion)
    if state == "accepted":
        if plan["status"] != "closed":
            errors.append("accepted outcome requires closed control state")
        if outcome["unresolved"]:
            errors.append("accepted outcome cannot have unresolved issues")
        if len(passing) != len(criteria) or any(c not in passing for c in criteria):
            errors.append("accepted outcome requires one passing check for every acceptance criterion")
        for worker_id, worker in workers.items():
            if worker["write_surfaces"] and _holds_write(worker):
                errors.append(f"accepted outcome has unknown or unresolved writes: {worker_id}")


def declared_outcome(plan: dict[str, Any]) -> str:
    outcome = plan.get("outcome")
    return outcome.get("state", "unverified") if isinstance(outcome, dict) else "unverified"


def validate(plan: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ["root must be a JSON object"]

    missing = sorted(REQUIRED_TOP - set(plan))
    extra = sorted(set(plan) - REQUIRED_TOP - OPTIONAL_TOP)
    if missing:
        errors.append("missing top-level fields: " + ", ".join(missing))
    if extra:
        errors.append("unexpected top-level fields: " + ", ".join(extra))
    if errors:
        return errors

    if plan["format"] != "cd-agent-swarm-plan/v1":
        errors.append("format must be cd-agent-swarm-plan/v1")
    for field in ("plan_id", "updated_at", "mission", "admission_basis", "next_move"):
        if not _nonempty_string(plan[field]):
            errors.append(f"{field} must be a non-empty string")
    if not _string_list(plan["acceptance"], nonempty=True):
        errors.append("acceptance must be a non-empty array of non-empty strings")
    regime = plan["regime"] if isinstance(plan["regime"], str) else None
    plan_status = plan["status"] if isinstance(plan["status"], str) else None
    if regime not in REGIMES:
        errors.append("regime is invalid")
    if plan_status not in PLAN_STATUSES:
        errors.append("status is invalid")

    authority = plan["authority"]
    allowed_authority: set[str] = set()
    if not isinstance(authority, dict) or set(authority) != {"allowed", "reserved", "sensitive_material"}:
        errors.append("authority must contain only allowed, reserved, and sensitive_material")
    elif not _string_list(authority["allowed"], nonempty=True) or not _string_list(authority["reserved"]) or not isinstance(authority["sensitive_material"], str):
        errors.append("authority fields have invalid types")
    else:
        allowed_authority = {_authority_identity(item) for item in authority["allowed"]}
        overlap = allowed_authority & {_authority_identity(item) for item in authority["reserved"]}
        if overlap:
            errors.append("authority.allowed conflicts with authority.reserved: " + ", ".join(sorted(overlap)))

    root = plan["root"]
    if not isinstance(root, dict) or set(root) != {"owner", "work"} or not all(_nonempty_string(root.get(k)) for k in ("owner", "work")):
        errors.append("root must contain non-empty owner and work strings")

    budgets = plan["budgets"]
    if not isinstance(budgets, dict) or set(budgets) != {"concurrency_limit", "model_policy", "stop_condition"}:
        errors.append("budgets must contain only concurrency_limit, model_policy, and stop_condition")
    else:
        if not isinstance(budgets["concurrency_limit"], int) or isinstance(budgets["concurrency_limit"], bool) or budgets["concurrency_limit"] < 1:
            errors.append("budgets.concurrency_limit must be an integer >= 1")
        for field in ("model_policy", "stop_condition"):
            if not _nonempty_string(budgets[field]):
                errors.append(f"budgets.{field} must be a non-empty string")

    merge = plan["merge"]
    if not isinstance(merge, dict) or set(merge) != {"owner", "method", "indispensable_gates"}:
        errors.append("merge must contain only owner, method, and indispensable_gates")
    elif not _nonempty_string(merge["owner"]) or not _nonempty_string(merge["method"]) or not _string_list(merge["indispensable_gates"], nonempty=True):
        errors.append("merge fields have invalid types or empty values")

    workers = plan["workers"]
    if not isinstance(workers, list):
        errors.append("workers must be an array")
        return errors

    if regime == "direct" and workers:
        errors.append("direct regime must not declare workers")
    if regime is not None and regime != "direct" and not workers:
        errors.append("non-direct regime must declare at least one worker")
    if regime == "enlist" and len(workers) != 1:
        errors.append("enlist regime must declare exactly one worker")
    if regime in {"assemble", "chain"} and len(workers) < 2:
        errors.append(f"{regime} regime must declare at least two workers")

    required_worker = {
        "id", "objective", "deliverable", "depends_on", "read_surfaces",
        "write_surfaces", "authority", "evidence_required", "status", "return_condition",
    }
    ids: list[str] = []
    worker_by_id: dict[str, dict[str, Any]] = {}
    for index, worker in enumerate(workers):
        label = f"workers[{index}]"
        if not isinstance(worker, dict):
            errors.append(f"{label} must be an object")
            continue
        missing_worker = sorted(required_worker - set(worker))
        extra_worker = sorted(set(worker) - required_worker - {"started", "output", "write_readback"})
        if missing_worker:
            errors.append(f"{label} missing fields: {', '.join(missing_worker)}")
        if extra_worker:
            errors.append(f"{label} unexpected fields: {', '.join(extra_worker)}")
        if missing_worker:
            continue
        for field in ("id", "objective", "deliverable", "return_condition"):
            if not _nonempty_string(worker[field]):
                errors.append(f"{label}.{field} must be a non-empty string")
        for field in ("depends_on", "read_surfaces", "write_surfaces"):
            if not _string_list(worker[field]):
                errors.append(f"{label}.{field} must be an array of non-empty strings")
        if not _string_list(worker["evidence_required"], nonempty=True):
            errors.append(f"{label}.evidence_required must be a non-empty array of strings")
        else:
            placeholders = sorted(
                item for item in worker["evidence_required"]
                if _evidence_identity(item) in EVIDENCE_PLACEHOLDER_IDENTITIES
            )
            if placeholders:
                errors.append(f"{label}.evidence_required contains placeholder evidence: {', '.join(placeholders)}")
        if not _string_list(worker["authority"], nonempty=True):
            errors.append(f"{label}.authority must be a non-empty array of strings")
        else:
            expanded = sorted(item for item in worker["authority"] if _authority_identity(item) not in allowed_authority)
            if expanded:
                errors.append(f"{label}.authority exceeds plan authority.allowed: {', '.join(expanded)}")
        worker_status = worker["status"] if isinstance(worker["status"], str) else None
        if worker_status not in WORKER_STATUSES:
            errors.append(f"{label}.status is invalid")
        if "started" in worker:
            if not isinstance(worker["started"], bool):
                errors.append(f"{label}.started must be a boolean when known; omit when unknown")
            elif worker_status in STARTED_WORKER_STATUSES and not worker["started"]:
                errors.append(f"{label}.started contradicts status {worker_status}")
            elif worker_status == "planned" and worker["started"]:
                errors.append(f"{label}.started contradicts planned status")
        for field, states in (("output", {"pending", "accepted", "rejected"}), ("write_readback", {"unknown", "reconciled"})):
            if field not in worker:
                continue
            record = worker[field]
            if not isinstance(record, dict) or set(record) != {"state", "evidence"}:
                errors.append(f"{label}.{field} must contain only state and evidence")
                continue
            state = record["state"] if isinstance(record["state"], str) else None
            if state not in states or not _string_list(record["evidence"]):
                errors.append(f"{label}.{field} has invalid state or evidence")
            elif state in {"accepted", "rejected", "reconciled"} and not _concrete_evidence(record["evidence"]):
                errors.append(f"{label}.{field} decision requires concrete observed evidence references")
        output = worker.get("output")
        output_state = output.get("state") if isinstance(output, dict) and isinstance(output.get("state"), str) else None
        readback = worker.get("write_readback")
        readback_state = readback.get("state") if isinstance(readback, dict) and isinstance(readback.get("state"), str) else None
        if worker_status == "reconciled" and output is not None and output_state != "accepted":
            errors.append(f"{label}.output contradicts reconciled accepted-output status")
        if worker_status == "reconciled" and worker["write_surfaces"] and readback is not None and readback_state != "reconciled":
            errors.append(f"{label}.write_readback contradicts reconciled write state")
        if output_state == "accepted" and worker_status in {"planned", "dispatched", "working"}:
            errors.append(f"{label}.output accepted before worker returned")
        if worker.get("started") is False and output_state in {"accepted", "rejected"}:
            errors.append(f"{label}.output decision contradicts never-started worker")
        worker_id = worker["id"]
        if _nonempty_string(worker_id):
            ids.append(worker_id)
            worker_by_id[worker_id] = {
                "depends_on": worker["depends_on"] if _string_list(worker["depends_on"]) else [],
                "write_surfaces": worker["write_surfaces"] if _string_list(worker["write_surfaces"]) else [],
                "status": worker_status,
                "started": worker.get("started"),
                "output_state": output_state,
                "readback_state": readback_state,
            }

    limit = budgets.get("concurrency_limit") if isinstance(budgets, dict) else None
    running = [worker_id for worker_id, worker in worker_by_id.items() if worker["status"] in RUNNING_WORKER_STATUSES]
    if isinstance(limit, int) and not isinstance(limit, bool) and len(running) > limit:
        errors.append(f"active worker count {len(running)} exceeds budgets.concurrency_limit {limit}")

    duplicates = sorted({worker_id for worker_id in ids if ids.count(worker_id) > 1})
    if duplicates:
        errors.append("duplicate worker ids: " + ", ".join(duplicates))

    id_set = set(ids)
    for worker_id, worker in worker_by_id.items():
        for dependency in worker["depends_on"]:
            if dependency == worker_id:
                errors.append(f"worker {worker_id} depends on itself")
            elif dependency not in id_set:
                errors.append(f"worker {worker_id} depends on unknown worker {dependency}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(worker_id: str) -> None:
        if worker_id in visiting:
            errors.append(f"dependency cycle reaches worker {worker_id}")
            return
        if worker_id in visited or worker_id not in worker_by_id:
            return
        visiting.add(worker_id)
        for dependency in worker_by_id[worker_id]["depends_on"]:
            visit(dependency)
        visiting.remove(worker_id)
        visited.add(worker_id)

    for worker_id in ids:
        visit(worker_id)

    if regime == "assemble":
        dependent = sorted(worker_id for worker_id, worker in worker_by_id.items() if worker["depends_on"])
        if dependent:
            errors.append("assemble regime workers must be independent; dependencies declared by: " + ", ".join(dependent))

    if regime == "chain" and len(worker_by_id) >= 2 and not duplicates:
        roots = sorted(worker_id for worker_id, worker in worker_by_id.items() if not worker["depends_on"])
        multi_parent = sorted(worker_id for worker_id, worker in worker_by_id.items() if len(worker["depends_on"]) != (0 if worker_id in roots else 1))
        dependent_counts = {worker_id: 0 for worker_id in worker_by_id}
        for worker in worker_by_id.values():
            for dependency in worker["depends_on"]:
                if dependency in dependent_counts:
                    dependent_counts[dependency] += 1
        branching = sorted(worker_id for worker_id, count in dependent_counts.items() if count > 1)
        edges = sum(len(worker["depends_on"]) for worker in worker_by_id.values())
        if len(roots) != 1 or multi_parent or branching or edges != len(worker_by_id) - 1:
            errors.append("chain regime must form one linear dependency path across all workers")

    for worker_id, worker in worker_by_id.items():
        if worker["status"] not in STARTED_WORKER_STATUSES and worker["started"] is not True:
            continue
        for dependency in worker["depends_on"]:
            prerequisite = worker_by_id.get(dependency, {})
            dependency_status = prerequisite.get("status")
            accepted = dependency_status == "reconciled" or (
                dependency_status in TERMINAL_WORKER_STATUSES
                and prerequisite.get("output_state") == "accepted"
                and (not prerequisite.get("write_surfaces") or prerequisite.get("readback_state") == "reconciled")
            )
            if not accepted:
                errors.append(
                    f"worker {worker_id} status {worker['status']} requires accepted dependency {dependency}; found {dependency_status or 'unknown'}"
                )

    def depends_transitively(descendant: str, ancestor: str, seen: set[str] | None = None) -> bool:
        if descendant not in worker_by_id:
            return False
        seen = set() if seen is None else seen
        if descendant in seen:
            return False
        seen.add(descendant)
        for dependency in worker_by_id[descendant]["depends_on"]:
            if dependency == ancestor or depends_transitively(dependency, ancestor, seen):
                return True
        return False

    # A reserved directory owns its descendants too. Unknown stopped writes remain
    # held until observed readback, rather than treating interruption as rollback.
    for left, right in combinations(sorted(worker_by_id), 2):
        a, b = worker_by_id[left], worker_by_id[right]
        if not _holds_write(a) or not _holds_write(b):
            continue
        if depends_transitively(left, right):
            downstream = left
        elif depends_transitively(right, left):
            downstream = right
        else:
            downstream = ""
        if downstream and worker_by_id[downstream]["status"] == "planned":
            continue
        overlaps = set()
        for left_path in a["write_surfaces"]:
            for right_path in b["write_surfaces"]:
                x, y = _surface_identity(left_path), _surface_identity(right_path)
                if _surfaces_overlap(x, y):
                    overlaps.add(x if x == y else f"{x} / {y}")
        for surface in sorted(overlaps):
            errors.append(f"active workers share write surface {surface}: {left}, {right}")

    if "outcome" in plan:
        _validate_outcome(plan, worker_by_id, errors)

    if plan_status in {"closed", "cancelled"}:
        unfinished = sorted(
            worker_id for worker_id, worker in worker_by_id.items()
            if worker["status"] not in TERMINAL_WORKER_STATUSES
        )
        if unfinished:
            errors.append("terminal plan has non-terminal workers: " + ", ".join(unfinished))
        next_move = plan["next_move"].strip().casefold() if _nonempty_string(plan["next_move"]) else ""
        if next_move and not _terminal_next_move_is_valid(next_move):
            errors.append("terminal plan next_move must be an exact closure or an explicit re-entry-only-if condition")

    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path, help="UTF-8 JSON plan; validates declarations, not evidence authenticity")
    args = parser.parse_args(argv[1:])
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"INVALID: {exc}")
        return 1
    errors = validate(plan)
    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print("VALID cd-agent-swarm-plan/v1 — declared structure only")
    print(f"Control: {plan['status']}; mission outcome: {declared_outcome(plan)} (declared, not independently authenticated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
