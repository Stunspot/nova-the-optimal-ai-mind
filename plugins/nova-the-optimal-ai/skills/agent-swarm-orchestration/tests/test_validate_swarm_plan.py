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

    def test_assemble_rejects_internal_dependency(self):
        second = copy.deepcopy(self.plan["workers"][0])
        second["id"] = "worker-b"
        second["depends_on"] = ["worker-a"]
        self.plan["workers"].append(second)
        self.plan["regime"] = "assemble"
        errors = MODULE.validate(self.plan)
        self.assertIn("assemble regime workers must be independent; dependencies declared by: worker-b", errors)

    def test_chain_requires_one_linear_dependency_path(self):
        second = copy.deepcopy(self.plan["workers"][0])
        second["id"] = "worker-b"
        self.plan["workers"].append(second)
        self.plan["regime"] = "chain"
        errors = MODULE.validate(self.plan)
        self.assertIn("chain regime must form one linear dependency path across all workers", errors)

    def test_started_downstream_requires_reconciled_dependency(self):
        second = copy.deepcopy(self.plan["workers"][0])
        second["id"] = "worker-b"
        second["depends_on"] = ["worker-a"]
        second["status"] = "working"
        self.plan["workers"][0]["status"] = "returned"
        self.plan["workers"].append(second)
        self.plan["regime"] = "chain"
        errors = MODULE.validate(self.plan)
        self.assertIn("worker worker-b status working requires accepted dependency worker-a; found returned", errors)

    def test_worker_authority_must_be_drawn_from_plan_allowed(self):
        self.plan["workers"][0]["authority"] = ["Publish externally."]
        errors = MODULE.validate(self.plan)
        self.assertIn("workers[0].authority exceeds plan authority.allowed: Publish externally.", errors)

    def test_dependency_sequenced_same_surface_is_allowed_while_downstream_planned(self):
        second = copy.deepcopy(self.plan["workers"][0])
        second["id"] = "worker-b"
        second["depends_on"] = ["worker-a"]
        self.plan["workers"][0]["write_surfaces"] = ["shared.md"]
        second["write_surfaces"] = ["./shared.md"]
        self.plan["workers"].append(second)
        self.plan["regime"] = "chain"
        errors = MODULE.validate(self.plan)
        self.assertFalse(any("active workers share write surface" in error for error in errors), errors)
        self.assertFalse(any("linear dependency path" in error for error in errors), errors)

    def test_evidence_burden_must_not_be_empty(self):
        self.plan["workers"][0]["evidence_required"] = []
        errors = MODULE.validate(self.plan)
        self.assertIn("workers[0].evidence_required must be a non-empty array of strings", errors)

    def test_terminal_plan_rejects_action_next_move(self):
        self.plan["workers"][0]["status"] = "reconciled"
        self.plan["status"] = "closed"
        self.plan["next_move"] = "Dispatch this worker again."
        errors = MODULE.validate(self.plan)
        self.assertIn("terminal plan next_move must be an exact closure or an explicit re-entry-only-if condition", errors)

    def test_terminal_plan_accepts_explicit_reentry_condition(self):
        self.plan["workers"][0]["status"] = "reconciled"
        self.plan["status"] = "closed"
        self.plan["next_move"] = "Re-entry only if new evidence reopens the mission."
        self.assertEqual([], MODULE.validate(self.plan))

    def test_empty_allowed_authority_cannot_disable_worker_subset_check(self):
        self.plan["authority"]["allowed"] = []
        self.plan["workers"][0]["authority"] = ["Publish externally."]
        errors = MODULE.validate(self.plan)
        self.assertIn(
            "workers[0].authority exceeds plan authority.allowed: Publish externally.",
            errors,
        )

    def test_started_downstream_rejects_closed_dependency(self):
        second = copy.deepcopy(self.plan["workers"][0])
        second["id"] = "worker-b"
        second["depends_on"] = ["worker-a"]
        second["status"] = "working"
        self.plan["workers"][0]["status"] = "closed"
        self.plan["workers"].append(second)
        self.plan["regime"] = "chain"
        errors = MODULE.validate(self.plan)
        self.assertIn(
            "worker worker-b status working requires accepted dependency worker-a; found closed",
            errors,
        )

    def test_started_downstream_accepts_reconciled_dependency(self):
        second = copy.deepcopy(self.plan["workers"][0])
        second["id"] = "worker-b"
        second["depends_on"] = ["worker-a"]
        second["status"] = "working"
        self.plan["workers"][0]["status"] = "reconciled"
        self.plan["workers"].append(second)
        self.plan["regime"] = "chain"
        self.assertEqual([], MODULE.validate(self.plan))

    def test_placeholder_evidence_is_rejected(self):
        for placeholder in ("none", "N/A", "n-a", "not required", "not_required"):
            with self.subTest(placeholder=placeholder):
                plan = copy.deepcopy(self.plan)
                plan["workers"][0]["evidence_required"] = [placeholder]
                errors = MODULE.validate(plan)
                self.assertIn(
                    f"workers[0].evidence_required contains placeholder evidence: {placeholder}",
                    errors,
                )

    def test_concrete_evidence_burden_remains_valid(self):
        self.plan["workers"][0]["evidence_required"] = [
            "Observe the cited source location and retained command output."
        ]
        self.assertEqual([], MODULE.validate(self.plan))

    def test_terminal_plan_rejects_closure_prefix_smuggling(self):
        self.plan["workers"][0]["status"] = "reconciled"
        self.plan["status"] = "closed"
        self.plan["next_move"] = "None; dispatch this worker again."
        errors = MODULE.validate(self.plan)
        self.assertIn(
            "terminal plan next_move must be an exact closure or an explicit re-entry-only-if condition",
            errors,
        )

    def test_terminal_plan_accepts_exact_closure_forms(self):
        for next_move in ("None", "No further action.", "Closed.", "Cancelled"):
            with self.subTest(next_move=next_move):
                plan = copy.deepcopy(self.plan)
                plan["workers"][0]["status"] = "reconciled"
                plan["status"] = "closed"
                plan["next_move"] = next_move
                self.assertEqual([], MODULE.validate(plan))

    def test_windows_trailing_dot_or_space_write_aliases_collide(self):
        for alias in ("shared.md.", "shared.md "):
            with self.subTest(alias=alias):
                plan = copy.deepcopy(self.plan)
                second = copy.deepcopy(plan["workers"][0])
                second["id"] = "worker-b"
                plan["workers"][0]["write_surfaces"] = ["shared.md"]
                second["write_surfaces"] = [alias]
                plan["workers"].append(second)
                plan["regime"] = "assemble"
                errors = MODULE.validate(plan)
                self.assertIn(
                    "active workers share write surface shared.md: worker-a, worker-b",
                    errors,
                )

    def test_schema_requires_nonempty_authority_and_concrete_evidence(self):
        schema = json.loads((SKILL_ROOT / "assets" / "swarm-plan.schema.json").read_text(encoding="utf-8"))
        allowed = schema["properties"]["authority"]["properties"]["allowed"]
        evidence_item = schema["properties"]["workers"]["items"]["properties"]["evidence_required"]["items"]
        self.assertEqual(1, allowed["minItems"])
        self.assertEqual(1, allowed["items"]["minLength"])
        self.assertIn("pattern", evidence_item)


if __name__ == "__main__":
    unittest.main()
