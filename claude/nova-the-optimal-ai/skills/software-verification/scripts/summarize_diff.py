#!/usr/bin/env python3
"""Classify changed paths from a Git diff or patch without interpreting code."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

from common.filesystem import write_json


def classify(path: str) -> str:
    low = path.lower()
    name = Path(low).name
    if ".test." in low or ".spec." in low or "/tests/" in f"/{low}" or name.startswith("test_"):
        return "tests"
    if name in {"package.json", "pyproject.toml", "requirements.txt", "pom.xml", "cargo.toml", "go.mod"} or "lock" in name:
        return "dependencies"
    if "migration" in low or low.endswith(".sql") or "schema" in name:
        return "schema"
    if low.startswith(".github/") or "docker" in name or "terraform" in low or low.endswith((".yml", ".yaml")) and "ci" in low:
        return "infrastructure"
    if low.endswith((".json", ".toml", ".ini", ".cfg", ".env", ".yaml", ".yml")):
        return "configuration"
    return "production_code"


def paths_from_patch(text: str) -> list[str]:
    found = []
    for line in text.splitlines():
        match = re.match(r"^\+\+\+ b/(.+)$", line)
        if match and match.group(1) != "/dev/null":
            found.append(match.group(1))
        match = re.match(r"^diff --git a/(.+?) b/(.+)$", line)
        if match:
            found.append(match.group(2))
    return sorted(set(found))


def summarize(paths: list[str], source: str, warnings: list[str] | None = None) -> dict:
    groups: dict[str, list[str]] = defaultdict(list)
    for path in sorted(set(paths)):
        groups[classify(path)].append(path)
    return {"format_version": "1.0", "source": source, "changed_file_count": len(set(paths)), "groups": dict(sorted(groups.items())), "warnings": warnings or []}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--patch", type=Path)
    source.add_argument("--repository", type=Path)
    parser.add_argument("--base", default="HEAD~1")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    warnings: list[str] = []
    if args.patch:
        text = args.patch.read_text(encoding="utf-8-sig", errors="replace")
        result = summarize(paths_from_patch(text), str(args.patch), warnings)
    else:
        repo = args.repository.resolve()
        proc = subprocess.run(["git", "diff", "--name-only", "--no-ext-diff", args.base, args.head], cwd=repo, text=True, capture_output=True, timeout=30, check=False)
        if proc.returncode:
            warnings.append(proc.stderr.strip() or f"git diff exited {proc.returncode}")
        paths = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        result = summarize(paths, f"git:{args.base}..{args.head}", warnings)
    if args.output: write_json(args.output, result)
    else: print(json.dumps(result, indent=2))
    return 0 if not warnings else 2


if __name__ == "__main__":
    raise SystemExit(main())
