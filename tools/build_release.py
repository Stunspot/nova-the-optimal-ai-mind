#!/usr/bin/env python3
"""Build deterministic archives for the two contest plugins."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"
RELEASE = ROOT / "release"
VERSION = "1.0.0"
TARGETS = ("augment-of-mind", "nova-the-optimal-ai")
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
EXCLUDED_DIRECTORIES = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".tox",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "htmlcov",
    "release",
    "verification",
}
EXCLUDED_FILENAMES = {".coverage", ".DS_Store", "Thumbs.db", "desktop.ini"}
EXCLUDED_SUFFIXES = {".bak", ".log", ".pyc", ".pyo", ".tmp"}


@dataclass(frozen=True)
class Member:
    archive_path: str
    data: bytes
    sha256: str


@dataclass(frozen=True)
class PluginSnapshot:
    name: str
    source: Path
    members: tuple[Member, ...]
    excluded: tuple[str, ...]
    source_tree_sha256: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_relative(path: Path, root: Path) -> str:
    relative = path.relative_to(root).as_posix()
    candidate = PurePosixPath(relative)
    if candidate.is_absolute() or not candidate.parts or any(part in {"", ".", ".."} for part in candidate.parts):
        raise ValueError(f"Unsafe package path: {relative}")
    return relative


def should_exclude_file(path: Path) -> bool:
    return path.name in EXCLUDED_FILENAMES or path.suffix.casefold() in EXCLUDED_SUFFIXES


def stable_read(path: Path) -> bytes:
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    before_signature = (before.st_size, before.st_mtime_ns)
    after_signature = (after.st_size, after.st_mtime_ns)
    if before_signature != after_signature or len(data) != after.st_size:
        raise RuntimeError(f"Source changed while being read: {path}")
    return data


def tree_digest(members: list[Member]) -> str:
    digest = hashlib.sha256()
    for member in members:
        encoded_path = member.archive_path.encode("utf-8")
        digest.update(len(encoded_path).to_bytes(8, "big"))
        digest.update(encoded_path)
        digest.update(len(member.data).to_bytes(8, "big"))
        digest.update(member.data)
    return digest.hexdigest()


def snapshot_plugin(name: str) -> PluginSnapshot:
    source = PLUGINS / name
    manifest_path = source / ".codex-plugin" / "plugin.json"
    if not source.is_dir() or not manifest_path.is_file():
        raise FileNotFoundError(f"Missing plugin source or manifest: {source}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("name") != name:
        raise ValueError(f"Plugin name mismatch for {name}: {manifest.get('name')!r}")
    if manifest.get("version") != VERSION:
        raise ValueError(f"Plugin version mismatch for {name}: {manifest.get('version')!r}")

    members: list[Member] = []
    excluded: list[str] = []
    for current, directories, filenames in os.walk(source, followlinks=False):
        current_path = Path(current)
        retained_directories: list[str] = []
        for directory in sorted(directories):
            candidate = current_path / directory
            relative = normalized_relative(candidate, source)
            if candidate.is_symlink():
                raise ValueError(f"Symlink directory is not releasable: {name}/{relative}")
            if directory in EXCLUDED_DIRECTORIES:
                excluded.append(f"{relative}/")
            else:
                retained_directories.append(directory)
        directories[:] = retained_directories

        for filename in sorted(filenames):
            path = current_path / filename
            relative = normalized_relative(path, source)
            if path.is_symlink():
                raise ValueError(f"Symlink file is not releasable: {name}/{relative}")
            if should_exclude_file(path):
                excluded.append(relative)
                continue
            if not path.is_file():
                raise ValueError(f"Non-regular package member: {name}/{relative}")
            data = stable_read(path)
            archive_path = (PurePosixPath(name) / PurePosixPath(relative)).as_posix()
            members.append(
                Member(
                    archive_path=archive_path,
                    data=data,
                    sha256=sha256_bytes(data),
                )
            )

    members.sort(key=lambda member: member.archive_path)
    if not members:
        raise ValueError(f"Plugin contains no releasable files: {name}")
    return PluginSnapshot(
        name=name,
        source=source,
        members=tuple(members),
        excluded=tuple(sorted(excluded)),
        source_tree_sha256=tree_digest(members),
    )


def write_archive(snapshot: PluginSnapshot, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
        delete=False,
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(
            temporary_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            strict_timestamps=True,
        ) as archive:
            for member in snapshot.members:
                info = zipfile.ZipInfo(member.archive_path, date_time=FIXED_TIMESTAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                info.extra = b""
                info.comment = b""
                archive.writestr(
                    info,
                    member.data,
                    compress_type=zipfile.ZIP_DEFLATED,
                    compresslevel=9,
                )
        verify_archive(temporary_path, snapshot)
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def verify_archive(path: Path, snapshot: PluginSnapshot) -> None:
    expected = {member.archive_path: member for member in snapshot.members}
    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if names != sorted(expected):
            raise RuntimeError(f"Archive member order or inventory mismatch: {path}")
        if len(names) != len(set(names)):
            raise RuntimeError(f"Duplicate archive member: {path}")
        if archive.testzip() is not None:
            raise RuntimeError(f"Archive CRC verification failed: {path}")
        for info in infos:
            if info.date_time != FIXED_TIMESTAMP:
                raise RuntimeError(f"Archive timestamp drift: {info.filename}")
            if info.create_system != 3 or (info.external_attr >> 16) != (stat.S_IFREG | 0o644):
                raise RuntimeError(f"Archive permission metadata drift: {info.filename}")
            if archive.read(info) != expected[info.filename].data:
                raise RuntimeError(f"Archive content mismatch: {info.filename}")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    ) as temporary:
        temporary_path = Path(temporary.name)
        temporary.write(data)
    try:
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def build() -> dict[str, object]:
    snapshots = [snapshot_plugin(name) for name in TARGETS]
    archive_records: list[dict[str, object]] = []
    for snapshot in snapshots:
        archive_path = RELEASE / f"{snapshot.name}-{VERSION}.zip"
        write_archive(snapshot, archive_path)
        archive_records.append(
            {
                "plugin": snapshot.name,
                "source": snapshot.source.relative_to(ROOT).as_posix(),
                "source_tree_sha256": snapshot.source_tree_sha256,
                "archive": archive_path.relative_to(ROOT).as_posix(),
                "archive_sha256": sha256_file(archive_path),
                "archive_bytes": archive_path.stat().st_size,
                "member_count": len(snapshot.members),
                "excluded_paths": list(snapshot.excluded),
                "members": [
                    {
                        "path": member.archive_path,
                        "bytes": len(member.data),
                        "sha256": member.sha256,
                    }
                    for member in snapshot.members
                ],
            }
        )

    receipt: dict[str, object] = {
        "format": "collaborative-dynamics-build-week-release/v1",
        "version": VERSION,
        "determinism": {
            "targets": list(TARGETS),
            "member_order": "UTF-8 POSIX path lexicographic",
            "member_timestamp": "1980-01-01T00:00:00",
            "member_mode": "regular file 0644",
            "compression": "ZIP_DEFLATED level 9",
            "archive_root": "one top-level directory matching plugin name",
            "volatile_fields": "none",
        },
        "archives": archive_records,
        "evidence_boundary": (
            "Hashes establish this exact source snapshot, archive topology, and byte content only; "
            "installation, discovery, invocation, and model behavior require separate evidence."
        ),
    }
    receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
    atomic_write(RELEASE / "release-receipt.json", receipt_bytes)

    checksum_lines = [
        f"{record['archive_sha256']}  {Path(str(record['archive'])).name}"
        for record in archive_records
    ]
    atomic_write(RELEASE / "SHA256SUMS", ("\n".join(checksum_lines) + "\n").encode("ascii"))
    return receipt


def main() -> int:
    receipt = build()
    summary = {
        "valid": True,
        "receipt": "release/release-receipt.json",
        "checksums": "release/SHA256SUMS",
        "archives": [
            {
                "archive": record["archive"],
                "sha256": record["archive_sha256"],
                "members": record["member_count"],
                "excluded": record["excluded_paths"],
            }
            for record in receipt["archives"]  # type: ignore[index]
        ],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
