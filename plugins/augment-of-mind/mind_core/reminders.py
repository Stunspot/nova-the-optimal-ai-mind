"""Persona-neutral associative reminder fields over the MIND capability estate."""

from __future__ import annotations

import hashlib
import secrets
from collections import defaultdict
from typing import Any, Iterable

from .association_math import (
    LEXICAL_CUE_MEMBERSHIP_CONTRACT,
    LEXICAL_PROFILE_ID,
    LEXICAL_UNICODE_TOKEN_GRAMMAR,
    MAX_LEXICAL_HINT_CHARACTERS,
    coerce_float32_vector,
    contains_contiguous_tokens,
    exact_cosine_distance,
    lexical_tokens,
    pack_float32_vector,
    unpack_float32_vector,
    within_radius,
)
from .constants import CAPABILITY_EXPOSURE_POLICIES
from .estate import CapabilityEstate
from .errors import ConflictError, NotFoundError, ValidationError
from .field_tokens import sign_visibility_token, verify_visibility_token
from .handshake import HostRegistry
from .receipts import ReceiptLedger
from .store import CoreStore, insert_exact
from .util import (
    canonical_json,
    is_fresh,
    new_id,
    parse_timestamp,
    record_binding_hash,
    require_bounded_interval,
    require_identifier,
    require_sha256,
    require_text,
    sha256_text,
    timestamp,
)


VIEW_KINDS = frozenset(
    {
        "transformation",
        "situation",
        "positive_cue",
        "error_or_correction",
        "negative_boundary",
        "example",
    }
)
RELATION_KINDS = frozenset(
    {"bridges_to", "complements", "requires", "false_friend_of"}
)
SESSION_EXPOSURE_SCOPES = frozenset(
    {"public_only", "public_and_agent_private"}
)
QUALIFICATION_STATES = frozenset(
    {"unqualified", "test_only", "behavior_qualified", "fresh_host_qualified"}
)
VECTOR_COVERAGE_STATES = frozenset({"complete", "unavailable"})

MAX_ANCHORS = 16
MAX_HINTS_PER_ANCHOR = 16
MAX_TOTAL_HINTS = 64

FIELD_HEADER = (
    "MIND · ARM'S REACH\n"
    "Notice the nearby handles; treat proximity as memory, not verdict. "
    "Open only the transformation the work actually needs."
)


def _exact_fields(
    value: object,
    *,
    required: frozenset[str],
    optional: frozenset[str] = frozenset(),
    field: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{field} must be an object")
    missing = required - set(value)
    unknown = set(value) - required - optional
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append("missing=" + ",".join(sorted(missing)))
        if unknown:
            details.append("unsupported=" + ",".join(sorted(unknown)))
        raise ValidationError(f"invalid {field}: " + "; ".join(details))
    return value


def _require_positive_integer(value: object, field: str, *, maximum: int) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
        or value > maximum
    ):
        raise ValidationError(f"{field} must be an integer between 1 and {maximum}")
    return value


def _require_nonnegative_integer(value: object, field: str, *, maximum: int) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        or value > maximum
    ):
        raise ValidationError(f"{field} must be an integer between 0 and {maximum}")
    return value


def _record_digest(record: dict[str, Any], digest_field: str) -> str:
    return sha256_text(
        canonical_json(
            {key: value for key, value in record.items() if key != digest_field}
        )
    )


def _require_record_digest(
    record: dict[str, Any], digest_field: str, *, field: str
) -> None:
    expected = require_sha256(record.get(digest_field), f"{field}.{digest_field}")
    if _record_digest(record, digest_field) != expected:
        raise ValidationError(f"{field}.{digest_field} does not bind its record")


