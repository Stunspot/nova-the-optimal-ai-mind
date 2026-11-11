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


    def test_malformed_arrays_are_errors_not_crashes(self):
        for name in ["assumptions","redlines"]:
            case=self.load_example();case["ledger"][name]=None
            with self.subTest(name=name):self.assertIn("ledger."+name+" must be an array",validate_case(case))

    def test_malformed_enum_objects_are_errors_not_crashes(self):
        case=self.load_example();case["status"]={};case["receipts"][0]["result"]=[];case["ledger"]["assumptions"][0]["evidence_state"]={}
        self.assertGreaterEqual(len(validate_case(case)),3)

    def test_impossible_calendar_date_is_rejected(self):
        case=self.load_example();case["updated_at"]="2026-99-99"
        self.assertIn("updated_at must be YYYY-MM-DD",validate_case(case))


if __name__ == "__main__":
    unittest.main()

