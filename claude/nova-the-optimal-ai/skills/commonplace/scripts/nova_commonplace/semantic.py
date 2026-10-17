"""Local-only semantic primitives for rebuildable Concordance indexes."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from ipaddress import ip_address
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import json
import math
import re
import struct


DEFAULT_OLLAMA_ENDPOINT = "http://127.0.0.1:11434"
DEFAULT_EMBEDDING_MODEL = "qwen3-embedding:0.6b"
EMBEDDING_INPUT_POLICY = "title-body-kind/v1"
_DIGEST = re.compile(r"[0-9a-f]{64}")


class SemanticError(RuntimeError):
    """Base class for typed semantic retrieval failures."""

    code = "semantic_error"

    def as_dict(self) -> dict[str, str]:
        return {"status": "error", "code": self.code, "message": str(self)}


class SemanticContractError(SemanticError):
    code = "semantic_contract_error"


class SemanticUnavailableError(SemanticError):
    code = "semantic_unavailable"


class SemanticIntegrityError(SemanticError):
    code = "semantic_integrity_error"


class SemanticProviderResponseError(SemanticIntegrityError):
    code = "semantic_provider_response_error"


class SemanticModelDriftError(SemanticIntegrityError):
    code = "semantic_model_drift"


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON object key {key!r}")
        value[key] = item
    return value


def _reject_nonfinite_json(value: str) -> Any:
    raise ValueError(f"non-finite JSON number {value!r}")


def _strict_json(payload: bytes, *, source: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_json,
        )
    except (UnicodeError, ValueError) as exc:
        raise SemanticProviderResponseError(
            f"{source} returned invalid JSON: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise SemanticProviderResponseError(
            f"{source} response must be a JSON object"
        )
    return value


def _normalise_digest(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise SemanticProviderResponseError(f"{field} must be a SHA-256 string")
    lowered = value.casefold()
    if lowered.startswith("sha256:"):
        lowered = lowered[7:]
    if _DIGEST.fullmatch(lowered) is None:
        raise SemanticProviderResponseError(f"{field} must be a lowercase SHA-256")
    return lowered


def normalise_loopback_endpoint(value: Any) -> str:
    """Accept only unauthenticated HTTP endpoints on literal/localhost loopback."""

    if not isinstance(value, str) or not value.strip():
        raise SemanticContractError("semantic endpoint must be a non-empty string")
    parsed = urlsplit(value.strip())
    if parsed.scheme.casefold() != "http":
        raise SemanticContractError("semantic endpoint must use local HTTP")
    if parsed.username is not None or parsed.password is not None:
        raise SemanticContractError("semantic endpoint must not contain credentials")
    if parsed.query or parsed.fragment:
        raise SemanticContractError("semantic endpoint must not contain query or fragment")
    if parsed.path not in ("", "/"):
        raise SemanticContractError("semantic endpoint must not contain an API path")
    hostname = parsed.hostname
    if hostname is None:
        raise SemanticContractError("semantic endpoint must contain a host")
    is_loopback = hostname.casefold() == "localhost"
    if not is_loopback:
        try:
            is_loopback = ip_address(hostname).is_loopback
        except ValueError:
            is_loopback = False
    if not is_loopback:
        raise SemanticContractError(
            "semantic endpoint is restricted to unauthenticated loopback"
        )
    try:
        port = parsed.port
    except ValueError as exc:
        raise SemanticContractError("semantic endpoint port is invalid") from exc
    if port is None:
        port = 80
    host_text = f"[{hostname}]" if ":" in hostname else hostname.casefold()
    return f"http://{host_text}:{port}"


@dataclass(frozen=True)
class SemanticIndexConfig:
    provider: str = "ollama-local"
    endpoint: str = DEFAULT_OLLAMA_ENDPOINT
    model: str = DEFAULT_EMBEDDING_MODEL
    input_policy: str = EMBEDDING_INPUT_POLICY
    batch_size: int = 16
    best_effort: bool = False
    timeout_seconds: float = 30.0

    @classmethod
    def from_value(
        cls, value: "SemanticIndexConfig | Mapping[str, Any]"
    ) -> "SemanticIndexConfig":
        if isinstance(value, cls):
            return value.validated()
        if not isinstance(value, Mapping):
            raise SemanticContractError(
                "semantic_config must be a SemanticIndexConfig or mapping"
            )
        allowed = {
            "provider", "endpoint", "model", "input_policy", "batch_size",
            "best_effort", "timeout_seconds",
        }
        unknown = set(value) - allowed
        if unknown:
            raise SemanticContractError(
                f"semantic_config contains unknown fields: {sorted(unknown)!r}"
            )
        return cls(
            provider=value.get("provider", "ollama-local"),
            endpoint=value.get("endpoint", DEFAULT_OLLAMA_ENDPOINT),
            model=value.get("model", DEFAULT_EMBEDDING_MODEL),
            input_policy=value.get("input_policy", EMBEDDING_INPUT_POLICY),
            batch_size=value.get("batch_size", 16),
            best_effort=value.get("best_effort", False),
            timeout_seconds=value.get("timeout_seconds", 30.0),
        ).validated()

    def validated(self) -> "SemanticIndexConfig":
        if self.provider != "ollama-local":
            raise SemanticContractError(
                "the built-in semantic provider must be 'ollama-local'"
            )
        endpoint = normalise_loopback_endpoint(self.endpoint)
        if not isinstance(self.model, str) or not self.model.strip():
            raise SemanticContractError("semantic model must be a non-empty string")
        model = self.model.strip()
        if len(model) > 200:
            raise SemanticContractError("semantic model is unreasonably long")
        if self.input_policy != EMBEDDING_INPUT_POLICY:
            raise SemanticContractError(
                f"unsupported semantic input policy {self.input_policy!r}"
            )
        if (
            isinstance(self.batch_size, bool)
            or not isinstance(self.batch_size, int)
            or not 1 <= self.batch_size <= 128
        ):
            raise SemanticContractError("semantic batch_size must be between 1 and 128")
        if not isinstance(self.best_effort, bool):
            raise SemanticContractError("semantic best_effort must be a boolean")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not math.isfinite(float(self.timeout_seconds))
            or not 0.1 <= float(self.timeout_seconds) <= 120.0
        ):
            raise SemanticContractError(
                "semantic timeout_seconds must be between 0.1 and 120"
            )
        return SemanticIndexConfig(
            provider=self.provider,
            endpoint=endpoint,
            model=model,
            input_policy=self.input_policy,
            batch_size=self.batch_size,
            best_effort=self.best_effort,
            timeout_seconds=float(self.timeout_seconds),
        )

    def to_dict(self) -> dict[str, Any]:
        checked = self.validated()
        return {
            "provider": checked.provider,
            "endpoint": checked.endpoint,
            "model": checked.model,
            "input_policy": checked.input_policy,
            "batch_size": checked.batch_size,
            "best_effort": checked.best_effort,
            "timeout_seconds": checked.timeout_seconds,
        }


class OllamaEmbeddingProvider:
    """Minimal stdlib client for Ollama's local tags and embed endpoints."""

    def __init__(self, config: SemanticIndexConfig) -> None:
        self.config = config.validated()

    def _request_json(
        self, method: str, path: str, payload: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(
                payload, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(
            self.config.endpoint + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                body = response.read()
        except HTTPError as exc:
            raise SemanticUnavailableError(
                f"local Ollama returned HTTP {exc.code} for {path}"
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise SemanticUnavailableError(
                f"local Ollama is unavailable at {self.config.endpoint}: {exc}"
            ) from exc
        return _strict_json(body, source=f"Ollama {path}")

    def identity(self, model: str) -> dict[str, Any]:
        response = self._request_json("GET", "/api/tags")
        models = response.get("models")
        if (
            isinstance(models, (str, bytes, bytearray))
            or not isinstance(models, Sequence)
        ):
            raise SemanticProviderResponseError(
                "Ollama /api/tags response has no models list"
            )
        matches: list[tuple[str, str]] = []
        for item in models:
            if not isinstance(item, Mapping):
                continue
            name = item.get("name", item.get("model"))
            if name == model:
                matches.append(
                    (str(name), _normalise_digest(item.get("digest"), field="model digest"))
                )
        if not matches:
            raise SemanticUnavailableError(
                f"embedding model {model!r} is not installed in local Ollama"
            )
        digests = {digest for _, digest in matches}
        if len(digests) != 1:
            raise SemanticProviderResponseError(
                f"Ollama reported conflicting digests for model {model!r}"
            )
        return {
            "provider": "ollama-local",
            "endpoint": self.config.endpoint,
            "model": model,
            "model_digest": next(iter(digests)),
        }

    def embed(self, model: str, texts: Sequence[str]) -> list[list[float]]:
        response = self._request_json(
            "POST", "/api/embed", {"model": model, "input": list(texts)}
        )
        reported_model = response.get("model")
        if reported_model is not None and reported_model != model:
            raise SemanticProviderResponseError(
                "Ollama embed response model does not match the requested model"
            )
        embeddings = response.get("embeddings")
        if (
            isinstance(embeddings, (str, bytes, bytearray))
            or not isinstance(embeddings, Sequence)
        ):
            raise SemanticProviderResponseError(
                "Ollama embed response has no embeddings list"
            )
        return list(embeddings)


def validate_provider_identity(
    identity: Any, config: SemanticIndexConfig
) -> dict[str, Any]:
    if not isinstance(identity, Mapping):
        raise SemanticProviderResponseError("semantic provider identity must be an object")
    provider = identity.get("provider")
    endpoint = identity.get("endpoint")
    model = identity.get("model")
    if provider != config.provider:
        raise SemanticProviderResponseError(
            "semantic provider identity does not match configured provider"
        )
    try:
        normalized_endpoint = normalise_loopback_endpoint(endpoint)
    except SemanticContractError as exc:
        raise SemanticProviderResponseError(str(exc)) from exc
    if normalized_endpoint != config.endpoint:
        raise SemanticProviderResponseError(
            "semantic provider identity does not match configured endpoint"
        )
    if model != config.model:
        raise SemanticProviderResponseError(
            "semantic provider identity does not match configured model"
        )
    return {
        "provider": provider,
        "endpoint": normalized_endpoint,
        "model": model,
        "model_digest": _normalise_digest(
            identity.get("model_digest"), field="model digest"
        ),
    }


def embedding_input(
    record: Mapping[str, Any], *, policy: str = EMBEDDING_INPUT_POLICY
) -> tuple[str, str]:
    if policy != EMBEDDING_INPUT_POLICY:
        raise SemanticContractError(f"unsupported semantic input policy {policy!r}")
    values = []
    for field in ("title", "body", "kind"):
        value = record.get(field)
        if not isinstance(value, str):
            raise SemanticContractError(
                f"semantic record field {field!r} must be a string"
            )
        values.append(value)
    text = f"Title: {values[0]}\n\n{values[1]}\n\nKind: {values[2]}"
    return text, sha256(text.encode("utf-8")).hexdigest()


def validate_vectors(
    vectors: Any,
    *,
    expected_count: int,
    expected_dimensions: int | None = None,
) -> tuple[list[tuple[bytes, float]], int]:
    count = len(vectors) if isinstance(vectors, Sequence) else "invalid"
    if (
        isinstance(vectors, (str, bytes, bytearray))
        or not isinstance(vectors, Sequence)
        or len(vectors) != expected_count
    ):
        raise SemanticProviderResponseError(
            f"semantic provider returned {count} vectors; expected {expected_count}"
        )
    packed: list[tuple[bytes, float]] = []
    dimensions = expected_dimensions
    for vector in vectors:
        if (
            isinstance(vector, (str, bytes, bytearray))
            or not isinstance(vector, Sequence)
            or not vector
        ):
            raise SemanticProviderResponseError(
                "semantic provider returned an empty or invalid vector"
            )
        if dimensions is None:
            dimensions = len(vector)
        if len(vector) != dimensions:
            raise SemanticProviderResponseError(
                "semantic provider returned inconsistent vector dimensions"
            )
        values: list[float] = []
        for item in vector:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise SemanticProviderResponseError(
                    "semantic provider vector elements must be numbers"
                )
            number = float(item)
            if not math.isfinite(number):
                raise SemanticProviderResponseError(
                    "semantic provider returned a non-finite vector element"
                )
            values.append(number)
        try:
            blob = struct.pack(f"<{dimensions}f", *values)
            float32_values = struct.unpack(f"<{dimensions}f", blob)
        except (OverflowError, struct.error) as exc:
            raise SemanticProviderResponseError(
                f"semantic vector cannot be represented as float32: {exc}"
            ) from exc
        if any(not math.isfinite(value) for value in float32_values):
            raise SemanticProviderResponseError(
                "semantic provider vector became non-finite as float32"
            )
        norm = math.sqrt(sum(value * value for value in float32_values))
        if not math.isfinite(norm) or norm <= 0.0:
            raise SemanticProviderResponseError(
                "semantic provider returned a zero-norm or invalid vector"
            )
        packed.append((blob, norm))
    if dimensions is None or dimensions < 1:
        raise SemanticProviderResponseError(
            "semantic provider returned no vector dimensions"
        )
    return packed, dimensions


def unpack_vector(blob: Any, dimensions: Any) -> tuple[float, ...]:
    if (
        isinstance(dimensions, bool)
        or not isinstance(dimensions, int)
        or dimensions < 1
        or not isinstance(blob, (bytes, bytearray, memoryview))
    ):
        raise SemanticIntegrityError("stored semantic vector contract is invalid")
    raw = bytes(blob)
    if len(raw) != dimensions * 4:
        raise SemanticIntegrityError(
            "stored semantic vector byte length does not match its dimensions"
        )
    try:
        values = struct.unpack(f"<{dimensions}f", raw)
    except struct.error as exc:
        raise SemanticIntegrityError(f"stored semantic vector is invalid: {exc}") from exc
    if any(not math.isfinite(value) for value in values):
        raise SemanticIntegrityError("stored semantic vector contains non-finite values")
    return values


def cosine_similarity(
    left: Sequence[float], right: Sequence[float], *, right_norm: float | None = None
) -> float:
    if len(left) != len(right) or not left:
        raise SemanticIntegrityError("semantic vectors have incompatible dimensions")
    left_norm = math.sqrt(sum(float(value) * float(value) for value in left))
    computed_right_norm = (
        float(right_norm)
        if right_norm is not None
        else math.sqrt(sum(float(value) * float(value) for value in right))
    )
    if (
        not math.isfinite(left_norm)
        or not math.isfinite(computed_right_norm)
        or left_norm <= 0.0
        or computed_right_norm <= 0.0
    ):
        raise SemanticIntegrityError("semantic vector norm is invalid")
    score = sum(float(a) * float(b) for a, b in zip(left, right)) / (
        left_norm * computed_right_norm
    )
    if not math.isfinite(score):
        raise SemanticIntegrityError("semantic cosine score is non-finite")
    return max(-1.0, min(1.0, score))


__all__ = [
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_OLLAMA_ENDPOINT",
    "EMBEDDING_INPUT_POLICY",
    "OllamaEmbeddingProvider",
    "SemanticContractError",
    "SemanticError",
    "SemanticIndexConfig",
    "SemanticIntegrityError",
    "SemanticModelDriftError",
    "SemanticProviderResponseError",
    "SemanticUnavailableError",
    "cosine_similarity",
    "embedding_input",
    "normalise_loopback_endpoint",
    "unpack_vector",
    "validate_provider_identity",
    "validate_vectors",
]
