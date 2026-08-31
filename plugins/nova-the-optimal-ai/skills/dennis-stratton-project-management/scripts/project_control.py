#!/usr/bin/env python3
"""Validate, migrate, fingerprint, bootstrap, and render project-control records.

This tool provides STRUCTURAL_DIAGNOSTICS_ONLY. It does not prove delivery,
authority, health, acceptance, or value.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "cd-project-control/v2"
LEGACY_SCHEMA_VERSION = "cd-project-control/v1"
BOUNDARY = "STRUCTURAL_DIAGNOSTICS_ONLY"
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{1,127}$")
STORE_SCHEMA_VERSION = "cd-project-record-store/v1"
STORE_ENV_VAR = "DENNIS_PROJECT_HOME"
DEFAULT_STORE_PARTS = (".dennis-stratton", "project-records")

PROJECT_STATUSES = {"proposed", "active", "paused", "recovering", "closing", "closed", "cancelled"}
HIERARCHY_KINDS = {"phase", "stage", "milestone", "workstream"}
HIERARCHY_STATUSES = {"planned", "active", "blocked", "complete", "cancelled", "superseded"}
WORK_STATUSES = {"planned", "ready", "active", "blocked", "complete", "cancelled"}
CRITERION_STATUSES = {"pending", "observed", "verified", "accepted", "waived", "failed"}
COMPLETION_STATUSES = {"pending", "satisfied", "waived", "unknown", "not_applicable"}
DECISION_STATUSES = {"proposed", "accepted", "rejected", "superseded"}
CHANGE_STATUSES = {"proposed", "approved", "rejected", "implemented", "withdrawn"}
CONTROL_KINDS = {"risk", "assumption", "issue", "dependency"}
CONTROL_STATUSES = {"open", "watch", "blocked", "mitigated", "resolved", "accepted", "invalidated"}
EVIDENCE_LEVELS = {"proposed", "reported", "observed", "verified", "accepted", "rejected"}
SOURCE_STATUSES = {"current", "stale", "superseded", "unavailable", "disputed"}
SOURCE_KINDS = {
    "owner_decision", "accepted_decision", "charter", "roadmap", "repository",
    "runtime", "verification", "task_history", "derived_summary",
    "external_requirement", "other",
}
AUTHORITY_KINDS = {"owner_policy", "external_requirement", "repository_rule", "technical_limit", "agent_safeguard"}
AUTHORITY_STATUSES = {"active", "expired", "superseded", "proposed"}
POSTURES = {"provisional", "authorized", "executing", "blocked", "recovering", "review", "complete"}

TOP_LEVEL = [
    "schema_version", "project", "source_authority", "hierarchy", "current",
    "scope", "authority", "justification", "benefits", "governance",
    "forecast", "capacity", "stakeholders", "commercial_alignment",
    "work_packages", "exit_criteria", "completion_contract", "decisions",
    "changes", "controls", "evidence", "transition", "checkpoints",
]
COLLECTIONS = [
    "source_authority", "hierarchy", "work_packages", "exit_criteria",
    "decisions", "changes", "controls", "evidence", "checkpoints",
    "benefits", "stakeholders", "commercial_alignment",
]

def load_record(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("record root must be a JSON object")
    return value


def canonical_bytes(record: dict[str, Any]) -> bytes:
    return (json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def fingerprint(record: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(record)).hexdigest()


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone offset is required")
    return parsed


def _schema_reference(root: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise ValueError(f"unsupported schema reference: {reference}")
    node: Any = root
    for raw in reference[2:].split("/"):
        key = raw.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or key not in node:
            raise ValueError(f"unresolved schema reference: {reference}")
        node = node[key]
    if not isinstance(node, dict):
        raise ValueError(f"schema reference does not resolve to an object: {reference}")
    return node


def _json_type_matches(value: Any, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, False)


def schema_issues(instance: Any, schema: dict[str, Any]) -> list[dict[str, str]]:
    """Validate the JSON Schema vocabulary used by the bundled control schema."""
    issues: list[dict[str, str]] = []

    def issue(code: str, path: str, message: str) -> None:
        issues.append({"code": code, "path": path, "message": message})

    def canonical(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def walk(value: Any, node: dict[str, Any], path: str, target: list[dict[str, str]]) -> None:
        if "$ref" in node:
            walk(value, _schema_reference(schema, node["$ref"]), path, target)
            return
        if "anyOf" in node:
            for branch in node["anyOf"]:
                branch_issues: list[dict[str, str]] = []
                walk(value, branch, path, branch_issues)
                if not branch_issues:
                    break
            else:
                target.append({"code": "SCHEMA_ANY_OF", "path": path, "message": "does not match any allowed schema shape"})
            return
        expected = node.get("type")
        if isinstance(expected, str) and not _json_type_matches(value, expected):
            target.append({"code": "SCHEMA_TYPE", "path": path, "message": f"must be of type {expected}"})
            return
        if "const" in node and canonical(value) != canonical(node["const"]):
            target.append({"code": "SCHEMA_CONST", "path": path, "message": f"must equal {node['const']!r}"})
        if "enum" in node and canonical(value) not in {canonical(item) for item in node["enum"]}:
            target.append({"code": "SCHEMA_ENUM", "path": path, "message": "value is not in the allowed set"})
        if isinstance(value, str):
            if len(value) < node.get("minLength", 0):
                target.append({"code": "SCHEMA_MIN_LENGTH", "path": path, "message": f"must contain at least {node['minLength']} character(s)"})
            pattern = node.get("pattern")
            if pattern is not None and re.search(pattern, value) is None:
                target.append({"code": "SCHEMA_PATTERN", "path": path, "message": f"must match {pattern}"})
        if isinstance(value, (int, float)) and not isinstance(value, bool) and "minimum" in node and value < node["minimum"]:
            target.append({"code": "SCHEMA_MINIMUM", "path": path, "message": f"must be at least {node['minimum']}"})
        if isinstance(value, list):
            if len(value) < node.get("minItems", 0):
                target.append({"code": "SCHEMA_MIN_ITEMS", "path": path, "message": f"must contain at least {node['minItems']} item(s)"})
            if node.get("uniqueItems"):
                seen: set[str] = set()
                for index, item in enumerate(value):
                    encoded = canonical(item)
                    if encoded in seen:
                        target.append({"code": "SCHEMA_UNIQUE_ITEMS", "path": f"{path}[{index}]", "message": "duplicates an earlier array item"})
                    seen.add(encoded)
            item_schema = node.get("items")
            if isinstance(item_schema, dict):
                for index, item in enumerate(value):
                    walk(item, item_schema, f"{path}[{index}]", target)
        if isinstance(value, dict):
            required_fields = node.get("required", [])
            for field in required_fields:
                if field not in value:
                    target.append({"code": "SCHEMA_REQUIRED", "path": f"{path}.{field}", "message": "required field is missing"})
            properties = node.get("properties", {})
            if node.get("additionalProperties") is False:
                for field in value:
                    if field not in properties:
                        target.append({"code": "SCHEMA_ADDITIONAL_PROPERTY", "path": f"{path}.{field}", "message": "field is not allowed"})
            for field, child_schema in properties.items():
                if field in value:
                    walk(value[field], child_schema, f"{path}.{field}", target)

    walk(instance, schema, "$", issues)
    return issues

def validate_record(record: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    def add(target: list[dict[str, str]], code: str, path: str, message: str) -> None:
        target.append({"code": code, "path": path, "message": message})

    def error(code: str, path: str, message: str) -> None:
        add(errors, code, path, message)

    def warn(code: str, path: str, message: str) -> None:
        add(warnings, code, path, message)

    try:
        schema_path = Path(__file__).resolve().parent.parent / "schemas" / "project-control.schema.json"
        schema = load_record(schema_path)
        errors.extend(schema_issues(record, schema))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        error("SCHEMA_UNAVAILABLE", "schema", f"cannot load maintained schema: {exc}")
    if errors:
        return errors, warnings
    def obj(value: Any, path: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            error("TYPE_OBJECT", path, "must be an object")
            return {}
        return value

    def array(value: Any, path: str) -> list[Any]:
        if not isinstance(value, list):
            error("TYPE_ARRAY", path, "must be an array")
            return []
        return value

    def required(container: dict[str, Any], fields: list[str], path: str) -> None:
        for field in fields:
            if field not in container:
                error("MISSING_FIELD", f"{path}.{field}", "required field is missing")

    def nonempty(value: Any, path: str) -> bool:
        if not isinstance(value, str) or not value.strip():
            error("NONEMPTY_STRING", path, "must be a non-empty string")
            return False
        return True

    def valid_id(value: Any, path: str) -> bool:
        if not nonempty(value, path):
            return False
        if not ID_PATTERN.fullmatch(value):
            error("INVALID_ID", path, "must match the stable identifier pattern")
            return False
        return True

    def string_array(value: Any, path: str) -> list[str]:
        values = array(value, path)
        output: list[str] = []
        for index, item in enumerate(values):
            if nonempty(item, f"{path}[{index}]"):
                output.append(item)
        return output

    def valid_timestamp(value: Any, path: str) -> datetime | None:
        if not nonempty(value, path):
            return None
        try:
            return parse_timestamp(value)
        except ValueError as exc:
            error("INVALID_TIMESTAMP", path, f"must be an ISO-8601 timestamp with timezone: {exc}")
            return None
    for field in TOP_LEVEL:
        if field not in record:
            error("MISSING_TOP_LEVEL", field, "required top-level field is missing")
    if record.get("schema_version") != SCHEMA_VERSION:
        error("SCHEMA_VERSION", "schema_version", f"must equal {SCHEMA_VERSION}")

    project = obj(record.get("project"), "project")
    required(project, ["id", "name", "outcome", "status", "owner", "updated_at"], "project")
    valid_id(project.get("id"), "project.id")
    for field in ["name", "outcome", "owner", "updated_at"]:
        nonempty(project.get(field), f"project.{field}")
    valid_timestamp(project.get("updated_at"), "project.updated_at")
    if project.get("status") not in PROJECT_STATUSES:
        error("PROJECT_STATUS", "project.status", f"must be one of {sorted(PROJECT_STATUSES)}")

    lists: dict[str, list[Any]] = {}
    for name in COLLECTIONS:
        lists[name] = array(record.get(name), name)
    if not lists["source_authority"]:
        error("SOURCE_REQUIRED", "source_authority", "at least one authority source is required")
    if not lists["hierarchy"]:
        error("HIERARCHY_REQUIRED", "hierarchy", "at least one hierarchy node is required")

    registries: dict[str, dict[str, dict[str, Any]]] = {name: {} for name in COLLECTIONS}
    all_ids: dict[str, str] = {}

    def register(collection: str, item: dict[str, Any], path: str) -> str | None:
        identifier = item.get("id")
        if not valid_id(identifier, f"{path}.id"):
            return None
        if identifier in all_ids:
            error("DUPLICATE_ID", f"{path}.id", f"duplicates {all_ids[identifier]}")
            return identifier
        all_ids[identifier] = path
        registries[collection][identifier] = item
        return identifier

    ranks: dict[int, str] = {}
    for index, raw in enumerate(lists["source_authority"]):
        path = f"source_authority[{index}]"
        item = obj(raw, path)
        required(item, ["id", "rank", "kind", "locator", "scope", "observed_at", "status"], path)
        identifier = register("source_authority", item, path)
        rank = item.get("rank")
        if not isinstance(rank, int) or isinstance(rank, bool) or rank < 1:
            error("SOURCE_RANK", f"{path}.rank", "must be a positive integer")
        elif rank in ranks:
            error("DUPLICATE_RANK", f"{path}.rank", f"duplicates rank used by {ranks[rank]}")
        elif identifier:
            ranks[rank] = identifier
        if item.get("kind") not in SOURCE_KINDS:
            error("SOURCE_KIND", f"{path}.kind", f"must be one of {sorted(SOURCE_KINDS)}")
        if item.get("status") not in SOURCE_STATUSES:
            error("SOURCE_STATUS", f"{path}.status", f"must be one of {sorted(SOURCE_STATUSES)}")
        for field in ["locator", "scope", "observed_at"]:
            nonempty(item.get(field), f"{path}.{field}")
        valid_timestamp(item.get("observed_at"), f"{path}.observed_at")

    for index, raw in enumerate(lists["hierarchy"]):
        path = f"hierarchy[{index}]"
        item = obj(raw, path)
        required(item, ["id", "kind", "label", "parent_id", "status", "purpose", "exit_criteria_ids"], path)
        register("hierarchy", item, path)
        if item.get("kind") not in HIERARCHY_KINDS:
            error("HIERARCHY_KIND", f"{path}.kind", f"must be one of {sorted(HIERARCHY_KINDS)}")
        if item.get("status") not in HIERARCHY_STATUSES:
            error("HIERARCHY_STATUS", f"{path}.status", f"must be one of {sorted(HIERARCHY_STATUSES)}")
        for field in ["label", "purpose"]:
            nonempty(item.get(field), f"{path}.{field}")
        if item.get("parent_id") is not None:
            valid_id(item.get("parent_id"), f"{path}.parent_id")
        string_array(item.get("exit_criteria_ids"), f"{path}.exit_criteria_ids")
    authority = obj(record.get("authority"), "authority")
    required(authority, ["project_owner", "grants", "reserved"], "authority")
    nonempty(authority.get("project_owner"), "authority.project_owner")
    grants = array(authority.get("grants"), "authority.grants")
    grant_map: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(grants):
        path = f"authority.grants[{index}]"
        item = obj(raw, path)
        required(item, ["id", "actor", "issued_by", "scope", "kind", "may", "may_not", "source_id", "rationale", "effective_at", "expires_at", "revisit_trigger", "status"], path)
        identifier = item.get("id")
        if valid_id(identifier, f"{path}.id"):
            if identifier in all_ids:
                error("DUPLICATE_ID", f"{path}.id", f"duplicates {all_ids[identifier]}")
            else:
                all_ids[identifier] = path
                grant_map[identifier] = item
        for field in ["actor", "issued_by", "scope", "rationale", "effective_at", "revisit_trigger"]:
            nonempty(item.get(field), f"{path}.{field}")
        may = string_array(item.get("may"), f"{path}.may")
        may_not = string_array(item.get("may_not"), f"{path}.may_not")
        if not may and not may_not:
            warn("EMPTY_GRANT", path, "grant carries neither permission nor reservation")
        if item.get("kind") not in AUTHORITY_KINDS:
            error("AUTHORITY_KIND", f"{path}.kind", f"must be one of {sorted(AUTHORITY_KINDS)}")
        if item.get("status") not in AUTHORITY_STATUSES:
            error("AUTHORITY_STATUS", f"{path}.status", f"must be one of {sorted(AUTHORITY_STATUSES)}")
        valid_id(item.get("source_id"), f"{path}.source_id")
        valid_timestamp(item.get("effective_at"), f"{path}.effective_at")
        if item.get("expires_at") is not None:
            valid_timestamp(item.get("expires_at"), f"{path}.expires_at")
    string_array(authority.get("reserved"), "authority.reserved")

    for index, raw in enumerate(lists["work_packages"]):
        path = f"work_packages[{index}]"
        item = obj(raw, path)
        required(item, ["id", "parent_id", "outcome", "status", "dependency_ids", "acceptance_criteria_ids", "authority_ids", "owner", "next_action"], path)
        register("work_packages", item, path)
        valid_id(item.get("parent_id"), f"{path}.parent_id")
        for field in ["outcome", "owner", "next_action"]:
            nonempty(item.get(field), f"{path}.{field}")
        if item.get("status") not in WORK_STATUSES:
            error("WORK_STATUS", f"{path}.status", f"must be one of {sorted(WORK_STATUSES)}")
        for field in ["dependency_ids", "acceptance_criteria_ids", "authority_ids"]:
            string_array(item.get(field), f"{path}.{field}")

    for index, raw in enumerate(lists["exit_criteria"]):
        path = f"exit_criteria[{index}]"
        item = obj(raw, path)
        required(item, ["id", "owner_id", "description", "status", "evidence_ids", "waiver_decision_id"], path)
        register("exit_criteria", item, path)
        valid_id(item.get("owner_id"), f"{path}.owner_id")
        nonempty(item.get("description"), f"{path}.description")
        if item.get("status") not in CRITERION_STATUSES:
            error("CRITERION_STATUS", f"{path}.status", f"must be one of {sorted(CRITERION_STATUSES)}")
        string_array(item.get("evidence_ids"), f"{path}.evidence_ids")
        if item.get("waiver_decision_id") is not None:
            valid_id(item.get("waiver_decision_id"), f"{path}.waiver_decision_id")

    for index, raw in enumerate(lists["decisions"]):
        path = f"decisions[{index}]"
        item = obj(raw, path)
        required(item, ["id", "status", "decision", "options", "rationale", "authority", "source_id", "date", "supersedes_ids"], path)
        register("decisions", item, path)
        if item.get("status") not in DECISION_STATUSES:
            error("DECISION_STATUS", f"{path}.status", f"must be one of {sorted(DECISION_STATUSES)}")
        for field in ["decision", "rationale", "authority", "date"]:
            nonempty(item.get(field), f"{path}.{field}")
        string_array(item.get("options"), f"{path}.options")
        valid_id(item.get("source_id"), f"{path}.source_id")
        string_array(item.get("supersedes_ids"), f"{path}.supersedes_ids")

    for index, raw in enumerate(lists["changes"]):
        path = f"changes[{index}]"
        item = obj(raw, path)
        required(item, ["id", "status", "request", "impact", "authority", "decision_id"], path)
        register("changes", item, path)
        if item.get("status") not in CHANGE_STATUSES:
            error("CHANGE_STATUS", f"{path}.status", f"must be one of {sorted(CHANGE_STATUSES)}")
        nonempty(item.get("request"), f"{path}.request")
        nonempty(item.get("authority"), f"{path}.authority")
        if item.get("decision_id") is not None:
            valid_id(item.get("decision_id"), f"{path}.decision_id")
        impact = obj(item.get("impact"), f"{path}.impact")
        impact_fields = ["scope", "schedule", "cost", "risk", "quality", "benefits"]
        required(impact, impact_fields, f"{path}.impact")
        for field in impact_fields:
            nonempty(impact.get(field), f"{path}.impact.{field}")

    for index, raw in enumerate(lists["controls"]):
        path = f"controls[{index}]"
        item = obj(raw, path)
        required(item, ["id", "kind", "description", "owner", "status", "trigger", "next_action", "due"], path)
        register("controls", item, path)
        if item.get("kind") not in CONTROL_KINDS:
            error("CONTROL_KIND", f"{path}.kind", f"must be one of {sorted(CONTROL_KINDS)}")
        if item.get("status") not in CONTROL_STATUSES:
            error("CONTROL_STATUS", f"{path}.status", f"must be one of {sorted(CONTROL_STATUSES)}")
        for field in ["description", "owner", "trigger", "next_action"]:
            nonempty(item.get(field), f"{path}.{field}")
        if item.get("due") is not None:
            nonempty(item.get("due"), f"{path}.due")

    for index, raw in enumerate(lists["evidence"]):
        path = f"evidence[{index}]"
        item = obj(raw, path)
        required(item, ["id", "claim", "level", "locator", "observed_at", "method", "limits", "actor"], path)
        register("evidence", item, path)
        if item.get("level") not in EVIDENCE_LEVELS:
            error("EVIDENCE_LEVEL", f"{path}.level", f"must be one of {sorted(EVIDENCE_LEVELS)}")
        for field in ["claim", "locator", "observed_at", "method", "limits", "actor"]:
            nonempty(item.get(field), f"{path}.{field}")
        valid_timestamp(item.get("observed_at"), f"{path}.observed_at")

    for index, raw in enumerate(lists["checkpoints"]):
        path = f"checkpoints[{index}]"
        item = obj(raw, path)
        required(item, ["id", "timestamp", "hierarchy_path", "completed", "remaining", "blockers", "repository_state", "next_action"], path)
        register("checkpoints", item, path)
        valid_timestamp(item.get("timestamp"), f"{path}.timestamp")
        string_array(item.get("hierarchy_path"), f"{path}.hierarchy_path")
        for field in ["completed", "remaining", "blockers"]:
            string_array(item.get(field), f"{path}.{field}")
        nonempty(item.get("next_action"), f"{path}.next_action")
        repository_state = item.get("repository_state")
        if repository_state is not None:
            repository_state = obj(repository_state, f"{path}.repository_state")
            required(repository_state, ["branch", "head", "worktree", "remote_state"], f"{path}.repository_state")
            nonempty(repository_state.get("branch"), f"{path}.repository_state.branch")
            nonempty(repository_state.get("head"), f"{path}.repository_state.head")
            if repository_state.get("worktree") not in {"clean", "dirty", "unknown"}:
                error("WORKTREE_STATE", f"{path}.repository_state.worktree", "invalid worktree state")
            if repository_state.get("remote_state") not in {"synchronized", "ahead", "behind", "diverged", "unconfigured", "unknown"}:
                error("REMOTE_STATE", f"{path}.repository_state.remote_state", "invalid remote state")
    current = obj(record.get("current"), "current")
    required(current, ["path", "active_commitment_id", "as_of", "posture", "purpose_connection", "next_action", "next_decision"], "current")
    current_path = string_array(current.get("path"), "current.path")
    if not current_path:
        error("CURRENT_PATH_REQUIRED", "current.path", "must name the active hierarchy path")
    if current.get("active_commitment_id") is not None:
        valid_id(current.get("active_commitment_id"), "current.active_commitment_id")
    for field in ["as_of", "purpose_connection", "next_action"]:
        nonempty(current.get(field), f"current.{field}")
    valid_timestamp(current.get("as_of"), "current.as_of")
    if current.get("posture") not in POSTURES:
        error("CURRENT_POSTURE", "current.posture", f"must be one of {sorted(POSTURES)}")
    if current.get("next_decision") is not None:
        nonempty(current.get("next_decision"), "current.next_decision")

    scope = obj(record.get("scope"), "scope")
    required(scope, ["in", "out", "non_goals"], "scope")
    for field in ["in", "out", "non_goals"]:
        string_array(scope.get(field), f"scope.{field}")

    contract = obj(record.get("completion_contract"), "completion_contract")
    required(contract, ["unit_id", "definition", "states"], "completion_contract")
    valid_id(contract.get("unit_id"), "completion_contract.unit_id")
    nonempty(contract.get("definition"), "completion_contract.definition")
    completion_states = array(contract.get("states"), "completion_contract.states")
    if not completion_states:
        error("COMPLETION_STATES_REQUIRED", "completion_contract.states", "at least one completion state is required")
    state_names: set[str] = set()
    for index, raw in enumerate(completion_states):
        path = f"completion_contract.states[{index}]"
        item = obj(raw, path)
        required(item, ["name", "required", "status", "evidence_ids", "waiver_decision_id"], path)
        name = item.get("name")
        if nonempty(name, f"{path}.name"):
            if name in state_names:
                error("DUPLICATE_COMPLETION_STATE", f"{path}.name", "completion-state name must be unique")
            state_names.add(name)
        if not isinstance(item.get("required"), bool):
            error("COMPLETION_REQUIRED_BOOL", f"{path}.required", "must be a boolean")
        if item.get("status") not in COMPLETION_STATUSES:
            error("COMPLETION_STATUS", f"{path}.status", f"must be one of {sorted(COMPLETION_STATUSES)}")
        string_array(item.get("evidence_ids"), f"{path}.evidence_ids")
        if item.get("waiver_decision_id") is not None:
            valid_id(item.get("waiver_decision_id"), f"{path}.waiver_decision_id")

    hierarchy_map = registries["hierarchy"]
    work_map = registries["work_packages"]
    criterion_map = registries["exit_criteria"]
    decision_map = registries["decisions"]
    evidence_map = registries["evidence"]
    source_map = registries["source_authority"]

    roots = [identifier for identifier, item in hierarchy_map.items() if item.get("parent_id") is None]
    if not roots:
        error("HIERARCHY_ROOT", "hierarchy", "at least one root hierarchy node is required")

    for identifier, item in hierarchy_map.items():
        parent_id = item.get("parent_id")
        if parent_id is not None and parent_id not in hierarchy_map:
            error("UNKNOWN_HIERARCHY_PARENT", f"hierarchy.{identifier}.parent_id", f"unknown hierarchy node {parent_id}")
        seen = {identifier}
        cursor = parent_id
        while cursor is not None and cursor in hierarchy_map:
            if cursor in seen:
                error("HIERARCHY_CYCLE", f"hierarchy.{identifier}.parent_id", "hierarchy contains a cycle")
                break
            seen.add(cursor)
            cursor = hierarchy_map[cursor].get("parent_id")
        for criterion_id in item.get("exit_criteria_ids", []):
            if criterion_id not in criterion_map:
                error("UNKNOWN_EXIT_CRITERION", f"hierarchy.{identifier}.exit_criteria_ids", f"unknown criterion {criterion_id}")
            elif criterion_map[criterion_id].get("owner_id") != identifier:
                error("CRITERION_OWNER_MISMATCH", f"hierarchy.{identifier}.exit_criteria_ids", f"criterion {criterion_id} belongs to another unit")

    for identifier, item in work_map.items():
        parent_id = item.get("parent_id")
        if parent_id not in hierarchy_map:
            error("UNKNOWN_WORK_PARENT", f"work_packages.{identifier}.parent_id", f"unknown hierarchy node {parent_id}")
        for dependency_id in item.get("dependency_ids", []):
            if dependency_id not in work_map:
                error("UNKNOWN_DEPENDENCY", f"work_packages.{identifier}.dependency_ids", f"unknown work package {dependency_id}")
            elif dependency_id == identifier:
                error("SELF_DEPENDENCY", f"work_packages.{identifier}.dependency_ids", "work package cannot depend on itself")
        for criterion_id in item.get("acceptance_criteria_ids", []):
            if criterion_id not in criterion_map:
                error("UNKNOWN_ACCEPTANCE_CRITERION", f"work_packages.{identifier}.acceptance_criteria_ids", f"unknown criterion {criterion_id}")
        for grant_id in item.get("authority_ids", []):
            if grant_id not in grant_map:
                error("UNKNOWN_AUTHORITY_GRANT", f"work_packages.{identifier}.authority_ids", f"unknown authority grant {grant_id}")
        if item.get("status") == "complete":
            incomplete = [criterion_id for criterion_id in item.get("acceptance_criteria_ids", []) if criterion_map.get(criterion_id, {}).get("status") not in {"verified", "accepted", "waived"}]
            if incomplete:
                error("COMPLETE_WITH_OPEN_CRITERIA", f"work_packages.{identifier}.status", f"complete work has open criteria: {incomplete}")
            open_dependencies = [dependency_id for dependency_id in item.get("dependency_ids", []) if work_map.get(dependency_id, {}).get("status") not in {"complete", "cancelled"}]
            if open_dependencies:
                error("COMPLETE_WITH_OPEN_DEPENDENCY", f"work_packages.{identifier}.status", f"complete work has open dependencies: {open_dependencies}")

    def dependency_cycle(start: str) -> bool:
        visiting: set[str] = set()
        visited: set[str] = set()
        def walk(identifier: str) -> bool:
            if identifier in visiting:
                return True
            if identifier in visited or identifier not in work_map:
                return False
            visiting.add(identifier)
            for dependency_id in work_map[identifier].get("dependency_ids", []):
                if walk(dependency_id):
                    return True
            visiting.remove(identifier)
            visited.add(identifier)
            return False
        return walk(start)

    for identifier in work_map:
        if dependency_cycle(identifier):
            error("DEPENDENCY_CYCLE", f"work_packages.{identifier}.dependency_ids", "dependency graph contains a cycle")

    for identifier, item in grant_map.items():
        source = source_map.get(item.get("source_id"))
        if source is None:
            error("UNKNOWN_GRANT_SOURCE", f"authority.grants.{identifier}.source_id", f"unknown source {item.get('source_id')}")
        if item.get("kind") == "agent_safeguard" and item.get("status") == "active":
            if source is None or source.get("kind") not in {"owner_decision", "accepted_decision"}:
                error("UNCONFIRMED_AGENT_SAFEGUARD", f"authority.grants.{identifier}.status", "an active agent safeguard requires owner-backed or accepted-decision authority; otherwise keep it proposed")

    for identifier, item in criterion_map.items():
        owner_id = item.get("owner_id")
        if owner_id not in hierarchy_map and owner_id not in work_map:
            error("UNKNOWN_CRITERION_OWNER", f"exit_criteria.{identifier}.owner_id", f"unknown owner {owner_id}")
        evidence_ids = item.get("evidence_ids", [])
        for evidence_id in evidence_ids:
            if evidence_id not in evidence_map:
                error("UNKNOWN_CRITERION_EVIDENCE", f"exit_criteria.{identifier}.evidence_ids", f"unknown evidence {evidence_id}")
        status = item.get("status")
        minimum_levels = {
            "observed": {"observed", "verified", "accepted"},
            "verified": {"verified", "accepted"},
            "accepted": {"accepted"},
        }
        if status in minimum_levels:
            if not evidence_ids:
                error("CRITERION_WITHOUT_EVIDENCE", f"exit_criteria.{identifier}.status", f"{status} criterion requires named evidence")
            unsupported = [evidence_id for evidence_id in evidence_ids if evidence_map.get(evidence_id, {}).get("level") not in minimum_levels[status]]
            if unsupported:
                error("INSUFFICIENT_CRITERION_EVIDENCE", f"exit_criteria.{identifier}.evidence_ids", f"evidence does not support {status}: {unsupported}")
        waiver_id = item.get("waiver_decision_id")
        if status == "waived":
            if waiver_id not in decision_map or decision_map.get(waiver_id, {}).get("status") != "accepted":
                error("INVALID_CRITERION_WAIVER", f"exit_criteria.{identifier}.waiver_decision_id", "waiver requires an accepted decision")
        elif waiver_id is not None:
            warn("UNUSED_CRITERION_WAIVER", f"exit_criteria.{identifier}.waiver_decision_id", "waiver decision is named but criterion is not waived")
    for identifier, item in decision_map.items():
        if item.get("source_id") not in source_map:
            error("UNKNOWN_DECISION_SOURCE", f"decisions.{identifier}.source_id", f"unknown source {item.get('source_id')}")
        for superseded_id in item.get("supersedes_ids", []):
            if superseded_id not in decision_map and superseded_id not in grant_map:
                error("UNKNOWN_SUPERSEDED_ITEM", f"decisions.{identifier}.supersedes_ids", f"unknown decision or grant {superseded_id}")
            elif superseded_id == identifier:
                error("SELF_SUPERSESSION", f"decisions.{identifier}.supersedes_ids", "decision cannot supersede itself")

    for identifier, item in registries["changes"].items():
        decision_id = item.get("decision_id")
        if decision_id is not None and decision_id not in decision_map:
            error("UNKNOWN_CHANGE_DECISION", f"changes.{identifier}.decision_id", f"unknown decision {decision_id}")
        if item.get("status") in {"approved", "implemented"}:
            if decision_id not in decision_map or decision_map.get(decision_id, {}).get("status") != "accepted":
                error("CHANGE_WITHOUT_ACCEPTED_DECISION", f"changes.{identifier}.status", "approved or implemented change requires an accepted decision")

    for index, item in enumerate(lists["benefits"]):
        evidence_ids = item.get("evidence_ids", [])
        path = f"benefits[{index}]"
        for evidence_id in evidence_ids:
            if evidence_id not in evidence_map:
                error("UNKNOWN_BENEFIT_EVIDENCE", f"{path}.evidence_ids", f"unknown evidence {evidence_id}")
        if item.get("status") == "realized":
            if not evidence_ids:
                error("REALIZED_BENEFIT_WITHOUT_EVIDENCE", f"{path}.status", "realized benefit requires named verified or accepted evidence")
            unsupported = [evidence_id for evidence_id in evidence_ids if evidence_map.get(evidence_id, {}).get("level") not in {"verified", "accepted"}]
            if unsupported:
                error("INSUFFICIENT_BENEFIT_EVIDENCE", f"{path}.evidence_ids", f"realized benefit requires verified or accepted evidence: {unsupported}")

    governance = record.get("governance", {})
    gates = governance.get("gates", []) if isinstance(governance, dict) else []
    for index, item in enumerate(gates):
        evidence_ids = item.get("evidence_ids", [])
        path = f"governance.gates[{index}]"
        for evidence_id in evidence_ids:
            if evidence_id not in evidence_map:
                error("UNKNOWN_GATE_EVIDENCE", f"{path}.evidence_ids", f"unknown evidence {evidence_id}")
        if item.get("status") in {"approved", "rejected"}:
            if not evidence_ids:
                error("DECIDED_GATE_WITHOUT_EVIDENCE", f"{path}.status", "approved or rejected gate requires named accepted evidence")
            unsupported = [evidence_id for evidence_id in evidence_ids if evidence_map.get(evidence_id, {}).get("level") != "accepted"]
            if unsupported:
                error("INSUFFICIENT_GATE_EVIDENCE", f"{path}.evidence_ids", f"approved or rejected gate requires accepted evidence: {unsupported}")

    transition = record.get("transition", {})
    if isinstance(transition, dict):
        evidence_ids = transition.get("evidence_ids", [])
        for evidence_id in evidence_ids:
            if evidence_id not in evidence_map:
                error("UNKNOWN_TRANSITION_EVIDENCE", "transition.evidence_ids", f"unknown evidence {evidence_id}")
        decided_transition = transition.get("acceptance_state") in {"accepted", "rejected"} or transition.get("support_state") == "accepted"
        if decided_transition:
            if not evidence_ids:
                error("DECIDED_TRANSITION_WITHOUT_EVIDENCE", "transition", "accepted or rejected transition state requires named accepted evidence")
            unsupported = [evidence_id for evidence_id in evidence_ids if evidence_map.get(evidence_id, {}).get("level") != "accepted"]
            if unsupported:
                error("INSUFFICIENT_TRANSITION_EVIDENCE", "transition.evidence_ids", f"accepted or rejected transition state requires accepted evidence: {unsupported}")

    for identifier, item in registries["controls"].items():
        decision_id = item.get("acceptance_decision_id")
        if decision_id is not None and decision_id not in decision_map:
            error("UNKNOWN_CONTROL_ACCEPTANCE_DECISION", f"controls.{identifier}.acceptance_decision_id", f"unknown decision {decision_id}")
        if item.get("status") == "accepted":
            if decision_id not in decision_map or decision_map.get(decision_id, {}).get("status") != "accepted":
                error("CONTROL_ACCEPTED_WITHOUT_DECISION", f"controls.{identifier}.status", "accepted control requires an accepted decision")

    for position, node_id in enumerate(current_path):
        if node_id not in hierarchy_map:
            error("UNKNOWN_CURRENT_NODE", f"current.path[{position}]", f"unknown hierarchy node {node_id}")
            continue
        if position == 0:
            if hierarchy_map[node_id].get("parent_id") is not None:
                error("CURRENT_PATH_NOT_ROOTED", "current.path[0]", "first current-path node must be a root")
        else:
            previous = current_path[position - 1]
            if hierarchy_map[node_id].get("parent_id") != previous:
                error("BROKEN_CURRENT_PATH", f"current.path[{position}]", f"{node_id} is not a child of {previous}")
    commitment_id = current.get("active_commitment_id")
    if commitment_id is not None:
        if commitment_id not in work_map:
            error("UNKNOWN_ACTIVE_COMMITMENT", "current.active_commitment_id", f"unknown work package {commitment_id}")
        elif current_path and work_map[commitment_id].get("parent_id") != current_path[-1]:
            error("COMMITMENT_PATH_MISMATCH", "current.active_commitment_id", "active commitment does not belong to the current hierarchy leaf")

    for identifier, item in hierarchy_map.items():
        if item.get("status") != "complete":
            continue
        open_criteria = [criterion_id for criterion_id in item.get("exit_criteria_ids", []) if criterion_map.get(criterion_id, {}).get("status") not in {"verified", "accepted", "waived"}]
        if open_criteria:
            error("COMPLETE_NODE_WITH_OPEN_CRITERIA", f"hierarchy.{identifier}.status", f"complete hierarchy node has open criteria: {open_criteria}")
        open_children = [child_id for child_id, child in hierarchy_map.items() if child.get("parent_id") == identifier and child.get("status") not in {"complete", "cancelled", "superseded"}]
        if open_children:
            error("COMPLETE_NODE_WITH_OPEN_CHILDREN", f"hierarchy.{identifier}.status", f"complete hierarchy node has open children: {open_children}")
        open_work = [work_id for work_id, work in work_map.items() if work.get("parent_id") == identifier and work.get("status") not in {"complete", "cancelled"}]
        if open_work:
            error("COMPLETE_NODE_WITH_OPEN_WORK", f"hierarchy.{identifier}.status", f"complete hierarchy node has open work: {open_work}")

    unit_id = contract.get("unit_id")
    project_id = project.get("id")
    if unit_id not in hierarchy_map and unit_id not in work_map and unit_id != project_id:
        error("UNKNOWN_COMPLETION_UNIT", "completion_contract.unit_id", f"unknown unit {unit_id}")
    if unit_id != project_id:
        allowed_targets = set()
        if current_path:
            allowed_targets.add(current_path[-1])
        if commitment_id is not None:
            allowed_targets.add(commitment_id)
        if unit_id not in allowed_targets:
            error("COMPLETION_TARGET_MISMATCH", "completion_contract.unit_id", "completion contract must target the current hierarchy leaf, active commitment, or project closeout")

    required_states = [item for item in completion_states if isinstance(item, dict) and item.get("required") is True]
    if not required_states:
        error("NO_REQUIRED_COMPLETION_STATE", "completion_contract.states", "at least one completion state must be required")
    completion_done = bool(required_states)
    completion_unknown = False
    for index, item in enumerate(completion_states):
        if not isinstance(item, dict):
            completion_done = False
            continue
        path = f"completion_contract.states[{index}]"
        status = item.get("status")
        required_state = item.get("required") is True
        evidence_ids = item.get("evidence_ids", [])
        for evidence_id in evidence_ids:
            if evidence_id not in evidence_map:
                error("UNKNOWN_COMPLETION_EVIDENCE", f"{path}.evidence_ids", f"unknown evidence {evidence_id}")
        if status == "satisfied":
            if not evidence_ids:
                error("SATISFIED_WITHOUT_EVIDENCE", f"{path}.status", "satisfied state requires named evidence")
            unsupported = [evidence_id for evidence_id in evidence_ids if evidence_map.get(evidence_id, {}).get("level") not in {"verified", "accepted"}]
            if unsupported:
                error("INSUFFICIENT_COMPLETION_EVIDENCE", f"{path}.evidence_ids", f"satisfied state requires verified or accepted evidence: {unsupported}")
        waiver_id = item.get("waiver_decision_id")
        if status == "waived":
            if waiver_id not in decision_map or decision_map.get(waiver_id, {}).get("status") != "accepted":
                error("INVALID_COMPLETION_WAIVER", f"{path}.waiver_decision_id", "waiver requires an accepted decision")
        elif waiver_id is not None:
            warn("UNUSED_COMPLETION_WAIVER", f"{path}.waiver_decision_id", "waiver decision is named but state is not waived")
        if required_state and status == "not_applicable":
            error("REQUIRED_NOT_APPLICABLE", f"{path}.status", "required completion state cannot be not_applicable")
        if required_state and status not in {"satisfied", "waived"}:
            completion_done = False
        if required_state and status == "unknown":
            completion_unknown = True

    if unit_id == project_id:
        unit_recorded_complete = project.get("status") == "closed"
    elif unit_id in hierarchy_map:
        unit_recorded_complete = hierarchy_map[unit_id].get("status") == "complete"
    elif unit_id in work_map:
        unit_recorded_complete = work_map[unit_id].get("status") == "complete"
    else:
        unit_recorded_complete = False

    if unit_recorded_complete and not completion_done:
        error("FALSE_RECORDED_COMPLETE", "completion_contract", "the completion unit is recorded complete while required states remain open")
    if current.get("posture") == "complete" and (not completion_done or not unit_recorded_complete):
        error("FALSE_COMPLETE_POSTURE", "current.posture", "complete posture requires both a satisfied contract and a formally complete unit")

    if project.get("status") == "closed":
        if unit_id != project_id:
            error("PROJECT_CLOSEOUT_TARGET", "completion_contract.unit_id", "a closed project requires a project-level completion contract")
        if not completion_done:
            error("FALSE_CLOSED_PROJECT", "project.status", "project cannot be closed while required project completion states remain open")
        open_nodes = [identifier for identifier, item in hierarchy_map.items() if item.get("status") not in {"complete", "cancelled", "superseded"}]
        if open_nodes:
            error("CLOSED_PROJECT_WITH_OPEN_NODES", "project.status", f"closed project has open hierarchy nodes: {open_nodes}")
        open_work = [identifier for identifier, item in work_map.items() if item.get("status") not in {"complete", "cancelled"}]
        if open_work:
            error("CLOSED_PROJECT_WITH_OPEN_WORK", "project.status", f"closed project has open work: {open_work}")
        if current.get("posture") != "complete":
            error("CLOSED_PROJECT_POSTURE", "current.posture", "a closed project must have complete control posture")
    for identifier, item in registries["checkpoints"].items():
        checkpoint_path = item.get("hierarchy_path", [])
        previous: str | None = None
        for position, node_id in enumerate(checkpoint_path):
            if node_id not in hierarchy_map:
                error("UNKNOWN_CHECKPOINT_NODE", f"checkpoints.{identifier}.hierarchy_path[{position}]", f"unknown hierarchy node {node_id}")
            elif previous is None:
                if hierarchy_map[node_id].get("parent_id") is not None:
                    error("CHECKPOINT_PATH_NOT_ROOTED", f"checkpoints.{identifier}.hierarchy_path[0]", "checkpoint path must begin at a root")
            elif hierarchy_map[node_id].get("parent_id") != previous:
                error("BROKEN_CHECKPOINT_PATH", f"checkpoints.{identifier}.hierarchy_path[{position}]", f"{node_id} is not a child of {previous}")
            previous = node_id

    if completion_done and not errors:
        warn("READY_FOR_CLOSEOUT_REVIEW", "completion_contract", "all required states are evidenced or waived; human closeout review is still required")
    if completion_unknown:
        warn("UNKNOWN_COMPLETION_STATE", "completion_contract", "one or more required completion states are explicitly unknown")
    forecast = record.get("forecast", {})
    if isinstance(forecast, dict) and isinstance(forecast.get("lower"), (int, float)) and isinstance(forecast.get("upper"), (int, float)) and forecast["lower"] > forecast["upper"]:
        error("FORECAST_RANGE", "forecast", "lower bound cannot exceed upper bound")
    capacity = record.get("capacity", {})
    if isinstance(capacity, dict) and isinstance(capacity.get("active_wip"), int) and isinstance(capacity.get("wip_limit"), int) and capacity["active_wip"] > capacity["wip_limit"]:
        warn("WIP_LIMIT_EXCEEDED", "capacity.active_wip", "active WIP exceeds the declared limit; record the exception decision")
    if not lists["benefits"]:
        warn("NO_BENEFIT_REGISTER", "benefits", "no measurable benefit is recorded")
    if not lists["stakeholders"]:
        warn("NO_STAKEHOLDER_REGISTER", "stakeholders", "no stakeholder readiness or incentive state is recorded")
    if not lists["checkpoints"]:
        warn("NO_CHECKPOINT", "checkpoints", "no durable recovery checkpoint is recorded")

    return errors, warnings


def completion_posture(
    record: dict[str, Any],
    validation_errors: list[dict[str, str]] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    if validation_errors is None:
        validation_errors, _warnings = validate_record(record)
    contract = record.get("completion_contract", {})
    states = contract.get("states", []) if isinstance(contract, dict) else []
    required = [item for item in states if isinstance(item, dict) and item.get("required") is True]
    if validation_errors:
        return "INVALID", states
    if not required or any(item.get("status") == "unknown" for item in required):
        return "UNKNOWN", states
    if all(item.get("status") in {"satisfied", "waived"} for item in required):
        project = record.get("project", {}) if isinstance(record.get("project"), dict) else {}
        hierarchy = {
            item.get("id"): item for item in record.get("hierarchy", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        } if isinstance(record.get("hierarchy"), list) else {}
        work = {
            item.get("id"): item for item in record.get("work_packages", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        } if isinstance(record.get("work_packages"), list) else {}
        unit_id = contract.get("unit_id")
        if unit_id == project.get("id"):
            recorded_complete = project.get("status") == "closed"
        elif unit_id in hierarchy:
            recorded_complete = hierarchy[unit_id].get("status") == "complete"
        else:
            recorded_complete = work.get(unit_id, {}).get("status") == "complete"
        return ("YES" if recorded_complete else "NO"), states
    return "NO", states


def render_status(record: dict[str, Any]) -> str:
    errors, warnings = validate_record(record)
    project = record.get("project", {}) if isinstance(record.get("project"), dict) else {}
    current = record.get("current", {}) if isinstance(record.get("current"), dict) else {}
    hierarchy_items = record.get("hierarchy", []) if isinstance(record.get("hierarchy"), list) else []
    work_items = record.get("work_packages", []) if isinstance(record.get("work_packages"), list) else []
    hierarchy = {
        item.get("id"): item for item in hierarchy_items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    work = {
        item.get("id"): item for item in work_items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    path_ids = current.get("path", []) if isinstance(current.get("path"), list) else []
    path_labels = [hierarchy.get(identifier, {}).get("label", identifier) for identifier in path_ids]
    done, states = completion_posture(record, errors)
    contract = record.get("completion_contract", {}) if isinstance(record.get("completion_contract"), dict) else {}
    unit_id = contract.get("unit_id", "unknown")
    if unit_id == project.get("id"):
        unit_label = project.get("name", unit_id)
    else:
        unit_label = hierarchy.get(unit_id, {}).get("label", work.get(unit_id, {}).get("outcome", unit_id))
    commitment_id = current.get("active_commitment_id")
    commitment = work.get(commitment_id, {}) if commitment_id is not None else {}

    latest_checkpoint = None
    checkpoints = record.get("checkpoints", [])
    if isinstance(checkpoints, list):
        dated: list[tuple[datetime, dict[str, Any]]] = []
        for item in checkpoints:
            if not isinstance(item, dict) or not isinstance(item.get("timestamp"), str):
                continue
            try:
                dated.append((parse_timestamp(item["timestamp"]), item))
            except ValueError:
                continue
        if dated:
            latest_checkpoint = max(dated, key=lambda pair: pair[0])[1]

    lines = [
        f"# Project status - {project.get('name', 'Unnamed project')}",
        "",
        f"**Is the active completion unit done? {done}.**",
        f"Unit: `{unit_id}` - {unit_label}",
        f"Project state: `{project.get('status', 'unknown')}` | Control posture: `{current.get('posture', 'unknown')}` | As of: {current.get('as_of', 'unknown')}",
        f"Current path: {' > '.join(path_labels) if path_labels else 'unknown'}",
        "",
        "## Purpose",
        "",
        str(project.get("outcome", "Unknown outcome")),
        "",
        str(current.get("purpose_connection", "Purpose connection not recorded.")),
        "",
        "## Continued justification and benefits",
        "",
        f"- Justification: `{record.get('justification', {}).get('status', 'unknown')}` - {record.get('justification', {}).get('reason', 'Not recorded.')}",
        f"- Sponsor: {record.get('governance', {}).get('sponsor', 'unknown')}",
        f"- Benefit owner: {record.get('justification', {}).get('benefit_owner', 'unknown')}",
        f"- Benefits tracked: {len(record.get('benefits', [])) if isinstance(record.get('benefits'), list) else 0}",
        "",
        "## Forecast and capacity",
        "",
        f"- Forecast: {record.get('forecast', {}).get('lower', '?')} to {record.get('forecast', {}).get('upper', '?')} {record.get('forecast', {}).get('unit', '')} at `{record.get('forecast', {}).get('confidence', 'unknown')}` confidence",
        f"- Basis: {record.get('forecast', {}).get('basis', 'Not recorded.')}",
        f"- WIP: {record.get('capacity', {}).get('active_wip', '?')}/{record.get('capacity', {}).get('wip_limit', '?')} | Bottleneck: {record.get('capacity', {}).get('bottleneck', 'unknown')}",
        "",        "## Active commitment",
        "",
        f"- ID: `{commitment_id or 'none'}`",
        f"- Outcome: {commitment.get('outcome', 'No active commitment recorded.')}",
        f"- State: `{commitment.get('status', 'none')}`",
        f"- Next action: {current.get('next_action', commitment.get('next_action', 'Not recorded.'))}",
        f"- Next decision: {current.get('next_decision') or 'None recorded.'}",
        "",
        "## Completion contract",
        "",
    ]
    if states:
        for item in states:
            evidence_ids = item.get("evidence_ids", []) if isinstance(item.get("evidence_ids"), list) else []
            evidence_text = ", ".join(f"`{identifier}`" for identifier in evidence_ids) or "none"
            requirement = "required" if item.get("required") is True else "optional"
            lines.append(f"- **{item.get('name', 'UNNAMED')}** ({requirement}): `{item.get('status', 'unknown')}`; evidence: {evidence_text}")
    else:
        lines.append("- No required completion states are recorded.")

    lines.extend(["", "## Authority and constraints", ""])
    authority = record.get("authority", {}) if isinstance(record.get("authority"), dict) else {}
    lines.append(f"- Project owner: {authority.get('project_owner', 'unknown')}")
    reserved = authority.get("reserved", []) if isinstance(authority.get("reserved"), list) else []
    if reserved:
        lines.append(f"- Reserved actions: {'; '.join(str(item) for item in reserved)}")
    grants = authority.get("grants", []) if isinstance(authority.get("grants"), list) else []
    active_grants = [item for item in grants if isinstance(item, dict) and item.get("status") == "active"]
    lines.append(f"- Active authority grants: {len(active_grants)}")

    lines.extend(["", "## Live controls", ""])
    controls = record.get("controls", []) if isinstance(record.get("controls"), list) else []
    live_controls = [
        item for item in controls
        if isinstance(item, dict) and item.get("status") in {"open", "watch", "blocked"}
    ]
    if live_controls:
        for item in live_controls:
            lines.append(
                f"- `{item.get('id', 'unknown')}` {item.get('kind', 'control')} / {item.get('status', 'unknown')}: "
                f"{item.get('description', 'No description.')} Next: {item.get('next_action', 'Not recorded.')}"
            )
    else:
        lines.append("- No open, watch, or blocked controls recorded.")

    lines.extend(["", "## Latest recovery checkpoint", ""])
    if latest_checkpoint:
        lines.append(f"- Timestamp: {latest_checkpoint.get('timestamp', 'unknown')}")
        remaining = latest_checkpoint.get("remaining", [])
        blockers = latest_checkpoint.get("blockers", [])
        lines.append(f"- Remaining: {'; '.join(str(item) for item in remaining) if remaining else 'Nothing recorded.'}")
        lines.append(f"- Blockers: {'; '.join(str(item) for item in blockers) if blockers else 'None recorded.'}")
        repository_state = latest_checkpoint.get("repository_state")
        if isinstance(repository_state, dict):
            lines.append(
                "- Repository: "
                f"branch `{repository_state.get('branch', 'unknown')}`, "
                f"head `{repository_state.get('head', 'unknown')}`, "
                f"worktree `{repository_state.get('worktree', 'unknown')}`, "
                f"remote `{repository_state.get('remote_state', 'unknown')}`"
            )
    else:
        lines.append("- No valid timestamped checkpoint recorded.")

    lines.extend([
        "",
        "## Record integrity",
        "",
        f"- Structural errors: {len(errors)}",
        f"- Warnings: {len(warnings)}",
    ])
    for item in errors:
        lines.append(f"- ERROR `{item['code']}` at `{item['path']}`: {item['message']}")
    for item in warnings:
        lines.append(f"- WARNING `{item['code']}` at `{item['path']}`: {item['message']}")
    lines.extend([
        f"- Fingerprint: `{fingerprint(record)}`",
        f"- Boundary: `{BOUNDARY}` - this report does not independently prove delivery or acceptance.",
    ])
    return "\n".join(lines) + "\n"

def slug_identifier(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if len(slug) < 2:
        slug = f"project-{slug or 'new'}"
    return slug[:120]


def resolve_store(
    explicit: Path | None = None,
    environ: dict[str, str] | None = None,
    home: Path | None = None,
) -> tuple[Path, str]:
    """Resolve the project-record estate without creating filesystem state."""
    environment = os.environ if environ is None else environ
    if explicit is not None:
        raw = explicit
        source = "explicit"
    elif environment.get(STORE_ENV_VAR, "").strip():
        raw = Path(environment[STORE_ENV_VAR].strip())
        source = "environment"
    else:
        raise ValueError(
            "DENNIS_PROJECT_HOME is required in Nova Emergent; use Nova Operations to configure the governed Nova estate"
        )
    return raw.expanduser().resolve(strict=False), source


def store_marker() -> dict[str, Any]:
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "record_schema": SCHEMA_VERSION,
        "layout": "projects/<stable-project-key>/{project-control.json,records/}",
        "network_dependencies": [],
    }


def ensure_store_marker(store: Path) -> None:
    marker_path = store / "store.json"
    if marker_path.exists():
        marker = load_record(marker_path)
        if marker.get("schema_version") != STORE_SCHEMA_VERSION:
            raise ValueError(f"unsupported project-record store marker: {marker_path}")
        if marker.get("record_schema") != SCHEMA_VERSION:
            raise ValueError(f"project-record store uses an unsupported record schema: {marker_path}")
        return
    write_json_document(marker_path, store_marker(), False)


def record_source_locators(record: dict[str, Any]) -> list[str]:
    items = record.get("source_authority", [])
    if not isinstance(items, list):
        return []
    return [
        str(item.get("locator"))
        for item in items
        if isinstance(item, dict) and isinstance(item.get("locator"), str)
    ]


def scan_store(store: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Inspect canonical project controls without repairing or creating the store."""
    rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, str]] = []
    projects = store / "projects"
    if not projects.is_dir():
        return rows, diagnostics
    for path in sorted(projects.glob("*/project-control.json"), key=lambda item: str(item).casefold()):
        try:
            record = load_record(path)
            project = record.get("project", {}) if isinstance(record.get("project"), dict) else {}
            rows.append({
                "path": path.resolve(),
                "relative_path": path.relative_to(store).as_posix(),
                "project_id": project.get("id"),
                "project_name": project.get("name"),
                "source_locators": record_source_locators(record),
                "fingerprint": fingerprint(record),
                "record": record,
            })
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            diagnostics.append({"path": str(path.resolve()), "message": str(exc)})
    return rows, diagnostics


