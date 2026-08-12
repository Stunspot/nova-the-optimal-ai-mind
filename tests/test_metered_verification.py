from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIND = ROOT / "plugins" / "augment-of-mind"
SCRIPT = MIND / "skills" / "software-verification" / "scripts" / "assess_metered_verification.py"
SKILL = MIND / "skills" / "software-verification" / "SKILL.md"
RESPONSE_TEMPLATE = MIND / "skills" / "software-verification" / "assets" / "templates" / "metered-verification-response.md"

SPEC = importlib.util.spec_from_file_location("assess_metered_verification", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
NOW = datetime(2026, 8, 12, 12, 10, tzinfo=timezone.utc)


def base_plan(**changes: object) -> dict[str, object]:
    plan: dict[str, object] = {
        "format": "testforge-metered-verification/v1",
        "provider": "github-actions",
        "execution_id": "verify:pr-25:head-abc",
        "capacity_billing_scope": "user:Stunspot",
        "execution_billing_scope": "user:Stunspot",
        "observed_at": "2026-08-12T12:00:00Z",
        "valid_until": "2026-08-12T12:30:00Z",
        "evidence_source": "GitHub billing API",
        "refresh_at": "2026-09-01T00:00:00Z",
        "capacity_status": "observed",
        "remaining_minutes": 100,
        "reserve_minutes": 20,
        "paid_overage_available": False,
        "planned_runs": [
            {"name": "pull_request", "jobs": [{"ceiling_minutes": 20}]}
        ],
    }
    plan.update(changes)
    return plan


class MeteredVerificationTests(unittest.TestCase):
    def test_exact_capacity_plus_reserve_proceeds(self) -> None:
        result = MODULE.assess(base_plan(remaining_minutes=40), now=NOW)
        self.assertEqual(result["outcome"], "PROCEED")
        self.assertTrue(result["automatic_invocation_permitted"])

    def test_unavailable_provider_holds_even_without_numeric_allowance(self) -> None:
        result = MODULE.assess(
            base_plan(capacity_status="unavailable", remaining_minutes=None), now=NOW
        )
        self.assertEqual(result["outcome"], "HOLD_PROVIDER_UNAVAILABLE")
        self.assertFalse(result["automatic_invocation_permitted"])

    def test_unknown_capacity_holds_instead_of_probing(self) -> None:
        result = MODULE.assess(
            base_plan(capacity_status="unknown", remaining_minutes=None), now=NOW
        )
        self.assertEqual(result["outcome"], "HOLD_UNKNOWN")
        self.assertFalse(result["automatic_invocation_permitted"])

    def test_duplicate_triggers_matrix_and_attempts_are_all_counted(self) -> None:
        jobs = [{"ceiling_minutes": 10, "count": 2, "attempts": 2}]
        result = MODULE.assess(
            base_plan(
                remaining_minutes=100,
                reserve_minutes=0,
                planned_runs=[
                    {"name": "push", "jobs": jobs},
                    {"name": "pull_request", "jobs": jobs},
                ],
            ),
            now=NOW,
        )
        self.assertEqual(result["estimated_minutes"], 80)
        self.assertEqual(
            result["run_estimates"],
            [
                {"name": "push", "estimated_minutes": 40},
                {"name": "pull_request", "estimated_minutes": 40},
            ],
        )

    def test_billing_multiplier_is_counted(self) -> None:
        result = MODULE.assess(
            base_plan(
                reserve_minutes=0,
                planned_runs=[
                    {
                        "name": "weighted-runner",
                        "jobs": [
                            {"ceiling_minutes": 10, "billing_multiplier": 2.5}
                        ],
                    }
                ],
            ),
            now=NOW,
        )
        self.assertEqual(result["estimated_minutes"], 25)

    def test_reserve_is_not_silently_consumed(self) -> None:
        result = MODULE.assess(base_plan(remaining_minutes=20), now=NOW)
        self.assertEqual(result["outcome"], "HOLD_RESERVE")

    def test_paid_overage_requires_authority_outside_the_assessor(self) -> None:
        result = MODULE.assess(
            base_plan(remaining_minutes=0, paid_overage_available=True), now=NOW
        )
        self.assertEqual(result["outcome"], "AUTHORITY_REQUIRED_PAID")
        self.assertFalse(result["automatic_invocation_permitted"])
        self.assertFalse(result["paid_dispatch_permitted"])
        self.assertFalse(result["paid_overage_authorized"])

    def test_paid_minutes_preserve_reserve(self) -> None:
        result = MODULE.assess(
            base_plan(
                remaining_minutes=15,
                reserve_minutes=10,
                paid_overage_available=True,
                planned_runs=[
                    {
                        "name": "pull_request",
                        "jobs": [{"ceiling_minutes": 15, "count": 3}],
                    }
                ],
            ),
            now=NOW,
        )
        self.assertEqual(result["estimated_minutes"], 45)
        self.assertEqual(result["required_with_reserve_minutes"], 55)
        self.assertEqual(result["paid_minutes_required"], 40)

    def test_caller_cannot_fabricate_paid_authority(self) -> None:
        with self.assertRaisesRegex(MODULE.PlanError, "cannot accept or grant"):
            MODULE.assess(
                base_plan(
                    remaining_minutes=0,
                    paid_overage_available=True,
                    paid_overage_authorization={
                    "authorization_id": "decision:tiny",
                    "authorized_by": "stunspot",
                    "execution_id": "verify:pr-25:head-abc",
                    "plan_sha256": "0" * 64,
                    "authorized_at": "2026-08-12T12:05:00Z",
                    "valid_until": "2026-08-12T13:00:00Z",
                    "billing_scope": "user:Stunspot",
                    "max_paid_minutes": 20,
                },
                ),
                now=NOW,
            )

    def test_caller_cannot_supply_a_favorable_consumption_ledger(self) -> None:
        with self.assertRaisesRegex(MODULE.PlanError, "cannot accept or grant"):
            MODULE.assess(
                base_plan(
                    remaining_minutes=0,
                    paid_overage_available=True,
                    consumed_authorization_ids=[],
                ),
                now=NOW,
            )

    def test_malformed_or_stale_snapshot_is_rejected(self) -> None:
        with self.assertRaisesRegex(MODULE.PlanError, "valid ISO 8601"):
            MODULE.assess(base_plan(observed_at="not-a-date"), now=NOW)
        with self.assertRaisesRegex(MODULE.PlanError, "expired"):
            MODULE.assess(
                base_plan(
                    observed_at="2026-08-12T10:00:00Z",
                    valid_until="2026-08-12T10:30:00Z",
                ),
                now=NOW,
            )

    def test_capacity_must_belong_to_execution_billing_scope(self) -> None:
        with self.assertRaisesRegex(MODULE.PlanError, "exactly match"):
            MODULE.assess(
                base_plan(execution_billing_scope="org:SomeoneElse"), now=NOW
            )

    def test_snapshot_is_invalid_after_billing_cycle_refresh(self) -> None:
        with self.assertRaisesRegex(MODULE.PlanError, "refresh boundary"):
            MODULE.assess(
                base_plan(
                    observed_at="2026-08-12T11:50:00Z",
                    valid_until="2026-08-12T12:20:00Z",
                    refresh_at="2026-08-12T12:00:00Z",
                ),
                now=NOW,
            )

    def test_skill_makes_capacity_preflight_mandatory(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("## Preflight metered verification", text)
        self.assertIn("Do not launch a metered check merely to discover", text)
        self.assertIn("scripts/assess_metered_verification.py", text)
        self.assertIn("`Capacity`, `Expansion`, `Decision`, `Substitute`, and `Authority`", text)
        self.assertIn("`Substitute` is mandatory on every hold", text)
        self.assertIn("current multiplier is unobserved, mark it explicitly `unknown`", text)
        self.assertIn("triggers × matrix jobs × attempts × ceiling minutes × provider multiplier", text)
        self.assertIn("Never label the intermediate job-attempt count as runner-minutes", text)
        self.assertIn("This substitute does not prove:", text)
        self.assertIn("PREPARED — NOT EXECUTED", text)
        self.assertIn("Copy snapshot facts exactly", text)
        self.assertIn("required_with_reserve_minutes = estimated_minutes + reserve_minutes", text)
        self.assertIn("maximum_paid_minutes_required", text)
        self.assertIn("assets/templates/metered-verification-response.md", text)

        response_template = RESPONSE_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("2 × 3 × 2 × 20 = 240 raw runner-minutes", response_template)
        self.assertIn("required with reserve is 55", response_template)
        self.assertIn("maximum paid minutes required is 40", response_template)
        self.assertIn("A formula that omits its evaluated result is incomplete", response_template)
        self.assertIn("Exact run: `[trigger name and count", response_template)
        self.assertIn("Never replace the exact run with the phrase", response_template)
        self.assertIn("If capacity or reserve is unknown", response_template)
        self.assertIn("This substitute does not prove:", response_template)
        self.assertIn("Do not invent a local command or file path", text)


if __name__ == "__main__":
    unittest.main()
