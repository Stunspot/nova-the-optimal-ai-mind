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
ENGINE_VERSION = "1.1.0"
MODEL_SET_CONTRACT = "cd-model-agnosticism-model-set/v2"
SEQUENCE_CONTRACT = "cd-model-agnosticism-observation-sequence/v2"
RUN_CONTRACT = "cd-model-agnosticism-inference-run/v2"
ERROR_CONTRACT = "cd-model-agnosticism-error/v2"
VALIDATION_CONTRACT = "cd-model-agnosticism-validation/v2"
RECEIPT_ENVELOPE = "cd-model-agnosticism-receipt-envelope/v2"
ORDERING_RULE = "event_time_strictly_ascending/v2"
SURPRISAL_METRIC = "mean_predictive_surprisal"
LOG_BASE = "e"
SURPRISAL_UNIT = "nats_per_observation"
TRANSITION_LAYOUT = "source_state_rows_target_state_columns/v1"
EMISSION_LAYOUT = "state_rows_symbol_columns/v1"
NORMALIZATION_POLICY = "l1_within_absolute_tolerance_canonical_positive_zero/v1"
EPISTEMIC_LANES = {"evidence_update", "assumption_stress_test"}
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
MAX_ERROR_MESSAGE_CHARS = 4_096
TOLERANCE = 1e-9
LOG_PROBABILITY_CEILING_TOLERANCE = 16 * MAX_STATES * math.ulp(1.0)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$")
MIN_POSITIVE_FLOAT = float.fromhex("0x0.0000000000001p-1022")
LOG_MIN_POSITIVE_FLOAT = math.log(MIN_POSITIVE_FLOAT)


def _sanitize_error_code(value: Any) -> str:
    try:
        text = str(value).upper()
    except Exception:
        return "INTERNAL_ERROR"
    text = re.sub(r"[^A-Z0-9_]", "_", text)[:128]
    if not text or not text[0].isalpha():
        return "INTERNAL_ERROR"
    return text


def _sanitize_error_message(value: Any) -> str:
    try:
        text = str(value)
    except Exception:
        text = "Error detail could not be rendered"
    safe = "".join(
        character
        if ord(character) >= 0x20
        and ord(character) != 0x7F
        and not 0xD800 <= ord(character) <= 0xDFFF
        else "?"
        for character in text
    ).strip()
    if not safe:
        safe = "Unspecified Trellis error"
    if len(safe) > MAX_ERROR_MESSAGE_CHARS:
        safe = safe[: MAX_ERROR_MESSAGE_CHARS - 3] + "..."
    return safe


class TrellisError(ValueError):
    def __init__(self, code: str, message: Any):
        self.code = _sanitize_error_code(code)
        self.message = _sanitize_error_message(message)
        super().__init__(self.message)


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
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise TrellisError("INVALID_FIELD", f"{path} contains a disallowed control character")
    return value


def _need_id(value: Any, path: str) -> str:
    return _need_string(value, path, max_chars=MAX_ID_CHARS)


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


def _new_normalization_stats() -> dict[str, Any]:
    return {
        "policy": NORMALIZATION_POLICY,
        "absolute_tolerance": TOLERANCE,
        "vectors_checked": 0,
        "vectors_adjusted": 0,
        "negative_zero_values_canonicalized": 0,
        "max_absolute_sum_error": 0.0,
        "max_absolute_value_adjustment": 0.0,
    }


def _distribution(
    values: Any,
    length: int,
    path: str,
    *,
    stats: dict[str, Any] | None = None,
) -> list[float]:
    if not isinstance(values, list) or len(values) != length:
        raise TrellisError("INVALID_DIMENSION", f"{path} must contain exactly {length} probabilities")
    result = [_probability(item, f"{path}[{index}]") for index, item in enumerate(values)]
    typed = [float(item) for item in result]
    total = math.fsum(typed)
    error = abs(total - 1.0)
    if error > TOLERANCE:
        raise TrellisError("NON_STOCHASTIC", f"{path} must sum to 1 within {TOLERANCE}")
    negative_zeros = sum(
        1 for item in typed if item == 0.0 and math.copysign(1.0, item) < 0.0
    )
    normalized = [0.0 if item == 0.0 else item / total for item in typed]
    value_adjustment = max(
        (abs(normalized[index] - typed[index]) for index in range(len(typed))),
        default=0.0,
    )
    if stats is not None:
        stats["vectors_checked"] += 1
        stats["max_absolute_sum_error"] = max(stats["max_absolute_sum_error"], error)
        stats["max_absolute_value_adjustment"] = max(
            stats["max_absolute_value_adjustment"], value_adjustment
        )
        stats["negative_zero_values_canonicalized"] += negative_zeros
        if total != 1.0 or negative_zeros:
            stats["vectors_adjusted"] += 1
    return normalized


def _matrix(
    value: Any,
    rows: int,
    columns: int,
    path: str,
    *,
    stats: dict[str, Any] | None = None,
) -> list[list[float]]:
    if not isinstance(value, list) or len(value) != rows:
        raise TrellisError("INVALID_DIMENSION", f"{path} must contain exactly {rows} rows")
    return [
        _distribution(row, columns, f"{path}[{index}]", stats=stats)
        for index, row in enumerate(value)
    ]


def _parse_time(value: Any, path: str) -> datetime:
    text = _need_string(value, path, max_chars=64)
    if not RFC3339.fullmatch(text):
        raise TrellisError(
            "INVALID_TIME",
            f"{path} must be an RFC-3339 timestamp with at most six fractional-second digits",
        )
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            raise ValueError("timezone missing")
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise TrellisError(
            "INVALID_TIME",
            f"{path} is outside the supported RFC-3339 microsecond timestamp envelope",
        ) from exc


def _validate_step_contract(value: Any, path: str) -> dict[str, Any]:
    step = _exact_object(value, path, {"kind", "interval_seconds", "description"})
    if step["kind"] not in {"event_step", "fixed_interval"}:
        raise TrellisError("UNSUPPORTED_POLICY", f"{path}.kind must be event_step or fixed_interval")
    _need_string(step["description"], f"{path}.description")
    interval = step["interval_seconds"]
    if step["kind"] == "event_step":
        if interval is not None:
            raise TrellisError("INVALID_FIELD", f"{path}.interval_seconds must be null for event_step")
    else:
        _positive_int(interval, f"{path}.interval_seconds")
    return step


def _validate_input_provenance(value: Any, path: str) -> dict[str, Any]:
    provenance = _exact_object(
        value,
        path,
        {"kind", "fixed_before_sequence", "basis", "source_refs"},
    )
    if provenance["kind"] not in {
        "estimated_independent_data", "expert_elicited", "stipulated_scenario"
    }:
        raise TrellisError("INVALID_FIELD", f"{path}.kind is unsupported")
    _need_bool(provenance["fixed_before_sequence"], f"{path}.fixed_before_sequence")
    _need_string(provenance["basis"], f"{path}.basis")
    _string_list(
        provenance["source_refs"],
        f"{path}.source_refs",
        nonempty=True,
        unique=True,
    )
    return provenance


