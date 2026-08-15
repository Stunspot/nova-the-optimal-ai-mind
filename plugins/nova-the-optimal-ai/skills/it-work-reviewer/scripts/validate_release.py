#!/usr/bin/env python3
"""Create or validate the Beryl IT Benchcraft release manifest and runtime paths."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

MANIFEST = "release-manifest.json"
REQUIRED = {
    "README.md", "PROVENANCE.md", "SKILL.md",
    "personas/beryl-it-benchcraft-practitioner.md",
    "knowledge/windows-systems-engineering.md", "knowledge/network-architecture.md",
    "assets/it-case.template.json", "schemas/it-case.schema.json",
    "scripts/validate_case_file.py", "scripts/validate_release.py",
    "evals/eval-manifest.yaml", "evals/core-transfer-cases.yaml",
    "fallbacks/universal-copy-paste-workflow.md", "docs/QUICK-START.md",
}
TEXT_SUFFIXES = {".md", ".txt", ".yaml", ".yml", ".json", ".py"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inventory(root: Path) -> dict[str, dict[str, object]]:
    result = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if rel == MANIFEST:
            continue
        result[rel] = {"sha256": digest(path), "bytes": path.stat().st_size}
    return result


def validate_paths(root: Path, files: dict[str, dict[str, object]]) -> list[str]:
    errors = []
    missing = sorted(REQUIRED - files.keys())
    if missing:
        errors.append("missing required files: " + ", ".join(missing))
    for rel in ("SKILL.md",):
        path = root / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8-sig")
        if not text.startswith("---\n") or "\nname:" not in text[:500] or "\ndescription:" not in text[:1000]:
            errors.append(f"invalid skill frontmatter: {rel}")
        for token in re.findall(r"`((?:\.\./)+[^`]+)`", text):
            target = (path.parent / token).resolve()
            if not target.exists():
                errors.append(f"broken runtime path in {rel}: {token}")
    for rel in files:
        path = root / rel
        if path.suffix.lower() in TEXT_SUFFIXES:
            try:
                path.read_text(encoding="utf-8-sig")
            except UnicodeError as exc:
                errors.append(f"text encoding failure {rel}: {exc}")
    for rel in ("assets/it-case.template.json", "schemas/it-case.schema.json", "evals/eval-manifest.yaml", "evals/core-transfer-cases.yaml"):
        if (root / rel).exists():
            try:
                json.loads((root / rel).read_text(encoding="utf-8-sig"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                errors.append(f"JSON-compatible parse failure {rel}: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    files = inventory(root)
    errors = validate_paths(root, files)
    if args.write_manifest and not errors:
        payload = {"package": "beryl-it-benchcraft", "version": "0.1.3", "files": files}
        (root / MANIFEST).write_bytes((json.dumps(payload, indent=2) + "\n").encode("utf-8"))
    manifest_path = root / MANIFEST
    if manifest_path.exists() and not args.write_manifest:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            if manifest.get("files") != files:
                errors.append("release manifest does not match current file inventory")
        except (UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"invalid release manifest: {exc}")
    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1
    print(f"PASS {root} ({len(files)} manifested files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
