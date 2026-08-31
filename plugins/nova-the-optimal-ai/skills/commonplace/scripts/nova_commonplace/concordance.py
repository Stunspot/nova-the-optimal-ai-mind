"""Rebuildable, read-only navigation over a Nova Commonplace snapshot.

Concordance is deliberately derived. The canonical snapshot remains the source of
truth; an index is usable only while its workspace, generation, and digest match the
canonical root/CURRENT.json pointer.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import html
import json
import math
import os
import re
import shutil
import sqlite3
import tempfile
import uuid

from .runtime import (
    CommonplaceError as CanonicalStoreError,
    PathPolicy,
    opaque_identifier,
)
from .store import CommonplaceStore
from .semantic import (
    EMBEDDING_INPUT_POLICY,
    OllamaEmbeddingProvider,
    SemanticContractError,
    SemanticError,
    SemanticIndexConfig,
    SemanticIntegrityError,
    SemanticModelDriftError,
    SemanticProviderResponseError,
    SemanticUnavailableError,
    cosine_similarity,
    embedding_input,
    unpack_vector,
    validate_provider_identity,
    validate_vectors,
)


BUILDER_ID = "nova-commonplace-concordance/0.2.0"
INDEX_SCHEMA = "nova.commonplace.concordance.sqlite.v2"
POINTER_SCHEMA = "nova.commonplace.concordance.pointer.v2"
VIEWS_SCHEMA = "nova.commonplace.concordance.views.v2"
CANONICAL_POINTER_SCHEMA = "nova-commonplace.pointer.v1"
CANONICAL_SNAPSHOT_SCHEMA = "nova-commonplace.snapshot.v1"
_STATE_AXES = ("lifecycle", "sensitivity", "review", "dispute", "origin")
_APPROVED_REVIEWS = ("accepted", "verified")
_CANONICAL_LIFECYCLES = ("current", "superseded", "retracted")
_OWNER_NAMES = (
    "Commonplace",
    "Dunbar",
    "Corkboard",
    "Dennis",
    "Continuity",
    "Striving",
    "Giles",
    "Dex",
    "Skills",
    "Repositories",
    "ExternalCorpora",
)
_ROUTE_STATUSES = {
    "current", "stale", "unavailable", "scope_denied", "incompatible", "partial"
}
DEFAULT_SEARCH_SENSITIVITIES = ("public", "personal")
DEFAULT_MARKDOWN_SENSITIVITIES = ("public", "personal")
MAX_CONTEXT_PACKET_BYTES = 24_576


class ConcordanceError(RuntimeError):
    """Typed Concordance failure suitable for CLI translation."""

    code = "concordance_error"

    def as_dict(self) -> dict[str, str]:
        return {"status": "error", "code": self.code, "message": str(self)}


class ContractError(ConcordanceError):
    code = "contract_error"


class IntegrityError(ConcordanceError):
    code = "integrity_error"


class StaleIndexError(ConcordanceError):
    code = "stale_index"


class IndexUnavailableError(ConcordanceError):
    code = "index_unavailable"


@dataclass(frozen=True)
class CanonicalSnapshot:
    workspace_id: str
    generation: int
    digest: str
    relative_path: str
    path: Path
    document: dict[str, Any]


def _canonical_json(value: Any, *, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, indent=2, separators=(",", ": ")
        ) + "\n"
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _sha256_path(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON object key {key!r}")
        value[key] = item
    return value


def _reject_nonfinite_json(value: str) -> Any:
    raise ValueError(f"non-finite JSON number {value!r}")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_json,
        )
    except FileNotFoundError as exc:
        raise IndexUnavailableError(f"Required file is unavailable: {path}") from exc
    except (OSError, UnicodeError, ValueError) as exc:
        raise ContractError(f"Invalid JSON file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"Expected a JSON object in {path}")
    return value


def _confined_path(root: Path, relative: Any, *, field: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise ContractError(f"{field} must be a non-empty relative path")
    fragment = Path(relative)
    if fragment.is_absolute():
        raise ContractError(f"{field} must be relative to {root}")
    resolved_root = root.resolve()
    resolved = (resolved_root / fragment).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ContractError(f"{field} escapes its governed root") from exc
    return resolved


def _governed_path(policy: PathPolicy, relative: Any, *, field: str) -> Path:
    """Resolve a persisted relative path without crossing links or reparse points."""

    if not isinstance(relative, str) or not relative.strip():
        raise ContractError(f"{field} must be a non-empty relative path")
    fragment = Path(relative)
    if fragment.is_absolute():
        raise ContractError(f"{field} must be relative to {policy.root}")
    return policy.assert_confined(policy.root / fragment)


def _pointer_value(pointer: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in pointer:
            return pointer[name]
    return None


def _load_canonical_snapshot(canonical_home: os.PathLike[str] | str) -> CanonicalSnapshot:
    """Load through strict JSON plus the canonical store's anti-resurrection checks."""

    try:
        policy = PathPolicy(canonical_home)
        root = policy.root
        strict_pointer = _read_json(policy.confined("CURRENT.json"))
        strict_relative = strict_pointer.get("snapshot")
        strict_snapshot_path = _governed_path(
            policy, strict_relative, field="snapshot"
        )
        strict_document = _read_json(strict_snapshot_path)
        pointer, document, digest = CommonplaceStore(root).read_current()
    except (CanonicalStoreError, ConcordanceError) as exc:
        raise IntegrityError(
            f"Canonical Commonplace rejected its current state: {exc}"
        ) from exc
    if strict_pointer != pointer or strict_document != document:
        raise IntegrityError(
            "Canonical Commonplace strict read disagrees with validated current state"
        )
    relative = pointer["snapshot"]
    snapshot_path = _governed_path(policy, relative, field="snapshot")
    return CanonicalSnapshot(
        workspace_id=document["workspace_id"],
        generation=document["generation"],
        digest=digest,
        relative_path=Path(relative).as_posix(),
        path=snapshot_path,
        document=document,
    )

def _normalise_record(record_id: str, raw: Any) -> dict[str, Any]:
    if not isinstance(record_id, str) or not record_id:
        raise ContractError("Canonical record keys must be non-empty strings")
    if not isinstance(raw, dict):
        raise ContractError(f"Record {record_id!r} must be an object")
    if raw.get("id") != record_id:
        raise ContractError(f"Record {record_id!r} id does not match its map key")
    title, body, kind = raw.get("title"), raw.get("body"), raw.get("kind")
    state = raw.get("state")
    if state is None:
        state = {axis: raw.get(axis) for axis in _STATE_AXES}
    if not isinstance(title, str) or not isinstance(body, str):
        raise ContractError(f"Record {record_id!r} title and body must be strings")
    if not isinstance(kind, str) or not kind:
        raise ContractError(f"Record {record_id!r} kind must be a non-empty string")
    revision = raw.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise ContractError(
            f"Record {record_id!r} revision must be a positive integer"
        )
    if not isinstance(state, dict):
        raise ContractError(f"Record {record_id!r} state must be an object")
    missing = [axis for axis in _STATE_AXES if not isinstance(state.get(axis), str)]
    if missing:
        raise ContractError(
            f"Record {record_id!r} is missing state axes: {', '.join(missing)}"
        )
    if state["lifecycle"] not in _CANONICAL_LIFECYCLES:
        raise ContractError(
            f"Record {record_id!r} has unsupported lifecycle {state['lifecycle']!r}"
        )
    if "provenance" not in raw:
        raise ContractError(f"Record {record_id!r} is missing provenance")
    if not isinstance(raw.get("relations"), list):
        raise ContractError(f"Record {record_id!r} relations must be a list")
    return {
        "id": record_id,
        "title": title,
        "body": body,
        "kind": kind,
        "revision": revision,
        "state": {axis: state[axis] for axis in _STATE_AXES},
        "source": raw.get("source"),
        "provenance": raw.get("provenance"),
        "relations": raw["relations"],
        "canonical": raw,
    }


