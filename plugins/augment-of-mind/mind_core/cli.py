"""Administrative CLI and cooperative H0 entrypoints for MIND Core."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .core import MindCore
from .errors import MindCoreError
from .service import QueryService, serve
from .util import canonical_json


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mind-core")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "status", "serve"):
        command = subparsers.add_parser(name)
        command.add_argument("--database", required=True, type=Path)
    bootstrap = subparsers.add_parser("bootstrap")
    bootstrap.add_argument("--database", required=True, type=Path)
    bootstrap.add_argument("--manifest", required=True, type=Path)
    index = subparsers.add_parser("index")
    index.add_argument("--database", required=True, type=Path)
    index.add_argument("--manifest", required=True, type=Path)
    activate = subparsers.add_parser("activate-estate-generation")
    activate.add_argument("--database", required=True, type=Path)
    activate.add_argument("--bootstrap", required=True, type=Path)
    activate.add_argument("--index", required=True, type=Path)
    issue = subparsers.add_parser("issue-session-capability")
    issue.add_argument("--database", required=True, type=Path)
    issue.add_argument("--agent-instance-id", required=True)
    issue.add_argument("--host-session-id", required=True)
    issue.add_argument(
        "--exposure-scope",
        choices=("public_only", "public_and_agent_private"),
        default="public_only",
    )
    issue.add_argument("--expires-at")
    revoke = subparsers.add_parser("revoke-session-capability")
    revoke.add_argument("--database", required=True, type=Path)
    revoke.add_argument("--session-capability", required=True)
    query = subparsers.add_parser("query")
    query.add_argument("--database", required=True, type=Path)
    query.add_argument("--request", required=True, type=Path)
    return parser


def _write_json(value: Any) -> None:
    sys.stdout.buffer.write((canonical_json(value) + "\n").encode("utf-8"))
    sys.stdout.buffer.flush()


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "activate-estate-generation":
            bootstrap = json.loads(args.bootstrap.read_text(encoding="utf-8"))
            index = json.loads(args.index.read_text(encoding="utf-8"))
            if not isinstance(bootstrap, dict):
                raise ValueError("bootstrap manifest must be a JSON object")
            if not isinstance(index, dict):
                raise ValueError("associative index manifest must be a JSON object")
            snapshot = index.get("snapshot")
            profile = index.get("embedding_profile")
            activation = index.get("activation")
            if not all(
                isinstance(value, dict) for value in (snapshot, profile, activation)
            ):
                raise ValueError("associative index manifest is missing activation metadata")

            with MindCore(args.database) as core:
                core.activate_estate_generation(bootstrap, index)
            with MindCore(args.database) as reopened:
                report = reopened.activation_operator_report(
                    submitted_snapshot_id=snapshot.get("associative_index_snapshot_id"),
                    submitted_snapshot_digest=snapshot.get("snapshot_digest"),
                    submitted_embedding_profile_id=profile.get("embedding_profile_id"),
                    submitted_activation_id=activation.get(
                        "associative_snapshot_activation_id"
                    ),
                    submitted_prior_snapshot_id=activation.get(
                        "prior_associative_index_snapshot_id"
                    ),
                )
            if (
                not report["matches_submission"]
                or not report["active_matches_submission"]
                or not report["current"]
                or not report["activation_receipt"]["binding_valid"]
                or report["sqlite"]["integrity_check"] != "ok"
                or report["sqlite"]["foreign_key_violation_count"]
            ):
                raise MindCoreError("activation did not survive durable verification")
            _write_json(report)
            return 0

        with MindCore(args.database) as core:
            if args.command == "init":
                _write_json(core.status())
                return 0
            if args.command == "status":
                _write_json(core.status())
                return 0
            if args.command == "bootstrap":
                manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
                if not isinstance(manifest, dict):
                    raise ValueError("bootstrap manifest must be a JSON object")
                _write_json(core.bootstrap(manifest))
                return 0
            if args.command == "index":
                manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
                if not isinstance(manifest, dict):
                    raise ValueError("associative index manifest must be a JSON object")
                _write_json(core.reminders.ingest_index(manifest))
                return 0
            if args.command == "issue-session-capability":
                _write_json(
                    core.reminders.issue_session_capability(
                        args.agent_instance_id,
                        args.host_session_id,
                        exposure_scope=args.exposure_scope,
                        expires_at=args.expires_at,
                    )
                )
                return 0
            if args.command == "revoke-session-capability":
                _write_json(
                    core.reminders.revoke_session_capability(
                        args.session_capability
                    )
                )
                return 0
            if args.command == "query":
                request = json.loads(args.request.read_text(encoding="utf-8"))
                if not isinstance(request, dict):
                    raise ValueError("query request must be a JSON object")
                _write_json(QueryService(core).handle(request))
                return 0
            if args.command == "serve":
                return serve(core, sys.stdin.buffer, sys.stdout.buffer)
    except (MindCoreError, OSError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"mind-core: {exc}\n")
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
