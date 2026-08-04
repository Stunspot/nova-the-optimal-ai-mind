"""Checksum-bound embedded SQLite migrations."""

from __future__ import annotations

import hashlib
import importlib.resources
import sqlite3
from dataclasses import dataclass

from .constants import APPLICATION_ID, RUNTIME_VERSION, SCHEMA_VERSION
from .errors import MigrationError
from .util import timestamp


@dataclass(frozen=True)
class Migration:
    migration_id: str
    sql: str
    checksum: str


def embedded_migrations() -> tuple[Migration, ...]:
    root = importlib.resources.files("mind_core.migrations")
    migrations: list[Migration] = []
    for item in sorted(root.iterdir(), key=lambda value: value.name):
        if not item.name.endswith(".sql"):
            continue
        sql = item.read_text(encoding="utf-8")
        migration_id = item.name.removesuffix(".sql")
        digest = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        migrations.append(Migration(migration_id, sql, digest))
    if not migrations:
        raise MigrationError("no embedded migrations were found")
    return tuple(migrations)


def _has_table(connection: sqlite3.Connection, name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_schema WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def apply_migrations(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA journal_mode = WAL")

    for migration in embedded_migrations():
        if _has_table(connection, "schema_migrations"):
            existing = connection.execute(
                "SELECT checksum FROM schema_migrations WHERE migration_id=?",
                (migration.migration_id,),
            ).fetchone()
            if existing is not None:
                if existing[0] != migration.checksum:
                    raise MigrationError(
                        f"migration checksum mismatch: {migration.migration_id}"
                    )
                continue

        applied_at = timestamp()
        rendered = (
            migration.sql.replace("{{CHECKSUM}}", migration.checksum)
            .replace("{{APPLIED_AT}}", applied_at)
            .replace("{{RUNNER_VERSION}}", RUNTIME_VERSION)
        )
        try:
            connection.executescript(rendered)
        except sqlite3.Error as exc:
            raise MigrationError(
                f"migration failed: {migration.migration_id}: {exc}"
            ) from exc

    application_id = connection.execute("PRAGMA application_id").fetchone()[0]
    user_version = connection.execute("PRAGMA user_version").fetchone()[0]
    if application_id != APPLICATION_ID:
        raise MigrationError(f"unexpected SQLite application_id: {application_id}")
    if user_version != SCHEMA_VERSION:
        raise MigrationError(f"unexpected SQLite user_version: {user_version}")
    failures = connection.execute("PRAGMA foreign_key_check").fetchall()
    if failures:
        raise MigrationError(f"foreign-key check failed: {failures!r}")
