#!/usr/bin/env python3
"""Fetch public OpenRouter model metadata without credentials."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


URL = "https://openrouter.ai/api/v1/models"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", type=float, default=20)
    args = parser.parse_args()
    try:
        request = urllib.request.Request(URL, headers={"User-Agent": "Collaborative-Dynamics-Cognition-Economist/0.1"})
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            payload = json.load(response)
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ValueError("unexpected API response shape")
        result = {
            "format": "cd-openrouter-model-snapshot/v1",
            "source": URL,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "model_count": len(payload["data"]),
            "data": payload["data"],
            "boundary": "Public metadata snapshot; account fees, contract terms, actual served provider, and quality evidence are separate."
        }
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"output": str(Path(args.output).resolve()), "model_count": result["model_count"], "checked_at": result["checked_at"]}, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as exc:
        print(f"ERROR: OpenRouter refresh failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
