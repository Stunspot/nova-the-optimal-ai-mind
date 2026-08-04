"""Agent-instance, host-session, and H0 coverage observations."""

from __future__ import annotations

import sqlite3
from typing import Any

from .constants import (
    CONFORMANCE_LEVELS,
    COVERAGE_STATES,
    PROTOCOL_VERSION,
    TIMING_STATES,
)
from .errors import ConflictError, NotFoundError, ValidationError
from .receipts import ReceiptLedger
from .store import CoreStore, insert_exact
from .util import (
    canonical_json,
    is_fresh,
    new_id,
    optional_text,
    parse_timestamp,
    require_bounded_interval,
    require_identifier,
    require_interval,
    require_sha256,
    require_text,
    sha256_text,
    timestamp,
)


class HostRegistry:
    def __init__(self, store: CoreStore, receipts: ReceiptLedger):
        self._store = store
        self.receipts = receipts

    def handshake(self, record: dict[str, Any]) -> dict[str, Any]:
        observed_at, expires_at = require_interval(
            record.get("observed_at"), record.get("expires_at")
        )
        catalog_expiry = timestamp(
            parse_timestamp(
                record.get("catalog_snapshot_expires_at"),
                "catalog_snapshot_expires_at",
            )
        )
        if catalog_expiry <= observed_at:
            raise ValidationError("catalog_snapshot_expires_at must be after observed_at")
        if catalog_expiry > expires_at:
            raise ValidationError(
                "catalog_snapshot_expires_at must not outlive the host session"
            )
        declared = require_identifier(
            record.get("declared_conformance_level", "H0"),
            "declared_conformance_level",
        )
        if declared not in CONFORMANCE_LEVELS:
            raise ValidationError(f"unsupported conformance level: {declared}")

        protocol_version = require_text(
            record.get("protocol_version"), "protocol_version", maximum=128
        )
        if protocol_version != PROTOCOL_VERSION:
            raise ValidationError(
                f"unsupported protocol_version: {protocol_version}"
            )

        agent_candidate = {
            "agent_instance_id": require_identifier(
                record.get("agent_instance_id"), "agent_instance_id"
            ),
            "persona_id": (
                require_identifier(record["persona_id"], "persona_id")
                if record.get("persona_id") is not None
                else None
            ),
            "profile_id": (
                require_identifier(record["profile_id"], "profile_id")
                if record.get("profile_id") is not None
                else None
            ),
            "created_at": observed_at,
            "retired_at": None,
        }
        session = {
            "host_session_id": require_identifier(
                record.get("host_session_id"), "host_session_id"
            ),
            "host_id": require_identifier(record.get("host_id"), "host_id"),
            "external_session_id": require_identifier(
                record.get("external_session_id"), "external_session_id"
            ),
            "session_epoch": record.get("session_epoch"),
            "agent_instance_id": agent_candidate["agent_instance_id"],
            "adapter_id": require_identifier(record.get("adapter_id"), "adapter_id"),
            "adapter_version": require_text(
                record.get("adapter_version"), "adapter_version", maximum=128
            ),
            "protocol_version": protocol_version,
            "declared_conformance_level": declared,
            "evidence_conformance_level": "H0",
            "catalog_snapshot_hash": require_sha256(
                record.get("catalog_snapshot_hash"), "catalog_snapshot_hash"
            ),
            "catalog_snapshot_expires_at": catalog_expiry,
            "permission_observation_hash": require_sha256(
                record.get("permission_observation_hash"), "permission_observation_hash"
            ),
            "authentication_observation_hash": require_sha256(
                record.get("authentication_observation_hash"),
                "authentication_observation_hash",
            ),
            "observed_at": observed_at,
            "expires_at": expires_at,
        }
        if not isinstance(session["session_epoch"], int) or session["session_epoch"] < 0:
            raise ValidationError("session_epoch must be a non-negative integer")

        with self._store.transaction() as connection:
            existing_agent = connection.execute(
                "SELECT * FROM agent_instances WHERE agent_instance_id=?",
                (agent_candidate["agent_instance_id"],),
            ).fetchone()
            if existing_agent is None:
                insert_exact(
                    connection,
                    "agent_instances",
                    agent_candidate,
                    ("agent_instance_id",),
                )
                agent = agent_candidate
            else:
                agent = dict(existing_agent)
                if (
                    agent["persona_id"] != agent_candidate["persona_id"]
                    or agent["profile_id"] != agent_candidate["profile_id"]
                ):
                    raise ConflictError(
                        "persona_id and profile_id are immutable for an agent instance"
                    )
                if agent["retired_at"] is not None:
                    raise ConflictError("retired agent instance cannot open a host session")

            competing_session = connection.execute(
                "SELECT host_session_id FROM host_sessions "
                "WHERE host_id=? AND external_session_id=? AND session_epoch=? "
                "AND agent_instance_id=?",
                (
                    session["host_id"],
                    session["external_session_id"],
                    session["session_epoch"],
                    session["agent_instance_id"],
                ),
            ).fetchone()
            if (
                competing_session is not None
                and competing_session["host_session_id"] != session["host_session_id"]
            ):
                raise ConflictError(
                    "host/session/epoch identity is already bound to another host_session_id"
                )
            insert_exact(connection, "host_sessions", session, ("host_session_id",))
            payload_hash = sha256_text(
                canonical_json({"agent": agent, "session": session})
            )
            receipt = self.receipts.append(
                {
                    "receipt_id": record.get("receipt_id", new_id("receipt")),
                    "idempotency_key": record.get(
                        "idempotency_key", f"handshake:{session['host_session_id']}"
                    ),
                    "receipt_type": "host.handshake",
                    "subject_kind": "host_session",
                    "subject_id": session["host_session_id"],
                    "agent_instance_id": agent["agent_instance_id"],
                    "host_session_id": session["host_session_id"],
                    "evidence_state": "reported",
                    "claimed_boundary": (
                        "Adapter-supplied host metadata was durably recorded by Core. "
                        "Authentication, permission, and catalog claims remain reported. "
                        "MIND Core evidence remains H0; "
                        "automatic delivery, activation, result interception, and dispatch gating are unproved."
                    ),
                    "observed_at": observed_at,
                    "expires_at": expires_at,
                    "redaction_class": "metadata_only",
                    "payload_hash": payload_hash,
                },
                connection=connection,
            )
        return {"session": self.session(session["host_session_id"], agent["agent_instance_id"]), "receipt": receipt}

    def session(
        self,
        host_session_id: str,
        agent_instance_id: str,
        *,
        require_fresh: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(require_fresh, bool):
            raise ValidationError("require_fresh must be boolean")
        host_session_id = require_identifier(host_session_id, "host_session_id")
        agent_instance_id = require_identifier(agent_instance_id, "agent_instance_id")
        row = self._store.connection.execute(
            "SELECT * FROM host_sessions WHERE host_session_id=? AND agent_instance_id=?",
            (host_session_id, agent_instance_id),
        ).fetchone()
        if row is None:
            raise NotFoundError("host session not found in the requested agent scope")
        result = dict(row)
        result["fresh"] = is_fresh(result["expires_at"])
        result["catalog_snapshot_fresh"] = result["fresh"] and is_fresh(
            result["catalog_snapshot_expires_at"]
        )
        result["permission_observation_fresh"] = result["fresh"]
        result["authentication_observation_fresh"] = result["fresh"]
        if require_fresh and not result["fresh"]:
            raise NotFoundError("host session is expired")
        return result

    def record_coverage(self, record: dict[str, Any]) -> dict[str, Any]:
        session = self.session(
            record.get("host_session_id"), record.get("agent_instance_id"), require_fresh=False
        )
        observed_at, expires_at = require_interval(
            record.get("observed_at"), record.get("expires_at")
        )
        require_bounded_interval(
            observed_at,
            expires_at,
            session["observed_at"],
            session["expires_at"],
            "event_coverage",
        )
        declared = require_identifier(
            record.get("declared_coverage_state"), "declared_coverage_state"
        )
        if declared not in COVERAGE_STATES:
            raise ValidationError(f"unsupported coverage state: {declared}")
        effective = "unobservable" if declared == "unobservable" else "advisory_only"
        timing = require_identifier(record.get("timing"), "timing")
        if timing not in TIMING_STATES:
            raise ValidationError(f"unsupported timing: {timing}")
        coverage = {
            "coverage_id": require_identifier(
                record.get("coverage_id", new_id("coverage")), "coverage_id"
            ),
            "host_session_id": session["host_session_id"],
            "agent_instance_id": session["agent_instance_id"],
            "event_kind": require_identifier(record.get("event_kind"), "event_kind"),
            "action_class": (
                require_identifier(record["action_class"], "action_class")
                if record.get("action_class")
                else ""
            ),
            "source_observer": require_text(
                record.get("source_observer"), "source_observer", maximum=512
            ),
            "timing": timing,
            "delivery_durability": require_text(
                record.get("delivery_durability"), "delivery_durability", maximum=512
            ),
            "correlation_method": require_text(
                record.get("correlation_method"), "correlation_method", maximum=512
            ),
            "declared_coverage_state": declared,
            "effective_coverage_state": effective,
            "evidence_conformance_level": "H0",
            "observed_at": observed_at,
            "expires_at": expires_at,
            "source_receipt_ref": optional_text(
                record.get("source_receipt_ref"), "source_receipt_ref", maximum=512
            ),
        }
        payload_hash = sha256_text(canonical_json(coverage))
        with self._store.transaction() as connection:
            insert_exact(connection, "event_coverage", coverage, ("coverage_id",))
            receipt = self.receipts.append(
                {
                    "idempotency_key": record.get(
                        "idempotency_key", f"coverage:{coverage['coverage_id']}"
                    ),
                    "receipt_type": "event.coverage",
                    "subject_kind": "event_coverage",
                    "subject_id": coverage["coverage_id"],
                    "agent_instance_id": coverage["agent_instance_id"],
                    "host_session_id": coverage["host_session_id"],
                    "evidence_state": "reported",
                    "claimed_boundary": (
                        f"Adapter declared {declared}; MIND Core records effective coverage as {effective} "
                        "and cannot establish H1, H2, or H3."
                    ),
                    "observed_at": observed_at,
                    "expires_at": expires_at,
                    "redaction_class": "metadata_only",
                    "payload_hash": payload_hash,
                },
                connection=connection,
            )
        return {"coverage": coverage, "receipt": receipt}

    def coverage(self, host_session_id: str, agent_instance_id: str) -> list[dict[str, Any]]:
        self.session(host_session_id, agent_instance_id, require_fresh=False)
        return [
            {**dict(row), "fresh": is_fresh(row["expires_at"])}
            for row in self._store.connection.execute(
                "SELECT * FROM event_coverage WHERE host_session_id=? AND agent_instance_id=? "
                "ORDER BY event_kind, action_class, observed_at DESC",
                (host_session_id, agent_instance_id),
            ).fetchall()
        ]
