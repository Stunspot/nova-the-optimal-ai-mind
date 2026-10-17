#!/usr/bin/env python3
"""Validate TestForge behavioral evaluation case structure."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common.filesystem import load_data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("eval_dir", type=Path); args = parser.parse_args()
    errors = []; cases = 0; ids = set(); dimensions = set()
    for path in sorted(args.eval_dir.glob("*-cases.yaml")):
        try: data = load_data(path)
        except Exception as exc: errors.append(f"{path.name}: {exc}"); continue
        for case in data.get("cases", []) if isinstance(data, dict) else []:
            cases += 1; case_id = case.get("id")
            if not case_id: errors.append(f"{path.name}: case missing id")
            elif case_id in ids: errors.append(f"duplicate case id: {case_id}")
            ids.add(case_id); dimensions.update(case.get("dimensions", []))
            for field in ("input", "expected_behaviors", "failure_signals"):
                if not case.get(field): errors.append(f"{case_id or path.name}: missing {field}")
    report = {"valid": not errors, "case_count": cases, "dimensions": sorted(dimensions), "errors": errors}
    print(json.dumps(report, indent=2)); return 0 if report["valid"] else 1


if __name__ == "__main__": raise SystemExit(main())
