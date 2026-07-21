#!/usr/bin/env python3
"""Check Signal Loom package structure and static contracts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REQUIRED = (
    "SKILL.md",
    "agents/openai.yaml",
    "manifest.json",
    "knowledge/infographic-toolkit-v2-canonical.md",
    "knowledge/infographic-toolkit-users-guide-canonical.md",
    "knowledge/operating-doctrine.md",
    "assets/canonical/infographic-toolkit-cover.png",
    "assets/loomfile.template/project.yaml",
    "schemas/project.schema.json",
    "scripts/init_loomfile.py",
    "scripts/validate_loomfile.py",
    "scripts/inspect_infographic_html.py",
    "scripts/package_loomfile.py",
    "fallbacks/degraded-capability.md",
    "fallbacks/universal-copy-paste-workflow.md",
    "evals/eval-manifest.yaml",
)


def run() -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED:
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            errors.append(f"missing or unsafe package resource: {relative}")
    skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not skill_text.startswith("---\n"):
        errors.append("SKILL.md does not begin with YAML frontmatter")
    match = re.search(r"^name:\s*(.+)$", skill_text, flags=re.MULTILINE)
    if not match or match.group(1).strip() != "signal-loom":
        errors.append("SKILL.md frontmatter name must be signal-loom")
    agent_text = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    if "$signal-loom" not in agent_text:
        errors.append("agents/openai.yaml default_prompt must invoke $signal-loom")
    try:
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"manifest.json invalid: {exc}")
    else:
        if manifest.get("name") != "signal-loom" or manifest.get("version") != "0.1.0":
            errors.append("manifest identity or version mismatch")
        if sorted(manifest.get("hosts", [])) != ["claude", "codex"]:
            errors.append("manifest must declare separate Codex and Claude hosts")
    for schema_path in sorted((ROOT / "schemas").glob("*.json")):
        try:
            json.loads(schema_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON schema {schema_path.name}: {exc}")
    for path in ROOT.rglob("*"):
        if path.is_symlink():
            errors.append(f"symbolic link not permitted: {path.relative_to(ROOT)}")
    return errors


def main() -> int:
    errors = run()
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAIL: {len(errors)} package error(s)")
        return 1
    print("PASS: Signal Loom package self-check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