def match_store_rows(
    rows: list[dict[str, Any]],
    project_id: str | None = None,
    project_name: str | None = None,
    source_locator: str | None = None,
) -> list[dict[str, Any]]:
    if not any((project_id, project_name, source_locator)):
        raise ValueError("locate requires --project-id, --project-name, or --source-locator")
    matches = []
    for row in rows:
        if project_id is not None and row["project_id"] != project_id:
            continue
        if project_name is not None and str(row["project_name"]).casefold() != project_name.casefold():
            continue
        if source_locator is not None and source_locator not in row["source_locators"]:
            continue
        matches.append(row)
    return matches


def public_store_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: str(value) if isinstance(value, Path) else value for key, value in row.items() if key != "record"}


def locate_in_store(
    store: Path,
    project_id: str | None = None,
    project_name: str | None = None,
    source_locator: str | None = None,
) -> dict[str, Any]:
    rows, diagnostics = scan_store(store)
    matches = match_store_rows(rows, project_id, project_name, source_locator)
    if len(matches) > 1:
        paths = ", ".join(str(item["path"]) for item in matches)
        raise ValueError(f"project selectors are ambiguous across: {paths}")
    return {
        "boundary": BOUNDARY,
        "store": str(store),
        "store_exists": store.is_dir(),
        "found": len(matches) == 1,
        "match": public_store_row(matches[0]) if matches else None,
        "diagnostics": diagnostics,
    }


