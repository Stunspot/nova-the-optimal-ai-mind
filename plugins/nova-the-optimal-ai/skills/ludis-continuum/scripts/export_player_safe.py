from __future__ import annotations

import argparse
from pathlib import Path

from exportlib import ExportError, build_pack


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a reviewable, audience-separated Ludis player pack.")
    parser.add_argument("ledger", type=Path, help="Path to campaign-ledger.json.")
    parser.add_argument("output", type=Path, help="Must end in .candidate.zip.")
    args = parser.parse_args()
    if args.ledger.name != "campaign-ledger.json":
        print("FAIL: ledger must be named campaign-ledger.json inside its campaign workspace")
        return 2
    try:
        result = build_pack(args.ledger.parent, args.output, "player")
    except (ExportError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 2
    print(f"PASS: APPROVAL REQUIRED: {result.artifact}")
    print(f"SHA256: {result.artifact_sha256.upper()}")
    print(f"PREVIEW: {result.preview}")
    print("REVIEW: extract a new review copy; compare every member with the preview and audit; inspect or listen to non-rendered members; treat code as text and do not execute it before approval. Then use export_campaign.py approve. No legacy boolean confers current approval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
