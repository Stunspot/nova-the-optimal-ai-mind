#!/usr/bin/env python3
"""Run deterministic structural checks for the self-contained skill."""

from __future__ import annotations

import argparse
import json
import os
import stat
import re
import sys
from pathlib import Path

from validate_learner_profile import validate_profile


REQUIRED = {
    "SKILL.md",
    "scripts/validate_learner_profile.py",
    "scripts/validate_release.py",
    "scripts/tests/test_evidence_contract.py",
    "examples/progress-and-return/demonstration.md",
    "examples/progress-and-return/fictional-profile.json",
    "examples/progress-and-return/observed-profile.json",
    "examples/urgent-first-value/demonstration.md",
    "examples/fluency-with-selective-correction/demonstration.md",
    "examples/ambiguous-workplace-translation/demonstration.md",
    "examples/consequential-language-boundary/demonstration.md",
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
    root = Path(os.path.abspath(root))
    try:
        for p in [root, *root.parents]:
            s = p.lstat()
            if stat.S_ISLNK(s.st_mode) or getattr(s, 'st_file_attributes', 0) & 0x400:
                return [f'linked/reparse root is not portable: {p}']
        for parent, dirs, names in os.walk(root, followlinks=False):
            for name in dirs + names:
                p = Path(parent) / name; s = p.lstat()
                if stat.S_ISLNK(s.st_mode) or getattr(s, 'st_file_attributes', 0) & 0x400:
                    return [f'linked/reparse entry is not portable: {p}']
    except OSError as exc:
        return [f'cannot inspect runtime tree: {exc}']
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
        template = parsed[profile_path]
        if not isinstance(template, dict) or any(template.get(k) != [] for k in ('evidence','goals','retrieval_queue')):
            errors.append('creation template must contain no learner history')
        else:
            probe = dict(template, profile_id='template-check', updated_at='2026-10-06T00:00:00Z', working_language='English', target_languages=[dict(language='Spanish', variety='unspecified', script='Latin')])
            errors.extend('filled template: '+e for e in validate_profile(probe))
    for name in ('fictional-profile.json', 'observed-profile.json'):
        p = root / 'examples/progress-and-return' / name
        if p.exists():
            try: errors.extend(name+': '+e for e in validate_profile(json.loads(p.read_text(encoding='utf-8'))))
            except (OSError, ValueError, UnicodeError) as exc: errors.append(f'{name}: {exc}')

    manifest_path = root / "evals/eval-manifest.yaml"
    suite_path = root / "evals/core-transfer-cases.yaml"
    if manifest_path in parsed and not isinstance(parsed[manifest_path], dict): errors.append("eval manifest must be an object")
    if suite_path in parsed and not isinstance(parsed[suite_path], dict): errors.append("eval suite must be an object")
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
            for case in cases:
                if not isinstance(case, dict) or not isinstance(case.get('id'), str) or not case['id'].strip() or not isinstance(case.get('input'), str) or not case['input'].strip():
                    errors.append('eval case needs a nonempty id and actual input')
                    continue
                for key in ('expected_behaviors', 'failure_signals'):
                    if not isinstance(case.get(key), list) or not case[key] or any(not isinstance(x, str) or not x.strip() for x in case[key]): errors.append(f'eval {case["id"]}: malformed {key}')
            ids = [case.get("id") for case in cases if isinstance(case, dict) and isinstance(case.get('id'), str)]
            if len(ids) != len(set(ids)):
                errors.append("eval case IDs are not unique")

    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', type=Path, default=Path(__file__).resolve().parents[1])
    root = parser.parse_args(argv[1:]).root
    try: errors = validate(root)
    except (OSError, ValueError, UnicodeError, TypeError) as exc: errors = [f'cannot validate runtime: {exc}']
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
