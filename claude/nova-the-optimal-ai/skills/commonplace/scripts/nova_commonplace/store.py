"""Filesystem-snapshot canonical store for Nova Commonplace.

Concordance indexes are intentionally absent from this module. This store owns
only deliberate Commonplace records, governed state, and content-free receipts.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any
from uuid import uuid4

from .model import (
    apply_state_changes,
    evaluate_record_validity,
    normalize_record,
    record_provenance_dependencies,
    sanitize_references,
    validate_record_id,
)
from .runtime import (
    AlreadyInitializedError,
    AntiResurrectionError,
    ConflictError,
    FileLock,
    IntegrityError,
    NotInitializedError,
    PathPolicy,
    ValidationError,
    atomic_write,
    atomic_write_json,
    canonical_json_bytes,
    digest_object,
    normalize_authority,
    opaque_identifier,
    read_json,
    sha256_bytes,
    utc_now,
    validate_component,
    validate_timestamp,
)

SNAPSHOT_SCHEMA = "nova-commonplace.snapshot.v1"
POINTER_SCHEMA = "nova-commonplace.pointer.v1"
RECEIPT_SCHEMA = "nova-commonplace.commit-receipt.v1"
FORGET_MARKER_SCHEMA = "nova-commonplace.forget-marker.v1"
BACKUP_SCHEMA = "nova-commonplace.backup.v1"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_WORKSPACE_ID = re.compile(r"^ws-[0-9a-f]{32}$")
_SNAPSHOT_FILE = re.compile(r"^g[0-9]{20}-[0-9a-f]{64}[.]json$")
_COMMIT_RECEIPT_FILE = re.compile(
    r"^commit-g([0-9]{20})-([A-Za-z0-9][A-Za-z0-9._-]{0,127})[.]json$"
)
_RECOVER_RECEIPT_FILE = re.compile(
    r"^recover-([A-Za-z0-9][A-Za-z0-9._-]{0,127})[.]json$"
)
_FORGET_RECEIPT_FILE = re.compile(r"^forget-([0-9a-f]{64})[.]json$")
_SNAPSHOT_OPERATIONS = frozenset(
    {
        "initialize",
        "put",
        "put-promotion-proposal",
        "update-state",
        "supersede",
        "forget",
    }
)


class CommonplaceStore:
    """Governed copy-on-write store rooted at one confined directory."""

    def __init__(self, root: str | Path, *, lock_timeout: float = 10.0) -> None:
        self.paths = PathPolicy(root)
        self.root = self.paths.root
        self.current_path = self.paths.confined("CURRENT.json")
        self.snapshots_path = self.paths.confined("snapshots")
        self.receipts_path = self.paths.confined("receipts")
        self.backups_path = self.paths.confined("backups")
        self.restore_tests_path = self.paths.confined("restore-tests")
        self.lock_path = self.paths.confined(".commonplace.lock")
        self.lock_timeout = lock_timeout

    def _lock(self) -> FileLock:
        return FileLock(self.lock_path, timeout=self.lock_timeout)

    def _ensure_layout(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        for path in (self.snapshots_path, self.receipts_path, self.backups_path, self.restore_tests_path):
            path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate_generation(value: Any, *, field: str = "generation") -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValidationError(f"{field} must be a non-negative integer")
        return value

    def _snapshot_name(self, generation: int, digest: str) -> str:
        self._validate_generation(generation)
        if not _HEX64.fullmatch(digest):
            raise ValidationError("snapshot digest is invalid")
        return f"g{generation:020d}-{digest}.json"

    def _pointer(
        self, workspace_id: str, generation: int, digest: str, *, updated_at: str
    ) -> dict[str, Any]:
        if not isinstance(workspace_id, str) or not _WORKSPACE_ID.fullmatch(workspace_id):
            raise ValidationError("workspace_id is invalid")
        return {
            "schema": POINTER_SCHEMA,
            "workspace_id": workspace_id,
            "generation": generation,
            "snapshot": f"snapshots/{self._snapshot_name(generation, digest)}",
            "snapshot_sha256": digest,
            "updated_at": updated_at,
        }

    def _location_fields(self, workspace_id: str, generation: int, digest: str) -> dict[str, Any]:
        snapshot_name = self._snapshot_name(generation, digest)
        snapshot_path = self.snapshots_path / snapshot_name
        return {
            "workspace_id": workspace_id,
            "pointer_name": self.current_path.name,
            "pointer_path": str(self.current_path),
            "snapshot_name": snapshot_name,
            "snapshot_path": str(snapshot_path),
        }

    def _snapshot(
        self,
        *,
        generation: int,
        workspace_id: str,
        records: Mapping[str, Any],
        idempotency: Mapping[str, Any],
        forget_markers: list[str],
        parent_digest: str | None,
        operation: str,
        authority: Mapping[str, Any],
        created_at: str,
        history_boundary: str | None = None,
        transaction_id: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(workspace_id, str) or not _WORKSPACE_ID.fullmatch(workspace_id):
            raise ValidationError("workspace_id is invalid")
        checked_transaction_id = validate_component(
            transaction_id or uuid4().hex, field="transaction id"
        )
        result: dict[str, Any] = {
            "schema": SNAPSHOT_SCHEMA,
            "workspace_id": workspace_id,
            "generation": generation,
            "created_at": created_at,
            "parent_digest": parent_digest,
            "transaction": {
                "id": checked_transaction_id,
                "operation": operation,
                "authority_digest": digest_object(authority),
            },
            "records": {key: deepcopy(records[key]) for key in sorted(records)},
            "idempotency": {key: deepcopy(idempotency[key]) for key in sorted(idempotency)},
            "forget_markers": sorted(set(forget_markers)),
        }
        if history_boundary is not None:
            result["history_boundary"] = history_boundary
        self._validate_snapshot(result)
        return result

    def _validate_idempotency(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            raise IntegrityError("snapshot.idempotency must be an object")
        normalized: dict[str, Any] = {}
        required = {
            "operation", "payload_digest", "generation", "record_ids", "transaction_id"
        }
        for key, entry in value.items():
            if not isinstance(key, str) or not _HEX64.fullmatch(key):
                raise IntegrityError("idempotency keys must be opaque SHA-256 digests")
            if not isinstance(entry, Mapping) or set(entry) != required:
                raise IntegrityError("idempotency entry has unexpected fields")
            if not isinstance(entry.get("operation"), str) or not entry["operation"]:
                raise IntegrityError("idempotency operation is invalid")
            if not isinstance(entry.get("payload_digest"), str) or not _HEX64.fullmatch(entry["payload_digest"]):
                raise IntegrityError("idempotency payload digest is invalid")
            generation = self._validate_generation(entry.get("generation"), field="idempotency.generation")
            try:
                transaction_id = validate_component(
                    entry.get("transaction_id"), field="idempotency.transaction_id"
                )
            except ValidationError as exc:
                raise IntegrityError(str(exc)) from exc
            record_ids = entry.get("record_ids")
            if not isinstance(record_ids, list):
                raise IntegrityError("idempotency record_ids must be an array")
            checked = [validate_record_id(item, field="idempotency.record_ids") for item in record_ids]
            if len(set(checked)) != len(checked):
                raise IntegrityError("idempotency record_ids contains duplicates")
            normalized[key] = {
                "operation": entry["operation"],
                "payload_digest": entry["payload_digest"],
                "generation": generation,
                "record_ids": sorted(checked),
                "transaction_id": transaction_id,
            }
        return normalized
    def _validate_snapshot(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            raise IntegrityError("snapshot must be an object")
        required = {
            "schema", "workspace_id", "generation", "created_at", "parent_digest", "transaction",
            "records", "idempotency", "forget_markers"
        }
        if set(value) - (required | {"history_boundary"}) or required - set(value):
            raise IntegrityError("snapshot fields do not match the canonical schema")
        if value.get("schema") != SNAPSHOT_SCHEMA:
            raise IntegrityError(f"snapshot.schema must be {SNAPSHOT_SCHEMA}")
        workspace_id = value.get("workspace_id")
        if not isinstance(workspace_id, str) or not _WORKSPACE_ID.fullmatch(workspace_id):
            raise IntegrityError("snapshot.workspace_id is invalid")
        generation = self._validate_generation(value.get("generation"), field="snapshot.generation")
        created_at = validate_timestamp(value.get("created_at"), field="snapshot.created_at", optional=False)
        parent_digest = value.get("parent_digest")
        if parent_digest is not None and (not isinstance(parent_digest, str) or not _HEX64.fullmatch(parent_digest)):
            raise IntegrityError("snapshot.parent_digest is invalid")
        transaction = value.get("transaction")
        if (
            not isinstance(transaction, Mapping)
            or set(transaction) != {"id", "operation", "authority_digest"}
        ):
            raise IntegrityError("snapshot.transaction is invalid")
        try:
            transaction_id = validate_component(
                transaction.get("id"), field="snapshot.transaction.id"
            )
        except ValidationError as exc:
            raise IntegrityError(str(exc)) from exc
        if not isinstance(transaction.get("operation"), str) or not transaction["operation"]:
            raise IntegrityError("snapshot.transaction.operation is invalid")
        authority_digest = transaction.get("authority_digest")
        if not isinstance(authority_digest, str) or not _HEX64.fullmatch(authority_digest):
            raise IntegrityError("snapshot.transaction.authority_digest is invalid")
        records = value.get("records")
        if not isinstance(records, Mapping):
            raise IntegrityError("snapshot.records must be an object")
        normalized_records: dict[str, Any] = {}
        for record_id, record in records.items():
            validate_record_id(record_id, field="snapshot record key")
            try:
                checked = normalize_record(record, allow_reviewed_model_inference=True)
            except ValidationError as exc:
                raise IntegrityError(f"record {record_id} is invalid: {exc}") from exc
            if checked["id"] != record_id or checked != record:
                raise IntegrityError(f"record {record_id} is not in canonical form")
            if checked["kind"] == "promotion_proposal":
                try:
                    # Local import avoids a module cycle while making subtype
                    # validation part of every canonical snapshot read.
                    from .promotion import _proposal_metadata

                    _proposal_metadata(checked)
                except ValidationError as exc:
                    raise IntegrityError(
                        f"record {record_id} promotion subtype is invalid: {exc}"
                    ) from exc
            normalized_records[record_id] = checked

        known_ids = set(normalized_records)
        missing_references: set[str] = set()
        for record_id, record in normalized_records.items():
            missing_references.update(
                relation["target_id"]
                for relation in record["relations"]
                if relation["target_id"] not in known_ids
            )
            missing_references.update(
                target for target in record["supersedes"] if target not in known_ids
            )
            missing_references.update(
                target for target in record["superseded_by"] if target not in known_ids
            )
            missing_references.update(
                entry["source_ref"]
                for entry in record["provenance"]
                if entry["source_type"] == "record" and entry["source_ref"] not in known_ids
            )
            for target in record["supersedes"]:
                if target in normalized_records and record_id not in normalized_records[target]["superseded_by"]:
                    raise IntegrityError(
                        f"supersession link {record_id} -> {target} is not bidirectional"
                    )
            for target in record["superseded_by"]:
                if target in normalized_records and record_id not in normalized_records[target]["supersedes"]:
                    raise IntegrityError(
                        f"superseded_by link {record_id} -> {target} is not bidirectional"
                    )
        if missing_references:
            raise IntegrityError(
                "snapshot records reference absent Commonplace IDs: "
                + ", ".join(sorted(missing_references))
            )

        idempotency = self._validate_idempotency(value.get("idempotency"))
        for entry in idempotency.values():
            if entry["generation"] > generation:
                raise IntegrityError("idempotency entry generation exceeds snapshot generation")
            missing_record_ids = set(entry["record_ids"]) - known_ids
            if missing_record_ids:
                raise IntegrityError(
                    "idempotency entry references absent records: "
                    + ", ".join(sorted(missing_record_ids))
                )
        markers = value.get("forget_markers")
        if not isinstance(markers, list) or any(not isinstance(item, str) or not _HEX64.fullmatch(item) for item in markers):
            raise IntegrityError("snapshot.forget_markers must contain SHA-256 marker IDs")
        if markers != sorted(set(markers)):
            raise IntegrityError("snapshot.forget_markers must be sorted and unique")
        boundary = value.get("history_boundary")
        if boundary is not None and (not isinstance(boundary, str) or boundary not in markers):
            raise IntegrityError("snapshot.history_boundary must name an included forget marker")
        operation = transaction["operation"]
        if operation not in _SNAPSHOT_OPERATIONS:
            raise IntegrityError("snapshot.transaction.operation is not supported")
        if generation == 0:
            if (
                operation != "initialize"
                or parent_digest is not None
                or boundary is not None
                or markers
            ):
                raise IntegrityError(
                    "generation 0 must be an unmarked initialize anchor with no parent"
                )
        elif boundary is not None:
            if operation != "forget" or parent_digest is not None:
                raise IntegrityError(
                    "a nonzero history boundary must be a forget snapshot with no parent"
                )
        elif parent_digest is None or operation in {"initialize", "forget"}:
            raise IntegrityError(
                "a nonboundary nonzero snapshot must name its parent and use a normal mutation"
            )
        return {
            "schema": SNAPSHOT_SCHEMA,
            "workspace_id": workspace_id,
            "generation": generation,
            "created_at": created_at,
            "parent_digest": parent_digest,
            "transaction": {
                "id": transaction_id,
                "operation": transaction["operation"],
                "authority_digest": authority_digest,
            },
            "records": normalized_records,
            "idempotency": idempotency,
            "forget_markers": markers,
            **({"history_boundary": boundary} if boundary is not None else {}),
        }
    def _validate_pointer(self, value: Any) -> dict[str, Any]:
        fields = {"schema", "workspace_id", "generation", "snapshot", "snapshot_sha256", "updated_at"}
        if not isinstance(value, Mapping) or set(value) != fields:
            raise IntegrityError("CURRENT pointer fields do not match the canonical schema")
        if value.get("schema") != POINTER_SCHEMA:
            raise IntegrityError(f"CURRENT.schema must be {POINTER_SCHEMA}")
        workspace_id = value.get("workspace_id")
        if not isinstance(workspace_id, str) or not _WORKSPACE_ID.fullmatch(workspace_id):
            raise IntegrityError("CURRENT.workspace_id is invalid")
        generation = self._validate_generation(value.get("generation"), field="CURRENT.generation")
        digest = value.get("snapshot_sha256")
        if not isinstance(digest, str) or not _HEX64.fullmatch(digest):
            raise IntegrityError("CURRENT.snapshot_sha256 is invalid")
        expected = f"snapshots/{self._snapshot_name(generation, digest)}"
        if value.get("snapshot") != expected:
            raise IntegrityError("CURRENT snapshot path does not bind its generation and digest")
        validate_timestamp(value.get("updated_at"), field="CURRENT.updated_at", optional=False)
        return dict(value)

    def _load_marker_receipts(self) -> dict[str, dict[str, Any]]:
        if not self.receipts_path.exists():
            return {}
        result: dict[str, dict[str, Any]] = {}
        required = {
            "schema", "marker_id", "workspace_id", "created_at", "generation",
            "transaction_id", "canonical_plan_digest", "affected_id_hashes",
            "target_snapshot_digests", "target_backup_digests",
            "authority_digest", "physical_erasure_claim", "statement",
        }
        for path in sorted(self.receipts_path.glob("forget-*.json")):
            marker = read_json(path)
            if not isinstance(marker, Mapping) or set(marker) != required or marker.get("schema") != FORGET_MARKER_SCHEMA:
                raise IntegrityError(f"forget marker {path.name} has an invalid schema")
            marker_id = marker.get("marker_id")
            core = dict(marker)
            del core["marker_id"]
            if not isinstance(marker_id, str) or not _HEX64.fullmatch(marker_id):
                raise IntegrityError(f"forget marker {path.name} has an invalid ID")
            if digest_object(core) != marker_id or path.name != f"forget-{marker_id}.json":
                raise IntegrityError(f"forget marker {path.name} does not match its digest")
            workspace_id = marker.get("workspace_id")
            if not isinstance(workspace_id, str) or not _WORKSPACE_ID.fullmatch(workspace_id):
                raise IntegrityError(f"forget marker {path.name} has an invalid workspace_id")
            try:
                validate_component(
                    marker.get("transaction_id"), field="forget.transaction_id"
                )
            except ValidationError as exc:
                raise IntegrityError(str(exc)) from exc
            if (
                not isinstance(marker.get("canonical_plan_digest"), str)
                or not _HEX64.fullmatch(marker["canonical_plan_digest"])
            ):
                raise IntegrityError("forget marker canonical plan digest is invalid")
            for field in (
                "affected_id_hashes", "target_snapshot_digests", "target_backup_digests"
            ):
                values = marker.get(field)
                if not isinstance(values, list) or values != sorted(set(values)) or any(
                    not isinstance(item, str) or not _HEX64.fullmatch(item) for item in values
                ):
                    raise IntegrityError(f"forget marker {path.name} has invalid {field}")
            if marker.get("physical_erasure_claim") is not False:
                raise IntegrityError("forget marker must not claim physical erasure")
            validate_timestamp(marker.get("created_at"), field="forget.created_at", optional=False)
            self._validate_generation(marker.get("generation"), field="forget.generation")
            if not isinstance(marker.get("authority_digest"), str) or not _HEX64.fullmatch(marker["authority_digest"]):
                raise IntegrityError("forget marker authority digest is invalid")
            if not isinstance(marker.get("statement"), str) or not marker["statement"]:
                raise IntegrityError("forget marker statement is invalid")
            if marker["generation"] == 0:
                raise IntegrityError("forget marker generation must be greater than zero")
            result[marker_id] = dict(marker)
        generations = Counter(marker["generation"] for marker in result.values())
        duplicates = sorted(
            generation for generation, count in generations.items() if count > 1
        )
        if duplicates:
            raise IntegrityError(
                f"multiple forget markers claim the same generations: {duplicates}"
            )
        return result
    @staticmethod
    def _marker_hashes(markers: Mapping[str, Mapping[str, Any]]) -> set[str]:
        return {item for marker in markers.values() for item in marker.get("affected_id_hashes", [])}

    def _assert_no_resurrection(self, snapshot: Mapping[str, Any], markers: Mapping[str, Mapping[str, Any]]) -> None:
        foreign = sorted(
            marker_id
            for marker_id, marker in markers.items()
            if marker.get("workspace_id") != snapshot["workspace_id"]
        )
        if foreign:
            raise IntegrityError("forget marker receipt belongs to a different workspace")
        blocked = self._marker_hashes(markers)
        resurrected = sorted(record_id for record_id in snapshot["records"] if opaque_identifier(record_id) in blocked)
        if resurrected:
            raise AntiResurrectionError(
                "snapshot would resurrect logically forgotten record IDs: " + ", ".join(resurrected)
            )

    def _load_snapshot_path(self, path: Path) -> tuple[dict[str, Any], str]:
        self.paths.assert_confined(path)
        data = path.read_bytes()
        digest = sha256_bytes(data)
        snapshot = self._validate_snapshot(read_json(path))
        if path.name != self._snapshot_name(snapshot["generation"], digest):
            raise IntegrityError(f"snapshot filename does not bind content: {path.name}")
        return snapshot, digest

    def _load_current(
        self,
        *,
        enforce_markers: bool = True,
        audit_catalog: bool = True,
        allow_pending_purge: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        try:
            pointer = self._validate_pointer(read_json(self.current_path))
        except FileNotFoundError as exc:
            raise NotInitializedError(f"Commonplace store is not initialized at {self.root}") from exc
        path = self.paths.confined(pointer["snapshot"])
        try:
            snapshot, digest = self._load_snapshot_path(path)
        except FileNotFoundError as exc:
            raise IntegrityError("CURRENT references a missing snapshot") from exc
        if (
            digest != pointer["snapshot_sha256"]
            or snapshot["generation"] != pointer["generation"]
            or snapshot["workspace_id"] != pointer["workspace_id"]
        ):
            raise IntegrityError("CURRENT binding does not match snapshot content")
        if enforce_markers:
            markers = self._load_marker_receipts()
            self._assert_no_resurrection(snapshot, markers)
            if set(snapshot["forget_markers"]) - set(markers):
                raise IntegrityError("current snapshot references missing forget marker receipts")
            self._validate_snapshot_chain(
                snapshot, digest, markers, selected=True
            )
            if audit_catalog:
                audit = self._audit_managed_store(
                    markers=markers,
                    allow_resurrection_candidates=allow_pending_purge,
                )
                if audit["workspace_id"] != snapshot["workspace_id"]:
                    raise IntegrityError(
                        "CURRENT workspace does not match the managed snapshot catalog"
                    )
                highest = audit["highest_safe"]
                if (
                    highest["generation"] != snapshot["generation"]
                    or highest["digest"] != digest
                ):
                    raise IntegrityError(
                        "CURRENT is not the highest authenticated safe generation; "
                        "run recover before continuing"
                    )
        return pointer, snapshot, digest
    def _write_snapshot(
        self,
        snapshot: Mapping[str, Any],
        *,
        marker_receipts: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> tuple[Path, str]:
        checked = self._validate_snapshot(snapshot)
        if checked != snapshot:
            raise IntegrityError("candidate snapshot is not in canonical form")
        markers = (
            dict(marker_receipts)
            if marker_receipts is not None
            else self._load_marker_receipts()
        )
        self._assert_no_resurrection(checked, markers)
        missing_markers = set(checked["forget_markers"]) - set(markers)
        if missing_markers:
            raise IntegrityError("candidate snapshot references missing forget markers")
        data = canonical_json_bytes(checked)
        digest = sha256_bytes(data)
        path = self.snapshots_path / self._snapshot_name(checked["generation"], digest)
        self.paths.assert_confined(path)
        if path.exists():
            if path.read_bytes() != data:
                raise IntegrityError("snapshot path collision")
        else:
            atomic_write(path, data)
        return path, digest

    def _commit_receipt_path(self, generation: int, transaction_id: str) -> Path:
        checked_generation = self._validate_generation(
            generation, field="receipt.generation"
        )
        checked_transaction = validate_component(
            transaction_id, field="receipt.transaction_id"
        )
        return self.receipts_path / (
            f"commit-g{checked_generation:020d}-{checked_transaction}.json"
        )

    def _validate_receipt_document(
        self,
        value: Any,
        *,
        kind: str,
        path: Path | None = None,
    ) -> dict[str, Any]:
        required = {
            "schema", "generation", "created_at", "operation", "transaction_id",
            "authority_digest", "snapshot_sha256", "record_id_hashes",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != required
            or value.get("schema") != RECEIPT_SCHEMA
        ):
            raise IntegrityError(f"{kind} receipt schema is invalid")
        try:
            generation = self._validate_generation(
                value.get("generation"), field=f"{kind}.generation"
            )
            transaction_id = validate_component(
                value.get("transaction_id"), field=f"{kind}.transaction_id"
            )
        except ValidationError as exc:
            raise IntegrityError(str(exc)) from exc
        created_at = validate_timestamp(
            value.get("created_at"), field=f"{kind}.created_at", optional=False
        )
        operation = value.get("operation")
        if kind == "commit":
            if operation not in _SNAPSHOT_OPERATIONS:
                raise IntegrityError("commit receipt operation is invalid")
        elif kind == "recover":
            if operation != "recover":
                raise IntegrityError("recovery receipt operation must be recover")
        else:
            raise IntegrityError(f"unsupported receipt kind: {kind}")
        for field in ("authority_digest", "snapshot_sha256"):
            if (
                not isinstance(value.get(field), str)
                or not _HEX64.fullmatch(value[field])
            ):
                raise IntegrityError(f"{kind} receipt {field} is invalid")
        hashes = value.get("record_id_hashes")
        if (
            not isinstance(hashes, list)
            or hashes != sorted(set(hashes))
            or any(
                not isinstance(item, str) or not _HEX64.fullmatch(item)
                for item in hashes
            )
        ):
            raise IntegrityError(f"{kind} receipt record identifier hashes are invalid")
        if kind == "recover" and hashes:
            raise IntegrityError("recovery receipt must not retain record identifiers")
        checked = {
            "schema": RECEIPT_SCHEMA,
            "generation": generation,
            "created_at": created_at,
            "operation": operation,
            "transaction_id": transaction_id,
            "authority_digest": value["authority_digest"],
            "snapshot_sha256": value["snapshot_sha256"],
            "record_id_hashes": list(hashes),
        }
        if checked != value:
            raise IntegrityError(f"{kind} receipt is not in canonical form")
        if path is not None:
            self.paths.assert_confined(path)
            if kind == "commit":
                match = _COMMIT_RECEIPT_FILE.fullmatch(path.name)
                if (
                    match is None
                    or int(match.group(1)) != generation
                    or match.group(2) != transaction_id
                ):
                    raise IntegrityError("commit receipt filename binding is invalid")
            else:
                match = _RECOVER_RECEIPT_FILE.fullmatch(path.name)
                if match is None or match.group(1) != transaction_id:
                    raise IntegrityError("recovery receipt filename binding is invalid")
        return checked
    def _write_commit_receipt(
        self, *, snapshot: Mapping[str, Any], snapshot_digest: str, record_ids: list[str]
    ) -> dict[str, Any]:
        transaction = snapshot["transaction"]
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "generation": snapshot["generation"],
            "created_at": snapshot["created_at"],
            "operation": transaction["operation"],
            "transaction_id": transaction["id"],
            "authority_digest": transaction["authority_digest"],
            "snapshot_sha256": snapshot_digest,
            "record_id_hashes": sorted(opaque_identifier(value) for value in set(record_ids)),
        }
        path = self._commit_receipt_path(
            snapshot["generation"], transaction["id"]
        )
        if path.exists() and read_json(path) != receipt:
            raise IntegrityError("commit receipt path collision")
        atomic_write_json(path, receipt)
        return receipt

    def _load_commit_receipt(self, entry: Mapping[str, Any]) -> dict[str, Any]:
        path = self._commit_receipt_path(
            entry["generation"], entry["transaction_id"]
        )
        try:
            receipt = self._validate_receipt_document(
                read_json(path), kind="commit", path=path
            )
        except FileNotFoundError as exc:
            raise IntegrityError("required commit receipt is missing") from exc
        if (
            receipt["generation"] != entry["generation"]
            or receipt["operation"] != entry["operation"]
            or receipt["transaction_id"] != entry["transaction_id"]
        ):
            raise IntegrityError("idempotency commit receipt binding is invalid")
        expected_hashes = sorted(
            opaque_identifier(value) for value in set(entry["record_ids"])
        )
        if receipt["record_id_hashes"] != expected_hashes:
            raise IntegrityError("commit receipt record identifier hashes are invalid")
        return receipt


    def _commit_snapshot(
        self,
        snapshot: Mapping[str, Any],
        *,
        record_ids: list[str],
        forget_marker: Mapping[str, Any] | None = None,
    ) -> str:
        markers = self._load_marker_receipts()
        if forget_marker is not None:
            marker_id = forget_marker.get("marker_id")
            if not isinstance(marker_id, str) or not _HEX64.fullmatch(marker_id):
                raise IntegrityError("candidate forget marker is invalid")
            markers = {**markers, marker_id: dict(forget_marker)}
        _, digest = self._write_snapshot(snapshot, marker_receipts=markers)
        self._write_commit_receipt(
            snapshot=snapshot, snapshot_digest=digest, record_ids=record_ids
        )
        if forget_marker is not None:
            marker_path = self.receipts_path / f"forget-{forget_marker['marker_id']}.json"
            if marker_path.exists() and read_json(marker_path) != forget_marker:
                raise IntegrityError("forget marker path collision")
            atomic_write_json(marker_path, forget_marker)
        atomic_write_json(
            self.current_path,
            self._pointer(
                snapshot["workspace_id"],
                snapshot["generation"],
                digest,
                updated_at=snapshot["created_at"],
            ),
        )
        _, committed, committed_digest = self._load_current(audit_catalog=False)
        if (
            committed["generation"] != snapshot["generation"]
            or committed_digest != digest
            or committed["workspace_id"] != snapshot["workspace_id"]
        ):
            raise IntegrityError("published CURRENT did not verify against its commit")
        return digest
    @staticmethod
    def _idempotency_key_digest(key: str | None) -> str | None:
        if key is None:
            return None
        if not isinstance(key, str) or not key.strip() or len(key) > 256:
            raise ValidationError("idempotency_key must be a non-blank string up to 256 characters")
        return digest_object({"idempotency_key": key})

    @staticmethod
    def _payload_digest(operation: str, payload: Any) -> str:
        return digest_object({"operation": operation, "payload": payload})

    def _idempotency_replay(
        self,
        snapshot: Mapping[str, Any],
        *,
        key_digest: str | None,
        payload_digest: str,
        operation: str,
        snapshot_digest: str,
    ) -> dict[str, Any] | None:
        if key_digest is None:
            return None
        entry = snapshot["idempotency"].get(key_digest)
        if entry is None:
            return None
        if entry["operation"] != operation or entry["payload_digest"] != payload_digest:
            raise ConflictError("idempotency key was already used for a different request")
        receipt = self._load_commit_receipt(entry)
        original_records: list[dict[str, Any]] = []
        content_available = False
        original_path = self.snapshots_path / self._snapshot_name(
            entry["generation"], receipt["snapshot_sha256"]
        )
        try:
            original_snapshot, original_digest = self._load_snapshot_path(original_path)
            self._assert_no_resurrection(
                original_snapshot, self._load_marker_receipts()
            )
            if original_digest != receipt["snapshot_sha256"]:
                raise IntegrityError("idempotency snapshot digest mismatch")
            original_records = [
                deepcopy(original_snapshot["records"][record_id])
                for record_id in entry["record_ids"]
                if record_id in original_snapshot["records"]
            ]
            content_available = len(original_records) == len(entry["record_ids"])
        except (FileNotFoundError, IntegrityError, AntiResurrectionError):
            original_records = []
            content_available = False
        return {
            "ok": True,
            "operation": operation,
            "generation": entry["generation"],
            "committed_generation": entry["generation"],
            "current_generation": snapshot["generation"],
            "snapshot_sha256": receipt["snapshot_sha256"],
            **self._location_fields(
                snapshot["workspace_id"],
                entry["generation"],
                receipt["snapshot_sha256"],
            ),
            "replayed": True,
            "record_ids": list(entry["record_ids"]),
            "records": original_records,
            "record_content_available": content_available,
            **(
                {"record": original_records[0]}
                if len(original_records) == 1
                else {}
            ),
        }
    def _check_expected(self, snapshot: Mapping[str, Any], expected_generation: int) -> None:
        expected = self._validate_generation(expected_generation, field="expected_generation")
        if snapshot["generation"] != expected:
            raise ConflictError(f"stale generation: expected {expected}, current is {snapshot['generation']}")

    @staticmethod
    def _put_idempotency(
        table: dict[str, Any],
        *,
        key_digest: str | None,
        operation: str,
        payload_digest: str,
        generation: int,
        record_ids: list[str],
        transaction_id: str,
    ) -> None:
        if key_digest is not None:
            table[key_digest] = {
                "operation": operation,
                "payload_digest": payload_digest,
                "generation": generation,
                "record_ids": sorted(set(record_ids)),
                "transaction_id": validate_component(
                    transaction_id, field="idempotency.transaction_id"
                ),
            }

    def initialize(self, *, authority: str | Mapping[str, Any]) -> dict[str, Any]:
        normalized_authority = normalize_authority(authority)
        self._ensure_layout()
        with self._lock():
            if self.current_path.exists():
                raise AlreadyInitializedError(f"Commonplace store is already initialized at {self.root}")
            if any(self.snapshots_path.glob("*.json")):
                raise IntegrityError("snapshots exist without CURRENT; use recover instead of reinitializing")
            timestamp = utc_now()
            workspace_id = f"ws-{uuid4().hex}"
            snapshot = self._snapshot(
                generation=0,
                workspace_id=workspace_id,
                records={},
                idempotency={},
                forget_markers=[],
                parent_digest=None,
                operation="initialize",
                authority=normalized_authority,
                created_at=timestamp,
            )
            digest = self._commit_snapshot(snapshot, record_ids=[])
        return {
            "ok": True,
            "operation": "initialize",
            "generation": 0,
            "snapshot_sha256": digest,
            "replayed": False,
            "record_ids": [],
            **self._location_fields(workspace_id, 0, digest),
            "root": str(self.root),
        }

    def status(self) -> dict[str, Any]:
        if not self.current_path.exists():
            return {
                "ok": True,
                "initialized": False,
                "root": str(self.root),
                "workspace_id": None,
                "generation": None,
                "record_count": 0,
                "pointer_name": self.current_path.name,
                "pointer_path": str(self.current_path),
                "snapshot_name": None,
                "snapshot_path": None,
                "snapshot_sha256": None,
            }
        pointer, snapshot, digest = self._load_current(allow_pending_purge=True)
        kind_counts = Counter(record["kind"] for record in snapshot["records"].values())
        return {
            "ok": True,
            "initialized": True,
            "root": str(self.root),
            "generation": snapshot["generation"],
            "snapshot_sha256": digest,
            "snapshot": pointer["snapshot"],
            **self._location_fields(snapshot["workspace_id"], snapshot["generation"], digest),
            "record_count": len(snapshot["records"]),
            "kind_counts": dict(sorted(kind_counts.items())),
            "idempotency_count": len(snapshot["idempotency"]),
            "forget_marker_count": len(snapshot["forget_markers"]),
        }

    def read_current(self) -> tuple[dict[str, Any], dict[str, Any], str]:
        """Return a defensive copy of the fully validated anti-resurrection-safe binding."""
        pointer, snapshot, digest = self._load_current(allow_pending_purge=True)
        return deepcopy(pointer), deepcopy(snapshot), digest

    def records(self) -> list[dict[str, Any]]:
        _, snapshot, _ = self.read_current()
        return [deepcopy(snapshot["records"][key]) for key in sorted(snapshot["records"])]

    def get(self, record_id: str) -> dict[str, Any]:
        checked_id = validate_record_id(record_id)
        _, snapshot, _ = self._load_current(allow_pending_purge=True)
        if checked_id not in snapshot["records"]:
            raise KeyError(f"Commonplace record not found: {checked_id}")
        return deepcopy(snapshot["records"][checked_id])

    def _authenticated_history_chain(
        self,
    ) -> tuple[
        dict[str, Any],
        dict[str, Any],
        str,
        dict[str, dict[str, Any]],
        list[dict[str, Any]],
    ]:
        """Load the exact retained current chain and authenticate every member."""

        pointer, current, current_digest = self._load_current(
            allow_pending_purge=True
        )
        markers = self._load_marker_receipts()
        chain: list[dict[str, Any]] = []
        seen: set[str] = set()
        snapshot = current
        snapshot_digest = current_digest

        while True:
            if snapshot_digest in seen:
                raise IntegrityError("snapshot history contains a digest cycle")
            seen.add(snapshot_digest)
            checked = self._validate_snapshot(snapshot)
            if checked != snapshot:
                raise IntegrityError("snapshot history member is not canonical")
            self._assert_no_resurrection(checked, markers)
            receipt = self._snapshot_commit_receipt(checked, snapshot_digest)
            chain.append(
                {
                    "snapshot": checked,
                    "snapshot_sha256": snapshot_digest,
                    "receipt": receipt,
                }
            )

            if checked["generation"] == 0 or checked.get("history_boundary") is not None:
                break

            parent_digest = checked["parent_digest"]
            parent_path = self.snapshots_path / self._snapshot_name(
                checked["generation"] - 1, parent_digest
            )
            try:
                parent, observed_parent_digest = self._load_snapshot_path(parent_path)
            except FileNotFoundError as exc:
                raise IntegrityError(
                    f"snapshot generation {checked['generation']} has no authenticated parent"
                ) from exc
            if (
                observed_parent_digest != parent_digest
                or parent["generation"] != checked["generation"] - 1
                or parent["workspace_id"] != checked["workspace_id"]
                or parent["forget_markers"] != checked["forget_markers"]
            ):
                raise IntegrityError(
                    f"snapshot generation {checked['generation']} parent binding is invalid"
                )
            changed_ids = sorted(
                record_id
                for record_id in set(parent["records"]) | set(checked["records"])
                if parent["records"].get(record_id) != checked["records"].get(record_id)
            )
            expected_hashes = sorted(opaque_identifier(value) for value in changed_ids)
            if receipt["record_id_hashes"] != expected_hashes:
                raise IntegrityError(
                    f"snapshot generation {checked['generation']} commit receipt "
                    "record binding is invalid"
                )
            snapshot = parent
            snapshot_digest = observed_parent_digest

        chain.reverse()
        for earlier, later in zip(chain, chain[1:]):
            if later["snapshot"]["created_at"] < earlier["snapshot"]["created_at"]:
                raise IntegrityError(
                    "retained authenticated history has non-monotonic timestamps"
                )
        final_pointer, final_current, final_digest = self._load_current(
            allow_pending_purge=True
        )
        if (
            final_pointer != pointer
            or final_digest != current_digest
            or final_current["workspace_id"] != current["workspace_id"]
            or final_current["generation"] != current["generation"]
        ):
            raise ConflictError(
                "Commonplace store advanced during temporal read; retry"
            )
        return pointer, current, current_digest, markers, chain

    @staticmethod
    def _history_anchor(chain: list[dict[str, Any]]) -> dict[str, Any]:
        first = chain[0]["snapshot"]
        boundary = first.get("history_boundary")
        result = {
            "type": "forget" if boundary is not None else "initialize",
            "generation": first["generation"],
            "created_at": first["created_at"],
            "snapshot_sha256": chain[0]["snapshot_sha256"],
        }
        if boundary is not None:
            result["marker_id"] = boundary
        return result

    @staticmethod
    def _forget_history_status(marker: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "marker_id": marker["marker_id"],
            "generation": marker["generation"],
            "created_at": marker["created_at"],
            "physical_erasure_claim": False,
        }

    def history(self, record_id: str) -> dict[str, Any]:
        """Return content changes from the retained authenticated chain only."""

        checked_id = validate_record_id(record_id)
        pointer, current, current_digest, markers, chain = (
            self._authenticated_history_chain()
        )
        anchor = self._history_anchor(chain)
        base = {
            "ok": True,
            "operation": "history",
            "record_id": checked_id,
            "workspace_id": current["workspace_id"],
            "current_generation": current["generation"],
            "current_snapshot_sha256": current_digest,
            "pointer_name": self.current_path.name,
            "pointer_path": str(self.current_path),
            "history_anchor": anchor,
            "history_complete": anchor["type"] == "initialize",
            "authenticated_generation_count": len(chain),
        }
        forgotten = self._find_forget_marker(
            markers, record_hash=opaque_identifier(checked_id)
        )
        if forgotten is not None:
            return {
                **base,
                "status": "forgotten",
                "record_content_available": False,
                "entries": [],
                "forget": self._forget_history_status(forgotten),
            }

        entries: list[dict[str, Any]] = []
        previous: dict[str, Any] | None = None
        appeared = False
        for index, item in enumerate(chain):
            snapshot = item["snapshot"]
            record = snapshot["records"].get(checked_id)
            if record is None:
                if appeared:
                    raise IntegrityError(
                        "authenticated history contains an ordinary record removal"
                    )
                continue
            if not appeared:
                change = (
                    "retained_at_forget_boundary"
                    if index == 0 and snapshot.get("history_boundary") is not None
                    else "introduced"
                )
            elif record == previous:
                continue
            else:
                change = "revised"
            entries.append(
                {
                    "generation": snapshot["generation"],
                    "created_at": snapshot["created_at"],
                    "snapshot_sha256": item["snapshot_sha256"],
                    "operation": snapshot["transaction"]["operation"],
                    "change": change,
                    "record": deepcopy(record),
                    "validity_at_snapshot": evaluate_record_validity(
                        record, at=snapshot["created_at"]
                    ),
                }
            )
            previous = record
            appeared = True

        status = "present" if checked_id in current["records"] else "absent"
        if status == "absent" and entries:
            raise IntegrityError(
                "authenticated history is incompatible with current identity state"
            )
        return {
            **base,
            "status": status,
            "record_content_available": status == "present",
            "entries": entries,
        }

    @staticmethod
    def _normalize_as_of_selector(
        *,
        generation: int | None,
        timestamp: str | None,
    ) -> dict[str, Any]:
        if (generation is None) == (timestamp is None):
            raise ValidationError(
                "get_as_of requires exactly one of generation or timestamp"
            )
        if generation is not None:
            checked_generation = CommonplaceStore._validate_generation(
                generation, field="as_of.generation"
            )
            return {"kind": "generation", "value": checked_generation}
        checked_timestamp = validate_timestamp(
            timestamp, field="as_of.timestamp", optional=False
        )
        return {"kind": "timestamp", "value": checked_timestamp}

    def get_as_of(
        self,
        record_id: str,
        *,
        generation: int | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        """Read one record at a retained authenticated generation or timestamp."""

        checked_id = validate_record_id(record_id)
        selector = self._normalize_as_of_selector(
            generation=generation, timestamp=timestamp
        )
        pointer, current, current_digest, markers, chain = (
            self._authenticated_history_chain()
        )
        anchor = self._history_anchor(chain)
        base = {
            "ok": True,
            "operation": "get-as-of",
            "record_id": checked_id,
            "selector": selector,
            "workspace_id": current["workspace_id"],
            "current_generation": current["generation"],
            "current_snapshot_sha256": current_digest,
            "pointer_name": self.current_path.name,
            "pointer_path": str(self.current_path),
            "history_anchor": anchor,
            "history_complete": anchor["type"] == "initialize",
        }

        if (
            selector["kind"] == "generation"
            and selector["value"] > current["generation"]
        ):
            raise ValidationError(
                "as_of.generation must not exceed the current generation"
            )

        forgotten = self._find_forget_marker(
            markers, record_hash=opaque_identifier(checked_id)
        )
        if forgotten is not None:
            return {
                **base,
                "status": "forgotten",
                "record_content_available": False,
                "forget": self._forget_history_status(forgotten),
            }

        selected: dict[str, Any] | None = None
        if selector["kind"] == "generation":
            if selector["value"] < anchor["generation"]:
                return {
                    **base,
                    "status": "history_unavailable",
                    "record_content_available": False,
                    "reason": "selector_precedes_retained_history",
                }
            selected = next(
                (
                    item
                    for item in chain
                    if item["snapshot"]["generation"] == selector["value"]
                ),
                None,
            )
            if selected is None:
                raise IntegrityError(
                    "retained authenticated history has a generation gap"
                )
        else:
            eligible = [
                item
                for item in chain
                if item["snapshot"]["created_at"] <= selector["value"]
            ]
            if not eligible:
                return {
                    **base,
                    "status": "history_unavailable",
                    "record_content_available": False,
                    "reason": (
                        "selector_precedes_retained_history"
                        if anchor["type"] == "forget"
                        else "selector_precedes_workspace_initialization"
                    ),
                }
            selected = max(
                eligible,
                key=lambda item: item["snapshot"]["generation"],
            )

        snapshot = selected["snapshot"]
        record = snapshot["records"].get(checked_id)
        selected_fields = {
            "selected_generation": snapshot["generation"],
            "selected_created_at": snapshot["created_at"],
            "selected_snapshot_sha256": selected["snapshot_sha256"],
        }
        if record is not None:
            evaluation_time = (
                selector["value"]
                if selector["kind"] == "timestamp"
                else snapshot["created_at"]
            )
            return {
                **base,
                **selected_fields,
                "status": "found",
                "record_content_available": True,
                "record": deepcopy(record),
                "validity": evaluate_record_validity(
                    record, at=evaluation_time
                ),
            }

        status = (
            "not_yet_created"
            if checked_id in current["records"]
            else "absent"
        )
        return {
            **base,
            **selected_fields,
            "status": status,
            "record_content_available": False,
        }

    def _put_record(
        self,
        record: Mapping[str, Any],
        *,
        authority: str | Mapping[str, Any],
        expected_generation: int,
        idempotency_key: str | None,
        operation: str,
        proposal_only: bool,
    ) -> dict[str, Any]:
        if not isinstance(record, Mapping):
            raise ValidationError("record must be an object")
        raw = deepcopy(dict(record))
        raw_kind = raw.get("kind")
        if proposal_only:
            if raw_kind != "promotion_proposal":
                raise ValidationError(
                    "the dedicated proposal insertion path accepts only "
                    "kind=promotion_proposal"
                )
        elif raw_kind == "promotion_proposal":
            raise ValidationError(
                "generic put cannot create promotion_proposal; "
                "use create_promotion_proposal"
            )
        payload_digest = self._payload_digest(operation, raw)
        key_digest = self._idempotency_key_digest(idempotency_key)
        normalized_authority = normalize_authority(authority)
        with self._lock():
            _, snapshot, parent_digest = self._load_current()
            replay = self._idempotency_replay(
                snapshot,
                key_digest=key_digest,
                payload_digest=payload_digest,
                operation=operation,
                snapshot_digest=parent_digest,
            )
            if replay is not None:
                return replay
            self._check_expected(snapshot, expected_generation)
            candidate = deepcopy(raw)
            candidate.setdefault("id", f"cp-{uuid4().hex}")
            normalized = normalize_record(candidate)
            if normalized["revision"] != 1:
                raise ValidationError("new Commonplace records must begin at revision 1")
            if proposal_only:
                from .promotion import _validate_proposal_insertion

                _validate_proposal_insertion(normalized, snapshot, parent_digest)
            record_id = normalized["id"]
            if record_id in snapshot["records"]:
                raise ConflictError(f"record already exists: {record_id}")
            records = deepcopy(snapshot["records"])
            records[record_id] = normalized
            idempotency = deepcopy(snapshot["idempotency"])
            generation = snapshot["generation"] + 1
            transaction_id = uuid4().hex
            self._put_idempotency(
                idempotency,
                key_digest=key_digest,
                operation=operation,
                payload_digest=payload_digest,
                generation=generation,
                record_ids=[record_id],
                transaction_id=transaction_id,
            )
            timestamp = utc_now()
            next_snapshot = self._snapshot(
                generation=generation,
                workspace_id=snapshot["workspace_id"],
                records=records,
                idempotency=idempotency,
                forget_markers=snapshot["forget_markers"],
                parent_digest=parent_digest,
                operation=operation,
                authority=normalized_authority,
                created_at=timestamp,
                transaction_id=transaction_id,
            )
            digest = self._commit_snapshot(next_snapshot, record_ids=[record_id])
        return {
            "ok": True,
            "operation": operation,
            "generation": generation,
            "snapshot_sha256": digest,
            **self._location_fields(snapshot["workspace_id"], generation, digest),
            "replayed": False,
            "record_ids": [record_id],
            "record": deepcopy(normalized),
            "records": [deepcopy(normalized)],
        }

    def put(
        self,
        record: Mapping[str, Any],
        *,
        authority: str | Mapping[str, Any],
        expected_generation: int,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Insert an ordinary Commonplace record.

        Promotion proposals are a governed subtype and are rejected here even
        when their generic record shape is otherwise valid.
        """

        return self._put_record(
            record,
            authority=authority,
            expected_generation=expected_generation,
            idempotency_key=idempotency_key,
            operation="put",
            proposal_only=False,
        )

    def _put_promotion_proposal(
        self,
        record: Mapping[str, Any],
        *,
        authority: str | Mapping[str, Any],
        expected_generation: int,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        """Store-owned insertion path used by the promotion domain module only."""

        return self._put_record(
            record,
            authority=authority,
            expected_generation=expected_generation,
            idempotency_key=idempotency_key,
            operation="put-promotion-proposal",
            proposal_only=True,
        )

    def update_state(
        self,
        record_id: str,
        changes: Mapping[str, Any],
        *,
        authority: str | Mapping[str, Any],
        expected_generation: int,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        checked_id = validate_record_id(record_id)
        raw_changes = deepcopy(dict(changes)) if isinstance(changes, Mapping) else changes
        payload_digest = self._payload_digest("update-state", {"record_id": checked_id, "changes": raw_changes})
        key_digest = self._idempotency_key_digest(idempotency_key)
        normalized_authority = normalize_authority(authority)
        with self._lock():
            _, snapshot, parent_digest = self._load_current()
            replay = self._idempotency_replay(
                snapshot, key_digest=key_digest, payload_digest=payload_digest,
                operation="update-state", snapshot_digest=parent_digest
            )
            if replay is not None:
                return replay
            self._check_expected(snapshot, expected_generation)
            if checked_id not in snapshot["records"]:
                raise KeyError(f"Commonplace record not found: {checked_id}")
            existing = snapshot["records"][checked_id]
            normalized = apply_state_changes(existing, raw_changes)
            if existing["kind"] == "promotion_proposal":
                from .promotion import _proposal_metadata

                # Revalidate the subtype before constructing a snapshot. This
                # permits admission/retraction and sensitivity raises, while
                # blocking floor downgrades or contract drift.
                _proposal_metadata(normalized)
            records = deepcopy(snapshot["records"])
            records[checked_id] = normalized
            idempotency = deepcopy(snapshot["idempotency"])
            generation = snapshot["generation"] + 1
            transaction_id = uuid4().hex
            self._put_idempotency(
                idempotency, key_digest=key_digest, operation="update-state",
                payload_digest=payload_digest, generation=generation, record_ids=[checked_id],
                transaction_id=transaction_id,
            )
            timestamp = utc_now()
            next_snapshot = self._snapshot(
                generation=generation, workspace_id=snapshot["workspace_id"], records=records, idempotency=idempotency,
                forget_markers=snapshot["forget_markers"], parent_digest=parent_digest,
                operation="update-state", authority=normalized_authority, created_at=timestamp,
                transaction_id=transaction_id,
            )
            digest = self._commit_snapshot(next_snapshot, record_ids=[checked_id])
        return {
            "ok": True, "operation": "update-state", "generation": generation,
            "snapshot_sha256": digest,
            **self._location_fields(snapshot["workspace_id"], generation, digest),
            "replayed": False, "record_ids": [checked_id],
            "record": deepcopy(normalized), "records": [deepcopy(normalized)]
        }
    def supersede(
        self,
        record_id: str,
        replacement: Mapping[str, Any],
        *,
        authority: str | Mapping[str, Any],
        expected_generation: int,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        checked_id = validate_record_id(record_id)
        if not isinstance(replacement, Mapping):
            raise ValidationError("replacement must be an object")
        raw = deepcopy(dict(replacement))
        if raw.get("kind") == "promotion_proposal":
            raise ValidationError(
                "generic supersede cannot create promotion_proposal; "
                "use create_promotion_proposal"
            )
        payload_digest = self._payload_digest("supersede", {"record_id": checked_id, "replacement": raw})
        key_digest = self._idempotency_key_digest(idempotency_key)
        normalized_authority = normalize_authority(authority)
        with self._lock():
            _, snapshot, parent_digest = self._load_current()
            replay = self._idempotency_replay(
                snapshot, key_digest=key_digest, payload_digest=payload_digest,
                operation="supersede", snapshot_digest=parent_digest
            )
            if replay is not None:
                return replay
            self._check_expected(snapshot, expected_generation)
            if checked_id not in snapshot["records"]:
                raise KeyError(f"Commonplace record not found: {checked_id}")
            if snapshot["records"][checked_id]["kind"] == "promotion_proposal":
                raise ValidationError(
                    "promotion proposals cannot be superseded through the generic path; "
                    "use governed state transitions"
                )
            if snapshot["records"][checked_id]["lifecycle"] != "current":
                raise ConflictError("only a current record can be superseded")
            candidate = deepcopy(raw)
            candidate.setdefault("id", f"cp-{uuid4().hex}")
            replacement_id = validate_record_id(candidate["id"])
            if replacement_id in snapshot["records"] or replacement_id == checked_id:
                raise ConflictError(f"replacement record already exists: {replacement_id}")
            listed = candidate.get("supersedes", [])
            if not isinstance(listed, list):
                raise ValidationError("replacement.supersedes must be an array")
            candidate["supersedes"] = sorted(set(listed) | {checked_id})
            candidate["lifecycle"] = "current"
            normalized_replacement = normalize_record(candidate)
            if normalized_replacement["revision"] != 1:
                raise ValidationError("replacement records must begin at revision 1")
            old = deepcopy(snapshot["records"][checked_id])
            old["lifecycle"] = "superseded"
            old["superseded_by"] = sorted(set(old["superseded_by"]) | {replacement_id})
            old["revision"] += 1
            old["updated_at"] = utc_now()
            normalized_old = normalize_record(old, now=old["updated_at"], allow_reviewed_model_inference=True)
            records = deepcopy(snapshot["records"])
            records[checked_id] = normalized_old
            records[replacement_id] = normalized_replacement
            idempotency = deepcopy(snapshot["idempotency"])
            generation = snapshot["generation"] + 1
            transaction_id = uuid4().hex
            self._put_idempotency(
                idempotency, key_digest=key_digest, operation="supersede",
                payload_digest=payload_digest, generation=generation,
                record_ids=[checked_id, replacement_id],
                transaction_id=transaction_id,
            )
            timestamp = utc_now()
            next_snapshot = self._snapshot(
                generation=generation, workspace_id=snapshot["workspace_id"], records=records, idempotency=idempotency,
                forget_markers=snapshot["forget_markers"], parent_digest=parent_digest,
                operation="supersede", authority=normalized_authority, created_at=timestamp,
                transaction_id=transaction_id,
            )
            digest = self._commit_snapshot(next_snapshot, record_ids=[checked_id, replacement_id])
        return {
            "ok": True, "operation": "supersede", "generation": generation,
            "snapshot_sha256": digest,
            **self._location_fields(snapshot["workspace_id"], generation, digest),
            "replayed": False,
            "record_ids": [checked_id, replacement_id],
            "records": [deepcopy(normalized_old), deepcopy(normalized_replacement)],
            "record": deepcopy(normalized_replacement)
        }

    @staticmethod
    def _is_link_edge(path: Path) -> bool:
        return bool(path.is_symlink() or getattr(path, "is_junction", lambda: False)())

    def _snapshot_commit_receipt(
        self,
        snapshot: Mapping[str, Any],
        snapshot_digest: str,
    ) -> dict[str, Any]:
        path = self._commit_receipt_path(
            snapshot["generation"], snapshot["transaction"]["id"]
        )
        try:
            receipt = self._validate_receipt_document(
                read_json(path), kind="commit", path=path
            )
        except FileNotFoundError as exc:
            raise IntegrityError(
                f"snapshot generation {snapshot['generation']} has no commit receipt"
            ) from exc
        expected = {
            "generation": snapshot["generation"],
            "created_at": snapshot["created_at"],
            "operation": snapshot["transaction"]["operation"],
            "transaction_id": snapshot["transaction"]["id"],
            "authority_digest": snapshot["transaction"]["authority_digest"],
            "snapshot_sha256": snapshot_digest,
        }
        observed = {key: receipt[key] for key in expected}
        if observed != expected:
            raise IntegrityError(
                f"snapshot generation {snapshot['generation']} commit receipt binding is invalid"
            )
        if snapshot["transaction"]["operation"] in {"initialize", "forget"} and receipt[
            "record_id_hashes"
        ]:
            raise IntegrityError(
                "initialize and forget commit receipts must not retain record identifiers"
            )
        return receipt

    def _validate_snapshot_chain(
        self,
        snapshot: Mapping[str, Any],
        snapshot_digest: str,
        markers: Mapping[str, Mapping[str, Any]],
        *,
        selected: bool,
        visited: set[str] | None = None,
    ) -> dict[str, Any]:
        """Authenticate one exact parent chain back to initialize or a forget boundary."""

        checked = self._validate_snapshot(snapshot)
        if checked != snapshot:
            raise IntegrityError("snapshot chain member is not canonical")
        expected_markers = sorted(
            marker_id
            for marker_id, marker in markers.items()
            if marker["workspace_id"] == checked["workspace_id"]
            and marker["generation"] <= checked["generation"]
        )
        foreign_markers = sorted(
            marker_id
            for marker_id, marker in markers.items()
            if marker["workspace_id"] != checked["workspace_id"]
        )
        if foreign_markers:
            raise IntegrityError("forget marker receipt belongs to a different workspace")
        if checked["forget_markers"] != expected_markers:
            raise IntegrityError(
                f"snapshot generation {checked['generation']} marker set is not exact"
            )
        if selected and set(checked["forget_markers"]) != set(markers):
            raise IntegrityError("CURRENT snapshot does not include every forget marker")
        receipt = self._snapshot_commit_receipt(checked, snapshot_digest)

        seen = set() if visited is None else visited
        if snapshot_digest in seen:
            raise IntegrityError("snapshot parent chain contains a digest cycle")
        seen.add(snapshot_digest)

        generation = checked["generation"]
        if generation == 0:
            return {"anchor": "initialize", "depth": 1}

        boundary = checked.get("history_boundary")
        if boundary is not None:
            marker = markers.get(boundary)
            if marker is None:
                raise IntegrityError("history boundary marker receipt is missing")
            binding = {
                "workspace_id": checked["workspace_id"],
                "generation": generation,
                "created_at": checked["created_at"],
                "transaction_id": checked["transaction"]["id"],
                "authority_digest": checked["transaction"]["authority_digest"],
            }
            if {key: marker.get(key) for key in binding} != binding:
                raise IntegrityError("history boundary does not match its forget marker")
            if receipt["operation"] != "forget" or receipt["record_id_hashes"]:
                raise IntegrityError("history boundary commit receipt is invalid")
            return {"anchor": "forget", "marker_id": boundary, "depth": 1}

        parent_digest = checked["parent_digest"]
        parent_path = self.snapshots_path / self._snapshot_name(
            generation - 1, parent_digest
        )
        try:
            parent, observed_parent_digest = self._load_snapshot_path(parent_path)
        except FileNotFoundError as exc:
            raise IntegrityError(
                f"snapshot generation {generation} has no authenticated parent"
            ) from exc
        if (
            observed_parent_digest != parent_digest
            or parent["generation"] != generation - 1
            or parent["workspace_id"] != checked["workspace_id"]
        ):
            raise IntegrityError(
                f"snapshot generation {generation} parent binding is invalid"
            )
        if parent["forget_markers"] != checked["forget_markers"]:
            raise IntegrityError(
                "ordinary snapshot parent and child must carry the same marker set"
            )
        parent_result = self._validate_snapshot_chain(
            parent,
            observed_parent_digest,
            markers,
            selected=False,
            visited=seen,
        )
        return {
            "anchor": parent_result["anchor"],
            "depth": int(parent_result["depth"]) + 1,
            **(
                {"marker_id": parent_result["marker_id"]}
                if "marker_id" in parent_result
                else {}
            ),
        }

    def _audit_root_layout(self) -> dict[str, Any]:
        self.paths.assert_confined(self.root)
        if self._is_link_edge(self.root) or not self.root.is_dir():
            raise IntegrityError("Commonplace root is not a safe direct directory")
        allowed = {
            "CURRENT.json",
            "snapshots",
            "receipts",
            "backups",
            "restore-tests",
            ".commonplace.lock",
        }
        entries = {path.name: path for path in self.root.iterdir()}
        unexpected = sorted(set(entries) - allowed)
        if unexpected:
            raise IntegrityError(
                f"Commonplace root contains unmanaged entries: {unexpected}"
            )
        for path in (
            self.snapshots_path,
            self.receipts_path,
            self.backups_path,
            self.restore_tests_path,
        ):
            if (
                not path.exists()
                or self._is_link_edge(path)
                or not path.is_dir()
            ):
                raise IntegrityError(
                    f"managed root {path.name!r} is not a safe direct directory"
                )
        if self.current_path.exists() and (
            self._is_link_edge(self.current_path) or not self.current_path.is_file()
        ):
            raise IntegrityError("CURRENT.json is not a safe direct file")
        if self.lock_path.exists() and (
            self._is_link_edge(self.lock_path) or not self.lock_path.is_file()
        ):
            raise IntegrityError(".commonplace.lock is not a safe direct file")
        restore_entries = list(self.restore_tests_path.iterdir())
        if restore_entries:
            raise IntegrityError(
                "restore-tests contains residue from an incomplete restore rehearsal"
            )
        return {
            "root_entries": len(entries),
            "lock_present": self.lock_path.exists(),
            "restore_tests_empty": True,
        }

    def _load_receipt_inventory(
        self,
        markers: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, Any]:
        commit: dict[str, dict[str, Any]] = {}
        recover: dict[str, dict[str, Any]] = {}
        observed_markers: set[str] = set()
        for path in sorted(self.receipts_path.iterdir(), key=lambda item: item.name):
            self.paths.assert_confined(path)
            if self._is_link_edge(path) or not path.is_file():
                raise IntegrityError("receipts contains an unsafe or non-file entry")
            forget_match = _FORGET_RECEIPT_FILE.fullmatch(path.name)
            commit_match = _COMMIT_RECEIPT_FILE.fullmatch(path.name)
            recover_match = _RECOVER_RECEIPT_FILE.fullmatch(path.name)
            if forget_match is not None:
                marker_id = forget_match.group(1)
                if marker_id not in markers:
                    raise IntegrityError(
                        f"forget receipt {path.name} was not validated"
                    )
                observed_markers.add(marker_id)
            elif commit_match is not None:
                receipt = self._validate_receipt_document(
                    read_json(path), kind="commit", path=path
                )
                commit[path.name] = receipt
            elif recover_match is not None:
                receipt = self._validate_receipt_document(
                    read_json(path), kind="recover", path=path
                )
                recover[path.name] = receipt
            else:
                raise IntegrityError(
                    f"receipts contains an unmanaged entry: {path.name}"
                )
        if observed_markers != set(markers):
            raise IntegrityError("forget receipt inventory is incomplete")
        return {
            "commit": commit,
            "recover": recover,
            "forget_count": len(observed_markers),
        }

    def _audit_managed_store(
        self,
        *,
        markers: Mapping[str, Mapping[str, Any]],
        allow_resurrection_candidates: bool,
    ) -> dict[str, Any]:
        """Exhaustively validate every managed canonical artifact."""

        root_audit = self._audit_root_layout()
        receipt_inventory = self._load_receipt_inventory(markers)
        snapshots: list[dict[str, Any]] = []
        generations: dict[int, str] = {}
        workspace_ids: set[str] = set()
        for path in sorted(self.snapshots_path.iterdir(), key=lambda item: item.name):
            self.paths.assert_confined(path)
            if (
                self._is_link_edge(path)
                or not path.is_file()
                or not _SNAPSHOT_FILE.fullmatch(path.name)
            ):
                raise IntegrityError(
                    "snapshot custody contains an unexpected or unsafe entry"
                )
            snapshot, digest = self._load_snapshot_path(path)
            generation = snapshot["generation"]
            if generation in generations and generations[generation] != digest:
                raise IntegrityError(
                    f"multiple snapshot branches claim generation {generation}"
                )
            generations[generation] = digest
            workspace_ids.add(snapshot["workspace_id"])
            snapshots.append(
                {
                    "path": path,
                    "digest": digest,
                    "generation": generation,
                    "snapshot": snapshot,
                }
            )
        if not snapshots:
            raise IntegrityError("managed snapshot catalog is empty")
        if len(workspace_ids) != 1:
            raise IntegrityError("managed snapshots span multiple workspaces")
        workspace_id = next(iter(workspace_ids))
        if any(marker["workspace_id"] != workspace_id for marker in markers.values()):
            raise IntegrityError("forget marker receipt belongs to a different workspace")

        safe: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        for item in snapshots:
            self._validate_snapshot_chain(
                item["snapshot"],
                item["digest"],
                markers,
                selected=False,
            )
            try:
                self._assert_no_resurrection(item["snapshot"], markers)
            except AntiResurrectionError:
                if not allow_resurrection_candidates:
                    raise
                blocked.append(item)
            else:
                safe.append(item)
        if not safe:
            raise IntegrityError("no authenticated anti-resurrection-safe snapshot exists")
        highest_safe = max(safe, key=lambda item: (item["generation"], item["digest"]))

        present_digests = {item["digest"] for item in snapshots}
        target_markers: dict[str, list[Mapping[str, Any]]] = {}
        for marker in markers.values():
            for digest in marker["target_snapshot_digests"]:
                target_markers.setdefault(digest, []).append(marker)

        def receipt_is_governed(receipt: Mapping[str, Any]) -> bool:
            digest = receipt["snapshot_sha256"]
            if digest in present_digests:
                return True
            return any(
                marker["generation"] > receipt["generation"]
                for marker in target_markers.get(digest, [])
            )

        ungoverned_blocked = [
            item["digest"]
            for item in blocked
            if item["digest"] not in target_markers
        ]
        if ungoverned_blocked:
            raise AntiResurrectionError(
                "anti-resurrection candidates are not named by a forget plan: "
                + ", ".join(sorted(ungoverned_blocked))
            )

        present_by_digest = {
            item["digest"]: item["snapshot"] for item in snapshots
        }
        for path_name, receipt in receipt_inventory["commit"].items():
            present = present_by_digest.get(receipt["snapshot_sha256"])
            if present is not None:
                expected_path = self._commit_receipt_path(
                    present["generation"], present["transaction"]["id"]
                )
                expected_binding = {
                    "generation": present["generation"],
                    "created_at": present["created_at"],
                    "operation": present["transaction"]["operation"],
                    "transaction_id": present["transaction"]["id"],
                    "authority_digest": present["transaction"]["authority_digest"],
                    "snapshot_sha256": receipt["snapshot_sha256"],
                }
                if (
                    path_name != expected_path.name
                    or {key: receipt.get(key) for key in expected_binding}
                    != expected_binding
                ):
                    raise IntegrityError(
                        f"commit receipt {path_name} does not belong to its snapshot"
                    )
            elif not receipt_is_governed(receipt):
                raise IntegrityError(
                    f"receipt {path_name} points to an unmanaged snapshot digest"
                )
        for path_name, receipt in receipt_inventory["recover"].items():
            present = present_by_digest.get(receipt["snapshot_sha256"])
            if present is not None:
                if receipt["generation"] != present["generation"]:
                    raise IntegrityError(
                        f"recovery receipt {path_name} generation does not bind its snapshot"
                    )
            elif not receipt_is_governed(receipt):
                raise IntegrityError(
                    f"receipt {path_name} points to an unmanaged snapshot digest"
                )

        for marker_id, marker in markers.items():
            receipt_path = self._commit_receipt_path(
                marker["generation"], marker["transaction_id"]
            )
            receipt = receipt_inventory["commit"].get(receipt_path.name)
            if receipt is None:
                raise IntegrityError(
                    f"forget marker {marker_id} has no exact commit receipt"
                )
            expected = {
                "generation": marker["generation"],
                "created_at": marker["created_at"],
                "operation": "forget",
                "transaction_id": marker["transaction_id"],
                "authority_digest": marker["authority_digest"],
            }
            if (
                {key: receipt.get(key) for key in expected} != expected
                or receipt["record_id_hashes"]
            ):
                raise IntegrityError(
                    f"forget marker {marker_id} commit receipt binding is invalid"
                )
            if receipt["snapshot_sha256"] not in present_digests and not any(
                later["generation"] > marker["generation"]
                for later in target_markers.get(receipt["snapshot_sha256"], [])
            ):
                raise IntegrityError(
                    f"forget marker {marker_id} boundary snapshot is ungoverned"
                )

        backups: list[dict[str, Any]] = []
        for path in sorted(self.backups_path.iterdir(), key=lambda item: item.name):
            backup = self._load_backup_artifact(
                path,
                workspace_id=workspace_id,
                markers=markers,
                enforce_resurrection=not allow_resurrection_candidates,
            )
            if backup["snapshot_digest"] not in present_digests:
                raise IntegrityError(
                    f"backup {backup['name']} is detached from the managed snapshot catalog"
                )
            backups.append(backup)

        return {
            "workspace_id": workspace_id,
            "root": root_audit,
            "snapshots": snapshots,
            "safe": safe,
            "blocked": blocked,
            "highest_safe": highest_safe,
            "backups": backups,
            "commit_receipts_checked": len(receipt_inventory["commit"]),
            "recovery_receipts_checked": len(receipt_inventory["recover"]),
            "forget_markers_checked": receipt_inventory["forget_count"],
        }
    def _load_backup_artifact(
        self,
        path: Path,
        *,
        workspace_id: str,
        markers: Mapping[str, Mapping[str, Any]],
        enforce_resurrection: bool,
    ) -> dict[str, Any]:
        self.paths.assert_confined(path)
        if self._is_link_edge(path) or not path.is_dir():
            raise IntegrityError("managed backup entry is not a safe direct directory")
        try:
            checked_name = validate_component(path.name, field="backup name")
        except ValidationError as exc:
            raise IntegrityError(str(exc)) from exc
        entries = list(path.iterdir())
        if any(self._is_link_edge(item) for item in entries):
            raise IntegrityError("managed backup contains a link or reparse edge")
        if {item.name for item in entries} != {"manifest.json", "snapshot.json"}:
            raise IntegrityError("managed backup file set is not exact")
        if any(not item.is_file() for item in entries):
            raise IntegrityError("managed backup contains a non-regular file")

        manifest_path = path / "manifest.json"
        snapshot_path = path / "snapshot.json"
        manifest_bytes = manifest_path.read_bytes()
        manifest = read_json(manifest_path)
        required = {
            "schema", "name", "created_at", "workspace_id", "snapshot_generation",
            "snapshot_sha256", "source_pointer_sha256", "authority_digest",
            "record_id_hashes",
        }
        if (
            not isinstance(manifest, Mapping)
            or set(manifest) != required
            or manifest.get("schema") != BACKUP_SCHEMA
            or manifest.get("name") != checked_name
        ):
            raise IntegrityError("managed backup manifest schema or name is invalid")
        validate_timestamp(
            manifest.get("created_at"), field="backup.created_at", optional=False
        )
        if manifest.get("workspace_id") != workspace_id:
            raise IntegrityError("managed backup belongs to a different workspace")
        generation = self._validate_generation(
            manifest.get("snapshot_generation"),
            field="backup.snapshot_generation",
        )
        for field in (
            "snapshot_sha256", "source_pointer_sha256", "authority_digest"
        ):
            if (
                not isinstance(manifest.get(field), str)
                or not _HEX64.fullmatch(manifest[field])
            ):
                raise IntegrityError(f"managed backup {field} is invalid")
        snapshot_bytes = snapshot_path.read_bytes()
        snapshot_digest = sha256_bytes(snapshot_bytes)
        if snapshot_digest != manifest["snapshot_sha256"]:
            raise IntegrityError("managed backup snapshot digest does not match manifest")
        snapshot = self._validate_snapshot(read_json(snapshot_path))
        if (
            snapshot["workspace_id"] != workspace_id
            or snapshot["generation"] != generation
        ):
            raise IntegrityError("managed backup snapshot binding is invalid")
        expected_hashes = sorted(
            opaque_identifier(value) for value in snapshot["records"]
        )
        if manifest.get("record_id_hashes") != expected_hashes:
            raise IntegrityError("managed backup record identifier hashes are invalid")
        if set(snapshot["forget_markers"]) - set(markers):
            raise IntegrityError("managed backup references missing forget markers")
        if enforce_resurrection:
            self._assert_no_resurrection(snapshot, markers)
        return {
            "kind": "backup",
            "path": path,
            "name": checked_name,
            "digest": sha256_bytes(manifest_bytes),
            "snapshot_digest": snapshot_digest,
            "record_ids": sorted(snapshot["records"]),
            "record_id_hashes": expected_hashes,
        }

    def _inventory_managed_artifacts(
        self,
        *,
        workspace_id: str,
        markers: Mapping[str, Mapping[str, Any]],
        enforce_resurrection: bool = True,
    ) -> dict[str, list[dict[str, Any]]]:
        snapshots: list[dict[str, Any]] = []
        backups: list[dict[str, Any]] = []
        for root, label in (
            (self.snapshots_path, "snapshot"),
            (self.backups_path, "backup"),
        ):
            self.paths.assert_confined(root)
            if self._is_link_edge(root) or not root.is_dir():
                raise IntegrityError(f"managed {label} root is not a safe directory")
        for path in sorted(self.snapshots_path.iterdir(), key=lambda item: item.name):
            self.paths.assert_confined(path)
            if (
                self._is_link_edge(path)
                or not path.is_file()
                or not _SNAPSHOT_FILE.fullmatch(path.name)
            ):
                raise IntegrityError("snapshot custody contains an unexpected or unsafe entry")
            snapshot, digest = self._load_snapshot_path(path)
            if snapshot["workspace_id"] != workspace_id:
                raise IntegrityError("managed snapshot belongs to a different workspace")
            if set(snapshot["forget_markers"]) - set(markers):
                raise IntegrityError("managed snapshot references missing forget markers")
            if enforce_resurrection:
                self._assert_no_resurrection(snapshot, markers)
            snapshots.append(
                {
                    "kind": "snapshot",
                    "path": path,
                    "name": path.name,
                    "digest": digest,
                    "record_ids": sorted(snapshot["records"]),
                    "record_id_hashes": sorted(
                        opaque_identifier(value) for value in snapshot["records"]
                    ),
                }
            )
        for path in sorted(self.backups_path.iterdir(), key=lambda item: item.name):
            backups.append(
                self._load_backup_artifact(
                    path,
                    workspace_id=workspace_id,
                    markers=markers,
                    enforce_resurrection=enforce_resurrection,
                )
            )
        return {"snapshots": snapshots, "backups": backups}

    def _compute_forget_plan(
        self,
        snapshot: Mapping[str, Any],
        record_id: str,
        inventory: Mapping[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        if record_id not in snapshot["records"]:
            raise KeyError(f"Commonplace record not found: {record_id}")
        affected = {record_id}
        changed = True
        while changed:
            changed = False
            for candidate_id, record in snapshot["records"].items():
                if candidate_id not in affected and record_provenance_dependencies(record).intersection(affected):
                    affected.add(candidate_id)
                    changed = True
        affected_hashes = {opaque_identifier(value) for value in affected}
        snapshot_targets = [
            item
            for item in inventory["snapshots"]
            if set(item["record_ids"]).intersection(affected)
        ]
        backup_targets = [
            item
            for item in inventory["backups"]
            if set(item["record_ids"]).intersection(affected)
        ]
        reference_count = 0
        for candidate_id, record in snapshot["records"].items():
            if candidate_id in affected:
                continue
            reference_count += sum(rel["target_id"] in affected for rel in record.get("relations", []))
            reference_count += sum(value in affected for value in record.get("supersedes", []))
            reference_count += sum(value in affected for value in record.get("superseded_by", []))
        return {
            "ok": True,
            "operation": "forget-plan",
            "generation": snapshot["generation"],
            "record_id": record_id,
            "affected_record_ids": sorted(affected),
            "affected_id_hashes": sorted(affected_hashes),
            "snapshot_files": [item["name"] for item in snapshot_targets],
            "snapshot_digests": sorted({item["digest"] for item in snapshot_targets}),
            "backup_names": [item["name"] for item in backup_targets],
            "backup_digests": sorted({item["digest"] for item in backup_targets}),
            "survivor_reference_count": reference_count,
            "physical_erasure_claim": False,
        }

    def _bound_forget_plan(
        self,
        pointer: Mapping[str, Any],
        snapshot: Mapping[str, Any],
        digest: str,
        record_id: str,
        inventory: Mapping[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        plan = self._compute_forget_plan(snapshot, record_id, inventory)
        plan.update(
            {
                "workspace_id": snapshot["workspace_id"],
                "snapshot": pointer["snapshot"],
                "snapshot_sha256": digest,
                **self._location_fields(
                    snapshot["workspace_id"], snapshot["generation"], digest
                ),
            }
        )
        plan["canonical_plan_digest"] = digest_object(plan)
        return plan

    def forget_plan(self, record_id: str) -> dict[str, Any]:
        checked_id = validate_record_id(record_id)
        with self._lock():
            pointer, snapshot, digest = self._load_current()
            markers = self._load_marker_receipts()
            inventory = self._inventory_managed_artifacts(
                workspace_id=snapshot["workspace_id"], markers=markers
            )
            return self._bound_forget_plan(
                pointer, snapshot, digest, checked_id, inventory
            )

    @staticmethod
    def _find_forget_marker(
        markers: Mapping[str, Mapping[str, Any]],
        *,
        record_hash: str,
        generation: int | None = None,
        transaction_id: str | None = None,
    ) -> dict[str, Any] | None:
        matches = [
            dict(marker)
            for marker in markers.values()
            if record_hash in marker["affected_id_hashes"]
            and (generation is None or marker["generation"] == generation)
            and (
                transaction_id is None
                or marker["transaction_id"] == transaction_id
            )
        ]
        if len(matches) > 1:
            raise IntegrityError("multiple forget markers cover the same operation")
        return matches[0] if matches else None

    @staticmethod
    def _cleanup_error(
        code: str,
        *,
        artifact_digest: str | None = None,
        detail: str | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {"code": code}
        if artifact_digest is not None:
            result["artifact_digest"] = artifact_digest
        if detail is not None:
            result["detail_digest"] = digest_object(
                {"code": code, "detail": detail}
            )
        return result

    def _purge_forget_artifacts(
        self,
        marker: Mapping[str, Any],
        *,
        current_snapshot_digest: str,
    ) -> dict[str, Any]:
        errors: list[dict[str, Any]] = []
        deleted_snapshots: list[str] = []
        deleted_backups: list[str] = []
        requires_repair = False
        try:
            inventory = self._inventory_managed_artifacts(
                workspace_id=marker["workspace_id"],
                markers=self._load_marker_receipts(),
                enforce_resurrection=False,
            )
        except (IntegrityError, OSError, AntiResurrectionError) as exc:
            return {
                "status": "purge_incomplete",
                "retryable": False,
                "requires_repair": True,
                "deleted": {"snapshot_digests": [], "backup_digests": []},
                "pending": {
                    "snapshot_digests": list(marker["target_snapshot_digests"]),
                    "backup_digests": list(marker["target_backup_digests"]),
                },
                "errors": [
                    self._cleanup_error(
                        "inventory_invalid",
                        detail=f"{type(exc).__name__}:{exc}",
                    )
                ],
                "negative_check": {"affected_id_hashes_absent": False},
            }

        target_snapshots = set(marker["target_snapshot_digests"])
        target_backups = set(marker["target_backup_digests"])
        for item in inventory["snapshots"]:
            if item["digest"] not in target_snapshots:
                continue
            if item["digest"] == current_snapshot_digest:
                requires_repair = True
                errors.append(
                    self._cleanup_error(
                        "current_snapshot_is_purge_target",
                        artifact_digest=item["digest"],
                    )
                )
                continue
            try:
                item["path"].unlink()
                deleted_snapshots.append(item["digest"])
            except FileNotFoundError:
                pass
            except OSError as exc:
                errors.append(
                    self._cleanup_error(
                        "delete_failed",
                        artifact_digest=item["digest"],
                        detail=f"{type(exc).__name__}:{exc}",
                    )
                )
        for item in inventory["backups"]:
            if item["digest"] not in target_backups:
                continue
            try:
                shutil.rmtree(item["path"])
                deleted_backups.append(item["digest"])
            except FileNotFoundError:
                pass
            except OSError as exc:
                errors.append(
                    self._cleanup_error(
                        "delete_failed",
                        artifact_digest=item["digest"],
                        detail=f"{type(exc).__name__}:{exc}",
                    )
                )

        try:
            remaining_inventory = self._inventory_managed_artifacts(
                workspace_id=marker["workspace_id"],
                markers=self._load_marker_receipts(),
                enforce_resurrection=False,
            )
        except (IntegrityError, OSError, AntiResurrectionError) as exc:
            requires_repair = True
            errors.append(
                self._cleanup_error(
                    "post_delete_inventory_invalid",
                    detail=f"{type(exc).__name__}:{exc}",
                )
            )
            remaining_inventory = {"snapshots": [], "backups": []}

        remaining_snapshot_digests = sorted(
            target_snapshots.intersection(
                item["digest"] for item in remaining_inventory["snapshots"]
            )
        )
        remaining_backup_digests = sorted(
            target_backups.intersection(
                item["digest"] for item in remaining_inventory["backups"]
            )
        )
        affected_hashes = set(marker["affected_id_hashes"])
        unplanned_residue = [
            item
            for kind in ("snapshots", "backups")
            for item in remaining_inventory[kind]
            if affected_hashes.intersection(item["record_id_hashes"])
            and item["digest"]
            not in (
                target_snapshots if kind == "snapshots" else target_backups
            )
        ]
        if unplanned_residue:
            requires_repair = True
            errors.extend(
                self._cleanup_error(
                    "unplanned_resurrection_residue",
                    artifact_digest=item["digest"],
                )
                for item in unplanned_residue
            )
        complete = (
            not errors
            and not remaining_snapshot_digests
            and not remaining_backup_digests
            and not unplanned_residue
        )
        return {
            "status": "complete" if complete else "purge_incomplete",
            "retryable": bool(
                not complete
                and not requires_repair
                and (remaining_snapshot_digests or remaining_backup_digests)
            ),
            "requires_repair": requires_repair,
            "deleted": {
                "snapshot_digests": sorted(set(deleted_snapshots)),
                "backup_digests": sorted(set(deleted_backups)),
            },
            "pending": {
                "snapshot_digests": remaining_snapshot_digests,
                "backup_digests": remaining_backup_digests,
            },
            "errors": errors,
            "negative_check": {
                "affected_id_hashes_absent": complete,
            },
        }

    def _forget_result(
        self,
        marker: Mapping[str, Any],
        current_snapshot: Mapping[str, Any],
        purge: Mapping[str, Any],
        *,
        replayed: bool,
    ) -> dict[str, Any]:
        entry = {
            "generation": marker["generation"],
            "transaction_id": marker["transaction_id"],
            "operation": "forget",
            "record_ids": [],
        }
        receipt = self._load_commit_receipt(entry)
        complete = purge["status"] == "complete"
        return {
            "ok": complete,
            "operation": "forget",
            "status": purge["status"],
            "canonical_committed": True,
            "generation": marker["generation"],
            "committed_generation": marker["generation"],
            "current_generation": current_snapshot["generation"],
            "snapshot_sha256": receipt["snapshot_sha256"],
            **self._location_fields(
                marker["workspace_id"],
                marker["generation"],
                receipt["snapshot_sha256"],
            ),
            "replayed": replayed,
            "record_ids": [],
            "record_content_available": False,
            "marker_id": marker["marker_id"],
            "canonical_plan_digest": marker["canonical_plan_digest"],
            "affected_count": len(marker["affected_id_hashes"]),
            "affected_id_hashes": list(marker["affected_id_hashes"]),
            "purge": dict(purge),
            "pruned_snapshot_digests": list(
                purge["deleted"]["snapshot_digests"]
            ),
            "pruned_backup_digests": list(
                purge["deleted"]["backup_digests"]
            ),
            "physical_erasure_claim": False,
            "statement": marker["statement"],
        }

    def forget(
        self,
        record_id: str,
        *,
        authority: str | Mapping[str, Any],
        expected_generation: int,
        idempotency_key: str | None = None,
        expected_plan_digest: str,
    ) -> dict[str, Any]:
        checked_id = validate_record_id(record_id)
        if (
            not isinstance(expected_plan_digest, str)
            or not _HEX64.fullmatch(expected_plan_digest)
        ):
            raise ValidationError(
                "expected_plan_digest must be the canonical SHA-256 from forget_plan"
            )
        key_digest = self._idempotency_key_digest(idempotency_key)
        payload_digest = self._payload_digest("forget", {"record_id": checked_id})
        normalized_authority = normalize_authority(authority)
        with self._lock():
            pointer, snapshot, parent_digest = self._load_current(
                allow_pending_purge=True
            )
            markers = self._load_marker_receipts()
            replay = self._idempotency_replay(
                snapshot,
                key_digest=key_digest,
                payload_digest=payload_digest,
                operation="forget",
                snapshot_digest=parent_digest,
            )
            checked_hash = opaque_identifier(checked_id)
            if replay is not None:
                marker = self._find_forget_marker(
                    markers,
                    record_hash=checked_hash,
                    generation=replay["committed_generation"],
                    transaction_id=snapshot["idempotency"][key_digest]["transaction_id"],
                )
                if marker is None:
                    raise IntegrityError(
                        "forget idempotency receipt has no corresponding marker"
                    )
                purge = self._purge_forget_artifacts(
                    marker, current_snapshot_digest=parent_digest
                )
                return self._forget_result(
                    marker, snapshot, purge, replayed=True
                )

            existing = self._find_forget_marker(
                markers, record_hash=checked_hash
            )
            if checked_id not in snapshot["records"]:
                if existing is None:
                    raise KeyError(f"Commonplace record not found: {checked_id}")
                purge = self._purge_forget_artifacts(
                    existing, current_snapshot_digest=parent_digest
                )
                return self._forget_result(
                    existing, snapshot, purge, replayed=True
                )

            self._check_expected(snapshot, expected_generation)
            inventory = self._inventory_managed_artifacts(
                workspace_id=snapshot["workspace_id"], markers=markers
            )
            plan = self._bound_forget_plan(
                pointer, snapshot, parent_digest, checked_id, inventory
            )
            if plan["canonical_plan_digest"] != expected_plan_digest:
                raise ConflictError(
                    "canonical forget plan changed; inspect a fresh forget-plan"
                )
            affected = set(plan["affected_record_ids"])
            timestamp = utc_now()
            records = {
                survivor_id: sanitize_references(record, affected, now=timestamp)
                for survivor_id, record in snapshot["records"].items()
                if survivor_id not in affected
            }
            idempotency = {
                key: deepcopy(entry)
                for key, entry in snapshot["idempotency"].items()
                if not set(entry["record_ids"]).intersection(affected)
            }
            generation = snapshot["generation"] + 1
            transaction_id = uuid4().hex
            self._put_idempotency(
                idempotency,
                key_digest=key_digest,
                operation="forget",
                payload_digest=payload_digest,
                generation=generation,
                record_ids=[],
                transaction_id=transaction_id,
            )
            statement = (
                "Logical canonical forget completed; physical erasure of storage media, "
                "filesystem journals, remote replicas, or external copies is not claimed."
            )
            authority_digest = digest_object(normalized_authority)
            marker_core = {
                "schema": FORGET_MARKER_SCHEMA,
                "workspace_id": snapshot["workspace_id"],
                "created_at": timestamp,
                "generation": generation,
                "transaction_id": transaction_id,
                "canonical_plan_digest": plan["canonical_plan_digest"],
                "affected_id_hashes": plan["affected_id_hashes"],
                "target_snapshot_digests": plan["snapshot_digests"],
                "target_backup_digests": plan["backup_digests"],
                "authority_digest": authority_digest,
                "physical_erasure_claim": False,
                "statement": statement,
            }
            marker_id = digest_object(marker_core)
            marker = {**marker_core, "marker_id": marker_id}
            next_snapshot = self._snapshot(
                generation=generation,
                workspace_id=snapshot["workspace_id"],
                records=records,
                idempotency=idempotency,
                forget_markers=list(snapshot["forget_markers"]) + [marker_id],
                parent_digest=None,
                operation="forget",
                authority=normalized_authority,
                created_at=timestamp,
                history_boundary=marker_id,
                transaction_id=transaction_id,
            )
            digest = self._commit_snapshot(
                next_snapshot, record_ids=[], forget_marker=marker
            )
            purge = self._purge_forget_artifacts(
                marker, current_snapshot_digest=digest
            )
            return self._forget_result(
                marker, next_snapshot, purge, replayed=False
            )
    def backup(
        self,
        *,
        name: str | None = None,
        authority: str | Mapping[str, Any] = "local-backup",
    ) -> dict[str, Any]:
        normalized_authority = normalize_authority(authority)
        if name is None:
            name = "backup-" + utc_now().replace(":", "").replace("-", "") + "-" + uuid4().hex[:8]
        checked_name = validate_component(name, field="backup name")
        self._ensure_layout()
        with self._lock():
            pointer, snapshot, digest = self._load_current()
            destination = self.paths.confined("backups", checked_name)
            if destination.exists():
                raise ConflictError(f"backup already exists: {checked_name}")
            temporary = self.paths.confined("backups", f".{checked_name}.tmp-{uuid4().hex}")
            temporary.mkdir(parents=False)
            try:
                snapshot_bytes = self.paths.confined(pointer["snapshot"]).read_bytes()
                atomic_write(temporary / "snapshot.json", snapshot_bytes)
                manifest = {
                    "schema": BACKUP_SCHEMA,
                    "name": checked_name,
                    "created_at": utc_now(),
                    "workspace_id": snapshot["workspace_id"],
                    "snapshot_generation": snapshot["generation"],
                    "snapshot_sha256": digest,
                    "source_pointer_sha256": digest_object(pointer),
                    "authority_digest": digest_object(normalized_authority),
                    "record_id_hashes": sorted(opaque_identifier(value) for value in snapshot["records"]),
                }
                atomic_write_json(temporary / "manifest.json", manifest)
                temporary.replace(destination)
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)
        return {
            "ok": True, "operation": "backup", "name": checked_name,
            "path": str(destination), "generation": snapshot["generation"],
            "snapshot_sha256": digest,
            **self._location_fields(snapshot["workspace_id"], snapshot["generation"], digest),
            "record_count": len(snapshot["records"])
        }

    def restore_test(self, name: str) -> dict[str, Any]:
        checked_name = validate_component(name, field="backup name")
        backup_dir = self.paths.confined("backups", checked_name)
        if not backup_dir.is_dir():
            raise FileNotFoundError(f"backup not found: {checked_name}")
        try:
            manifest = read_json(backup_dir / "manifest.json")
            if not isinstance(manifest, Mapping) or manifest.get("schema") != BACKUP_SCHEMA:
                raise IntegrityError("backup manifest schema is invalid")
            snapshot_bytes = (backup_dir / "snapshot.json").read_bytes()
            digest = sha256_bytes(snapshot_bytes)
            if digest != manifest.get("snapshot_sha256"):
                raise IntegrityError("backup snapshot digest does not match manifest")
            snapshot = self._validate_snapshot(read_json(backup_dir / "snapshot.json"))
            if snapshot["generation"] != manifest.get("snapshot_generation"):
                raise IntegrityError("backup snapshot generation does not match manifest")
            if snapshot["workspace_id"] != manifest.get("workspace_id"):
                raise IntegrityError("backup workspace_id does not match snapshot")
            expected_id_hashes = sorted(opaque_identifier(value) for value in snapshot["records"])
            if expected_id_hashes != manifest.get("record_id_hashes"):
                raise IntegrityError("backup record identifier hashes do not match snapshot")
            self._assert_no_resurrection(snapshot, self._load_marker_receipts())
            self.restore_tests_path.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="restore-test-", dir=self.restore_tests_path) as temp_text:
                copied = Path(temp_text) / "snapshot.json"
                atomic_write(copied, snapshot_bytes)
                if sha256_bytes(copied.read_bytes()) != digest:
                    raise IntegrityError("restore-test copy did not preserve the snapshot digest")
        except (IntegrityError, AntiResurrectionError, OSError) as exc:
            return {
                "ok": False, "operation": "restore-test", "name": checked_name,
                "errors": [str(exc)], "resurrection_blocked": isinstance(exc, AntiResurrectionError)
            }
        return {
            "ok": True, "operation": "restore-test", "name": checked_name,
            "workspace_id": snapshot["workspace_id"],
            "generation": snapshot["generation"], "snapshot_sha256": digest,
            "snapshot_path": str(backup_dir / "snapshot.json"),
            "record_count": len(snapshot["records"]), "errors": [], "resurrection_blocked": False
        }

    def recover(
        self,
        *,
        authority: str | Mapping[str, Any],
        expected_generation: int | None = None,
    ) -> dict[str, Any]:
        normalized_authority = normalize_authority(authority)
        self._ensure_layout()
        with self._lock():
            markers = self._load_marker_receipts()
            audit = self._audit_managed_store(
                markers=markers,
                allow_resurrection_candidates=True,
            )
            highest = audit["highest_safe"]
            recovered_snapshot = highest["snapshot"]
            generation = highest["generation"]
            digest = highest["digest"]
            path = highest["path"]
            if expected_generation is not None:
                expected = self._validate_generation(
                    expected_generation, field="expected_generation"
                )
                if generation != expected:
                    raise ConflictError(
                        f"recovery candidate generation {generation} "
                        f"does not match expected {expected}"
                    )

            current_valid = False
            try:
                _, current_snapshot, current_digest = self._load_current(
                    audit_catalog=False
                )
                current_valid = (
                    current_snapshot["generation"] == generation
                    and current_digest == digest
                )
                current_error = None
            except (
                NotInitializedError,
                IntegrityError,
                AntiResurrectionError,
                OSError,
                ValidationError,
            ) as exc:
                current_error = str(exc)

            blocked_paths = [item["path"] for item in audit["blocked"]]
            if current_valid and not blocked_paths:
                return {
                    "ok": True,
                    "operation": "recover",
                    "recovered": False,
                    "generation": generation,
                    "snapshot_sha256": digest,
                    **self._location_fields(
                        recovered_snapshot["workspace_id"], generation, digest
                    ),
                    "reason": "CURRENT and the exhaustive managed catalog are valid",
                }

            timestamp = utc_now()
            receipt = {
                "schema": RECEIPT_SCHEMA,
                "generation": generation,
                "created_at": timestamp,
                "operation": "recover",
                "transaction_id": uuid4().hex,
                "authority_digest": digest_object(normalized_authority),
                "snapshot_sha256": digest,
                "record_id_hashes": [],
            }
            receipt_path = self.receipts_path / (
                f"recover-{receipt['transaction_id']}.json"
            )
            self._validate_receipt_document(
                receipt, kind="recover", path=receipt_path
            )
            if receipt_path.exists():
                raise IntegrityError("recovery receipt path collision")
            atomic_write_json(receipt_path, receipt)
            atomic_write_json(
                self.current_path,
                self._pointer(
                    recovered_snapshot["workspace_id"],
                    generation,
                    digest,
                    updated_at=timestamp,
                ),
            )
            _, published, published_digest = self._load_current(
                audit_catalog=False
            )
            if (
                published["generation"] != generation
                or published_digest != digest
                or published["workspace_id"] != recovered_snapshot["workspace_id"]
            ):
                raise IntegrityError("recovery CURRENT did not verify after publication")

            pruned_resurrection_candidates: list[str] = []
            for blocked_path in blocked_paths:
                try:
                    blocked_path.unlink()
                    pruned_resurrection_candidates.append(blocked_path.name)
                except FileNotFoundError:
                    pass
                except OSError as exc:
                    raise IntegrityError(
                        "recovery published safe state but could not prune "
                        f"{blocked_path.name}: {exc}"
                    ) from exc

            final_audit = self._audit_managed_store(
                markers=markers,
                allow_resurrection_candidates=False,
            )
            if (
                final_audit["highest_safe"]["generation"] != generation
                or final_audit["highest_safe"]["digest"] != digest
            ):
                raise IntegrityError("recovery final catalog binding changed")
        return {
            "ok": True,
            "operation": "recover",
            "recovered": True,
            "generation": generation,
            "snapshot_sha256": digest,
            **self._location_fields(
                recovered_snapshot["workspace_id"], generation, digest
            ),
            "snapshot": f"snapshots/{path.name}",
            "previous_error": current_error,
            "pruned_resurrection_candidates": sorted(
                pruned_resurrection_candidates
            ),
            "commit_receipts_checked": final_audit[
                "commit_receipts_checked"
            ],
            "recovery_receipts_checked": final_audit[
                "recovery_receipts_checked"
            ],
        }

    def verify(self) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        current_digest: str | None = None
        current_generation: int | None = None
        snapshots_checked = 0
        backups_checked = 0
        commit_receipts_checked = 0
        recovery_receipts_checked = 0
        markers: dict[str, dict[str, Any]] = {}
        audit: dict[str, Any] | None = None

        try:
            markers = self._load_marker_receipts()
        except (IntegrityError, OSError, ValidationError) as exc:
            errors.append(str(exc))
        if not errors:
            try:
                audit = self._audit_managed_store(
                    markers=markers,
                    allow_resurrection_candidates=False,
                )
                snapshots_checked = len(audit["snapshots"])
                backups_checked = len(audit["backups"])
                commit_receipts_checked = audit["commit_receipts_checked"]
                recovery_receipts_checked = audit["recovery_receipts_checked"]
            except (
                IntegrityError,
                AntiResurrectionError,
                OSError,
                ValidationError,
            ) as exc:
                errors.append(f"managed artifact audit: {exc}")

        try:
            pointer, current, current_digest = self._load_current(
                audit_catalog=False
            )
            current_generation = current["generation"]
            if audit is not None:
                highest = audit["highest_safe"]
                if (
                    highest["generation"] != current_generation
                    or highest["digest"] != current_digest
                ):
                    errors.append(
                        "CURRENT is not the highest authenticated safe generation"
                    )
                if audit["workspace_id"] != current["workspace_id"]:
                    errors.append(
                        "CURRENT workspace does not match the managed catalog"
                    )
        except (
            NotInitializedError,
            IntegrityError,
            AntiResurrectionError,
            OSError,
            ValidationError,
        ) as exc:
            errors.append(str(exc))

        return {
            "ok": not errors,
            "operation": "verify",
            "root": str(self.root),
            "generation": current_generation,
            "snapshot_sha256": current_digest,
            "snapshots_checked": snapshots_checked,
            "backups_checked": backups_checked,
            "commit_receipts_checked": commit_receipts_checked,
            "recovery_receipts_checked": recovery_receipts_checked,
            "forget_markers_checked": len(markers),
            "intentionally_unmanaged_artifact_classes": [
                ".commonplace.lock runtime coordination payload"
            ],
            "errors": errors,
            "warnings": warnings,
        }
