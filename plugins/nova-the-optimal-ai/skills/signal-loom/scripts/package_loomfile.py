#!/usr/bin/env python3
"""Validate and package a Loomfile as a one-root ZIP with a checksum manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from validate_loomfile import validate


DENIED_NAMES = {".env", "id_rsa", "id_ed25519", "credentials", "credentials.json"}
DENIED_SUFFIXES = {".key", ".pem", ".pfx", ".p12"}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def package(root: Path, output: Path) -> tuple[Path, int]:
    root = root.expanduser().resolve()
    output = output.expanduser().resolve()
    errors, warnings = validate(root)
    if errors:
        raise ValueError("Loomfile validation failed:\n- " + "\n- ".join(errors))
    files: list[Path] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().lower()):
        if path.is_symlink():
            raise ValueError(f"symbolic links are not packaged: {path.relative_to(root)}")
        if not path.is_file():
            continue
        if path.name.lower() in DENIED_NAMES or path.suffix.lower() in DENIED_SUFFIXES:
            raise ValueError(f"secret-like file denied: {path.relative_to(root)}")
        files.append(path)

    manifest_path = root / "review" / "release-manifest.json"
    manifest = {
        "status": "packaged",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "warnings": warnings,
        "files": [
            {"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)}
            for path in files
            if path != manifest_path
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    files = [path for path in files if path != manifest_path] + [manifest_path]

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError(f"output already exists: {output}")
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, f"{root.name}/{path.relative_to(root).as_posix()}")
    return output, len(files)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("loomfile", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        output, count = package(args.loomfile, args.output)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Packaged {count} files: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
