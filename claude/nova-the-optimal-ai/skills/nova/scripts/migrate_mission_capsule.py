#!/usr/bin/env python3
"""Migrate a published Faculty Runtime mission capsule from v1 to v2.

The v1 schema remains available for faithful reads. This script performs only
the transformations whose meaning is deterministic; contradictions that would
require inventing user intent are reported for review instead.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


V1 = "collaborative-dynamics-mission-capsule/v1"
V2 = "collaborative-dynamics-mission-capsule/v2"

PHASES = {
    "orient",
    "model",
    "regulate",
    "deliberate",
    "decide",
    "act",
    "measure",
    "verify",
    "reunify",
    "communicate",
    "recover",
    "closed",
}
ACCEPTANCE_STATUSES = {"unmet", "partially_met", "met", "blocked"}
CLOSURE_STATUSES = {"open", "awaiting_authority", "blocked", "complete", "cancelled"}
ACTIVATIONS = {"consult", "own", "sustain"}
COMMITMENT_STATES = {
    "proposed",
    "authorized",
    "attempted",
    "observed",
    "verified",
    "blocked",
    "none",
}

ROOT_REQUIRED = {
    "schema",
    "mission_id",
    "desired_state",
    "acceptance",
    "phase",
    "authority",
    "active_coalition",
    "unresolved_transformations",
    "closure",
}
ROOT_ALLOWED = ROOT_REQUIRED | {
    "reasoning_horizon",
    "stakes",
    "constraints",
    "decisive_state",
    "commitment",
    "cross_cutting_conflicts",
    "budgets",
    "reassessment_trigger",
}


class CapsuleMigrationError(ValueError):
    """A v1 capsule cannot be migrated without changing unresolved meaning."""


def _object(
    value: object,
    label: str,
    *,
    required: set[str],
    allowed: set[str],
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CapsuleMigrationError(f"{label} must be an object")
    missing = sorted(required - set(value))
    if missing:
        raise CapsuleMigrationError(f"{label} is missing required fields: {', '.join(missing)}")
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise CapsuleMigrationError(f"{label} has unsupported fields: {', '.join(unknown)}")
    return value


def _string(value: object, label: str, *, nonempty: bool = False) -> str:
    if not isinstance(value, str):
        raise CapsuleMigrationError(f"{label} must be a string")
    if nonempty and len(value) == 0:
        raise CapsuleMigrationError(f"{label} must not be empty")
    return value


def _enum(value: object, label: str, choices: set[str]) -> str:
    text = _string(value, label)
    if text not in choices:
        raise CapsuleMigrationError(f"{label} has unsupported value: {text!r}")
    return text


def _array(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise CapsuleMigrationError(f"{label} must be an array")
    return value


def _string_array(value: object, label: str) -> None:
    for index, item in enumerate(_array(value, label)):
        _string(item, f"{label}[{index}]")


def validate_v1(capsule: object) -> Mapping[str, Any]:
    """Validate the published v1 contract using only the Python standard library."""

    root = _object(capsule, "capsule", required=ROOT_REQUIRED, allowed=ROOT_ALLOWED)
    if root["schema"] != V1:
        raise CapsuleMigrationError(f"capsule.schema must be {V1!r}")
    _string(root["mission_id"], "capsule.mission_id", nonempty=True)
    _string(root["desired_state"], "capsule.desired_state", nonempty=True)
    _enum(root["phase"], "capsule.phase", PHASES)

    acceptance = _array(root["acceptance"], "capsule.acceptance")
    if not acceptance:
        raise CapsuleMigrationError("capsule.acceptance must contain at least one item")
    for index, item in enumerate(acceptance):
        label = f"capsule.acceptance[{index}]"
        entry = _object(
            item,
            label,
            required={"criterion", "evidence_required", "status"},
            allowed={"criterion", "evidence_required", "status"},
        )
        _string(entry["criterion"], f"{label}.criterion", nonempty=True)
        _string(entry["evidence_required"], f"{label}.evidence_required", nonempty=True)
        _enum(entry["status"], f"{label}.status", ACCEPTANCE_STATUSES)

    authority = _object(
        root["authority"],
        "capsule.authority",
        required={"granted", "reserved"},
        allowed={"granted", "reserved"},
    )
    _string_array(authority["granted"], "capsule.authority.granted")
    _string_array(authority["reserved"], "capsule.authority.reserved")

    for index, item in enumerate(_array(root["active_coalition"], "capsule.active_coalition")):
        label = f"capsule.active_coalition[{index}]"
        member = _object(
            item,
            label,
            required={"faculty", "activation", "owned_transformation", "return_condition"},
            allowed={"faculty", "activation", "owned_transformation", "return_condition"},
        )
        _string(member["faculty"], f"{label}.faculty", nonempty=True)
        _enum(member["activation"], f"{label}.activation", ACTIVATIONS)
        _string(member["owned_transformation"], f"{label}.owned_transformation", nonempty=True)
        _string(member["return_condition"], f"{label}.return_condition", nonempty=True)

    _string_array(root["unresolved_transformations"], "capsule.unresolved_transformations")
    for key in ("stakes", "constraints", "cross_cutting_conflicts"):
        if key in root:
            _string_array(root[key], f"capsule.{key}")

    if "reasoning_horizon" in root:
        _string(root["reasoning_horizon"], "capsule.reasoning_horizon")
    if "reassessment_trigger" in root:
        _string(root["reassessment_trigger"], "capsule.reassessment_trigger")

    if "decisive_state" in root:
        decisive = _object(
            root["decisive_state"],
            "capsule.decisive_state",
            required=set(),
            allowed={
                "evidence",
                "contradictions",
                "model_or_recommendation_changes",
                "action_or_verification_changes",
            },
        )
        for key, value in decisive.items():
            _string_array(value, f"capsule.decisive_state.{key}")

    if "commitment" in root:
        commitment = _object(
            root["commitment"],
            "capsule.commitment",
            required=set(),
            allowed={"current", "state", "stop_condition"},
        )
        if "current" in commitment:
            _string(commitment["current"], "capsule.commitment.current")
        if "state" in commitment:
            _enum(commitment["state"], "capsule.commitment.state", COMMITMENT_STATES)
        if "stop_condition" in commitment:
            _string(commitment["stop_condition"], "capsule.commitment.stop_condition")

    if "budgets" in root:
        budgets = _object(
            root["budgets"],
            "capsule.budgets",
            required=set(),
            allowed={"context", "time", "cost", "tool_use"},
        )
        for key, value in budgets.items():
            _string(value, f"capsule.budgets.{key}")

    closure = _object(
        root["closure"],
        "capsule.closure",
        required={"status", "reopening_condition"},
        allowed={"status", "reopening_condition"},
    )
    _enum(closure["status"], "capsule.closure.status", CLOSURE_STATUSES)
    _string(closure["reopening_condition"], "capsule.closure.reopening_condition")
    return root


def migrate_v1_to_v2(capsule: object) -> dict[str, Any]:
    """Return a deterministic v2 copy, or stop where migration needs judgment."""

    source = validate_v1(capsule)
    if not source["mission_id"].strip():
        raise CapsuleMigrationError("capsule.mission_id needs substantive content before v2 migration")
    if not source["desired_state"].strip():
        raise CapsuleMigrationError("capsule.desired_state needs substantive content before v2 migration")

    for index, item in enumerate(source["acceptance"]):
        if not item["criterion"].strip():
            raise CapsuleMigrationError(
                f"capsule.acceptance[{index}].criterion needs substantive content before v2 migration"
            )
        if not item["evidence_required"].strip():
            raise CapsuleMigrationError(
                f"capsule.acceptance[{index}].evidence_required needs substantive content before v2 migration"
            )

    closure_status = source["closure"]["status"]
    if closure_status == "complete" and any(
        item["status"] != "met" for item in source["acceptance"]
    ):
        raise CapsuleMigrationError(
            "legacy capsule claims complete while acceptance remains unmet; review the closure or criteria"
        )
    if source["phase"] == "closed" and closure_status not in {"complete", "cancelled"}:
        raise CapsuleMigrationError(
            "legacy capsule has phase 'closed' with a nonterminal closure; review the terminal state"
        )

    migrated: dict[str, Any] = {}
    for key, value in source.items():
        if key == "schema":
            migrated["schema"] = V2
        elif key == "desired_state":
            migrated["current_direction"] = copy.deepcopy(value)
        elif key == "acceptance":
            migrated["acceptance"] = [
                {
                    "criterion": item["criterion"],
                    "basis": "legacy_v1",
                    "evidence_required": item["evidence_required"],
                    "status": item["status"],
                }
                for item in value
            ]
        elif key == "closure":
            migrated_closure = {"status": value["status"]}
            if value["reopening_condition"].strip():
                migrated_closure["reopening_condition"] = value["reopening_condition"]
            migrated["closure"] = migrated_closure
        else:
            migrated[key] = copy.deepcopy(value)

    if closure_status in {"complete", "cancelled"}:
        migrated["phase"] = "closed"
    return migrated


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UTF-8 JSON capsule using the published v1 schema")
    parser.add_argument(
        "--output",
        type=Path,
        help="write a new v2 JSON file; omitted writes to stdout and never changes the input",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        source = json.loads(args.input.read_text(encoding="utf-8"))
        migrated = migrate_v1_to_v2(source)
        rendered = json.dumps(migrated, ensure_ascii=False, indent=2) + "\n"
        if args.output is None:
            sys.stdout.write(rendered)
        else:
            if args.output.resolve() == args.input.resolve():
                raise CapsuleMigrationError("refusing to overwrite the v1 source capsule")
            with args.output.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(rendered)
    except (CapsuleMigrationError, json.JSONDecodeError, OSError) as exc:
        print(f"mission capsule migration failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
