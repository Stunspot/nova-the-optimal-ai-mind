from __future__ import annotations

import argparse
from pathlib import Path

from exportlib import ExportError, approve_candidate, build_pack, verify_pack


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Build inspectable, offline Ludis campaign packs.")
    sub = command.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="Build a GM pack or a reviewable player candidate.")
    build.add_argument("campaign", type=Path, help="Campaign directory containing campaign-ledger.json.")
    build.add_argument("output", type=Path, help="Output .zip; player candidates must end in .candidate.zip.")
    build.add_argument("--audience", choices=("gm", "player"), required=True)
    build.add_argument("--object", dest="objects", action="append", default=[], help="Limit to one object id; repeat as needed.")

    approve = sub.add_parser("approve", help="Approve exact player-candidate and preview bytes, then finalize unchanged bytes.")
    approve.add_argument("candidate", type=Path)
    approve.add_argument("--asserted-by", required=True, help="Unauthenticated local operator label recorded in the approval receipt.")
    approve.add_argument("--final", type=Path, help="Optional final .zip path.")

    verify = sub.add_parser("verify", help="Verify a Ludis Pack member inventory and digests.")
    verify.add_argument("pack", type=Path)
    return command


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "build":
            result = build_pack(args.campaign, args.output, args.audience, args.objects or None)
            state = "FINAL" if result.finalized else "APPROVAL REQUIRED"
            print(f"PASS: {state}: {result.artifact}")
            print(f"SHA256: {result.artifact_sha256.upper()}")
            print(f"AUDIT: {result.audit}")
            print(f"PREVIEW: {result.preview}")
            if result.audience == "player":
                print("REVIEW: extract a new review copy; compare every member with the preview and audit; inspect or listen to non-rendered members; treat code as text and do not execute it before approval.")
            return 0
        if args.command == "approve":
            final, receipt = approve_candidate(args.candidate, args.asserted_by, args.final)
            print(f"PASS: FINALIZED UNCHANGED: {final}")
            print(f"SHA256: {verify_pack(final)['sha256'].upper()}")
            print(f"APPROVAL: {receipt}")
            return 0
        report = verify_pack(args.pack)
        print(f"PASS: {report['format']} {report['audience']} pack; {report['members']} archive members")
        print(f"SHA256: {report['sha256'].upper()}")
        return 0
    except (ExportError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
