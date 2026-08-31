#!/usr/bin/env python3
"""Nova Free estate bootstrap, registry-backed launcher, and diagnostics."""

from __future__ import annotations

import argparse
import copy
import ctypes
import json
import os
import platform
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

PRODUCT_VERSION = "1.0.4"
REGISTRY_FORMAT = "nova-path-selectors/v1"
MANIFEST_FORMAT = "nova-estate-manifest/v1"
LEGACY_MANIFEST_FORMAT = "nova-data-estate/v1"
SERVICE_MANIFEST_FORMAT = "nova-emergent-estate-services/v1"
ERROR_FORMAT = "nova-emergent-operation-error/v1"
REPARSE_ATTRIBUTE = 0x400
CORE_SELECTOR_KEYS = (
    "NOVA_DATA_ROOT",
    "NOVA_CONTINUITY_HOME",
    "DUNBAR_STORE",
    "CORKBOARD_HOME",
)
KNOWN_ADDITIVE_SELECTOR_KEYS = (
    "DENNIS_PROJECT_HOME",
    "NOVA_COMMONPLACE_HOME",
    "NOVA_CONCORDANCE_HOME",
)
SELECTOR_KEYS = CORE_SELECTOR_KEYS + KNOWN_ADDITIVE_SELECTOR_KEYS
LEGACY_MIND_SELECTOR_KEYS = ("MIND_CORE_DATABASE", "MIND_HOOK_RECEIPT_DIRECTORY")
MANAGED_ENVIRONMENT_KEYS = SELECTOR_KEYS + LEGACY_MIND_SELECTOR_KEYS
SERVICE_ENTRYPOINTS = {
    "continuity": ("cognitive-continuity", "scripts", "continuity_store_v2.py"),
    "worldline": ("cognitive-continuity", "scripts", "worldline.py"),
    "dunbar": ("dunbar", "scripts", "dunbar.py"),
    "corkboard": ("corkboard", "scripts", "corkboard.py"),
    "project-management": (
        "dennis-stratton-project-management",
        "scripts",
        "project_control.py",
    ),
    "commonplace": ("commonplace", "scripts", "commonplace.py"),
}
SERVICE_LOCATIONS = {
    "continuity": "memory/continuity-v2",
    "dunbar": "memory/dunbar/people.sqlite3",
    "corkboard": "memory/corkboard",
    "project_management": "projects/project-records",
    "commonplace": "memory/commonplace",
    "concordance": "derived/concordance",
}


class NovaEstateError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def emit(value: Any, *, stream: Any = sys.stdout) -> None:
    json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=False)
    stream.write("\n")


def fail(code: str, message: str, *, detail: Any = None) -> int:
    payload: dict[str, Any] = {"format": ERROR_FORMAT, "code": code, "message": message}
    if detail is not None:
        payload["detail"] = detail
    emit(payload, stream=sys.stderr)
    return 2


def platform_default_root() -> Path:
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "Collaborative Dynamics" / "Nova"
        return Path.home() / "AppData" / "Local" / "Collaborative Dynamics" / "Nova"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Collaborative Dynamics" / "Nova"
    base = os.environ.get("XDG_DATA_HOME")
    anchor = Path(base).expanduser() if base else Path.home() / ".local" / "share"
    return anchor / "collaborative-dynamics" / "nova"


def current_estate_locator_path() -> Path:
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA")
        anchor = Path(base) if base else Path.home() / "AppData" / "Local"
        return anchor / "Collaborative Dynamics" / "Nova Operations" / "current-estate.json"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Collaborative Dynamics" / "Nova Operations" / "current-estate.json"
    base = os.environ.get("XDG_CONFIG_HOME")
    anchor = Path(base).expanduser() if base else Path.home() / ".config"
    return anchor / "collaborative-dynamics" / "nova" / "current-estate.json"


def read_current_estate_locator() -> Path | None:
    path = current_estate_locator_path()
    if not os.path.lexists(path):
        return None
    value = read_json(path)
    if value.get("format") != "nova-current-estate-locator/v1":
        raise NovaEstateError(f"Unsupported current-estate locator format: {path}")
    raw = value.get("root")
    if not isinstance(raw, str) or not raw.strip() or not Path(raw).expanduser().is_absolute():
        raise NovaEstateError(f"Current-estate locator has no absolute root: {path}")
    lexical = _lexical_absolute(Path(raw).expanduser())
    _assert_no_link_or_reparse(lexical, "Current estate")
    selected = lexical.resolve(strict=False)
    default = _lexical_absolute(platform_default_root()).resolve(strict=False)
    if selected == default:
        raise NovaEstateError("The platform-default estate must not have a duplicate current-estate locator")
    return selected


def default_root() -> Path:
    """Discover the registry location without depending on a shell environment."""
    located = read_current_estate_locator()
    return located if located is not None else platform_default_root()


def root_selection_source(value: str | None) -> str:
    if value:
        return "explicit_cli"
    return "platform_current_estate_locator" if os.path.lexists(current_estate_locator_path()) else "platform_default"


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _assert_no_link_or_reparse(path: Path, label: str) -> None:
    current = _lexical_absolute(path)
    while True:
        if os.path.lexists(current):
            try:
                observed = os.lstat(current)
            except OSError as exc:
                raise NovaEstateError(f"Could not inspect {label} path edge {current}: {exc}") from exc
            if stat.S_ISLNK(observed.st_mode):
                raise NovaEstateError(f"{label} crosses a symbolic link: {current}")
            if getattr(observed, "st_file_attributes", 0) & REPARSE_ATTRIBUTE:
                raise NovaEstateError(f"{label} crosses a reparse edge: {current}")
        if current.parent == current:
            break
        current = current.parent


def _assert_plain_tree(root: Path, label: str) -> None:
    """Reject links, reparse points, and special files before staging an owner tree."""
    _assert_no_link_or_reparse(root, label)
    pending = [root]
    while pending:
        current = pending.pop()
        try:
            entries = list(os.scandir(current))
        except OSError as exc:
            raise NovaEstateError(f"Could not inspect {label} directory {current}: {exc}") from exc
        for entry in entries:
            path = Path(entry.path)
            try:
                observed = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise NovaEstateError(f"Could not inspect {label} path {path}: {exc}") from exc
            if stat.S_ISLNK(observed.st_mode):
                raise NovaEstateError(f"{label} contains a symbolic link: {path}")
            if getattr(observed, "st_file_attributes", 0) & REPARSE_ATTRIBUTE:
                raise NovaEstateError(f"{label} contains a reparse edge: {path}")
            if stat.S_ISDIR(observed.st_mode):
                pending.append(path)
            elif not stat.S_ISREG(observed.st_mode):
                raise NovaEstateError(f"{label} contains a non-regular file: {path}")