def project_directory(store: Path, project_id: str, project_name: str) -> Path:
    return store / "projects" / slug_identifier(project_id or project_name)


def ensure_project(
    store: Path,
    project_name: str,
    owner: str,
    outcome: str,
    project_id: str | None = None,
    source_locator: str | None = None,
) -> dict[str, Any]:
    stable_id = project_id or slug_identifier(project_name)
    rows, diagnostics = scan_store(store)
    id_matches = [row for row in rows if row["project_id"] == stable_id]
    if len(id_matches) > 1:
        raise ValueError(f"project ID {stable_id!r} identifies multiple store records")
    if id_matches:
        existing = id_matches[0]
        if str(existing["project_name"]).casefold() != project_name.casefold():
            raise ValueError(f"project ID {stable_id!r} already belongs to {existing['project_name']!r}")
        errors, _warnings = validate_record(existing["record"])
        if errors:
            raise ValueError(f"existing project record has {len(errors)} validation errors")
        records_directory = existing["path"].parent / "records"
        records_directory.mkdir(parents=True, exist_ok=True)
        return {
            "boundary": BOUNDARY,
            "store": str(store),
            "created": False,
            "record": public_store_row(existing),
            "records_directory": str(records_directory),
            "diagnostics": diagnostics,
        }

    identity_conflicts = [
        row for row in rows
        if str(row["project_name"]).casefold() == project_name.casefold()
        or (source_locator is not None and source_locator in row["source_locators"])
    ]
    if identity_conflicts:
        paths = ", ".join(str(item["path"]) for item in identity_conflicts)
        raise ValueError(f"project identity conflicts with existing store record(s): {paths}")

    record = bootstrap_record(project_name, owner, outcome, stable_id, source_locator)
    errors, warnings = validate_record(record)
    if errors:
        raise ValueError(f"maintained bootstrap template produced {len(errors)} validation errors")
    directory = project_directory(store, stable_id, project_name)
    record_path = directory / "project-control.json"
    if directory.exists():
        raise FileExistsError(f"refusing to claim an existing unregistered project directory: {directory}")
    ensure_store_marker(store)
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "records").mkdir()
    write_record(record_path, record, False)
    row = {
        "path": record_path.resolve(),
        "relative_path": record_path.relative_to(store).as_posix(),
        "project_id": stable_id,
        "project_name": project_name,
        "source_locators": record_source_locators(record),
        "fingerprint": fingerprint(record),
        "record": record,
    }
    return {
        "boundary": BOUNDARY,
        "store": str(store),
        "created": True,
        "record": public_store_row(row),
        "records_directory": str(directory / "records"),
        "warnings": warnings,
        "diagnostics": diagnostics,
    }


