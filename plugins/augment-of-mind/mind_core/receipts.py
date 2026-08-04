"""Append-only, redacted evidence receipts."""

from __future__ import annotations

import sqlite3
from contextlib import nullcontext
from typing import Any, Iterable

from .constants import EVIDENCE_STATES
from .errors import ConflictError, NotFoundError, ScopeError, ValidationError
from .store import CoreStore
from .util import (
    canonical_json,
    new_id,
    optional_text,
    parse_timestamp,
    require_identifier,
    require_sha256,
    require_text,
    sha256_text,
    timestamp,
)


class ReceiptLedger:
    def __init__(self, store: CoreStore):
        self._store = store

    def append(
        self,
        envelope: dict[str, Any],
        *,
        parents: Iterable[dict[str, str]] = (),
        connection: sqlite3.Connection | None = None,
    ) -> dict[str, Any]:
        parent_list: list[dict[str, str]] = []
        parent_keys: set[tuple[str, str]] = set()
        for item in parents:
            parent = {
                "receipt_id": require_identifier(
                    item["receipt_id"], "parent.receipt_id"
                ),
                "relation": require_identifier(item["relation"], "parent.relation"),
            }
            key = (parent["receipt_id"], parent["relation"])
            if key in parent_keys:
                raise ValidationError("duplicate receipt parent edge")
            parent_keys.add(key)
            parent_list.append(parent)
        parent_list.sort(key=lambda item: (item["receipt_id"], item["relation"]))
        agent_instance_id = envelope.get("agent_instance_id")
        host_session_id = envelope.get("host_session_id")
        if (agent_instance_id is None) != (host_session_id is None):
            raise ScopeError("receipt scope requires both agent_instance_id and host_session_id")
        if agent_instance_id is not None:
            agent_instance_id = require_identifier(agent_instance_id, "agent_instance_id")
            host_session_id = require_identifier(host_session_id, "host_session_id")

        evidence_state = require_identifier(envelope.get("evidence_state"), "evidence_state")
        if evidence_state not in EVIDENCE_STATES:
            raise ValidationError(f"unsupported evidence_state: {evidence_state}")
        observed = timestamp(parse_timestamp(envelope.get("observed_at"), "observed_at"))
        expiry_value = envelope.get("expires_at")
        expires_at = None
        if expiry_value is not None:
            expires = parse_timestamp(expiry_value, "expires_at")
            if expires <= parse_timestamp(observed, "observed_at"):
                raise ValidationError("receipt expires_at must be after observed_at")
            expires_at = timestamp(expires)

        logical = {
            "idempotency_key": require_identifier(
                envelope.get("idempotency_key"), "idempotency_key"
            ),
            "receipt_type": require_identifier(envelope.get("receipt_type"), "receipt_type"),
            "subject_kind": require_identifier(envelope.get("subject_kind"), "subject_kind"),
            "subject_id": require_identifier(envelope.get("subject_id"), "subject_id"),
            "agent_instance_id": agent_instance_id,
            "host_session_id": host_session_id,
            "evidence_state": evidence_state,
            "claimed_boundary": require_text(
                envelope.get("claimed_boundary"), "claimed_boundary", maximum=2048
            ),
            "observed_at": observed,
            "expires_at": expires_at,
            "redaction_class": require_identifier(
                envelope.get("redaction_class", "metadata_only"), "redaction_class"
            ),
            "payload_hash": require_sha256(envelope.get("payload_hash"), "payload_hash"),
            "parents": parent_list,
        }
        content_digest = sha256_text(canonical_json(logical))

        transaction = (
            self._store.transaction() if connection is None else nullcontext(connection)
        )
        with transaction as active_connection:
            if agent_instance_id is None:
                existing = active_connection.execute(
                    "SELECT * FROM receipts WHERE idempotency_key=? "
                    "AND agent_instance_id IS NULL AND host_session_id IS NULL",
                    (logical["idempotency_key"],),
                ).fetchone()
            else:
                existing = active_connection.execute(
                    "SELECT * FROM receipts WHERE idempotency_key=? "
                    "AND agent_instance_id=? AND host_session_id=?",
                    (logical["idempotency_key"], agent_instance_id, host_session_id),
                ).fetchone()
            if existing is not None:
                if existing["content_digest"] != content_digest:
                    raise ConflictError("receipt idempotency key was reused with different content")
                requested_receipt_id = envelope.get("receipt_id")
                if (
                    requested_receipt_id is not None
                    and require_identifier(requested_receipt_id, "receipt_id")
                    != existing["receipt_id"]
                ):
                    raise ConflictError("receipt id changed on idempotent replay")
                existing_edges = active_connection.execute(
                    "SELECT parent_receipt_id AS receipt_id, relation FROM receipt_edges "
                    "WHERE child_receipt_id=? ORDER BY parent_receipt_id, relation",
                    (existing["receipt_id"],),
                ).fetchall()
                if [dict(row) for row in existing_edges] != parent_list:
                    raise ConflictError("receipt parent set changed on replay")
                result = dict(existing)
            else:
                receipt_id = require_identifier(
                    envelope.get("receipt_id", new_id("receipt")), "receipt_id"
                )
                if active_connection.execute(
                    "SELECT 1 FROM receipts WHERE receipt_id=?", (receipt_id,)
                ).fetchone() is not None:
                    raise ConflictError("receipt_id is already in use")
                validated_parents: list[dict[str, str]] = []
                for parent in parent_list:
                    parent_row = active_connection.execute(
                        "SELECT receipt_id,agent_instance_id,host_session_id "
                        "FROM receipts WHERE receipt_id=?",
                        (parent["receipt_id"],),
                    ).fetchone()
                    if parent_row is None:
                        raise NotFoundError(
                            f"parent receipt not found: {parent['receipt_id']}"
                        )
                    if agent_instance_id is None:
                        compatible = parent_row["agent_instance_id"] is None
                    else:
                        compatible = parent_row["agent_instance_id"] is None or (
                            parent_row["agent_instance_id"] == agent_instance_id
                            and parent_row["host_session_id"] == host_session_id
                        )
                    if not compatible:
                        raise ScopeError("receipt parent is outside the child scope")
                    validated_parents.append(parent)
                recorded_at = timestamp()
                active_connection.execute(
                    """
                    INSERT INTO receipts(
                      receipt_id,idempotency_key,receipt_type,subject_kind,subject_id,
                      agent_instance_id,host_session_id,evidence_state,claimed_boundary,
                      observed_at,recorded_at,expires_at,redaction_class,payload_hash,content_digest
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        receipt_id,
                        logical["idempotency_key"],
                        logical["receipt_type"],
                        logical["subject_kind"],
                        logical["subject_id"],
                        agent_instance_id,
                        host_session_id,
                        evidence_state,
                        logical["claimed_boundary"],
                        observed,
                        recorded_at,
                        expires_at,
                        logical["redaction_class"],
                        logical["payload_hash"],
                        content_digest,
                    ),
                )
                for parent in validated_parents:
                    active_connection.execute(
                        "INSERT INTO receipt_edges(child_receipt_id,parent_receipt_id,relation) "
                        "VALUES (?,?,?)",
                        (receipt_id, parent["receipt_id"], parent["relation"]),
                    )
                result = dict(
                    active_connection.execute(
                        "SELECT * FROM receipts WHERE receipt_id=?", (receipt_id,)
                    ).fetchone()
                )
        return result

    def require_compatible_scope(
        self,
        receipt_id: str,
        *,
        agent_instance_id: str | None,
        host_session_id: str | None,
        allow_global_for_scoped: bool,
        connection: sqlite3.Connection | None = None,
    ) -> dict[str, Any]:
        """Return evidence only when its scope may support the target record."""

        receipt_id = require_identifier(receipt_id, "receipt_id")
        if (agent_instance_id is None) != (host_session_id is None):
            raise ScopeError("evidence scope requires both agent and host session")
        active_connection = connection or self._store.connection
        row = active_connection.execute(
            "SELECT * FROM receipts WHERE receipt_id=?", (receipt_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"receipt not found: {receipt_id}")
        if agent_instance_id is None:
            compatible = row["agent_instance_id"] is None
        else:
            compatible = (
                allow_global_for_scoped and row["agent_instance_id"] is None
            ) or (
                row["agent_instance_id"] == agent_instance_id
                and row["host_session_id"] == host_session_id
            )
        if not compatible:
            raise NotFoundError(f"receipt not found in the requested scope: {receipt_id}")
        return dict(row)

    def require_binding(
        self,
        receipt_id: str,
        *,
        receipt_type: str,
        subject_kind: str,
        subject_id: str,
        payload_hash: str,
        agent_instance_id: str | None,
        host_session_id: str | None,
        allow_global_for_scoped: bool,
        allowed_evidence_states: frozenset[str] | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> dict[str, Any]:
        """Require scope plus an exact typed subject and canonical payload binding."""

        expected = {
            "receipt_type": require_identifier(receipt_type, "receipt_type"),
            "subject_kind": require_identifier(subject_kind, "subject_kind"),
            "subject_id": require_identifier(subject_id, "subject_id"),
            "payload_hash": require_sha256(payload_hash, "payload_hash"),
        }
        receipt = self.require_compatible_scope(
            receipt_id,
            agent_instance_id=agent_instance_id,
            host_session_id=host_session_id,
            allow_global_for_scoped=allow_global_for_scoped,
            connection=connection,
        )
        mismatches = [
            field for field, value in expected.items() if receipt[field] != value
        ]
        if mismatches:
            raise ValidationError(
                "receipt is not bound to the target record: " + ",".join(mismatches)
            )
        if (
            allowed_evidence_states is not None
            and receipt["evidence_state"] not in allowed_evidence_states
        ):
            raise ValidationError(
                "receipt evidence_state cannot support this target claim"
            )
        return receipt

    def get(
        self,
        receipt_id: str,
        *,
        agent_instance_id: str | None = None,
        host_session_id: str | None = None,
    ) -> dict[str, Any]:
        receipt_id = require_identifier(receipt_id, "receipt_id")
        row = self._store.connection.execute(
            "SELECT * FROM receipts WHERE receipt_id=?", (receipt_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"receipt not found: {receipt_id}")
        if row["agent_instance_id"] is not None:
            if agent_instance_id != row["agent_instance_id"] or host_session_id != row["host_session_id"]:
                raise NotFoundError(f"receipt not found: {receipt_id}")
        result = dict(row)
        result["parents"] = [
            dict(item)
            for item in self._store.connection.execute(
                "SELECT parent_receipt_id AS receipt_id, relation FROM receipt_edges "
                "WHERE child_receipt_id=? ORDER BY parent_receipt_id, relation",
                (receipt_id,),
            ).fetchall()
        ]
        return result
