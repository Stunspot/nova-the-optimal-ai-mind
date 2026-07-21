from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def inventory(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): digest(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare a plugin source tree with its installed Codex cache.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--marketplace", required=True)
    parser.add_argument("--plugin", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    source = (ROOT / args.source).resolve() if not args.source.is_absolute() else args.source.resolve()
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).resolve()
    installed = codex_home / "plugins" / "cache" / args.marketplace / args.plugin / args.version
    if not source.is_dir():
        parser.error(f"source tree is missing: {source}")
    if not installed.is_dir():
        parser.error(f"installed cache is missing for {args.plugin}@{args.marketplace} {args.version}")

    source_files = inventory(source)
    installed_files = inventory(installed)
    missing = sorted(set(source_files) - set(installed_files))
    extra = sorted(set(installed_files) - set(source_files))
    changed = sorted(
        path for path in set(source_files) & set(installed_files) if source_files[path] != installed_files[path]
    )
    report = {
        "format": "codex-installed-plugin-comparison/v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "plugin": args.plugin,
        "marketplace": args.marketplace,
        "version": args.version,
        "source_label": args.source.as_posix(),
        "installed_label": f"$CODEX_HOME/plugins/cache/{args.marketplace}/{args.plugin}/{args.version}",
        "source_files": len(source_files),
        "installed_files": len(installed_files),
        "missing": missing,
        "extra": extra,
        "changed": changed,
        "valid": not (missing or extra or changed),
        "boundary": "Byte equality proves installed payload fidelity only; registration, discovery, invocation, and model behavior require separate evidence.",
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