def _sorted_associations(values: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    deduplicated = {canonical_json(value): value for value in values}
    return [deduplicated[key] for key in sorted(deduplicated)]


class AssociativeReminders:
    """Administer immutable reminder projections and answer side-effect-free fields."""

    def __init__(
        self,
        store: CoreStore,
        receipts: ReceiptLedger,
        hosts: HostRegistry,
        estate: CapabilityEstate,
    ) -> None:
        self._store = store
        self.receipts = receipts
        self.hosts = hosts
        self.estate = estate
        self._ensure_signing_key()

    def _ensure_signing_key(self) -> None:
        with self._store.transaction() as connection:
            row = connection.execute(
                "SELECT value FROM core_meta WHERE key='reminder_visibility_hmac_key'"
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO core_meta(key,value,updated_at) VALUES (?,?,?)",
                    (
                        "reminder_visibility_hmac_key",
                        secrets.token_hex(32),
                        timestamp(),
                    ),
                )

    def _signing_key(self) -> bytes:
        row = self._store.connection.execute(
            "SELECT value FROM core_meta WHERE key='reminder_visibility_hmac_key'"
        ).fetchone()
        if row is None:
            raise ConflictError("reminder visibility key is unavailable")
        try:
            key = bytes.fromhex(row["value"])
        except ValueError as exc:
            raise ConflictError("reminder visibility key is invalid") from exc
        if len(key) != 32:
            raise ConflictError("reminder visibility key is invalid")
        return key

    def issue_session_capability(
        self,
        agent_instance_id: str,
        host_session_id: str,
        *,
        exposure_scope: str = "public_only",
        expires_at: str | None = None,
    ) -> dict[str, Any]:
        """Issue one raw query capability; Core persists only its digest."""

        if exposure_scope not in SESSION_EXPOSURE_SCOPES:
            raise ValidationError(f"unsupported exposure_scope: {exposure_scope}")
        session = self.hosts.session(
            host_session_id, agent_instance_id, require_fresh=True
        )
        issued_at = timestamp()
        expiry = (
            timestamp(parse_timestamp(expires_at, "expires_at"))
            if expires_at is not None
            else session["expires_at"]
        )
        require_bounded_interval(
            issued_at,
            expiry,
            session["observed_at"],
            session["expires_at"],
            "session_query_capability",
        )
        raw_token = secrets.token_urlsafe(32)
        token_hash = sha256_text(raw_token)
        record = {
            "token_hash": token_hash,
            "agent_instance_id": session["agent_instance_id"],
            "host_session_id": session["host_session_id"],
            "session_epoch": session["session_epoch"],
            "exposure_scope": exposure_scope,
            "issued_at": issued_at,
            "expires_at": expiry,
            "issuance_receipt_id": new_id("receipt"),
        }
        with self._store.transaction() as connection:
            self.receipts.append(
                {
                    "receipt_id": record["issuance_receipt_id"],
                    "idempotency_key": f"reminder-session-capability:{token_hash}",
                    "receipt_type": "reminder.session_capability",
                    "subject_kind": "session_query_capability",
                    "subject_id": token_hash,
                    "agent_instance_id": record["agent_instance_id"],
                    "host_session_id": record["host_session_id"],
                    "evidence_state": "observed",
                    "claimed_boundary": (
                        "Core issued one scoped reminder-query capability and stored "
                        "only its SHA-256 digest. This does not establish host delivery."
                    ),
                    "observed_at": issued_at,
                    "expires_at": expiry,
                    "redaction_class": "secret_digest_only",
                    "payload_hash": record_binding_hash(record),
                },
                connection=connection,
            )
            insert_exact(
                connection,
                "session_query_capabilities",
                record,
                ("token_hash",),
            )
        return {
            "session_capability": raw_token,
            "agent_instance_id": record["agent_instance_id"],
            "host_session_id": record["host_session_id"],
            "session_epoch": record["session_epoch"],
            "exposure_scope": exposure_scope,
            "expires_at": expiry,
            "claim_boundary": (
                "The raw capability is returned once. Possession authorizes only "
                "the bound H0 reminder-query scope until expiry or revocation."
            ),
        }

    def revoke_session_capability(
        self, session_capability: str
    ) -> dict[str, Any]:
        binding = self._bound_scope(session_capability, allow_revoked=True)
        existing = self._store.connection.execute(
            "SELECT * FROM session_capability_revocations WHERE token_hash=?",
            (binding["token_hash"],),
        ).fetchone()
        if existing is not None:
            return dict(existing)
        revoked_at = timestamp()
        record = {
            "session_capability_revocation_id": new_id("query-cap-revocation"),
            "token_hash": binding["token_hash"],
            "revoked_at": revoked_at,
            "revocation_receipt_id": new_id("receipt"),
        }
        with self._store.transaction() as connection:
            self.receipts.append(
                {
                    "receipt_id": record["revocation_receipt_id"],
                    "idempotency_key": (
                        f"reminder-session-capability-revoke:{binding['token_hash']}"
                    ),
                    "receipt_type": "reminder.session_capability_revoked",
                    "subject_kind": "session_query_capability",
                    "subject_id": binding["token_hash"],
                    "agent_instance_id": binding["agent_instance_id"],
                    "host_session_id": binding["host_session_id"],
                    "evidence_state": "observed",
                    "claimed_boundary": (
                        "Core recorded revocation of the scoped reminder-query capability."
                    ),
                    "observed_at": revoked_at,
                    "expires_at": binding["expires_at"],
                    "redaction_class": "secret_digest_only",
                    "payload_hash": record_binding_hash(record),
                },
                connection=connection,
            )
            insert_exact(
                connection,
                "session_capability_revocations",
                record,
                ("session_capability_revocation_id",),
            )
        return record

    def _bound_scope(
        self, session_capability: object, *, allow_revoked: bool = False
    ) -> dict[str, Any]:
        if not isinstance(session_capability, str) or len(session_capability) > 1024:
            raise NotFoundError("reminder session capability is unavailable")
        token_hash = sha256_text(session_capability)
        row = self._store.connection.execute(
            "SELECT * FROM session_query_capabilities WHERE token_hash=?",
            (token_hash,),
        ).fetchone()
        if row is None:
            raise NotFoundError("reminder session capability is unavailable")
        binding = dict(row)
        revoked = self._store.connection.execute(
            "SELECT 1 FROM session_capability_revocations WHERE token_hash=?",
            (token_hash,),
        ).fetchone()
        if revoked is not None and not allow_revoked:
            raise NotFoundError("reminder session capability is unavailable")
        if not is_fresh(binding["expires_at"]):
            raise NotFoundError("reminder session capability is unavailable")
        try:
            session = self.hosts.session(
                binding["host_session_id"],
                binding["agent_instance_id"],
                require_fresh=True,
            )
        except NotFoundError:
            raise NotFoundError("reminder session capability is unavailable") from None
        if session["session_epoch"] != binding["session_epoch"]:
            raise NotFoundError("reminder session capability is unavailable")
        return binding

    def estate_capability(
        self,
        capability_id: str,
        session_capability: str | None = None,
    ) -> dict[str, Any]:
        binding = (
            self._bound_scope(session_capability)
            if session_capability is not None
            else None
        )
        return self.estate.capability(
            capability_id,
            agent_instance_id=(binding["agent_instance_id"] if binding else None),
            host_session_id=(binding["host_session_id"] if binding else None),
            _private_agent_instance_id=(
                binding["agent_instance_id"]
                if binding
                and binding["exposure_scope"] == "public_and_agent_private"
                else None
            ),
        )

    def estate_resolve(
        self,
        handle_or_alias: str,
        session_capability: str | None = None,
    ) -> list[dict[str, Any]]:
        binding = (
            self._bound_scope(session_capability)
            if session_capability is not None
            else None
        )
        return self.estate.resolve(
            handle_or_alias,
            agent_instance_id=(binding["agent_instance_id"] if binding else None),
            host_session_id=(binding["host_session_id"] if binding else None),
            _private_agent_instance_id=(
                binding["agent_instance_id"]
                if binding
                and binding["exposure_scope"] == "public_and_agent_private"
                else None
            ),
        )

    def ingest_index(self, manifest: dict[str, Any]) -> dict[str, Any]:
        """Transactionally ingest one complete immutable associative generation."""

        validated = self._validate_index_manifest(manifest)
        with self._store.transaction() as connection:
            return self._ingest_validated_index(
                connection=connection,
                server_observed_at=timestamp(),
                **validated,
            )

    def active_snapshot_binding(self) -> dict[str, Any]:
        """Return the latest activated snapshot's public embedding binding."""

        row = self._store.connection.execute(
            "SELECT snapshot.associative_index_snapshot_id,snapshot.snapshot_digest,"
            "snapshot.embedding_profile_id,profile.model_id "
            "FROM associative_snapshot_activations AS activation "
            "JOIN associative_index_snapshots AS snapshot "
            "ON snapshot.associative_index_snapshot_id="
            "activation.associative_index_snapshot_id "
            "JOIN embedding_profiles AS profile "
            "ON profile.embedding_profile_id=snapshot.embedding_profile_id "
            "ORDER BY activation.activated_at DESC,"
            "activation.associative_snapshot_activation_id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            raise NotFoundError("no active associative snapshot")
        result = dict(row)
        result["current"] = self._snapshot_status(
            result["associative_index_snapshot_id"]
        )["current"]
        return result

    def _validate_index_manifest(self, manifest: dict[str, Any]) -> dict[str, Any]:
        """Normalize a manifest before its estate-bound writer transaction."""

        manifest = _exact_fields(
            manifest,
            required=frozenset(
                {
                    "format",
                    "lexical_profile",
                    "embedding_profile",
                    "clusters",
                    "cards",
                    "relations",
                    "snapshot",
                    "vectors",
                    "activation",
                }
            ),
            field="associative index manifest",
        )
        if manifest.get("format") != "mind-associative-index/v1":
            raise ValidationError("unsupported associative index manifest format")

        lexical_profile = self._validate_lexical_profile(manifest["lexical_profile"])
        embedding_profile = self._validate_embedding_profile(
            manifest["embedding_profile"]
        )
        clusters = self._validate_clusters(manifest["clusters"])
        cards, views = self._validate_cards(manifest["cards"])
        relations = self._validate_relations(manifest["relations"])
        snapshot = self._validate_snapshot(manifest["snapshot"])
        activation = self._validate_activation(manifest["activation"])
        vectors = self._validate_vectors(
            manifest["vectors"], dimensions=embedding_profile["dimensions"]
        )
        return {
            "lexical_profile": lexical_profile,
            "embedding_profile": embedding_profile,
            "clusters": clusters,
            "cards": cards,
            "views": views,
            "relations": relations,
            "snapshot": snapshot,
            "vectors": vectors,
            "activation": activation,
        }

    def _ingest_validated_index(
        self,
        *,
        connection: Any,
        server_observed_at: str,
        lexical_profile: dict[str, Any],
        embedding_profile: dict[str, Any],
        clusters: list[dict[str, Any]],
        cards: list[dict[str, Any]],
        views: list[dict[str, Any]],
        relations: list[dict[str, Any]],
        snapshot: dict[str, Any],
        vectors: list[dict[str, Any]],
        activation: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate, replay, insert, and activate under one writer transaction."""

        if parse_timestamp(activation["activated_at"], "activated_at") > parse_timestamp(
            server_observed_at, "server_observed_at"
        ):
            raise ValidationError(
                "snapshot activation cannot be later than Core observation time"
            )

        existing = connection.execute(
            "SELECT snapshot_digest FROM associative_index_snapshots "
            "WHERE associative_index_snapshot_id=?",
            (snapshot["associative_index_snapshot_id"],),
        ).fetchone()
        if existing is not None:
            if existing["snapshot_digest"] != snapshot["snapshot_digest"]:
                raise ConflictError("associative snapshot identity was reused")
            self._validate_generation_bindings(
                lexical_profile=lexical_profile,
                embedding_profile=embedding_profile,
                clusters=clusters,
                cards=cards,
                views=views,
                relations=relations,
                snapshot=snapshot,
                vectors=vectors,
                activation=activation,
                validate_activation_chain=False,
            )
            self._require_exact_replay(
                lexical_profile=lexical_profile,
                embedding_profile=embedding_profile,
                clusters=clusters,
                cards=cards,
                views=views,
                relations=relations,
                snapshot=snapshot,
                vectors=vectors,
                activation=activation,
            )
            return self._snapshot_status(snapshot["associative_index_snapshot_id"])

        self._validate_generation_bindings(
            lexical_profile=lexical_profile,
            embedding_profile=embedding_profile,
            clusters=clusters,
            cards=cards,
            views=views,
            relations=relations,
            snapshot=snapshot,
            vectors=vectors,
            activation=activation,
        )

        if existing is None:
            insert_exact(
                connection,
                "lexical_profiles",
                lexical_profile,
                ("lexical_profile_id",),
            )
            insert_exact(
                connection,
                "embedding_profiles",
                embedding_profile,
                ("embedding_profile_id",),
            )
            for cluster in clusters:
                insert_exact(connection, "associative_clusters", cluster, ("cluster_id",))
            for card in cards:
                insert_exact(
                    connection,
                    "capability_cards",
                    card,
                    ("capability_card_id",),
                )
            for view in views:
                insert_exact(
                    connection,
                    "capability_card_views",
                    view,
                    ("capability_card_view_id",),
                )
            for relation in relations:
                insert_exact(
                    connection,
                    "capability_relations",
                    relation,
                    ("capability_relation_id",),
                )
            snapshot_record = {
                key: value
                for key, value in snapshot.items()
                if not key.startswith("expected_")
            }
            insert_exact(
                connection,
                "associative_index_snapshots",
                snapshot_record,
                ("associative_index_snapshot_id",),
            )
            for card in cards:
                connection.execute(
                    "INSERT INTO associative_snapshot_cards("
                    "associative_index_snapshot_id,capability_card_id,source_digest,card_digest"
                    ") VALUES (?,?,?,?)",
                    (
                        snapshot["associative_index_snapshot_id"],
                        card["capability_card_id"],
                        card["source_digest"],
                        card["card_digest"],
                    ),
                )
            for relation in relations:
                connection.execute(
                    "INSERT INTO associative_snapshot_relations("
                    "associative_index_snapshot_id,capability_relation_id,relation_digest"
                    ") VALUES (?,?,?)",
                    (
                        snapshot["associative_index_snapshot_id"],
                        relation["capability_relation_id"],
                        relation["relation_digest"],
                    ),
                )
            for vector in vectors:
                connection.execute(
                    "INSERT INTO associative_view_vectors("
                    "associative_index_snapshot_id,capability_card_view_id,dimensions,"
                    "vector_float32_le,vector_digest) VALUES (?,?,?,?,?)",
                    (
                        snapshot["associative_index_snapshot_id"],
                        vector["capability_card_view_id"],
                        vector["dimensions"],
                        vector["vector_float32_le"],
                        vector["vector_digest"],
                    ),
                )
            card_by_id = {card["capability_card_id"]: card for card in cards}
            for view in views:
                card = card_by_id[view["capability_card_id"]]
                handle = connection.execute(
                    "SELECT handle FROM capabilities WHERE capability_id=?",
                    (card["capability_id"],),
                ).fetchone()["handle"]
                connection.execute(
                    "INSERT INTO capability_card_fts("
                    "associative_index_snapshot_id,capability_card_view_id,capability_id,handle,content"
                    ") VALUES (?,?,?,?,?)",
                    (
                        snapshot["associative_index_snapshot_id"],
                        view["capability_card_view_id"],
                        card["capability_id"],
                        handle,
                        view["content"],
                    ),
                )

            activation_record = {
                "associative_snapshot_activation_id": activation[
                    "associative_snapshot_activation_id"
                ],
                "associative_index_snapshot_id": snapshot[
                    "associative_index_snapshot_id"
                ],
                "prior_associative_index_snapshot_id": activation[
                    "prior_associative_index_snapshot_id"
                ],
                "activated_at": activation["activated_at"],
                "activation_receipt_id": new_id("receipt"),
            }
            self.receipts.append(
                {
                    "receipt_id": activation_record["activation_receipt_id"],
                    "idempotency_key": (
                        "associative-snapshot-activate:"
                        + activation_record["associative_snapshot_activation_id"]
                    ),
                    "receipt_type": "reminder.snapshot_activation",
                    "subject_kind": "associative_index_snapshot",
                    "subject_id": snapshot["associative_index_snapshot_id"],
                    "evidence_state": "observed",
                    "claimed_boundary": (
                        "Core validated and committed the supplied card, relation, "
                        "lexical, and vector bytes as one active derived snapshot. "
                        "Semantic retrieval quality is not established by ingestion."
                    ),
                    "observed_at": server_observed_at,
                    "redaction_class": "metadata_only",
                    "payload_hash": record_binding_hash(activation_record),
                },
                connection=connection,
            )
            insert_exact(
                connection,
                "associative_snapshot_activations",
                activation_record,
                ("associative_snapshot_activation_id",),
            )
        status = self._snapshot_status(snapshot["associative_index_snapshot_id"])
        if not status["current"]:
            raise ConflictError(
                "snapshot activation did not produce a queryable current generation"
            )
        return status

    def _validate_lexical_profile(self, value: object) -> dict[str, Any]:
        item = _exact_fields(
            value,
            required=frozenset(
                {
                    "lexical_profile_id",
                    "name",
                    "normalization_contract",
                    "unicode_token_grammar",
                    "cue_membership_contract",
                    "profile_digest",
                    "created_at",
                }
            ),
            field="lexical_profile",
        )
        record = {
            "lexical_profile_id": require_identifier(
                item.get("lexical_profile_id"), "lexical_profile_id"
            ),
            "name": require_text(item.get("name"), "lexical_profile.name", maximum=256),
            "normalization_contract": require_identifier(
                item.get("normalization_contract"), "normalization_contract"
            ),
            "unicode_token_grammar": require_text(
                item.get("unicode_token_grammar"),
                "unicode_token_grammar",
                maximum=1024,
            ),
            "cue_membership_contract": require_text(
                item.get("cue_membership_contract"),
                "cue_membership_contract",
                maximum=1024,
            ),
            "profile_digest": require_sha256(
                item.get("profile_digest"), "lexical_profile.profile_digest"
            ),
            "created_at": timestamp(
                parse_timestamp(item.get("created_at"), "lexical_profile.created_at")
            ),
        }
        if record["normalization_contract"] != LEXICAL_PROFILE_ID:
            raise ValidationError("unsupported lexical normalization contract")
        if record["unicode_token_grammar"] != LEXICAL_UNICODE_TOKEN_GRAMMAR:
            raise ValidationError("lexical profile token grammar is not executable here")
        if record["cue_membership_contract"] != LEXICAL_CUE_MEMBERSHIP_CONTRACT:
            raise ValidationError("lexical profile cue membership contract is unsupported")
        _require_record_digest(record, "profile_digest", field="lexical_profile")
        return record

    def _validate_embedding_profile(self, value: object) -> dict[str, Any]:
        item = _exact_fields(
            value,
            required=frozenset(
                {
                    "embedding_profile_id",
                    "name",
                    "provider_id",
                    "model_id",
                    "dimensions",
                    "metric",
                    "radius",
                    "comparison_tolerance",
                    "vector_encoding",
                    "qualification_state",
                    "qualification_evidence_ref",
                    "qualification_digest",
                    "profile_digest",
                    "created_at",
                }
            ),
            field="embedding_profile",
        )
        dimensions = _require_positive_integer(
            item.get("dimensions"), "embedding_profile.dimensions", maximum=4096
        )
        radius = item.get("radius")
        tolerance = item.get("comparison_tolerance")
        if isinstance(radius, bool) or not isinstance(radius, (int, float)):
            raise ValidationError("embedding_profile.radius must be numeric")
        if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)):
            raise ValidationError(
                "embedding_profile.comparison_tolerance must be numeric"
            )
        radius = float(radius)
        tolerance = float(tolerance)
        within_radius(radius, radius, tolerance)
        provider_id = item.get("provider_id")
        qualification_state = require_identifier(
            item.get("qualification_state"), "qualification_state"
        )
        if qualification_state not in QUALIFICATION_STATES:
            raise ValidationError(
                f"unsupported qualification_state: {qualification_state}"
            )
        record = {
            "embedding_profile_id": require_identifier(
                item.get("embedding_profile_id"), "embedding_profile_id"
            ),
            "name": require_text(
                item.get("name"), "embedding_profile.name", maximum=256
            ),
            "provider_id": (
                require_identifier(provider_id, "provider_id")
                if provider_id is not None
                else None
            ),
            "model_id": require_text(item.get("model_id"), "model_id", maximum=512),
            "dimensions": dimensions,
            "metric": require_identifier(item.get("metric"), "metric"),
            "radius": radius,
            "comparison_tolerance": tolerance,
            "vector_encoding": require_identifier(
                item.get("vector_encoding"), "vector_encoding"
            ),
            "qualification_state": qualification_state,
            "qualification_evidence_ref": require_text(
                item.get("qualification_evidence_ref"),
                "qualification_evidence_ref",
                maximum=2048,
            ),
            "qualification_digest": require_sha256(
                item.get("qualification_digest"), "qualification_digest"
            ),
            "profile_digest": require_sha256(
                item.get("profile_digest"), "embedding_profile.profile_digest"
            ),
            "created_at": timestamp(
                parse_timestamp(item.get("created_at"), "embedding_profile.created_at")
            ),
        }
        if record["metric"] != "cosine_distance":
            raise ValidationError("embedding profile metric must be cosine_distance")
        if record["vector_encoding"] != "float32_le":
            raise ValidationError("embedding vector encoding must be float32_le")
        _require_record_digest(record, "profile_digest", field="embedding_profile")
        return record

    def _validate_clusters(self, value: object) -> list[dict[str, Any]]:
        if not isinstance(value, list) or not value:
            raise ValidationError("clusters must be a non-empty array")
        records: list[dict[str, Any]] = []
        for index, candidate in enumerate(value):
            item = _exact_fields(
                candidate,
                required=frozenset(
                    {
                        "cluster_id",
                        "handle",
                        "name",
                        "description",
                        "source_id",
                        "source_digest",
                        "cluster_digest",
                        "created_at",
                    }
                ),
                field=f"clusters[{index}]",
            )
            record = {
                "cluster_id": require_identifier(item.get("cluster_id"), "cluster_id"),
                "handle": require_identifier(item.get("handle"), "cluster.handle").casefold(),
                "name": require_text(item.get("name"), "cluster.name", maximum=256),
                "description": require_text(
                    item.get("description"), "cluster.description", maximum=1024
                ),
                "source_id": require_identifier(item.get("source_id"), "source_id"),
                "source_digest": require_sha256(
                    item.get("source_digest"), "cluster.source_digest"
                ),
                "cluster_digest": require_sha256(
                    item.get("cluster_digest"), "cluster.cluster_digest"
                ),
                "created_at": timestamp(
                    parse_timestamp(item.get("created_at"), "cluster.created_at")
                ),
            }
            _require_record_digest(record, "cluster_digest", field=f"clusters[{index}]")
            records.append(record)
        self._require_unique(records, "cluster_id", "clusters")
        self._require_unique(records, "handle", "clusters")
        return records

    def _validate_cards(
        self, value: object
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if not isinstance(value, list) or not value:
            raise ValidationError("cards must be a non-empty array")
        cards: list[dict[str, Any]] = []
        views: list[dict[str, Any]] = []
        for index, candidate in enumerate(value):
            item = _exact_fields(
                candidate,
                required=frozenset(
                    {
                        "capability_card_id",
                        "capability_id",
                        "revision",
                        "compact_projection",
                        "boundaries",
                        "cluster_id",
                        "exposure_policy",
                        "owner_agent_instance_id",
                        "source_id",
                        "source_digest",
                        "card_digest",
                        "context_cost",
                        "created_at",
                        "views",
                    }
                ),
                field=f"cards[{index}]",
            )
            exposure = require_identifier(
                item.get("exposure_policy"), "exposure_policy"
            )
            if exposure not in CAPABILITY_EXPOSURE_POLICIES:
                raise ValidationError(f"unsupported exposure_policy: {exposure}")
            owner = item.get("owner_agent_instance_id")
            owner_id = (
                require_identifier(owner, "owner_agent_instance_id")
                if owner is not None
                else None
            )
            if (exposure == "public_safe") != (owner_id is None):
                raise ValidationError(
                    "public_safe cards require no owner; agent_private cards require one"
                )
            card = {
                "capability_card_id": require_identifier(
                    item.get("capability_card_id"), "capability_card_id"
                ),
                "capability_id": require_identifier(
                    item.get("capability_id"), "capability_id"
                ),
                "revision": _require_positive_integer(
                    item.get("revision"), "card.revision", maximum=2_147_483_647
                ),
                "compact_projection": require_text(
                    item.get("compact_projection"),
                    "compact_projection",
                    maximum=512,
                ),
                "boundaries": require_text(
                    item.get("boundaries"), "boundaries", maximum=1024
                ),
                "cluster_id": require_identifier(item.get("cluster_id"), "cluster_id"),
                "exposure_policy": exposure,
                "owner_agent_instance_id": owner_id,
                "source_id": require_identifier(item.get("source_id"), "source_id"),
                "source_digest": require_sha256(
                    item.get("source_digest"), "card.source_digest"
                ),
                "card_digest": require_sha256(
                    item.get("card_digest"), "card.card_digest"
                ),
                "context_cost": _require_nonnegative_integer(
                    item.get("context_cost"), "context_cost", maximum=1_000_000
                ),
                "created_at": timestamp(
                    parse_timestamp(item.get("created_at"), "card.created_at")
                ),
            }
            raw_views = item.get("views")
            if not isinstance(raw_views, list) or not raw_views:
                raise ValidationError(f"cards[{index}].views must be a non-empty array")
            card_views: list[dict[str, Any]] = []
            for view_index, raw_view in enumerate(raw_views):
                view_item = _exact_fields(
                    raw_view,
                    required=frozenset(
                        {
                            "capability_card_view_id",
                            "view_kind",
                            "content",
                            "content_digest",
                            "created_at",
                        }
                    ),
                    field=f"cards[{index}].views[{view_index}]",
                )
                kind = require_identifier(view_item.get("view_kind"), "view_kind")
                if kind not in VIEW_KINDS:
                    raise ValidationError(f"unsupported view_kind: {kind}")
                view = {
                    "capability_card_view_id": require_identifier(
                        view_item.get("capability_card_view_id"),
                        "capability_card_view_id",
                    ),
                    "capability_card_id": card["capability_card_id"],
                    "view_kind": kind,
                    "content": require_text(
                        view_item.get("content"), "view.content", maximum=4096
                    ),
                    "content_digest": require_sha256(
                        view_item.get("content_digest"), "view.content_digest"
                    ),
                    "created_at": timestamp(
                        parse_timestamp(view_item.get("created_at"), "view.created_at")
                    ),
                }
                if sha256_text(view["content"]) != view["content_digest"]:
                    raise ValidationError("view.content_digest does not bind its content")
                card_views.append(view)
            card_material = {**card, "views": sorted(card_views, key=lambda row: row["capability_card_view_id"])}
            if _record_digest(card_material, "card_digest") != card["card_digest"]:
                raise ValidationError(f"cards[{index}].card_digest does not bind its card and views")
            cards.append(card)
            views.extend(card_views)
        self._require_unique(cards, "capability_card_id", "cards")
        self._require_unique(cards, "capability_id", "cards")
        self._require_unique(views, "capability_card_view_id", "card views")
        return cards, views

    def _validate_relations(self, value: object) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            raise ValidationError("relations must be an array")
        records: list[dict[str, Any]] = []
        for index, candidate in enumerate(value):
            item = _exact_fields(
                candidate,
                required=frozenset(
                    {
                        "capability_relation_id",
                        "from_capability_card_id",
                        "to_capability_card_id",
                        "relation_kind",
                        "source_id",
                        "source_digest",
                        "relation_digest",
                        "created_at",
                    }
                ),
                field=f"relations[{index}]",
            )
            kind = require_identifier(item.get("relation_kind"), "relation_kind")
            if kind not in RELATION_KINDS:
                raise ValidationError(f"unsupported relation_kind: {kind}")
            record = {
                "capability_relation_id": require_identifier(
                    item.get("capability_relation_id"), "capability_relation_id"
                ),
                "from_capability_card_id": require_identifier(
                    item.get("from_capability_card_id"), "from_capability_card_id"
                ),
                "to_capability_card_id": require_identifier(
                    item.get("to_capability_card_id"), "to_capability_card_id"
                ),
                "relation_kind": kind,
                "source_id": require_identifier(item.get("source_id"), "source_id"),
                "source_digest": require_sha256(
                    item.get("source_digest"), "relation.source_digest"
                ),
                "relation_digest": require_sha256(
                    item.get("relation_digest"), "relation.relation_digest"
                ),
                "created_at": timestamp(
                    parse_timestamp(item.get("created_at"), "relation.created_at")
                ),
            }
            if record["from_capability_card_id"] == record["to_capability_card_id"]:
                raise ValidationError("capability relation cannot reference itself")
            _require_record_digest(record, "relation_digest", field=f"relations[{index}]")
            records.append(record)
        self._require_unique(records, "capability_relation_id", "relations")
        return records

    def _validate_snapshot(self, value: object) -> dict[str, Any]:
        item = _exact_fields(
            value,
            required=frozenset(
                {
                    "associative_index_snapshot_id",
                    "embedding_profile_id",
                    "lexical_profile_id",
                    "vector_coverage_state",
                    "estate_digest",
                    "source_digest",
                    "card_digest",
                    "profile_digest",
                    "snapshot_digest",
                    "builder_identity",
                    "evidence_boundary",
                    "created_at",
                    "expected_card_count",
                    "expected_relation_count",
                    "expected_vector_count",
                }
            ),
            field="snapshot",
        )
        return {
            "associative_index_snapshot_id": require_identifier(
                item.get("associative_index_snapshot_id"),
                "associative_index_snapshot_id",
            ),
            "embedding_profile_id": require_identifier(
                item.get("embedding_profile_id"), "embedding_profile_id"
            ),
            "lexical_profile_id": require_identifier(
                item.get("lexical_profile_id"), "lexical_profile_id"
            ),
            "vector_coverage_state": require_identifier(
                item.get("vector_coverage_state"), "vector_coverage_state"
            ),
            "estate_digest": require_sha256(item.get("estate_digest"), "estate_digest"),
            "source_digest": require_sha256(item.get("source_digest"), "source_digest"),
            "card_digest": require_sha256(item.get("card_digest"), "card_digest"),
            "profile_digest": require_sha256(item.get("profile_digest"), "profile_digest"),
            "snapshot_digest": require_sha256(item.get("snapshot_digest"), "snapshot_digest"),
            "builder_identity": require_text(
                item.get("builder_identity"), "builder_identity", maximum=512
            ),
            "evidence_boundary": require_text(
                item.get("evidence_boundary"), "evidence_boundary", maximum=2048
            ),
            "created_at": timestamp(
                parse_timestamp(item.get("created_at"), "snapshot.created_at")
            ),
            "expected_card_count": _require_positive_integer(
                item.get("expected_card_count"),
                "expected_card_count",
                maximum=100_000,
            ),
            "expected_relation_count": _require_nonnegative_integer(
                item.get("expected_relation_count"),
                "expected_relation_count",
                maximum=1_000_000,
            ),
            "expected_vector_count": _require_nonnegative_integer(
                item.get("expected_vector_count"),
                "expected_vector_count",
                maximum=1_000_000,
            ),
        }

    def _validate_activation(self, value: object) -> dict[str, Any]:
        item = _exact_fields(
            value,
            required=frozenset(
                {
                    "associative_snapshot_activation_id",
                    "prior_associative_index_snapshot_id",
                    "activated_at",
                }
            ),
            field="activation",
        )
        prior = item.get("prior_associative_index_snapshot_id")
        return {
            "associative_snapshot_activation_id": require_identifier(
                item.get("associative_snapshot_activation_id"),
                "associative_snapshot_activation_id",
            ),
            "prior_associative_index_snapshot_id": (
                require_identifier(prior, "prior_associative_index_snapshot_id")
                if prior is not None
                else None
            ),
            "activated_at": timestamp(
                parse_timestamp(item.get("activated_at"), "activated_at")
            ),
        }

    def _validate_vectors(
        self, value: object, *, dimensions: int
    ) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            raise ValidationError("vectors must be an array")
        records: list[dict[str, Any]] = []
        for index, candidate in enumerate(value):
            item = _exact_fields(
                candidate,
                required=frozenset(
                    {"capability_card_view_id", "values", "vector_digest"}
                ),
                field=f"vectors[{index}]",
            )
            vector = coerce_float32_vector(
                item.get("values"), dimensions=dimensions, field=f"vectors[{index}].values"
            )
            payload = pack_float32_vector(vector)
            digest = require_sha256(
                item.get("vector_digest"), f"vectors[{index}].vector_digest"
            )
            if hashlib.sha256(payload).hexdigest() != digest:
                raise ValidationError(f"vectors[{index}].vector_digest does not bind its bytes")
            records.append(
                {
                    "capability_card_view_id": require_identifier(
                        item.get("capability_card_view_id"),
                        "capability_card_view_id",
                    ),
                    "dimensions": dimensions,
                    "vector_float32_le": payload,
                    "vector_digest": digest,
                }
            )
        self._require_unique(records, "capability_card_view_id", "vectors")
        return records

    def _validate_generation_bindings(
        self,
        *,
        lexical_profile: dict[str, Any],
        embedding_profile: dict[str, Any],
        clusters: list[dict[str, Any]],
        cards: list[dict[str, Any]],
        views: list[dict[str, Any]],
        relations: list[dict[str, Any]],
        snapshot: dict[str, Any],
        vectors: list[dict[str, Any]],
        activation: dict[str, Any],
        validate_activation_chain: bool = True,
    ) -> None:
        if snapshot["embedding_profile_id"] != embedding_profile["embedding_profile_id"]:
            raise ValidationError("snapshot embedding profile binding changed")
        if snapshot["lexical_profile_id"] != lexical_profile["lexical_profile_id"]:
            raise ValidationError("snapshot lexical profile binding changed")
        if snapshot["expected_card_count"] != len(cards):
            raise ValidationError("snapshot card count does not match manifest")
        if snapshot["expected_relation_count"] != len(relations):
            raise ValidationError("snapshot relation count does not match manifest")
        if snapshot["expected_vector_count"] != len(vectors):
            raise ValidationError("snapshot vector count does not match manifest")

        cluster_ids = {item["cluster_id"] for item in clusters}
        card_ids = {item["capability_card_id"] for item in cards}
        capability_ids = {item["capability_id"] for item in cards}
        view_ids = {item["capability_card_view_id"] for item in views}
        if len(capability_ids) != len(cards):
            raise ValidationError(
                "a snapshot must contain exactly one card revision per capability"
            )
        estate_capability_ids = {
            row["capability_id"]
            for row in self._store.connection.execute(
                "SELECT capability_id FROM capabilities"
            ).fetchall()
        }
        if capability_ids - estate_capability_ids:
            raise ValidationError("card capability is absent from the estate")
        if capability_ids != estate_capability_ids:
            raise ValidationError(
                "a snapshot must cover the complete capability estate"
            )
        if any(card["cluster_id"] not in cluster_ids for card in cards):
            raise ValidationError("card references a cluster outside the manifest")
        if any(
            relation["from_capability_card_id"] not in card_ids
            or relation["to_capability_card_id"] not in card_ids
            for relation in relations
        ):
            raise ValidationError("relation endpoint is outside the snapshot")

        snapshot_created_at = parse_timestamp(
            snapshot["created_at"], "snapshot.created_at"
        )
        activation_at = parse_timestamp(activation["activated_at"], "activated_at")
        for label, record in (
            ("lexical profile", lexical_profile),
            ("embedding profile", embedding_profile),
            *(("cluster", record) for record in clusters),
            *(("card", record) for record in cards),
            *(("card view", record) for record in views),
            *(("relation", record) for record in relations),
        ):
            if parse_timestamp(record["created_at"], f"{label}.created_at") > snapshot_created_at:
                raise ValidationError(
                    f"{label} creation cannot be later than its snapshot"
                )
        if snapshot_created_at > activation_at:
            raise ValidationError("snapshot activation predates its generation")

        cluster_created = {
            cluster["cluster_id"]: parse_timestamp(
                cluster["created_at"], "cluster.created_at"
            )
            for cluster in clusters
        }
        card_created = {
            card["capability_card_id"]: parse_timestamp(
                card["created_at"], "card.created_at"
            )
            for card in cards
        }
        for card in cards:
            if cluster_created[card["cluster_id"]] > card_created[card["capability_card_id"]]:
                raise ValidationError("card creation predates its associative cluster")
        for view in views:
            if parse_timestamp(view["created_at"], "card view.created_at") < card_created[
                view["capability_card_id"]
            ]:
                raise ValidationError("card-view creation predates its card revision")
        for relation in relations:
            relation_created = parse_timestamp(
                relation["created_at"], "relation.created_at"
            )
            if relation_created < max(
                card_created[relation["from_capability_card_id"]],
                card_created[relation["to_capability_card_id"]],
            ):
                raise ValidationError("relation creation predates one of its card endpoints")

        if snapshot["vector_coverage_state"] not in VECTOR_COVERAGE_STATES:
            raise ValidationError("unsupported snapshot vector_coverage_state")
        vector_view_ids = {vector["capability_card_view_id"] for vector in vectors}
        if snapshot["vector_coverage_state"] == "complete":
            if vector_view_ids != view_ids:
                raise ValidationError(
                    "complete snapshots require exactly one vector for every card view"
                )
        elif vector_view_ids:
            raise ValidationError("unavailable vector snapshots must contain no vectors")

        connection = self._store.connection
        for source_record in [*clusters, *cards, *relations]:
            source = connection.execute(
                "SELECT digest FROM sources WHERE source_id=?",
                (source_record["source_id"],),
            ).fetchone()
            if source is None or source["digest"] != source_record["source_digest"]:
                raise ValidationError("source digest is not current in the capability estate")
        for card in cards:
            capability = connection.execute(
                "SELECT exposure_policy,owner_agent_instance_id "
                "FROM capabilities WHERE capability_id=?",
                (card["capability_id"],),
            ).fetchone()
            if capability is None:
                raise ValidationError("card capability is absent from the estate")
            if (
                card["exposure_policy"] != capability["exposure_policy"]
                or card["owner_agent_instance_id"]
                != capability["owner_agent_instance_id"]
            ):
                raise ValidationError(
                    "card visibility must exactly match its capability visibility"
                )
            if card["owner_agent_instance_id"] is not None:
                agent = connection.execute(
                    "SELECT 1 FROM agent_instances WHERE agent_instance_id=?",
                    (card["owner_agent_instance_id"],),
                ).fetchone()
                if agent is None:
                    raise ValidationError("private card owner is absent")
        if embedding_profile["provider_id"] is not None:
            provider = connection.execute(
                "SELECT 1 FROM providers WHERE provider_id=?",
                (embedding_profile["provider_id"],),
            ).fetchone()
            if provider is None:
                raise ValidationError("embedding provider is absent from the estate")

        estate_digest = sha256_text(
            canonical_json(
                self._capability_surface_manifest(estate_capability_ids)
            )
        )
        source_digest = sha256_text(
            canonical_json(
                sorted(
                    {
                        (record["source_id"], record["source_digest"])
                        for record in [*clusters, *cards, *relations]
                    }
                )
            )
        )
        card_digest = sha256_text(
            canonical_json(sorted(card["card_digest"] for card in cards))
        )
        profile_digest = sha256_text(
            canonical_json(
                [lexical_profile["profile_digest"], embedding_profile["profile_digest"]]
            )
        )
        expected_digests = {
            "estate_digest": estate_digest,
            "source_digest": source_digest,
            "card_digest": card_digest,
            "profile_digest": profile_digest,
        }
        for field, expected in expected_digests.items():
            if snapshot[field] != expected:
                raise ValidationError(f"snapshot {field} does not bind the generation")

        snapshot_material = {
            key: value
            for key, value in snapshot.items()
            if key
            not in {
                "snapshot_digest",
                "expected_card_count",
                "expected_relation_count",
                "expected_vector_count",
            }
        }
        snapshot_material.update(
            {
                "cards": sorted(
                    (card["capability_card_id"], card["card_digest"])
                    for card in cards
                ),
                "clusters": sorted(
                    (cluster["cluster_id"], cluster["cluster_digest"])
                    for cluster in clusters
                ),
                "relations": sorted(
                    (relation["capability_relation_id"], relation["relation_digest"])
                    for relation in relations
                ),
                "vectors": sorted(
                    (vector["capability_card_view_id"], vector["vector_digest"])
                    for vector in vectors
                ),
            }
        )
        if snapshot["snapshot_digest"] != sha256_text(canonical_json(snapshot_material)):
            raise ValidationError("snapshot_digest does not bind the complete generation")
        if validate_activation_chain:
            latest = self._latest_activation_for_profiles(
                embedding_profile["embedding_profile_id"],
                lexical_profile["lexical_profile_id"],
            )
            latest_snapshot_id = (
                latest["associative_index_snapshot_id"] if latest is not None else None
            )
            if activation["prior_associative_index_snapshot_id"] != latest_snapshot_id:
                raise ConflictError(
                    "snapshot activation does not continue the current profile chain"
                )
            if latest is not None and parse_timestamp(
                activation["activated_at"], "activated_at"
            ) <= parse_timestamp(latest["activated_at"], "prior activated_at"):
                raise ConflictError("snapshot activation time must advance the profile chain")
            global_latest = self._store.connection.execute(
                "SELECT associative_index_snapshot_id,activated_at "
                "FROM associative_snapshot_activations "
                "ORDER BY activated_at DESC,associative_snapshot_activation_id DESC "
                "LIMIT 1"
            ).fetchone()
            if global_latest is not None and activation_at <= parse_timestamp(
                global_latest["activated_at"], "global prior activated_at"
            ):
                raise ConflictError(
                    "snapshot activation time must advance the global generation chain"
                )
            coverage_snapshot_id = (
                global_latest["associative_index_snapshot_id"]
                if global_latest is not None
                else None
            )
            if coverage_snapshot_id is not None:
                prior_capabilities = {
                    row["capability_id"]
                    for row in self._store.connection.execute(
                        "SELECT card.capability_id "
                        "FROM associative_snapshot_cards AS membership "
                        "JOIN capability_cards AS card "
                        "ON card.capability_card_id=membership.capability_card_id "
                        "WHERE membership.associative_index_snapshot_id=?",
                        (coverage_snapshot_id,),
                    ).fetchall()
                }
                omitted = prior_capabilities - capability_ids
                if omitted:
                    raise ConflictError(
                        "snapshot activation must be a complete successor generation"
                    )
            for card in cards:
                activated_revision = self._store.connection.execute(
                    "SELECT MAX(candidate.revision) "
                    "FROM capability_cards AS candidate "
                    "JOIN associative_snapshot_cards AS membership "
                    "ON membership.capability_card_id=candidate.capability_card_id "
                    "JOIN associative_snapshot_activations AS activation "
                    "ON activation.associative_index_snapshot_id="
                    "membership.associative_index_snapshot_id "
                    "WHERE candidate.capability_id=?",
                    (card["capability_id"],),
                ).fetchone()[0]
                if activated_revision is not None and card["revision"] < activated_revision:
                    raise ConflictError(
                        "snapshot activation contains a stale capability-card revision"
                    )

    def _capability_surface_manifest(
        self, capability_ids: Iterable[str]
    ) -> list[dict[str, Any]]:
        """Bind every capability surface consumed by retrieval or rendering."""

        identifiers = sorted(set(capability_ids))
        if not identifiers:
            return []
        placeholders = ",".join("?" for _ in identifiers)
        capabilities = self._store.connection.execute(
            "SELECT capability_id,handle,exposure_policy,owner_agent_instance_id "
            "FROM capabilities WHERE capability_id IN ("
            + placeholders
            + ") ORDER BY capability_id",
            tuple(identifiers),
        ).fetchall()
        if len(capabilities) != len(identifiers):
            raise ValidationError("card capability is absent from the estate")
        aliases: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in self._store.connection.execute(
            "SELECT capability_id,namespace,normalized_alias,display_alias "
            "FROM capability_aliases WHERE capability_id IN ("
            + placeholders
            + ") ORDER BY capability_id,namespace,normalized_alias,display_alias",
            tuple(identifiers),
        ).fetchall():
            aliases[row["capability_id"]].append(
                {
                    "namespace": row["namespace"],
                    "normalized_alias": row["normalized_alias"],
                    "display_alias": row["display_alias"],
                }
            )
        return [
            {
                "capability_id": row["capability_id"],
                "handle": row["handle"],
                "exposure_policy": row["exposure_policy"],
                "owner_agent_instance_id": row["owner_agent_instance_id"],
                "aliases": aliases[row["capability_id"]],
            }
            for row in capabilities
        ]

    @staticmethod
    def _require_unique(
        records: Iterable[dict[str, Any]], key: str, label: str
    ) -> None:
        values = [record[key] for record in records]
        if len(values) != len(set(values)):
            raise ValidationError(f"{label} contain duplicate {key} values")

    def _require_stored_exact(
        self,
        table: str,
        record: dict[str, Any],
        key_fields: tuple[str, ...],
    ) -> None:
        where = " AND ".join(f"{field}=?" for field in key_fields)
        row = self._store.connection.execute(
            f"SELECT * FROM {table} WHERE {where}",
            tuple(record[field] for field in key_fields),
        ).fetchone()
        if row is None or any(row[field] != value for field, value in record.items()):
            raise ConflictError(f"associative replay differs in {table}")

    def _require_exact_replay(
        self,
        *,
        lexical_profile: dict[str, Any],
        embedding_profile: dict[str, Any],
        clusters: list[dict[str, Any]],
        cards: list[dict[str, Any]],
        views: list[dict[str, Any]],
        relations: list[dict[str, Any]],
        snapshot: dict[str, Any],
        vectors: list[dict[str, Any]],
        activation: dict[str, Any],
    ) -> None:
        self._require_stored_exact(
            "lexical_profiles", lexical_profile, ("lexical_profile_id",)
        )
        self._require_stored_exact(
            "embedding_profiles", embedding_profile, ("embedding_profile_id",)
        )
        for table, records, key in (
            ("associative_clusters", clusters, "cluster_id"),
            ("capability_cards", cards, "capability_card_id"),
            ("capability_card_views", views, "capability_card_view_id"),
            ("capability_relations", relations, "capability_relation_id"),
        ):
            for record in records:
                self._require_stored_exact(table, record, (key,))

        snapshot_id = snapshot["associative_index_snapshot_id"]
        snapshot_record = {
            key: value for key, value in snapshot.items() if not key.startswith("expected_")
        }
        self._require_stored_exact(
            "associative_index_snapshots",
            snapshot_record,
            ("associative_index_snapshot_id",),
        )
        for card in cards:
            self._require_stored_exact(
                "associative_snapshot_cards",
                {
                    "associative_index_snapshot_id": snapshot_id,
                    "capability_card_id": card["capability_card_id"],
                    "source_digest": card["source_digest"],
                    "card_digest": card["card_digest"],
                },
                ("associative_index_snapshot_id", "capability_card_id"),
            )
        for relation in relations:
            self._require_stored_exact(
                "associative_snapshot_relations",
                {
                    "associative_index_snapshot_id": snapshot_id,
                    "capability_relation_id": relation["capability_relation_id"],
                    "relation_digest": relation["relation_digest"],
                },
                ("associative_index_snapshot_id", "capability_relation_id"),
            )
        for vector in vectors:
            self._require_stored_exact(
                "associative_view_vectors",
                {"associative_index_snapshot_id": snapshot_id, **vector},
                ("associative_index_snapshot_id", "capability_card_view_id"),
            )

        count_expectations = {
            "associative_snapshot_cards": len(cards),
            "associative_snapshot_relations": len(relations),
            "associative_view_vectors": len(vectors),
        }
        for table, expected_count in count_expectations.items():
            actual_count = self._store.connection.execute(
                f"SELECT COUNT(*) FROM {table} "
                "WHERE associative_index_snapshot_id=?",
                (snapshot_id,),
            ).fetchone()[0]
            if actual_count != expected_count:
                raise ConflictError(f"associative replay has extra rows in {table}")
        card_ids = [card["capability_card_id"] for card in cards]
        placeholders = ",".join("?" for _ in card_ids)
        stored_view_count = self._store.connection.execute(
            "SELECT COUNT(*) FROM capability_card_views WHERE capability_card_id IN ("
            + placeholders
            + ")",
            tuple(card_ids),
        ).fetchone()[0]
        if stored_view_count != len(views):
            raise ConflictError("associative replay has extra card views")

        activation_rows = self._store.connection.execute(
            "SELECT associative_snapshot_activation_id,"
            "prior_associative_index_snapshot_id,activated_at "
            "FROM associative_snapshot_activations "
            "WHERE associative_index_snapshot_id=?",
            (snapshot_id,),
        ).fetchall()
        if len(activation_rows) != 1 or any(
            activation_rows[0][field] != value for field, value in activation.items()
        ):
            raise ConflictError("associative replay differs in snapshot activation")

        capability_handles = {
            row["capability_id"]: row["handle"]
            for row in self._store.connection.execute(
                "SELECT capability_id,handle FROM capabilities WHERE capability_id IN ("
                + ",".join("?" for _ in cards)
                + ")",
                tuple(card["capability_id"] for card in cards),
            ).fetchall()
        }
        expected_fts = sorted(
            (
                view["capability_card_view_id"],
                next(
                    card["capability_id"]
                    for card in cards
                    if card["capability_card_id"] == view["capability_card_id"]
                ),
                capability_handles[
                    next(
                        card["capability_id"]
                        for card in cards
                        if card["capability_card_id"] == view["capability_card_id"]
                    )
                ],
                view["content"],
            )
            for view in views
        )
        actual_fts = sorted(
            (
                row["capability_card_view_id"],
                row["capability_id"],
                row["handle"],
                row["content"],
            )
            for row in self._store.connection.execute(
                "SELECT capability_card_view_id,capability_id,handle,content "
                "FROM capability_card_fts WHERE associative_index_snapshot_id=?",
                (snapshot_id,),
            ).fetchall()
        )
        if actual_fts != expected_fts:
            raise ConflictError("associative replay differs in the lexical projection")

    def _latest_activation_for_profiles(
        self, embedding_profile_id: str, lexical_profile_id: str
    ) -> dict[str, Any] | None:
        row = self._store.connection.execute(
            "SELECT activation.* FROM associative_snapshot_activations AS activation "
            "JOIN associative_index_snapshots AS snapshot "
            "ON snapshot.associative_index_snapshot_id="
            "activation.associative_index_snapshot_id "
            "WHERE snapshot.embedding_profile_id=? AND snapshot.lexical_profile_id=? "
            "ORDER BY activation.activated_at DESC, "
            "activation.associative_snapshot_activation_id DESC LIMIT 1",
            (embedding_profile_id, lexical_profile_id),
        ).fetchone()
        return dict(row) if row is not None else None

    def _latest_snapshot_for_profiles(
        self, embedding_profile_id: str, lexical_profile_id: str
    ) -> str | None:
        activation = self._latest_activation_for_profiles(
            embedding_profile_id, lexical_profile_id
        )
        return (
            activation["associative_index_snapshot_id"]
            if activation is not None
            else None
        )

    def _snapshot_sources_current(
        self, snapshot_id: str, visible_card_ids: set[str] | None = None
    ) -> bool:
        if visible_card_ids is not None and not visible_card_ids:
            return True
        card_filter = ""
        relation_filter = ""
        parameters: list[Any] = [snapshot_id]
        if visible_card_ids is not None:
            placeholders = ",".join("?" for _ in visible_card_ids)
            card_filter = " AND membership.capability_card_id IN (" + placeholders + ")"
            parameters.extend(sorted(visible_card_ids))
        card_rows = self._store.connection.execute(
            "SELECT membership.source_digest AS membership_digest,"
            "card.source_digest AS object_digest,source.digest AS current_digest "
            "FROM associative_snapshot_cards AS membership "
            "JOIN capability_cards AS card "
            "ON card.capability_card_id=membership.capability_card_id "
            "LEFT JOIN sources AS source ON source.source_id=card.source_id "
            "WHERE membership.associative_index_snapshot_id=?" + card_filter,
            tuple(parameters),
        ).fetchall()

        parameters = [snapshot_id]
        if visible_card_ids is not None:
            placeholders = ",".join("?" for _ in visible_card_ids)
            relation_filter = (
                " AND relation.from_capability_card_id IN ("
                + placeholders
                + ") AND relation.to_capability_card_id IN ("
                + placeholders
                + ")"
            )
            ordered_ids = sorted(visible_card_ids)
            parameters.extend(ordered_ids)
            parameters.extend(ordered_ids)
        relation_rows = self._store.connection.execute(
            "SELECT relation.source_digest AS membership_digest,"
            "relation.source_digest AS object_digest,source.digest AS current_digest "
            "FROM associative_snapshot_relations AS membership "
            "JOIN capability_relations AS relation "
            "ON relation.capability_relation_id=membership.capability_relation_id "
            "LEFT JOIN sources AS source ON source.source_id=relation.source_id "
            "WHERE membership.associative_index_snapshot_id=?" + relation_filter,
            tuple(parameters),
        ).fetchall()

        parameters = [snapshot_id]
        if visible_card_ids is not None:
            placeholders = ",".join("?" for _ in visible_card_ids)
            parameters.extend(sorted(visible_card_ids))
            card_filter = " AND membership.capability_card_id IN (" + placeholders + ")"
        cluster_rows = self._store.connection.execute(
            "SELECT cluster.source_digest AS membership_digest,"
            "cluster.source_digest AS object_digest,source.digest AS current_digest "
            "FROM associative_snapshot_cards AS membership "
            "JOIN capability_cards AS card "
            "ON card.capability_card_id=membership.capability_card_id "
            "JOIN associative_clusters AS cluster ON cluster.cluster_id=card.cluster_id "
            "LEFT JOIN sources AS source ON source.source_id=cluster.source_id "
            "WHERE membership.associative_index_snapshot_id=?" + card_filter,
            tuple(parameters),
        ).fetchall()
        rows = [*card_rows, *relation_rows, *cluster_rows]
        return bool(rows) and all(
            row["membership_digest"]
            == row["object_digest"]
            == row["current_digest"]
            for row in rows
        )

    def _snapshot_card_revisions_current(
        self, snapshot_id: str, visible_card_ids: set[str] | None = None
    ) -> bool:
        parameters: list[Any] = [snapshot_id]
        visibility_filter = ""
        if visible_card_ids is not None:
            if not visible_card_ids:
                return True
            placeholders = ",".join("?" for _ in visible_card_ids)
            visibility_filter = (
                " AND current_membership.capability_card_id IN ("
                + placeholders
                + ")"
            )
            parameters.extend(sorted(visible_card_ids))
        newer = self._store.connection.execute(
            "SELECT 1 "
            "FROM associative_snapshot_cards AS current_membership "
            "JOIN capability_cards AS current_card "
            "ON current_card.capability_card_id=current_membership.capability_card_id "
            "JOIN capability_cards AS newer_card "
            "ON newer_card.capability_id=current_card.capability_id "
            "AND newer_card.revision>current_card.revision "
            "JOIN associative_snapshot_cards AS newer_membership "
            "ON newer_membership.capability_card_id=newer_card.capability_card_id "
            "JOIN associative_snapshot_activations AS newer_activation "
            "ON newer_activation.associative_index_snapshot_id="
            "newer_membership.associative_index_snapshot_id "
            "WHERE current_membership.associative_index_snapshot_id=?"
            + visibility_filter
            + " LIMIT 1",
            tuple(parameters),
        ).fetchone()
        return newer is None

    def _snapshot_status(self, snapshot_id: str) -> dict[str, Any]:
        row = self._store.connection.execute(
            "SELECT snapshot.*, profile.qualification_state "
            "FROM associative_index_snapshots AS snapshot "
            "JOIN embedding_profiles AS profile "
            "ON profile.embedding_profile_id=snapshot.embedding_profile_id "
            "WHERE snapshot.associative_index_snapshot_id=?",
            (snapshot_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError("associative snapshot not found")
        snapshot = dict(row)
        latest = self._latest_snapshot_for_profiles(
            snapshot["embedding_profile_id"], snapshot["lexical_profile_id"]
        )
        activation_current = latest == snapshot_id
        source_current = self._snapshot_sources_current(snapshot_id)
        card_revisions_current = self._snapshot_card_revisions_current(snapshot_id)
        return {
            **snapshot,
            "current": (
                activation_current and source_current and card_revisions_current
            ),
            "activation_current": activation_current,
            "source_current": source_current,
            "card_revisions_current": card_revisions_current,
            "counts": {
                "cards": self._store.connection.execute(
                    "SELECT COUNT(*) FROM associative_snapshot_cards "
                    "WHERE associative_index_snapshot_id=?",
                    (snapshot_id,),
                ).fetchone()[0],
                "relations": self._store.connection.execute(
                    "SELECT COUNT(*) FROM associative_snapshot_relations "
                    "WHERE associative_index_snapshot_id=?",
                    (snapshot_id,),
                ).fetchone()[0],
                "vectors": self._store.connection.execute(
                    "SELECT COUNT(*) FROM associative_view_vectors "
                    "WHERE associative_index_snapshot_id=?",
                    (snapshot_id,),
                ).fetchone()[0],
            },
            "claim_boundary": (
                "Current means the latest activated generation for the exact profiles, "
                "with current source bindings and no activated newer card revision. "
                "It does not establish semantic quality or delivery."
            ),
        }

    def _scoped_projection_digest(
        self, snapshot_id: str, cards: list[dict[str, Any]]
    ) -> str:
        card_ids = sorted(card["capability_card_id"] for card in cards)
        if not card_ids:
            return sha256_text(canonical_json({"empty": True}))
        placeholders = ",".join("?" for _ in card_ids)
        clusters = [
            (row["cluster_id"], row["cluster_digest"])
            for row in self._store.connection.execute(
                "SELECT DISTINCT cluster.cluster_id,cluster.cluster_digest "
                "FROM associative_snapshot_cards AS membership "
                "JOIN capability_cards AS card "
                "ON card.capability_card_id=membership.capability_card_id "
                "JOIN associative_clusters AS cluster ON cluster.cluster_id=card.cluster_id "
                "WHERE membership.associative_index_snapshot_id=? "
                "AND membership.capability_card_id IN ("
                + placeholders
                + ") ORDER BY cluster.cluster_id",
                (snapshot_id, *card_ids),
            ).fetchall()
        ]
        relation_parameters = (snapshot_id, *card_ids, *card_ids)
        relations = [
            (row["capability_relation_id"], row["relation_digest"])
            for row in self._store.connection.execute(
                "SELECT relation.capability_relation_id,relation.relation_digest "
                "FROM associative_snapshot_relations AS membership "
                "JOIN capability_relations AS relation "
                "ON relation.capability_relation_id=membership.capability_relation_id "
                "WHERE membership.associative_index_snapshot_id=? "
                "AND relation.from_capability_card_id IN ("
                + placeholders
                + ") AND relation.to_capability_card_id IN ("
                + placeholders
                + ") ORDER BY relation.capability_relation_id",
                relation_parameters,
            ).fetchall()
        ]
        vectors = [
            (row["capability_card_view_id"], row["vector_digest"])
            for row in self._store.connection.execute(
                "SELECT vector.capability_card_view_id,vector.vector_digest "
                "FROM associative_view_vectors AS vector "
                "JOIN capability_card_views AS view "
                "ON view.capability_card_view_id=vector.capability_card_view_id "
                "WHERE vector.associative_index_snapshot_id=? "
                "AND view.capability_card_id IN ("
                + placeholders
                + ") ORDER BY vector.capability_card_view_id",
                (snapshot_id, *card_ids),
            ).fetchall()
        ]
        return sha256_text(
            canonical_json(
                {
                    "capabilities": self._capability_surface_manifest(
                        card["capability_id"] for card in cards
                    ),
                    "cards": sorted(
                        (card["capability_card_id"], card["card_digest"])
                        for card in cards
                    ),
                    "clusters": clusters,
                    "relations": relations,
                    "vectors": vectors,
                }
            )
        )

    def _latest_scope_activation(
        self,
        embedding_profile_id: str,
        lexical_profile_id: str,
        binding: dict[str, Any],
    ) -> tuple[str, list[dict[str, Any]]] | None:
        rows = self._store.connection.execute(
            "SELECT activation.associative_index_snapshot_id "
            "FROM associative_snapshot_activations AS activation "
            "JOIN associative_index_snapshots AS snapshot "
            "ON snapshot.associative_index_snapshot_id="
            "activation.associative_index_snapshot_id "
            "WHERE snapshot.embedding_profile_id=? AND snapshot.lexical_profile_id=? "
            "ORDER BY activation.activated_at DESC,"
            "activation.associative_snapshot_activation_id DESC",
            (embedding_profile_id, lexical_profile_id),
        ).fetchall()
        for row in rows:
            candidate_id = row["associative_index_snapshot_id"]
            cards = self._visible_cards(candidate_id, binding)
            if cards:
                return candidate_id, cards
        return None

    def _scoped_snapshot_status(
        self,
        snapshot_id: str,
        binding: dict[str, Any],
        visible_cards: list[dict[str, Any]],
    ) -> dict[str, Any]:
        row = self._store.connection.execute(
            "SELECT snapshot.*, profile.qualification_state "
            "FROM associative_index_snapshots AS snapshot "
            "JOIN embedding_profiles AS profile "
            "ON profile.embedding_profile_id=snapshot.embedding_profile_id "
            "WHERE snapshot.associative_index_snapshot_id=?",
            (snapshot_id,),
        ).fetchone()
        if row is None or not visible_cards:
            raise NotFoundError("associative snapshot not found")
        snapshot = dict(row)
        latest = self._latest_scope_activation(
            snapshot["embedding_profile_id"], snapshot["lexical_profile_id"], binding
        )
        activation_current = bool(
            latest
            and self._scoped_projection_digest(snapshot_id, visible_cards)
            == self._scoped_projection_digest(latest[0], latest[1])
        )
        card_ids = {card["capability_card_id"] for card in visible_cards}
        source_current = self._snapshot_sources_current(snapshot_id, card_ids)
        card_revisions_current = self._snapshot_card_revisions_current(
            snapshot_id, card_ids
        )
        return {
            **snapshot,
            "current": activation_current and source_current and card_revisions_current,
            "activation_current": activation_current,
            "source_current": source_current,
            "card_revisions_current": card_revisions_current,
            "claim_boundary": (
                "Scoped current means equivalent to the latest activated visible "
                "projection for the exact profiles, with current visible source "
                "bindings and no activated newer visible card revision. It does not "
                "establish semantic quality or delivery."
            ),
        }

    def _require_current_snapshot(
        self, snapshot_id: object, binding: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        snapshot_id = require_identifier(snapshot_id, "snapshot_id")
        visible_cards = self._visible_cards(snapshot_id, binding) if binding else None
        status = (
            self._scoped_snapshot_status(snapshot_id, binding, visible_cards)
            if binding is not None and visible_cards is not None
            else self._snapshot_status(snapshot_id)
        )
        if not status["current"]:
            raise ConflictError("associative snapshot is not current")
        profile = self._store.connection.execute(
            "SELECT * FROM embedding_profiles WHERE embedding_profile_id=?",
            (status["embedding_profile_id"],),
        ).fetchone()
        lexical = self._store.connection.execute(
            "SELECT * FROM lexical_profiles WHERE lexical_profile_id=?",
            (status["lexical_profile_id"],),
        ).fetchone()
        return {
            "snapshot": status,
            "embedding_profile": dict(profile),
            "lexical_profile": dict(lexical),
            **({"visible_cards": visible_cards} if visible_cards is not None else {}),
        }

    def _visible_cards(
        self, snapshot_id: str, binding: dict[str, Any]
    ) -> list[dict[str, Any]]:
        allow_private = binding["exposure_scope"] == "public_and_agent_private"
        rows = self._store.connection.execute(
            "SELECT card.*, capability.handle, cluster.handle AS cluster_handle, "
            "cluster.name AS cluster_name "
            "FROM associative_snapshot_cards AS membership "
            "JOIN capability_cards AS card "
            "ON card.capability_card_id=membership.capability_card_id "
            "JOIN capabilities AS capability ON capability.capability_id=card.capability_id "
            "JOIN associative_clusters AS cluster ON cluster.cluster_id=card.cluster_id "
            "WHERE membership.associative_index_snapshot_id=? "
            "AND card.exposure_policy=capability.exposure_policy "
            "AND card.owner_agent_instance_id IS capability.owner_agent_instance_id "
            "AND (capability.exposure_policy='public_safe' OR "
            "(?=1 AND capability.exposure_policy='agent_private' "
            "AND capability.owner_agent_instance_id=?)) "
            "ORDER BY capability.handle, card.capability_card_id",
            (snapshot_id, int(allow_private), binding["agent_instance_id"]),
        ).fetchall()
        return [dict(row) for row in rows]

    def neighborhood(
        self,
        session_capability: str,
        snapshot_id: str,
        anchors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        binding = self._bound_scope(session_capability)
        snapshot_bundle = self._require_current_snapshot(snapshot_id, binding)
        snapshot = snapshot_bundle["snapshot"]
        profile = snapshot_bundle["embedding_profile"]
        lexical_profile = snapshot_bundle["lexical_profile"]
        if lexical_profile["normalization_contract"] != LEXICAL_PROFILE_ID:
            raise ConflictError("active lexical profile is unsupported")
        parsed_anchors = self._validate_anchors(anchors, profile["dimensions"])
        if snapshot["vector_coverage_state"] == "unavailable" and any(
            anchor["vector"] is not None for anchor in parsed_anchors
        ):
            raise ValidationError(
                "active snapshot has no vector projection; use lexical hints only"
            )
        cards = snapshot_bundle["visible_cards"]
        card_by_id = {card["capability_card_id"]: card for card in cards}
        scoped_estate_digest = sha256_text(
            canonical_json(
                {
                    "capabilities": self._capability_surface_manifest(
                        card["capability_id"] for card in cards
                    ),
                    "cards": sorted(
                        (card["capability_card_id"], card["card_digest"])
                        for card in cards
                    ),
                }
            )
        )
        views_by_card = self._views_for_cards(card_by_id)
        aliases_by_capability = self._aliases_for_cards(cards)

        associations: dict[str, list[dict[str, Any]]] = defaultdict(list)
        boundary_cards: set[str] = set()
        vector_anchor_count = 0
        lexical_hint_count = 0

        vector_rows = self._visible_vectors(snapshot_id, card_by_id)
        for anchor in parsed_anchors:
            if anchor["vector"] is not None:
                vector_anchor_count += 1
                for row in vector_rows:
                    stored = unpack_float32_vector(
                        row["vector_float32_le"],
                        dimensions=profile["dimensions"],
                    )
                    distance = exact_cosine_distance(anchor["vector"], stored)
                    if within_radius(
                        distance,
                        profile["radius"],
                        profile["comparison_tolerance"],
                    ):
                        associations[row["capability_card_id"]].append(
                            {
                                "anchor_id": anchor["anchor_id"],
                                "anchor_kind": anchor["anchor_kind"],
                                "basis": "vector",
                                "view_kind": row["view_kind"],
                            }
                        )
                        if row["view_kind"] == "negative_boundary":
                            boundary_cards.add(row["capability_card_id"])
            for hint_tokens in anchor["lexical_tokens"]:
                lexical_hint_count += 1
                for card_id, card in card_by_id.items():
                    matches = self._lexical_matches(
                        card,
                        views_by_card[card_id],
                        aliases_by_capability[card["capability_id"]],
                        hint_tokens,
                    )
                    for match in matches:
                        associations[card_id].append(
                            {
                                "anchor_id": anchor["anchor_id"],
                                "anchor_kind": anchor["anchor_kind"],
                                "basis": "lexical",
                                **match,
                            }
                        )
                        if match.get("view_kind") == "negative_boundary":
                            boundary_cards.add(card_id)

        direct_ids = set(associations)
        self._add_relation_paths(
            snapshot_id=snapshot_id,
            direct_ids=direct_ids,
            visible_cards=card_by_id,
            associations=associations,
            boundary_cards=boundary_cards,
        )

        members: list[dict[str, Any]] = []
        for card_id in sorted(associations, key=lambda value: card_by_id[value]["handle"]):
            card = card_by_id[card_id]
            members.append(
                {
                    "capability_id": card["capability_id"],
                    "handle": card["handle"],
                    "card_id": card["capability_card_id"],
                    "card_revision": card["revision"],
                    "compact_projection": card["compact_projection"],
                    "boundaries": card["boundaries"],
                    "cluster": {
                        "cluster_id": card["cluster_id"],
                        "handle": card["cluster_handle"],
                        "name": card["cluster_name"],
                    },
                    "presentation": (
                        "boundary_only" if card_id in boundary_cards else "nearby"
                    ),
                    "associations": _sorted_associations(associations[card_id]),
                    "lifecycle_observations": self._lifecycle_for_capability(
                        card["capability_id"], binding
                    ),
                }
            )

        membership_manifest = [
            {
                "capability_id": member["capability_id"],
                "card_id": member["card_id"],
                "card_revision": member["card_revision"],
                "presentation": member["presentation"],
                "associations": member["associations"],
            }
            for member in members
        ]
        membership_digest = sha256_text(canonical_json(membership_manifest))
        anchor_fingerprints = [
            {
                "anchor_id": anchor["anchor_id"],
                "anchor_kind": anchor["anchor_kind"],
                "vector_digest": (
                    hashlib.sha256(pack_float32_vector(anchor["vector"])).hexdigest()
                    if anchor["vector"] is not None
                    else None
                ),
                "lexical_hint_digests": anchor["lexical_hint_digests"],
            }
            for anchor in parsed_anchors
        ]
        field_id = "field:" + sha256_text(
            canonical_json(
                {
                    "snapshot_id": snapshot_id,
                    "session_capability_hash": binding["token_hash"],
                    "anchors": anchor_fingerprints,
                    "membership_manifest_digest": membership_digest,
                }
            )
        )
        token_expiry = min(binding["expires_at"], self.hosts.session(
            binding["host_session_id"], binding["agent_instance_id"], require_fresh=True
        )["expires_at"])
        for member in members:
            member["visibility_token"] = sign_visibility_token(
                {
                    "format": "mind-reminder-visibility/v1",
                    "field_id": field_id,
                    "membership_manifest_digest": membership_digest,
                    "snapshot_id": snapshot_id,
                    "card_id": member["card_id"],
                    "card_revision": member["card_revision"],
                    "capability_id": member["capability_id"],
                    "agent_instance_id": binding["agent_instance_id"],
                    "host_session_id": binding["host_session_id"],
                    "session_epoch": binding["session_epoch"],
                    "session_capability_hash": binding["token_hash"],
                    "expires_at": token_expiry,
                },
                self._signing_key(),
            )

        canonical_field = self._render_canonical(members)
        compact_field = self._render_compact(members)
        if vector_anchor_count and lexical_hint_count:
            mode = "hybrid_current"
        elif vector_anchor_count:
            mode = "vector_current"
        elif lexical_hint_count:
            mode = "lexical_degraded"
        else:
            mode = "unavailable"
        return {
            "field_id": field_id,
            "snapshot_id": snapshot_id,
            "scoped_estate_digest": scoped_estate_digest,
            "embedding_profile_id": profile["embedding_profile_id"],
            "lexical_profile_id": lexical_profile["lexical_profile_id"],
            "reported_profile_qualification": {
                "state": profile["qualification_state"],
                "evidence_ref": profile["qualification_evidence_ref"],
                "evidence_digest": profile["qualification_digest"],
                "evidence_state": "reported",
            },
            "vector_coverage_state": snapshot["vector_coverage_state"],
            "mode": mode,
            "membership_manifest_digest": membership_digest,
            "anchors": [
                {
                    "anchor_id": anchor["anchor_id"],
                    "anchor_kind": anchor["anchor_kind"],
                    "vector_supplied": anchor["vector"] is not None,
                    "lexical_hint_count": len(anchor["lexical_tokens"]),
                }
                for anchor in parsed_anchors
            ],
            "members": members,
            "representations": {
                "canonical": self._representation(canonical_field, membership_digest),
                "compact": self._representation(compact_field, membership_digest),
            },
            "claim_boundary": (
                "Membership means local vector or exhaustive lexical association, or "
                "one explicit relation hop, in the named snapshot and scope. It does "
                "not establish utility, selection, activation, authority, fitness, "
                "health, delivery, attention, or use."
            ),
        }

    def _validate_anchors(
        self, value: object, dimensions: int
    ) -> list[dict[str, Any]]:
        if not isinstance(value, list) or not value or len(value) > MAX_ANCHORS:
            raise ValidationError(f"anchors must contain between 1 and {MAX_ANCHORS} items")
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        total_hints = 0
        for index, candidate in enumerate(value):
            item = _exact_fields(
                candidate,
                required=frozenset({"anchor_id", "anchor_kind"}),
                optional=frozenset({"vector", "lexical_hints"}),
                field=f"anchors[{index}]",
            )
            anchor_id = require_identifier(item.get("anchor_id"), "anchor_id")
            if anchor_id in seen:
                raise ValidationError("anchor_id values must be unique")
            seen.add(anchor_id)
            raw_hints = item.get("lexical_hints", [])
            if not isinstance(raw_hints, list) or len(raw_hints) > MAX_HINTS_PER_ANCHOR:
                raise ValidationError(
                    f"lexical_hints may contain at most {MAX_HINTS_PER_ANCHOR} items"
                )
            hint_tokens = [
                lexical_tokens(
                    hint,
                    f"anchors[{index}].lexical_hints[{hint_index}]",
                    maximum=MAX_LEXICAL_HINT_CHARACTERS,
                )
                for hint_index, hint in enumerate(raw_hints)
            ]
            total_hints += len(hint_tokens)
            raw_vector = item.get("vector")
            vector = (
                coerce_float32_vector(
                    raw_vector,
                    dimensions=dimensions,
                    field=f"anchors[{index}].vector",
                )
                if raw_vector is not None
                else None
            )
            result.append(
                {
                    "anchor_id": anchor_id,
                    "anchor_kind": require_identifier(
                        item.get("anchor_kind"), "anchor_kind"
                    ),
                    "vector": vector,
                    "lexical_tokens": hint_tokens,
                    "lexical_hint_digests": [
                        sha256_text(canonical_json(tokens)) for tokens in hint_tokens
                    ],
                }
            )
        if total_hints > MAX_TOTAL_HINTS:
            raise ValidationError(
                f"anchors may contain at most {MAX_TOTAL_HINTS} lexical hints in total"
            )
        return result

    def _views_for_cards(
        self, cards: dict[str, dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = defaultdict(list)
        if not cards:
            return result
        placeholders = ",".join("?" for _ in cards)
        rows = self._store.connection.execute(
            "SELECT * FROM capability_card_views WHERE capability_card_id IN ("
            + placeholders
            + ") ORDER BY capability_card_id,view_kind,capability_card_view_id",
            tuple(cards),
        ).fetchall()
        for row in rows:
            result[row["capability_card_id"]].append(dict(row))
        return result

    def _aliases_for_cards(
        self, cards: list[dict[str, Any]]
    ) -> dict[str, list[str]]:
        result: dict[str, list[str]] = defaultdict(list)
        capability_ids = sorted({card["capability_id"] for card in cards})
        if not capability_ids:
            return result
        placeholders = ",".join("?" for _ in capability_ids)
        rows = self._store.connection.execute(
            "SELECT capability_id,normalized_alias,display_alias FROM capability_aliases "
            "WHERE capability_id IN ("
            + placeholders
            + ") ORDER BY capability_id,namespace,normalized_alias",
            tuple(capability_ids),
        ).fetchall()
        for row in rows:
            for alias in (row["normalized_alias"], row["display_alias"]):
                if alias not in result[row["capability_id"]]:
                    result[row["capability_id"]].append(alias)
        return result

    def _visible_vectors(
        self, snapshot_id: str, cards: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not cards:
            return []
        placeholders = ",".join("?" for _ in cards)
        rows = self._store.connection.execute(
            "SELECT view.capability_card_id,view.view_kind,vector.vector_float32_le "
            "FROM associative_view_vectors AS vector "
            "JOIN capability_card_views AS view "
            "ON view.capability_card_view_id=vector.capability_card_view_id "
            "WHERE vector.associative_index_snapshot_id=? "
            "AND view.capability_card_id IN ("
            + placeholders
            + ") ORDER BY view.capability_card_id,view.view_kind,view.capability_card_view_id",
            (snapshot_id, *cards),
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _lexical_matches(
        card: dict[str, Any],
        views: list[dict[str, Any]],
        aliases: list[str],
        hint_tokens: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        if contains_contiguous_tokens(lexical_tokens(card["handle"]), hint_tokens):
            matches.append({"lexical_surface": "handle"})
        for alias in aliases:
            if contains_contiguous_tokens(lexical_tokens(alias), hint_tokens):
                matches.append({"lexical_surface": "alias"})
        for view in views:
            if contains_contiguous_tokens(lexical_tokens(view["content"]), hint_tokens):
                matches.append(
                    {
                        "lexical_surface": "card_view",
                        "view_kind": view["view_kind"],
                    }
                )
        return matches

    def _add_relation_paths(
        self,
        *,
        snapshot_id: str,
        direct_ids: set[str],
        visible_cards: dict[str, dict[str, Any]],
        associations: dict[str, list[dict[str, Any]]],
        boundary_cards: set[str],
    ) -> None:
        if not direct_ids:
            return
        placeholders = ",".join("?" for _ in direct_ids)
        rows = self._store.connection.execute(
            "SELECT relation.* FROM associative_snapshot_relations AS membership "
            "JOIN capability_relations AS relation "
            "ON relation.capability_relation_id=membership.capability_relation_id "
            "WHERE membership.associative_index_snapshot_id=? "
            "AND relation.from_capability_card_id IN ("
            + placeholders
            + ") ORDER BY relation.from_capability_card_id,relation.relation_kind,"
            "relation.to_capability_card_id",
            (snapshot_id, *sorted(direct_ids)),
        ).fetchall()
        for row in rows:
            target_id = row["to_capability_card_id"]
            source_id = row["from_capability_card_id"]
            if target_id not in visible_cards:
                continue
            associations[target_id].append(
                {
                    "basis": "relation",
                    "relation_kind": row["relation_kind"],
                    "from_handle": visible_cards[source_id]["handle"],
                }
            )
            if row["relation_kind"] == "false_friend_of":
                boundary_cards.add(target_id)

    def _lifecycle_for_capability(
        self, capability_id: str, binding: dict[str, Any]
    ) -> list[dict[str, Any]]:
        rows = self._store.connection.execute(
            "SELECT axis,state,distribution_id,agent_instance_id,host_session_id,"
            "observed_at,expires_at,source_reference "
            "FROM lifecycle_observations WHERE capability_id=? AND ("
            "(agent_instance_id IS NULL AND host_session_id IS NULL) OR "
            "(agent_instance_id=? AND host_session_id=?)) "
            "ORDER BY axis,observed_at,observation_id",
            (
                capability_id,
                binding["agent_instance_id"],
                binding["host_session_id"],
            ),
        ).fetchall()
        return [
            {
                **dict(row),
                "fresh": row["expires_at"] is None or is_fresh(row["expires_at"]),
            }
            for row in rows
        ]

    @staticmethod
    def _lifecycle_summary(member: dict[str, Any]) -> str:
        latest: dict[str, dict[str, Any]] = {}
        for observation in member["lifecycle_observations"]:
            if observation["fresh"]:
                latest[observation["axis"]] = observation
        if not latest:
            return "lifecycle=unobserved"
        return ", ".join(
            f"{axis}={latest[axis]['state']}" for axis in sorted(latest)
        )

    @classmethod
    def _render_canonical(cls, members: list[dict[str, Any]]) -> str:
        lines = [FIELD_HEADER]
        if not members:
            lines.append("\n(no handles occupy this field)")
            return "\n".join(lines)
        for member in members:
            model_paths = member["associations"]
            if member["presentation"] == "boundary_only":
                model_paths = [
                    path
                    for path in member["associations"]
                    if (
                        path.get("relation_kind") == "false_friend_of"
                        or path.get("view_kind") == "negative_boundary"
                    )
                ]
            paths = ", ".join(
                (
                    f"negative_boundary←{path['anchor_kind']}"
                    if (
                        member["presentation"] == "boundary_only"
                        and path.get("view_kind") == "negative_boundary"
                    )
                    else (
                        f"{path['anchor_kind']}:{path['basis']}"
                        if path["basis"] != "relation"
                        else f"{path['relation_kind']}←{path['from_handle']}"
                    )
                )
                for path in model_paths
            )
            boundary = (
                f" BOUNDARY ONLY — {member['boundaries']}"
                if member["presentation"] == "boundary_only"
                else f" Boundary: {member['boundaries']}"
            )
            lines.append(
                f"\n- ⟦{member['handle']}⟧ {member['compact_projection']} "
                f"[near: {paths}; {cls._lifecycle_summary(member)}].{boundary}"
            )
        return "".join(lines)

    @staticmethod
    def _render_compact(members: list[dict[str, Any]]) -> str:
        lines = [FIELD_HEADER]
        if not members:
            lines.append("\n(no handles occupy this field)")
            return "\n".join(lines)
        grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
        for member in members:
            marker = "⚠" if member["presentation"] == "boundary_only" else ""
            grouped[
                (member["cluster"]["handle"], member["cluster"]["name"])
            ].append(f"⟦{member['handle']}⟧{marker}")
        for (cluster_handle, cluster_name), handles in sorted(grouped.items()):
            lines.append(
                f"\n- {cluster_name} ⟪{cluster_handle}⟫: " + " · ".join(sorted(handles))
            )
        lines.append("\n⚠ = boundary only")
        return "".join(lines)

    @staticmethod
    def _representation(text: str, membership_digest: str) -> dict[str, Any]:
        return {
            "text": text,
            "body_sha256": sha256_text(text),
            "utf8_bytes": len(text.encode("utf-8")),
            "membership_manifest_digest": membership_digest,
        }

    def card(
        self,
        session_capability: str,
        field_id: str,
        membership_manifest_digest: str,
        visibility_token: str,
    ) -> dict[str, Any]:
        binding = self._bound_scope(session_capability)
        field_id = require_identifier(field_id, "field_id")
        membership_manifest_digest = require_sha256(
            membership_manifest_digest, "membership_manifest_digest"
        )
        payload = verify_visibility_token(visibility_token, self._signing_key())
        expected = {
            "format": "mind-reminder-visibility/v1",
            "field_id": field_id,
            "membership_manifest_digest": membership_manifest_digest,
            "agent_instance_id": binding["agent_instance_id"],
            "host_session_id": binding["host_session_id"],
            "session_epoch": binding["session_epoch"],
            "session_capability_hash": binding["token_hash"],
        }
        if any(payload.get(key) != value for key, value in expected.items()):
            raise NotFoundError("reminder card is unavailable")
        try:
            if not is_fresh(payload["expires_at"]):
                raise NotFoundError("reminder card is unavailable")
            snapshot_id = require_identifier(payload["snapshot_id"], "snapshot_id")
            card_id = require_identifier(payload["card_id"], "card_id")
            revision = _require_positive_integer(
                payload["card_revision"], "card_revision", maximum=2_147_483_647
            )
            capability_id = require_identifier(
                payload["capability_id"], "capability_id"
            )
        except (KeyError, ValidationError):
            raise NotFoundError("reminder card is unavailable") from None
        snapshot_bundle = self._require_current_snapshot(snapshot_id, binding)
        visible = {
            row["capability_card_id"]: row
            for row in snapshot_bundle["visible_cards"]
        }
        card = visible.get(card_id)
        if (
            card is None
            or card["revision"] != revision
            or card["capability_id"] != capability_id
        ):
            raise NotFoundError("reminder card is unavailable")
        views = [
            dict(row)
            for row in self._store.connection.execute(
                "SELECT capability_card_view_id,view_kind,content,content_digest,created_at "
                "FROM capability_card_views WHERE capability_card_id=? "
                "ORDER BY view_kind,capability_card_view_id",
                (card_id,),
            ).fetchall()
        ]
        return {
            "field_id": field_id,
            "membership_manifest_digest": membership_manifest_digest,
            "snapshot_id": snapshot_id,
            "card": {
                "card_id": card_id,
                "card_revision": revision,
                "capability_id": capability_id,
                "handle": card["handle"],
                "compact_projection": card["compact_projection"],
                "boundaries": card["boundaries"],
                "cluster_id": card["cluster_id"],
                "source_id": card["source_id"],
                "source_digest": card["source_digest"],
                "card_digest": card["card_digest"],
                "views": views,
                "lifecycle_observations": self._lifecycle_for_capability(
                    capability_id, binding
                ),
            },
            "claim_boundary": (
                "This is the exact immutable card revision exposed by the named "
                "field. No backing package or owner corpus was opened."
            ),
        }
