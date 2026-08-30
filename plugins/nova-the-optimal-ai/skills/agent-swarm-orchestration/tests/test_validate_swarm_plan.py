import copy
import importlib.util
import json
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL_ROOT / "scripts" / "validate_swarm_plan.py"
TEMPLATE_PATH = SKILL_ROOT / "assets" / "swarm-plan.template.json"
SPEC = importlib.util.spec_from_file_location("validate_swarm_plan", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ValidateSwarmPlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
        self.plan["regime"] = "enlist"

    def test_template_is_valid_when_enlist_has_one_worker(self):
        self.assertEqual([], MODULE.validate(self.plan))

    def test_direct_rejects_workers(self):
        self.plan["regime"] = "direct"
        errors = MODULE.validate(self.plan)
        self.assertIn("direct regime must not declare workers", errors)

    def test_unknown_dependency_is_rejected(self):
        self.plan["workers"][0]["depends_on"] = ["missing"]
        errors = MODULE.validate(self.plan)
        self.assertIn("worker worker-a depends on unknown worker missing", errors)

    def test_dependency_cycle_is_rejected(self):
        second = copy.deepcopy(self.plan["workers"][0])
        second["id"] = "worker-b"
        self.plan["workers"][0]["depends_on"] = ["worker-b"]
        second["depends_on"] = ["worker-a"]
        self.plan["workers"].append(second)
        self.plan["regime"] = "chain"
        errors = MODULE.validate(self.plan)
        self.assertTrue(any("dependency cycle" in error for error in errors))

    def test_active_write_collision_is_rejected(self):
        second = copy.deepcopy(self.plan["workers"][0])
        second["id"] = "worker-b"
        self.plan["workers"][0]["write_surfaces"] = ["shared.md"]
        second["write_surfaces"] = ["shared.md"]
        self.plan["workers"].append(second)
        self.plan["regime"] = "assemble"
        errors = MODULE.validate(self.plan)
        self.assertIn("active workers share write surface shared.md: worker-a, worker-b", errors)

    def test_active_write_alias_collision_is_rejected(self):
        second = copy.deepcopy(self.plan["workers"][0])
        second["id"] = "worker-b"
        self.plan["workers"][0]["write_surfaces"] = ["shared.md"]
        second["write_surfaces"] = ["./shared.md"]
        self.plan["workers"].append(second)
        self.plan["regime"] = "assemble"
        errors = MODULE.validate(self.plan)
        self.assertIn("active workers share write surface shared.md: worker-a, worker-b", errors)

    def test_malformed_worker_arrays_are_reported_without_exception(self):
        self.plan["workers"][0]["depends_on"] = 7
        self.plan["workers"][0]["write_surfaces"] = 9
        errors = MODULE.validate(self.plan)
        self.assertIn("workers[0].depends_on must be an array of non-empty strings", errors)
        self.assertIn("workers[0].write_surfaces must be an array of non-empty strings", errors)

    def test_duplicate_worker_ids_are_rejected(self):
        second = copy.deepcopy(self.plan["workers"][0])
        self.plan["workers"].append(second)
        self.plan["regime"] = "assemble"
        errors = MODULE.validate(self.plan)
        self.assertIn("duplicate worker ids: worker-a", errors)

    def test_assemble_requires_at_least_two_workers(self):
        self.plan["regime"] = "assemble"
        errors = MODULE.validate(self.plan)
        self.assertIn("assemble regime must declare at least two workers", errors)

    def test_closed_plan_requires_terminal_workers(self):
        self.plan["status"] = "closed"
        errors = MODULE.validate(self.plan)
        self.assertIn("terminal plan has non-terminal workers: worker-a", errors)


if __name__ == "__main__":
    unittest.main()
