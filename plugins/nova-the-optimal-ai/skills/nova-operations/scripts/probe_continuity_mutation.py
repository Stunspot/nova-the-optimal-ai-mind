#!/usr/bin/env python3
"""Read-only probe for the canonical Continuity mutation filesystem adapter."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

FORMAT = "nova-continuity-mutation-support/v1"


def emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--runtime", required=True)
    root.add_argument("--workspace", required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    runtime = Path(args.runtime).expanduser().resolve(strict=True)
    workspace = Path(args.workspace).expanduser().resolve(strict=False)
    if not runtime.is_file():
        emit({
            "format": FORMAT,
            "supported": False,
            "probe_completed": False,
            "code": "runtime_missing",
            "source_mutated": False,
        })
        return 2
    try:
        sys.path.insert(0, str(runtime.parent))
        spec = importlib.util.spec_from_file_location("_nova_continuity_workspace_runtime", runtime)
        if spec is None or spec.loader is None:
            raise RuntimeError("could not construct module loader")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            result = module.mutation_filesystem_support(workspace, lexical_root=workspace)
        finally:
            sys.modules.pop(spec.name, None)
        supported = result.get("status") == "qualified"
        emit({
            "format": FORMAT,
            "supported": supported,
            "probe_completed": True,
            "code": None if supported else result.get("reason_code", "filesystem_semantics_unsupported"),
            "adapter": result.get("adapter"),
            "detail": result,
            "source_mutated": False,
        })
        return 0
    except Exception as exc:
        emit({
            "format": FORMAT,
            "supported": False,
            "probe_completed": False,
            "code": "probe_failed",
            "detail": f"{type(exc).__name__}: {exc}",
            "source_mutated": False,
        })
        return 2


if __name__ == "__main__":
    raise SystemExit(main())