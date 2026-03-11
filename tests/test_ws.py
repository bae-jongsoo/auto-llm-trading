from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

import pytest
from django.utils import timezone
from django_redis import get_redis_connection

from apps.ws.services import (
    get_recent_price_flow,
    save_quote_tick,
    save_trade_tick,
    trim_ticks,
)
from shared.external.kis_ws import build_ws_subscribe_messages
from shared.stock_universe import TARGET_STOCKS


@pytest.fixture
def redis_client():
    client = get_redis_connection("default")
    client.flushdb()
    yield client
    client.flushdb()


def _체결_tick(
    *,
    trade_id: str = "trade-1",
    trade_time: str = "09:00:00",
    price: int = 70000,
    volume: int = 3,
) -> dict:
    return {
        "trade_id": trade_id,
        "trade_time": trade_time,
        "price": price,
        "volume": volume,
    }


def _호가_tick(
    *,
    quote_time: str = "09:00:01",
    ask_price: int = 70100,
    bid_price: int = 70000,
) -> dict:
    return {
        "quote_time": quote_time,
        "ask_price": ask_price,
        "bid_price": bid_price,
    }


def _to_datetime(raw: object) -> datetime:
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    raise AssertionError("datetime 또는 ISO 문자열이어야 합니다")


def _결과_흐름(result: dict) -> list[dict]:
    assert "price_flow" in result
    assert isinstance(result["price_flow"], list)
    return result["price_flow"]


def _흐름_가격(point: dict) -> int:
    assert "price" in point
    return int(point["price"])


def _흐름_시각(point: dict) -> datetime:
    assert "collected_at" in point
    collected_at = _to_datetime(point["collected_at"])
    assert collected_at.tzinfo is not None
    return collected_at


def _메시지_tr_id(message: dict) -> str | None:
    return (
        message.get("body", {}).get("input", {}).get("tr_id")
        or message.get("header", {}).get("tr_id")
        or message.get("tr_id")
    )


def _메시지_tr_key(message: dict) -> str | None:
    return (
        message.get("body", {}).get("input", {}).get("tr_key")
        or message.get("tr_key")
    )


# ──────────────────────────────────────
# build_ws_subscribe_messages
# ──────────────────────────────────────

def test_웹소켓_구독메시지_생성_성공_체결호가2건():
    messages = build_ws_subscribe_messages("005930")

    assert isinstance(messages, list)
    assert len(messages) == 2
    assert all(isinstance(message, dict) for message in messages)
    assert {_메시지_tr_key(message) for message in messages} == {"005930"}
    assert {_메시지_tr_id(message) for message in messages} == {"H0STCNT0", "H0STASP0"}


def test_웹소켓_구독메시지_대상10종목_전체_생성_성공():
    for stock_code in TARGET_STOCKS:
        messages = build_ws_subscribe_messages(stock_code)
        assert len(messages) == 2
        assert {_메시지_tr_key(message) for message in messages} == {stock_code}
        assert {_메시지_tr_id(message) for message in messages} == {"H0STCNT0", "H0STASP0"}


def test_웹소켓_구독메시지_지원하지_않는_종목코드_실패():
    with pytest.raises(ValueError, match="지원하지 않는 종목코드"):
        build_ws_subscribe_messages("999999")


# ──────────────────────────────────────
# save_trade_tick / save_quote_tick / trim_ticks / get_recent_price_flow
# ──────────────────────────────────────

def test_체결틱_저장_성공_최근가격흐름_반영(redis_client):
    now = timezone.now().replace(microsecond=0)

    save_trade_tick("005930", _체결_tick(price=70100), now=now)
    result = get_recent_price_flow("005930", minutes=10)

    flow = _결과_흐름(result)
    assert len(flow) == 1
    assert _흐름_가격(flow[0]) == 70100


def test_체결틱_저장_대상10종목_전체_허용(redis_client):
    now = timezone.now().replace(microsecond=0)

    for index, stock_code in enumerate(TARGET_STOCKS):
        save_trade_tick(
            stock_code,
            _체결_tick(trade_id=f"trade-{index}", price=70000 + index),
            now=now,
        )

    for index, stock_code in enumerate(TARGET_STOCKS):
        result = get_recent_price_flow(stock_code, minutes=10)
        flow = _결과_흐름(result)
        assert len(flow) == 1
        assert _흐름_가격(flow[0]) == 70000 + index


def test_호가틱_저장_성공_체결과_키분리(redis_client):
    now = timezone.now().replace(microsecond=0)

    save_trade_tick("005930", _체결_tick(trade_id="trade-sep"), now=now)
    save_quote_tick("005930", _호가_tick(), now=now)

    keys = [
        key.decode("utf-8") if isinstance(key, bytes) else str(key)
        for key in redis_client.keys("*")
    ]
    stock_keys = [key for key in keys if "005930" in key]
    assert len(stock_keys) >= 2


