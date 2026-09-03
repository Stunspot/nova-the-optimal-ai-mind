#!/usr/bin/env python3
"""Deterministic, custody-neutral inference for explicit discrete HMM model sets."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ENGINE_ID = "cd-model-agnosticism-trellis"
ENGINE_VERSION = "1.0.0"
MODEL_SET_CONTRACT = "cd-model-agnosticism-model-set/v1"
SEQUENCE_CONTRACT = "cd-model-agnosticism-observation-sequence/v1"
RUN_CONTRACT = "cd-model-agnosticism-inference-run/v1"
ERROR_CONTRACT = "cd-model-agnosticism-error/v1"
VALIDATION_CONTRACT = "cd-model-agnosticism-validation/v1"
RECEIPT_ENVELOPE = "cd-model-agnosticism-receipt-envelope/v1"
ORDERING_RULE = "event_time_ascending_then_observation_id/v1"
SURPRISAL_METRIC = "mean_predictive_surprisal"
LOG_BASE = "e"
SURPRISAL_UNIT = "nats_per_observation"
MAX_BYTES = 4 * 1024 * 1024
MAX_MODELS = 32
MAX_STATES = 64
MAX_SYMBOLS = 512
MAX_OBSERVATIONS = 10_000
MAX_WORK_UNITS = 10_000_000
MAX_POSTERIOR_CELLS = 500_000
MAX_OUTPUT_BYTES = 32 * 1024 * 1024
MAX_ID_CHARS = 256
MAX_TEXT_CHARS = 16_384
MAX_REF_CHARS = 2_048
MAX_REFS = 128
MAX_NUMERIC_TOKEN_CHARS = 128
TOLERANCE = 1e-9
HEX64 = re.compile(r"^[0-9a-f]{64}$")
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
MIN_POSITIVE_FLOAT = float.fromhex("0x0.0000000000001p-1022")
LOG_MIN_POSITIVE_FLOAT = math.log(MIN_POSITIVE_FLOAT)


class TrellisError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _reject_constant(value: str) -> None:
    raise TrellisError("NON_FINITE_JSON", f"JSON constant is not permitted: {value}")


def _parse_int_token(value: str) -> int:
    digits = value[1:] if value.startswith("-") else value
    if len(digits) > MAX_NUMERIC_TOKEN_CHARS:
        raise TrellisError("NUMERIC_RANGE", "JSON integer token exceeds the supported numeric envelope")
    return int(value)


def _parse_float_token(value: str) -> float:
    if len(value) > MAX_NUMERIC_TOKEN_CHARS:
        raise TrellisError("NUMERIC_RANGE", "JSON number token exceeds the supported numeric envelope")
    try:
        exact = Decimal(value)
        parsed = float(exact)
    except (InvalidOperation, OverflowError, ValueError) as exc:
        raise TrellisError("NUMERIC_RANGE", f"JSON number is outside the supported binary64 envelope: {value}") from exc
    if not exact.is_finite() or not math.isfinite(parsed):
        raise TrellisError("NON_FINITE_JSON", f"JSON number is not finite in binary64: {value}")
    if exact != 0 and parsed == 0.0:
        raise TrellisError("NUMERIC_UNDERFLOW", f"JSON number underflows binary64 before inference: {value}")
    return parsed


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TrellisError("DUPLICATE_KEY", f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        size = path.stat().st_size
        if size > MAX_BYTES:
            raise TrellisError("RESOURCE_LIMIT", f"Input exceeds {MAX_BYTES} bytes: {path}")
        data = path.read_bytes()
    except TrellisError:
        raise
    except OSError as exc:
        raise TrellisError("INPUT_UNREADABLE", f"Cannot read {path}: {exc}") from exc
    if len(data) > MAX_BYTES:
        raise TrellisError("RESOURCE_LIMIT", f"Input exceeds {MAX_BYTES} bytes: {path}")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TrellisError("INVALID_UTF8", f"Input is not UTF-8: {path}") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_float=_parse_float_token,
            parse_int=_parse_int_token,
        )
    except TrellisError:
        raise
    except json.JSONDecodeError as exc:
        raise TrellisError("INVALID_JSON", f"Malformed JSON in {path}: {exc.msg}") from exc
    except RecursionError as exc:
        raise TrellisError("RESOURCE_LIMIT", f"JSON nesting exceeds the supported envelope: {path}") from exc
    if not isinstance(value, dict):
        raise TrellisError("INVALID_DOCUMENT", f"Top-level JSON value must be an object: {path}")
    return value


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (UnicodeEncodeError, ValueError, OverflowError) as exc:
        raise TrellisError("NON_CANONICAL_VALUE", "Value cannot be represented as canonical finite UTF-8 JSON") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _exact_object(value: Any, path: str, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TrellisError("INVALID_FIELD", f"{path} must be an object")
    actual = set(value)
    missing = sorted(keys - actual)
    extra = sorted(actual - keys)
    if missing:
        raise TrellisError("MISSING_FIELD", f"{path} is missing required fields: {', '.join(missing)}")
    if extra:
        raise TrellisError("UNKNOWN_FIELD", f"{path} contains unsupported fields: {', '.join(extra)}")
    return value


def _valid_unicode(value: str, path: str) -> None:
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise TrellisError("INVALID_UNICODE", f"{path} contains a non-scalar Unicode value") from exc


def _need_string(value: Any, path: str, *, max_chars: int = MAX_TEXT_CHARS) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TrellisError("INVALID_FIELD", f"{path} must be a non-empty string")
    _valid_unicode(value, path)
    if len(value) > max_chars:
        raise TrellisError("RESOURCE_LIMIT", f"{path} exceeds {max_chars} characters")
    return value


def _need_id(value: Any, path: str) -> str:
    result = _need_string(value, path, max_chars=MAX_ID_CHARS)
    if any(ord(character) < 0x20 for character in result):
        raise TrellisError("INVALID_FIELD", f"{path} contains a control character")
    return result


def _need_digest(value: Any, path: str) -> str:
    result = _need_string(value, path, max_chars=64)
    if not HEX64.fullmatch(result):
        raise TrellisError("INVALID_DIGEST", f"{path} must be 64 hexadecimal characters")
    return result


def _need_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise TrellisError("INVALID_FIELD", f"{path} must be boolean")
    return value


def _positive_int(value: Any, path: str) -> int:
    if type(value) is not int or value < 1:
        raise TrellisError("INVALID_FIELD", f"{path} must be a positive integer")
    return value


def _nonnegative_int(value: Any, path: str) -> int:
    if type(value) is not int or value < 0:
        raise TrellisError("INVALID_FIELD", f"{path} must be a non-negative integer")
    return value


def _number(value: Any, path: str, *, allow_none: bool = False) -> float | None:
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TrellisError("INVALID_PROBABILITY", f"{path} must be a finite number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise TrellisError("NUMERIC_RANGE", f"{path} is outside the supported binary64 envelope") from exc
    if not math.isfinite(result):
        raise TrellisError("INVALID_PROBABILITY", f"{path} must be finite")
    return result


def _probability(value: Any, path: str, *, allow_none: bool = False) -> float | None:
    result = _number(value, path, allow_none=allow_none)
    if result is None:
        return None
    if result < 0.0 or result > 1.0:
        raise TrellisError("INVALID_PROBABILITY", f"{path} must be within [0, 1]")
    return result


def _string_list(
    value: Any,
    path: str,
    *,
    nonempty: bool = False,
    max_items: int = MAX_REFS,
    max_chars: int = MAX_REF_CHARS,
    unique: bool = False,
) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        suffix = " and non-empty" if nonempty else ""
        raise TrellisError("INVALID_FIELD", f"{path} must be a list{suffix}")
    if len(value) > max_items:
        raise TrellisError("RESOURCE_LIMIT", f"{path} exceeds {max_items} entries")
    result = [_need_string(item, f"{path}[{index}]", max_chars=max_chars) for index, item in enumerate(value)]
    if unique and len(result) != len(set(result)):
        raise TrellisError("DUPLICATE_ID", f"{path} contains duplicate entries")
    return result


def _check_unique(values: list[str], path: str) -> None:
    if len(values) != len(set(values)):
        raise TrellisError("DUPLICATE_ID", f"{path} contains duplicate identifiers")


def _distribution(values: Any, length: int, path: str) -> list[float]:
    if not isinstance(values, list) or len(values) != length:
        raise TrellisError("INVALID_DIMENSION", f"{path} must contain exactly {length} probabilities")
    result = [_probability(item, f"{path}[{index}]") for index, item in enumerate(values)]
    typed = [float(item) for item in result]
    total = math.fsum(typed)
    if abs(total - 1.0) > TOLERANCE:
        raise TrellisError("NON_STOCHASTIC", f"{path} must sum to 1 within {TOLERANCE}")
    return [item / total for item in typed]


def _matrix(value: Any, rows: int, columns: int, path: str) -> list[list[float]]:
    if not isinstance(value, list) or len(value) != rows:
        raise TrellisError("INVALID_DIMENSION", f"{path} must contain exactly {rows} rows")
    return [_distribution(row, columns, f"{path}[{index}]") for index, row in enumerate(value)]


def _parse_time(value: Any, path: str) -> datetime:
    text = _need_string(value, path, max_chars=64)
    if not RFC3339.fullmatch(text):
        raise TrellisError("INVALID_TIME", f"{path} must be an RFC-3339 timestamp")
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise TrellisError("INVALID_TIME", f"{path} must be an RFC-3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise TrellisError("INVALID_TIME", f"{path} must include an offset or Z")
    return parsed.astimezone(timezone.utc)


def _validate_calibration(value: Any, path: str) -> dict[str, Any] | None:
    if value is None:
        return None
    calibration = _exact_object(
        value,
        path,
        {"calibration_id", "revision", "digest", "metric", "log_base", "unit", "encoder_digest", "step_semantics"},
    )
    _need_id(calibration["calibration_id"], f"{path}.calibration_id")
    _positive_int(calibration["revision"], f"{path}.revision")
    calibration["digest"] = _need_digest(calibration["digest"], f"{path}.digest")
    if calibration["metric"] != SURPRISAL_METRIC:
        raise TrellisError("UNSUPPORTED_POLICY", f"{path}.metric must be {SURPRISAL_METRIC}")
    if calibration["log_base"] != LOG_BASE:
        raise TrellisError("UNSUPPORTED_POLICY", f"{path}.log_base must be {LOG_BASE}")
    if calibration["unit"] != SURPRISAL_UNIT:
        raise TrellisError("UNSUPPORTED_POLICY", f"{path}.unit must be {SURPRISAL_UNIT}")
    calibration["encoder_digest"] = _need_digest(calibration["encoder_digest"], f"{path}.encoder_digest")
    _need_string(calibration["step_semantics"], f"{path}.step_semantics")
    return calibration
def validate_model_set(document: dict[str, Any]) -> dict[str, Any]:
    document = _exact_object(
        document,
        "model_set",
        {
            "contract", "model_set_id", "revision", "case_ref", "question", "scope",
            "observation_contract", "models", "comparison_contract", "reframe_policy", "provenance",
        },
    )
    if document["contract"] != MODEL_SET_CONTRACT:
        raise TrellisError("UNSUPPORTED_CONTRACT", f"model-set contract must be {MODEL_SET_CONTRACT}")
    _need_id(document["model_set_id"], "model_set_id")
    _positive_int(document["revision"], "revision")
    _need_string(document["case_ref"], "case_ref", max_chars=MAX_REF_CHARS)
    _need_string(document["question"], "question")
    _need_string(document["scope"], "scope")

    observation = _exact_object(
        document["observation_contract"],
        "observation_contract",
        {
            "encoder_id", "encoder_version", "encoder_digest", "step_semantics",
            "ordering_rule", "missing_policy", "oov_policy", "symbols",
        },
    )
    _need_id(observation["encoder_id"], "observation_contract.encoder_id")
    _need_id(observation["encoder_version"], "observation_contract.encoder_version")
    observation["encoder_digest"] = _need_digest(observation["encoder_digest"], "observation_contract.encoder_digest")
    _need_string(observation["step_semantics"], "observation_contract.step_semantics")
    if observation["ordering_rule"] != ORDERING_RULE:
        raise TrellisError("UNSUPPORTED_POLICY", f"observation_contract.ordering_rule must be {ORDERING_RULE}")
    _need_string(observation["missing_policy"], "observation_contract.missing_policy")
    if observation["oov_policy"] != "error":
        raise TrellisError("UNSUPPORTED_POLICY", "observation_contract.oov_policy must be error")
    symbols_raw = observation["symbols"]
    if not isinstance(symbols_raw, list) or not 1 <= len(symbols_raw) <= MAX_SYMBOLS:
        raise TrellisError("RESOURCE_LIMIT", f"observation_contract.symbols must contain 1..{MAX_SYMBOLS} entries")
    symbol_ids: list[str] = []
    for index, raw_item in enumerate(symbols_raw):
        item = _exact_object(raw_item, f"observation_contract.symbols[{index}]", {"symbol_id", "definition", "coding_rule"})
        symbol_ids.append(_need_id(item["symbol_id"], f"observation_contract.symbols[{index}].symbol_id"))
        _need_string(item["definition"], f"observation_contract.symbols[{index}].definition")
        _need_string(item["coding_rule"], f"observation_contract.symbols[{index}].coding_rule")
    _check_unique(symbol_ids, "observation_contract.symbols")

    models = document["models"]
    if not isinstance(models, list) or not 1 <= len(models) <= MAX_MODELS:
        raise TrellisError("RESOURCE_LIMIT", f"models must contain 1..{MAX_MODELS} entries")
    model_ids: list[str] = []
    normalized_models: list[dict[str, Any]] = []
    for model_index, raw_model in enumerate(models):
        prefix = f"models[{model_index}]"
        model = _exact_object(
            raw_model,
            prefix,
            {
                "model_id", "label", "model_version", "family", "prior_model_weight", "state_order",
                "states", "initial", "transition", "emission", "assumptions", "parameter_basis",
                "evidence_refs", "calibration_ref", "comparison_eligible",
            },
        )
        model_id = _need_id(model["model_id"], f"{prefix}.model_id")
        model_ids.append(model_id)
        _need_string(model["label"], f"{prefix}.label")
        _need_id(model["model_version"], f"{prefix}.model_version")
        if model["family"] != "discrete_first_order_hmm":
            raise TrellisError("UNSUPPORTED_MODEL", f"{prefix}.family must be discrete_first_order_hmm")
        state_order = _string_list(
            model["state_order"], f"{prefix}.state_order", nonempty=True,
            max_items=MAX_STATES, max_chars=MAX_ID_CHARS, unique=True,
        )
        states = model["states"]
        if not isinstance(states, list) or len(states) != len(state_order):
            raise TrellisError("INVALID_DIMENSION", f"{prefix}.states must match state_order")
        declared_order: list[str] = []
        for state_index, raw_state in enumerate(states):
            state = _exact_object(raw_state, f"{prefix}.states[{state_index}]", {"state_id", "meaning"})
            declared_order.append(_need_id(state["state_id"], f"{prefix}.states[{state_index}].state_id"))
            _need_string(state["meaning"], f"{prefix}.states[{state_index}].meaning")
        if declared_order != state_order:
            raise TrellisError("ORDER_MISMATCH", f"{prefix}.states must follow state_order exactly")
        initial = _distribution(model["initial"], len(state_order), f"{prefix}.initial")
        transition = _matrix(model["transition"], len(state_order), len(state_order), f"{prefix}.transition")
        emission = _matrix(model["emission"], len(state_order), len(symbol_ids), f"{prefix}.emission")
        assumptions = _exact_object(
            model["assumptions"], f"{prefix}.assumptions",
            {"markov_order", "output_independence", "one_observation_per_step", "stationarity_window"},
        )
        if type(assumptions["markov_order"]) is not int or assumptions["markov_order"] != 1:
            raise TrellisError("UNSUPPORTED_MODEL", f"{prefix}.assumptions.markov_order must be integer 1")
        for field in ("output_independence", "one_observation_per_step", "stationarity_window"):
            _need_string(assumptions[field], f"{prefix}.assumptions.{field}")
        _need_string(model["parameter_basis"], f"{prefix}.parameter_basis")
        _string_list(model["evidence_refs"], f"{prefix}.evidence_refs", nonempty=True, unique=True)
        calibration_ref = _validate_calibration(model["calibration_ref"], f"{prefix}.calibration_ref")
        comparison_eligible = _need_bool(model["comparison_eligible"], f"{prefix}.comparison_eligible")
        prior = _probability(model["prior_model_weight"], f"{prefix}.prior_model_weight", allow_none=True)
        if prior is not None and prior <= 0.0:
            raise TrellisError(
                "INVALID_PROBABILITY",
                f"{prefix}.prior_model_weight must be strictly positive when declared; "
                "exact zero is reserved for structural probabilities within the bounded supplied HMM",
            )
        normalized_models.append(
            {
                "raw": model,
                "model_id": model_id,
                "state_order": state_order,
                "initial": initial,
                "transition": transition,
                "emission": emission,
                "log_initial": [_safe_log(item) for item in initial],
                "log_transition": [[_safe_log(item) for item in row] for row in transition],
                "log_emission": [[_safe_log(item) for item in row] for row in emission],
                "prior": prior,
                "comparison_eligible": comparison_eligible,
                "calibration_ref": calibration_ref,
                "model_artifact_digest": digest(model),
                "effective_model_digest": digest({"model": model, "observation_contract": observation}),
            }
        )
    _check_unique(model_ids, "models")

    comparison = _exact_object(
        document["comparison_contract"],
        "comparison_contract",
        {
            "status", "shared_observation_semantics_required", "shared_sequence_required",
            "prior_basis", "calibration_basis", "absolute_fit_policy",
        },
    )
    if comparison["status"] not in {"eligible", "ineligible"}:
        raise TrellisError("INVALID_FIELD", "comparison_contract.status must be eligible or ineligible")
    for field in ("shared_observation_semantics_required", "shared_sequence_required"):
        _need_bool(comparison[field], f"comparison_contract.{field}")
    for field in ("prior_basis", "calibration_basis"):
        if comparison[field] is not None:
            _need_string(comparison[field], f"comparison_contract.{field}")
    fit_policy = comparison["absolute_fit_policy"]
    if fit_policy is not None:
        fit_policy = _exact_object(
            fit_policy,
            "comparison_contract.absolute_fit_policy",
            {"metric", "log_base", "unit", "threshold", "direction", "calibration_ref"},
        )
        if fit_policy["metric"] != SURPRISAL_METRIC:
            raise TrellisError("UNSUPPORTED_POLICY", f"absolute_fit_policy.metric must be {SURPRISAL_METRIC}")
        if fit_policy["log_base"] != LOG_BASE:
            raise TrellisError("UNSUPPORTED_POLICY", f"absolute_fit_policy.log_base must be {LOG_BASE}")
        if fit_policy["unit"] != SURPRISAL_UNIT:
            raise TrellisError("UNSUPPORTED_POLICY", f"absolute_fit_policy.unit must be {SURPRISAL_UNIT}")
        if fit_policy["direction"] != "lte":
            raise TrellisError("UNSUPPORTED_POLICY", "absolute_fit_policy.direction must be lte")
        threshold = _number(fit_policy["threshold"], "comparison_contract.absolute_fit_policy.threshold")
        if threshold is None or threshold < 0.0:
            raise TrellisError("INVALID_FIELD", "absolute_fit_policy.threshold must be non-negative")
        _validate_calibration(fit_policy["calibration_ref"], "comparison_contract.absolute_fit_policy.calibration_ref")

    reframe_policy = _exact_object(
        document["reframe_policy"], "reframe_policy", {"all_zero_likelihood", "all_absolute_fit_fail"}
    )
    if reframe_policy["all_zero_likelihood"] != "required" or reframe_policy["all_absolute_fit_fail"] != "required":
        raise TrellisError("INVALID_FIELD", "reframe_policy must require all-zero and all-fit-fail reframing")
    provenance = _exact_object(document["provenance"], "provenance", {"created_by", "source_refs"})
    _need_string(provenance["created_by"], "provenance.created_by")
    _string_list(provenance["source_refs"], "provenance.source_refs", nonempty=True, unique=True)
    return {
        "document": document,
        "digest": digest(document),
        "observation_contract_digest": digest(observation),
        "symbol_ids": symbol_ids,
        "models": normalized_models,
        "comparison": comparison,
    }
def _validate_prior_sequence(value: Any, sequence_id: str, revision: int) -> dict[str, Any] | None:
    if revision == 1:
        if value is not None:
            raise TrellisError("INVALID_REVISION_CHAIN", "revision 1 must have prior_sequence null")
        return None
    prior = _exact_object(value, "prior_sequence", {"sequence_id", "revision", "digest"})
    if _need_id(prior["sequence_id"], "prior_sequence.sequence_id") != sequence_id:
        raise TrellisError("BINDING_MISMATCH", "prior_sequence.sequence_id must match sequence_id")
    if _positive_int(prior["revision"], "prior_sequence.revision") != revision - 1:
        raise TrellisError("INVALID_REVISION_CHAIN", "prior_sequence.revision must be the immediately preceding revision")
    prior["digest"] = _need_digest(prior["digest"], "prior_sequence.digest")
    return prior


def _validate_supersedes(value: Any, path: str) -> dict[str, Any]:
    supersedes = _exact_object(
        value, path, {"sequence_id", "sequence_revision", "sequence_digest", "observation_id"}
    )
    _need_id(supersedes["sequence_id"], f"{path}.sequence_id")
    _positive_int(supersedes["sequence_revision"], f"{path}.sequence_revision")
    supersedes["sequence_digest"] = _need_digest(supersedes["sequence_digest"], f"{path}.sequence_digest")
    _need_id(supersedes["observation_id"], f"{path}.observation_id")
    return supersedes


def validate_sequence(document: dict[str, Any], model_set: dict[str, Any]) -> dict[str, Any]:
    document = _exact_object(
        document,
        "observation_sequence",
        {
            "contract", "sequence_id", "revision", "prior_sequence", "case_ref", "model_set_id",
            "model_set_revision", "model_set_digest", "encoder", "analysis_as_of", "ordering_rule",
            "step_semantics", "items",
        },
    )
    if document["contract"] != SEQUENCE_CONTRACT:
        raise TrellisError("UNSUPPORTED_CONTRACT", f"observation-sequence contract must be {SEQUENCE_CONTRACT}")
    sequence_id = _need_id(document["sequence_id"], "sequence_id")
    revision = _positive_int(document["revision"], "revision")
    prior_sequence = _validate_prior_sequence(document["prior_sequence"], sequence_id, revision)
    if document["case_ref"] != model_set["document"]["case_ref"]:
        raise TrellisError("BINDING_MISMATCH", "observation sequence case_ref differs from model set")
    if _need_id(document["model_set_id"], "model_set_id") != model_set["document"]["model_set_id"]:
        raise TrellisError("BINDING_MISMATCH", "observation sequence model_set_id differs")
    model_set_revision = _positive_int(document["model_set_revision"], "model_set_revision")
    if model_set_revision != model_set["document"]["revision"]:
        raise TrellisError("BINDING_MISMATCH", "observation sequence model_set_revision differs")
    if _need_digest(document["model_set_digest"], "model_set_digest") != model_set["digest"]:
        raise TrellisError("BINDING_MISMATCH", "observation sequence model_set_digest differs from canonical model-set digest")
    encoder = _exact_object(document["encoder"], "encoder", {"encoder_id", "encoder_version", "encoder_digest"})
    source_encoder = model_set["document"]["observation_contract"]
    for field in ("encoder_id", "encoder_version"):
        _need_id(encoder[field], f"encoder.{field}")
        if encoder[field] != source_encoder[field]:
            raise TrellisError("ENCODER_MISMATCH", f"encoder.{field} differs from the model-set observation contract")
    encoder_digest = _need_digest(encoder["encoder_digest"], "encoder.encoder_digest")
    if encoder_digest != source_encoder["encoder_digest"]:
        raise TrellisError("ENCODER_MISMATCH", "encoder.encoder_digest differs from the model-set observation contract")
    if document["ordering_rule"] != ORDERING_RULE or document["ordering_rule"] != source_encoder["ordering_rule"]:
        raise TrellisError("ENCODER_MISMATCH", f"ordering_rule must be {ORDERING_RULE}")
    if document["step_semantics"] != source_encoder["step_semantics"]:
        raise TrellisError("ENCODER_MISMATCH", "step_semantics differs from the model-set observation contract")
    _need_string(document["step_semantics"], "step_semantics")
    analysis_as_of = _parse_time(document["analysis_as_of"], "analysis_as_of")
    items = document["items"]
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_OBSERVATIONS:
        raise TrellisError("RESOURCE_LIMIT", f"items must contain 1..{MAX_OBSERVATIONS} observations")
    symbol_lookup = {symbol: index for index, symbol in enumerate(model_set["symbol_ids"])}
    observation_ids: list[str] = []
    symbol_indices: list[int] = []
    parsed_items: list[dict[str, Any]] = []
    declared_dependencies = False
    for index, raw_item in enumerate(items):
        prefix = f"items[{index}]"
        item = _exact_object(
            raw_item,
            prefix,
            {
                "observation_id", "sequence_index", "symbol_id", "event_time", "known_at",
                "source_refs", "coding_basis", "coding_status", "dependence_refs", "supersedes",
            },
        )
        observation_id = _need_id(item["observation_id"], f"{prefix}.observation_id")
        observation_ids.append(observation_id)
        sequence_index = _nonnegative_int(item["sequence_index"], f"{prefix}.sequence_index")
        if sequence_index != index:
            raise TrellisError("ORDER_MISMATCH", f"{prefix}.sequence_index must be {index}")
        symbol = _need_id(item["symbol_id"], f"{prefix}.symbol_id")
        if symbol not in symbol_lookup:
            raise TrellisError("OOV_SYMBOL", f"{prefix}.symbol_id is outside the declared observation vocabulary: {symbol}")
        symbol_indices.append(symbol_lookup[symbol])
        event_time = _parse_time(item["event_time"], f"{prefix}.event_time")
        known_at = _parse_time(item["known_at"], f"{prefix}.known_at")
        if known_at > analysis_as_of:
            raise TrellisError("FUTURE_KNOWLEDGE", f"{prefix}.known_at exceeds analysis_as_of")
        _string_list(item["source_refs"], f"{prefix}.source_refs", nonempty=True, unique=True)
        _need_string(item["coding_basis"], f"{prefix}.coding_basis")
        if item["coding_status"] not in {"observed", "corrected"}:
            raise TrellisError("INVALID_FIELD", f"{prefix}.coding_status must be observed or corrected")
        dependencies = _string_list(item["dependence_refs"], f"{prefix}.dependence_refs", unique=True)
        declared_dependencies = declared_dependencies or bool(dependencies)
        if item["coding_status"] == "observed":
            if item["supersedes"] is not None:
                raise TrellisError("INVALID_SUPERSESSION", f"{prefix}.observed item must have supersedes null")
            supersedes = None
        else:
            if item["supersedes"] is None:
                raise TrellisError("INVALID_SUPERSESSION", f"{prefix}.corrected item must bind a prior observation")
            supersedes = _validate_supersedes(item["supersedes"], f"{prefix}.supersedes")
        parsed_items.append(
            {"observation_id": observation_id, "event_time": event_time, "known_at": known_at, "supersedes": supersedes}
        )
    _check_unique(observation_ids, "items.observation_id")
    order_keys = [(item["event_time"], item["observation_id"]) for item in parsed_items]
    if order_keys != sorted(order_keys):
        raise TrellisError("ORDER_MISMATCH", f"items must follow {ORDERING_RULE}")

    superseded_ids: list[str] = []
    for index, item in enumerate(parsed_items):
        supersedes = item["supersedes"]
        if supersedes is None:
            continue
        if prior_sequence is None:
            raise TrellisError("INVALID_SUPERSESSION", f"items[{index}] correction requires a bound prior_sequence")
        if (
            supersedes["sequence_id"] != prior_sequence["sequence_id"]
            or supersedes["sequence_revision"] != prior_sequence["revision"]
            or supersedes["sequence_digest"] != prior_sequence["digest"]
        ):
            raise TrellisError("BINDING_MISMATCH", f"items[{index}].supersedes differs from prior_sequence binding")
        target = supersedes["observation_id"]
        if target in observation_ids:
            raise TrellisError("DOUBLE_COUNT_RISK", f"items[{index}] supersedes an observation still present in the effective sequence")
        superseded_ids.append(target)
    if len(superseded_ids) != len(set(superseded_ids)):
        raise TrellisError("DUPLICATE_SUPERSESSION", "multiple current observations supersede the same prior observation")

    event_before_known = all(item["event_time"] <= item["known_at"] for item in parsed_items)
    knowledge_monotonic = all(
        parsed_items[index - 1]["known_at"] <= parsed_items[index]["known_at"]
        for index in range(1, len(parsed_items))
    )
    filtered_is_as_known_then = event_before_known and knowledge_monotonic
    temporal_mode = "historical_prefix" if filtered_is_as_known_then else "retrospective_event_order"
    return {
        "document": document,
        "digest": digest(document),
        "observation_ids": observation_ids,
        "symbol_indices": symbol_indices,
        "declared_dependencies": declared_dependencies,
        "filtered_is_as_known_then": filtered_is_as_known_then,
        "temporal_mode": temporal_mode,
        "correction_count": len(superseded_ids),
        "prior_sequence": prior_sequence,
    }
def _safe_log(value: float) -> float:
    return math.log(value) if value > 0.0 else -math.inf


def _logsumexp(values: list[float]) -> float:
    maximum = max(values)
    if maximum == -math.inf:
        return -math.inf
    return maximum + math.log(math.fsum(math.exp(value - maximum) for value in values))


def _finite_exp(value: float) -> tuple[float | None, bool]:
    if value == -math.inf:
        return 0.0, False
    if not math.isfinite(value):
        raise TrellisError("NUMERIC_FAILURE", "A non-finite log value escaped the inference kernel")
    if value < LOG_MIN_POSITIVE_FLOAT:
        return None, True
    result = math.exp(value)
    if result == 0.0:
        return None, True
    return result, False


def _posterior_from_logs(values: list[float]) -> list[float]:
    if all(value == -math.inf for value in values):
        raise TrellisError("NUMERIC_FAILURE", "Cannot normalize an all-zero posterior")
    normalized = _logsumexp(values)
    probabilities = [0.0 if value == -math.inf else math.exp(value - normalized) for value in values]
    total = math.fsum(probabilities)
    if total <= 0.0 or not math.isfinite(total):
        raise TrellisError("NUMERIC_FAILURE", "Posterior normalization failed")
    return [value / total for value in probabilities]


def estimate_resources(
    model_set: dict[str, Any],
    sequence: dict[str, Any],
    *,
    decode: bool,
    smoothing: bool,
) -> dict[str, Any]:
    observation_count = len(sequence["symbol_indices"])
    work_units = 0
    posterior_cells = 0
    estimated_output_bytes = 8_192 + sum(len(item.encode("utf-8")) + 8 for item in sequence["observation_ids"])
    for model in model_set["models"]:
        state_count = len(model["state_order"])
        recurrence_units = state_count + max(0, observation_count - 1) * state_count * state_count
        work_units += recurrence_units
        if smoothing:
            work_units += max(0, observation_count - 1) * state_count * state_count
        if decode:
            work_units += recurrence_units
        model_cells = observation_count * state_count
        posterior_cells += model_cells * (1 + int(smoothing))
        estimated_output_bytes += 2_048 + sum(len(item.encode("utf-8")) + 8 for item in model["state_order"])
        estimated_output_bytes += observation_count * (192 + 28 * state_count)
        if smoothing:
            estimated_output_bytes += observation_count * (112 + 28 * state_count)
        if decode:
            estimated_output_bytes += observation_count * 12
    estimate = {
        "work_units": work_units,
        "posterior_cells": posterior_cells,
        "estimated_output_bytes": estimated_output_bytes,
        "limits": {
            "max_work_units": MAX_WORK_UNITS,
            "max_posterior_cells": MAX_POSTERIOR_CELLS,
            "max_output_bytes": MAX_OUTPUT_BYTES,
        },
    }
    exceeded: list[str] = []
    if work_units > MAX_WORK_UNITS:
        exceeded.append(f"work_units={work_units}>{MAX_WORK_UNITS}")
    if posterior_cells > MAX_POSTERIOR_CELLS:
        exceeded.append(f"posterior_cells={posterior_cells}>{MAX_POSTERIOR_CELLS}")
    if estimated_output_bytes > MAX_OUTPUT_BYTES:
        exceeded.append(f"estimated_output_bytes={estimated_output_bytes}>{MAX_OUTPUT_BYTES}")
    if exceeded:
        raise TrellisError("RESOURCE_LIMIT", "Inference request exceeds the safe envelope: " + "; ".join(exceeded))
    return estimate


def forward(model: dict[str, Any], symbols: list[int]) -> dict[str, Any]:
    log_initial = model["log_initial"]
    log_transition = model["log_transition"]
    log_emission = model["log_emission"]
    state_count = len(model["state_order"])
    log_filtered_vectors: list[list[float] | None] = []
    step_log_probabilities: list[float] = []
    log_likelihood = 0.0
    previous: list[float] | None = None
    zero_at: int | None = None
    for step, symbol in enumerate(symbols):
        if previous is None:
            log_unscaled = [log_initial[state] + log_emission[state][symbol] for state in range(state_count)]
        else:
            log_unscaled = []
            for target in range(state_count):
                log_prediction = _logsumexp(
                    [previous[source] + log_transition[source][target] for source in range(state_count)]
                )
                log_unscaled.append(log_prediction + log_emission[target][symbol])
        log_scale = _logsumexp(log_unscaled)
        step_log_probabilities.append(log_scale)
        if log_scale == -math.inf:
            zero_at = step
            log_filtered_vectors.append(None)
            for _ in range(step + 1, len(symbols)):
                log_filtered_vectors.append(None)
                step_log_probabilities.append(-math.inf)
            log_likelihood = -math.inf
            break
        current = [value - log_scale for value in log_unscaled]
        log_filtered_vectors.append(current)
        previous = current
        log_likelihood += log_scale
    mean_surprisal = math.inf if log_likelihood == -math.inf else -log_likelihood / len(symbols)
    return {
        "status": "zero_likelihood" if zero_at is not None else "completed",
        "zero_at": zero_at,
        "log_filtered_vectors": log_filtered_vectors,
        "step_log_probabilities": step_log_probabilities,
        "log_likelihood": log_likelihood,
        "mean_surprisal": mean_surprisal,
    }


def filtered_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, log_vector in enumerate(result["log_filtered_vectors"]):
        log_predictive = result["step_log_probabilities"][index]
        predictive, underflow = _finite_exp(log_predictive)
        rows.append(
            {
                "sequence_index": index,
                "log_predictive_probability": None if log_predictive == -math.inf else log_predictive,
                "predictive_probability": predictive,
                "predictive_probability_underflow": underflow,
                "posterior": None if log_vector is None else _posterior_from_logs(log_vector),
            }
        )
    return rows


def smooth(model: dict[str, Any], symbols: list[int], result: dict[str, Any]) -> list[dict[str, Any]] | None:
    if result["status"] != "completed":
        return None
    log_transition = model["log_transition"]
    log_emission = model["log_emission"]
    state_count = len(model["state_order"])
    length = len(symbols)
    log_beta = [[0.0] * state_count for _ in range(length)]
    for step in range(length - 2, -1, -1):
        log_scale = result["step_log_probabilities"][step + 1]
        for source in range(state_count):
            log_beta[step][source] = _logsumexp(
                [
                    log_transition[source][target]
                    + log_emission[target][symbols[step + 1]]
                    + log_beta[step + 1][target]
                    for target in range(state_count)
                ]
            ) - log_scale
    output: list[dict[str, Any]] = []
    for step in range(length):
        log_filtered = result["log_filtered_vectors"][step]
        if log_filtered is None:
            raise TrellisError("NUMERIC_FAILURE", "Completed forward pass contains an undefined posterior")
        log_smoothed = [log_filtered[state] + log_beta[step][state] for state in range(state_count)]
        output.append(
            {
                "sequence_index": step,
                "posterior": _posterior_from_logs(log_smoothed),
                "uses_later_observations": step < length - 1,
            }
        )
    return output


def viterbi(model: dict[str, Any], symbols: list[int]) -> dict[str, Any] | None:
    log_initial = model["log_initial"]
    log_transition = model["log_transition"]
    log_emission = model["log_emission"]
    state_count = len(model["state_order"])
    scores = [log_initial[state] + log_emission[state][symbols[0]] for state in range(state_count)]
    backpointers: list[list[int]] = []
    for symbol in symbols[1:]:
        next_scores: list[float] = []
        pointers: list[int] = []
        for target in range(state_count):
            candidates = [scores[source] + log_transition[source][target] for source in range(state_count)]
            best = max(range(state_count), key=lambda index: (candidates[index], -index))
            next_scores.append(candidates[best] + log_emission[target][symbol])
            pointers.append(best)
        scores = next_scores
        backpointers.append(pointers)
    last = max(range(state_count), key=lambda index: (scores[index], -index))
    best_log = scores[last]
    if best_log == -math.inf:
        return None
    path = [last]
    for pointers in reversed(backpointers):
        path.append(pointers[path[-1]])
    path.reverse()
    joint, underflow = _finite_exp(best_log)
    return {
        "state_indices": path,
        "log_joint_probability": best_log,
        "joint_probability": joint,
        "joint_probability_underflow": underflow,
        "tie_breaking": "lowest_predecessor_and_terminal_index_in_declared_state_order",
    }
def _calibration_reasons(model: dict[str, Any], model_set: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    calibration = model["calibration_ref"]
    policy = model_set["comparison"].get("absolute_fit_policy")
    observation = model_set["document"]["observation_contract"]
    if calibration is None:
        reasons.append("model_calibration_ref_missing")
    else:
        if calibration["encoder_digest"] != observation["encoder_digest"]:
            reasons.append("calibration_encoder_mismatch")
        if calibration["step_semantics"] != observation["step_semantics"]:
            reasons.append("calibration_step_semantics_mismatch")
    if not isinstance(policy, dict):
        reasons.append("absolute_fit_policy_missing")
    elif calibration is not None and canonical_bytes(calibration) != canonical_bytes(policy["calibration_ref"]):
        reasons.append("calibration_reference_mismatch")
    return reasons


def _absolute_fit(model: dict[str, Any], result: dict[str, Any], model_set: dict[str, Any]) -> dict[str, Any]:
    policy = model_set["comparison"].get("absolute_fit_policy")
    reasons = _calibration_reasons(model, model_set)
    if reasons or not isinstance(policy, dict):
        return {
            "status": "unassessed",
            "reason": reasons,
            "metric": SURPRISAL_METRIC,
            "log_base": LOG_BASE,
            "unit": SURPRISAL_UNIT,
            "threshold": None if not isinstance(policy, dict) else float(policy["threshold"]),
            "calibration_ref": None if not isinstance(policy, dict) else policy["calibration_ref"],
        }
    return {
        "status": "pass" if result["mean_surprisal"] <= float(policy["threshold"]) else "fail",
        "reason": [],
        "metric": SURPRISAL_METRIC,
        "log_base": LOG_BASE,
        "unit": SURPRISAL_UNIT,
        "threshold": float(policy["threshold"]),
        "calibration_ref": policy["calibration_ref"],
    }


def _comparison(
    models: list[dict[str, Any]],
    results: list[dict[str, Any]],
    contract: dict[str, Any],
    fits: list[dict[str, Any]],
) -> dict[str, Any]:
    reasons: list[str] = []
    if len(models) < 2:
        reasons.append("single_model_closed_world")
    if contract["status"] != "eligible":
        reasons.append("comparison_contract_ineligible")
    if contract["shared_observation_semantics_required"] is not True or contract["shared_sequence_required"] is not True:
        reasons.append("shared_semantics_or_sequence_not_required")
    if not contract["prior_basis"]:
        reasons.append("prior_basis_missing")
    if not contract["calibration_basis"] or not isinstance(contract["absolute_fit_policy"], dict):
        reasons.append("calibration_contract_incomplete")
    if any(not model["comparison_eligible"] for model in models):
        reasons.append("model_declared_ineligible")
    priors = [model["prior"] for model in models]
    if any(prior is None for prior in priors):
        reasons.append("model_prior_missing")
    elif abs(math.fsum(float(prior) for prior in priors) - 1.0) > TOLERANCE:
        reasons.append("model_priors_non_stochastic")
    for fit in fits:
        if fit["status"] == "unassessed":
            reasons.extend(fit["reason"])
    if fits and all(fit["status"] == "fail" for fit in fits):
        reasons.append("absolute_fit_gate_failed")
    if all(result["log_likelihood"] == -math.inf for result in results):
        reasons.append("all_models_zero_likelihood")
    reasons = list(dict.fromkeys(reasons))
    if reasons:
        return {
            "weights_status": "unsupported",
            "reason": reasons,
            "conditional_on_model_set": True,
            "relative_model_weights": [],
        }
    log_weights = [
        _safe_log(float(models[index]["prior"])) + results[index]["log_likelihood"]
        for index in range(len(models))
    ]
    maximum = max(log_weights)
    if maximum == -math.inf:
        return {
            "weights_status": "unsupported",
            "reason": ["all_models_zero_likelihood"],
            "conditional_on_model_set": True,
            "relative_model_weights": [],
        }
    scaled = [math.exp(value - maximum) for value in log_weights]
    total = math.fsum(scaled)
    return {
        "weights_status": "computed",
        "reason": [],
        "conditional_on_model_set": True,
        "relative_model_weights": [
            {"model_id": models[index]["model_id"], "weight": scaled[index] / total}
            for index in range(len(models))
        ],
    }


def _numeric_runtime() -> dict[str, Any]:
    return {
        "implementation": sys.implementation.name,
        "python_version": ".".join(str(item) for item in sys.version_info[:3]),
        "float_radix": sys.float_info.radix,
        "float_mant_dig": sys.float_info.mant_dig,
        "float_max_exp": sys.float_info.max_exp,
    }


def engine_descriptor() -> dict[str, Any]:
    try:
        artifact_sha256 = hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()
    except OSError as exc:
        raise TrellisError("ENGINE_UNREADABLE", f"Cannot fingerprint the inference engine: {exc}") from exc
    return {
        "engine_id": ENGINE_ID,
        "engine_version": ENGINE_VERSION,
        "artifact_sha256": artifact_sha256,
        "numeric_kernel": "logsumexp-forward_logsumexp-backward_log-viterbi",
        "numeric_runtime": _numeric_runtime(),
        "schema_versions": {
            "model_set": MODEL_SET_CONTRACT,
            "observation_sequence": SEQUENCE_CONTRACT,
            "receipt_envelope": RECEIPT_ENVELOPE,
        },
    }
def analyze(
    model_set: dict[str, Any],
    sequence: dict[str, Any],
    *,
    decode: bool,
    smoothing: bool,
) -> dict[str, Any]:
    resource_estimate = estimate_resources(model_set, sequence, decode=decode, smoothing=smoothing)
    symbols = sequence["symbol_indices"]
    results = [forward(model, symbols) for model in model_set["models"]]
    fits = [_absolute_fit(model_set["models"][index], result, model_set) for index, result in enumerate(results)]
    comparison = _comparison(model_set["models"], results, model_set["comparison"], fits)
    if all(result["log_likelihood"] == -math.inf for result in results):
        reframe_status, reframe_reasons = "required", ["all_models_zero_likelihood"]
    elif fits and all(fit["status"] == "fail" for fit in fits):
        reframe_status, reframe_reasons = "required", ["all_models_failed_calibrated_absolute_fit"]
    elif any(fit["status"] == "unassessed" for fit in fits):
        reframe_status, reframe_reasons = "unassessed", ["absolute_fit_not_fully_calibrated"]
    else:
        reframe_status, reframe_reasons = "not_required", []
    per_model: list[dict[str, Any]] = []
    for index, model in enumerate(model_set["models"]):
        result = results[index]
        likelihood, underflow = _finite_exp(result["log_likelihood"])
        item: dict[str, Any] = {
            "model_id": model["model_id"],
            "model_version": model["raw"]["model_version"],
            "model_artifact_digest": model["model_artifact_digest"],
            "effective_model_digest": model["effective_model_digest"],
            "observation_contract_digest": model_set["observation_contract_digest"],
            "state_order": model["state_order"],
            "inference_status": result["status"],
            "log_sequence_likelihood": None if result["log_likelihood"] == -math.inf else result["log_likelihood"],
            "sequence_likelihood": likelihood,
            "sequence_likelihood_underflow": underflow,
            "mean_predictive_surprisal": None if result["mean_surprisal"] == math.inf else result["mean_surprisal"],
            "surprisal_log_base": LOG_BASE,
            "surprisal_unit": SURPRISAL_UNIT,
            "absolute_fit": fits[index],
            "filtered_state_posteriors": filtered_rows(result),
        }
        if result["zero_at"] is not None:
            item["zero_likelihood_at_sequence_index"] = result["zero_at"]
        if smoothing:
            item["smoothed_state_posteriors"] = smooth(model, symbols, result)
        if decode:
            item["viterbi"] = viterbi(model, symbols)
        per_model.append(item)
    options = {"filter": True, "decode": decode, "smooth": smoothing}
    diagnostics: list[str] = []
    if sequence["declared_dependencies"]:
        diagnostics.append("observation_dependence_declared; HMM likelihood does not correct it automatically")
    if not sequence["filtered_is_as_known_then"]:
        diagnostics.append("filter is retrospective event-order inference, not a historical as-known-then estimate")
    if sequence["correction_count"]:
        diagnostics.append("corrections are bound to the prior sequence digest; prior document contents were not independently loaded")
    receipt: dict[str, Any] = {
        "contract": RUN_CONTRACT,
        "engine": engine_descriptor(),
        "inputs": {
            "model_set_id": model_set["document"]["model_set_id"],
            "model_set_revision": model_set["document"]["revision"],
            "model_set_digest": model_set["digest"],
            "sequence_id": sequence["document"]["sequence_id"],
            "sequence_revision": sequence["document"]["revision"],
            "sequence_digest": sequence["digest"],
            "prior_sequence": sequence["prior_sequence"],
            "observation_ids": sequence["observation_ids"],
            "temporal_mode": sequence["temporal_mode"],
        },
        "options": options,
        "resource_estimate": resource_estimate,
        "run_status": "reframe_required" if reframe_status == "required" else "completed",
        "per_model": per_model,
        "comparison": comparison,
        "reframe": {"status": reframe_status, "reasons": reframe_reasons},
        "diagnostics": diagnostics,
        "semantic_boundary": {
            "epistemic_model_agnosticism": True,
            "model_relative": True,
            "claim_confidence": False,
            "truth_certification": False,
            "source_confidence_modified": False,
            "authority_effect": "none",
            "decision_authority": False,
            "persistence_performed": False,
            "filtered_temporal_mode": sequence["temporal_mode"],
            "filtered_is_as_known_then": sequence["filtered_is_as_known_then"],
            "smoothed_is_retrospective": smoothing,
        },
    }
    receipt["run_id"] = "sha256:" + digest(receipt)
    return receipt


def validation_receipt(model_set: dict[str, Any], sequence: dict[str, Any]) -> dict[str, Any]:
    resource_estimate = estimate_resources(model_set, sequence, decode=False, smoothing=False)
    receipt: dict[str, Any] = {
        "contract": VALIDATION_CONTRACT,
        "status": "valid",
        "engine": engine_descriptor(),
        "inputs": {
            "model_set_digest": model_set["digest"],
            "sequence_digest": sequence["digest"],
            "model_count": len(model_set["models"]),
            "observation_count": len(sequence["symbol_indices"]),
        },
        "resource_estimate": resource_estimate,
        "comparison_declared": model_set["comparison"]["status"],
        "temporal_semantics": {
            "mode": sequence["temporal_mode"],
            "filtered_is_as_known_then": sequence["filtered_is_as_known_then"],
        },
        "semantic_boundary": {
            "structural_and_stochastic_only": True,
            "ontology_validated": False,
            "calibration_truth_validated": False,
            "semantic_truth_certified": False,
            "authority_effect": "none",
        },
    }
    receipt["validation_id"] = "sha256:" + digest(receipt)
    return receipt


def error_receipt(error: TrellisError) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "contract": ERROR_CONTRACT,
        "status": "error",
        "engine": engine_descriptor(),
        "code": error.code,
        "message": error.message,
    }
    receipt["error_id"] = "sha256:" + digest(receipt)
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate or analyze explicit epistemic model sets with deterministic HMM inference."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "analyze"):
        command = subparsers.add_parser(name)
        command.add_argument("model_set", type=Path)
        command.add_argument("sequence", type=Path)
        if name == "analyze":
            command.add_argument("--decode", action="store_true")
            command.add_argument("--smooth", action="store_true")
    return parser


def _serialize_output(output: dict[str, Any]) -> str:
    return json.dumps(output, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    exit_code = 0
    try:
        model_set = validate_model_set(load_json(args.model_set))
        sequence = validate_sequence(load_json(args.sequence), model_set)
        output = (
            validation_receipt(model_set, sequence)
            if args.command == "validate"
            else analyze(model_set, sequence, decode=args.decode, smoothing=args.smooth)
        )
    except TrellisError as exc:
        output = error_receipt(exc)
        exit_code = 2
    except Exception as exc:  # Last-resort CLI containment; library callers still receive programming faults.
        output = error_receipt(
            TrellisError("INTERNAL_ERROR", f"Unexpected inference failure: {type(exc).__name__}: {exc}")
        )
        exit_code = 3
    try:
        serialized = _serialize_output(output)
    except (TypeError, ValueError, UnicodeError, OverflowError) as exc:
        output = error_receipt(
            TrellisError("OUTPUT_ENCODING_ERROR", f"Cannot encode finite UTF-8 JSON output: {type(exc).__name__}: {exc}")
        )
        serialized = _serialize_output(output)
        exit_code = 3
    if len(serialized.encode("utf-8")) > MAX_OUTPUT_BYTES:
        output = error_receipt(TrellisError("RESOURCE_LIMIT", f"Rendered output exceeds {MAX_OUTPUT_BYTES} bytes"))
        serialized = _serialize_output(output)
        exit_code = 2
    print(serialized)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())