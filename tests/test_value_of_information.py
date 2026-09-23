from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import random
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins" / "nova-the-optimal-ai" / "skills" / "nova"
SCRIPT = SKILL / "scripts" / "value_of_information.py"
EXAMPLE = SKILL / "assets" / "value-of-inquiry" / "decision-example.json"
SPEC = importlib.util.spec_from_file_location("value_of_information", SCRIPT)
assert SPEC and SPEC.loader
VOI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VOI)


def fixture():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def analyze(document):
    return VOI.analyze_model(VOI.validate_document(document))


class ValueOfInformationTests(unittest.TestCase):
    def test_known_fixture_and_observation_only_policy(self):
        result = analyze(fixture())
        inquiry = result["inquiries"][0]
        self.assertEqual(result["current_expected_utility"], 20)
        self.assertEqual(result["perfect_information_expected_utility"], 50)
        self.assertEqual(result["value_of_perfect_information"], 30)
        self.assertEqual(inquiry["expected_utility_after_inquiry"], 34)
        self.assertEqual(inquiry["gross_value_of_information"], 14)
        self.assertEqual(inquiry["net_value_of_information"], 9)
        self.assertEqual(inquiry["outcomes"][0]["conditional_actions"]["best_ids"], ["proceed"])
        self.assertEqual(inquiry["outcomes"][1]["conditional_actions"]["best_ids"], ["decline"])
        self.assertEqual(result["options_by_net_value"]["best_ids"], ["inquiry:probe"])
        self.assertLess(inquiry["expected_utility_after_inquiry"], result["perfect_information_expected_utility"])

    def test_uninformative_signal_and_cost(self):
        document = fixture()
        for outcome in document["inquiries"][0]["outcomes"]:
            outcome["likelihoods"] = {"favorable": 0.5, "adverse": 0.5}
        result = analyze(document)
        self.assertEqual(result["inquiries"][0]["gross_value_of_information"], 0)
        self.assertEqual(result["inquiries"][0]["net_value_of_information"], -5)
        self.assertEqual(result["options_by_net_value"]["best_ids"], ["proceed_without_inquiry"])

    def test_perfect_signal_equals_evpi(self):
        document = fixture()
        document["inquiries"][0]["outcomes"][0]["likelihoods"] = {"favorable": 1, "adverse": 0}
        document["inquiries"][0]["outcomes"][1]["likelihoods"] = {"favorable": 0, "adverse": 1}
        result = analyze(document)
        self.assertEqual(result["inquiries"][0]["gross_value_of_information"], result["value_of_perfect_information"])

    def test_impossible_outcome_has_no_posterior_or_policy(self):
        document = fixture()
        document["inquiries"][0]["outcomes"].append({"id": "impossible", "likelihoods": {"favorable": 0, "adverse": 0}})
        outcome = analyze(document)["inquiries"][0]["outcomes"][-1]
        self.assertEqual(outcome["probability"], 0)
        self.assertIsNone(outcome["posterior"])
        self.assertIsNone(outcome["conditional_actions"])

    def test_zero_prior_state_and_dominant_action(self):
        document = fixture()
        document["states"][0]["probability"] = 1
        document["states"][1]["probability"] = 0
        result = analyze(document)
        self.assertEqual(result["value_of_perfect_information"], 0)
        self.assertEqual(result["inquiries"][0]["gross_value_of_information"], 0)
        document = fixture()
        document["actions"][0]["utilities"]["adverse"] = 10
        result = analyze(document)
        self.assertEqual(result["value_of_perfect_information"], 0)
        self.assertEqual(result["inquiries"][0]["gross_value_of_information"], 0)

    def test_exact_ties_all_preserved_in_actions_and_options(self):
        document = fixture()
        document["actions"].append({"id": "same", "utilities": {"favorable": 100, "adverse": -60}})
        document["inquiries"][0]["cost"] = 14
        result = analyze(document)
        self.assertEqual(result["current"]["best_ids"], ["proceed", "same"])
        self.assertEqual(result["options_by_net_value"]["best_ids"], ["proceed_without_inquiry", "inquiry:probe"])

    def test_near_ties_do_not_become_exact_ties(self):
        document = fixture()
        document["actions"] = [
            {"id": "higher", "utilities": {"favorable": Decimal("1.0000000000001"), "adverse": Decimal("1.0000000000001")}},
            {"id": "lower", "utilities": {"favorable": 1, "adverse": 1}},
        ]
        result = analyze(document)
        self.assertEqual(result["current"]["best_ids"], ["higher"])
        self.assertEqual(result["current"]["near_best_ids"], ["lower"])
        self.assertFalse(result["arithmetic"]["near_ties_mean_human_indifference"])
        self.assertEqual(result["current"]["values"][1]["exact_gap_to_best"], "1/10000000000000")

    def test_large_common_baseline_does_not_hide_decision_gap(self):
        document = fixture()
        baseline = 10**100
        for action in document["actions"]:
            for state in action["utilities"]:
                action["utilities"][state] += baseline
        result = analyze(document)
        self.assertEqual(result["value_of_perfect_information"], 30)
        self.assertEqual(result["inquiries"][0]["gross_value_of_information"], 14)
        self.assertEqual(result["current"]["best_ids"], ["proceed"])
        self.assertEqual(result["current"]["near_best_ids"], [])
        values = result["current"]["values"]
        self.assertEqual(values[0]["value"], values[1]["value"])
        self.assertNotEqual(values[0]["exact_value"], values[1]["exact_value"])
        self.assertEqual(values[1]["gap_to_best"], 20)
        self.assertTrue(values[0]["value_projection_rounded"])

    def test_tiny_outcome_uses_joint_weights_without_discarding_information(self):
        document = fixture()
        document["states"] = [{"id": "favorable", "probability": Decimal("1e-200")}, {"id": "adverse", "probability": 1}]
        document["actions"] = [{"id": "proceed", "utilities": {"favorable": Decimal("1e200"), "adverse": -1}},
                               {"id": "decline", "utilities": {"favorable": 0, "adverse": 0}}]
        document["inquiries"][0]["cost"] = 0
        document["inquiries"][0]["outcomes"][0]["likelihoods"] = {"favorable": 1, "adverse": 0}
        document["inquiries"][0]["outcomes"][1]["likelihoods"] = {"favorable": 0, "adverse": 1}
        result = analyze(document)
        self.assertAlmostEqual(result["inquiries"][0]["gross_value_of_information"], 1)
        self.assertEqual(result["inquiries"][0]["outcomes"][0]["conditional_actions"]["best_ids"], ["proceed"])

    def test_translation_and_positive_scale_invariance(self):
        original = analyze(fixture())
        for scale, shift in ((1, 500), (3, -111), (Decimal("0.125"), Decimal("10.25"))):
            document = fixture()
            for action in document["actions"]:
                action["utilities"] = {sid: value * scale + shift for sid, value in action["utilities"].items()}
            document["inquiries"][0]["cost"] *= scale
            result = analyze(document)
            self.assertEqual(result["current"]["best_ids"], original["current"]["best_ids"])
            self.assertEqual(result["options_by_net_value"]["best_ids"], original["options_by_net_value"]["best_ids"])
            self.assertEqual(result["value_of_perfect_information"], float(30 * scale))
            self.assertEqual(result["inquiries"][0]["gross_value_of_information"], float(14 * scale))
            self.assertEqual(result["inquiries"][0]["net_value_of_information"], float(9 * scale))

    def test_splitting_an_outcome_preserves_information_value(self):
        original = analyze(fixture())
        document = fixture()
        document["inquiries"][0]["outcomes"] = [
            {"id": "positive-a", "likelihoods": {"favorable": Decimal("0.24"), "adverse": Decimal("0.06")}},
            {"id": "positive-b", "likelihoods": {"favorable": Decimal("0.56"), "adverse": Decimal("0.14")}},
            document["inquiries"][0]["outcomes"][1],
        ]
        result = analyze(document)
        self.assertEqual(result["inquiries"][0]["gross_value_of_information"], original["inquiries"][0]["gross_value_of_information"])
        self.assertEqual(result["inquiries"][0]["outcomes"][0]["conditional_actions"], result["inquiries"][0]["outcomes"][1]["conditional_actions"])

    def test_complementary_inquiry_bundle_is_not_sum_of_parts(self):
        document = fixture()
        ids = ["00", "01", "10", "11"]
        document["states"] = [{"id": sid, "probability": 0.25} for sid in ids]
        document["actions"] = [{"id": "even", "utilities": {sid: int(sid[0] == sid[1]) for sid in ids}},
                               {"id": "odd", "utilities": {sid: int(sid[0] != sid[1]) for sid in ids}}]
        document["inquiries"] = [{"id": f"bit{index}", "cost": 0, "outcomes": [
            {"id": bit, "likelihoods": {sid: int(sid[index] == bit) for sid in ids}} for bit in "01"]} for index in (0, 1)]
        document["inquiries"].append({"id": "joint", "cost": 0, "outcomes": [
            {"id": observed, "likelihoods": {sid: int(sid == observed) for sid in ids}} for observed in ids]})
        result = analyze(document)
        self.assertEqual([q["gross_value_of_information"] for q in result["inquiries"]], [0, 0, 0.5])
        self.assertEqual(result["options_by_net_value"]["best_ids"], ["inquiry:joint"])

    def test_randomized_information_bounds(self):
        rng = random.Random(20260923)
        for _ in range(80):
            document = fixture()
            ids = [f"s{i}" for i in range(rng.randint(2, 5))]
            counts = [rng.randint(1, 10) for _ in ids]
            document["states"] = [{"id": sid, "probability": count / sum(counts)} for sid, count in zip(ids, counts)]
            document["actions"] = [{"id": f"a{i}", "utilities": {sid: rng.randint(-100, 100) for sid in ids}} for i in range(rng.randint(2, 5))]
            probabilities = {sid: rng.randint(0, 10) / 10 for sid in ids}
            document["inquiries"] = [{"id": "q", "cost": 0, "outcomes": [
                {"id": "yes", "likelihoods": probabilities},
                {"id": "no", "likelihoods": {sid: 1-p for sid, p in probabilities.items()}}]}]
            result = analyze(document)
            evsi = result["inquiries"][0]["gross_value_of_information"]
            self.assertGreaterEqual(evsi, 0)
            self.assertLessEqual(evsi, result["value_of_perfect_information"])

    def test_normalization_is_bounded_and_disclosed(self):
        document = fixture()
        document["states"][0]["probability"] = Decimal("0.4999999999999")
        result = analyze(document)
        self.assertEqual(result["normalization"]["adjusted_distributions"][0]["path"], "states")
        document["states"][0]["probability"] = Decimal("0.49")
        with self.assertRaises(VOI.Refusal) as caught:
            analyze(document)
        self.assertEqual(caught.exception.code, "INVALID_DISTRIBUTION")

    def test_malformed_numbers_shapes_and_ids_refused(self):
        mutations = [
            lambda d: d.update(extra=1),
            lambda d: d.pop("purpose"),
            lambda d: d["states"][0].update(probability=True),
            lambda d: d["states"][0].update(probability=-0.1),
            lambda d: d["states"][0].update(probability=1.1),
            lambda d: d["states"][0].update(probability=float("nan")),
            lambda d: d["actions"][0]["utilities"].update(favorable=float("inf")),
            lambda d: d["actions"][0]["utilities"].pop("adverse"),
            lambda d: d["actions"][1].update(id="proceed"),
            lambda d: d["states"][1].update(id="favorable"),
            lambda d: d["inquiries"][0]["outcomes"][1].update(id="positive"),
            lambda d: d["inquiries"].append(copy.deepcopy(d["inquiries"][0])),
            lambda d: d["inquiries"][0].update(cost=-1),
            lambda d: d["inquiries"][0]["outcomes"][0]["likelihoods"].update(favorable=0.9),
            lambda d: d["basis"].update(mode="certified"),
            lambda d: d["basis"].update(source_refs=[]),
            lambda d: d.update(actions=[]),
            lambda d: d.update(inquiries=[]),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                document = fixture()
                mutate(document)
                with self.assertRaises(VOI.Refusal):
                    analyze(document)

    def test_resource_bounds(self):
        document = fixture()
        document["actions"] = [{"id": f"a{i}", "utilities": {"favorable": 0, "adverse": 0}} for i in range(65)]
        with self.assertRaises(VOI.Refusal):
            analyze(document)
        with mock.patch.object(VOI, "MAX_OPERATIONS", 1):
            with self.assertRaises(VOI.Refusal) as caught:
                analyze(fixture())
            self.assertEqual(caught.exception.code, "WORK_LIMIT")
        with self.assertRaises(VOI.Refusal) as caught:
            VOI.bounded(Fraction(1, 1 << VOI.MAX_RATIONAL_BITS))
        self.assertEqual(caught.exception.code, "ARITHMETIC_RESOURCE_LIMIT")

    def test_output_overflow_and_underflow_are_refusals(self):
        for value in (Fraction(10**309), Fraction(1, 10**325)):
            with self.assertRaises(VOI.Refusal) as caught:
                VOI.project(value)
            self.assertEqual(caught.exception.code, "NUMERIC_RANGE")
        document = fixture()
        document["actions"][0]["utilities"] = {"favorable": 1e308, "adverse": 1e308}
        document["actions"][1]["utilities"] = {"favorable": -1e308, "adverse": -1e308}
        with self.assertRaises(VOI.Refusal) as caught:
            analyze(document)
        self.assertEqual(caught.exception.code, "NUMERIC_RANGE")

    def test_tiny_and_huge_numeric_tokens_refused_before_fraction(self):
        for token in ("1e99999999", "1e-99999999", "1"*129):
            with self.assertRaises(VOI.Refusal):
                VOI.parse_numeric_token(token)

    def test_authority_and_evidence_flags_remain_false(self):
        document = fixture()
        document["basis"]["mode"] = "evidence_informed"
        result = analyze(document)
        for key, value in result["semantic_boundary"].items():
            if key != "interpretation":
                self.assertIs(value, False, key)
        self.assertEqual(result["semantic_boundary"]["interpretation"], "conditional_arithmetic")

    def run_cli(self, command, contents):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_bytes(contents if isinstance(contents, bytes) else contents.encode("utf-8"))
            completed = subprocess.run([sys.executable, "-B", str(SCRIPT), command, str(path)], capture_output=True, text=True, timeout=20)
            return completed, json.loads(completed.stdout)

    def test_cli_analysis_and_validation_bind_exact_input_bytes(self):
        raw = EXAMPLE.read_bytes()
        for command, schema in (("validate", "validation"), ("analyze", "analysis")):
            completed, receipt = self.run_cli(command, raw)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual(completed.stderr, "")
            self.assertEqual(receipt["schema"], f"nova-value-of-information-{schema}/v1")
            self.assertEqual(receipt["input_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(receipt["engine_version"], "1.0.0")
        self.assertNotIn("inquiries", self.run_cli("validate", raw)[1])

    def test_cli_duplicate_nonfinite_oversize_and_invalid_input_refusals(self):
        cases = [("{\"schema\":1,\"schema\":2}", "DUPLICATE_JSON_KEY"),
                 ("{\"x\":NaN}", "INVALID_NUMBER"),
                 ("{\"x\":Infinity}", "INVALID_NUMBER"),
                 ("{\"x\":1e999999}", "INVALID_NUMBER"),
                 ("{" + " "*VOI.MAX_BYTES, "INPUT_SIZE_LIMIT"),
                 ("", "INPUT_SIZE_LIMIT"),
                 ("[", "INVALID_JSON"),
                 ("[]", "INVALID_FIELDS")]
        for raw, code in cases:
            with self.subTest(code=code):
                completed, receipt = self.run_cli("analyze", raw)
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(receipt["error"]["code"], code)
                self.assertEqual(completed.stderr, "")

    def test_cli_bad_command_is_typed_refusal(self):
        completed = subprocess.run([sys.executable, "-B", str(SCRIPT)], capture_output=True, text=True, timeout=20)
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(json.loads(completed.stdout)["error"]["code"], "INVALID_COMMAND")
        self.assertEqual(completed.stderr, "")


if __name__ == "__main__":
    unittest.main()
