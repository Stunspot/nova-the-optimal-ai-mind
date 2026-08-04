"""Contextual composite fields over an active MIND associative snapshot."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

from .association_math import (
    coerce_float32_vector,
    exact_cosine_distance,
    pack_float32_vector,
    unpack_float32_vector,
)
from .contextual_geometry import (
    BOUNDARY_VIEW_KINDS,
    POSITIVE_VIEW_KINDS,
    complete_neighborhood,
    composite_vector,
)
from .errors import ConflictError
from .field_tokens import sign_visibility_token
from .util import canonical_json, sha256_text


DEFAULT_CONTRAST_RADIUS = 2.4


def _sorted_associations(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduplicated = {canonical_json(value): value for value in values}
    return [deduplicated[key] for key in sorted(deduplicated)]


def contextual_neighborhood(
    reminders: Any,
    session_capability: str,
    snapshot_id: str,
    *,
    anchor_id: str,
    positive_vector: list[float],
    boundary_vector: list[float] | None = None,
    contrast_radius: float = DEFAULT_CONTRAST_RADIUS,
) -> dict[str, Any]:
    """Return every visible card inside the contextual composite membrane."""

    binding = reminders._bound_scope(session_capability)
    snapshot_bundle = reminders._require_current_snapshot(snapshot_id, binding)
    snapshot = snapshot_bundle["snapshot"]
    profile = snapshot_bundle["embedding_profile"]
    if snapshot["vector_coverage_state"] != "complete":
        raise ConflictError("contextual association requires complete vector coverage")
    positive = coerce_float32_vector(
        positive_vector,
        dimensions=profile["dimensions"],
        field="positive_vector",
    )
    boundary = (
        coerce_float32_vector(
            boundary_vector,
            dimensions=profile["dimensions"],
            field="boundary_vector",
        )
        if boundary_vector is not None
        else None
    )

    cards = snapshot_bundle["visible_cards"]
    card_by_id = {card["capability_card_id"]: card for card in cards}
    vectors_by_card: dict[str, dict[str, list[float]]] = defaultdict(dict)
    for row in reminders._visible_vectors(snapshot_id, card_by_id):
        vectors_by_card[row["capability_card_id"]][row["view_kind"]] = (
            unpack_float32_vector(
                row["vector_float32_le"],
                dimensions=profile["dimensions"],
            )
        )

    ordered_card_ids = sorted(card_by_id, key=lambda value: card_by_id[value]["handle"])
    positive_distances: list[float] = []
    boundary_distances: list[float] = []
    for card_id in ordered_card_ids:
        views = vectors_by_card.get(card_id, {})
        positive_composite = composite_vector(
            {kind: views[kind] for kind in POSITIVE_VIEW_KINDS if kind in views},
            POSITIVE_VIEW_KINDS,
            field=f"card[{card_id}].positive",
        )
        positive_distances.append(exact_cosine_distance(positive, positive_composite))
        if boundary is not None:
            boundary_composite = composite_vector(
                {kind: views[kind] for kind in BOUNDARY_VIEW_KINDS if kind in views},
                BOUNDARY_VIEW_KINDS,
                field=f"card[{card_id}].boundary",
            )
            boundary_distances.append(
                exact_cosine_distance(boundary, boundary_composite)
            )

    selected_positive = set(
        complete_neighborhood(
            positive_distances,
            contrast_radius=contrast_radius,
            absolute_radius=profile["radius"],
            comparison_tolerance=profile["comparison_tolerance"],
        )
    )
    selected_boundary = (
        set(
            complete_neighborhood(
                boundary_distances,
                contrast_radius=contrast_radius,
                absolute_radius=profile["radius"],
                comparison_tolerance=profile["comparison_tolerance"],
            )
        )
        if boundary is not None
        else set()
    )

    associations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    boundary_cards: set[str] = set()
    for index in sorted(selected_positive):
        card_id = ordered_card_ids[index]
        associations[card_id].append(
            {
                "anchor_id": anchor_id,
                "anchor_kind": "semantic_membrane",
                "basis": "contextual_composite",
                "channel": "positive",
                "view_kinds": list(POSITIVE_VIEW_KINDS),
            }
        )
    for index in sorted(selected_boundary):
        card_id = ordered_card_ids[index]
        associations[card_id].append(
            {
                "anchor_id": anchor_id,
                "anchor_kind": "semantic_membrane",
                "basis": "contextual_composite",
                "channel": "boundary",
                "view_kind": "negative_boundary",
                "view_kinds": list(BOUNDARY_VIEW_KINDS),
            }
        )
        boundary_cards.add(card_id)

    direct_ids = set(associations)
    reminders._add_relation_paths(
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
                "lifecycle_observations": reminders._lifecycle_for_capability(
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
    anchor_fingerprint = {
        "anchor_id": anchor_id,
        "anchor_kind": "semantic_membrane",
        "positive_vector_digest": hashlib.sha256(
            pack_float32_vector(positive)
        ).hexdigest(),
        "boundary_vector_digest": (
            hashlib.sha256(pack_float32_vector(boundary)).hexdigest()
            if boundary is not None
            else None
        ),
        "contrast_radius": contrast_radius,
        "absolute_radius": profile["radius"],
    }
    field_id = "field:" + sha256_text(
        canonical_json(
            {
                "snapshot_id": snapshot_id,
                "session_capability_hash": binding["token_hash"],
                "anchors": [anchor_fingerprint],
                "membership_manifest_digest": membership_digest,
            }
        )
    )
    token_expiry = min(
        binding["expires_at"],
        reminders.hosts.session(
            binding["host_session_id"],
            binding["agent_instance_id"],
            require_fresh=True,
        )["expires_at"],
    )
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
            reminders._signing_key(),
        )

    scoped_estate_digest = sha256_text(
        canonical_json(
            {
                "capabilities": reminders._capability_surface_manifest(
                    card["capability_id"] for card in cards
                ),
                "cards": sorted(
                    (card["capability_card_id"], card["card_digest"])
                    for card in cards
                ),
            }
        )
    )
    canonical_field = reminders._render_canonical(members)
    compact_field = reminders._render_compact(members)
    return {
        "field_id": field_id,
        "snapshot_id": snapshot_id,
        "scoped_estate_digest": scoped_estate_digest,
        "embedding_profile_id": profile["embedding_profile_id"],
        "lexical_profile_id": snapshot_bundle["lexical_profile"]["lexical_profile_id"],
        "reported_profile_qualification": {
            "state": profile["qualification_state"],
            "evidence_ref": profile["qualification_evidence_ref"],
            "evidence_digest": profile["qualification_digest"],
            "evidence_state": "reported",
        },
        "vector_coverage_state": snapshot["vector_coverage_state"],
        "mode": "contextual_composite_current",
        "membership_manifest_digest": membership_digest,
        "anchors": [
            {
                "anchor_id": anchor_id,
                "anchor_kind": "semantic_membrane",
                "positive_vector_supplied": True,
                "boundary_vector_supplied": boundary is not None,
                "contrast_radius": contrast_radius,
                "absolute_radius": profile["radius"],
            }
        ],
        "members": members,
        "representations": {
            "canonical": reminders._representation(canonical_field, membership_digest),
            "compact": reminders._representation(compact_field, membership_digest),
        },
        "claim_boundary": (
            "Membership means complete contextual-composite association inside both "
            "the robust local-contrast radius and the active profile's absolute "
            "radius, or one explicit relation hop, in the named snapshot and scope. "
            "It is not a rank, verdict, activation, authority, fitness, or permission."
        ),
    }
