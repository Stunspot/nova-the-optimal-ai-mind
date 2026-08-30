from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import zipfile
from pathlib import Path
from typing import Iterable

IGNORED_PARTS = {"__pycache__", ".DS_Store", "Thumbs.db"}


def is_runtime_file(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if any(part in IGNORED_PARTS for part in relative.parts):
        return False
    return path.is_file() and path.suffix not in {".pyc", ".pyo"}


def files(root: Path) -> list[Path]:
    return sorted(
        (path for path in root.rglob("*") if is_runtime_file(path, root)),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_digest(root: Path) -> dict[str, object]:
    digest = hashlib.sha256()
    selected = files(root)
    for path in selected:
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
    return {"file_count": len(selected), "tree_sha256": digest.hexdigest()}


def copy_tree(source: Path, destination: Path, *, exclude_top: Iterable[str] = ()) -> None:
    excluded = set(exclude_top)
    destination.mkdir(parents=True, exist_ok=True)
    for path in files(source):
        relative = path.relative_to(source)
        if relative.parts and relative.parts[0] in excluded:
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def write_json(path: Path, value: object) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2))


def ensure_descendant(path: Path, parent: Path) -> Path:
    resolved = path.resolve()
    anchor = parent.resolve()
    try:
        resolved.relative_to(anchor)
    except ValueError as exc:
        raise ValueError(f"Refusing path outside allowed parent: {resolved}") from exc
    if resolved == anchor:
        raise ValueError(f"Refusing broad target equal to parent: {resolved}")
    return resolved


def replace_directory(path: Path, parent: Path) -> Path:
    resolved = ensure_descendant(path, parent)
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)
    return resolved


def deterministic_zip(source: Path, destination: Path, *, prefix: str) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    with zipfile.ZipFile(
        destination,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for path in files(source):
            relative = path.relative_to(source).as_posix()
            name = f"{prefix}/{relative}" if prefix else relative
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return sha256_file(destination)


def git_value(repo: Path, *args: str) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode:
        return None
    return completed.stdout.strip()
