import unittest
from datetime import date

from input.reporting import filter_reports


class InclusiveDateRangeRegression(unittest.TestCase):
    def test_includes_both_boundaries_and_excludes_neighbors(self):
        rows = [
            {"id": "before", "date": date(2026, 6, 30)},
            {"id": "start", "date": date(2026, 7, 1)},
            {"id": "middle", "date": date(2026, 7, 15)},
            {"id": "end", "date": date(2026, 7, 31)},
            {"id": "after", "date": date(2026, 8, 1)},
        ]
        result = filter_reports(rows, date(2026, 7, 1), date(2026, 7, 31))
        self.assertEqual(["start", "middle", "end"], [row["id"] for row in result])


if __name__ == "__main__":
    unittest.main()