def _iter_spans(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if any(key in value for key in ("start", "end", "quote", "selector")):
            yield {
                key: value[key]
                for key in ("start", "end", "quote", "selector")
                if key in value
            }
        for key in ("span", "spans", "source_span", "source_spans"):
            if key in value:
                yield from _iter_spans(value[key])
    elif isinstance(value, list):
        for item in value:
            yield from _iter_spans(item)


def _citations_for(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    source, provenance = record.get("source"), record.get("provenance")
    spans = list(_iter_spans(provenance)) or list(_iter_spans(source))
    base = {
        "record_id": record["id"],
        "title": record["title"],
        "source": source,
        "provenance": provenance,
    }
    return (
        [{**base, "source_span": span} for span in spans]
        if spans
        else [{**base, "source_span": None}]
    )


def _content_fingerprint(records: Sequence[Mapping[str, Any]]) -> str:
    projection = [
        {
            "id": record["id"], "title": record["title"], "body": record["body"],
            "kind": record["kind"], "revision": record["revision"],
            "state": record["state"],
            "source": record["source"], "provenance": record["provenance"],
            "relations": record["relations"],
        }
        for record in records
    ]
    return sha256(_canonical_json(projection).encode("utf-8")).hexdigest()


_SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
PRAGMA secure_delete = ON;
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID;
CREATE TABLE records (
    id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    kind TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    lifecycle TEXT NOT NULL,
    sensitivity TEXT NOT NULL,
    review TEXT NOT NULL,
    dispute TEXT NOT NULL,
    origin TEXT NOT NULL,
    source_json TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    relations_json TEXT NOT NULL,
    canonical_json TEXT NOT NULL
);
CREATE TABLE citations (
    record_id TEXT NOT NULL REFERENCES records(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    citation_json TEXT NOT NULL,
    PRIMARY KEY (record_id, ordinal)
) WITHOUT ROWID;
CREATE TABLE semantic_vectors (
    record_id TEXT PRIMARY KEY REFERENCES records(id) ON DELETE CASCADE,
    input_digest TEXT NOT NULL CHECK (length(input_digest) = 64),
    dimensions INTEGER NOT NULL CHECK (dimensions > 0),
    vector BLOB NOT NULL,
    norm REAL NOT NULL CHECK (norm > 0)
) WITHOUT ROWID;
CREATE VIRTUAL TABLE records_fts USING fts5(
    id UNINDEXED,
    title,
    body,
    kind,
    content='records',
    content_rowid='rowid',
    tokenize='unicode61 remove_diacritics 2'
);
"""


def _active_records(snapshot: CanonicalSnapshot) -> list[dict[str, Any]]:
    # Governed forgetting removes records and sanitises references in the canonical
    # snapshot before Concordance sees them. No persisted "purged" lifecycle exists.
    return [
        _normalise_record(record_id, snapshot.document["records"][record_id])
        for record_id in sorted(snapshot.document["records"])
    ]


def _call_provider_identity(
    provider: Any, config: SemanticIndexConfig
) -> dict[str, Any]:
    method = getattr(provider, "identity", None)
    if not callable(method):
        raise SemanticContractError(
            "embedding_provider must expose identity(model)"
        )
    try:
        raw = method(config.model)
    except SemanticError:
        raise
    except Exception as exc:
        raise SemanticUnavailableError(
            f"semantic provider identity lookup failed: {exc}"
        ) from exc
    return validate_provider_identity(raw, config)


def _call_provider_embed(
    provider: Any, config: SemanticIndexConfig, texts: Sequence[str]
) -> Any:
    method = getattr(provider, "embed", None)
    if not callable(method):
        raise SemanticContractError(
            "embedding_provider must expose embed(model, texts)"
        )
    try:
        return method(config.model, list(texts))
    except SemanticError:
        raise
    except Exception as exc:
        raise SemanticUnavailableError(
            f"semantic provider embedding failed: {exc}"
        ) from exc


def _resolve_semantic_config(
    policy: PathPolicy,
    supplied: SemanticIndexConfig | Mapping[str, Any] | bool | None,
) -> tuple[SemanticIndexConfig | None, str]:
    if supplied is False:
        return None, "explicit_disabled"
    if supplied is not None:
        if supplied is True:
            supplied = {}
        return SemanticIndexConfig.from_value(supplied), "explicit"

    pointer_path = policy.confined("state", "current.json")
    if not pointer_path.is_file():
        return None, "default_disabled"
    pointer = _read_json(pointer_path)
    prior = pointer.get("semantic_config")
    if prior is None:
        return None, "default_disabled"
    if pointer.get("schema") != POINTER_SCHEMA:
        raise SemanticIntegrityError(
            "cannot safely inherit semantic config from an incompatible pointer"
        )
    return SemanticIndexConfig.from_value(prior), "inherited"


def _prior_semantic_vectors(
    policy: PathPolicy,
    config: SemanticIndexConfig,
    identity: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any] | None]:
    pointer_path = policy.confined("state", "current.json")
    if not pointer_path.is_file():
        return {}, None
    pointer = _read_json(pointer_path)
    semantic = pointer.get("semantic")
    if (
        pointer.get("schema") != POINTER_SCHEMA
        or not isinstance(semantic, Mapping)
        or semantic.get("status") != "current"
    ):
        return {}, None
    try:
        prior_config = SemanticIndexConfig.from_value(
            pointer.get("semantic_config")
        )
    except SemanticError as exc:
        raise SemanticIntegrityError(
            f"prior semantic config is invalid: {exc}"
        ) from exc
    if prior_config.to_dict() != config.to_dict():
        return {}, None

    _verify_managed_inventory(policy, pointer)
    index_path = _governed_path(policy, pointer.get("index"), field="index")
    if _sha256_path(index_path) != pointer.get("index_sha256"):
        raise SemanticIntegrityError(
            "prior semantic index digest does not match its pointer"
        )
    connection = _open_readonly(index_path)
    try:
        metadata = _metadata(connection)
        _verify_connection(connection)
        expected_binding = {
            "schema": INDEX_SCHEMA,
            "builder": BUILDER_ID,
            "workspace_id": str(pointer.get("workspace_id")),
            "generation": str(pointer.get("generation")),
            "canonical_snapshot": str(pointer.get("canonical_snapshot")),
            "canonical_snapshot_digest": str(
                pointer.get("canonical_snapshot_digest")
            ),
            "content_fingerprint": str(pointer.get("content_fingerprint")),
            "record_count": str(pointer.get("record_count")),
            "semantic_config": _canonical_json(
                pointer.get("semantic_config")
            ),
        }
        actual_binding = {
            key: metadata.get(key) for key in expected_binding
        }
        if actual_binding != expected_binding:
            raise SemanticIntegrityError(
                "prior semantic index metadata does not match its pointer"
            )
        try:
            prior_identity = json.loads(metadata["semantic_identity"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SemanticIntegrityError(
                "prior semantic identity metadata is invalid"
            ) from exc
        if not isinstance(prior_identity, dict):
            raise SemanticIntegrityError(
                "prior semantic identity metadata must be an object"
            )
        if prior_identity != dict(identity):
            return {}, prior_identity
        rows: dict[str, dict[str, Any]] = {}
        for row in connection.execute(
            "SELECT record_id, input_digest, dimensions, vector, norm "
            "FROM semantic_vectors ORDER BY record_id"
        ):
            dimensions = int(row["dimensions"])
            values = unpack_vector(row["vector"], dimensions)
            norm = math.sqrt(sum(value * value for value in values))
            if not math.isclose(
                norm, float(row["norm"]), rel_tol=1e-6, abs_tol=1e-7
            ):
                raise SemanticIntegrityError(
                    "prior semantic vector norm does not verify"
                )
            rows[str(row["record_id"])] = {
                "input_digest": str(row["input_digest"]),
                "dimensions": dimensions,
                "vector": bytes(row["vector"]),
                "norm": float(row["norm"]),
            }
        return rows, prior_identity
    except sqlite3.DatabaseError as exc:
        raise SemanticIntegrityError(
            f"could not read prior semantic vectors: {exc}"
        ) from exc
    finally:
        connection.close()


def _semantic_disabled_payload(source: str) -> dict[str, Any]:
    return {
        "config": None,
        "status": "disabled",
        "source": source,
        "identity": None,
        "dimensions": None,
        "rows": [],
        "reused_count": 0,
        "embedded_count": 0,
        "model_digest_drift": None,
        "reason": None,
    }


def _semantic_unavailable_payload(
    config: SemanticIndexConfig,
    source: str,
    exc: SemanticError,
    identity: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "config": config,
        "status": "unavailable",
        "source": source,
        "identity": dict(identity) if identity is not None else None,
        "dimensions": None,
        "rows": [],
        "reused_count": 0,
        "embedded_count": 0,
        "model_digest_drift": None,
        "reason": {"code": exc.code, "message": str(exc)},
    }


def _prepare_semantic_payload(
    records: Sequence[Mapping[str, Any]],
    policy: PathPolicy,
    config: SemanticIndexConfig | None,
    source: str,
    embedding_provider: Any | None,
) -> dict[str, Any]:
    if config is None:
        return _semantic_disabled_payload(source)

    provider = embedding_provider or OllamaEmbeddingProvider(config)
    identity: dict[str, Any] | None = None
    try:
        identity = _call_provider_identity(provider, config)
        reuse, prior_identity = _prior_semantic_vectors(
            policy, config, identity
        )
        drift = None
        if prior_identity is not None and prior_identity != identity:
            drift = {
                "previous_model_digest": prior_identity.get("model_digest"),
                "current_model_digest": identity["model_digest"],
            }
            reuse = {}

        prepared: list[dict[str, Any]] = []
        pending: list[tuple[str, str, str]] = []
        dimensions: int | None = None
        reused_count = 0
        for record in records:
            text, input_digest = embedding_input(
                record, policy=config.input_policy
            )
            prior = reuse.get(str(record["id"]))
            if prior is not None and prior["input_digest"] == input_digest:
                if dimensions is None:
                    dimensions = int(prior["dimensions"])
                if int(prior["dimensions"]) != dimensions:
                    raise SemanticIntegrityError(
                        "reused semantic vectors have inconsistent dimensions"
                    )
                prepared.append({
                    "record_id": str(record["id"]),
                    "input_digest": input_digest,
                    "dimensions": dimensions,
                    "vector": prior["vector"],
                    "norm": prior["norm"],
                })
                reused_count += 1
            else:
                pending.append((str(record["id"]), input_digest, text))

        embedded_count = 0
        for offset in range(0, len(pending), config.batch_size):
            batch = pending[offset:offset + config.batch_size]
            raw = _call_provider_embed(
                provider, config, [item[2] for item in batch]
            )
            packed, dimensions = validate_vectors(
                raw,
                expected_count=len(batch),
                expected_dimensions=dimensions,
            )
            for (record_id, input_digest, _), (blob, norm) in zip(batch, packed):
                prepared.append({
                    "record_id": record_id,
                    "input_digest": input_digest,
                    "dimensions": dimensions,
                    "vector": blob,
                    "norm": norm,
                })
                embedded_count += 1

        if dimensions is None:
            probe = _call_provider_embed(provider, config, [""])
            _, dimensions = validate_vectors(probe, expected_count=1)

        final_identity = _call_provider_identity(provider, config)
        if final_identity != identity:
            raise SemanticModelDriftError(
                "semantic model identity changed during index construction"
            )
        prepared.sort(key=lambda item: item["record_id"])
        return {
            "config": config,
            "status": "current",
            "source": source,
            "identity": identity,
            "dimensions": dimensions,
            "rows": prepared,
            "reused_count": reused_count,
            "embedded_count": embedded_count,
            "model_digest_drift": drift,
            "reason": None,
        }
    except SemanticError as exc:
        if config.best_effort:
            return _semantic_unavailable_payload(
                config, source, exc, identity
            )
        raise


def _semantic_public(payload: Mapping[str, Any]) -> dict[str, Any]:
    identity = payload.get("identity")
    public: dict[str, Any] = {
        "enabled": payload["status"] != "disabled",
        "status": payload["status"],
        "config_source": payload["source"],
        "input_policy": (
            payload["config"].input_policy
            if isinstance(payload.get("config"), SemanticIndexConfig)
            else None
        ),
        "vector_count": len(payload["rows"]),
        "reused_count": payload["reused_count"],
        "embedded_count": payload["embedded_count"],
        "dimensions": payload["dimensions"],
        "reason": payload["reason"],
        "model_digest_drift": payload["model_digest_drift"],
    }
    if isinstance(identity, Mapping):
        public.update({
            "provider": identity.get("provider"),
            "endpoint": identity.get("endpoint"),
            "model": identity.get("model"),
            "model_digest": identity.get("model_digest"),
        })
    elif isinstance(payload.get("config"), SemanticIndexConfig):
        config = payload["config"]
        public.update({
            "provider": config.provider,
            "endpoint": config.endpoint,
            "model": config.model,
            "model_digest": None,
        })
    return public


def _semantic_metadata(payload: Mapping[str, Any]) -> dict[str, str]:
    config = payload.get("config")
    identity = payload.get("identity")
    values = {
        "semantic_enabled": (
            "false" if payload["status"] == "disabled" else "true"
        ),
        "semantic_status": str(payload["status"]),
        "semantic_vector_count": str(len(payload["rows"])),
        "semantic_config": _canonical_json(
            config.to_dict() if isinstance(config, SemanticIndexConfig) else None
        ),
        "semantic_identity": _canonical_json(
            dict(identity) if isinstance(identity, Mapping) else None
        ),
        "semantic_dimensions": (
            "" if payload["dimensions"] is None else str(payload["dimensions"])
        ),
        "semantic_reason": _canonical_json(payload["reason"]),
    }
    return values

def _verify_connection(
    connection: sqlite3.Connection, *, expected_count: int | None = None
) -> dict[str, Any]:
    integrity_rows = [row[0] for row in connection.execute("PRAGMA integrity_check")]
    foreign_key_rows = list(connection.execute("PRAGMA foreign_key_check"))
    record_count = int(connection.execute("SELECT COUNT(*) FROM records").fetchone()[0])
    fts_count = int(connection.execute("SELECT COUNT(*) FROM records_fts").fetchone()[0])
    semantic_count = int(
        connection.execute("SELECT COUNT(*) FROM semantic_vectors").fetchone()[0]
    )
    if not (
        integrity_rows == ["ok"]
        and not foreign_key_rows
        and record_count == fts_count
        and (expected_count is None or record_count == expected_count)
    ):
        raise IntegrityError(
            "Concordance verification failed: "
            f"integrity={integrity_rows!r}, foreign_keys={foreign_key_rows!r}, "
            f"records={record_count}, fts={fts_count}, expected={expected_count}"
        )

    metadata = {
        str(row[0]): str(row[1])
        for row in connection.execute("SELECT key, value FROM metadata")
    }
    status = metadata.get("semantic_status")
    enabled = metadata.get("semantic_enabled")
    try:
        declared_count = int(metadata.get("semantic_vector_count", "-1"))
    except ValueError as exc:
        raise IntegrityError("Semantic vector count metadata is invalid") from exc
    if declared_count != semantic_count:
        raise IntegrityError(
            "Semantic vector count does not match index metadata"
        )
    if status not in {"disabled", "current", "unavailable"}:
        raise IntegrityError("Semantic index status metadata is invalid")
    if enabled != ("false" if status == "disabled" else "true"):
        raise IntegrityError("Semantic enabled metadata is inconsistent")

    try:
        config_value = json.loads(
            metadata.get("semantic_config", ""),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_json,
        )
        identity_value = json.loads(
            metadata.get("semantic_identity", ""),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_json,
        )
        reason_value = json.loads(
            metadata.get("semantic_reason", ""),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_json,
        )
    except ValueError as exc:
        raise IntegrityError(f"Semantic metadata JSON is invalid: {exc}") from exc

    dimensions: int | None = None
    if status == "disabled":
        if (
            semantic_count != 0
            or config_value is not None
            or identity_value is not None
            or metadata.get("semantic_dimensions") != ""
            or reason_value is not None
        ):
            raise IntegrityError("Disabled semantic metadata is inconsistent")
    else:
        try:
            config = SemanticIndexConfig.from_value(config_value)
        except SemanticError as exc:
            raise IntegrityError(f"Semantic config metadata is invalid: {exc}") from exc
        if status == "current":
            try:
                identity = validate_provider_identity(identity_value, config)
                dimensions = int(metadata.get("semantic_dimensions", ""))
            except (SemanticError, ValueError) as exc:
                raise IntegrityError(
                    f"Current semantic identity metadata is invalid: {exc}"
                ) from exc
            if dimensions < 1 or semantic_count != record_count or reason_value is not None:
                raise IntegrityError("Current semantic index coverage is incomplete")
            for row in connection.execute(
                "SELECT record_id, input_digest, dimensions, vector, norm "
                "FROM semantic_vectors ORDER BY record_id"
            ):
                if re.fullmatch(r"[0-9a-f]{64}", str(row[1])) is None:
                    raise IntegrityError(
                        "Semantic vector input digest is invalid"
                    )
                if int(row[2]) != dimensions:
                    raise IntegrityError(
                        "Semantic vector dimensions do not match index identity"
                    )
                try:
                    values = unpack_vector(row[3], int(row[2]))
                except SemanticError as exc:
                    raise IntegrityError(str(exc)) from exc
                computed_norm = math.sqrt(sum(value * value for value in values))
                stored_norm = float(row[4])
                if (
                    not math.isfinite(stored_norm)
                    or not math.isclose(
                        computed_norm, stored_norm, rel_tol=1e-6, abs_tol=1e-7
                    )
                ):
                    raise IntegrityError("Semantic vector norm does not verify")
            _ = identity
        else:
            if (
                semantic_count != 0
                or metadata.get("semantic_dimensions") != ""
                or not isinstance(reason_value, dict)
                or not isinstance(reason_value.get("code"), str)
                or not isinstance(reason_value.get("message"), str)
            ):
                raise IntegrityError("Unavailable semantic metadata is inconsistent")
            if identity_value is not None:
                try:
                    validate_provider_identity(identity_value, config)
                except SemanticError as exc:
                    raise IntegrityError(
                        f"Unavailable semantic identity metadata is invalid: {exc}"
                    ) from exc

    return {
        "integrity": "ok",
        "foreign_keys": "ok",
        "record_count": record_count,
        "fts_count": fts_count,
        "fts_parity": True,
        "semantic": {
            "status": status,
            "vector_count": semantic_count,
            "dimensions": dimensions,
            "coverage_parity": (
                semantic_count == record_count if status == "current" else None
            ),
        },
    }


def _create_index(
    path: Path,
    snapshot: CanonicalSnapshot,
    records: Sequence[Mapping[str, Any]],
    semantic_payload: Mapping[str, Any],
) -> dict[str, Any]:
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA page_size = 4096")
        connection.executescript(_SCHEMA_SQL)
        fingerprint = _content_fingerprint(records)
        for record in records:
            state = record["state"]
            connection.execute(
                """
                INSERT INTO records(
                    id, title, body, kind, revision, lifecycle, sensitivity,
                    review, dispute, origin, source_json, provenance_json,
                    relations_json, canonical_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"], record["title"], record["body"], record["kind"],
                    record["revision"], state["lifecycle"],
                    state["sensitivity"], state["review"],
                    state["dispute"], state["origin"],
                    _canonical_json(record["source"]),
                    _canonical_json(record["provenance"]),
                    _canonical_json(record["relations"]),
                    _canonical_json(record["canonical"]),
                ),
            )
            connection.executemany(
                "INSERT INTO citations(record_id, ordinal, citation_json) VALUES (?, ?, ?)",
                [
                    (record["id"], ordinal, _canonical_json(citation))
                    for ordinal, citation in enumerate(_citations_for(record))
                ],
            )
        connection.executemany(
            """
            INSERT INTO semantic_vectors(
                record_id, input_digest, dimensions, vector, norm
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    row["record_id"], row["input_digest"], row["dimensions"],
                    row["vector"], row["norm"],
                )
                for row in semantic_payload["rows"]
            ],
        )
        metadata = {
            "schema": INDEX_SCHEMA,
            "builder": BUILDER_ID,
            "workspace_id": snapshot.workspace_id,
            "generation": str(snapshot.generation),
            "canonical_snapshot": snapshot.relative_path,
            "canonical_snapshot_digest": snapshot.digest,
            "content_fingerprint": fingerprint,
            "record_count": str(len(records)),
            **_semantic_metadata(semantic_payload),
        }
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)", sorted(metadata.items())
        )
        connection.execute("INSERT INTO records_fts(records_fts) VALUES ('rebuild')")
        connection.execute(
            "INSERT INTO records_fts(records_fts, rank) VALUES ('integrity-check', 1)"
        )
        connection.commit()
        checks = _verify_connection(connection, expected_count=len(records))
        connection.execute("VACUUM")
        connection.commit()
        return {
            "record_count": len(records),
            "content_fingerprint": fingerprint,
            "checks": checks,
            "semantic": _semantic_public(semantic_payload),
        }
    except sqlite3.DatabaseError as exc:
        raise IntegrityError(f"Could not build Concordance index: {exc}") from exc
    finally:
        connection.close()

def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_json(value, pretty=True))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _safe_component(value: str, *, limit: int = 64) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return (slug or "record")[:limit].rstrip("-") or "record"


def _note_filename(record_id: str, title: str) -> str:
    identity = sha256(record_id.encode("utf-8")).hexdigest()[:16]
    return (
        f"{_safe_component(title, limit=48)}--"
        f"{_safe_component(record_id, limit=20)}-{identity}.md"
    )


def _markdown_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def _safe_markdown_body(body: str) -> str:
    return html.escape(body, quote=False).replace("![[", r"\![[")


def _source_locator(source: Any) -> str | None:
    if isinstance(source, str) and source:
        return source
    if isinstance(source, dict):
        for key in ("url", "uri", "path", "locator", "id"):
            value = source.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _render_note(
    row: sqlite3.Row, *, filenames: Mapping[str, str],
    workspace_id: str, generation: int, digest: str,
) -> str:
    state = {axis: row[axis] for axis in _STATE_AXES}
    source = json.loads(row["source_json"])
    provenance = json.loads(row["provenance_json"])
    relations = [
        relation
        for relation in json.loads(row["relations_json"])
        if isinstance(relation, dict)
        and relation.get("review") in _APPROVED_REVIEWS
    ]
    lines = [
        "---",
        f"id: {_canonical_json(row['id'])}",
        f"workspace_id: {_canonical_json(workspace_id)}",
        f"generation: {generation}",
        "canonical: false",
        f"canonical_snapshot_digest: {_canonical_json(digest)}",
        f"kind: {_canonical_json(row['kind'])}",
        f"revision: {row['revision']}",
    ]
    lines.extend(f"{key}: {_canonical_json(value)}" for key, value in state.items())
    lines.extend([
        "---", "", f"# {_markdown_label(row['title'])}", "",
        "> [!note] Derived Concordance view",
        "> Rebuildable navigation only; edit the canonical Commonplace record.",
        "", _safe_markdown_body(row["body"]), "", "## Provenance", "",
    ])
    locator = _source_locator(source)
    lines.append(f"- Source: {locator}" if locator else "- Source locator: unavailable")
    lines.append(f"- Source packet: {_canonical_json(source)}")
    lines.append(f"- Provenance: {_canonical_json(provenance)}")
    if relations:
        lines.extend(["", "## Relations", ""])
        for relation in sorted(relations, key=_canonical_json):
            if isinstance(relation, dict):
                relation_type = str(relation.get("type", "related"))
                target = relation.get("target", relation.get("target_id"))
                epistemic = relation.get("epistemic")
                qualifiers = [
                    str(relation.get("origin", "unknown")),
                    str(relation.get("review", "unknown")),
                ]
                if epistemic is not None:
                    qualifiers.append(str(epistemic))
                label = relation_type + " (" + ", ".join(qualifiers) + ")"
                if isinstance(target, str) and target in filenames:
                    lines.append(
                        f"- {label} -> [[{filenames[target][:-3]}|{_markdown_label(target)}]]"
                    )
                else:
                    lines.append(f"- {label} -> {target}")
            else:
                lines.append(f"- {relation}")
    return "\n".join(lines).rstrip() + "\n"


def _open_readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _render_views_from_index(
    index_path: Path, views_root: Path, pointer: Mapping[str, Any],
    included_sensitivities: Sequence[str],
) -> tuple[Path, str, int, int]:
    sensitivities = tuple(dict.fromkeys(included_sensitivities))
    if not sensitivities:
        raise ContractError("At least one Markdown sensitivity must be selected")
    staging = views_root / f".staging-{uuid.uuid4().hex}"
    final = views_root / (
        f"g{pointer['generation']}-{str(pointer['canonical_snapshot_digest'])[:12]}"
        f"-{uuid.uuid4().hex[:10]}"
    )
    staging.mkdir(parents=True, exist_ok=False)
    connection = _open_readonly(index_path)
    try:
        placeholders = ",".join("?" for _ in sensitivities)
        approved_rows = list(connection.execute(
            f"""
            SELECT * FROM records
            WHERE sensitivity IN ({placeholders})
              AND lifecycle = 'current'
              AND review IN (?, ?)
            ORDER BY id
            """,
            (*sensitivities, *_APPROVED_REVIEWS),
        ))
        review_rows = list(connection.execute(
            f"""
            SELECT * FROM records
            WHERE sensitivity IN ({placeholders})
              AND lifecycle = 'current'
              AND review NOT IN (?, ?)
            ORDER BY id
            """,
            (*sensitivities, *_APPROVED_REVIEWS),
        ))
        relation_rows = list(connection.execute(
            f"""
            SELECT id, title, revision, relations_json FROM records
            WHERE sensitivity IN ({placeholders})
              AND lifecycle = 'current'
            ORDER BY id
            """,
            sensitivities,
        ))
        filenames = {
            row["id"]: _note_filename(row["id"], row["title"])
            for row in approved_rows
        }
        approved_manifest = []
        for row in approved_rows:
            filename = filenames[row["id"]]
            content = _render_note(
                row, filenames=filenames, workspace_id=str(pointer["workspace_id"]),
                generation=int(pointer["generation"]),
                digest=str(pointer["canonical_snapshot_digest"]),
            )
            (staging / filename).write_text(content, encoding="utf-8", newline="\n")
            approved_manifest.append({
                "id": row["id"], "revision": row["revision"], "file": filename,
                "sha256": sha256(content.encode("utf-8")).hexdigest(),
            })

        index_lines = [
            "---", f"workspace_id: {_canonical_json(pointer['workspace_id'])}",
            f"generation: {pointer['generation']}", "canonical: false",
            f"canonical_snapshot_digest: {_canonical_json(pointer['canonical_snapshot_digest'])}",
            "---", "", "# Nova Commonplace Concordance", "",
            "> Derived admitted view. Canonical edits belong in Commonplace.", "",
        ]
        for row in approved_rows:
            index_lines.append(
                f"- [[{filenames[row['id']][:-3]}|{_markdown_label(row['title'])}]] "
                f"(revision {row['revision']}; {row['kind']}, "
                f"{row['sensitivity']}, {row['review']})"
            )
        index_content = "\n".join(index_lines).rstrip() + "\n"
        (staging / "Index.md").write_text(index_content, encoding="utf-8", newline="\n")

        inbox_lines = [
            "---", f"workspace_id: {_canonical_json(pointer['workspace_id'])}",
            f"generation: {pointer['generation']}", "canonical: false",
            "review_inbox: true",
            f"canonical_snapshot_digest: {_canonical_json(pointer['canonical_snapshot_digest'])}",
            "---", "", "# Concordance Review Inbox", "",
            "> Derived admission queue. These records are not in the approved wiki.", "",
        ]
        inbox_manifest = []
        for row in review_rows:
            inbox_lines.append(
                f"- {_markdown_label(row['title'])} "
                f"(id: {row['id']}; revision: {row['revision']}; "
                f"kind: {row['kind']}; review: {row['review']}; "
                f"origin: {row['origin']}; dispute: {row['dispute']})"
            )
            inbox_manifest.append({
                "kind": "record",
                "id": row["id"],
                "revision": row["revision"],
                "review": row["review"],
                "origin": row["origin"],
            })
        for row in relation_rows:
            for relation in json.loads(row["relations_json"]):
                if (
                    not isinstance(relation, dict)
                    or relation.get("review") in _APPROVED_REVIEWS
                ):
                    continue
                inbox_lines.append(
                    f"- Pending relation on {_markdown_label(row['title'])} "
                    f"(record: {row['id']}; type: {relation.get('type')}; "
                    f"target: {relation.get('target_id')}; "
                    f"origin: {relation.get('origin')}; "
                    f"review: {relation.get('review')})"
                )
                inbox_manifest.append(
                    {
                        "kind": "relation",
                        "record_id": row["id"],
                        "record_revision": row["revision"],
                        "type": relation.get("type"),
                        "target_id": relation.get("target_id"),
                        "origin": relation.get("origin"),
                        "review": relation.get("review"),
                    }
                )
        inbox_content = "\n".join(inbox_lines).rstrip() + "\n"
        (staging / "Review Inbox.md").write_text(
            inbox_content, encoding="utf-8", newline="\n"
        )

        manifest = {
            "schema": VIEWS_SCHEMA, "builder": BUILDER_ID,
            "workspace_id": pointer["workspace_id"], "generation": pointer["generation"],
            "canonical_snapshot_digest": pointer["canonical_snapshot_digest"],
            "canonical": False, "included_sensitivities": list(sensitivities),
            "approved_records": approved_manifest,
            "review_inbox_records": inbox_manifest,
            "index_sha256": sha256(index_content.encode("utf-8")).hexdigest(),
            "review_inbox_sha256": sha256(inbox_content.encode("utf-8")).hexdigest(),
        }
        manifest_content = _canonical_json(manifest, pretty=True)
        (staging / "manifest.json").write_text(
            manifest_content, encoding="utf-8", newline="\n"
        )
        manifest_digest = sha256(manifest_content.encode("utf-8")).hexdigest()
        verification_pointer = {
            **pointer,
            "views_manifest_sha256": manifest_digest,
            "view_record_count": len(approved_manifest),
            "review_inbox_record_count": len(inbox_manifest),
        }
        _verify_views(staging, verification_pointer)
        os.replace(staging, final)
        return (
            final,
            manifest_digest,
            len(approved_manifest),
            len(inbox_manifest),
        )
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    finally:
        connection.close()


def _prune_derived(
    home: Path, *, current_index: Path, current_views: Path
) -> dict[str, Any]:
    """Remove every noncurrent projection, including abandoned staging artifacts."""

    policy = PathPolicy(home)
    roots_and_kept = (
        (policy.confined("indexes"), policy.assert_confined(current_index)),
        (policy.confined("views"), policy.assert_confined(current_views)),
    )
    removed: list[str] = []
    failures: list[str] = []
    for root, kept in roots_and_kept:
        try:
            kept.relative_to(root)
        except ValueError as exc:
            raise IntegrityError("Current derived artifact escapes Concordance custody") from exc
        for child in list(root.iterdir()):
            try:
                if child == kept:
                    continue
                relative = child.relative_to(policy.root).as_posix()
                if _is_linklike(child) or child.is_file():
                    child.unlink()
                elif child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
                removed.append(relative)
            except OSError as exc:
                failures.append(f"{child}: {exc}")
        leftovers = [child for child in root.iterdir() if child != kept]
        failures.extend(f"{child}: remained after cleanup" for child in leftovers)
    if failures:
        raise IntegrityError(
            "Published current Concordance but could not purge obsolete derived "
            "artifacts: " + "; ".join(failures)
        )
    return {"status": "ok", "removed": sorted(set(removed))}


def _is_linklike(path: Path) -> bool:
    return path.is_symlink() or bool(
        getattr(path, "is_junction", lambda: False)()
    )


def _remove_managed_entry(path: Path) -> None:
    """Remove one lexical entry without following symlinks or junctions."""
    if _is_linklike(path) or path.is_file():
        path.unlink()
        return
    if path.is_dir():
        for child in list(path.iterdir()):
            _remove_managed_entry(child)
        path.rmdir()
        return
    path.unlink()


def invalidate_concordance(
    concordance_home: os.PathLike[str] | str,
) -> dict[str, Any]:
    """Unpublish first, then purge managed projections without following links."""

    home = Path(os.path.abspath(os.fspath(Path(concordance_home).expanduser())))
    removed: list[str] = []
    errors: list[dict[str, str]] = []

    if os.path.lexists(home) and (_is_linklike(home) or not home.is_dir()):
        return {
            "status": "purge_incomplete",
            "ok": False,
            "canonical": False,
            "removed": [],
            "errors": [{
                "path": ".",
                "error": "Concordance home is not a direct directory; refusing to follow it",
            }],
            "remaining": ["."],
        }

    def relative(path: Path) -> str:
        return path.relative_to(home).as_posix()

    state_root = home / "state"
    pointer = state_root / "current.json"
    if os.path.lexists(state_root) and (_is_linklike(state_root) or not state_root.is_dir()):
        try:
            _remove_managed_entry(state_root)
            removed.append(relative(state_root))
        except OSError as exc:
            errors.append({"path": relative(state_root), "error": str(exc)})
    elif os.path.lexists(pointer):
        try:
            if pointer.is_dir() and not _is_linklike(pointer):
                raise IntegrityError("Published pointer path is an unexpected directory")
            _remove_managed_entry(pointer)
            removed.append(relative(pointer))
        except (OSError, ConcordanceError) as exc:
            errors.append({"path": relative(pointer), "error": str(exc)})

    for root_name in ("indexes", "views"):
        root = home / root_name
        if not os.path.lexists(root):
            continue
        try:
            if _is_linklike(root) or root.is_file():
                _remove_managed_entry(root)
                removed.append(relative(root))
                continue
            if not root.is_dir():
                raise IntegrityError("Managed artifact root has an unsafe type")
            for child in list(root.iterdir()):
                try:
                    _remove_managed_entry(child)
                    removed.append(relative(child))
                except OSError as exc:
                    errors.append({"path": relative(child), "error": str(exc)})
        except (OSError, ConcordanceError) as exc:
            errors.append({"path": relative(root), "error": str(exc)})

    remaining: list[str] = []
    if os.path.lexists(state_root):
        if _is_linklike(state_root) or not state_root.is_dir():
            remaining.append(relative(state_root))
        elif os.path.lexists(pointer):
            remaining.append(relative(pointer))
    for root_name in ("indexes", "views"):
        root = home / root_name
        if not os.path.lexists(root):
            continue
        if _is_linklike(root) or not root.is_dir():
            remaining.append(relative(root))
            continue
        remaining.extend(relative(child) for child in root.iterdir())

    if remaining:
        known = {(item["path"], item["error"]) for item in errors}
        for item in remaining:
            error = "managed derived artifact remained after invalidation"
            if (item, error) not in known:
                errors.append({"path": item, "error": error})
    ok = not errors and not remaining
    return {
        "status": "ok" if ok else "purge_incomplete",
        "ok": ok,
        "canonical": False,
        "removed": sorted(set(removed)),
        "errors": errors,
        "remaining": sorted(set(remaining)),
    }


def build_concordance(
    canonical_home: os.PathLike[str] | str,
    concordance_home: os.PathLike[str] | str,
    *,
    markdown_sensitivities: Sequence[str] = DEFAULT_MARKDOWN_SENSITIVITIES,
    semantic_config: (
        SemanticIndexConfig | Mapping[str, Any] | bool | None
    ) = None,
    embedding_provider: Any | None = None,
) -> dict[str, Any]:
    """Build and atomically publish a fresh derived index and Markdown views.

    With no explicit or previously published semantic config this remains a
    lexical-only build. A published config is inherited so ordinary rebuilds do
    not silently shed semantic coverage; pass False to disable it explicitly.
    """

    snapshot = _load_canonical_snapshot(canonical_home)
    records = _active_records(snapshot)
    policy = PathPolicy(concordance_home)
    home = policy.root
    if os.path.lexists(home) and not home.is_dir():
        raise IntegrityError("Concordance home must be a direct directory")
    home.mkdir(parents=True, exist_ok=True)
    policy = PathPolicy(home)

    managed: dict[str, Path] = {}
    for name in ("indexes", "views", "state"):
        directory = policy.confined(name)
        if os.path.lexists(directory) and not directory.is_dir():
            raise IntegrityError(f"Concordance managed root {name!r} is not a directory")
        directory.mkdir(parents=True, exist_ok=True)
        managed[name] = policy.assert_confined(directory)

    resolved_config, config_source = _resolve_semantic_config(
        policy, semantic_config
    )
    if embedding_provider is not None and resolved_config is None:
        raise SemanticContractError(
            "embedding_provider requires an explicit or inherited semantic config"
        )

    temporary = policy.confined(
        "indexes", f".building-{uuid.uuid4().hex}.sqlite3"
    )
    final = policy.confined(
        "indexes",
        f"g{snapshot.generation}-{snapshot.digest[:12]}-{uuid.uuid4().hex[:10]}.sqlite3",
    )
    try:
        semantic_payload = _prepare_semantic_payload(
            records,
            policy,
            resolved_config,
            config_source,
            embedding_provider,
        )
        build_result = _create_index(
            temporary, snapshot, records, semantic_payload
        )
        os.replace(temporary, final)
        final = policy.assert_confined(final)
        pointer: dict[str, Any] = {
            "schema": POINTER_SCHEMA,
            "builder": BUILDER_ID,
            "workspace_id": snapshot.workspace_id,
            "generation": snapshot.generation,
            "canonical_snapshot": snapshot.relative_path,
            "canonical_snapshot_digest": snapshot.digest,
            "index": final.relative_to(home).as_posix(),
            "index_sha256": _sha256_path(final),
            "content_fingerprint": build_result["content_fingerprint"],
            "record_count": build_result["record_count"],
            "canonical": False,
            "semantic_config": (
                resolved_config.to_dict()
                if resolved_config is not None
                else None
            ),
            "semantic": build_result["semantic"],
        }
        view_path, manifest_digest, view_count, inbox_count = _render_views_from_index(
            final, managed["views"], pointer, markdown_sensitivities
        )
        view_path = policy.assert_confined(view_path)
        pointer.update({
            "views": view_path.relative_to(home).as_posix(),
            "views_manifest_sha256": manifest_digest,
            "view_record_count": view_count,
            "review_inbox_record_count": inbox_count,
            "markdown_sensitivities": list(dict.fromkeys(markdown_sensitivities)),
        })
        _atomic_write_json(policy.confined("state", "current.json"), pointer)
        cleanup = _prune_derived(
            home, current_index=final, current_views=view_path
        )
        return {
            **pointer,
            "status": "current",
            "checks": build_result["checks"],
            "cleanup": cleanup,
        }
    except BaseException:
        if os.path.lexists(temporary) and not _is_linklike(temporary):
            temporary.unlink(missing_ok=True)
        raise

def _metadata(connection: sqlite3.Connection) -> dict[str, str]:
    return {
        str(row["key"]): str(row["value"])
        for row in connection.execute("SELECT key, value FROM metadata")
    }


def _verify_views(
    views_path: Path, pointer: Mapping[str, Any]
) -> dict[str, Any]:
    manifest_path = views_path / "manifest.json"
    expected_manifest_digest = pointer.get("views_manifest_sha256")
    if (
        not isinstance(expected_manifest_digest, str)
        or _sha256_path(manifest_path) != expected_manifest_digest
    ):
        raise IntegrityError("Published Concordance views manifest digest mismatch")
    manifest = _read_json(manifest_path)
    expected_binding = {
        "schema": VIEWS_SCHEMA,
        "builder": BUILDER_ID,
        "workspace_id": pointer.get("workspace_id"),
        "generation": pointer.get("generation"),
        "canonical_snapshot_digest": pointer.get("canonical_snapshot_digest"),
        "canonical": False,
    }
    actual_binding = {key: manifest.get(key) for key in expected_binding}
    if actual_binding != expected_binding:
        raise IntegrityError("Views manifest does not match its Concordance pointer")

    approved = manifest.get("approved_records")
    inbox = manifest.get("review_inbox_records")
    if not isinstance(approved, list) or not isinstance(inbox, list):
        raise IntegrityError("Views manifest record lists are invalid")
    if len(approved) != pointer.get("view_record_count"):
        raise IntegrityError("Approved view count does not match its pointer")
    if len(inbox) != pointer.get("review_inbox_record_count"):
        raise IntegrityError("Review inbox count does not match its pointer")

    expected_markdown = {"Index.md", "Review Inbox.md"}
    seen_ids: set[str] = set()
    seen_files: set[str] = set()
    for item in approved:
        if (
            not isinstance(item, dict)
            or set(item) != {"id", "revision", "file", "sha256"}
            or isinstance(item["revision"], bool)
            or not isinstance(item["revision"], int)
            or item["revision"] < 1
        ):
            raise IntegrityError("Approved view manifest entry is invalid")
        if item["id"] in seen_ids:
            raise IntegrityError("Approved view manifest contains duplicate record IDs")
        if item["file"] in seen_files:
            raise IntegrityError("Approved view manifest contains duplicate filenames")
        seen_ids.add(item["id"])
        seen_files.add(item["file"])
        note_path = _confined_path(views_path, item["file"], field="view file")
        if not note_path.is_file() or _sha256_path(note_path) != item["sha256"]:
            raise IntegrityError(f"Derived note failed digest verification: {item['file']}")
        expected_markdown.add(Path(item["file"]).as_posix())

    for item in inbox:
        if not isinstance(item, dict):
            raise IntegrityError("Review inbox manifest entry is invalid")
        revision_key = "revision" if item.get("kind") == "record" else "record_revision"
        revision = item.get(revision_key)
        if (
            isinstance(revision, bool)
            or not isinstance(revision, int)
            or revision < 1
        ):
            raise IntegrityError("Review inbox manifest entry revision is invalid")

    for name, digest_field in (
        ("Index.md", "index_sha256"),
        ("Review Inbox.md", "review_inbox_sha256"),
    ):
        path = views_path / name
        if not path.is_file() or _sha256_path(path) != manifest.get(digest_field):
            raise IntegrityError(f"Derived view failed digest verification: {name}")
    expected_entries = expected_markdown | {"manifest.json"}
    actual_entries: set[str] = set()
    for child in views_path.iterdir():
        if _is_linklike(child) or not child.is_file():
            raise IntegrityError(
                f"Derived views contain an unmanaged or link-like entry: {child.name}"
            )
        actual_entries.add(child.name)
    if actual_entries != expected_entries:
        raise IntegrityError("Derived view file set does not match its manifest")
    return {
        "manifest": "ok",
        "approved_records": len(approved),
        "review_inbox_records": len(inbox),
        "markdown_files": len(expected_markdown),
    }


def _public_index_binding(pointer: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": INDEX_SCHEMA,
        "pointer_schema": pointer.get("schema"),
        "builder": pointer.get("builder"),
        "workspace_id": pointer.get("workspace_id"),
        "generation": pointer.get("generation"),
        "canonical_snapshot": pointer.get("canonical_snapshot"),
        "canonical_snapshot_digest": pointer.get("canonical_snapshot_digest"),
        "index": pointer.get("index"),
        "index_sha256": pointer.get("index_sha256"),
        "semantic": pointer.get("semantic"),
    }


def _verify_managed_inventory(
    policy: PathPolicy, pointer: Mapping[str, Any] | None
) -> dict[str, Any]:
    """Require the entire Concordance home to match the published projection."""

    home = policy.root
    if not os.path.lexists(home):
        return {
            "managed_empty": True,
            "root_entries": 0,
            "index_entries": 0,
            "view_entries": 0,
            "state_entries": 0,
        }
    if not home.is_dir():
        raise IntegrityError("Concordance home is not a direct directory")

    allowed_roots = {"indexes", "views", "state"}
    root_entries = {child.name for child in home.iterdir()}
    unexpected_roots = root_entries - allowed_roots
    if unexpected_roots:
        raise IntegrityError(
            f"Concordance home contains unmanaged entries: {sorted(unexpected_roots)}"
        )

    roots: dict[str, Path] = {}
    entries: dict[str, set[str]] = {}
    for name in sorted(allowed_roots):
        path = policy.confined(name)
        if os.path.lexists(path):
            if not path.is_dir():
                raise IntegrityError(
                    f"Concordance managed root {name!r} is not a direct directory"
                )
            roots[name] = path
            entries[name] = {child.name for child in path.iterdir()}
        else:
            roots[name] = path
            entries[name] = set()

    if pointer is None:
        leftovers = {
            name: sorted(values)
            for name, values in entries.items()
            if values
        }
        if leftovers:
            raise IntegrityError(
                f"Concordance is unpublished but managed artifacts remain: {leftovers}"
            )
        return {
            "managed_empty": True,
            "root_entries": len(root_entries),
            "index_entries": 0,
            "view_entries": 0,
            "state_entries": 0,
        }

    index_relative = pointer.get("index")
    views_relative = pointer.get("views")
    if not isinstance(index_relative, str) or not isinstance(views_relative, str):
        raise IntegrityError("Concordance pointer omits managed artifact paths")
    index_fragment = Path(index_relative)
    views_fragment = Path(views_relative)
    if (
        len(index_fragment.parts) != 2
        or index_fragment.parts[0] != "indexes"
        or len(views_fragment.parts) != 2
        or views_fragment.parts[0] != "views"
    ):
        raise IntegrityError("Concordance pointer paths do not match managed roots")

    expected_entries = {
        "indexes": {index_fragment.name},
        "views": {views_fragment.name},
        "state": {"current.json"},
    }
    for name, expected in expected_entries.items():
        if entries[name] != expected:
            raise IntegrityError(
                f"Concordance {name} inventory does not match the pointer: "
                f"expected={sorted(expected)!r}, actual={sorted(entries[name])!r}"
            )

    index_path = _governed_path(policy, index_relative, field="index")
    views_path = _governed_path(policy, views_relative, field="views")
    if not index_path.is_file() or _is_linklike(index_path):
        raise IntegrityError("Published Concordance index is not a direct file")
    if not views_path.is_dir() or _is_linklike(views_path):
        raise IntegrityError("Published Concordance views are not a direct directory")
    return {
        "managed_empty": False,
        "root_entries": len(root_entries),
        "index_entries": len(entries["indexes"]),
        "view_entries": len(entries["views"]),
        "state_entries": len(entries["state"]),
    }

def inspect_concordance(
    canonical_home: os.PathLike[str] | str,
    concordance_home: os.PathLike[str] | str,
) -> dict[str, Any]:
    """Inspect the complete managed projection without accepting stale state."""

    try:
        policy = PathPolicy(concordance_home)
        home = policy.root
        pointer_path = policy.confined("state", "current.json")
        if not pointer_path.is_file():
            inventory = _verify_managed_inventory(policy, None)
            return {
                "status": "unavailable",
                "reason": "Concordance has no published current pointer",
                "canonical": False,
                "managed_empty": True,
                "inventory": inventory,
            }
        pointer = _read_json(pointer_path)
        if pointer.get("schema") != POINTER_SCHEMA:
            return {
                "status": "incompatible",
                "reason": "Unsupported Concordance pointer schema",
                "canonical": False,
            }

        inventory = _verify_managed_inventory(policy, pointer)
        index_path = _governed_path(policy, pointer.get("index"), field="index")
        views_path = _governed_path(policy, pointer.get("views"), field="views")
        if _sha256_path(index_path) != pointer.get("index_sha256"):
            raise IntegrityError("Published Concordance index digest mismatch")
        if pointer.get("builder") != BUILDER_ID or pointer.get("canonical") is not False:
            raise IntegrityError("Concordance pointer builder or canonical flag is invalid")
        view_checks = _verify_views(views_path, pointer)
        snapshot = _load_canonical_snapshot(canonical_home)
        connection = _open_readonly(index_path)
        try:
            metadata = _metadata(connection)
            checks = _verify_connection(connection)
        finally:
            connection.close()
        binding = {
            "schema": metadata.get("schema"), "builder": metadata.get("builder"),
            "workspace_id": metadata.get("workspace_id"),
            "generation": metadata.get("generation"),
            "canonical_snapshot_digest": metadata.get("canonical_snapshot_digest"),
        }
        expected = {
            "schema": INDEX_SCHEMA, "builder": str(pointer.get("builder")),
            "workspace_id": str(pointer.get("workspace_id")),
            "generation": str(pointer.get("generation")),
            "canonical_snapshot_digest": str(pointer.get("canonical_snapshot_digest")),
        }
        if binding != expected:
            raise IntegrityError(f"Index metadata does not match its pointer: {binding!r}")
        if metadata.get("content_fingerprint") != pointer.get("content_fingerprint"):
            raise IntegrityError("Index content fingerprint does not match its pointer")
        if int(metadata.get("record_count", "-1")) != pointer.get("record_count"):
            raise IntegrityError("Index record count does not match its pointer")
        pointer_semantic = pointer.get("semantic")
        if not isinstance(pointer_semantic, dict):
            raise IntegrityError("Concordance pointer semantic status is invalid")
        if (
            pointer_semantic.get("status") != metadata.get("semantic_status")
            or pointer_semantic.get("vector_count")
            != int(metadata.get("semantic_vector_count", "-1"))
            or _canonical_json(pointer.get("semantic_config"))
            != metadata.get("semantic_config")
        ):
            raise IntegrityError(
                "Semantic index metadata does not match its pointer"
            )
        if (
            snapshot.workspace_id != pointer.get("workspace_id")
            or snapshot.generation != pointer.get("generation")
            or snapshot.digest != pointer.get("canonical_snapshot_digest")
        ):
            public_binding = _public_index_binding(pointer)
            return {
                "status": "stale", "reason": "Canonical current pointer has advanced",
                "canonical": False, "managed_empty": False,
                "schema": public_binding["schema"],
                "pointer_schema": public_binding["pointer_schema"],
                "builder": public_binding["builder"],
                "index": public_binding["index"],
                "index_sha256": public_binding["index_sha256"],
                "binding": public_binding,
                "indexed": {
                    **public_binding,
                    "snapshot_digest": pointer.get("canonical_snapshot_digest"),
                },
                "canonical_current": {
                    "workspace_id": snapshot.workspace_id,
                    "generation": snapshot.generation,
                    "snapshot_digest": snapshot.digest,
                },
                "inventory": inventory,
            }
        public_binding = _public_index_binding(pointer)
        return {
            "status": "current", "canonical": False, "managed_empty": False,
            "schema": public_binding["schema"],
            "pointer_schema": public_binding["pointer_schema"],
            "builder": public_binding["builder"],
            "workspace_id": snapshot.workspace_id, "generation": snapshot.generation,
            "canonical_snapshot_digest": snapshot.digest,
            "index": public_binding["index"],
            "index_sha256": public_binding["index_sha256"],
            "binding": public_binding,
            "index_path": str(index_path), "views_path": str(views_path),
            "content_fingerprint": metadata.get("content_fingerprint"),
            "checks": {**checks, "views": view_checks},
            "inventory": inventory,
            "approved_view_count": pointer.get("view_record_count"),
            "review_inbox_count": pointer.get("review_inbox_record_count"),
            "semantic": pointer_semantic,
            "semantic_config": pointer.get("semantic_config"),
        }
    except (
        CanonicalStoreError,
        ConcordanceError,
        SemanticError,
        sqlite3.DatabaseError,
        OSError,
    ) as exc:
        return {"status": "incompatible", "reason": str(exc), "canonical": False}


def _require_current(
    canonical_home: os.PathLike[str] | str,
    concordance_home: os.PathLike[str] | str,
) -> tuple[Path, dict[str, Any]]:
    inspection = inspect_concordance(canonical_home, concordance_home)
    if inspection["status"] == "stale":
        raise StaleIndexError(inspection["reason"])
    if inspection["status"] != "current":
        raise IndexUnavailableError(
            f"Concordance is {inspection['status']}: "
            f"{inspection.get('reason', 'not readable')}"
        )
    return Path(inspection["index_path"]), inspection


def _fts_expression(query: str) -> str | None:
    tokens = re.findall(r"[^\W_]+", query, flags=re.UNICODE)
    return " AND ".join(f'"{token}"' for token in tokens) if tokens else None


def _decode_citations(
    connection: sqlite3.Connection, record_id: str
) -> list[dict[str, Any]]:
    return [
        json.loads(row["citation_json"])
        for row in connection.execute(
            "SELECT citation_json FROM citations WHERE record_id = ? ORDER BY ordinal",
            (record_id,),
        )
    ]


def search_concordance(
    canonical_home: os.PathLike[str] | str,
    concordance_home: os.PathLike[str] | str,
    query: str,
    *,
    allowed_sensitivities: Sequence[str] = DEFAULT_SEARCH_SENSITIVITIES,
    limit: int = 10,
    review_inbox: bool = False,
) -> list[dict[str, Any]]:
    """Run privacy- and admission-filtered BM25 retrieval over a current index."""

    if not isinstance(query, str):
        raise ContractError("query must be a string")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ContractError("limit must be between 1 and 100")
    if isinstance(allowed_sensitivities, (str, bytes)) or not isinstance(
        allowed_sensitivities, Sequence
    ):
        raise ContractError("allowed_sensitivities must be a sequence of strings")
    sensitivities = tuple(dict.fromkeys(allowed_sensitivities))
    if any(not isinstance(value, str) or not value for value in sensitivities):
        raise ContractError("allowed_sensitivities must contain non-empty strings")
    index_path, inspection = _require_current(canonical_home, concordance_home)
    expression = _fts_expression(query)
    if expression is None:
        raise ContractError("query must contain at least one searchable token")
    if not sensitivities:
        return []
    placeholders = ",".join("?" for _ in sensitivities)
    review_predicate = (
        "r.review NOT IN (?, ?)" if review_inbox else "r.review IN (?, ?)"
    )
    candidate_sql = f"""
        SELECT r.id, r.title, r.kind, r.revision, r.lifecycle,
               r.sensitivity, r.review, r.dispute, r.origin,
               bm25(records_fts, 0.0, 5.0, 1.0, 0.5) AS score,
               snippet(records_fts, 2, '[', ']', ' . ', 28) AS excerpt
        FROM records_fts
        JOIN records AS r ON r.rowid = records_fts.rowid
        WHERE records_fts MATCH ?
          AND r.sensitivity IN ({placeholders})
          AND r.lifecycle = 'current'
          AND {review_predicate}
        ORDER BY score, r.id
        LIMIT ?
    """
    connection = _open_readonly(index_path)
    try:
        rows = list(connection.execute(
            candidate_sql, (expression, *sensitivities, *_APPROVED_REVIEWS, limit)
        ))
        return [
            {
                "id": row["id"], "title": row["title"], "kind": row["kind"],
                "revision": row["revision"],
                "state": {
                    "lifecycle": row["lifecycle"], "sensitivity": row["sensitivity"],
                    "review": row["review"], "dispute": row["dispute"],
                    "origin": row["origin"],
                },
                "score": float(row["score"]), "excerpt": row["excerpt"],
                "citations": _decode_citations(connection, row["id"]),
                "canonical": False, "review_inbox": review_inbox,
                "binding": dict(inspection["binding"]),
            }
            for row in rows
        ]
    except sqlite3.DatabaseError as exc:
        raise IntegrityError(f"Concordance search failed: {exc}") from exc
    finally:
        connection.close()


def _validated_search_sensitivities(
    allowed_sensitivities: Sequence[str],
) -> tuple[str, ...]:
    if isinstance(allowed_sensitivities, (str, bytes)) or not isinstance(
        allowed_sensitivities, Sequence
    ):
        raise ContractError("allowed_sensitivities must be a sequence of strings")
    sensitivities = tuple(dict.fromkeys(allowed_sensitivities))
    if any(not isinstance(value, str) or not value for value in sensitivities):
        raise ContractError(
            "allowed_sensitivities must contain non-empty strings"
        )
    return sensitivities


def _semantic_ranked(
    index_path: Path,
    inspection: Mapping[str, Any],
    query: str,
    sensitivities: Sequence[str],
    *,
    limit: int,
    review_inbox: bool,
    embedding_provider: Any | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    semantic = inspection.get("semantic")
    if not isinstance(semantic, Mapping) or semantic.get("status") != "current":
        reason = (
            semantic.get("reason")
            if isinstance(semantic, Mapping)
            else None
        )
        raise SemanticUnavailableError(
            "Concordance has no current semantic projection"
            + (f": {reason}" if reason else "")
        )
    config = SemanticIndexConfig.from_value(
        inspection.get("semantic_config")
    )
    provider = embedding_provider or OllamaEmbeddingProvider(config)
    current_identity = _call_provider_identity(provider, config)

    connection = _open_readonly(index_path)
    try:
        metadata = _metadata(connection)
        try:
            indexed_identity = json.loads(
                metadata["semantic_identity"],
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_nonfinite_json,
            )
            dimensions = int(metadata["semantic_dimensions"])
        except (KeyError, ValueError) as exc:
            raise SemanticIntegrityError(
                "semantic identity metadata is unreadable"
            ) from exc
        if current_identity != indexed_identity:
            raise SemanticModelDriftError(
                "local embedding model digest differs from the indexed model; "
                "rebuild Concordance before semantic retrieval"
            )

        raw_query = _call_provider_embed(provider, config, [query])
        packed, query_dimensions = validate_vectors(
            raw_query,
            expected_count=1,
            expected_dimensions=dimensions,
        )
        final_identity = _call_provider_identity(provider, config)
        if final_identity != indexed_identity:
            raise SemanticModelDriftError(
                "semantic model identity changed during query embedding"
            )
        query_vector = unpack_vector(packed[0][0], query_dimensions)

        placeholders = ",".join("?" for _ in sensitivities)
        review_predicate = (
            "r.review NOT IN (?, ?)"
            if review_inbox
            else "r.review IN (?, ?)"
        )
        # Admission and sensitivity filters are deliberately in candidate SQL,
        # before any vector blob is loaded or scored.
        rows = list(connection.execute(
            f"""
            SELECT r.id, r.title, r.body, r.kind, r.revision, r.lifecycle,
                   r.sensitivity, r.review, r.dispute, r.origin,
                   v.dimensions, v.vector, v.norm
            FROM records AS r
            JOIN semantic_vectors AS v ON v.record_id = r.id
            WHERE r.sensitivity IN ({placeholders})
              AND r.lifecycle = 'current'
              AND {review_predicate}
            ORDER BY r.id
            """,
            (*sensitivities, *_APPROVED_REVIEWS),
        ))
        scored: list[tuple[float, sqlite3.Row]] = []
        for row in rows:
            vector = unpack_vector(row["vector"], int(row["dimensions"]))
            score = cosine_similarity(
                query_vector, vector, right_norm=float(row["norm"])
            )
            scored.append((score, row))
        scored.sort(key=lambda item: (-item[0], str(item[1]["id"])))
        results = []
        for score, row in scored[:limit]:
            body = str(row["body"])
            excerpt = body if len(body) <= 280 else body[:277] + "..."
            results.append({
                "id": row["id"],
                "title": row["title"],
                "kind": row["kind"],
                "revision": row["revision"],
                "state": {
                    "lifecycle": row["lifecycle"],
                    "sensitivity": row["sensitivity"],
                    "review": row["review"],
                    "dispute": row["dispute"],
                    "origin": row["origin"],
                },
                "score": score,
                "excerpt": excerpt,
                "citations": _decode_citations(connection, row["id"]),
                "canonical": False,
                "review_inbox": review_inbox,
                "binding": dict(inspection["binding"]),
            })
        semantic_status = {
            **dict(semantic),
            "status": "current",
            "query_identity_verified": True,
            "same_model_for_index_and_query": True,
        }
        return results, semantic_status
    except sqlite3.DatabaseError as exc:
        raise SemanticIntegrityError(
            f"semantic retrieval failed: {exc}"
        ) from exc
    finally:
        connection.close()


def _component_results(
    mode: str,
    lexical: Sequence[Mapping[str, Any]],
    semantic: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    lexical_by_id = {
        str(item["id"]): (rank, item)
        for rank, item in enumerate(lexical, start=1)
    }
    semantic_by_id = {
        str(item["id"]): (rank, item)
        for rank, item in enumerate(semantic, start=1)
    }
    identities = set(lexical_by_id) | set(semantic_by_id)
    fused: list[dict[str, Any]] = []
    for record_id in identities:
        lexical_item = lexical_by_id.get(record_id)
        semantic_item = semantic_by_id.get(record_id)
        base = dict(
            (semantic_item or lexical_item)[1]  # type: ignore[index]
        )
        components: dict[str, Any] = {}
        if lexical_item is not None:
            components["lexical"] = {
                "rank": lexical_item[0],
                "score": float(lexical_item[1]["score"]),
                "score_direction": "lower_is_better",
            }
        if semantic_item is not None:
            components["semantic"] = {
                "rank": semantic_item[0],
                "score": float(semantic_item[1]["score"]),
                "score_direction": "higher_is_better",
            }
        if mode == "hybrid":
            score = sum(
                1.0 / (60.0 + component["rank"])
                for component in components.values()
            )
            base["score"] = score
            base["score_kind"] = "rrf"
        elif mode == "semantic":
            base["score_kind"] = "cosine"
        else:
            base["score_kind"] = "bm25"
        base["components"] = components
        base["retrieval"] = "direct"
        fused.append(base)
    if mode == "hybrid":
        fused.sort(key=lambda item: (-float(item["score"]), str(item["id"])))
    elif mode == "semantic":
        fused.sort(key=lambda item: (-float(item["score"]), str(item["id"])))
    else:
        fused.sort(key=lambda item: (float(item["score"]), str(item["id"])))
    return fused


def _graph_expand(
    index_path: Path,
    direct_results: Sequence[Mapping[str, Any]],
    sensitivities: Sequence[str],
    *,
    limit: int,
    review_inbox: bool,
    graph_hops: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    maximum_nodes = 50
    all_direct = [dict(item) for item in direct_results]
    metadata = {
        "requested_hops": graph_hops,
        "maximum_hops": 2,
        "maximum_nodes": maximum_nodes,
        "seed_count": 0,
        "nodes_added": 0,
        "paths_added": 0,
        "excluded_edges": 0,
        "truncated": False,
    }
    if graph_hops == 0 or not all_direct:
        return all_direct[:limit], metadata

    # Expand only the strongest bounded seed set, then fill unused result slots
    # with the remaining direct ranking. This lets graph evidence enter a full
    # semantic candidate list without allowing it to flood or erase top hits.
    seed_count = min(len(all_direct), min(5, max(1, limit // 2)))
    metadata["seed_count"] = seed_count
    selected = all_direct[:seed_count]
    direct_by_id = {str(item["id"]): item for item in all_direct}

    placeholders = ",".join("?" for _ in sensitivities)
    review_predicate = (
        "review NOT IN (?, ?)" if review_inbox else "review IN (?, ?)"
    )
    connection = _open_readonly(index_path)
    try:
        rows = list(connection.execute(
            f"""
            SELECT id, title, body, kind, revision, lifecycle, sensitivity,
                   review, dispute, origin, relations_json
            FROM records
            WHERE sensitivity IN ({placeholders})
              AND lifecycle = 'current'
              AND {review_predicate}
            ORDER BY id
            """,
            (*sensitivities, *_APPROVED_REVIEWS),
        ))
        allowed = {str(row["id"]): row for row in rows}
        adjacency: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            relations = _decode_index_json(
                str(row["relations_json"]), field="relations_json"
            )
            if not isinstance(relations, list):
                raise SemanticIntegrityError(
                    "graph relation projection is not a list"
                )
            edges: list[dict[str, Any]] = []
            for ordinal, relation in enumerate(relations):
                if not isinstance(relation, Mapping):
                    metadata["excluded_edges"] += 1
                    continue
                target = relation.get("target_id", relation.get("target"))
                if (
                    relation.get("origin") != "user_authored"
                    or relation.get("review") not in _APPROVED_REVIEWS
                    or not isinstance(relation.get("type"), str)
                    or not relation.get("type")
                    or not isinstance(target, str)
                    or target not in allowed
                ):
                    metadata["excluded_edges"] += 1
                    continue
                edges.append({
                    "from_id": str(row["id"]),
                    "from_revision": int(row["revision"]),
                    "to_id": target,
                    "type": relation["type"],
                    "origin": relation["origin"],
                    "review": relation["review"],
                    "ordinal": ordinal,
                    "provenance": "canonical_commonplace_relation",
                })
            adjacency[str(row["id"])] = sorted(
                edges,
                key=lambda item: (
                    item["type"], item["to_id"], item["ordinal"]
                ),
            )

        by_id = {str(item["id"]): item for item in selected}
        queue: list[tuple[str, str, int, list[dict[str, Any]]]] = [
            (str(item["id"]), str(item["id"]), 0, [])
            for item in selected
            if str(item["id"]) in allowed
        ]
        best_depth = {record_id: 0 for record_id in by_id}
        processed = 0
        cursor = 0
        while cursor < len(queue) and processed < maximum_nodes:
            root_id, source_id, depth, path = queue[cursor]
            cursor += 1
            processed += 1
            if depth >= graph_hops:
                continue
            for edge in adjacency.get(source_id, []):
                target_id = edge["to_id"]
                next_depth = depth + 1
                next_path = [*path, edge]
                existing = by_id.get(target_id)
                if existing is not None:
                    paths = existing.setdefault("graph_paths", [])
                    if next_path not in paths:
                        paths.append(next_path)
                        graph_component = existing.setdefault(
                            "components", {}
                        ).setdefault(
                            "graph",
                            {"root_ids": [], "minimum_hop": next_depth},
                        )
                        if root_id not in graph_component["root_ids"]:
                            graph_component["root_ids"].append(root_id)
                        graph_component["minimum_hop"] = min(
                            graph_component["minimum_hop"], next_depth
                        )
                        existing["retrieval"] = "direct+graph"
                        metadata["paths_added"] += 1
                elif len(selected) < limit and len(by_id) < maximum_nodes:
                    if target_id in direct_by_id:
                        hit = dict(direct_by_id[target_id])
                        hit["components"] = dict(hit.get("components", {}))
                        hit["components"]["graph"] = {
                            "root_ids": [root_id],
                            "minimum_hop": next_depth,
                        }
                        hit["retrieval"] = "direct+graph"
                        hit["graph_paths"] = [next_path]
                    else:
                        row = allowed[target_id]
                        body = str(row["body"])
                        hit = {
                            "id": target_id,
                            "title": row["title"],
                            "kind": row["kind"],
                            "revision": row["revision"],
                            "state": {
                                "lifecycle": row["lifecycle"],
                                "sensitivity": row["sensitivity"],
                                "review": row["review"],
                                "dispute": row["dispute"],
                                "origin": row["origin"],
                            },
                            "score": 0.0,
                            "score_kind": "graph_path",
                            "excerpt": (
                                body if len(body) <= 280 else body[:277] + "..."
                            ),
                            "citations": _decode_citations(
                                connection, target_id
                            ),
                            "canonical": False,
                            "review_inbox": review_inbox,
                            "binding": dict(selected[0]["binding"]),
                            "components": {
                                "graph": {
                                    "root_ids": [root_id],
                                    "minimum_hop": next_depth,
                                }
                            },
                            "retrieval": "graph",
                            "graph_paths": [next_path],
                        }
                    selected.append(hit)
                    by_id[target_id] = hit
                    metadata["nodes_added"] += 1
                    metadata["paths_added"] += 1
                previous_depth = best_depth.get(target_id)
                if previous_depth is None or next_depth < previous_depth:
                    best_depth[target_id] = next_depth
                    queue.append((root_id, target_id, next_depth, next_path))
            if len(selected) >= limit:
                break

        for item in all_direct[seed_count:]:
            if len(selected) >= limit:
                break
            record_id = str(item["id"])
            if record_id not in by_id:
                selected.append(item)
                by_id[record_id] = item
        if cursor < len(queue) or processed >= maximum_nodes:
            metadata["truncated"] = True
        return selected[:limit], metadata
    except sqlite3.DatabaseError as exc:
        raise SemanticIntegrityError(
            f"graph retrieval failed: {exc}"
        ) from exc
    finally:
        connection.close()

def hybrid_search_concordance(
    canonical_home: os.PathLike[str] | str,
    concordance_home: os.PathLike[str] | str,
    query: str,
    *,
    mode: str = "hybrid",
    allowed_sensitivities: Sequence[str] = DEFAULT_SEARCH_SENSITIVITIES,
    limit: int = 10,
    review_inbox: bool = False,
    allow_degraded: bool = False,
    graph_hops: int = 0,
    embedding_provider: Any | None = None,
) -> dict[str, Any]:
    """Run typed lexical, semantic, or RRF retrieval with optional safe graph hops."""

    if not isinstance(query, str) or not query.strip():
        raise ContractError("query must be a non-empty string")
    if mode not in {"lexical", "semantic", "hybrid"}:
        raise ContractError("mode must be lexical, semantic, or hybrid")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ContractError("limit must be between 1 and 100")
    if not isinstance(review_inbox, bool):
        raise ContractError("review_inbox must be a boolean")
    if not isinstance(allow_degraded, bool):
        raise ContractError("allow_degraded must be a boolean")
    if (
        isinstance(graph_hops, bool)
        or not isinstance(graph_hops, int)
        or not 0 <= graph_hops <= 2
    ):
        raise ContractError("graph_hops must be between 0 and 2")
    sensitivities = _validated_search_sensitivities(
        allowed_sensitivities
    )
    index_path, inspection = _require_current(
        canonical_home, concordance_home
    )
    if not sensitivities:
        return {
            "schema": "nova.commonplace.concordance.search.v2",
            "status": "current",
            "canonical": False,
            "mode_requested": mode,
            "mode_effective": mode,
            "allow_degraded": allow_degraded,
            "degradation": None,
            "semantic": inspection.get("semantic"),
            "graph": {
                "requested_hops": graph_hops,
                "maximum_hops": 2,
                "maximum_nodes": 50,
                "nodes_added": 0,
                "paths_added": 0,
                "excluded_edges": 0,
                "truncated": False,
            },
            "results": [],
            "binding": dict(inspection["binding"]),
        }

    candidate_limit = min(100, max(limit * 4, limit))
    lexical_results: list[dict[str, Any]] = []
    semantic_results: list[dict[str, Any]] = []
    lexical_error: Exception | None = None
    semantic_error: SemanticError | None = None
    semantic_status = inspection.get("semantic")

    if mode in {"lexical", "hybrid"}:
        try:
            lexical_results = search_concordance(
                canonical_home,
                concordance_home,
                query,
                allowed_sensitivities=sensitivities,
                limit=candidate_limit,
                review_inbox=review_inbox,
            )
        except ContractError as exc:
            lexical_error = exc
    if mode in {"semantic", "hybrid"}:
        try:
            semantic_results, semantic_status = _semantic_ranked(
                index_path,
                inspection,
                query,
                sensitivities,
                limit=candidate_limit,
                review_inbox=review_inbox,
                embedding_provider=embedding_provider,
            )
        except SemanticError as exc:
            semantic_error = exc

    degradation = None
    effective_mode = mode
    if mode == "lexical":
        if lexical_error is not None:
            raise lexical_error
    elif mode == "semantic":
        if semantic_error is not None:
            if not allow_degraded:
                raise semantic_error
            try:
                lexical_results = search_concordance(
                    canonical_home,
                    concordance_home,
                    query,
                    allowed_sensitivities=sensitivities,
                    limit=candidate_limit,
                    review_inbox=review_inbox,
                )
            except ContractError:
                raise semantic_error
            effective_mode = "lexical"
            degradation = {
                "component": "semantic",
                "code": semantic_error.code,
                "message": str(semantic_error),
                "fallback": "lexical",
            }
    else:
        failures = [
            ("lexical", lexical_error),
            ("semantic", semantic_error),
        ]
        failures = [(name, error) for name, error in failures if error is not None]
        if failures:
            if not allow_degraded:
                raise failures[0][1]
            if lexical_error is not None and semantic_error is not None:
                raise semantic_error
            if semantic_error is not None:
                effective_mode = "lexical"
                degradation = {
                    "component": "semantic",
                    "code": semantic_error.code,
                    "message": str(semantic_error),
                    "fallback": "lexical",
                }
            else:
                effective_mode = "semantic"
                degradation = {
                    "component": "lexical",
                    "code": "lexical_query_unavailable",
                    "message": str(lexical_error),
                    "fallback": "semantic",
                }

    ranked = _component_results(
        effective_mode,
        lexical_results,
        semantic_results,
    )
    expanded, graph_status = _graph_expand(
        index_path,
        ranked,
        sensitivities,
        limit=limit,
        review_inbox=review_inbox,
        graph_hops=graph_hops,
    )
    return {
        "schema": "nova.commonplace.concordance.search.v2",
        "status": "degraded" if degradation is not None else "current",
        "canonical": False,
        "mode_requested": mode,
        "mode_effective": effective_mode,
        "allow_degraded": allow_degraded,
        "degradation": degradation,
        "semantic": semantic_status,
        "fusion": (
            {"method": "reciprocal_rank_fusion", "k": 60}
            if effective_mode == "hybrid"
            else None
        ),
        "graph": graph_status,
        "results": expanded,
        "binding": dict(inspection["binding"]),
    }

def _records_for_context(
    index_path: Path, record_ids: Sequence[str], sensitivities: Sequence[str],
    *, review_inbox: bool,
) -> dict[str, sqlite3.Row]:
    if not record_ids or not sensitivities:
        return {}
    id_marks = ",".join("?" for _ in record_ids)
    sensitivity_marks = ",".join("?" for _ in sensitivities)
    review_predicate = "review NOT IN (?, ?)" if review_inbox else "review IN (?, ?)"
    connection = _open_readonly(index_path)
    try:
        rows = list(connection.execute(
            f"""
            SELECT * FROM records
            WHERE id IN ({id_marks}) AND sensitivity IN ({sensitivity_marks})
              AND lifecycle = 'current' AND {review_predicate}
            """,
            (*record_ids, *sensitivities, *_APPROVED_REVIEWS),
        ))
        return {row["id"]: row for row in rows}
    finally:
        connection.close()


def _truncate_utf8(value: str, max_bytes: int) -> tuple[str, bool]:
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value, False
    if max_bytes <= 0:
        return "", True
    ellipsis = "…".encode("utf-8")
    if max_bytes < len(ellipsis):
        return "", True
    prefix = encoded[: max_bytes - len(ellipsis)].decode("utf-8", errors="ignore")
    return prefix.rstrip() + "…", True


def _compact_citation(
    citation: Mapping[str, Any],
) -> tuple[dict[str, Any], bool]:
    truncated = False
    record_id, record_id_truncated = _truncate_utf8(
        str(citation.get("record_id", "")), 160
    )
    truncated = truncated or record_id_truncated

    source_ref = _source_locator(citation.get("source"))
    provenance = citation.get("provenance")
    provenance_items = (
        [provenance]
        if isinstance(provenance, Mapping)
        else provenance if isinstance(provenance, list) else []
    )
    if source_ref is None:
        for item in provenance_items:
            if not isinstance(item, Mapping):
                continue
            candidate = item.get("source_ref")
            if isinstance(candidate, str) and candidate:
                source_ref = candidate
                break
    if source_ref is not None:
        source_ref, source_truncated = _truncate_utf8(source_ref, 384)
        truncated = truncated or source_truncated

    compact_span: dict[str, Any] | None = None
    source_span = citation.get("source_span")
    if isinstance(source_span, Mapping):
        compact_span = {}
        for key in ("start", "end"):
            value = source_span.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                compact_span[key] = value
            elif isinstance(value, str):
                compact_span[key], clipped = _truncate_utf8(value, 64)
                truncated = truncated or clipped
        for key in ("quote", "selector"):
            value = source_span.get(key)
            if isinstance(value, str):
                compact_span[key], clipped = _truncate_utf8(value, 320)
                truncated = truncated or clipped
        if not compact_span:
            compact_span = None

    return {
        "record_id": record_id,
        "source_ref": source_ref,
        "source_span": compact_span,
    }, truncated


def _compact_citations(
    citations: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    projected: list[dict[str, Any]] = []
    field_truncations = 0
    for citation in citations[:2]:
        compact, truncated = _compact_citation(citation)
        projected.append(compact)
        field_truncations += int(truncated)
    omitted_count = max(0, len(citations) - len(projected))
    if omitted_count or field_truncations:
        return projected, {
            "reason": "citation_projection_truncation",
            "omitted_citations": omitted_count,
            "truncated_citations": field_truncations,
        }
    return projected, None


def _context_packet_bytes(packet: Mapping[str, Any]) -> int:
    return len(_canonical_json(packet).encode("utf-8"))


def _truncate_chars(value: str, limit: int) -> tuple[str, bool]:
    if len(value) <= limit:
        return value, False
    if limit <= 0:
        return "", True
    if limit == 1:
        return "…", True
    return value[: limit - 1].rstrip() + "…", True


def build_context_packet(
    canonical_home: os.PathLike[str] | str,
    concordance_home: os.PathLike[str] | str,
    query: str,
    *,
    allowed_sensitivities: Sequence[str] = DEFAULT_SEARCH_SENSITIVITIES,
    max_chars: int = 4000,
    candidate_limit: int = 20,
    review_inbox: bool = False,
) -> dict[str, Any]:
    """Compose a bounded, explicitly non-canonical retrieval packet."""

    if (
        isinstance(max_chars, bool)
        or not isinstance(max_chars, int)
        or not 0 <= max_chars <= MAX_CONTEXT_PACKET_BYTES
    ):
        raise ContractError(
            f"max_chars must be between 0 and {MAX_CONTEXT_PACKET_BYTES}"
        )
    if (
        isinstance(candidate_limit, bool)
        or not isinstance(candidate_limit, int)
        or not 1 <= candidate_limit <= 100
    ):
        raise ContractError("candidate_limit must be between 1 and 100")

    if isinstance(allowed_sensitivities, (str, bytes)) or not isinstance(
        allowed_sensitivities, Sequence
    ):
        raise ContractError("allowed_sensitivities must be a sequence of strings")
    sensitivities = tuple(dict.fromkeys(allowed_sensitivities))
    hits = search_concordance(
        canonical_home, concordance_home, query,
        allowed_sensitivities=sensitivities, limit=candidate_limit,
        review_inbox=review_inbox,
    )
    index_path, inspection = _require_current(canonical_home, concordance_home)
    records = _records_for_context(
        index_path, [hit["id"] for hit in hits], sensitivities,
        review_inbox=review_inbox,
    )

    packet_query, query_truncated = _truncate_utf8(query, 1024)
    packet: dict[str, Any] = {
        "schema": "nova.commonplace.concordance.context.v1",
        "canonical": False,
        "review_inbox": review_inbox,
        "query": packet_query,
        "binding": dict(inspection["binding"]),
        "budget": {
            "unit": "characters",
            "limit": max_chars,
            "used": 0,
            "packet_unit": "utf-8-bytes",
            "packet_limit_bytes": MAX_CONTEXT_PACKET_BYTES,
            "packet_used_bytes": MAX_CONTEXT_PACKET_BYTES,
        },
        "context": [],
        "disagreements": [],
        "unknowns": [],
        "omissions": [],
        "omission_summary": {
            "context_items_omitted": 0,
            "context_items_truncated": 0,
            "citation_sets_truncated": 0,
            "governance_items_omitted": 0,
            "query_truncated": int(query_truncated),
            "omission_details_omitted": 0,
        },
    }

    def append_if_fits(
        collection: list[dict[str, Any]],
        item: dict[str, Any],
        *,
        reserve_bytes: int = 1024,
    ) -> bool:
        collection.append(item)
        if _context_packet_bytes(packet) <= MAX_CONTEXT_PACKET_BYTES - reserve_bytes:
            return True
        collection.pop()
        return False

    def record_omission(
        item: dict[str, Any],
        summary_key: str,
    ) -> None:
        packet["omission_summary"][summary_key] += 1
        if len(packet["omissions"]) >= 16:
            packet["omission_summary"]["omission_details_omitted"] += 1
            return
        packet["omissions"].append(item)
        if _context_packet_bytes(packet) > MAX_CONTEXT_PACKET_BYTES - 256:
            packet["omissions"].pop()
            packet["omission_summary"]["omission_details_omitted"] += 1

    if query_truncated:
        packet["omissions"].append({"reason": "query_projection_truncation"})

    for hit in hits:
        citation_count = len(hit["citations"])
        has_span = any(
            citation.get("source_span") is not None
            for citation in hit["citations"]
            if isinstance(citation, Mapping)
        )
        if hit["state"]["dispute"] in {"challenged", "contradicted"}:
            disagreement = {
                "record_id": hit["id"],
                "revision": hit["revision"],
                "dispute": hit["state"]["dispute"],
                "citation_count": citation_count,
                "source_span_available": has_span,
            }
            if not append_if_fits(packet["disagreements"], disagreement):
                record_omission(
                    {
                        "record_id": hit["id"],
                        "reason": "packet_budget_disagreement",
                    },
                    "governance_items_omitted",
                )
        if not hit["citations"] or not has_span:
            unknown = {
                "record_id": hit["id"],
                "revision": hit["revision"],
                "kind": "source_span_unavailable",
            }
            if not append_if_fits(packet["unknowns"], unknown):
                record_omission(
                    {
                        "record_id": hit["id"],
                        "reason": "packet_budget_unknown",
                    },
                    "governance_items_omitted",
                )

    if not hits:
        append_if_fits(
            packet["unknowns"],
            {"kind": "no_matching_evidence"},
        )

    used = 0
    for hit in hits:
        row = records.get(hit["id"])
        if row is None:
            record_omission(
                {"record_id": hit["id"], "reason": "filtered_or_missing"},
                "context_items_omitted",
            )
            continue

        remaining = max_chars - used
        if remaining <= 0:
            record_omission(
                {"record_id": row["id"], "reason": "context_character_budget"},
                "context_items_omitted",
            )
            continue

        original_text = f"{row['title']}\n{row['body']}"
        text, character_truncated = _truncate_chars(original_text, remaining)
        citations, citation_omission = _compact_citations(hit["citations"])
        item = {
            "record_id": row["id"],
            "revision": row["revision"],
            "text": text,
            "state": hit["state"],
            "citations": citations,
            "canonical": False,
        }

        if append_if_fits(packet["context"], item):
            used += len(text)
            if character_truncated:
                record_omission(
                    {
                        "record_id": row["id"],
                        "reason": "context_character_truncation",
                    },
                    "context_items_truncated",
                )
            if citation_omission is not None:
                record_omission(
                    {"record_id": row["id"], **citation_omission},
                    "citation_sets_truncated",
                )
            continue

        low, high, best_text = 0, len(text), ""
        while low <= high:
            middle = (low + high) // 2
            candidate_text, _ = _truncate_chars(text, middle)
            item["text"] = candidate_text
            if candidate_text and append_if_fits(packet["context"], item):
                packet["context"].pop()
                best_text = candidate_text
                low = middle + 1
            else:
                high = middle - 1
        item["text"] = best_text
        if best_text and append_if_fits(packet["context"], item):
            used += len(best_text)
            record_omission(
                {
                    "record_id": row["id"],
                    "reason": "packet_byte_budget_truncation",
                },
                "context_items_truncated",
            )
            if citation_omission is not None:
                record_omission(
                    {"record_id": row["id"], **citation_omission},
                    "citation_sets_truncated",
                )
        else:
            record_omission(
                {"record_id": row["id"], "reason": "packet_byte_budget"},
                "context_items_omitted",
            )

    packet["budget"]["used"] = used
    for _ in range(8):
        measured = _context_packet_bytes(packet)
        if packet["budget"]["packet_used_bytes"] == measured:
            break
        packet["budget"]["packet_used_bytes"] = measured
    if _context_packet_bytes(packet) > MAX_CONTEXT_PACKET_BYTES:
        raise IntegrityError("Context packet exceeded its hard UTF-8 byte budget")
    return packet


def _iter_structural_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key)
            yield from _iter_structural_strings(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            yield from _iter_structural_strings(child)


def _decode_index_json(value: str, *, field: str) -> Any:
    try:
        return json.loads(
            value,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_json,
        )
    except (TypeError, ValueError) as exc:
        raise IntegrityError(f"Concordance {field} contains invalid JSON: {exc}") from exc


def verify_absent_id_hashes(
    canonical_home: os.PathLike[str] | str,
    concordance_home: os.PathLike[str] | str,
    affected_id_hashes: Sequence[str],
) -> dict[str, Any]:
    """Prove forgotten record identities are absent from current structured surfaces."""

    if isinstance(affected_id_hashes, (str, bytes, bytearray)):
        raise ContractError("affected_id_hashes must be a sequence")
    targets = set(affected_id_hashes)
    if not targets or any(
        not isinstance(item, str)
        or re.fullmatch(r"[0-9a-f]{64}", item) is None
        for item in targets
    ):
        raise ContractError("affected_id_hashes must contain lowercase SHA-256 values")

    index_path, inspection = _require_current(canonical_home, concordance_home)
    observed: set[str] = set()
    checked_records = 0
    checked_citations = 0
    checked_vectors = 0
    connection = _open_readonly(index_path)
    try:
        for row in connection.execute(
            "SELECT id, source_json, provenance_json, relations_json, canonical_json "
            "FROM records ORDER BY id"
        ):
            checked_records += 1
            observed.add(opaque_identifier(str(row["id"])))
            for field in (
                "source_json", "provenance_json", "relations_json", "canonical_json"
            ):
                decoded = _decode_index_json(str(row[field]), field=field)
                observed.update(
                    opaque_identifier(value)
                    for value in _iter_structural_strings(decoded)
                )
        for row in connection.execute(
            "SELECT citation_json FROM citations ORDER BY record_id, ordinal"
        ):
            checked_citations += 1
            decoded = _decode_index_json(
                str(row["citation_json"]), field="citation_json"
            )
            observed.update(
                opaque_identifier(value)
                for value in _iter_structural_strings(decoded)
            )
        for row in connection.execute(
            "SELECT record_id FROM semantic_vectors ORDER BY record_id"
        ):
            checked_vectors += 1
            observed.add(opaque_identifier(str(row["record_id"])))
    except sqlite3.DatabaseError as exc:
        raise IntegrityError(f"Could not verify forgotten index identities: {exc}") from exc
    finally:
        connection.close()

    policy = PathPolicy(concordance_home)
    pointer = _read_json(policy.confined("state", "current.json"))
    views_path = _governed_path(policy, pointer.get("views"), field="views")
    manifest = _read_json(policy.assert_confined(views_path / "manifest.json"))
    observed.update(
        opaque_identifier(value)
        for value in _iter_structural_strings(manifest)
    )

    matches = sorted(targets.intersection(observed))
    ok = not matches
    return {
        "ok": ok,
        "status": "ok" if ok else "purge_incomplete",
        "canonical": False,
        "affected_id_hashes_absent": ok,
        "checked_id_hashes": sorted(targets),
        "matched_id_hashes": matches,
        "checked_records": checked_records,
        "checked_citations": checked_citations,
        "checked_vectors": checked_vectors,
        "binding": {
            "workspace_id": inspection["workspace_id"],
            "generation": inspection["generation"],
            "canonical_snapshot_digest": inspection["canonical_snapshot_digest"],
            "index_sha256": inspection["index_sha256"],
            "views_manifest_sha256": pointer["views_manifest_sha256"],
        },
    }

def rebuild_markdown_views(
    canonical_home: os.PathLike[str] | str,
    concordance_home: os.PathLike[str] | str,
    *,
    included_sensitivities: Sequence[str] = DEFAULT_MARKDOWN_SENSITIVITIES,
) -> dict[str, Any]:
    """Rebuild deterministic admitted and review-inbox views and atomically repoint."""

    index_path, inspection = _require_current(canonical_home, concordance_home)
    policy = PathPolicy(concordance_home)
    home = policy.root
    pointer_path = policy.confined("state", "current.json")
    pointer = _read_json(pointer_path)
    views_root = policy.confined("views")
    if not views_root.is_dir():
        raise IntegrityError("Concordance views root is not a direct directory")
    view_path, manifest_digest, count, inbox_count = _render_views_from_index(
        index_path, views_root, pointer, included_sensitivities
    )
    view_path = policy.assert_confined(view_path)
    pointer.update({
        "views": view_path.relative_to(home).as_posix(),
        "views_manifest_sha256": manifest_digest,
        "view_record_count": count,
        "review_inbox_record_count": inbox_count,
        "markdown_sensitivities": list(dict.fromkeys(included_sensitivities)),
    })
    _atomic_write_json(pointer_path, pointer)
    cleanup = _prune_derived(
        home, current_index=index_path, current_views=view_path
    )
    return {
        "status": "current", "canonical": False, "cleanup": cleanup,
        "workspace_id": inspection["workspace_id"],
        "generation": inspection["generation"], "views": pointer["views"],
        "views_manifest_sha256": manifest_digest, "record_count": count,
        "review_inbox_record_count": inbox_count,
    }


_OWNER_RULES: dict[str, tuple[str, ...]] = {
    "Commonplace": (
        "note", "clip", "snippet", "idea", "commonplace", "capture", "saved"
    ),
    "Dunbar": (
        "person", "people", "contact", "relationship", "birthday", "met ", "who is"
    ),
    "Corkboard": (
        "remind", "reminder", "remember to", "todo", "to-do", "due "
    ),
    "Dennis": (
        "project", "milestone", "work packet", "deliverable", "dependency",
        "project status"
    ),
    "Continuity": (
        "worldline", "continuity", "prior task", "previous task",
        "earlier conversation", "decision history", "last time"
    ),
    "Striving": (
        "striving", "pursuit", "long-term goal", "long term goal",
        "durable goal", "life goal", "ongoing goal", "aspiration"
    ),
    "Giles": (
        "giles", "authoritative file", "authoritative version",
        "authoritative source", "canonical file", "organize files",
        "document custody", "knowledge custody", "which version", "library",
        "provenance", "inventory", "disposition"
    ),
    "Dex": (
        "dex", "database", "dataset", "data quality", "lineage", "schema",
        "table", "data system"
    ),
    "Skills": (
        "skill", "capability", "augment", "praxis", "playbook"
    ),
    "Repositories": (
        "repository", " repo ", "git", "source code", "codebase", "github"
    ),
    "ExternalCorpora": (
        "corpus", "corpora", "web page", "external source", "paper",
        "article", "transcript", " url "
    ),
}


def _normalise_owner_state(owner: str, value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        status = value
        supplied: Mapping[str, Any] = {}
    elif isinstance(value, Mapping):
        status = value.get("status")
        supplied = value
    else:
        status = "incompatible"
        supplied = {"reason": "Owner state must be a status string or object"}

    if status not in _ROUTE_STATUSES:
        status = "incompatible"
        reason = "Invalid owner status contract"
    else:
        raw_reason = supplied.get("reason")
        if raw_reason is None:
            reason = (
                None
                if status == "current"
                else f"{owner} reported {status} without a reason"
            )
        elif isinstance(raw_reason, str) and raw_reason.strip():
            reason = raw_reason.strip()
        else:
            status = "incompatible"
            reason = "Invalid owner reason contract"

    detail: dict[str, Any] = {}
    if reason is not None:
        detail["reason"] = reason

    if "locator" in supplied:
        locator = supplied["locator"]
        if not isinstance(locator, str) or not locator.strip():
            status = "incompatible"
            detail = {"reason": "Invalid owner locator contract"}
        else:
            detail["locator"] = locator.strip()

    if "capabilities" in supplied:
        capabilities = supplied["capabilities"]
        if (
            isinstance(capabilities, (str, bytes))
            or not isinstance(capabilities, Sequence)
            or any(
                not isinstance(item, str) or not item.strip()
                for item in capabilities
            )
        ):
            status = "incompatible"
            detail = {"reason": "Invalid owner capabilities contract"}
        else:
            detail["capabilities"] = list(
                dict.fromkeys(item.strip() for item in capabilities)
            )

    if "generation" in supplied:
        generation = supplied["generation"]
        if (
            isinstance(generation, bool)
            or not isinstance(generation, int)
            or generation < 0
        ):
            status = "incompatible"
            detail = {"reason": "Invalid owner generation contract"}
        else:
            detail["generation"] = generation

    if status != "current" and (
        not isinstance(detail.get("reason"), str)
        or not detail["reason"].strip()
    ):
        detail["reason"] = f"{owner} is {status}; no usable reason was supplied"

    return {
        "owner": owner,
        "status": status,
        "operation": "read",
        "writes_allowed": False,
        **detail,
    }


def route_query(
    query: str, owner_states: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return typed, read-only owner routes; never dispatch or mutate an owner."""

    if not isinstance(query, str):
        raise ContractError("query must be a string")
    if owner_states is not None and not isinstance(owner_states, Mapping):
        raise ContractError("owner_states must be a mapping")
    supplied = dict(owner_states or {})
    lowered = query.casefold()
    explicit_pattern = (
        r"\b("
        + "|".join(re.escape(owner.casefold()) for owner in _OWNER_NAMES)
        + r")\s*:"
    )
    explicit = re.findall(explicit_pattern, lowered)
    selected = [owner for owner in _OWNER_NAMES if owner.casefold() in explicit]
    if not selected:
        selected = [
            owner for owner, signals in _OWNER_RULES.items()
            if any(signal in lowered for signal in signals)
        ]
    if not selected:
        selected = ["Commonplace"]
    defaults = {
        owner: {
            "status": "unavailable",
            "reason": "Owner state was not supplied",
        }
        for owner in _OWNER_NAMES
    }
    routes = [
        _normalise_owner_state(owner, supplied.get(owner, defaults[owner]))
        for owner in _OWNER_NAMES if owner in selected
    ]
    statuses = {route["status"] for route in routes}
    aggregate = next(iter(statuses)) if len(statuses) == 1 else "partial"
    return {
        "schema": "nova.commonplace.concordance.routes.v1",
        "status": aggregate, "query": query, "operation": "read",
        "writes_allowed": False, "routes": routes,
        "unknown_owner_states": sorted(set(supplied) - set(_OWNER_NAMES)),
    }


class Concordance:
    """Small CLI-friendly facade over the functional API."""

    def __init__(
        self, canonical_home: os.PathLike[str] | str,
        concordance_home: os.PathLike[str] | str,
    ) -> None:
        self.canonical_home, self.home = Path(canonical_home), Path(concordance_home)

    def build(
        self,
        *,
        markdown_sensitivities: Sequence[str] = DEFAULT_MARKDOWN_SENSITIVITIES,
        semantic_config: (
            SemanticIndexConfig | Mapping[str, Any] | bool | None
        ) = None,
        embedding_provider: Any | None = None,
    ) -> dict[str, Any]:
        return build_concordance(
            self.canonical_home,
            self.home,
            markdown_sensitivities=markdown_sensitivities,
            semantic_config=semantic_config,
            embedding_provider=embedding_provider,
        )

    def inspect(self) -> dict[str, Any]:
        return inspect_concordance(self.canonical_home, self.home)

    def invalidate(self) -> dict[str, Any]:
        return invalidate_concordance(self.home)

    def verify_absent(self, affected_id_hashes: Sequence[str]) -> dict[str, Any]:
        return verify_absent_id_hashes(
            self.canonical_home, self.home, affected_id_hashes
        )

    def search(
        self, query: str, *,
        allowed_sensitivities: Sequence[str] = DEFAULT_SEARCH_SENSITIVITIES,
        limit: int = 10, review_inbox: bool = False,
    ) -> list[dict[str, Any]]:
        return search_concordance(
            self.canonical_home, self.home, query,
            allowed_sensitivities=allowed_sensitivities, limit=limit,
            review_inbox=review_inbox,
        )

    def hybrid_search(
        self,
        query: str,
        *,
        mode: str = "hybrid",
        allowed_sensitivities: Sequence[str] = DEFAULT_SEARCH_SENSITIVITIES,
        limit: int = 10,
        review_inbox: bool = False,
        allow_degraded: bool = False,
        graph_hops: int = 0,
        embedding_provider: Any | None = None,
    ) -> dict[str, Any]:
        return hybrid_search_concordance(
            self.canonical_home,
            self.home,
            query,
            mode=mode,
            allowed_sensitivities=allowed_sensitivities,
            limit=limit,
            review_inbox=review_inbox,
            allow_degraded=allow_degraded,
            graph_hops=graph_hops,
            embedding_provider=embedding_provider,
        )

    def context(
        self, query: str, *,
        allowed_sensitivities: Sequence[str] = DEFAULT_SEARCH_SENSITIVITIES,
        max_chars: int = 4000, candidate_limit: int = 20,
        review_inbox: bool = False,
    ) -> dict[str, Any]:
        return build_context_packet(
            self.canonical_home, self.home, query,
            allowed_sensitivities=allowed_sensitivities,
            max_chars=max_chars, candidate_limit=candidate_limit,
            review_inbox=review_inbox,
        )


__all__ = [
    "BUILDER_ID", "INDEX_SCHEMA", "POINTER_SCHEMA", "Concordance",
    "ConcordanceError", "ContractError", "IndexUnavailableError",
    "IntegrityError", "StaleIndexError", "SemanticContractError",
    "SemanticError", "SemanticIndexConfig", "SemanticIntegrityError",
    "SemanticModelDriftError", "SemanticProviderResponseError",
    "SemanticUnavailableError", "build_concordance",
    "build_context_packet", "hybrid_search_concordance",
    "inspect_concordance", "invalidate_concordance",
    "rebuild_markdown_views", "verify_absent_id_hashes",
    "route_query", "search_concordance",
]
