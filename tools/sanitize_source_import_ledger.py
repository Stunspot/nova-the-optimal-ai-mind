#!/usr/bin/env python3
"""Publish a path-safe source-import receipt from a private custody ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def alias_imported(row: dict) -> str:
    return f"source://{row['selection']}/{row['destination']}"


def alias_excluded(row: dict, index: int) -> str:
    name = Path(row["source"]).name or "source-item"
    return f"source://{row['selection']}/excluded/{index:04d}-{name}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-ledger", required=True, type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "verification" / "source-import-ledger.json",
    )
    args = parser.parse_args()

    payload = json.loads(args.private_ledger.read_text(encoding="utf-8"))
    payload["repository"] = "."
    for row in payload["imported"]:
        row["source"] = alias_imported(row)
    for index, row in enumerate(payload["excluded"], start=1):
        row["source"] = alias_excluded(row, index)
    payload["path_custody"] = {
        "public_representation": "Logical source aliases only; no machine-local source paths are embedded.",
        "private_original": "Retained by the release operator outside public Git custody.",
    }
    payload["boundary"] = (
        "This public ledger proves byte custody for the initial import through destination and SHA-256 records. "
        "Logical source aliases deliberately omit machine-local paths. Subsequent curated repository edits "
        "require Git and verification evidence."
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "imported": len(payload["imported"]),
                "excluded": len(payload["excluded"]),
                "output": args.output.relative_to(ROOT).as_posix(),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
