from __future__ import annotations

import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone
from django_redis import get_redis_connection

from shared.stock_universe import validate_stock_code

KST = ZoneInfo("Asia/Seoul")
TRADE_TICK_KEY_PATTERN = "ws:trade:{stock_code}"
QUOTE_TICK_KEY_PATTERN = "ws:quote:{stock_code}"
TICK_RETENTION_HOURS = 1


def save_trade_tick(stock_code: str, tick: dict, now: datetime | None = None) -> None:
    normalized_stock_code = validate_stock_code(stock_code)
    collected_at = _resolve_now(now)

    trade_id = _require_text(tick.get("trade_id"), "trade_id")
    trade_time = _require_text(tick.get("trade_time"), "trade_time")
    _parse_time_or_raise(trade_time, "trade_time")
    price = _require_int(tick.get("price"), "price")
    volume = _require_int(tick.get("volume"), "volume")

    payload = {
        "trade_id": trade_id,
        "trade_time": trade_time,
        "price": price,
        "volume": volume,
    }
    redis_client = get_redis_connection("default")
    redis_client.zadd(
        _trade_tick_key(normalized_stock_code),
        {_serialize_payload(payload): collected_at.timestamp()},
        nx=True,
    )
    trim_ticks(normalized_stock_code, now=collected_at)


def save_quote_tick(stock_code: str, tick: dict, now: datetime | None = None) -> None:
    normalized_stock_code = validate_stock_code(stock_code)
    collected_at = _resolve_now(now)

    quote_time = _require_text(tick.get("quote_time"), "quote_time")
    _parse_time_or_raise(quote_time, "quote_time")
    ask_price = _require_int(tick.get("ask_price"), "ask_price")
    bid_price = _require_int(tick.get("bid_price"), "bid_price")

    payload = {
        "quote_time": quote_time,
        "ask_price": ask_price,
        "bid_price": bid_price,
    }
    redis_client = get_redis_connection("default")
    redis_client.zadd(
        _quote_tick_key(normalized_stock_code),
        {_serialize_payload(payload): collected_at.timestamp()},
        nx=True,
    )
    trim_ticks(normalized_stock_code, now=collected_at)


def trim_ticks(stock_code: str, now: datetime | None = None) -> None:
    normalized_stock_code = validate_stock_code(stock_code)
    current_time = _resolve_now(now)
    cutoff = (current_time - timedelta(hours=TICK_RETENTION_HOURS)).timestamp()

    redis_client = get_redis_connection("default")
    redis_client.zremrangebyscore(_trade_tick_key(normalized_stock_code), "-inf", cutoff)
    redis_client.zremrangebyscore(_quote_tick_key(normalized_stock_code), "-inf", cutoff)


def get_recent_price_flow(stock_code: str, minutes: int = 10) -> dict:
    normalized_stock_code = validate_stock_code(stock_code)
    if minutes <= 0:
        raise ValueError("minutes는 1 이상이어야 합니다")

    collected_at = _resolve_now(None)
    min_collected_at = collected_at - timedelta(minutes=minutes)

    redis_client = get_redis_connection("default")
    raw_ticks = redis_client.zrangebyscore(
        _trade_tick_key(normalized_stock_code),
        min_collected_at.timestamp(),
        "+inf",
        withscores=True,
    )

    price_flow = []
    for raw_member, score in raw_ticks:
        try:
            payload = json.loads(_decode_member(raw_member))
        except json.JSONDecodeError as exc:
            raise ValueError("메시지 JSON 파싱 실패") from exc

        price = _require_int(payload.get("price"), "price")
        tick_collected_at = datetime.fromtimestamp(float(score), tz=KST)
        price_flow.append(
            {
                "price": price,
                "collected_at": tick_collected_at.isoformat(),
            }
        )

    price_flow.sort(key=lambda item: item["collected_at"])
    return {
        "stock_code": normalized_stock_code,
        "collected_at": collected_at.isoformat(),
        "price_flow": price_flow,
    }


def _trade_tick_key(stock_code: str) -> str:
    return TRADE_TICK_KEY_PATTERN.format(stock_code=stock_code)


def _quote_tick_key(stock_code: str) -> str:
    return QUOTE_TICK_KEY_PATTERN.format(stock_code=stock_code)


def _resolve_now(now: datetime | None) -> datetime:
    base = now or timezone.now()
    if timezone.is_naive(base):
        return timezone.make_aware(base, KST)
    return base.astimezone(KST)


def _parse_time_or_raise(raw_time: str, field_name: str) -> None:
    try:
        datetime.strptime(raw_time, "%H:%M:%S")
    except ValueError as exc:
        raise ValueError(f"메시지 형식 파싱 실패: {field_name}") from exc


def _require_text(raw_value: object, field_name: str) -> str:
    text = str(raw_value).strip() if raw_value is not None else ""
    if not text:
        raise ValueError(f"웹소켓 필수 필드 누락: {field_name}")
    return text


def _require_int(raw_value: object, field_name: str) -> int:
    if raw_value in (None, ""):
        raise ValueError(f"웹소켓 필수 필드 누락: {field_name}")
    try:
        return int(str(raw_value).strip().replace(",", ""))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"메시지 숫자 파싱 실패: {field_name}") from exc


def _serialize_payload(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decode_member(raw_member: object) -> str:
    if isinstance(raw_member, bytes):
        return raw_member.decode("utf-8")
    return str(raw_member)
