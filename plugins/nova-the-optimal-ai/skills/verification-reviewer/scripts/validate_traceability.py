#!/usr/bin/env python3
"""Validate risk-to-scenario-to-test-to-execution traceability."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common.filesystem import load_data, write_json


def validate(data: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    risks = {x.get("id"): x for x in data.get("risks", []) if isinstance(x, dict) and x.get("id")}
    scenarios = {x.get("id"): x for x in data.get("scenarios", []) if isinstance(x, dict) and x.get("id")}
    tests = {x.get("id"): x for x in data.get("tests", []) if isinstance(x, dict) and x.get("id")}
    executions = {x.get("id"): x for x in data.get("executions", []) if isinstance(x, dict) and x.get("id")}

    for risk_id, risk in risks.items():
        linked_scenarios = [sid for sid, s in scenarios.items() if risk_id in s.get("risk_ids", [])]
        linked_tests = [tid for tid, t in tests.items() if set(t.get("scenario_ids", [])) & set(linked_scenarios)]
        linked_evidence = [t.get("execution_id") for t in tests.values() if t.get("id") in linked_tests and t.get("execution_id") in executions and executions[t.get("execution_id")].get("status") in {"passed", "failed"}]
        if risk.get("severity") == "critical" and risk.get("disposition") != "accepted_by_human" and not linked_scenarios:
            errors.append(f"{risk_id}: critical risk has no scenario")
        if risk.get("disposition") == "covered":
            if not linked_tests: errors.append(f"{risk_id}: covered risk has no test")
            if not linked_evidence: errors.append(f"{risk_id}: covered risk has no execution evidence")
        elif linked_evidence and risk.get("disposition") in {"planned", "blocked", "unresolved"}:
            warnings.append(f"{risk_id}: execution exists but disposition remains {risk.get('disposition')}")

    for scenario_id, scenario in scenarios.items():
        if not scenario.get("risk_ids"): errors.append(f"{scenario_id}: no risk link")
        if not scenario.get("expected"): errors.append(f"{scenario_id}: no oracle")
    for test_id, test in tests.items():
        if not test.get("scenario_ids"): errors.append(f"{test_id}: no scenario link")
        if test.get("status") in {"passed", "failed"} and test.get("execution_id") not in executions:
            errors.append(f"{test_id}: completed test has no valid execution")
    return {"valid": not errors, "errors": errors, "warnings": warnings, "counts": {"risks": len(risks), "scenarios": len(scenarios), "tests": len(tests), "executions": len(executions)}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try: report = validate(load_data(args.manifest))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc: report = {"valid": False, "errors": [str(exc)], "warnings": []}
    if args.output: write_json(args.output, report)
    else: print(json.dumps(report, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
