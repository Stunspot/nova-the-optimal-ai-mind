#!/usr/bin/env python3
"""Run deterministic structural checks for the self-contained skill."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from validate_learner_profile import validate_profile


REQUIRED = {
    "SKILL.md",
    "agents/openai.yaml",
    "personas/lex-foster-language-companion.md",
    "references/operating-doctrine.md",
    "references/translation-and-localization.md",
    "references/learner-model-and-progress.md",
    "references/culture-protocol-and-variation.md",
    "references/pronunciation-and-script-support.md",
    "references/trust-privacy-and-high-stakes.md",
    "references/evidence-foundations.md",
    "assets/learner-profile.template.json",
    "assets/language-mission.template.md",
    "assets/translation-brief.template.md",
    "assets/session-recap.template.md",
    "schemas/learner-profile.schema.json",
    "fallbacks/universal-copy-paste-companion.md",
    "evals/eval-manifest.yaml",
    "evals/core-transfer-cases.yaml",
}


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in sorted(REQUIRED):
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")

    skill_path = root / "SKILL.md"
    if skill_path.is_file():
        skill_text = skill_path.read_text(encoding="utf-8")
        match = re.match(
            r'^---\s*\nname:\s*([^\n]+)\ndescription:\s*"([^"]+)"\s*\n---',
            skill_text,
        )
        if not match:
            errors.append("SKILL.md frontmatter is not in the expected minimal form")
        else:
            if match.group(1).strip() != root.name:
                errors.append("SKILL.md name does not match the skill directory")
            description = match.group(2)
            if not 25 <= len(description) <= 45:
                errors.append(
                    f"SKILL.md description length is {len(description)}; expected 25-45"
                )

    for path in root.rglob("*"):
        if path.is_symlink():
            errors.append(f"symlink is not portable: {path.relative_to(root)}")
        if not path.is_file() or path.suffix.lower() not in {
            ".md",
            ".json",
            ".yaml",
            ".yml",
        }:
            continue
        text = path.read_text(encoding="utf-8")
        if "\ufffd" in text:
            errors.append(f"replacement character found: {path.relative_to(root)}")
        if "../" in text or "..\\" in text:
            errors.append(f"upward path traversal found: {path.relative_to(root)}")

    json_files = [
        root / "assets/learner-profile.template.json",
        root / "schemas/learner-profile.schema.json",
        root / "evals/eval-manifest.yaml",
        root / "evals/core-transfer-cases.yaml",
    ]
    parsed: dict[Path, object] = {}
    for path in json_files:
        if not path.is_file():
            continue
        try:
            parsed[path] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON-compatible content in {path.name}: {exc}")

    profile_path = root / "assets/learner-profile.template.json"
    if profile_path in parsed:
        for error in validate_profile(parsed[profile_path]):
            errors.append(f"learner profile template: {error}")

    manifest_path = root / "evals/eval-manifest.yaml"
    suite_path = root / "evals/core-transfer-cases.yaml"
    if isinstance(parsed.get(manifest_path), dict):
        manifest = parsed[manifest_path]
        if manifest.get("format") != "cd-augment-eval/v1":
            errors.append("eval manifest format is not cd-augment-eval/v1")
        if manifest.get("files") != ["core-transfer-cases.yaml"]:
            errors.append("eval manifest files do not bind the core suite")
    if isinstance(parsed.get(suite_path), dict):
        suite = parsed[suite_path]
        if suite.get("format") != "cd-augment-eval/v1":
            errors.append("eval suite format is not cd-augment-eval/v1")
        cases = suite.get("cases")
        if not isinstance(cases, list) or not cases:
            errors.append("eval suite contains no cases")
        else:
            ids = [case.get("id") for case in cases if isinstance(case, dict)]
            if len(ids) != len(set(ids)):
                errors.append("eval case IDs are not unique")

    return errors


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 else Path(__file__).resolve().parents[1]
    errors = validate(root)
    if errors:
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        print(f"FAIL {root}: {len(errors)} error(s)", file=sys.stderr)
        return 1

    file_count = sum(1 for path in root.rglob("*") if path.is_file())
    print(f"PASS {root}: {file_count} files, self-contained structural checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
