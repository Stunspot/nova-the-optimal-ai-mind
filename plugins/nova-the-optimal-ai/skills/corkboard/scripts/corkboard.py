#!/usr/bin/env python3
"""A tiny harness-global corkboard backed by SQLite."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
from datetime import datetime, timezone
from uuid import uuid4


DB_NAME = "corkboard.sqlite3"
SCHEMA_VERSION = 2
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]+", re.IGNORECASE)
PIN_ID_RE = re.compile(r"PIN-[0-9a-f]{12}\Z")
STOPWORDS = {
    "about", "after", "again", "also", "and", "anything", "are", "but",
    "check", "for", "from", "have", "into", "its", "later", "look", "me",
    "of", "on", "or", "our", "remember", "reminder", "some", "that", "the",
    "their", "this", "time", "to", "try", "was", "we", "what", "when",
    "with", "you", "your",
}
V1_COLUMNS = {"id", "text", "cue", "tags", "project", "source", "created_at"}
V2_COLUMNS = V1_COLUMNS | {"concepts"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def configure_stdio() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")


def resolve_home(override: str | None = None) -> Path:
    if override:
        return Path(override).expanduser()
    configured = os.environ.get("CORKBOARD_HOME")
    if configured:
        return Path(configured).expanduser()
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "corkboard"
    return Path.home() / ".codex" / "corkboard"


def database_path(home: Path) -> Path:
    return home / DB_NAME


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        str(row[1])
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }


def validate_schema(connection: sqlite3.Connection, version: int) -> None:
    if version not in {1, SCHEMA_VERSION}:
        raise RuntimeError(
            f"unsupported corkboard schema version {version}; expected {SCHEMA_VERSION}"
        )
    expected = V1_COLUMNS if version == 1 else V2_COLUMNS
    if table_columns(connection, "pins") != expected:
        raise RuntimeError(f"corkboard schema does not match version {version}")
    if version == SCHEMA_VERSION:
        fts_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'pin_fts'"
        ).fetchone()
        if not fts_exists:
            raise RuntimeError("corkboard RAG index is missing")


def create_fts(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE VIRTUAL TABLE pin_fts USING fts5(
            pin_id UNINDEXED,
            concepts,
            cue,
            text,
            tags,
            project,
            tokenize = 'unicode61 remove_diacritics 2'
        )
        """
    )


def fts_values(record: dict[str, object]) -> tuple[str, str, str, str, str, str]:
    return (
        str(record["id"]),
        " ".join(str(value) for value in record.get("concepts", [])),
        str(record.get("cue", "")),
        str(record.get("text", "")),
        " ".join(str(value) for value in record.get("tags", [])),
        str(record.get("project") or ""),
    )


def index_record(connection: sqlite3.Connection, record: dict[str, object]) -> None:
    connection.execute(
        """
        INSERT INTO pin_fts(pin_id, concepts, cue, text, tags, project)
        VALUES(?, ?, ?, ?, ?, ?)
        """,
        fts_values(record),
    )


