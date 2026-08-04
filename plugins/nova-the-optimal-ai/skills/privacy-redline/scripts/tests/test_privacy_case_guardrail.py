import json
import tempfile
import unittest
from pathlib import Path

from scripts.privacy_case_guardrail import validate_case


ROOT = Path(__file__).resolve().parents[2]


class PrivacyCaseGuardrailTests(unittest.TestCase):
    def load_example(self):
        return json.loads((ROOT / "examples/redline-session/case.json").read_text(encoding="utf-8"))

    def test_valid_example(self):
        self.assertEqual(validate_case(self.load_example()), [])

    def test_rejects_secret_fields(self):
        case = self.load_example()
        case["password"] = "do-not-store"
        errors = validate_case(case)
        self.assertTrue(any("sensitive field" in error for error in errors))

    def test_redline_requires_owner(self):
        case = self.load_example()
        case["ledger"]["redlines"][0]["owner"] = ""
        errors = validate_case(case)
        self.assertIn("ledger.redlines[0].owner is required", errors)

    def test_queue_requires_confirmation_gate(self):
        case = self.load_example()
        del case["queue"][0]["confirmation_gate"]
        errors = validate_case(case)
        self.assertIn("queue[0].confirmation_gate is required", errors)

    def test_receipt_result_is_bounded(self):
        case = self.load_example()
        case["receipts"][0]["result"] = "secure"
        errors = validate_case(case)
        self.assertIn("receipts[0].result is invalid", errors)

    def test_assumption_evidence_state_is_bounded(self):
        case = self.load_example()
        case["ledger"]["assumptions"][0]["evidence_state"] = "obvious"
        errors = validate_case(case)
        self.assertIn("ledger.assumptions[0].evidence_state is invalid", errors)


if __name__ == "__main__":
    unittest.main()

