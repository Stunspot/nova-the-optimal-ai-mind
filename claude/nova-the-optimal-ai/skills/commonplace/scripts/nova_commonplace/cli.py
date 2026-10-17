"""Machine-stable command line for Nova Commonplace and Concordance."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any, Callable

from .concordance import (
    ConcordanceError,
    build_concordance,
    build_context_packet,
    inspect_concordance,
    invalidate_concordance,
    hybrid_search_concordance,
    rebuild_markdown_views,
    route_query,
    search_concordance,
    verify_absent_id_hashes,
)
from .federation import FederationError, federated_search
from .promotion import (
    create_promotion_proposal,
    export_promotion_handoff,
    promotion_plan,
)
from .registry import RegistryError, resolve_service_paths
from .semantic import SemanticError
from .runtime import (
    AlreadyInitializedError,
    AntiResurrectionError,
    CommonplaceError,
    ConflictError,
    ConfinementError,
    IntegrityError,
    LockTimeoutError,
    NotInitializedError,
    ValidationError,
    digest_object,
    load_json_bytes,
)
from .store import CommonplaceStore


ERROR_SCHEMA = "nova-commonplace.error.v1"
RESULT_SCHEMA = "nova-commonplace.result.v1"
ALLOWED_SENSITIVITIES = ("public", "personal", "private", "restricted")
CONTROL_FIELDS = frozenset(
    {
        "authority",
        "expected_generation",
        "idempotency_key",
        "record",
        "changes",
        "replacement",
        "record_id",
        "plan_digest",
    }
)


class CliInputError(ValueError):
    """The CLI invocation or JSON envelope was malformed."""


class JsonArgumentParser(argparse.ArgumentParser):
    """Argparse variant whose machine-facing failures remain one JSON object."""

    def error(self, message: str) -> None:
        raise CliInputError(message)


def _emit(value: Any, *, stream: Any = sys.stdout) -> None:
    json.dump(value, stream, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    stream.write("\n")


def _object(value: Any, *, field: str = "input") -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CliInputError(f"{field} must be a JSON object")
    return deepcopy(dict(value))


def _stdin_object(args: argparse.Namespace) -> dict[str, Any]:
    if not getattr(args, "stdin_json", False):
        raise CliInputError("this command requires --stdin-json")
    stream = sys.stdin
    raw = (
        stream.buffer.read()
        if hasattr(stream, "buffer")
        else stream.read().encode("utf-8")
    )
    try:
        value = load_json_bytes(raw, source="standard input")
    except IntegrityError as error:
        raise CliInputError(str(error)) from error
    return _object(value)


def _boolean(
    payload: Mapping[str, Any], key: str, *, default: bool = False
) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise CliInputError(f"{key} must be a JSON boolean")
    return value


def _authority(payload: Mapping[str, Any]) -> Any:
    authority = payload.get("authority")
    if not isinstance(authority, (str, Mapping)):
        raise CliInputError("authority must be a non-empty string or JSON object")
    if isinstance(authority, str) and not authority.strip():
        raise CliInputError("authority must not be blank")
    return authority


def _generation(payload: Mapping[str, Any], *, optional: bool = False) -> int | None:
    value = payload.get("expected_generation")
    if optional and value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CliInputError("expected_generation must be a non-negative integer")
    return value


def _idempotency(payload: Mapping[str, Any]) -> str:
    value = payload.get("idempotency_key")
    if not isinstance(value, str) or not value.strip():
        raise CliInputError("idempotency_key is required and must be a non-empty string")
    return value


def _record_id(payload: Mapping[str, Any]) -> str:
    value = payload.get("record_id")
    if not isinstance(value, str) or not value.strip():
        raise CliInputError("record_id must be a non-empty string")
    return value


def _sensitivities(
    payload: Mapping[str, Any], *, default: Sequence[str] = ("public", "personal")
) -> tuple[str, ...]:
    value = payload.get("allowed_sensitivities", payload.get("allowed_sensitivity", default))
    if isinstance(value, str):
        value = [value]
    elif not isinstance(value, list):
        value = list(value) if isinstance(value, tuple) else value
    if not isinstance(value, list) or not value:
        raise CliInputError("allowed_sensitivities must be a non-empty JSON array")
    result = tuple(dict.fromkeys(value))
    if any(not isinstance(item, str) or item not in ALLOWED_SENSITIVITIES for item in result):
        raise CliInputError(
            "allowed_sensitivities may contain only " + ", ".join(ALLOWED_SENSITIVITIES)
        )
    return result


def _take_source_alias(
    value: dict[str, Any], names: Sequence[str], *, field: str
) -> Any:
    present = [name for name in names if name in value]
    if len(present) > 1:
        raise CliInputError(
            f"{field} was supplied more than once through aliases: {present}"
        )
    return value.pop(present[0]) if present else None


def _source_to_provenance(source: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if source is None:
        return [], {}
    if not isinstance(source, Mapping):
        raise CliInputError("source must be null or a JSON object")
    value = dict(source)
    source_type = _take_source_alias(
        value, ("source_type", "type"), field="source type"
    )
    source_ref = _take_source_alias(
        value,
        ("source_ref", "locator", "url", "path"),
        field="source locator",
    )
    if not isinstance(source_type, str) or not source_type:
        raise CliInputError("source requires source_type (or type)")
    if not isinstance(source_ref, str) or not source_ref:
        raise CliInputError("source requires source_ref (or locator/url/path)")
    entry: dict[str, Any] = {"source_type": source_type, "source_ref": source_ref}
    for key in ("retrieved_at", "content_sha256", "span", "note"):
        if key in value:
            entry[key] = value.pop(key)
    metadata: dict[str, Any] = {}
    for source_key, metadata_key in (
        ("title", "source_title"),
        ("author", "source_author"),
        ("published_at", "source_published_at"),
    ):
        if source_key in value:
            metadata[metadata_key] = value.pop(source_key)
    if value:
        raise CliInputError(f"source contains unsupported fields: {sorted(value)}")
    return [entry], metadata

def _capture_record(payload: Mapping[str, Any]) -> dict[str, Any]:
    if "record" in payload:
        record = _object(payload["record"], field="record")
        if record.get("kind") == "promotion_proposal":
            raise CliInputError(
                "capture cannot create promotion_proposal; use propose-promotion"
            )
        extra = set(payload) - CONTROL_FIELDS
        if extra:
            raise CliInputError(
                "nested record input cannot also contain flat record fields: "
                + ", ".join(sorted(extra))
            )
        return record

    record = {key: deepcopy(value) for key, value in payload.items() if key not in CONTROL_FIELDS}
    source = record.pop("source", None)
    provenance, source_metadata = _source_to_provenance(source)
    if provenance:
        supplied = record.get("provenance")
        if supplied not in (None, []):
            raise CliInputError("use either source or provenance, not both")
        record["provenance"] = provenance
    metadata = _object(record.pop("metadata", {}), field="metadata")
    metadata.update(source_metadata)
    for key in ("intent", "intended_use", "why_saved", "creation_actor"):
        if key in record:
            metadata[key] = record.pop(key)
    if metadata:
        record["metadata"] = metadata
    record.setdefault("kind", "note")
    if record["kind"] == "promotion_proposal":
        raise CliInputError(
            "capture cannot create promotion_proposal; use propose-promotion"
        )
    record.setdefault("origin", "user_authored")
    record.setdefault("review", "accepted")
    record.setdefault("dispute", "undisputed")
    record.setdefault("lifecycle", "current")
    record.setdefault("sensitivity", "private")
    record.setdefault("rights", "self_authored")
    return record


def _paths(args: argparse.Namespace) -> Any:
    return resolve_service_paths(getattr(args, "estate_root", None))


def _store(args: argparse.Namespace) -> CommonplaceStore:
    return CommonplaceStore(_paths(args).commonplace)


def _status(args: argparse.Namespace) -> Any:
    paths = _paths(args)
    result = CommonplaceStore(paths.commonplace).status()
    result["registry"] = str(paths.registry)
    result["concordance_root"] = str(paths.concordance)
    if result["initialized"]:
        result["concordance"] = inspect_concordance(paths.commonplace, paths.concordance)
    else:
        result["concordance"] = {
            "status": "unavailable",
            "reason": "Commonplace is not initialized",
        }
    return result


def _initialize(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    return _store(args).initialize(authority=_authority(payload))


def _verify(args: argparse.Namespace) -> Any:
    paths = _paths(args)
    canonical = CommonplaceStore(paths.commonplace).verify()
    concordance = inspect_concordance(paths.commonplace, paths.concordance)
    canonical_ok = bool(canonical.get("ok"))
    concordance_ok = concordance.get("status") in {"current", "unavailable"}
    return {
        "ok": canonical_ok and concordance_ok,
        "operation": "verify-all",
        "canonical": canonical,
        "concordance": concordance,
        **(
            {"_exit_code": 6 if not canonical_ok else 9}
            if not (canonical_ok and concordance_ok)
            else {}
        ),
    }


def _project_after_mutation(paths: Any, canonical: Mapping[str, Any]) -> dict[str, Any]:
    try:
        derived = build_concordance(paths.commonplace, paths.concordance)
    except BaseException as error:
        exit_code, code = _failure(error)
        invalidation = invalidate_concordance(paths.concordance)
        return {
            "ok": False,
            "operation": canonical.get("operation"),
            "status": "partial",
            "canonical_committed": True,
            "canonical_receipt": dict(canonical),
            "projection": {
                "ok": False,
                "code": code,
                "message": str(error),
                "stale_retrieval_refused": True,
                "invalidation": invalidation,
                "recovery": "run rebuild after resolving the reported projection failure",
            },
            "_exit_code": 9,
        }
    return {
        **dict(canonical),
        "canonical_committed": True,
        "projection": {
            "ok": True,
            "status": derived["status"],
            "canonical": False,
            "builder": derived["builder"],
            "workspace_id": derived["workspace_id"],
            "generation": derived["generation"],
            "canonical_snapshot_digest": derived["canonical_snapshot_digest"],
            "index": derived["index"],
            "index_sha256": derived["index_sha256"],
            "cleanup": derived["cleanup"],
        },
    }


def _capture(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    paths = _paths(args)
    canonical = CommonplaceStore(paths.commonplace).put(
        _capture_record(payload),
        authority=_authority(payload),
        expected_generation=int(_generation(payload)),
        idempotency_key=_idempotency(payload),
    )
    return _project_after_mutation(paths, canonical)


def _get(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    record = _store(args).get(_record_id(payload))
    allowed = _sensitivities(payload)
    if record["sensitivity"] not in allowed:
        return {
            "ok": False,
            "status": "scope_denied",
            "record_id": record["id"],
            "allowed_sensitivities": list(allowed),
        }
    return {"ok": True, "record": record, "canonical": True}


def _list_records(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    allowed = _sensitivities(payload)
    records = [
        record for record in _store(args).records() if record["sensitivity"] in allowed
    ]
    return {
        "ok": True,
        "canonical": True,
        "allowed_sensitivities": list(allowed),
        "record_count": len(records),
        "records": records,
    }


def _update_state(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    paths = _paths(args)
    canonical = CommonplaceStore(paths.commonplace).update_state(
        _record_id(payload),
        _object(payload.get("changes"), field="changes"),
        authority=_authority(payload),
        expected_generation=int(_generation(payload)),
        idempotency_key=_idempotency(payload),
    )
    return _project_after_mutation(paths, canonical)


def _supersede(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    paths = _paths(args)
    replacement = _object(payload.get("replacement"), field="replacement")
    if replacement.get("kind") == "promotion_proposal":
        raise CliInputError(
            "supersede cannot create promotion_proposal; use propose-promotion"
        )
    canonical = CommonplaceStore(paths.commonplace).supersede(
        _record_id(payload),
        replacement,
        authority=_authority(payload),
        expected_generation=int(_generation(payload)),
        idempotency_key=_idempotency(payload),
    )
    return _project_after_mutation(paths, canonical)


def _managed_concordance_targets(home: Path) -> list[dict[str, str]]:
    """Describe exact managed derived targets without reading content."""
    targets: list[dict[str, str]] = []
    pointer = home / "state" / "current.json"
    if pointer.is_file():
        targets.append({"kind": "pointer", "path": "state/current.json"})
    for name, kind in (("indexes", "index"), ("views", "view")):
        directory = home / name
        if not directory.is_dir():
            continue
        for item in sorted(directory.iterdir(), key=lambda candidate: candidate.name):
            targets.append(
                {
                    "kind": kind,
                    "path": item.relative_to(home).as_posix(),
                }
            )
    return targets


def _build_forget_plan(paths: Any, record_id: str) -> dict[str, Any]:
    plan = CommonplaceStore(paths.commonplace).forget_plan(record_id)
    plan["derived"] = {
        "owner": "Concordance",
        "canonical": False,
        "root": str(paths.concordance),
        "inspection": inspect_concordance(paths.commonplace, paths.concordance),
        "targets": _managed_concordance_targets(paths.concordance),
        "action": "rebuild from the post-forget generation and prune every noncurrent managed projection",
    }
    plan["plan_digest"] = digest_object(plan)
    return plan


def _forget_plan(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    return _build_forget_plan(_paths(args), _record_id(payload))


def _forget(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    paths = _paths(args)
    record_id = _record_id(payload)
    supplied_plan_digest = payload.get("plan_digest")
    if (
        not isinstance(supplied_plan_digest, str)
        or len(supplied_plan_digest) != 64
        or any(character not in "0123456789abcdef" for character in supplied_plan_digest)
    ):
        raise CliInputError("plan_digest must be the lowercase SHA-256 from forget-plan")
    store = CommonplaceStore(paths.commonplace)
    try:
        current_plan = _build_forget_plan(paths, record_id)
    except KeyError:
        current_plan = None
    if current_plan is not None and supplied_plan_digest != current_plan["plan_digest"]:
        raise ConflictError(
            "forget plan changed; inspect a fresh forget-plan before destructive execution"
        )
    canonical = store.forget(
        record_id,
        authority=_authority(payload),
        expected_generation=int(_generation(payload)),
        idempotency_key=_idempotency(payload),
        expected_plan_digest=(
            current_plan["canonical_plan_digest"]
            if current_plan is not None
            else supplied_plan_digest
        ),
    )
    try:
        derived = build_concordance(paths.commonplace, paths.concordance)
        negative = verify_absent_id_hashes(
            paths.commonplace,
            paths.concordance,
            canonical["affected_id_hashes"],
        )
        if not negative["ok"]:
            invalidation = invalidate_concordance(paths.concordance)
            return {
                "ok": False,
                "operation": "forget",
                "status": "partial",
                "canonical_committed": True,
                "canonical_receipt": canonical,
                "derived_cleanup": {
                    "ok": False,
                    "code": "forgotten_identity_present",
                    "negative_verification": negative,
                    "stale_retrieval_refused": True,
                    "invalidation": invalidation,
                },
                "physical_erasure_claim": False,
                "_exit_code": 6 if not canonical.get("ok") else 9,
            }
    except BaseException as error:
        exit_code, code = _failure(error)
        invalidation = invalidate_concordance(paths.concordance)
        return {
            "ok": False,
            "operation": "forget",
            "status": "partial",
            "canonical_committed": True,
            "canonical_receipt": canonical,
            "derived_cleanup": {
                "ok": False,
                "code": code,
                "message": str(error),
                "stale_retrieval_refused": True,
                "invalidation": invalidation,
            },
            "physical_erasure_claim": False,
            "_exit_code": 6 if not canonical.get("ok") else 9,
        }
    derived_cleanup = {
        "ok": True,
        "binding": {
            "workspace_id": derived["workspace_id"],
            "generation": derived["generation"],
            "canonical_snapshot_digest": derived["canonical_snapshot_digest"],
            "builder": derived["builder"],
            "index": derived["index"],
            "index_sha256": derived["index_sha256"],
        },
        "cleanup": derived["cleanup"],
        "negative_verification": negative,
    }
    if not canonical.get("ok"):
        return {
            "ok": False,
            "operation": "forget",
            "status": "partial",
            "canonical_committed": True,
            "canonical_receipt": canonical,
            "plan_digest": supplied_plan_digest,
            "derived_cleanup": derived_cleanup,
            "physical_erasure_claim": False,
            "_exit_code": 6,
        }
    return {
        **canonical,
        "plan_digest": supplied_plan_digest,
        "derived_cleanup": derived_cleanup,
    }

def _backup(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    name = payload.get("name")
    if name is not None and not isinstance(name, str):
        raise CliInputError("name must be a string when supplied")
    return _store(args).backup(name=name, authority=_authority(payload))


def _restore_test(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    name = payload.get("name")
    if not isinstance(name, str) or not name:
        raise CliInputError("name must be a non-empty string")
    return _store(args).restore_test(name)


def _recover(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    return _store(args).recover(
        authority=_authority(payload),
        expected_generation=_generation(payload, optional=True),
    )


def _rebuild(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    paths = _paths(args)
    sensitivities = _sensitivities(payload, default=("public", "personal"))
    semantic_config = payload.get("semantic_config")
    if semantic_config is not None and not isinstance(semantic_config, (bool, Mapping)):
        raise CliInputError("semantic_config must be a boolean or JSON object")
    return build_concordance(
        paths.commonplace,
        paths.concordance,
        markdown_sensitivities=sensitivities,
        semantic_config=semantic_config,
    )


def _inspect(args: argparse.Namespace) -> Any:
    paths = _paths(args)
    return inspect_concordance(paths.commonplace, paths.concordance)


def _history(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    allowed = _sensitivities(payload)
    result = _store(args).history(_record_id(payload))
    entries = result.get("entries", [])
    if any(
        isinstance(item, Mapping)
        and isinstance(item.get("record"), Mapping)
        and item["record"].get("sensitivity") not in allowed
        for item in entries
    ):
        return {
            "ok": False,
            "status": "scope_denied",
            "record_id": result["record_id"],
            "allowed_sensitivities": list(allowed),
            "record_content_available": False,
        }
    return result


def _as_of(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    generation = payload.get("generation")
    timestamp = payload.get("timestamp")
    result = _store(args).get_as_of(
        _record_id(payload), generation=generation, timestamp=timestamp
    )
    allowed = _sensitivities(payload)
    record = result.get("record")
    if isinstance(record, Mapping) and record.get("sensitivity") not in allowed:
        return {
            "ok": False,
            "status": "scope_denied",
            "record_id": result["record_id"],
            "selector": result["selector"],
            "allowed_sensitivities": list(allowed),
            "record_content_available": False,
        }
    return result


def _propose_promotion(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    proposal = payload.get("proposal")
    if not isinstance(proposal, Mapping):
        raise CliInputError("proposal must be a JSON object")
    paths = _paths(args)
    result = create_promotion_proposal(
        CommonplaceStore(paths.commonplace),
        proposal,
        authority=_authority(payload),
        expected_generation=int(_generation(payload)),
        idempotency_key=_idempotency(payload),
    )
    return _project_after_mutation(paths, result)


def _promotion_scope(
    args: argparse.Namespace, payload: Mapping[str, Any]
) -> tuple[CommonplaceStore, str] | dict[str, Any]:
    store = _store(args)
    proposal_id = payload.get("proposal_id", payload.get("record_id"))
    if not isinstance(proposal_id, str) or not proposal_id.strip():
        raise CliInputError("proposal_id must be a non-empty string")
    record = store.get(proposal_id)
    allowed = _sensitivities(payload)
    if record["sensitivity"] not in allowed:
        return {
            "ok": False,
            "status": "scope_denied",
            "proposal_id": proposal_id,
            "allowed_sensitivities": list(allowed),
        }
    return store, proposal_id


def _promotion_plan(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    scoped = _promotion_scope(args, payload)
    if isinstance(scoped, dict):
        return scoped
    store, proposal_id = scoped
    return promotion_plan(store, proposal_id)


def _promotion_export(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    scoped = _promotion_scope(args, payload)
    if isinstance(scoped, dict):
        return scoped
    store, proposal_id = scoped
    return export_promotion_handoff(store, proposal_id)


def _federated_search(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    query = payload.get("query")
    if not isinstance(query, str):
        raise CliInputError("query must be a string")
    owners = payload.get("owners")
    if owners is not None and (
        isinstance(owners, (str, bytes)) or not isinstance(owners, list)
    ):
        raise CliInputError("owners must be a JSON array")
    owner_options = payload.get("owner_options")
    if owner_options is not None and not isinstance(owner_options, Mapping):
        raise CliInputError("owner_options must be a JSON object")
    limit = payload.get("limit", 8)
    timeout_ms = payload.get("timeout_ms", 5000)
    graph_hops = payload.get("graph_hops", 0)
    if any(
        isinstance(value, bool) or not isinstance(value, int)
        for value in (limit, timeout_ms, graph_hops)
    ):
        raise CliInputError("limit, timeout_ms, and graph_hops must be integers")
    mode = payload.get("commonplace_mode", "hybrid")
    if mode not in {"lexical", "semantic", "hybrid"}:
        raise CliInputError("commonplace_mode must be lexical, semantic, or hybrid")
    return federated_search(
        query,
        estate_root=getattr(args, "estate_root", None),
        owners=owners,
        allowed_sensitivities=_sensitivities(payload),
        limit=limit,
        owner_options=owner_options,
        commonplace_mode=mode,
        allow_degraded=_boolean(payload, "allow_degraded"),
        graph_hops=graph_hops,
        timeout_ms=timeout_ms,
    )


def _search(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    query = payload.get("query")
    if not isinstance(query, str):
        raise CliInputError("query must be a string")
    limit = payload.get("limit", 10)
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise CliInputError("limit must be an integer")
    mode = payload.get("mode", "lexical")
    if mode not in {"lexical", "semantic", "hybrid"}:
        raise CliInputError("mode must be lexical, semantic, or hybrid")
    graph_hops = payload.get("graph_hops", 0)
    if isinstance(graph_hops, bool) or not isinstance(graph_hops, int):
        raise CliInputError("graph_hops must be an integer")
    paths = _paths(args)
    sensitivities = _sensitivities(payload)
    review_inbox = _boolean(payload, "review_inbox")
    if mode == "lexical" and graph_hops == 0:
        hits = search_concordance(
            paths.commonplace,
            paths.concordance,
            query,
            allowed_sensitivities=sensitivities,
            limit=limit,
            review_inbox=review_inbox,
        )
        return {"ok": True, "operation": "search", "query": query, "mode": "lexical", "hits": hits}
    result = hybrid_search_concordance(
        paths.commonplace,
        paths.concordance,
        query,
        mode=mode,
        allowed_sensitivities=sensitivities,
        limit=limit,
        review_inbox=review_inbox,
        allow_degraded=_boolean(payload, "allow_degraded"),
        graph_hops=graph_hops,
    )
    return {"ok": True, "operation": "search", "query": query, **result}


def _context(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    query = payload.get("query")
    if not isinstance(query, str):
        raise CliInputError("query must be a string")
    max_chars = payload.get("max_chars", 4000)
    candidate_limit = payload.get("candidate_limit", 20)
    if any(
        isinstance(value, bool) or not isinstance(value, int)
        for value in (max_chars, candidate_limit)
    ):
        raise CliInputError("max_chars and candidate_limit must be integers")
    if not 0 <= max_chars <= 24 * 1024:
        raise CliInputError("max_chars must be between 0 and 24576")
    if not 1 <= candidate_limit <= 100:
        raise CliInputError("candidate_limit must be between 1 and 100")
    paths = _paths(args)
    return build_context_packet(
        paths.commonplace,
        paths.concordance,
        query,
        allowed_sensitivities=_sensitivities(payload),
        max_chars=max_chars,
        candidate_limit=candidate_limit,
        review_inbox=_boolean(payload, "review_inbox"),
    )


def _views(args: argparse.Namespace) -> Any:
    paths = _paths(args)
    return rebuild_markdown_views(paths.commonplace, paths.concordance)


def _route(args: argparse.Namespace) -> Any:
    payload = _stdin_object(args)
    query = payload.get("query")
    if not isinstance(query, str):
        raise CliInputError("query must be a string")
    owner_states = payload.get("owner_states")
    if owner_states is not None and not isinstance(owner_states, Mapping):
        raise CliInputError("owner_states must be a JSON object")
    return route_query(query, owner_states=owner_states)


def _command(
    subparsers: Any,
    name: str,
    handler: Callable[[argparse.Namespace], Any],
    *,
    stdin_json: bool = False,
) -> None:
    command = subparsers.add_parser(name)
    command.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    if stdin_json:
        command.add_argument("--stdin-json", action="store_true")
    command.set_defaults(handler=handler)


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(prog="nova-commonplace")
    parser.add_argument("--estate-root", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, handler in (
        ("status", _status),
        ("verify", _verify),
        ("inspect", _inspect),
        ("views", _views),
    ):
        _command(commands, name, handler)
    for name, handler in (
        ("init", _initialize),
        ("capture", _capture),
        ("get", _get),
        ("list", _list_records),
        ("update-state", _update_state),
        ("supersede", _supersede),
        ("forget-plan", _forget_plan),
        ("forget", _forget),
        ("backup", _backup),
        ("restore-test", _restore_test),
        ("recover", _recover),
        ("rebuild", _rebuild),
        ("search", _search),
        ("context", _context),
        ("route", _route),
        ("history", _history),
        ("as-of", _as_of),
        ("propose-promotion", _propose_promotion),
        ("promotion-plan", _promotion_plan),
        ("promotion-export", _promotion_export),
        ("federated-search", _federated_search),
    ):
        _command(commands, name, handler, stdin_json=True)
    return parser


def _failure(error: BaseException) -> tuple[int, str]:
    if isinstance(error, (CliInputError, ValidationError)):
        return 2, "invalid_input"
    if isinstance(error, RegistryError):
        return 3, "registry_error"
    if isinstance(error, (ConflictError, AlreadyInitializedError)):
        return 4, "conflict"
    if isinstance(error, NotInitializedError):
        return 5, "not_initialized"
    if isinstance(error, AntiResurrectionError):
        return 6, "anti_resurrection"
    if isinstance(error, (IntegrityError, ConfinementError)):
        return 6, "integrity_error"
    if isinstance(error, LockTimeoutError):
        return 7, "lock_timeout"
    if isinstance(error, (KeyError, FileNotFoundError)):
        return 8, "not_found"
    if isinstance(error, SemanticError):
        return 9, getattr(error, "code", "semantic_error")
    if isinstance(error, ConcordanceError):
        return 9, getattr(error, "code", "concordance_error")
    if isinstance(error, FederationError):
        return 11, getattr(error, "code", "federation_error")
    if isinstance(error, CommonplaceError):
        return 10, "commonplace_error"
    return 70, "internal_error"


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        result = args.handler(args)
    except SystemExit:
        raise
    except BaseException as error:
        exit_code, code = _failure(error)
        _emit(
            {
                "ok": False,
                "schema": ERROR_SCHEMA,
                "response_schema": RESULT_SCHEMA,
                "error": {"code": code, "message": str(error)},
            }
        )
        return exit_code
    exit_code = 0
    if isinstance(result, dict):
        result = dict(result)
        if "_exit_code" in result:
            exit_code = int(result.pop("_exit_code"))
        result.setdefault("response_schema", RESULT_SCHEMA)
    _emit(result)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