def adopt_project(store: Path, source: Path) -> dict[str, Any]:
    source_bytes = source.read_bytes()
    record = load_record(source)
    if record.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"adopt requires {SCHEMA_VERSION}; migrate v1 explicitly first")
    errors, warnings = validate_record(record)
    if errors:
        raise ValueError(f"adopt requires a valid v2 record; found {len(errors)} validation errors")
    project = record.get("project", {})
    project_id = project.get("id")
    project_name = project.get("name")
    if not isinstance(project_id, str) or not isinstance(project_name, str):
        raise ValueError("adopt requires project.id and project.name")
    rows, diagnostics = scan_store(store)
    conflicts = [row for row in rows if row["project_id"] == project_id]
    if conflicts:
        if len(conflicts) == 1 and conflicts[0]["fingerprint"] == fingerprint(record):
            return {
                "boundary": BOUNDARY,
                "store": str(store),
                "created": False,
                "record": public_store_row(conflicts[0]),
                "source_preserved": source.read_bytes() == source_bytes,
                "warnings": warnings,
                "diagnostics": diagnostics,
            }
        raise ValueError(f"project ID {project_id!r} already exists with different canonical content")
    directory = project_directory(store, project_id, project_name)
    if directory.exists():
        raise FileExistsError(f"refusing to claim an existing unregistered project directory: {directory}")
    ensure_store_marker(store)
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "records").mkdir()
    record_path = directory / "project-control.json"
    write_record(record_path, record, False)
    if source.read_bytes() != source_bytes:
        raise ValueError("external source changed during adoption")
    row = {
        "path": record_path.resolve(),
        "relative_path": record_path.relative_to(store).as_posix(),
        "project_id": project_id,
        "project_name": project_name,
        "source_locators": record_source_locators(record),
        "fingerprint": fingerprint(record),
        "record": record,
    }
    return {
        "boundary": BOUNDARY,
        "store": str(store),
        "created": True,
        "record": public_store_row(row),
        "records_directory": str(directory / "records"),
        "source": str(source.resolve()),
        "source_preserved": True,
        "warnings": warnings,
        "diagnostics": diagnostics,
    }


