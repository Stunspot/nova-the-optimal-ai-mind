"""Read the known Personal AI Archive through small, private immutable snapshots.

Only ``root/rag/archive-current.sqlite3`` is recognized. Source database bytes
and sidecars are never opened for writing. Returned locators use archive-owned
source/external_id/ordinal identities, never implementation row IDs.
"""
from __future__ import annotations

import atexit
from collections import OrderedDict
from datetime import datetime, timezone
import hashlib
import os
import stat
from pathlib import Path
import re
import secrets
import sqlite3
import tempfile
import threading
from typing import Callable

MAX_DATABASE_BYTES = 256 * 1024 * 1024
MAX_RECORD_CHARACTERS = 32768
MAX_SNAPSHOTS = 2
SCHEMA = "personal-ai-archive/giles-reader/v1"


class ArchiveReadError(ValueError):
    """The registered archive cannot safely satisfy the requested read."""


class ArchiveStaleError(ArchiveReadError):
    """An explicit snapshot no longer describes the registered source."""


class _Snapshot:
    def __init__(self, source: Path, signature: tuple, directory, copied: Path, digest: str):
        self.source = source
        self.signature = signature
        self.directory = directory
        self.copied = copied
        self.digest = digest
        self.token = secrets.token_urlsafe(24)
        self.created_at = datetime.now(timezone.utc).isoformat()

    def close(self):
        self.directory.cleanup()


_CACHE: OrderedDict[str, _Snapshot] = OrderedDict()
_LOCK = threading.RLock()


def _clear_cache():
    """Release private copies; also used by isolated adapter tests."""
    with _LOCK:
        for cached in _CACHE.values():
            cached.close()
        _CACHE.clear()


atexit.register(_clear_cache)


def _linked(path: Path) -> bool:
    if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
        return True
    try:
        attributes = getattr(os.lstat(path), "st_file_attributes", 0)
        return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    except FileNotFoundError:
        return False


def detect(root) -> Path | None:
    """Return the confined known path; reject linked roots, rag folders and DBs."""
    try:
        requested = Path(root).expanduser().absolute()
        if any(_linked(path) for path in (requested, requested / "rag", requested / "rag" / "archive-current.sqlite3")):
            return None
        base = requested.resolve()
        candidate = base / "rag" / "archive-current.sqlite3"
        resolved = candidate.resolve()
        resolved.relative_to(base)
        return resolved if resolved.is_file() else None
    except (OSError, TypeError, ValueError):
        return None


def _stat_signature(path: Path) -> tuple:
    info = path.stat()
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _sidecars_safe(source: Path):
    for suffix in ("-wal", "-journal"):
        sidecar = Path(str(source) + suffix)
        try:
            if sidecar.exists() and sidecar.stat().st_size:
                raise ArchiveReadError(
                    f"Archive has a nonempty {suffix[1:]} sidecar. Ask the archive owner "
                    "to finish/checkpoint its writes, then deliberately refresh. "
                    "Giles will not change the original database or sidecars."
                )
        except OSError as exc:
            raise ArchiveReadError("Archive sidecar state could not be inspected.") from exc


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _connect(path: Path):
    connection = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    connection.execute("PRAGMA trusted_schema=OFF")
    return connection


def _known_schema(connection):
    required = {
        "documents": {"id", "source", "external_id", "title", "created_at", "source_path", "metadata_json", "ingested_at"},
        "chunks": {"id", "document_id", "ordinal", "role", "created_at", "content"},
    }
    for table, columns in required.items():
        definition = connection.execute("SELECT type,sql FROM sqlite_master WHERE name=?", (table,)).fetchone()
        if definition is None or definition["type"] != "table" or re.search(r"\bVIRTUAL\s+TABLE\b", definition["sql"] or "", re.IGNORECASE):
            raise ArchiveReadError(f"Unsupported archive schema: {table} must be an ordinary table.")
        actual = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
        if not columns.issubset(actual):
            raise ArchiveReadError(f"Unsupported archive schema: {table} lacks expected columns.")
    row = connection.execute("SELECT sql FROM sqlite_master WHERE name='chunks_fts' AND type='table'").fetchone()
    definition = (row["sql"] if row else "") or ""
    if not re.search(r"\bUSING\s+fts5\s*\(", definition, re.IGNORECASE):
        raise ArchiveReadError("Unsupported archive schema: chunks_fts must be FTS5.")
    if not re.search(r"\bcontent\s*=\s*['\"]chunks['\"]", definition, re.IGNORECASE):
        raise ArchiveReadError("Unsupported archive schema: chunks_fts must index external chunks content.")
    fts_columns = {row["name"] for row in connection.execute("PRAGMA table_info(chunks_fts)")}
    if "content" not in fts_columns:
        raise ArchiveReadError("Unsupported archive schema: chunks_fts lacks content.")