def _validate_calibration(value: Any, path: str) -> dict[str, Any]:
    calibration = _exact_object(
        value,
        path,
        {
            "calibration_id", "revision", "digest", "calibration_target_digest",
            "minimum_observations", "maximum_observations", "provenance",
        },
    )
    _need_id(calibration["calibration_id"], f"{path}.calibration_id")
    _positive_int(calibration["revision"], f"{path}.revision")
    calibration["digest"] = _need_digest(calibration["digest"], f"{path}.digest")
    calibration["calibration_target_digest"] = _need_digest(
        calibration["calibration_target_digest"],
        f"{path}.calibration_target_digest",
    )
    minimum = _positive_int(
        calibration["minimum_observations"], f"{path}.minimum_observations"
    )
    maximum = _positive_int(
        calibration["maximum_observations"], f"{path}.maximum_observations"
    )
    if maximum > MAX_OBSERVATIONS:
        raise TrellisError(
            "RESOURCE_LIMIT",
            f"{path}.maximum_observations exceeds {MAX_OBSERVATIONS}",
        )
    if minimum > maximum:
        raise TrellisError(
            "INVALID_FIELD",
            f"{path}.minimum_observations must not exceed maximum_observations",
        )
    _validate_input_provenance(calibration["provenance"], f"{path}.provenance")
    return calibration


def _calibration_target_digest(
    models: list[dict[str, Any]],
    observation_contract_digest: str,
    stopping_contract_digest: str,
    minimum_observations: int,
    maximum_observations: int,
) -> str:
    return digest(
        {
            "target_contract": "cd-model-agnosticism-calibration-target/v1",
            "candidate_hmms": sorted(
                [
                {
                    "model_id": model["model_id"],
                    "model_version": model["raw"]["model_version"],
                    "comparison_unit_id": model["comparison_unit_id"],
                    "family": model["raw"]["family"],
                    "predictive_kernel_digest": model["predictive_kernel_digest"],
                }
                for model in models
                ],
                key=lambda item: (item["comparison_unit_id"], item["model_id"]),
            ),
            "observation_contract_digest": observation_contract_digest,
            "stopping_contract_digest": stopping_contract_digest,
            "calibration_observation_bounds": {
                "minimum_observations": minimum_observations,
                "maximum_observations": maximum_observations,
            },
        }
    )

