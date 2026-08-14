#!/usr/bin/env python3
"""Continuity v2 immutable-generation workspace kernel and selector resolver."""
from __future__ import annotations

import ctypes
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
IMPLEMENTATION_VERSION = "0.2.0"
SELECTOR = "NOVA_CONTINUITY_HOME"
ROOT_SELECTOR = "NOVA_DATA_ROOT"
SELECTOR_REGISTRY = Path(r"E:\Indranet\Nova\estate\path-selectors.json")
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
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda p: p.as_posix()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8") + b"\0" + bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()

def _flush(handle: Any) -> None:
    handle.flush()
    os.fsync(handle.fileno())

def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            _flush(handle)
        os.replace(temporary, path)
        _fsync_directory(path.parent)
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
        os.replace(temporary, path)
        _fsync_directory(path.parent)
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
        return _loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ContinuityError(f"Cannot read valid JSON from {path}: {exc}", "workspace_invalid") from exc

def _read_jsonl_path(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                value = _loads(line)
                if not isinstance(value, dict):
                    raise ValueError("row is not an object")
                rows.append(value)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ContinuityError(f"Cannot read valid JSONL from {path}: {exc}", "workspace_invalid") from exc
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
    relative = manifest.get("active_generation_path")
    if not isinstance(relative, str):
        raise ContinuityError("Manifest lacks active generation path", "recovery_required")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ContinuityError("Active generation escapes workspace", "custody_denied") from exc
    return candidate

def _verify_generation(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    bundle = generation_path(root, manifest)
    generation_file = bundle / "generation.json"
    if not generation_file.is_file():
        raise ContinuityError("Active generation metadata is missing", "recovery_required")
    observed_digest = sha256_file(generation_file)
    if observed_digest != manifest.get("active_generation_manifest_sha256"):
        raise ContinuityError("Active generation manifest digest mismatch", "recovery_required")
    metadata = _read_json_path(generation_file)
    if metadata.get("format") != GENERATION_FORMAT or metadata.get("workspace_id") != manifest.get("workspace_id") or metadata.get("generation") != manifest.get("generation"):
        raise ContinuityError("Active generation identity mismatch", "recovery_required")
    members = metadata.get("members") or {}
    for name in MEMBERS:
        path = bundle / name
        expected = (members.get(name) or {}).get("sha256")
        if not path.is_file() or not expected or sha256_file(path) != expected:
            raise ContinuityError(f"Active generation member is missing or corrupt: {name}", "recovery_required")
    return metadata

def open_snapshot(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = root / "manifest.json"
    for _ in range(2):
        try:
            first = manifest_path.read_bytes()
        except OSError as exc:
            raise ContinuityError("Workspace manifest is unavailable", "workspace_missing") from exc
        manifest = _loads(first.decode("utf-8-sig"))
        if manifest.get("format") != FORMAT:
            raise ContinuityError("Immutable snapshot requires v2", "version_unsupported")
        metadata = _verify_generation(root, manifest)
        second = manifest_path.read_bytes()
        if first == second:
            return manifest, metadata
    raise ContinuityError("Workspace changed during both read attempts", "snapshot_changed")

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
def _absolute_local(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ContinuityError(f"{label} is missing", "selector_registry_invalid")
    raw = value.strip()
    candidate = Path(raw)
    if not candidate.is_absolute() or any(part in {".", ".."} for part in candidate.parts) or raw.startswith("\\\\?\\") or raw.startswith("\\\\.\\"):
        raise ContinuityError(f"{label} is not an absolute supported local path", "selector_registry_invalid")
    return candidate.resolve()

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
        if not item.exists():
            continue
        try:
            info = os.lstat(item)
        except OSError:
            return True
        attributes = getattr(info, "st_file_attributes", 0)
        if item.is_symlink() or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            return True
    return False

def _registry(path: Path | None = None) -> tuple[Path, dict[str, Any], str]:
    registry_path = (path or SELECTOR_REGISTRY).resolve()
    if not registry_path.is_file() or registry_path.is_symlink() or _has_reparse_component(registry_path):
        raise ContinuityError("Trusted Nova selector registry is unavailable or indirect", "selector_registry_invalid")
    try:
        first = registry_path.read_bytes()
        value = _loads(first.decode("utf-8-sig"))
        second = registry_path.read_bytes()
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ContinuityError(f"Trusted Nova selector registry is invalid: {exc}", "selector_registry_invalid") from exc
    if first != second:
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
    root = _absolute_local(active.get(ROOT_SELECTOR), ROOT_SELECTOR)
    continuity = _absolute_local(active.get(SELECTOR), SELECTOR)
    _within(root, continuity, "selector_registry_invalid")
    if not root.exists() or _has_reparse_component(root) or _has_reparse_component(continuity, root):
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
        selected_lexical = Path(os.path.abspath(str(path_value).strip()))
        selected = _absolute_local(path_value, "workspace")
        if ".codex" in {part.casefold() for part in selected.parts}:
            raise ContinuityError("Host .codex custody is a protected target", "protected_target_denied")
        if _has_reparse_component(selected):
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
        selected_lexical = Path(os.path.abspath(str(path_value).strip()))
        selected = _absolute_local(path_value, "workspace")
        _within(custody_root, selected, "caller_root_denied")
        provenance = f"nova_explicit_authorized:{grant_id}:{digest[:16]}"
    _within(custody_root, selected, "caller_root_denied")
    if ".codex" in {part.casefold() for part in selected.parts}:
        raise ContinuityError("Nova Continuity cannot use host .codex custody", "protected_target_denied")
    if _has_reparse_component(selected, custody_root):
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
    if os.path.normcase(str(lexical.resolve())) != os.path.normcase(str(root.resolve())):
        raise ContinuityError("Selected workspace path changed after resolution", "selector_registry_changed")
    if os.path.normcase(str(root.resolve())) != os.path.normcase(str(Path(token.selected_root).resolve())):
        raise ContinuityError("Resolved workspace differs from its selection token", "selector_registry_changed")
    _filesystem_adapter(root)
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

def _filesystem_adapter(root: Path) -> str:
    if os.name != "nt":
        raise ContinuityError("Only qualified local Windows NTFS mutation is supported", "filesystem_semantics_unsupported")
    raw = str(root)
    if raw.startswith("\\\\"):
        raise ContinuityError("UNC and network paths are outside the qualified mutation boundary", "filesystem_semantics_unsupported")
    probe = root.resolve()
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    cloud_roots: list[Path] = []
    for name in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer", "Dropbox", "GoogleDrive", "iCloudDrive"):
        value = os.environ.get(name)
        if value:
            try:
                cloud_roots.append(Path(value).resolve())
            except OSError:
                pass
    for cloud_root in cloud_roots:
        try:
            root.resolve().relative_to(cloud_root)
        except ValueError:
            continue
        raise ContinuityError("Cloud-synchronized paths are outside the qualified mutation boundary", "filesystem_semantics_unsupported")
    if any(part.casefold() in {"onedrive", "dropbox", "google drive", "icloud drive", "box"} for part in root.parts):
        raise ContinuityError("Cloud-synchronized paths are outside the qualified mutation boundary", "filesystem_semantics_unsupported")
    volume_path = ctypes.create_unicode_buffer(261)
    if not ctypes.windll.kernel32.GetVolumePathNameW(str(probe), volume_path, len(volume_path)):
        raise ContinuityError("Cannot resolve local filesystem semantics", "filesystem_semantics_unsupported")
    if ctypes.windll.kernel32.GetDriveTypeW(volume_path.value) != 3:
        raise ContinuityError("Mapped, remote, removable, and unknown drives are unsupported", "filesystem_semantics_unsupported")
    filesystem = ctypes.create_unicode_buffer(261)
    if not ctypes.windll.kernel32.GetVolumeInformationW(volume_path.value, None, 0, None, None, None, filesystem, len(filesystem)):
        raise ContinuityError("Cannot inspect local filesystem semantics", "filesystem_semantics_unsupported")
    if filesystem.value.upper() != "NTFS":
        raise ContinuityError(f"Unsupported filesystem for v2 mutation: {filesystem.value}", "filesystem_semantics_unsupported")
    return "windows-LockFileEx-MoveFileExW-write-through-ntfs/v1"

def _selector_custody_boundaries() -> list[Path]:
    """Return every active Nova custody boundary from one stable registry read."""
    boundaries = {
        SELECTOR_REGISTRY.resolve(),
        Path(r"E:\Indranet\Nova\mind").resolve(),
        Path(r"E:\Indranet\Nova\mind\receipts").resolve(),
        Path(r"E:\Indranet\Nova\mind\qualification\egdod-r7-prepared-2026-08-12").resolve(),
        Path(r"E:\Indranet\Nova\archive").resolve(),
    }
    if SELECTOR_REGISTRY.is_file():
        _, registry, _ = _registry(SELECTOR_REGISTRY)
        active = registry["active_values"]
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


def validate_external_target(source_root: Path, value: str, label: str, *, must_be_absent: bool = False) -> Path:
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
    _filesystem_adapter(target)
    if must_be_absent and target.exists():
        raise ContinuityError(f"{label} must be absent", "protected_target_denied")
    return target

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
def workspace_lock(root: Path, timeout: float = 0.0, *, transaction_id: str | None = None) -> Iterator[dict[str, Any]]:
    adapter = _filesystem_adapter(root)
    locks = root / "locks"
    locks.mkdir(parents=True, exist_ok=True)
    lock_path = locks / "workspace.lock"
    if not lock_path.exists():
        _write_new(lock_path, b"\0")
    descriptor = os.open(str(lock_path), os.O_RDWR)
    acquired = False
    state: Any = None
    deadline = time.monotonic() + max(0.0, timeout)
    try:
        while True:
            acquired, state = _try_os_lock(descriptor)
            if acquired:
                break
            if time.monotonic() >= deadline:
                observed = _owner_observation(root)
                raise ContinuityError(f"Continuity writer lock is busy; owner={observed['classification']}; retry_after_ms=100", "lock_busy")
            time.sleep(min(0.025, max(0.0, deadline - time.monotonic())))
        token = uuid.uuid4().hex + uuid.uuid4().hex
        owner = {
            "format": LOCK_FORMAT, "owner_token": token, "pid": os.getpid(), "process_started_at": _PROCESS_STARTED_AT,
            "host": socket.gethostname(), "session_identity": os.environ.get("SESSIONNAME") or _RUNTIME_SESSION_ID,
            "runtime_identity": f"python-{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "transaction_id": transaction_id, "acquired_at": utc_now(), "adapter": adapter,
            "prior_owner_observation": _owner_observation(root),
        }
        atomic_json(locks / "workspace-owner.json", owner)
        try:
            yield owner
        finally:
            owner_path = locks / "workspace-owner.json"
            try:
                current = _read_json_path(owner_path)
                if isinstance(current, dict) and current.get("owner_token") == token:
                    owner_path.unlink(missing_ok=True)
            except ContinuityError:
                pass
    finally:
        try:
            if acquired:
                _unlock_os_lock(descriptor, state)
        finally:
            os.close(descriptor)
def _crash(point: str) -> None:
    if os.environ.get("CONTINUITY_TEST_FAILPOINT") == point:
        raise ContinuityError(f"Injected failure at {point}", "test_failpoint")
    if os.environ.get("CONTINUITY_TEST_CRASHPOINT") == point:
        os._exit(97)

def _journal_transition(path: Path, state: str, *, recovery: bool = False, **updates: Any) -> dict[str, Any]:
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
    atomic_json(path, value)
    return value

def _all_transaction_directories(root: Path) -> list[Path]:
    base = root / "transactions"
    if not base.is_dir():
        return []
    return sorted(item for item in base.iterdir() if item.is_dir())

def pending_transactions(root: Path) -> list[Path]:
    pending: list[Path] = []
    for directory in _all_transaction_directories(root):
        journal_path = directory / "journal.json"
        if not journal_path.is_file():
            pending.append(directory)
            continue
        try:
            state = _read_json_path(journal_path).get("state")
        except ContinuityError:
            pending.append(directory)
            continue
        if state not in FINAL_JOURNAL_STATES:
            pending.append(directory)
    return pending

def _quarantine_path(root: Path, target: Path, transaction_id: str, label: str) -> str | None:
    if not target.exists():
        return None
    _inside(root, target)
    quarantine = root / "quarantine"
    quarantine.mkdir(parents=True, exist_ok=True)
    destination = quarantine / f"{transaction_id}-{label}"
    suffix = 0
    while destination.exists():
        suffix += 1
        destination = quarantine / f"{transaction_id}-{label}-{suffix}"
    os.replace(target, destination)
    _fsync_directory(quarantine)
    return destination.relative_to(root).as_posix()

def _journal_artifacts(root: Path, journal: dict[str, Any]) -> tuple[Path | None, Path | None, Path]:
    transaction_root = root / "transactions" / str(journal.get("transaction_id") or journal.get("id"))
    staged_value = journal.get("staged_generation_path")
    final_value = journal.get("final_generation_path")
    staged = root / str(staged_value) if isinstance(staged_value, str) else transaction_root / "stage" / str(journal.get("generation_directory") or "unknown")
    final = root / str(final_value) if isinstance(final_value, str) else None
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

def _recover_committed(root: Path, journal_path: Path, manifest: dict[str, Any], journal: dict[str, Any]) -> str:
    _committed_evidence(root, manifest, journal)
    current = journal
    if current.get("state") != "committed":
        current = _journal_transition(journal_path, "committed", recovery=True, recovery_disposition="manifest_commit_authoritative", recovered_at=utc_now())
    if current.get("state") != "finalized":
        _journal_transition(journal_path, "finalized", recovery=True, recovery_disposition="manifest_commit_authoritative", finalized_at=utc_now())
    return str(journal.get("transaction_id") or journal.get("id"))

def _recover_uncommitted(root: Path, journal_path: Path, manifest: dict[str, Any], journal: dict[str, Any]) -> str:
    if journal.get("state") == "recovery_required":
        raise ContinuityError("A recovery_required transaction requires human disposition", "recovery_required")
    transaction_id = str(journal.get("transaction_id") or journal.get("id"))
    staged, final, manifest_next = _journal_artifacts(root, journal)
    quarantined: list[str] = []
    if staged is not None:
        item = _quarantine_path(root, staged, transaction_id, "staged")
        if item:
            quarantined.append(item)
    if final is not None and final.resolve() != generation_path(root, manifest).resolve():
        item = _quarantine_path(root, final, transaction_id, "published")
        if item:
            quarantined.append(item)
    if manifest_next.is_file():
        try:
            candidate = _read_json_path(manifest_next)
        except ContinuityError:
            candidate = {}
        if candidate.get("committing_transaction_id") in {None, transaction_id}:
            item = _quarantine_path(root, manifest_next, transaction_id, "manifest-next")
            if item:
                quarantined.append(item)
    _journal_transition(journal_path, "aborted", recovery=True, recovery_disposition="uncommitted_preserved_prior", quarantined=quarantined, aborted_at=utc_now())
    return transaction_id

def _mark_recovery_required(journal_path: Path, reason: str) -> None:
    try:
        _journal_transition(journal_path, "recovery_required", recovery=True, recovery_disposition=reason)
    except ContinuityError:
        pass

def _recover_transactions_locked(root: Path) -> list[str]:
    directories = pending_transactions(root)
    if not directories:
        return []
    manifest, _ = open_snapshot(root)
    parsed: list[tuple[Path, dict[str, Any]]] = []
    for directory in directories:
        path = directory / "journal.json"
        if not path.is_file():
            raise ContinuityError(f"Transaction directory lacks journal: {directory.name}", "recovery_required")
        journal = _read_json_path(path)
        if not isinstance(journal, dict) or journal.get("format") != TRANSACTION_FORMAT:
            raise ContinuityError(f"Invalid transaction journal: {directory.name}", "recovery_required")
        if journal.get("state") == "recovery_required":
            raise ContinuityError("A recovery_required transaction requires human disposition", "recovery_required")
        if str(journal.get("transaction_id") or journal.get("id")) != directory.name:
            _mark_recovery_required(path, "journal_directory_identity_mismatch")
            raise ContinuityError("Transaction identity and directory disagree", "recovery_required")
        parsed.append((path, journal))
    active_transaction = manifest.get("committing_transaction_id")
    matching = [(path, journal) for path, journal in parsed if str(journal.get("transaction_id") or journal.get("id")) == active_transaction]
    if len(parsed) > 1 and len(matching) != 1:
        for path, _ in parsed:
            _mark_recovery_required(path, "multiple_unfinished_ambiguous")
        raise ContinuityError("Multiple unfinished journals cannot be reconciled unambiguously", "recovery_required")
    recovered: list[str] = []
    if matching:
        path, journal = matching[0]
        try:
            recovered.append(_recover_committed(root, path, manifest, journal))
        except ContinuityError:
            _mark_recovery_required(path, "manifest_or_bundle_evidence_disagrees")
            raise
    for path, journal in parsed:
        transaction_id = str(journal.get("transaction_id") or journal.get("id"))
        if transaction_id == active_transaction:
            continue
        expected = journal.get("expected_generation")
        new_generation = journal.get("new_generation")
        final_value = journal.get("final_generation_path")
        active_path = manifest.get("active_generation_path")
        provably_uncommitted = (
            isinstance(expected, int) and isinstance(new_generation, int)
            and expected <= int(manifest.get("generation", -1))
            and new_generation <= int(manifest.get("generation", -1)) + 1
            and final_value != active_path
        )
        if len(parsed) == 1:
            provably_uncommitted = expected == manifest.get("generation") and new_generation == int(expected) + 1
        if not provably_uncommitted:
            _mark_recovery_required(path, "uncommitted_status_not_provable")
            raise ContinuityError("Unfinished transaction is not safely classifiable", "recovery_required")
        recovered.append(_recover_uncommitted(root, path, manifest, journal))
    return recovered

def recover_transactions(root: Path, *, lock_timeout: float = 0.0) -> list[str]:
    with workspace_lock(root, lock_timeout, transaction_id="recovery"):
        return _recover_transactions_locked(root)

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
def _replace_manifest(source: Path, destination: Path) -> str:
    if source.parent.resolve() != destination.parent.resolve():
        raise ContinuityError("Manifest commit must remain in one directory", "filesystem_semantics_unsupported")
    if os.name == "nt":
        MOVEFILE_REPLACE_EXISTING = 0x1
        MOVEFILE_WRITE_THROUGH = 0x8
        ok = ctypes.windll.kernel32.MoveFileExW(str(source), str(destination), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)
        if not ok:
            raise ctypes.WinError(ctypes.windll.kernel32.GetLastError())
        return "windows-MoveFileExW-replace-write-through/v1"
    os.replace(source, destination)
    _fsync_directory(destination.parent)
    return "posix-rename-parent-fsync/v1"

def _row_count(value: bytes) -> int:
    if not value:
        return 0
    return sum(1 for line in value.splitlines() if line.strip())

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

    def __enter__(self) -> "WorkspaceTransaction":
        # Complete every read-only preflight before acquiring a lock or creating evidence.
        self.adapter = _filesystem_adapter(self.root)
        pre_manifest, _ = open_snapshot(self.root)
        observed_generation = int(pre_manifest["generation"])
        if self.expected_generation != observed_generation:
            raise ContinuityError(f"Expected generation {self.expected_generation}, observed {observed_generation}", "generation_conflict")
        duplicate = find_idempotent_receipt(self.root, self.public_idempotency_key, self.request_digest, self.operation)
        if duplicate is not None:
            raise IdempotentReplay(duplicate)
        self.lock_context = workspace_lock(self.root, self.lock_timeout, transaction_id=self.id)
        self.lock_context.__enter__()
        try:
            if self.resolution_token is not None:
                revalidate_resolution(self.resolution_token, self.root)
            _recover_transactions_locked(self.root)
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

    def _record_intent(self) -> None:
        if self.journal_path.exists() or not self.entered or self.adapter is None:
            raise ContinuityError("Transaction intent state is invalid", "internal_unclassified")
        _crash("before_intent")
        try:
            self.transaction_root.mkdir(parents=True, exist_ok=False)
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
                },
                "expected_generation": self.generation_before,
                "new_generation": self.generation_after,
                "previous_manifest_digest": sha256_file(self.root / "manifest.json"),
                "previous_generation_manifest_digest": self.manifest_before.get("active_generation_manifest_sha256"),
                "generation_directory": generation_directory,
                "staged_generation_path": f"transactions/{self.id}/stage/{generation_directory}",
                "final_generation_path": f"generations/{generation_directory}",
                "planned_artifacts": [*MEMBERS, "generation.json", "manifest.next"],
            }
            atomic_json(self.journal_path, intent)
        except BaseException:
            if self.transaction_root.is_dir() and not any(self.transaction_root.iterdir()):
                self.transaction_root.rmdir()
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
        final.parent.mkdir(parents=True, exist_ok=True)
        if final.exists():
            raise ContinuityError("Published generation destination already exists", "recovery_required")
        os.rename(stage, final)
        _fsync_directory(final.parent)
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
        adapter = _replace_manifest(manifest_next_path, self.root / "manifest.json")
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
            if self.entered and not self.finished and self.journal_path.is_file():
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
    manifest.update({
        "active_generation_path": "generations/g-00000000000000000000",
        "active_generation_manifest_sha256": digest,
        "committing_transaction_id": transaction_id,
        "previous_generation": None,
        "previous_generation_manifest_sha256": None,
    })
    atomic_json(root / "manifest.json", manifest)
    open_snapshot(root)

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
    _filesystem_adapter(root)
    if root.exists():
        raise ContinuityError(f"Initialization target must be absent: {root}", "protected_target_denied")
    root.mkdir(parents=True, exist_ok=False)
    try:
        for name in ("generations", "transactions", "locks", "quarantine"):
            (root / name).mkdir(exist_ok=False)
        _write_new(root / "locks" / "workspace.lock", b"\0")
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
        _publish_initial_workspace(root, manifest, rows, transaction_id, "initialize")
        return root, receipt
    except BaseException:
        if root.exists() and root.parent.exists():
            shutil.rmtree(root, ignore_errors=True)
        raise

def migrate_copy(
    source_value: str, destination_value: str, *, authority: str,
    expected_source_tree_sha256: str,
) -> dict[str, Any]:
    if not authority or not authority.strip():
        raise ContinuityError("Copy migration requires explicit authority", "authority_denied")
    if contains_secret_data(authority):
        raise ContinuityError("Migration authority identifier failed redaction", "redaction_rejected")
    source = _absolute_local(source_value, "source workspace")
    destination = validate_external_target(source, destination_value, "migration destination", must_be_absent=True)
    if source == destination or source in destination.parents or destination in source.parents:
        raise ContinuityError("Migration requires a distinct non-nested destination", "protected_target_denied")
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
            successor_errors = catalog.validate(row, successor_schema)
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
    destination.mkdir(parents=True, exist_ok=False)
    try:
        for name in ("generations", "transactions", "locks", "quarantine"):
            (destination / name).mkdir(exist_ok=False)
        _write_new(destination / "locks" / "workspace.lock", b"\0")
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
        }
        transaction_id = new_id("TX")
        key = f"migrate:{source_digest_before}"
        payload = {"source_digest": source_digest_before, "destination_digest": sha256_bytes(str(destination).encode("utf-8")), "authority": authority}
        digest = request_digest("migrate-copy", payload)
        source_after = tree_digest(source)
        if source_after != source_digest_before:
            raise ContinuityError("Migration source changed before destination publication", "source_changed")
        receipt, idempotency = _initial_receipt_and_idempotency(
            manifest, transaction_id=transaction_id, operation="migrate-copy", kind="migration-copied",
            selector="generic_explicit", authority=authority, key=key, request_digest_value=digest,
            details={
                "source_workspace_id": source_manifest.get("workspace_id"), "source_format": LEGACY_FORMAT,
                "source_tree_sha256": source_digest_before, "source_tree_sha256_after": source_after,
                "canonical_source_changed": False,
                "mapping": {"episodes": len(source_rows["episodes.jsonl"]), "state": len(source_rows["state.jsonl"]), "proposals": len(source_rows["proposals.jsonl"]), "unsupported": 0},
                "mapping_policy": "schema-valid-identity-copy/v2",
                "legacy_receipt_provenance_sha256": receipt_provenance_digest,
                "legacy_receipt_file_count": len(receipt_files),
                "legacy_receipt_disposition": "digest-bound-not-promoted-to-v2-authority",
            },
        )
        rows = {name: list(source_rows.get(name, [])) for name in MEMBERS}
        rows["receipts.jsonl"] = [receipt]
        rows["idempotency.jsonl"] = [idempotency]
        _publish_initial_workspace(destination, manifest, rows, transaction_id, "migrate-copy")
        if tree_digest(source) != source_digest_before:
            raise ContinuityError("Migration source changed during copy", "source_changed")
        return receipt
    except BaseException:
        if destination.exists() and destination.parent.exists():
            shutil.rmtree(destination, ignore_errors=True)
        raise