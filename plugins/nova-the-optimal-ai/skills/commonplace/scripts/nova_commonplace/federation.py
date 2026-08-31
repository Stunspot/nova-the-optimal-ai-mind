"""Query-routed, read-only federation across Nova's canonical owners.

Federation composes published owner reads. It stores no owner payload, performs
no writes, and treats every returned packet as derived navigation with explicit
source, sensitivity, integrity, and failure state.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from .concordance import ContractError, hybrid_search_concordance, route_query
from .registry import load_selector_registry
from .runtime import IntegrityError as JsonIntegrityError, load_json_bytes


FEDERATION_SCHEMA = "nova-commonplace.federation-result.v1"
OWNER_RESULT_SCHEMA = "nova-commonplace.federation-owner-result.v1"
WORKER_REQUEST_SCHEMA = "nova-commonplace.federation-worker-request.v1"
ADAPTER_MANIFEST_SCHEMA = "nova-commonplace.federation-adapter-manifest.v2"
OWNER_NAMES = (
    "Commonplace",
    "Dunbar",
    "Corkboard",
    "Dennis",
    "Continuity",
    "Striving",
    "Giles",
    "Dex",
    "Skills",
    "Repositories",
    "ExternalCorpora",
)
EXECUTABLE_OWNERS = frozenset(
    {"Commonplace", "Dunbar", "Corkboard", "Dennis", "Continuity"}
)
_SELECTOR_KEYS = {
    "Dunbar": "DUNBAR_STORE",
    "Corkboard": "CORKBOARD_HOME",
    "Dennis": "DENNIS_PROJECT_HOME",
    "Continuity": "NOVA_CONTINUITY_HOME",
}
_MODULE_PATHS = {
    "Dunbar": "dunbar/scripts/dunbar.py",
    "Corkboard": "corkboard/scripts/corkboard.py",
    "Dennis": "dennis-stratton-project-management/scripts/project_control.py",
    "Continuity": "cognitive-continuity/scripts/worldline.py",
}
_DEPENDENCY_PATHS: dict[str, tuple[tuple[str, str], ...]] = {
    "Dunbar": (),
    "Corkboard": (),
    "Dennis": (),
    "Continuity": (
        ("eligibility_policy", "cognitive-continuity/scripts/eligibility_policy.py"),
        ("schema_validation", "cognitive-continuity/scripts/schema_validation.py"),
        ("workspace_runtime", "cognitive-continuity/scripts/workspace_runtime.py"),
    ),
}
_PACKAGE_ROOTS = {
    "Dunbar": None,
    "Corkboard": None,
    "Dennis": None,
    "Continuity": "cognitive-continuity",
}
_BUILTIN_ADAPTER_MANIFEST: dict[str, Any] = {
    "schema": ADAPTER_MANIFEST_SCHEMA,
    "approval_id": "nova-emergent-owner-reads-1.0.4",
    "adapters": {
        "Dunbar": {
            "relative_path": _MODULE_PATHS["Dunbar"],
            "sha256": "9c43c59ffa96151381a1e366e332f43cb3ab6906154edb91380410556d2dc3d5",
            "dependencies": [],
            "package": None,
        },
        "Corkboard": {
            "relative_path": _MODULE_PATHS["Corkboard"],
            "sha256": "f83809964f34d4b8aca21056060c73d2af760766c82ac143587f16f3082226f3",
            "dependencies": [],
            "package": None,
        },
        "Dennis": {
            "relative_path": _MODULE_PATHS["Dennis"],
            "sha256": "1d6e2deb933c3444c40678ff1453c2d39eafe83e4319fd921cd11339ee2d53d8",
            "dependencies": [],
            "package": None,
        },
        "Continuity": {
            "relative_path": _MODULE_PATHS["Continuity"],
            "sha256": "9daf3a120220459d3151d39d55a412f62e3ef78b1915b180110132e4f4581266",
            "dependencies": [
                {
                    "module": "eligibility_policy",
                    "relative_path": "cognitive-continuity/scripts/eligibility_policy.py",
                    "sha256": "8bf0d621644032f36897ec597a93625c783d1815e19acf46b657a532b8e1db9e",
                },
                {
                    "module": "schema_validation",
                    "relative_path": "cognitive-continuity/scripts/schema_validation.py",
                    "sha256": "8bf552d00f363e7acdacae6307c80cd77b8b61b0031d0329dbf594f806e3fd88",
                },
                {
                    "module": "workspace_runtime",
                    "relative_path": "cognitive-continuity/scripts/workspace_runtime.py",
                    "sha256": "79d99c8a5acf8430e4a41ad50fc3d1fcedb14e6691c4b2f2e95137423b1c67ea",
                },
            ],
            "package": {
                "relative_root": "cognitive-continuity",
                "file_count": 73,
                "tree_sha256": "c632d0656c1b04ac493f40cceceafc46fb4df3b150626c54ef00679a21cef5be",
            },
        },
    },
}
_ROUTE_ONLY_REASONS = {
    "Striving": "Striving owns authorized durable pursuits; no approved federated read adapter is available",
    "Giles": "Giles is a stewardship capability; no owner-published query store is available",
    "Dex": "Dex is a data-systems capability; no Nova canonical query store is registered",
    "Skills": "Skills remain package-owned; no executable cross-skill search adapter is approved",
    "Repositories": "Repositories retain their own custody; no repository corpus was opted in",
    "ExternalCorpora": "External corpora retain source custody; no corpus adapter was supplied",
}
_ALLOWED_STATUSES = {
    "current",
    "degraded",
    "stale",
    "unavailable",
    "scope_denied",
    "incompatible",
    "integrity_error",
    "partial",
}
_ROUTE_STATUS_MAP = {"degraded": "partial", "integrity_error": "incompatible"}
_SENSITIVITY_ORDER = ("public", "personal", "private", "restricted")
_ALLOWED_SENSITIVITIES = frozenset(_SENSITIVITY_ORDER)
_DIGEST_RE = re.compile(r"[0-9a-f]{64}")


class FederationError(RuntimeError):
    code = "federation_error"


class FederationUnavailableError(FederationError):
    code = "federation_unavailable"


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _normalise_adapter_manifest(value: Mapping[str, Any] | None) -> dict[str, Any]:
    supplied: Any = _BUILTIN_ADAPTER_MANIFEST if value is None else value
    if not isinstance(supplied, Mapping) or set(supplied) != {
        "schema",
        "approval_id",
        "adapters",
    }:
        raise ContractError("approved_adapter_manifest has an invalid envelope")
    if supplied.get("schema") != ADAPTER_MANIFEST_SCHEMA:
        raise ContractError("approved_adapter_manifest has an unsupported schema")
    approval_id = supplied.get("approval_id")
    if (
        not isinstance(approval_id, str)
        or not approval_id.strip()
        or len(approval_id) > 256
    ):
        raise ContractError("approved_adapter_manifest.approval_id is invalid")
    adapters = supplied.get("adapters")
    if not isinstance(adapters, Mapping) or set(adapters) != set(_MODULE_PATHS):
        raise ContractError(
            "approved_adapter_manifest.adapters must contain exactly the fixed owner set"
        )
    normalized: dict[str, dict[str, Any]] = {}
    for owner, expected_path in _MODULE_PATHS.items():
        entry = adapters.get(owner)
        if not isinstance(entry, Mapping) or set(entry) != {
            "relative_path",
            "sha256",
            "dependencies",
            "package",
        }:
            raise ContractError(f"approved adapter entry for {owner} is invalid")
        relative_path = entry.get("relative_path")
        digest = entry.get("sha256")
        if relative_path != expected_path:
            raise ContractError(f"approved adapter path for {owner} is not fixed")
        if not isinstance(digest, str) or _DIGEST_RE.fullmatch(digest) is None:
            raise ContractError(f"approved adapter digest for {owner} is invalid")
        dependencies = entry.get("dependencies")
        expected_dependencies = _DEPENDENCY_PATHS[owner]
        if not isinstance(dependencies, list) or len(dependencies) != len(
            expected_dependencies
        ):
            raise ContractError(
                f"approved adapter dependency closure for {owner} is incomplete"
            )
        normalized_dependencies: list[dict[str, str]] = []
        for supplied_dependency, (module, dependency_path) in zip(
            dependencies, expected_dependencies
        ):
            if not isinstance(supplied_dependency, Mapping) or set(
                supplied_dependency
            ) != {"module", "relative_path", "sha256"}:
                raise ContractError(
                    f"approved adapter dependency entry for {owner} is invalid"
                )
            dependency_digest = supplied_dependency.get("sha256")
            if (
                supplied_dependency.get("module") != module
                or supplied_dependency.get("relative_path") != dependency_path
                or not isinstance(dependency_digest, str)
                or _DIGEST_RE.fullmatch(dependency_digest) is None
            ):
                raise ContractError(
                    f"approved adapter dependency closure for {owner} is not fixed"
                )
            normalized_dependencies.append(
                {
                    "module": module,
                    "relative_path": dependency_path,
                    "sha256": dependency_digest,
                }
            )
        package = entry.get("package")
        expected_package_root = _PACKAGE_ROOTS[owner]
        if expected_package_root is None:
            if package is not None:
                raise ContractError(
                    f"approved adapter package binding for {owner} must be null"
                )
            normalized_package = None
        else:
            if not isinstance(package, Mapping) or set(package) != {
                "relative_root",
                "file_count",
                "tree_sha256",
            }:
                raise ContractError(
                    f"approved adapter package binding for {owner} is invalid"
                )
            file_count = package.get("file_count")
            tree_digest = package.get("tree_sha256")
            if (
                package.get("relative_root") != expected_package_root
                or isinstance(file_count, bool)
                or not isinstance(file_count, int)
                or not 1 <= file_count <= 10_000
                or not isinstance(tree_digest, str)
                or _DIGEST_RE.fullmatch(tree_digest) is None
            ):
                raise ContractError(
                    f"approved adapter package binding for {owner} is not fixed"
                )
            normalized_package = {
                "relative_root": expected_package_root,
                "file_count": file_count,
                "tree_sha256": tree_digest,
            }
        normalized[owner] = {
            "relative_path": relative_path,
            "sha256": digest,
            "dependencies": normalized_dependencies,
            "package": normalized_package,
        }
    return {
        "schema": ADAPTER_MANIFEST_SCHEMA,
        "approval_id": approval_id.strip(),
        "adapters": normalized,
    }


def _manifest_digest(manifest: Mapping[str, Any]) -> str:
    return sha256(_canonical_json(manifest)).hexdigest()


def _skills_root(explicit: str | os.PathLike[str] | None) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(Path(explicit))
    environment = os.environ.get("NOVA_SKILLS_ROOT")
    if environment:
        candidates.append(Path(environment))
    candidates.append(Path(__file__).resolve().parents[3])
    for candidate in candidates:
        if not candidate.is_absolute():
            continue
        resolved = candidate.resolve(strict=False)
        if all((resolved / relative).is_file() for relative in _MODULE_PATHS.values()):
            return resolved
    raise FederationUnavailableError(
        "Nova owner skill root is unavailable; discovery alone never approves an "
        "adapter, and every executable adapter must also match the approved manifest"
    )


def _sensitivities(value: Sequence[str]) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ContractError("allowed_sensitivities must be a sequence")
    supplied = tuple(value)
    if (
        not supplied
        or any(
            not isinstance(item, str) or item not in _ALLOWED_SENSITIVITIES
            for item in supplied
        )
        or len(set(supplied)) != len(supplied)
    ):
        raise ContractError(
            "allowed_sensitivities must be a non-empty unique subset of "
            + ", ".join(_SENSITIVITY_ORDER)
        )
    selected = set(supplied)
    return tuple(item for item in _SENSITIVITY_ORDER if item in selected)


def _owners(query: str, requested: Sequence[str] | None) -> list[str]:
    if requested is not None:
        if isinstance(requested, (str, bytes)) or not isinstance(requested, Sequence):
            raise ContractError("owners must be a sequence")
        result = list(dict.fromkeys(requested))
        if not result or any(owner not in OWNER_NAMES for owner in result):
            raise ContractError(f"owners may contain only {list(OWNER_NAMES)}")
        return result
    routed = route_query(query)
    return [route["owner"] for route in routed["routes"]]


def _owner_query(query: str) -> str:
    pattern = r"\b(?:" + "|".join(re.escape(item) for item in OWNER_NAMES) + r")\s*:"
    value = re.sub(pattern, " ", query, flags=re.IGNORECASE)
    value = " ".join(value.split())
    return value or query


def _failure_result(
    owner: str,
    status: str,
    reason: str,
    sensitivities: Sequence[str],
    *,
    code: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": OWNER_RESULT_SCHEMA,
        "owner": owner,
        "status": status,
        "operation": "read",
        "writes_allowed": False,
        "canonical": False,
        "allowed_sensitivities": list(sensitivities),
        "result_sensitivities": [],
        "reason": reason,
    }
    if code:
        result["code"] = code
    return result


def _validate_worker_result(
    value: Any,
    *,
    owner: str,
    skills_root: Path,
    selector: Path,
    sensitivities: Sequence[str],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    def violation(reason: str) -> dict[str, Any]:
        return _failure_result(
            owner,
            "incompatible",
            f"{owner} adapter violated the read-result contract: {reason}",
            sensitivities,
            code="adapter_contract_violation",
        )

    if not isinstance(value, Mapping):
        return violation("result is not an object")
    result = dict(value)
    allowed_keys = {
        "schema",
        "owner",
        "status",
        "operation",
        "writes_allowed",
        "canonical",
        "allowed_sensitivities",
        "result_sensitivities",
        "sensitivity_ceiling",
        "source",
        "payload",
        "reason",
        "code",
    }
    if set(result) - allowed_keys:
        return violation("result contains unknown fields")
    status = result.get("status")
    if (
        result.get("schema") != OWNER_RESULT_SCHEMA
        or result.get("owner") != owner
        or status not in _ALLOWED_STATUSES
        or result.get("operation") != "read"
        or result.get("writes_allowed") is not False
        or result.get("canonical") is not False
    ):
        return violation("envelope fields do not match the request")
    if result.get("allowed_sensitivities") != list(sensitivities):
        return violation("allowed_sensitivities is not the requested exact set")
    observed = result.get("result_sensitivities")
    if (
        not isinstance(observed, list)
        or any(not isinstance(item, str) for item in observed)
    ):
        return violation("result_sensitivities is invalid or exceeds the exact set")
    observed_set = set(observed)
    if (
        len(observed) != len(observed_set)
        or any(item not in sensitivities for item in observed)
        or observed != [item for item in _SENSITIVITY_ORDER if item in observed_set]
    ):
        return violation("result_sensitivities is invalid or exceeds the exact set")
    successful = status in {"current", "degraded", "stale", "partial"}
    if successful:
        source = result.get("source")
        if not isinstance(source, Mapping) or set(source) != {
            "owner",
            "adapter",
            "adapter_sha256",
            "selector",
            "manifest_sha256",
            "approval_id",
        }:
            return violation("successful result lacks an exact source binding")
        entry = manifest["adapters"][owner]
        expected_adapter = os.path.normcase(
            os.path.abspath(os.fspath(skills_root / entry["relative_path"]))
        )
        actual_adapter = source.get("adapter")
        if not isinstance(actual_adapter, str):
            return violation("source adapter path does not match the approval")
        try:
            actual_adapter_path = os.path.normcase(os.path.abspath(actual_adapter))
        except (OSError, TypeError, ValueError):
            return violation("source adapter path does not match the approval")
        if actual_adapter_path != expected_adapter:
            return violation("source adapter path does not match the approval")
        if (
            source.get("owner") != owner
            or source.get("adapter_sha256") != entry["sha256"]
            or source.get("selector") != str(selector)
            or source.get("manifest_sha256") != _manifest_digest(manifest)
            or source.get("approval_id") != manifest["approval_id"]
        ):
            return violation("source binding does not match the approved manifest")
        payload = result.get("payload")
        if owner == "Continuity":
            if not isinstance(payload, Mapping):
                return violation("Continuity payload is not an object")
            ceiling = result.get("sensitivity_ceiling")
            if not observed or ceiling != observed[-1]:
                return violation("Continuity sensitivity ceiling is missing or inconsistent")
        else:
            if not isinstance(payload, list):
                return violation(f"{owner} payload is not an array")
            for item in payload:
                if not isinstance(item, Mapping) or item.get("sensitivity") not in observed:
                    return violation("payload item lacks an allowed explicit sensitivity")
    else:
        reason = result.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            return violation("failed result lacks a reason")
        if "payload" in result or "source" in result or observed:
            return violation("failed result contains payload, source, or result sensitivity")
    if status != "current":
        reason = result.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            return violation("non-current result lacks a reason")
    return result


def _worker_call(
    *,
    owner: str,
    query: str,
    limit: int,
    allowed_sensitivities: Sequence[str],
    options: Mapping[str, Any],
    skills_root: Path,
    selector: Path,
    registry_path: Path,
    timeout_ms: int,
    adapter_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    sensitivities = _sensitivities(allowed_sensitivities)
    manifest = _normalise_adapter_manifest(adapter_manifest)
    worker_path = Path(__file__).with_name("federation_worker.py")
    request = {
        "schema": WORKER_REQUEST_SCHEMA,
        "owner": owner,
        "query": query,
        "limit": limit,
        "allowed_sensitivities": list(sensitivities),
        "options": dict(options),
        "skills_root": str(skills_root),
        "selector": str(selector),
        "registry_path": str(registry_path),
        "adapter_manifest": manifest,
        "adapter_manifest_sha256": _manifest_digest(manifest),
    }
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        completed = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", str(worker_path)],
            input=_canonical_json(request),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_ms / 1000.0,
            check=False,
            creationflags=creationflags,
        )
    except subprocess.TimeoutExpired:
        return _failure_result(
            owner,
            "unavailable",
            f"{owner} read deadline exceeded",
            sensitivities,
            code="deadline_exceeded",
        )
    if len(completed.stdout) > 2_097_152 or len(completed.stderr) > 65_536:
        return _failure_result(
            owner,
            "incompatible",
            f"{owner} adapter exceeded its output budget",
            sensitivities,
            code="output_budget_exceeded",
        )
    try:
        value = load_json_bytes(completed.stdout, source=f"{owner} adapter output")
    except JsonIntegrityError as exc:
        return _failure_result(
            owner,
            "integrity_error",
            f"{owner} adapter emitted invalid JSON: {exc}",
            sensitivities,
            code="invalid_adapter_json",
        )
    if completed.returncode != 0:
        return _failure_result(
            owner,
            "incompatible",
            f"{owner} adapter exited {completed.returncode}",
            sensitivities,
            code="adapter_exit_nonzero",
        )
    return _validate_worker_result(
        value,
        owner=owner,
        skills_root=skills_root,
        selector=selector,
        sensitivities=sensitivities,
        manifest=manifest,
    )


def _aggregate(results: Sequence[Mapping[str, Any]]) -> str:
    statuses = [item["status"] for item in results]
    if not statuses:
        return "unavailable"
    if len(set(statuses)) == 1:
        return statuses[0]
    return "partial"


def _commonplace_result(
    payload: Any,
    *,
    commonplace_home: Path,
    sensitivities: Sequence[str],
) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or payload.get("status") not in {
        "current",
        "degraded",
    }:
        return _failure_result(
            "Commonplace",
            "incompatible",
            "Commonplace search returned an invalid status contract",
            sensitivities,
            code="commonplace_contract_violation",
        )
    rows = payload.get("results")
    if not isinstance(rows, list):
        return _failure_result(
            "Commonplace",
            "incompatible",
            "Commonplace search results are not an array",
            sensitivities,
            code="commonplace_contract_violation",
        )
    labels: set[str] = set()
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            sensitivity = None
        else:
            state = row.get("state")
            sensitivity = row.get("sensitivity")
            if sensitivity is None and isinstance(state, Mapping):
                sensitivity = state.get("sensitivity")
        if sensitivity not in sensitivities:
            return _failure_result(
                "Commonplace",
                "integrity_error",
                "Commonplace search returned an unlabeled or out-of-scope result",
                sensitivities,
                code="sensitivity_contract_violation",
            )
        projected = dict(row)
        projected["sensitivity"] = sensitivity
        normalized_rows.append(projected)
        labels.add(sensitivity)
    normalized_payload = dict(payload)
    normalized_payload["results"] = normalized_rows
    status = payload["status"]
    result: dict[str, Any] = {
        "schema": OWNER_RESULT_SCHEMA,
        "owner": "Commonplace",
        "status": status,
        "operation": "read",
        "writes_allowed": False,
        "canonical": False,
        "allowed_sensitivities": list(sensitivities),
        "result_sensitivities": [
            item for item in _SENSITIVITY_ORDER if item in labels
        ],
        "source": {
            "owner": "Commonplace",
            "selector": str(commonplace_home),
            "binding": payload.get("binding"),
            "semantic_status": (
                payload.get("semantic", {}).get("status")
                if isinstance(payload.get("semantic"), Mapping)
                else None
            ),
        },
        "payload": normalized_payload,
    }
    if status == "degraded":
        degradation = payload.get("degradation")
        message = degradation.get("message") if isinstance(degradation, Mapping) else None
        result["reason"] = (
            message.strip()
            if isinstance(message, str) and message.strip()
            else "Commonplace search completed in an explicitly degraded mode"
        )
    return result


def _commonplace_failure(exc: Exception, sensitivities: Sequence[str]) -> dict[str, Any]:
    code = getattr(exc, "code", exc.__class__.__name__)
    if code == "integrity_error":
        status = "integrity_error"
    elif code == "stale_index":
        status = "stale"
    elif code in {"contract_error"}:
        status = "incompatible"
    else:
        status = "unavailable"
    return _failure_result("Commonplace", status, str(exc), sensitivities, code=str(code))


def _route_state(item: Mapping[str, Any]) -> dict[str, Any]:
    actual_status = item["status"]
    route_status = _ROUTE_STATUS_MAP.get(actual_status, actual_status)
    state: dict[str, Any] = {"status": route_status, "capabilities": ["read"]}
    reason = item.get("reason")
    if route_status != "current":
        if isinstance(reason, str) and reason.strip():
            state["reason"] = reason.strip()
        else:
            state["reason"] = f"Owner reported {actual_status}"
    source = item.get("source")
    if isinstance(source, Mapping):
        locator = source.get("selector")
        if isinstance(locator, str) and locator.strip():
            state["locator"] = locator.strip()
    return state


def federated_search(
    query: str,
    *,
    estate_root: str | os.PathLike[str] | None = None,
    skills_root: str | os.PathLike[str] | None = None,
    approved_adapter_manifest: Mapping[str, Any] | None = None,
    owners: Sequence[str] | None = None,
    allowed_sensitivities: Sequence[str] = ("public", "personal"),
    limit: int = 8,
    owner_options: Mapping[str, Any] | None = None,
    commonplace_mode: str = "hybrid",
    allow_degraded: bool = False,
    graph_hops: int = 0,
    timeout_ms: int = 5_000,
    embedding_provider: Any = None,
) -> dict[str, Any]:
    """Search selected owners without copying or mutating canonical state."""

    if not isinstance(query, str) or not query.strip() or len(query) > 16_384:
        raise ContractError("query must be a non-empty string up to 16384 characters")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
        raise ContractError("limit must be between 1 and 50")
    if (
        isinstance(timeout_ms, bool)
        or not isinstance(timeout_ms, int)
        or not 100 <= timeout_ms <= 60_000
    ):
        raise ContractError("timeout_ms must be between 100 and 60000")
    if owner_options is None:
        options: dict[str, Any] = {}
    elif not isinstance(owner_options, Mapping):
        raise ContractError("owner_options must be an object")
    else:
        options = dict(owner_options)
    unknown_options = sorted(set(options) - set(OWNER_NAMES))
    if unknown_options:
        raise ContractError(f"owner_options contains unknown owners: {unknown_options}")
    if any(not isinstance(value, Mapping) for value in options.values()):
        raise ContractError("each owner_options value must be an object")

    sensitivities = _sensitivities(allowed_sensitivities)
    selected = _owners(query, owners)
    registry = load_selector_registry(estate_root)
    commonplace_home = registry.selector("NOVA_COMMONPLACE_HOME")
    concordance_home = registry.selector("NOVA_CONCORDANCE_HOME")
    assert commonplace_home is not None and concordance_home is not None
    cleaned_query = _owner_query(query)
    results: dict[str, dict[str, Any]] = {}

    if "Commonplace" in selected:
        try:
            payload = hybrid_search_concordance(
                commonplace_home,
                concordance_home,
                cleaned_query,
                mode=commonplace_mode,
                allowed_sensitivities=sensitivities,
                limit=limit,
                allow_degraded=allow_degraded,
                graph_hops=graph_hops,
                embedding_provider=embedding_provider,
            )
            results["Commonplace"] = _commonplace_result(
                payload,
                commonplace_home=commonplace_home,
                sensitivities=sensitivities,
            )
        except Exception as exc:
            results["Commonplace"] = _commonplace_failure(exc, sensitivities)

    worker_owners = [owner for owner in selected if owner in _SELECTOR_KEYS]
    if worker_owners:
        manifest = _normalise_adapter_manifest(approved_adapter_manifest)
        try:
            trusted_skills_root = _skills_root(skills_root)
        except FederationUnavailableError as exc:
            for owner in worker_owners:
                results[owner] = _failure_result(
                    owner, "unavailable", str(exc), sensitivities, code=exc.code
                )
        else:
            futures = {}
            with ThreadPoolExecutor(max_workers=min(4, len(worker_owners))) as executor:
                for owner in worker_owners:
                    selector = registry.selector(_SELECTOR_KEYS[owner], required=False)
                    if selector is None:
                        results[owner] = _failure_result(
                            owner,
                            "unavailable",
                            f"selector {_SELECTOR_KEYS[owner]} is unavailable",
                            sensitivities,
                            code="selector_unavailable",
                        )
                        continue
                    future = executor.submit(
                        _worker_call,
                        owner=owner,
                        query=cleaned_query,
                        limit=limit,
                        allowed_sensitivities=sensitivities,
                        options=dict(options.get(owner, {})),
                        skills_root=trusted_skills_root,
                        selector=selector,
                        registry_path=registry.path,
                        timeout_ms=timeout_ms,
                        adapter_manifest=manifest,
                    )
                    futures[future] = owner
                for future in as_completed(futures):
                    owner = futures[future]
                    try:
                        results[owner] = future.result()
                    except Exception as exc:
                        results[owner] = _failure_result(
                            owner,
                            "incompatible",
                            str(exc),
                            sensitivities,
                            code="federation_worker_failure",
                        )

    for owner in selected:
        if owner not in results:
            results[owner] = _failure_result(
                owner,
                "unavailable",
                _ROUTE_ONLY_REASONS.get(
                    owner, "No read adapter is available for this owner"
                ),
                sensitivities,
                code="adapter_unavailable",
            )

    ordered = [results[owner] for owner in selected]
    owner_states = {item["owner"]: _route_state(item) for item in ordered}
    if owners is None:
        routing = route_query(query, owner_states=owner_states)
    else:
        route_rows = []
        for item in ordered:
            state = _route_state(item)
            route_rows.append(
                {
                    "owner": item["owner"],
                    "status": state["status"],
                    "operation": "read",
                    "writes_allowed": False,
                    **({"reason": state["reason"]} if "reason" in state else {}),
                    **({"locator": state["locator"]} if "locator" in state else {}),
                }
            )
        routing = {
            "schema": "nova.commonplace.concordance.routes.v1",
            "status": _aggregate(route_rows),
            "query": query,
            "operation": "read",
            "writes_allowed": False,
            "routes": route_rows,
            "unknown_owner_states": [],
        }
    aggregate = _aggregate(ordered)
    return {
        "ok": aggregate in {"current", "degraded", "partial"},
        "schema": FEDERATION_SCHEMA,
        "status": aggregate,
        "operation": "read",
        "writes_allowed": False,
        "canonical": False,
        "query": query,
        "allowed_sensitivities": list(sensitivities),
        "selected_owners": selected,
        "routing": routing,
        "owners": ordered,
        "custody": {
            "registry": str(registry.path),
            "federation_store_created": False,
            "owner_payload_persisted": False,
        },
    }


__all__ = [
    "ADAPTER_MANIFEST_SCHEMA",
    "EXECUTABLE_OWNERS",
    "FEDERATION_SCHEMA",
    "FederationError",
    "FederationUnavailableError",
    "OWNER_NAMES",
    "OWNER_RESULT_SCHEMA",
    "federated_search",
]
