"""Runtime primitives for Nova Commonplace's canonical filesystem store.

The canonical store deliberately uses immutable JSON snapshots and a digest-bound
CURRENT pointer.  This module contains the small, stdlib-only substrate needed by
that design: strict JSON, atomic replacement, path confinement, and a portable
exclusive lock.
"""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import AbstractContextManager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import socket
import stat
import time
from typing import Any
from uuid import uuid4


class CommonplaceError(Exception):
    """Base class for public Commonplace failures."""


class ValidationError(CommonplaceError):
    """Input or persisted data failed schema validation."""


class ConflictError(CommonplaceError):
    """A compare-and-swap or uniqueness precondition failed."""


class IntegrityError(CommonplaceError):
    """Persisted state did not match its cryptographic bindings."""


class NotInitializedError(CommonplaceError):
    """The selected store has not been initialized."""


class AlreadyInitializedError(CommonplaceError):
    """The selected store is already initialized."""


class LockTimeoutError(CommonplaceError):
    """The filesystem transaction lock could not be acquired in time."""


class ConfinementError(CommonplaceError):
    """A caller tried to escape the configured store root."""


class AntiResurrectionError(IntegrityError):
    """Candidate state contains an identifier covered by a forget marker."""


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def utc_now() -> str:
    """Return a canonical, second-resolution UTC timestamp."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_timestamp(value: Any, *, field: str, optional: bool = True) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{field} must be a non-empty RFC 3339 timestamp")
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError(f"{field} must be an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValidationError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise IntegrityError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> Any:
    raise IntegrityError(f"non-finite JSON number is not allowed: {value}")


def load_json_bytes(data: bytes, *, source: str = "JSON") -> Any:
    try:
        return json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except UnicodeDecodeError as exc:
        raise IntegrityError(f"{source} is not UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise IntegrityError(f"{source} is not valid JSON: {exc}") from exc


def read_json(path: Path) -> Any:
    try:
        return load_json_bytes(path.read_bytes(), source=str(path))
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise IntegrityError(f"could not read {path}: {exc}") from exc


def _reject_nonfinite(value: Any, *, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValidationError(f"{path} contains a non-finite number")
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValidationError(f"{path} contains a non-string object key")
            _reject_nonfinite(child, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_nonfinite(child, path=f"{path}[{index}]")
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise ValidationError(f"{path} contains unsupported type {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    """Encode stable JSON used both on disk and for digest calculation."""
    _reject_nonfinite(value)
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"value is not canonical-JSON encodable: {exc}") from exc
    return text.encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_object(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def opaque_identifier(identifier: str) -> str:
    """One-way marker for anti-resurrection checks without retaining the identifier."""
    return sha256_bytes(("nova-commonplace-id-v1\0" + identifier).encode("utf-8"))


def validate_component(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not _SAFE_COMPONENT.fullmatch(value):
        raise ValidationError(
            f"{field} must be 1-128 characters using letters, digits, dot, underscore, or hyphen"
        )
    return value


def normalize_authority(value: str | Mapping[str, Any]) -> dict[str, Any]:
    """Normalize transaction authority supplied by the trusted caller.

    Record payloads never participate in this function.  Captured text can say
    anything; it remains data and cannot confer mutation authority.
    """
    if isinstance(value, str):
        value = {"actor": value, "source": "runtime-api"}
    if not isinstance(value, Mapping):
        raise ValidationError("authority must be a string or object")
    authority = dict(value)
    allowed = {"actor", "source", "reason", "correlation_id"}
    unknown = set(authority) - allowed
    if unknown:
        raise ValidationError(f"authority contains unsupported fields: {sorted(unknown)}")
    for field in ("actor", "source"):
        if not isinstance(authority.get(field), str) or not authority[field].strip():
            raise ValidationError(f"authority.{field} is required")
        authority[field] = authority[field].strip()
    for field in ("reason", "correlation_id"):
        if field in authority:
            if not isinstance(authority[field], str) or not authority[field].strip():
                raise ValidationError(f"authority.{field} must be a non-empty string")
            authority[field] = authority[field].strip()
    canonical_json_bytes(authority)
    return authority


_REPARSE_ATTRIBUTE = 0x400


def _absolute_lexical(path: str | os.PathLike[str]) -> Path:
    return Path(os.path.abspath(os.fspath(Path(path).expanduser())))


def _assert_safe_edges(path: Path, *, stop: Path | None = None) -> None:
    current = _absolute_lexical(path)
    boundary = _absolute_lexical(stop) if stop is not None else None
    while True:
        if os.path.lexists(current):
            observed = os.lstat(current)
            if stat.S_ISLNK(observed.st_mode):
                raise ConfinementError(f"path crosses a symbolic link: {current}")
            if getattr(observed, "st_file_attributes", 0) & _REPARSE_ATTRIBUTE:
                raise ConfinementError(f"path crosses a reparse edge: {current}")
        if current == boundary or current.parent == current:
            break
        current = current.parent


class PathPolicy:
    """Resolve all service-owned paths beneath one immutable link-safe root."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        lexical = _absolute_lexical(root)
        _assert_safe_edges(lexical)
        self.root = lexical.resolve(strict=False)

    def confined(self, *parts: str) -> Path:
        candidate = self.root
        for part in parts:
            if not isinstance(part, str) or not part or Path(part).is_absolute():
                raise ConfinementError("path components must be non-empty and relative")
            candidate = candidate / part
        _assert_safe_edges(candidate, stop=self.root)
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise ConfinementError(f"path escapes store root: {resolved}") from exc
        return resolved

    def assert_confined(self, path: Path) -> Path:
        lexical = _absolute_lexical(path)
        _assert_safe_edges(lexical, stop=self.root)
        resolved = lexical.resolve(strict=False)
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise ConfinementError(f"path escapes store root: {resolved}") from exc
        return resolved


