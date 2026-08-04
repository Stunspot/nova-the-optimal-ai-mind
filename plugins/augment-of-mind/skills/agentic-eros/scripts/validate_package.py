#!/usr/bin/env python3
"""Validate the self-contained Agentic Eros skill package."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "SKILL.md",
    "manifest.json",
    "agents/openai.yaml",
    "references/eros-and-relational-perception.md",
    "references/evidence-and-boundaries.md",
    "references/desire-and-response.md",
    "references/discovery-and-personalization.md",
    "references/seduction-and-embodiment.md",
    "references/roleplay-and-continuity.md",
    "references/pacing-completion-and-closure.md",
    "references/variation-and-inclusion.md",
    "references/host-policy-adapter.md",
    "assets/preference-capsule.md",
    "assets/scene-state-card.md",
    "examples/sparse-signal.md",
    "examples/responsive-pivot.md",
    "examples/completion-variants.md",
    "examples/relational-restraint.md",
    "examples/ambiguous-charge.md",
    "examples/ambient-analysis.md",
    "evals/eval-manifest.yaml",
    "evals/core-transfer-cases.yaml",
    "fallbacks/copy-paste-prompt.md",
]
FORBIDDEN = [
    "[TODO:",
    "C:\\Users\\",
    "E:\\Indranet\\",
    "E:\\Github\\",
    "Erotic Literature Virtuoso - E.L. James",
    "Seduction Exploits",
]


def main() -> int:
    errors: list[str] = []
    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            errors.append(f"missing required file: {rel}")

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not skill.startswith("---\nname: agentic-eros\n"):
        errors.append("SKILL.md frontmatter name is invalid")
    description = re.search(r"^description:\s*(.+)$", skill, re.MULTILINE)
    if not description or not 25 <= len(description.group(1).strip()) <= 512:
        errors.append("SKILL.md description must be 25-512 Unicode characters")

    markdown_link = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for target in markdown_link.findall(skill):
        if "://" not in target and not (ROOT / target).is_file():
            errors.append(f"SKILL.md link target missing: {target}")

    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".json", ".yaml", ".py"}:
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT).as_posix()
        if rel != "scripts/validate_package.py":
            for token in FORBIDDEN:
                if token in text:
                    errors.append(f"forbidden runtime token in {rel}: {token}")

    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("name") != "agentic-eros" or manifest.get("version") != "0.2.0":
        errors.append("manifest identity or version mismatch")
    if "canonical_host_mode" in manifest:
        errors.append("manifest must not expose a selectable host mode")

    eval_manifest = json.loads((ROOT / "evals/eval-manifest.yaml").read_text(encoding="utf-8"))
    suite = json.loads((ROOT / "evals/core-transfer-cases.yaml").read_text(encoding="utf-8"))
    if eval_manifest.get("format") != "cd-augment-eval/v1" or suite.get("format") != "cd-augment-eval/v1":
        errors.append("evaluation format mismatch")
    if eval_manifest.get("package_version") != suite.get("package_version"):
        errors.append("evaluation package versions differ")
    cases = suite.get("cases", [])
    ids = [case.get("id") for case in cases]
    if len(cases) < 18 or len(ids) != len(set(ids)):
        errors.append("evaluation suite must contain at least 18 uniquely identified cases")
    expected_ids = [f"AE-{number:03d}" for number in range(1, 19)]
    if ids != expected_ids:
        errors.append("evaluation case IDs must be the ordered AE-001 through AE-018 contract")
    required_case_fields = {
        "id", "concern", "dimensions", "input", "expected_behaviors",
        "acceptable_variation", "failure_signals",
    }
    for case in cases:
        missing = required_case_fields - set(case)
        if missing:
            errors.append(f"case {case.get('id', 'UNKNOWN')} missing fields: {sorted(missing)}")
        policy = case.get("followup_policy")
        if policy is not None and policy != "always_after_initial":
            errors.append(f"case {case.get('id', 'UNKNOWN')} has unsupported followup policy: {policy}")
        if policy == "always_after_initial" and not isinstance(case.get("on_question_reply"), str):
            errors.append(f"case {case.get('id', 'UNKNOWN')} followup policy lacks a reply turn")
    observed_dimensions = {dimension for case in cases for dimension in case.get("dimensions", [])}
    absent = set(eval_manifest.get("indispensable_dimensions", [])) - observed_dimensions
    if absent:
        errors.append(f"indispensable dimensions absent from cases: {sorted(absent)}")

    agent_yaml = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
    if 'display_name: "Agentic Eros"' not in agent_yaml:
        errors.append("agents/openai.yaml display name mismatch")
    default_prompt = re.search(r'^\s*default_prompt:\s*"([^"]+)"\s*$', agent_yaml, re.MULTILINE)
    if not default_prompt or len(default_prompt.group(1)) > 128:
        errors.append("agents/openai.yaml default prompt must be present and at most 128 characters")
    if "$agentic-eros" not in agent_yaml:
        errors.append("agents/openai.yaml default prompt must invoke $agentic-eros")
    if "$erotic-intelligence" in agent_yaml:
        errors.append("agents/openai.yaml must not expose the legacy alias")
    if "allow_implicit_invocation: true" not in agent_yaml:
        errors.append("agents/openai.yaml must keep Agentic Eros available for implicit relevance routing")

    fallback = (ROOT / "fallbacks/copy-paste-prompt.md").read_text(encoding="utf-8")
    if "[HOST MODE:" in fallback or "Replace the bracketed host mode" in fallback:
        errors.append("fallback must not expose a host-mode selector")
    if "not a costume or a mode to announce" not in fallback:
        errors.append("fallback lacks the non-theatrical ambient-use contract")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"VALID: {ROOT}")
    print(f"CASES: {len(cases)}")
    print(f"FILES: {sum(1 for path in ROOT.rglob('*') if path.is_file())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
