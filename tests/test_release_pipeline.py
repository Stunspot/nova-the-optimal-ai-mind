from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUILDER = REPO / "tools" / "build_release.py"
VERIFIER = REPO / "tools" / "verify_package.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReleasePipelineTests(unittest.TestCase):
    def test_build_is_deterministic_and_verifies(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nova-free-release-") as directory:
            base = Path(directory)
            command = [
                sys.executable, "-B", "-X", "utf8", str(BUILDER),
                "--repo", str(REPO),
                "--output-parent", str(base / "dist"),
                "--artifact-parent", str(base / "release"),
            ]
            first = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            first_result = json.loads(first.stdout)
            customer = Path(first_result["customer_zip"])
            codex = Path(first_result["codex_zip"])
            claude = Path(first_result["claude_zip"])
            first_hashes = {path.name: digest(path) for path in (customer, codex, claude)}

            verify = subprocess.run(
                [sys.executable, "-B", "-X", "utf8", str(VERIFIER), first_result["package_root"]],
                capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            self.assertEqual(json.loads(verify.stdout)["verdict"], "PASS")

            second = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(second.returncode, 0, second.stderr)
            second_result = json.loads(second.stdout)
            second_paths = (Path(second_result["customer_zip"]), Path(second_result["codex_zip"]), Path(second_result["claude_zip"]))
            self.assertEqual(first_hashes, {path.name: digest(path) for path in second_paths})

            with zipfile.ZipFile(second_result["customer_zip"]) as archive:
                names = archive.namelist()
            prefix = "nova-the-optimal-ai-free-3.0.0/"
            self.assertTrue(all(name.startswith(prefix) for name in names))
            self.assertIn(prefix + "codex/.agents/plugins/marketplace.json", names)
            self.assertIn(prefix + "claude/nova-the-optimal-ai/.claude-plugin/plugin.json", names)


if __name__ == "__main__":
    unittest.main()
