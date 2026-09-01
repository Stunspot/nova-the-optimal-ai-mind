from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import struct
import subprocess
import zipfile
from pathlib import Path, PureWindowsPath
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


ZIP_UTF8_FLAG = 0x0800
ZIP_LOCAL_SIGNATURE = b"PK\x03\x04"
ZIP_CENTRAL_SIGNATURE = b"PK\x01\x02"
ZIP_EOCD_SIGNATURE = b"PK\x05\x06"


def zip_filename_findings(path: Path, expected_names: Iterable[str] | None = None) -> list[str]:
    findings: list[str] = []
    raw = path.read_bytes()
    search_start = max(0, len(raw) - (22 + 0xFFFF))
    eocd = raw.rfind(ZIP_EOCD_SIGNATURE, search_start)
    if eocd < 0 or eocd + 22 > len(raw):
        return ["ZIP end-of-central-directory record is missing or truncated"]

    (
        disk_number,
        central_disk,
        entries_on_disk,
        entry_count,
        central_size,
        central_offset,
        comment_size,
    ) = struct.unpack_from("<HHHHIIH", raw, eocd + 4)
    if disk_number or central_disk or entries_on_disk != entry_count:
        findings.append("multi-disk ZIPs are unsupported")
    if entry_count == 0xFFFF or central_size == 0xFFFFFFFF or central_offset == 0xFFFFFFFF:
        findings.append("ZIP64 filename validation is unsupported")
        return findings
    if eocd + 22 + comment_size != len(raw):
        findings.append("ZIP has trailing bytes or a malformed archive comment")
    if central_offset + central_size != eocd:
        findings.append("ZIP central-directory bounds are inconsistent")

    names: list[str] = []
    cursor = central_offset
    central_end = central_offset + central_size
    for index in range(entry_count):
        if cursor + 46 > len(raw) or raw[cursor:cursor + 4] != ZIP_CENTRAL_SIGNATURE:
            findings.append(f"central header {index} is missing or truncated")
            break
        flags = struct.unpack_from("<H", raw, cursor + 8)[0]
        name_size, extra_size, member_comment_size = struct.unpack_from("<HHH", raw, cursor + 28)
        local_offset = struct.unpack_from("<I", raw, cursor + 42)[0]
        name_start = cursor + 46
        name_end = name_start + name_size
        record_end = name_end + extra_size + member_comment_size
        if record_end > len(raw) or record_end > central_end:
            findings.append(f"central header {index} exceeds the declared directory")
            break
        raw_name = raw[name_start:name_end]
        try:
            name = raw_name.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            findings.append(f"central filename {index} is not valid UTF-8: byte {exc.start}")
            name = None
        if name is not None:
            names.append(name)
            if any(byte >= 0x80 for byte in raw_name) and not flags & ZIP_UTF8_FLAG:
                findings.append(f"non-ASCII central filename lacks the UTF-8 flag: {name}")
            if (
                not name
                or "\\" in name
                or name.startswith("/")
                or bool(PureWindowsPath(name).drive)
                or any(part in {"", ".", ".."} for part in name.split("/"))
            ):
                findings.append(f"unsafe ZIP member name: {name!r}")

        if local_offset + 30 > len(raw) or raw[local_offset:local_offset + 4] != ZIP_LOCAL_SIGNATURE:
            findings.append(f"local header {index} is missing or truncated")
        else:
            local_flags = struct.unpack_from("<H", raw, local_offset + 6)[0]
            local_name_size, local_extra_size = struct.unpack_from("<HH", raw, local_offset + 26)
            local_name_start = local_offset + 30
            local_name_end = local_name_start + local_name_size
            if local_name_end + local_extra_size > len(raw):
                findings.append(f"local header {index} exceeds the archive")
            else:
                local_name = raw[local_name_start:local_name_end]
                if local_name != raw_name:
                    findings.append(f"local and central filename bytes differ at member {index}")
                if (local_flags ^ flags) & ZIP_UTF8_FLAG:
                    findings.append(f"local and central UTF-8 flags differ at member {index}")
                try:
                    local_name.decode("utf-8", errors="strict")
                except UnicodeDecodeError as exc:
                    findings.append(f"local filename {index} is not valid UTF-8: byte {exc.start}")
                if any(byte >= 0x80 for byte in local_name) and not local_flags & ZIP_UTF8_FLAG:
                    findings.append(f"non-ASCII local filename lacks the UTF-8 flag at member {index}")
        cursor = record_end

    if cursor != central_end:
        findings.append("ZIP central-directory size does not match parsed headers")
    if len(names) != len(set(names)):
        findings.append("ZIP contains duplicate decoded member names")

    if expected_names is not None:
        expected = list(expected_names)
        if names != expected:
            missing = sorted(set(expected) - set(names))
            unexpected = sorted(set(names) - set(expected))
            findings.append(
                f"ZIP member inventory or order differs: missing={missing}, unexpected={unexpected}"
            )

    if not findings:
        try:
            with zipfile.ZipFile(path) as archive:
                if archive.namelist() != names:
                    findings.append("ZIP library decoding differs from raw UTF-8 member names")
                damaged = archive.testzip()
                if damaged is not None:
                    findings.append(f"ZIP member fails decompression or CRC: {damaged}")
        except (OSError, RuntimeError, UnicodeError, zipfile.BadZipFile) as exc:
            findings.append(f"ZIP cannot be read portably: {exc}")
    return findings


def deterministic_zip(source: Path, destination: Path, *, prefix: str) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    expected_names: list[str] = []
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
            name.encode("utf-8", errors="strict")
            expected_names.append(name)
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    findings = zip_filename_findings(destination, expected_names)
    if findings:
        destination.unlink(missing_ok=True)
        raise RuntimeError("Portable ZIP filename validation failed: " + "; ".join(findings))
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
