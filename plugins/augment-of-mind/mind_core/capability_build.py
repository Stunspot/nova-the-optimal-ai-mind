"""Compile a reviewed capability estate into canonical MIND Core assets.

The compiler deliberately starts after discovery and semantic authoring. Its input is
reviewed, host-neutral metadata: no raw skill bodies and no host filesystem paths. It
normalizes that input, derives every Core binding digest and float32 vector row, and
returns the bootstrap and associative-index manifests as one deterministic result.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Sequence
from typing import Any

from .association_math import (
    LEXICAL_CUE_MEMBERSHIP_CONTRACT,
    LEXICAL_PROFILE_ID,
    LEXICAL_UNICODE_TOKEN_GRAMMAR,
    MAX_VECTOR_DIMENSIONS,
    coerce_float32_vector,
    pack_float32_vector,
    within_radius,
)
from .constants import CAPABILITY_EXPOSURE_POLICIES, LIFECYCLE_STATES
from .errors import ValidationError
from .reminders import QUALIFICATION_STATES, RELATION_KINDS, VIEW_KINDS
from .util import (
    canonical_json,
    parse_timestamp,
    require_identifier,
    require_sha256,
    require_text,
    sha256_text,
    timestamp,
)


REVIEWED_ESTATE_FORMAT = "mind-reviewed-capability-estate/v1"
VIEW_ORDER = (
    "transformation",
    "situation",
    "positive_cue",
    "error_or_correction",
    "negative_boundary",
    "example",
)

_WINDOWS_PATH = re.compile(r"[A-Za-z]:")


def _exact_object(
    value: object,
    *,
    required: frozenset[str],
    field: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{field} must be an object")
    missing = required - set(value)
    unknown = set(value) - required
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append("missing=" + ",".join(sorted(missing)))
        if unknown:
            details.append("unsupported=" + ",".join(sorted(unknown)))
        raise ValidationError(f"invalid {field}: " + "; ".join(details))
    return value


def _array(value: object, field: str, *, nonempty: bool = False) -> list[Any]:
    if not isinstance(value, list) or (nonempty and not value):
        suffix = "non-empty " if nonempty else ""
        raise ValidationError(f"{field} must be a {suffix}array")
    return value


def _normalized_timestamp(value: object, field: str) -> str:
    return timestamp(parse_timestamp(value, field))


def _nullable_identifier(value: object, field: str) -> str | None:
    return require_identifier(value, field) if value is not None else None


def _positive_integer(value: object, field: str, *, maximum: int) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
        or value > maximum
    ):
        raise ValidationError(f"{field} must be an integer between 1 and {maximum}")
    return value


def _nonnegative_integer(value: object, field: str, *, maximum: int) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        or value > maximum
    ):
        raise ValidationError(f"{field} must be an integer between 0 and {maximum}")
    return value


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{field} must be numeric")
    return float(value)


def _host_neutral_reference(
    value: object, field: str, *, maximum: int = 4096
) -> str:
    result = require_text(value, field, maximum=maximum)
    folded = result.casefold()
    if (
        _WINDOWS_PATH.match(result)
        or result.startswith(("/", "\\"))
        or "\\" in result
        or folded.startswith("file:")
        or ".." in result.split("/")
    ):
        raise ValidationError(f"{field} must not contain a host filesystem path")
    return result


def _optional_host_neutral_reference(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _host_neutral_reference(value, field)


def _record_digest(record: dict[str, Any], digest_field: str) -> str:
    return sha256_text(
        canonical_json(
            {key: value for key, value in record.items() if key != digest_field}
        )
    )


def _unique(records: Sequence[dict[str, Any]], key: str, field: str) -> None:
    values = [record[key] for record in records]
    if len(values) != len(set(values)):
        raise ValidationError(f"{field} contain duplicate {key} values")


def _normalize_sources(value: object) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, candidate in enumerate(_array(value, "sources", nonempty=True)):
        item = _exact_object(
            candidate,
            required=frozenset(
                {
                    "source_id",
                    "locator",
                    "digest",
                    "custody_state",
                    "authority_ref",
                    "observed_at",
                }
            ),
            field=f"sources[{index}]",
        )
        custody_state = require_identifier(
            item["custody_state"], f"sources[{index}].custody_state"
        )
        if custody_state not in LIFECYCLE_STATES["custody"]:
            raise ValidationError(f"unsupported custody state: {custody_state}")
        records.append(
            {
                "source_id": require_identifier(
                    item["source_id"], f"sources[{index}].source_id"
                ),
                "locator": _host_neutral_reference(
                    item["locator"], f"sources[{index}].locator"
                ),
                "digest": require_sha256(
                    item["digest"], f"sources[{index}].digest"
                ),
                "custody_state": custody_state,
                "authority_ref": require_text(
                    item["authority_ref"],
                    f"sources[{index}].authority_ref",
                    maximum=2048,
                ),
                "observed_at": _normalized_timestamp(
                    item["observed_at"], f"sources[{index}].observed_at"
                ),
            }
        )
    _unique(records, "source_id", "sources")
    return sorted(records, key=lambda record: record["source_id"])


def _normalize_products(value: object) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, candidate in enumerate(_array(value, "products")):
        item = _exact_object(
            candidate,
            required=frozenset(
                {"product_id", "name", "owner", "canonical_uri", "created_at"}
            ),
            field=f"products[{index}]",
        )
        records.append(
            {
                "product_id": require_identifier(
                    item["product_id"], f"products[{index}].product_id"
                ),
                "name": require_text(
                    item["name"], f"products[{index}].name", maximum=512
                ),
                "owner": require_text(
                    item["owner"], f"products[{index}].owner", maximum=512
                ),
                "canonical_uri": _optional_host_neutral_reference(
                    item["canonical_uri"], f"products[{index}].canonical_uri"
                ),
                "created_at": _normalized_timestamp(
                    item["created_at"], f"products[{index}].created_at"
                ),
            }
        )
    _unique(records, "product_id", "products")
    return sorted(records, key=lambda record: record["product_id"])


def _normalize_providers(value: object) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, candidate in enumerate(_array(value, "providers")):
        item = _exact_object(
            candidate,
            required=frozenset(
                {
                    "provider_id",
                    "name",
                    "owner",
                    "provider_kind",
                    "canonical_uri",
                    "created_at",
                }
            ),
            field=f"providers[{index}]",
        )
        records.append(
            {
                "provider_id": require_identifier(
                    item["provider_id"], f"providers[{index}].provider_id"
                ),
                "name": require_text(
                    item["name"], f"providers[{index}].name", maximum=512
                ),
                "owner": require_text(
                    item["owner"], f"providers[{index}].owner", maximum=512
                ),
                "provider_kind": require_identifier(
                    item["provider_kind"], f"providers[{index}].provider_kind"
                ),
                "canonical_uri": _optional_host_neutral_reference(
                    item["canonical_uri"], f"providers[{index}].canonical_uri"
                ),
                "created_at": _normalized_timestamp(
                    item["created_at"], f"providers[{index}].created_at"
                ),
            }
        )
    _unique(records, "provider_id", "providers")
    return sorted(records, key=lambda record: record["provider_id"])


def _normalize_aliases(value: object, field: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, candidate in enumerate(_array(value, field)):
        item = _exact_object(
            candidate,
            required=frozenset({"namespace", "alias", "display_alias"}),
            field=f"{field}[{index}]",
        )
        namespace = require_identifier(
            item["namespace"], f"{field}[{index}].namespace"
        )
        alias = require_text(
            item["alias"], f"{field}[{index}].alias", maximum=512
        )
        key = (namespace, alias.casefold())
        if key in seen:
            raise ValidationError(f"{field} contain duplicate normalized aliases")
        seen.add(key)
        records.append(
            {
                "namespace": namespace,
                "alias": alias,
                "display_alias": require_text(
                    item["display_alias"],
                    f"{field}[{index}].display_alias",
                    maximum=512,
                ),
            }
        )
    return sorted(
        records,
        key=lambda record: (
            record["namespace"],
            record["alias"].casefold(),
            record["display_alias"],
        ),
    )


def _normalize_entrypoints(value: object, field: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, candidate in enumerate(_array(value, field)):
        item = _exact_object(
            candidate,
            required=frozenset(
                {"entrypoint_id", "entrypoint_kind", "locator", "operation"}
            ),
            field=f"{field}[{index}]",
        )
        records.append(
            {
                "entrypoint_id": require_identifier(
                    item["entrypoint_id"], f"{field}[{index}].entrypoint_id"
                ),
                "entrypoint_kind": require_identifier(
                    item["entrypoint_kind"], f"{field}[{index}].entrypoint_kind"
                ),
                "locator": _host_neutral_reference(
                    item["locator"], f"{field}[{index}].locator"
                ),
                "operation": require_text(
                    item["operation"], f"{field}[{index}].operation", maximum=1024
                ),
            }
        )
    _unique(records, "entrypoint_id", field)
    return sorted(records, key=lambda record: record["entrypoint_id"])


def _normalize_capabilities(value: object) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, candidate in enumerate(_array(value, "capabilities", nonempty=True)):
        item = _exact_object(
            candidate,
            required=frozenset(
                {
                    "capability_id",
                    "handle",
                    "name",
                    "product_id",
                    "canonical_source_id",
                    "promise",
                    "negative_space",
                    "created_at",
                    "superseded_by",
                    "exposure_policy",
                    "owner_agent_instance_id",
                    "aliases",
                    "entrypoints",
                }
            ),
            field=f"capabilities[{index}]",
        )
        exposure = require_identifier(
            item["exposure_policy"], f"capabilities[{index}].exposure_policy"
        )
        if exposure not in CAPABILITY_EXPOSURE_POLICIES:
            raise ValidationError(f"unsupported exposure_policy: {exposure}")
        owner = _nullable_identifier(
            item["owner_agent_instance_id"],
            f"capabilities[{index}].owner_agent_instance_id",
        )
        if (exposure == "public_safe") != (owner is None):
            raise ValidationError(
                "public capabilities require no owner; private capabilities require one"
            )
        records.append(
            {
                "capability_id": require_identifier(
                    item["capability_id"], f"capabilities[{index}].capability_id"
                ),
                "handle": require_identifier(
                    item["handle"], f"capabilities[{index}].handle"
                ).lower(),
                "name": require_text(
                    item["name"], f"capabilities[{index}].name", maximum=512
                ),
                "product_id": _nullable_identifier(
                    item["product_id"], f"capabilities[{index}].product_id"
                ),
                "canonical_source_id": _nullable_identifier(
                    item["canonical_source_id"],
                    f"capabilities[{index}].canonical_source_id",
                ),
                "promise": require_text(
                    item["promise"], f"capabilities[{index}].promise", maximum=4096
                ),
                "negative_space": require_text(
                    item["negative_space"],
                    f"capabilities[{index}].negative_space",
                    maximum=4096,
                ),
                "created_at": _normalized_timestamp(
                    item["created_at"], f"capabilities[{index}].created_at"
                ),
                "superseded_by": _nullable_identifier(
                    item["superseded_by"], f"capabilities[{index}].superseded_by"
                ),
                "exposure_policy": exposure,
                "owner_agent_instance_id": owner,
                "aliases": _normalize_aliases(
                    item["aliases"], f"capabilities[{index}].aliases"
                ),
                "entrypoints": _normalize_entrypoints(
                    item["entrypoints"], f"capabilities[{index}].entrypoints"
                ),
            }
        )
    _unique(records, "capability_id", "capabilities")
    _unique(records, "handle", "capabilities")
    return sorted(records, key=lambda record: record["capability_id"])


def _normalize_distributions(value: object) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, candidate in enumerate(_array(value, "distributions")):
        item = _exact_object(
            candidate,
            required=frozenset(
                {
                    "distribution_id",
                    "capability_id",
                    "product_id",
                    "provider_id",
                    "version",
                    "package_form",
                    "artifact_digest",
                    "source_id",
                    "created_at",
                }
            ),
            field=f"distributions[{index}]",
        )
        artifact_digest = item["artifact_digest"]
        records.append(
            {
                "distribution_id": require_identifier(
                    item["distribution_id"],
                    f"distributions[{index}].distribution_id",
                ),
                "capability_id": require_identifier(
                    item["capability_id"],
                    f"distributions[{index}].capability_id",
                ),
                "product_id": _nullable_identifier(
                    item["product_id"], f"distributions[{index}].product_id"
                ),
                "provider_id": require_identifier(
                    item["provider_id"], f"distributions[{index}].provider_id"
                ),
                "version": require_text(
                    item["version"], f"distributions[{index}].version", maximum=128
                ),
                "package_form": require_identifier(
                    item["package_form"], f"distributions[{index}].package_form"
                ),
                "artifact_digest": (
                    require_sha256(
                        artifact_digest,
                        f"distributions[{index}].artifact_digest",
                    )
                    if artifact_digest is not None
                    else None
                ),
                "source_id": _nullable_identifier(
                    item["source_id"], f"distributions[{index}].source_id"
                ),
                "created_at": _normalized_timestamp(
                    item["created_at"], f"distributions[{index}].created_at"
                ),
            }
        )
    _unique(records, "distribution_id", "distributions")
    return sorted(records, key=lambda record: record["distribution_id"])


def _validate_bootstrap_references(
    *,
    sources: Sequence[dict[str, Any]],
    products: Sequence[dict[str, Any]],
    providers: Sequence[dict[str, Any]],
    capabilities: Sequence[dict[str, Any]],
    distributions: Sequence[dict[str, Any]],
) -> None:
    source_ids = {record["source_id"] for record in sources}
    product_ids = {record["product_id"] for record in products}
    provider_ids = {record["provider_id"] for record in providers}
    capability_ids = {record["capability_id"] for record in capabilities}
    for capability in capabilities:
        if (
            capability["product_id"] is not None
            and capability["product_id"] not in product_ids
        ):
            raise ValidationError("capability product is absent from the estate")
        if (
            capability["canonical_source_id"] is not None
            and capability["canonical_source_id"] not in source_ids
        ):
            raise ValidationError(
                "capability canonical source is absent from the estate"
            )
        superseded_by = capability["superseded_by"]
        if superseded_by is not None:
            if superseded_by == capability["capability_id"]:
                raise ValidationError("capability cannot supersede itself")
            if superseded_by not in capability_ids:
                raise ValidationError(
                    "capability successor is absent from the estate"
                )
    for distribution in distributions:
        if distribution["capability_id"] not in capability_ids:
            raise ValidationError("distribution capability is absent from the estate")
        if (
            distribution["product_id"] is not None
            and distribution["product_id"] not in product_ids
        ):
            raise ValidationError("distribution product is absent from the estate")
        if distribution["provider_id"] not in provider_ids:
            raise ValidationError("distribution provider is absent from the estate")
        if (
            distribution["source_id"] is not None
            and distribution["source_id"] not in source_ids
        ):
            raise ValidationError("distribution source is absent from the estate")


def _normalize_lexical_profile(value: object) -> dict[str, Any]:
    item = _exact_object(
        value,
        required=frozenset(
            {
                "lexical_profile_id",
                "name",
                "normalization_contract",
                "unicode_token_grammar",
                "cue_membership_contract",
                "created_at",
            }
        ),
        field="lexical_profile",
    )
    record = {
        "lexical_profile_id": require_identifier(
            item["lexical_profile_id"], "lexical_profile.lexical_profile_id"
        ),
        "name": require_text(
            item["name"], "lexical_profile.name", maximum=256
        ),
        "normalization_contract": require_identifier(
            item["normalization_contract"],
            "lexical_profile.normalization_contract",
        ),
        "unicode_token_grammar": require_text(
            item["unicode_token_grammar"],
            "lexical_profile.unicode_token_grammar",
            maximum=1024,
        ),
        "cue_membership_contract": require_text(
            item["cue_membership_contract"],
            "lexical_profile.cue_membership_contract",
            maximum=1024,
        ),
        "created_at": _normalized_timestamp(
            item["created_at"], "lexical_profile.created_at"
        ),
    }
    if record["normalization_contract"] != LEXICAL_PROFILE_ID:
        raise ValidationError("unsupported lexical normalization contract")
    if record["unicode_token_grammar"] != LEXICAL_UNICODE_TOKEN_GRAMMAR:
        raise ValidationError("lexical profile token grammar is not executable here")
    if record["cue_membership_contract"] != LEXICAL_CUE_MEMBERSHIP_CONTRACT:
        raise ValidationError("lexical profile cue membership contract is unsupported")
    record["profile_digest"] = _record_digest(record, "profile_digest")
    return record


def _normalize_embedding_profile(
    value: object, provider_ids: set[str]
) -> dict[str, Any]:
    item = _exact_object(
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
                "created_at",
            }
        ),
        field="embedding_profile",
    )
    provider_id = _nullable_identifier(
        item["provider_id"], "embedding_profile.provider_id"
    )
    if provider_id is not None and provider_id not in provider_ids:
        raise ValidationError("embedding provider is absent from the estate")
    dimensions = _positive_integer(
        item["dimensions"],
        "embedding_profile.dimensions",
        maximum=MAX_VECTOR_DIMENSIONS,
    )
    radius = _number(item["radius"], "embedding_profile.radius")
    tolerance = _number(
        item["comparison_tolerance"],
        "embedding_profile.comparison_tolerance",
    )
    within_radius(radius, radius, tolerance)
    qualification_state = require_identifier(
        item["qualification_state"], "embedding_profile.qualification_state"
    )
    if qualification_state not in QUALIFICATION_STATES:
        raise ValidationError(
            f"unsupported qualification_state: {qualification_state}"
        )
    record = {
        "embedding_profile_id": require_identifier(
            item["embedding_profile_id"],
            "embedding_profile.embedding_profile_id",
        ),
        "name": require_text(
            item["name"], "embedding_profile.name", maximum=256
        ),
        "provider_id": provider_id,
        "model_id": require_text(
            item["model_id"], "embedding_profile.model_id", maximum=512
        ),
        "dimensions": dimensions,
        "metric": require_identifier(
            item["metric"], "embedding_profile.metric"
        ),
        "radius": radius,
        "comparison_tolerance": tolerance,
        "vector_encoding": require_identifier(
            item["vector_encoding"], "embedding_profile.vector_encoding"
        ),
        "qualification_state": qualification_state,
        "qualification_evidence_ref": _host_neutral_reference(
            item["qualification_evidence_ref"],
            "embedding_profile.qualification_evidence_ref",
            maximum=2048,
        ),
        "qualification_digest": require_sha256(
            item["qualification_digest"],
            "embedding_profile.qualification_digest",
        ),
        "created_at": _normalized_timestamp(
            item["created_at"], "embedding_profile.created_at"
        ),
    }
    if record["metric"] != "cosine_distance":
        raise ValidationError("embedding profile metric must be cosine_distance")
    if record["vector_encoding"] != "float32_le":
        raise ValidationError("embedding vector encoding must be float32_le")
    record["profile_digest"] = _record_digest(record, "profile_digest")
    return record


def _source_digest(
    source_id: str, source_digests: dict[str, str], field: str
) -> str:
    if source_id not in source_digests:
        raise ValidationError(f"{field} source is absent from the estate")
    return source_digests[source_id]


def _normalize_clusters(
    value: object, source_digests: dict[str, str]
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, candidate in enumerate(_array(value, "clusters", nonempty=True)):
        item = _exact_object(
            candidate,
            required=frozenset(
                {
                    "cluster_id",
                    "handle",
                    "name",
                    "description",
                    "source_id",
                    "created_at",
                }
            ),
            field=f"clusters[{index}]",
        )
        source_id = require_identifier(
            item["source_id"], f"clusters[{index}].source_id"
        )
        record = {
            "cluster_id": require_identifier(
                item["cluster_id"], f"clusters[{index}].cluster_id"
            ),
            "handle": require_identifier(
                item["handle"], f"clusters[{index}].handle"
            ).casefold(),
            "name": require_text(
                item["name"], f"clusters[{index}].name", maximum=256
            ),
            "description": require_text(
                item["description"],
                f"clusters[{index}].description",
                maximum=1024,
            ),
            "source_id": source_id,
            "source_digest": _source_digest(
                source_id, source_digests, f"clusters[{index}]"
            ),
            "created_at": _normalized_timestamp(
                item["created_at"], f"clusters[{index}].created_at"
            ),
        }
        record["cluster_digest"] = _record_digest(record, "cluster_digest")
        records.append(record)
    _unique(records, "cluster_id", "clusters")
    _unique(records, "handle", "clusters")
    return sorted(records, key=lambda record: record["cluster_id"])


def _normalize_card_views(
    value: object,
    *,
    field: str,
    card_created_at: str,
) -> list[dict[str, Any]]:
    by_kind: dict[str, dict[str, Any]] = {}
    for index, candidate in enumerate(_array(value, field, nonempty=True)):
        item = _exact_object(
            candidate,
            required=frozenset(
                {"capability_card_view_id", "view_kind", "content", "created_at"}
            ),
            field=f"{field}[{index}]",
        )
        kind = require_identifier(
            item["view_kind"], f"{field}[{index}].view_kind"
        )
        if kind not in VIEW_KINDS:
            raise ValidationError(f"unsupported view_kind: {kind}")
        if kind in by_kind:
            raise ValidationError(f"{field} contain duplicate view kinds")
        content = require_text(
            item["content"], f"{field}[{index}].content", maximum=4096
        )
        created_at = _normalized_timestamp(
            item["created_at"], f"{field}[{index}].created_at"
        )
        if parse_timestamp(created_at, "card view.created_at") < parse_timestamp(
            card_created_at, "card.created_at"
        ):
            raise ValidationError("card-view creation predates its card revision")
        by_kind[kind] = {
            "capability_card_view_id": require_identifier(
                item["capability_card_view_id"],
                f"{field}[{index}].capability_card_view_id",
            ),
            "view_kind": kind,
            "content": content,
            "content_digest": sha256_text(content),
            "created_at": created_at,
        }
    if set(by_kind) != set(VIEW_ORDER) or len(by_kind) != len(VIEW_ORDER):
        raise ValidationError(
            f"{field} must contain exactly the six required semantic view kinds"
        )
    return [by_kind[kind] for kind in VIEW_ORDER]


def _normalize_cards(
    value: object,
    *,
    capabilities: Sequence[dict[str, Any]],
    clusters: Sequence[dict[str, Any]],
    source_digests: dict[str, str],
) -> list[dict[str, Any]]:
    capability_by_id = {
        record["capability_id"]: record for record in capabilities
    }
    cluster_by_id = {record["cluster_id"]: record for record in clusters}
    records: list[dict[str, Any]] = []
    view_ids: set[str] = set()
    for index, candidate in enumerate(_array(value, "cards", nonempty=True)):
        item = _exact_object(
            candidate,
            required=frozenset(
                {
                    "capability_card_id",
                    "capability_id",
                    "revision",
                    "compact_projection",
                    "boundaries",
                    "cluster_id",
                    "source_id",
                    "context_cost",
                    "created_at",
                    "views",
                }
            ),
            field=f"cards[{index}]",
        )
        capability_id = require_identifier(
            item["capability_id"], f"cards[{index}].capability_id"
        )
        capability = capability_by_id.get(capability_id)
        if capability is None:
            raise ValidationError("card capability is absent from the estate")
        cluster_id = require_identifier(
            item["cluster_id"], f"cards[{index}].cluster_id"
        )
        cluster = cluster_by_id.get(cluster_id)
        if cluster is None:
            raise ValidationError("card references a cluster outside the manifest")
        created_at = _normalized_timestamp(
            item["created_at"], f"cards[{index}].created_at"
        )
        if parse_timestamp(cluster["created_at"], "cluster.created_at") > parse_timestamp(
            created_at, "card.created_at"
        ):
            raise ValidationError("card creation predates its associative cluster")
        source_id = require_identifier(
            item["source_id"], f"cards[{index}].source_id"
        )
        card_id = require_identifier(
            item["capability_card_id"],
            f"cards[{index}].capability_card_id",
        )
        views = _normalize_card_views(
            item["views"],
            field=f"cards[{index}].views",
            card_created_at=created_at,
        )
        for view in views:
            view_id = view["capability_card_view_id"]
            if view_id in view_ids:
                raise ValidationError(
                    "card views contain duplicate capability_card_view_id values"
                )
            view_ids.add(view_id)
        card = {
            "capability_card_id": card_id,
            "capability_id": capability_id,
            "revision": _positive_integer(
                item["revision"], f"cards[{index}].revision", maximum=2_147_483_647
            ),
            "compact_projection": require_text(
                item["compact_projection"],
                f"cards[{index}].compact_projection",
                maximum=512,
            ),
            "boundaries": require_text(
                item["boundaries"], f"cards[{index}].boundaries", maximum=1024
            ),
            "cluster_id": cluster_id,
            "exposure_policy": capability["exposure_policy"],
            "owner_agent_instance_id": capability["owner_agent_instance_id"],
            "source_id": source_id,
            "source_digest": _source_digest(
                source_id, source_digests, f"cards[{index}]"
            ),
            "context_cost": _nonnegative_integer(
                item["context_cost"],
                f"cards[{index}].context_cost",
                maximum=1_000_000,
            ),
            "created_at": created_at,
        }
        digest_material = {
            **card,
            "views": sorted(
                (
                    {**view, "capability_card_id": card_id}
                    for view in views
                ),
                key=lambda record: record["capability_card_view_id"],
            ),
        }
        card["card_digest"] = _record_digest(
            digest_material, "card_digest"
        )
        records.append({**card, "views": views})
    _unique(records, "capability_card_id", "cards")
    _unique(records, "capability_id", "cards")
    capability_ids = {record["capability_id"] for record in capabilities}
    if {record["capability_id"] for record in records} != capability_ids:
        raise ValidationError(
            "cards must contain exactly one card for every estate capability"
        )
    return sorted(records, key=lambda record: record["capability_id"])


def _normalize_relations(
    value: object,
    *,
    cards: Sequence[dict[str, Any]],
    source_digests: dict[str, str],
) -> list[dict[str, Any]]:
    card_by_capability = {
        record["capability_id"]: record for record in cards
    }
    records: list[dict[str, Any]] = []
    for index, candidate in enumerate(_array(value, "relations")):
        item = _exact_object(
            candidate,
            required=frozenset(
                {
                    "capability_relation_id",
                    "from_capability_id",
                    "to_capability_id",
                    "relation_kind",
                    "source_id",
                    "created_at",
                }
            ),
            field=f"relations[{index}]",
        )
        from_capability_id = require_identifier(
            item["from_capability_id"],
            f"relations[{index}].from_capability_id",
        )
        to_capability_id = require_identifier(
            item["to_capability_id"],
            f"relations[{index}].to_capability_id",
        )
        if from_capability_id == to_capability_id:
            raise ValidationError("capability relation cannot reference itself")
        if (
            from_capability_id not in card_by_capability
            or to_capability_id not in card_by_capability
        ):
            raise ValidationError("relation endpoint is outside the snapshot")
        kind = require_identifier(
            item["relation_kind"], f"relations[{index}].relation_kind"
        )
        if kind not in RELATION_KINDS:
            raise ValidationError(f"unsupported relation_kind: {kind}")
        source_id = require_identifier(
            item["source_id"], f"relations[{index}].source_id"
        )
        created_at = _normalized_timestamp(
            item["created_at"], f"relations[{index}].created_at"
        )
        from_card = card_by_capability[from_capability_id]
        to_card = card_by_capability[to_capability_id]
        if parse_timestamp(created_at, "relation.created_at") < max(
            parse_timestamp(from_card["created_at"], "from card.created_at"),
            parse_timestamp(to_card["created_at"], "to card.created_at"),
        ):
            raise ValidationError("relation creation predates one of its card endpoints")
        record = {
            "capability_relation_id": require_identifier(
                item["capability_relation_id"],
                f"relations[{index}].capability_relation_id",
            ),
            "from_capability_card_id": from_card["capability_card_id"],
            "to_capability_card_id": to_card["capability_card_id"],
            "relation_kind": kind,
            "source_id": source_id,
            "source_digest": _source_digest(
                source_id, source_digests, f"relations[{index}]"
            ),
            "created_at": created_at,
        }
        record["relation_digest"] = _record_digest(
            record, "relation_digest"
        )
        records.append(record)
    _unique(records, "capability_relation_id", "relations")
    return sorted(records, key=lambda record: record["capability_relation_id"])


def _normalize_snapshot_metadata(value: object) -> dict[str, Any]:
    item = _exact_object(
        value,
        required=frozenset(
            {
                "associative_index_snapshot_id",
                "builder_identity",
                "evidence_boundary",
                "created_at",
            }
        ),
        field="snapshot",
    )
    return {
        "associative_index_snapshot_id": require_identifier(
            item["associative_index_snapshot_id"],
            "snapshot.associative_index_snapshot_id",
        ),
        "builder_identity": require_text(
            item["builder_identity"], "snapshot.builder_identity", maximum=512
        ),
        "evidence_boundary": require_text(
            item["evidence_boundary"],
            "snapshot.evidence_boundary",
            maximum=2048,
        ),
        "created_at": _normalized_timestamp(
            item["created_at"], "snapshot.created_at"
        ),
    }


def _normalize_activation(value: object) -> dict[str, Any]:
    item = _exact_object(
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
    return {
        "associative_snapshot_activation_id": require_identifier(
            item["associative_snapshot_activation_id"],
            "activation.associative_snapshot_activation_id",
        ),
        "prior_associative_index_snapshot_id": _nullable_identifier(
            item["prior_associative_index_snapshot_id"],
            "activation.prior_associative_index_snapshot_id",
        ),
        "activated_at": _normalized_timestamp(
            item["activated_at"], "activation.activated_at"
        ),
    }


def _validate_generation_times(
    *,
    lexical_profile: dict[str, Any],
    embedding_profile: dict[str, Any],
    clusters: Sequence[dict[str, Any]],
    cards: Sequence[dict[str, Any]],
    relations: Sequence[dict[str, Any]],
    snapshot: dict[str, Any],
    activation: dict[str, Any],
) -> None:
    snapshot_at = parse_timestamp(snapshot["created_at"], "snapshot.created_at")
    records: list[tuple[str, dict[str, Any]]] = [
        ("lexical profile", lexical_profile),
        ("embedding profile", embedding_profile),
        *(("cluster", record) for record in clusters),
        *(("card", record) for record in cards),
        *(
            ("card view", view)
            for card in cards
            for view in card["views"]
        ),
        *(("relation", record) for record in relations),
    ]
    for label, record in records:
        if parse_timestamp(record["created_at"], f"{label}.created_at") > snapshot_at:
            raise ValidationError(
                f"{label} creation cannot be later than its snapshot"
            )
    if snapshot_at > parse_timestamp(
        activation["activated_at"], "activation.activated_at"
    ):
        raise ValidationError("snapshot activation predates its generation")


def _embed_vectors(
    cards: Sequence[dict[str, Any]],
    *,
    dimensions: int,
    embed: Callable[[list[str]], Sequence[Sequence[float]]],
) -> list[dict[str, Any]]:
    if not callable(embed):
        raise ValidationError("embed must be callable")
    view_rows = sorted(
        (
            (view["capability_card_view_id"], view["content"])
            for card in cards
            for view in card["views"]
        ),
        key=lambda row: row[0],
    )
    raw_vectors = embed([content for _, content in view_rows])
    if (
        isinstance(raw_vectors, (str, bytes))
        or not isinstance(raw_vectors, Sequence)
        or len(raw_vectors) != len(view_rows)
    ):
        raise ValidationError(
            "embed must return exactly one vector for every card view"
        )
    vectors: list[dict[str, Any]] = []
    for index, ((view_id, _), raw_vector) in enumerate(
        zip(view_rows, raw_vectors, strict=True)
    ):
        rounded = coerce_float32_vector(
            raw_vector,
            dimensions=dimensions,
            field=f"embed result[{index}]",
        )
        canonical_vector = tuple(
            0.0 if component == 0.0 else component for component in rounded
        )
        payload = pack_float32_vector(canonical_vector)
        vectors.append(
            {
                "capability_card_view_id": view_id,
                "values": list(canonical_vector),
                "vector_digest": hashlib.sha256(payload).hexdigest(),
            }
        )
    return vectors


def _estate_surface_manifest(
    capabilities: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "capability_id": capability["capability_id"],
            "handle": capability["handle"],
            "exposure_policy": capability["exposure_policy"],
            "owner_agent_instance_id": capability["owner_agent_instance_id"],
            "aliases": [
                {
                    "namespace": alias["namespace"],
                    "normalized_alias": alias["alias"].casefold(),
                    "display_alias": alias["display_alias"],
                }
                for alias in capability["aliases"]
            ],
        }
        for capability in capabilities
    ]


def _build_snapshot(
    *,
    metadata: dict[str, Any],
    capabilities: Sequence[dict[str, Any]],
    lexical_profile: dict[str, Any],
    embedding_profile: dict[str, Any],
    clusters: Sequence[dict[str, Any]],
    cards: Sequence[dict[str, Any]],
    relations: Sequence[dict[str, Any]],
    vectors: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    snapshot = {
        "associative_index_snapshot_id": metadata[
            "associative_index_snapshot_id"
        ],
        "embedding_profile_id": embedding_profile["embedding_profile_id"],
        "lexical_profile_id": lexical_profile["lexical_profile_id"],
        "vector_coverage_state": "complete",
        "estate_digest": sha256_text(
            canonical_json(_estate_surface_manifest(capabilities))
        ),
        "source_digest": sha256_text(
            canonical_json(
                sorted(
                    {
                        (record["source_id"], record["source_digest"])
                        for record in [*clusters, *cards, *relations]
                    }
                )
            )
        ),
        "card_digest": sha256_text(
            canonical_json(sorted(card["card_digest"] for card in cards))
        ),
        "profile_digest": sha256_text(
            canonical_json(
                [
                    lexical_profile["profile_digest"],
                    embedding_profile["profile_digest"],
                ]
            )
        ),
        "builder_identity": metadata["builder_identity"],
        "evidence_boundary": metadata["evidence_boundary"],
        "created_at": metadata["created_at"],
        "expected_card_count": len(cards),
        "expected_relation_count": len(relations),
        "expected_vector_count": len(vectors),
    }
    snapshot_material = {
        key: value
        for key, value in snapshot.items()
        if key
        not in {
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
                (
                    relation["capability_relation_id"],
                    relation["relation_digest"],
                )
                for relation in relations
            ),
            "vectors": sorted(
                (vector["capability_card_view_id"], vector["vector_digest"])
                for vector in vectors
            ),
        }
    )
    snapshot["snapshot_digest"] = sha256_text(canonical_json(snapshot_material))
    return snapshot


def build_capability_assets(
    reviewed_estate: object,
    embed: Callable[[list[str]], Sequence[Sequence[float]]],
) -> dict[str, dict[str, Any]]:
    """Return canonical bootstrap and index assets for one reviewed estate.

    Discovery and semantic authoring are intentionally out of scope. The caller
    supplies reviewed metadata and one embedding function; the compiler performs no
    filesystem discovery, model selection, network access, or timestamp generation.
    """

    item = _exact_object(
        reviewed_estate,
        required=frozenset(
            {
                "format",
                "sources",
                "products",
                "providers",
                "capabilities",
                "distributions",
                "clusters",
                "cards",
                "relations",
                "lexical_profile",
                "embedding_profile",
                "snapshot",
                "activation",
            }
        ),
        field="reviewed estate",
    )
    if item["format"] != REVIEWED_ESTATE_FORMAT:
        raise ValidationError("unsupported reviewed estate format")
    if frozenset(VIEW_ORDER) != VIEW_KINDS:
        raise ValidationError("builder semantic view contract has drifted from Core")

    sources = _normalize_sources(item["sources"])
    products = _normalize_products(item["products"])
    providers = _normalize_providers(item["providers"])
    capabilities = _normalize_capabilities(item["capabilities"])
    distributions = _normalize_distributions(item["distributions"])
    _validate_bootstrap_references(
        sources=sources,
        products=products,
        providers=providers,
        capabilities=capabilities,
        distributions=distributions,
    )

    source_digests = {
        record["source_id"]: record["digest"] for record in sources
    }
    lexical_profile = _normalize_lexical_profile(item["lexical_profile"])
    embedding_profile = _normalize_embedding_profile(
        item["embedding_profile"],
        {record["provider_id"] for record in providers},
    )
    clusters = _normalize_clusters(item["clusters"], source_digests)
    cards = _normalize_cards(
        item["cards"],
        capabilities=capabilities,
        clusters=clusters,
        source_digests=source_digests,
    )
    relations = _normalize_relations(
        item["relations"],
        cards=cards,
        source_digests=source_digests,
    )
    snapshot_metadata = _normalize_snapshot_metadata(item["snapshot"])
    activation = _normalize_activation(item["activation"])
    _validate_generation_times(
        lexical_profile=lexical_profile,
        embedding_profile=embedding_profile,
        clusters=clusters,
        cards=cards,
        relations=relations,
        snapshot=snapshot_metadata,
        activation=activation,
    )
    vectors = _embed_vectors(
        cards,
        dimensions=embedding_profile["dimensions"],
        embed=embed,
    )
    snapshot = _build_snapshot(
        metadata=snapshot_metadata,
        capabilities=capabilities,
        lexical_profile=lexical_profile,
        embedding_profile=embedding_profile,
        clusters=clusters,
        cards=cards,
        relations=relations,
        vectors=vectors,
    )

    bootstrap = {
        "format": "mind-core-bootstrap/v1",
        "sources": sources,
        "products": products,
        "providers": providers,
        "capabilities": capabilities,
        "distributions": distributions,
        "receipts": [],
        "lifecycle_observations": [],
        "mounts": [],
    }
    index = {
        "format": "mind-associative-index/v1",
        "lexical_profile": lexical_profile,
        "embedding_profile": embedding_profile,
        "clusters": clusters,
        "cards": cards,
        "relations": relations,
        "snapshot": snapshot,
        "vectors": vectors,
        "activation": activation,
    }
    return {"bootstrap": bootstrap, "index": index}
