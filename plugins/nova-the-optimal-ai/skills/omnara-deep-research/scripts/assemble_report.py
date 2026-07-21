#!/usr/bin/env python3
"""Assemble ordered Markdown section drafts and report length evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def assemble(directory: Path) -> dict:
    drafts = sorted((directory / "draft").glob("*.md"))
    if not drafts:
        raise ValueError("no Markdown section drafts found")
    text = "\n\n".join(path.read_text(encoding="utf-8").strip() for path in drafts) + "\n"
    report = directory / "report.md"
    report.write_text(text, encoding="utf-8")
    words = re.findall(r"\b[\w'-]+\b", text)
    result = {
        "sections": len(drafts),
        "words": len(words),
        "estimated_pages_300_words": round(len(words) / 300, 1),
        "estimated_pages_500_words": round(len(words) / 500, 1),
        "estimate_boundary": "Rendered pages depend on layout, figures, tables, and citation density.",
    }
    (directory / "report-metrics.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(assemble(args.directory), indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
