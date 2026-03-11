from typing import Optional

from ninja import Schema


class NewsCollectIn(Schema):
    stock_codes: Optional[list[str]] = None
    limit: int = 10


class NewsCollectOut(Schema):
    stock_codes: list[str]
    fetched_items: int
    saved_items: int
    summarized_items: int
