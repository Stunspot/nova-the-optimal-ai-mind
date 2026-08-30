#!/usr/bin/env python3
"""Continuity v2 immutable-generation workspace kernel and selector resolver."""
from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import shutil
import socket
import stat
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

from schema_validation import SchemaCatalog
from eligibility_policy import contains_secret_data

LEGACY_FORMAT = "cd-cognitive-continuity/v1"
FORMAT = "cd-cognitive-continuity/v2"
EXPORT_FORMAT = "cd-cognitive-continuity-export/v2"
IMPLEMENTATION_VERSION = "0.2.4"
SELECTOR = "NOVA_CONTINUITY_HOME"
ROOT_SELECTOR = "NOVA_DATA_ROOT"


def _default_selector_registry() -> Path:
    raw_root = os.environ.get(ROOT_SELECTOR, "").strip()
    candidate = Path(raw_root) if raw_root else None
    if candidate is not None and candidate.is_absolute() and not any(part in {".", ".."} for part in candidate.parts):
        return candidate / "estate" / "path-selectors.json"
    return Path("estate") / "path-selectors.json"


SELECTOR_REGISTRY = _default_selector_registry()
LOCK_FORMAT = "cd-continuity-lock-owner/v1"
TRANSACTION_FORMAT = "cd-continuity-transaction-journal/v1"
RECEIPT_FORMAT = "cd-continuity-receipt/v2"
GENERATION_FORMAT = "cd-continuity-generation/v1"
MEMBERS = ("episodes.jsonl", "state.jsonl", "proposals.jsonl", "receipts.jsonl", "idempotency.jsonl")
LOGICAL = {("episodes", "events.jsonl"): "episodes.jsonl", ("state", "records.jsonl"): "state.jsonl", ("proposals", "proposals.jsonl"): "proposals.jsonl"}
FINAL_JOURNAL_STATES = {"finalized", "aborted"}

@dataclass(frozen=True)
class ResolutionToken:
    mode: str
    selected_root: str
    selected_lexical: str
    provenance: str
    registry_path: str | None = None
    registry_digest: str | None = None
    custody_root: str | None = None
    ambient_root: str | None = None
    grant_id: str | None = None

    def __str__(self) -> str:
        return self.provenance

@dataclass(frozen=True)
class NovaMigrationGrant:
    grant_id: str
    registry_path: str
    registry_digest: str
    custody_root: str
    ambient_root: str
    destination_root: str
    destination_lexical: str
    destination_sha256: str

class ContinuityError(RuntimeError):
    def __init__(self, message: str, code: str = "operation_failed"):
        super().__init__(message)
        self.code = code
    def __str__(self) -> str:
        return f"{self.code}: {super().__str__()}"

class IdempotentReplay(Exception):
    def __init__(self, receipt: dict[str, Any]):
        super().__init__("duplicate_committed")
        self.receipt = receipt

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"

