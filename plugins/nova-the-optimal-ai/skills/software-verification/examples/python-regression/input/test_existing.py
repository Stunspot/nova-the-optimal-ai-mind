import unittest
from datetime import date

from input.reporting import filter_reports


class ExistingCoverage(unittest.TestCase):
    def test_interior_date(self):
        rows = [{"id": 1, "date": date(2026, 7, 15)}]
        self.assertEqual([1], [row["id"] for row in filter_reports(rows, date(2026, 7, 1), date(2026, 7, 31))])


if __name__ == "__main__":
    unittest.main()
