from typing import List, Tuple, Optional


def paginate(
    items: List, limit: int = 20, cursor: Optional[int] = None
) -> Tuple[List, Optional[int]]:
    start = cursor or 0
    end = start + limit
    page = items[start:end]
    next_cursor = end if end < len(items) else None
    return page, next_cursor
