import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from validate_release import validate


class ReleaseValidationTests(unittest.TestCase):
    def test_current_skill_is_structurally_valid(self):
        self.assertEqual(validate(SKILL_ROOT), [])


if __name__ == "__main__":
    unittest.main()
