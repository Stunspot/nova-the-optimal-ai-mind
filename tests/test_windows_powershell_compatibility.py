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
        self.assertIn("--database', $tempDatabase", verifier)


if __name__ == "__main__":
    unittest.main()