def bootstrap_record(project_name: str, owner: str, outcome: str, project_id: str | None = None, source_locator: str | None = None) -> dict[str, Any]:
    template_path = Path(__file__).resolve().parent.parent / "assets" / "project-control.template.json"
    record = load_record(template_path)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    record["project"].update({
        "id": project_id or slug_identifier(project_name),
        "name": project_name,
        "outcome": outcome,
        "owner": owner,
        "updated_at": now,
    })
    record["source_authority"][0].update({
        "locator": source_locator or "Explicit project-owner request captured during bootstrap",
        "observed_at": now,
    })
    record["authority"]["project_owner"] = owner
    record["authority"]["grants"][0]["effective_at"] = now
    record["current"]["as_of"] = now
    record["checkpoints"][0]["timestamp"] = now
    return record


def migrate_v1(record: dict[str, Any]) -> dict[str, Any]:
    """Create an explicit v2 derivative while preserving the supplied v1 record."""
    if record.get("schema_version") != LEGACY_SCHEMA_VERSION:
        raise ValueError(f"migrate requires {LEGACY_SCHEMA_VERSION}")
    migrated = json.loads(json.dumps(record, ensure_ascii=False))
    stamp = migrated.get("project", {}).get("updated_at", "unknown")
    owner = migrated.get("project", {}).get("owner", "Project owner")
    migrated["schema_version"] = SCHEMA_VERSION
    migrated["justification"] = {"status": "proposed", "reason": "Reconfirm why this project remains the best intervention.", "alternatives": ["Reassess the do-nothing and lower-cost alternatives."], "viability": "Not yet reassessed during migration.", "sponsor": owner, "benefit_owner": owner, "last_reviewed_at": stamp, "revisit_trigger": "Value, viability, cost, risk, or strategic fit changes."}
    migrated["benefits"] = []
    migrated["governance"] = {"sponsor": owner, "accountable_owner": owner, "cadence": "Reconfirm the governance cadence after migration.", "tolerances": ["Escalate material scope, forecast, benefit, risk, quality, or capacity exceptions."], "gates": [], "decision_latency_target": "Reconfirm after migration."}
    migrated["forecast"] = {"as_of": stamp, "unit": "unspecified", "lower": 0, "upper": 0, "confidence": "low", "basis": "No v1 forecast migrated.", "baseline": "Reconfirm after migration.", "variance": "Unknown.", "next_update": "At the next project-control review."}
    migrated["capacity"] = {"constraints": ["Capacity was not first-class in v1; reassess it."], "bottleneck": "Unknown after migration.", "wip_limit": 1, "active_wip": 0, "queue": [], "next_action": "Assess capacity, WIP, queue, and bottleneck."}
    migrated["stakeholders"] = []
    migrated["commercial_alignment"] = []
    for control in migrated.get("controls", []):
        description = control.get("description", "Legacy control")
        control.setdefault("objective", f"Control the consequence of: {description}")
        control.setdefault("cause_event_effect", f"Legacy v1 control; restate cause, event, and effect for: {description}")
        control.setdefault("exposure", "Reassess exposure after migration.")
        control.setdefault("treatment", control.get("next_action", "Define treatment."))
        control.setdefault("resource_commitment", "Reconfirm the resources committed to treatment.")
        control.setdefault("residual_state", "Reassess residual exposure after treatment.")
        control.setdefault("escalation_threshold", control.get("trigger", "Define an escalation threshold."))
        control.setdefault("acceptance_decision_id", None)
    migrated["transition"] = {"operational_owner": owner, "acceptance_state": "not_ready", "support_state": "not_ready", "benefit_review_owner": owner, "benefit_review_at": "Reconfirm after migration.", "residuals": ["Operational acceptance, support readiness, and benefit review require confirmation."], "evidence_ids": []}
    return migrated

