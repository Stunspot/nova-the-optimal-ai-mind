#!/usr/bin/env python3
"""Check Privacy Redline package containment and required runtime resources."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "SKILL.md", "agents/openai.yaml", "manifest.json",
    "knowledge/operating-doctrine.md", "knowledge/state-and-routing.md",
    "knowledge/currentness-and-authority.md",
    "personas/ronan-redline-canonical.md", "personas/quinn-airlock-canonical.md",
    "personas/avery-docket-canonical.md", "personas/nadia-traceveil-canonical.md",
    "personas/felix-garrison-canonical.md",
    "knowledge/ronan-threat-modeling-canonical.md", "knowledge/quinn-hardening-canonical.md",
    "knowledge/avery-structuring-canonical.md", "knowledge/nadia-exhaust-canonical.md",
    "knowledge/felix-human-reliability-canonical.md",
    "references/instruments/ronan-omnibus-canonical.md",
    "references/instruments/quinn-omnibus-canonical.md",
    "references/instruments/avery-omnibus-canonical.md",
    "references/instruments/nadia-omnibus-canonical.md",
    "references/instruments/felix-omnibus-canonical.md",
    "schemas/privacy-case.schema.json", "schemas/receipt.schema.json",
    "scripts/privacy_case_guardrail.py", "evals/eval-manifest.yaml",
]


def main() -> int:
    errors: list[str] = []
    for rel in REQUIRED:
        path = ROOT / rel
        if not path.is_file():
            errors.append(f"missing: {rel}")

    skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for match in re.findall(r"`([^`]+)`", skill_text):
        if match.startswith(("assets/", "knowledge/", "personas/", "references/", "scripts/", "schemas/", "fallbacks/")):
            if "\\" in match or ".." in Path(match).parts:
                errors.append(f"unsafe package path: {match}")
            elif not (ROOT / match).exists():
                errors.append(f"unresolved package path: {match}")

    for rel in ("manifest.json", "schemas/privacy-case.schema.json", "schemas/receipt.schema.json"):
        try:
            json.loads((ROOT / rel).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON {rel}: {exc}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: {len(REQUIRED)} required runtime resources present; package paths contained")
    return 0


if __name__ == "__main__":
    sys.exit(main())