def _fsync_directory(path: Path) -> None:
    # Opening directories for fsync is not supported on all Windows builds.
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def atomic_write(path: Path, data: bytes) -> None:
    """Write bytes via same-directory temporary file and atomic replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{uuid4().hex}")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write(path, canonical_json_bytes(value))


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        # On Windows, access behavior varies.  Err toward preserving the lock.
        return True
    return True


class FileLock(AbstractContextManager["FileLock"]):
    """Cross-platform lock based on exclusive file creation.

    Lock ownership is token-bound.  A crashed lock is reclaimed only when it is
    old *and* its originating process can be shown not to exist.
    """

    def __init__(
        self,
        path: Path,
        *,
        timeout: float = 10.0,
        poll_interval: float = 0.05,
        stale_after: float = 300.0,
    ) -> None:
        self.path = path
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.stale_after = stale_after
        self.token = uuid4().hex
        self._held = False

    def _try_reclaim_stale(self) -> bool:
        try:
            payload = read_json(self.path)
            created = float(payload["created_epoch"])
            pid = int(payload["pid"])
        except (FileNotFoundError, KeyError, TypeError, ValueError, IntegrityError):
            return False
        if time.time() - created <= self.stale_after or _pid_alive(pid):
            return False
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        return True

    def acquire(self) -> "FileLock":
        deadline = time.monotonic() + self.timeout
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = canonical_json_bytes(
            {
                "schema": "nova-commonplace.lock.v1",
                "token": self.token,
                "pid": os.getpid(),
                "host": socket.gethostname(),
                "created_epoch": time.time(),
            }
        )
        while True:
            try:
                descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                self._try_reclaim_stale()
                if time.monotonic() >= deadline:
                    raise LockTimeoutError(f"timed out acquiring {self.path}")
                time.sleep(self.poll_interval)
                continue
            try:
                os.write(descriptor, payload)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            self._held = True
            return self

    def release(self) -> None:
        if not self._held:
            return
        try:
            payload = read_json(self.path)
            if payload.get("token") != self.token:
                raise IntegrityError("transaction lock ownership changed unexpectedly")
            self.path.unlink()
        except FileNotFoundError:
            raise IntegrityError("transaction lock disappeared before release")
        finally:
            self._held = False

    def __enter__(self) -> "FileLock":
        return self.acquire()

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.release()