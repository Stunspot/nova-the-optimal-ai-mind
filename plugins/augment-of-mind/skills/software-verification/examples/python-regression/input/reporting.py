from datetime import date


def filter_reports(rows: list[dict], start: date, end: date) -> list[dict]:
    """Return rows whose report date is in the inclusive requested range."""
    # Planted regression: start should be inclusive.
    return [row for row in rows if start < row["date"] <= end]
