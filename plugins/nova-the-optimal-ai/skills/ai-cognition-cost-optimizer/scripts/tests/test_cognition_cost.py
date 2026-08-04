from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "cognition_cost.py"


def card(route: str, **prices):
    base = {
        "format": "cd-cognition-rate-card/v1", "id": route, "currency": "USD", "provider": "fixture", "model": "fixture", "route": route,
        "source": {"kind": "scenario-assumption", "reference": "test fixture", "checked_at": "2026-07-17T00:00:00Z", "effective_at": None, "confidence": "high"},
        "prices": {"input_per_million": 1, "cached_input_read_per_million": 0.1, "cache_write_per_million": 1.25, "output_per_million": 5, "reasoning_per_million": None, "request_each": 0, "tool_each": 0.02, "search_each": None, "image_each": None, "storage_gb_hour": None, "infrastructure_hour": None, "review_hour": 60},
        "surcharge_percent": 0, "fixed_cost": 0, "applied_modifiers": [], "constraints": [], "notes": []
    }
    base["prices"].update(prices)
    return base


def run(route: str, accepted=1, eligible=True, **quantities):
    values = {"input_tokens": 1_000_000, "output_tokens": 100_000, "requests": 1, "tool_calls": 0, "review_hours": 0}
    values.update(quantities)
    return {"format": "cd-cognition-workflow-run/v1", "id": "run", "mode": "forecast", "route_id": route, "attempts": 1, "accepted_outcomes": accepted, "elapsed_hours": 1, "eligible": eligible, "floor_failures": [] if eligible else ["quality floor"], "quantities": values, "direct_costs": {}, "assumptions": []}


class CostTests(unittest.TestCase):
    def invoke(self, *args, expected=0):
        result = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False)
        self.assertEqual(expected, result.returncode, result.stderr)
        return result

    def write(self, root, name, value):
        path = root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return str(path)

    def estimate(self, root, route="a", card_value=None, run_value=None, extra=()):
        c = self.write(root, "card.json", card_value or card(route))
        r = self.write(root, "run.json", run_value or run(route))
        return self.invoke("estimate", "--rate-card", c, "--run", r, *extra)

    def test_complete_cost_per_accepted_outcome(self):
        with tempfile.TemporaryDirectory() as d:
            value = json.loads(self.estimate(Path(d)).stdout)
            self.assertEqual(1.5, value["total_cost"])
            self.assertEqual(1.5, value["cost_per_accepted_outcome"])
            self.assertEqual("complete", value["status"])

    def test_unknown_positive_rate_is_not_zero(self):
        with tempfile.TemporaryDirectory() as d:
            rr = run("a", search_calls=2)
            c = self.write(Path(d), "card.json", card("a")); r = self.write(Path(d), "run.json", rr)
            failure = self.invoke("estimate", "--rate-card", c, "--run", r, expected=2)
            self.assertIn("unknown rates", failure.stderr)

    def test_allow_incomplete_names_unknown_component(self):
        with tempfile.TemporaryDirectory() as d:
            rr = run("a", search_calls=2)
            value = json.loads(self.estimate(Path(d), run_value=rr, extra=("--allow-incomplete",)).stdout)
            self.assertEqual("incomplete", value["status"])
            self.assertIn("search_each", value["unknown_components"])

    def test_no_accepted_outcome_has_no_division_claim(self):
        with tempfile.TemporaryDirectory() as d:
            value = json.loads(self.estimate(Path(d), run_value=run("a", accepted=0)).stdout)
            self.assertIsNone(value["cost_per_accepted_outcome"])

    def test_review_and_rework_are_counted(self):
        with tempfile.TemporaryDirectory() as d:
            rr = run("a", review_hours=0.5); rr["direct_costs"] = {"rework": 10, "waste": 5}
            value = json.loads(self.estimate(Path(d), run_value=rr).stdout)
            self.assertEqual(41.5, value["total_cost"])
            self.assertGreater(value["waste_ratio"], 0)

    def test_compare_excludes_cheapest_ineligible_route(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            reports = []
            for route, eligible, input_rate in (("cheap", False, 0.1), ("fit", True, 2)):
                c = self.write(root, f"{route}-card.json", card(route, input_per_million=input_rate))
                r = self.write(root, f"{route}-run.json", run(route, eligible=eligible))
                out = root / f"{route}-report.json"
                self.invoke("estimate", "--rate-card", c, "--run", r, "--output", str(out))
                reports.append(str(out))
            result = json.loads(self.invoke("compare", *reports).stdout)
            self.assertEqual("fit", result["recommended_route"])

    def test_compare_rejects_unconverted_currency(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            a = {"format": "cd-cognition-cost-report/v1", "route_id": "a", "currency": "USD", "status": "complete", "total_cost": 1, "attempts": 1, "accepted_outcomes": 1, "cost_per_attempt": 1, "cost_per_accepted_outcome": 1, "waste_ratio": 0, "cost_velocity_per_hour": 1, "eligible": True, "floor_failures": [], "components": {}, "unknown_components": [], "evidence": {}}
            b = dict(a, route_id="b", currency="EUR")
            pa = self.write(root, "a.json", a); pb = self.write(root, "b.json", b)
            self.assertIn("same normalized currency", self.invoke("compare", pa, pb, expected=2).stderr)


if __name__ == "__main__":
    unittest.main()