def _assert_current(cached: _Snapshot):
    try:
        _sidecars_safe(cached.source)
        if _stat_signature(cached.source) != cached.signature:
            raise ArchiveStaleError("Archive changed since this snapshot. Deliberately refresh before continuing.")
    except OSError as exc:
        raise ArchiveStaleError("Archive source is no longer available. Deliberately refresh.") from exc
    try:
        digest = _digest(cached.copied)
    except OSError as exc:
        raise ArchiveStaleError("Private archive snapshot is unavailable. Deliberately refresh.") from exc
    if digest != cached.digest:
        raise ArchiveStaleError("Private archive snapshot changed. Deliberately refresh.")


def _make_snapshot(source: Path) -> _Snapshot:
    _sidecars_safe(source)
    before = _stat_signature(source)
    if before[2] > MAX_DATABASE_BYTES:
        raise ArchiveReadError("Archive database exceeds the 256 MB snapshot limit. Use its owner's retrieval tools.")
    directory = tempfile.TemporaryDirectory(prefix="giles-archive-read-")
    copied = Path(directory.name) / "archive.sqlite3"
    try:
        identity = hashlib.sha256()
        total = 0
        with source.open("rb") as incoming, copied.open("xb") as outgoing:
            for block in iter(lambda: incoming.read(1024 * 1024), b""):
                total += len(block)
                if total > MAX_DATABASE_BYTES:
                    raise ArchiveReadError("Archive grew beyond the 256 MB snapshot limit during copying.")
                outgoing.write(block)
                identity.update(block)
        _sidecars_safe(source)
        after = _stat_signature(source)
        digest = identity.hexdigest()
        if after != before or total != before[2]:
            raise ArchiveStaleError("Archive changed while being copied. Finish its writes and deliberately refresh.")
        if _digest(copied) != digest:
            raise ArchiveReadError("Private archive snapshot did not preserve the copied bytes.")
        connection = _connect(copied)
        try:
            _known_schema(connection)
        finally:
            connection.close()
        cached = _Snapshot(source, before, directory, copied, digest)
        _assert_current(cached)
        return cached
    except BaseException:
        directory.cleanup()
        raise


def _choose(root, token) -> _Snapshot:
    source = detect(root)
    if source is None:
        if token is not None:
            raise ArchiveStaleError("Archive source is unavailable or no longer confined to its registered root. Deliberately refresh.")
        raise ArchiveReadError("The registered root has no supported rag/archive-current.sqlite3 database.")
    if token is not None:
        if not isinstance(token, str) or token not in _CACHE:
            raise ArchiveStaleError("Archive snapshot is no longer cached. Deliberately refresh.")
        cached = _CACHE[token]
        if cached.source != source:
            raise ArchiveStaleError("Archive snapshot belongs to a different registered root. Deliberately refresh.")
        _assert_current(cached)
        _CACHE.move_to_end(token)
        return cached
    signature = _stat_signature(source)
    for key, cached in list(_CACHE.items()):
        if cached.source == source and cached.signature == signature:
            try:
                _assert_current(cached)
            except ArchiveStaleError:
                _CACHE.pop(key).close()
                continue
            _CACHE.move_to_end(key)
            return cached
    cached = _make_snapshot(source)
    _CACHE[cached.token] = cached
    while len(_CACHE) > MAX_SNAPSHOTS:
        _, expired = _CACHE.popitem(last=False)
        expired.close()
    return cached


