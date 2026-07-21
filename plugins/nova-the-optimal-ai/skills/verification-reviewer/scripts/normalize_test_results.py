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
    suites = [root] if root.tag == "testsuite" else list(root.findall(".//testsuite"))
    cases, totals = [], {"total": 0, "failed": 0, "skipped": 0, "errors": 0}
    for suite in suites:
        totals["total"] += int(suite.attrib.get("tests", len(suite.findall("testcase"))))
        totals["failed"] += int(suite.attrib.get("failures", 0))
        totals["skipped"] += int(suite.attrib.get("skipped", suite.attrib.get("disabled", 0)))
        totals["errors"] += int(suite.attrib.get("errors", 0))
        for case in suite.findall("testcase"):
            state = "failed" if case.find("failure") is not None else "error" if case.find("error") is not None else "skipped" if case.find("skipped") is not None else "passed"
            cases.append({"name": case.attrib.get("name", "unnamed"), "suite": case.attrib.get("classname", suite.attrib.get("name", "")), "status": state, "duration_seconds": float(case.attrib.get("time", 0) or 0)})
    passed = max(0, totals["total"] - totals["failed"] - totals["skipped"] - totals["errors"])
    status = "passed" if totals["failed"] == 0 and totals["errors"] == 0 else "failed"
    return {"format_version": "1.0", "source": {"format": "junit_xml", "path": str(path)}, "summary": _summary(totals["total"], passed, totals["failed"], totals["skipped"], totals["errors"], status), "cases": cases, "parse_warnings": []}


def normalize_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if "numTotalTests" in data:
        cases = []
        for suite in data.get("testResults", []):
            for case in suite.get("assertionResults", []):
                status = {"pending": "skipped", "todo": "skipped"}.get(case.get("status"), case.get("status", "unparsed"))
                cases.append({"name": case.get("fullName") or case.get("title"), "suite": suite.get("name"), "status": status, "duration_seconds": (case.get("duration") or 0) / 1000})
        failed = int(data.get("numFailedTests", 0)); skipped = int(data.get("numPendingTests", 0)) + int(data.get("numTodoTests", 0)); total = int(data.get("numTotalTests", 0)); passed = int(data.get("numPassedTests", max(0, total-failed-skipped)))
        return {"format_version": "1.0", "source": {"format": "jest_json", "path": str(path)}, "summary": _summary(total, passed, failed, skipped, 0, "passed" if failed == 0 and data.get("success", True) else "failed"), "cases": cases, "parse_warnings": []}
    if "command" in data and "status" in data:
        status = data.get("status")
        normalized = status if status in {"passed", "failed", "blocked", "interrupted"} else "unparsed"
        return {"format_version": "1.0", "source": {"format": "command_record", "path": str(path), "command": data.get("command")}, "summary": _summary(status=normalized), "cases": [], "parse_warnings": ["command record contains no per-test case counts"]}
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    return {"format_version": "1.0", "source": {"format": "generic_json", "path": str(path)}, "summary": _summary(summary.get("total", 0), summary.get("passed", 0), summary.get("failed", 0), summary.get("skipped", 0), summary.get("errors", 0), summary.get("status", "unparsed")), "cases": data.get("cases", []), "parse_warnings": ["generic JSON mapping; verify framework semantics"]}


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
    except (OSError, ValueError, json.JSONDecodeError, ET.ParseError) as exc:
        result = {"format_version": "1.0", "source": {"format": "unparsed", "path": str(args.input)}, "summary": _summary(status="unparsed"), "cases": [], "parse_warnings": [str(exc)]}
        write_json(args.output, result)
        return 1
    write_json(args.output, result)
    return 0 if result["summary"]["status"] != "unparsed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
