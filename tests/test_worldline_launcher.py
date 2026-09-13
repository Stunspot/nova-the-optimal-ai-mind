from __future__ import annotations
import json
import unittest
import test_state_and_operations as fixtures

class WorldlineLauncherTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.NovaOperationsFreeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.root = self.fixture.base / "worldline-estate"
        self.values = self.fixture.configure(self.root)

    def test_timeline_passthrough_has_no_project_or_identity_invention(self):
        args = ["overview", "--from", "2026-09-01T00:00:00-05:00", "--topic", "curiosity"]
        result = self.fixture.run_cli("worldline", "--root", str(self.root), *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["script"], "worldline_timeline.py")
        self.assertEqual(data["argv"], args)
        self.assertEqual(data["selectors"], self.values)
        self.assertFalse(data["mind_core_present"])
        self.assertFalse(data["mind_hook_present"])

    def test_explicit_legacy_route_preserves_project_interface(self):
        result = self.fixture.run_cli("worldline-legacy", "--root", str(self.root), "--mode", "resume", "--project", "work", "--task", "continue", "--user", "owner")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["script"], "worldline.py")
        self.assertEqual(data["argv"], ["resume", "--task", "continue", "--user", "owner", "--project", "work", "--agent", "Nova"])
        self.assertEqual(data["selectors"], self.values)

    def test_low_level_routes_select_distinct_service_scripts(self):
        routes = [
            ("worldline", "worldline_timeline.py", ["inspect", "--event-id", "episode-demo"]),
            ("worldline-legacy", "worldline.py", ["inspect", "--task", "audit", "--user", "owner", "--project", "work"]),
        ]
        for service, expected, args in routes:
            with self.subTest(service=service):
                result = self.fixture.run_cli("run", "--root", str(self.root), service, "--", *args)
                self.assertEqual(result.returncode, 0, result.stderr)
                data = json.loads(result.stdout)
                self.assertEqual(data["script"], expected)
                self.assertEqual(data["argv"], args)

    def test_request_envelope_is_forwarded_without_reencoding(self):
        result = self.fixture.run_cli("worldline", "--root", str(self.root), "--", "--request", "exact request.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["script"], "worldline_timeline.py")
        self.assertEqual(data["argv"], ["--request", "exact request.json"])
