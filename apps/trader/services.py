from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.asset.services import (
    apply_virtual_buy,
    apply_virtual_sell,
    get_cash_asset,
    get_open_position,
)
from apps.dart.models import DartDisclosure
from apps.market.models import MarketSnapshot
from apps.market.services import to_prompt_fields
from apps.news.models import News
from apps.trader.models import DecisionHistory, OrderHistory
from apps.ws.services import build_candles
from shared.external.llm import ask_llm
from shared.external.telegram import send_message as send_telegram
from shared.stock_universe import TARGET_STOCKS
from shared.utils.json_helpers import normalize_trade_decision, parse_llm_json_object

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")
DECISION_ALLOWED_RESULTS = {
    DecisionHistory.Result.BUY,
    DecisionHistory.Result.SELL,
    DecisionHistory.Result.HOLD,
}


def build_buy_prompt(now: datetime | None = None) -> str | None:
    current_time = _resolve_now(now)
    cash = get_cash_asset()

    stock_contexts = [
        ctx for stock_code in TARGET_STOCKS.keys()
        if (ctx := _build_stock_prompt_context(stock_code, current_time)) is not None
    ]

    if not stock_contexts:
        return None

    return _render_buy_prompt(
        current_time=current_time,
        cash_amount=cash.total_amount,
        stock_contexts=stock_contexts,
    )


def build_sell_prompt(stock_code: str, now: datetime | None = None) -> str | None:
    current_time = _resolve_now(now)
    position = get_open_position()
    if position is None or position.stock_code != stock_code:
        raise ValueError("보유 종목이 아니거나 미보유 상태입니다")

    stock_context = _build_stock_prompt_context(stock_code, current_time)
    if stock_context is None:
        return None

    return _render_sell_prompt(
        current_time=current_time,
        position=position,
        stock_context=stock_context,
    )


def record_decision_history(
    request_payload: str,
    response_payload: str,
    parsed_decision: dict,
    processing_time_ms: int,
    is_error: bool,
    error_message: str | None,
) -> DecisionHistory:
    result = _extract_result(parsed_decision)
    if result not in DECISION_ALLOWED_RESULTS:
        raise ValueError("result 허용값은 BUY, SELL, HOLD 입니다")

    return DecisionHistory.objects.create(
        request_payload=request_payload,
        response_payload=response_payload,
        parsed_decision=parsed_decision,
        processing_time_ms=max(processing_time_ms, 0),
        is_error=is_error,
        error_message=error_message,
        result=result,
    )


def execute_buy(
    decision_history: DecisionHistory,
    stock_code: str,
    price: Decimal,
    quantity: int,
) -> OrderHistory:
    if decision_history.result != DecisionHistory.Result.BUY:
        raise ValueError("BUY 판단 result가 아니면 매수 주문을 실행할 수 없습니다")
    _validate_positive_order(price=price, quantity=quantity)
    if get_open_position() is not None:
        raise ValueError("이미 보유 종목이 있어 매수 불가합니다")

    order_total_amount = price * quantity
    executed_at = timezone.now()

    with transaction.atomic():
        apply_virtual_buy(stock_code, price, quantity)
        return OrderHistory.objects.create(
            decision_history=decision_history,
            stock_code=stock_code,
            order_price=price,
            order_quantity=quantity,
            order_total_amount=order_total_amount,
            result_price=price,
            result_quantity=quantity,
            result_total_amount=order_total_amount,
            order_placed_at=executed_at,
            result_executed_at=executed_at,
        )


def execute_sell(
    decision_history: DecisionHistory,
    stock_code: str,
    price: Decimal,
    quantity: int,
) -> OrderHistory:
    if decision_history.result != DecisionHistory.Result.SELL:
        raise ValueError("SELL 판단 result가 아니면 매도 주문을 실행할 수 없습니다")
    _validate_positive_order(price=price, quantity=quantity)

    position = get_open_position()
    if position is None or position.stock_code != stock_code:
        raise ValueError("해당 종목을 보유하고 있지 않은 미보유 상태입니다")
    if quantity > position.quantity:
        raise ValueError("보유 수량을 초과해 매도할 수 없습니다")

    order_total_amount = price * quantity
    executed_at = timezone.now()

    with transaction.atomic():
        apply_virtual_sell(stock_code, price, quantity)
        return OrderHistory.objects.create(
            decision_history=decision_history,
            stock_code=stock_code,
            order_price=price,
            order_quantity=quantity,
            order_total_amount=order_total_amount,
            result_price=price,
            result_quantity=quantity,
            result_total_amount=order_total_amount,
            order_placed_at=executed_at,
            result_executed_at=executed_at,
        )


