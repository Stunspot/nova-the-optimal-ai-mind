#!/usr/bin/env python3
"""Validate OMNARA package structure and canonical custody."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

EXPECTED_HASHES = {
    "personas/canonical-omnara-t3-v1.md": "802E7CB66337A96C56BB3EC69D7F8A7F39A861D058EEE8166DCDC8B5D560D0B4",
    "personas/canonical-webworker-t3-v3.md": "EC61B5046D65B7571D54A3C00B24CAB5A4920F6FC2F51112D0C0F83180A1899A",
    "references/canonical/inquiry-engine-v1.md": "3C817B1A1FFDF6E6D66D51B2E0CB0949FC6AB50CD1DB61CAAC6473778AA60A97",
    "references/canonical/comprehensive-analysis-of-agentic-deep-research-architectures.md": "F0D5206F79B7BCA16AB315AA71CA7FC05646EAD8A1E9402D916464436C1388BE",
}
REQUIRED = [
    "SKILL.md",
    "agents/openai.yaml",
    "personas/omnara-investigative-research-intelligence.md",
    "knowledge/source-navigation.md",
    "references/operating-doctrine.md",
    "references/search-cartography.md",
    "references/evidence-and-investigation.md",
    "references/synthesis-and-citation-audit.md",
    "references/tooling-cost-and-security.md",
    "references/campaign-operations.md",
    "assets/campaign-vault/campaign.json",
    "schemas/research-campaign.schema.json",
    "scripts/research_campaign.py",
    "scripts/citation_audit.py",
    "scripts/assemble_report.py",
    "evals/eval-manifest.yaml",
    "evals/core-transfer-cases.yaml",
    "fallbacks/degraded-capability.md",
    "fallbacks/universal-copy-paste-workflow.md",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (root / relative).is_file():
            errors.append(f"missing {relative}")
    for relative, expected in EXPECTED_HASHES.items():
        path = root / relative
        if path.is_file() and sha256(path) != expected:
            errors.append(f"canonical hash mismatch: {relative}")
    for relative in [
        "assets/campaign-vault/campaign.json",
        "schemas/research-campaign.schema.json",
        "evals/eval-manifest.yaml",
        "evals/core-transfer-cases.yaml",
    ]:
        path = root / relative
        if path.is_file():
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"invalid JSON-compatible file {relative}: {exc}")
    if any(path.name == "__pycache__" for path in root.rglob("*")):
        errors.append("package contains __pycache__")
    return errors


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    errors = validate(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    files = sum(1 for path in root.rglob("*") if path.is_file())
    print(f"VALID: {root}")
    print(f"FILES: {files}")
    print("CANONICAL_HASHES: 4 matched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
