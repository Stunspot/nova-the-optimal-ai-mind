"""Isolated read-only worker for fixed Nova owner adapters.

The parent sends one JSON request on stdin. Queries never appear in process
arguments. Every adapter is bound to a fixed path and an approved SHA-256 before
its already-verified bytes are executed.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import tempfile
from types import ModuleType
from typing import Any, Mapping, Sequence


REQUEST_SCHEMA = "nova-commonplace.federation-worker-request.v1"
RESULT_SCHEMA = "nova-commonplace.federation-owner-result.v1"
MANIFEST_SCHEMA = "nova-commonplace.federation-adapter-manifest.v2"
_ALLOWED_OWNERS = {"Dunbar", "Corkboard", "Dennis", "Continuity"}
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
_SENSITIVITY_ORDER = ("public", "personal", "private", "restricted")
_REPARSE_ATTRIBUTE = 0x400
_TOKEN_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)
_DIGEST_RE = re.compile(r"[0-9a-f]{64}")


class WorkerError(RuntimeError):
    pass


class AdapterIntegrityError(WorkerError):
    pass


def _duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise WorkerError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _loads(data: str) -> Any:
    try:
        return json.loads(
            data,
            object_pairs_hook=_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                WorkerError(f"non-finite JSON value {value!r}")
            ),
        )
    except json.JSONDecodeError as exc:
        raise WorkerError(f"invalid request JSON: {exc}") from exc


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return sha256(_dump(value).encode("utf-8")).hexdigest()


def _absolute(value: Any, *, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise WorkerError(f"{field} must be a non-empty absolute path")
    path = Path(value)
    if not path.is_absolute():
        raise WorkerError(f"{field} must be absolute")
    return Path(os.path.abspath(os.fspath(path)))


def _assert_direct_edges(path: Path, *, stop: Path | None = None) -> None:
    current = path
    stop_norm = os.path.normcase(str(stop)) if stop is not None else None
    while True:
        if os.path.lexists(current):
            observed = os.lstat(current)
            if stat.S_ISLNK(observed.st_mode):
                raise WorkerError(f"path crosses a symbolic link: {current}")
            if getattr(observed, "st_file_attributes", 0) & _REPARSE_ATTRIBUTE:
                raise WorkerError(f"path crosses a reparse edge: {current}")
        if current.parent == current or (
            stop_norm is not None and os.path.normcase(str(current)) == stop_norm
        ):
            break
        current = current.parent


def _confined(root: Path, relative: str) -> Path:
    candidate = Path(os.path.abspath(os.fspath(root / Path(relative))))
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise WorkerError("owner adapter path escapes the trusted skills root") from exc
    _assert_direct_edges(candidate, stop=root)
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def _normalise_manifest(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "schema",
        "approval_id",
        "adapters",
    }:
        raise WorkerError("adapter manifest envelope is invalid")
    if value.get("schema") != MANIFEST_SCHEMA:
        raise WorkerError("adapter manifest schema is unsupported")
    approval_id = value.get("approval_id")
    if (
        not isinstance(approval_id, str)
        or not approval_id.strip()
        or len(approval_id) > 256
    ):
        raise WorkerError("adapter manifest approval_id is invalid")
    adapters = value.get("adapters")
    if not isinstance(adapters, Mapping) or set(adapters) != set(_MODULE_PATHS):
        raise WorkerError("adapter manifest does not contain the exact fixed owner set")
    normalized: dict[str, dict[str, Any]] = {}
    for owner, fixed_path in _MODULE_PATHS.items():
        entry = adapters.get(owner)
        if not isinstance(entry, Mapping) or set(entry) != {
            "relative_path",
            "sha256",
            "dependencies",
            "package",
        }:
            raise WorkerError(f"adapter manifest entry for {owner} is invalid")
        relative_path = entry.get("relative_path")
        expected_digest = entry.get("sha256")
        if relative_path != fixed_path:
            raise WorkerError(f"adapter manifest path for {owner} is not fixed")
        if (
            not isinstance(expected_digest, str)
            or _DIGEST_RE.fullmatch(expected_digest) is None
        ):
            raise WorkerError(f"adapter manifest digest for {owner} is invalid")
        dependencies = entry.get("dependencies")
        fixed_dependencies = _DEPENDENCY_PATHS[owner]
        if not isinstance(dependencies, list) or len(dependencies) != len(
            fixed_dependencies
        ):
            raise WorkerError(
                f"adapter dependency closure for {owner} is incomplete"
            )
        normalized_dependencies: list[dict[str, str]] = []
        for supplied_dependency, (module, dependency_path) in zip(
            dependencies, fixed_dependencies
        ):
            if not isinstance(supplied_dependency, Mapping) or set(
                supplied_dependency
            ) != {"module", "relative_path", "sha256"}:
                raise WorkerError(
                    f"adapter dependency entry for {owner} is invalid"
                )
            dependency_digest = supplied_dependency.get("sha256")
            if (
                supplied_dependency.get("module") != module
                or supplied_dependency.get("relative_path") != dependency_path
                or not isinstance(dependency_digest, str)
                or _DIGEST_RE.fullmatch(dependency_digest) is None
            ):
                raise WorkerError(
                    f"adapter dependency closure for {owner} is not fixed"
                )
            normalized_dependencies.append(
                {
                    "module": module,
                    "relative_path": dependency_path,
                    "sha256": dependency_digest,
                }
            )
        package = entry.get("package")
        fixed_package_root = _PACKAGE_ROOTS[owner]
        if fixed_package_root is None:
            if package is not None:
                raise WorkerError(
                    f"adapter package binding for {owner} must be null"
                )
            normalized_package = None
        else:
            if not isinstance(package, Mapping) or set(package) != {
                "relative_root",
                "file_count",
                "tree_sha256",
            }:
                raise WorkerError(
                    f"adapter package binding for {owner} is invalid"
                )
            file_count = package.get("file_count")
            tree_digest = package.get("tree_sha256")
            if (
                package.get("relative_root") != fixed_package_root
                or isinstance(file_count, bool)
                or not isinstance(file_count, int)
                or not 1 <= file_count <= 10_000
                or not isinstance(tree_digest, str)
                or _DIGEST_RE.fullmatch(tree_digest) is None
            ):
                raise WorkerError(
                    f"adapter package binding for {owner} is not fixed"
                )
            normalized_package = {
                "relative_root": fixed_package_root,
                "file_count": file_count,
                "tree_sha256": tree_digest,
            }
        normalized[owner] = {
            "relative_path": relative_path,
            "sha256": expected_digest,
            "dependencies": normalized_dependencies,
            "package": normalized_package,
        }
    return {
        "schema": MANIFEST_SCHEMA,
        "approval_id": approval_id.strip(),
        "adapters": normalized,
    }

def _stable_bytes(path: Path, *, label: str) -> bytes:
    first = path.read_bytes()
    second = path.read_bytes()
    if first != second:
        raise AdapterIntegrityError(f"{label} changed during stable read")
    return first


def _stable_approved_bytes(
    path: Path, expected_digest: str, *, label: str
) -> bytes:
    content = _stable_bytes(path, label=label)
    observed = sha256(content).hexdigest()
    if observed != expected_digest:
        raise AdapterIntegrityError(
            f"{label} digest mismatch: expected {expected_digest}, observed {observed}"
        )
    return content


def _verified_package(
    skills_root: Path, binding: Mapping[str, Any], *, owner: str
) -> tuple[Path, dict[str, bytes]]:
    package_root = Path(
        os.path.abspath(os.fspath(skills_root / binding["relative_root"]))
    )
    try:
        package_root.relative_to(skills_root)
    except ValueError as exc:
        raise WorkerError("approved package root escapes the trusted skills root") from exc
    _assert_direct_edges(package_root, stop=skills_root)
    if not package_root.is_dir():
        raise FileNotFoundError(package_root)

    files: list[tuple[str, Path]] = []
    for current_raw, directory_names, file_names in os.walk(
        package_root, topdown=True, followlinks=False
    ):
        current = Path(current_raw)
        _assert_direct_edges(current, stop=package_root)
        retained_directories: list[str] = []
        for name in directory_names:
            child = current / name
            if name == "__pycache__":
                continue
            observed = os.lstat(child)
            if stat.S_ISLNK(observed.st_mode) or (
                getattr(observed, "st_file_attributes", 0) & _REPARSE_ATTRIBUTE
            ):
                raise AdapterIntegrityError(
                    f"{owner} approved package crosses a linked directory: {child}"
                )
            retained_directories.append(name)
        directory_names[:] = retained_directories
        for name in file_names:
            if name.endswith((".pyc", ".pyo")):
                continue
            child = current / name
            observed = os.lstat(child)
            if not stat.S_ISREG(observed.st_mode) or stat.S_ISLNK(observed.st_mode) or (
                getattr(observed, "st_file_attributes", 0) & _REPARSE_ATTRIBUTE
            ):
                raise AdapterIntegrityError(
                    f"{owner} approved package contains a non-regular file: {child}"
                )
            relative = child.relative_to(package_root).as_posix()
            files.append((relative, child))
    files.sort(key=lambda item: item[0].encode("utf-8"))
    if len(files) != binding["file_count"]:
        raise AdapterIntegrityError(
            f"{owner} package file count mismatch: expected {binding['file_count']}, "
            f"observed {len(files)}"
        )

    aggregate = sha256()
    material: dict[str, bytes] = {}
    for relative, child in files:
        content = _stable_bytes(child, label=f"{owner} package file {relative}")
        file_digest = sha256(content).digest()
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(file_digest)
        material[relative] = content
    observed_tree = aggregate.hexdigest()
    if observed_tree != binding["tree_sha256"]:
        raise AdapterIntegrityError(
            f"{owner} package tree digest mismatch: expected {binding['tree_sha256']}, "
            f"observed {observed_tree}"
        )
    return package_root, material


def _publish_verified_package(
    material: Mapping[str, bytes], *, owner: str
) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    temporary = tempfile.TemporaryDirectory(prefix="nova-federation-")
    isolated_root = Path(temporary.name) / "approved-package"
    isolated_root.mkdir()
    try:
        for relative, content in material.items():
            target = isolated_root.joinpath(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            if target.read_bytes() != content:
                raise AdapterIntegrityError(
                    f"{owner} approved package changed during isolated publication"
                )
    except BaseException:
        temporary.cleanup()
        raise
    return temporary, isolated_root


def _module(
    owner: str, skills_root: Path, manifest: Mapping[str, Any]
) -> tuple[Any, Path, str]:
    entry = manifest["adapters"][owner]
    path = _confined(skills_root, entry["relative_path"])
    package_binding = entry["package"]
    temporary_package: tempfile.TemporaryDirectory[str] | None = None

    if package_binding is None:
        adapter_bytes = _stable_approved_bytes(
            path, entry["sha256"], label=f"{owner} adapter"
        )
        execution_path = path
        dependency_material: list[tuple[str, Path, bytes]] = []
        for dependency in entry["dependencies"]:
            dependency_path = _confined(skills_root, dependency["relative_path"])
            dependency_bytes = _stable_approved_bytes(
                dependency_path,
                dependency["sha256"],
                label=f"{owner} dependency {dependency['module']}",
            )
            dependency_material.append(
                (dependency["module"], dependency_path, dependency_bytes)
            )
    else:
        package_root, package_material = _verified_package(
            skills_root, package_binding, owner=owner
        )
        temporary_package, isolated_root = _publish_verified_package(
            package_material, owner=owner
        )
        entry_relative = path.relative_to(package_root).as_posix()
        adapter_bytes = package_material.get(entry_relative)
        if adapter_bytes is None or sha256(adapter_bytes).hexdigest() != entry["sha256"]:
            temporary_package.cleanup()
            raise AdapterIntegrityError(
                f"{owner} adapter digest does not match the approved package tree"
            )
        execution_path = isolated_root.joinpath(*entry_relative.split("/"))
        dependency_material = []
        for dependency in entry["dependencies"]:
            dependency_path = _confined(skills_root, dependency["relative_path"])
            dependency_relative = dependency_path.relative_to(package_root).as_posix()
            dependency_bytes = package_material.get(dependency_relative)
            if (
                dependency_bytes is None
                or sha256(dependency_bytes).hexdigest() != dependency["sha256"]
            ):
                temporary_package.cleanup()
                raise AdapterIntegrityError(
                    f"{owner} dependency {dependency['module']} digest does not "
                    "match the approved package tree"
                )
            dependency_execution_path = isolated_root.joinpath(
                *dependency_relative.split("/")
            )
            dependency_material.append(
                (
                    dependency["module"],
                    dependency_execution_path,
                    dependency_bytes,
                )
            )

    digest = sha256(adapter_bytes).hexdigest()
    module_name = "_nova_federation_" + owner.casefold() + "_" + digest[:12]
    loaded_names: list[str] = []
    try:
        for dependency_name, dependency_path, dependency_bytes in dependency_material:
            if dependency_name in sys.modules:
                raise AdapterIntegrityError(
                    f"{owner} dependency {dependency_name} was loaded before approved execution"
                )
            dependency_module = ModuleType(dependency_name)
            dependency_module.__file__ = str(dependency_path)
            dependency_module.__package__ = ""
            sys.modules[dependency_name] = dependency_module
            loaded_names.append(dependency_name)
            dependency_code = compile(
                dependency_bytes,
                str(dependency_path),
                "exec",
                dont_inherit=True,
            )
            exec(dependency_code, dependency_module.__dict__)

        module = ModuleType(module_name)
        module.__file__ = str(execution_path)
        module.__package__ = ""
        sys.modules[module_name] = module
        code = compile(adapter_bytes, str(execution_path), "exec", dont_inherit=True)
        exec(code, module.__dict__)
        if temporary_package is not None:
            module.__dict__["_nova_verified_package"] = temporary_package
    except BaseException:
        sys.modules.pop(module_name, None)
        for dependency_name in reversed(loaded_names):
            sys.modules.pop(dependency_name, None)
        if temporary_package is not None:
            temporary_package.cleanup()
        raise
    return module, path, digest


def _request(value: Any) -> dict[str, Any]:
    required = {
        "schema",
        "owner",
        "query",
        "limit",
        "allowed_sensitivities",
        "options",
        "skills_root",
        "selector",
        "registry_path",
        "adapter_manifest",
        "adapter_manifest_sha256",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise WorkerError("unsupported federation worker request envelope")
    if value.get("schema") != REQUEST_SCHEMA:
        raise WorkerError("unsupported federation worker request")
    owner = value.get("owner")
    if owner not in _ALLOWED_OWNERS:
        raise WorkerError("owner is not in the fixed read-adapter allowlist")
    query = value.get("query")
    if not isinstance(query, str) or not query.strip() or len(query) > 16_384:
        raise WorkerError("query must be 1-16384 characters")
    limit = value.get("limit")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
        raise WorkerError("limit must be between 1 and 50")
    sensitivities = value.get("allowed_sensitivities")
    if (
        not isinstance(sensitivities, list)
        or not sensitivities
        or any(not isinstance(item, str) for item in sensitivities)
    ):
        raise WorkerError("allowed_sensitivities is not a canonical exact set")
    sensitivity_set = set(sensitivities)
    if (
        len(sensitivities) != len(sensitivity_set)
        or any(item not in _SENSITIVITY_ORDER for item in sensitivities)
        or sensitivities
        != [item for item in _SENSITIVITY_ORDER if item in sensitivity_set]
    ):
        raise WorkerError("allowed_sensitivities is not a canonical exact set")
    options = value.get("options")
    if not isinstance(options, Mapping):
        raise WorkerError("options must be an object")
    manifest = _normalise_manifest(value.get("adapter_manifest"))
    supplied_manifest_digest = value.get("adapter_manifest_sha256")
    if (
        not isinstance(supplied_manifest_digest, str)
        or supplied_manifest_digest != _digest(manifest)
    ):
        raise AdapterIntegrityError("adapter manifest digest does not match its envelope")
    result = dict(value)
    result["owner"] = owner
    result["query"] = query.strip()
    result["options"] = dict(options)
    result["adapter_manifest"] = manifest
    return result


def _source(
    owner: str,
    module_path: Path,
    digest: str,
    selector: Path,
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "owner": owner,
        "adapter": str(module_path),
        "adapter_sha256": digest,
        "selector": str(selector),
        "manifest_sha256": _digest(manifest),
        "approval_id": manifest["approval_id"],
    }


def _normalise_rows(
    raw: Any,
    *,
    allowed: Sequence[str],
    default_sensitivity: str | None = None,
    source_mapping: Mapping[str, str] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise WorkerError("owner read returned a non-array payload")
    rows: list[dict[str, Any]] = []
    labels: set[str] = set()
    mapping = dict(source_mapping or {})
    for item in raw:
        if not isinstance(item, Mapping):
            raise WorkerError("owner read returned a non-object item")
        projected = dict(item)
        observed = projected.get("sensitivity", default_sensitivity)
        normalized = mapping.get(observed, observed)
        if normalized not in _SENSITIVITY_ORDER:
            raise WorkerError("owner item has an unknown sensitivity")
        if normalized not in allowed:
            continue
        if observed != normalized:
            projected["source_sensitivity"] = observed
        projected["sensitivity"] = normalized
        rows.append(projected)
        labels.add(normalized)
    ordered = [item for item in _SENSITIVITY_ORDER if item in labels]
    return rows, ordered


def _dunbar(
    request: Mapping[str, Any], module: Any, selector: Path
) -> tuple[list[dict[str, Any]], list[str]]:
    if not selector.is_file():
        raise FileNotFoundError(selector)
    uri = selector.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    connection.execute("PRAGMA foreign_keys = ON")
    owner_mapping = {
        "public": "public",
        "internal": "personal",
        "personal": "personal",
        "private": "private",
        "restricted": "restricted",
    }
    include_restricted = "restricted" in request["allowed_sensitivities"]
    include_history = request["options"].get("include_history", False)
    if not isinstance(include_history, bool):
        raise WorkerError("Dunbar include_history must be a boolean")
    try:
        raw = module.search_items(
            connection,
            request["query"],
            None,
            include_history,
            include_restricted,
            min(200, max(request["limit"] * 4, 40)),
        )
    finally:
        connection.close()
    rows, labels = _normalise_rows(
        raw,
        allowed=request["allowed_sensitivities"],
        source_mapping=owner_mapping,
    )
    return rows[: request["limit"]], labels


def _corkboard(
    request: Mapping[str, Any], module: Any, selector: Path
) -> tuple[list[dict[str, Any]], list[str]]:
    if not selector.is_dir():
        raise FileNotFoundError(selector)
    project = request["options"].get("project")
    if project is not None and (not isinstance(project, str) or not project.strip()):
        raise WorkerError("Corkboard project must be null or a non-empty string")
    all_projects = request["options"].get("all_projects", False)
    if not isinstance(all_projects, bool):
        raise WorkerError("Corkboard all_projects must be a boolean")
    raw = module.list_pins(
        selector,
        query=request["query"],
        project=project,
        all_projects=all_projects,
        limit=request["limit"],
    )
    return _normalise_rows(
        raw,
        allowed=request["allowed_sensitivities"],
        default_sensitivity="personal",
        source_mapping={"internal": "personal"},
    )


def _tokens(value: str) -> list[str]:
    return list(
        dict.fromkeys(
            token for token in _TOKEN_RE.findall(value.casefold()) if len(token) >= 2
        )
    )[:32]


def _dennis(
    request: Mapping[str, Any], module: Any, selector: Path
) -> tuple[list[dict[str, Any]], list[str]]:
    if not selector.is_dir():
        raise FileNotFoundError(selector)
    rows, diagnostics = module.scan_store(selector)
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
        raise WorkerError("Dennis scan returned a non-array row set")
    terms = _tokens(request["query"])
    ranked: list[tuple[float, str, dict[str, Any]]] = []
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("record"), Mapping):
            raise WorkerError("Dennis scan returned a malformed row")
        record = row["record"]
        searchable = _dump(record).casefold()
        hits = sum(searchable.count(term) for term in terms)
        if terms and hits == 0:
            continue
        project = record.get("project") if isinstance(record.get("project"), dict) else {}
        current = record.get("current") if isinstance(record.get("current"), dict) else {}
        projection = {
            "project_id": project.get("id"),
            "project_name": project.get("name"),
            "owner": project.get("owner"),
            "outcome": project.get("outcome"),
            "status": project.get("status"),
            "updated_at": project.get("updated_at"),
            "current": current,
            "relative_path": row.get("relative_path"),
            "fingerprint": row.get("fingerprint"),
            "source_locators": row.get("source_locators"),
            "retrieval_score": float(hits),
            "sensitivity": "personal",
        }
        ranked.append((float(hits), str(project.get("id") or ""), projection))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    results = [item[2] for item in ranked[: request["limit"]]]
    if diagnostics:
        results.append(
            {
                "kind": "diagnostic_summary",
                "count": len(diagnostics),
                "details_withheld": True,
                "sensitivity": "personal",
            }
        )
    return _normalise_rows(
        results,
        allowed=request["allowed_sensitivities"],
        default_sensitivity="personal",
    )


def _ceiling(allowed: list[str]) -> str:
    names = ("ordinary", "limited", "sensitive", "restricted")
    return names[len(allowed) - 1]


def _continuity_status(payload: Mapping[str, Any]) -> tuple[str, str | None]:
    native = payload.get("status")
    mapped = {"ok": "current", "partial": "partial", "degraded": "degraded"}.get(
        native
    )
    if mapped is None:
        raise WorkerError("Continuity returned an unsupported native status")
    if mapped == "current":
        return mapped, None
    degradation = payload.get("degradation")
    details = ""
    if isinstance(degradation, list) and all(
        isinstance(item, str) and item.strip() for item in degradation
    ):
        details = ": " + ", ".join(sorted(set(degradation)))
    return mapped, f"Continuity returned native status {native}{details}"


def _continuity(
    request: Mapping[str, Any], module: Any, registry_path: Path
) -> tuple[dict[str, Any], list[str], str, str, str | None]:
    allowed = request["allowed_sensitivities"]
    if allowed != list(_SENSITIVITY_ORDER[: len(allowed)]):
        raise WorkerError(
            "Continuity exposes a ceiling, so a non-prefix exact sensitivity set "
            "cannot be enforced and is refused"
        )
    options = request["options"]
    scope = options.get("scope")
    if not isinstance(scope, Mapping):
        raise PermissionError("Continuity requires an explicit scope object")
    normalized_scope: dict[str, Any] = {}
    for key in ("user", "project", "agent"):
        value = scope.get(key)
        if not isinstance(value, str) or not value.strip():
            raise PermissionError(f"Continuity scope requires {key}")
        normalized_scope[key] = value.strip()
    thread = scope.get("thread")
    if thread is not None and (not isinstance(thread, str) or not thread.strip()):
        raise WorkerError("Continuity scope.thread must be null or a non-empty string")
    normalized_scope["thread"] = thread
    mode = options.get("mode", "resume")
    if mode not in {"resume", "status", "inspect"}:
        raise WorkerError("Continuity mode must be resume, status, or inspect")
    budget = options.get("budget", 12_000)
    if isinstance(budget, bool) or not isinstance(budget, int) or not 512 <= budget <= 50_000:
        raise WorkerError("Continuity budget must be between 512 and 50000")
    deadline_ms = options.get("deadline_ms", 5_000)
    if (
        isinstance(deadline_ms, bool)
        or not isinstance(deadline_ms, int)
        or not 1 <= deadline_ms <= 60_000
    ):
        raise WorkerError("Continuity deadline_ms must be between 1 and 60000")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    seed = _dump({"task": request["query"], "scope": normalized_scope, "as_of": timestamp})
    request_id = "FWR-" + sha256(seed.encode("utf-8")).hexdigest()[:16]
    worldline_request = {
        "format": "cd-worldline-request/v1",
        "request_id": request_id,
        "correlation_id": request_id,
        "operation": "worldline.compile",
        "mode": mode,
        "task": request["query"],
        "scope": normalized_scope,
        "authority": "federated-read-only",
        "sensitivity_ceiling": _ceiling(allowed),
        "as_of": timestamp,
        "expiry_minutes": 5,
        "budget": budget,
        "deadline_ms": deadline_ms,
        "required_ids": [],
        "workspace": {
            "selection_mode": "nova_ambient",
            "path": None,
            "grant_id": None,
        },
        "environment": {"name": "nova-commonplace", "version": "0.2.0"},
        "unreachable_source_ids": [],
    }
    payload = module.compile_worldline(worldline_request, registry_path=registry_path)
    if not isinstance(payload, Mapping):
        raise WorkerError("Continuity returned a non-object payload")
    status, reason = _continuity_status(payload)
    return dict(payload), list(allowed), allowed[-1], status, reason


def run(request: Mapping[str, Any]) -> dict[str, Any]:
    owner = request["owner"]
    skills_root = _absolute(request.get("skills_root"), field="skills_root")
    _assert_direct_edges(skills_root)
    if not skills_root.is_dir():
        raise FileNotFoundError(skills_root)
    selector = _absolute(request.get("selector"), field="selector")
    _assert_direct_edges(selector)
    registry_path = _absolute(request.get("registry_path"), field="registry_path")
    _assert_direct_edges(registry_path)
    manifest = request["adapter_manifest"]
    module, module_path, module_digest = _module(owner, skills_root, manifest)
    sensitivity_ceiling: str | None = None
    status = "current"
    reason: str | None = None
    if owner == "Dunbar":
        payload, labels = _dunbar(request, module, selector)
    elif owner == "Corkboard":
        payload, labels = _corkboard(request, module, selector)
    elif owner == "Dennis":
        payload, labels = _dennis(request, module, selector)
    else:
        payload, labels, sensitivity_ceiling, status, reason = _continuity(
            request, module, registry_path
        )
    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "status": status,
        "owner": owner,
        "operation": "read",
        "writes_allowed": False,
        "canonical": False,
        "allowed_sensitivities": list(request["allowed_sensitivities"]),
        "result_sensitivities": labels,
        "source": _source(
            owner, module_path, module_digest, selector, manifest
        ),
        "payload": payload,
    }
    if sensitivity_ceiling is not None:
        result["sensitivity_ceiling"] = sensitivity_ceiling
    if reason is not None:
        result["reason"] = reason
    return result


def _error_context(value: Any) -> tuple[str | None, list[str]]:
    if not isinstance(value, Mapping):
        return None, []
    owner = value.get("owner")
    if owner not in _ALLOWED_OWNERS:
        owner = None
    sensitivities = value.get("allowed_sensitivities")
    if (
        not isinstance(sensitivities, list)
        or not sensitivities
        or any(not isinstance(item, str) for item in sensitivities)
    ):
        sensitivities = []
    else:
        sensitivity_set = set(sensitivities)
        if (
            len(sensitivities) != len(sensitivity_set)
            or any(item not in _SENSITIVITY_ORDER for item in sensitivities)
        ):
            sensitivities = []
        else:
            sensitivities = [
                item for item in _SENSITIVITY_ORDER if item in sensitivity_set
            ]
    return owner, sensitivities


def _error_result(
    *,
    owner: str | None,
    sensitivities: Sequence[str],
    status: str,
    reason: str,
    code: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "status": status,
        "operation": "read",
        "writes_allowed": False,
        "canonical": False,
        "allowed_sensitivities": list(sensitivities),
        "result_sensitivities": [],
        "reason": reason,
        "code": code,
    }
    if owner is not None:
        result["owner"] = owner
    return result


def main() -> int:
    raw_value: Any = None
    try:
        raw = sys.stdin.buffer.read(1_048_577)
        if len(raw) > 1_048_576:
            raise WorkerError("worker request exceeds 1 MiB")
        raw_value = _loads(raw.decode("utf-8"))
        request = _request(raw_value)
        result = run(request)
        sys.stdout.write(_dump(result) + "\n")
        return 0
    except PermissionError as exc:
        owner, sensitivities = _error_context(raw_value)
        result = _error_result(
            owner=owner,
            sensitivities=sensitivities,
            status="scope_denied",
            reason=str(exc),
            code="scope_denied",
        )
    except AdapterIntegrityError as exc:
        owner, sensitivities = _error_context(raw_value)
        result = _error_result(
            owner=owner,
            sensitivities=sensitivities,
            status="integrity_error",
            reason=str(exc),
            code="adapter_integrity_error",
        )
    except FileNotFoundError as exc:
        owner, sensitivities = _error_context(raw_value)
        result = _error_result(
            owner=owner,
            sensitivities=sensitivities,
            status="unavailable",
            reason=f"required owner surface is unavailable: {exc}",
            code="owner_surface_unavailable",
        )
    except BaseException as exc:
        owner, sensitivities = _error_context(raw_value)
        result = _error_result(
            owner=owner,
            sensitivities=sensitivities,
            status="incompatible",
            reason=str(exc),
            code="worker_contract_error",
        )
    sys.stdout.write(_dump(result) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
