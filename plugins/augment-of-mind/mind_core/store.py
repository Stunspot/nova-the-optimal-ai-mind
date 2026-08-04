"""The sole-writer SQLite boundary for MIND Core metadata."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .errors import ConflictError, MigrationError, ValidationError, WriterLeaseError
from .migration_runner import apply_migrations


class _WriterLease:
    def __init__(self, database: Path):
        self.path = Path(f"{database}.writer.lock")
        self._stream = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stream = self.path.open("a+b")
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, IOError) as exc:
            stream.close()
            raise WriterLeaseError(
                f"another MIND Core owns the writer lease for {self.path}"
            ) from exc
        self._stream = stream

    def release(self) -> None:
        if self._stream is None:
            return
        stream = self._stream
        try:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        finally:
            stream.close()
            self._stream = None


class CoreStore:
    """Own the one writable connection and its process-wide writer lease."""

    def __init__(self, database: str | Path):
        self.path = Path(database).expanduser().resolve()
        if str(database) == ":memory:":
            raise ValidationError("MIND Core requires a durable database path")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lease = _WriterLease(self.path)
        self._lease.acquire()
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(self.path, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            apply_migrations(connection)
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise MigrationError(f"SQLite integrity check failed: {integrity}")
            self.connection = connection
        except sqlite3.DatabaseError as exc:
            if connection is not None:
                connection.close()
            self._lease.release()
            raise MigrationError(f"SQLite startup failed: {exc}") from exc
        except BaseException:
            if connection is not None:
                connection.close()
            self._lease.release()
            raise

    def close(self) -> None:
        connection = getattr(self, "connection", None)
        try:
            if connection is not None:
                connection.close()
        finally:
            self._lease.release()

    def __enter__(self) -> "CoreStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.connection
        except BaseException:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def integrity(self) -> dict[str, object]:
        integrity = self.connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = self.connection.execute("PRAGMA foreign_key_check").fetchall()
        return {
            "integrity_check": integrity,
            "foreign_key_failures": [dict(row) for row in foreign_keys],
            "journal_mode": self.connection.execute("PRAGMA journal_mode").fetchone()[0],
            "foreign_keys_enabled": bool(
                self.connection.execute("PRAGMA foreign_keys").fetchone()[0]
            ),
        }


def insert_exact(
    connection: sqlite3.Connection,
    table: str,
    record: dict[str, object],
    key_fields: tuple[str, ...],
) -> bool:
    """Insert a stable record or prove an exact idempotent replay."""

    where = " AND ".join(f"{field}=?" for field in key_fields)
    key_values = tuple(record[field] for field in key_fields)
    existing = connection.execute(
        f"SELECT * FROM {table} WHERE {where}", key_values
    ).fetchone()
    if existing is not None:
        mismatches = [
            field for field, value in record.items() if existing[field] != value
        ]
        if mismatches:
            raise ConflictError(
                f"stable identity conflict in {table}: {','.join(mismatches)}"
            )
        return False

    fields = tuple(record)
    placeholders = ",".join("?" for _ in fields)
    connection.execute(
        f"INSERT INTO {table}({','.join(fields)}) VALUES ({placeholders})",
        tuple(record[field] for field in fields),
    )
    return True