def _snapshot_fields(cached: _Snapshot) -> dict:
    return {
        "schema": SCHEMA,
        "snapshot": cached.token,
        "snapshot_identity": cached.digest,
        "snapshot_created_at": cached.created_at,
        "source_database": str(cached.source),
        "source_modified_at": datetime.fromtimestamp(cached.signature[3] / 1e9, timezone.utc).isoformat(),
    }


def _read(root, snapshot, operation: Callable):
    with _LOCK:
        try:
            cached = _choose(root, snapshot)
            connection = _connect(cached.copied)
            try:
                result = operation(connection, cached)
            finally:
                connection.close()
            _assert_current(cached)
            return result
        except ArchiveReadError:
            raise
        except (OSError, sqlite3.Error, UnicodeError, TypeError) as exc:
            raise ArchiveReadError(f"Could not read the known archive: {exc}") from exc


def summary(root) -> dict:
    """Return known archive counts and the identity/time of their private snapshot."""
    def operation(connection, cached):
        return dict(_snapshot_fields(cached),
                    document_count=connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
                    chunk_count=connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
    return _read(root, None, operation)


_COLUMNS = "d.source,d.external_id,d.title,d.created_at AS document_created_at,d.source_path,d.ingested_at,c.ordinal,c.role,c.created_at"


def _locator(row) -> dict:
    source, external_id, ordinal = row["source"], row["external_id"], row["ordinal"]
    if not isinstance(source, str) or not isinstance(external_id, str) or not isinstance(ordinal, int) or ordinal < 0:
        raise ArchiveReadError("Archive record has no supported stable source/external_id/ordinal locator.")
    return {"source": source, "external_id": external_id, "ordinal": ordinal}


def _record_fields(row) -> dict:
    return {
        "locator": _locator(row), "title": row["title"], "role": row["role"],
        "created_at": row["created_at"], "document_created_at": row["document_created_at"],
        "ingested_at": row["ingested_at"], "recorded_source_path": row["source_path"],
    }


def _integer(value, name, minimum=0, maximum=None):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum or (maximum is not None and value > maximum):
        raise ArchiveReadError(f"{name} must be an integer from {minimum}" + (f" through {maximum}." if maximum is not None else "."))


def _literal_query(query: str) -> str | None:
    terms = re.findall(r"\w+", query, flags=re.UNICODE)
    if len(terms) > 32:
        raise ArchiveReadError("Archive search accepts at most 32 literal terms.")
    return " AND ".join('"' + term.replace('"', '""') + '"' for term in terms) or None


def search(root, query, limit=20, snapshot=None) -> dict:
    """Search FTS content with literal terms; a blank query shows recent records."""
    if not isinstance(query, str) or len(query) > 2048:
        raise ArchiveReadError("Archive search query must be text of at most 2048 characters.")
    _integer(limit, "limit", 1, 100)
    expression = _literal_query(query)
    def operation(connection, cached):
        if query.strip() and expression is None:
            rows = []
        elif expression:
            sql = ("SELECT " + _COLUMNS + ",snippet(chunks_fts,-1,'','',' … ',32) AS snippet "
                   "FROM chunks_fts JOIN chunks c ON c.id=chunks_fts.rowid JOIN documents d ON d.id=c.document_id "
                   "WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts),d.source,d.external_id,c.ordinal LIMIT ?")
            rows = connection.execute(sql, (expression, limit)).fetchall()
        else:
            sql = ("SELECT " + _COLUMNS + ",substr(c.content,1,512) AS snippet FROM chunks c JOIN documents d ON d.id=c.document_id "
                   "ORDER BY COALESCE(c.created_at,d.created_at,'') DESC,d.source,d.external_id,c.ordinal LIMIT ?")
            rows = connection.execute(sql, (limit,)).fetchall()
        hits = []
        for row in rows:
            fields = _record_fields(row)
            fields["snippet"] = (row["snippet"] or "")[:4096]
            fields["anchor"] = dict(fields["locator"], snapshot=cached.token, offset=0)
            hits.append(fields)
        return dict(_snapshot_fields(cached), query=query, hits=hits)
    return _read(root, snapshot, operation)


def record(root, source, external_id, ordinal, offset=0, snapshot=None) -> dict:
    """Read one stable chunk as an exact, bounded Unicode page with fingerprints."""
    for value, name in ((source, "source"), (external_id, "external_id")):
        if not isinstance(value, str) or not value or len(value) > 2048:
            raise ArchiveReadError(f"{name} must be nonempty text of at most 2048 characters.")
    _integer(ordinal, "ordinal")
    _integer(offset, "offset")
    def operation(connection, cached):
        rows = connection.execute(
            "SELECT " + _COLUMNS + ",c.content FROM chunks c JOIN documents d ON d.id=c.document_id "
            "WHERE d.source=? AND d.external_id=? AND c.ordinal=? LIMIT 2", (source, external_id, ordinal)).fetchall()
        if not rows:
            raise ArchiveReadError("No archive record matches that stable source/external_id/ordinal locator.")
        if len(rows) != 1:
            raise ArchiveReadError("Archive stable locator is ambiguous; its owner must resolve duplicate records.")
        row = rows[0]
        content = row["content"]
        if not isinstance(content, str):
            raise ArchiveReadError("Archive chunk content is not supported Unicode text.")
        if offset > len(content):
            raise ArchiveReadError("Record offset lies beyond the current chunk content.")
        page = content[offset:offset + MAX_RECORD_CHARACTERS]
        next_offset = offset + len(page) if offset + len(page) < len(content) else None
        fields = _record_fields(row)
        anchor = dict(fields["locator"], snapshot=cached.token, offset=offset)
        return dict(_snapshot_fields(cached), **fields, format="archive", content=page,
                    offset=offset, next_offset=next_offset, full_char_count=len(content),
                    truncated=next_offset is not None, anchor=anchor, source_fingerprint=cached.digest,
                    content_fingerprint=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    sample_sha256=hashlib.sha256(page.encode("utf-8")).hexdigest())
    return _read(root, snapshot, operation)


def browse_documents(root, offset=0, limit=40, snapshot=None):
    """Browse conversations/documents by title without requiring a remembered query."""
    _integer(offset, "offset")
    _integer(limit, "limit", 1, 100)
    def operation(connection, cached):
        total = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        rows = connection.execute("SELECT d.source,d.external_id,d.title,d.created_at,"
            "(SELECT COUNT(*) FROM chunks c WHERE c.document_id=d.id) AS part_count "
            "FROM documents d ORDER BY COALESCE(d.created_at,'') DESC,d.source,d.external_id LIMIT ? OFFSET ?",
            (limit, offset)).fetchall()
        documents = [dict(row) for row in rows]
        return dict(_snapshot_fields(cached), documents=documents, offset=offset, total=total,
                    next_offset=offset+limit if offset+limit<total else None)
    return _read(root, snapshot, operation)


def document_records(root, source, external_id, offset=0, limit=40, snapshot=None):
    """Browse the ordered messages/parts in a preserved document."""
    for value, name in ((source, "source"), (external_id, "external_id")):
        if not isinstance(value, str) or not value or len(value)>2048:
            raise ArchiveReadError(f"{name} must be nonempty text of at most 2048 characters.")
    _integer(offset, "offset")
    _integer(limit, "limit", 1, 100)
    def operation(connection, cached):
        matches = connection.execute("SELECT id,title FROM documents WHERE source=? AND external_id=? LIMIT 2",
                                     (source, external_id)).fetchall()
        if len(matches)!=1:
            raise ArchiveReadError("Document locator is missing or ambiguous.")
        total = connection.execute("SELECT COUNT(*) FROM chunks WHERE document_id=?", (matches[0]['id'],)).fetchone()[0]
        rows = connection.execute("SELECT " + _COLUMNS + ",substr(c.content,1,512) AS snippet "
            "FROM chunks c JOIN documents d ON d.id=c.document_id WHERE d.source=? AND d.external_id=? "
            "ORDER BY c.ordinal LIMIT ? OFFSET ?", (source, external_id, limit, offset)).fetchall()
        hits = []
        for row in rows:
            fields = _record_fields(row)
            fields['snippet'] = row['snippet'] or ''
            fields['anchor'] = dict(fields['locator'], snapshot=cached.token, offset=0)
            hits.append(fields)
        return dict(_snapshot_fields(cached), title=matches[0]['title'], hits=hits, offset=offset, total=total,
                    next_offset=offset+limit if offset+limit<total else None)
    return _read(root, snapshot, operation)
