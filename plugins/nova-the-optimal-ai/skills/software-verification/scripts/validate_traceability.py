#!/usr/bin/env python3
"""Validate risk-to-scenario-to-test-to-execution traceability."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common.filesystem import load_data, write_json


def validate(data: dict) -> dict:
    errors, warnings = [], []
    if not isinstance(data, dict):
        return {"valid": False, "errors": ["manifest root must be an object"], "warnings": []}
    maps = {}
    for field in ("risks", "scenarios", "tests", "executions"):
        rows = data.get(field, [])
        if not isinstance(rows, list):
            errors.append(f"{field} must be a list")
            rows = []
        maps[field] = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
                errors.append(f"{field}: each row requires a nonempty string id")
                continue
            if row["id"] in maps[field]:
                errors.append(f"duplicate {field} id: {row['id']}")
            maps[field][row["id"]] = row
    risks, scenarios, tests, executions = (maps[k] for k in ("risks", "scenarios", "tests", "executions"))
    def links(row, field, available):
        values = row.get(field, [])
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
            errors.append(f"{row['id']}: {field} must be a string list")
            return []
        for value in values:
            if value not in available:
                errors.append(f"{row['id']}: unknown {field} link {value}")
        return values
    for sid, scenario in scenarios.items():
        if not links(scenario, "risk_ids", risks): errors.append(f"{sid}: no risk link")
        if not scenario.get("expected"): errors.append(f"{sid}: no oracle")
    for tid, test in tests.items():
        if not links(test, "scenario_ids", scenarios): errors.append(f"{tid}: no scenario link")
        eid = test.get("execution_id")
        execution = executions.get(eid) if isinstance(eid, str) else None
        if eid and not execution: errors.append(f"{tid}: unknown execution")
        if test.get("status") in ("passed", "failed"):
            if not execution or execution.get("status") not in ("passed", "failed"):
                errors.append(f"{tid}: completed test has no completed execution")
            elif test.get("status") == "failed" and execution.get("status") == "passed":
                errors.append(f"{tid}: failed test contradicts passing execution")
            elif test.get("status") == "passed" and execution.get("status") == "failed" and not test.get("case_evidence"):
                errors.append(f"{tid}: passing case in failed run requires case_evidence")
    for rid, risk in risks.items():
        links(risk, "verification", set(scenarios) | set(tests) | set(executions))
        linked_scenarios = [sid for sid, row in scenarios.items() if isinstance(row.get("risk_ids"), list) and rid in row["risk_ids"]]
        linked_tests = [t for t in tests.values() if isinstance(t.get("scenario_ids"), list) and any(isinstance(sid, str) and sid in linked_scenarios for sid in t["scenario_ids"])]
        evidence = [t for t in linked_tests if t.get("status") in ("passed", "failed") and isinstance(t.get("execution_id"), str) and executions.get(t["execution_id"], {}).get("status") in ("passed", "failed")]
        if risk.get("severity") == "critical" and risk.get("disposition") != "accepted_by_human" and not linked_scenarios:
            errors.append(f"{rid}: critical risk has no scenario")
        if risk.get("disposition") == "covered":
            if not linked_tests: errors.append(f"{rid}: covered risk has no test")
            if not evidence: errors.append(f"{rid}: covered risk has no execution evidence")
    return {"valid": not errors, "errors": errors, "warnings": warnings, "counts": {k: len(v) for k, v in maps.items()}}


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
