#!/usr/bin/env python3
"""Validate and package a Loomfile as a one-root ZIP with a checksum manifest."""

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

try:
    from .validate_loomfile import validate
except ImportError:  # Direct script execution.
    from validate_loomfile import validate


DENIED_NAMES = {".env", "id_rsa", "id_ed25519", "credentials", "credentials.json"}
DENIED_SUFFIXES = {".key", ".pem", ".pfx", ".p12"}
CHUNK_SIZE = 1024 * 1024


def _temporary_path(directory: Path, prefix: str, suffix: str) -> Path:
    descriptor, name = tempfile.mkstemp(dir=directory, prefix=prefix, suffix=suffix)
    os.close(descriptor)
    return Path(name)


def _remove_if_present(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _within(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False




def _write_file_entry(archive: zipfile.ZipFile, path: Path, arcname: str) -> dict[str, object]:
    value = hashlib.sha256()
    byte_count = 0
    with path.open("rb") as source, archive.open(arcname, "w", force_zip64=True) as destination:
        for block in iter(lambda: source.read(CHUNK_SIZE), b""):
            destination.write(block)
            value.update(block)
            byte_count += len(block)
    return {"path": arcname.split("/", 1)[1], "bytes": byte_count, "sha256": value.hexdigest()}


def package(root: Path, output: Path) -> tuple[Path, int]:
    root = root.expanduser().resolve()
    output = output.expanduser().resolve()
    if _within(root, output):
        raise ValueError(f"output must be outside the Loomfile: {output}")
    if output.exists() or output.is_symlink():
        raise ValueError(f"output already exists: {output}")

    errors, warnings = validate(root)
    if errors:
        raise ValueError("Loomfile validation failed:\n- " + "\n- ".join(errors))

    manifest_path = root / "review" / "release-manifest.json"
    directories: list[Path] = []
    files: list[Path] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().lower()):
        if path.is_symlink():
            raise ValueError(f"symbolic links are not packaged: {path.relative_to(root)}")
        if path.is_dir():
            directories.append(path)
            continue
        if not path.is_file():
            continue
        if path.name.lower() in DENIED_NAMES or path.suffix.lower() in DENIED_SUFFIXES:
            raise ValueError(f"secret-like file denied: {path.relative_to(root)}")
        if path != manifest_path:
            files.append(path)

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_archive: Path | None = None

    try:
        temporary_archive = _temporary_path(output.parent, f".{output.name}.", ".tmp")
        manifest_entries: list[dict[str, object]] = []
        with zipfile.ZipFile(
            temporary_archive,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for path in directories:
                relative = path.relative_to(root).as_posix()
                archive.writestr(f"{root.name}/{relative}/", b"")
            for path in files:
                relative = path.relative_to(root).as_posix()
                manifest_entries.append(
                    _write_file_entry(archive, path, f"{root.name}/{relative}")
                )
            manifest = {
                "status": "packaged",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "warnings": warnings,
                "files": manifest_entries,
            }
            manifest_bytes = (
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
            ).encode("utf-8")
            archive.writestr(f"{root.name}/review/release-manifest.json", manifest_bytes)

        with tempfile.TemporaryDirectory(
            dir=output.parent, prefix=f".{output.name}.verify."
        ) as verification_directory:
            with zipfile.ZipFile(temporary_archive, "r") as archive:
                archive.extractall(verification_directory)
            extracted_root = Path(verification_directory) / root.name
            packaged_errors, _ = validate(extracted_root)
            if packaged_errors:
                raise ValueError(
                    "Packaged Loomfile validation failed:\n- "
                    + "\n- ".join(packaged_errors)
                )

        # The completed, revalidated archive is the only committed artifact. A hard
        # link creates the final name without overwriting a concurrent output. Once
        # that call begins, never delete the destination automatically: an interrupt
        # may make link completion ambiguous, and another process can replace the
        # path before cleanup. The caller must inspect any surviving destination.
        os.link(temporary_archive, output)
        _remove_if_present(temporary_archive)
        temporary_archive = None
        return output, len(files) + 1
    finally:
        if temporary_archive is not None:
            _remove_if_present(temporary_archive)


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
