"""Shared non-following path and tree-walk safeguards for Officefile scripts."""

from __future__ import annotations

import os
import stat
from pathlib import Path, PurePosixPath, PureWindowsPath


WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{number}" for number in range(1, 10)), *(f"LPT{number}" for number in range(1, 10))}
WINDOWS_FORBIDDEN_COMPONENT_CHARS = set('<>:"|?*')
REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def safe_relative(value: object) -> bool:
    """Accept only safe portable members, not paths, ADS streams, or device names."""
    if not isinstance(value, str) or not value or "\x00" in value:
        return False
    windows = PureWindowsPath(value)
    posix = PurePosixPath(value.replace("\\", "/"))
    if windows.is_absolute() or windows.drive or posix.is_absolute():
        return False
    for component in posix.parts:
        if component in {"", ".", ".."}:
            return False
        if any(ord(character) < 32 or character in WINDOWS_FORBIDDEN_COMPONENT_CHARS for character in component):
            return False
        if component[-1:] in {".", " "}:
            return False
        stem = component.split(".", 1)[0].upper()
        if stem in WINDOWS_RESERVED:
            return False
    return True


def is_reparse_or_symlink(path: Path) -> bool:
    try:
        details = path.stat(follow_symlinks=False)
    except OSError:
        return True
    return path.is_symlink() or bool(getattr(details, "st_file_attributes", 0) & REPARSE_POINT)


def resolve_officefile_root(root_value: str | Path) -> tuple[Path | None, list[str]]:
    supplied = Path(root_value).absolute()
    if not supplied.is_dir():
        return None, ["Officefile directory does not exist"]
    if is_reparse_or_symlink(supplied):
        return None, ["Officefile root must not be a symlink or Windows reparse point"]
    return supplied.resolve(), []


def member_path(root: Path, relative: object) -> Path | None:
    """Resolve an existing member only when it stays in root and is not a reparse point."""
    if not safe_relative(relative):
        return None
    candidate = root.joinpath(*PurePosixPath(str(relative).replace("\\", "/")).parts)
    if candidate.exists() and is_reparse_or_symlink(candidate):
        return None
    try:
        resolved = candidate.resolve()
        resolved.relative_to(root)
    except (OSError, ValueError):
        return None
    return resolved


def walk_officefile_files(root_value: str | Path) -> tuple[Path | None, list[Path], list[str]]:
    """Return regular files through one explicit non-following walk.

    Symlinks and Windows reparse points are reported and never traversed. Every
    returned resolved member is checked again to remain within the resolved root.
    """
    root, errors = resolve_officefile_root(root_value)
    if root is None:
        return None, [], errors
    files: list[Path] = []
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except OSError as exc:
            errors.append(f"cannot scan {directory.relative_to(root).as_posix() or '.'}: {exc}")
            continue
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            try:
                entry_stat = entry.stat(follow_symlinks=False)
            except OSError as exc:
                errors.append(f"cannot stat {relative}: {exc}")
                continue
            if entry.is_symlink() or bool(getattr(entry_stat, "st_file_attributes", 0) & REPARSE_POINT):
                errors.append(f"reparse or symlink member rejected: {relative}")
                continue
            if entry.is_dir(follow_symlinks=False):
                pending.append(path)
                continue
            if not entry.is_file(follow_symlinks=False):
                errors.append(f"non-regular member rejected: {relative}")
                continue
            try:
                resolved = path.resolve()
                resolved.relative_to(root)
            except (OSError, ValueError):
                errors.append(f"member escapes Officefile root: {relative}")
                continue
            files.append(resolved)
    return root, files, errors