def run_trading_cycle(now: datetime | None = None) -> DecisionHistory:
    started_at = time.monotonic()
    current_time = _resolve_now(now)
    request_payload = ""
    response_payload = ""
    parsed_decision = {"decision": {"result": DecisionHistory.Result.HOLD}}
    is_error = False
    error_message: str | None = None

    try:
        position = get_open_position()
        if position is None:
            request_payload = build_buy_prompt(now=current_time)
        else:
            request_payload = build_sell_prompt(position.stock_code, now=current_time)

        if request_payload is None:
            processing_time_ms = int((time.monotonic() - started_at) * 1000)
            return record_decision_history(
                request_payload="",
                response_payload="",
                parsed_decision=parsed_decision,
                processing_time_ms=processing_time_ms,
                is_error=False,
                error_message=None,
            )

        response_payload = ask_llm(request_payload)
        parsed_payload = parse_llm_json_object(response_payload)
        normalized_decision = normalize_trade_decision(parsed_payload)
        parsed_decision = normalized_decision

        if _has_invalid_result(parsed_payload):
            is_error = True
            error_message = "decision.result 허용값이 아닙니다"
        elif _downgraded_to_hold(parsed_payload, normalized_decision):
            is_error = True
            error_message = "BUY/SELL 주문 필수값이 누락되었거나 유효하지 않습니다"

    except Exception as exc:
        is_error = True
        error_message = str(exc) or exc.__class__.__name__
        parsed_decision = {"decision": {"result": DecisionHistory.Result.HOLD}}

    processing_time_ms = int((time.monotonic() - started_at) * 1000)
    decision_history = record_decision_history(
        request_payload=request_payload,
        response_payload=response_payload,
        parsed_decision=parsed_decision,
        processing_time_ms=processing_time_ms,
        is_error=is_error,
        error_message=error_message,
    )

    if not request_payload:
        _alert_telegram(f"[트레이더] 데이터 수집 이상 - 프롬프트 생성 실패 (id={decision_history.id})")
    elif not response_payload:
        _alert_telegram(f"[트레이더] LLM 응답 없음 (id={decision_history.id}, error={error_message})")

    decision = parsed_decision.get("decision", {})
    result = decision.get("result")
    if not is_error and result == DecisionHistory.Result.BUY:
        execute_buy(
            decision_history=decision_history,
            stock_code=str(decision["stock_code"]),
            price=Decimal(str(decision["price"])),
            quantity=int(decision["quantity"]),
        )
    elif not is_error and result == DecisionHistory.Result.SELL:
        execute_sell(
            decision_history=decision_history,
            stock_code=str(decision["stock_code"]),
            price=Decimal(str(decision["price"])),
            quantity=int(decision["quantity"]),
        )

    return decision_history