def test_체결틱_저장시_1시간_이전_데이터_자동삭제(redis_client):
    start = timezone.now().replace(microsecond=0)

    save_trade_tick("005930", _체결_tick(trade_id="old", price=70000), now=start)
    save_trade_tick(
        "005930",
        _체결_tick(trade_id="new", price=71000),
        now=start + timedelta(minutes=61),
    )

    result = get_recent_price_flow("005930", minutes=120)
    prices = [_흐름_가격(point) for point in _결과_흐름(result)]
    assert prices == [71000]


def test_trim_ticks_성공_1시간_윈도우밖_삭제(redis_client):
    base = timezone.now().replace(microsecond=0)

    save_trade_tick("005930", _체결_tick(trade_id="old", price=70000), now=base)
    save_trade_tick(
        "005930",
        _체결_tick(trade_id="mid", price=70500),
        now=base + timedelta(minutes=30),
    )

    trim_ticks("005930", now=base + timedelta(minutes=61))
    result = get_recent_price_flow("005930", minutes=120)

    prices = [_흐름_가격(point) for point in _결과_흐름(result)]
    assert prices == [70500]


def test_최근가격흐름_10분조회_시간순_정렬(redis_client):
    now = timezone.now().replace(microsecond=0)
    old_time = now - timedelta(minutes=5)
    new_time = now - timedelta(minutes=1)

    save_trade_tick("005930", _체결_tick(trade_id="new", price=72000), now=new_time)
    save_trade_tick("005930", _체결_tick(trade_id="old", price=70000), now=old_time)

    result = get_recent_price_flow("005930", minutes=10)
    flow = _결과_흐름(result)

    assert [_흐름_가격(point) for point in flow] == [70000, 72000]
    timestamps = [_흐름_시각(point) for point in flow]
    assert timestamps == sorted(timestamps)


def test_최근가격흐름_프롬프트포함형태_가격흐름과_수집시각(redis_client):
    now = timezone.now().replace(microsecond=0)

    save_trade_tick("005930", _체결_tick(price=70300), now=now)
    result = get_recent_price_flow("005930", minutes=10)

    assert result["stock_code"] == "005930"
    assert "collected_at" in result
    assert _to_datetime(result["collected_at"]).tzinfo is not None
    assert len(_결과_흐름(result)) >= 1
    assert all("price" in point and "collected_at" in point for point in _결과_흐름(result))


def test_시간정책_KST_기준_수집시각_반환(redis_client):
    utc_now = datetime.now(dt_timezone.utc).replace(microsecond=0)

    save_trade_tick("005930", _체결_tick(price=70500), now=utc_now)
    result = get_recent_price_flow("005930", minutes=10)

    top_collected_at = _to_datetime(result["collected_at"])
    first_point_collected_at = _흐름_시각(_결과_흐름(result)[0])
    assert top_collected_at.utcoffset().total_seconds() == 9 * 60 * 60
    assert first_point_collected_at.utcoffset().total_seconds() == 9 * 60 * 60


def test_체결틱_지원하지_않는_종목코드_실패(redis_client):
    with pytest.raises(ValueError, match="지원하지 않는 종목코드"):
        save_trade_tick("999999", _체결_tick(), now=timezone.now())


def test_체결틱_웹소켓_필수필드_누락_실패(redis_client):
    with pytest.raises(ValueError, match="필수|누락"):
        save_trade_tick("005930", {"trade_id": "missing-price"}, now=timezone.now())


def test_호가틱_웹소켓_필수필드_누락_실패(redis_client):
    with pytest.raises(ValueError, match="필수|누락"):
        save_quote_tick("005930", {"quote_time": "09:00:01"}, now=timezone.now())


def test_체결틱_비정상_메시지_파싱실패(redis_client):
    with pytest.raises(ValueError, match="파싱|형식|메시지|JSON"):
        save_trade_tick(
            "005930",
            _체결_tick(trade_time="invalid-time-format"),
            now=timezone.now(),
        )


def test_체결틱_저장_Redis_연결실패():
    with patch(
        "apps.ws.services.get_redis_connection",
        side_effect=ConnectionError("Redis connection refused"),
        create=True,
    ):
        with pytest.raises(Exception, match="Redis|redis|Connection|연결|refused|거부"):
            save_trade_tick("005930", _체결_tick(), now=timezone.now())


def test_연결재개_중복체결틱_중복저장_방지(redis_client):
    now = timezone.now().replace(microsecond=0)
    duplicated_tick = _체결_tick(
        trade_id="dup-1",
        trade_time="09:01:00",
        price=70900,
        volume=5,
    )

    save_trade_tick("005930", duplicated_tick, now=now)
    save_trade_tick("005930", duplicated_tick, now=now)

    result = get_recent_price_flow("005930", minutes=10)
    flow = _결과_흐름(result)
    assert len(flow) == 1
    assert _흐름_가격(flow[0]) == 70900