def normalize_root(value: str | None) -> Path:
    candidate = Path(value).expanduser() if value else default_root()
    if not candidate.is_absolute():
        raise NovaEstateError("Nova data root must be an absolute path")
    lexical = _lexical_absolute(candidate)
    if lexical == Path(lexical.anchor):
        raise NovaEstateError("Nova data root cannot be a filesystem root")
    if any(part.casefold() == ".codex" for part in lexical.parts):
        raise NovaEstateError("Nova-owned state cannot live under .codex")
    _assert_no_link_or_reparse(lexical, "Nova data root")
    return lexical.resolve(strict=False)


def layout(root: Path) -> dict[str, Path]:
    return {
        "NOVA_DATA_ROOT": root,
        "NOVA_CONTINUITY_HOME": root / "memory" / "continuity-v2",
        "DUNBAR_STORE": root / "memory" / "dunbar" / "people.sqlite3",
        "CORKBOARD_HOME": root / "memory" / "corkboard",
        "DENNIS_PROJECT_HOME": root / "projects" / "project-records",
        "NOVA_COMMONPLACE_HOME": root / "memory" / "commonplace",
        "NOVA_CONCORDANCE_HOME": root / "derived" / "concordance",
        "registry": root / "estate" / "path-selectors.json",
        "manifest": root / "estate" / "manifest.json",
        "service_manifest": root / "estate" / "nova-emergent-services.json",
        "env_file": root / "estate" / "nova.env",
    }


def legacy_1_0_0_partial(root: Path) -> bool:
    """Recognize only the proven-empty footprint left by the old init order."""
    if not root.is_dir():
        return False
    allowed = {
        "memory",
        "memory/corkboard",
        "memory/dunbar",
        "memory/continuity-v2",
        "projects",
        "projects/project-records",
        "estate",
    }
    required = {"memory/corkboard", "memory/dunbar", "projects/project-records"}
    observed: set[str] = set()
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        for name in directories:
            path = current_path / name
            _assert_no_link_or_reparse(path, "Legacy partial estate")
            relative = path.relative_to(root).as_posix()
            if relative not in allowed:
                return False
            observed.add(relative)
        if files:
            return False
    return required.issubset(observed)

def skill_root() -> Path:
    return Path(__file__).resolve().parents[2]


def service_script(service: str) -> Path:
    try:
        relative = SERVICE_ENTRYPOINTS[service]
    except KeyError:
        raise NovaEstateError(f"Unknown Nova service: {service}") from None
    path = skill_root().joinpath(*relative)
    if not path.is_file():
        raise NovaEstateError(f"Nova service entrypoint is missing: {path}")
    return path


def continuity_paths() -> dict[str, Path]:
    root = skill_root() / "cognitive-continuity"
    return {
        "root": root,
        "store": root / "scripts" / "continuity_store_v2.py",
        "worldline": root / "scripts" / "worldline.py",
        "validate": root / "scripts" / "validate_continuity_v2.py",
        "runtime": root / "scripts" / "workspace_runtime.py",
        "mutation_probe": Path(__file__).resolve().parent / "probe_continuity_mutation.py",
    }


def require_continuity_package() -> dict[str, Path]:
    paths = continuity_paths()
    missing = [str(path) for key, path in paths.items() if key != "root" and not path.is_file()]
    if missing:
        raise NovaEstateError("Canonical Cognitive Continuity package is incomplete: " + ", ".join(missing))
    return paths


