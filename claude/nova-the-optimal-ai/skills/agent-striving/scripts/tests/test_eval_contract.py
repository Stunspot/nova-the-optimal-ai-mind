from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any


SUITE = Path(__file__).resolve().parents[2] / "evals" / "core-transfer-cases.yaml"
CONTRACT_VERSION = "cd-striving-episode/v1"


def read_path(value: dict[str, Any], dotted_path: str) -> Any:
    current: Any = value
    for segment in dotted_path.split("."):
        current = current[segment]
    return current


def write_path(value: dict[str, Any], dotted_path: str, inserted: Any) -> None:
    segments = dotted_path.split(".")
    current = value
    for segment in segments[:-1]:
        current = current.setdefault(segment, {})
    current[segments[-1]] = inserted


def materialize_result(result: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(result["payload"])
    for response_path, request_path in result.get("copy_from_request", {}).items():
        write_path(payload, response_path, read_path(request, request_path))
    return payload


class EpisodeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(SUITE.read_text(encoding="utf-8"))
        cls.cases = {case["id"]: case for case in cls.data["cases"]}

    def contract(self, case_id: str) -> dict[str, Any]:
        return self.cases[case_id]["episode_contract"]

    def test_suite_does_not_misrepresent_specs_as_results(self) -> None:
        status = self.data["evidence_status"]
        self.assertIn("claims no model result", status)
        self.assertIn("captures", status)
        semantics = self.data["fixture_semantics"]
        self.assertIn("copy_from_request maps", semantics)
        self.assertIn("before the result is returned", semantics)

    def test_each_episode_contract_is_executable_and_fresh(self) -> None:
        for case_id in (
            "STRIVE-GOAL-PROMPTCRAFT-016",
            "STRIVE-REENTRY-017",
            "STRIVE-SUPERSESSION-018",
        ):
            contract = self.contract(case_id)
            self.assertEqual(contract["contract_version"], CONTRACT_VERSION)
            self.assertTrue(contract["required_assertions"])
            for episode in contract["episodes"]:
                with self.subTest(case_id=case_id, episode=episode["id"]):
                    self.assertTrue(episode["fresh_context"])
                    self.assertIn("allowed_prior_context", episode)
                    self.assertTrue(episode["required_calls"])
                    self.assertTrue(episode["captures"])
                    result_calls = {
                        result["after_call"] for result in episode["host_results"]
                    }
                    self.assertEqual(set(episode["required_calls"]), result_calls)

    def test_goal_contract_grades_the_materialized_host_payload(self) -> None:
        contract = self.contract("STRIVE-GOAL-PROMPTCRAFT-016")
        self.assertEqual(contract["mode"], "host-call-capture")
        episode = contract["episodes"][0]
        captures = set(episode["captures"])
        self.assertIn("create_goal.request.objective", captures)
        self.assertIn("create_goal.result.goal.objective", captures)

        candidate = (
            "Repair Striving so a future collaborator resumes intelligent work in natural prose, "
            "and bring the authorized integrations into agreement without publishing them."
        )
        request = {"objective": candidate}
        stored = materialize_result(episode["host_results"][0], request)
        self.assertEqual(read_path(stored, "goal.objective"), candidate)
        self.assertEqual(stored["goal"]["id"], "goal-016")

        joined = " ".join(contract["required_assertions"]).lower()
        self.assertIn("no-publication", joined)
        self.assertIn("exact create_goal request objective", joined)

    def test_reentry_contract_removes_the_earlier_transcript(self) -> None:
        contract = self.contract("STRIVE-REENTRY-017")
        self.assertEqual(contract["mode"], "fresh-context-reentry")
        episode_a, episode_b = contract["episodes"]
        self.assertEqual([episode_a["id"], episode_b["id"]], ["A", "B"])
        self.assertEqual(episode_b["allowed_prior_context"], ["reactivation cue: load p current"])
        self.assertIn("episode A transcript", episode_b["forbidden_context"])
        loaded = episode_b["host_results"][0]["payload"]
        self.assertEqual(loaded["revision"], 4)
        self.assertEqual(loaded["disposition"], "live")

    def test_supersession_contract_exercises_a_stale_wakeup(self) -> None:
        contract = self.contract("STRIVE-SUPERSESSION-018")
        self.assertEqual(contract["mode"], "fresh-context-supersession")
        self.assertEqual([episode["id"] for episode in contract["episodes"]], ["A", "B", "C"])
        episode_c = contract["episodes"][2]
        self.assertIn("revision 1", episode_c["input"])
        self.assertIn("episode B transcript", episode_c["forbidden_context"])
        loaded = episode_c["host_results"][0]["payload"]
        self.assertEqual(loaded["revision"], 2)
        self.assertEqual(loaded["disposition"], "released")
        self.assertIn("do not publish", loaded["current_direction"].lower())


if __name__ == "__main__":
    unittest.main()
