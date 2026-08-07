#!/usr/bin/env python3
"""Read-only inventory of local SQLite stores used by Nova, MIND, and related skills."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


FORMAT = "nova-local-store-audit/v1"
SQLITE_HEADER = b"SQLite format 3\x00"
SKIP_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
}
DIRECT_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
NAME_HINTS = {
    "mind_core",
    "mind-core",
    "corkboard",
    "dunbar",
    "people.sqlite",
    "people.db",
}

MIND_REQUIRED_TABLES = {
    "capabilities",
    "capability_cards",
    "capability_card_views",
    "associative_index_snapshots",
    "associative_snapshot_cards",
    "associative_view_vectors",
    "associative_snapshot_activations",
    "embedding_profiles",
}
DUNBAR_REQUIRED_TABLES = {"people", "aliases", "items", "relations", "audit_events"}
CORKBOARD_REQUIRED_TABLES = {"pins"}


class AuditError(RuntimeError):
    """Raised for invalid command inputs, not for individual unreadable files."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_candidate_name(path: Path) -> bool:
    name = path.name.casefold()
    if path.suffix.casefold() in DIRECT_SUFFIXES:
        return True
    if any(hint in name for hint in NAME_HINTS):
        return any(
            token in name
            for token in (".sqlite", ".sqlite3", ".db", ".bak", ".backup", ".old")
        )
    return False


def sqlite_header(path: Path) -> bool:
    try:
        with path.open("rb") as stream:
            return stream.read(len(SQLITE_HEADER)) == SQLITE_HEADER
    except OSError:
        return False


def normalized_roots(values: Iterable[str]) -> list[Path]:
    roots: list[Path] = []
    seen: set[str] = set()
    for raw in values:
        if not raw:
            continue
        path = Path(raw).expanduser()
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path.absolute()
        key = os.path.normcase(str(resolved))
        if key in seen or not resolved.exists():
            continue
        seen.add(key)
        roots.append(resolved)
    return roots


