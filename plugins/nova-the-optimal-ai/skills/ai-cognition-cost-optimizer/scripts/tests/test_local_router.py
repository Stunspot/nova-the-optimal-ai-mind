from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "local_router.py"
SPEC = importlib.util.spec_from_file_location("local_router", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def policy(*candidates):
    return {"format": "cd-local-route-policy/v1", "id": "policy", "candidates": list(candidates)}


def candidate(model="fit:latest", status="qualified", task_classes=None, priority=1, **overrides):
    value = {
        "model": model,
        "endpoint": "http://127.0.0.1:11434",
        "enabled": True,
        "priority": priority,
        "estimated_cost_per_accepted_outcome": 0.1,
        "capabilities": {"context_tokens": 32768, "modalities": ["text"], "structured_output": True},
        "qualification": {
            "status": status,
            "evaluated_task_classes": task_classes or ["summary"],
            "acceptance_rate": 0.95,
            "reliability_rate": 0.99,
            "observed_p95_latency_ms": 5000,
            "evidence": "bounded fixture",
        },
    }
    value.update(overrides)
    return value


def request(**overrides):
    value = {
        "format": "cd-local-cognition-request/v1",
        "id": "request",
        "task_class": "summary",
        "prompt": "Summarize this.",
        "execution_authorized": False,
        "required": {
            "min_context_tokens": 4096,
            "modalities": ["text"],
            "tool_use": False,
            "structured_output": False,
            "min_acceptance_rate": 0.9,
            "min_reliability_rate": 0.95,
            "max_p95_latency_ms": 10000,
        },
    }
    value.update(overrides)
    return value


def inventory(*models):
    return {"format": "cd-local-model-inventory/v1", "observed_at": "2026-07-18T00:00:00Z", "models": [{"name": model} for model in models]}


class LocalRouterTests(unittest.TestCase):
    def test_selects_installed_qualified_candidate(self):
        result = MODULE.plan(policy(candidate()), request(), inventory("fit:latest"))
        self.assertEqual("route-selected", result["status"])
        self.assertEqual("fit:latest", result["selected"]["model"])

    def test_unqualified_cheaper_candidate_cannot_win(self):
        cheap = candidate("cheap:latest", status="unverified", priority=0, estimated_cost_per_accepted_outcome=0.001)
        fit = candidate("fit:latest", priority=1)
        result = MODULE.plan(policy(cheap, fit), request(), inventory("cheap:latest", "fit:latest"))
        self.assertEqual("fit:latest", result["selected"]["model"])
        self.assertIn("model is not qualified", result["candidates"][0]["floor_failures"])

    def test_missing_model_returns_no_route(self):
        result = MODULE.plan(policy(candidate()), request(), inventory("other:latest"))
        self.assertEqual("no-eligible-local-route", result["status"])
        self.assertIsNone(result["selected"])

    def test_multiple_eligible_routes_require_comparable_outcome_cost(self):
        first = candidate("first:latest", estimated_cost_per_accepted_outcome=None)
        second = candidate("second:latest", estimated_cost_per_accepted_outcome=0.2)
        result = MODULE.plan(policy(first, second), request(), inventory("first:latest", "second:latest"))
        self.assertEqual("no-cost-comparable-local-route", result["status"])
        self.assertIsNone(result["selected"])
        self.assertTrue(result["decision_blockers"])

    def test_tool_requirement_is_rejected(self):
        value = request()
        value["required"]["tool_use"] = True
        result = MODULE.plan(policy(candidate()), value, inventory("fit:latest"))
        self.assertEqual("no-eligible-local-route", result["status"])
        self.assertIn("tool use is outside the v0.2 local executor", result["candidates"][0]["floor_failures"])

    def test_remote_endpoint_is_rejected(self):
        with self.assertRaises(MODULE.RouteError):
            MODULE.local_endpoint("https://api.example.com")

    def test_execution_requires_both_authority_gates(self):
        req = request(execution_authorized=True)
        route = MODULE.plan(policy(candidate()), req, inventory("fit:latest"))
        with self.assertRaisesRegex(MODULE.RouteError, "requires both"):
            MODULE.execute(route, req, False, 1)

    def test_local_execution_records_tokens_without_claiming_acceptance(self):
        req = request(execution_authorized=True)
        route = MODULE.plan(policy(candidate()), req, inventory("fit:latest"))
        response = {
            "response": "A bounded summary.",
            "done": True,
            "done_reason": "stop",
            "total_duration": 3_600_000_000,
            "prompt_eval_count": 20,
            "eval_count": 5,
        }
        route["selected"]["think"] = False
        with mock.patch.object(MODULE, "request_json", return_value=response) as called:
            result = MODULE.execute(route, req, True, 1)
        self.assertEqual("A bounded summary.", result["response"])
        self.assertEqual(0, result["workflow_run"]["accepted_outcomes"])
        self.assertEqual(20, result["workflow_run"]["quantities"]["input_tokens"])
        self.assertEqual("/api/generate", called.call_args.args[1])
        self.assertIs(False, called.call_args.args[2]["think"])


if __name__ == "__main__":
    unittest.main()
