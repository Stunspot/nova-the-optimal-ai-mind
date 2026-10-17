import unittest
from datetime import date

from expected.fixed.reporting import filter_reports


class VerifiedMinimalFix(unittest.TestCase):
    def test_includes_both_boundaries_and_excludes_neighbors(self):
        rows = [
            {"id": "before", "date": date(2026, 6, 30)},
            {"id": "start", "date": date(2026, 7, 1)},
            {"id": "middle", "date": date(2026, 7, 15)},
            {"id": "end", "date": date(2026, 7, 31)},
            {"id": "after", "date": date(2026, 8, 1)},
        ]
        self.assertEqual(["start", "middle", "end"], [row["id"] for row in filter_reports(rows, date(2026, 7, 1), date(2026, 7, 31))])


if __name__ == "__main__":
    unittest.main()
