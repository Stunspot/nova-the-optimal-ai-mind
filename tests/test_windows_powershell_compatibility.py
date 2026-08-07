from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WindowsPowerShellCompatibilityTests(unittest.TestCase):
    def test_powershell_scripts_are_ascii_safe(self) -> None:
        offenders: dict[str, list[str]] = {}
        for path in sorted(ROOT.rglob("*.ps1")):
            text = path.read_text(encoding="utf-8")
            non_ascii = sorted({character for character in text if ord(character) > 127})
            if non_ascii:
                offenders[path.relative_to(ROOT).as_posix()] = non_ascii
        self.assertEqual(
            offenders,
            {},
            "Windows PowerShell 5.1 reads UTF-8-without-BOM scripts through the local code page; keep shipped .ps1 files ASCII-safe.",
        )

    def test_verifier_probes_a_temporary_database_copy(self) -> None:
        verifier = (ROOT / "verify-install.ps1").read_text(encoding="ascii")
        for required in (
            "source.backup(target)",
            "$tempDatabase",
            "original_unchanged_by_verifier = $true",
            "Get-FileHash -LiteralPath $DatabasePath",
        ):
            self.assertIn(required, verifier)
        self.assertIn("'--database', $tempDatabase", verifier)

    def test_verifier_tolerates_plugin_list_without_cache_paths(self) -> None:
        verifier = (ROOT / "verify-install.ps1").read_text(encoding="ascii")
        self.assertIn("function Get-OptionalPropertyValue", verifier)
        self.assertNotIn("$plugin.installedPath", verifier)
        self.assertIn("installed_path = $installedPath", verifier)

    def test_verifier_reports_total_and_active_estate_sizes(self) -> None:
        verifier = (ROOT / "verify-install.ps1").read_text(encoding="ascii")
        for required in (
            "total_capabilities = [int]$inspection.counts.capabilities",
            "total_cards = [int]$inspection.counts.capability_cards",
            "total_vectors = [int]$inspection.counts.associative_view_vectors",
            "active_generation = $inspection.active_generation",
            "largest_generation_by_cards = $inspection.largest_generation_by_cards",
            "largest_generation_by_vectors = $inspection.largest_generation_by_vectors",
        ):
            self.assertIn(required, verifier)
        self.assertNotIn("$status.capability_count", verifier)
        self.assertNotIn("$status.active_associative_snapshot_id", verifier)

    def test_local_store_audit_is_read_only_and_estate_aware(self) -> None:
        wrapper = (ROOT / "audit-local-stores.ps1").read_text(encoding="ascii")
        tool = (ROOT / "tools" / "audit_local_stores.py").read_text(encoding="ascii")
        for required in (
            "Close Codex desktop before running this store audit",
            "tools\\audit_local_stores.py",
            "MIND ESTATES",
            "LargestCards",
            "LargestVectors",
        ):
            self.assertIn(required, wrapper)
        for required in (
            '"?mode=ro"',
            '"read_only": True',
            '"largest_generation_by_cards"',
            '"largest_generation_by_vectors"',
            '"capability_cards"',
            '"associative_view_vectors"',
            '"corkboard"',
            '"dunbar"',
        ):
            self.assertIn(required, tool)


if __name__ == "__main__":
    unittest.main()
