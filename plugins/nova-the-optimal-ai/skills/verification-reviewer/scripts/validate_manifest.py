#!/usr/bin/env python3
"""Validate a TestForge manifest structurally and semantically."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common.filesystem import is_within, load_data, write_json

REQUIRED = {"manifest_version", "target", "scope", "claim_custody", "risks", "scenarios", "tests", "executions", "findings", "residual_risks", "review", "decision"}
RELEASE_STATUSES = {"READY", "READY_WITH_RESIDUAL_RISK", "NOT_READY", "INSUFFICIENT_EVIDENCE", "BLOCKED_BY_ENVIRONMENT"}
REVIEW_STATUSES = {"NOT_RUN", "REVIEW_PASS", "REVIEW_PASS_WITH_CONDITIONS", "REVIEW_FAIL"}
SEVERITIES = {"critical", "high", "medium", "low"}
RISK_DISPOSITIONS = {"covered", "planned", "accepted_by_human", "blocked", "unresolved"}
TEST_STATUSES = {"designed", "unexecuted", "passed", "failed", "blocked", "not_applicable"}
EXECUTION_STATUSES = {"passed", "failed", "blocked", "interrupted", "unparsed", "not_run"}


def _ids(items: Any, label: str, errors: list[str]) -> set[str]:
    if not isinstance(items, list):
        errors.append(f"{label} must be a list")
        return set()
    seen: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            errors.append(f"{label}[{index}] requires a non-empty string id")
            continue
        if item["id"] in seen:
            errors.append(f"duplicate {label} id: {item['id']}")
        seen.add(item["id"])
    return seen


def validate(data: Any, root: Path | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return {"valid": False, "errors": ["manifest root must be an object"], "warnings": []}
    missing = sorted(REQUIRED - set(data))
    if missing: errors.append("missing required sections: " + ", ".join(missing))
    if data.get("manifest_version") != "1.0": errors.append("manifest_version must be '1.0'")
    target = data.get("target", {})
    if not isinstance(target, dict) or not target.get("name") or not target.get("revision"):
        errors.append("target requires name and revision")
    scope = data.get("scope", {})
    if not isinstance(scope, dict) or not isinstance(scope.get("included"), list) or not scope.get("included"):
        errors.append("scope.included must be a non-empty list")
    custody = data.get("claim_custody", {})
    for state in ("observed", "inferred", "assumed", "unresolved"):
        if not isinstance(custody, dict) or not isinstance(custody.get(state), list):
            errors.append(f"claim_custody.{state} must be a list")

    risk_ids = _ids(data.get("risks", []), "risks", errors)
    scenario_ids = _ids(data.get("scenarios", []), "scenarios", errors)
    test_ids = _ids(data.get("tests", []), "tests", errors)
    execution_ids = _ids(data.get("executions", []), "executions", errors)
    _ids(data.get("findings", []), "findings", errors)
    _ids(data.get("residual_risks", []), "residual_risks", errors)

    for risk in data.get("risks", []) if isinstance(data.get("risks"), list) else []:
        if not isinstance(risk, dict): continue
        if risk.get("severity") not in SEVERITIES: errors.append(f"{risk.get('id', 'risk')}: invalid severity")
        if risk.get("disposition") not in RISK_DISPOSITIONS: errors.append(f"{risk.get('id', 'risk')}: invalid disposition")
        links = risk.get("verification", [])
        if not isinstance(links, list): errors.append(f"{risk.get('id', 'risk')}: verification must be a list")
        elif risk.get("severity") == "critical" and not links and risk.get("disposition") != "accepted_by_human":
            errors.append(f"{risk.get('id', 'risk')}: critical risk has no verification disposition link")
        if risk.get("disposition") == "covered" and not links:
            errors.append(f"{risk.get('id', 'risk')}: covered risk has no linked evidence")
        if risk.get("disposition") == "accepted_by_human" and not risk.get("acceptance_authority"):
            errors.append(f"{risk.get('id', 'risk')}: accepted risk requires acceptance_authority")
        for link in links if isinstance(links, list) else []:
            if link not in scenario_ids | test_ids | execution_ids:
                errors.append(f"{risk.get('id', 'risk')}: unknown verification link {link}")

    for scenario in data.get("scenarios", []) if isinstance(data.get("scenarios"), list) else []:
        if not isinstance(scenario, dict): continue
        for risk_id in scenario.get("risk_ids", []):
            if risk_id not in risk_ids: errors.append(f"{scenario.get('id', 'scenario')}: unknown risk {risk_id}")
        if not scenario.get("expected"): errors.append(f"{scenario.get('id', 'scenario')}: expected oracle is empty")

    for test in data.get("tests", []) if isinstance(data.get("tests"), list) else []:
        if not isinstance(test, dict): continue
        test_id = test.get("id", "test")
        if test.get("status") not in TEST_STATUSES: errors.append(f"{test_id}: invalid test status")
        for scenario_id in test.get("scenario_ids", []):
            if scenario_id not in scenario_ids: errors.append(f"{test_id}: unknown scenario {scenario_id}")
        execution_id = test.get("execution_id")
        if execution_id and execution_id not in execution_ids: errors.append(f"{test_id}: unknown execution {execution_id}")
        if test.get("status") in {"passed", "failed"} and not execution_id:
            errors.append(f"{test_id}: {test.get('status')} test requires execution_id")
        if root and test.get("path") and test.get("status") != "not_applicable":
            candidate = (root / str(test["path"])).resolve()
            if not is_within(candidate, root): errors.append(f"{test_id}: path escapes root")
            elif not candidate.exists(): warnings.append(f"{test_id}: referenced path does not exist: {test['path']}")

    for execution in data.get("executions", []) if isinstance(data.get("executions"), list) else []:
        if not isinstance(execution, dict): continue
        if execution.get("status") not in EXECUTION_STATUSES: errors.append(f"{execution.get('id', 'execution')}: invalid execution status")
        if execution.get("status") in {"passed", "failed"} and not isinstance(execution.get("exit_code"), int):
            errors.append(f"{execution.get('id', 'execution')}: completed execution requires integer exit_code")

    decision = data.get("decision", {})
    status = decision.get("status") if isinstance(decision, dict) else None
    if status not in RELEASE_STATUSES: errors.append("decision.status is invalid")
    review_status = data.get("review", {}).get("status") if isinstance(data.get("review"), dict) else None
    if review_status not in REVIEW_STATUSES: errors.append("review.status is invalid")
    blockers = [r.get("id") for r in data.get("risks", []) if isinstance(r, dict) and r.get("severity") in {"critical", "high"} and r.get("disposition") in {"planned", "blocked", "unresolved"}]
    failed_tests = [t.get("id") for t in data.get("tests", []) if isinstance(t, dict) and t.get("status") == "failed"]
    if status in {"READY", "READY_WITH_RESIDUAL_RISK"}:
        if blockers: errors.append("ready status conflicts with unresolved high/critical risks: " + ", ".join(blockers))
        if failed_tests: errors.append("ready status conflicts with failed tests: " + ", ".join(failed_tests))
        if review_status not in {"REVIEW_PASS", "REVIEW_PASS_WITH_CONDITIONS"}: errors.append("ready status requires reviewer pass")
    if status == "READY" and data.get("residual_risks"):
        warnings.append("READY has residual risks; consider READY_WITH_RESIDUAL_RISK")
    return {"valid": not errors, "errors": errors, "warnings": warnings, "counts": {"risks": len(risk_ids), "scenarios": len(scenario_ids), "tests": len(test_ids), "executions": len(execution_ids)}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        data = load_data(args.manifest)
        report = validate(data, args.root.resolve() if args.root else args.manifest.parent.resolve())
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        report = {"valid": False, "errors": [str(exc)], "warnings": []}
    if args.output: write_json(args.output, report)
    else: print(json.dumps(report, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
