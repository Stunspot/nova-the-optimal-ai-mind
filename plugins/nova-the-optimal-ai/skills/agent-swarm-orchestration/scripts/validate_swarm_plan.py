#!/usr/bin/env python3
"""Validate CD Agent Swarm Plan v1 structure and orchestration invariants."""

from __future__ import annotations

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
STARTED_WORKER_STATUSES = WORKER_STATUSES - {"planned"}
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


def validate(plan: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ["root must be a JSON object"]

    missing = sorted(REQUIRED_TOP - set(plan))
    extra = sorted(set(plan) - REQUIRED_TOP)
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
        extra_worker = sorted(set(worker) - required_worker)
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
        worker_id = worker["id"]
        if _nonempty_string(worker_id):
            ids.append(worker_id)
            worker_by_id[worker_id] = {
                "depends_on": worker["depends_on"] if _string_list(worker["depends_on"]) else [],
                "write_surfaces": worker["write_surfaces"] if _string_list(worker["write_surfaces"]) else [],
                "status": worker_status,
            }

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
        if worker["status"] not in STARTED_WORKER_STATUSES:
            continue
        for dependency in worker["depends_on"]:
            dependency_status = worker_by_id.get(dependency, {}).get("status")
            if dependency_status not in ACCEPTED_DEPENDENCY_STATUSES:
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

    surface_owners: dict[str, list[str]] = {}
    for worker_id, worker in worker_by_id.items():
        if worker["status"] not in OPEN_WRITE_STATUSES:
            continue
        for surface in worker["write_surfaces"]:
            identity = _surface_identity(surface)
            surface_owners.setdefault(identity, []).append(worker_id)
    for surface, owners in sorted(surface_owners.items()):
        conflicting: set[str] = set()
        for left, right in combinations(sorted(set(owners)), 2):
            if depends_transitively(left, right):
                downstream, upstream = left, right
            elif depends_transitively(right, left):
                downstream, upstream = right, left
            else:
                downstream = upstream = ""
            safely_sequenced = bool(downstream) and worker_by_id[downstream]["status"] == "planned"
            if not safely_sequenced:
                conflicting.update((left, right))
        if conflicting:
            errors.append(f"active workers share write surface {surface}: {', '.join(sorted(conflicting))}")

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
    if len(argv) != 2:
        print("usage: validate_swarm_plan.py <swarm-plan.json>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"INVALID: {exc}")
        return 1
    errors = validate(plan)
    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print("VALID cd-agent-swarm-plan/v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