def validate_model_set(document: dict[str, Any]) -> dict[str, Any]:
    document = _exact_object(
        document,
        "model_set",
        {
            "contract", "model_set_id", "revision", "case_ref", "question", "scope",
            "epistemic_lane", "observation_contract", "candidate_selection",
            "stopping_contract", "models", "comparison_contract", "reframe_policy", "provenance",
        },
    )
    if document["contract"] != MODEL_SET_CONTRACT:
        raise TrellisError("UNSUPPORTED_CONTRACT", f"model-set contract must be {MODEL_SET_CONTRACT}")
    _need_id(document["model_set_id"], "model_set_id")
    _positive_int(document["revision"], "revision")
    _need_string(document["case_ref"], "case_ref", max_chars=MAX_REF_CHARS)
    _need_string(document["question"], "question")
    _need_string(document["scope"], "scope")
    lane = document["epistemic_lane"]
    if lane not in EPISTEMIC_LANES:
        raise TrellisError(
            "INVALID_FIELD",
            "epistemic_lane must be evidence_update or assumption_stress_test",
        )

    observation = _exact_object(
        document["observation_contract"],
        "observation_contract",
        {
            "encoder_id", "encoder_version", "encoder_digest", "step_semantics",
            "step_contract", "ordering_rule", "missing_policy", "oov_policy", "symbols",
            "mapping_provenance",
        },
    )
    _need_id(observation["encoder_id"], "observation_contract.encoder_id")
    _need_id(observation["encoder_version"], "observation_contract.encoder_version")
    observation["encoder_digest"] = _need_digest(
        observation["encoder_digest"], "observation_contract.encoder_digest"
    )
    _need_string(observation["step_semantics"], "observation_contract.step_semantics")
    _validate_step_contract(observation["step_contract"], "observation_contract.step_contract")
    mapping_provenance = _validate_input_provenance(
        observation["mapping_provenance"], "observation_contract.mapping_provenance"
    )
    if observation["ordering_rule"] != ORDERING_RULE:
        raise TrellisError(
            "UNSUPPORTED_POLICY",
            f"observation_contract.ordering_rule must be {ORDERING_RULE}",
        )
    _need_string(observation["missing_policy"], "observation_contract.missing_policy")
    if observation["oov_policy"] != "error":
        raise TrellisError("UNSUPPORTED_POLICY", "observation_contract.oov_policy must be error")
    symbols_raw = observation["symbols"]
    if not isinstance(symbols_raw, list) or not 1 <= len(symbols_raw) <= MAX_SYMBOLS:
        raise TrellisError(
            "RESOURCE_LIMIT",
            f"observation_contract.symbols must contain 1..{MAX_SYMBOLS} entries",
        )
    symbol_ids: list[str] = []
    for index, raw_item in enumerate(symbols_raw):
        item = _exact_object(
            raw_item,
            f"observation_contract.symbols[{index}]",
            {"symbol_id", "definition", "coding_rule"},
        )
        symbol_ids.append(
            _need_id(item["symbol_id"], f"observation_contract.symbols[{index}].symbol_id")
        )
        _need_string(item["definition"], f"observation_contract.symbols[{index}].definition")
        _need_string(item["coding_rule"], f"observation_contract.symbols[{index}].coding_rule")
    _check_unique(symbol_ids, "observation_contract.symbols")
    observation_contract_digest = digest(observation)

    candidate_selection = _exact_object(
        document["candidate_selection"],
        "candidate_selection",
        {"status", "basis", "source_refs"},
    )
    if candidate_selection["status"] not in {
        "fixed_before_sequence", "data_dependent", "scenario_only"
    }:
        raise TrellisError(
            "INVALID_FIELD",
            "candidate_selection.status must be fixed_before_sequence, data_dependent, or scenario_only",
        )
    _need_string(candidate_selection["basis"], "candidate_selection.basis")
    _string_list(
        candidate_selection["source_refs"],
        "candidate_selection.source_refs",
        nonempty=True,
        unique=True,
    )

    stopping_contract = _exact_object(
        document["stopping_contract"],
        "stopping_contract",
        {"status", "basis", "maximum_observations"},
    )
    if stopping_contract["status"] not in {
        "fixed_before_sequence", "data_dependent", "scenario_only"
    }:
        raise TrellisError(
            "INVALID_FIELD",
            "stopping_contract.status must be fixed_before_sequence, data_dependent, or scenario_only",
        )
    _need_string(stopping_contract["basis"], "stopping_contract.basis")
    if stopping_contract["maximum_observations"] is not None:
        maximum_observations = _positive_int(
            stopping_contract["maximum_observations"],
            "stopping_contract.maximum_observations",
        )
        if maximum_observations > MAX_OBSERVATIONS:
            raise TrellisError(
                "RESOURCE_LIMIT",
                f"stopping_contract.maximum_observations exceeds {MAX_OBSERVATIONS}",
            )
    stopping_contract_digest = digest(stopping_contract)

    models = document["models"]
    if not isinstance(models, list) or not 1 <= len(models) <= MAX_MODELS:
        raise TrellisError("RESOURCE_LIMIT", f"models must contain 1..{MAX_MODELS} entries")
    model_ids: list[str] = []
    comparison_unit_ids: list[str] = []
    normalized_models: list[dict[str, Any]] = []
    for model_index, raw_model in enumerate(models):
        prefix = f"models[{model_index}]"
        model = _exact_object(
            raw_model,
            prefix,
            {
                "model_id", "comparison_unit_id", "label", "model_version", "family",
                "prior_model_weight", "prior_provenance", "state_order", "states",
                "initial", "transition", "emission", "matrix_layout", "assumptions",
                "parameter_basis", "parameter_provenance", "evidence_refs",
                "comparison_eligible",
            },
        )
        model_id = _need_id(model["model_id"], f"{prefix}.model_id")
        model_ids.append(model_id)
        comparison_unit_id = _need_id(
            model["comparison_unit_id"], f"{prefix}.comparison_unit_id"
        )
        comparison_unit_ids.append(comparison_unit_id)
        _need_string(model["label"], f"{prefix}.label")
        _need_id(model["model_version"], f"{prefix}.model_version")
        if model["family"] != "discrete_first_order_hmm":
            raise TrellisError(
                "UNSUPPORTED_MODEL",
                f"{prefix}.family must be discrete_first_order_hmm",
            )
        state_order = _string_list(
            model["state_order"],
            f"{prefix}.state_order",
            nonempty=True,
            max_items=MAX_STATES,
            max_chars=MAX_ID_CHARS,
            unique=True,
        )
        states = model["states"]
        if not isinstance(states, list) or len(states) != len(state_order):
            raise TrellisError("INVALID_DIMENSION", f"{prefix}.states must match state_order")
        declared_order: list[str] = []
        for state_index, raw_state in enumerate(states):
            state = _exact_object(
                raw_state,
                f"{prefix}.states[{state_index}]",
                {"state_id", "meaning"},
            )
            declared_order.append(
                _need_id(state["state_id"], f"{prefix}.states[{state_index}].state_id")
            )
            _need_string(state["meaning"], f"{prefix}.states[{state_index}].meaning")
        if declared_order != state_order:
            raise TrellisError("ORDER_MISMATCH", f"{prefix}.states must follow state_order exactly")

        matrix_layout = _exact_object(
            model["matrix_layout"],
            f"{prefix}.matrix_layout",
            {"transition", "emission"},
        )
        if matrix_layout["transition"] != TRANSITION_LAYOUT:
            raise TrellisError(
                "MATRIX_LAYOUT_MISMATCH",
                f"{prefix}.matrix_layout.transition must be {TRANSITION_LAYOUT}",
            )
        if matrix_layout["emission"] != EMISSION_LAYOUT:
            raise TrellisError(
                "MATRIX_LAYOUT_MISMATCH",
                f"{prefix}.matrix_layout.emission must be {EMISSION_LAYOUT}",
            )

        normalization = _new_normalization_stats()
        initial = _distribution(
            model["initial"], len(state_order), f"{prefix}.initial", stats=normalization
        )
        transition = _matrix(
            model["transition"],
            len(state_order),
            len(state_order),
            f"{prefix}.transition",
            stats=normalization,
        )
        emission = _matrix(
            model["emission"],
            len(state_order),
            len(symbol_ids),
            f"{prefix}.emission",
            stats=normalization,
        )
        assumptions = _exact_object(
            model["assumptions"],
            f"{prefix}.assumptions",
            {"markov_order", "output_independence", "one_observation_per_step", "stationarity_window"},
        )
        if type(assumptions["markov_order"]) is not int or assumptions["markov_order"] != 1:
            raise TrellisError(
                "UNSUPPORTED_MODEL",
                f"{prefix}.assumptions.markov_order must be integer 1",
            )
        for field in ("output_independence", "one_observation_per_step", "stationarity_window"):
            _need_string(assumptions[field], f"{prefix}.assumptions.{field}")
        _need_string(model["parameter_basis"], f"{prefix}.parameter_basis")
        parameter_provenance = _validate_input_provenance(
            model["parameter_provenance"], f"{prefix}.parameter_provenance"
        )
        _string_list(
            model["evidence_refs"],
            f"{prefix}.evidence_refs",
            nonempty=True,
            unique=True,
        )
        prior_provenance = _validate_input_provenance(
            model["prior_provenance"], f"{prefix}.prior_provenance"
        )
        comparison_eligible = _need_bool(
            model["comparison_eligible"], f"{prefix}.comparison_eligible"
        )
        prior = _probability(
            model["prior_model_weight"],
            f"{prefix}.prior_model_weight",
            allow_none=True,
        )
        if prior is not None and prior <= 0.0:
            raise TrellisError(
                "INVALID_PROBABILITY",
                f"{prefix}.prior_model_weight must be strictly positive when declared; "
                "exact zero is reserved for structural probabilities within the bounded supplied HMM",
            )

        model_document_digest = digest(model)
        predictive_kernel_digest = digest(
            {
                "family": model["family"],
                "observation_contract_digest": observation_contract_digest,
                "matrix_layout": matrix_layout,
                "initial": initial,
                "transition": transition,
                "emission": emission,
                "normalization_policy": NORMALIZATION_POLICY,
            }
        )
        inference_model_digest = digest(
            {
                "family": model["family"],
                "observation_contract_digest": observation_contract_digest,
                "state_order": state_order,
                "symbol_order": symbol_ids,
                "matrix_layout": matrix_layout,
                "normalization_policy": NORMALIZATION_POLICY,
                "normalized_initial": initial,
                "normalized_transition": transition,
                "normalized_emission": emission,
            }
        )
        normalized_models.append(
            {
                "raw": model,
                "model_id": model_id,
                "comparison_unit_id": comparison_unit_id,
                "state_order": state_order,
                "initial": initial,
                "transition": transition,
                "emission": emission,
                "log_initial": [_safe_log(item) for item in initial],
                "log_transition": [[_safe_log(item) for item in row] for row in transition],
                "log_emission": [[_safe_log(item) for item in row] for row in emission],
                "prior": prior,
                "comparison_eligible": comparison_eligible,
                "parameter_provenance": parameter_provenance,
                "prior_provenance": prior_provenance,
                "matrix_layout": matrix_layout,
                "normalization": normalization,
                "model_document_digest": model_document_digest,
                "predictive_kernel_digest": predictive_kernel_digest,
                "inference_model_digest": inference_model_digest,
            }
        )
    _check_unique(model_ids, "models")
    if len(comparison_unit_ids) != len(set(comparison_unit_ids)):
        raise TrellisError(
            "DUPLICATE_COMPARISON_UNIT",
            "models repeat a comparison_unit_id; one declared comparison unit may enter the candidate set only once",
        )
    kernel_ids = [model["predictive_kernel_digest"] for model in normalized_models]
    if len(kernel_ids) != len(set(kernel_ids)):
        raise TrellisError(
            "DUPLICATE_PREDICTIVE_KERNEL",
            "models contain an identical ordered predictive kernel; duplicate candidates cannot be compared",
        )

    comparison = _exact_object(
        document["comparison_contract"],
        "comparison_contract",
        {
            "status", "shared_observation_semantics_required", "shared_sequence_required",
            "prior_basis", "calibration_basis", "absolute_fit_policy",
        },
    )
    if comparison["status"] not in {"eligible", "ineligible"}:
        raise TrellisError(
            "INVALID_FIELD",
            "comparison_contract.status must be eligible or ineligible",
        )
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
            {
                "assessment_basis", "metric", "log_base", "unit", "threshold",
                "direction", "calibration_ref",
            },
        )
        if fit_policy["assessment_basis"] != "declared_threshold_arithmetic":
            raise TrellisError(
                "UNSUPPORTED_POLICY",
                "absolute_fit_policy.assessment_basis must be declared_threshold_arithmetic",
            )
        if fit_policy["metric"] != SURPRISAL_METRIC:
            raise TrellisError(
                "UNSUPPORTED_POLICY",
                f"absolute_fit_policy.metric must be {SURPRISAL_METRIC}",
            )
        if fit_policy["log_base"] != LOG_BASE:
            raise TrellisError(
                "UNSUPPORTED_POLICY",
                f"absolute_fit_policy.log_base must be {LOG_BASE}",
            )
        if fit_policy["unit"] != SURPRISAL_UNIT:
            raise TrellisError(
                "UNSUPPORTED_POLICY",
                f"absolute_fit_policy.unit must be {SURPRISAL_UNIT}",
            )
        if fit_policy["direction"] != "lte":
            raise TrellisError(
                "UNSUPPORTED_POLICY",
                "absolute_fit_policy.direction must be lte",
            )
        threshold = _number(
            fit_policy["threshold"],
            "comparison_contract.absolute_fit_policy.threshold",
        )
        if threshold is None or threshold < 0.0:
            raise TrellisError(
                "INVALID_FIELD",
                "absolute_fit_policy.threshold must be non-negative",
            )
        fit_policy["calibration_ref"] = _validate_calibration(
            fit_policy["calibration_ref"],
            "comparison_contract.absolute_fit_policy.calibration_ref",
        )
        calibration = fit_policy["calibration_ref"]
        calibration_target_digest = _calibration_target_digest(
            normalized_models,
            observation_contract_digest,
            stopping_contract_digest,
            calibration["minimum_observations"],
            calibration["maximum_observations"],
        )
    else:
        calibration_target_digest = None

    reframe_policy = _exact_object(
        document["reframe_policy"],
        "reframe_policy",
        {"all_zero_likelihood", "all_absolute_fit_fail"},
    )
    if (
        reframe_policy["all_zero_likelihood"] != "required"
        or reframe_policy["all_absolute_fit_fail"] != "required"
    ):
        raise TrellisError(
            "INVALID_FIELD",
            "reframe_policy must require all-zero and all-fit-fail reframing",
        )
    provenance = _exact_object(
        document["provenance"],
        "provenance",
        {"created_by", "source_refs"},
    )
    _need_string(provenance["created_by"], "provenance.created_by")
    _string_list(
        provenance["source_refs"],
        "provenance.source_refs",
        nonempty=True,
        unique=True,
    )
    return {
        "document": document,
        "digest": digest(document),
        "epistemic_lane": lane,
        "observation_contract_digest": observation_contract_digest,
        "stopping_contract_digest": stopping_contract_digest,
        "calibration_target_digest": calibration_target_digest,
        "mapping_provenance": mapping_provenance,
        "symbol_ids": symbol_ids,
        "models": normalized_models,
        "comparison": comparison,
        "candidate_selection": candidate_selection,
        "stopping_contract": stopping_contract,
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
            "step_semantics", "step_contract", "items",
        },
    )
    if document["contract"] != SEQUENCE_CONTRACT:
        raise TrellisError(
            "UNSUPPORTED_CONTRACT",
            f"observation-sequence contract must be {SEQUENCE_CONTRACT}",
        )
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
        raise TrellisError(
            "BINDING_MISMATCH",
            "observation sequence model_set_digest differs from canonical model-set digest",
        )
    encoder = _exact_object(
        document["encoder"],
        "encoder",
        {"encoder_id", "encoder_version", "encoder_digest"},
    )
    source_encoder = model_set["document"]["observation_contract"]
    for field in ("encoder_id", "encoder_version"):
        _need_id(encoder[field], f"encoder.{field}")
        if encoder[field] != source_encoder[field]:
            raise TrellisError(
                "ENCODER_MISMATCH",
                f"encoder.{field} differs from the model-set observation contract",
            )
    encoder_digest = _need_digest(encoder["encoder_digest"], "encoder.encoder_digest")
    if encoder_digest != source_encoder["encoder_digest"]:
        raise TrellisError(
            "ENCODER_MISMATCH",
            "encoder.encoder_digest differs from the model-set observation contract",
        )
    if document["ordering_rule"] != ORDERING_RULE or document["ordering_rule"] != source_encoder["ordering_rule"]:
        raise TrellisError("ENCODER_MISMATCH", f"ordering_rule must be {ORDERING_RULE}")
    if document["step_semantics"] != source_encoder["step_semantics"]:
        raise TrellisError(
            "ENCODER_MISMATCH",
            "step_semantics differs from the model-set observation contract",
        )
    _need_string(document["step_semantics"], "step_semantics")
    step_contract = _validate_step_contract(document["step_contract"], "step_contract")
    if canonical_bytes(step_contract) != canonical_bytes(source_encoder["step_contract"]):
        raise TrellisError(
            "ENCODER_MISMATCH",
            "step_contract differs from the model-set observation contract",
        )
    analysis_as_of = _parse_time(document["analysis_as_of"], "analysis_as_of")
    items = document["items"]
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_OBSERVATIONS:
        raise TrellisError(
            "RESOURCE_LIMIT",
            f"items must contain 1..{MAX_OBSERVATIONS} observations",
        )
    maximum_observations = model_set["stopping_contract"]["maximum_observations"]
    if maximum_observations is not None and len(items) > maximum_observations:
        raise TrellisError(
            "STOPPING_LIMIT_EXCEEDED",
            f"items contains {len(items)} observations but stopping_contract.maximum_observations is {maximum_observations}",
        )

    symbol_lookup = {symbol: index for index, symbol in enumerate(model_set["symbol_ids"])}
    observation_ids: list[str] = []
    symbol_indices: list[int] = []
    parsed_items: list[dict[str, Any]] = []
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
            raise TrellisError(
                "OOV_SYMBOL",
                f"{prefix}.symbol_id is outside the declared observation vocabulary: {symbol}",
            )
        symbol_indices.append(symbol_lookup[symbol])
        event_time = _parse_time(item["event_time"], f"{prefix}.event_time")
        known_at = _parse_time(item["known_at"], f"{prefix}.known_at")
        if event_time > analysis_as_of:
            raise TrellisError(
                "FUTURE_EVENT",
                f"{prefix}.event_time exceeds analysis_as_of",
            )
        if event_time > known_at:
            raise TrellisError(
                "KNOWLEDGE_PRECEDES_EVENT",
                f"{prefix}.known_at precedes its observed event_time",
            )
        if known_at > analysis_as_of:
            raise TrellisError("FUTURE_KNOWLEDGE", f"{prefix}.known_at exceeds analysis_as_of")
        _string_list(item["source_refs"], f"{prefix}.source_refs", nonempty=True, unique=True)
        _need_string(item["coding_basis"], f"{prefix}.coding_basis")
        if item["coding_status"] not in {"observed", "corrected"}:
            raise TrellisError(
                "INVALID_FIELD",
                f"{prefix}.coding_status must be observed or corrected",
            )
        dependencies = _string_list(
            item["dependence_refs"],
            f"{prefix}.dependence_refs",
            unique=True,
        )
        if dependencies:
            raise TrellisError(
                "UNMODELED_OBSERVATION_DEPENDENCE",
                f"{prefix} ({observation_id}) declares dependence_refs, but Trellis engine 1.1.0 "
                "cannot adjust dependent evidence; encode one composite observation or revise the model",
            )
        if item["coding_status"] == "observed":
            if item["supersedes"] is not None:
                raise TrellisError(
                    "INVALID_SUPERSESSION",
                    f"{prefix}.observed item must have supersedes null",
                )
            supersedes = None
        else:
            if item["supersedes"] is None:
                raise TrellisError(
                    "INVALID_SUPERSESSION",
                    f"{prefix}.corrected item must bind a prior observation",
                )
            supersedes = _validate_supersedes(item["supersedes"], f"{prefix}.supersedes")
        parsed_items.append(
            {
                "observation_id": observation_id,
                "event_time": event_time,
                "known_at": known_at,
                "supersedes": supersedes,
            }
        )
    _check_unique(observation_ids, "items.observation_id")

    for index in range(1, len(parsed_items)):
        previous_time = parsed_items[index - 1]["event_time"]
        current_time = parsed_items[index]["event_time"]
        if current_time == previous_time:
            raise TrellisError(
                "STEP_TIME_COLLISION",
                f"items[{index}].event_time duplicates the preceding step; encode a composite observation",
            )
        if current_time < previous_time:
            raise TrellisError(
                "ORDER_MISMATCH",
                f"items must follow {ORDERING_RULE}",
            )
        if step_contract["kind"] == "fixed_interval":
            interval_seconds = step_contract["interval_seconds"]
            elapsed = current_time - previous_time
            actual_whole_seconds = elapsed.days * 86_400 + elapsed.seconds
            if actual_whole_seconds != interval_seconds or elapsed.microseconds != 0:
                actual_seconds = str(actual_whole_seconds)
                if elapsed.microseconds:
                    actual_seconds += f".{elapsed.microseconds:06d}".rstrip("0")
                raise TrellisError(
                    "STEP_INTERVAL_MISMATCH",
                    f"items[{index}] advances {actual_seconds} seconds; fixed_interval requires {interval_seconds}",
                )

    superseded_ids: list[str] = []
    for index, item in enumerate(parsed_items):
        supersedes = item["supersedes"]
        if supersedes is None:
            continue
        if prior_sequence is None:
            raise TrellisError(
                "INVALID_SUPERSESSION",
                f"items[{index}] correction requires a bound prior_sequence",
            )
        if (
            supersedes["sequence_id"] != prior_sequence["sequence_id"]
            or supersedes["sequence_revision"] != prior_sequence["revision"]
            or supersedes["sequence_digest"] != prior_sequence["digest"]
        ):
            raise TrellisError(
                "BINDING_MISMATCH",
                f"items[{index}].supersedes differs from prior_sequence binding",
            )
        target = supersedes["observation_id"]
        if target in observation_ids:
            raise TrellisError(
                "DOUBLE_COUNT_RISK",
                f"items[{index}] supersedes an observation still present in the effective sequence",
            )
        superseded_ids.append(target)
    if len(superseded_ids) != len(set(superseded_ids)):
        raise TrellisError(
            "DUPLICATE_SUPERSESSION",
            "multiple current observations supersede the same prior observation",
        )

    knowledge_monotonic = all(
        parsed_items[index - 1]["known_at"] < parsed_items[index]["known_at"]
        for index in range(1, len(parsed_items))
    )
    filtered_is_as_known_then = knowledge_monotonic
    temporal_mode = (
        "historical_prefix"
        if filtered_is_as_known_then
        else "retrospective_event_order"
    )
    return {
        "document": document,
        "digest": digest(document),
        "observation_ids": observation_ids,
        "symbol_indices": symbol_indices,
        "filtered_is_as_known_then": filtered_is_as_known_then,
        "temporal_mode": temporal_mode,
        "step_contract": step_contract,
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


def _bounded_log_probability(value: float) -> float:
    if value == 0.0:
        return 0.0
    if value < 0.0:
        return value
    if value <= LOG_PROBABILITY_CEILING_TOLERANCE:
        return 0.0
    raise TrellisError(
        "NUMERIC_FAILURE",
        "Predictive log probability exceeded zero beyond the binary64 roundoff envelope",
    )


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


def _posterior_from_logs(values: list[float]) -> dict[str, Any]:
    if all(value == -math.inf for value in values):
        raise TrellisError("NUMERIC_FAILURE", "Cannot normalize an all-zero posterior")
    normalizer = _logsumexp(values)
    linear: list[float] = []
    log_probabilities: list[float | None] = []
    underflow_indices: list[int] = []
    structural_zero_indices: list[int] = []
    for index, value in enumerate(values):
        if value == -math.inf:
            linear.append(0.0)
            log_probabilities.append(None)
            structural_zero_indices.append(index)
            continue
        log_probability = _bounded_log_probability(value - normalizer)
        scalar, underflow = _finite_exp(log_probability)
        log_probabilities.append(log_probability)
        if underflow:
            linear.append(0.0)
            underflow_indices.append(index)
        else:
            if scalar is None:
                raise TrellisError("NUMERIC_FAILURE", "Posterior conversion lost a finite value")
            linear.append(scalar)
    total = math.fsum(linear)
    if total <= 0.0 or not math.isfinite(total):
        raise TrellisError("NUMERIC_FAILURE", "Posterior normalization failed")
    return {
        "posterior": [0.0 if value == 0.0 else value / total for value in linear],
        "posterior_log_probabilities": log_probabilities,
        "posterior_finite_log_underflow_state_indices": underflow_indices,
        "posterior_structural_zero_state_indices": structural_zero_indices,
    }

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
    estimated_output_bytes = 16_384 + sum(
        2 * len(item.encode("utf-8")) + 16
        for item in sequence["observation_ids"]
    )
    symbol_order_bytes_per_model = sum(
        len(canonical_bytes(item)) + 16
        for item in model_set["symbol_ids"]
    )
    for echoed in (
        model_set.get("candidate_selection"),
        model_set.get("stopping_contract"),
        model_set.get("mapping_provenance"),
        sequence.get("step_contract"),
        sequence.get("prior_sequence"),
    ):
        if echoed is not None:
            estimated_output_bytes += 2 * len(canonical_bytes(echoed)) + 256
    comparison = model_set.get("comparison", {})
    fit_policy = comparison.get("absolute_fit_policy") if isinstance(comparison, dict) else None
    calibration_bytes = (
        len(canonical_bytes(fit_policy["calibration_ref"]))
        if isinstance(fit_policy, dict)
        else 0
    )
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
        model_id = str(model.get("model_id", ""))
        comparison_unit_id = str(model.get("comparison_unit_id", ""))
        estimated_output_bytes += 8_192 + calibration_bytes
        estimated_output_bytes += symbol_order_bytes_per_model
        estimated_output_bytes += 4 * (
            len(model_id.encode("utf-8")) + len(comparison_unit_id.encode("utf-8"))
        )
        estimated_output_bytes += sum(
            2 * len(item.encode("utf-8")) + 16 for item in model["state_order"]
        )
        for provenance_key in ("parameter_provenance", "prior_provenance"):
            provenance = model.get(provenance_key)
            if provenance is not None:
                estimated_output_bytes += 2 * len(canonical_bytes(provenance)) + 256
        estimated_output_bytes += observation_count * (512 + 96 * state_count)
        if smoothing:
            estimated_output_bytes += observation_count * (384 + 96 * state_count)
        if decode:
            estimated_output_bytes += observation_count * 16
    estimated_output_bytes += len(model_set["models"]) * 512
    estimated_output_bytes += (
        len(model_set["models"]) * (len(model_set["models"]) - 1) // 2
    ) * 512
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
    step_log_probabilities: list[float | None] = []
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
        log_scale = _bounded_log_probability(_logsumexp(log_unscaled))
        step_log_probabilities.append(log_scale)
        if log_scale == -math.inf:
            zero_at = step
            log_filtered_vectors.append(None)
            for _ in range(step + 1, len(symbols)):
                log_filtered_vectors.append(None)
                step_log_probabilities.append(None)
            log_likelihood = -math.inf
            break
        current = [value - log_scale for value in log_unscaled]
        log_filtered_vectors.append(current)
        previous = current
        log_likelihood += log_scale
    mean_surprisal = (
        math.inf
        if log_likelihood == -math.inf
        else 0.0 if log_likelihood == 0.0 else -log_likelihood / len(symbols)
    )
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
        if log_predictive is None:
            rows.append(
                {
                    "sequence_index": index,
                    "log_predictive_probability": None,
                    "predictive_probability": None,
                    "predictive_probability_underflow": False,
                    "posterior": None,
                    "posterior_log_probabilities": None,
                    "posterior_finite_log_underflow_state_indices": None,
                    "posterior_structural_zero_state_indices": None,
                }
            )
            continue
        predictive, underflow = _finite_exp(log_predictive)
        posterior = None if log_vector is None else _posterior_from_logs(log_vector)
        rows.append(
            {
                "sequence_index": index,
                "log_predictive_probability": None if log_predictive == -math.inf else log_predictive,
                "predictive_probability": predictive,
                "predictive_probability_underflow": underflow,
                "posterior": None if posterior is None else posterior["posterior"],
                "posterior_log_probabilities": (
                    None if posterior is None else posterior["posterior_log_probabilities"]
                ),
                "posterior_finite_log_underflow_state_indices": (
                    None
                    if posterior is None
                    else posterior["posterior_finite_log_underflow_state_indices"]
                ),
                "posterior_structural_zero_state_indices": (
                    None
                    if posterior is None
                    else posterior["posterior_structural_zero_state_indices"]
                ),
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
        posterior = _posterior_from_logs(log_smoothed)
        output.append(
            {
                "sequence_index": step,
                "posterior": posterior["posterior"],
                "posterior_log_probabilities": posterior["posterior_log_probabilities"],
                "posterior_finite_log_underflow_state_indices": posterior[
                    "posterior_finite_log_underflow_state_indices"
                ],
                "posterior_structural_zero_state_indices": posterior[
                    "posterior_structural_zero_state_indices"
                ],
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
def _calibration_reasons(
    model_set: dict[str, Any], observation_count: int
) -> list[str]:
    policy = model_set["comparison"].get("absolute_fit_policy")
    if not isinstance(policy, dict):
        return ["absolute_fit_policy_missing"]
    calibration = policy["calibration_ref"]
    reasons: list[str] = []
    if calibration["calibration_target_digest"] != model_set["calibration_target_digest"]:
        reasons.append("calibration_target_mismatch")
    if observation_count < calibration["minimum_observations"]:
        reasons.append("calibration_horizon_below_minimum")
    if observation_count > calibration["maximum_observations"]:
        reasons.append("calibration_horizon_above_maximum")
    return reasons


def _absolute_fit(
    result: dict[str, Any],
    model_set: dict[str, Any],
    observation_count: int,
) -> dict[str, Any]:
    policy = model_set["comparison"].get("absolute_fit_policy")
    reasons = _calibration_reasons(model_set, observation_count)
    common = {
        "assessment_basis": "declared_threshold_arithmetic",
        "calibration_truth_validated": False,
        "metric": SURPRISAL_METRIC,
        "log_base": LOG_BASE,
        "unit": SURPRISAL_UNIT,
        "threshold": None if not isinstance(policy, dict) else float(policy["threshold"]),
        "calibration_ref": None if not isinstance(policy, dict) else policy["calibration_ref"],
    }
    if reasons or not isinstance(policy, dict):
        return {"status": "unassessed", "reason": reasons, **common}
    return {
        "status": "pass" if result["mean_surprisal"] <= float(policy["threshold"]) else "fail",
        "reason": [],
        **common,
    }


def _fit_summary(models: list[dict[str, Any]], fits: list[dict[str, Any]]) -> dict[str, Any]:
    passing = [models[index]["model_id"] for index, fit in enumerate(fits) if fit["status"] == "pass"]
    failing = [models[index]["model_id"] for index, fit in enumerate(fits) if fit["status"] == "fail"]
    unassessed = [
        models[index]["model_id"]
        for index, fit in enumerate(fits)
        if fit["status"] == "unassessed"
    ]
    if unassessed:
        status = "unassessed"
    elif passing and failing:
        status = "mixed"
    elif passing:
        status = "all_pass"
    else:
        status = "all_fail"
    return {
        "status": status,
        "passing_model_ids": passing,
        "failing_model_ids": failing,
        "unassessed_model_ids": unassessed,
    }


def _duplicate_groups(
    models: list[dict[str, Any]], key: str, value_key: str
) -> list[dict[str, Any]]:
    groups: dict[str, list[str]] = {}
    for model in models:
        groups.setdefault(model[key], []).append(model["model_id"])
    return [
        {value_key: value, "model_ids": model_ids}
        for value, model_ids in groups.items()
        if len(model_ids) > 1
    ]


def _duplicate_screen(models: list[dict[str, Any]]) -> dict[str, Any]:
    repeated_units = _duplicate_groups(models, "comparison_unit_id", "comparison_unit_id")
    identical_kernels = _duplicate_groups(
        models, "predictive_kernel_digest", "predictive_kernel_digest"
    )
    return {
        "status": "blocked" if repeated_units or identical_kernels else "clear",
        "basis": "declared_comparison_unit_identity_and_identical_ordered_predictive_kernel",
        "repeated_comparison_unit_groups": repeated_units,
        "identical_ordered_kernel_groups": identical_kernels,
        "general_observational_equivalence_validated": False,
    }


def _base_comparison_reasons(
    models: list[dict[str, Any]],
    contract: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if len(models) < 2:
        reasons.append("single_model_closed_world")
    if contract["status"] != "eligible":
        reasons.append("comparison_contract_ineligible")
    if (
        contract["shared_observation_semantics_required"] is not True
        or contract["shared_sequence_required"] is not True
    ):
        reasons.append("shared_semantics_or_sequence_not_required")
    if any(not model["comparison_eligible"] for model in models):
        reasons.append("model_declared_ineligible")
    return reasons


def _provenance_is_evidence_ready(provenance: dict[str, Any]) -> bool:
    return (
        provenance["fixed_before_sequence"] is True
        and provenance["kind"] != "stipulated_scenario"
    )


def _evidence_input_reasons(model_set: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if model_set["candidate_selection"]["status"] != "fixed_before_sequence":
        reasons.append("candidate_selection_not_fixed_before_sequence")
    if model_set["stopping_contract"]["status"] != "fixed_before_sequence":
        reasons.append("stopping_rule_not_fixed_before_sequence")
    if not _provenance_is_evidence_ready(model_set["mapping_provenance"]):
        reasons.append("observation_mapping_provenance_not_evidence_ready")
    if any(
        not _provenance_is_evidence_ready(model["parameter_provenance"])
        for model in model_set["models"]
    ):
        reasons.append("parameter_provenance_not_evidence_ready")
    if any(
        not _provenance_is_evidence_ready(model["prior_provenance"])
        for model in model_set["models"]
    ):
        reasons.append("prior_provenance_not_evidence_ready")
    policy = model_set["comparison"].get("absolute_fit_policy")
    if not isinstance(policy, dict):
        reasons.append("calibration_contract_incomplete")
    elif not _provenance_is_evidence_ready(policy["calibration_ref"]["provenance"]):
        reasons.append("calibration_provenance_not_evidence_ready")
    return reasons


def _normalize_model_priors(
    models: list[dict[str, Any]],
) -> tuple[list[float] | None, dict[str, Any], list[str]]:
    priors = [model["prior"] for model in models]
    summary: dict[str, Any] = {
        "policy": NORMALIZATION_POLICY,
        "absolute_tolerance": TOLERANCE,
        "sum_before": None,
        "adjusted": False,
    }
    if any(prior is None for prior in priors):
        return None, summary, ["model_prior_missing"]
    typed = [float(prior) for prior in priors]
    total = math.fsum(typed)
    summary["sum_before"] = total
    if abs(total - 1.0) > TOLERANCE:
        return None, summary, ["model_priors_non_stochastic"]
    summary["adjusted"] = total != 1.0
    return [value / total for value in typed], summary, []


def _pairwise_log_likelihood_ratios(
    models: list[dict[str, Any]],
    results: list[dict[str, Any]],
    reasons: list[str],
    effective_interpretation: str,
) -> dict[str, Any]:
    if reasons:
        return {
            "status": "unsupported",
            "reason": list(dict.fromkeys(reasons)),
            "log_base": LOG_BASE,
            "orientation": "numerator_model_over_denominator_model",
            "interpretation": "none",
            "rows": [],
        }
    rows: list[dict[str, Any]] = []
    for left in range(len(models)):
        for right in range(left + 1, len(models)):
            numerator = results[left]["log_likelihood"]
            denominator = results[right]["log_likelihood"]
            if numerator == -math.inf and denominator == -math.inf:
                status, value = "undefined_both_zero", None
            elif numerator == -math.inf:
                status, value = "negative_infinity", None
            elif denominator == -math.inf:
                status, value = "positive_infinity", None
            else:
                status, value = "finite", numerator - denominator
            rows.append(
                {
                    "numerator_model_id": models[left]["model_id"],
                    "denominator_model_id": models[right]["model_id"],
                    "status": status,
                    "log_likelihood_ratio": value,
                }
            )
    interpretation = {
        "conditional_evidence_update": "conditional_evidence",
        "scenario_only": "scenario_only",
        "diagnostic_only": "diagnostic_only",
    }[effective_interpretation]
    return {
        "status": "computed",
        "reason": [],
        "log_base": LOG_BASE,
        "orientation": "numerator_model_over_denominator_model",
        "interpretation": interpretation,
        "rows": rows,
    }


def _comparison(
    model_set: dict[str, Any],
    results: list[dict[str, Any]],
    fits: list[dict[str, Any]],
) -> dict[str, Any]:
    models = model_set["models"]
    contract = model_set["comparison"]
    lane = model_set["epistemic_lane"]
    fit_summary = _fit_summary(models, fits)
    duplicate_screen = _duplicate_screen(models)
    arithmetic_reasons = _base_comparison_reasons(models, contract)
    if not contract["prior_basis"]:
        arithmetic_reasons.append("prior_basis_missing")
    normalized_priors, prior_normalization, prior_reasons = _normalize_model_priors(models)
    arithmetic_reasons.extend(prior_reasons)
    if duplicate_screen["repeated_comparison_unit_groups"]:
        arithmetic_reasons.append("repeated_comparison_unit")
    if duplicate_screen["identical_ordered_kernel_groups"]:
        arithmetic_reasons.append("identical_ordered_predictive_kernel")
    if all(result["log_likelihood"] == -math.inf for result in results):
        arithmetic_reasons.append("all_models_zero_likelihood")
    arithmetic_reasons = list(dict.fromkeys(arithmetic_reasons))

    evidence_reasons = list(arithmetic_reasons)
    if not contract["calibration_basis"]:
        evidence_reasons.append("calibration_contract_incomplete")
    evidence_reasons.extend(_evidence_input_reasons(model_set))
    for fit in fits:
        if fit["status"] == "unassessed":
            evidence_reasons.extend(fit["reason"])
    if fit_summary["status"] == "all_fail":
        evidence_reasons.append("absolute_fit_gate_failed")
    evidence_reasons = list(dict.fromkeys(evidence_reasons))

    if lane == "assumption_stress_test":
        evidence_gate = {"status": "not_applicable", "reasons": []}
        effective_interpretation = "scenario_only"
    elif evidence_reasons:
        evidence_gate = {"status": "failed", "reasons": evidence_reasons}
        effective_interpretation = "diagnostic_only"
    else:
        evidence_gate = {"status": "passed", "reasons": []}
        effective_interpretation = "conditional_evidence_update"
    weight_reasons = arithmetic_reasons

    pairwise_reasons = _base_comparison_reasons(models, contract)
    if duplicate_screen["repeated_comparison_unit_groups"]:
        pairwise_reasons.append("repeated_comparison_unit")
    if duplicate_screen["identical_ordered_kernel_groups"]:
        pairwise_reasons.append("identical_ordered_predictive_kernel")
    pairwise = _pairwise_log_likelihood_ratios(
        models,
        results,
        list(dict.fromkeys(pairwise_reasons)),
        effective_interpretation,
    )

    common = {
        "conditional_on_model_set": True,
        "effective_interpretation": effective_interpretation,
        "evidence_gate": evidence_gate,
        "fit_summary": fit_summary,
        "prior_normalization": prior_normalization,
        "duplicate_screen": duplicate_screen,
        "pairwise_log_likelihood_ratios": pairwise,
    }
    if weight_reasons or normalized_priors is None:
        return {
            "weights_status": "unsupported",
            "reason": weight_reasons,
            "weight_interpretation": "none",
            "linear_weights_complete": False,
            "relative_model_weights": [],
            **common,
        }

    unnormalized_log_weights = [
        _safe_log(normalized_priors[index]) + results[index]["log_likelihood"]
        for index in range(len(models))
    ]
    log_normalizer = _logsumexp(unnormalized_log_weights)
    if log_normalizer == -math.inf:
        return {
            "weights_status": "unsupported",
            "reason": ["all_models_zero_likelihood"],
            "weight_interpretation": "none",
            "linear_weights_complete": False,
            "relative_model_weights": [],
            **common,
        }

    rows: list[dict[str, Any]] = []
    linear_weights_complete = True
    for index, unnormalized in enumerate(unnormalized_log_weights):
        if unnormalized == -math.inf:
            log_weight, weight, weight_status = None, 0.0, "exact_zero"
        else:
            log_weight = _bounded_log_probability(unnormalized - log_normalizer)
            weight, underflow = _finite_exp(log_weight)
            if underflow:
                weight_status = "underflow"
                linear_weights_complete = False
            else:
                weight_status = "finite"
        rows.append(
            {
                "model_id": models[index]["model_id"],
                "comparison_unit_id": models[index]["comparison_unit_id"],
                "log_weight": log_weight,
                "weight": weight,
                "weight_status": weight_status,
                "absolute_fit_status": fits[index]["status"],
            }
        )
    return {
        "weights_status": "computed",
        "reason": [],
        "weight_interpretation": effective_interpretation,
        "linear_weights_complete": linear_weights_complete,
        "relative_model_weights": rows,
        **common,
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
        "matrix_layout": {
            "transition": TRANSITION_LAYOUT,
            "emission": EMISSION_LAYOUT,
        },
        "normalization": {
            "policy": NORMALIZATION_POLICY,
            "absolute_tolerance": TOLERANCE,
        },
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
    resource_estimate = estimate_resources(
        model_set,
        sequence,
        decode=decode,
        smoothing=smoothing,
    )
    symbols = sequence["symbol_indices"]
    results = [forward(model, symbols) for model in model_set["models"]]
    fits = [
        _absolute_fit(result, model_set, len(symbols))
        for result in results
    ]
    comparison = _comparison(model_set, results, fits)
    fit_status = comparison["fit_summary"]["status"]
    if all(result["log_likelihood"] == -math.inf for result in results):
        reframe_status, reframe_reasons = "required", ["all_models_zero_likelihood"]
    elif fit_status == "all_fail":
        reframe_status, reframe_reasons = (
            "required",
            ["all_models_failed_calibrated_absolute_fit"],
        )
    elif fit_status == "unassessed":
        reframe_status, reframe_reasons = (
            "unassessed",
            ["absolute_fit_not_fully_calibrated"],
        )
    else:
        reframe_status, reframe_reasons = "not_required", []

    per_model: list[dict[str, Any]] = []
    for index, model in enumerate(model_set["models"]):
        result = results[index]
        likelihood, underflow = _finite_exp(result["log_likelihood"])
        item: dict[str, Any] = {
            "model_id": model["model_id"],
            "comparison_unit_id": model["comparison_unit_id"],
            "model_version": model["raw"]["model_version"],
            "model_document_digest": model["model_document_digest"],
            "inference_model_digest": model["inference_model_digest"],
            "predictive_kernel_digest": model["predictive_kernel_digest"],
            "observation_contract_digest": model_set["observation_contract_digest"],
            "state_order": model["state_order"],
            "symbol_order": model_set["symbol_ids"],
            "matrix_layout": model["matrix_layout"],
            "normalization": model["normalization"],
            "parameter_provenance": model["parameter_provenance"],
            "prior_provenance": model["prior_provenance"],
            "inference_status": result["status"],
            "log_sequence_likelihood": (
                None if result["log_likelihood"] == -math.inf else result["log_likelihood"]
            ),
            "sequence_likelihood": likelihood,
            "sequence_likelihood_underflow": underflow,
            "mean_predictive_surprisal": (
                None if result["mean_surprisal"] == math.inf else result["mean_surprisal"]
            ),
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
    if any(result["zero_at"] is not None for result in results):
        diagnostics.append(
            "zero_likelihood marks an observation outside supplied model support, not a claim "
            "about what can occur in the world; later aligned rows were not evaluated"
        )
    if not sequence["filtered_is_as_known_then"]:
        diagnostics.append(
            "filter is retrospective event-order inference, not a historical as-known-then estimate"
        )
    if sequence["correction_count"]:
        diagnostics.append(
            "corrections are bound to the prior sequence digest; prior document contents were not independently loaded"
        )
    if model_set["epistemic_lane"] == "assumption_stress_test":
        diagnostics.append(
            "assumption_stress_test numbers are conditional what-if results, not evidential belief or claim confidence"
        )
    elif comparison["evidence_gate"]["status"] == "failed":
        diagnostics.append(
            "requested evidence_update failed one or more evidence gates; probabilistic outputs are diagnostic only"
        )
    if any(model["normalization"]["vectors_adjusted"] for model in model_set["models"]):
        diagnostics.append(
            "one or more probability vectors were normalized within the declared tolerance; per-model receipts disclose the adjustment"
        )
    if fit_status == "mixed":
        diagnostics.append(
            "relative weights retain every declared candidate; a model-relative weight does not rehabilitate an absolute-fit failure"
        )
    diagnostics.append(
        "empty dependence_refs means no dependence was declared; Trellis did not validate observation independence or apply dependence reweighting"
    )

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
            "observation_contract_digest": model_set["observation_contract_digest"],
            "stopping_contract_digest": model_set["stopping_contract_digest"],
            "calibration_target_digest": model_set["calibration_target_digest"],
            "epistemic_lane": model_set["epistemic_lane"],
            "mapping_provenance": model_set["mapping_provenance"],
            "candidate_selection": model_set["candidate_selection"],
            "stopping_contract": model_set["stopping_contract"],
            "step_contract": sequence["step_contract"],
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
            "epistemic_lane": model_set["epistemic_lane"],
            "model_relative": True,
            "probabilities_are_conditional": True,
            "probabilistic_output_interpretation": (
                comparison["effective_interpretation"]
            ),
            "all_probabilistic_outputs_scenario_conditioned": (
                comparison["effective_interpretation"] == "scenario_only"
            ),
            "claim_confidence": False,
            "truth_certification": False,
            "source_confidence_modified": False,
            "parameter_uncertainty_integrated": False,
            "parameter_provenance_truth_validated": False,
            "calibration_truth_validated": False,
            "observational_equivalence_validated": False,
            "candidate_selection_truth_validated": False,
            "stopping_rule_truth_validated": False,
            "observation_independence_validated": False,
            "declared_dependence_count": 0,
            "dependence_adjustment": "none",
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
    resource_estimate = estimate_resources(
        model_set,
        sequence,
        decode=False,
        smoothing=False,
    )
    receipt: dict[str, Any] = {
        "contract": VALIDATION_CONTRACT,
        "status": "valid",
        "engine": engine_descriptor(),
        "inputs": {
            "model_set_digest": model_set["digest"],
            "sequence_digest": sequence["digest"],
            "observation_contract_digest": model_set["observation_contract_digest"],
            "stopping_contract_digest": model_set["stopping_contract_digest"],
            "calibration_target_digest": model_set["calibration_target_digest"],
            "epistemic_lane": model_set["epistemic_lane"],
            "mapping_provenance": model_set["mapping_provenance"],
            "model_count": len(model_set["models"]),
            "observation_count": len(sequence["symbol_indices"]),
        },
        "resource_estimate": resource_estimate,
        "comparison_declared": model_set["comparison"]["status"],
        "candidate_selection": model_set["candidate_selection"],
        "stopping_contract": model_set["stopping_contract"],
        "model_contracts": [
            {
                "model_id": model["model_id"],
                "comparison_unit_id": model["comparison_unit_id"],
                "model_document_digest": model["model_document_digest"],
                "inference_model_digest": model["inference_model_digest"],
                "predictive_kernel_digest": model["predictive_kernel_digest"],
                "normalization": model["normalization"],
                "parameter_provenance": model["parameter_provenance"],
                "prior_provenance": model["prior_provenance"],
            }
            for model in model_set["models"]
        ],
        "temporal_semantics": {
            "mode": sequence["temporal_mode"],
            "filtered_is_as_known_then": sequence["filtered_is_as_known_then"],
            "step_contract": sequence["step_contract"],
        },
        "semantic_boundary": {
            "structural_and_stochastic_only": True,
            "ontology_validated": False,
            "calibration_truth_validated": False,
            "observational_equivalence_validated": False,
            "parameter_provenance_truth_validated": False,
            "candidate_selection_truth_validated": False,
            "stopping_rule_truth_validated": False,
            "observation_independence_validated": False,
            "declared_dependence_count": 0,
            "dependence_adjustment": "none",
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
