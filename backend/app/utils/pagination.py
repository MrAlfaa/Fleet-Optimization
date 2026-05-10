import math
from typing import Any


def calculate_skip(page: int, limit: int) -> int:
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    return (page - 1) * limit


def normalize_pagination(page: int, limit: int) -> tuple[int, int]:
    return max(page, 1), min(max(limit, 1), 100)


def build_pagination_response(items: list[dict[str, Any]], total: int, page: int, limit: int) -> dict[str, Any]:
    page, limit = normalize_pagination(page, limit)
    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "pages": math.ceil(total / limit) if total else 0,
    }
