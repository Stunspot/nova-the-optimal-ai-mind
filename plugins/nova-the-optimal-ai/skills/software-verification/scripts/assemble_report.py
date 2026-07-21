#!/usr/bin/env python3
"""Assemble a canonical Markdown verification report from a valid manifest."""
from __future__ import annotations

import argparse
from pathlib import Path

from common.filesystem import load_data
from validate_manifest import validate


def bullets(items):
    return "\n".join(f"- {item}" for item in items) if items else "- None recorded"


def assemble(data: dict) -> str:
    report = validate(data)
    if not report["valid"]:
        raise ValueError("manifest invalid: " + "; ".join(report["errors"]))
    target = data["target"]; scope = data["scope"]; decision = data["decision"]
    lines = [
        "# Verification report", "", "## Decision", "",
        f"**Status:** {decision['status']}", f"**Target:** {target['name']}", f"**Revision:** {target['revision']}", f"**Reviewer:** {data['review']['status']}", "",
        "### Basis", "", bullets(decision.get("basis", [])), "",
        "## Scope", "", "### Included", "", bullets(scope.get("included", [])), "", "### Excluded", "", bullets(scope.get("excluded", [])), "",
        "## Critical invariants", "", bullets([f"{x.get('id')}: {x.get('statement')}" for x in data.get("invariants", [])]), "",
        "## Risk register", "", "| ID | Severity | Disposition | Risk |", "|---|---|---|---|",
    ]
    lines.extend(f"| {r.get('id')} | {r.get('severity')} | {r.get('disposition')} | {r.get('statement')} |" for r in data.get("risks", []))
    lines += ["", "## Execution evidence", "", "| ID | Status | Exit | Command | Raw evidence |", "|---|---|---:|---|---|"]
    lines.extend(f"| {e.get('id')} | {e.get('status')} | {e.get('exit_code', '')} | `{' '.join(e.get('command', []))}` | {e.get('raw_evidence') or 'not_available'} |" for e in data.get("executions", []))
    lines += ["", "## Findings", "", bullets([f"{f.get('id')} [{f.get('classification')}/{f.get('severity')}]: {f.get('statement')} — {f.get('status')}" for f in data.get("findings", [])]), "", "## Residual risk", "", bullets([f"{r.get('id')}: {r.get('statement')} — {r.get('treatment')}" for r in data.get("residual_risks", [])]), "", "## Authority still required", "", bullets(decision.get("authority_required", [])), ""]
    text = "\n".join(lines)
    if "REPLACE" in text or "{{" in text or "}}" in text:
        raise ValueError("unresolved placeholder in assembled report")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        text = assemble(load_data(args.manifest))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
