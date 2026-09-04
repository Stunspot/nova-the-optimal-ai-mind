from __future__ import annotations

import copy
import hashlib
import importlib.util
import itertools
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import jsonschema
except ImportError:  # Optional verification dependency; calculator runtime remains stdlib-only.
    jsonschema = None

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_FIXTURES = ROOT / "tests" / "fixtures" / "model-agnosticism-engine-1.0.0"


def resolve_runtime_layout() -> tuple[Path, Path]:
    authoring_assets = ROOT / "source" / "instruments" / "model-agnosticism"
    authoring_script = authoring_assets / "model_agnosticism_trellis.py"
    if authoring_assets.is_dir() and authoring_script.is_file():
        return authoring_assets, authoring_script

    free_skill = ROOT / "plugins" / "nova-the-optimal-ai" / "skills" / "nova"
    free_assets = free_skill / "assets" / "model-agnosticism"
    free_script = free_skill / "scripts" / "model_agnosticism_trellis.py"
    if free_assets.is_dir() and free_script.is_file():
        return free_assets, free_script

    product_path = ROOT / "source" / "product.json"
    if product_path.is_file():
        product = json.loads(product_path.read_text(encoding="utf-8"))
        mind_source = product.get("composition", {}).get("mind", {}).get("source")
        if isinstance(mind_source, str) and mind_source.strip():
            frozen_codex = ROOT / mind_source / "codex"
            frozen_assets = frozen_codex / "assets" / "model-agnosticism"
            frozen_script = frozen_codex / "scripts" / "model_agnosticism_trellis.py"
            if frozen_assets.is_dir() and frozen_script.is_file():
                return frozen_assets, frozen_script

    raise RuntimeError("Cannot locate Trellis assets and runtime in an authoring, Nova Free, or active Nova Emergent layout")


SOURCE, SCRIPT = resolve_runtime_layout()
SPEC = importlib.util.spec_from_file_location("model_agnosticism_trellis", SCRIPT)
assert SPEC and SPEC.loader
TRELLIS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRELLIS)


def load(name: str) -> dict:
    return json.loads((SOURCE / name).read_text(encoding="utf-8"))


def bound_documents(model_document: dict, sequence_document: dict) -> tuple[dict, dict]:
    model_document = copy.deepcopy(model_document)
    sequence_document = copy.deepcopy(sequence_document)
    sequence_document["case_ref"] = model_document["case_ref"]
    sequence_document["model_set_id"] = model_document["model_set_id"]
    sequence_document["model_set_revision"] = model_document["revision"]
    sequence_document["model_set_digest"] = TRELLIS.digest(model_document)
    encoder = model_document["observation_contract"]
    sequence_document["encoder"] = {key: encoder[key] for key in ("encoder_id", "encoder_version", "encoder_digest")}
    sequence_document["ordering_rule"] = encoder["ordering_rule"]
    sequence_document["step_semantics"] = encoder["step_semantics"]
    return model_document, sequence_document


def bind(model_document: dict, sequence_document: dict) -> tuple[dict, dict]:
    model_document, sequence_document = bound_documents(model_document, sequence_document)
    model_set = TRELLIS.validate_model_set(model_document)
    return model_set, TRELLIS.validate_sequence(sequence_document, model_set)


def analyze_documents(
    model_document: dict,
    sequence_document: dict,
    *,
    decode: bool = True,
    smoothing: bool = True,
) -> dict:
    model_set, sequence = bind(model_document, sequence_document)
    return TRELLIS.analyze(model_set, sequence, decode=decode, smoothing=smoothing)


class TrellisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = load("example-model-set.json")
        self.sequence = load("example-observation-sequence.json")

    def textbook_result(self) -> dict:
        result = analyze_documents(self.model, self.sequence)
        return next(item for item in result["per_model"] if item["model_id"] == "textbook-weather")

    def test_reference_313_math_and_array_contract(self) -> None:
        result = self.textbook_result()
        self.assertEqual(result["state_order"], ["H", "C"])
        self.assertAlmostEqual(result["sequence_likelihood"], 0.028562, places=12)
        self.assertAlmostEqual(result["filtered_state_posteriors"][-1]["posterior"][0], 0.8226314683845669, places=14)
        self.assertEqual(result["viterbi"]["state_indices"], [0, 1, 0])
        self.assertAlmostEqual(result["viterbi"]["joint_probability"], 0.0128, places=14)
        self.assertEqual(result["surprisal_log_base"], "e")
        self.assertEqual(result["surprisal_unit"], "nats_per_observation")

    def test_forward_agrees_with_brute_force(self) -> None:
        model = self.model["models"][0]
        symbols = [2, 0, 2]
        total = 0.0
        for path in itertools.product(range(2), repeat=3):
            probability = model["initial"][path[0]] * model["emission"][path[0]][symbols[0]]
            for step in range(1, 3):
                probability *= model["transition"][path[step - 1]][path[step]] * model["emission"][path[step]][symbols[step]]
            total += probability
        self.assertAlmostEqual(self.textbook_result()["sequence_likelihood"], total, places=14)

    def test_filters_and_smoothers_are_normalized_and_time_typed(self) -> None:
        result = self.textbook_result()
        for item in result["filtered_state_posteriors"]:
            self.assertAlmostEqual(math.fsum(item["posterior"]), 1.0, places=14)
        for index, item in enumerate(result["smoothed_state_posteriors"]):
            self.assertAlmostEqual(math.fsum(item["posterior"]), 1.0, places=14)
            self.assertEqual(item["uses_later_observations"], index < 2)

    def test_comparable_models_receive_normalized_conditional_weights(self) -> None:
        result = analyze_documents(self.model, self.sequence)
        self.assertEqual(result["comparison"]["weights_status"], "computed")
        self.assertAlmostEqual(math.fsum(item["weight"] for item in result["comparison"]["relative_model_weights"]), 1.0, places=14)
        self.assertTrue(result["comparison"]["conditional_on_model_set"])

    def test_ineligible_comparison_preserves_per_model_inference(self) -> None:
        model = copy.deepcopy(self.model)
        model["comparison_contract"]["status"] = "ineligible"
        result = analyze_documents(model, self.sequence)
        self.assertEqual(result["comparison"]["weights_status"], "unsupported")
        self.assertIn("comparison_contract_ineligible", result["comparison"]["reason"])
        self.assertEqual(len(result["per_model"]), 2)
        self.assertTrue(all(item["inference_status"] == "completed" for item in result["per_model"]))

    def test_missing_or_mismatched_calibration_prevents_weights(self) -> None:
        missing = copy.deepcopy(self.model)
        missing["models"][0]["calibration_ref"] = None
        result = analyze_documents(missing, self.sequence)
        self.assertEqual(result["comparison"]["weights_status"], "unsupported")
        self.assertIn("model_calibration_ref_missing", result["comparison"]["reason"])
        self.assertEqual(result["per_model"][0]["absolute_fit"]["status"], "unassessed")

        mismatched = copy.deepcopy(self.model)
        mismatched["models"][0]["calibration_ref"]["digest"] = "a" * 64
        result = analyze_documents(mismatched, self.sequence)
        self.assertEqual(result["comparison"]["weights_status"], "unsupported")
        self.assertIn("calibration_reference_mismatch", result["comparison"]["reason"])
        self.assertEqual(result["per_model"][0]["absolute_fit"]["status"], "unassessed")

    def test_single_model_never_fabricates_between_model_weight(self) -> None:
        model = copy.deepcopy(self.model)
        model["models"] = [model["models"][0]]
        model["models"][0]["prior_model_weight"] = 1.0
        result = analyze_documents(model, self.sequence)
        self.assertEqual(result["comparison"]["weights_status"], "unsupported")
        self.assertIn("single_model_closed_world", result["comparison"]["reason"])

    def test_zero_model_prior_is_rejected_while_support_exclusions_remain_valid(self) -> None:
        for zero in (0, 0.0, -0.0):
            with self.subTest(zero=repr(zero)):
                model = copy.deepcopy(self.model)
                model["models"][1]["prior_model_weight"] = zero
                self.assert_trellis_error("INVALID_PROBABILITY", lambda: TRELLIS.validate_model_set(model))

        structural = copy.deepcopy(self.model)
        candidate = structural["models"][0]
        candidate["initial"] = [1.0, 0.0]
        candidate["transition"] = [[1.0, 0.0], [0.0, 1.0]]
        candidate["emission"] = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        candidate["parameter_basis"] = "Fixture-declared support exclusions for zero-probability acceptance coverage."
        validated = TRELLIS.validate_model_set(structural)
        self.assertEqual(validated["models"][0]["initial"], [1.0, 0.0])
        self.assertEqual(validated["models"][0]["transition"], [[1.0, 0.0], [0.0, 1.0]])
        self.assertEqual(validated["models"][0]["emission"], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])

        if jsonschema is not None:
            validator = jsonschema.Draft202012Validator(load("model-set.schema.json"))
            rejected = copy.deepcopy(self.model)
            rejected["models"][1]["prior_model_weight"] = 0.0
            with self.assertRaises(jsonschema.ValidationError):
                validator.validate(rejected)
            validator.validate(structural)

    def assert_trellis_error(self, code: str, action) -> None:
        with self.assertRaises(TRELLIS.TrellisError) as raised:
            action()
        self.assertEqual(raised.exception.code, code)

    def revision_two_sequence(self) -> dict:
        sequence = copy.deepcopy(self.sequence)
        sequence["revision"] = 2
        sequence["prior_sequence"] = {
            "sequence_id": sequence["sequence_id"],
            "revision": 1,
            "digest": "b" * 64,
        }
        item = sequence["items"][0]
        item["observation_id"] = "day-1-corrected"
        item["coding_status"] = "corrected"
        item["coding_basis"] = "replacement coding bound to the prior sequence"
        item["supersedes"] = {
            "sequence_id": sequence["sequence_id"],
            "sequence_revision": 1,
            "sequence_digest": "b" * 64,
            "observation_id": "legacy-day-1",
        }
        return sequence

    def test_all_zero_likelihood_requires_reframe_without_world_impossibility_claim(self) -> None:
        model = copy.deepcopy(self.model)
        for candidate in model["models"]:
            candidate["parameter_basis"] = "Fixture-declared support exclusion: symbol 3 is outside this model's support."
            for row in candidate["emission"]:
                row[:] = [0.5, 0.5, 0.0]
        sequence = copy.deepcopy(self.sequence)
        for item in sequence["items"]:
            item["symbol_id"] = "3"
        result = analyze_documents(model, sequence)
        self.assertEqual(result["run_status"], "reframe_required")
        self.assertEqual(result["reframe"]["status"], "required")
        self.assertEqual(result["reframe"]["reasons"], ["all_models_zero_likelihood"])
        self.assertEqual(result["comparison"]["weights_status"], "unsupported")
        self.assertIn("all_models_zero_likelihood", result["comparison"]["reason"])
        self.assertTrue(any("outside supplied model support" in item for item in result["diagnostics"]))
        self.assertTrue(any("not a claim about what can occur in the world" in item for item in result["diagnostics"]))
        for candidate in result["per_model"]:
            self.assertEqual(candidate["inference_status"], "zero_likelihood")
            self.assertEqual(candidate["zero_likelihood_at_sequence_index"], 0)
            self.assertEqual(candidate["sequence_likelihood"], 0.0)
            trigger, *unevaluated = candidate["filtered_state_posteriors"]
            self.assertIsNone(trigger["log_predictive_probability"])
            self.assertEqual(trigger["predictive_probability"], 0.0)
            self.assertFalse(trigger["predictive_probability_underflow"])
            self.assertIsNone(trigger["posterior"])
            for row in unevaluated:
                self.assertIsNone(row["log_predictive_probability"])
                self.assertIsNone(row["predictive_probability"])
                self.assertFalse(row["predictive_probability_underflow"])
                self.assertIsNone(row["posterior"])
            self.assertIsNone(candidate["smoothed_state_posteriors"])
            self.assertIsNone(candidate["viterbi"])
        json.dumps(result, allow_nan=False)

    def test_mid_sequence_support_boundary_distinguishes_trigger_from_unevaluated_tail(self) -> None:
        model = copy.deepcopy(self.model)
        for candidate in model["models"]:
            candidate["parameter_basis"] = "Fixture-declared support exclusion for symbol 1."
            candidate["emission"] = [[0.0, 0.5, 0.5] for _ in candidate["emission"]]
        sequence = copy.deepcopy(self.sequence)
        for item, symbol in zip(sequence["items"], ("3", "1", "3"), strict=True):
            item["symbol_id"] = symbol
        result = analyze_documents(model, sequence)
        for candidate in result["per_model"]:
            self.assertEqual(candidate["zero_likelihood_at_sequence_index"], 1)
            evaluated, trigger, tail = candidate["filtered_state_posteriors"]
            self.assertIsNotNone(evaluated["log_predictive_probability"])
            self.assertIsNotNone(evaluated["predictive_probability"])
            self.assertIsNotNone(evaluated["posterior"])
            self.assertIsNone(trigger["log_predictive_probability"])
            self.assertEqual(trigger["predictive_probability"], 0.0)
            self.assertFalse(trigger["predictive_probability_underflow"])
            self.assertIsNone(trigger["posterior"])
            self.assertIsNone(tail["log_predictive_probability"])
            self.assertIsNone(tail["predictive_probability"])
            self.assertFalse(tail["predictive_probability_underflow"])
            self.assertIsNone(tail["posterior"])

    def test_declared_observation_dependence_refuses_inference(self) -> None:
        sequence = copy.deepcopy(self.sequence)
        sequence["items"][1]["dependence_refs"] = ["observation://day-1"]
        self.assert_trellis_error("UNMODELED_OBSERVATION_DEPENDENCE", lambda: bind(self.model, sequence))

    def test_all_calibrated_absolute_fit_fail_requires_reframe(self) -> None:
        model = copy.deepcopy(self.model)
        model["comparison_contract"]["absolute_fit_policy"]["threshold"] = 0.0
        result = analyze_documents(model, self.sequence)
        self.assertEqual(result["run_status"], "reframe_required")
        self.assertEqual(result["reframe"]["reasons"], ["all_models_failed_calibrated_absolute_fit"])
        self.assertTrue(all(item["absolute_fit"]["status"] == "fail" for item in result["per_model"]))
        self.assertIn("absolute_fit_gate_failed", result["comparison"]["reason"])

    def test_calibration_applicability_binds_encoder_and_step_semantics(self) -> None:
        for field, replacement, expected in (
            ("encoder_digest", "c" * 64, "calibration_encoder_mismatch"),
            ("step_semantics", "one hour per observation", "calibration_step_semantics_mismatch"),
        ):
            with self.subTest(field=field):
                model = copy.deepcopy(self.model)
                for candidate in model["models"]:
                    candidate["calibration_ref"][field] = replacement
                model["comparison_contract"]["absolute_fit_policy"]["calibration_ref"][field] = replacement
                result = analyze_documents(model, self.sequence)
                self.assertEqual(result["comparison"]["weights_status"], "unsupported")
                self.assertIn(expected, result["comparison"]["reason"])
                self.assertTrue(all(item["absolute_fit"]["status"] == "unassessed" for item in result["per_model"]))

    def test_out_of_vocabulary_symbol_is_typed(self) -> None:
        sequence = copy.deepcopy(self.sequence)
        sequence["items"][0]["symbol_id"] = "999"
        self.assert_trellis_error("OOV_SYMBOL", lambda: bind(self.model, sequence))

    def test_known_after_analysis_cutoff_is_typed(self) -> None:
        sequence = copy.deepcopy(self.sequence)
        sequence["items"][0]["known_at"] = "2026-09-03T00:00:00Z"
        self.assert_trellis_error("FUTURE_KNOWLEDGE", lambda: bind(self.model, sequence))

    def test_event_order_is_machine_enforced(self) -> None:
        sequence = copy.deepcopy(self.sequence)
        sequence["items"][0], sequence["items"][1] = sequence["items"][1], sequence["items"][0]
        for index, item in enumerate(sequence["items"]):
            item["sequence_index"] = index
        self.assert_trellis_error("ORDER_MISMATCH", lambda: bind(self.model, sequence))

    def test_nonhistorical_knowledge_order_is_reported_honestly(self) -> None:
        sequence = copy.deepcopy(self.sequence)
        sequence["items"][0]["known_at"] = "2026-09-01T12:00:00Z"
        result = analyze_documents(self.model, sequence)
        self.assertFalse(result["semantic_boundary"]["filtered_is_as_known_then"])
        self.assertEqual(result["semantic_boundary"]["filtered_temporal_mode"], "retrospective_event_order")
        self.assertIn("not a historical as-known-then estimate", result["diagnostics"][0])

    def test_valid_bound_prior_correction_is_accepted_and_disclosed(self) -> None:
        sequence = self.revision_two_sequence()
        result = analyze_documents(self.model, sequence)
        self.assertEqual(result["inputs"]["prior_sequence"], sequence["prior_sequence"])
        self.assertTrue(any("prior document contents were not independently loaded" in item for item in result["diagnostics"]))

    def test_correction_cannot_supersede_current_observation(self) -> None:
        sequence = self.revision_two_sequence()
        sequence["items"][0]["supersedes"]["observation_id"] = "day-2"
        self.assert_trellis_error("DOUBLE_COUNT_RISK", lambda: bind(self.model, sequence))

    def test_correction_binding_must_match_prior_sequence(self) -> None:
        sequence = self.revision_two_sequence()
        sequence["items"][0]["supersedes"]["sequence_digest"] = "c" * 64
        self.assert_trellis_error("BINDING_MISMATCH", lambda: bind(self.model, sequence))

    def test_duplicate_prior_target_is_rejected(self) -> None:
        sequence = self.revision_two_sequence()
        second = sequence["items"][1]
        second["coding_status"] = "corrected"
        second["supersedes"] = copy.deepcopy(sequence["items"][0]["supersedes"])
        self.assert_trellis_error("DUPLICATE_SUPERSESSION", lambda: bind(self.model, sequence))

    def test_revision_one_correction_without_prior_is_rejected(self) -> None:
        sequence = copy.deepcopy(self.sequence)
        item = sequence["items"][0]
        item["coding_status"] = "corrected"
        item["supersedes"] = {
            "sequence_id": sequence["sequence_id"],
            "sequence_revision": 1,
            "sequence_digest": "d" * 64,
            "observation_id": "legacy-day-1",
        }
        self.assert_trellis_error("INVALID_SUPERSESSION", lambda: bind(self.model, sequence))

    def test_observed_item_cannot_carry_supersession(self) -> None:
        sequence = copy.deepcopy(self.sequence)
        sequence["items"][0]["supersedes"] = {
            "sequence_id": sequence["sequence_id"],
            "sequence_revision": 1,
            "sequence_digest": "d" * 64,
            "observation_id": "legacy-day-1",
        }
        self.assert_trellis_error("INVALID_SUPERSESSION", lambda: bind(self.model, sequence))
    def assert_load_error(self, text: str, code: str, *, raw_bytes: bytes | None = None) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            if raw_bytes is None:
                path.write_text(text, encoding="utf-8")
            else:
                path.write_bytes(raw_bytes)
            self.assert_trellis_error(code, lambda: TRELLIS.load_json(path))

    def test_runtime_rejects_boolean_integer_and_probability_aliases(self) -> None:
        model = copy.deepcopy(self.model)
        model["revision"] = True
        self.assert_trellis_error("INVALID_FIELD", lambda: bind(model, self.sequence))

        model = copy.deepcopy(self.model)
        model["models"][0]["assumptions"]["markov_order"] = True
        self.assert_trellis_error("UNSUPPORTED_MODEL", lambda: bind(model, self.sequence))

        model = copy.deepcopy(self.model)
        model["models"][0]["initial"][0] = True
        self.assert_trellis_error("INVALID_PROBABILITY", lambda: TRELLIS.validate_model_set(model))

        sequence = copy.deepcopy(self.sequence)
        sequence["items"][0]["sequence_index"] = False
        self.assert_trellis_error("INVALID_FIELD", lambda: bind(self.model, sequence))

    def test_runtime_rejects_unknown_fields_at_every_document_boundary(self) -> None:
        model = copy.deepcopy(self.model)
        model["surprise"] = "not in contract"
        self.assert_trellis_error("UNKNOWN_FIELD", lambda: bind(model, self.sequence))

        model = copy.deepcopy(self.model)
        model["models"][0]["surprise"] = "not in contract"
        self.assert_trellis_error("UNKNOWN_FIELD", lambda: bind(model, self.sequence))

        sequence = copy.deepcopy(self.sequence)
        sequence["items"][0]["surprise"] = "not in contract"
        self.assert_trellis_error("UNKNOWN_FIELD", lambda: bind(self.model, sequence))

    def test_nonfinite_probability_is_typed(self) -> None:
        model = copy.deepcopy(self.model)
        model["models"][0]["initial"][0] = math.nan
        self.assert_trellis_error("INVALID_PROBABILITY", lambda: TRELLIS.validate_model_set(model))

    def test_json_loader_rejects_duplicate_nonfinite_underflow_and_huge_tokens(self) -> None:
        self.assert_load_error('{"x":1,"x":2}', "DUPLICATE_KEY")
        self.assert_load_error('{"x":NaN}', "NON_FINITE_JSON")
        self.assert_load_error('{"x":1e-400}', "NUMERIC_UNDERFLOW")
        self.assert_load_error('{"x":' + "9" * 129 + '}', "NUMERIC_RANGE")
        self.assert_load_error("", "INVALID_UTF8", raw_bytes=b"\xff\xfe")

    def test_surrogate_and_noncanonical_values_are_contained(self) -> None:
        model = copy.deepcopy(self.model)
        model["question"] = chr(0xD800)
        self.assert_trellis_error("INVALID_UNICODE", lambda: TRELLIS.validate_model_set(model))
        self.assert_trellis_error("NON_CANONICAL_VALUE", lambda: TRELLIS.digest({"bad": math.nan}))

    def test_extreme_joint_probability_survives_in_log_domain(self) -> None:
        model = copy.deepcopy(self.model)
        model["models"] = [model["models"][0]]
        candidate = model["models"][0]
        candidate["prior_model_weight"] = 1.0
        candidate["initial"] = [1e-200, 1.0]
        candidate["emission"] = [[1.0, 0.0, 1e-200], [1.0, 0.0, 0.0]]
        sequence = copy.deepcopy(self.sequence)
        sequence["items"] = [sequence["items"][0]]
        result = analyze_documents(model, sequence)
        candidate_result = result["per_model"][0]
        self.assertEqual(candidate_result["inference_status"], "completed")
        self.assertAlmostEqual(candidate_result["log_sequence_likelihood"], math.log(1e-200) * 2, places=12)
        self.assertIsNone(candidate_result["sequence_likelihood"])
        self.assertTrue(candidate_result["sequence_likelihood_underflow"])
        self.assertIsNotNone(candidate_result["filtered_state_posteriors"][0]["posterior"])
        json.dumps(result, allow_nan=False)

    def test_scaled_backward_subnormal_fixture_is_finite(self) -> None:
        model = copy.deepcopy(self.model)
        model["models"] = [model["models"][0]]
        candidate = model["models"][0]
        candidate["prior_model_weight"] = 1.0
        candidate["initial"] = [1.0, 0.0]
        candidate["transition"] = [[1.0, 0.0], [0.0, 1.0]]
        candidate["emission"] = [[TRELLIS.MIN_POSITIVE_FLOAT, 1.0, 0.0], [1.0, 0.0, 0.0]]
        sequence = copy.deepcopy(self.sequence)
        sequence["items"] = sequence["items"][:2]
        sequence["items"][0]["symbol_id"] = "2"
        sequence["items"][1]["symbol_id"] = "1"
        result = analyze_documents(model, sequence)
        candidate_result = result["per_model"][0]
        self.assertEqual(candidate_result["inference_status"], "completed")
        self.assertTrue(math.isfinite(candidate_result["log_sequence_likelihood"]))
        for row in candidate_result["smoothed_state_posteriors"]:
            self.assertTrue(all(math.isfinite(value) for value in row["posterior"]))
            self.assertAlmostEqual(math.fsum(row["posterior"]), 1.0, places=15)
        json.dumps(result, allow_nan=False)

    def test_long_sequence_keeps_finite_log_likelihood(self) -> None:
        model_set = TRELLIS.validate_model_set(copy.deepcopy(self.model))
        result = TRELLIS.forward(model_set["models"][0], [2] * 10_000)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(math.isfinite(result["log_likelihood"]))
        scalar, underflow = TRELLIS._finite_exp(result["log_likelihood"])
        self.assertIsNone(scalar)
        self.assertTrue(underflow)

    @staticmethod
    def fake_resource_request(model_count: int, state_count: int, observation_count: int) -> tuple[dict, dict]:
        states = [f"s-{index}" for index in range(state_count)]
        model_set = {"models": [{"state_order": states} for _ in range(model_count)]}
        sequence = {
            "symbol_indices": [0] * observation_count,
            "observation_ids": [f"o-{index:05d}" for index in range(observation_count)],
        }
        return model_set, sequence

    def test_resource_envelope_rejects_excess_work(self) -> None:
        model_set, sequence = self.fake_resource_request(1, 64, 3_000)
        with self.assertRaises(TRELLIS.TrellisError) as raised:
            TRELLIS.estimate_resources(model_set, sequence, decode=False, smoothing=False)
        self.assertEqual(raised.exception.code, "RESOURCE_LIMIT")
        self.assertIn("work_units=", raised.exception.message)

    def test_resource_envelope_rejects_excess_posterior_cells(self) -> None:
        model_set, sequence = self.fake_resource_request(32, 1, 10_000)
        with self.assertRaises(TRELLIS.TrellisError) as raised:
            TRELLIS.estimate_resources(model_set, sequence, decode=False, smoothing=True)
        self.assertEqual(raised.exception.code, "RESOURCE_LIMIT")
        self.assertIn("posterior_cells=640000>500000", raised.exception.message)

    def test_resource_envelope_rejects_excess_estimated_output(self) -> None:
        model_set, sequence = self.fake_resource_request(32, 1, 10_000)
        with self.assertRaises(TRELLIS.TrellisError) as raised:
            TRELLIS.estimate_resources(model_set, sequence, decode=False, smoothing=False)
        self.assertEqual(raised.exception.code, "RESOURCE_LIMIT")
        self.assertIn("estimated_output_bytes=", raised.exception.message)

    def test_resource_receipt_declares_hard_caps(self) -> None:
        result = analyze_documents(self.model, self.sequence)
        self.assertEqual(
            result["resource_estimate"]["limits"],
            {"max_work_units": 10_000_000, "max_posterior_cells": 500_000, "max_output_bytes": 32 * 1024 * 1024},
        )

    def test_runtime_source_has_no_network_or_write_surface(self) -> None:
        import ast

        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        forbidden_imports = {"requests", "urllib", "http", "socket", "ftplib", "subprocess", "shutil", "tempfile"}
        imported_roots: set[str] = set()
        write_calls: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"write_text", "write_bytes", "open", "touch", "mkdir", "unlink", "replace", "rename"}:
                    write_calls.append(node.func.attr)
        self.assertFalse(imported_roots & forbidden_imports)
        self.assertEqual(write_calls, [])
    def test_run_and_validation_ids_cover_full_receipt_body(self) -> None:
        import hashlib

        model_set, sequence = bind(self.model, self.sequence)
        run = TRELLIS.analyze(model_set, sequence, decode=True, smoothing=True)
        run_body = copy.deepcopy(run)
        run_id = run_body.pop("run_id")
        self.assertEqual(run_id, "sha256:" + TRELLIS.digest(run_body))

        validation = TRELLIS.validation_receipt(model_set, sequence)
        validation_body = copy.deepcopy(validation)
        validation_id = validation_body.pop("validation_id")
        self.assertEqual(validation_id, "sha256:" + TRELLIS.digest(validation_body))

        error = TRELLIS.error_receipt(TRELLIS.TrellisError("TEST_ERROR", "deliberate"))
        error_body = copy.deepcopy(error)
        error_id = error_body.pop("error_id")
        self.assertEqual(error_id, "sha256:" + TRELLIS.digest(error_body))

        expected_artifact = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
        self.assertEqual(run["engine"]["artifact_sha256"], expected_artifact)
        self.assertEqual(run["engine"]["schema_versions"]["receipt_envelope"], TRELLIS.RECEIPT_ENVELOPE)
        self.assertEqual(run["engine"]["numeric_runtime"]["python_version"], ".".join(str(item) for item in sys.version_info[:3]))

    def test_model_artifact_and_effective_model_provenance_are_distinct_and_exact(self) -> None:
        model_set, sequence = bind(self.model, self.sequence)
        result = TRELLIS.analyze(model_set, sequence, decode=False, smoothing=False)
        source_model = model_set["models"][0]
        emitted = result["per_model"][0]
        self.assertEqual(emitted["model_artifact_digest"], TRELLIS.digest(source_model["raw"]))
        self.assertEqual(
            emitted["effective_model_digest"],
            TRELLIS.digest({"model": source_model["raw"], "observation_contract": model_set["document"]["observation_contract"]}),
        )
        self.assertEqual(emitted["observation_contract_digest"], model_set["observation_contract_digest"])

    def test_same_runtime_and_inputs_produce_identical_receipt(self) -> None:
        first = analyze_documents(self.model, self.sequence)
        second = analyze_documents(self.model, self.sequence)
        self.assertEqual(first, second)

    def test_semantic_boundary_disclaims_truth_confidence_authority_and_persistence(self) -> None:
        boundary = analyze_documents(self.model, self.sequence)["semantic_boundary"]
        self.assertTrue(boundary["epistemic_model_agnosticism"])
        for key in (
            "claim_confidence", "truth_certification", "source_confidence_modified",
            "decision_authority", "persistence_performed",
        ):
            self.assertFalse(boundary[key])
        self.assertEqual(boundary["authority_effect"], "none")

    @unittest.skipIf(jsonschema is None, "jsonschema is an optional verification dependency")
    def test_all_schemas_are_valid_draft_2020_12_and_examples_conform(self) -> None:
        schemas = {
            name: load(name)
            for name in (
                "model-set.schema.json",
                "observation-sequence.schema.json",
                "inference-run.schema.json",
            )
        }
        for name, schema in schemas.items():
            with self.subTest(schema=name):
                jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schemas["model-set.schema.json"]).validate(self.model)
        jsonschema.Draft202012Validator(schemas["observation-sequence.schema.json"]).validate(self.sequence)

    @unittest.skipIf(jsonschema is None, "jsonschema is an optional verification dependency")
    def test_receipt_envelope_accepts_current_and_genuine_historical_receipts(self) -> None:
        schema = load("inference-run.schema.json")
        validator = jsonschema.Draft202012Validator(schema)
        model_set, sequence = bind(self.model, self.sequence)
        historical_names = (
            "run-independent.json",
            "run-dependent.json",
            "validation-independent.json",
            "validation-dependent.json",
        )
        receipts = (
            TRELLIS.analyze(model_set, sequence, decode=True, smoothing=True),
            TRELLIS.validation_receipt(model_set, sequence),
            TRELLIS.error_receipt(TRELLIS.TrellisError("TEST_ERROR", "deliberate")),
            *(json.loads((HISTORICAL_FIXTURES / name).read_text(encoding="utf-8")) for name in historical_names),
        )
        for receipt in receipts:
            with self.subTest(contract=receipt["contract"], engine=receipt["engine"]["engine_version"]):
                validator.validate(receipt)

        manifest = json.loads((HISTORICAL_FIXTURES / "fixture-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["source_commit"], "0c88c3c9ab373b5b291321ede036a5ab74483298")
        for name, record in manifest["files"].items():
            payload = (HISTORICAL_FIXTURES / name).read_bytes()
            self.assertEqual(len(payload), record["bytes"])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), record["sha256"])

        expected_artifact = hashlib.sha256(
            (HISTORICAL_FIXTURES / "model_agnosticism_trellis-1.0.0.py").read_bytes()
        ).hexdigest()
        for name in historical_names:
            receipt = json.loads((HISTORICAL_FIXTURES / name).read_text(encoding="utf-8"))
            self.assertEqual(receipt["engine"]["engine_version"], "1.0.0")
            self.assertEqual(receipt["engine"]["artifact_sha256"], expected_artifact)
            id_field = "run_id" if receipt["contract"] == TRELLIS.RUN_CONTRACT else "validation_id"
            body = copy.deepcopy(receipt)
            identifier = body.pop(id_field)
            self.assertEqual(identifier, "sha256:" + TRELLIS.digest(body))

    def test_engine_100_dependent_receipt_is_historical_not_supported_evidence(self) -> None:
        dependent_sequence = json.loads(
            (HISTORICAL_FIXTURES / "sequence-dependent.json").read_text(encoding="utf-8")
        )
        dependent_run = json.loads(
            (HISTORICAL_FIXTURES / "run-dependent.json").read_text(encoding="utf-8")
        )
        independent_sequence = json.loads(
            (HISTORICAL_FIXTURES / "sequence-independent.json").read_text(encoding="utf-8")
        )
        self.assertTrue(any(item["dependence_refs"] for item in dependent_sequence["items"]))
        self.assertTrue(all(not item["dependence_refs"] for item in independent_sequence["items"]))
        self.assertEqual(dependent_run["inputs"]["sequence_digest"], TRELLIS.digest(dependent_sequence))
        self.assertEqual(dependent_run["comparison"]["weights_status"], "computed")
        self.assertTrue(dependent_run["comparison"]["relative_model_weights"])
        self.assertIn(
            "observation_dependence_declared; HMM likelihood does not correct it automatically",
            dependent_run["diagnostics"],
        )
        doctrine = (ROOT / "plugins" / "nova-the-optimal-ai" / "skills" / "nova" / "references" / "mind" / "model-agnosticism.md").read_text(encoding="utf-8")
        self.assertIn("Engine 1.0.0 did not enforce that boundary", doctrine)
        self.assertIn("mark the probabilistic result `unsupported/reframe`", doctrine)
        observation_schema = load("observation-sequence.schema.json")
        dependence_description = observation_schema["properties"]["items"]["items"]["properties"]["dependence_refs"]["description"]
        self.assertIn("Engine 1.0.1 refuses inference", dependence_description)
        self.assertIn("Historical engine 1.0.0 accepted the disclosure as warning-only", dependence_description)
    @unittest.skipIf(jsonschema is None, "jsonschema is an optional verification dependency")
    def test_receipt_envelope_is_strict(self) -> None:
        schema = load("inference-run.schema.json")
        receipt = analyze_documents(self.model, self.sequence)
        receipt["undeclared"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(receipt)

    def test_cli_dependence_refusal_is_typed_deterministic_and_pre_inference(self) -> None:
        model, sequence = bound_documents(self.model, self.sequence)
        sequence["items"][1]["dependence_refs"] = ["observation://day-1"]
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory)
            model_path = cwd / "model.json"
            sequence_path = cwd / "sequence.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")
            sequence_path.write_text(json.dumps(sequence), encoding="utf-8")
            receipts = []
            for command in ("validate", "analyze", "analyze"):
                completed = subprocess.run(
                    [sys.executable, str(SCRIPT), command, str(model_path), str(sequence_path)],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 2, completed.stderr)
                self.assertNotIn("Traceback", completed.stdout + completed.stderr)
                receipt = json.loads(completed.stdout)
                self.assertEqual(receipt["contract"], TRELLIS.ERROR_CONTRACT)
                self.assertEqual(receipt["code"], "UNMODELED_OBSERVATION_DEPENDENCE")
                self.assertNotIn("observation://day-1", receipt["message"])
                for forbidden in ("resource_estimate", "per_model", "comparison", "reframe", "diagnostics"):
                    self.assertNotIn(forbidden, receipt)
                receipts.append(receipt)
            self.assertEqual(receipts[1]["error_id"], receipts[2]["error_id"])
            if jsonschema is not None:
                validator = jsonschema.Draft202012Validator(load("inference-run.schema.json"))
                for receipt in receipts:
                    validator.validate(receipt)

    def test_cli_error_is_typed_json_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bad_model = Path(directory) / "bad-model.json"
            bad_model.write_text('{"contract":"x","contract":"y"}', encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "analyze", str(bad_model), str(SOURCE / "example-observation-sequence.json")],
                cwd=directory,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 2)
        self.assertNotIn("Traceback", completed.stdout + completed.stderr)
        receipt = json.loads(completed.stdout)
        self.assertEqual(receipt["contract"], TRELLIS.ERROR_CONTRACT)
        self.assertEqual(receipt["code"], "DUPLICATE_KEY")
        if jsonschema is not None:
            jsonschema.Draft202012Validator(load("inference-run.schema.json")).validate(receipt)

    def test_cli_analysis_writes_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory)
            before = list(cwd.iterdir())
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "analyze",
                    str(SOURCE / "example-model-set.json"),
                    str(SOURCE / "example-observation-sequence.json"),
                    "--decode",
                    "--smooth",
                ],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
            )
            after = list(cwd.iterdir())
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(before, after)
        receipt = json.loads(completed.stdout)
        self.assertEqual(receipt["contract"], TRELLIS.RUN_CONTRACT)
        self.assertFalse(receipt["semantic_boundary"]["persistence_performed"])

    def test_schema_and_runtime_share_digest_and_nonblank_string_rules(self) -> None:
        uppercase = copy.deepcopy(self.model)
        uppercase["observation_contract"]["encoder_digest"] = "A" * 64
        self.assert_trellis_error("INVALID_DIGEST", lambda: TRELLIS.validate_model_set(uppercase))

        whitespace = copy.deepcopy(self.model)
        whitespace["question"] = "   "
        self.assert_trellis_error("INVALID_FIELD", lambda: TRELLIS.validate_model_set(whitespace))

        malformed_time = copy.deepcopy(self.sequence)
        malformed_time["analysis_as_of"] = "2026-09-02T00:00:00z"
        self.assert_trellis_error("INVALID_TIME", lambda: bind(self.model, malformed_time))
        controlled_id = copy.deepcopy(self.model)
        controlled_id["model_set_id"] = "bad" + chr(1) + "id"
        self.assert_trellis_error("INVALID_FIELD", lambda: TRELLIS.validate_model_set(controlled_id))

        if jsonschema is not None:
            validator = jsonschema.Draft202012Validator(load("model-set.schema.json"))
            for invalid in (uppercase, whitespace, controlled_id):
                with self.assertRaises(jsonschema.ValidationError):
                    validator.validate(invalid)
            sequence_validator = jsonschema.Draft202012Validator(load("observation-sequence.schema.json"))
            _, bound_malformed_time = bind(self.model, self.sequence)
            schema_sequence = copy.deepcopy(bound_malformed_time["document"])
            schema_sequence["analysis_as_of"] = malformed_time["analysis_as_of"]
            with self.assertRaises(jsonschema.ValidationError):
                sequence_validator.validate(schema_sequence)


if __name__ == "__main__":
    unittest.main()
