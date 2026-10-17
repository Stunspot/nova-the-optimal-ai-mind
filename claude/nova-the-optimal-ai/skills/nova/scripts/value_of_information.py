#!/usr/bin/env python3
"""Bounded, exact finite-decision value-of-information arithmetic; no actions or stores."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path

ENGINE_ID = "nova-value-of-information"
ENGINE_VERSION = "1.0.0"
INPUT_SCHEMA = "nova-value-of-information/v1"
MAX_BYTES = 1024 * 1024
MAX_STATES = 64
MAX_ACTIONS = 64
MAX_INQUIRIES = 32
MAX_OUTCOMES = 32
MAX_OPERATIONS = 5_000_000
MAX_RATIONAL_BITS = 4096
MAX_OUTPUT_BYTES = 32 * 1024 * 1024
DISTRIBUTION_TOLERANCE = Fraction(1, 10**12)
NEAR_TIE_TOLERANCE = Fraction(1, 10**12)


class Refusal(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def refuse(code: str, message: str):
    raise Refusal(code, message)


def bounded(value: Fraction) -> Fraction:
    if max(value.numerator.bit_length(), value.denominator.bit_length()) > MAX_RATIONAL_BITS:
        refuse("ARITHMETIC_RESOURCE_LIMIT", "Exact rational arithmetic exceeded 4096 bits; reduce numerical complexity.")
    return value


def add(values) -> Fraction:
    total = Fraction(0)
    for value in values:
        total = bounded(total + value)
    return total


def mul(left: Fraction, right: Fraction) -> Fraction:
    return bounded(left * right)


def div(left: Fraction, right: Fraction) -> Fraction:
    return bounded(left / right)


def sub(left: Fraction, right: Fraction) -> Fraction:
    return bounded(left - right)


def project(value: Fraction) -> float:
    try:
        result = float(value)
    except (OverflowError, ValueError):
        refuse("NUMERIC_RANGE", "A value cannot be represented as a finite JSON number.")
    if not math.isfinite(result) or (value != 0 and result == 0):
        refuse("NUMERIC_RANGE", "A nonzero value overflows or underflows the JSON binary64 projection.")
    return 0.0 if result == 0 else result


def number(value, path: str, probability: bool = False, nonnegative: bool = False) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        refuse("INVALID_NUMBER", f"{path} must be a finite JSON number, not a boolean or string.")
    try:
        decimal = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError):
        refuse("INVALID_NUMBER", f"{path} is not a finite number.")
    if not decimal.is_finite():
        refuse("INVALID_NUMBER", f"{path} must be finite.")
    parts = decimal.as_tuple()
    if len(parts.digits) > 128 or abs(parts.exponent) > 400:
        refuse("NUMERIC_RESOURCE_LIMIT", f"{path} exceeds the supported numeric precision or exponent.")
    result = bounded(Fraction(decimal))
    project(result)
    if probability and not 0 <= result <= 1:
        refuse("INVALID_PROBABILITY", f"{path} must be between zero and one.")
    if nonnegative and result < 0:
        refuse("INVALID_COST", f"{path} must be nonnegative.")
    return result


def text(value, path: str, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        refuse("INVALID_TEXT", f"{path} must be nonempty text of at most {maximum} characters.")
    return value


def fields(value, expected: set[str], path: str):
    if not isinstance(value, dict) or set(value) != expected:
        refuse("INVALID_FIELDS", f"{path} requires exactly these keys: {', '.join(sorted(expected))}.")


def rows(value, path: str, maximum: int):
    if not isinstance(value, list) or not 1 <= len(value) <= maximum:
        refuse("RESOURCE_OR_SHAPE_LIMIT", f"{path} must have 1 through {maximum} entries.")
    return value


def unique_id(value, seen: set[str], path: str) -> str:
    item_id = text(value, path, 256)
    if item_id in seen:
        refuse("DUPLICATE_ID", f"{path} duplicates an identifier in its collection.")
    seen.add(item_id)
    return item_id


def distribution(values, path: str, adjustments: list):
    total = add(values)
    if total <= 0 or abs(total - 1) > DISTRIBUTION_TOLERANCE:
        refuse("INVALID_DISTRIBUTION", f"{path} must sum to one within absolute tolerance 1e-12.")
    normalized = [div(value, total) for value in values]
    if total != 1:
        adjustments.append({"path": path, "supplied_sum": project(total),
                            "maximum_absolute_adjustment": project(max(abs(a-b) for a, b in zip(values, normalized)))})
    return normalized


def validate_document(document: dict) -> dict:
    fields(document, {"schema", "purpose", "utility_unit", "basis", "states", "actions", "inquiries"}, "input")
    if document["schema"] != INPUT_SCHEMA:
        refuse("WRONG_SCHEMA", f"schema must be {INPUT_SCHEMA}.")
    purpose = text(document["purpose"], "purpose")
    unit = text(document["utility_unit"], "utility_unit", 256)
    basis = document["basis"]
    fields(basis, {"mode", "assumptions", "source_refs"}, "basis")
    if basis["mode"] not in ("stipulated_scenario", "evidence_informed"):
        refuse("INVALID_BASIS", "basis.mode must be stipulated_scenario or evidence_informed.")
    for field in ("assumptions", "source_refs"):
        for i, item in enumerate(rows(basis[field], f"basis.{field}", 128)):
            text(item, f"basis.{field}[{i}]")
    states, seen, adjustments = [], set(), []
    for i, row in enumerate(rows(document["states"], "states", MAX_STATES)):
        fields(row, {"id", "probability"}, f"states[{i}]")
        states.append({"id": unique_id(row["id"], seen, f"states[{i}].id"),
                       "probability": number(row["probability"], f"states[{i}].probability", probability=True)})
    probabilities = distribution([row["probability"] for row in states], "states", adjustments)
    for state, probability in zip(states, probabilities):
        state["probability"] = probability
    state_ids = [row["id"] for row in states]
    actions, seen = [], set()
    for i, row in enumerate(rows(document["actions"], "actions", MAX_ACTIONS)):
        fields(row, {"id", "utilities"}, f"actions[{i}]")
        fields(row["utilities"], set(state_ids), f"actions[{i}].utilities")
        actions.append({"id": unique_id(row["id"], seen, f"actions[{i}].id"),
                        "utilities": [number(row["utilities"][sid], f"actions[{i}].utilities.{sid}") for sid in state_ids]})
    inquiries, seen = [], set()
    for i, row in enumerate(rows(document["inquiries"], "inquiries", MAX_INQUIRIES)):
        fields(row, {"id", "cost", "outcomes"}, f"inquiries[{i}]")
        inquiry_id = unique_id(row["id"], seen, f"inquiries[{i}].id")
        cost = number(row["cost"], f"inquiries[{i}].cost", nonnegative=True)
        outcomes, outcome_ids = [], set()
        for j, outcome in enumerate(rows(row["outcomes"], f"inquiries[{i}].outcomes", MAX_OUTCOMES)):
            fields(outcome, {"id", "likelihoods"}, f"inquiries[{i}].outcomes[{j}]")
            fields(outcome["likelihoods"], set(state_ids), f"inquiries[{i}].outcomes[{j}].likelihoods")
            outcomes.append({"id": unique_id(outcome["id"], outcome_ids, f"inquiries[{i}].outcomes[{j}].id"),
                             "likelihoods": [number(outcome["likelihoods"][sid], f"inquiries[{i}].outcomes[{j}].likelihoods.{sid}", probability=True) for sid in state_ids]})
        for k, sid in enumerate(state_ids):
            normalized = distribution([outcome["likelihoods"][k] for outcome in outcomes], f"inquiries[{i}].likelihoods.{sid}", adjustments)
            for outcome, likelihood in zip(outcomes, normalized):
                outcome["likelihoods"][k] = likelihood
        inquiries.append({"id": inquiry_id, "cost": cost, "outcomes": outcomes})
    operations = len(states) * len(actions) * (2 + sum(len(q["outcomes"]) for q in inquiries))
    if operations > MAX_OPERATIONS:
        refuse("WORK_LIMIT", "Estimated state-action-outcome operations exceed five million.")
    return {"purpose": purpose, "utility_unit": unit, "basis": basis, "states": states,
            "actions": actions, "inquiries": inquiries, "normalization": adjustments,
            "estimated_operations": operations}


def envelope(kind: str, digest: str | None) -> dict:
    return {"schema": f"nova-value-of-information-{kind}/v1", "engine_id": ENGINE_ID,
            "engine_version": ENGINE_VERSION, "input_sha256": digest,
            "semantic_boundary": {"interpretation": "conditional_arithmetic",
                "provenance_validated": False, "calibration_validated": False,
                "model_completeness_validated": False, "utility_endorsed": False,
                "action_authorized": False, "persistence_performed": False}}


def common(model: dict, kind: str, digest: str | None) -> dict:
    result = envelope(kind, digest)
    result.update({"purpose": model["purpose"], "utility_unit": model["utility_unit"],
        "basis": model["basis"], "normalization": {"absolute_tolerance": project(DISTRIBUTION_TOLERANCE),
        "adjusted_distributions": model["normalization"]},
        "arithmetic": {"method": "exact_rational_from_json_decimal_numbers", "output_projection": "binary64",
            "maximizers_use_exact_arithmetic": True, "output_rounding_can_hide_value_differences": True, "ranking_uses_projected_numbers": False,
            "near_tie_absolute_tolerance": project(NEAR_TIE_TOLERANCE),
            "near_ties_change_maximizers": False, "near_ties_mean_human_indifference": False,
            "maximum_rational_bits": MAX_RATIONAL_BITS,
            "estimated_state_action_outcome_operations": model["estimated_operations"]}})
    return result


def rank(ids: list[str], values: list[Fraction]) -> dict:
    best = max(values)
    gaps = [sub(best, value) for value in values]
    return {"best_ids": [item for item, gap in zip(ids, gaps) if gap == 0],
            "near_best_ids": [item for item, gap in zip(ids, gaps) if 0 < gap <= NEAR_TIE_TOLERANCE],
            "values": [{"id": item, "value": project(value), "gap_to_best": project(gap),
                        "exact_value": str(value), "exact_gap_to_best": str(gap),
                        "value_projection_rounded": Fraction.from_float(project(value)) != value,
                        "gap_projection_rounded": Fraction.from_float(project(gap)) != gap}
                       for item, value, gap in zip(ids, values, gaps)]}


def analyze_model(model: dict, digest: str | None = None) -> dict:
    states, actions = model["states"], model["actions"]
    state_ids = [state["id"] for state in states]
    action_ids = [action["id"] for action in actions]
    priors = [state["probability"] for state in states]
    current = [add(mul(p, u) for p, u in zip(priors, action["utilities"])) for action in actions]
    baseline = max(current)
    perfect = add(mul(p, max(action["utilities"][i] for action in actions)) for i, p in enumerate(priors))
    evpi = sub(perfect, baseline)
    if evpi < 0:
        raise ArithmeticError("Perfect information invariant failed.")
    inquiry_results, net_values = [], [Fraction(0)]
    for inquiry in model["inquiries"]:
        outcome_results, weighted_best = [], []
        for outcome in inquiry["outcomes"]:
            joint = [mul(p, likelihood) for p, likelihood in zip(priors, outcome["likelihoods"])]
            probability = add(joint)
            if probability == 0:
                outcome_results.append({"id": outcome["id"], "probability": 0.0,
                    "posterior": None, "conditional_actions": None})
                weighted_best.append(Fraction(0))
                continue
            # Each action sees only this observed outcome; state remains latent.
            weighted = [add(mul(p, u) for p, u in zip(joint, action["utilities"])) for action in actions]
            weighted_best.append(max(weighted))
            outcome_results.append({"id": outcome["id"], "probability": project(probability),
                "posterior": {sid: project(div(p, probability)) for sid, p in zip(state_ids, joint)},
                "conditional_actions": rank(action_ids, [div(value, probability) for value in weighted])})
        gross = add(weighted_best)
        evsi = sub(gross, baseline)
        if not 0 <= evsi <= evpi:
            raise ArithmeticError("Sample information invariant failed.")
        net = sub(evsi, inquiry["cost"])
        net_values.append(net)
        inquiry_results.append({"id": inquiry["id"], "cost": project(inquiry["cost"]),
            "outcomes": outcome_results, "expected_utility_after_inquiry": project(gross),
            "expected_utility_after_cost": project(sub(gross, inquiry["cost"])),
            "gross_value_of_information": project(evsi), "net_value_of_information": project(net)})
    result = common(model, "analysis", digest)
    option_ids = ["proceed_without_inquiry"] + [f"inquiry:{q['id']}" for q in model["inquiries"]]
    result.update({"current": rank(action_ids, current), "current_expected_utility": project(baseline),
        "perfect_information_expected_utility": project(perfect), "value_of_perfect_information": project(evpi),
        "inquiries": inquiry_results, "options_by_net_value": rank(option_ids, net_values)})
    return result


def duplicate_free_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            refuse("DUPLICATE_JSON_KEY", "JSON contains a duplicate object key.")
        result[key] = value
    return result


def parse_numeric_token(token: str):
    if len(token) > 128:
        refuse("NUMERIC_RESOURCE_LIMIT", "A JSON number exceeds 128 characters.")
    value = Decimal(token)
    if not value.is_finite() or abs(value.as_tuple().exponent) > 400:
        refuse("INVALID_NUMBER", "JSON numbers must be finite and within the supported exponent range.")
    return value


def load_document(path: Path) -> tuple[dict, str]:
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
    except OSError:
        refuse("INPUT_UNAVAILABLE", "The input file could not be read.")
    if not raw or len(raw) > MAX_BYTES:
        refuse("INPUT_SIZE_LIMIT", "The input must be nonempty and at most 1 MiB.")
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=duplicate_free_object,
                              parse_float=parse_numeric_token, parse_int=parse_numeric_token,
                              parse_constant=lambda token: refuse("INVALID_NUMBER", "NaN and Infinity are unsupported."))
    except (UnicodeError, json.JSONDecodeError, RecursionError, InvalidOperation):
        refuse("INVALID_JSON", "Input must be valid bounded UTF-8 JSON without excessive nesting.")
    return document, hashlib.sha256(raw).hexdigest()


class Parser(argparse.ArgumentParser):
    def error(self, message):
        refuse("INVALID_COMMAND", "Use: value_of_information.py validate|analyze INPUT.json")


def main(argv=None) -> int:
    digest = None
    try:
        parser = Parser(add_help=False)
        parser.add_argument("command", choices=("validate", "analyze"))
        parser.add_argument("input")
        args = parser.parse_args(argv)
        document, digest = load_document(Path(args.input))
        model = validate_document(document)
        if args.command == "validate":
            result = common(model, "validation", digest)
            result["structural_and_stochastic_only"] = True
            result["arithmetic_analysis_performed"] = False
        else:
            result = analyze_model(model, digest)
        encoded = json.dumps(result, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > MAX_OUTPUT_BYTES:
            refuse("OUTPUT_SIZE_LIMIT", "Output exceeds 32 MiB.")
        exit_code = 0
    except Refusal as error:
        result = envelope("error", digest)
        result["error"] = {"code": error.code, "message": str(error)}
        encoded, exit_code = json.dumps(result, ensure_ascii=True, allow_nan=False), 2
    except Exception:
        result = envelope("error", digest)
        result["error"] = {"code": "INTERNAL_ERROR", "message": "Contained calculation or output failure; no result is supported."}
        encoded, exit_code = json.dumps(result, ensure_ascii=True, allow_nan=False), 3
    try:
        sys.stdout.write(encoded + "\n")
    except (OSError, UnicodeError):
        return 3
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
