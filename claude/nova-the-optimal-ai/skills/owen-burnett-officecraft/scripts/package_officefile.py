#!/usr/bin/env python3
"""Create a snapshot-bound, safe, non-overwriting ZIP from a valid Officefile."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO

from officefile_safety import safe_relative, walk_officefile_files
from validate_officefile import validate_officefile


STRONG_ARTIFACT_STATUSES = {"produced", "inspected", "reviewed", "approved"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def hash_stream(handle: BinaryIO) -> str:
    digest = hashlib.sha256()
    while chunk := handle.read(1024 * 1024):
        digest.update(chunk)
    return digest.hexdigest()


def snapshot_officefile(root_value: str | Path) -> tuple[Path, dict[str, dict[str, Any]]]:
    root, files, errors = walk_officefile_files(root_value)
    if root is None or errors:
        raise ValueError("Officefile tree safety preflight failed: " + "; ".join(errors))
    snapshot: dict[str, dict[str, Any]] = {}
    for path in sorted(files):
        relative = path.relative_to(root).as_posix()
        if not safe_relative(relative):
            raise ValueError(f"Unsafe package member: {relative}")
        try:
            path.resolve().relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Package member escapes Officefile root: {relative}") from exc
        with path.open("rb") as handle:
            digest = hash_stream(handle)
        snapshot[relative] = {"path": path, "size": path.stat().st_size, "sha256": digest}
    return root, snapshot


def snapshot_signature(snapshot: dict[str, dict[str, Any]]) -> dict[str, tuple[int, str]]:
    return {name: (details["size"], details["sha256"]) for name, details in snapshot.items()}


def snapshot_digest(snapshot: dict[str, dict[str, Any]]) -> str:
    payload = json.dumps(snapshot_signature(snapshot), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_zip_snapshot(path: Path, expected: dict[str, dict[str, Any]]) -> None:
    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos if not info.is_dir()]
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError("ZIP member list does not match validated Officefile snapshot")
        for name in names:
            info = archive.getinfo(name)
            if info.file_size != expected[name]["size"]:
                raise ValueError(f"ZIP member size changed after validation: {name}")
            with archive.open(info, "r") as handle:
                digest = hash_stream(handle)
            if digest != expected[name]["sha256"]:
                raise ValueError(f"ZIP member bytes changed after validation: {name}")


def package_officefile(root_value: str | Path, output_value: str | Path) -> dict[str, object]:
    root, first_snapshot = snapshot_officefile(root_value)
    output = Path(output_value).resolve()
    if output.exists():
        raise ValueError(f"Refusing to overwrite output: {output}")
    try:
        output.relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError("Output ZIP must be outside the Officefile directory")
    if not output.parent.is_dir():
        raise ValueError(f"Output parent directory does not exist: {output.parent}")

    validation = validate_officefile(root)
    if not validation["valid"]:
        raise ValueError("Officefile validation failed; package was not created")
    _, second_snapshot = snapshot_officefile(root)
    if snapshot_signature(first_snapshot) != snapshot_signature(second_snapshot):
        raise ValueError("Officefile changed during validation; package was not created")

    register_path = second_snapshot["state/artifact-register.json"]["path"]
    register = json.loads(register_path.read_text(encoding="utf-8-sig"))
    member_names = set(second_snapshot)
    for artifact in register.get("artifacts", []):
        if isinstance(artifact, dict) and artifact.get("status") in STRONG_ARTIFACT_STATUSES:
            required = artifact.get("path")
            if not isinstance(required, str) or required.replace("\\", "/") not in member_names:
                raise ValueError("Produced-or-stronger registered artifact is absent from ZIP preflight")

    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for relative, details in second_snapshot.items():
                archive.write(details["path"], relative)
        verify_zip_snapshot(temporary, second_snapshot)
        _, final_snapshot = snapshot_officefile(root)
        if snapshot_signature(second_snapshot) != snapshot_signature(final_snapshot):
            raise ValueError("Officefile changed during ZIP creation; package was not published")
        try:
            os.link(temporary, output)
        except FileExistsError as exc:
            raise ValueError(f"Refusing to overwrite output: {output}") from exc
        except OSError as exc:
            raise ValueError(f"Could not atomically publish ZIP without overwrite risk: {exc}") from exc
    finally:
        if temporary.exists():
            temporary.unlink()
    return {
        "format": "officecraft-package/v1",
        "officefile": str(root),
        "output": str(output),
        "created_at": utc_now(),
        "snapshot_sha256": snapshot_digest(second_snapshot),
        "included_files": sorted(second_snapshot),
        "validation": validation,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("officefile")
    parser.add_argument("output")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(package_officefile(args.officefile, args.output), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print(json.dumps({"format": "officecraft-package/v1", "created": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