def candidate_files(roots: Iterable[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        if root.is_file():
            candidates = [root]
        else:
            candidates = []
            for directory, child_directories, filenames in os.walk(root):
                child_directories[:] = [
                    name for name in child_directories if name not in SKIP_DIRECTORIES
                ]
                base = Path(directory)
                for filename in filenames:
                    path = base / filename
                    if is_candidate_name(path):
                        candidates.append(path)
        for path in candidates:
            try:
                resolved = path.resolve()
            except OSError:
                resolved = path.absolute()
            key = os.path.normcase(str(resolved))
            if key in seen or not resolved.is_file() or not sqlite_header(resolved):
                continue
            seen.add(key)
            result.append(resolved)
    return sorted(result, key=lambda path: os.path.normcase(str(path)))


def open_read_only(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


def count_rows(connection: sqlite3.Connection, table: str) -> int | None:
    try:
        return int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
    except sqlite3.DatabaseError:
        return None


def mind_details(connection: sqlite3.Connection, tables: set[str]) -> dict[str, Any]:
    total_tables = (
        "capabilities",
        "capability_cards",
        "capability_card_views",
        "capability_relations",
        "associative_index_snapshots",
        "associative_snapshot_cards",
        "associative_view_vectors",
        "associative_snapshot_activations",
    )
    counts = {table: count_rows(connection, table) for table in total_tables}
    if "associative_snapshot_relations" in tables:
        relation_subquery = """
            (SELECT COUNT(*)
             FROM associative_snapshot_relations AS relation
             WHERE relation.associative_index_snapshot_id = activation.associative_index_snapshot_id
            ) AS relation_count
        """
    else:
        relation_subquery = "0 AS relation_count"

    rows = connection.execute(
        f"""
        SELECT
            activation.associative_snapshot_activation_id,
            activation.associative_index_snapshot_id,
            activation.prior_associative_index_snapshot_id,
            activation.activated_at,
            snapshot.created_at,
            snapshot.vector_coverage_state,
            profile.model_id,
            profile.dimensions,
            profile.radius,
            profile.qualification_state,
            (SELECT COUNT(*)
             FROM associative_snapshot_cards AS membership
             WHERE membership.associative_index_snapshot_id = activation.associative_index_snapshot_id
            ) AS card_count,
            (SELECT COUNT(DISTINCT card.capability_id)
             FROM associative_snapshot_cards AS membership
             JOIN capability_cards AS card
               ON card.capability_card_id = membership.capability_card_id
             WHERE membership.associative_index_snapshot_id = activation.associative_index_snapshot_id
            ) AS capability_count,
            (SELECT COUNT(*)
             FROM capability_card_views AS view
             JOIN associative_snapshot_cards AS membership
               ON membership.capability_card_id = view.capability_card_id
             WHERE membership.associative_index_snapshot_id = activation.associative_index_snapshot_id
            ) AS view_count,
            (SELECT COUNT(*)
             FROM associative_view_vectors AS vector
             WHERE vector.associative_index_snapshot_id = activation.associative_index_snapshot_id
            ) AS vector_count,
            {relation_subquery}
        FROM associative_snapshot_activations AS activation
        JOIN associative_index_snapshots AS snapshot
          ON snapshot.associative_index_snapshot_id = activation.associative_index_snapshot_id
        JOIN embedding_profiles AS profile
          ON profile.embedding_profile_id = snapshot.embedding_profile_id
        ORDER BY activation.activated_at DESC,
                 activation.associative_snapshot_activation_id DESC
        """
    ).fetchall()
    generations = [dict(row) for row in rows]
    return {
        "counts": counts,
        "active_generation": generations[0] if generations else None,
        "largest_generation_by_cards": (
            max(generations, key=lambda item: int(item["card_count"]))
            if generations else None
        ),
        "largest_generation_by_vectors": (
            max(generations, key=lambda item: int(item["vector_count"]))
            if generations else None
        ),
        "generations": generations,
    }


def corkboard_details(connection: sqlite3.Connection, tables: set[str]) -> dict[str, Any]:
    return {
        "schema_version": int(connection.execute("PRAGMA user_version").fetchone()[0]),
        "pins": count_rows(connection, "pins"),
        "fts_present": "pin_fts" in tables,
    }


def dunbar_details(connection: sqlite3.Connection) -> dict[str, Any]:
    return {
        table: count_rows(connection, table)
        for table in ("people", "aliases", "items", "relations", "sources", "audit_events")
    }


def generic_details(connection: sqlite3.Connection, tables: set[str]) -> dict[str, Any]:
    visible = sorted(
        table
        for table in tables
        if not table.startswith("sqlite_")
        and not table.endswith(("_data", "_idx", "_docsize", "_config", "_content"))
    )
    return {
        "tables": visible,
        "row_counts": {table: count_rows(connection, table) for table in visible[:100]},
    }


def inspect_database(path: Path) -> dict[str, Any]:
    stat = path.stat()
    record: dict[str, Any] = {
        "path": str(path),
        "bytes": stat.st_size,
        "last_write_utc": datetime.fromtimestamp(
            stat.st_mtime, timezone.utc
        ).isoformat().replace("+00:00", "Z"),
        "sha256": sha256_file(path),
        "wal": {
            "path": str(Path(str(path) + "-wal")),
            "present": Path(str(path) + "-wal").is_file(),
            "bytes": (
                Path(str(path) + "-wal").stat().st_size
                if Path(str(path) + "-wal").is_file() else 0
            ),
        },
        "shm": {
            "path": str(Path(str(path) + "-shm")),
            "present": Path(str(path) + "-shm").is_file(),
            "bytes": (
                Path(str(path) + "-shm").stat().st_size
                if Path(str(path) + "-shm").is_file() else 0
            ),
        },
    }
    try:
        with open_read_only(path) as connection:
            tables = table_names(connection)
            record["integrity_check"] = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
            if MIND_REQUIRED_TABLES.issubset(tables):
                record["kind"] = "mind_core"
                record["details"] = mind_details(connection, tables)
            elif DUNBAR_REQUIRED_TABLES.issubset(tables):
                record["kind"] = "dunbar"
                record["details"] = dunbar_details(connection)
            elif CORKBOARD_REQUIRED_TABLES.issubset(tables):
                record["kind"] = "corkboard"
                record["details"] = corkboard_details(connection, tables)
            else:
                record["kind"] = "other_sqlite"
                record["details"] = generic_details(connection, tables)
    except (OSError, sqlite3.DatabaseError, ValueError) as error:
        record["kind"] = "unreadable_sqlite"
        record["error"] = str(error)
    return record


def parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument(
        "--root", action="append", default=[], help="Root directory or file to inspect"
    )
    argument_parser.add_argument("--output", type=Path)
    return argument_parser


def main() -> int:
    args = parser().parse_args()
    roots = normalized_roots(args.root)
    if not roots:
        raise AuditError("at least one existing --root is required")
    databases = [inspect_database(path) for path in candidate_files(roots)]
    mind_estates = [record for record in databases if record.get("kind") == "mind_core"]
    summary = {
        "database_count": len(databases),
        "mind_core_count": len(mind_estates),
        "corkboard_count": sum(record.get("kind") == "corkboard" for record in databases),
        "dunbar_count": sum(record.get("kind") == "dunbar" for record in databases),
        "largest_mind_generation_by_cards": max(
            (
                {
                    "path": record["path"],
                    **record["details"]["largest_generation_by_cards"],
                }
                for record in mind_estates
                if record["details"].get("largest_generation_by_cards")
            ),
            key=lambda item: int(item["card_count"]),
            default=None,
        ),
        "largest_mind_generation_by_vectors": max(
            (
                {
                    "path": record["path"],
                    **record["details"]["largest_generation_by_vectors"],
                }
                for record in mind_estates
                if record["details"].get("largest_generation_by_vectors")
            ),
            key=lambda item: int(item["vector_count"]),
            default=None,
        ),
    }
    report = {
        "format": FORMAT,
        "generated_at": utc_now(),
        "read_only": True,
        "roots_scanned": [str(path) for path in roots],
        "environment": {
            name: os.environ.get(name)
            for name in (
                "CODEX_HOME",
                "MIND_CORE_DATABASE",
                "CORKBOARD_HOME",
                "DUNBAR_STORE",
            )
        },
        "summary": summary,
        "databases": databases,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.expanduser().parent.mkdir(parents=True, exist_ok=True)
        args.output.expanduser().write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as error:
        print(f"audit-local-stores: {error}", file=sys.stderr)
        raise SystemExit(2)
