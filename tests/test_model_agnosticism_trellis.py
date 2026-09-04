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
from unittest import mock
from pathlib import Path

try:
    import jsonschema
except ImportError:  # Optional verification dependency; calculator runtime remains stdlib-only.
    jsonschema = None

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_FIXTURES = ROOT / "tests" / "fixtures" / "model-agnosticism-engine-1.0.0"
HISTORICAL_101_FIXTURES = ROOT / "tests" / "fixtures" / "model-agnosticism-engine-1.0.1"


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
    sequence_document["step_contract"] = copy.deepcopy(encoder["step_contract"])
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

    def evidence_model(self) -> dict:
        model = copy.deepcopy(self.model)
        model["epistemic_lane"] = "evidence_update"
        model["question"] = "Which predeclared candidate process better predicts the encoded observations?"
        model["scope"] = "Synthetic evidence-lane regression fixture with inputs declared before observations were reviewed."
        model["candidate_selection"] = {
            "status": "fixed_before_sequence",
            "basis": "Candidate family and membership were declared before observations were reviewed.",
            "source_refs": ["protocol://candidate-set/predeclared-v1"],
        }
        model["stopping_contract"] = {
            "status": "fixed_before_sequence",
            "basis": "A three-observation horizon was declared before observations were reviewed.",
            "maximum_observations": 3,
        }
        model["comparison_contract"]["prior_basis"] = (
            "Equal priors were elicited before observations were reviewed."
        )
        model["comparison_contract"]["calibration_basis"] = (
            "Threshold declaration derived from independent pre-sequence calibration data."
        )
        model["observation_contract"]["mapping_provenance"] = {
            "kind": "expert_elicited",
            "fixed_before_sequence": True,
            "basis": "The observation mapping was declared before observations were reviewed.",
            "source_refs": ["protocol://observation-mapping/predeclared-v1"],
        }
        for candidate in model["models"]:
            candidate["parameter_provenance"] = {
                "kind": "estimated_independent_data",
                "fixed_before_sequence": True,
                "basis": "Parameters were estimated from independent pre-sequence data.",
                "source_refs": ["dataset://independent-training/predeclared-v1"],
            }
            candidate["prior_provenance"] = {
                "kind": "expert_elicited",
                "fixed_before_sequence": True,
                "basis": "Model prior was elicited before observations were reviewed.",
                "source_refs": ["protocol://model-priors/predeclared-v1"],
            }
        calibration = model["comparison_contract"]["absolute_fit_policy"]["calibration_ref"]
        calibration["provenance"] = {
            "kind": "estimated_independent_data",
            "fixed_before_sequence": True,
            "basis": "Threshold calibration was declared from independent pre-sequence data.",
            "source_refs": ["dataset://calibration/predeclared-v1"],
        }
        calibration["calibration_target_digest"] = "0" * 64
        calibration["calibration_target_digest"] = TRELLIS.validate_model_set(model)[
            "calibration_target_digest"
        ]
        self.assertNotIn("scenario", json.dumps(model).lower())
        self.assertNotIn("stipulated", json.dumps(model).lower())
        return model

    def rebind_calibration_target(self, model: dict) -> dict:
        calibration = model["comparison_contract"]["absolute_fit_policy"]["calibration_ref"]
        calibration["calibration_target_digest"] = "0" * 64
        calibration["calibration_target_digest"] = TRELLIS.validate_model_set(model)[
            "calibration_target_digest"
        ]
        return model

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

    def test_missing_or_mismatched_calibration_downgrades_to_diagnostic_only(self) -> None:
        missing = self.evidence_model()
        missing["comparison_contract"]["absolute_fit_policy"] = None
        result = analyze_documents(missing, self.sequence)
        self.assertEqual(result["comparison"]["weights_status"], "computed")
        self.assertEqual(result["comparison"]["effective_interpretation"], "diagnostic_only")
        self.assertIn("absolute_fit_policy_missing", result["comparison"]["evidence_gate"]["reasons"])
        self.assertEqual(result["per_model"][0]["absolute_fit"]["status"], "unassessed")

        mismatched = self.evidence_model()
        mismatched["comparison_contract"]["absolute_fit_policy"]["calibration_ref"][
            "calibration_target_digest"
        ] = "a" * 64
        result = analyze_documents(mismatched, self.sequence)
        self.assertEqual(result["comparison"]["weights_status"], "computed")
        self.assertEqual(result["comparison"]["weight_interpretation"], "diagnostic_only")
        self.assertIn("calibration_target_mismatch", result["comparison"]["evidence_gate"]["reasons"])
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
        model = self.evidence_model()
        model["comparison_contract"]["absolute_fit_policy"]["threshold"] = 0.0
        result = analyze_documents(model, self.sequence)
        self.assertEqual(result["run_status"], "reframe_required")
        self.assertEqual(result["reframe"]["reasons"], ["all_models_failed_calibrated_absolute_fit"])
        self.assertTrue(all(item["absolute_fit"]["status"] == "fail" for item in result["per_model"]))
        self.assertIn("absolute_fit_gate_failed", result["comparison"]["evidence_gate"]["reasons"])
        self.assertEqual(result["comparison"]["effective_interpretation"], "diagnostic_only")

    def test_calibration_target_binds_candidate_hmm_observation_stop_and_horizon(self) -> None:
        mutations = (
            lambda model: model["models"][0].update(model_id="changed-model-id"),
            lambda model: model["models"][0].update(model_version="1.1.1"),
            lambda model: model["models"][0].update(comparison_unit_id="changed-unit"),
            lambda model: model["models"][0]["transition"].__setitem__(0, [0.7, 0.3]),
            lambda model: model["observation_contract"]["mapping_provenance"].update(
                basis="A different predeclared mapping basis."
            ),
            lambda model: model["observation_contract"].update(step_semantics="one declared event per step"),
            lambda model: model["stopping_contract"].update(basis="A different predeclared stop basis."),
            lambda model: model["comparison_contract"]["absolute_fit_policy"]["calibration_ref"].update(maximum_observations=4),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                model = self.evidence_model()
                mutate(model)
                result = analyze_documents(model, self.sequence)
                self.assertEqual(result["comparison"]["weights_status"], "computed")
                self.assertEqual(result["comparison"]["effective_interpretation"], "diagnostic_only")
                self.assertIn("calibration_target_mismatch", result["comparison"]["evidence_gate"]["reasons"])
                self.assertTrue(all(item["absolute_fit"]["status"] == "unassessed" for item in result["per_model"]))

        unsupported_family = self.evidence_model()
        unsupported_family["models"][0]["family"] = "different_hmm_family"
        self.assert_trellis_error(
            "UNSUPPORTED_MODEL",
            lambda: TRELLIS.validate_model_set(unsupported_family),
        )

        reordered = self.evidence_model()
        expected_target = reordered["comparison_contract"]["absolute_fit_policy"][
            "calibration_ref"
        ]["calibration_target_digest"]
        reordered["models"].reverse()
        validated = TRELLIS.validate_model_set(reordered)
        self.assertEqual(validated["calibration_target_digest"], expected_target)

    def test_calibration_horizon_bounds_gate_fit_and_evidence_interpretation(self) -> None:
        at_bound = analyze_documents(self.evidence_model(), self.sequence)
        self.assertTrue(all(item["absolute_fit"]["status"] == "pass" for item in at_bound["per_model"]))
        self.assertTrue(all(item["absolute_fit"]["calibration_truth_validated"] is False for item in at_bound["per_model"]))

        for minimum, maximum, reason in (
            (4, 4, "calibration_horizon_below_minimum"),
            (1, 2, "calibration_horizon_above_maximum"),
        ):
            with self.subTest(reason=reason):
                model = self.evidence_model()
                calibration = model["comparison_contract"]["absolute_fit_policy"]["calibration_ref"]
                calibration["minimum_observations"] = minimum
                calibration["maximum_observations"] = maximum
                self.rebind_calibration_target(model)
                result = analyze_documents(model, self.sequence)
                self.assertTrue(all(item["absolute_fit"]["status"] == "unassessed" for item in result["per_model"]))
                self.assertIn(reason, result["comparison"]["evidence_gate"]["reasons"])
                self.assertEqual(result["comparison"]["effective_interpretation"], "diagnostic_only")

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

    def test_equal_batch_knowledge_times_are_retrospective_not_as_known(self) -> None:
        sequence = copy.deepcopy(self.sequence)
        sequence["items"][0]["known_at"] = sequence["items"][1]["known_at"]
        result = analyze_documents(self.model, sequence)
        self.assertFalse(result["semantic_boundary"]["filtered_is_as_known_then"])
        self.assertEqual(
            result["semantic_boundary"]["filtered_temporal_mode"],
            "retrospective_event_order",
        )

    def test_rfc3339_is_microsecond_bounded_and_utc_overflow_is_typed(self) -> None:
        for timestamp in (
            "2026-09-01T00:00:00.1Z",
            "2026-09-01T00:00:00.123456+00:00",
        ):
            with self.subTest(timestamp=timestamp):
                self.assertIsNotNone(TRELLIS._parse_time(timestamp, "timestamp"))
        self.assert_trellis_error(
            "INVALID_TIME",
            lambda: TRELLIS._parse_time("2026-09-01T00:00:00.1234567Z", "timestamp"),
        )
        self.assert_trellis_error(
            "INVALID_TIME",
            lambda: TRELLIS._parse_time("0001-01-01T00:00:00+14:00", "timestamp"),
        )

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
        sequence["revision"] = 1
        sequence["prior_sequence"] = None
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

    def test_programmatic_error_receipts_bound_and_sanitize_hostile_values(self) -> None:
        hostile_errors = (
            TRELLIS.TrellisError("X" * 512, "m" * (TRELLIS.MAX_ERROR_MESSAGE_CHARS + 10_000)),
            TRELLIS.TrellisError(
                "BAD\nCODE",
                "control:" + chr(0) + chr(0x1F) + chr(0x7F) + " surrogate:" + chr(0xD800),
            ),
        )
        validator = (
            jsonschema.Draft202012Validator(load("inference-run.schema.json"))
            if jsonschema is not None
            else None
        )
        for error in hostile_errors:
            with self.subTest(code=error.code):
                receipt = TRELLIS.error_receipt(error)
                self.assertLessEqual(len(receipt["code"]), 128)
                self.assertLessEqual(len(receipt["message"]), TRELLIS.MAX_ERROR_MESSAGE_CHARS)
                self.assertTrue(receipt["message"].strip())
                self.assertFalse(
                    any(
                        ord(character) < 0x20
                        or ord(character) == 0x7F
                        or 0xD800 <= ord(character) <= 0xDFFF
                        for character in receipt["message"]
                    )
                )
                serialized = TRELLIS._serialize_output(receipt)
                self.assertEqual(json.loads(serialized), receipt)
                if validator is not None:
                    validator.validate(receipt)

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

    def test_probability_one_roundoff_cannot_create_negative_surprisal(self) -> None:
        model = copy.deepcopy(self.model)
        model["models"] = [model["models"][0]]
        candidate = model["models"][0]
        candidate["prior_model_weight"] = 1.0
        candidate["initial"] = [0.698438098155856, 0.301561901844144]
        candidate["emission"] = [[0.0, 0.0, 1.0], [0.0, 0.0, 1.0]]
        sequence = copy.deepcopy(self.sequence)
        sequence["items"] = [sequence["items"][0]]

        receipt = analyze_documents(model, sequence)
        result = receipt["per_model"][0]
        self.assertEqual(result["log_sequence_likelihood"], 0.0)
        self.assertEqual(result["mean_predictive_surprisal"], 0.0)
        self.assertEqual(result["filtered_state_posteriors"][0]["log_predictive_probability"], 0.0)
        self.assertEqual(result["sequence_likelihood"], 1.0)
        if jsonschema is not None:
            jsonschema.Draft202012Validator(load("inference-run.schema.json")).validate(receipt)

    def test_bounded_log_probability_enforces_ceiling_and_positive_zero(self) -> None:
        tolerance = TRELLIS.LOG_PROBABILITY_CEILING_TOLERANCE
        self.assertLess(TRELLIS._bounded_log_probability(math.nextafter(0.0, -math.inf)), 0.0)
        self.assertEqual(TRELLIS._bounded_log_probability(math.nextafter(tolerance, 0.0)), 0.0)
        self.assertEqual(TRELLIS._bounded_log_probability(tolerance), 0.0)
        signed_zero = TRELLIS._bounded_log_probability(-0.0)
        self.assertEqual(signed_zero, 0.0)
        self.assertEqual(math.copysign(1.0, signed_zero), 1.0)
        self.assert_trellis_error(
            "NUMERIC_FAILURE",
            lambda: TRELLIS._bounded_log_probability(math.nextafter(tolerance, math.inf)),
        )

    def test_state_and_model_mass_underflow_remains_distinct_from_structural_zero(self) -> None:
        finite = TRELLIS._posterior_from_logs([-1000.0, 0.0])
        self.assertEqual(finite["posterior"], [0.0, 1.0])
        self.assertEqual(finite["posterior_log_probabilities"], [-1000.0, 0.0])
        self.assertEqual(finite["posterior_finite_log_underflow_state_indices"], [0])
        self.assertEqual(finite["posterior_structural_zero_state_indices"], [])

        structural = TRELLIS._posterior_from_logs([-math.inf, 0.0])
        self.assertEqual(structural["posterior"], [0.0, 1.0])
        self.assertEqual(structural["posterior_log_probabilities"], [None, 0.0])
        self.assertEqual(structural["posterior_finite_log_underflow_state_indices"], [])
        self.assertEqual(structural["posterior_structural_zero_state_indices"], [0])

        model_set, _ = bind(self.evidence_model(), self.sequence)
        fits = [{"status": "pass"}, {"status": "pass"}]
        underflow = TRELLIS._comparison(
            model_set,
            [{"log_likelihood": -1000.0}, {"log_likelihood": 0.0}],
            fits,
        )
        first = underflow["relative_model_weights"][0]
        self.assertEqual(first["weight_status"], "underflow")
        self.assertIsNone(first["weight"])
        self.assertTrue(math.isfinite(first["log_weight"]))
        self.assertFalse(underflow["linear_weights_complete"])

        exact = TRELLIS._comparison(
            model_set,
            [{"log_likelihood": -math.inf}, {"log_likelihood": 0.0}],
            fits,
        )
        first = exact["relative_model_weights"][0]
        self.assertEqual(first["weight_status"], "exact_zero")
        self.assertEqual(first["weight"], 0.0)
        self.assertIsNone(first["log_weight"])
        self.assertTrue(exact["linear_weights_complete"])

    @staticmethod
    def fake_resource_request(model_count: int, state_count: int, observation_count: int) -> tuple[dict, dict]:
        states = [f"s-{index}" for index in range(state_count)]
        model_set = {
            "models": [{"state_order": states} for _ in range(model_count)],
            "symbol_ids": ["symbol"],
        }
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
        actual = len(TRELLIS._serialize_output(result).encode("utf-8"))
        self.assertLessEqual(actual, result["resource_estimate"]["estimated_output_bytes"])

    def test_multibyte_symbol_order_amplification_is_conservatively_estimated(self) -> None:
        model = copy.deepcopy(self.model)
        symbol_ids = [
            ("💠" * 240) + f'\\"-{index:03d}'
            for index in range(64)
        ]
        model["observation_contract"]["symbols"] = [
            {"symbol_id": symbol_id, "definition": "fixture symbol", "coding_rule": "exact fixture id"}
            for symbol_id in symbol_ids
        ]
        model["stopping_contract"] = {
            "status": "scenario_only",
            "basis": "The fixture contains one observation.",
            "maximum_observations": 1,
        }
        model["comparison_contract"]["absolute_fit_policy"] = None
        model["comparison_contract"]["calibration_basis"] = None
        template = copy.deepcopy(model["models"][0])
        candidates = []
        for index in range(8):
            candidate = copy.deepcopy(template)
            candidate["model_id"] = f"multibyte-model-{index}"
            candidate["comparison_unit_id"] = f"multibyte-unit-{index}"
            candidate["prior_model_weight"] = 0.125
            candidate["state_order"] = ["s"]
            candidate["states"] = [{"state_id": "s", "meaning": "fixture state"}]
            candidate["initial"] = [1.0]
            candidate["transition"] = [[1.0]]
            emission = [0.0] * len(symbol_ids)
            emission[index] = 1.0
            candidate["emission"] = [emission]
            candidates.append(candidate)
        model["models"] = candidates
        sequence = copy.deepcopy(self.sequence)
        sequence["items"] = sequence["items"][:1]
        sequence["items"][0]["symbol_id"] = symbol_ids[0]

        result = analyze_documents(model, sequence, decode=False, smoothing=False)
        actual = len(TRELLIS._serialize_output(result).encode("utf-8"))
        estimated = result["resource_estimate"]["estimated_output_bytes"]
        symbol_charge = len(candidates) * sum(
            len(TRELLIS.canonical_bytes(symbol_id)) + 16
            for symbol_id in symbol_ids
        )
        self.assertGreaterEqual(estimated, symbol_charge)
        self.assertLessEqual(actual, estimated)

    def test_amplified_symbol_order_is_refused_before_inference(self) -> None:
        model_set, sequence = self.fake_resource_request(32, 1, 1_500)
        model_set["symbol_ids"] = [
            ("💠" * 252) + f"-{index:03d}"
            for index in range(512)
        ]
        with mock.patch.object(
            TRELLIS,
            "forward",
            side_effect=AssertionError("inference must not begin after a failed preflight"),
        ) as forward:
            self.assert_trellis_error(
                "RESOURCE_LIMIT",
                lambda: TRELLIS.analyze(model_set, sequence, decode=False, smoothing=False),
            )
        forward.assert_not_called()

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
        self.assertEqual(emitted["model_document_digest"], TRELLIS.digest(source_model["raw"]))
        expected_kernel = TRELLIS.digest(
            {
                "family": source_model["raw"]["family"],
                "observation_contract_digest": model_set["observation_contract_digest"],
                "matrix_layout": source_model["matrix_layout"],
                "initial": source_model["initial"],
                "transition": source_model["transition"],
                "emission": source_model["emission"],
                "normalization_policy": TRELLIS.NORMALIZATION_POLICY,
            }
        )
        self.assertEqual(emitted["predictive_kernel_digest"], expected_kernel)
        self.assertEqual(
            emitted["inference_model_digest"],
            TRELLIS.digest(
                {
                    "family": source_model["raw"]["family"],
                    "observation_contract_digest": model_set["observation_contract_digest"],
                    "state_order": source_model["state_order"],
                    "symbol_order": model_set["symbol_ids"],
                    "matrix_layout": source_model["matrix_layout"],
                    "normalization_policy": TRELLIS.NORMALIZATION_POLICY,
                    "normalized_initial": source_model["initial"],
                    "normalized_transition": source_model["transition"],
                    "normalized_emission": source_model["emission"],
                }
            ),
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
            id_field = "run_id" if receipt["contract"] == "cd-model-agnosticism-inference-run/v1" else "validation_id"
            body = copy.deepcopy(receipt)
            identifier = body.pop(id_field)
            self.assertEqual(identifier, "sha256:" + TRELLIS.digest(body))

    @unittest.skipIf(jsonschema is None, "jsonschema is an optional verification dependency")
    def test_engine_101_fixture_is_immutable_and_preserves_dependence_refusal(self) -> None:
        manifest = json.loads(
            (HISTORICAL_101_FIXTURES / "fixture-manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["engine_version"], "1.0.1")
        self.assertEqual(
            manifest["source_commit"],
            "c9380d20add89de9bcb9bd23bf5afe4807ee9b00",
        )
        for name, record in manifest["files"].items():
            payload = (HISTORICAL_101_FIXTURES / name).read_bytes()
            self.assertEqual(len(payload), record["bytes"])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), record["sha256"])

        validator = jsonschema.Draft202012Validator(load("inference-run.schema.json"))
        receipts = {
            name: json.loads((HISTORICAL_101_FIXTURES / name).read_text(encoding="utf-8"))
            for name in (
                "run-independent.json",
                "validation-independent.json",
                "error-dependent.json",
            )
        }
        expected_artifact = hashlib.sha256(
            (HISTORICAL_101_FIXTURES / "model_agnosticism_trellis-1.0.1.py").read_bytes()
        ).hexdigest()
        for name, receipt in receipts.items():
            with self.subTest(name=name):
                validator.validate(receipt)
                self.assertEqual(receipt["engine"]["engine_version"], "1.0.1")
                self.assertEqual(receipt["engine"]["artifact_sha256"], expected_artifact)
                id_field = {
                    "cd-model-agnosticism-inference-run/v1": "run_id",
                    "cd-model-agnosticism-validation/v1": "validation_id",
                    "cd-model-agnosticism-error/v1": "error_id",
                }[receipt["contract"]]
                body = copy.deepcopy(receipt)
                identifier = body.pop(id_field)
                self.assertEqual(identifier, "sha256:" + TRELLIS.digest(body))
        self.assertEqual(
            receipts["error-dependent.json"]["code"],
            "UNMODELED_OBSERVATION_DEPENDENCE",
        )
        self.assertNotIn("per_model", receipts["error-dependent.json"])
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
        doctrine = (SOURCE.parents[1] / "references" / "mind" / "model-agnosticism.md").read_text(encoding="utf-8")
        self.assertIn("Engine 1.0.0 did not:", doctrine)
        self.assertIn("Otherwise mark them unsupported and reframe.", doctrine)
        observation_schema = load("observation-sequence.schema.json")
        dependence_description = observation_schema["properties"]["items"]["items"]["properties"]["dependence_refs"]["description"]
        self.assertIn("Engine 1.1.0 refuses inference", dependence_description)
        receipt_description = load("inference-run.schema.json")["description"]
        self.assertIn("Historical acceptance does not upgrade", receipt_description)
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

    def test_cli_hostile_keys_produce_bounded_schema_valid_error_json(self) -> None:
        hostile_keys = (
            "x" * (TRELLIS.MAX_ERROR_MESSAGE_CHARS + 10_000),
            "hostile-" + chr(0) + chr(0x1F) + chr(0x7F) + chr(0xD800),
        )
        validator = (
            jsonschema.Draft202012Validator(load("inference-run.schema.json"))
            if jsonschema is not None
            else None
        )
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory)
            model_path = cwd / "hostile-model.json"
            for index, hostile_key in enumerate(hostile_keys):
                with self.subTest(index=index):
                    document = copy.deepcopy(self.model)
                    document[hostile_key] = True
                    model_path.write_text(
                        json.dumps(document, ensure_ascii=True),
                        encoding="utf-8",
                    )
                    completed = subprocess.run(
                        [
                            sys.executable,
                            str(SCRIPT),
                            "analyze",
                            str(model_path),
                            str(SOURCE / "example-observation-sequence.json"),
                        ],
                        cwd=cwd,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(completed.returncode, 2, completed.stderr)
                    self.assertEqual(completed.stderr, "")
                    self.assertNotIn("Traceback", completed.stdout)
                    receipt = json.loads(completed.stdout)
                    self.assertEqual(receipt["contract"], TRELLIS.ERROR_CONTRACT)
                    self.assertEqual(receipt["code"], "UNKNOWN_FIELD")
                    self.assertLessEqual(
                        len(receipt["message"]), TRELLIS.MAX_ERROR_MESSAGE_CHARS
                    )
                    self.assertFalse(
                        any(
                            ord(character) < 0x20
                            or ord(character) == 0x7F
                            or 0xD800 <= ord(character) <= 0xDFFF
                            for character in receipt["message"]
                        )
                    )
                    if validator is not None:
                        validator.validate(receipt)

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

    def test_runtime_and_input_schemas_reject_del_controls_and_stopping_over_cap(self) -> None:
        invalid_documents = []
        for field, value in (
            ("model_set_id", "bad" + chr(0x7F) + "id"),
            ("question", "bad" + chr(0x1F) + "text"),
            ("case_ref", "bad" + chr(0x7F) + "ref"),
        ):
            model = copy.deepcopy(self.model)
            model[field] = value
            invalid_documents.append(model)
            self.assert_trellis_error(
                "INVALID_FIELD", lambda model=model: TRELLIS.validate_model_set(model)
            )

        capped = copy.deepcopy(self.model)
        capped["stopping_contract"]["maximum_observations"] = 10_000
        TRELLIS.validate_model_set(capped)
        over = copy.deepcopy(self.model)
        over["stopping_contract"]["maximum_observations"] = 10_001
        self.assert_trellis_error(
            "RESOURCE_LIMIT", lambda: TRELLIS.validate_model_set(over)
        )

        if jsonschema is not None:
            validator = jsonschema.Draft202012Validator(load("model-set.schema.json"))
            for model in invalid_documents + [over]:
                with self.assertRaises(jsonschema.ValidationError):
                    validator.validate(model)
            validator.validate(capped)


    def test_lanes_make_scenario_and_evidence_interpretations_unambiguous(self) -> None:
        scenario = analyze_documents(self.model, self.sequence)
        self.assertEqual(scenario["inputs"]["epistemic_lane"], "assumption_stress_test")
        self.assertEqual(scenario["comparison"]["weight_interpretation"], "scenario_only")
        self.assertEqual(
            scenario["semantic_boundary"]["probabilistic_output_interpretation"],
            "scenario_only",
        )
        self.assertTrue(
            scenario["semantic_boundary"]["all_probabilistic_outputs_scenario_conditioned"]
        )
        self.assertEqual(
            scenario["comparison"]["pairwise_log_likelihood_ratios"]["interpretation"],
            "scenario_only",
        )
        self.assertEqual(scenario["comparison"]["evidence_gate"]["status"], "not_applicable")

        evidence = analyze_documents(self.evidence_model(), self.sequence)
        self.assertEqual(evidence["comparison"]["weights_status"], "computed")
        self.assertEqual(
            evidence["comparison"]["weight_interpretation"],
            "conditional_evidence_update",
        )
        self.assertEqual(
            evidence["semantic_boundary"]["probabilistic_output_interpretation"],
            "conditional_evidence_update",
        )
        self.assertFalse(
            evidence["semantic_boundary"]["all_probabilistic_outputs_scenario_conditioned"]
        )
        self.assertEqual(evidence["comparison"]["evidence_gate"]["status"], "passed")
        pairwise = evidence["comparison"]["pairwise_log_likelihood_ratios"]
        self.assertEqual(pairwise["interpretation"], "conditional_evidence")
        self.assertEqual(pairwise["rows"][0]["status"], "finite")
        self.assertAlmostEqual(
            pairwise["rows"][0]["log_likelihood_ratio"],
            evidence["per_model"][0]["log_sequence_likelihood"]
            - evidence["per_model"][1]["log_sequence_likelihood"],
            places=14,
        )

    def test_evidence_weights_enforce_selection_stopping_and_parameter_gates(self) -> None:
        mutations = (
            (
                lambda model: model["candidate_selection"].update(status="data_dependent"),
                "candidate_selection_not_fixed_before_sequence",
            ),
            (
                lambda model: model["stopping_contract"].update(status="data_dependent"),
                "stopping_rule_not_fixed_before_sequence",
            ),
            (
                lambda model: model["observation_contract"].update(
                    mapping_provenance={
                        "kind": "stipulated_scenario",
                        "fixed_before_sequence": True,
                        "basis": "A post hoc mapping stress case.",
                        "source_refs": ["fixture://post-hoc-mapping"],
                    }
                ),
                "observation_mapping_provenance_not_evidence_ready",
            ),
            (
                lambda model: model["models"][0].update(
                    parameter_provenance={
                        "kind": "stipulated_scenario",
                        "fixed_before_sequence": True,
                        "basis": "A stipulated parameter scenario.",
                        "source_refs": ["fixture://stipulated-parameters"],
                    }
                ),
                "parameter_provenance_not_evidence_ready",
            ),
            (
                lambda model: model["models"][0].update(
                    prior_provenance={
                        "kind": "expert_elicited",
                        "fixed_before_sequence": False,
                        "basis": "A prior elicited after the sequence was reviewed.",
                        "source_refs": ["protocol://post-sequence-prior"],
                    }
                ),
                "prior_provenance_not_evidence_ready",
            ),
            (
                lambda model: model["comparison_contract"]["absolute_fit_policy"][
                    "calibration_ref"
                ].update(
                    provenance={
                        "kind": "stipulated_scenario",
                        "fixed_before_sequence": True,
                        "basis": "A calibration stress case.",
                        "source_refs": ["fixture://calibration-stress"],
                    }
                ),
                "calibration_provenance_not_evidence_ready",
            ),
        )
        for mutate, reason in mutations:
            with self.subTest(reason=reason):
                model = self.evidence_model()
                mutate(model)
                result = analyze_documents(model, self.sequence)
                self.assertEqual(result["comparison"]["weights_status"], "computed")
                self.assertEqual(result["comparison"]["weight_interpretation"], "diagnostic_only")
                self.assertIn(reason, result["comparison"]["evidence_gate"]["reasons"])
                self.assertEqual(
                    result["semantic_boundary"]["probabilistic_output_interpretation"],
                    "diagnostic_only",
                )

        capped = copy.deepcopy(self.model)
        capped["stopping_contract"]["maximum_observations"] = 2
        self.assert_trellis_error(
            "STOPPING_LIMIT_EXCEEDED", lambda: bind(capped, self.sequence)
        )

    def test_strict_temporal_and_step_contracts_reject_false_transitions(self) -> None:
        duplicate = copy.deepcopy(self.sequence)
        duplicate["items"][1]["event_time"] = duplicate["items"][0]["event_time"]
        duplicate["items"][1]["known_at"] = duplicate["items"][0]["known_at"]
        self.assert_trellis_error("STEP_TIME_COLLISION", lambda: bind(self.model, duplicate))

        gap = copy.deepcopy(self.sequence)
        gap["items"][1]["event_time"] = "2026-09-01T00:00:00Z"
        gap["items"][1]["known_at"] = "2026-09-01T00:00:00Z"
        self.assert_trellis_error("STEP_INTERVAL_MISMATCH", lambda: bind(self.model, gap))

        future = copy.deepcopy(self.sequence)
        future["items"][0]["event_time"] = "2026-09-03T00:00:00Z"
        future["items"][0]["known_at"] = "2026-09-03T00:00:00Z"
        self.assert_trellis_error("FUTURE_EVENT", lambda: bind(self.model, future))

        preknowledge = copy.deepcopy(self.sequence)
        preknowledge["items"][0]["known_at"] = "2026-08-29T00:00:00Z"
        self.assert_trellis_error(
            "KNOWLEDGE_PRECEDES_EVENT", lambda: bind(self.model, preknowledge)
        )

        event_model = copy.deepcopy(self.model)
        event_model["observation_contract"]["step_semantics"] = "one composite event per step"
        event_model["observation_contract"]["step_contract"] = {
            "kind": "event_step",
            "interval_seconds": None,
            "description": "Each strictly later composite event advances one transition.",
        }
        event_sequence = copy.deepcopy(self.sequence)
        for item, timestamp in zip(
            event_sequence["items"],
            ("2026-08-01T00:00:00Z", "2026-08-17T00:00:00Z", "2026-09-01T00:00:00Z"),
            strict=True,
        ):
            item["event_time"] = timestamp
            item["known_at"] = timestamp
        _, validated = bind(event_model, event_sequence)
        self.assertEqual(validated["step_contract"]["kind"], "event_step")

    def test_fixed_interval_comparison_preserves_microseconds_at_datetime_boundary(self) -> None:
        exact_interval_seconds = 315_506_361_600
        model = copy.deepcopy(self.model)
        model["observation_contract"]["step_contract"] = {
            "kind": "fixed_interval",
            "interval_seconds": exact_interval_seconds,
            "description": "One exact interval spanning year 0001 to year 9999.",
        }
        sequence = copy.deepcopy(self.sequence)
        sequence["analysis_as_of"] = "9999-01-01T00:00:00.000001Z"
        sequence["items"] = sequence["items"][:2]
        sequence["items"][0]["event_time"] = "0001-01-01T00:00:00Z"
        sequence["items"][0]["known_at"] = "0001-01-01T00:00:00Z"
        sequence["items"][1]["event_time"] = "9999-01-01T00:00:00Z"
        sequence["items"][1]["known_at"] = "9999-01-01T00:00:00Z"

        _, validated = bind(model, sequence)
        self.assertEqual(
            validated["step_contract"]["interval_seconds"], exact_interval_seconds
        )

        for timestamp in (
            "9998-12-31T23:59:59.999999Z",
            "9999-01-01T00:00:00.000001Z",
        ):
            with self.subTest(timestamp=timestamp):
                neighboring = copy.deepcopy(sequence)
                neighboring["items"][1]["event_time"] = timestamp
                neighboring["items"][1]["known_at"] = timestamp
                self.assert_trellis_error(
                    "STEP_INTERVAL_MISMATCH", lambda: bind(model, neighboring)
                )

    def test_normalization_layout_and_computation_digests_are_auditable(self) -> None:
        model = copy.deepcopy(self.model)
        model["models"][0]["initial"] = [0.8000000004, 0.1999999997]
        model["models"][0]["transition"][0] = [-0.0, 1.0]
        model_set = TRELLIS.validate_model_set(model)
        candidate = model_set["models"][0]
        stats = candidate["normalization"]
        self.assertEqual(stats["negative_zero_values_canonicalized"], 1)
        self.assertGreaterEqual(stats["vectors_adjusted"], 1)
        self.assertAlmostEqual(stats["max_absolute_sum_error"], 1e-10, places=15)
        self.assertGreater(stats["max_absolute_value_adjustment"], 0.0)
        self.assertLessEqual(
            stats["max_absolute_value_adjustment"], stats["max_absolute_sum_error"]
        )
        self.assertEqual(math.copysign(1.0, candidate["transition"][0][0]), 1.0)

        relabeled = copy.deepcopy(model)
        relabeled["models"][0]["label"] = "same computation, different prose label"
        relabeled_set = TRELLIS.validate_model_set(relabeled)
        self.assertNotEqual(
            candidate["model_document_digest"],
            relabeled_set["models"][0]["model_document_digest"],
        )
        self.assertEqual(
            candidate["inference_model_digest"],
            relabeled_set["models"][0]["inference_model_digest"],
        )
        self.assertEqual(
            candidate["predictive_kernel_digest"],
            relabeled_set["models"][0]["predictive_kernel_digest"],
        )

        bad_layout = copy.deepcopy(self.model)
        bad_layout["models"][0]["matrix_layout"]["transition"] = "target_rows_source_columns/v1"
        self.assert_trellis_error(
            "MATRIX_LAYOUT_MISMATCH", lambda: TRELLIS.validate_model_set(bad_layout)
        )

    def test_identical_ordered_predictive_kernel_is_rejected(self) -> None:
        model = copy.deepcopy(self.model)
        for field in ("initial", "transition", "emission"):
            model["models"][1][field] = copy.deepcopy(model["models"][0][field])
        self.assert_trellis_error(
            "DUPLICATE_PREDICTIVE_KERNEL",
            lambda: TRELLIS.validate_model_set(model),
        )

    def test_repeated_declared_comparison_unit_is_rejected_even_after_state_permutation(self) -> None:
        model = copy.deepcopy(self.model)
        left, right = model["models"]
        right["comparison_unit_id"] = left["comparison_unit_id"]
        right["state_order"] = list(reversed(right["state_order"]))
        right["states"] = list(reversed(right["states"]))
        right["initial"] = list(reversed(right["initial"]))
        right["transition"] = [
            [right["transition"][1][1], right["transition"][1][0]],
            [right["transition"][0][1], right["transition"][0][0]],
        ]
        right["emission"] = list(reversed(right["emission"]))
        self.assert_trellis_error(
            "DUPLICATE_COMPARISON_UNIT",
            lambda: TRELLIS.validate_model_set(model),
        )

    def test_mixed_absolute_fit_stays_visible_in_computed_evidence_weights(self) -> None:
        model = self.evidence_model()
        baseline = analyze_documents(model, self.sequence)
        surprisals = [item["mean_predictive_surprisal"] for item in baseline["per_model"]]
        self.assertNotAlmostEqual(surprisals[0], surprisals[1], places=14)
        model["comparison_contract"]["absolute_fit_policy"]["threshold"] = math.fsum(surprisals) / 2
        result = analyze_documents(model, self.sequence)
        self.assertEqual(result["comparison"]["fit_summary"]["status"], "mixed")
        self.assertEqual(result["comparison"]["weights_status"], "computed")
        statuses = {
            item["model_id"]: item["absolute_fit_status"]
            for item in result["comparison"]["relative_model_weights"]
        }
        self.assertEqual(set(statuses.values()), {"pass", "fail"})
        self.assertTrue(any("does not rehabilitate" in item for item in result["diagnostics"]))
if __name__ == "__main__":
    unittest.main()
