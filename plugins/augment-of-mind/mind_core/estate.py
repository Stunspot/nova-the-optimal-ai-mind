"""Authoritative capability identity and independent lifecycle observations."""

from __future__ import annotations

import sqlite3
from typing import Any, Iterable

from .constants import (
    CAPABILITY_EXPOSURE_POLICIES,
    GLOBAL_LIFECYCLE_AXES,
    LIFECYCLE_STATES,
    SESSION_LIFECYCLE_AXES,
)
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
    require_text,
    timestamp,
)


def _nullable_identifier(value: object, field: str) -> str | None:
    return require_identifier(value, field) if value is not None else None


class CapabilityEstate:
    def __init__(
        self, store: CoreStore, receipts: ReceiptLedger, hosts: HostRegistry
    ) -> None:
        self._store = store
        self.receipts = receipts
        self.hosts = hosts

    def ingest_sources(
        self, records: Iterable[dict[str, Any]], connection: sqlite3.Connection
    ) -> None:
        for item in records:
            digest = item.get("digest")
            record = {
                "source_id": require_identifier(item.get("source_id"), "source_id"),
                "locator": require_text(item.get("locator"), "locator", maximum=4096),
                "digest": (
                    require_text(digest, "digest", maximum=256) if digest is not None else None
                ),
                "custody_state": require_identifier(
                    item.get("custody_state"), "custody_state"
                ),
                "authority_ref": require_text(
                    item.get("authority_ref"), "authority_ref", maximum=2048
                ),
                "observed_at": timestamp(
                    parse_timestamp(item.get("observed_at"), "observed_at")
                ),
            }
            if record["custody_state"] not in LIFECYCLE_STATES["custody"]:
                raise ValidationError(f"unsupported custody state: {record['custody_state']}")
            insert_exact(connection, "sources", record, ("source_id",))

    def ingest_products(
        self, records: Iterable[dict[str, Any]], connection: sqlite3.Connection
    ) -> None:
        for item in records:
            record = {
                "product_id": require_identifier(item.get("product_id"), "product_id"),
                "name": require_text(item.get("name"), "name", maximum=512),
                "owner": require_text(item.get("owner"), "owner", maximum=512),
                "canonical_uri": optional_text(
                    item.get("canonical_uri"), "canonical_uri", maximum=4096
                ),
                "created_at": timestamp(
                    parse_timestamp(item.get("created_at"), "created_at")
                ),
            }
            insert_exact(connection, "products", record, ("product_id",))

    def ingest_providers(
        self, records: Iterable[dict[str, Any]], connection: sqlite3.Connection
    ) -> None:
        for item in records:
            record = {
                "provider_id": require_identifier(item.get("provider_id"), "provider_id"),
                "name": require_text(item.get("name"), "name", maximum=512),
                "owner": require_text(item.get("owner"), "owner", maximum=512),
                "provider_kind": require_identifier(
                    item.get("provider_kind"), "provider_kind"
                ),
                "canonical_uri": optional_text(
                    item.get("canonical_uri"), "canonical_uri", maximum=4096
                ),
                "created_at": timestamp(
                    parse_timestamp(item.get("created_at"), "created_at")
                ),
            }
            insert_exact(connection, "providers", record, ("provider_id",))

    def ingest_capabilities(
        self, records: Iterable[dict[str, Any]], connection: sqlite3.Connection
    ) -> None:
        records = list(records)
        self._require_capability_admission(records, connection)
        self._ingest_capability_records(records, connection)

    def _ingest_generation_capabilities(
        self, records: Iterable[dict[str, Any]], connection: sqlite3.Connection
    ) -> None:
        """Internal half of MindCore.activate_estate_generation's transaction."""

        if not connection.in_transaction:
            raise ValidationError("capability ingestion requires an active transaction")
        self._ingest_capability_records(list(records), connection)

    @staticmethod
    def _require_capability_admission(
        records: list[dict[str, Any]], connection: sqlite3.Connection
    ) -> None:
        if not connection.in_transaction:
            raise ValidationError("capability ingestion requires an active transaction")
        activation_exists = connection.execute(
            "SELECT 1 FROM associative_snapshot_activations LIMIT 1"
        ).fetchone() is not None
        if not activation_exists:
            return
        existing_ids = {
            row["capability_id"]
            for row in connection.execute(
                "SELECT capability_id FROM capabilities"
            ).fetchall()
        }
        incoming_ids = {
            require_identifier(item.get("capability_id"), "capability_id")
            for item in records
        }
        if not incoming_ids.issubset(existing_ids):
            raise ValidationError(
                "capability ingestion cannot expand the estate after associative "
                "activation; use activate_estate_generation"
            )

    def _ingest_capability_records(
        self, records: Iterable[dict[str, Any]], connection: sqlite3.Connection
    ) -> None:
        for item in records:
            exposure_policy = require_identifier(
                item.get("exposure_policy", "public_safe"), "exposure_policy"
            )
            if exposure_policy not in CAPABILITY_EXPOSURE_POLICIES:
                raise ValidationError(
                    f"unsupported capability exposure_policy: {exposure_policy}"
                )
            owner_agent_instance_id = _nullable_identifier(
                item.get("owner_agent_instance_id"), "owner_agent_instance_id"
            )
            if (exposure_policy == "public_safe") != (
                owner_agent_instance_id is None
            ):
                raise ValidationError(
                    "public capabilities require no owner; private capabilities require one"
                )
            record = {
                "capability_id": require_identifier(
                    item.get("capability_id"), "capability_id"
                ),
                "handle": require_identifier(item.get("handle"), "handle").lower(),
                "name": require_text(item.get("name"), "name", maximum=512),
                "product_id": _nullable_identifier(item.get("product_id"), "product_id"),
                "canonical_source_id": _nullable_identifier(
                    item.get("canonical_source_id"), "canonical_source_id"
                ),
                "promise": require_text(item.get("promise"), "promise", maximum=4096),
                "negative_space": require_text(
                    item.get("negative_space"), "negative_space", maximum=4096
                ),
                "created_at": timestamp(
                    parse_timestamp(item.get("created_at"), "created_at")
                ),
                "superseded_by": _nullable_identifier(
                    item.get("superseded_by"), "superseded_by"
                ),
                "exposure_policy": exposure_policy,
                "owner_agent_instance_id": owner_agent_instance_id,
            }
            insert_exact(connection, "capabilities", record, ("capability_id",))
            for alias in item.get("aliases", []):
                alias_record = {
                    "capability_id": record["capability_id"],
                    "namespace": require_identifier(
                        alias.get("namespace", "global"), "alias.namespace"
                    ),
                    "normalized_alias": require_text(
                        alias.get("alias"), "alias.alias", maximum=512
                    ).casefold(),
                    "display_alias": require_text(
                        alias.get("display_alias", alias.get("alias")),
                        "alias.display_alias",
                        maximum=512,
                    ),
                }
                insert_exact(
                    connection,
                    "capability_aliases",
                    alias_record,
                    ("capability_id", "namespace", "normalized_alias"),
                )
            for entrypoint in item.get("entrypoints", []):
                entry_record = {
                    "capability_id": record["capability_id"],
                    "entrypoint_id": require_identifier(
                        entrypoint.get("entrypoint_id"), "entrypoint_id"
                    ),
                    "entrypoint_kind": require_identifier(
                        entrypoint.get("entrypoint_kind"), "entrypoint_kind"
                    ),
                    "locator": require_text(
                        entrypoint.get("locator"), "entrypoint.locator", maximum=4096
                    ),
                    "operation": require_text(
                        entrypoint.get("operation"), "entrypoint.operation", maximum=1024
                    ),
                }
                insert_exact(
                    connection,
                    "capability_entrypoints",
                    entry_record,
                    ("capability_id", "entrypoint_id"),
                )

    def ingest_distributions(
        self, records: Iterable[dict[str, Any]], connection: sqlite3.Connection
    ) -> None:
        for item in records:
            record = {
                "distribution_id": require_identifier(
                    item.get("distribution_id"), "distribution_id"
                ),
                "capability_id": require_identifier(
                    item.get("capability_id"), "capability_id"
                ),
                "product_id": _nullable_identifier(item.get("product_id"), "product_id"),
                "provider_id": require_identifier(
                    item.get("provider_id"), "provider_id"
                ),
                "version": require_text(item.get("version"), "version", maximum=128),
                "package_form": require_identifier(
                    item.get("package_form"), "package_form"
                ),
                "artifact_digest": optional_text(
                    item.get("artifact_digest"), "artifact_digest", maximum=256
                ),
                "source_id": _nullable_identifier(item.get("source_id"), "source_id"),
                "created_at": timestamp(
                    parse_timestamp(item.get("created_at"), "created_at")
                ),
            }
            insert_exact(connection, "distributions", record, ("distribution_id",))

    def ingest_lifecycle_observations(
        self, records: Iterable[dict[str, Any]], connection: sqlite3.Connection
    ) -> None:
        for item in records:
            axis = require_identifier(item.get("axis"), "axis")
            state = require_identifier(item.get("state"), "state")
            if state not in LIFECYCLE_STATES.get(axis, ()):
                raise ValidationError(f"unsupported lifecycle state: {axis}/{state}")
            agent_instance_id = _nullable_identifier(
                item.get("agent_instance_id"), "agent_instance_id"
            )
            host_session_id = _nullable_identifier(
                item.get("host_session_id"), "host_session_id"
            )
            if (agent_instance_id is None) != (host_session_id is None):
                raise ValidationError("lifecycle scope requires both agent and host session")
            if axis in GLOBAL_LIFECYCLE_AXES and agent_instance_id is not None:
                raise ValidationError(f"{axis} lifecycle observations must be global")
            if axis in SESSION_LIFECYCLE_AXES and agent_instance_id is None:
                raise ValidationError(f"{axis} lifecycle observations require a host scope")
            session = None
            if agent_instance_id is not None:
                session = self.hosts.session(
                    host_session_id, agent_instance_id, require_fresh=False
                )
            observed_at = timestamp(
                parse_timestamp(item.get("observed_at"), "observed_at")
            )
            expires_value = item.get("expires_at")
            expires_at = None
            if expires_value is not None:
                expires_at = timestamp(parse_timestamp(expires_value, "expires_at"))
                if expires_at <= observed_at:
                    raise ValidationError("lifecycle expires_at must be after observed_at")
            if session is not None:
                if expires_at is None:
                    raise ValidationError(
                        "session-scoped lifecycle observations require expires_at"
                    )
                require_bounded_interval(
                    observed_at,
                    expires_at,
                    session["observed_at"],
                    session["expires_at"],
                    "lifecycle_observation",
                )
            evidence_receipt_id = require_identifier(
                item.get("evidence_receipt_id"), "evidence_receipt_id"
            )
            record = {
                "observation_id": require_identifier(
                    item.get("observation_id"), "observation_id"
                ),
                "capability_id": require_identifier(
                    item.get("capability_id"), "capability_id"
                ),
                "distribution_id": _nullable_identifier(
                    item.get("distribution_id"), "distribution_id"
                ),
                "axis": axis,
                "state": state,
                "agent_instance_id": agent_instance_id,
                "host_session_id": host_session_id,
                "observed_at": observed_at,
                "expires_at": expires_at,
                "evidence_receipt_id": evidence_receipt_id,
                "source_reference": require_text(
                    item.get("source_reference"), "source_reference", maximum=2048
                ),
            }
            self.receipts.require_binding(
                evidence_receipt_id,
                receipt_type="lifecycle.observation",
                subject_kind="lifecycle_observation",
                subject_id=record["observation_id"],
                payload_hash=record_binding_hash(record),
                agent_instance_id=agent_instance_id,
                host_session_id=host_session_id,
                allow_global_for_scoped=False,
                connection=connection,
            )
            insert_exact(connection, "lifecycle_observations", record, ("observation_id",))

    def capability(
        self,
        capability_id: str,
        *,
        agent_instance_id: str | None = None,
        host_session_id: str | None = None,
        _private_agent_instance_id: str | None = None,
    ) -> dict[str, Any]:
        capability_id = require_identifier(capability_id, "capability_id")
        if _private_agent_instance_id is not None:
            _private_agent_instance_id = require_identifier(
                _private_agent_instance_id, "private_agent_instance_id"
            )
        if (agent_instance_id is None) != (host_session_id is None):
            raise ValidationError("capability scope requires both agent and host session")
        session_fresh = True
        if agent_instance_id is not None:
            session = self.hosts.session(
                host_session_id, agent_instance_id, require_fresh=False
            )
            session_fresh = bool(session["fresh"])
        row = self._store.connection.execute(
            "SELECT * FROM capabilities WHERE capability_id=?", (capability_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"capability not found: {capability_id}")
        if (
            row["exposure_policy"] == "agent_private"
            and row["owner_agent_instance_id"] != _private_agent_instance_id
        ):
            raise NotFoundError(f"capability not found: {capability_id}")
        result = dict(row)
        result["aliases"] = [
            dict(item)
            for item in self._store.connection.execute(
                "SELECT namespace, normalized_alias, display_alias FROM capability_aliases "
                "WHERE capability_id=? ORDER BY namespace, normalized_alias",
                (capability_id,),
            ).fetchall()
        ]
        result["entrypoints"] = [
            dict(item)
            for item in self._store.connection.execute(
                "SELECT entrypoint_id,entrypoint_kind,locator,operation FROM capability_entrypoints "
                "WHERE capability_id=? ORDER BY entrypoint_id",
                (capability_id,),
            ).fetchall()
        ]
        result["distributions"] = [
            dict(item)
            for item in self._store.connection.execute(
                "SELECT d.*, p.name AS provider_name FROM distributions d "
                "JOIN providers p ON p.provider_id=d.provider_id "
                "WHERE d.capability_id=? ORDER BY d.provider_id,d.version,d.distribution_id",
                (capability_id,),
            ).fetchall()
        ]
        params: list[object] = [capability_id]
        scope_clause = "agent_instance_id IS NULL AND host_session_id IS NULL"
        if agent_instance_id is not None:
            scope_clause = (
                "(agent_instance_id IS NULL AND host_session_id IS NULL) OR "
                "(agent_instance_id=? AND host_session_id=?)"
            )
            params.extend([agent_instance_id, host_session_id])
        observations = self._store.connection.execute(
            f"SELECT * FROM lifecycle_observations WHERE capability_id=? AND ({scope_clause}) "
            "ORDER BY axis, observed_at, observation_id",
            tuple(params),
        ).fetchall()
        result["lifecycle_observations"] = [
            {
                **dict(item),
                "fresh": (
                    item["expires_at"] is None or is_fresh(item["expires_at"])
                )
                and (item["agent_instance_id"] is None or session_fresh),
            }
            for item in observations
        ]
        result["derived_active_state"] = None
        result["claim_boundary"] = (
            "Lifecycle axes are independent observations. This response does not infer active, usable, invoked, or healthy."
        )
        return result

    def resolve(
        self,
        handle_or_alias: str,
        *,
        agent_instance_id: str | None = None,
        host_session_id: str | None = None,
        _private_agent_instance_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query = require_text(handle_or_alias, "handle_or_alias", maximum=512).casefold()
        private_agent = (
            require_identifier(
                _private_agent_instance_id, "private_agent_instance_id"
            )
            if _private_agent_instance_id is not None
            else ""
        )
        rows = self._store.connection.execute(
            """
            SELECT capability_id FROM capabilities
            WHERE handle=?
              AND (exposure_policy='public_safe' OR owner_agent_instance_id=?)
            UNION
            SELECT alias.capability_id
            FROM capability_aliases AS alias
            JOIN capabilities AS capability
              ON capability.capability_id=alias.capability_id
            WHERE alias.normalized_alias=?
              AND (capability.exposure_policy='public_safe'
                   OR capability.owner_agent_instance_id=?)
            ORDER BY capability_id
            """,
            (query, private_agent, query, private_agent),
        ).fetchall()
        return [
            self.capability(
                row["capability_id"],
                agent_instance_id=agent_instance_id,
                host_session_id=host_session_id,
                _private_agent_instance_id=(
                    private_agent if _private_agent_instance_id is not None else None
                ),
            )
            for row in rows
        ]
