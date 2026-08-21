from typing import Any


FORMULA_PREFIXES = ("=", "+", "-", "@")


def safe_spreadsheet_value(value: Any) -> Any:
    """Prevent spreadsheet applications from evaluating exported user text."""
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return f"'{value}"
    return value
