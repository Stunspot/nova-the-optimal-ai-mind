#!/usr/bin/env python3
"""Heuristically flag test constructs that can weaken evidence."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from common.filesystem import iter_files, write_json

PATTERNS = [
    ("skipped_test", r"\b(?:it|test|describe)\.skip\b|@pytest\.mark\.skip|unittest\.skip|\bxit\s*\(", "medium"),
    ("fixed_sleep", r"\b(?:time\.)?sleep\s*\(|setTimeout\s*\(", "medium"),
    ("snapshot_assertion", r"toMatchSnapshot\s*\(|snapshot", "low"),
    ("broad_exception_swallow", r"except\s+(?:Exception|BaseException)\s*:\s*(?:pass|return)|catch\s*\([^)]*\)\s*\{\s*\}", "high"),
    ("truthiness_only", r"assert\s+\w+\s*$|toBeTruthy\s*\(", "low"),
    ("focus_marker", r"\b(?:it|test|describe)\.only\b|@pytest\.mark\.focus|\bfit\s*\(", "high"),
]
TEST_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".rb", ".go", ".rs"}


def scan(paths: list[Path]) -> dict:
    findings = []
    files = []
    for supplied in paths:
        candidates = iter_files(supplied) if supplied.is_dir() else [supplied]
        for path in candidates:
            if path.suffix.lower() not in TEST_SUFFIXES: continue
            low = path.name.lower()
            if not ("test" in low or "spec" in low or "test" in {p.lower() for p in path.parts} or "tests" in {p.lower() for p in path.parts}): continue
            files.append(str(path))
            try: text = path.read_text(encoding="utf-8-sig", errors="replace")
            except OSError as exc:
                findings.append({"file": str(path), "line": 0, "smell": "unreadable", "severity": "medium", "evidence": str(exc)})
                continue
            for smell, pattern, severity in PATTERNS:
                for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
                    line = text.count("\n", 0, match.start()) + 1
                    findings.append({"file": str(path), "line": line, "smell": smell, "severity": severity, "evidence": match.group(0)[:120]})
            assertion_tokens = re.findall(r"\bassert\b|expect\s*\(|assert[A-Z]\w*\s*\(", text)
            test_tokens = re.findall(r"\bdef\s+test_|\b(?:it|test)\s*\(", text)
            if test_tokens and not assertion_tokens:
                findings.append({"file": str(path), "line": 1, "smell": "assertion_poverty", "severity": "high", "evidence": "test declarations found without recognizable assertions"})
    return {"format_version": "1.0", "heuristic_only": True, "files_scanned": len(set(files)), "finding_count": len(findings), "findings": findings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = scan(args.paths)
    if args.output: write_json(args.output, result)
    else: print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
