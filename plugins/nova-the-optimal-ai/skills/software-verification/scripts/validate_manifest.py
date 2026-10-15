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
    for field in ("risks", "scenarios", "tests", "executions", "findings", "residual_risks", "invariants"):
        if field in data and (not isinstance(data[field], list) or any(not isinstance(x, dict) for x in data[field])):
            errors.append(f"{field} must be a list of objects")
    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}
    # Reject malformed imported metadata before enum/set operations can raise.
    def text(value): return isinstance(value, str) and bool(value.strip())
    def strings(value): return isinstance(value, list) and all(text(v) for v in value)
    for field in ("target", "scope", "claim_custody", "review", "decision"):
        if field in data and not isinstance(data[field], dict): errors.append(f"{field} must be an object")
    for field, enums in (("risks", ("severity", "disposition")), ("tests", ("status",)), ("executions", ("status",)), ("findings", ("classification", "severity", "status"))):
        for row in data.get(field, []):
            for key in enums:
                if key in row and not isinstance(row[key], str): errors.append(f"{field}.{key} must be a string")
            if field == "tests" and row.get("execution_id") is not None and not isinstance(row["execution_id"], str): errors.append("test.execution_id must be a string")
            if field == "tests" and "decision_critical" in row and type(row["decision_critical"]) is not bool: errors.append("test.decision_critical must be boolean")
    for field in ("review", "decision"):
        if isinstance(data.get(field), dict) and not isinstance(data[field].get("status"), str): errors.append(f"{field}.status must be a string")
    if errors: return {"valid": False, "errors": errors, "warnings": warnings}
    from validate_traceability import validate as trace_validate
    trace = trace_validate(data)
    errors.extend(trace["errors"])
    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}
    missing = sorted(REQUIRED - set(data))
    if missing: errors.append("missing required sections: " + ", ".join(missing))
    if data.get("manifest_version") != "1.0": errors.append("manifest_version must be '1.0'")
    target = data.get("target", {})
    if not isinstance(target, dict) or not text(target.get("name")) or not text(target.get("revision")):
        errors.append("target requires name and revision")
    # Check authoring slots from the shipped template, never serialized evidence.
    # Literal template syntax in a finding or observed source is legitimate content.
    for field in ("name", "revision"):
        if isinstance(target.get(field), str) and target[field].strip() == "REPLACE":
            errors.append("target." + field + " retains the unfilled template value REPLACE")
    scope = data.get("scope", {})
    if isinstance(scope.get("included"), list):
        for index, item in enumerate(scope["included"]):
            if isinstance(item, str) and item.strip() == "REPLACE":
                errors.append(f"scope.included[{index}] retains the unfilled template value REPLACE")
    if not isinstance(scope, dict) or not strings(scope.get("included")) or not scope.get("included"):
        errors.append("scope.included must be a non-empty list")
    for field in ("excluded", "constraints", "safety_boundary"):
        if field in scope and not strings(scope[field]): errors.append(f"scope.{field} must be a string list")
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
    if errors: return {"valid": False, "errors": errors, "warnings": warnings}

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
        if risk.get("disposition") == "accepted_by_human" and not text(risk.get("acceptance_authority")):
            errors.append(f"{risk.get('id', 'risk')}: accepted risk requires acceptance_authority")
        for link in links if isinstance(links, list) else []:
            if link not in scenario_ids | test_ids | execution_ids:
                errors.append(f"{risk.get('id', 'risk')}: unknown verification link {link}")

    for scenario in data.get("scenarios", []) if isinstance(data.get("scenarios"), list) else []:
        if not isinstance(scenario, dict): continue
        for risk_id in scenario.get("risk_ids", []):
            if risk_id not in risk_ids: errors.append(f"{scenario.get('id', 'scenario')}: unknown risk {risk_id}")
        if not strings(scenario.get("expected")) or not scenario.get("expected"): errors.append(f"{scenario.get('id', 'scenario')}: expected oracle is empty")

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

    for execution in data.get("executions", []):
        eid = execution.get("id")
        state = execution.get("status")
        if state not in EXECUTION_STATUSES: errors.append(f"{eid}: invalid execution status")
        if "test_ids" in execution:
            links = execution["test_ids"]
            if not strings(links) or not links:
                errors.append(f"{eid}: execution.test_ids must be a nonempty string list")
            elif len(set(links)) != len(links) or any(tid not in test_ids for tid in links):
                errors.append(f"{eid}: execution.test_ids contains duplicate or unknown tests")
        kind = execution.get("kind", "command")
        if kind not in ("command", "observation"): errors.append(f"{eid}: kind must be command or observation")
        if execution.get("target_revision") is not None and execution["target_revision"] != target.get("revision"):
            errors.append(f"{eid}: execution belongs to a different target revision")
        if state in {"passed", "failed"}:
            if kind == "command":
                code = execution.get("exit_code")
                if type(code) is not int or (state == "passed" and code != 0) or (state == "failed" and code == 0):
                    errors.append(f"{eid}: execution status conflicts with exit code")
                if not strings(execution.get("command")) or not execution["command"]:
                    errors.append(f"{eid}: completed command requires command tokens")
            elif kind == "observation":
                for field in ("procedure", "observed"):
                    if not strings(execution.get(field)) or not execution[field]: errors.append(f"{eid}: observation requires nonempty {field}")
                if execution.get("source") not in ("observed", "supplied"): errors.append(f"{eid}: observation source must be observed or supplied")
                for field in ("recorder", "environment"):
                    if not text(execution.get(field)): errors.append(f"{eid}: observation requires {field}")
                if execution.get("exit_code") is not None or execution.get("command"):
                    errors.append(f"{eid}: observation must not impersonate command execution")
            locator = execution.get("raw_evidence")
            if not text(locator): errors.append(f"{eid}: completed execution requires raw_evidence locator")
            elif root:
                # External/supplied records retain their source; existence never authenticates content.
                if "://" in locator or locator.startswith("supplied:"):
                    warnings.append(f"{eid}: external/supplied evidence must be inspected by reviewer: {locator}")
                else:
                    evidence_path = (root / locator.split("#", 1)[0]).resolve()
                    if not is_within(evidence_path, root.resolve()): errors.append(f"{eid}: raw evidence escapes evidence root")
                    elif not evidence_path.is_file(): errors.append(f"{eid}: raw evidence does not exist: {locator}")
            else: warnings.append(f"{eid}: raw evidence content not inspected; no evidence root supplied")

    decision = data.get("decision", {})
    status = decision.get("status") if isinstance(decision, dict) else None
    if status not in RELEASE_STATUSES: errors.append("decision.status is invalid")
    review_status = data.get("review", {}).get("status") if isinstance(data.get("review"), dict) else None
    if review_status not in REVIEW_STATUSES: errors.append("review.status is invalid")
    review = data.get("review", {})
    if review.get("target_revision") is not None and review["target_revision"] != target.get("revision"):
        errors.append("review belongs to a different target revision")
    for key in ("basis", "authority_required"):
        if key in decision and not strings(decision[key]): errors.append(f"decision.{key} must be a string list")
    for section in ("observed", "inferred", "assumed", "unresolved"):
        for claim in custody.get(section, []) if isinstance(custody, dict) and isinstance(custody.get(section), list) else []:
            if not isinstance(claim, dict) or not text(claim.get("statement")) or not text(claim.get("basis")): errors.append(f"claim_custody.{section} requires statement and basis")
    review_findings = review.get("findings", [])
    if not strings(review_findings): errors.append("review.findings must be a string list"); review_findings = []
    dispositions = review.get("finding_dispositions", {})
    if not isinstance(dispositions, dict): errors.append("review.finding_dispositions must be an object"); dispositions = {}
    conditions = review.get("conditions", [])
    if not isinstance(conditions, list) or any(not isinstance(c, dict) for c in conditions): errors.append("review.conditions must be an object list"); conditions = []
    for condition in conditions:
        if not text(condition.get("statement")) or condition.get("status") not in ("met", "open") or type(condition.get("blocking")) is not bool:
            errors.append("review condition requires statement, met/open status and boolean blocking")
    residuals = data.get("residual_risks", [])
    for residual in residuals:
        if not text(residual.get("statement")) or not text(residual.get("treatment")): errors.append(f"{residual.get('id')}: residual requires statement and treatment")
        for field in ("test_ids", "risk_ids"):
            if field in residual and not strings(residual[field]): errors.append(f"{residual.get('id')}: {field} must be a string list")
    def residual_for(test_id):
        return [r for r in residuals if isinstance(r.get("test_ids"), list) and test_id in r["test_ids"]]
    executions = {e["id"]:e for e in data.get("executions", [])}
    findings = {f["id"]:f for f in data.get("findings", []) if isinstance(f.get("id"), str)}
    tests_by_id = {t["id"]:t for t in data.get("tests", [])}
    def superseded_support(e):
        replacement = executions.get(e.get("superseded_by")) if isinstance(e.get("superseded_by"), str) else None
        finding = findings.get(e.get("triage_finding_id")) if isinstance(e.get("triage_finding_id"), str) else None
        failed_scope = e.get("test_ids")
        replacement_scope = replacement.get("test_ids") if replacement else None
        scope_matches = bool(strings(failed_scope) and failed_scope and strings(replacement_scope) and replacement_scope
                             and set(failed_scope).issubset(set(replacement_scope))
                             and all(tid in tests_by_id and tests_by_id[tid].get("status") == "passed"
                                     and tests_by_id[tid].get("execution_id") == replacement.get("id")
                                     for tid in failed_scope))
        return bool(scope_matches and replacement and replacement["id"] != e["id"] and replacement.get("status") == "passed"
                    and replacement.get("target_revision") == e.get("target_revision") == target.get("revision")
                    and finding and finding.get("status") == "resolved" and finding.get("classification") in {"TEST_DEFECT", "TOOLING_FAILURE", "ENVIRONMENT_FAILURE"}
                    and strings(finding.get("evidence")) and finding.get("evidence"))
    blockers = [r.get("id") for r in data.get("risks", []) if isinstance(r, dict) and r.get("severity") in {"critical", "high"} and r.get("disposition") in {"planned", "blocked", "unresolved"}]
    failed_tests = [t.get("id") for t in data.get("tests", []) if isinstance(t, dict) and t.get("status") == "failed"]
    if status in {"READY", "READY_WITH_RESIDUAL_RISK"}:
        for field in ("risks", "scenarios", "tests", "executions"):
            if not data.get(field): errors.append(f"ready status requires nonempty {field}")
        if not strings(decision.get("basis")) or not decision.get("basis"): errors.append("ready status requires a decision basis")
        for field in ("reviewer", "raw_evidence", "evidence_cutoff"):
            if not text(review.get(field)): errors.append(f"ready status requires review.{field}")
        if review.get("target_revision") != target.get("revision"): errors.append("ready status requires review of this target revision")
        for execution in data.get("executions", []):
            if execution.get("status") in {"passed", "failed"}:
                if execution.get("target_revision") != target.get("revision"): errors.append(f"{execution['id']}: ready status requires candidate-bound execution")
                if not text(execution.get("environment")): errors.append(f"{execution['id']}: ready status requires execution environment")
        if root and text(review.get("raw_evidence")):
            locator = review["raw_evidence"]
            if "://" not in locator and not locator.startswith("supplied:"):
                review_path = (root / locator.split("#", 1)[0]).resolve()
                if not is_within(review_path, root.resolve()) or not review_path.is_file(): errors.append("review raw evidence missing or outside evidence root")
            else: warnings.append("review evidence is external/supplied; inspect its source and scope")
        for finding in review_findings:
            disposition = dispositions.get(finding)
            if not isinstance(disposition, dict) or disposition.get("status") not in ("resolved", "non_blocking") or not text(disposition.get("reason")):
                errors.append(f"ready status requires explicit disposition of reviewer finding: {finding}")
        if review_status == "REVIEW_PASS_WITH_CONDITIONS" and not conditions: errors.append("conditional review requires named conditions")
        if any(c.get("status") == "open" and c.get("blocking") for c in conditions): errors.append("ready status conflicts with open blocking reviewer condition")
        if any(c.get("status") == "open" for c in conditions) and status != "READY_WITH_RESIDUAL_RISK": errors.append("open nonblocking review condition requires residual-risk status")
        if decision.get("claims_release_authorization") is True and decision.get("authority_required"): errors.append("claimed release authorization conflicts with outstanding authority")
        for residual in residuals:
            if not text(residual.get("owner")) or not text(residual.get("revisit_condition")): errors.append(f"{residual.get('id')}: ready residual risk requires owner and revisit_condition")
        for test in data.get("tests", []):
            state = test.get("status")
            if state == "not_applicable":
                if not text(test.get("applicability_reason")): errors.append(f"{test['id']}: not_applicable requires a scope-based reason")
                if test.get("decision_critical") is True: errors.append(f"{test['id']}: decision-critical check cannot be silently made not_applicable")
            elif state != "passed" and test.get("decision_critical", True):
                errors.append(f"{test['id']}: ready status requires every decision-critical check to pass")
            elif state in {"designed", "unexecuted", "blocked"} and not residual_for(test["id"]):
                errors.append(f"{test['id']}: unfinished noncritical check requires a specifically linked residual risk")

        completed = [t for t in data.get("tests", []) if t.get("status") == "passed" and any(e.get("id") == t.get("execution_id") and e.get("status") == "passed" for e in data.get("executions", []))]
        if not completed: errors.append("ready status requires a passed test linked to a passed execution")
        unfinished = [t.get("id") for t in data.get("tests", []) if t.get("status") in {"designed", "unexecuted", "blocked"}]
        if unfinished and status == "READY": errors.append("READY has unfinished tests; qualify residual risk or use INSUFFICIENT_EVIDENCE")
        if status == "READY_WITH_RESIDUAL_RISK" and unfinished and not data.get("residual_risks"): errors.append("unfinished tests require explicit residual risk")
        if status == "READY" and any(r.get("disposition") != "covered" for r in data.get("risks", [])): errors.append("READY requires covered risks; qualify accepted or unfinished risk explicitly")

        open_findings = [f.get("id") for f in data.get("findings", []) if f.get("status") not in {"resolved", "closed", "superseded"} and (f.get("classification") == "PRODUCT_DEFECT" or f.get("severity") in {"critical", "high"})]
        if open_findings: errors.append("ready status conflicts with open material findings: " + ", ".join(open_findings))
        failed_executions = [e for e in data.get("executions", []) if e.get("status") == "failed"]
        if any(not superseded_support(e) for e in failed_executions): errors.append("ready status conflicts with failed execution lacking a resolved support-failure disposition")
        if len(failed_executions) > 1: errors.append("more than one support correction exceeds the bounded verification cycle")
        if any(e.get("status") in {"interrupted", "unparsed", "blocked", "not_run"} and not text(e.get("disposition")) for e in data.get("executions", [])): errors.append("incomplete execution requires explicit disposition")

        if blockers: errors.append("ready status conflicts with unresolved high/critical risks: " + ", ".join(blockers))
        if failed_tests: errors.append("ready status conflicts with failed tests: " + ", ".join(failed_tests))
        if review_status not in {"REVIEW_PASS", "REVIEW_PASS_WITH_CONDITIONS"}: errors.append("ready status requires reviewer pass")
    if status == "READY" and data.get("residual_risks"):
        errors.append("READY has residual risks; use READY_WITH_RESIDUAL_RISK")
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
