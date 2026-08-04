#!/usr/bin/env python3
"""Run bounded local integrity checks for Current Intelligence Observatory."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "SKILL.md",
    "agents/openai.yaml",
    "manifest.json",
    "schemas/observatory-case.schema.json",
    "assets/observatory-case.template.json",
    "scripts/observatory_guardrail.py",
    "evals/eval-manifest.yaml",
    "examples/harbor-lantern/case-baseline.json",
    "examples/harbor-lantern/case-update.json",
)


def main() -> int:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")
    for relative in ("manifest.json", "schemas/observatory-case.schema.json", "assets/observatory-case.template.json"):
        try:
            json.loads((ROOT / relative).read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON {relative}: {exc}")
    for path in sorted((ROOT / "scripts").rglob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            errors.append(f"invalid Python {path.relative_to(ROOT)}: {exc}")
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8-sig") if (ROOT / "SKILL.md").is_file() else ""
    if not skill.startswith("---\n"):
        errors.append("SKILL.md requires YAML frontmatter")
    lower_skill = skill.lower()
    if not all(term in lower_skill for term in ("semantic", "truth", "publication-ready")):
        errors.append("SKILL.md is missing semantic or publication boundary language")
    result = {
        "label": "STATIC_PACKAGE_INTEGRITY_ONLY",
        "valid": not errors,
        "errors": errors,
        "live_host_assessed": False,
        "semantic_truth_assessed": False,
        "accessibility_conformance_assessed": False,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
