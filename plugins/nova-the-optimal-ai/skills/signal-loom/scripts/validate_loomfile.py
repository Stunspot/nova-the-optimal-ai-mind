#!/usr/bin/env python3
"""Validate core Signal Loom state without third-party dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


STAGES = ("intake", "spined", "planned", "built", "reviewed", "approved_for_export")
AUTHORITIES = {"draft", "reviewed", "approved"}
CLAIM_STATUSES = {"sourced", "inferred", "illustrative", "missing", "stale", "disputed"}
CURRENTNESS = {"timeless", "dated", "current-sensitive"}
REQUIRED_DIRS = (
    "sources/originals",
    "state",
    "output/web",
    "output/carousel",
    "output/platforms",
    "review",
    "checkpoints/snapshots",
)
REQUIRED_FILES = (
    "project.yaml",
    "sources/manifest.json",
    "state/brief.json",
    "state/claims.jsonl",
    "state/spine.json",
    "state/visual-plan.json",
    "state/theme.tokens.json",
    "state/interactions.json",
    "state/distribution.json",
    "state/decisions.jsonl",
)


def load_json(path: Path, errors: list[str]) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.name}: invalid JSON-compatible data: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path.name}: expected a JSON object")
        return {}
    return value


def within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(root: Path, verify_hashes: bool = True) -> tuple[list[str], list[str]]:
    root = root.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    if not root.is_dir():
        return [f"not a Loomfile directory: {root}"], warnings

    for relative in REQUIRED_DIRS:
        path = root / relative
        if not path.is_dir() or path.is_symlink():
            errors.append(f"missing or unsafe required directory: {relative}")
    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            errors.append(f"missing or unsafe required file: {relative}")
    if errors:
        return errors, warnings

    project = load_json(root / "project.yaml", errors)
    stage = project.get("stage")
    authority = project.get("authority_status")
    if stage not in STAGES:
        errors.append(f"project.yaml: invalid stage {stage!r}")
    if authority not in AUTHORITIES:
        errors.append(f"project.yaml: invalid authority_status {authority!r}")
    if project.get("publication_status") != "manual_only":
        errors.append("project.yaml: publication_status must remain manual_only")
    if not isinstance(project.get("requested_outputs"), list) or not project.get("requested_outputs"):
        errors.append("project.yaml: requested_outputs must be a non-empty list")
    if stage == "approved_for_export" and authority != "approved":
        errors.append("project.yaml: approved_for_export requires human authority_status approved")

    manifest = load_json(root / "sources" / "manifest.json", errors)
    source_ids: set[str] = set()
    for index, source in enumerate(manifest.get("sources", []), 1):
        if not isinstance(source, dict):
            errors.append(f"sources/manifest.json: source {index} is not an object")
            continue
        source_id = source.get("id")
        if not isinstance(source_id, str) or not source_id:
            errors.append(f"sources/manifest.json: source {index} has no id")
            continue
        if source_id in source_ids:
            errors.append(f"sources/manifest.json: duplicate id {source_id}")
        source_ids.add(source_id)
        relative = source.get("path")
        if not isinstance(relative, str) or not relative:
            errors.append(f"sources/manifest.json: {source_id} has no path")
            continue
        path = root / relative
        if not within(root, path):
            errors.append(f"sources/manifest.json: {source_id} path escapes Loomfile")
            continue
        if not path.is_file() or path.is_symlink():
            errors.append(f"sources/manifest.json: {source_id} file missing or unsafe: {relative}")
            continue
        expected = source.get("sha256")
        if verify_hashes and expected:
            actual = sha256(path)
            if actual.lower() != str(expected).lower():
                errors.append(f"sources/manifest.json: {source_id} hash mismatch")
        elif not expected:
            warnings.append(f"sources/manifest.json: {source_id} has no recorded hash")

    claims_path = root / "state" / "claims.jsonl"
    for line_number, raw in enumerate(claims_path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            claim = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"state/claims.jsonl:{line_number}: invalid JSON: {exc}")
            continue
        if not isinstance(claim, dict):
            errors.append(f"state/claims.jsonl:{line_number}: expected object")
            continue
        status = claim.get("status")
        currentness = claim.get("currentness")
        if status not in CLAIM_STATUSES:
            errors.append(f"state/claims.jsonl:{line_number}: invalid status {status!r}")
        if currentness not in CURRENTNESS:
            errors.append(f"state/claims.jsonl:{line_number}: invalid currentness {currentness!r}")
        source_id = claim.get("source_id")
        if status == "sourced" and source_id not in source_ids:
            errors.append(f"state/claims.jsonl:{line_number}: sourced claim lacks a valid source_id")
        if status == "sourced" and not claim.get("locator"):
            errors.append(f"state/claims.jsonl:{line_number}: sourced claim lacks a locator")
        if currentness == "current-sensitive" and status == "sourced" and not claim.get("as_of"):
            errors.append(f"state/claims.jsonl:{line_number}: current-sensitive sourced claim lacks as_of")
        if stage == "approved_for_export" and status in {"missing", "stale", "disputed"}:
            errors.append(f"state/claims.jsonl:{line_number}: unresolved claim blocks approved_for_export")

    stage_index = STAGES.index(stage) if stage in STAGES else 0
    if stage_index >= STAGES.index("built") and not (root / "output" / "web" / "index.html").is_file():
        errors.append("stage built or later requires output/web/index.html")
    if stage_index >= STAGES.index("reviewed") and not (root / "review" / "diagnostics.json").is_file():
        errors.append("stage reviewed or later requires review/diagnostics.json")
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("loomfile", type=Path)
    parser.add_argument("--skip-hashes", action="store_true")
    args = parser.parse_args(argv)
    errors, warnings = validate(args.loomfile, verify_hashes=not args.skip_hashes)
    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"PASS: Loomfile core checks ({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
