from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from apps.trader.models import DecisionHistory, OrderHistory


def build_buy_prompt(now: datetime | None = None) -> str:
    raise NotImplementedError


def build_sell_prompt(stock_code: str, now: datetime | None = None) -> str:
    raise NotImplementedError


def record_decision_history(
    request_payload: str,
    response_payload: str,
    parsed_decision: dict,
    processing_time_ms: int,
    is_error: bool,
    error_message: str | None,
) -> DecisionHistory:
    raise NotImplementedError


def execute_buy(
    decision_history: DecisionHistory,
    stock_code: str,
    price: Decimal,
    quantity: int,
) -> OrderHistory:
    raise NotImplementedError


def execute_sell(
    decision_history: DecisionHistory,
    stock_code: str,
    price: Decimal,
    quantity: int,
) -> OrderHistory:
    raise NotImplementedError


def run_trading_cycle(now: datetime | None = None) -> DecisionHistory:
    raise NotImplementedError
