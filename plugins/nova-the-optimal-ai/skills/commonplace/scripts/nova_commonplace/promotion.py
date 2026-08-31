"""Proposal-only promotion gates for moving Commonplace knowledge toward its real owner.

A promotion proposal is canonical Commonplace state. It can be reviewed and
exported as a non-executable, snapshot-bound handoff packet. This module never
imports an owner writer, invokes a target tool, or mutates a target store.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import re
from typing import Any

from .model import (
    SENSITIVITIES,
    evaluate_record_validity,
    normalize_record,
    validate_record_id,
)
from .runtime import (
    ConflictError,
    ValidationError,
    canonical_json_bytes,
    digest_object,
    utc_now,
    validate_timestamp,
)
from .store import CommonplaceStore


PROPOSAL_SCHEMA = "nova-commonplace.promotion-proposal.v1"
HANDOFF_SCHEMA = "nova-commonplace.promotion-handoff.v1"
PLAN_SCHEMA = "nova-commonplace.promotion-plan.v1"

# Closed contracts: a free-form owner plus a plausible string is not an interface.
OWNER_CONTRACTS: dict[str, frozenset[str]] = {
    "Dunbar": frozenset({"dunbar-item/v1"}),
    "Corkboard": frozenset({"corkboard-pin/v1"}),
    "Dennis": frozenset({"dennis-project-record/v1"}),
    "Continuity": frozenset({"worldline-observation/v1"}),
    "Giles": frozenset({"giles-custody-candidate/v1"}),
    "Dex": frozenset({"dex-data-candidate/v1"}),
    "Skills": frozenset(
        {
            "codex-skill-candidate/v1",
            "claude-skill-candidate/v1",
            "dual-host-skill-candidate/v1",
        }
    ),
    "Repositories": frozenset({"repository-change-candidate/v1"}),
}
TARGET_OWNERS = frozenset(OWNER_CONTRACTS)

# Callers may acknowledge these requirements but may neither replace nor trim them.
_OWNER_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "Dunbar": ("explicit owner write authority", "Dunbar validation"),
    "Corkboard": (
        "explicit reminder creation authority",
        "Corkboard validation",
    ),
    "Dennis": ("explicit project-control authority", "Dennis validation"),
    "Continuity": ("explicit Continuity operation", "NOVA_CONTINUITY_HOME"),
    "Giles": (
        "explicit custody or disposition authority",
        "source-owner verification",
    ),
    "Dex": ("explicit data-system authority", "lineage validation"),
    "Skills": (
        "skill-creator review",
        "independent verification",
        "explicit install authority",
    ),
    "Repositories": (
        "repository-scoped authority",
        "review and rollback evidence",
    ),
}

_ADMITTED_REVIEWS = frozenset({"accepted", "verified"})
_SAFE_SOURCE_RIGHTS = frozenset({"self_authored", "quoted_excerpt", "licensed"})
_SENSITIVITY_RANK = {
    "public": 0,
    "personal": 1,
    "private": 2,
    "restricted": 3,
}
_FORBIDDEN_CONTROL_KEYS = frozenset(
    {
        "authority",
        "authorization",
        "system_instruction",
        "tool_call",
        "execute",
        "command",
        "shell",
        "install",
        "write",
        "mutation",
    }
)
_EVIDENCE_TYPES = frozenset(
    {
        "owner_validation",
        "skill_creator_review",
        "independent_verification",
        "test_report",
        "review_record",
        "source_record",
    }
)
_SKILL_EVIDENCE_TYPES = frozenset(
    {"skill_creator_review", "independent_verification"}
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _required_text(value: Any, *, field: str, limit: int = 100_000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} must be a non-empty string")
    text = value.strip()
    if len(text) > limit:
        raise ValidationError(f"{field} exceeds {limit} characters")
    return text


def _string_list(value: Any, *, field: str, required: bool = False) -> list[str]:
    if value is None:
        value = []
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValidationError(f"{field} must be an array of strings")
    result: list[str] = []
    for item in value:
        text = _required_text(item, field=field, limit=16_384)
        if text not in result:
            result.append(text)
    if required and not result:
        raise ValidationError(f"{field} must not be empty")
    return result


def _sha256(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise ValidationError(f"{field} must be lowercase SHA-256")
    return value


def _safe_payload(value: Any, *, path: str = "proposed_payload") -> Any:
    """Copy JSON data while rejecting fields that could masquerade as authority."""

    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for raw_key, child in value.items():
            if not isinstance(raw_key, str) or not raw_key:
                raise ValidationError(f"{path} keys must be non-empty strings")
            if raw_key.casefold() in _FORBIDDEN_CONTROL_KEYS:
                raise ValidationError(
                    f"{path}.{raw_key} is an execution or authority field; "
                    "promotion packets are data-only"
                )
            result[raw_key] = _safe_payload(child, path=f"{path}.{raw_key}")
        canonical_json_bytes(result)
        return result
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        result = [_safe_payload(child, path=f"{path}[]") for child in value]
        canonical_json_bytes(result)
        return result
    canonical_json_bytes(value)
    return deepcopy(value)


def _source_bindings(
    snapshot: Mapping[str, Any], raw_sources: Any
) -> tuple[list[dict[str, Any]], str]:
    if isinstance(raw_sources, (str, bytes)) or not isinstance(raw_sources, Sequence):
        raise ValidationError("source_records must be a non-empty array")
    if not raw_sources:
        raise ValidationError("source_records must be a non-empty array")
    bindings: list[dict[str, Any]] = []
    seen: set[str] = set()
    sensitivity = "public"
    records = snapshot["records"]
    for index, raw in enumerate(raw_sources):
        field = f"source_records[{index}]"
        if isinstance(raw, str):
            record_id = validate_record_id(raw, field=field)
            expected_revision = None
        elif isinstance(raw, Mapping):
            unknown = set(raw) - {"record_id", "revision"}
            if unknown:
                raise ValidationError(
                    f"{field} contains unsupported fields: {sorted(unknown)}"
                )
            record_id = validate_record_id(
                raw.get("record_id"), field=f"{field}.record_id"
            )
            expected_revision = raw.get("revision")
            if expected_revision is not None and (
                isinstance(expected_revision, bool)
                or not isinstance(expected_revision, int)
                or expected_revision < 1
            ):
                raise ValidationError(f"{field}.revision must be a positive integer")
        else:
            raise ValidationError(f"{field} must be a record id or object")
        if record_id in seen:
            raise ValidationError(f"{field} duplicates {record_id}")
        seen.add(record_id)
        record = records.get(record_id)
        if record is None:
            raise ValidationError(
                f"source Commonplace record does not exist: {record_id}"
            )
        if record["kind"] == "promotion_proposal":
            raise ValidationError("a promotion proposal cannot source another promotion")
        if record["lifecycle"] != "current":
            raise ValidationError(
                f"source Commonplace record is not current: {record_id}"
            )
        if expected_revision is not None and record["revision"] != expected_revision:
            raise ConflictError(
                f"source revision changed for {record_id}: "
                f"expected {expected_revision}, found {record['revision']}"
            )
        if _SENSITIVITY_RANK[record["sensitivity"]] > _SENSITIVITY_RANK[sensitivity]:
            sensitivity = record["sensitivity"]
        bindings.append(
            {
                "record_id": record_id,
                "revision": record["revision"],
                "record_sha256": digest_object(record),
                "sensitivity": record["sensitivity"],
            }
        )
    return bindings, sensitivity


def _validate_target_owner(value: Any) -> str:
    owner = _required_text(value, field="target_owner", limit=64)
    if owner not in TARGET_OWNERS:
        raise ValidationError(f"target_owner must be one of {sorted(TARGET_OWNERS)}")
    return owner


def _validate_target_contract(owner: str, value: Any, *, field: str) -> str:
    contract = _required_text(value, field=field, limit=4_096)
    allowed = OWNER_CONTRACTS[owner]
    if contract not in allowed:
        raise ValidationError(
            f"{field} must be one of {sorted(allowed)} for target owner {owner}"
        )
    return contract


def _validate_required_authority(owner: str, value: Any) -> list[str]:
    required = list(_OWNER_REQUIREMENTS[owner])
    if value is None:
        return required
    supplied = _string_list(value, field="required_authority", required=True)
    if supplied != required:
        raise ValidationError(
            "required_authority is fixed by the target-owner contract and "
            "cannot be replaced, reordered, or reduced"
        )
    return required


def _typed_evidence(
    value: Any,
    *,
    bindings: Sequence[Mapping[str, Any]],
    field: str = "validation_evidence",
) -> list[dict[str, str]]:
    if value is None:
        value = []
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValidationError(f"{field} must be an array of typed evidence objects")
    bound = {item["record_id"]: item for item in bindings}
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    exact_keys = {
        "evidence_type",
        "evidence_ref",
        "content_sha256",
        "source_record_id",
        "source_record_sha256",
    }
    for index, raw in enumerate(value):
        item_field = f"{field}[{index}]"
        if not isinstance(raw, Mapping) or set(raw) != exact_keys:
            raise ValidationError(
                f"{item_field} must contain exactly {sorted(exact_keys)}"
            )
        evidence_type = _required_text(
            raw.get("evidence_type"), field=f"{item_field}.evidence_type", limit=64
        )
        if evidence_type not in _EVIDENCE_TYPES:
            raise ValidationError(
                f"{item_field}.evidence_type must be one of {sorted(_EVIDENCE_TYPES)}"
            )
        evidence_ref = _required_text(
            raw.get("evidence_ref"), field=f"{item_field}.evidence_ref", limit=16_384
        )
        content_sha256 = _sha256(
            raw.get("content_sha256"), field=f"{item_field}.content_sha256"
        )
        source_record_id = validate_record_id(
            raw.get("source_record_id"), field=f"{item_field}.source_record_id"
        )
        source_record_sha256 = _sha256(
            raw.get("source_record_sha256"),
            field=f"{item_field}.source_record_sha256",
        )
        binding = bound.get(source_record_id)
        if binding is None or binding["record_sha256"] != source_record_sha256:
            raise ValidationError(
                f"{item_field} is not provenance-bound to an exact proposal source"
            )
        identity = (evidence_type, evidence_ref, content_sha256)
        if identity in seen:
            raise ValidationError(f"{item_field} duplicates another evidence item")
        seen.add(identity)
        result.append(
            {
                "evidence_type": evidence_type,
                "evidence_ref": evidence_ref,
                "content_sha256": content_sha256,
                "source_record_id": source_record_id,
                "source_record_sha256": source_record_sha256,
            }
        )
    canonical_json_bytes(result)
    return result


def create_promotion_proposal(
    store: CommonplaceStore,
    payload: Mapping[str, Any],
    *,
    authority: str | Mapping[str, Any],
    expected_generation: int,
    idempotency_key: str,
    now: str | None = None,
) -> dict[str, Any]:
    """Commit a reviewable proposal to Commonplace without touching its target."""

    if not isinstance(payload, Mapping):
        raise ValidationError("promotion proposal must be an object")
    allowed = {
        "proposal_id",
        "title",
        "summary",
        "target_owner",
        "target_contract",
        "source_records",
        "proposed_payload",
        "required_authority",
        "validation_evidence",
        "rollback",
        "risks",
        "expires_at",
        "origin",
        "review",
        "sensitivity",
    }
    unknown = set(payload) - allowed
    if unknown:
        raise ValidationError(
            f"promotion proposal contains unsupported fields: {sorted(unknown)}"
        )
    proposal_id = validate_record_id(payload.get("proposal_id"), field="proposal_id")
    title = _required_text(payload.get("title"), field="title", limit=4_096)
    summary = _required_text(payload.get("summary"), field="summary")
    owner = _validate_target_owner(payload.get("target_owner"))
    target_contract = _validate_target_contract(
        owner, payload.get("target_contract"), field="target_contract"
    )
    proposed_payload = payload.get("proposed_payload")
    if not isinstance(proposed_payload, Mapping):
        raise ValidationError("proposed_payload must be a JSON object")
    safe_payload = _safe_payload(proposed_payload)
    timestamp = validate_timestamp(now or utc_now(), field="now", optional=False)
    expires_at = validate_timestamp(payload.get("expires_at"), field="expires_at")
    if expires_at is not None and expires_at <= timestamp:
        raise ValidationError("expires_at must be later than proposal creation time")

    pointer, snapshot, snapshot_digest = store.read_current()
    if snapshot["generation"] != expected_generation:
        raise ConflictError(
            f"expected generation {expected_generation}, current generation is "
            f"{snapshot['generation']}"
        )
    bindings, minimum_sensitivity = _source_bindings(
        snapshot, payload.get("source_records")
    )
    requested_sensitivity = payload.get("sensitivity", minimum_sensitivity)
    if requested_sensitivity not in SENSITIVITIES:
        raise ValidationError(f"sensitivity must be one of {sorted(SENSITIVITIES)}")
    if _SENSITIVITY_RANK[requested_sensitivity] < _SENSITIVITY_RANK[minimum_sensitivity]:
        raise ValidationError(
            "promotion proposal sensitivity cannot be lower than its most sensitive source"
        )
    origin = payload.get("origin", "model_inferred")
    if origin not in {"user_authored", "model_inferred"}:
        raise ValidationError(
            "promotion proposal origin must be user_authored or model_inferred"
        )
    review = payload.get(
        "review", "accepted" if origin == "user_authored" else "unreviewed"
    )
    if origin == "model_inferred" and review != "unreviewed":
        raise ValidationError("model-inferred promotion proposals must remain unreviewed")
    if review not in {"unreviewed", "accepted"}:
        raise ValidationError(
            "new promotion proposal review must be unreviewed or accepted"
        )

    required_authority = _validate_required_authority(
        owner, payload.get("required_authority")
    )
    validation_evidence = _typed_evidence(
        payload.get("validation_evidence"), bindings=bindings
    )
    risks = _string_list(payload.get("risks"), field="risks")
    rollback = _required_text(
        payload.get("rollback"), field="rollback", limit=16_384
    )
    promotion = {
        "schema": PROPOSAL_SCHEMA,
        "target_owner": owner,
        "target_contract": target_contract,
        "source_binding": {
            "workspace_id": snapshot["workspace_id"],
            "generation": snapshot["generation"],
            "snapshot_sha256": snapshot_digest,
            "records": bindings,
        },
        "proposed_payload": safe_payload,
        "required_authority": required_authority,
        "validation_evidence": validation_evidence,
        "rollback": rollback,
        "risks": risks,
        "expires_at": expires_at,
        "target_write_performed": False,
        "executable": False,
    }
    relation_origin = "user_authored" if origin == "user_authored" else "model_inferred"
    relation_review = "accepted" if origin == "user_authored" else "unreviewed"
    record = normalize_record(
        {
            "id": proposal_id,
            "kind": "promotion_proposal",
            "title": title,
            "body": summary,
            "origin": origin,
            "review": review,
            "dispute": "undisputed",
            "lifecycle": "current",
            "sensitivity": requested_sensitivity,
            "rights": "self_authored",
            "time": {"observed_at": timestamp, "valid_to": expires_at},
            "provenance": [
                {
                    "source_type": "record",
                    "source_ref": item["record_id"],
                    "content_sha256": item["record_sha256"],
                    "retrieved_at": timestamp,
                }
                for item in bindings
            ],
            "relations": [
                {
                    "type": "proposes_promotion_of",
                    "target_id": item["record_id"],
                    "origin": relation_origin,
                    "review": relation_review,
                }
                for item in bindings
            ],
            "metadata": {"promotion": promotion},
        },
        now=timestamp,
    )
    # Generic put cannot create this subtype. The store revalidates its exact
    # parent binding under lock through this narrow insertion path.
    commit = store._put_promotion_proposal(
        record,
        authority=authority,
        expected_generation=expected_generation,
        idempotency_key=idempotency_key,
    )
    return {
        "ok": True,
        "operation": "propose_promotion",
        "canonical": True,
        "proposal_id": proposal_id,
        "target_owner": owner,
        "target_write_performed": False,
        "writes_allowed": {"commonplace": True, "target_owner": False},
        "commit": commit,
        "source_pointer": pointer,
    }


def _proposal_metadata(record: Mapping[str, Any]) -> dict[str, Any]:
    """Revalidate the complete subtype contract on every canonical read."""

    if record.get("kind") != "promotion_proposal":
        raise ValidationError("record is not a promotion proposal")
    metadata = record.get("metadata")
    if not isinstance(metadata, Mapping) or set(metadata) != {"promotion"}:
        raise ValidationError(
            "promotion proposal metadata must contain exactly the promotion contract"
        )
    promotion = metadata.get("promotion")
    if not isinstance(promotion, Mapping) or promotion.get("schema") != PROPOSAL_SCHEMA:
        raise ValidationError("promotion proposal metadata is missing or incompatible")
    required_keys = {
        "schema",
        "target_owner",
        "target_contract",
        "source_binding",
        "proposed_payload",
        "required_authority",
        "validation_evidence",
        "rollback",
        "risks",
        "expires_at",
        "target_write_performed",
        "executable",
    }
    if set(promotion) != required_keys:
        raise ValidationError(
            "promotion proposal metadata fields do not match its versioned contract"
        )
    owner = _validate_target_owner(promotion.get("target_owner"))
    target_contract = _validate_target_contract(
        owner,
        promotion.get("target_contract"),
        field="promotion.target_contract",
    )
    proposed_payload = promotion.get("proposed_payload")
    if not isinstance(proposed_payload, Mapping):
        raise ValidationError("promotion.proposed_payload must be an object")
    checked_payload = _safe_payload(
        proposed_payload, path="promotion.proposed_payload"
    )
    required_authority = _string_list(
        promotion.get("required_authority"),
        field="promotion.required_authority",
        required=True,
    )
    if required_authority != list(_OWNER_REQUIREMENTS[owner]):
        raise ValidationError(
            "promotion.required_authority does not match the mandatory owner contract"
        )
    risks = _string_list(promotion.get("risks"), field="promotion.risks")
    rollback = _required_text(
        promotion.get("rollback"), field="promotion.rollback", limit=16_384
    )
    expires_at = validate_timestamp(
        promotion.get("expires_at"), field="promotion.expires_at"
    )
    if promotion.get("target_write_performed") is not False:
        raise ValidationError("promotion.target_write_performed must remain false")
    if promotion.get("executable") is not False:
        raise ValidationError("promotion.executable must remain false")

    binding = promotion.get("source_binding")
    if not isinstance(binding, Mapping) or set(binding) != {
        "workspace_id",
        "generation",
        "snapshot_sha256",
        "records",
    }:
        raise ValidationError("promotion.source_binding is malformed")
    workspace_id = _required_text(
        binding.get("workspace_id"),
        field="promotion.source_binding.workspace_id",
        limit=256,
    )
    generation = binding.get("generation")
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
        raise ValidationError(
            "promotion.source_binding.generation must be non-negative"
        )
    snapshot_sha256 = _sha256(
        binding.get("snapshot_sha256"),
        field="promotion.source_binding.snapshot_sha256",
    )
    raw_records = binding.get("records")
    if (
        isinstance(raw_records, (str, bytes))
        or not isinstance(raw_records, Sequence)
        or not raw_records
    ):
        raise ValidationError(
            "promotion.source_binding.records must be a non-empty array"
        )
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_records):
        field = f"promotion.source_binding.records[{index}]"
        if not isinstance(raw, Mapping) or set(raw) != {
            "record_id",
            "revision",
            "record_sha256",
            "sensitivity",
        }:
            raise ValidationError(f"{field} is malformed")
        record_id = validate_record_id(
            raw.get("record_id"), field=f"{field}.record_id"
        )
        if record_id in seen:
            raise ValidationError(f"{field} duplicates {record_id}")
        seen.add(record_id)
        revision = raw.get("revision")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise ValidationError(f"{field}.revision must be positive")
        record_sha256 = _sha256(
            raw.get("record_sha256"), field=f"{field}.record_sha256"
        )
        sensitivity = raw.get("sensitivity")
        if sensitivity not in SENSITIVITIES:
            raise ValidationError(f"{field}.sensitivity is invalid")
        records.append(
            {
                "record_id": record_id,
                "revision": revision,
                "record_sha256": record_sha256,
                "sensitivity": sensitivity,
            }
        )

    validation_evidence = _typed_evidence(
        promotion.get("validation_evidence"),
        bindings=records,
        field="promotion.validation_evidence",
    )
    proposal_sensitivity = record.get("sensitivity")
    if proposal_sensitivity not in SENSITIVITIES:
        raise ValidationError("promotion proposal sensitivity is invalid")
    source_floor = max(
        records, key=lambda item: _SENSITIVITY_RANK[item["sensitivity"]]
    )["sensitivity"]
    if _SENSITIVITY_RANK[proposal_sensitivity] < _SENSITIVITY_RANK[source_floor]:
        raise ValidationError(
            "promotion proposal sensitivity is lower than its bound source evidence"
        )
    if record.get("rights") != "self_authored":
        raise ValidationError("promotion proposal rights must remain self_authored")
    if record.get("origin") not in {"user_authored", "model_inferred"}:
        raise ValidationError(
            "promotion proposal origin must be user_authored or model_inferred"
        )
    temporal = record.get("time")
    if not isinstance(temporal, Mapping) or temporal.get("valid_to") != expires_at:
        raise ValidationError(
            "promotion proposal valid_to must remain bound to promotion.expires_at"
        )

    provenance = record.get("provenance")
    if isinstance(provenance, (str, bytes)) or not isinstance(provenance, Sequence):
        raise ValidationError("promotion proposal provenance is malformed")
    actual_evidence: list[tuple[str, str]] = []
    for item in provenance:
        if (
            not isinstance(item, Mapping)
            or item.get("source_type") != "record"
            or not isinstance(item.get("content_sha256"), str)
        ):
            raise ValidationError(
                "promotion proposal provenance must contain only digest-bound records"
            )
        actual_evidence.append((item.get("source_ref"), item["content_sha256"]))
    expected_evidence = [
        (item["record_id"], item["record_sha256"]) for item in records
    ]
    if sorted(actual_evidence) != sorted(expected_evidence):
        raise ValidationError(
            "promotion proposal provenance must bind exactly every source record digest"
        )

    relations = record.get("relations")
    if isinstance(relations, (str, bytes)) or not isinstance(relations, Sequence):
        raise ValidationError("promotion proposal relations are malformed")
    expected_origin = (
        "user_authored" if record.get("origin") == "user_authored" else "model_inferred"
    )
    expected_review = "accepted" if expected_origin == "user_authored" else "unreviewed"
    actual_relations: list[tuple[str, str, str, str]] = []
    for item in relations:
        if not isinstance(item, Mapping) or set(item) != {
            "type",
            "target_id",
            "origin",
            "review",
        }:
            raise ValidationError(
                "promotion proposal relations must contain only exact source bindings"
            )
        actual_relations.append(
            (
                item.get("type"),
                item.get("target_id"),
                item.get("origin"),
                item.get("review"),
            )
        )
    expected_relations = [
        (
            "proposes_promotion_of",
            item["record_id"],
            expected_origin,
            expected_review,
        )
        for item in records
    ]
    if sorted(actual_relations) != sorted(expected_relations):
        raise ValidationError(
            "promotion proposal relations must bind exactly its source records"
        )

    checked = {
        "schema": PROPOSAL_SCHEMA,
        "target_owner": owner,
        "target_contract": target_contract,
        "source_binding": {
            "workspace_id": workspace_id,
            "generation": generation,
            "snapshot_sha256": snapshot_sha256,
            "records": records,
        },
        "proposed_payload": checked_payload,
        "required_authority": required_authority,
        "validation_evidence": validation_evidence,
        "rollback": rollback,
        "risks": risks,
        "expires_at": expires_at,
        "target_write_performed": False,
        "executable": False,
    }
    canonical_json_bytes(checked)
    return checked


def _validate_proposal_insertion(
    record: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    snapshot_digest: str,
) -> dict[str, Any]:
    """Store-side parent binding check used only by the dedicated insertion path."""

    promotion = _proposal_metadata(record)
    binding = promotion["source_binding"]
    if record.get("revision") != 1 or record.get("lifecycle") != "current":
        raise ValidationError(
            "new promotion proposals must begin at revision 1 and lifecycle=current"
        )
    if binding["workspace_id"] != snapshot["workspace_id"]:
        raise ConflictError("promotion source binding workspace does not match the store")
    if binding["generation"] != snapshot["generation"]:
        raise ConflictError("promotion source binding generation is no longer current")
    if binding["snapshot_sha256"] != snapshot_digest:
        raise ConflictError("promotion source binding snapshot is no longer current")
    for bound in binding["records"]:
        current = snapshot["records"].get(bound["record_id"])
        if current is None:
            raise ConflictError(
                f"promotion source disappeared before insertion: {bound['record_id']}"
            )
        if current.get("kind") == "promotion_proposal":
            raise ValidationError("a promotion proposal cannot source another promotion")
        if (
            current.get("lifecycle") != "current"
            or current.get("revision") != bound["revision"]
            or current.get("sensitivity") != bound["sensitivity"]
            or digest_object(current) != bound["record_sha256"]
        ):
            raise ConflictError(
                f"promotion source changed before insertion: {bound['record_id']}"
            )
    return promotion


def _add_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _source_eligibility_reasons(
    record: Mapping[str, Any], *, record_id: str, at: str
) -> list[str]:
    reasons: list[str] = []
    if record.get("lifecycle") != "current":
        reasons.append(f"source_not_current:{record_id}")
    if record.get("review") not in _ADMITTED_REVIEWS:
        reasons.append(f"source_not_human_admitted:{record_id}")
    if record.get("dispute") != "undisputed":
        reasons.append(f"source_disputed:{record_id}")
    if record.get("rights") not in _SAFE_SOURCE_RIGHTS:
        reasons.append(f"source_rights_unknown:{record_id}")
    validity = evaluate_record_validity(record, at=at)
    if validity["status"] != "valid":
        reasons.append(f"source_not_temporally_valid:{record_id}")
    return reasons


def _evaluate_promotion(
    store: CommonplaceStore, proposal_id: str, *, now: str | None = None
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    checked_id = validate_record_id(proposal_id, field="proposal_id")
    timestamp = validate_timestamp(now or utc_now(), field="now", optional=False)
    pointer, snapshot, snapshot_digest = store.read_current()
    proposal = snapshot["records"].get(checked_id)
    if proposal is None:
        raise KeyError(f"Commonplace promotion proposal not found: {checked_id}")
    proposal = deepcopy(proposal)
    promotion = _proposal_metadata(proposal)
    reasons: list[str] = []
    source_checks: list[dict[str, Any]] = []
    binding = promotion["source_binding"]

    if binding["workspace_id"] != snapshot["workspace_id"]:
        _add_reason(reasons, "source_binding_workspace_mismatch")
    if binding["generation"] >= snapshot["generation"]:
        _add_reason(reasons, "source_binding_generation_invalid")

    authenticated_binding = True
    for bound in binding["records"]:
        historical_status = "unchecked"
        if (
            binding["workspace_id"] == snapshot["workspace_id"]
            and binding["generation"] < snapshot["generation"]
        ):
            historical = store.get_as_of(
                bound["record_id"], generation=binding["generation"]
            )
            if historical.get("current_snapshot_sha256") != snapshot_digest:
                raise ConflictError(
                    "Commonplace changed while promotion evidence was evaluated"
                )
            historical_status = historical.get("status", "unknown")
            historical_record = historical.get("record")
            if (
                historical_status != "found"
                or historical.get("selected_snapshot_sha256")
                != binding["snapshot_sha256"]
                or not isinstance(historical_record, Mapping)
                or digest_object(historical_record) != bound["record_sha256"]
            ):
                authenticated_binding = False
        else:
            authenticated_binding = False
        current = snapshot["records"].get(bound["record_id"])
        status = "current"
        if current is None:
            status = "absent"
        elif current["lifecycle"] != "current":
            status = "not_current"
        elif current["revision"] != bound["revision"]:
            status = "revision_changed"
        elif digest_object(current) != bound["record_sha256"]:
            status = "content_changed"
        if status != "current":
            _add_reason(reasons, f"source_{status}:{bound['record_id']}")
        else:
            for reason in _source_eligibility_reasons(
                current, record_id=bound["record_id"], at=timestamp
            ):
                _add_reason(reasons, reason)
        source_checks.append(
            {
                "record_id": bound["record_id"],
                "bound_revision": bound["revision"],
                "status": status,
                "current_revision": current.get("revision") if current else None,
                "historical_binding": historical_status,
            }
        )
    if not authenticated_binding:
        _add_reason(reasons, "source_binding_not_authenticated")

    if proposal["review"] not in _ADMITTED_REVIEWS:
        _add_reason(reasons, "proposal_not_human_admitted")
    if proposal["dispute"] != "undisputed":
        _add_reason(reasons, "proposal_disputed")
    if proposal["lifecycle"] != "current":
        _add_reason(reasons, "proposal_not_current")
    expires_at = promotion.get("expires_at")
    if isinstance(expires_at, str) and expires_at <= timestamp:
        _add_reason(reasons, "proposal_expired")

    if promotion["target_owner"] == "Skills":
        present_types = {
            item["evidence_type"] for item in promotion["validation_evidence"]
        }
        if not _SKILL_EVIDENCE_TYPES.issubset(present_types):
            _add_reason(reasons, "skill_validation_evidence_missing")

    final_pointer, final_snapshot, final_digest = store.read_current()
    if (
        final_digest != snapshot_digest
        or final_pointer != pointer
        or final_snapshot["workspace_id"] != snapshot["workspace_id"]
        or final_snapshot["generation"] != snapshot["generation"]
        or final_snapshot["records"].get(checked_id) != proposal
    ):
        raise ConflictError("Commonplace changed while promotion plan was evaluated")

    eligible = not reasons
    plan = {
        "ok": True,
        "schema": PLAN_SCHEMA,
        "operation": "promotion_plan",
        "canonical": False,
        "proposal_id": checked_id,
        "target_owner": promotion["target_owner"],
        "target_contract": promotion["target_contract"],
        "status": "eligible_for_handoff" if eligible else "blocked",
        "eligible_for_handoff": eligible,
        "target_write_performed": False,
        "writes_allowed": False,
        "reasons": reasons,
        "source_checks": source_checks,
        "required_authority": deepcopy(promotion["required_authority"]),
        "validation_evidence": deepcopy(promotion["validation_evidence"]),
        "rollback": promotion["rollback"],
        "risks": deepcopy(promotion["risks"]),
        "binding": {
            "workspace_id": snapshot["workspace_id"],
            "generation": snapshot["generation"],
            "snapshot_sha256": snapshot_digest,
            "pointer": pointer["snapshot"],
            "proposal_revision": proposal["revision"],
            "proposal_sha256": digest_object(proposal),
            "source_snapshot_sha256": binding["snapshot_sha256"],
            "source_generation": binding["generation"],
        },
    }
    return plan, proposal, promotion


def promotion_plan(
    store: CommonplaceStore, proposal_id: str, *, now: str | None = None
) -> dict[str, Any]:
    """Evaluate review, evidence, freshness, and authority gates read-only."""

    plan, _, _ = _evaluate_promotion(store, proposal_id, now=now)
    return plan


def export_promotion_handoff(
    store: CommonplaceStore, proposal_id: str, *, now: str | None = None
) -> dict[str, Any]:
    """Return one exact data-only packet for a separately authorized owner workflow."""

    plan, evaluated_proposal, promotion = _evaluate_promotion(
        store, proposal_id, now=now
    )
    if not plan["eligible_for_handoff"]:
        raise ConflictError(
            "promotion proposal is not eligible for handoff: "
            + ", ".join(plan["reasons"])
        )

    # Recheck CURRENT and emit only the object retained from the evaluated snapshot.
    pointer, snapshot, snapshot_digest = store.read_current()
    current = snapshot["records"].get(proposal_id)
    binding = plan["binding"]
    if (
        snapshot_digest != binding["snapshot_sha256"]
        or snapshot["workspace_id"] != binding["workspace_id"]
        or snapshot["generation"] != binding["generation"]
        or pointer.get("snapshot") != binding["pointer"]
        or current != evaluated_proposal
        or not isinstance(current, Mapping)
        or digest_object(current) != binding["proposal_sha256"]
        or current.get("revision") != binding["proposal_revision"]
    ):
        raise ConflictError(
            "promotion proposal or its canonical binding changed before export"
        )
    if _proposal_metadata(current) != promotion:
        raise ConflictError("promotion proposal subtype changed before export")

    return {
        "ok": True,
        "schema": HANDOFF_SCHEMA,
        "operation": "promotion_handoff",
        "canonical": False,
        "executable": False,
        "writes_allowed": False,
        "target_write_performed": False,
        "proposal_id": proposal_id,
        "proposal_record_sha256": binding["proposal_sha256"],
        "target_owner": promotion["target_owner"],
        "target_contract": promotion["target_contract"],
        "proposed_payload": deepcopy(promotion["proposed_payload"]),
        "source_binding": deepcopy(promotion["source_binding"]),
        "required_authority": deepcopy(promotion["required_authority"]),
        "validation_evidence": deepcopy(promotion["validation_evidence"]),
        "rollback": promotion["rollback"],
        "risks": deepcopy(promotion["risks"]),
        "plan_binding": deepcopy(binding),
        "next_step": (
            "Present this packet to the named owner's canonical workflow under fresh, "
            "explicit authority. This packet is evidence, not authorization."
        ),
    }


__all__ = [
    "HANDOFF_SCHEMA",
    "OWNER_CONTRACTS",
    "PLAN_SCHEMA",
    "PROPOSAL_SCHEMA",
    "TARGET_OWNERS",
    "create_promotion_proposal",
    "export_promotion_handoff",
    "promotion_plan",
]
