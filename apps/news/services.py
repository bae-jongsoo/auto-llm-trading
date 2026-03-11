from __future__ import annotations

from apps.news.models import News


def upsert_news_items(stock_code: str, items: list[dict]) -> list[News]:
    raise NotImplementedError


def summarize_news(news: News) -> News:
    raise NotImplementedError


def collect_news(stock_codes: list[str] | None = None, limit: int = 10) -> dict:
    raise NotImplementedError
