"""Registry-backed Nova Commonplace path discovery."""

from __future__ import annotations

from dataclasses import dataclass
import os
import platform
import stat
from pathlib import Path
from typing import Any

from .runtime import IntegrityError, load_json_bytes


REGISTRY_FORMAT = "nova-path-selectors/v1"
LOCATOR_FORMAT = "nova-current-estate-locator/v1"
REPARSE_ATTRIBUTE = 0x400


class RegistryError(RuntimeError):
    """Raised when Nova custody cannot be established from the registry."""


@dataclass(frozen=True)
class ServicePaths:
    root: Path
    registry: Path
    commonplace: Path
    concordance: Path


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _assert_safe_edges(path: Path, label: str) -> None:
    current = _absolute(path)
    while True:
        if os.path.lexists(current):
            observed = os.lstat(current)
            if stat.S_ISLNK(observed.st_mode):
                raise RegistryError(f"{label} crosses a symbolic link: {current}")
            if getattr(observed, "st_file_attributes", 0) & REPARSE_ATTRIBUTE:
                raise RegistryError(f"{label} crosses a reparse edge: {current}")
        if current.parent == current:
            break
        current = current.parent


def _stable_object(path: Path, label: str) -> dict[str, Any]:
    _assert_safe_edges(path, label)
    try:
        first = path.read_bytes()
        second = path.read_bytes()
    except FileNotFoundError:
        raise RegistryError(f"{label} is missing: {path}") from None
    except OSError as error:
        raise RegistryError(f"Could not read {label} {path}: {error}") from error
    if first != second:
        raise RegistryError(f"{label} changed during stable read: {path}")
    try:
        value = load_json_bytes(first, source=f"{label} {path}")
    except IntegrityError as error:
        raise RegistryError(f"Could not decode {label} {path}: {error}") from error
    if not isinstance(value, dict):
        raise RegistryError(f"{label} is not a JSON object: {path}")
    return value


def platform_default_root() -> Path:
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA")
        anchor = Path(base) if base else Path.home() / "AppData" / "Local"
        return anchor / "Collaborative Dynamics" / "Nova"
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


def discover_root(explicit_root: str | Path | None = None) -> Path:
    if explicit_root is not None:
        candidate = Path(explicit_root).expanduser()
    else:
        locator_path = current_estate_locator_path()
        if os.path.lexists(locator_path):
            locator = _stable_object(locator_path, "Current-estate locator")
            if locator.get("format") != LOCATOR_FORMAT:
                raise RegistryError(f"Unsupported current-estate locator format: {locator_path}")
            raw = locator.get("root")
            if not isinstance(raw, str) or not raw.strip():
                raise RegistryError(f"Current-estate locator has no root: {locator_path}")
            candidate = Path(raw).expanduser()
        else:
            candidate = platform_default_root()
    if not candidate.is_absolute():
        raise RegistryError("Nova data root must be absolute")
    lexical = _absolute(candidate)
    if lexical == Path(lexical.anchor):
        raise RegistryError("Nova data root cannot be a filesystem root")
    if any(part.casefold() == ".codex" for part in lexical.parts):
        raise RegistryError("Nova-owned state cannot live under .codex")
    _assert_safe_edges(lexical, "Nova data root")
    return lexical.resolve(strict=False)


def _selector(active: dict[str, Any], key: str, root: Path) -> Path:
    raw = active.get(key)
    if not isinstance(raw, str) or not raw.strip():
        raise RegistryError(f"Nova estate upgrade required: selector registry lacks {key}")
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        raise RegistryError(f"{key} must be absolute")
    lexical = _absolute(candidate)
    _assert_safe_edges(lexical, key)
    resolved = lexical.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError:
        raise RegistryError(f"{key} escapes NOVA_DATA_ROOT") from None
    if any(part.casefold() == ".codex" for part in resolved.parts):
        raise RegistryError(f"{key} resolves under .codex")
    return resolved


@dataclass(frozen=True)
class SelectorRegistry:
    """Stable read-only view of the authoritative Nova selector registry."""

    root: Path
    path: Path
    active_values: dict[str, Any]

    def selector(self, key: str, *, required: bool = True) -> Path | None:
        if key not in self.active_values or self.active_values.get(key) in (None, ""):
            if required:
                raise RegistryError(f"Nova estate upgrade required: selector registry lacks {key}")
            return None
        return _selector(self.active_values, key, self.root)


def load_selector_registry(
    explicit_root: str | Path | None = None,
) -> SelectorRegistry:
    """Read selectors stably without initializing, repairing, or writing state."""

    root = discover_root(explicit_root)
    registry_path = root / "estate" / "path-selectors.json"
    registry = _stable_object(registry_path, "Selector registry")
    if registry.get("format") != REGISTRY_FORMAT:
        raise RegistryError(f"Unsupported selector registry format: {registry_path}")
    active = registry.get("active_values")
    if not isinstance(active, dict):
        raise RegistryError("Selector registry lacks active_values")
    registered_root = _selector(active, "NOVA_DATA_ROOT", root)
    if registered_root != root:
        raise RegistryError("Registry NOVA_DATA_ROOT does not match the selected root")
    return SelectorRegistry(root, registry_path, dict(active))


def resolve_service_paths(explicit_root: str | Path | None = None) -> ServicePaths:
    registry = load_selector_registry(explicit_root)
    commonplace = registry.selector("NOVA_COMMONPLACE_HOME")
    concordance = registry.selector("NOVA_CONCORDANCE_HOME")
    assert commonplace is not None and concordance is not None
    if commonplace == concordance:
        raise RegistryError("Canonical Commonplace and derived Concordance paths must differ")
    if commonplace in concordance.parents or concordance in commonplace.parents:
        raise RegistryError("Canonical Commonplace and derived Concordance paths must not nest")
    return ServicePaths(registry.root, registry.path, commonplace, concordance)
