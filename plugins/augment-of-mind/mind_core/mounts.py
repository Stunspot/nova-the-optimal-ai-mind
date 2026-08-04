"""Federated mount metadata without opening or absorbing owner stores."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Iterable

from .constants import AVAILABILITY_STATES, REGISTRATION_STATES
from .errors import NotFoundError, ValidationError
from .handshake import HostRegistry
from .receipts import ReceiptLedger
from .store import CoreStore, insert_exact
from .util import (
    is_fresh,
    optional_text,
    parse_timestamp,
    record_binding_hash,
    require_bounded_interval,
    require_identifier,
    require_interval,
    require_text,
    timestamp,
)


class MountCatalog:
    def __init__(
        self, store: CoreStore, receipts: ReceiptLedger, hosts: HostRegistry
    ) -> None:
        self._store = store
        self.receipts = receipts
        self.hosts = hosts

    def ingest_mounts(
        self, records: Iterable[dict[str, Any]], connection: sqlite3.Connection
    ) -> None:
        for item in records:
            registration_state = require_identifier(
                item.get("registration_state"), "registration_state"
            )
            if registration_state not in REGISTRATION_STATES:
                raise ValidationError(f"unsupported registration_state: {registration_state}")
            record = {
                "mount_id": require_identifier(item.get("mount_id"), "mount_id"),
                "handle": require_identifier(item.get("handle"), "handle").lower(),
                "owner_id": require_identifier(item.get("owner_id"), "owner_id"),
                "mount_class": require_identifier(item.get("mount_class"), "mount_class"),
                "purpose": require_text(item.get("purpose"), "purpose", maximum=2048),
                "front_door": require_text(
                    item.get("front_door"), "front_door", maximum=2048
                ),
                "registration_state": registration_state,
                "registration_provenance": require_text(
                    item.get("registration_provenance"),
                    "registration_provenance",
                    maximum=2048,
                ),
                "canonical_role": require_identifier(
                    item.get("canonical_role"), "canonical_role"
                ),
                "sensitivity_ceiling": require_identifier(
                    item.get("sensitivity_ceiling"), "sensitivity_ceiling"
                ),
                "portability": require_identifier(
                    item.get("portability"), "portability"
                ),
                "indexing_eligibility": require_identifier(
                    item.get("indexing_eligibility"), "indexing_eligibility"
                ),
                "export_eligibility": require_identifier(
                    item.get("export_eligibility"), "export_eligibility"
                ),
                "created_at": timestamp(
                    parse_timestamp(item.get("created_at"), "created_at")
                ),
            }
            insert_exact(connection, "mounts", record, ("mount_id",))

    def record_grant(self, item: dict[str, Any]) -> dict[str, Any]:
        session = self.hosts.session(
            item.get("host_session_id"), item.get("agent_instance_id"), require_fresh=False
        )
        observed_at, expires_at = require_interval(
            item.get("observed_at"), item.get("expires_at")
        )
        require_bounded_interval(
            observed_at,
            expires_at,
            session["observed_at"],
            session["expires_at"],
            "mount_grant",
        )
        operations = item.get("allowed_operations", [])
        if not isinstance(operations, list) or not all(
            isinstance(operation, str) and operation for operation in operations
        ):
            raise ValidationError("allowed_operations must be a list of strings")
        record = {
            "grant_id": require_identifier(item.get("grant_id"), "grant_id"),
            "mount_id": require_identifier(item.get("mount_id"), "mount_id"),
            "agent_instance_id": session["agent_instance_id"],
            "host_session_id": session["host_session_id"],
            "purpose": require_text(item.get("purpose"), "purpose", maximum=2048),
            "sensitivity_ceiling": require_identifier(
                item.get("sensitivity_ceiling"), "sensitivity_ceiling"
            ),
            "allowed_operations_json": json.dumps(
                sorted(set(operations)), ensure_ascii=False, separators=(",", ":")
            ),
            "authority_ref": require_text(
                item.get("authority_ref"), "authority_ref", maximum=2048
            ),
            "observed_at": observed_at,
            "expires_at": expires_at,
            "evidence_receipt_id": require_identifier(
                item.get("evidence_receipt_id"), "evidence_receipt_id"
            ),
        }
        with self._store.transaction() as connection:
            self.receipts.require_binding(
                record["evidence_receipt_id"],
                receipt_type="mount.grant",
                subject_kind="mount_grant",
                subject_id=record["grant_id"],
                payload_hash=record_binding_hash(record),
                agent_instance_id=record["agent_instance_id"],
                host_session_id=record["host_session_id"],
                allow_global_for_scoped=False,
                connection=connection,
            )
            insert_exact(connection, "mount_grants", record, ("grant_id",))
        return record

    def record_observation(self, item: dict[str, Any]) -> dict[str, Any]:
        session = self.hosts.session(
            item.get("host_session_id"), item.get("agent_instance_id"), require_fresh=False
        )
        availability = require_identifier(
            item.get("availability_state"), "availability_state"
        )
        if availability not in AVAILABILITY_STATES:
            raise ValidationError(f"unsupported availability state: {availability}")
        observed_at, expires_at = require_interval(
            item.get("observed_at"), item.get("expires_at")
        )
        require_bounded_interval(
            observed_at,
            expires_at,
            session["observed_at"],
            session["expires_at"],
            "mount_observation",
        )

        def boolean_or_none(field: str) -> bool | None:
            value = item.get(field)
            if value is None:
                return None
            if not isinstance(value, bool):
                raise ValidationError(f"{field} must be boolean or null")
            return value

        values = {
            field: boolean_or_none(field)
            for field in (
                "path_visible",
                "runtime_openable",
                "schema_valid",
                "integrity_valid",
                "authoritative_read_succeeded",
            )
        }
        failure_boundary = optional_text(
            item.get("failure_boundary"), "failure_boundary", maximum=2048
        )
        self._validate_availability(availability, values, failure_boundary)

        record = {
            "mount_observation_id": require_identifier(
                item.get("mount_observation_id"), "mount_observation_id"
            ),
            "mount_id": require_identifier(item.get("mount_id"), "mount_id"),
            "agent_instance_id": session["agent_instance_id"],
            "host_session_id": session["host_session_id"],
            "availability_state": availability,
            **values,
            "failure_boundary": failure_boundary,
            "observed_at": observed_at,
            "expires_at": expires_at,
            "evidence_receipt_id": require_identifier(
                item.get("evidence_receipt_id"), "evidence_receipt_id"
            ),
        }
        with self._store.transaction() as connection:
            allowed_evidence_states = (
                frozenset(
                    {
                        "tool_returned",
                        "observed",
                        "reconciled",
                        "independently_verified",
                    }
                )
                if availability == "AUTHORITATIVE_EMPTY"
                else None
            )
            self.receipts.require_binding(
                record["evidence_receipt_id"],
                receipt_type="mount.observation",
                subject_kind="mount_observation",
                subject_id=record["mount_observation_id"],
                payload_hash=record_binding_hash(record),
                agent_instance_id=record["agent_instance_id"],
                host_session_id=record["host_session_id"],
                allow_global_for_scoped=False,
                allowed_evidence_states=allowed_evidence_states,
                connection=connection,
            )
            insert_exact(
                connection,
                "mount_observations",
                record,
                ("mount_observation_id",),
            )
        return self._render_observation(record)

    @staticmethod
    def _validate_availability(
        availability: str,
        values: dict[str, bool | None],
        failure_boundary: str | None,
    ) -> None:
        if values["runtime_openable"] == 0 and availability != "BACKEND_UNAVAILABLE":
            raise ValidationError(
                "runtime_openable=false requires BACKEND_UNAVAILABLE"
            )
        if availability == "AUTHORITATIVE_EMPTY" and not all(
            values[field] == 1
            for field in (
                "runtime_openable",
                "schema_valid",
                "integrity_valid",
                "authoritative_read_succeeded",
            )
        ):
            raise ValidationError(
                "AUTHORITATIVE_EMPTY requires a successful authoritative read "
                "through an open, schema-valid, integrity-valid runtime"
            )
        if availability == "INTEGRITY_FAILED" and values["integrity_valid"] != 0:
            raise ValidationError("INTEGRITY_FAILED requires integrity_valid=false")
        if availability in {
            "BACKEND_UNAVAILABLE",
            "DENIED_SCOPE",
            "INTEGRITY_FAILED",
            "PARTIAL",
            "BROKER_UNAVAILABLE",
        } and failure_boundary is None:
            raise ValidationError(f"{availability} requires failure_boundary")

    @staticmethod
    def _render_observation(
        record: dict[str, Any], *, scope_fresh: bool = True
    ) -> dict[str, Any]:
        rendered = dict(record)
        for field in (
            "path_visible",
            "runtime_openable",
            "schema_valid",
            "integrity_valid",
            "authoritative_read_succeeded",
        ):
            if rendered.get(field) is not None:
                rendered[field] = bool(rendered[field])
        rendered["fresh"] = scope_fresh and is_fresh(rendered["expires_at"])
        return rendered

    def catalog(self, host_session_id: str, agent_instance_id: str) -> list[dict[str, Any]]:
        session = self.hosts.session(
            host_session_id, agent_instance_id, require_fresh=False
        )
        mounts = self._store.connection.execute(
            "SELECT * FROM mounts ORDER BY handle, mount_id"
        ).fetchall()
        result: list[dict[str, Any]] = []
        for mount in mounts:
            observation = self._store.connection.execute(
                "SELECT * FROM mount_observations WHERE mount_id=? AND agent_instance_id=? "
                "AND host_session_id=? ORDER BY observed_at DESC, mount_observation_id DESC LIMIT 1",
                (mount["mount_id"], agent_instance_id, host_session_id),
            ).fetchone()
            grants = self._store.connection.execute(
                "SELECT * FROM mount_grants WHERE mount_id=? AND agent_instance_id=? "
                "AND host_session_id=? ORDER BY observed_at DESC, grant_id",
                (mount["mount_id"], agent_instance_id, host_session_id),
            ).fetchall()
            result.append(
                {
                    **dict(mount),
                    "observation": (
                        self._render_observation(
                            dict(observation), scope_fresh=bool(session["fresh"])
                        )
                        if observation is not None
                        else None
                    ),
                    "grants": [
                        {
                            **dict(grant),
                            "allowed_operations": json.loads(
                                grant["allowed_operations_json"]
                            ),
                            "fresh": bool(session["fresh"])
                            and is_fresh(grant["expires_at"]),
                        }
                        for grant in grants
                    ],
                    "claim_boundary": (
                        "Catalog metadata is not a store read. Missing observation is unknown, not absent or empty."
                    ),
                }
            )
        return result

    def observation(
        self, mount_id: str, host_session_id: str, agent_instance_id: str
    ) -> dict[str, Any] | None:
        mount_id = require_identifier(mount_id, "mount_id")
        session = self.hosts.session(
            host_session_id, agent_instance_id, require_fresh=False
        )
        if self._store.connection.execute(
            "SELECT 1 FROM mounts WHERE mount_id=?", (mount_id,)
        ).fetchone() is None:
            raise NotFoundError(f"mount not found: {mount_id}")
        row = self._store.connection.execute(
            "SELECT * FROM mount_observations WHERE mount_id=? AND agent_instance_id=? "
            "AND host_session_id=? ORDER BY observed_at DESC, mount_observation_id DESC LIMIT 1",
            (mount_id, agent_instance_id, host_session_id),
        ).fetchone()
        return (
            self._render_observation(dict(row), scope_fresh=bool(session["fresh"]))
            if row is not None
            else None
        )
