#!/usr/bin/env python3
"""Statically verify a Codex plugin, skill, or generic source package."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common.filesystem import iter_files, write_json


PRIVATE_PATH = re.compile(
    r"(?:[A-Za-z]:\\+(?:Users|Documents and Settings)\\+[^\\\s]+|/Users/[^/\s]+|/home/[^/\s]+)",
    re.IGNORECASE,
)
RELATIVE_LINK = re.compile(r"`((?:\.?\.?/)+[^`]+)`")


def _required_files(root: Path) -> tuple[list[str], str]:
    if (root / ".codex-plugin" / "plugin.json").is_file():
        return [".codex-plugin/plugin.json"], "codex-plugin"
    if (root / "SKILL.md").is_file():
        return ["SKILL.md", "agents/openai.yaml"], "codex-skill"
    if any((root / name).is_file() for name in ("pyproject.toml", "package.json", "Cargo.toml", "go.mod")):
        return [], "source-package"
    return [], "generic-directory"


def verify(root: Path, extra_required: list[str] | None = None) -> dict:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    checked = 0
    required, package_type = _required_files(root)
    required.extend(extra_required or [])
    if package_type == "generic-directory":
        warnings.append("no recognized package descriptor; structural checks only")
    for rel in required:
        if not (root / rel).is_file():
            errors.append(f"missing required file: {rel}")

    skill_count = 0
    for path in iter_files(root):
        checked += 1
        rel = path.relative_to(root).as_posix()
        if path.suffix.lower() == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"invalid JSON {rel}: {exc}")
        if path.suffix.lower() == ".py":
            try:
                compile(path.read_text(encoding="utf-8-sig"), str(path), "exec")
            except (OSError, SyntaxError) as exc:
                errors.append(f"invalid Python {rel}: {exc}")
        if path.suffix.lower() not in {".md", ".txt", ".yaml", ".yml", ".json", ".py"}:
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if path.name != "verify_package.py" and PRIVATE_PATH.search(text):
            errors.append(f"private absolute path found in {rel}")
        if path.name == "SKILL.md":
            skill_count += 1
            if not text.startswith("---\n") or "\nname:" not in text[:1000] or "\ndescription:" not in text[:2000]:
                errors.append(f"invalid skill envelope: {rel}")
            for raw in RELATIVE_LINK.findall(text):
                clean = raw.split("#", 1)[0]
                candidate = (path.parent / clean).resolve()
                if not candidate.exists():
                    errors.append(f"broken skill resource path in {rel}: {raw}")

    if package_type == "codex-plugin" and skill_count == 0:
        errors.append("Codex plugin contains no SKILL.md")
    return {
        "valid": not errors,
        "root": str(root),
        "package_type": package_type,
        "files_checked": checked,
        "skills_checked": skill_count,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--require", action="append", default=[], help="Additional required relative file")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify(args.package, args.require)
    if args.output:
        write_json(args.output, report)
    else:
        print(json.dumps(report, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