def _build_stock_prompt_context(stock_code: str, now: datetime) -> dict | None:
    market_snapshot = (
        MarketSnapshot.objects
        .filter(stock_code=stock_code)
        .order_by("-published_at", "-created_at")
        .first()
    )
    disclosures = list(
        DartDisclosure.objects.filter(
            stock_code=stock_code,
            published_at__gte=now - timedelta(days=7),
            published_at__lte=now,
        )
        .order_by("-published_at", "-created_at")
    )
    news_items = list(
        News.objects.filter(stock_code=stock_code)
        .filter(Q(useful=True) | Q(useful__isnull=True))
        .order_by("-published_at", "-created_at")[:10]
    )
    candles = build_candles(stock_code, minutes=30)

    if market_snapshot is None:
        logger.warning("시장 스냅샷 없음 stock_code=%s", stock_code)
        return None
    if not candles:
        logger.warning("분봉 데이터 없음 stock_code=%s", stock_code)
        return None

    return {
        "stock_code": stock_code,
        "stock_name": TARGET_STOCKS.get(stock_code, ""),
        "market": {
            "collected_at": _to_iso(market_snapshot.published_at or market_snapshot.created_at),
            "fields": to_prompt_fields(market_snapshot),
        },
        "disclosures": [
            {
                "title": one.title,
                "description": one.description,
                "published_at": _to_iso(one.published_at),
                "collected_at": _to_iso(one.created_at),
            }
            for one in disclosures
        ],
        "news": [
            {
                "title": one.title,
                "summary": one.summary,
                "useful": one.useful,
                "published_at": _to_iso(one.published_at),
                "collected_at": _to_iso(one.created_at),
            }
            for one in news_items
        ],
        "candles": [
            {
                "minute_at": _to_iso(c.minute_at),
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles
        ],
    }


def _render_buy_prompt(
    current_time: datetime,
    cash_amount: Decimal,
    stock_contexts: list[dict],
) -> str:
    prompt_payload = {
        "current_time": current_time,
        "cash_amount": cash_amount,
        "stocks": stock_contexts,
    }

    return (
        f"현재 시각은 {current_time.isoformat()}입니다.\n"
        f"보유 현금: {cash_amount}원\n"
        "아래 종목 데이터를 보고, 단타 매수할 종목이 있는지 판단하세요.\n"
        "매수하려면 BUY, 관망하려면 HOLD로 응답하세요.\n\n"
        "Respond in the following JSON format:\n"
        "{\n"
        '  "analysis": [\n'
        '    {"stock_code": "6-digit code", "stock_name": "name", "reason": "string", "confidence": 0.0 to 1.0}\n'
        "  ],\n"
        '  "decision": {\n'
        '    "result": "BUY" or "HOLD",\n'
        '    "confidence": 0.0 to 1.0 (must be 0 when HOLD),\n'
        '    "stock_code": "6-digit code (required for BUY, must match one from analysis)",\n'
        '    "price": integer (required for BUY),\n'
        '    "quantity": integer (required for BUY)\n'
        "  }\n"
        "}\n"
        "Rules:\n"
        "- analysis must include ALL stocks provided below.\n"
        "- decision.stock_code must be a valid 6-digit stock code from the data, never null.\n\n"
        "<주식정보>\n"
        f"{json.dumps(prompt_payload, ensure_ascii=False, default=_json_default, indent=2)}"
    )


def _render_sell_prompt(
    current_time: datetime,
    position,
    stock_context: dict,
) -> str:
    stock_name = TARGET_STOCKS.get(position.stock_code, "")

    return (
        f"현재 시각은 {current_time.isoformat()}입니다.\n"
        f"현재 {stock_name}({position.stock_code})을 {position.quantity}주 보유 중입니다.\n"
        f"매수 단가: {position.unit_price}원, 총 매수금액: {position.total_amount}원\n"
        "아래 데이터를 보고, 지금 매도할지 계속 보유할지 판단하세요.\n"
        "매도하려면 SELL, 계속 보유하려면 HOLD로 응답하세요.\n\n"
        "Respond in the following JSON format:\n"
        "{\n"
        '  "analysis": [\n'
        '    {"stock_code": "6-digit code", "stock_name": "name", "reason": "string", "confidence": 0.0 to 1.0}\n'
        "  ],\n"
        '  "decision": {\n'
        '    "result": "SELL" or "HOLD",\n'
        '    "confidence": 0.0 to 1.0 (must be 0 when HOLD),\n'
        f'    "stock_code": "{position.stock_code}",\n'
        '    "price": integer (required for SELL),\n'
        '    "quantity": integer (required for SELL, max ' + str(position.quantity) + ')\n'
        "  }\n"
        "}\n"
        "Rules:\n"
        "- decision.stock_code must be \"" + position.stock_code + "\".\n"
        "- decision.quantity must not exceed " + str(position.quantity) + ".\n\n"
        "<주식정보>\n"
        f"{json.dumps(stock_context, ensure_ascii=False, default=_json_default, indent=2)}"
    )


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return _to_iso(value)
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if timezone.is_naive(value):
        aware = timezone.make_aware(value, KST)
    else:
        aware = value.astimezone(KST)
    return aware.isoformat()


def _resolve_now(now: datetime | None) -> datetime:
    current = now or timezone.now()
    if timezone.is_naive(current):
        return timezone.make_aware(current, KST)
    return current.astimezone(KST)


def _extract_result(parsed_decision: dict) -> str:
    decision = parsed_decision.get("decision")
    raw_result = decision.get("result") if isinstance(decision, dict) else None
    return str(raw_result).strip().upper()


def _validate_positive_order(price: Decimal, quantity: int) -> None:
    if price <= 0 or quantity <= 0:
        raise ValueError("가격과 수량은 0보다 큰 양수여야 합니다")


def _alert_telegram(message: str) -> None:
    try:
        send_telegram(settings.TELEGRAM_DEFAULT_CHAT_ID, message)
    except Exception:
        logger.exception("텔레그램 알림 발송 실패")


def _has_invalid_result(payload: dict) -> bool:
    decision = payload.get("decision")
    raw_result = decision.get("result") if isinstance(decision, dict) else None
    if raw_result is None:
        return True
    return str(raw_result).strip().upper() not in DECISION_ALLOWED_RESULTS


def _downgraded_to_hold(original_payload: dict, normalized_payload: dict) -> bool:
    original_decision = original_payload.get("decision")
    original_result = (
        str(original_decision.get("result")).strip().upper()
        if isinstance(original_decision, dict) and original_decision.get("result") is not None
        else ""
    )
    normalized_decision = normalized_payload.get("decision", {})
    normalized_result = str(normalized_decision.get("result")).strip().upper()
    return original_result in {
        DecisionHistory.Result.BUY,
        DecisionHistory.Result.SELL,
    } and normalized_result == DecisionHistory.Result.HOLD