def backup_database(connection: sqlite3.Connection, path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = path.with_name(f"corkboard-v1-{stamp}-{uuid4().hex[:8]}.sqlite3.bak")
    backup = sqlite3.connect(backup_path)
    try:
        connection.backup(backup)
    finally:
        backup.close()
    return backup_path


def migrate_v1_to_v2(connection: sqlite3.Connection, path: Path) -> Path:
    validate_schema(connection, 1)
    backup_path = backup_database(connection, path)
    rows = connection.execute(
        "SELECT id, text, cue, tags, project, source, created_at FROM pins"
    ).fetchall()
    with connection:
        connection.execute(
            "ALTER TABLE pins ADD COLUMN concepts TEXT NOT NULL DEFAULT '[]'"
        )
        create_fts(connection)
        for row in rows:
            tags = json.loads(str(row[3]))
            concepts = derive_concepts(tags, str(row[2]), str(row[1]))
            connection.execute(
                "UPDATE pins SET concepts = ? WHERE id = ?",
                (json.dumps(concepts, ensure_ascii=False), str(row[0])),
            )
            index_record(
                connection,
                {
                    "id": str(row[0]),
                    "text": str(row[1]),
                    "cue": str(row[2]),
                    "tags": tags,
                    "concepts": concepts,
                    "project": row[4],
                },
            )
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    validate_schema(connection, SCHEMA_VERSION)
    return backup_path


def connect(home: Path, *, create: bool) -> sqlite3.Connection | None:
    path = database_path(home)
    if not create and not path.exists():
        return None
    existed = path.exists()
    if create:
        home.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
        if existed:
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version == 1:
                migrate_v1_to_v2(connection, path)
                version = SCHEMA_VERSION
            try:
                validate_schema(connection, version)
            except RuntimeError:
                connection.close()
                raise
        else:
            connection.executescript(
                """
                CREATE TABLE pins (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL CHECK (length(trim(text)) > 0),
                    cue TEXT NOT NULL DEFAULT '',
                    concepts TEXT NOT NULL DEFAULT '[]',
                    tags TEXT NOT NULL DEFAULT '[]',
                    project TEXT,
                    source TEXT NOT NULL DEFAULT 'user',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX pins_created_at ON pins(created_at DESC);
                """
            )
            create_fts(connection)
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.commit()
    else:
        uri = f"{path.resolve().as_uri()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        try:
            validate_schema(connection, version)
        except RuntimeError:
            connection.close()
            raise
    connection.row_factory = sqlite3.Row
    return connection


def normalize_tags(raw: str | list[object] | None) -> list[str]:
    if not raw:
        return []
    values = raw if isinstance(raw, list) else raw.split(",")
    tags: list[str] = []
    seen: set[str] = set()
    for value in values:
        tag = str(value).strip()
        key = tag.casefold()
        if tag and key not in seen:
            tags.append(tag)
            seen.add(key)
    return tags


def normalize_concepts(raw: str | list[object] | None) -> list[str]:
    return normalize_tags(raw)


def ordered_tokens(value: str) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for token in TOKEN_RE.findall(value):
        key = token.casefold()
        if key not in STOPWORDS and key not in seen:
            tokens.append(token)
            seen.add(key)
    return tokens


def derive_concepts(
    tags: str | list[object] | None,
    cue: str,
    text: str,
    *,
    limit: int = 8,
) -> list[str]:
    concepts: list[str] = []
    seen: set[str] = set()
    candidates = [*normalize_tags(tags), *ordered_tokens(cue), *ordered_tokens(text)]
    for candidate in candidates:
        value = str(candidate).strip()
        key = value.casefold()
        if value and key not in seen:
            concepts.append(value)
            seen.add(key)
        if len(concepts) >= limit:
            break
    return concepts


def tokenize(value: str) -> set[str]:
    return {
        token.casefold()
        for token in TOKEN_RE.findall(value)
        if token.casefold() not in STOPWORDS
    }


def token_forms(token: str) -> set[str]:
    forms = {token}
    if len(token) > 4 and token.endswith("s"):
        forms.add(token[:-1])
    else:
        forms.add(f"{token}s")
    return forms


def pin(
    home: Path,
    *,
    text: str,
    cue: str = "",
    concepts: str | list[object] | None = None,
    tags: str | list[object] | None = None,
    project: str | None = None,
    source: str = "user",
) -> dict[str, object]:
    note = text.strip()
    if not note:
        raise ValueError("pin text must not be blank")
    pin_id = f"PIN-{uuid4().hex[:12]}"
    normalized_tags = normalize_tags(tags)
    normalized_concepts = normalize_concepts(concepts)
    if not normalized_concepts:
        normalized_concepts = derive_concepts(normalized_tags, cue, note)
    record = {
        "id": pin_id,
        "text": note,
        "cue": cue.strip(),
        "concepts": normalized_concepts,
        "tags": normalized_tags,
        "project": project.strip() if project and project.strip() else None,
        "source": source.strip() or "user",
        "created_at": utc_now(),
    }
    connection = connect(home, create=True)
    assert connection is not None
    with connection:
        connection.execute(
            """
            INSERT INTO pins(id, text, cue, concepts, tags, project, source, created_at)
            VALUES(:id, :text, :cue, :concepts, :tags, :project, :source, :created_at)
            """,
            {
                **record,
                "concepts": json.dumps(record["concepts"], ensure_ascii=False),
                "tags": json.dumps(record["tags"], ensure_ascii=False),
            },
        )
        index_record(connection, record)
    connection.close()
    return record


def row_to_record(row: sqlite3.Row) -> dict[str, object]:
    record = dict(row)
    record["tags"] = json.loads(record["tags"])
    if "concepts" in record:
        record["concepts"] = json.loads(record["concepts"])
    else:
        record["concepts"] = derive_concepts(
            record["tags"], str(record["cue"]), str(record["text"])
        )
    return record


def relevance_score(record: dict[str, object], query: str) -> int:
    query_tokens = tokenize(query)
    if not query_tokens:
        return 0
    text_value = str(record["text"])
    cue_value = str(record["cue"])
    concepts = [str(concept) for concept in record.get("concepts", [])]
    tags_value = " ".join(str(tag) for tag in record["tags"])
    project_value = str(record.get("project") or "")
    text_tokens = tokenize(text_value)
    cue_tokens = tokenize(cue_value)
    tag_tokens = tokenize(tags_value)
    project_tokens = tokenize(project_value)
    score = 0
    for token in query_tokens:
        forms = token_forms(token)
        for position, concept in enumerate(concepts):
            if forms & tokenize(concept):
                score += max(10 - (position * 2), 3)
                break
        score += 5 if forms & cue_tokens else 0
        score += 3 if forms & text_tokens else 0
        score += 2 if forms & tag_tokens else 0
        score += 1 if forms & project_tokens else 0
    normalized_query = " ".join(query.casefold().split())
    if len(normalized_query) >= 6:
        for position, concept in enumerate(concepts):
            if normalized_query in concept.casefold():
                score += max(12 - (position * 2), 4)
                break
        score += 8 if normalized_query in cue_value.casefold() else 0
        score += 5 if normalized_query in text_value.casefold() else 0
    return score


def retrieval_text(record: dict[str, object]) -> str:
    segments: list[str] = []
    concepts = [str(value) for value in record.get("concepts", []) if str(value).strip()]
    if concepts:
        segments.append(" · ".join(concepts))
    cue = str(record.get("cue", "")).strip()
    if cue:
        segments.append(cue)
    segments.append(str(record["text"]).strip())
    return " — ".join(segments)


def fts_match_expression(query: str) -> str:
    forms: set[str] = set()
    for token in tokenize(query):
        forms.update(token_forms(token))
    return " OR ".join(f'"{value.replace(chr(34), chr(34) * 2)}"' for value in sorted(forms))


def fts_seed_order(connection: sqlite3.Connection, query: str) -> dict[str, int]:
    expression = fts_match_expression(query)
    if not expression:
        return {}
    rows = connection.execute(
        """
        SELECT pin_id
        FROM pin_fts
        WHERE pin_fts MATCH ?
        ORDER BY bm25(pin_fts, 0.0, 8.0, 5.0, 3.0, 2.0, 1.0)
        """,
        (expression,),
    ).fetchall()
    return {str(row[0]): len(rows) - position for position, row in enumerate(rows)}


def scope_records(
    records: list[dict[str, object]],
    *,
    project: str | None,
    all_projects: bool,
) -> list[dict[str, object]]:
    if all_projects:
        return records
    if project:
        return [
            record
            for record in records
            if record["project"] is None or record["project"] == project
        ]
    return [record for record in records if record["project"] is None]


def list_pins(
    home: Path,
    *,
    query: str | None = None,
    project: str | None = None,
    all_projects: bool = False,
    limit: int = 20,
) -> list[dict[str, object]]:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    connection = connect(home, create=False)
    if connection is None:
        return []
    rows = connection.execute("SELECT * FROM pins").fetchall()
    connection.close()
    records = scope_records(
        [row_to_record(row) for row in rows],
        project=project,
        all_projects=all_projects,
    )
    if query:
        scored = [
            (relevance_score(record, query), record)
            for record in records
        ]
        records = [record for score, record in scored if score > 0]
        records.sort(
            key=lambda record: (
                relevance_score(record, query),
                str(record["created_at"]),
            ),
            reverse=True,
        )
    else:
        records.sort(key=lambda record: str(record["created_at"]), reverse=True)
    return records[:limit]


def rag_corpus(
    home: Path,
    *,
    query: str,
    project: str | None = None,
    all_projects: bool = False,
) -> dict[str, object]:
    context = query.strip()
    if not context:
        raise ValueError("RAG query must not be blank")
    connection = connect(home, create=False)
    if connection is None:
        records: list[dict[str, object]] = []
        fts_order: dict[str, int] = {}
    else:
        rows = connection.execute("SELECT * FROM pins").fetchall()
        records = scope_records(
            [row_to_record(row) for row in rows],
            project=project,
            all_projects=all_projects,
        )
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        fts_order = (
            fts_seed_order(connection, context)
            if version == SCHEMA_VERSION
            else {}
        )
        connection.close()
    records.sort(
        key=lambda record: (
            relevance_score(record, context),
            fts_order.get(str(record["id"]), 0),
            str(record["created_at"]),
        ),
        reverse=True,
    )
    documents = [
        {
            "id": record["id"],
            "retrieval_text": retrieval_text(record),
            "concepts": record["concepts"],
            "cue": record["cue"],
            "text": record["text"],
            "tags": record["tags"],
            "project": record["project"],
            "created_at": record["created_at"],
        }
        for record in records
    ]
    return {
        "format": "cd-corkboard-rag/v1",
        "query": context,
        "retrieval_mode": "full-scoped-corpus-hybrid",
        "corpus_size": len(documents),
        "documents": documents,
    }


def migrate_board(home: Path) -> dict[str, object]:
    path = database_path(home)
    if not path.exists():
        return {
            "database": str(path),
            "migrated": False,
            "schema_before": None,
            "schema_after": None,
            "backup": None,
            "pin_count": 0,
        }
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    before = int(connection.execute("PRAGMA user_version").fetchone()[0])
    backup_path: Path | None = None
    try:
        if before == 1:
            backup_path = migrate_v1_to_v2(connection, path)
        else:
            validate_schema(connection, before)
        after = int(connection.execute("PRAGMA user_version").fetchone()[0])
        count = int(connection.execute("SELECT COUNT(*) FROM pins").fetchone()[0])
    finally:
        connection.close()
    return {
        "database": str(path),
        "migrated": before != after,
        "schema_before": before,
        "schema_after": after,
        "backup": str(backup_path) if backup_path else None,
        "pin_count": count,
    }


def unpin(home: Path, *, pin_id: str) -> bool:
    path = database_path(home)
    if not path.exists():
        return False
    connection = connect(home, create=True)
    assert connection is not None
    with connection:
        cursor = connection.execute("DELETE FROM pins WHERE id = ?", (pin_id,))
        connection.execute("DELETE FROM pin_fts WHERE pin_id = ?", (pin_id,))
    removed = cursor.rowcount == 1
    connection.close()
    return removed


def emit(value: object, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return
    if isinstance(value, list):
        if not value:
            print("The corkboard is empty.")
            return
        for record in value:
            print(f"[{record['id']}] {record['text']}")
        return
    if isinstance(value, dict) and value.get("removed") is not None:
        state = "unpinned" if value["removed"] else "not found"
        print(f"{value['id']}: {state}")
        return
    if isinstance(value, dict) and value.get("format") == "cd-corkboard-rag/v1":
        documents = value.get("documents", [])
        if not documents:
            print("No pins are eligible in this scope.")
            return
        for document in documents:
            print(f"[{document['id']}] {document['retrieval_text']}")
        return
    if isinstance(value, dict) and "migrated" in value:
        print(
            f"schema {value['schema_before']} -> {value['schema_after']}; "
            f"pins: {value['pin_count']}"
        )
        return
    if isinstance(value, dict):
        print(f"[{value['id']}] {value['text']}")


def read_stdin_object() -> dict[str, object]:
    loaded = json.loads(sys.stdin.readline())
    if not isinstance(loaded, dict):
        raise ValueError("stdin JSON must be an object")
    return loaded


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", help="override the harness-global corkboard home")
    commands = parser.add_subparsers(dest="command", required=True)

    pin_parser = commands.add_parser("pin", help="pin a reminder")
    pin_parser.add_argument(
        "--stdin-json",
        action="store_true",
        required=True,
        help="read one JSON object containing text/cue/concepts/tags/project/source from stdin",
    )
    pin_parser.add_argument("--json", action="store_true")

    list_parser = commands.add_parser("list", help="list or search pins")
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.add_argument("--stdin-json", action="store_true")
    list_parser.add_argument("--json", action="store_true")

    relevant_parser = commands.add_parser("relevant", help="find contextually relevant pins")
    relevant_parser.add_argument(
        "--stdin-json",
        action="store_true",
        required=True,
        help="read one JSON object containing query/project/limit from stdin",
    )
    relevant_parser.add_argument("--limit", type=int, default=3)
    relevant_parser.add_argument("--json", action="store_true")

    rag_parser = commands.add_parser(
        "rag", help="retrieve the full scoped corpus for contextual semantic reranking"
    )
    rag_parser.add_argument(
        "--stdin-json",
        action="store_true",
        required=True,
        help="read one JSON object containing query/project/all_projects from stdin",
    )
    rag_parser.add_argument("--json", action="store_true")

    migrate_parser = commands.add_parser(
        "migrate", help="transactionally upgrade and index an existing board"
    )
    migrate_parser.add_argument("--json", action="store_true")

    unpin_parser = commands.add_parser("unpin", help="delete a pin")
    unpin_parser.add_argument("--id", required=True)
    unpin_parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_stdio()
    args = build_parser().parse_args(argv)
    home = resolve_home(args.home)
    try:
        if args.command == "pin":
            payload = read_stdin_object()
            text_value = payload.get("text")
            if not isinstance(text_value, str):
                raise ValueError("pin text must be a string")
            emit(
                pin(
                    home,
                    text=text_value,
                    cue=str(payload.get("cue", "")),
                    concepts=payload.get("concepts"),
                    tags=payload.get("tags"),
                    project=(
                        str(payload["project"])
                        if payload.get("project") is not None
                        else None
                    ),
                    source=str(payload.get("source", "user")),
                ),
                as_json=args.json,
            )
            return 0
        if args.command in {"list", "relevant"}:
            payload = read_stdin_object() if args.stdin_json else {}
            query = None
            if payload.get("query") is not None:
                if not isinstance(payload["query"], str):
                    raise ValueError("query must be a string")
                query = payload["query"]
            project = None
            if payload.get("project") is not None:
                if not isinstance(payload["project"], str):
                    raise ValueError("project must be a string")
                project = payload["project"]
            all_projects = False
            if payload.get("all_projects") is not None:
                if not isinstance(payload["all_projects"], bool):
                    raise ValueError("all_projects must be a boolean")
                all_projects = payload["all_projects"]
            limit = args.limit
            if payload.get("limit") is not None:
                if not isinstance(payload["limit"], int):
                    raise ValueError("limit must be an integer")
                limit = payload["limit"]
            emit(
                list_pins(
                    home,
                    query=query,
                    project=project,
                    all_projects=all_projects,
                    limit=limit,
                ),
                as_json=args.json,
            )
            return 0
        if args.command == "rag":
            payload = read_stdin_object()
            query = payload.get("query")
            if not isinstance(query, str):
                raise ValueError("query must be a string")
            project = None
            if payload.get("project") is not None:
                if not isinstance(payload["project"], str):
                    raise ValueError("project must be a string")
                project = payload["project"]
            all_projects = False
            if payload.get("all_projects") is not None:
                if not isinstance(payload["all_projects"], bool):
                    raise ValueError("all_projects must be a boolean")
                all_projects = payload["all_projects"]
            emit(
                rag_corpus(
                    home,
                    query=query,
                    project=project,
                    all_projects=all_projects,
                ),
                as_json=args.json,
            )
            return 0
        if args.command == "migrate":
            emit(migrate_board(home), as_json=args.json)
            return 0
        if args.command == "unpin":
            if not PIN_ID_RE.fullmatch(args.id):
                raise ValueError("pin id must match PIN- followed by 12 hexadecimal characters")
            removed = unpin(home, pin_id=args.id)
            emit({"id": args.id, "removed": removed}, as_json=args.json)
            return 0 if removed else 1
    except (OSError, RuntimeError, sqlite3.Error, ValueError) as error:
        print(f"corkboard: {error}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
