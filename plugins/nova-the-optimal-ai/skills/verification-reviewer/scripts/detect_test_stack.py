#!/usr/bin/env python3
"""Detect candidate test frameworks and repository-local commands."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from common.filesystem import write_json


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def detect(root: Path) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"repository path is not a directory: {root}")
    candidates, managers, evidence = [], [], []
    package_json = root / "package.json"
    if package_json.exists():
        try:
            package = json.loads(_read_text(package_json))
        except json.JSONDecodeError:
            package = {}
            evidence.append("package.json exists but is invalid JSON")
        deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
        scripts = package.get("scripts", {})
        if (root / "pnpm-lock.yaml").exists(): managers.append("pnpm")
        elif (root / "yarn.lock").exists(): managers.append("yarn")
        else: managers.append("npm")
        for framework, signal in (("vitest", "vitest"), ("jest", "jest"), ("@playwright/test", "playwright")):
            if framework in deps or any(signal in str(v).lower() for v in scripts.values()):
                command = next((f"{managers[0]} run {k}" for k, v in scripts.items() if signal in str(v).lower()), None)
                command = command or ("npx vitest run" if framework == "vitest" else "npx jest" if framework == "jest" else "npx playwright test")
                candidates.append({"framework": framework, "language": "TypeScript/JavaScript", "confidence": "high", "command": command, "evidence": ["package.json"]})
        if scripts.get("test") and not any(c["command"].endswith(" run test") for c in candidates):
            candidates.append({"framework": "repository test script", "language": "TypeScript/JavaScript", "confidence": "high", "command": f"{managers[0]} test", "evidence": ["package.json scripts.test"]})

    py_files = [root / "pyproject.toml", root / "pytest.ini", root / "tox.ini", root / "setup.cfg", root / "requirements.txt"]
    py_text = "\n".join(_read_text(p) for p in py_files if p.exists()).lower()
    if (root / "uv.lock").exists(): managers.append("uv")
    if (root / "poetry.lock").exists(): managers.append("poetry")
    if "pytest" in py_text or (root / "pytest.ini").exists():
        candidates.append({"framework": "pytest", "language": "Python", "confidence": "high", "command": "python -m pytest -q", "evidence": [p.name for p in py_files if p.exists() and "pytest" in _read_text(p).lower()]})
    else:
        test_py = [path for path in root.rglob("test*.py") if "__pycache__" not in path.parts][:20]
        if test_py:
            body = "\n".join(_read_text(p)[:20_000] for p in test_py[:20])
            if "unittest" in body or re.search(r"class\s+\w+\(.*TestCase", body):
                candidates.append({"framework": "unittest", "language": "Python", "confidence": "medium", "command": "python -m unittest discover", "evidence": [str(p.relative_to(root)) for p in test_py[:5]]})

    if not candidates:
        candidates.append({"framework": "unknown", "language": "unknown", "confidence": "low", "command": None, "evidence": ["no supported framework signal found"]})
    return {"format_version": "1.0", "root": str(root), "package_managers": sorted(set(managers)), "candidates": candidates, "warnings": evidence}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = detect(args.repository)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.output: write_json(args.output, result)
    else: print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
