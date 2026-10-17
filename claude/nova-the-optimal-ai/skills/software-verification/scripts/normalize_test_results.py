#!/usr/bin/env python3
"""Normalize JUnit XML, Jest JSON, or captured command records."""
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from common.filesystem import write_json


def _summary(total=0, passed=0, failed=0, skipped=0, errors=0, status="unparsed"):
    return {"total": int(total), "passed": int(passed), "failed": int(failed), "skipped": int(skipped), "errors": int(errors), "status": status}


def normalize_junit(path: Path) -> dict:
    root = ET.parse(path).getroot()
    local = lambda element: element.tag.rsplit("}", 1)[-1]
    if local(root) not in {"testsuite", "testsuites"}:
        raise ValueError("not a JUnit testsuite/testsuites document")
    cases, warnings = [], []
    for suite in root.iter():
        if local(suite) not in {"testsuite", "testsuites"}:
            continue
        direct = [c for c in suite if local(c) == "testcase"]
        for case in direct:
            tags = {local(c) for c in case}
            state = "error" if "error" in tags else "failed" if "failure" in tags else "skipped" if "skipped" in tags else "passed"
            cases.append({"name": case.attrib.get("name", "unnamed"), "suite": case.attrib.get("classname", suite.attrib.get("name", "")), "status": state, "duration_seconds": float(case.attrib.get("time", 0) or 0)})
        # Parent aggregates include descendants; count testcase records once.
        descendants = [c for c in suite.iter() if local(c) == "testcase"]
        observed = {"tests": len(descendants), "failures": sum(any(local(x) == "failure" for x in c) for c in descendants), "errors": sum(any(local(x) == "error" for x in c) for c in descendants), "skipped": sum(any(local(x) == "skipped" for x in c) for c in descendants)}
        for key, count in observed.items():
            if key in suite.attrib and int(suite.attrib[key]) != count:
                warnings.append(f"suite {suite.attrib.get('name', '')}: declared {key} differs from testcase records")
    counts = {state: sum(c["status"] == state for c in cases) for state in ("passed", "failed", "error", "skipped")}
    status = "failed" if counts["failed"] or counts["error"] else "unparsed" if not cases or warnings else "passed" if counts["passed"] else "unparsed"
    if not cases:
        warnings.append("no testcase records; no test pass is established")
    return {"format_version": "1.0", "source": {"format": "junit_xml", "path": str(path)}, "summary": _summary(len(cases), counts["passed"], counts["failed"], counts["skipped"], counts["error"], status), "cases": cases, "parse_warnings": warnings}


def normalize_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("result root must be an object")
    if "numTotalTests" in data:
        cases = []
        for suite in data.get("testResults", []):
            for case in suite.get("assertionResults", []):
                status = {"pending": "skipped", "todo": "skipped"}.get(case.get("status"), case.get("status", "unparsed"))
                cases.append({"name": case.get("fullName") or case.get("title"), "suite": suite.get("name"), "status": status, "duration_seconds": (case.get("duration") or 0) / 1000})
        failed = int(data.get("numFailedTests", 0)); skipped = int(data.get("numPendingTests", 0)) + int(data.get("numTodoTests", 0)); total = int(data.get("numTotalTests", 0)); passed = int(data.get("numPassedTests", max(0, total-failed-skipped)))
        if min(total, passed, failed, skipped) < 0 or passed + failed + skipped != total:
            raise ValueError("inconsistent Jest test counts")
        warnings = []
        observed = {state: sum(c["status"] == state for c in cases) for state in ("passed", "failed", "skipped")}
        if cases and (len(cases), observed["passed"], observed["failed"], observed["skipped"]) != (total, passed, failed, skipped):
            warnings.append("Jest aggregate counts differ from assertion records")
        if not cases:
            warnings.append("no assertion records; aggregate counts do not establish test-case proof")
        # Preserve any observed failure even when aggregate metadata says success.
        if failed or observed["failed"] or data.get("success") is False:
            status = "failed"
        elif warnings or not passed or any(c["status"] not in observed for c in cases):
            status = "unparsed"
        else:
            status = "passed"
        if cases:
            total, passed, failed, skipped = len(cases), observed["passed"], observed["failed"], observed["skipped"]
        return {"format_version": "1.0", "source": {"format": "jest_json", "path": str(path)}, "summary": _summary(total, passed, failed, skipped, 0, status), "cases": cases, "parse_warnings": warnings}

    if "command" in data and "status" in data:
        status = data.get("status")
        code = data.get("exit_code")
        if status in {"passed", "failed"} and (type(code) is not int or (status == "passed" and code != 0) or (status == "failed" and code == 0)):
            raise ValueError("command status contradicts or lacks its exit code")
        normalized = status if status in {"passed", "failed", "blocked", "interrupted"} else "unparsed"
        return {"format_version": "1.0", "source": {"format": "command_record", "path": str(path), "command": data.get("command")}, "summary": _summary(status=normalized), "cases": [], "parse_warnings": ["command record contains no per-test case counts"]}
    if not isinstance(data.get("summary"), dict):
        raise ValueError("unsupported result JSON; expected Jest, command record or normalized summary")
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    counts = [summary.get(k, 0) for k in ("total", "passed", "failed", "skipped", "errors")]
    if any(type(x) is not int or x < 0 for x in counts) or counts[0] != sum(counts[1:]):
        raise ValueError("inconsistent generic test counts")
    if summary.get("status") == "passed" and (not counts[1] or counts[2] or counts[4]):
        raise ValueError("generic passed status lacks passing evidence or contradicts failures")
    cases = data.get("cases", [])
    if not isinstance(cases, list) or any(not isinstance(c, dict) for c in cases):
        raise ValueError("generic cases must be an object list")
    warnings = ["generic JSON mapping; verify framework semantics"]
    states = ("passed", "failed", "skipped", "error")
    observed = {state: sum(c.get("status") == state for c in cases) for state in states}
    result_status = summary.get("status", "unparsed")
    if result_status not in ("passed", "failed", "blocked", "interrupted", "unparsed"):
        raise ValueError("unknown generic status")
    if cases:
        actual = [len(cases), observed["passed"], observed["failed"], observed["skipped"], observed["error"]]
        if actual != counts or any(c.get("status") not in states for c in cases):
            warnings.append("generic summary counts differ from case records")
            result_status = "unparsed"
        if observed["failed"] or observed["error"] or counts[2] or counts[4]: result_status = "failed"
        counts = actual
    elif result_status == "passed":
        warnings.append("no case records; generic aggregate does not establish exercised cases")
        result_status = "unparsed"
    return {"format_version": "1.0", "source": {"format": "generic_json", "path": str(path)}, "summary": _summary(*counts, status=result_status), "cases": cases, "parse_warnings": warnings}


def normalize(path: Path, format_name: str = "auto") -> dict:
    if format_name == "auto": format_name = "junit" if path.suffix.lower() == ".xml" else "json"
    if format_name == "junit": return normalize_junit(path)
    if format_name == "json": return normalize_json(path)
    raise ValueError(f"unsupported format: {format_name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--format", choices=["auto", "junit", "json"], default="auto")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try: result = normalize(args.input, args.format)
    except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError, ET.ParseError) as exc:
        result = {"format_version": "1.0", "source": {"format": "unparsed", "path": str(args.input)}, "summary": _summary(status="unparsed"), "cases": [], "parse_warnings": [str(exc)]}
        write_json(args.output, result)
        return 1
    write_json(args.output, result)
    return 0 if result["summary"]["status"] != "unparsed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
