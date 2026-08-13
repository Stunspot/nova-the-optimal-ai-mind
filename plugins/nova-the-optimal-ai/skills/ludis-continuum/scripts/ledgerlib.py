from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, BinaryIO, Iterable, Iterator

LEGACY_VERSION = "0.1.0"
LEDGER_FORMAT_V2 = "cd-ludis-campaign-ledger/v2"
STATUSES = {"proposed", "active_canon", "disputed", "superseded", "quarantined", "retired"}
VISIBILITY = {"gm_only", "player_safe"}
CONFIDENCE = {"unknown", "low", "medium", "high"}
EXPORT_ELIGIBILITY = {"eligible", "blocked", "quarantined_unmapped"}
RIGHTS_STATUS = {"owned", "licensed", "public_domain", "permission_granted", "unknown"}

# Kinds Ludis can carry into its neutral pack without pretending to understand an
# arbitrary legacy payload. New kinds retain identity and canon during migration,
# but remain quarantined from export until a person maps them deliberately.
KNOWN_OBJECT_KINDS = {
    "adventure", "audio_cue", "backstory", "character", "clock", "consequence",
    "creature", "cursed_item", "dispute", "dungeon", "encounter", "encounter_chain",
    "faction", "faction_allegiance", "handout", "homebrew_mechanic", "impossible_invention",
    "intrigue_web", "item", "journal", "legendary_artifact", "location", "lore_claim",
    "lost_civilization", "magic_system", "map", "myth", "npc", "observation", "party",
    "prophecy", "proposal", "puzzle", "quest", "region_map", "rule_assumption",
    "rule_reference", "rules_question", "rumor", "scene", "secret", "secret_society",
    "session_note", "settlement", "spell", "table", "tavern_menu", "thread", "token",
    "trap", "urban_dungeon", "villain", "villain_scheme",
}

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EXTENSION_KEY_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)+$")


class LedgerBusyError(RuntimeError):
    """Raised when another Ludis writer owns the ledger reservation."""


class LedgerWriteConflictError(RuntimeError):
    """Raised when the ledger changed after a read-modify-write began."""