def read_json(path: Path) -> dict[str, Any]:
    _assert_no_link_or_reparse(path, "JSON configuration")
    try:
        first = path.read_bytes()
        second = path.read_bytes()
    except FileNotFoundError:
        raise NovaEstateError(f"Required file is missing: {path}") from None
    except OSError as exc:
        raise NovaEstateError(f"Could not read {path}: {exc}") from exc
    if first != second:
        raise NovaEstateError(f"File changed during stable read: {path}")
    try:
        value = json.loads(first.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NovaEstateError(f"Could not decode {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise NovaEstateError(f"Expected a JSON object: {path}")
    return value


def _normalized_selector(key: str, raw: Any, root: Path) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise NovaEstateError(f"Selector registry lacks {key}")
    lexical = _lexical_absolute(Path(raw).expanduser())
    _assert_no_link_or_reparse(lexical, key)
    target = lexical.resolve(strict=False)
    expected = layout(root)[key].resolve(strict=False)
    if target != expected:
        raise NovaEstateError(f"Existing {key} conflicts with the Nova Free estate layout")
    if key != "NOVA_DATA_ROOT":
        try:
            target.relative_to(root)
        except ValueError:
            raise NovaEstateError(f"{key} escapes NOVA_DATA_ROOT") from None
        if any(part.casefold() == ".codex" for part in target.parts):
            raise NovaEstateError(f"{key} resolves under .codex")
    return str(target)


def registry_upgrade_analysis(
    registry: dict[str, Any], root: Path
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    if registry.get("format") != REGISTRY_FORMAT:
        raise NovaEstateError(f"Unsupported selector registry format: {registry.get('format')!r}")
    active = registry.get("active_values")
    if not isinstance(active, dict):
        raise NovaEstateError("Selector registry lacks active_values")
    values: dict[str, str] = {}
    for key in CORE_SELECTOR_KEYS:
        values[key] = _normalized_selector(key, active.get(key), root)
    missing: list[str] = []
    for key in KNOWN_ADDITIVE_SELECTOR_KEYS:
        raw = active.get(key)
        if not isinstance(raw, str) or not raw.strip():
            missing.append(key)
            continue
        values[key] = _normalized_selector(key, raw, root)
    for key in LEGACY_MIND_SELECTOR_KEYS:
        legacy_value = active.get(key)
        if legacy_value is not None and (not isinstance(legacy_value, str) or not legacy_value.strip()):
            raise NovaEstateError(f"Existing {key} must be null or a nonempty legacy selector string")
    return active, values, missing


def registry_values(registry: dict[str, Any], root: Path) -> dict[str, str]:
    _, values, missing = registry_upgrade_analysis(registry, root)
    if missing:
        raise NovaEstateError("Selector registry lacks " + ", ".join(missing))
    return {key: values[key] for key in SELECTOR_KEYS}


def _fsync_parent(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_parent(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def custom_root_requires_locator(root: Path) -> bool:
    return root != _lexical_absolute(platform_default_root()).resolve(strict=False)


def assert_locator_conflict_free(root: Path) -> Path | None:
    located = read_current_estate_locator()
    if located is not None and located != root:
        raise NovaEstateError(
            f"Current-estate locator already selects {located}; refusing to select conflicting root {root}"
        )
    return located


def write_current_estate_locator(root: Path) -> None:
    if not custom_root_requires_locator(root):
        return
    path = current_estate_locator_path()
    _assert_no_link_or_reparse(path, "Current-estate locator")
    atomic_json(
        path,
        {
            "format": "nova-current-estate-locator/v1",
            "root": str(root),
            "registry": "estate/path-selectors.json",
            "set_at_utc": utc_now(),
            "authority": "discovery_pointer_only_registry_must_corroborate",
        },
    )


def remove_current_estate_locator_if_owned(root: Path) -> None:
    path = current_estate_locator_path()
    try:
        located = read_current_estate_locator()
    except NovaEstateError:
        return
    if located != root:
        return
    try:
        path.unlink()
        _fsync_parent(path.parent)
    except OSError:
        return


def process_environment(values: dict[str, str]) -> dict[str, str]:
    """Replace inherited Nova selectors with one exact registry snapshot."""
    env = os.environ.copy()
    for key in MANAGED_ENVIRONMENT_KEYS:
        env.pop(key, None)
    env.update({key: values[key] for key in SELECTOR_KEYS})
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env

def user_environment_values(keys: tuple[str, ...]) -> dict[str, str | None]:
    if platform.system() != "Windows":
        return {key: None for key in keys}
    import winreg

    values: dict[str, str | None] = {}
    try:
        handle = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ)
    except FileNotFoundError:
        return {key: None for key in keys}
    with handle:
        for key in keys:
            try:
                value, _ = winreg.QueryValueEx(handle, key)
                values[key] = str(value)
            except FileNotFoundError:
                values[key] = None
    return values


def require_windows_environment_flag_supported(requested: bool) -> None:
    if requested and platform.system() != "Windows":
        raise NovaEstateError("--apply-user-environment is a Windows-only convenience and must not be used on this platform")


def apply_windows_user_environment(values: dict[str, str]) -> None:
    require_windows_environment_flag_supported(True)
    import winreg

    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as handle:
        for key, value in values.items():
            winreg.SetValueEx(handle, key, 0, winreg.REG_SZ, value)
    try:
        ctypes.windll.user32.SendMessageTimeoutW(
            0xFFFF,
            0x001A,
            0,
            "Environment",
            0x0002,
            5000,
            None,
        )
    except Exception:
        pass


def run_json(
    command: Sequence[str],
    *,
    env: dict[str, str] | None = None,
    input_value: Any = None,
) -> tuple[int, Any, str]:
    completed = subprocess.run(
        list(command),
        env=env,
        input=(json.dumps(input_value, ensure_ascii=False) + "\n" if input_value is not None else None),
        stdin=(None if input_value is not None else subprocess.DEVNULL),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    parsed: Any = None
    if stdout:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            parsed = stdout
    return completed.returncode, parsed, stderr


def service_command(service: str, service_args: Sequence[str]) -> list[str]:
    return [sys.executable, "-B", "-X", "utf8", str(service_script(service)), *service_args]


def run_service_process(
    service: str,
    service_args: Sequence[str],
    values: dict[str, str],
    *,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = service_command(service, service_args)
    options: dict[str, Any] = {
        "env": process_environment(values),
        "check": False,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if capture:
        options.update(
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    return subprocess.run(command, **options)


def commonplace_support(values: dict[str, str], *, verify: bool) -> dict[str, Any]:
    operation = "verify" if verify else "status"
    try:
        command = service_command(
            "commonplace",
            ["--estate-root", values["NOVA_DATA_ROOT"], operation, "--json"],
        )
    except NovaEstateError as exc:
        return {
            "available": False,
            "exit_code": None,
            "operation": operation,
            "result": None,
            "error": str(exc),
            "canonical": None,
            "concordance": {"status": "unavailable", "reason": "entrypoint_missing"},
        }
    code, result, stderr = run_json(
        command,
        env=process_environment(values),
    )
    payload: dict[str, Any] = {
        "available": code == 0,
        "exit_code": code,
        "operation": operation,
        "result": result,
    }
    if stderr:
        payload["stderr"] = stderr
    if isinstance(result, dict):
        if verify:
            payload["canonical"] = result.get("canonical")
            payload["concordance"] = result.get("concordance")
        else:
            payload["canonical"] = {
                key: value for key, value in result.items() if key != "concordance"
            }
            payload["concordance"] = result.get("concordance")
    return payload


def launcher_payload() -> dict[str, Any]:
    entries: dict[str, Any] = {}
    ready = True
    for service, relative in SERVICE_ENTRYPOINTS.items():
        path = skill_root().joinpath(*relative)
        present = path.is_file()
        entries[service] = {"path": str(path), "present": present}
        ready = ready and present
    return {
        "ready": ready,
        "shell_used": False,
        "selector_source": "estate/path-selectors.json",
        "services": entries,
    }


def probe_mutation_support(canonical: dict[str, Path], values: dict[str, str]) -> dict[str, Any]:
    code, result, stderr = run_json(
        [
            sys.executable,
            "-B",
            "-X",
            "utf8",
            str(canonical["mutation_probe"]),
            "--runtime",
            str(canonical["runtime"]),
            "--workspace",
            values["NOVA_CONTINUITY_HOME"],
        ],
        env=process_environment(values),
    )
    if not isinstance(result, dict):
        result = {
            "format": "nova-continuity-mutation-support/v1",
            "supported": False,
            "probe_completed": False,
            "code": "probe_output_invalid",
            "detail": result,
            "source_mutated": False,
        }
    result["exit_code"] = code
    if stderr:
        result["stderr"] = stderr
    return result


def continuity_support(values: dict[str, str], *, validate: bool) -> dict[str, Any]:
    canonical = require_continuity_package()
    env = process_environment(values)
    open_code, opened, open_stderr = run_json(
        [sys.executable, "-B", "-X", "utf8", str(canonical["store"]), "open"],
        env=env,
    )
    result: dict[str, Any] = {
        "read": {
            "supported": open_code == 0,
            "exit_code": open_code,
            "result": opened,
            "stderr": open_stderr or None,
        },
        "mutation": probe_mutation_support(canonical, values),
    }
    if validate:
        code, validated, stderr = run_json(
            [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                str(canonical["validate"]),
                values["NOVA_CONTINUITY_HOME"],
            ],
            env=env,
        )
        result["validation"] = {
            "supported": code == 0,
            "exit_code": code,
            "result": validated,
            "stderr": stderr or None,
        }
    return result


def load_configured_root(root_value: str | None) -> tuple[Path, dict[str, str], dict[str, Path]]:
    root = normalize_root(root_value)
    paths = layout(root)
    registry = read_json(paths["registry"])
    return root, registry_values(registry, root), paths


def status_payload(root: Path, *, root_source: str = "explicit") -> dict[str, Any]:
    paths = layout(root)
    payload: dict[str, Any] = {
        "format": "nova-emergent-estate-status/v2",
        "product_version": PRODUCT_VERSION,
        "root": str(root),
        "root_selection_source": root_source,
        "selector_authority": "registry",
        "registry": {"path": str(paths["registry"]), "present": paths["registry"].is_file()},
        "manifest": {"path": str(paths["manifest"]), "present": paths["manifest"].is_file()},
        "configured": False,
        "global_environment_required": False,
        "restart_required": False,
        "current_estate_locator": {
            "path": str(current_estate_locator_path()),
            "present": os.path.lexists(current_estate_locator_path()),
            "role": "discovery_pointer_only",
        },
    }
    if not paths["registry"].is_file():
        if legacy_1_0_0_partial(root):
            payload["state"] = "legacy_1_0_0_partial"
            payload["repair"] = "retry init against the same root; only the proven-empty legacy footprint will be replaced"
        else:
            payload["state"] = "not_configured"
        payload["default_is_outside_codex"] = ".codex" not in {part.casefold() for part in root.parts}
        return payload
    try:
        registry = read_json(paths["registry"])
        _, _, missing = registry_upgrade_analysis(registry, root)
        if missing:
            payload["state"] = "upgrade_required"
            payload["missing_selectors"] = missing
            payload["upgrade_paths"] = {key: str(paths[key]) for key in missing}
            return payload
        values = registry_values(registry, root)
        support = continuity_support(values, validate=False)
        commonplace = commonplace_support(values, verify=False)
        launcher = launcher_payload()
        environment_matches = {key: os.environ.get(key) == value for key, value in values.items()}
        continuity_present = Path(values["NOVA_CONTINUITY_HOME"]).is_dir()
        project_records_present = Path(values["DENNIS_PROJECT_HOME"]).is_dir()
        commonplace_present = Path(values["NOVA_COMMONPLACE_HOME"]).is_dir()
        concordance_present = Path(values["NOVA_CONCORDANCE_HOME"]).is_dir()
        canonical_commonplace = commonplace.get("canonical")
        commonplace_initialized = bool(
            commonplace.get("available")
            and isinstance(canonical_commonplace, dict)
            and canonical_commonplace.get("initialized")
        )
        concordance = commonplace.get("concordance")
        concordance_state = (
            concordance.get("status", "unavailable") if isinstance(concordance, dict) else "unavailable"
        )
        read_supported = bool(support["read"].get("supported"))
        mutation_supported = bool(support["mutation"].get("supported"))
        if read_supported and mutation_supported:
            operating_mode = "full"
        elif read_supported:
            operating_mode = "read_only"
        else:
            operating_mode = "unavailable"
        payload.update(
            selectors=values,
            environment_convenience={
                "supported": platform.system() == "Windows",
                "required": False,
                "matches_current_process": environment_matches,
            },
            configured=True,
            continuity_present=continuity_present,
            project_records_present=project_records_present,
            commonplace_present=commonplace_present,
            concordance_present=concordance_present,
            continuity_read_support=support["read"],
            continuity_mutation_support=support["mutation"],
            continuity_operating_mode=operating_mode,
            commonplace=commonplace,
            commonplace_initialized=commonplace_initialized,
            concordance_state=concordance_state,
            launcher=launcher,
            state=(
                "configured_service_missing"
                if not (
                    continuity_present
                    and project_records_present
                    and commonplace_present
                    and concordance_present
                    and launcher["ready"]
                    and commonplace_initialized
                )
                else (
                    "configured_service_attention"
                    if concordance_state not in {"current", "unavailable"}
                    else "configured"
                )
            ),
        )
    except NovaEstateError as exc:
        payload["state"] = "registry_invalid"
        payload["error"] = str(exc)
    return payload

def command_plan(args: argparse.Namespace) -> int:
    root = normalize_root(args.root)
    paths = layout(root)
    current = status_payload(root, root_source=root_selection_source(args.root))
    state = current.get("state")
    manifest_format: str | None = None
    if paths["manifest"].is_file():
        try:
            observed_manifest_format = read_json(paths["manifest"]).get("format")
            if isinstance(observed_manifest_format, str):
                manifest_format = observed_manifest_format
        except NovaEstateError:
            manifest_format = None

    if state == "upgrade_required":
        missing = [key for key in current.get("missing_selectors", []) if key in KNOWN_ADDITIVE_SELECTOR_KEYS]
        exact_commonplace_addition = missing == ["NOVA_COMMONPLACE_HOME", "NOVA_CONCORDANCE_HOME"]
        operation = "add_commonplace_and_concordance" if exact_commonplace_addition else "additive_upgrade"
        proposed_selectors = {key: str(paths[key]) for key in missing}
        effects = [
            "add only the missing approved selectors to the authoritative registry",
            "stage and publish an empty generation-zero Commonplace plus its bound empty lexical, model-free Concordance",
            "update the Nova environment helper and product-service metadata before the registry commit point",
            "preserve every existing canonical owner and its bytes unchanged",
        ]
        if "DENNIS_PROJECT_HOME" in missing:
            effects.insert(1, "create the missing centralized Project Management location")
        does_not = [
            "initialize, move, rewrite, or delete existing Cognitive Continuity",
            "modify existing Corkboard, Dunbar, Project Management, MIND, pursuit, persona, repository, or external-corpus state",
            "capture notes, crawl files, or copy specialist-owner state into Commonplace or Concordance",
            "replace or relabel a historical nova-data-estate/v1 manifest",
            "install or replace the Nova Free plugin, publish, or migrate a live estate without separate execution authority",
        ]
    elif state in {"configured", "configured_service_attention", "configured_service_missing"}:
        operation = "no_selector_change"
        proposed_selectors = {}
        effects = ["make no selector or estate mutation; inspect the reported service state"]
        does_not = ["initialize or overwrite any configured service"]
    elif state == "registry_invalid":
        operation = "blocked_for_inspection"
        proposed_selectors = {}
        effects = ["make no mutation until the invalid registry condition is resolved"]
        does_not = ["guess, replace, or normalize conflicting owner selectors"]
    else:
        operation = "initialize_estate"
        proposed_selectors = {key: str(paths[key]) for key in SELECTOR_KEYS}
        effects = [
            "initialize one absent Cognitive Continuity v2 workspace",
            "publish one complete selector registry and estate manifest",
            "create empty Corkboard, Dunbar, and centralized Project Management locations plus an empty generation-zero Commonplace and bound lexical, model-free Concordance",
            "optionally set current-user environment selectors on Windows",
        ]
        does_not = [
            "install or replace the Nova Free plugin",
            "import contacts, conversations, projects, reminders, or existing stores",
            "capture notes, crawl files, or copy specialist-owner state into Commonplace or Concordance",
            "enable Arm's Reach, a prompt hook, a local model, embeddings, or a vector database",
            "delete, migrate, merge, or publish data",
        ]

    emit(
        {
            "format": "nova-emergent-estate-plan/v2",
            "product_version": PRODUCT_VERSION,
            "root": str(root),
            "operation": operation,
            "current": current,
            "proposed_selectors": proposed_selectors,
            "manifest_strategy": (
                "preserve_historical_manifest_and_publish_additive_product_service_sidecar"
                if manifest_format == LEGACY_MANIFEST_FORMAT
                else "use_product_estate_manifest"
            ),
            "effects_if_authorized": effects,
            "runtime_contract": {
                "selector_authority": "registry",
                "global_environment_required": False,
                "launcher": "nova_estate.py run",
            },
            "does_not": does_not,
        }
    )
    return 0
def command_status(args: argparse.Namespace) -> int:
    root = normalize_root(args.root)
    emit(status_payload(root, root_source=root_selection_source(args.root)))
    return 0


def _create_parent_chain(parent: Path) -> list[Path]:
    missing: list[Path] = []
    cursor = parent
    while not cursor.exists():
        missing.append(cursor)
        if cursor.parent == cursor:
            raise NovaEstateError(f"Cannot create estate parent: {parent}")
        cursor = cursor.parent
    _assert_no_link_or_reparse(cursor, "Estate parent")
    created: list[Path] = []
    try:
        for path in reversed(missing):
            path.mkdir()
            created.append(path)
    except OSError as exc:
        for path in reversed(created):
            try:
                path.rmdir()
            except OSError:
                pass
        raise NovaEstateError(f"Could not create estate parent {parent}: {exc}") from exc
    return created


def _cleanup_empty_parents(created: Sequence[Path]) -> None:
    for path in reversed(created):
        try:
            path.rmdir()
        except OSError:
            pass


def _bootstrap_environment() -> dict[str, str]:
    env = os.environ.copy()
    for key in MANAGED_ENVIRONMENT_KEYS:
        env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _selector_values(paths: dict[str, Path]) -> dict[str, str]:
    return {key: str(paths[key]) for key in SELECTOR_KEYS}


def _env_text(
    values: dict[str, str], *, active_values: dict[str, Any] | None = None
) -> str:
    exported = dict(values)
    if active_values is not None:
        for key in LEGACY_MIND_SELECTOR_KEYS:
            value = active_values.get(key)
            if isinstance(value, str) and value.strip():
                exported[key] = value
    return "\n".join(f"export {key}={json.dumps(value)}" for key, value in exported.items()) + "\n"


def command_init(args: argparse.Namespace) -> int:
    require_windows_environment_flag_supported(args.apply_user_environment)
    root = normalize_root(args.root)
    locator_preexisting = assert_locator_conflict_free(root)
    paths = layout(root)
    legacy_partial = False
    if root.exists():
        current = status_payload(root, root_source="explicit_cli")
        if current.get("configured"):
            emit(
                {
                    "format": "nova-emergent-estate-init/v2",
                    "state": "already_configured",
                    "status": current,
                    "source_mutated": False,
                }
            )
            return 0
        if current.get("state") == "legacy_1_0_0_partial":
            legacy_partial = True
        else:
            raise NovaEstateError("Estate target already exists but is not a complete configured estate; inspect it before repair")

    canonical = require_continuity_package()
    created_parents: list[Path] = []
    staging: Path | None = None
    legacy_backup: Path | None = None
    published = False
    try:
        created_parents = _create_parent_chain(root.parent)
        staging = Path(tempfile.mkdtemp(prefix=f".{root.name}.init-", dir=root.parent))
        staged_paths = layout(staging)
        staged_paths["CORKBOARD_HOME"].mkdir(parents=True, exist_ok=False)
        staged_paths["DUNBAR_STORE"].parent.mkdir(parents=True, exist_ok=False)
        staged_paths["DENNIS_PROJECT_HOME"].mkdir(parents=True, exist_ok=False)
        staged_paths["NOVA_COMMONPLACE_HOME"].mkdir(parents=True, exist_ok=False)
        staged_paths["NOVA_CONCORDANCE_HOME"].mkdir(parents=True, exist_ok=False)
        continuity = staged_paths["NOVA_CONTINUITY_HOME"]
        code, receipt, stderr = run_json(
            [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                str(canonical["store"]),
                "init",
                str(continuity),
                "--user",
                args.user,
                "--project",
                "*",
                "--agent",
                "Nova",
            ],
            env=_bootstrap_environment(),
        )
        if code != 0:
            raise NovaEstateError(f"Cognitive Continuity initialization failed: {stderr or receipt}")

        staged_selector_values = _selector_values(staged_paths)
        atomic_json(
            staged_paths["registry"],
            {
                "format": REGISTRY_FORMAT,
                "active_values": {
                    **staged_selector_values,
                    "MIND_CORE_DATABASE": None,
                    "MIND_HOOK_RECEIPT_DIRECTORY": None,
                },
            },
        )
        commonplace_code, commonplace_receipt, commonplace_error = run_json(
            service_command(
                "commonplace",
                ["--estate-root", str(staging), "init", "--stdin-json", "--json"],
            ),
            env=process_environment(staged_selector_values),
            input_value={
                "authority": {
                    "actor": "Nova Operations",
                    "source": "estate-init",
                    "reason": f"Nova Free {PRODUCT_VERSION} estate initialization authorized for {args.user}",
                }
            },
        )
        if commonplace_code != 0:
            raise NovaEstateError(
                f"Commonplace initialization failed: {commonplace_error or commonplace_receipt}"
            )
        concordance_code, concordance_receipt, concordance_error = run_json(
            service_command(
                "commonplace",
                ["--estate-root", str(staging), "rebuild", "--stdin-json", "--json"],
            ),
            env=process_environment(staged_selector_values),
            input_value={"allowed_sensitivities": ["public", "personal"]},
        )
        if concordance_code != 0:
            raise NovaEstateError(
                f"Concordance initialization failed: {concordance_error or concordance_receipt}"
            )

        selector_values = _selector_values(paths)
        previous = (
            user_environment_values(SELECTOR_KEYS)
            if args.apply_user_environment
            else {key: None for key in SELECTOR_KEYS}
        )
        registry = {
            "format": REGISTRY_FORMAT,
            "set_at_utc": utc_now(),
            "scope": "UserEnvironmentAndProductRegistry" if args.apply_user_environment else "ProductRegistry",
            "requires_codex_restart": bool(args.apply_user_environment),
            "previous_user_values": previous,
            "active_values": {
                **selector_values,
                "MIND_CORE_DATABASE": None,
                "MIND_HOOK_RECEIPT_DIRECTORY": None,
            },
            "note": "The registry is authoritative. Global environment selectors are optional Windows convenience only.",
        }
        manifest = {
            "format": MANIFEST_FORMAT,
            "product": "Nova the Optimal AI Free",
            "product_version": PRODUCT_VERSION,
            "created_at_utc": utc_now(),
            "selector_registry": "estate/path-selectors.json",
            "service_launcher": "nova-operations/scripts/nova_estate.py run",
            "services": dict(SERVICE_LOCATIONS),
            "source_imported": False,
        }
        atomic_json(staged_paths["manifest"], manifest)
        atomic_text(staged_paths["env_file"], _env_text(selector_values))
        atomic_json(staged_paths["registry"], registry)
        _fsync_parent(staging)
        if legacy_partial:
            if not legacy_1_0_0_partial(root):
                raise NovaEstateError("Legacy partial estate changed during repair; nothing was replaced")
            legacy_backup = root.parent / f".{root.name}.legacy-1.0.0-{secrets.token_hex(8)}"
            os.rename(root, legacy_backup)
            try:
                os.rename(staging, root)
            except BaseException:
                os.rename(legacy_backup, root)
                legacy_backup = None
                raise
        else:
            os.rename(staging, root)
        staging = None
        published = True
        _fsync_parent(root.parent)
        write_current_estate_locator(root)
        if legacy_backup is not None:
            shutil.rmtree(legacy_backup)
            legacy_backup = None
    except BaseException:
        if staging is not None and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        if published:
            if locator_preexisting is None:
                remove_current_estate_locator_if_owned(root)
            shutil.rmtree(root, ignore_errors=True)
            if legacy_backup is not None and legacy_backup.exists() and not root.exists():
                os.rename(legacy_backup, root)
                legacy_backup = None
        _cleanup_empty_parents(created_parents)
        raise

    environment_applied = False
    if args.apply_user_environment:
        apply_windows_user_environment(selector_values)
        environment_applied = True
    emit(
        {
            "format": "nova-emergent-estate-init/v2",
            "state": "initialized",
            "root": str(root),
            "selectors": selector_values,
            "continuity_receipt": receipt,
            "commonplace_binding": {
                key: commonplace_receipt.get(key)
                for key in ("workspace_id", "generation", "snapshot_sha256")
                if isinstance(commonplace_receipt, dict) and key in commonplace_receipt
            },
            "concordance_binding": {
                key: concordance_receipt.get(key)
                for key in ("workspace_id", "generation", "canonical_snapshot_digest", "status")
                if isinstance(concordance_receipt, dict) and key in concordance_receipt
            },
            "environment_applied": environment_applied,
            "global_environment_required": False,
            "restart_required": environment_applied,
            "source_mutated": True,
            "recovered_legacy_1_0_0_partial": legacy_partial,
        }
    )
    return 0


def _optional_file_bytes(path: Path) -> bytes | None:
    if not os.path.lexists(path):
        return None
    _assert_no_link_or_reparse(path, "Estate transaction file")
    if not path.is_file():
        raise NovaEstateError(f"Estate transaction path is not a regular file: {path}")
    return path.read_bytes()


def _restore_transaction_file(path: Path, original: bytes | None) -> None:
    if original is None:
        if os.path.lexists(path):
            path.unlink()
            _fsync_parent(path.parent)
        return
    atomic_text(path, original.decode("utf-8"))


def _prepare_commonplace_upgrade(
    root: Path,
    paths: dict[str, Path],
    *,
    initialize_commonplace: bool,
    rebuild_concordance: bool,
) -> tuple[Path | None, dict[str, Any] | None, dict[str, Any] | None]:
    if not initialize_commonplace and not rebuild_concordance:
        return None, None, None
    staging = Path(tempfile.mkdtemp(prefix=f".{root.name}.commonplace-upgrade-", dir=root.parent))
    try:
        staged_paths = layout(staging)
        staged_values = _selector_values(staged_paths)
        atomic_json(
            staged_paths["registry"],
            {
                "format": REGISTRY_FORMAT,
                "active_values": {
                    **staged_values,
                    "MIND_CORE_DATABASE": None,
                    "MIND_HOOK_RECEIPT_DIRECTORY": None,
                },
            },
        )
        if initialize_commonplace:
            code, commonplace_receipt, error = run_json(
                service_command(
                    "commonplace",
                    ["--estate-root", str(staging), "init", "--stdin-json", "--json"],
                ),
                env=process_environment(staged_values),
                input_value={
                    "authority": {
                        "actor": "Nova Operations",
                        "source": "estate-upgrade",
                        "reason": f"Known additive Nova Free {PRODUCT_VERSION} estate migration",
                    }
                },
            )
            if code != 0:
                raise NovaEstateError(f"Commonplace upgrade initialization failed: {error or commonplace_receipt}")
        else:
            _assert_plain_tree(paths["NOVA_COMMONPLACE_HOME"], "Existing Commonplace")
            shutil.copytree(paths["NOVA_COMMONPLACE_HOME"], staged_paths["NOVA_COMMONPLACE_HOME"])
            code, verified, error = run_json(
                service_command(
                    "commonplace",
                    ["--estate-root", str(staging), "verify", "--json"],
                ),
                env=process_environment(staged_values),
            )
            if code != 0 or not isinstance(verified, dict) or not verified.get("ok"):
                raise NovaEstateError(f"Existing Commonplace could not be verified for Concordance migration: {error or verified}")
            commonplace_receipt = verified.get("canonical")

        concordance_receipt: dict[str, Any] | None = None
        if rebuild_concordance:
            code, rebuilt, error = run_json(
                service_command(
                    "commonplace",
                    ["--estate-root", str(staging), "rebuild", "--stdin-json", "--json"],
                ),
                env=process_environment(staged_values),
                input_value={"allowed_sensitivities": ["public", "personal"]},
            )
            if code != 0 or not isinstance(rebuilt, dict):
                raise NovaEstateError(f"Concordance upgrade initialization failed: {error or rebuilt}")
            concordance_receipt = rebuilt
        return staging, commonplace_receipt, concordance_receipt
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def command_upgrade(args: argparse.Namespace) -> int:
    require_windows_environment_flag_supported(args.apply_user_environment)
    root = normalize_root(args.root)
    locator_preexisting = assert_locator_conflict_free(root)
    paths = layout(root)
    registry = read_json(paths["registry"])
    manifest = read_json(paths["manifest"])
    manifest_format = manifest.get("format")
    legacy_manifest = manifest_format == LEGACY_MANIFEST_FORMAT
    if manifest_format not in {MANIFEST_FORMAT, LEGACY_MANIFEST_FORMAT}:
        raise NovaEstateError(f"Unsupported estate manifest format: {manifest_format!r}")

    manifest_original = paths["manifest"].read_bytes()
    if legacy_manifest:
        legacy_root = manifest.get("root")
        if (
            not isinstance(legacy_root, str)
            or not legacy_root.strip()
            or _lexical_absolute(Path(legacy_root).expanduser()).resolve(strict=False) != root
        ):
            raise NovaEstateError("Legacy estate manifest root does not match the selected root")
        if not isinstance(manifest.get("stores"), list):
            raise NovaEstateError("Legacy estate manifest lacks its historical stores list")
        service_document_path = paths["service_manifest"]
        service_document_original = _optional_file_bytes(service_document_path)
        if service_document_original is None:
            service_document = {
                "format": SERVICE_MANIFEST_FORMAT,
                "product": "Nova the Optimal AI Free",
                "source_manifest": "estate/manifest.json",
                "source_manifest_format": LEGACY_MANIFEST_FORMAT,
                "services": {},
            }
        else:
            service_document = read_json(service_document_path)
            if service_document.get("format") != SERVICE_MANIFEST_FORMAT:
                raise NovaEstateError(
                    f"Unsupported product-service manifest format: {service_document.get('format')!r}"
                )
            if service_document.get("source_manifest") != "estate/manifest.json":
                raise NovaEstateError("Product-service manifest does not bind the historical estate manifest")
    else:
        service_document_path = paths["manifest"]
        service_document_original = manifest_original
        service_document = manifest

    active, _, missing = registry_upgrade_analysis(registry, root)
    services = service_document.get("services")
    if not isinstance(services, dict):
        raise NovaEstateError("Product service metadata lacks services")
    for service, expected in SERVICE_LOCATIONS.items():
        current = services.get(service)
        if current is not None and current != expected:
            raise NovaEstateError(f"Existing {service} service location conflicts with the Nova Free estate layout")

    missing_set = set(missing)
    for key in ("NOVA_COMMONPLACE_HOME", "NOVA_CONCORDANCE_HOME"):
        target = paths[key]
        _assert_no_link_or_reparse(target, key)
        if os.path.lexists(target):
            if not target.is_dir():
                raise NovaEstateError(f"{key} target exists but is not a directory: {target}")
            if key in missing_set:
                raise NovaEstateError(
                    f"Unregistered {key} target already exists; preserving it unchanged for review: {target}"
                )

    commonplace_exists = paths["NOVA_COMMONPLACE_HOME"].is_dir()
    concordance_exists = paths["NOVA_CONCORDANCE_HOME"].is_dir()
    if "NOVA_COMMONPLACE_HOME" not in missing_set and not commonplace_exists:
        raise NovaEstateError(
            "The registry names a canonical Commonplace but its directory is missing; "
            "use governed recovery rather than initializing an empty replacement"
        )
    initialize_commonplace = "NOVA_COMMONPLACE_HOME" in missing_set
    rebuild_concordance = "NOVA_CONCORDANCE_HOME" in missing_set or not concordance_exists
    if initialize_commonplace and concordance_exists:
        raise NovaEstateError(
            "Cannot initialize a new canonical Commonplace while an existing Concordance target is present"
        )

    registry_original = paths["registry"].read_bytes()
    env_original = _optional_file_bytes(paths["env_file"])
    desired_registry = copy.deepcopy(registry)
    desired_service_document = copy.deepcopy(service_document)
    desired_active = desired_registry["active_values"]
    previous = desired_registry.get("previous_user_values")
    if not isinstance(previous, dict):
        previous = {}
        desired_registry["previous_user_values"] = previous
    for key in missing:
        previous.setdefault(key, None)
        desired_active[key] = str(paths[key])
    for key in LEGACY_MIND_SELECTOR_KEYS:
        desired_active.setdefault(key, None)

    desired_services = desired_service_document["services"]
    desired_services.update(SERVICE_LOCATIONS)
    desired_service_document["product_version"] = PRODUCT_VERSION
    desired_service_document["service_launcher"] = "nova-operations/scripts/nova_estate.py run"
    desired_values = _selector_values(paths)
    desired_env = _env_text(desired_values, active_values=desired_active)

    dennis_needs_directory = not paths["DENNIS_PROJECT_HOME"].is_dir()
    locator_needs_publication = custom_root_requires_locator(root) and locator_preexisting is None
    content_change = (
        desired_registry != registry
        or desired_service_document != service_document
        or env_original != desired_env.encode("utf-8")
        or initialize_commonplace
        or rebuild_concordance
        or dennis_needs_directory
        or locator_needs_publication
    )

    if content_change:
        timestamp = utc_now()
        desired_registry["set_at_utc"] = timestamp
        desired_registry["upgraded_for_product_version"] = PRODUCT_VERSION
        desired_registry["requires_codex_restart"] = bool(args.apply_user_environment)
        desired_registry["note"] = "The registry is authoritative. Global environment selectors are optional Windows convenience only."
        desired_service_document["upgraded_at_utc"] = timestamp

    staging: Path | None = None
    commonplace_receipt: dict[str, Any] | None = None
    concordance_receipt: dict[str, Any] | None = None
    created_parents: list[Path] = []
    published: list[tuple[Path, Path]] = []
    dennis_created = False
    estate_write_started = False
    try:
        staging, commonplace_receipt, concordance_receipt = _prepare_commonplace_upgrade(
            root,
            paths,
            initialize_commonplace=initialize_commonplace,
            rebuild_concordance=rebuild_concordance,
        )
        if content_change:
            if dennis_needs_directory:
                created_parents.extend(_create_parent_chain(paths["DENNIS_PROJECT_HOME"].parent))
                paths["DENNIS_PROJECT_HOME"].mkdir()
                dennis_created = True
            if staging is not None and initialize_commonplace:
                created_parents.extend(_create_parent_chain(paths["NOVA_COMMONPLACE_HOME"].parent))
                staged_commonplace = layout(staging)["NOVA_COMMONPLACE_HOME"]
                os.rename(staged_commonplace, paths["NOVA_COMMONPLACE_HOME"])
                published.append((paths["NOVA_COMMONPLACE_HOME"], staged_commonplace))
            if staging is not None and rebuild_concordance:
                created_parents.extend(_create_parent_chain(paths["NOVA_CONCORDANCE_HOME"].parent))
                staged_concordance = layout(staging)["NOVA_CONCORDANCE_HOME"]
                os.rename(staged_concordance, paths["NOVA_CONCORDANCE_HOME"])
                published.append((paths["NOVA_CONCORDANCE_HOME"], staged_concordance))

            estate_write_started = True
            atomic_json(service_document_path, desired_service_document)
            atomic_text(paths["env_file"], desired_env)
            if locator_needs_publication:
                write_current_estate_locator(root)
            # The authoritative selector registry is the transaction commit point.
            # Publish every ancillary locator/helper before this final replacement.
            atomic_json(paths["registry"], desired_registry)
    except BaseException as exc:
        rollback_errors: list[str] = []
        if estate_write_started:
            try:
                _restore_transaction_file(service_document_path, service_document_original)
                _restore_transaction_file(paths["env_file"], env_original)
                _restore_transaction_file(paths["registry"], registry_original)
            except BaseException as rollback_error:
                rollback_errors.append(f"estate files: {rollback_error}")
        if locator_preexisting is None:
            remove_current_estate_locator_if_owned(root)
        if not rollback_errors:
            for target, staged_target in reversed(published):
                try:
                    staged_target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists() and not staged_target.exists():
                        os.rename(target, staged_target)
                except BaseException as rollback_error:
                    rollback_errors.append(f"{target}: {rollback_error}")
            if dennis_created:
                try:
                    paths["DENNIS_PROJECT_HOME"].rmdir()
                except OSError as rollback_error:
                    rollback_errors.append(f"{paths['DENNIS_PROJECT_HOME']}: {rollback_error}")
            _cleanup_empty_parents(created_parents)
        if staging is not None and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        if rollback_errors:
            raise NovaEstateError(
                "Estate upgrade failed and rollback was incomplete: " + "; ".join(rollback_errors)
            ) from exc
        raise
    finally:
        if staging is not None and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)

    environment_applied = False
    if args.apply_user_environment:
        apply_windows_user_environment(desired_values)
        environment_applied = True
    emit(
        {
            "format": "nova-emergent-estate-upgrade/v2",
            "state": "upgraded" if content_change else "already_current",
            "product_version": PRODUCT_VERSION,
            "root": str(root),
            "selectors": desired_values,
            "added_selectors": missing,
            "project_records": str(paths["DENNIS_PROJECT_HOME"]),
            "commonplace": str(paths["NOVA_COMMONPLACE_HOME"]),
            "concordance": str(paths["NOVA_CONCORDANCE_HOME"]),
            "commonplace_binding": (
                {
                    key: commonplace_receipt.get(key)
                    for key in ("workspace_id", "generation", "snapshot_sha256")
                    if key in commonplace_receipt
                }
                if isinstance(commonplace_receipt, dict)
                else None
            ),
            "concordance_binding": (
                {
                    key: concordance_receipt.get(key)
                    for key in ("workspace_id", "generation", "canonical_snapshot_digest", "status")
                    if key in concordance_receipt
                }
                if isinstance(concordance_receipt, dict)
                else None
            ),
            "registry_commit_point": str(paths["registry"]),
            "estate_manifest": str(paths["manifest"]),
            "estate_manifest_format": manifest_format,
            "legacy_manifest_preserved": legacy_manifest,
            "service_manifest": str(service_document_path),
            "preserved_legacy_mind_selectors": [
                key for key in LEGACY_MIND_SELECTOR_KEYS if desired_active.get(key) is not None
            ],
            "environment_applied": environment_applied,
            "global_environment_required": False,
            "restart_required": environment_applied,
            "source_mutated": content_change,
        }
    )
    return 0

def command_run(args: argparse.Namespace) -> int:
    root, values, _ = load_configured_root(args.root)
    forwarded = list(args.service_args)
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    if args.service == "commonplace":
        if "--estate-root" in forwarded:
            raise NovaEstateError(
                "Commonplace estate root is supplied by Nova Operations and must not be overridden"
            )
        forwarded = ["--estate-root", str(root), *forwarded]
    completed = run_service_process(args.service, forwarded, values)
    return int(completed.returncode)


def command_doctor(args: argparse.Namespace) -> int:
    root, values, _ = load_configured_root(args.root)
    support = continuity_support(values, validate=True)
    commonplace = commonplace_support(values, verify=True)
    launcher = launcher_payload()
    locations = {
        "continuity": Path(values["NOVA_CONTINUITY_HOME"]).is_dir(),
        "dunbar_parent": Path(values["DUNBAR_STORE"]).parent.is_dir(),
        "corkboard": Path(values["CORKBOARD_HOME"]).is_dir(),
        "project_management": Path(values["DENNIS_PROJECT_HOME"]).is_dir(),
        "commonplace": Path(values["NOVA_COMMONPLACE_HOME"]).is_dir(),
        "concordance": Path(values["NOVA_CONCORDANCE_HOME"]).is_dir(),
    }
    read_supported = bool(support["read"].get("supported"))
    mutation_supported = bool(support["mutation"].get("supported"))
    validation_supported = bool(support["validation"].get("supported"))
    canonical_commonplace = commonplace.get("canonical")
    commonplace_valid = bool(
        commonplace.get("available")
        and isinstance(canonical_commonplace, dict)
        and canonical_commonplace.get("ok")
    )
    concordance = commonplace.get("concordance")
    concordance_state = concordance.get("status", "unavailable") if isinstance(concordance, dict) else "unavailable"
    healthy = (
        read_supported
        and mutation_supported
        and validation_supported
        and commonplace_valid
        and concordance_state in {"current", "unavailable"}
        and launcher["ready"]
        and all(locations.values())
    )
    operating_mode = "full" if read_supported and mutation_supported else ("read_only" if read_supported else "unavailable")
    emit(
        {
            "format": "nova-emergent-estate-doctor/v2",
            "product_version": PRODUCT_VERSION,
            "root": str(root),
            "healthy": healthy,
            "operating_mode": operating_mode,
            "selector_authority": "registry",
            "global_environment_required": False,
            "environment_convenience": {
                "supported": platform.system() == "Windows",
                "required": False,
                "matches_current_process": {
                    key: os.environ.get(key) == value for key, value in values.items()
                },
            },
            "service_locations": locations,
            "launcher": launcher,
            "continuity_read_support": support["read"],
            "continuity_mutation_support": support["mutation"],
            "continuity_validation": support["validation"],
            "commonplace": commonplace,
            "commonplace_valid": commonplace_valid,
            "concordance_state": concordance_state,
            "source_mutated": False,
        }
    )
    return 0 if healthy else 2


def command_worldline(args: argparse.Namespace) -> int:
    _, values, _ = load_configured_root(args.root)
    command_args = [
        args.mode,
        "--task",
        args.task,
        "--user",
        args.user,
        "--project",
        args.project,
        "--agent",
        "Nova",
    ]
    completed = run_service_process("worldline", command_args, values, capture=True)
    if completed.returncode == 0:
        sys.stdout.write(completed.stdout)
        if completed.stdout and not completed.stdout.endswith("\n"):
            sys.stdout.write("\n")
        return 0
    detail: Any = completed.stderr.strip() or completed.stdout.strip()
    try:
        detail = json.loads(detail)
    except (TypeError, json.JSONDecodeError):
        pass
    return fail("worldline_failed", "Canonical Worldline operation failed", detail=detail)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    for name, function in (("plan", command_plan), ("status", command_status)):
        item = commands.add_parser(name)
        item.add_argument("--root")
        item.set_defaults(function=function)

    init = commands.add_parser("init")
    init.add_argument("--root", required=True)
    init.add_argument("--user", default="local-user")
    init.add_argument("--apply-user-environment", action="store_true")
    init.set_defaults(function=command_init)

    upgrade = commands.add_parser("upgrade")
    upgrade.add_argument("--root")
    upgrade.add_argument("--apply-user-environment", action="store_true")
    upgrade.set_defaults(function=command_upgrade)

    doctor = commands.add_parser("doctor")
    doctor.add_argument("--root")
    doctor.set_defaults(function=command_doctor)

    run = commands.add_parser("run", help="Run a bundled service with the exact registry selector snapshot")
    run.add_argument("--root")
    run.add_argument("service", choices=tuple(SERVICE_ENTRYPOINTS))
    run.add_argument("service_args", nargs=argparse.REMAINDER)
    run.set_defaults(function=command_run)

    worldline = commands.add_parser("worldline", help="Compatibility facade over the registry-backed worldline service")
    worldline.add_argument("--root")
    worldline.add_argument("--mode", choices=("resume", "status", "checkpoint", "inspect"), required=True)
    worldline.add_argument("--project", required=True)
    worldline.add_argument("--task", required=True)
    worldline.add_argument("--user", default="local-user")
    worldline.set_defaults(function=command_worldline)
    return root


def main() -> int:
    try:
        args = parser().parse_args()
        return int(args.function(args))
    except NovaEstateError as exc:
        return fail("estate_error", str(exc))
    except OSError as exc:
        return fail("estate_io_error", str(exc))
    except KeyboardInterrupt:
        return fail("cancelled", "Operation cancelled before completion")


if __name__ == "__main__":
    raise SystemExit(main())