from __future__ import annotations

from datetime import datetime


def save_trade_tick(stock_code: str, tick: dict, now: datetime | None = None) -> None:
    raise NotImplementedError


def save_quote_tick(stock_code: str, tick: dict, now: datetime | None = None) -> None:
    raise NotImplementedError


def trim_ticks(stock_code: str, now: datetime | None = None) -> None:
    raise NotImplementedError


def get_recent_price_flow(stock_code: str, minutes: int = 10) -> dict:
    raise NotImplementedError
