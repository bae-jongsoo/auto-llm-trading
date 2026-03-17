from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

import pytest
from django.utils import timezone
from django_redis import get_redis_connection

from apps.ws.models import MinuteCandle
from apps.ws.services import (
    build_candles,
    save_quote_tick,
    save_trade_tick,
    trim_ticks,
)
from shared.stock_universe import TARGET_STOCKS, validate_stock_code


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


def _build_ws_subscribe_messages(stock_code: str) -> list[dict]:
    normalized = validate_stock_code(stock_code)
    return [
        {"header": {"tr_type": "1", "tr_id": "H0STCNT0"}, "body": {"input": {"tr_id": "H0STCNT0", "tr_key": normalized}}},
        {"header": {"tr_type": "1", "tr_id": "H0STASP0"}, "body": {"input": {"tr_id": "H0STASP0", "tr_key": normalized}}},
    ]


def test_웹소켓_구독메시지_생성_성공_체결호가2건():
    messages = _build_ws_subscribe_messages("005930")

    assert isinstance(messages, list)
    assert len(messages) == 2
    assert all(isinstance(message, dict) for message in messages)
    assert {_메시지_tr_key(message) for message in messages} == {"005930"}
    assert {_메시지_tr_id(message) for message in messages} == {"H0STCNT0", "H0STASP0"}


def test_웹소켓_구독메시지_대상10종목_전체_생성_성공():
    for stock_code in TARGET_STOCKS:
        messages = _build_ws_subscribe_messages(stock_code)
        assert len(messages) == 2
        assert {_메시지_tr_key(message) for message in messages} == {stock_code}
        assert {_메시지_tr_id(message) for message in messages} == {"H0STCNT0", "H0STASP0"}


def test_웹소켓_구독메시지_지원하지_않는_종목코드_실패():
    with pytest.raises(ValueError, match="지원하지 않는 종목코드"):
        _build_ws_subscribe_messages("999999")


# ──────────────────────────────────────
# save_trade_tick / save_quote_tick / trim_ticks
# ──────────────────────────────────────

@pytest.mark.django_db
def test_체결틱_저장_성공(redis_client):
    now = timezone.now().replace(microsecond=0)
    save_trade_tick("005930", _체결_tick(price=70100), now=now)

    candles = build_candles("005930", minutes=10)
    assert len(candles) == 1
    assert candles[0].close == 70100


@pytest.mark.django_db
def test_체결틱_저장_대상10종목_전체_허용(redis_client):
    now = timezone.now().replace(microsecond=0)

    for index, stock_code in enumerate(TARGET_STOCKS):
        save_trade_tick(
            stock_code,
            _체결_tick(trade_id=f"trade-{index}", price=70000 + index),
            now=now,
        )

    for index, stock_code in enumerate(TARGET_STOCKS):
        candles = build_candles(stock_code, minutes=10)
        assert len(candles) == 1
        assert candles[0].close == 70000 + index


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


@pytest.mark.django_db
def test_체결틱_저장시_1시간_이전_데이터_자동삭제(redis_client):
    start = timezone.now().replace(microsecond=0)

    save_trade_tick("005930", _체결_tick(trade_id="old", price=70000), now=start)
    save_trade_tick(
        "005930",
        _체결_tick(trade_id="new", price=71000),
        now=start + timedelta(minutes=61),
    )

    candles = build_candles("005930", minutes=120)
    assert len(candles) == 1
    assert candles[0].close == 71000


@pytest.mark.django_db
def test_trim_ticks_성공_1시간_윈도우밖_삭제(redis_client):
    base = timezone.now().replace(microsecond=0)

    save_trade_tick("005930", _체결_tick(trade_id="old", price=70000), now=base)
    save_trade_tick(
        "005930",
        _체결_tick(trade_id="mid", price=70500),
        now=base + timedelta(minutes=30),
    )

    trim_ticks("005930", now=base + timedelta(minutes=61))
    candles = build_candles("005930", minutes=120)

    assert len(candles) == 1
    assert candles[0].close == 70500


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


@pytest.mark.django_db
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

    candles = build_candles("005930", minutes=10)
    assert len(candles) == 1
    assert candles[0].close == 70900


# ──────────────────────────────────────
# build_candles
# ──────────────────────────────────────

@pytest.mark.django_db
def test_분봉_OHLCV_정확성(redis_client):
    now = timezone.now().replace(second=0, microsecond=0)

    save_trade_tick("005930", _체결_tick(trade_id="t1", price=100, volume=10), now=now)
    save_trade_tick("005930", _체결_tick(trade_id="t2", price=120, volume=20), now=now + timedelta(seconds=10))
    save_trade_tick("005930", _체결_tick(trade_id="t3", price=90, volume=30), now=now + timedelta(seconds=20))
    save_trade_tick("005930", _체결_tick(trade_id="t4", price=110, volume=40), now=now + timedelta(seconds=30))

    candles = build_candles("005930", minutes=10)

    assert len(candles) == 1
    c = candles[0]
    assert c.stock_code == "005930"
    assert c.open == 100
    assert c.high == 120
    assert c.low == 90
    assert c.close == 110
    assert c.volume == 100  # 10+20+30+40


@pytest.mark.django_db
def test_분봉_여러분_생성(redis_client):
    now = timezone.now().replace(second=0, microsecond=0)

    # 첫 번째 분
    save_trade_tick("005930", _체결_tick(trade_id="t1", price=100, volume=10), now=now)
    # 두 번째 분
    save_trade_tick("005930", _체결_tick(trade_id="t2", price=200, volume=20), now=now + timedelta(minutes=1))
    # 세 번째 분
    save_trade_tick("005930", _체결_tick(trade_id="t3", price=300, volume=30), now=now + timedelta(minutes=2))

    candles = build_candles("005930", minutes=10)

    assert len(candles) == 3
    assert candles[0].close == 100
    assert candles[1].close == 200
    assert candles[2].close == 300


@pytest.mark.django_db
def test_분봉_빈_틱_빈_리스트(redis_client):
    candles = build_candles("005930", minutes=10)
    assert candles == []


@pytest.mark.django_db
def test_분봉_upsert_중복_실행_레코드_1개(redis_client):
    now = timezone.now().replace(microsecond=0)

    save_trade_tick("005930", _체결_tick(trade_id="t1", price=100, volume=10), now=now)

    build_candles("005930", minutes=10)
    build_candles("005930", minutes=10)

    assert MinuteCandle.objects.filter(stock_code="005930").count() == 1


@pytest.mark.django_db
def test_분봉_upsert_업데이트_반영(redis_client):
    now = timezone.now().replace(second=0, microsecond=0)

    save_trade_tick("005930", _체결_tick(trade_id="t1", price=100, volume=10), now=now)
    build_candles("005930", minutes=10)

    save_trade_tick("005930", _체결_tick(trade_id="t2", price=200, volume=20), now=now + timedelta(seconds=10))
    candles = build_candles("005930", minutes=10)

    assert MinuteCandle.objects.filter(stock_code="005930").count() == 1
    assert candles[0].close == 200
    assert candles[0].high == 200
    assert candles[0].volume == 30  # 10+20


@pytest.mark.django_db
def test_분봉_DB_저장_확인(redis_client):
    now = timezone.now().replace(microsecond=0)

    save_trade_tick("005930", _체결_tick(trade_id="t1", price=100, volume=10), now=now)
    build_candles("005930", minutes=10)

    db_candle = MinuteCandle.objects.get(stock_code="005930")
    assert db_candle.open == 100
    assert db_candle.close == 100
    assert db_candle.volume == 10