def dump_canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def sha256_file(path: Path) -> str:
    try:
        value, _ = _read_direct_file_bytes(path, boundary=path.parent)
    except OSError as exc:
        raise ContinuityError(
            f"Cannot hash one direct regular file: {path}",
            "workspace_invalid",
        ) from exc
    return sha256_bytes(value)


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    files: list[Path] = []
    try:
        items = list(root.rglob("*"))
    except OSError as exc:
        raise ContinuityError("Tree custody cannot be enumerated", "custody_denied") from exc
    for item in items:
        if _has_reparse_component(item, root):
            raise ContinuityError(
                f"Tree custody contains an indirect entry: {item}",
                "custody_reparse_escape",
            )
        try:
            metadata = os.stat(item, follow_symlinks=False)
        except OSError as exc:
            raise ContinuityError(
                f"Tree custody entry identity is unavailable: {item}",
                "custody_denied",
            ) from exc
        if stat.S_ISREG(metadata.st_mode):
            files.append(item)
    for path in sorted(files, key=lambda candidate: candidate.as_posix()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8") + b"\0" + bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()

# Darwin <sys/fcntl.h> defines F_FULLFSYNC as command 51.
_F_FULLFSYNC = 51


def _darwin_full_fsync(descriptor: int, fcntl_module: Any | None = None) -> bool:
    """Request Darwin's device-cache flush; return False when the filesystem declines it."""
    if fcntl_module is None:
        import fcntl as fcntl_module
    while True:
        try:
            fcntl_module.fcntl(descriptor, _F_FULLFSYNC)
            return True
        except OSError as exc:
            if exc.errno == errno.EINTR:
                continue
            if exc.errno in {errno.EINVAL, errno.ENOTSUP, errno.ENOSYS}:
                return False
            raise


def _flush(handle: Any) -> None:
    handle.flush()
    os.fsync(handle.fileno())
    if sys.platform == "darwin":
        _darwin_full_fsync(handle.fileno())

def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

def _exclusive_rename(source: Path, destination: Path) -> None:
    if sys.platform == "win32":
        movefile_write_through = 0x8
        if not ctypes.windll.kernel32.MoveFileExW(str(source), str(destination), movefile_write_through):
            raise ctypes.WinError(ctypes.windll.kernel32.GetLastError())
        return

    try:
        library = ctypes.CDLL(None, use_errno=True)
        source_bytes = os.fsencode(source)
        destination_bytes = os.fsencode(destination)
        if sys.platform == "darwin":
            operation = library.renamex_np
            operation.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
            arguments = (source_bytes, destination_bytes, 0x00000004)  # RENAME_EXCL
        elif sys.platform.startswith("linux"):
            operation = library.renameat2
            operation.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
            arguments = (-100, source_bytes, -100, destination_bytes, 1)  # AT_FDCWD, RENAME_NOREPLACE
        else:
            raise OSError(errno.ENOTSUP, "Atomic no-clobber rename is unavailable on this platform")
        operation.restype = ctypes.c_int
    except AttributeError as exc:
        raise OSError(errno.ENOTSUP, "Atomic no-clobber rename primitive is unavailable") from exc
    if operation(*arguments) != 0:
        observed_errno = ctypes.get_errno()
        raise OSError(observed_errno, os.strerror(observed_errno), str(destination))


def _move_path_write_through(
    source: str | Path,
    destination: Path,
    *,
    replace_existing: bool,
) -> None:
    source_path = Path(source)
    source_parent = source_path.parent
    destination_parent = destination.parent
    if replace_existing and sys.platform == "win32":
        flags = 0x8 | 0x1
        if not ctypes.windll.kernel32.MoveFileExW(str(source_path), str(destination), flags):
            raise ctypes.WinError(ctypes.windll.kernel32.GetLastError())
        return
    if replace_existing:
        os.replace(source_path, destination)
    else:
        _exclusive_rename(source_path, destination)
    _fsync_directory(destination_parent)
    if source_parent.resolve() != destination_parent.resolve():
        _fsync_directory(source_parent)


def _replace_file_write_through(source: str | Path, destination: Path) -> None:
    _move_path_write_through(source, destination, replace_existing=True)

def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            _flush(handle)
        _replace_file_write_through(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(value)
            _flush(handle)
        _replace_file_write_through(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def _write_new(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    descriptor = os.open(str(path), flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(value)
            _flush(handle)
    finally:
        os.close(descriptor)

def atomic_new_bytes(path: Path, value: bytes) -> tuple[int, int]:
    """Publish a new external file without clobbering or unsafe error cleanup."""
    if not path.parent.is_dir():
        raise ContinuityError(
            "External output requires an existing exact parent directory",
            "protected_target_denied",
        )
    if os.path.lexists(path):
        raise ContinuityError("External output target must remain absent", "protected_target_denied")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    temporary_path = Path(temporary)
    try:
        opened = os.fstat(descriptor)
        temporary_identity = (int(opened.st_dev), int(opened.st_ino))
        if not stat.S_ISREG(opened.st_mode) or int(opened.st_ino) == 0:
            raise OSError(errno.ENOTSUP, "External staging identity is unavailable")
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(value)
            _flush(handle)
    except BaseException as exc:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise ContinuityError(
            f"External output staging failed; retained path: {temporary_path}",
            "recovery_required",
        ) from exc
    if _file_identity(temporary_path) != temporary_identity:
        raise ContinuityError(
            f"External output staging identity changed; retained path: {temporary_path}",
            "recovery_required",
        )
    try:
        _move_path_write_through(temporary_path, path, replace_existing=False)
    except OSError as exc:
        retained = path if _file_identity(path) == temporary_identity else temporary_path
        raise ContinuityError(
            f"External output publication failed without unsafe cleanup; retained path: {retained}",
            "recovery_required",
        ) from exc
    published_identity = _file_identity(path)
    if published_identity != temporary_identity:
        raise ContinuityError(
            f"External output identity changed during publication; retained path: {path}",
            "recovery_required",
        )
    return published_identity


def atomic_new_json(path: Path, value: Any) -> tuple[int, int]:
    encoded = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return atomic_new_bytes(path, encoded)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result

def _loads(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_unique_object)

def _read_json_path(path: Path) -> Any:
    try:
        value, _ = _read_direct_file_bytes(path, boundary=path.parent)
        return _loads(value.decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ContinuityError(f"Cannot read valid direct JSON from {path}: {exc}", "workspace_invalid") from exc


def _read_jsonl_path(path: Path) -> list[dict[str, Any]]:
    if not os.path.lexists(path):
        return []
    rows: list[dict[str, Any]] = []
    try:
        value, _ = _read_direct_file_bytes(path, boundary=path.parent)
        for line_no, line in enumerate(value.decode("utf-8-sig").splitlines(), 1):
            if not line.strip():
                continue
            item = _loads(line)
            if not isinstance(item, dict):
                raise ValueError("row is not an object")
            rows.append(item)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ContinuityError(f"Cannot read valid direct JSONL from {path}: {exc}", "workspace_invalid") from exc
    return rows

def encode_jsonl(rows: Iterable[dict[str, Any]]) -> bytes:
    return "".join(dump_canonical(row) + "\n" for row in rows).encode("utf-8")

def _logical_member(path: Path) -> tuple[Path, str] | None:
    parts = path.parts
    if len(parts) < 3:
        return None
    member = LOGICAL.get((parts[-2], parts[-1]))
    return (path.parent.parent, member) if member else None

def generation_path(root: Path, manifest: dict[str, Any]) -> Path:
    relative_value = manifest.get("active_generation_path")
    if not isinstance(relative_value, str):
        raise ContinuityError("Manifest lacks active generation path", "recovery_required")
    relative = Path(relative_value)
    if (
        relative.is_absolute()
        or any(part in {"", ".", ".."} for part in relative.parts)
        or len(relative.parts) != 2
        or relative.parts[0] != "generations"
    ):
        raise ContinuityError("Active generation path is not canonical", "custody_denied")
    candidate = root / relative
    if _has_reparse_component(candidate, root):
        raise ContinuityError("Active generation crosses an indirect custody edge", "custody_reparse_escape")
    try:
        metadata = os.stat(candidate, follow_symlinks=False)
    except OSError as exc:
        raise ContinuityError("Active generation is unavailable", "recovery_required") from exc
    if not stat.S_ISDIR(metadata.st_mode):
        raise ContinuityError("Active generation is not one direct directory", "custody_denied")
    return candidate


def _verify_generation(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    bundle = generation_path(root, manifest)
    generation_file = bundle / "generation.json"
    try:
        generation_bytes, _ = _read_direct_file_bytes(generation_file, boundary=root)
        metadata = _loads(generation_bytes.decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ContinuityError("Active generation metadata is missing or indirect", "recovery_required") from exc
    if sha256_bytes(generation_bytes) != manifest.get("active_generation_manifest_sha256"):
        raise ContinuityError("Active generation manifest digest mismatch", "recovery_required")
    if metadata.get("format") != GENERATION_FORMAT or metadata.get("workspace_id") != manifest.get("workspace_id") or metadata.get("generation") != manifest.get("generation"):
        raise ContinuityError("Active generation identity mismatch", "recovery_required")
    members = metadata.get("members") or {}
    for name in MEMBERS:
        path = bundle / name
        expected = (members.get(name) or {}).get("sha256")
        try:
            member_bytes, _ = _read_direct_file_bytes(path, boundary=root)
        except OSError as exc:
            raise ContinuityError(
                f"Active generation member is missing or indirect: {name}",
                "recovery_required",
            ) from exc
        if not expected or sha256_bytes(member_bytes) != expected:
            raise ContinuityError(f"Active generation member is missing or corrupt: {name}", "recovery_required")
    return metadata

def open_snapshot_identity(root: Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Return one verified manifest snapshot and the digest of those exact bytes."""
    manifest_path = root / "manifest.json"
    for _ in range(2):
        try:
            first, first_identity = _read_direct_file_bytes(manifest_path, boundary=root)
            manifest = _loads(first.decode("utf-8-sig"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ContinuityError("Workspace manifest is unavailable, indirect, or invalid", "workspace_missing") from exc
        if manifest.get("format") != FORMAT:
            raise ContinuityError("Immutable snapshot requires v2", "version_unsupported")
        metadata = _verify_generation(root, manifest)
        try:
            second, second_identity = _read_direct_file_bytes(manifest_path, boundary=root)
        except OSError as exc:
            raise ContinuityError("Workspace manifest became unavailable or indirect", "snapshot_changed") from exc
        if first == second and first_identity == second_identity:
            return manifest, metadata, sha256_bytes(first)
    raise ContinuityError("Workspace changed during both read attempts", "snapshot_changed")


def open_snapshot(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest, metadata, _ = open_snapshot_identity(root)
    return manifest, metadata

def read_json(path: Path) -> Any:
    return _read_json_path(path)

def read_jsonl(path: Path) -> list[dict[str, Any]]:
    logical = _logical_member(path)
    if not logical or path.exists():
        return _read_jsonl_path(path)
    root, member = logical
    manifest = _read_json_path(root / "manifest.json")
    if manifest.get("format") == FORMAT:
        _verify_generation(root, manifest)
        return _read_jsonl_path(generation_path(root, manifest) / member)
    return []

def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    atomic_bytes(path, encode_jsonl(rows))

def _inside(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ContinuityError("Path escapes workspace custody", "custody_denied") from exc
def _absolute_lexical(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ContinuityError(f"{label} is missing", "selector_registry_invalid")
    raw = value.strip()
    candidate = Path(raw)
    if not candidate.is_absolute() or any(part in {".", ".."} for part in candidate.parts) or raw.startswith("\\\\?\\") or raw.startswith("\\\\.\\"):
        raise ContinuityError(f"{label} is not an absolute supported local path", "selector_registry_invalid")
    return Path(os.path.abspath(raw))


def _absolute_local(value: Any, label: str) -> Path:
    return _absolute_lexical(value, label).resolve()

def _has_reparse_component(path: Path, boundary: Path | None = None) -> bool:
    current = path
    stop = boundary.resolve() if boundary is not None else Path(path.anchor)
    candidates: list[Path] = []
    while True:
        candidates.append(current)
        if current == stop or current.parent == current:
            break
        current = current.parent
    for item in reversed(candidates):
        # A broken symlink does not exist(), but it is still an indirect edge.
        if item.is_symlink():
            return True
        if not item.exists():
            continue
        try:
            info = os.lstat(item)
        except OSError:
            return True
        attributes = getattr(info, "st_file_attributes", 0)
        if attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            return True
    return False


def _existing_identity(path: Path) -> tuple[Path, tuple[str, ...]]:
    """Return the nearest existing ancestor and exact unresolved suffix."""
    current = Path(os.path.abspath(str(path)))
    suffix: list[str] = []
    while not current.exists() and current.parent != current:
        suffix.append(current.name)
        current = current.parent
    return current, tuple(reversed(suffix))


def _same_path_identity(left: Path, right: Path) -> bool:
    """Compare existing identities, retaining exact names for absent descendants."""
    left_anchor, left_suffix = _existing_identity(left)
    right_anchor, right_suffix = _existing_identity(right)
    if left_suffix != right_suffix:
        return False
    try:
        return os.path.samefile(left_anchor, right_anchor)
    except (FileNotFoundError, OSError):
        return os.path.normcase(str(left_anchor.resolve())) == os.path.normcase(str(right_anchor.resolve()))


def _verify_lexical_identity(root: Path, lexical_root: Path) -> None:
    lexical = Path(os.path.abspath(str(lexical_root)))
    if _has_reparse_component(lexical):
        raise ContinuityError("Workspace path crosses an unexamined symlink or reparse edge", "custody_reparse_escape")
    if not _same_path_identity(root, lexical):
        raise ContinuityError("Workspace lexical and resolved identities disagree", "selector_registry_changed")

def _registry(path: Path | None = None) -> tuple[Path, dict[str, Any], str]:
    registry_lexical = Path(os.path.abspath(str(path or SELECTOR_REGISTRY)))
    if _has_reparse_component(registry_lexical):
        raise ContinuityError("Trusted Nova selector registry is unavailable or indirect", "selector_registry_invalid")
    try:
        first, first_identity = _read_direct_file_bytes(registry_lexical)
        value = _loads(first.decode("utf-8-sig"))
        second, second_identity = _read_direct_file_bytes(registry_lexical)
        registry_path = registry_lexical.resolve(strict=True)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ContinuityError(f"Trusted Nova selector registry is invalid: {exc}", "selector_registry_invalid") from exc
    if first != second or first_identity != second_identity:
        raise ContinuityError("Trusted Nova selector registry changed during resolution", "selector_registry_changed")
    if not isinstance(value, dict) or value.get("format") != "nova-path-selectors/v1" or not isinstance(value.get("active_values"), dict):
        raise ContinuityError("Trusted Nova selector registry has an unsupported shape", "selector_registry_invalid")
    return registry_path, value, sha256_bytes(first)

def _within(root: Path, target: Path, code: str = "caller_root_denied") -> None:
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ContinuityError("Requested workspace is outside trusted custody", code) from exc

def _nova_registry_values(registry_path: Path | None = None) -> tuple[Path, Path, Path, dict[str, Any], str]:
    path, registry, digest = _registry(registry_path)
    active = registry["active_values"]
    root_lexical = _absolute_lexical(active.get(ROOT_SELECTOR), ROOT_SELECTOR)
    continuity_lexical = _absolute_lexical(active.get(SELECTOR), SELECTOR)
    root = root_lexical.resolve()
    continuity = continuity_lexical.resolve()
    _within(root, continuity, "selector_registry_invalid")
    if not root.exists() or _has_reparse_component(root_lexical) or _has_reparse_component(continuity_lexical, root_lexical):
        raise ContinuityError("Trusted Nova custody path crosses an unrecorded reparse edge", "custody_reparse_escape")
    return path, root, continuity, registry, digest

def select_workspace(
    path_value: str | None,
    *,
    mode: str = "generic",
    registry_path: Path | None = None,
    grant_id: str | None = None,
    operation_class: str = "read",
) -> tuple[Path, ResolutionToken]:
    normalized_mode = mode
    if mode == "generic":
        normalized_mode = "generic_explicit" if path_value else "nova_ambient"
    elif mode == "nova":
        normalized_mode = "nova_explicit_authorized" if path_value else "nova_ambient"
    if normalized_mode == "generic_explicit":
        if not path_value:
            raise ContinuityError("Generic mode requires an explicit workspace", "selector_missing")
        selected_lexical = _absolute_lexical(path_value, "workspace")
        selected = _absolute_local(path_value, "workspace")
        if ".codex" in {part.casefold() for part in selected.parts}:
            raise ContinuityError("Host .codex custody is a protected target", "protected_target_denied")
        if _has_reparse_component(selected_lexical):
            raise ContinuityError("Explicit workspace crosses an unexamined reparse edge", "custody_reparse_escape")
        return selected, ResolutionToken(mode="generic_explicit", selected_root=str(selected), selected_lexical=str(selected_lexical), provenance="generic_explicit")
    if normalized_mode not in {"nova_ambient", "nova_explicit_authorized"}:
        raise ContinuityError(f"Unsupported resolution mode: {normalized_mode}", "selector_registry_invalid")
    registry, custody_root, ambient, registry_value, digest = _nova_registry_values(registry_path)
    if normalized_mode == "nova_ambient":
        observed_root = os.environ.get(ROOT_SELECTOR)
        observed_continuity = os.environ.get(SELECTOR)
        if not observed_root:
            raise ContinuityError(f"{ROOT_SELECTOR} is not present for ambient corroboration", "nova_root_mismatch")
        if not observed_continuity:
            raise ContinuityError(f"{SELECTOR} is not present for ambient corroboration", "continuity_selector_mismatch")
        try:
            environment_root = _absolute_local(observed_root, ROOT_SELECTOR)
            environment_continuity = _absolute_local(observed_continuity, SELECTOR)
        except ContinuityError as exc:
            code = "nova_root_mismatch" if not observed_root else "continuity_selector_mismatch"
            raise ContinuityError(str(exc), code) from exc
        if os.path.normcase(str(environment_root)) != os.path.normcase(str(custody_root)):
            raise ContinuityError("Process NOVA_DATA_ROOT disagrees with the trusted registry", "nova_root_mismatch")
        if os.path.normcase(str(environment_continuity)) != os.path.normcase(str(ambient)):
            raise ContinuityError("Process NOVA_CONTINUITY_HOME disagrees with the trusted registry", "continuity_selector_mismatch")
        selected = ambient
        selected_lexical = Path(os.path.abspath(str(registry_value["active_values"][SELECTOR]).strip()))
        provenance = f"nova_ambient:{digest[:16]}"
    else:
        if not path_value:
            raise ContinuityError("Authorized explicit mode requires a workspace path", "selector_missing")
        if not grant_id or not str(grant_id).strip():
            raise ContinuityError("Authorized explicit Nova selection requires a recorded grant ID", "authority_denied")
        selected_lexical = _absolute_lexical(path_value, "workspace")
        selected = _absolute_local(path_value, "workspace")
        _within(custody_root, selected, "caller_root_denied")
        provenance = f"nova_explicit_authorized:{grant_id}:{digest[:16]}"
    _within(custody_root, selected, "caller_root_denied")
    if ".codex" in {part.casefold() for part in selected.parts}:
        raise ContinuityError("Nova Continuity cannot use host .codex custody", "protected_target_denied")
    if _has_reparse_component(selected_lexical, custody_root):
        raise ContinuityError("Selected Nova workspace crosses a reparse edge", "custody_reparse_escape")
    if not selected.exists():
        raise ContinuityError("Selected Nova workspace does not exist", "workspace_missing")
    _, _, _, _, final_digest = _nova_registry_values(registry_path)
    if final_digest != digest:
        raise ContinuityError("Trusted Nova selector registry changed during resolution", "selector_registry_changed")
    return selected, ResolutionToken(
        mode=normalized_mode,
        selected_root=str(selected),
        selected_lexical=str(selected_lexical),
        provenance=provenance,
        registry_path=str(registry),
        registry_digest=digest,
        custody_root=str(custody_root),
        ambient_root=str(ambient),
        grant_id=str(grant_id) if grant_id is not None else None,
    )


def revalidate_resolution(token: ResolutionToken, root: Path) -> None:
    """Revalidate the exact selector decision while the writer lock is held."""
    lexical = Path(token.selected_lexical)
    if _has_reparse_component(lexical):
        raise ContinuityError("Selected workspace crossed a late reparse edge", "custody_reparse_escape")
    if not _same_path_identity(lexical, root):
        raise ContinuityError("Selected workspace path changed after resolution", "selector_registry_changed")
    if not _same_path_identity(root, Path(token.selected_root)):
        raise ContinuityError("Resolved workspace differs from its selection token", "selector_registry_changed")
    _filesystem_adapter(
        root,
        lexical_root=lexical,
        workspace_root=True,
        perform_capability_probe=False,
    )
    if token.mode == "generic_explicit":
        return
    if not token.registry_path or not token.registry_digest or not token.custody_root or not token.ambient_root:
        raise ContinuityError("Nova resolution token is incomplete", "selector_registry_invalid")
    registry_path, custody_root, ambient, _, digest = _nova_registry_values(Path(token.registry_path))
    if digest != token.registry_digest:
        raise ContinuityError("Trusted Nova selector registry changed before mutation", "selector_registry_changed")
    if os.path.normcase(str(registry_path)) != os.path.normcase(str(Path(token.registry_path).resolve())):
        raise ContinuityError("Trusted Nova selector registry identity changed", "selector_registry_changed")
    if os.path.normcase(str(custody_root)) != os.path.normcase(str(Path(token.custody_root).resolve())):
        raise ContinuityError("Trusted Nova custody root changed", "selector_registry_changed")
    if os.path.normcase(str(ambient)) != os.path.normcase(str(Path(token.ambient_root).resolve())):
        raise ContinuityError("Trusted Continuity selector changed", "selector_registry_changed")
    _within(custody_root, root, "caller_root_denied")
    if token.mode == "nova_ambient" and os.path.normcase(str(root.resolve())) != os.path.normcase(str(ambient)):
        raise ContinuityError("Ambient Continuity selector changed", "continuity_selector_mismatch")
    observed_root = os.environ.get(ROOT_SELECTOR)
    observed_continuity = os.environ.get(SELECTOR)
    if not observed_root or os.path.normcase(str(_absolute_local(observed_root, ROOT_SELECTOR))) != os.path.normcase(str(custody_root)):
        raise ContinuityError("Process NOVA_DATA_ROOT no longer corroborates the registry", "nova_root_mismatch")
    if token.mode == "nova_ambient" and (not observed_continuity or os.path.normcase(str(_absolute_local(observed_continuity, SELECTOR))) != os.path.normcase(str(ambient))):
        raise ContinuityError("Process NOVA_CONTINUITY_HOME no longer corroborates the registry", "continuity_selector_mismatch")


def workspace_selector(path_value: str | None, *, mode: str = "generic", grant_id: str | None = None) -> str:
    return str(select_workspace(path_value, mode=mode, grant_id=grant_id)[1])

def open_workspace(
    path_value: str | None,
    *,
    writable: bool = False,
    mode: str = "generic",
    registry_path: Path | None = None,
    grant_id: str | None = None,
) -> tuple[Path, ResolutionToken]:
    root, provenance = select_workspace(path_value, mode=mode, registry_path=registry_path, grant_id=grant_id, operation_class="write" if writable else "read")
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ContinuityError(f"Not an initialized Continuity workspace: {root}", "workspace_missing")
    manifest = _read_json_path(manifest_path)
    observed = manifest.get("format") if isinstance(manifest, dict) else None
    if observed == LEGACY_FORMAT:
        if writable:
            raise ContinuityError("v1 is read-only through the v2 interface; copy-migrate before mutation", "migration_required_for_mutation")
        return root, provenance
    if observed != FORMAT:
        raise ContinuityError(f"Unsupported Continuity workspace format: {observed!r}", "version_unsupported")
    open_snapshot(root)
    return root, provenance

def workspace(
    path_value: str | None,
    *,
    writable: bool = False,
    mode: str = "generic",
    registry_path: Path | None = None,
    grant_id: str | None = None,
) -> Path:
    return open_workspace(
        path_value, writable=writable, mode=mode,
        registry_path=registry_path, grant_id=grant_id,
    )[0]

_WINDOWS_FILE_READ_ONLY_VOLUME = 0x00080000
_DARWIN_MNT_RDONLY = 0x00000001
_DARWIN_MNT_LOCAL = 0x00001000

_LINUX_REMOTE_FILESYSTEMS = frozenset({
    "9p",
    "afs",
    "ceph",
    "cifs",
    "davfs",
    "fuse.gcsfuse",
    "fuse.glusterfs",
    "fuse.rclone",
    "fuse.s3fs",
    "fuse.sshfs",
    "fuse.vmhgfs-fuse",
    "gcsfuse",
    "gfs2",
    "glusterfs",
    "lustre",
    "ocfs2",
    "nfs",
    "nfs4",
    "s3fs",
    "smb3",
    "sshfs",
    "vboxsf",
    "virtiofs",
})
_LINUX_EPHEMERAL_FILESYSTEMS = frozenset({"ramfs", "tmpfs"})


class _DarwinFsid(ctypes.Structure):
    _fields_ = [("value", ctypes.c_int32 * 2)]


class _DarwinStatfs(ctypes.Structure):
    # Darwin's 64-bit statfs layout from <sys/mount.h>.
    _fields_ = [
        ("f_bsize", ctypes.c_uint32),
        ("f_iosize", ctypes.c_int32),
        ("f_blocks", ctypes.c_uint64),
        ("f_bfree", ctypes.c_uint64),
        ("f_bavail", ctypes.c_uint64),
        ("f_files", ctypes.c_uint64),
        ("f_ffree", ctypes.c_uint64),
        ("f_fsid", _DarwinFsid),
        ("f_owner", ctypes.c_uint32),
        ("f_type", ctypes.c_uint32),
        ("f_flags", ctypes.c_uint32),
        ("f_fssubtype", ctypes.c_uint32),
        ("f_fstypename", ctypes.c_char * 16),
        ("f_mntonname", ctypes.c_char * 1024),
        ("f_mntfromname", ctypes.c_char * 1024),
        ("f_flags_ext", ctypes.c_uint32),
        ("f_reserved", ctypes.c_uint32 * 7),
    ]


def _darwin_text(value: Any) -> str:
    return bytes(value).split(b"\0", 1)[0].decode("utf-8", errors="strict")


def _darwin_filesystem_observation(probe: Path) -> dict[str, Any]:
    descriptor = os.open(str(probe), os.O_RDONLY)
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        # The explicit 64-bit syscall matches _DarwinStatfs without header-time symbol rewriting.
        fstatfs64 = libc.fstatfs64
        fstatfs64.argtypes = [ctypes.c_int, ctypes.POINTER(_DarwinStatfs)]
        fstatfs64.restype = ctypes.c_int
        observed = _DarwinStatfs()
        if fstatfs64(descriptor, ctypes.byref(observed)) != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))
    finally:
        os.close(descriptor)
    return {
        "filesystem": _darwin_text(observed.f_fstypename),
        "flags": int(observed.f_flags),
        "fsid": tuple(int(value) for value in observed.f_fsid.value),
        "mount_point": _darwin_text(observed.f_mntonname),
        "mounted_from": _darwin_text(observed.f_mntfromname),
    }


def _nearest_existing(path: Path) -> Path:
    probe = path.resolve()
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    if not probe.exists():
        raise ContinuityError("Cannot resolve filesystem semantics", "filesystem_semantics_unsupported")
    return probe


def _windows_filesystem_observation(probe: Path) -> dict[str, Any]:
    volume_path = ctypes.create_unicode_buffer(261)
    if not ctypes.windll.kernel32.GetVolumePathNameW(str(probe), volume_path, len(volume_path)):
        raise OSError(ctypes.windll.kernel32.GetLastError(), "GetVolumePathNameW failed")
    filesystem = ctypes.create_unicode_buffer(261)
    serial = ctypes.c_uint32()
    maximum_component_length = ctypes.c_uint32()
    flags = ctypes.c_uint32()
    if not ctypes.windll.kernel32.GetVolumeInformationW(
        volume_path.value,
        None,
        0,
        ctypes.byref(serial),
        ctypes.byref(maximum_component_length),
        ctypes.byref(flags),
        filesystem,
        len(filesystem),
    ):
        raise OSError(ctypes.windll.kernel32.GetLastError(), "GetVolumeInformationW failed")
    return {
        "filesystem": filesystem.value,
        "flags": int(flags.value),
        "drive_type": int(ctypes.windll.kernel32.GetDriveTypeW(volume_path.value)),
        "volume_path": volume_path.value,
        "volume_serial": int(serial.value),
        "maximum_component_length": int(maximum_component_length.value),
    }


def _file_identity(path: Path) -> tuple[int, int] | None:
    try:
        lexical = os.lstat(path)
    except OSError:
        return None
    if (
        not stat.S_ISREG(lexical.st_mode)
        or int(lexical.st_ino) == 0
        or _has_reparse_component(path, path.parent)
    ):
        return None
    return int(lexical.st_dev), int(lexical.st_ino)


def _direct_regular_file_identity(lock_path: Path) -> tuple[int, int]:
    identity = _file_identity(lock_path)
    if identity is None:
        raise OSError(
            errno.ENOTSUP,
            "Permanent Continuity lock must be one direct regular file with a stable identity",
        )
    return identity


def _read_direct_file_bytes(
    path: Path,
    *,
    boundary: Path | None = None,
) -> tuple[bytes, tuple[int, int]]:
    """Read one direct regular file while binding the opened and lexical identities."""
    checked_boundary = boundary or path.parent
    if _has_reparse_component(path, checked_boundary):
        raise OSError(errno.ELOOP, "Direct file read crossed an indirect edge", str(path))
    expected = _direct_regular_file_identity(path)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(str(path), flags)
    try:
        opened = os.fstat(descriptor)
        opened_identity = (int(opened.st_dev), int(opened.st_ino))
        if (
            not stat.S_ISREG(opened.st_mode)
            or int(opened.st_ino) == 0
            or opened_identity != expected
        ):
            raise OSError(errno.ESTALE, "Direct file identity changed while opening", str(path))
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            value = handle.read()
        if _file_identity(path) != expected:
            raise OSError(errno.ESTALE, "Direct file identity changed while reading", str(path))
        return value, expected
    finally:
        os.close(descriptor)


def _probe_regular_file_lock(lock_path: Path) -> None:
    lexical_device, lexical_inode = _direct_regular_file_identity(lock_path)
    flags = os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(str(lock_path), flags)
    acquired = False
    state: Any = None
    try:
        try:
            opened = os.fstat(descriptor)
        except OSError as exc:
            raise ContinuityError(
                "Permanent Continuity lock identity cannot be inspected",
                "filesystem_semantics_unsupported",
            ) from exc
        if (
            not stat.S_ISREG(opened.st_mode)
            or int(opened.st_dev) != lexical_device
            or int(opened.st_ino) != lexical_inode
        ):
            raise OSError(errno.ESTALE, "Permanent Continuity lock identity changed while opening")
        acquired, state = _try_os_lock(descriptor)
        # An initially busy permanent lock already demonstrates exclusion. When this
        # process acquires it, a second independently opened handle must be refused.
        if acquired:
            challenger = os.open(str(lock_path), flags)
            challenger_acquired = False
            challenger_state: Any = None
            try:
                challenger_opened = os.fstat(challenger)
                if (
                    not stat.S_ISREG(challenger_opened.st_mode)
                    or int(challenger_opened.st_dev) != lexical_device
                    or int(challenger_opened.st_ino) != lexical_inode
                ):
                    raise OSError(errno.ESTALE, "Permanent Continuity lock identity changed for exclusion check")
                challenger_acquired, challenger_state = _try_os_lock(challenger)
                if challenger_acquired:
                    raise OSError(errno.EIO, "Filesystem lock primitive did not enforce exclusion")
            finally:
                if challenger_acquired:
                    _unlock_os_lock(challenger, challenger_state)
                os.close(challenger)
        os.fsync(descriptor)
    finally:
        if acquired:
            _unlock_os_lock(descriptor, state)
        os.close(descriptor)


def _filesystem_capability_probe(
    root: Path,
    probe: Path,
    replace_operation: Any,
    *,
    workspace_root: bool,
) -> None:
    if workspace_root and root.exists():
        if not root.is_dir():
            raise OSError(errno.ENOTDIR, "Continuity root is not a directory")
        lock_path = root / "locks" / "workspace.lock"
        _probe_regular_file_lock(lock_path)
        capability_parent = lock_path.parent
    elif root.is_dir():
        capability_parent = root
    else:
        capability_parent = probe if probe.is_dir() else probe.parent
    if not capability_parent.is_dir():
        raise OSError(errno.ENOTDIR, "Capability probe parent is not a directory")

    capability_root = capability_parent / f".cc-filesystem-probe-{uuid.uuid4().hex}"
    try:
        capability_root.mkdir(mode=0o700)
        _fsync_directory(capability_parent)
        lock_path = capability_root / "workspace.lock"
        source = capability_root / "replace.source"
        destination = capability_root / "replace.destination"
        directory_source = capability_root / "directory.source"
        occupied_directory = capability_root / "directory.occupied"
        directory_destination = capability_root / "directory.destination"
        _write_new(lock_path, b"\0")
        directory_source.mkdir()
        occupied_directory.mkdir()
        _fsync_directory(capability_root)
        _probe_regular_file_lock(lock_path)
        try:
            _exclusive_rename(directory_source, occupied_directory)
        except OSError as exc:
            if exc.errno not in {errno.EEXIST, errno.ENOTEMPTY}:
                raise
        else:
            raise OSError(errno.EIO, "Exclusive directory rename replaced an existing destination")
        occupied_directory.rmdir()
        _exclusive_rename(directory_source, directory_destination)
        _fsync_directory(capability_root)
        if directory_source.exists() or not directory_destination.is_dir():
            raise OSError(errno.EIO, "Exclusive directory publication verification failed")
        directory_destination.rmdir()
        _write_new(source, b"replacement")
        _write_new(destination, b"previous")
        replace_operation(source, destination)
        _fsync_directory(capability_root)
        if source.exists() or destination.read_bytes() != b"replacement":
            raise OSError(errno.EIO, "Same-directory replacement verification failed")
        destination.unlink()
        lock_path.unlink()
        _fsync_directory(capability_root)
    finally:
        if capability_root.exists():
            shutil.rmtree(capability_root)
        _fsync_directory(capability_parent)
    if workspace_root and root.exists():
        _fsync_directory(root)


def _windows_filesystem_capability_probe(
    root: Path,
    probe: Path,
    *,
    workspace_root: bool = False,
) -> None:
    def replace_with_write_through(source: Path, destination: Path) -> None:
        movefile_replace_existing = 0x1
        movefile_write_through = 0x8
        ok = ctypes.windll.kernel32.MoveFileExW(
            str(source),
            str(destination),
            movefile_replace_existing | movefile_write_through,
        )
        if not ok:
            raise ctypes.WinError(ctypes.windll.kernel32.GetLastError())

    _filesystem_capability_probe(
        root,
        probe,
        replace_with_write_through,
        workspace_root=workspace_root,
    )


def _posix_filesystem_capability_probe(
    root: Path,
    probe: Path,
    *,
    workspace_root: bool = False,
) -> None:
    _filesystem_capability_probe(root, probe, os.replace, workspace_root=workspace_root)

def _windows_filesystem_adapter(
    root: Path,
    observer: Any | None = None,
    capability_probe: Any | None = None,
    *,
    workspace_root: bool = False,
    perform_capability_probe: bool = True,
) -> str:
    probe = _nearest_existing(root)
    if not probe.is_dir():
        probe = probe.parent
    try:
        observation = (observer or _windows_filesystem_observation)(probe)
        str(observation["filesystem"])
        flags = int(observation["flags"])
        drive_type = int(observation["drive_type"])
    except (AttributeError, KeyError, TypeError, ValueError, OSError) as exc:
        raise ContinuityError("Cannot inspect Windows filesystem semantics", "filesystem_semantics_unsupported") from exc
    if flags & _WINDOWS_FILE_READ_ONLY_VOLUME:
        raise ContinuityError("Read-only Windows volumes cannot support mutation", "filesystem_semantics_unsupported")
    if drive_type not in {2, 3}:
        raise ContinuityError(
            "Windows mutation requires a writable fixed or removable volume; remote, optical, RAM, and unresolved volumes are unqualified",
            "filesystem_semantics_unsupported",
        )
    if perform_capability_probe:
        try:
            if capability_probe is None:
                _windows_filesystem_capability_probe(root, probe, workspace_root=workspace_root)
            else:
                capability_probe(root, probe)
        except (ImportError, OSError) as exc:
            raise ContinuityError("Windows filesystem lacks a required lock, flush, or replacement primitive", "filesystem_semantics_unsupported") from exc
    # The filesystem label is diagnostic only. Admission follows the Win32 primitive set and observed hazards.
    return "windows-LockFileEx-MoveFileExW-write-through/v2"


def _darwin_filesystem_adapter(
    root: Path,
    observer: Any | None = None,
    capability_probe: Any | None = None,
    *,
    workspace_root: bool = False,
    perform_capability_probe: bool = True,
) -> str:
    probe = _nearest_existing(root)
    if not probe.is_dir():
        probe = probe.parent
    try:
        observation = (observer or _darwin_filesystem_observation)(probe)
        str(observation["filesystem"])
        flags = int(observation["flags"])
    except (AttributeError, KeyError, TypeError, ValueError, OSError, UnicodeError) as exc:
        raise ContinuityError("Cannot inspect Darwin filesystem semantics", "filesystem_semantics_unsupported") from exc
    if not flags & _DARWIN_MNT_LOCAL:
        raise ContinuityError("Network and nonlocal Darwin filesystems are outside the qualified mutation boundary", "filesystem_semantics_unsupported")
    if flags & _DARWIN_MNT_RDONLY:
        raise ContinuityError("Read-only Darwin filesystems cannot support mutation", "filesystem_semantics_unsupported")
    if perform_capability_probe:
        try:
            if capability_probe is None:
                _posix_filesystem_capability_probe(root, probe, workspace_root=workspace_root)
            else:
                capability_probe(root, probe)
        except (ImportError, OSError) as exc:
            raise ContinuityError("Darwin filesystem lacks a required lock, flush, or replacement primitive", "filesystem_semantics_unsupported") from exc
    # APFS, HFS, ZFS, and future local filesystem names take the same capability path.
    return "darwin-fcntl-flock-fsync-F_FULLFSYNC-when-available-rename-parent-fsync/v2"


def _parse_linux_mountinfo(mount_id: str, mountinfo_text: str) -> dict[str, Any]:
    for line in mountinfo_text.splitlines():
        fields = line.split()
        if not fields or fields[0] != mount_id:
            continue
        try:
            separator = fields.index("-")
            filesystem = fields[separator + 1].casefold()
            mount_options = frozenset(fields[5].casefold().split(","))
            super_options = frozenset(fields[separator + 3].casefold().split(","))
            all_options = mount_options | super_options
        except (IndexError, ValueError):
            return {}
        return {
            "mount_id": mount_id,
            "device": fields[2],
            "mount_root": fields[3],
            "mount_point": fields[4],
            "filesystem": filesystem,
            "mount_options": mount_options,
            "super_options": super_options,
            "remote": filesystem in _LINUX_REMOTE_FILESYSTEMS,
            "ephemeral": filesystem in _LINUX_EPHEMERAL_FILESYSTEMS,
            "volatile": filesystem == "overlay" and bool(
                all_options & {"volatile", "fsync=volatile", "fsync=off"}
            ),
        }
    return {}


def _linux_mount_observation(descriptor: int) -> dict[str, Any]:
    fdinfo_path = Path(f"/proc/self/fdinfo/{descriptor}")
    mountinfo_path = Path("/proc/self/mountinfo")
    if not fdinfo_path.is_file() or not mountinfo_path.is_file():
        return {}
    mount_id: str | None = None
    for line in fdinfo_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("mnt_id:"):
            mount_id = line.split(":", 1)[1].strip()
            break
    if not mount_id:
        return {}
    return _parse_linux_mountinfo(mount_id, mountinfo_path.read_text(encoding="utf-8"))

def _linux_filesystem_observation(probe: Path) -> dict[str, Any]:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(str(probe), flags)
    try:
        statvfs = os.fstatvfs(descriptor)
        observation = _linux_mount_observation(descriptor)
        observation["readonly"] = bool(statvfs.f_flag & getattr(os, "ST_RDONLY", 1))
        return observation
    finally:
        os.close(descriptor)


def _linux_filesystem_adapter(
    root: Path,
    observer: Any | None = None,
    capability_probe: Any | None = None,
    *,
    workspace_root: bool = False,
    perform_capability_probe: bool = True,
) -> str:
    probe = _nearest_existing(root)
    if not probe.is_dir():
        probe = probe.parent
    try:
        observation = (observer or _linux_filesystem_observation)(probe)
        filesystem = str(observation["filesystem"]).strip().casefold()
        mount_id = str(observation["mount_id"]).strip()
        device = str(observation["device"]).strip()
        if not filesystem or not mount_id or not device:
            raise ValueError("Linux mount identity is incomplete")
        readonly = bool(observation["readonly"])
        remote = bool(observation.get("remote", False)) or filesystem in _LINUX_REMOTE_FILESYSTEMS
        ephemeral = bool(observation.get("ephemeral", False)) or filesystem in _LINUX_EPHEMERAL_FILESYSTEMS
        volatile = bool(observation.get("volatile", False))
    except (AttributeError, KeyError, TypeError, ValueError, OSError, UnicodeError) as exc:
        raise ContinuityError("Cannot inspect Linux filesystem semantics", "filesystem_semantics_unsupported") from exc
    if readonly:
        raise ContinuityError("Read-only Linux filesystems cannot support mutation", "filesystem_semantics_unsupported")
    if remote:
        raise ContinuityError("Remote or shared Linux filesystems require a separately qualified distributed-lock boundary", "filesystem_semantics_unsupported")
    if ephemeral:
        raise ContinuityError("Memory-backed Linux filesystems cannot provide persistent continuity", "filesystem_semantics_unsupported")
    if volatile:
        raise ContinuityError("Volatile OverlayFS explicitly lacks the required sync guarantee", "filesystem_semantics_unsupported")
    if perform_capability_probe:
        try:
            if capability_probe is None:
                _posix_filesystem_capability_probe(root, probe, workspace_root=workspace_root)
            else:
                capability_probe(root, probe)
        except (ImportError, OSError) as exc:
            raise ContinuityError("Linux filesystem lacks a required lock, flush, or replacement primitive", "filesystem_semantics_unsupported") from exc
    # No positive name allowlist: unknown local names qualify when required primitives do; known hazard types still fail closed.
    return "linux-fcntl-flock-fsync-rename-parent-fsync/v1"


def _filesystem_adapter(
    root: Path,
    *,
    lexical_root: Path | None = None,
    platform_name: str | None = None,
    windows_observer: Any | None = None,
    windows_capability_probe: Any | None = None,
    darwin_observer: Any | None = None,
    linux_observer: Any | None = None,
    posix_capability_probe: Any | None = None,
    workspace_root: bool = False,
    perform_capability_probe: bool = True,
) -> str:
    _verify_lexical_identity(root, lexical_root or root)
    observed_platform = platform_name or sys.platform
    if observed_platform == "win32":
        return _windows_filesystem_adapter(
            root,
            windows_observer,
            windows_capability_probe,
            workspace_root=workspace_root,
            perform_capability_probe=perform_capability_probe,
        )
    if observed_platform == "darwin":
        return _darwin_filesystem_adapter(
            root,
            darwin_observer,
            posix_capability_probe,
            workspace_root=workspace_root,
            perform_capability_probe=perform_capability_probe,
        )
    if observed_platform.startswith("linux"):
        return _linux_filesystem_adapter(
            root,
            linux_observer,
            posix_capability_probe,
            workspace_root=workspace_root,
            perform_capability_probe=perform_capability_probe,
        )
    raise ContinuityError(
        "Qualified mutation requires a Windows, Darwin, or Linux primitive adapter",
        "filesystem_semantics_unsupported",
    )


_CRITICAL_FILESYSTEM_DIRECTORIES = ("locks", "transactions", "generations", "quarantine")


def _filesystem_qualification_witness(
    root: Path,
    *,
    lexical_root: Path | None = None,
    perform_capability_probe: bool = True,
) -> dict[str, Any]:
    adapter = _filesystem_adapter(
        root,
        lexical_root=lexical_root,
        workspace_root=True,
        perform_capability_probe=perform_capability_probe,
    )
    if not root.is_dir():
        raise ContinuityError("Qualified workspace root is not a directory", "filesystem_semantics_unsupported")
    critical_items = [(".", root)] + [
        (name, root / name) for name in _CRITICAL_FILESYSTEM_DIRECTORIES
    ]
    critical_identities: dict[str, dict[str, int]] = {}
    try:
        for label, path in critical_items:
            metadata = os.stat(path, follow_symlinks=False)
            if not stat.S_ISDIR(metadata.st_mode):
                raise ContinuityError(
                    "A critical Continuity directory is missing or indirect",
                    "filesystem_semantics_unsupported",
                )
            if _has_reparse_component(path, root):
                raise ContinuityError(
                    "A critical Continuity directory crosses an indirect edge",
                    "custody_reparse_escape",
                )
            if int(metadata.st_ino) == 0:
                raise ContinuityError(
                    "A critical Continuity directory file identity is unavailable",
                    "filesystem_semantics_unsupported",
                )
            critical_identities[label] = {
                "device": int(metadata.st_dev),
                "inode": int(metadata.st_ino),
            }
    except OSError as exc:
        raise ContinuityError(
            "A critical Continuity directory identity is unavailable",
            "filesystem_semantics_unsupported",
        ) from exc
    directory_identity_pairs = {
        (identity["device"], identity["inode"])
        for identity in critical_identities.values()
    }
    if len(directory_identity_pairs) != len(critical_identities):
        raise ContinuityError(
            "Critical Continuity directories do not have distinct file identities",
            "filesystem_semantics_unsupported",
        )
    devices = {identity["device"] for identity in critical_identities.values()}
    if len(devices) != 1:
        raise ContinuityError("Critical Continuity directories cross filesystem devices", "filesystem_semantics_unsupported")
    critical = [path for _, path in critical_items]
    try:
        lock_device, lock_inode = _direct_regular_file_identity(root / "locks" / "workspace.lock")
    except OSError as exc:
        raise ContinuityError("Permanent Continuity lock identity is unavailable", "filesystem_semantics_unsupported") from exc
    if lock_device != next(iter(devices)):
        raise ContinuityError("Permanent Continuity lock crosses filesystem devices", "filesystem_semantics_unsupported")
    observed_platform = sys.platform
    witness: dict[str, Any] = {
        "adapter": adapter,
        "platform": observed_platform,
        "device": next(iter(devices)),
        "critical_directory_count": len(critical),
        "critical_directory_identities": critical_identities,
        "lock_device": lock_device,
        "lock_inode": lock_inode,
    }
    try:
        if observed_platform == "win32":
            observations = [_windows_filesystem_observation(path) for path in critical]
            identities: set[tuple[str, int]] = set()
            for observation in observations:
                volume_path = str(observation.get("volume_path") or "").casefold()
                volume_serial = observation.get("volume_serial")
                flags = int(observation.get("flags", _WINDOWS_FILE_READ_ONLY_VOLUME))
                drive_type = int(observation.get("drive_type", 0))
                if not volume_path or not isinstance(volume_serial, int):
                    raise ContinuityError("Windows volume identity is unavailable", "filesystem_semantics_unsupported")
                if flags & _WINDOWS_FILE_READ_ONLY_VOLUME or drive_type not in {2, 3}:
                    raise ContinuityError("A critical Windows directory is not on a qualified writable volume", "filesystem_semantics_unsupported")
                identities.add((volume_path, int(volume_serial)))
            if len(identities) != 1:
                raise ContinuityError("Critical Continuity directories cross Windows volume identities", "filesystem_semantics_unsupported")
            volume_path, volume_serial = next(iter(identities))
            witness["volume_path"] = volume_path
            witness["volume_serial"] = volume_serial
        elif observed_platform == "darwin":
            observations = [_darwin_filesystem_observation(path) for path in critical]
            identities: set[tuple[tuple[int, ...], str, str]] = set()
            for observation in observations:
                flags = int(observation.get("flags", 0))
                fsid_value = observation.get("fsid")
                mount_point = str(observation.get("mount_point") or "")
                mounted_from = str(observation.get("mounted_from") or "")
                if (
                    not isinstance(fsid_value, (tuple, list))
                    or len(fsid_value) != 2
                    or not mount_point
                    or not mounted_from
                ):
                    raise ContinuityError("Darwin mount identity is unavailable", "filesystem_semantics_unsupported")
                if not flags & _DARWIN_MNT_LOCAL or flags & _DARWIN_MNT_RDONLY:
                    raise ContinuityError("A critical Darwin directory is not on a qualified local writable mount", "filesystem_semantics_unsupported")
                identities.add((tuple(int(value) for value in fsid_value), mount_point, mounted_from))
            if len(identities) != 1:
                raise ContinuityError("Critical Continuity directories cross Darwin mounts", "filesystem_semantics_unsupported")
            fsid_value, mount_point, mounted_from = next(iter(identities))
            witness["darwin_fsid"] = list(fsid_value)
            witness["mount_point"] = mount_point
            witness["mounted_from"] = mounted_from
        elif observed_platform.startswith("linux"):
            observations = [_linux_filesystem_observation(path) for path in critical]
            identities: set[tuple[str, str]] = set()
            for observation in observations:
                mount_id = observation.get("mount_id")
                device = observation.get("device")
                if not mount_id or not device:
                    raise ContinuityError("Linux mount identity is unavailable", "filesystem_semantics_unsupported")
                if bool(observation.get("readonly", False)):
                    raise ContinuityError("A critical Linux directory is read-only", "filesystem_semantics_unsupported")
                if bool(observation.get("remote", False)) or bool(observation.get("ephemeral", False)) or bool(observation.get("volatile", False)):
                    raise ContinuityError("A critical Linux directory acquired an unqualified mount hazard", "filesystem_semantics_unsupported")
                identities.add((str(mount_id), str(device)))
            if len(identities) != 1:
                raise ContinuityError("Critical Continuity directories cross Linux mounts", "filesystem_semantics_unsupported")
            mount_id, linux_device = next(iter(identities))
            witness["mount_id"] = mount_id
            witness["linux_device"] = linux_device
    except ContinuityError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError, OSError, UnicodeError) as exc:
        raise ContinuityError(
            "Cannot re-observe critical filesystem identities",
            "filesystem_semantics_unsupported",
        ) from exc
    return witness

def mutation_filesystem_support(
    root: Path,
    *,
    lexical_root: Path | None = None,
    platform_name: str | None = None,
    windows_observer: Any | None = None,
    windows_capability_probe: Any | None = None,
    darwin_observer: Any | None = None,
    linux_observer: Any | None = None,
    posix_capability_probe: Any | None = None,
) -> dict[str, Any]:
    """Report non-mutating mutation preflight without claiming primitive qualification."""
    try:
        if root.is_dir() and platform_name is None and all(
            value is None
            for value in (
                windows_observer,
                windows_capability_probe,
                darwin_observer,
                linux_observer,
                posix_capability_probe,
            )
        ):
            adapter = _filesystem_qualification_witness(
                root,
                lexical_root=lexical_root,
                perform_capability_probe=False,
            )["adapter"]
        else:
            adapter = _filesystem_adapter(
                root,
                lexical_root=lexical_root,
                platform_name=platform_name,
                windows_observer=windows_observer,
                windows_capability_probe=windows_capability_probe,
                darwin_observer=darwin_observer,
                linux_observer=linux_observer,
                posix_capability_probe=posix_capability_probe,
                perform_capability_probe=False,
            )
    except (ContinuityError, OSError) as exc:
        reason = exc.code if isinstance(exc, ContinuityError) else "filesystem_semantics_unsupported"
        return {"status": "unsupported", "reason_code": reason}
    return {
        "status": "preflight_supported",
        "adapter": adapter,
        "transaction_probe_required": True,
    }

def _selector_custody_boundaries() -> list[Path]:
    """Return every active Nova custody boundary from one stable registry read."""
    boundaries = {SELECTOR_REGISTRY.resolve()}
    if SELECTOR_REGISTRY.is_file():
        _, registry, _ = _registry(SELECTOR_REGISTRY)
        active = registry["active_values"]
        nova_root = _absolute_local(active.get(ROOT_SELECTOR), ROOT_SELECTOR)
        boundaries.add((nova_root / "mind").resolve())
        boundaries.add((nova_root / "archive").resolve())
        for selector_name, raw in active.items():
            selected = _absolute_local(raw, f"active selector {selector_name}")
            # File selectors own their containing capability directory; directory/root/home
            # selectors own the selected subtree. NOVA_DATA_ROOT deliberately protects the
            # complete Nova federation from operator-custodied artifacts.
            suffix = selected.suffix.casefold()
            boundary = selected.parent if suffix or selector_name.endswith(("_STORE", "_DATABASE")) else selected
            boundaries.add(boundary.resolve())
            boundaries.add(selected.resolve())
    return sorted(boundaries, key=lambda item: (len(item.parts), os.path.normcase(str(item))))


def _is_within(candidate: Path, boundary: Path) -> bool:
    try:
        candidate.relative_to(boundary)
        return True
    except ValueError:
        return False


def validate_external_target(
    source_root: Path,
    value: str,
    label: str,
    *,
    must_be_absent: bool = False,
    require_mutation: bool = True,
) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ContinuityError(f"{label} is missing", "selector_registry_invalid")
    raw = value.strip()
    lexical = Path(os.path.abspath(raw))
    # Inspect the caller's lexical path before resolve(); resolving first would erase the
    # junction/symlink edge we are obliged to reject.
    if _has_reparse_component(lexical):
        raise ContinuityError(f"{label} crosses an unverified reparse edge", "custody_reparse_escape")
    target = _absolute_local(raw, label)
    source = source_root.resolve()
    if _is_within(target, source):
        raise ContinuityError(f"{label} must remain outside source canon", "protected_target_denied")
    if ".codex" in {part.casefold() for part in target.parts}:
        raise ContinuityError(f"{label} cannot use host .codex custody", "protected_target_denied")
    for boundary in _selector_custody_boundaries():
        if _is_within(target, boundary):
            raise ContinuityError(f"{label} enters a protected Nova capability boundary", "protected_target_denied")
    if must_be_absent and target.exists():
        raise ContinuityError(f"{label} must be absent", "protected_target_denied")
    if require_mutation:
        # External writes, replacements, directory publication, and deletion all mutate the containing directory.
        if not target.parent.is_dir():
            raise ContinuityError(
                f"{label} requires an existing exact parent directory",
                "protected_target_denied",
            )
        _filesystem_adapter(target.parent, lexical_root=lexical.parent)
    return target

def _path_identity(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


def _corroborate_nova_migration_environment(custody_root: Path, ambient: Path) -> None:
    observed_root = os.environ.get(ROOT_SELECTOR)
    observed_continuity = os.environ.get(SELECTOR)
    if not observed_root or _path_identity(_absolute_local(observed_root, ROOT_SELECTOR)) != _path_identity(custody_root):
        raise ContinuityError("Process NOVA_DATA_ROOT disagrees with the trusted registry", "nova_root_mismatch")
    if not observed_continuity or _path_identity(_absolute_local(observed_continuity, SELECTOR)) != _path_identity(ambient):
        raise ContinuityError("Process NOVA_CONTINUITY_HOME disagrees with the trusted registry", "continuity_selector_mismatch")


def validate_nova_migration_destination(
    source_root: Path,
    value: str,
    label: str,
    *,
    grant_id: str,
    expected_registry_sha256: str,
    expected_destination_sha256: str,
    must_be_absent: bool = False,
) -> tuple[Path, NovaMigrationGrant]:
    """Authorize only an exact new sibling of the active Nova Continuity store."""
    if not isinstance(grant_id, str) or not grant_id.strip():
        raise ContinuityError("Nova copy migration requires a recorded grant ID", "authority_denied")
    if contains_secret_data(grant_id):
        raise ContinuityError("Migration grant ID failed redaction", "redaction_rejected")
    expected_registry = str(expected_registry_sha256 or "").strip().casefold()
    expected_destination = str(expected_destination_sha256 or "").strip().casefold()
    if len(expected_registry) != 64 or any(char not in "0123456789abcdef" for char in expected_registry):
        raise ContinuityError("Nova copy migration requires an exact selector registry SHA-256", "selector_registry_invalid")
    if len(expected_destination) != 64 or any(char not in "0123456789abcdef" for char in expected_destination):
        raise ContinuityError("Nova copy migration requires an exact normalized destination SHA-256", "selector_registry_invalid")

    registry_path, custody_root, ambient, registry, digest = _nova_registry_values()
    if digest != expected_registry:
        raise ContinuityError("Trusted Nova selector registry does not match the migration grant", "selector_registry_changed")
    _corroborate_nova_migration_environment(custody_root, ambient)
    source = source_root.resolve()
    if _path_identity(source) != _path_identity(ambient):
        raise ContinuityError("Nova copy migration source is not the active Continuity selector", "caller_root_denied")

    provided = str(value or "")
    raw = provided.strip()
    if provided != raw:
        raise ContinuityError(f"{label} has ambiguous surrounding whitespace", "protected_target_denied")
    lexical = Path(os.path.abspath(raw))
    if lexical.name.rstrip(" .") != lexical.name:
        raise ContinuityError(f"{label} has an alias-prone Windows name", "protected_target_denied")
    if _has_reparse_component(lexical):
        raise ContinuityError(f"{label} crosses an unverified reparse edge", "custody_reparse_escape")
    target = _absolute_local(raw, label)
    _within(custody_root, target, "caller_root_denied")
    if _path_identity(target.parent) != _path_identity(ambient.parent):
        raise ContinuityError(f"{label} must be a sibling of the active Continuity store", "protected_target_denied")
    if source == target or source in target.parents or target in source.parents:
        raise ContinuityError("Migration requires a distinct non-nested destination", "protected_target_denied")
    if ".codex" in {part.casefold() for part in target.parts}:
        raise ContinuityError(f"{label} cannot use host .codex custody", "protected_target_denied")

    for selector_name, selected_raw in registry["active_values"].items():
        if selector_name == ROOT_SELECTOR:
            continue
        selected = _absolute_local(selected_raw, f"active selector {selector_name}")
        suffix = selected.suffix.casefold()
        boundary = selected.parent if suffix or selector_name.endswith(("_STORE", "_DATABASE")) else selected
        if _is_within(target, boundary) or _is_within(boundary, target):
            raise ContinuityError(f"{label} overlaps active capability selector {selector_name}", "protected_target_denied")

    destination_sha256 = sha256_bytes(_path_identity(target).encode("utf-8"))
    if destination_sha256 != expected_destination:
        raise ContinuityError("Migration destination does not match the exact recorded grant", "authority_denied")
    if must_be_absent and target.exists():
        raise ContinuityError(f"{label} must be absent", "protected_target_denied")
    _filesystem_adapter(target.parent, lexical_root=lexical.parent)
    _, _, final_digest = _registry(registry_path)
    if final_digest != digest:
        raise ContinuityError("Trusted Nova selector registry changed during destination authorization", "selector_registry_changed")
    return target, NovaMigrationGrant(
        grant_id=grant_id.strip(),
        registry_path=str(registry_path),
        registry_digest=digest,
        custody_root=str(custody_root),
        ambient_root=str(ambient),
        destination_root=str(target),
        destination_lexical=str(lexical),
        destination_sha256=destination_sha256,
    )


def revalidate_nova_migration_grant(
    token: NovaMigrationGrant,
    source_root: Path,
    destination: Path,
    *,
    require_destination_absent: bool,
) -> None:
    registry_path, custody_root, ambient, registry, digest = _nova_registry_values(Path(token.registry_path))
    if digest != token.registry_digest:
        raise ContinuityError("Trusted Nova selector registry changed during copy migration", "selector_registry_changed")
    if _path_identity(registry_path) != _path_identity(Path(token.registry_path)):
        raise ContinuityError("Trusted Nova selector registry identity changed", "selector_registry_changed")
    if _path_identity(custody_root) != _path_identity(Path(token.custody_root)):
        raise ContinuityError("Trusted Nova custody root changed during copy migration", "selector_registry_changed")
    if _path_identity(ambient) != _path_identity(Path(token.ambient_root)):
        raise ContinuityError("Active Continuity selector changed during copy migration", "selector_registry_changed")
    _corroborate_nova_migration_environment(custody_root, ambient)
    if _path_identity(source_root) != _path_identity(ambient):
        raise ContinuityError("Copy migration source is no longer the active Continuity selector", "selector_registry_changed")
    if _path_identity(destination) != _path_identity(Path(token.destination_root)):
        raise ContinuityError("Copy migration destination changed after authorization", "selector_registry_changed")
    if sha256_bytes(_path_identity(destination).encode("utf-8")) != token.destination_sha256:
        raise ContinuityError("Copy migration destination grant no longer matches", "selector_registry_changed")
    if _has_reparse_component(source_root) or _has_reparse_component(Path(token.destination_lexical)):
        raise ContinuityError("Copy migration path crossed a reparse edge", "custody_reparse_escape")
    for selector_name, selected_raw in registry["active_values"].items():
        if selector_name == ROOT_SELECTOR:
            continue
        selected = _absolute_local(selected_raw, f"active selector {selector_name}")
        suffix = selected.suffix.casefold()
        boundary = selected.parent if suffix or selector_name.endswith(("_STORE", "_DATABASE")) else selected
        if _is_within(destination, boundary) or _is_within(boundary, destination):
            raise ContinuityError("Copy migration destination now overlaps an active capability selector", "selector_registry_changed")
    destination_lexical = Path(token.destination_lexical)
    if require_destination_absent:
        if destination.exists():
            raise ContinuityError(
                "Migration destination must remain absent until publication begins",
                "protected_target_denied",
            )
        _filesystem_adapter(
            destination.parent,
            lexical_root=destination_lexical.parent,
        )
    else:
        _filesystem_adapter(
            destination,
            lexical_root=destination_lexical,
            workspace_root=True,
        )

_PROCESS_STARTED_AT = utc_now()
_RUNTIME_SESSION_ID = uuid.uuid4().hex

class _WindowsOverlapped(ctypes.Structure):
    _fields_ = [("Internal", ctypes.c_size_t), ("InternalHigh", ctypes.c_size_t), ("Offset", ctypes.c_uint32), ("OffsetHigh", ctypes.c_uint32), ("hEvent", ctypes.c_void_p)]

def _try_os_lock(descriptor: int) -> tuple[bool, Any]:
    if os.name == "nt":
        import msvcrt
        handle = msvcrt.get_osfhandle(descriptor)
        overlapped = _WindowsOverlapped()
        flags = 0x00000002 | 0x00000001
        ok = ctypes.windll.kernel32.LockFileEx(ctypes.c_void_p(handle), flags, 0, 1, 0, ctypes.byref(overlapped))
        if not ok:
            error = ctypes.windll.kernel32.GetLastError()
            if error in {32, 33, 36, 158}:
                return False, overlapped
            raise ctypes.WinError(error)
        return True, overlapped
    import fcntl
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True, None
    except BlockingIOError:
        return False, None

def _unlock_os_lock(descriptor: int, state: Any) -> None:
    if os.name == "nt":
        import msvcrt
        handle = msvcrt.get_osfhandle(descriptor)
        if not ctypes.windll.kernel32.UnlockFileEx(ctypes.c_void_p(handle), 0, 1, 0, ctypes.byref(state)):
            raise ctypes.WinError(ctypes.windll.kernel32.GetLastError())
    else:
        import fcntl
        fcntl.flock(descriptor, fcntl.LOCK_UN)

def _owner_observation(root: Path) -> dict[str, Any]:
    path = root / "locks" / "workspace-owner.json"
    if not path.is_file():
        return {"classification": "absent"}
    try:
        value = _read_json_path(path)
    except ContinuityError:
        return {"classification": "unknown", "reason": "metadata_invalid"}
    host = value.get("host") if isinstance(value, dict) else None
    pid = value.get("pid") if isinstance(value, dict) else None
    classification = "unknown"
    if host == socket.gethostname() and isinstance(pid, int) and pid > 0:
        try:
            os.kill(pid, 0)
            classification = "live-looking"
        except ProcessLookupError:
            classification = "dead-looking"
        except OSError:
            classification = "unknown"
    return {"classification": classification, "owner_token": value.get("owner_token") if isinstance(value, dict) else None}

@contextmanager
def workspace_lock(
    root: Path,
    timeout: float = 0.0,
    *,
    transaction_id: str | None = None,
    lexical_root: Path | None = None,
) -> Iterator[dict[str, Any]]:
    """Acquire the permanent writer lock before any probe or metadata mutation."""
    lexical = lexical_root or root
    prelock_witness = _filesystem_qualification_witness(
        root,
        lexical_root=lexical,
        perform_capability_probe=False,
    )
    locks = root / "locks"
    if not locks.is_dir() or _has_reparse_component(locks, root):
        raise ContinuityError(
            "Permanent Continuity lock directory is missing or indirect",
            "filesystem_semantics_unsupported",
        )
    lock_path = locks / "workspace.lock"
    try:
        lexical_device, lexical_inode = _direct_regular_file_identity(lock_path)
    except OSError as exc:
        raise ContinuityError(
            "Permanent Continuity lock identity is unavailable",
            "filesystem_semantics_unsupported",
        ) from exc
    flags = os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(str(lock_path), flags)
    except OSError as exc:
        raise ContinuityError(
            "Permanent Continuity lock cannot be opened directly",
            "filesystem_semantics_unsupported",
        ) from exc
    acquired = False
    state: Any = None
    deadline = time.monotonic() + max(0.0, timeout)
    try:
        try:
            opened = os.fstat(descriptor)
        except OSError as exc:
            raise ContinuityError(
                "Permanent Continuity lock identity cannot be inspected",
                "filesystem_semantics_unsupported",
            ) from exc
        if (
            not stat.S_ISREG(opened.st_mode)
            or int(opened.st_ino) == 0
            or int(opened.st_dev) != lexical_device
            or int(opened.st_ino) != lexical_inode
        ):
            raise ContinuityError(
                "Permanent Continuity lock identity changed while opening",
                "filesystem_identity_changed",
            )
        while True:
            try:
                acquired, state = _try_os_lock(descriptor)
            except OSError as exc:
                raise ContinuityError(
                    "Permanent Continuity lock primitive failed",
                    "filesystem_semantics_unsupported",
                ) from exc
            if acquired:
                break
            if time.monotonic() >= deadline:
                observed = _owner_observation(root)
                raise ContinuityError(
                    f"Continuity writer lock is busy; owner={observed['classification']}; retry_after_ms=100",
                    "lock_busy",
                )
            time.sleep(min(0.025, max(0.0, deadline - time.monotonic())))

        # The disposable proof is deliberately inside the permanent lock. A busy
        # contender therefore performs no probe and changes no owner metadata.
        locked_witness = _filesystem_qualification_witness(
            root,
            lexical_root=lexical,
            perform_capability_probe=True,
        )
        if locked_witness != prelock_witness:
            raise ContinuityError(
                "Filesystem identity changed while acquiring the writer lock",
                "filesystem_identity_changed",
            )
        token = uuid.uuid4().hex + uuid.uuid4().hex
        owner = {
            "format": LOCK_FORMAT,
            "owner_token": token,
            "pid": os.getpid(),
            "process_started_at": _PROCESS_STARTED_AT,
            "host": socket.gethostname(),
            "session_identity": os.environ.get("SESSIONNAME") or _RUNTIME_SESSION_ID,
            "runtime_identity": f"python-{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "transaction_id": transaction_id,
            "acquired_at": utc_now(),
            "adapter": locked_witness["adapter"],
            "filesystem_witness": locked_witness,
            "prior_owner_observation": _owner_observation(root),
        }
        try:
            atomic_json(locks / "workspace-owner.json", owner)
        except OSError as exc:
            raise ContinuityError(
                "Writer lock owner evidence could not be published",
                "recovery_required",
            ) from exc
        try:
            yield owner
        finally:
            primary_exception = sys.exc_info()[1]
            owner_path = locks / "workspace-owner.json"
            owner_cleanup_error: BaseException | None = None
            try:
                current = _read_json_path(owner_path)
                if isinstance(current, dict) and current.get("owner_token") == token:
                    owner_path.unlink()
                    _fsync_directory(locks)
                else:
                    owner_cleanup_error = ContinuityError(
                        "Writer lock owner evidence changed before cleanup",
                        "recovery_required",
                    )
            except (ContinuityError, OSError) as exc:
                owner_cleanup_error = exc
            if owner_cleanup_error is not None:
                if primary_exception is not None:
                    if hasattr(primary_exception, "add_note"):
                        primary_exception.add_note(
                            f"Writer lock owner cleanup was unconfirmed: {owner_cleanup_error}"
                        )
                else:
                    raise ContinuityError(
                        "Writer lock owner cleanup is unconfirmed",
                        "recovery_required",
                    ) from owner_cleanup_error
    finally:
        primary_exception = sys.exc_info()[1]
        release_error: BaseException | None = None
        if acquired:
            try:
                _unlock_os_lock(descriptor, state)
            except OSError as exc:
                release_error = exc
        try:
            os.close(descriptor)
        except OSError as exc:
            if release_error is None:
                release_error = exc
        if release_error is not None:
            if primary_exception is not None:
                if hasattr(primary_exception, "add_note"):
                    primary_exception.add_note(
                        f"Permanent writer lock release was unconfirmed: {release_error}"
                    )
            else:
                raise ContinuityError(
                    "Permanent writer lock release is unconfirmed",
                    "recovery_required",
                ) from release_error
def _crash(point: str) -> None:
    if os.environ.get("CONTINUITY_TEST_FAILPOINT") == point:
        raise ContinuityError(f"Injected failure at {point}", "test_failpoint")
    if os.environ.get("CONTINUITY_TEST_CRASHPOINT") == point:
        os._exit(97)

def _journal_transition(path: Path, state: str, *, recovery: bool = False, **updates: Any) -> dict[str, Any]:
    try:
        _direct_regular_file_identity(path)
    except OSError as exc:
        raise ContinuityError(
            "Transaction journal must remain one direct regular file",
            "recovery_required",
        ) from exc
    allowed = {
        "intent_recorded": "bundle_staged", "bundle_staged": "bundle_published", "bundle_published": "commit_ready",
        "commit_ready": "committed", "committed": "finalized",
    }
    journal = _read_json_path(path)
    if not isinstance(journal, dict) or journal.get("format") != TRANSACTION_FORMAT:
        raise ContinuityError("Transaction journal has an unsupported format", "recovery_required")
    prior_state = journal.get("state")
    if not recovery and allowed.get(str(prior_state)) != state:
        raise ContinuityError(f"Illegal transaction transition {prior_state!r} -> {state!r}", "recovery_required")
    if recovery and state not in {"aborted", "committed", "finalized", "recovery_required"}:
        raise ContinuityError("Illegal recovery transition", "recovery_required")
    prior_digest = sha256_file(path)
    value = dict(journal)
    value.update(updates)
    value.update({"state": state, "sequence": int(journal.get("sequence", 0)) + 1, "prior_state_digest": prior_digest, "transitioned_at": utc_now()})
    try:
        atomic_json(path, value)
    except OSError as exc:
        raise ContinuityError(
            "Transaction journal transition visibility or durability is unconfirmed",
            "recovery_required",
        ) from exc
    return value

def _all_transaction_directories(root: Path) -> list[Path]:
    base = root / "transactions"
    try:
        base_metadata = os.stat(base, follow_symlinks=False)
    except OSError as exc:
        raise ContinuityError(
            "Transaction custody directory is unavailable",
            "recovery_required",
        ) from exc
    if not stat.S_ISDIR(base_metadata.st_mode) or _has_reparse_component(base, root):
        raise ContinuityError(
            "Transaction custody directory must remain one direct directory",
            "recovery_required",
        )
    directories: list[Path] = []
    try:
        items = list(base.iterdir())
    except OSError as exc:
        raise ContinuityError(
            "Transaction custody directory cannot be enumerated",
            "recovery_required",
        ) from exc
    for item in items:
        if _has_reparse_component(item, base):
            raise ContinuityError(
                f"Indirect transaction custody entry is forbidden: {item.name}",
                "recovery_required",
            )
        try:
            metadata = os.stat(item, follow_symlinks=False)
        except OSError as exc:
            raise ContinuityError(
                f"Transaction custody entry identity is unavailable: {item.name}",
                "recovery_required",
            ) from exc
        if not stat.S_ISDIR(metadata.st_mode):
            raise ContinuityError(
                f"Transaction custody entry must be one direct directory: {item.name}",
                "recovery_required",
            )
        directories.append(item)
    return sorted(directories)


def pending_transactions(root: Path) -> list[Path]:
    pending: list[Path] = []
    for directory in _all_transaction_directories(root):
        journal_path = directory / "journal.json"
        if not os.path.lexists(journal_path):
            pending.append(directory)
            continue
        try:
            _direct_regular_file_identity(journal_path)
        except OSError as exc:
            raise ContinuityError(
                f"Transaction journal is not one direct regular file: {directory.name}",
                "recovery_required",
            ) from exc
        try:
            state = _read_json_path(journal_path).get("state")
        except ContinuityError:
            pending.append(directory)
            continue
        if state not in FINAL_JOURNAL_STATES:
            pending.append(directory)
    return pending

def _quarantine_path(root: Path, target: Path, transaction_id: str, label: str) -> str | None:
    _inside(root, target)
    protected = {
        root,
        root / "manifest.json",
        root / "locks",
        root / "locks" / "workspace.lock",
        root / "transactions",
        root / "generations",
        root / "quarantine",
    }
    if target in protected or _has_reparse_component(target, root):
        raise ContinuityError(
            "Recovery quarantine target is protected or indirect",
            "recovery_required",
        )
    quarantine = root / "quarantine"
    if not quarantine.is_dir() or _has_reparse_component(quarantine, root):
        raise ContinuityError(
            "Recovery quarantine custody is missing or indirect",
            "recovery_required",
        )
    destination = quarantine / f"{transaction_id}-{label}"
    target_present = os.path.lexists(target)
    destination_present = os.path.lexists(destination)
    if not target_present:
        if not destination_present:
            return None
        if _has_reparse_component(destination, root):
            raise ContinuityError(
                "Prior recovery quarantine result is indirect",
                "recovery_required",
            )
        _fsync_directory(target.parent)
        _fsync_directory(quarantine)
        return destination.relative_to(root).as_posix()
    if destination_present:
        raise ContinuityError(
            "Recovery found both source and prior quarantine destination",
            "recovery_required",
        )
    try:
        _move_path_write_through(target, destination, replace_existing=False)
    except OSError as exc:
        # A move can be visible even when the second parent sync fails. Confirm both
        # parents and accept that exact prior publication on retry.
        if not os.path.lexists(target) and os.path.lexists(destination):
            try:
                _fsync_directory(destination.parent)
                _fsync_directory(target.parent)
            except OSError as sync_exc:
                raise ContinuityError(
                    "Recovery quarantine move is visible but parent durability is unconfirmed",
                    "recovery_required",
                ) from sync_exc
        else:
            raise ContinuityError(
                "Recovery quarantine publication failed",
                "recovery_required",
            ) from exc
    return destination.relative_to(root).as_posix()


def _journal_artifacts(root: Path, journal: dict[str, Any]) -> tuple[Path, Path, Path]:
    transaction_id = str(journal.get("transaction_id") or journal.get("id") or "")
    new_generation = journal.get("new_generation")
    if not transaction_id or not isinstance(new_generation, int) or new_generation < 0:
        raise ContinuityError("Transaction artifact identity is incomplete", "recovery_required")
    generation_directory = f"g-{new_generation:020d}"
    transaction_root = root / "transactions" / transaction_id
    staged = transaction_root / "stage" / generation_directory
    final = root / "generations" / generation_directory
    expected_staged = staged.relative_to(root).as_posix()
    expected_final = final.relative_to(root).as_posix()
    if (
        journal.get("generation_directory") != generation_directory
        or journal.get("staged_generation_path") != expected_staged
        or journal.get("final_generation_path") != expected_final
    ):
        raise ContinuityError(
            "Transaction artifact paths do not match their deterministic identity",
            "recovery_required",
        )
    for candidate in (transaction_root, staged, final):
        if _has_reparse_component(candidate, root):
            raise ContinuityError(
                "Transaction artifact path crosses an indirect custody edge",
                "recovery_required",
            )
    return staged, final, root / "manifest.next"

def _committed_evidence(root: Path, manifest: dict[str, Any], journal: dict[str, Any]) -> None:
    transaction_id = str(journal.get("transaction_id") or journal.get("id"))
    if manifest.get("committing_transaction_id") != transaction_id or manifest.get("generation") != journal.get("new_generation"):
        raise ContinuityError("Active manifest does not bind the recovering transaction", "recovery_required")
    metadata = _verify_generation(root, manifest)
    if metadata.get("transaction_id") != transaction_id or metadata.get("generation") != journal.get("new_generation"):
        raise ContinuityError("Active generation does not bind the recovering transaction", "recovery_required")
    bundle = generation_path(root, manifest)
    receipts = _read_jsonl_path(bundle / "receipts.jsonl")
    matching_receipts = [row for row in receipts if row.get("transaction_id") == transaction_id and row.get("status") == "committed"]
    if len(matching_receipts) != 1:
        raise ContinuityError("Committed generation lacks one bound canonical receipt", "recovery_required")
    key = journal.get("idempotency_key")
    entries = _read_jsonl_path(bundle / "idempotency.jsonl")
    matching_entries = [row for row in entries if row.get("transaction_id") == transaction_id]
    if key and (len(matching_entries) != 1 or matching_entries[0].get("idempotency_key") != key or matching_entries[0].get("payload_digest") != journal.get("payload_digest")):
        raise ContinuityError("Committed generation lacks its bound idempotency result", "recovery_required")

def _recovery_witness_updates(
    journal: dict[str, Any],
    current_witness: dict[str, Any],
    *,
    allow_witness_rebind: bool,
) -> dict[str, Any]:
    runtime_identities = journal.get("runtime_identities")
    original_witness = (
        runtime_identities.get("filesystem_witness")
        if isinstance(runtime_identities, dict)
        else None
    )
    if original_witness == current_witness:
        return {}
    if not allow_witness_rebind:
        raise ContinuityError(
            "Pending transaction filesystem witness differs from the locked workspace",
            "filesystem_identity_changed",
        )
    return {
        "filesystem_witness_rebound": True,
        "original_filesystem_witness": original_witness,
        "recovery_filesystem_witness": current_witness,
        "filesystem_witness_rebound_at": utc_now(),
    }


def _recover_committed(
    root: Path,
    journal_path: Path,
    manifest: dict[str, Any],
    journal: dict[str, Any],
    recovery_witness_updates: dict[str, Any] | None = None,
) -> str:
    _committed_evidence(root, manifest, journal)
    current = journal
    witness_updates = dict(recovery_witness_updates or {})
    if current.get("state") != "committed":
        # A visible manifest with only commit_ready evidence may follow a crash after a
        # confirmed replace or an exception after visibility but before durability was
        # confirmed. Republish the verified bytes through the qualified write-through
        # path before treating the manifest as authoritative recovery evidence.
        try:
            atomic_json(root / "manifest.json", manifest)
            _fsync_directory(root)
        except OSError as exc:
            raise ContinuityError(
                "Recovery manifest republication durability is unconfirmed",
                "manifest_durability_uncertain",
            ) from exc
        republished_manifest, _ = open_snapshot(root)
        _committed_evidence(root, republished_manifest, journal)
        witness_updates["recovery_manifest_republished"] = True
        current = _journal_transition(
            journal_path,
            "committed",
            recovery=True,
            recovery_disposition="manifest_commit_authoritative",
            recovered_at=utc_now(),
            **witness_updates,
        )
    if current.get("state") != "finalized":
        _journal_transition(
            journal_path,
            "finalized",
            recovery=True,
            recovery_disposition="manifest_commit_authoritative",
            finalized_at=utc_now(),
            **witness_updates,
        )
    return str(journal.get("transaction_id") or journal.get("id"))


def _recover_uncommitted(
    root: Path,
    journal_path: Path,
    manifest: dict[str, Any],
    journal: dict[str, Any],
    recovery_witness_updates: dict[str, Any] | None = None,
) -> str:
    if journal.get("state") == "recovery_required":
        raise ContinuityError("A recovery_required transaction requires human disposition", "recovery_required")
    transaction_id = str(journal.get("transaction_id") or journal.get("id"))
    staged, final, manifest_next = _journal_artifacts(root, journal)
    transaction_root = root / "transactions" / transaction_id
    # Complete any source-parent sync left uncertain by an already-visible
    # cross-parent publication before classifying or moving its result.
    relevant_parents = {
        transaction_root.parent,
        transaction_root,
        staged.parent,
        final.parent,
        manifest_next.parent,
        root / "quarantine",
    }
    for parent in relevant_parents:
        if not os.path.lexists(parent):
            continue
        try:
            _fsync_directory(parent)
        except OSError as exc:
            raise ContinuityError(
                "Recovery could not confirm transaction parent durability",
                "recovery_required",
            ) from exc
    intent_value = journal.get("intent_construction_path")
    if isinstance(intent_value, str):
        intent_relative = Path(intent_value)
        if intent_relative.is_absolute() or any(part in {"", ".", ".."} for part in intent_relative.parts):
            raise ContinuityError("Intent construction path is invalid", "recovery_required")
        intent_source = root / intent_relative
        if _has_reparse_component(intent_source, root):
            raise ContinuityError("Intent construction path is indirect", "recovery_required")
        if os.path.lexists(intent_source):
            _mark_recovery_required(journal_path, "duplicate_intent_publication")
            raise ContinuityError(
                "Both published and construction transaction intents are present",
                "recovery_required",
            )
    quarantined: list[str] = []
    item = _quarantine_path(root, staged, transaction_id, "staged")
    if item:
        quarantined.append(item)
    if final != generation_path(root, manifest):
        item = _quarantine_path(root, final, transaction_id, "published")
        if item:
            quarantined.append(item)
    if os.path.lexists(manifest_next):
        try:
            candidate = _read_json_path(manifest_next)
        except ContinuityError as exc:
            _mark_recovery_required(journal_path, "manifest_next_not_direct_or_valid")
            raise ContinuityError(
                "manifest.next is present but cannot be attributed to this transaction",
                "recovery_required",
            ) from exc
        if candidate.get("committing_transaction_id") != transaction_id:
            _mark_recovery_required(journal_path, "manifest_next_transaction_mismatch")
            raise ContinuityError(
                "manifest.next belongs to another or unidentified transaction",
                "recovery_required",
            )
        item = _quarantine_path(root, manifest_next, transaction_id, "manifest-next")
        if item:
            quarantined.append(item)
    _journal_transition(
        journal_path,
        "aborted",
        recovery=True,
        recovery_disposition="uncommitted_preserved_prior",
        quarantined=quarantined,
        aborted_at=utc_now(),
        **dict(recovery_witness_updates or {}),
    )
    return transaction_id


def _mark_recovery_required(journal_path: Path, reason: str) -> None:
    try:
        _journal_transition(journal_path, "recovery_required", recovery=True, recovery_disposition=reason)
    except ContinuityError:
        pass


def _recover_transactions_locked(
    root: Path,
    current_witness: dict[str, Any],
    *,
    allow_witness_rebind: bool,
) -> list[str]:
    directories = pending_transactions(root)
    if not directories:
        return []
    manifest, _ = open_snapshot(root)
    parsed: list[tuple[Path, dict[str, Any], dict[str, Any]]] = []
    for directory in directories:
        path = directory / "journal.json"
        if not path.is_file():
            raise ContinuityError(f"Transaction directory lacks journal: {directory.name}", "recovery_required")
        journal = _read_json_path(path)
        if not isinstance(journal, dict) or journal.get("format") != TRANSACTION_FORMAT:
            raise ContinuityError(f"Invalid transaction journal: {directory.name}", "recovery_required")
        if journal.get("state") == "recovery_required":
            raise ContinuityError("A recovery_required transaction requires human disposition", "recovery_required")
        witness_updates = _recovery_witness_updates(
            journal,
            current_witness,
            allow_witness_rebind=allow_witness_rebind,
        )
        if str(journal.get("transaction_id") or journal.get("id")) != directory.name:
            _mark_recovery_required(path, "journal_directory_identity_mismatch")
            raise ContinuityError("Transaction identity and directory disagree", "recovery_required")
        parsed.append((path, journal, witness_updates))
    active_transaction = manifest.get("committing_transaction_id")
    matching = [
        (path, journal, witness_updates)
        for path, journal, witness_updates in parsed
        if str(journal.get("transaction_id") or journal.get("id")) == active_transaction
    ]
    if len(parsed) > 1 and len(matching) != 1:
        for path, _, _ in parsed:
            _mark_recovery_required(path, "multiple_unfinished_ambiguous")
        raise ContinuityError("Multiple unfinished journals cannot be reconciled unambiguously", "recovery_required")
    recovered: list[str] = []
    if matching:
        path, journal, witness_updates = matching[0]
        try:
            recovered.append(
                _recover_committed(root, path, manifest, journal, witness_updates)
            )
        except ContinuityError:
            _mark_recovery_required(path, "manifest_or_bundle_evidence_disagrees")
            raise
    for path, journal, witness_updates in parsed:
        transaction_id = str(journal.get("transaction_id") or journal.get("id"))
        if transaction_id == active_transaction:
            continue
        expected = journal.get("expected_generation")
        new_generation = journal.get("new_generation")
        final_value = journal.get("final_generation_path")
        active_path = manifest.get("active_generation_path")
        provably_uncommitted = (
            isinstance(expected, int)
            and isinstance(new_generation, int)
            and expected == manifest.get("generation")
            and new_generation == int(expected) + 1
            and final_value != active_path
        )
        if not provably_uncommitted:
            _mark_recovery_required(path, "uncommitted_status_not_provable")
            raise ContinuityError("Unfinished transaction is not safely classifiable", "recovery_required")
        recovered.append(
            _recover_uncommitted(root, path, manifest, journal, witness_updates)
        )
    return recovered


def recover_transactions(
    root: Path,
    *,
    lock_timeout: float = 0.0,
    selector: ResolutionToken | None = None,
    include_generation_interval: bool = False,
) -> list[str] | tuple[list[str], int, int]:
    lexical_root = Path(selector.selected_lexical) if selector is not None else root
    with workspace_lock(
        root,
        lock_timeout,
        transaction_id="recovery",
        lexical_root=lexical_root,
    ) as lock_owner:
        locked_witness = dict(lock_owner["filesystem_witness"])
        if selector is not None:
            revalidate_resolution(selector, root)
        current_witness = _filesystem_qualification_witness(
            root,
            lexical_root=lexical_root,
            perform_capability_probe=False,
        )
        if current_witness != locked_witness:
            raise ContinuityError(
                "Filesystem identity changed before recovery",
                "filesystem_identity_changed",
            )
        generation_before = int(open_snapshot(root)[0]["generation"])
        recovered = _recover_transactions_locked(
            root,
            locked_witness,
            allow_witness_rebind=True,
        )
        generation_after = int(open_snapshot(root)[0]["generation"])
        if include_generation_interval:
            return recovered, generation_before, generation_after
        return recovered

def request_digest(operation: str, payload: Any) -> str:
    return sha256_bytes(dump_canonical({"operation": operation, "payload": payload}).encode("utf-8"))

def normalize_idempotency_key(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    raw = str(value).strip()
    if len(raw) == 67 and raw.startswith("IK-") and all(character in "0123456789abcdef" for character in raw[3:]):
        return raw
    if contains_secret_data(raw):
        raise ContinuityError("Idempotency key failed redaction policy", "redaction_rejected")
    return "IK-" + sha256_bytes(raw.encode("utf-8"))

def _active_idempotency(root: Path) -> list[dict[str, Any]]:
    manifest, _ = open_snapshot(root)
    return _read_jsonl_path(generation_path(root, manifest) / "idempotency.jsonl")

def find_idempotent_receipt(root: Path, idempotency_key: str | None, digest: str | None, operation: str | None = None) -> dict[str, Any] | None:
    idempotency_key = normalize_idempotency_key(idempotency_key)
    if not idempotency_key:
        return None
    manifest = _read_json_path(root / "manifest.json")
    if manifest.get("format") != FORMAT:
        return None
    for entry in _active_idempotency(root):
        if entry.get("idempotency_key") != idempotency_key:
            continue
        if operation is not None and entry.get("operation_family") != operation:
            continue
        if entry.get("payload_digest") != digest:
            raise ContinuityError("Idempotency key was already committed with another payload", "idempotency_collision")
        result = entry.get("result")
        if not isinstance(result, dict) or sha256_bytes(dump_canonical(result).encode("utf-8")) != entry.get("result_digest"):
            raise ContinuityError("Stored idempotency result is corrupt", "recovery_required")
        duplicate = dict(result)
        duplicate["status"] = "duplicate_committed"
        return duplicate
    return None
def _replace_manifest(
    source: Path,
    destination: Path,
    *,
    platform_name: str | None = None,
    full_fsync_operation: Any | None = None,
    replace_operation: Any | None = None,
    directory_sync: Any | None = None,
) -> str:
    if source.parent.resolve() != destination.parent.resolve():
        raise ContinuityError("Manifest commit must remain in one directory", "filesystem_semantics_unsupported")
    observed_platform = platform_name or sys.platform
    if observed_platform == "win32":
        MOVEFILE_REPLACE_EXISTING = 0x1
        MOVEFILE_WRITE_THROUGH = 0x8
        ok = ctypes.windll.kernel32.MoveFileExW(str(source), str(destination), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)
        if not ok:
            raise ctypes.WinError(ctypes.windll.kernel32.GetLastError())
        return "windows-MoveFileExW-replace-write-through/v1"
    full_fsync = False
    if observed_platform == "darwin":
        descriptor = os.open(str(source), os.O_RDWR)
        try:
            os.fsync(descriptor)
            full_fsync = (full_fsync_operation or _darwin_full_fsync)(descriptor)
        finally:
            os.close(descriptor)
    (replace_operation or os.replace)(source, destination)
    (directory_sync or _fsync_directory)(destination.parent)
    if observed_platform == "darwin":
        strength = "F_FULLFSYNC" if full_fsync else "fsync-fallback"
        return f"darwin-{strength}-rename-parent-fsync/v1"
    return "posix-rename-parent-fsync/v1"

def _row_count(value: bytes) -> int:
    if not value:
        return 0
    return sum(1 for line in value.splitlines() if line.strip())

LEGACY_OVERSIZE_CONTENT_MAX_CHARACTERS = 16384
LEGACY_OVERSIZE_CONTENT_MAX_UTF8_BYTES = 65536


def legacy_content_provenance_errors(row: dict[str, Any]) -> list[str]:
    provenance = row.get("legacy_content_provenance")
    if provenance is None:
        return []
    if not isinstance(provenance, dict):
        return ["legacy content provenance is not an object"]
    content = row.get("content")
    if not isinstance(content, str):
        return ["legacy content provenance requires string content"]
    content_bytes = content.encode("utf-8")
    errors: list[str] = []
    if provenance.get("policy") != "legacy-v1-lossless-oversize-content/v1":
        errors.append("legacy content provenance policy mismatch")
    if len(content) <= 1000:
        errors.append("legacy content provenance is present on non-oversize content")
    if len(content) > LEGACY_OVERSIZE_CONTENT_MAX_CHARACTERS:
        errors.append("legacy content exceeds the migration character ceiling")
    if len(content_bytes) > LEGACY_OVERSIZE_CONTENT_MAX_UTF8_BYTES:
        errors.append("legacy content exceeds the migration byte ceiling")
    if provenance.get("source_characters") != len(content):
        errors.append("legacy content provenance character count mismatch")
    if provenance.get("source_utf8_bytes") != len(content_bytes):
        errors.append("legacy content provenance byte count mismatch")
    if provenance.get("source_content_sha256") != sha256_bytes(content_bytes):
        errors.append("legacy content provenance digest mismatch")
    return errors


def legacy_content_transformations(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "member": "episodes.jsonl",
            "row": index,
            "row_id": str(row.get("id") or ""),
            "provenance": row["legacy_content_provenance"],
        }
        for index, row in enumerate(episodes)
        if "legacy_content_provenance" in row
    ]


def _legacy_content_provenance_map(episodes: list[dict[str, Any]]) -> dict[str, str]:
    return {
        str(row.get("id") or ""): dump_canonical(row)
        for row in episodes
        if "legacy_content_provenance" in row
    }


def _validate_initial_legacy_content_binding(
    manifest: dict[str, Any], rows: dict[str, list[dict[str, Any]]], operation: str,
) -> None:
    transformations = legacy_content_transformations(rows["episodes.jsonl"])
    if transformations and operation != "migrate-copy":
        raise ContinuityError("Only copy migration may create legacy content provenance", "workspace_invalid")
    if operation != "migrate-copy":
        return
    migrated_from = manifest.get("migrated_from") or {}
    digest = sha256_bytes(dump_canonical(transformations).encode("utf-8"))
    if migrated_from.get("legacy_oversize_content_provenance_count") != len(transformations):
        raise ContinuityError("Migration manifest legacy content count mismatch", "workspace_invalid")
    if migrated_from.get("legacy_oversize_content_provenance_sha256") != digest:
        raise ContinuityError("Migration manifest legacy content digest mismatch", "workspace_invalid")
    receipts = [row for row in rows["receipts.jsonl"] if row.get("operation") == "migrate-copy"]
    if len(receipts) != 1:
        raise ContinuityError("Migration legacy content provenance requires one canonical receipt", "workspace_invalid")
    receipt = receipts[0]
    mapping = receipt.get("mapping") or {}
    if mapping.get("lossless_oversize_content_rows") != len(transformations):
        raise ContinuityError("Migration receipt legacy content count mismatch", "workspace_invalid")
    if receipt.get("legacy_oversize_content_provenance_sha256") != digest:
        raise ContinuityError("Migration receipt legacy content digest mismatch", "workspace_invalid")


def _validate_legacy_content_transition(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    operation: str,
    *,
    restore_source: list[dict[str, Any]] | None = None,
) -> None:
    before_map = _legacy_content_provenance_map(before)
    after_map = _legacy_content_provenance_map(after)
    if operation == "forget":
        invalid = {key: value for key, value in after_map.items() if before_map.get(key) != value}
        if invalid:
            raise ContinuityError("Forget may only remove unchanged legacy content provenance", "workspace_invalid")
        return
    if operation == "restore-forget":
        if restore_source is None or after_map != _legacy_content_provenance_map(restore_source):
            raise ContinuityError("Forget restore legacy content provenance does not match the retained predecessor", "workspace_invalid")
        return
    if after_map != before_map:
        raise ContinuityError("Legacy content provenance is immutable outside governed forget and restore", "workspace_invalid")


def _validate_bundle_rows(rows: dict[str, list[dict[str, Any]]]) -> None:
    catalog = SchemaCatalog(Path(__file__).resolve().parents[1] / "assets" / "schemas")
    schemas = {
        "episodes.jsonl": "episode-v2.schema.json", "state.jsonl": "state-record-v2.schema.json",
        "proposals.jsonl": "proposal-v2.schema.json", "receipts.jsonl": "receipt-v2.schema.json",
        "idempotency.jsonl": "idempotency-v1.schema.json",
    }
    for member, values in rows.items():
        if not isinstance(values, list) or any(not isinstance(row, dict) for row in values):
            raise ContinuityError(f"Invalid rows staged for {member}", "workspace_invalid")
        for index, row in enumerate(values):
            if contains_secret_data(row):
                raise ContinuityError(f"Secret-bearing row rejected before intent: {member}:{index}", "redaction_rejected")
            errors = catalog.validate(row, schemas[member])
            if member == "episodes.jsonl":
                errors.extend(legacy_content_provenance_errors(row))
            if errors:
                raise ContinuityError(f"Schema-invalid row rejected before intent: {member}:{index}: {'; '.join(errors[:4])}", "workspace_invalid")
        identities = (
            [[row.get("operation_family"), row.get("idempotency_key")] for row in values]
            if member == "idempotency.jsonl"
            else [row.get("id") for row in values if row.get("id") is not None]
        )
        if len(identities) != len(set(dump_canonical(item) for item in identities)):
            raise ContinuityError(f"Duplicate row identity in {member}", "workspace_invalid")
    receipts = {row.get("id"): row for row in rows["receipts.jsonl"]}
    for entry in rows["idempotency.jsonl"]:
        receipt_id = entry.get("receipt_id")
        if receipt_id not in receipts:
            raise ContinuityError("Idempotency entry references an absent receipt", "workspace_invalid")
        result = entry.get("result")
        if not isinstance(result, dict) or sha256_bytes(dump_canonical(result).encode("utf-8")) != entry.get("result_digest"):
            raise ContinuityError("Idempotency result digest is invalid", "workspace_invalid")

class WorkspaceTransaction:
    """One immutable-generation Continuity mutation under the OS-exclusive lock."""
    def __init__(
        self,
        root: Path,
        operation: str,
        expected_generation: int | None,
        selector: str,
        *,
        authority: str,
        idempotency_key: str | None,
        request_digest_value: str,
        request_payload: Any,
        source_ids: Iterable[str],
        lock_timeout: float,
    ):
        self.root = root.resolve()
        self.operation = operation
        self.expected_generation = expected_generation
        self.resolution_token = selector if isinstance(selector, ResolutionToken) else None
        self.selector = str(selector)
        self.authority = authority
        self.public_idempotency_key = normalize_idempotency_key(idempotency_key)
        self.request_digest = request_digest_value
        self.request_payload = request_payload
        self.source_ids = sorted(set(str(value) for value in source_ids))
        self.lock_timeout = lock_timeout
        self.id = new_id("TX")
        self.operation_id = new_id("OP")
        self.idempotency_key = str(self.public_idempotency_key)
        self.transaction_root = self.root / "transactions" / self.id
        self.journal_path = self.transaction_root / "journal.json"
        self.lock_context: Any = None
        self.manifest_before: dict[str, Any] = {}
        self.metadata_before: dict[str, Any] = {}
        self.generation_before = -1
        self.generation_after = -1
        self.active_bundle: Path | None = None
        self.staged_members: dict[str, bytes] = {}
        self.finished = False
        self.entered = False
        self.adapter: str | None = None
        self.filesystem_witness: dict[str, Any] | None = None
        self.manifest_publication_attempted = False
        self.manifest_publication_confirmed = False

    def __enter__(self) -> "WorkspaceTransaction":
        # Complete read-only generation/idempotency checks before lock acquisition.
        lexical_root = Path(self.resolution_token.selected_lexical) if self.resolution_token else self.root
        pre_manifest, _ = open_snapshot(self.root)
        observed_generation = int(pre_manifest["generation"])
        if self.expected_generation != observed_generation:
            raise ContinuityError(f"Expected generation {self.expected_generation}, observed {observed_generation}", "generation_conflict")
        duplicate = find_idempotent_receipt(self.root, self.public_idempotency_key, self.request_digest, self.operation)
        if duplicate is not None:
            raise IdempotentReplay(duplicate)
        self.lock_context = workspace_lock(
            self.root,
            self.lock_timeout,
            transaction_id=self.id,
            lexical_root=lexical_root,
        )
        lock_owner = self.lock_context.__enter__()
        self.filesystem_witness = dict(lock_owner["filesystem_witness"])
        self.adapter = str(self.filesystem_witness["adapter"])
        try:
            if self.resolution_token is not None:
                revalidate_resolution(self.resolution_token, self.root)
            self._assert_filesystem_witness("Filesystem identity changed before transaction entry")
            _recover_transactions_locked(
                self.root,
                self.filesystem_witness,
                allow_witness_rebind=False,
            )
            self.manifest_before, self.metadata_before = open_snapshot(self.root)
            self.generation_before = int(self.manifest_before["generation"])
            self.generation_after = self.generation_before + 1
            self.active_bundle = generation_path(self.root, self.manifest_before)
            if self.expected_generation != self.generation_before:
                raise ContinuityError(f"Expected generation {self.expected_generation}, observed {self.generation_before}", "generation_conflict")
            duplicate = find_idempotent_receipt(self.root, self.public_idempotency_key, self.request_digest, self.operation)
            if duplicate is not None:
                raise IdempotentReplay(duplicate)
            for entry in _active_idempotency(self.root):
                if entry.get("operation_family") == self.operation and entry.get("idempotency_key") == self.public_idempotency_key:
                    raise ContinuityError("Idempotency key payload collision", "idempotency_collision")
            self.entered = True
            return self
        except BaseException:
            self.lock_context.__exit__(*sys.exc_info())
            self.lock_context = None
            raise

    def _assert_filesystem_witness(self, message: str) -> None:
        try:
            current = _filesystem_qualification_witness(
                self.root,
                lexical_root=Path(self.resolution_token.selected_lexical) if self.resolution_token else self.root,
                perform_capability_probe=False,
            )
        except (ContinuityError, OSError) as exc:
            raise ContinuityError(message, "filesystem_identity_changed") from exc
        if current != self.filesystem_witness:
            raise ContinuityError(message, "filesystem_identity_changed")
    def _record_intent(self) -> None:
        if self.journal_path.exists() or not self.entered or self.adapter is None:
            raise ContinuityError("Transaction intent state is invalid", "internal_unclassified")
        self._assert_filesystem_witness("Filesystem identity changed before transaction intent")
        _crash("before_intent")
        intent_root = self.root / "quarantine" / f".{self.id}-intent-{uuid.uuid4().hex}"
        try:
            generation_directory = f"g-{self.generation_after:020d}"
            scope = self.request_payload.get("scope") if isinstance(self.request_payload, dict) else None
            intent = {
                "format": TRANSACTION_FORMAT,
                "transaction_id": self.id,
                "id": self.id,
                "state": "intent_recorded",
                "sequence": 0,
                "prior_state_digest": None,
                "recorded_at": utc_now(),
                "workspace_id": self.manifest_before.get("workspace_id"),
                "operation_family": self.operation,
                "operation_schema_version": "v1",
                "authority_grant_id": self.authority,
                "scope": scope,
                "operation_id": self.operation_id,
                "idempotency_key": self.idempotency_key,
                "caller_idempotency_key": self.public_idempotency_key,
                "payload_digest": self.request_digest,
                "source_evidence_ids": self.source_ids,
                "policy_identities": {
                    "transaction": "cd-continuity-file-transaction/v1",
                    "eligibility": (self.manifest_before.get("policies") or {}).get("eligibility_policy"),
                    "redaction": (self.manifest_before.get("policies") or {}).get("redaction_policy"),
                },
                "runtime_identities": {
                    "implementation_version": IMPLEMENTATION_VERSION,
                    "python": sys.version.split()[0],
                    "platform": sys.platform,
                    "adapter": self.adapter,
                    "filesystem_witness": self.filesystem_witness,
                },
                "expected_generation": self.generation_before,
                "new_generation": self.generation_after,
                "previous_manifest_digest": sha256_file(self.root / "manifest.json"),
                "previous_generation_manifest_digest": self.manifest_before.get("active_generation_manifest_sha256"),
                "generation_directory": generation_directory,
                "staged_generation_path": f"transactions/{self.id}/stage/{generation_directory}",
                "final_generation_path": f"generations/{generation_directory}",
                "planned_artifacts": [*MEMBERS, "generation.json", "manifest.next"],
                "intent_construction_path": intent_root.relative_to(self.root).as_posix(),
            }
            intent_root.mkdir(parents=False, exist_ok=False)
            atomic_json(intent_root / "journal.json", intent)
            _fsync_directory(intent_root)
            _publish_directory(intent_root, self.transaction_root)
        except BaseException:
            if intent_root.exists():
                shutil.rmtree(intent_root, ignore_errors=True)
                _fsync_directory(intent_root.parent)
            if self.transaction_root.is_dir() and not any(self.transaction_root.iterdir()):
                self.transaction_root.rmdir()
                _fsync_directory(self.transaction_root.parent)
            raise
        _crash("after_intent")
    def _member_for(self, path: Path) -> str:
        logical = _logical_member(path)
        if logical is None or logical[0].resolve() != self.root:
            raise ContinuityError("Canonical v2 transaction targets must be logical ledgers", "protected_target_denied")
        return logical[1]

    def write_jsonl(self, path: Path, rows: Iterable[dict[str, Any]]) -> None:
        member = self._member_for(path)
        self.staged_members[member] = encode_jsonl(list(rows))

    def write_member(self, member: str, rows: Iterable[dict[str, Any]]) -> None:
        if member not in MEMBERS:
            raise ContinuityError("Unknown canonical generation member", "protected_target_denied")
        self.staged_members[member] = encode_jsonl(list(rows))

    def write_json(self, path: Path, value: Any) -> None:
        raise ContinuityError("Non-ledger writes require an external lifecycle adapter", "operation_requires_external_lifecycle_adapter")

    def write_bytes(self, path: Path, value: bytes) -> None:
        raise ContinuityError("Non-ledger writes require an external lifecycle adapter", "operation_requires_external_lifecycle_adapter")

    def delete(self, path: Path) -> None:
        raise ContinuityError("In-place deletion is forbidden by the immutable-generation contract", "operation_requires_external_lifecycle_adapter")

    def maybe_fail(self, point: str) -> None:
        _crash(point)

    def _member_rows(self) -> dict[str, list[dict[str, Any]]]:
        if self.active_bundle is None:
            raise ContinuityError("Transaction has no active predecessor", "internal_unclassified")
        rows: dict[str, list[dict[str, Any]]] = {}
        for member in MEMBERS:
            value = self.staged_members.get(member)
            if value is None:
                value = (self.active_bundle / member).read_bytes()
            try:
                decoded = value.decode("utf-8")
                parsed: list[dict[str, Any]] = []
                for line in decoded.splitlines():
                    if line.strip():
                        row = _loads(line)
                        if not isinstance(row, dict):
                            raise ValueError("row is not an object")
                        parsed.append(row)
                rows[member] = parsed
            except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
                raise ContinuityError(f"Staged member is invalid: {member}: {exc}", "workspace_invalid") from exc
        return rows
    def finish(self, receipt_kind: str, details: dict[str, Any]) -> dict[str, Any]:
        if self.finished or not self.entered or self.active_bundle is None:
            raise ContinuityError("Transaction is not in a finishable state", "internal_unclassified")
        rows = self._member_rows()
        now = utc_now()
        receipt = {
            **details,
            "format": RECEIPT_FORMAT,
            "id": new_id("RC"),
            "kind": receipt_kind,
            "status": "committed",
            "at": now,
            "workspace_id": self.manifest_before["workspace_id"],
            "workspace_selector": self.selector,
            "transaction_id": self.id,
            "operation": self.operation,
            "operation_id": self.operation_id,
            "authority": self.authority,
            "idempotency_key": self.idempotency_key,
            "caller_idempotency_key": self.public_idempotency_key,
            "request_digest": self.request_digest,
            "source_evidence_ids": self.source_ids,
            "generation_before": self.generation_before,
            "generation_after": self.generation_after,
            "affected_members": sorted(self.staged_members),
        }
        rows["receipts.jsonl"].append(receipt)
        restore_source: list[dict[str, Any]] | None = None
        if self.operation == "restore-forget":
            active_metadata = _read_json_path(self.active_bundle / "generation.json")
            predecessor = active_metadata.get("predecessor_generation")
            if active_metadata.get("operation_family") != "forget" or predecessor != self.generation_before - 1:
                raise ContinuityError("Forget restore lacks an exact retained predecessor", "restore_generation_conflict")
            predecessor_path = self.root / "generations" / f"g-{int(predecessor):020d}" / "episodes.jsonl"
            restore_source = _read_jsonl_path(predecessor_path)
        _validate_legacy_content_transition(
            _read_jsonl_path(self.active_bundle / "episodes.jsonl"),
            rows["episodes.jsonl"],
            self.operation,
            restore_source=restore_source,
        )
        result_digest = sha256_bytes(dump_canonical(receipt).encode("utf-8"))
        idempotency_entry = {
            "format": "cd-continuity-idempotency/v1",
            "workspace_id": self.manifest_before["workspace_id"],
            "operation_family": self.operation,
            "idempotency_key": self.idempotency_key,
            "caller_idempotency_key": self.public_idempotency_key,
            "payload_digest": self.request_digest,
            "transaction_id": self.id,
            "prior_generation": self.generation_before,
            "new_generation": self.generation_after,
            "receipt_id": receipt["id"],
            "status": "committed",
            "result": receipt,
            "result_digest": result_digest,
            "committed_at": now,
        }
        rows["idempotency.jsonl"].append(idempotency_entry)
        _validate_bundle_rows(rows)
        encoded = {member: encode_jsonl(rows[member]) for member in MEMBERS}
        self._record_intent()
        stage = self.root / "transactions" / self.id / "stage" / f"g-{self.generation_after:020d}"
        final = self.root / "generations" / f"g-{self.generation_after:020d}"
        if stage.exists() or final.exists():
            raise ContinuityError("Next generation path already exists", "recovery_required")
        _crash("before_bundle_files")
        stage.mkdir(parents=True, exist_ok=False)
        member_metadata: dict[str, Any] = {}
        for member in MEMBERS:
            _crash(f"before_member_{member.replace('.', '_')}")
            path = stage / member
            _write_new(path, encoded[member])
            member_metadata[member] = {"sha256": sha256_bytes(encoded[member]), "bytes": len(encoded[member]), "rows": _row_count(encoded[member])}
            _crash(f"after_member_{member.replace('.', '_')}")
        generation_metadata = {
            "format": GENERATION_FORMAT,
            "workspace_id": self.manifest_before["workspace_id"],
            "generation": self.generation_after,
            "created_at": now,
            "transaction_id": self.id,
            "operation_family": self.operation,
            "predecessor_generation": self.generation_before,
            "predecessor_generation_manifest_sha256": self.manifest_before.get("active_generation_manifest_sha256"),
            "schemas": {
                "episodes.jsonl": "episode-v2.schema.json",
                "state.jsonl": "state-record-v2.schema.json",
                "proposals.jsonl": "proposal-v2.schema.json",
                "receipts.jsonl": "receipt-v2.schema.json",
                "idempotency.jsonl": "cd-continuity-idempotency/v1",
            },
            "members": member_metadata,
        }
        _crash("before_generation_manifest")
        _write_new(stage / "generation.json", (json.dumps(generation_metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
        generation_digest = sha256_file(stage / "generation.json")
        _fsync_directory(stage)
        _crash("after_generation_manifest")
        _crash("before_bundle_staged")
        _journal_transition(self.journal_path, "bundle_staged", generation_manifest_sha256=generation_digest, member_metadata=member_metadata)
        _crash("after_bundle_staged")
        _crash("before_bundle_publish")
        self._assert_filesystem_witness("Filesystem identity changed before generation publication")
        if not final.parent.is_dir():
            raise ContinuityError(
                "Generation custody directory disappeared before publication",
                "filesystem_identity_changed",
            )
        if final.exists():
            raise ContinuityError("Published generation destination already exists", "recovery_required")
        _publish_directory(stage, final)
        _crash("after_bundle_publish")
        _crash("before_bundle_published")
        _journal_transition(self.journal_path, "bundle_published", published_generation_manifest_sha256=generation_digest)
        _crash("after_bundle_published")
        manifest_next_path = self.root / "manifest.next"
        if manifest_next_path.exists():
            raise ContinuityError("An unresolved manifest.next blocks mutation", "recovery_required")
        manifest_next = dict(self.manifest_before)
        manifest_next.update({
            "format": FORMAT,
            "implementation_version": IMPLEMENTATION_VERSION,
            "workspace_schema_version": 2,
            "updated_at": utc_now(),
            "generation": self.generation_after,
            "active_generation_path": final.relative_to(self.root).as_posix(),
            "active_generation_manifest_sha256": generation_digest,
            "committing_transaction_id": self.id,
            "previous_generation": self.generation_before,
            "previous_generation_manifest_sha256": self.manifest_before.get("active_generation_manifest_sha256"),
            "transaction_protocol": "cd-continuity-file-transaction/v1",
        })
        _crash("before_manifest_next")
        _write_new(manifest_next_path, (json.dumps(manifest_next, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
        _crash("after_manifest_next")
        _crash("before_commit_ready")
        _journal_transition(self.journal_path, "commit_ready", manifest_next_sha256=sha256_file(manifest_next_path), next_manifest_generation=self.generation_after)
        _crash("after_commit_ready")
        _crash("before_manifest_commit")
        self._assert_filesystem_witness("Filesystem identity changed before manifest publication")
        self.manifest_publication_attempted = True
        try:
            adapter = _replace_manifest(manifest_next_path, self.root / "manifest.json")
        except OSError as exc:
            raise ContinuityError(
                "Manifest publication became visible or failed before durability could be confirmed; explicit recovery is required",
                "manifest_durability_uncertain",
            ) from exc
        self.manifest_publication_confirmed = True
        _crash("after_manifest_commit")
        committed_manifest, _ = open_snapshot(self.root)
        if committed_manifest.get("committing_transaction_id") != self.id:
            raise ContinuityError("Manifest commit verification disagrees", "recovery_required")
        _committed_evidence(self.root, committed_manifest, _read_json_path(self.journal_path))
        _crash("before_committed")
        _journal_transition(self.journal_path, "committed", commit_adapter=adapter, committed_at=utc_now(), committed_manifest_sha256=sha256_file(self.root / "manifest.json"))
        _crash("after_committed")
        _crash("before_finalized")
        _journal_transition(self.journal_path, "finalized", finalized_at=utc_now())
        _crash("after_finalized")
        self.finished = True
        return receipt

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        try:
            identity_changed = isinstance(exc, ContinuityError) and exc.code == "filesystem_identity_changed"
            publication_uncertain = (
                self.manifest_publication_attempted
                and not self.manifest_publication_confirmed
            )
            if publication_uncertain and exc is None:
                raise ContinuityError(
                    "Manifest durability is unconfirmed; explicit recovery is required",
                    "manifest_durability_uncertain",
                )
            if (
                self.entered
                and not self.finished
                and self.journal_path.is_file()
                and not identity_changed
                and not publication_uncertain
            ):
                self._assert_filesystem_witness(
                    "Filesystem identity changed before automatic exit recovery"
                )
                manifest, _ = open_snapshot(self.root)
                journal = _read_json_path(self.journal_path)
                if manifest.get("committing_transaction_id") == self.id and manifest.get("generation") == self.generation_after:
                    _recover_committed(self.root, self.journal_path, manifest, journal)
                    self.finished = True
                elif manifest.get("generation") == self.generation_before:
                    _recover_uncommitted(self.root, self.journal_path, manifest, journal)
                else:
                    _mark_recovery_required(self.journal_path, "exit_state_uncertain")
                    raise ContinuityError("Transaction exit cannot classify durable state", "recovery_required")
        finally:
            if self.lock_context is not None:
                self.lock_context.__exit__(exc_type, exc, traceback)
                self.lock_context = None
        return False

def transaction(
    root: Path,
    operation: str,
    *,
    expected_generation: int | None = None,
    selector: str = "generic_explicit",
    authority: str = "",
    idempotency_key: str | None = None,
    request_payload: Any = None,
    source_ids: Iterable[str] = (),
    lock_timeout: float | None = None,
) -> WorkspaceTransaction:
    if expected_generation is None or expected_generation < 0:
        raise ContinuityError("Mutation requires explicit non-negative expected_generation", "expected_generation_required")
    if not idempotency_key or not str(idempotency_key).strip():
        raise ContinuityError("Mutation requires explicit idempotency_key", "idempotency_required")
    if not authority or not str(authority).strip():
        raise ContinuityError("Mutation requires explicit authority", "authority_denied")
    payload = {} if request_payload is None else request_payload
    digest = request_digest(operation, payload)
    timeout = float(os.environ.get("CONTINUITY_LOCK_TIMEOUT_SECONDS", "5")) if lock_timeout is None else lock_timeout
    return WorkspaceTransaction(root, operation, expected_generation, selector, authority=str(authority).strip(), idempotency_key=str(idempotency_key).strip(), request_digest_value=digest, request_payload=payload, source_ids=source_ids, lock_timeout=timeout)
# Override the early compatibility helper: logical v2 reads always follow the stable manifest snapshot.
def read_jsonl(path: Path) -> list[dict[str, Any]]:
    logical = _logical_member(path)
    if logical is None:
        return _read_jsonl_path(path)
    root, member = logical
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        return _read_jsonl_path(path)
    manifest = _read_json_path(manifest_path)
    if manifest.get("format") == FORMAT:
        stable, _ = open_snapshot(root)
        return _read_jsonl_path(generation_path(root, stable) / member)
    return _read_jsonl_path(path)
def _directory_identity(path: Path) -> tuple[int, int] | None:
    try:
        metadata = os.stat(path, follow_symlinks=False)
    except OSError:
        return None
    if not stat.S_ISDIR(metadata.st_mode) or int(metadata.st_ino) == 0:
        return None
    return int(metadata.st_dev), int(metadata.st_ino)


def _publish_directory(source: Path, destination: Path) -> str:
    if destination.exists():
        raise ContinuityError("Published directory destination already exists", "recovery_required")
    if int(os.stat(source.parent).st_dev) != int(os.stat(destination.parent).st_dev):
        raise ContinuityError("Directory publication must remain on one filesystem device", "filesystem_semantics_unsupported")
    observed_platform = sys.platform
    try:
        _move_path_write_through(source, destination, replace_existing=False)
    except OSError as exc:
        if exc.errno in {errno.EEXIST, errno.ENOTEMPTY}:
            raise ContinuityError(
                "Published directory destination appeared before the atomic no-clobber rename",
                "recovery_required",
            ) from exc
        if destination.exists() and not source.exists():
            raise ContinuityError(
                "Directory publication is visible but parent durability is unconfirmed",
                "recovery_required",
            ) from exc
        raise ContinuityError(
            "Directory publication failed before visibility",
            "filesystem_semantics_unsupported",
        ) from exc
    if observed_platform == "win32":
        return "windows-MoveFileExW-directory-write-through/v1"
    if observed_platform == "darwin":
        return "darwin-renamex_np-RENAME_EXCL-parent-fsync/v1"
    if observed_platform.startswith("linux"):
        return "linux-renameat2-RENAME_NOREPLACE-parent-fsync/v1"
    raise ContinuityError(
        "Directory publication completed without a supported adapter identity",
        "filesystem_semantics_unsupported",
    )

def _base_manifest(*, workspace_id: str, created_at: str, scope: dict[str, Any], sensitivity: str, retention: str) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "implementation_version": IMPLEMENTATION_VERSION,
        "workspace_schema_version": 2,
        "workspace_id": workspace_id,
        "created_at": created_at,
        "updated_at": created_at,
        "generation": 0,
        "scope": scope,
        "policies": {
            "storage": "local-only",
            "scope_model": "harness-global" if scope.get("project") == "*" else "project",
            "default_sensitivity": sensitivity,
            "default_retention": retention,
            "semantic_retrieval": False,
            "background_consolidation": False,
            "eligibility_policy": "cd-continuity-eligibility/v2",
            "redaction_policy": "cd-fault-redaction/v1",
        },
        "capabilities": {
            "filesystem": True,
            "deterministic_scripts": True,
            "semantic_ranking": False,
            "scheduler": False,
            "selector_default": True,
            "workspace_lock": True,
            "transaction_recovery": True,
            "worldline": True,
            "error_neighborhood": True,
        },
        "last_consolidated_episode": None,
        "transaction_protocol": "cd-continuity-file-transaction/v1",
    }

def _publish_initial_workspace(root: Path, manifest: dict[str, Any], rows: dict[str, list[dict[str, Any]]], transaction_id: str, operation: str) -> None:
    _validate_bundle_rows(rows)
    _validate_initial_legacy_content_binding(manifest, rows, operation)
    generation_root = root / "generations" / "g-00000000000000000000"
    generation_root.mkdir(parents=True, exist_ok=False)
    members: dict[str, Any] = {}
    for name in MEMBERS:
        encoded = encode_jsonl(rows[name])
        _write_new(generation_root / name, encoded)
        members[name] = {"sha256": sha256_bytes(encoded), "bytes": len(encoded), "rows": _row_count(encoded)}
    metadata = {
        "format": GENERATION_FORMAT,
        "workspace_id": manifest["workspace_id"],
        "generation": 0,
        "created_at": manifest["created_at"],
        "transaction_id": transaction_id,
        "operation_family": operation,
        "predecessor_generation": None,
        "predecessor_generation_manifest_sha256": None,
        "schemas": {
            "episodes.jsonl": "episode-v2.schema.json",
            "state.jsonl": "state-record-v2.schema.json",
            "proposals.jsonl": "proposal-v2.schema.json",
            "receipts.jsonl": "receipt-v2.schema.json",
            "idempotency.jsonl": "cd-continuity-idempotency/v1",
        },
        "members": members,
    }
    _write_new(generation_root / "generation.json", (json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    digest = sha256_file(generation_root / "generation.json")
    _fsync_directory(generation_root)
    _fsync_directory(generation_root.parent)
    manifest.update({
        "active_generation_path": "generations/g-00000000000000000000",
        "active_generation_manifest_sha256": digest,
        "committing_transaction_id": transaction_id,
        "previous_generation": None,
        "previous_generation_manifest_sha256": None,
    })
    atomic_json(root / "manifest.json", manifest)
    open_snapshot(root)
    _fsync_directory(root.parent)

def _initial_receipt_and_idempotency(
    manifest: dict[str, Any], *, transaction_id: str, operation: str, kind: str, selector: str,
    authority: str, key: str, request_digest_value: str, details: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    receipt = {
        **details,
        "format": RECEIPT_FORMAT,
        "id": new_id("RC"),
        "kind": kind,
        "status": "committed",
        "at": manifest["created_at"],
        "workspace_id": manifest["workspace_id"],
        "workspace_selector": str(selector),
        "transaction_id": transaction_id,
        "operation": operation,
        "operation_id": new_id("OP"),
        "authority": authority,
        "idempotency_key": key,
        "caller_idempotency_key": key,
        "request_digest": request_digest_value,
        "source_evidence_ids": [],
        "generation_before": -1,
        "generation_after": 0,
        "affected_members": ["episodes.jsonl", "state.jsonl", "proposals.jsonl"],
    }
    result_digest = sha256_bytes(dump_canonical(receipt).encode("utf-8"))
    entry = {
        "format": "cd-continuity-idempotency/v1",
        "workspace_id": manifest["workspace_id"],
        "operation_family": operation,
        "idempotency_key": key,
        "caller_idempotency_key": key,
        "payload_digest": request_digest_value,
        "transaction_id": transaction_id,
        "prior_generation": -1,
        "new_generation": 0,
        "receipt_id": receipt["id"],
        "status": "committed",
        "result": receipt,
        "result_digest": result_digest,
        "committed_at": manifest["created_at"],
    }
    return receipt, entry

def initialize_workspace(
    path_value: str | None,
    *,
    user: str,
    project: str,
    agent: str,
    thread: str | None,
    sensitivity: str,
    retention: str,
) -> tuple[Path, dict[str, Any]]:
    if not path_value:
        raise ContinuityError("Initialization requires an explicit absent target", "protected_target_denied")
    root, selector = select_workspace(path_value, mode="generic_explicit")
    if root.exists():
        raise ContinuityError(f"Initialization target must be absent: {root}", "protected_target_denied")
    if not root.parent.is_dir():
        raise ContinuityError("Initialization requires an existing parent directory", "protected_target_denied")
    _filesystem_adapter(
        root, lexical_root=Path(selector.selected_lexical), workspace_root=True
    )
    construction = root.parent / f".{root.name}.cc-initialize-{uuid.uuid4().hex}"
    construction_identity: tuple[int, int] | None = None
    construction_created = False
    published = False
    try:
        construction.mkdir(exist_ok=False)
        construction_created = True
        construction_identity = _directory_identity(construction)
        if construction_identity is None:
            raise ContinuityError("Initialization construction identity is unavailable", "filesystem_semantics_unsupported")
        for name in ("generations", "transactions", "locks", "quarantine"):
            (construction / name).mkdir(exist_ok=False)
        _write_new(construction / "locks" / "workspace.lock", b"\0")
        _fsync_directory(construction / "locks")
        _filesystem_qualification_witness(construction, lexical_root=construction)
        now = utc_now()
        manifest = _base_manifest(
            workspace_id=new_id("CCW"), created_at=now,
            scope={"user": user, "project": project, "agent": agent, "thread": thread},
            sensitivity=sensitivity, retention=retention,
        )
        transaction_id = new_id("TX")
        key = f"initialize:{manifest['workspace_id']}"
        digest = request_digest("initialize", manifest["scope"])
        receipt, idempotency = _initial_receipt_and_idempotency(
            manifest, transaction_id=transaction_id, operation="initialize", kind="initialized",
            selector=selector, authority="user-authorized-local", key=key, request_digest_value=digest,
            details={"scope": manifest["scope"]},
        )
        rows = {name: [] for name in MEMBERS}
        rows["receipts.jsonl"] = [receipt]
        rows["idempotency.jsonl"] = [idempotency]
        _publish_initial_workspace(construction, manifest, rows, transaction_id, "initialize")
        if root.exists():
            raise ContinuityError("Initialization target appeared before publication", "protected_target_denied")
        _publish_directory(construction, root)
        published = True
        _filesystem_qualification_witness(root, lexical_root=Path(selector.selected_lexical))
        return root, receipt
    except BaseException as exc:
        retained: list[Path] = []
        if construction_created and os.path.lexists(construction):
            retained.append(construction)
        if os.path.lexists(root) and (
            published
            or construction_identity is None
            or _directory_identity(root) == construction_identity
        ):
            retained.append(root)
        if retained:
            names = ", ".join(str(path) for path in dict.fromkeys(retained))
            raise ContinuityError(
                f"Initialization failed without race-unsafe cleanup; retained path(s): {names}",
                "recovery_required",
            ) from exc
        raise
def normalize_legacy_temporal_rows(source_rows: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    fields = {
        "episodes.jsonl": ("valid_from", "valid_to"),
        "state.jsonl": ("valid_from", "valid_to", "expires_at"),
        "proposals.jsonl": (),
    }
    migrated: dict[str, list[dict[str, Any]]] = {}
    transformations: list[dict[str, Any]] = []
    for member, rows in source_rows.items():
        converted: list[dict[str, Any]] = []
        for index, row in enumerate(rows):
            mapped = dict(row)
            for field in fields.get(member, ()):
                value = mapped.get(field)
                if not isinstance(value, str) or len(value) != 10:
                    continue
                try:
                    parsed = datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    continue
                if parsed.strftime("%Y-%m-%d") != value:
                    continue
                mapped[field] = f"{value}T00:00:00Z"
                transformations.append({
                    "member": member, "row": index, "row_id": str(row.get("id") or ""),
                    "field": field, "policy": "legacy-full-date-as-utc-midnight",
                })
            converted.append(mapped)
        migrated[member] = converted
    return migrated, transformations


def annotate_legacy_oversize_content_rows(
    migrated_rows: dict[str, list[dict[str, Any]]],
    source_rows: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    annotated: dict[str, list[dict[str, Any]]] = {}
    transformations: list[dict[str, Any]] = []
    for member, rows in migrated_rows.items():
        converted: list[dict[str, Any]] = []
        for index, row in enumerate(rows):
            mapped = dict(row)
            original = source_rows[member][index]
            content = original.get("content")
            if member == "episodes.jsonl" and isinstance(content, str) and len(content) > 1000:
                content_bytes = content.encode("utf-8")
                provenance = {
                    "policy": "legacy-v1-lossless-oversize-content/v1",
                    "source_row_sha256": sha256_bytes(dump_canonical(original).encode("utf-8")),
                    "source_content_sha256": sha256_bytes(content_bytes),
                    "source_characters": len(content),
                    "source_utf8_bytes": len(content_bytes),
                }
                mapped["legacy_content_provenance"] = provenance
                transformations.append({
                    "member": member,
                    "row": index,
                    "row_id": str(original.get("id") or ""),
                    "provenance": provenance,
                })
            converted.append(mapped)
        annotated[member] = converted
    return annotated, transformations


def migrate_copy(
    source_value: str, destination_value: str, *, authority: str,
    expected_source_tree_sha256: str,
    destination_mode: str = "generic_external",
    grant_id: str | None = None,
    expected_selector_registry_sha256: str | None = None,
    expected_destination_sha256: str | None = None,
) -> dict[str, Any]:
    if not authority or not authority.strip():
        raise ContinuityError("Copy migration requires explicit authority", "authority_denied")
    if contains_secret_data(authority):
        raise ContinuityError("Migration authority identifier failed redaction", "redaction_rejected")
    source = _absolute_local(source_value, "source workspace")
    nova_grant: NovaMigrationGrant | None = None
    if destination_mode == "generic_external":
        if grant_id or expected_selector_registry_sha256 or expected_destination_sha256:
            raise ContinuityError("Generic migration cannot consume a Nova destination grant", "authority_denied")
        destination = validate_external_target(source, destination_value, "migration destination", must_be_absent=True)
        destination_selection: dict[str, Any] = {"mode": "generic_external"}
    elif destination_mode == "nova_guarded_successor":
        if not authority.lower().startswith(("user", "human", "stunspot")):
            raise ContinuityError("Nova copy migration requires recorded human authority", "authority_denied")
        destination, nova_grant = validate_nova_migration_destination(
            source,
            destination_value,
            "migration destination",
            grant_id=str(grant_id or ""),
            expected_registry_sha256=str(expected_selector_registry_sha256 or ""),
            expected_destination_sha256=str(expected_destination_sha256 or ""),
            must_be_absent=True,
        )
        destination_selection = {
            "mode": "nova_guarded_successor",
            "grant_id": nova_grant.grant_id,
            "selector_registry_sha256": nova_grant.registry_digest,
            "destination_path_sha256": nova_grant.destination_sha256,
            "destination_path_digest_policy": "normalized-absolute-path-os-normcase-utf8/v1",
            "source_selector": SELECTOR,
            "source_was_active": True,
            "destination_relation": "same-parent-sibling",
        }
    else:
        raise ContinuityError(f"Unsupported migration destination mode: {destination_mode}", "selector_registry_invalid")
    if source == destination or source in destination.parents or destination in source.parents:
        raise ContinuityError("Migration requires a distinct non-nested destination", "protected_target_denied")
    if not destination.parent.is_dir():
        raise ContinuityError("Migration requires an existing destination parent directory", "protected_target_denied")
    if _has_reparse_component(source):
        raise ContinuityError("Migration source crosses an unverified reparse edge", "custody_reparse_escape")
    source_manifest = _read_json_path(source / "manifest.json")
    if not isinstance(source_manifest, dict) or source_manifest.get("format") != LEGACY_FORMAT:
        raise ContinuityError("Copy migration accepts an exact v1 source only", "version_unsupported")
    catalog = SchemaCatalog(Path(__file__).resolve().parents[1] / "assets" / "schemas")
    manifest_errors = catalog.validate(source_manifest, "continuity-manifest.schema.json")
    if manifest_errors:
        raise ContinuityError("Legacy source manifest failed schema validation: " + "; ".join(manifest_errors[:4]), "migration_source_invalid")
    source_digest_before = tree_digest(source)
    if expected_source_tree_sha256 != source_digest_before:
        raise ContinuityError("Caller source digest does not match the legacy source", "source_changed")
    source_rows = {
        "episodes.jsonl": _read_jsonl_path(source / "episodes" / "events.jsonl"),
        "state.jsonl": _read_jsonl_path(source / "state" / "records.jsonl"),
        "proposals.jsonl": _read_jsonl_path(source / "proposals" / "proposals.jsonl"),
    }
    migrated_rows, temporal_transformations = normalize_legacy_temporal_rows(source_rows)
    migrated_rows, legacy_content_transformations = annotate_legacy_oversize_content_rows(migrated_rows, source_rows)
    temporal_normalization_digest = sha256_bytes(dump_canonical(temporal_transformations).encode("utf-8"))
    legacy_content_provenance_digest = sha256_bytes(dump_canonical(legacy_content_transformations).encode("utf-8"))
    schema_pairs = {
        "episodes.jsonl": ("episode.schema.json", "episode-v2.schema.json"),
        "state.jsonl": ("state-record.schema.json", "state-record-v2.schema.json"),
        "proposals.jsonl": ("proposal.schema.json", "proposal-v2.schema.json"),
    }
    unsupported: list[dict[str, Any]] = []
    for member, rows in source_rows.items():
        legacy_schema, successor_schema = schema_pairs[member]
        for index, row in enumerate(rows):
            legacy_errors = catalog.validate(row, legacy_schema)
            successor_errors = catalog.validate(migrated_rows[member][index], successor_schema)
            if contains_secret_data(row):
                unsupported.append({"member": member, "row": index, "disposition": "redaction_rejected"})
            elif legacy_errors:
                unsupported.append({"member": member, "row": index, "disposition": "legacy_schema_invalid"})
            elif successor_errors:
                unsupported.append({"member": member, "row": index, "disposition": "successor_schema_incompatible"})
    episode_ids = {str(row.get("id")) for row in source_rows["episodes.jsonl"] if row.get("id")}
    for member in ("state.jsonl", "proposals.jsonl"):
        for index, row in enumerate(source_rows[member]):
            if not set(str(item) for item in row.get("source_ids") or []).issubset(episode_ids):
                unsupported.append({"member": member, "row": index, "disposition": "source_unreachable"})
    if unsupported:
        digest = sha256_bytes(dump_canonical(unsupported).encode("utf-8"))
        raise ContinuityError(f"Legacy source cannot be copied safely; disposition_digest={digest}; unsupported={len(unsupported)}", "migration_source_ineligible")
    source_digest_after_read = tree_digest(source)
    if source_digest_after_read != source_digest_before:
        raise ContinuityError("Migration source changed while being read", "source_changed")
    receipt_files: list[dict[str, Any]] = []
    receipts_root = source / "receipts"
    if receipts_root.is_dir():
        for item in sorted(path for path in receipts_root.rglob("*") if path.is_file()):
            receipt_files.append({"path": item.relative_to(source).as_posix(), "sha256": sha256_file(item), "bytes": item.stat().st_size})
    receipt_provenance_digest = sha256_bytes(dump_canonical(receipt_files).encode("utf-8"))
    if nova_grant:
        revalidate_nova_migration_grant(nova_grant, source, destination, require_destination_absent=True)
    construction = destination.parent / f".{destination.name}.cc-migrate-{uuid.uuid4().hex}"
    construction_identity: tuple[int, int] | None = None
    construction_created = False
    published = False
    try:
        construction.mkdir(exist_ok=False)
        construction_created = True
        construction_identity = _directory_identity(construction)
        if construction_identity is None:
            raise ContinuityError("Migration construction identity is unavailable", "filesystem_semantics_unsupported")
        for name in ("generations", "transactions", "locks", "quarantine"):
            (construction / name).mkdir(exist_ok=False)
        _write_new(construction / "locks" / "workspace.lock", b"\0")
        _fsync_directory(construction / "locks")
        _filesystem_qualification_witness(construction, lexical_root=construction)
        now = utc_now()
        scope = dict(source_manifest.get("scope") or {"user": "unknown", "project": "*", "agent": "nova", "thread": None})
        manifest = _base_manifest(
            workspace_id=new_id("CCW"), created_at=now, scope=scope,
            sensitivity=str((source_manifest.get("policies") or {}).get("default_sensitivity", "ordinary")),
            retention=str((source_manifest.get("policies") or {}).get("default_retention", "manual")),
        )
        manifest["migrated_from"] = {
            "format": LEGACY_FORMAT, "workspace_id": source_manifest.get("workspace_id"),
            "source_tree_sha256": source_digest_before, "copied_at": now,
            "policy": "cd-continuity-copy-migration/v2",
            "legacy_receipt_provenance_sha256": receipt_provenance_digest,
            "legacy_receipt_file_count": len(receipt_files),
            "temporal_normalization_count": len(temporal_transformations),
            "temporal_normalization_sha256": temporal_normalization_digest,
            "legacy_oversize_content_provenance_count": len(legacy_content_transformations),
            "legacy_oversize_content_provenance_sha256": legacy_content_provenance_digest,
        }
        if nova_grant:
            manifest["migrated_from"]["destination_selection"] = destination_selection
        transaction_id = new_id("TX")
        key = f"migrate:{source_digest_before}"
        payload = {"source_digest": source_digest_before, "destination_digest": sha256_bytes(str(destination).encode("utf-8")), "authority": authority, "destination_selection": destination_selection}
        digest = request_digest("migrate-copy", payload)
        source_after = tree_digest(source)
        if source_after != source_digest_before:
            raise ContinuityError("Migration source changed before destination publication", "source_changed")
        if temporal_transformations and legacy_content_transformations:
            mapping_policy = "legacy-full-date-and-lossless-oversize-content/v2"
        elif temporal_transformations:
            mapping_policy = "legacy-full-date-normalization/v2"
        elif legacy_content_transformations:
            mapping_policy = "legacy-lossless-oversize-content/v1"
        else:
            mapping_policy = "schema-valid-identity-copy/v2"
        receipt, idempotency = _initial_receipt_and_idempotency(
            manifest, transaction_id=transaction_id, operation="migrate-copy", kind="migration-copied",
            selector=(f"nova_guarded_successor:{nova_grant.grant_id}:{nova_grant.registry_digest[:16]}" if nova_grant else "generic_explicit"), authority=authority, key=key, request_digest_value=digest,
            details={
                "destination_selection": destination_selection,
                "source_workspace_id": source_manifest.get("workspace_id"), "source_format": LEGACY_FORMAT,
                "source_tree_sha256": source_digest_before, "source_tree_sha256_after": source_after,
                "canonical_source_changed": False,
                "mapping": {"episodes": len(source_rows["episodes.jsonl"]), "state": len(source_rows["state.jsonl"]), "proposals": len(source_rows["proposals.jsonl"]), "unsupported": 0, "normalized_temporal_fields": len(temporal_transformations), "lossless_oversize_content_rows": len(legacy_content_transformations)},
                "mapping_policy": mapping_policy,
                "temporal_normalization_sha256": temporal_normalization_digest,
                "legacy_oversize_content_provenance_sha256": legacy_content_provenance_digest,
                "legacy_receipt_provenance_sha256": receipt_provenance_digest,
                "legacy_receipt_file_count": len(receipt_files),
                "legacy_receipt_disposition": "digest-bound-not-promoted-to-v2-authority",
            },
        )
        rows = {name: list(migrated_rows.get(name, [])) for name in MEMBERS}
        rows["receipts.jsonl"] = [receipt]
        rows["idempotency.jsonl"] = [idempotency]
        _publish_initial_workspace(construction, manifest, rows, transaction_id, "migrate-copy")
        if nova_grant:
            revalidate_nova_migration_grant(nova_grant, source, destination, require_destination_absent=True)
        if tree_digest(source) != source_digest_before:
            raise ContinuityError("Migration source changed during copy", "source_changed")
        if destination.exists():
            raise ContinuityError("Migration destination appeared before publication", "protected_target_denied")
        _publish_directory(construction, destination)
        published = True
        if nova_grant:
            revalidate_nova_migration_grant(nova_grant, source, destination, require_destination_absent=False)
        _filesystem_qualification_witness(
            destination,
            lexical_root=Path(nova_grant.destination_lexical) if nova_grant else destination,
        )
        return receipt
    except BaseException as exc:
        retained: list[Path] = []
        if construction_created and os.path.lexists(construction):
            retained.append(construction)
        if os.path.lexists(destination) and (
            published
            or construction_identity is None
            or _directory_identity(destination) == construction_identity
        ):
            retained.append(destination)
        if retained:
            names = ", ".join(str(path) for path in dict.fromkeys(retained))
            raise ContinuityError(
                f"Migration failed without race-unsafe cleanup; retained path(s): {names}",
                "recovery_required",
            ) from exc
        raise
