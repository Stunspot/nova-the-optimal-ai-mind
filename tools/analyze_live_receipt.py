from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


sys.dont_write_bytecode = True

CANDIDATE_SKILL_PATH = re.compile(
    r"\\plugins\\cache\\collaborative-dynamics-build-week\\"
    r"(?P<plugin>[^\\]+)\\1\.0\.0\\skills\\(?P<skill>[^\\'\"\s]+)",
    re.IGNORECASE,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze a captured Codex live-probe receipt.")
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--expect", action="append", default=[])
    parser.add_argument("--forbid", action="append", default=[])
    parser.add_argument("--forbid-response", action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    receipt = json.loads(args.receipt.read_text(encoding="utf-8-sig"))
    stderr = receipt.get("stderr", "")
    response = receipt.get("stdout", "")
    compact_stderr = stderr.replace("\\\\", "\\").replace("\r", "").replace("\n", "")
    loaded = sorted({match.group("skill") for match in CANDIDATE_SKILL_PATH.finditer(compact_stderr)})
    missing = sorted(set(args.expect) - set(loaded))
    unexpected = sorted(set(args.forbid) & set(loaded))
    response_hits = sorted(token for token in args.forbid_response if token.casefold() in response.casefold())

    model_match = re.search(r"^model:\s*(.+)$", stderr, re.MULTILINE)
    session_match = re.search(r"^session id:\s*([0-9a-f-]+)$", stderr, re.MULTILINE)
    report = {
        "format": "nova-mind-live-receipt-analysis/v1",
        "receipt": args.receipt.as_posix(),
        "command_status": receipt.get("status"),
        "exit_code": receipt.get("exit_code"),
        "model": model_match.group(1).strip() if model_match else None,
        "session_id_sha256": (
            hashlib.sha256(session_match.group(1).encode("utf-8")).hexdigest()
            if session_match
            else None
        ),
        "loaded_candidate_skills": loaded,
        "expected_skills": sorted(args.expect),
        "missing_expected_skills": missing,
        "forbidden_skills": sorted(args.forbid),
        "unexpected_loaded_skills": unexpected,
        "forbidden_response_hits": response_hits,
        "response": response.strip(),
        "valid": receipt.get("status") == "passed"
        and receipt.get("exit_code") == 0
        and not missing
        and not unexpected
        and not response_hits,
    }
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
