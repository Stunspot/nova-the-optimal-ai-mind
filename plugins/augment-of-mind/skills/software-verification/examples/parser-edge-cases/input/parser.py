def parse_pairs(text: str) -> dict[str, str]:
    """Parse key=value pairs separated by unescaped semicolons."""
    result: dict[str, str] = {}
    # Planted defect: escaped semicolons are split before escape processing.
    for pair in text.split(";"):
        if not pair:
            continue
        key, value = pair.split("=", 1)
        result[key] = value.replace(r"\;", ";").replace(r"\\", "\\")
    return result
