#!/usr/bin/env python3
"""Run one explicitly supplied command without a shell and retain its exact result."""
from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

from common.command_result import CommandResult, now_iso
from common.filesystem import write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--record-cwd", help="portable working-directory label stored in the record")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command and args.command[0] == "--" else args.command
    if not command:
        parser.error("supply a command after --")
    cwd = args.cwd.resolve()
    if not cwd.is_dir():
        parser.error(f"working directory does not exist: {cwd}")
    started_at = now_iso()
    started = time.monotonic()
    def portable(text: str) -> str:
        return text.replace(str(cwd), args.record_cwd or str(cwd)) if args.record_cwd else text
    try:
        proc = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=args.timeout, shell=False, check=False)
        result = CommandResult("1.0", command, args.record_cwd or str(cwd), started_at, now_iso(), round(time.monotonic() - started, 6), proc.returncode, False, portable(proc.stdout), portable(proc.stderr), "passed" if proc.returncode == 0 else "failed")
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        result = CommandResult("1.0", command, args.record_cwd or str(cwd), started_at, now_iso(), round(time.monotonic() - started, 6), None, True, portable(stdout), portable(stderr), "interrupted")
    except OSError as exc:
        result = CommandResult("1.0", command, args.record_cwd or str(cwd), started_at, now_iso(), round(time.monotonic() - started, 6), None, False, "", str(exc), "blocked")
    write_json(args.output, result.to_dict())
    return 0 if result.status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
