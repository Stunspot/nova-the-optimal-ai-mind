from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
from build_release import build
from verify_package import verify


class VerifierAdversarialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory(prefix="nova-free-adversarial-")
        base = Path(cls._temporary.name)
        result = build(REPO, base / "dist", base / "release", False)
        cls.pristine = Path(str(result["package_root"]))
        cls.cases = base / "cases"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temporary.cleanup()

    def clone(self, name: str) -> Path:
        target = self.cases / name
        shutil.copytree(self.pristine, target)
        return target

    def assert_finding(self, result: dict[str, object], phrase: str) -> None:
        self.assertEqual(result["verdict"], "FAIL", result)
        rendered = "\n".join(str(item) for item in result["findings"])
        self.assertIn(phrase, rendered)

    def test_missing_skill_root_is_rejected(self) -> None:
        package = self.clone("missing-skill")
        shutil.rmtree(package / "codex" / "plugins" / "nova-the-optimal-ai" / "skills" / "promptcraft")
        self.assert_finding(verify(package), "codex roots differ")

    def test_host_skill_drift_is_rejected(self) -> None:
        package = self.clone("host-drift")
        target = package / "claude" / "nova-the-optimal-ai" / "skills" / "promptcraft" / "SKILL.md"
        target.write_text(target.read_text(encoding="utf-8") + "\nunsafe drift\n", encoding="utf-8", newline="\n")
        self.assert_finding(verify(package), "Codex/Claude bytes differ for promptcraft")

    def test_broken_customer_reference_is_rejected(self) -> None:
        package = self.clone("broken-doc-link")
        target = package / "README.md"
        target.write_text(target.read_text(encoding="utf-8") + "\n[Missing guide](docs/NOT-HERE.md)\n", encoding="utf-8", newline="\n")
        self.assert_finding(verify(package), "broken customer Markdown reference README.md")

    def test_codex_state_fallback_is_rejected(self) -> None:
        package = self.clone("state-fallback")
        target = package / "codex" / "plugins" / "nova-the-optimal-ai" / "skills" / "corkboard" / "scripts" / "corkboard.py"
        target.write_text(target.read_text(encoding="utf-8") + "\n# CODEX_HOME fallback\n", encoding="utf-8", newline="\n")
        self.assert_finding(verify(package), "Stateful service retains CODEX_HOME fallback")

    def test_false_redistribution_ready_state_is_rejected(self) -> None:
        package = self.clone("license-overclaim")
        target = package / "RELEASE-MANIFEST.json"
        value = json.loads(target.read_text(encoding="utf-8"))
        value["redistribution_state"] = "ready"
        target.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")
        self.assert_finding(verify(package), "does not preserve the redistribution blocker")


if __name__ == "__main__":
    unittest.main()
