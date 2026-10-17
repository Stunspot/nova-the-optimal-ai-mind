#!/usr/bin/env python3
"""Create an empty Officefile without overwriting an existing destination."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ASSETS = SCRIPT_DIR.parent / "assets"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def initialize(destination: Path, project_id: str | None = None) -> dict[str, object]:
    destination = destination.resolve()
    if destination.exists():
        raise ValueError(f"Refusing to overwrite existing destination: {destination}")
    if destination.parent.exists() is False:
        raise ValueError(f"Parent directory does not exist: {destination.parent}")

    chosen_project_id = project_id or destination.name
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", chosen_project_id):
        raise ValueError("project_id must use letters, digits, dots, underscores, or hyphens")
    destination.mkdir()
    for relative in ("sources", "state", "working", "output", "review"):
        (destination / relative).mkdir()

    copied = {
        "state/brief.json": "brief-template.json",
        "sources/manifest.json": "source-manifest-template.json",
        "state/content-ledger.json": "content-ledger-template.json",
        "state/artifact-register.json": "artifact-register-template.json",
        "review/officecraft-review.json": "review-template.json",
    }
    for destination_name, source_name in copied.items():
        shutil.copyfile(ASSETS / source_name, destination / destination_name)

    brief_path = destination / "state" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["project_id"] = chosen_project_id
    brief["created_at"] = utc_now()
    brief["updated_at"] = brief["created_at"]
    write_json(brief_path, brief)
    (destination / "state" / "decisions.jsonl").write_text("", encoding="utf-8", newline="\n")
    shutil.copyfile(ASSETS / "handoff-template.md", destination / "HANDOFF.md")
    shutil.copyfile(ASSETS / "style-brief-template.md", destination / "working" / "style-brief.md")
    return {"format": "officecraft-init/v1", "officefile": str(destination), "created": sorted(copied) + ["HANDOFF.md", "state/decisions.jsonl", "working/style-brief.md"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", help="new Officefile directory")
    parser.add_argument("--project-id", help="safe project identifier; defaults to destination name")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(initialize(Path(args.destination), args.project_id), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"format": "officecraft-init/v1", "created": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