def require_distinct_migration_paths(source: Path, output: Path) -> None:
    """Reject any output path that identifies the source record."""
    source_resolved = source.resolve(strict=True)
    output_resolved = output.resolve(strict=False)
    if source_resolved == output_resolved:
        raise ValueError("migration output must be distinct from the source record")
    if output.exists() and source_resolved.samefile(output):
        raise ValueError("migration output must not alias the source record")


def write_record(path: Path, record: dict[str, Any], force: bool) -> None:
    write_json_document(path, record, force)


def write_json_document(path: Path, value: dict[str, Any], force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"refusing to overwrite existing record: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    temporary.write_text(payload, encoding="utf-8", newline="\n")
    temporary.replace(path)


def write_text(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"refusing to overwrite existing output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)

def print_validation(path: Path, record: dict[str, Any], as_json: bool) -> int:
    errors, warnings = validate_record(record)
    payload = {
        "boundary": BOUNDARY,
        "path": str(path.resolve()),
        "schema_version": record.get("schema_version"),
        "valid": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "fingerprint": fingerprint(record),
    }
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        verdict = "VALID" if payload["valid"] else "INVALID"
        print(f"{verdict} - {path}")
        print(f"Boundary: {BOUNDARY}")
        print(f"Errors: {len(errors)} | Warnings: {len(warnings)}")
        for item in errors:
            print(f"ERROR {item['code']} at {item['path']}: {item['message']}")
        for item in warnings:
            print(f"WARNING {item['code']} at {item['path']}: {item['message']}")
        print(f"Fingerprint: {payload['fingerprint']}")
    return 0 if not errors else 2

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Structural control for cd-project-control/v2 records with explicit v1 migration; never a substitute for project judgment."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate structure and semantic references")
    validate_parser.add_argument("record", type=Path)
    validate_parser.add_argument("--json", action="store_true", help="emit machine-readable diagnostics")

    fingerprint_parser = subparsers.add_parser("fingerprint", help="print the canonical SHA-256 fingerprint")
    fingerprint_parser.add_argument("record", type=Path)
    fingerprint_parser.add_argument("--json", action="store_true", help="emit a JSON result")

    status_parser = subparsers.add_parser("status", help="render a project-scale Markdown status brief")
    status_parser.add_argument("record", type=Path)
    status_parser.add_argument("--output", type=Path, help="write the Markdown report atomically")
    status_parser.add_argument("--force", action="store_true", help="replace an existing output path")

    migrate_parser = subparsers.add_parser("migrate", help="create an explicit v2 derivative from a v1 record")
    migrate_parser.add_argument("record", type=Path)
    migrate_parser.add_argument("output", type=Path)
    migrate_parser.add_argument("--force", action="store_true", help="replace an existing output path")
    bootstrap_parser = subparsers.add_parser("bootstrap", help="create a project-control record from the maintained template")
    bootstrap_parser.add_argument("output", type=Path)
    bootstrap_parser.add_argument("--project-name", required=True)
    bootstrap_parser.add_argument("--owner", required=True)
    bootstrap_parser.add_argument("--outcome", required=True)
    bootstrap_parser.add_argument("--project-id")
    bootstrap_parser.add_argument("--source-locator", help="locator for the project-owner authority source")
    bootstrap_parser.add_argument("--force", action="store_true", help="replace an existing output path")

    store_path_parser = subparsers.add_parser("store-path", help="resolve the centralized project-record estate without creating it")
    store_path_parser.add_argument("--store", type=Path, help=f"override {STORE_ENV_VAR} and the user-scoped default")

    locate_parser = subparsers.add_parser("locate", help="locate one canonical project record without creating state")
    locate_parser.add_argument("--store", type=Path, help=f"override {STORE_ENV_VAR} and the user-scoped default")
    locate_parser.add_argument("--project-id")
    locate_parser.add_argument("--project-name")
    locate_parser.add_argument("--source-locator")

    ensure_parser = subparsers.add_parser("ensure", help="return an existing project record or create one in the centralized estate")
    ensure_parser.add_argument("--store", type=Path, help=f"override {STORE_ENV_VAR} and the user-scoped default")
    ensure_parser.add_argument("--project-name", required=True)
    ensure_parser.add_argument("--owner", required=True)
    ensure_parser.add_argument("--outcome", required=True)
    ensure_parser.add_argument("--project-id")
    ensure_parser.add_argument("--source-locator")

    adopt_parser = subparsers.add_parser("adopt", help="copy a validated external v2 record into centralized custody")
    adopt_parser.add_argument("record", type=Path)
    adopt_parser.add_argument("--store", type=Path, help=f"override {STORE_ENV_VAR} and the user-scoped default")

    list_parser = subparsers.add_parser("list-projects", help="list canonical project controls and malformed store entries")
    list_parser.add_argument("--store", type=Path, help=f"override {STORE_ENV_VAR} and the user-scoped default")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command in {"store-path", "locate", "ensure", "adopt", "list-projects"}:
            store, source = resolve_store(args.store)
            if args.command == "store-path":
                print(json.dumps({
                    "boundary": BOUNDARY,
                    "store": str(store),
                    "source": source,
                    "environment_variable": STORE_ENV_VAR,
                    "exists": store.is_dir(),
                }, ensure_ascii=False, indent=2))
                return 0
            if args.command == "locate":
                result = locate_in_store(store, args.project_id, args.project_name, args.source_locator)
                result["store_source"] = source
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 0
            if args.command == "ensure":
                if args.project_id is not None and not ID_PATTERN.fullmatch(args.project_id):
                    raise ValueError("--project-id must match the stable identifier pattern")
                result = ensure_project(store, args.project_name, args.owner, args.outcome, args.project_id, args.source_locator)
                result["store_source"] = source
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 0
            if args.command == "adopt":
                result = adopt_project(store, args.record)
                result["store_source"] = source
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 0
            rows, diagnostics = scan_store(store)
            print(json.dumps({
                "boundary": BOUNDARY,
                "store": str(store),
                "store_source": source,
                "projects": [public_store_row(row) for row in rows],
                "diagnostics": diagnostics,
            }, ensure_ascii=False, indent=2))
            return 0
        if args.command == "migrate":
            require_distinct_migration_paths(args.record, args.output)
            legacy = load_record(args.record)
            record = migrate_v1(legacy)
            errors, warnings = validate_record(record)
            if errors:
                raise ValueError(f"migrated record produced {len(errors)} validation errors")
            write_record(args.output, record, args.force)
            print(json.dumps({"boundary": BOUNDARY, "created": str(args.output.resolve()), "warnings": warnings, "fingerprint": fingerprint(record)}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "bootstrap":
            if args.project_id is not None and not ID_PATTERN.fullmatch(args.project_id):
                raise ValueError("--project-id must match the stable identifier pattern")
            record = bootstrap_record(args.project_name, args.owner, args.outcome, args.project_id, args.source_locator)
            errors, warnings = validate_record(record)
            if errors:
                raise ValueError(f"maintained bootstrap template produced {len(errors)} validation errors")
            write_record(args.output, record, args.force)
            print(json.dumps({
                "boundary": BOUNDARY,
                "created": str(args.output.resolve()),
                "warnings": warnings,
                "fingerprint": fingerprint(record),
            }, ensure_ascii=False, indent=2))
            return 0

        record = load_record(args.record)
        if args.command == "validate":
            return print_validation(args.record, record, args.json)
        if args.command == "fingerprint":
            digest = fingerprint(record)
            if args.json:
                print(json.dumps({"boundary": BOUNDARY, "path": str(args.record.resolve()), "fingerprint": digest}, indent=2))
            else:
                print(digest)
            return 0
        if args.command == "status":
            errors, _warnings = validate_record(record)
            rendered = render_status(record)
            if args.output is not None:
                write_text(args.output, rendered, args.force)
            else:
                print(rendered, end="")
            return 0 if not errors else 2
        raise ValueError(f"unsupported command: {args.command}")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"project_control: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
