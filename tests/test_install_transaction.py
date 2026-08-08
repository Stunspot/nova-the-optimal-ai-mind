from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InstallerTransactionTests(unittest.TestCase):
    def _installers(self) -> list[Path]:
        candidates = [
            ROOT / "install.ps1",
            ROOT / "plugins" / "augment-of-mind" / "install.ps1",
        ]
        return [path for path in candidates if path.exists()]

    def test_semantic_preflight_precedes_every_customer_mutation(self) -> None:
        for path in self._installers():
            with self.subTest(installer=path.relative_to(ROOT).as_posix()):
                text = path.read_text(encoding="utf-8")
                self.assertEqual(text.count("[CmdletBinding()]"), 1)
                collision = text.index(
                    "if (Test-Path -LiteralPath $databaseFullPath)"
                )
                semantic = text.index("--database $stagingDatabase --model")
                marketplace = text.index("plugin marketplace add")
                plugin = text.index("plugin add $selector")
                commit = text.index(
                    "Move-Item -LiteralPath $stagingDatabase "
                    "-Destination $databaseFullPath"
                )
                cleanup = text.index(
                    "Remove-Item -LiteralPath $stagingRoot -Recurse -Force"
                )
                self.assertLess(collision, semantic)
                self.assertLess(semantic, marketplace)
                self.assertLess(marketplace, plugin)
                self.assertLess(plugin, commit)
                self.assertLess(commit, cleanup)
                self.assertNotIn(
                    "activate-estate-generation --database $DatabasePath",
                    text,
                )
                self.assertIn(
                    "MIND preflight semantic association failed. "
                    "Nothing was installed.",
                    text,
                )

    def test_plugin_steps_are_idempotent_and_target_commit_refuses_overwrite(self) -> None:
        for path in self._installers():
            with self.subTest(installer=path.relative_to(ROOT).as_posix()):
                text = path.read_text(encoding="utf-8")
                self.assertIn("$known.Count -eq 0", text)
                self.assertIn(
                    "$_.pluginId -eq $selector -and $_.enabled",
                    text,
                )
                self.assertIn(
                    "A MIND database appeared at $databaseFullPath "
                    "during installation. It was not overwritten.",
                    text,
                )


    def test_skip_plugin_install_has_a_truthful_completion_message(self) -> None:
        text = (ROOT / "install.ps1").read_text(encoding="utf-8")
        self.assertIn("if ($SkipPluginInstall)", text)
        self.assertIn("Plugin installation was skipped.", text)
        self.assertIn("Both plugins are enabled", text)
        self.assertLess(
            text.index("if ($SkipPluginInstall)"),
            text.index("Both plugins are enabled"),
        )
    def test_installer_never_writes_python_bytecode_into_the_package(self) -> None:
        for path in self._installers():
            with self.subTest(installer=path.relative_to(ROOT).as_posix()):
                text = path.read_text(encoding="utf-8")
                self.assertEqual(text.count("& $python.Source -B"), 4)
                self.assertNotIn("& $python.Source -m", text)
                self.assertNotIn("& $python.Source -X utf8", text)
                self.assertNotIn("& $python.Source -c", text)

if __name__ == "__main__":
    unittest.main()