class LedgerLockCleanupError(RuntimeError):
    """Raised when a completed ledger operation cannot release its own lock."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _decode_ledger(data: bytes) -> dict[str, Any]:
    value = json.loads(data.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("ledger root must be an object")
    return value


def load_with_digest(path: Path) -> tuple[dict[str, Any], str]:
    data = path.read_bytes()
    return _decode_ledger(data), _sha256(data)


def load(path: Path) -> dict[str, Any]:
    value, _ = load_with_digest(path)
    return value


def _write_staged_bytes(handle: BinaryIO, data: bytes) -> None:
    """Single injection seam for complete staged writes."""
    handle.write(data)
    handle.flush()
    os.fsync(handle.fileno())


def _remove_without_masking(path: Path, original_error: BaseException | None) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        if original_error is None:
            raise


def _windows_replace_file(destination: Path, replacement: Path, backup: Path | None) -> None:
    """Call ReplaceFileW so the exact displaced destination can be inspected."""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    replace_file = kernel32.ReplaceFileW
    replace_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.LPVOID,
    ]
    replace_file.restype = wintypes.BOOL
    replaced = replace_file(
        str(destination),
        str(replacement),
        str(backup) if backup is not None else None,
        0,
        None,
        None,
    )
    if not replaced:
        raise ctypes.WinError(ctypes.get_last_error())


@contextmanager
def _windows_ledger_write_guard(path: Path) -> Iterator[None]:
    """Deny direct writers while permitting the atomic ReplaceFileW swap."""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    generic_read = 0x80000000
    share_read = 0x00000001
    share_delete = 0x00000004
    open_existing = 3
    normal = 0x00000080
    invalid_handle = ctypes.c_void_p(-1).value
    handle = create_file(
        str(path),
        generic_read,
        share_read | share_delete,
        None,
        open_existing,
        normal,
        None,
    )
    if handle == invalid_handle:
        error = ctypes.get_last_error()
        raise LedgerWriteConflictError(
            "ledger could not be reserved against an external writer"
        ) from ctypes.WinError(error)
    operation_error: BaseException | None = None
    try:
        yield
    except BaseException as exc:
        operation_error = exc
        raise
    finally:
        if not close_handle(handle) and operation_error is None:
            raise OSError(ctypes.get_last_error(), "could not release Windows ledger write guard")


def _restore_windows_displaced(path: Path, displaced: Path) -> None:
    rejected = path.with_name(f".{path.name}.{uuid.uuid4().hex}.ludis-rejected")
    try:
        _windows_replace_file(path, displaced, rejected)
    finally:
        rejected.unlink(missing_ok=True)


def _replace_expected_windows(staged: Path, path: Path, expected_sha256: str, proposed: bytes) -> None:
    """Swap, inspect the exact displaced generation, and restore on conflict.

    The write guard blocks ordinary direct editors. ReplaceFileW also returns the
    precise destination generation displaced at the atomic boundary as `backup`,
    so an uncoordinated temp-file replacement cannot be silently overwritten.
    """
    backup = path.with_name(f".{path.name}.{uuid.uuid4().hex}.ludis-backup")
    with _windows_ledger_write_guard(path):
        try:
            current = path.read_bytes()
        except FileNotFoundError as exc:
            raise LedgerWriteConflictError("ledger disappeared before atomic replacement") from exc
        if _sha256(current) != expected_sha256:
            raise LedgerWriteConflictError("ledger changed before atomic replacement")
        try:
            _windows_replace_file(path, staged, backup)
        except PermissionError as exc:
            raise LedgerWriteConflictError("external writer reached the ledger replacement boundary") from exc
        try:
            try:
                displaced = backup.read_bytes()
            except OSError as exc:
                raise LedgerWriteConflictError(
                    f"cannot verify displaced ledger generation; preserve recovery file: {backup}"
                ) from exc
            if _sha256(displaced) != expected_sha256:
                try:
                    _restore_windows_displaced(path, backup)
                except OSError as restore_error:
                    conflict = LedgerWriteConflictError(
                        f"ledger changed at the replacement boundary and automatic restoration failed; preserve: {backup}"
                    )
                    if hasattr(conflict, "add_note"):
                        conflict.add_note(str(restore_error))
                    raise conflict from restore_error
                raise LedgerWriteConflictError("ledger changed at the atomic replacement boundary")
            try:
                installed = path.read_bytes()
            except OSError as exc:
                raise LedgerWriteConflictError("installed ledger could not be verified") from exc
            if installed != proposed:
                raise LedgerWriteConflictError(
                    f"ledger changed immediately after atomic replacement; prior generation preserved at {backup}"
                )
            backup.unlink(missing_ok=True)
        except BaseException:
            # On a normal conflict restoration consumes the backup. On an
            # ambiguous failure, retain it as explicit recovery evidence.
            raise


def _restore_posix_displaced(path: Path, displaced: Path) -> None:
    """Restore a displaced generation only while the canonical path is absent."""
    try:
        os.link(displaced, path)
    except FileExistsError as exc:
        raise LedgerWriteConflictError(
            f"cannot restore displaced ledger because another generation occupies {path}; preserve {displaced}"
        ) from exc
    except OSError as exc:
        raise LedgerWriteConflictError(
            f"cannot restore displaced ledger; preserve recovery file: {displaced}"
        ) from exc
    try:
        if path.read_bytes() != displaced.read_bytes():
            raise LedgerWriteConflictError(
                f"restored ledger does not match displaced recovery bytes; preserve {displaced}"
            )
        displaced.unlink()
    except BaseException:
        # Both hard links are intentionally retained if verification or cleanup
        # is ambiguous; neither generation is silently discarded.
        raise


def _recover_posix_after_publication(path: Path, displaced: Path) -> Path | None:
    """Preserve the current path, then restore the displaced generation safely."""
    rejected = path.with_name(f".{path.name}.{uuid.uuid4().hex}.ludis-rejected")
    preserved: Path | None = None
    try:
        os.rename(path, rejected)
        preserved = rejected
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise LedgerWriteConflictError(
            f"cannot preserve the ambiguous installed ledger; prior generation remains at {displaced}"
        ) from exc
    _restore_posix_displaced(path, displaced)
    return preserved


def _replace_expected_posix(staged: Path, path: Path, expected_sha256: str, proposed: bytes) -> None:
    """Displace, verify, and publish without overwriting a late POSIX writer."""
    displaced = path.with_name(f".{path.name}.{uuid.uuid4().hex}.ludis-displaced")
    try:
        os.rename(path, displaced)
    except FileNotFoundError as exc:
        raise LedgerWriteConflictError("ledger disappeared before atomic displacement") from exc
    except OSError as exc:
        raise LedgerWriteConflictError("ledger could not be atomically displaced for comparison") from exc

    try:
        try:
            displaced_bytes = displaced.read_bytes()
        except OSError as exc:
            raise LedgerWriteConflictError(
                f"cannot verify displaced ledger generation; preserve recovery file: {displaced}"
            ) from exc
        if _sha256(displaced_bytes) != expected_sha256:
            try:
                _restore_posix_displaced(path, displaced)
            except LedgerWriteConflictError as restore_error:
                conflict = LedgerWriteConflictError(
                    f"ledger changed at the atomic displacement boundary and could not be restored; preserve {displaced}"
                )
                if hasattr(conflict, "add_note"):
                    conflict.add_note(str(restore_error))
                raise conflict from restore_error
            raise LedgerWriteConflictError("ledger changed at the atomic displacement boundary")

        try:
            os.link(staged, path)
        except FileExistsError as exc:
            raise LedgerWriteConflictError(
                f"external writer occupied the ledger publication boundary; preserve prior generation at {displaced}"
            ) from exc
        except OSError as exc:
            try:
                _restore_posix_displaced(path, displaced)
            except LedgerWriteConflictError as restore_error:
                conflict = LedgerWriteConflictError(
                    f"ledger publication failed and prior generation could not be restored; preserve {displaced}"
                )
                if hasattr(conflict, "add_note"):
                    conflict.add_note(str(restore_error))
                raise conflict from restore_error
            raise LedgerWriteConflictError("ledger publication failed; prior generation was restored") from exc

        try:
            installed = path.read_bytes()
            displaced_after = displaced.read_bytes()
        except OSError as exc:
            try:
                rejected = _recover_posix_after_publication(path, displaced)
            except LedgerWriteConflictError as recovery_error:
                conflict = LedgerWriteConflictError(
                    f"installed or displaced ledger could not be verified; preserve {displaced}"
                )
                if hasattr(conflict, "add_note"):
                    conflict.add_note(str(recovery_error))
                raise conflict from recovery_error
            raise LedgerWriteConflictError(
                f"ledger verification failed after publication; prior generation restored; preserve {rejected}"
            ) from exc
        if installed != proposed or _sha256(displaced_after) != expected_sha256:
            try:
                rejected = _recover_posix_after_publication(path, displaced)
            except LedgerWriteConflictError as recovery_error:
                conflict = LedgerWriteConflictError(
                    f"ledger changed during final verification; preserve prior generation at {displaced}"
                )
                if hasattr(conflict, "add_note"):
                    conflict.add_note(str(recovery_error))
                raise conflict from recovery_error
            raise LedgerWriteConflictError(
                f"ledger changed during final verification; prior generation restored; preserve {rejected}"
            )
        displaced.unlink()
    except BaseException:
        # Recovery helpers consume `displaced` only after a verified restore.
        # Otherwise the file remains explicit evidence for operator recovery.
        raise


def save(path: Path, value: dict[str, Any], *, expected_sha256: str | None = None) -> None:
    """Atomically replace a ledger, optionally requiring the bytes read earlier."""
    path = Path(path)
    data = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, staged_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".ludis-stage",
        dir=path.parent,
    )
    staged = Path(staged_name)
    original_error: BaseException | None = None
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            _write_staged_bytes(handle, data)
        if expected_sha256 is None:
            os.replace(staged, path)
        elif os.name == "nt":
            _replace_expected_windows(staged, path, expected_sha256, data)
        else:
            _replace_expected_posix(staged, path, expected_sha256, data)
    except BaseException as exc:
        original_error = exc
        raise
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                if original_error is None:
                    raise
        _remove_without_masking(staged, original_error)
def ledger_lock_path(path: Path) -> Path:
    path = Path(path)
    return path.with_name(f".{path.name}.ludis-lock")


@contextmanager
def exclusive_ledger_lock(path: Path) -> Iterator[Path]:
    """Reserve one ledger for a fail-fast read-modify-write operation.

    Locks are never guessed stale or removed by a contender. Recovery therefore
    remains an explicit operator decision after checking that no writer is live.
    """
    lock = ledger_lock_path(path)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor: int | None = None
    identity: tuple[int, int] | None = None
    created = False
    operation_error: BaseException | None = None
    try:
        try:
            descriptor = os.open(lock, flags, 0o600)
        except FileExistsError as exc:
            raise LedgerBusyError(f"another Ludis writer reserved this ledger: {lock}") from exc
        created = True
        descriptor_state = os.fstat(descriptor)
        identity = (descriptor_state.st_dev, descriptor_state.st_ino)
        path_state = lock.lstat()
        if (path_state.st_dev, path_state.st_ino) != identity:
            raise RuntimeError(f"ledger lock identity changed during setup: {lock}")
        payload = f"pid={os.getpid()}\nledger={Path(path).resolve()}\n".encode("utf-8")
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise OSError(f"failed to write ledger lock metadata: {lock}")
            offset += written
        os.fsync(descriptor)
        yield lock
    except BaseException as exc:
        operation_error = exc
        raise
    finally:
        cleanup_error: BaseException | None = None
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as exc:
                cleanup_error = exc
        if created:
            try:
                current = lock.lstat()
                current_identity = (current.st_dev, current.st_ino)
                if identity is None:
                    cleanup_error = cleanup_error or RuntimeError(
                        f"cannot safely remove ledger lock without descriptor identity: {lock}"
                    )
                elif current_identity == identity:
                    lock.unlink()
                else:
                    cleanup_error = cleanup_error or RuntimeError(
                        f"ledger lock identity changed before cleanup; replacement preserved: {lock}"
                    )
            except FileNotFoundError:
                pass
            except OSError as exc:
                cleanup_error = cleanup_error or exc
        if cleanup_error is not None:
            message = f"ledger lock cleanup failed: {cleanup_error}"
            if operation_error is not None:
                if hasattr(operation_error, "add_note"):
                    operation_error.add_note(message)
            else:
                raise LedgerLockCleanupError(
                    f"ledger update may have completed, but {message}; inspect the ledger before retrying"
                ) from cleanup_error


def detect_format(value: dict[str, Any]) -> str:
    if value.get("format") == LEDGER_FORMAT_V2:
        return LEDGER_FORMAT_V2
    if value.get("ludis_version") == LEGACY_VERSION and "format" not in value:
        return "legacy_v0_1"
    return "unknown"


def is_valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value))


def campaign_id_from_seed(seed: str) -> str:
    """Return a stable campaign id from an explicit, owner-supplied seed."""
    if not isinstance(seed, str) or not seed.strip():
        raise ValueError("campaign seed must be a non-empty owner-supplied string")
    value = uuid.uuid5(uuid.NAMESPACE_URL, "cd-ludis-campaign:" + seed.strip())
    return "campaign-" + str(value)


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_id(value: Any, label: str, errors: list[str]) -> bool:
    if not _is_nonempty_string(value):
        errors.append(f"{label} required")
        return False
    if not _ID_RE.fullmatch(value):
        errors.append(f"{label} must use lowercase letters, digits, dots, underscores, or hyphens")
        return False
    return True


def _validate_string_list(value: Any, label: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not _is_nonempty_string(item):
            errors.append(f"{label}[{index}] must be a non-empty string")
        else:
            result.append(item)
    return result


def _validate_extensions(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return
    for key in value:
        if not isinstance(key, str) or not _EXTENSION_KEY_RE.fullmatch(key):
            errors.append(f"{label} key {key!r} must be namespaced")


def _unknown_fields(record: dict[str, Any], allowed: set[str], label: str, errors: list[str]) -> None:
    for key in sorted(set(record) - allowed):
        errors.append(f"{label} unknown field: {key}")


def _records(value: Any, label: str, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return []
    records: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"{label}[{index}] must be an object")
        else:
            records.append(item)
    return records


def _duplicate_ids(records: Iterable[dict[str, Any]], label: str, errors: list[str]) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(records):
        item_label = f"{label}[{index}]"
        item_id = record.get("id")
        if not _validate_id(item_id, f"{item_label}.id", errors):
            continue
        if item_id in by_id:
            errors.append(f"duplicate id: {item_id}")
        else:
            by_id[item_id] = record
    return by_id


def _validate_common_graph(
    objects: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    errors: list[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_id = _duplicate_ids(objects, "objects", errors)
    assets_by_id = _duplicate_ids(assets, "assets", errors)

    graph: dict[str, list[str]] = {}
    for index, obj in enumerate(objects):
        oid = obj.get("id")
        links = obj.get("links", [])
        if not isinstance(links, list):
            errors.append(f"objects[{index}].links must be an array")
            links = []
        clean_links: list[str] = []
        for ref in links:
            if not _is_nonempty_string(ref):
                errors.append(f"objects[{index}].links must contain non-empty ids")
            elif ref not in by_id:
                errors.append(f"broken link: {oid} -> {ref}")
            else:
                clean_links.append(ref)
        if isinstance(oid, str):
            graph[oid] = clean_links

        asset_ids = obj.get("asset_ids", [])
        if not isinstance(asset_ids, list):
            errors.append(f"objects[{index}].asset_ids must be an array")
            asset_ids = []
        for asset_id in asset_ids:
            if not _is_nonempty_string(asset_id):
                errors.append(f"objects[{index}].asset_ids must contain non-empty ids")
            elif asset_id not in assets_by_id:
                errors.append(f"broken asset link: {oid} -> {asset_id}")
            elif obj.get("visibility") == "player_safe" and assets_by_id[asset_id].get("visibility") == "gm_only":
                errors.append(f"spoiler asset link: {oid} -> {asset_id}")

    # A player-safe record cannot reach a secret through a chain that happens to
    # pass through another player-safe record. This is still a structural guard,
    # not a claim that free text contains no spoilers.
    for oid, obj in by_id.items():
        if obj.get("visibility") != "player_safe":
            continue
        pending = [(ref, [oid, ref]) for ref in graph.get(oid, [])]
        visited: set[str] = set()
        while pending:
            ref, path = pending.pop()
            if ref in visited:
                continue
            visited.add(ref)
            target = by_id.get(ref)
            if target is None:
                continue
            if target.get("visibility") == "gm_only":
                errors.append("spoiler link: " + " -> ".join(path))
                continue
            pending.extend((child, path + [child]) for child in graph.get(ref, []))

    return by_id, assets_by_id


def _validate_sessions(sessions: list[dict[str, Any]], errors: list[str], strict_v2: bool) -> None:
    if strict_v2:
        allowed = {"id", "scheduled_for", "status", "title", "notes", "links", "data", "extensions"}
        _duplicate_ids(sessions, "sessions", errors)
    seen: dict[str, Any] = {}
    for index, session in enumerate(sessions):
        label = f"sessions[{index}]"
        if strict_v2:
            _unknown_fields(session, allowed, label, errors)
            if "extensions" in session:
                _validate_extensions(session["extensions"], f"{label}.extensions", errors)
            if "data" in session and not isinstance(session["data"], dict):
                errors.append(f"{label}.data must be an object")
            if "links" in session:
                _validate_string_list(session["links"], f"{label}.links", errors)
        when = session.get("scheduled_for")
        if when is not None and not isinstance(when, str):
            errors.append(f"{label}.scheduled_for must be a string or null")
        if when:
            if when in seen:
                errors.append(f"session collision: {seen[when]} and {session.get('id')} at {when}")
            else:
                seen[when] = session.get("id")


def _validate_legacy(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("ludis_version", "campaign", "table_contract", "objects", "sessions", "approvals", "publication"):
        if key not in value:
            errors.append(f"missing top-level field: {key}")
    if value.get("ludis_version") != LEGACY_VERSION:
        errors.append(f"ludis_version must be {LEGACY_VERSION}")

    raw_objects = value.get("objects", [])
    objects = _records(raw_objects, "objects", errors)
    by_id = _duplicate_ids(objects, "objects", errors)
    for index, obj in enumerate(objects):
        label = f"objects[{index}]"
        for field in ("kind", "status", "visibility", "authority", "provenance", "confidence", "tenure"):
            if field not in obj:
                errors.append(f"{label} missing {field}")
        if obj.get("status") not in STATUSES:
            errors.append(f"{label}.status invalid")
        if obj.get("visibility") not in VISIBILITY:
            errors.append(f"{label}.visibility invalid")
        if obj.get("status") == "active_canon" and obj.get("authority") != "gm_approved":
            errors.append(f"{label} active canon requires gm_approved authority")
        links = obj.get("links", [])
        if not isinstance(links, list):
            errors.append(f"{label}.links must be an array")
            continue
        for ref in links:
            if not _is_nonempty_string(ref):
                errors.append(f"{label}.links must contain non-empty ids")
            elif ref not in by_id:
                errors.append(f"broken link: {obj.get('id')} -> {ref}")
            elif obj.get("visibility") == "player_safe" and by_id[ref].get("visibility") == "gm_only":
                errors.append(f"spoiler link: {obj.get('id')} -> {ref}")

    sessions = _records(value.get("sessions", []), "sessions", errors)
    _validate_sessions(sessions, errors, strict_v2=False)
    if not isinstance(value.get("campaign"), dict):
        errors.append("campaign must be an object")
    if not isinstance(value.get("table_contract"), dict):
        errors.append("table_contract must be an object")
    if not isinstance(value.get("approvals"), list):
        errors.append("approvals must be an array")
    if not isinstance(value.get("publication"), dict):
        errors.append("publication must be an object")
    return errors


def _validate_v2(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {"format", "campaign", "table_contract", "objects", "assets", "sessions", "approvals", "publication", "extensions"}
    allowed = required | {"producer", "updated", "next_prep"}
    for key in sorted(required):
        if key not in value:
            errors.append(f"missing top-level field: {key}")
    _unknown_fields(value, allowed, "ledger", errors)
    if value.get("format") != LEDGER_FORMAT_V2:
        errors.append(f"format must be {LEDGER_FORMAT_V2}")

    if "producer" in value:
        producer = value["producer"]
        if not isinstance(producer, dict):
            errors.append("producer must be an object")
        else:
            _unknown_fields(producer, {"name", "version", "extensions"}, "producer", errors)
            if not _is_nonempty_string(producer.get("name")):
                errors.append("producer.name required")
            if not _is_nonempty_string(producer.get("version")):
                errors.append("producer.version required")
            if "extensions" in producer:
                _validate_extensions(producer["extensions"], "producer.extensions", errors)

    campaign = value.get("campaign")
    if not isinstance(campaign, dict):
        errors.append("campaign must be an object")
    else:
        campaign_allowed = {"id", "title", "premise", "system", "edition", "tier", "current_horizon", "data", "extensions"}
        _unknown_fields(campaign, campaign_allowed, "campaign", errors)
        _validate_id(campaign.get("id"), "campaign.id", errors)
        for field in ("title", "premise", "system", "edition", "tier", "current_horizon"):
            if field in campaign and campaign[field] is not None and not isinstance(campaign[field], str):
                errors.append(f"campaign.{field} must be a string or null")
        if "data" in campaign and not isinstance(campaign["data"], dict):
            errors.append("campaign.data must be an object")
        if "extensions" in campaign:
            _validate_extensions(campaign["extensions"], "campaign.extensions", errors)

    table_contract = value.get("table_contract")
    if not isinstance(table_contract, dict):
        errors.append("table_contract must be an object")
    else:
        tc_allowed = {"player_preferences", "lines", "veils", "other_boundaries", "data", "extensions"}
        _unknown_fields(table_contract, tc_allowed, "table_contract", errors)
        for field in ("player_preferences", "lines", "veils", "other_boundaries"):
            if field not in table_contract:
                errors.append(f"table_contract missing {field}")
            else:
                _validate_string_list(table_contract[field], f"table_contract.{field}", errors)
        if "data" in table_contract and not isinstance(table_contract["data"], dict):
            errors.append("table_contract.data must be an object")
        if "extensions" in table_contract:
            _validate_extensions(table_contract["extensions"], "table_contract.extensions", errors)

    objects = _records(value.get("objects", []), "objects", errors)
    assets = _records(value.get("assets", []), "assets", errors)
    by_id, assets_by_id = _validate_common_graph(objects, assets, errors)

    object_allowed = {
        "id", "kind", "status", "visibility", "authority", "provenance", "confidence", "tenure",
        "title", "summary", "content", "claims", "links", "asset_ids", "contradicts", "tags",
        "export_eligibility", "data", "extensions",
    }
    for index, obj in enumerate(objects):
        label = f"objects[{index}]"
        _unknown_fields(obj, object_allowed, label, errors)
        for field in ("kind", "status", "visibility", "authority", "provenance", "confidence", "tenure", "links", "asset_ids", "export_eligibility"):
            if field not in obj:
                errors.append(f"{label} missing {field}")
        kind = obj.get("kind")
        if not _is_nonempty_string(kind) or not _ID_RE.fullmatch(kind):
            errors.append(f"{label}.kind invalid")
        if obj.get("status") not in STATUSES:
            errors.append(f"{label}.status invalid")
        if obj.get("visibility") not in VISIBILITY:
            errors.append(f"{label}.visibility invalid")
        if not _is_nonempty_string(obj.get("authority")):
            errors.append(f"{label}.authority required")
        _validate_string_list(obj.get("provenance"), f"{label}.provenance", errors)
        if obj.get("confidence") not in CONFIDENCE:
            errors.append(f"{label}.confidence invalid")
        if not _is_nonempty_string(obj.get("tenure")):
            errors.append(f"{label}.tenure required")
        if obj.get("status") == "active_canon" and obj.get("authority") != "gm_approved":
            errors.append(f"{label} active canon requires gm_approved authority")
        eligibility = obj.get("export_eligibility")
        if eligibility not in EXPORT_ELIGIBILITY:
            errors.append(f"{label}.export_eligibility invalid")
        if kind not in KNOWN_OBJECT_KINDS and eligibility != "quarantined_unmapped":
            errors.append(f"{label} unknown kind must be quarantined_unmapped")
        for field in ("claims", "contradicts", "tags"):
            if field in obj:
                _validate_string_list(obj[field], f"{label}.{field}", errors)
        for field in ("title", "summary", "content"):
            if field in obj and obj[field] is not None and not isinstance(obj[field], str):
                errors.append(f"{label}.{field} must be a string or null")
        if "data" in obj and not isinstance(obj["data"], dict):
            errors.append(f"{label}.data must be an object")
        if "extensions" in obj:
            _validate_extensions(obj["extensions"], f"{label}.extensions", errors)

    asset_allowed = {"id", "path", "kind", "media_type", "visibility", "rights", "provenance", "alt_text", "sha256", "data", "extensions"}
    for index, asset in enumerate(assets):
        label = f"assets[{index}]"
        _unknown_fields(asset, asset_allowed, label, errors)
        for field in ("path", "kind", "visibility", "rights", "provenance"):
            if field not in asset:
                errors.append(f"{label} missing {field}")
        if not _is_nonempty_string(asset.get("path")):
            errors.append(f"{label}.path required")
        elif Path(asset["path"]).is_absolute() or ".." in Path(asset["path"]).parts:
            errors.append(f"{label}.path must stay relative to the campaign root")
        if not _is_nonempty_string(asset.get("kind")):
            errors.append(f"{label}.kind required")
        if asset.get("visibility") not in VISIBILITY:
            errors.append(f"{label}.visibility invalid")
        _validate_string_list(asset.get("provenance"), f"{label}.provenance", errors)
        rights = asset.get("rights")
        if not isinstance(rights, dict):
            errors.append(f"{label}.rights must be an object")
        else:
            _unknown_fields(rights, {"status", "license", "credit", "source", "extensions"}, f"{label}.rights", errors)
            if rights.get("status") not in RIGHTS_STATUS:
                errors.append(f"{label}.rights.status invalid")
            for field in ("license", "credit", "source"):
                if field in rights and rights[field] is not None and not isinstance(rights[field], str):
                    errors.append(f"{label}.rights.{field} must be a string or null")
            if "extensions" in rights:
                _validate_extensions(rights["extensions"], f"{label}.rights.extensions", errors)
        if "sha256" in asset and (not isinstance(asset["sha256"], str) or not _SHA256_RE.fullmatch(asset["sha256"])):
            errors.append(f"{label}.sha256 must be lowercase SHA-256")
        if "alt_text" in asset and asset["alt_text"] is not None and not isinstance(asset["alt_text"], str):
            errors.append(f"{label}.alt_text must be a string or null")
        if "data" in asset and not isinstance(asset["data"], dict):
            errors.append(f"{label}.data must be an object")
        if "extensions" in asset:
            _validate_extensions(asset["extensions"], f"{label}.extensions", errors)

    sessions = _records(value.get("sessions", []), "sessions", errors)
    _validate_sessions(sessions, errors, strict_v2=True)

    approvals = _records(value.get("approvals", []), "approvals", errors)
    for index, approval in enumerate(approvals):
        label = f"approvals[{index}]"
        action = approval.get("action")
        if action == "promote_canon":
            _unknown_fields(approval, {"id", "object_id", "action", "at", "asserted_by", "extensions"}, label, errors)
            if not _is_nonempty_string(approval.get("object_id")):
                errors.append(f"{label}.object_id required")
            elif approval["object_id"] not in by_id:
                errors.append(f"{label}.object_id references missing object")
        elif action == "exact_candidate_approved":
            allowed_approval = {"id", "action", "run_id", "audience", "candidate_sha256", "preview_sha256", "asserted_by", "asserted_at", "extensions"}
            _unknown_fields(approval, allowed_approval, label, errors)
            for field in ("id", "run_id", "audience", "candidate_sha256", "preview_sha256", "asserted_by", "asserted_at"):
                if not _is_nonempty_string(approval.get(field)):
                    errors.append(f"{label}.{field} required")
            for field in ("candidate_sha256", "preview_sha256"):
                digest = approval.get(field)
                if isinstance(digest, str) and not _SHA256_RE.fullmatch(digest):
                    errors.append(f"{label}.{field} must be lowercase SHA-256")
        else:
            errors.append(f"{label}.action invalid")
        if "extensions" in approval:
            _validate_extensions(approval["extensions"], f"{label}.extensions", errors)

    publication = value.get("publication")
    if not isinstance(publication, dict):
        errors.append("publication must be an object")
    else:
        _unknown_fields(publication, {"status", "candidate_sha256", "published_at", "extensions"}, "publication", errors)
        if publication.get("status") not in {"private_draft", "candidate", "approved", "published", "archived"}:
            errors.append("publication.status invalid")
        if "candidate_sha256" in publication and (not isinstance(publication["candidate_sha256"], str) or not _SHA256_RE.fullmatch(publication["candidate_sha256"])):
            errors.append("publication.candidate_sha256 must be lowercase SHA-256")
        if "extensions" in publication:
            _validate_extensions(publication["extensions"], "publication.extensions", errors)

    if "next_prep" in value:
        _validate_string_list(value["next_prep"], "next_prep", errors)
    if "updated" in value and value["updated"] is not None and not isinstance(value["updated"], str):
        errors.append("updated must be a string or null")
    if "extensions" in value:
        _validate_extensions(value["extensions"], "extensions", errors)
    return errors


def validate(value: dict[str, Any]) -> list[str]:
    if not isinstance(value, dict):
        return ["ledger root must be an object"]
    ledger_format = detect_format(value)
    if ledger_format == "legacy_v0_1":
        return _validate_legacy(value)
    if ledger_format == LEDGER_FORMAT_V2:
        return _validate_v2(value)
    return [f"unrecognized ledger format; expected ludis_version {LEGACY_VERSION} or format {LEDGER_FORMAT_V2}"]
