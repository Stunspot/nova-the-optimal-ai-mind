from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "validate_pursuit_state.py"
TEMPLATE = Path(__file__).resolve().parents[2] / "assets" / "pursuit-state.template.json"
SPEC = importlib.util.spec_from_file_location("validate_pursuit_state", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class PursuitStateValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.valid = json.loads(TEMPLATE.read_text(encoding="utf-8"))

    def test_template_is_valid(self) -> None:
        self.assertEqual(MODULE.validate(copy.deepcopy(self.valid)), [])

    def test_completed_requires_evidence_and_no_remaining_work(self) -> None:
        state = copy.deepcopy(self.valid)
        state["status"] = "completed"
        errors = MODULE.validate(state)
        self.assertIn("completed pursuit cannot retain remaining work", errors)
        self.assertIn("completed pursuit requires completion_evidence", errors)

    def test_repeated_stall_requires_strategy_revision(self) -> None:
        state = copy.deepcopy(self.valid)
        state["progress"]["stall_count"] = 3
        self.assertIn("three or more stalled cycles require strategy.last_revision", MODULE.validate(state))
        state["strategy"]["last_revision"] = "Switched from repeated retrieval to source inventory."
        self.assertEqual(MODULE.validate(state), [])

    def test_authority_and_budget_states_require_their_gates(self) -> None:
        authority = copy.deepcopy(self.valid)
        authority["status"] = "awaiting-authority"
        self.assertIn("awaiting-authority status requires authority.pending_gate", MODULE.validate(authority))
        budget = copy.deepcopy(self.valid)
        budget["status"] = "budget-exhausted"
        self.assertIn("budget-exhausted status requires budgets.exhausted_dimension", MODULE.validate(budget))

    def test_cli_reports_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(path), "--json"],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()
