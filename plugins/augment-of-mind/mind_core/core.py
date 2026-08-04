"""Persona-neutral MIND Core façade."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .constants import (
    MAX_CONFORMANCE_LEVEL,
    PROTOCOL_VERSION,
    RUNTIME_VERSION,
    SCHEMA_VERSION,
)
from .errors import ConflictError, NotFoundError, ValidationError
from .estate import CapabilityEstate
from .handshake import HostRegistry
from .mounts import MountCatalog
from .receipts import ReceiptLedger
from .reminders import AssociativeReminders
from .store import CoreStore
from .util import (
    new_id,
    record_binding_hash,
    require_identifier,
    require_sha256,
    timestamp,
)


class MindCore:
    """One local metadata authority; never a model, persona, or owner-store."""

    def __init__(self, database: str | Path):
        self._store = CoreStore(database)
        self.receipts = ReceiptLedger(self._store)
        self.hosts = HostRegistry(self._store, self.receipts)
        self.estate = CapabilityEstate(self._store, self.receipts, self.hosts)
        self.mounts = MountCatalog(self._store, self.receipts, self.hosts)
        with self._store.transaction() as connection:
            row = connection.execute(
                "SELECT value FROM core_meta WHERE key='core_instance_id'"
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO core_meta(key,value,updated_at) VALUES (?,?,?)",
                    ("core_instance_id", new_id("core"), timestamp()),
                )
        self.reminders = AssociativeReminders(
            self._store, self.receipts, self.hosts, self.estate
        )

    def close(self) -> None:
        self._store.close()

    def __enter__(self) -> "MindCore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def status(self) -> dict[str, Any]:
        connection = self._store.connection
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "agent_instances",
                "host_sessions",
                "capabilities",
                "distributions",
                "lifecycle_observations",
                "mounts",
                "mount_observations",
                "capability_cards",
                "capability_card_views",
                "capability_relations",
                "associative_index_snapshots",
                "associative_view_vectors",
                "associative_snapshot_activations",
                "session_query_capabilities",
                "receipts",
            )
        }
        core_id = connection.execute(
            "SELECT value FROM core_meta WHERE key='core_instance_id'"
        ).fetchone()[0]
        return {
            "runtime_version": RUNTIME_VERSION,
            "schema_version": SCHEMA_VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "core_instance_id": core_id,
            "maximum_host_conformance": MAX_CONFORMANCE_LEVEL,
            "persona_required": False,
            "persona_inference": False,
            "mode": "phase2_associative_disclosure_h0",
            "implemented": [
                "agent_instance_isolation",
                "host_handshake_metadata",
                "event_coverage_metadata",
                "capability_estate_metadata",
                "mount_catalog_metadata",
                "append_only_receipts",
                "stdio_protocol_skeleton",
                "versioned_capability_cards",
                "exact_vector_radius_neighborhoods",
                "exhaustive_lexical_membership",
                "typed_associative_relations",
                "field_bound_card_expansion",
                "canonical_and_compact_reminder_fields",
            ],
            "not_implemented": [
                "event_delivery",
                "automatic_activation",
                "automatic_pre_sampling_reminder_delivery",
                "embedding_generation_or_model_installation",
                "vector_acceleration_extension",
                "owner_store_reads_or_writes",
                "legacy_data_migration",
                "action_admission_or_dispatch_gate",
                "capsule_export_or_import",
            ],
            "counts": counts,
            "sqlite": self._store.integrity(),
        }

    def query_status(self) -> dict[str, Any]:
        """Return H0 runtime identity without unscoped private-sensitive counts."""

        result = self.status()
        result.pop("counts", None)
        sqlite_status = result["sqlite"]
        result["sqlite"] = {
            "integrity_ok": sqlite_status["integrity_check"] == "ok",
            "foreign_key_ok": not sqlite_status["foreign_key_failures"],
            "foreign_keys_enabled": sqlite_status["foreign_keys_enabled"],
            "journal_mode": sqlite_status["journal_mode"],
        }
        return result

    def bootstrap(self, manifest: dict[str, Any]) -> dict[str, Any]:
        self._validate_bootstrap_manifest(manifest)
        with self._store.transaction() as connection:
            activation_exists = connection.execute(
                "SELECT 1 FROM associative_snapshot_activations LIMIT 1"
            ).fetchone() is not None
            capability_ids_before = {
                row["capability_id"]
                for row in connection.execute(
                    "SELECT capability_id FROM capabilities"
                ).fetchall()
            }
            self._ingest_validated_bootstrap(manifest, connection)
            if activation_exists:
                capability_ids_after = {
                    row["capability_id"]
                    for row in connection.execute(
                        "SELECT capability_id FROM capabilities"
                    ).fetchall()
                }
                if capability_ids_after != capability_ids_before:
                    raise ValidationError(
                        "bootstrap cannot expand the capability estate after associative "
                        "activation; use activate_estate_generation"
                    )
        return self.status()

    def activate_estate_generation(
        self,
        bootstrap_manifest: dict[str, Any],
        associative_index_manifest: dict[str, Any],
    ) -> dict[str, Any]:
        """Atomically admit estate records and activate their complete index."""

        self._validate_bootstrap_manifest(bootstrap_manifest)
        validated_index = self.reminders._validate_index_manifest(
            associative_index_manifest
        )
        with self._store.transaction() as connection:
            self._ingest_validated_bootstrap(
                bootstrap_manifest, connection, generation=True
            )
            return self.reminders._ingest_validated_index(
                connection=connection,
                server_observed_at=timestamp(),
                **validated_index,
            )

    def activation_operator_report(
        self,
        *,
        submitted_snapshot_id: str,
        submitted_snapshot_digest: str,
        submitted_embedding_profile_id: str,
        submitted_activation_id: str,
        submitted_prior_snapshot_id: str | None,
    ) -> dict[str, Any]:
        """Return a durable, content-free receipt for one submitted activation."""

        submitted_snapshot_id = require_identifier(
            submitted_snapshot_id, "submitted_snapshot_id"
        )
        submitted_snapshot_digest = require_sha256(
            submitted_snapshot_digest, "submitted_snapshot_digest"
        )
        submitted_embedding_profile_id = require_identifier(
            submitted_embedding_profile_id, "submitted_embedding_profile_id"
        )
        submitted_activation_id = require_identifier(
            submitted_activation_id, "submitted_activation_id"
        )
        if submitted_prior_snapshot_id is not None:
            submitted_prior_snapshot_id = require_identifier(
                submitted_prior_snapshot_id, "submitted_prior_snapshot_id"
            )

        connection = self._store.connection
        submitted = connection.execute(
            """
            SELECT snapshot.associative_index_snapshot_id,snapshot.snapshot_digest,
                   snapshot.embedding_profile_id,profile.qualification_state,
                   profile.qualification_digest,activation.associative_snapshot_activation_id,
                   activation.prior_associative_index_snapshot_id,
                   activation.activated_at,activation.activation_receipt_id
            FROM associative_index_snapshots AS snapshot
            JOIN embedding_profiles AS profile
              ON profile.embedding_profile_id=snapshot.embedding_profile_id
            JOIN associative_snapshot_activations AS activation
              ON activation.associative_index_snapshot_id=snapshot.associative_index_snapshot_id
            WHERE snapshot.associative_index_snapshot_id=?
            """,
            (submitted_snapshot_id,),
        ).fetchone()
        if submitted is None:
            raise NotFoundError("submitted associative snapshot was not activated")
        submitted = dict(submitted)
        matches_submission = (
            submitted["snapshot_digest"] == submitted_snapshot_digest
            and submitted["embedding_profile_id"] == submitted_embedding_profile_id
            and submitted["associative_snapshot_activation_id"] == submitted_activation_id
            and submitted["prior_associative_index_snapshot_id"]
            == submitted_prior_snapshot_id
        )

        activation_record = {
            "associative_snapshot_activation_id": submitted[
                "associative_snapshot_activation_id"
            ],
            "associative_index_snapshot_id": submitted[
                "associative_index_snapshot_id"
            ],
            "prior_associative_index_snapshot_id": submitted[
                "prior_associative_index_snapshot_id"
            ],
            "activated_at": submitted["activated_at"],
            "activation_receipt_id": submitted["activation_receipt_id"],
        }
        receipt = connection.execute(
            """
            SELECT receipt_id,receipt_type,subject_kind,subject_id,evidence_state,payload_hash
            FROM receipts WHERE receipt_id=?
            """,
            (submitted["activation_receipt_id"],),
        ).fetchone()
        if receipt is None:
            raise ConflictError("activation receipt is absent")
        receipt = dict(receipt)
        receipt_binding_valid = (
            receipt["receipt_type"] == "reminder.snapshot_activation"
            and receipt["subject_kind"] == "associative_index_snapshot"
            and receipt["subject_id"] == submitted_snapshot_id
            and receipt["evidence_state"] == "observed"
            and receipt["payload_hash"] == record_binding_hash(activation_record)
        )

        snapshot_counts = {
            "capabilities": connection.execute(
                "SELECT COUNT(*) FROM capabilities"
            ).fetchone()[0],
            "cards": connection.execute(
                "SELECT COUNT(*) FROM associative_snapshot_cards "
                "WHERE associative_index_snapshot_id=?",
                (submitted_snapshot_id,),
            ).fetchone()[0],
            "views": connection.execute(
                """
                SELECT COUNT(*) FROM capability_card_views AS view
                JOIN associative_snapshot_cards AS membership
                  ON membership.capability_card_id=view.capability_card_id
                WHERE membership.associative_index_snapshot_id=?
                """,
                (submitted_snapshot_id,),
            ).fetchone()[0],
            "vectors": connection.execute(
                "SELECT COUNT(*) FROM associative_view_vectors "
                "WHERE associative_index_snapshot_id=?",
                (submitted_snapshot_id,),
            ).fetchone()[0],
            "relations": connection.execute(
                "SELECT COUNT(*) FROM associative_snapshot_relations "
                "WHERE associative_index_snapshot_id=?",
                (submitted_snapshot_id,),
            ).fetchone()[0],
            "distinct_clusters": connection.execute(
                """
                SELECT COUNT(DISTINCT card.cluster_id)
                FROM associative_snapshot_cards AS membership
                JOIN capability_cards AS card
                  ON card.capability_card_id=membership.capability_card_id
                WHERE membership.associative_index_snapshot_id=?
                """,
                (submitted_snapshot_id,),
            ).fetchone()[0],
            "lexical_projections": connection.execute(
                "SELECT COUNT(*) FROM capability_card_fts "
                "WHERE associative_index_snapshot_id=?",
                (submitted_snapshot_id,),
            ).fetchone()[0],
        }
        active = self.reminders.active_snapshot_binding()
        current = self.reminders._snapshot_status(submitted_snapshot_id)["current"]
        active_matches_submission = (
            active["associative_index_snapshot_id"] == submitted_snapshot_id
            and active["snapshot_digest"] == submitted_snapshot_digest
            and active["embedding_profile_id"] == submitted_embedding_profile_id
        )
        integrity = self._store.integrity()
        return {
            "submitted": {
                "associative_index_snapshot_id": submitted_snapshot_id,
                "snapshot_digest": submitted_snapshot_digest,
                "embedding_profile_id": submitted_embedding_profile_id,
                "associative_snapshot_activation_id": submitted_activation_id,
                "prior_associative_index_snapshot_id": submitted_prior_snapshot_id,
            },
            "active": active,
            "embedding_profile": {
                "embedding_profile_id": submitted["embedding_profile_id"],
                "qualification_state": submitted["qualification_state"],
                "qualification_digest": submitted["qualification_digest"],
            },
            "activation": {
                "associative_snapshot_activation_id": submitted[
                    "associative_snapshot_activation_id"
                ],
                "prior_associative_index_snapshot_id": submitted[
                    "prior_associative_index_snapshot_id"
                ],
                "activated_at": submitted["activated_at"],
            },
            "current": current,
            "matches_submission": matches_submission,
            "active_matches_submission": active_matches_submission,
            "counts": snapshot_counts,
            "activation_receipt": {
                "receipt_id": submitted["activation_receipt_id"],
                "binding_valid": receipt_binding_valid,
                "receipt_type": receipt["receipt_type"],
                "subject_kind": receipt["subject_kind"],
                "subject_id": receipt["subject_id"],
                "evidence_state": receipt["evidence_state"],
            },
            "sqlite": {
                "integrity_check": integrity["integrity_check"],
                "foreign_key_violation_count": len(integrity["foreign_key_failures"]),
                "foreign_keys_enabled": integrity["foreign_keys_enabled"],
            },
        }

    @staticmethod
    def _validate_bootstrap_manifest(manifest: dict[str, Any]) -> None:
        if manifest.get("format") != "mind-core-bootstrap/v1":
            raise ValidationError("unsupported bootstrap manifest format")
        allowed = {
            "format",
            "sources",
            "products",
            "providers",
            "capabilities",
            "distributions",
            "receipts",
            "lifecycle_observations",
            "mounts",
        }
        unknown = sorted(set(manifest) - allowed)
        if unknown:
            raise ValidationError(f"unsupported bootstrap fields: {','.join(unknown)}")

    def _ingest_validated_bootstrap(
        self,
        manifest: dict[str, Any],
        connection: sqlite3.Connection,
        *,
        generation: bool = False,
    ) -> None:
        self.estate.ingest_sources(manifest.get("sources", []), connection)
        self.estate.ingest_products(manifest.get("products", []), connection)
        self.estate.ingest_providers(manifest.get("providers", []), connection)
        capability_records = manifest.get("capabilities", [])
        if generation:
            self.estate._ingest_generation_capabilities(
                capability_records, connection
            )
        else:
            self.estate.ingest_capabilities(capability_records, connection)
        self.estate.ingest_distributions(manifest.get("distributions", []), connection)
        for item in manifest.get("receipts", []):
            self.receipts.append(
                item,
                parents=item.get("parents", []),
                connection=connection,
            )
        self.estate.ingest_lifecycle_observations(
            manifest.get("lifecycle_observations", []), connection
        )
        self.mounts.ingest_mounts(manifest.get("mounts", []), connection)

    def schema_tables(self) -> list[str]:
        return [
            row["name"]
            for row in self._store.connection.execute(
                "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            ).fetchall()
        ]
