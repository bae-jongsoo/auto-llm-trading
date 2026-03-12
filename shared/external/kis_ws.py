from __future__ import annotations

import logging
import signal
from collections.abc import Callable
from threading import Event

from django.conf import settings
from pykis import PyKis
from pykis.api.websocket.order_book import KisRealtimeOrderbook
from pykis.api.websocket.price import KisRealtimePrice
from pykis.event.subscription import KisSubscriptionEventArgs

from shared.stock_universe import validate_stock_code

logger = logging.getLogger(__name__)


def build_ws_subscribe_messages(stock_code: str) -> list[dict]:
    normalized_stock_code = validate_stock_code(stock_code)
    return [
        {
            "header": {
                "tr_type": "1",
                "tr_id": "H0STCNT0",
            },
            "body": {
                "input": {
                    "tr_id": "H0STCNT0",
                    "tr_key": normalized_stock_code,
                }
            },
        },
        {
            "header": {
                "tr_type": "1",
                "tr_id": "H0STASP0",
            },
            "body": {
                "input": {
                    "tr_id": "H0STASP0",
                    "tr_key": normalized_stock_code,
                }
            },
        },
    ]


def create_pykis_client() -> PyKis:
    return PyKis(
        id=settings.KIS_HTS_ID or None,
        appkey=settings.KIS_APP_KEY,
        secretkey=settings.KIS_APP_SECRET,
        account=settings.KIS_ACCT_STOCK or None,
        use_websocket=True,
        keep_token=True,
    )


def map_trade_event(response: KisRealtimePrice) -> tuple[str, dict]:
    """pykis 체결 이벤트 → save_trade_tick 이 받는 (stock_code, tick) 변환"""
    stock_code = str(response.symbol)
    time_kst = response.time_kst
    return stock_code, {
        "trade_id": f"{stock_code}_{time_kst.isoformat()}",
        "trade_time": time_kst.strftime("%H:%M:%S"),
        "price": int(response.price),
        "volume": int(response.volume),
    }


def map_orderbook_event(response: KisRealtimeOrderbook) -> tuple[str, dict]:
    """pykis 호가 이벤트 → save_quote_tick 이 받는 (stock_code, tick) 변환"""
    stock_code = str(response.symbol)
    time_kst = response.time_kst
    return stock_code, {
        "quote_time": time_kst.strftime("%H:%M:%S"),
        "ask_price": int(response.asks[0].price),
        "bid_price": int(response.bids[0].price),
    }


def run_realtime_subscribe(
    stock_codes: list[str],
    on_trade: Callable[[str, dict], None],
    on_orderbook: Callable[[str, dict], None],
) -> None:
    """KIS WebSocket 구독 시작. SIGTERM/SIGINT 까지 블로킹."""
    kis = create_pykis_client()
    stop = Event()

    def _on_price(
        _client: object,
        event: KisSubscriptionEventArgs[KisRealtimePrice],
    ) -> None:
        try:
            stock_code, tick = map_trade_event(event.response)
            on_trade(stock_code, tick)
        except Exception:
            logger.exception("체결 이벤트 처리 실패")

    def _on_orderbook(
        _client: object,
        event: KisSubscriptionEventArgs[KisRealtimeOrderbook],
    ) -> None:
        try:
            stock_code, tick = map_orderbook_event(event.response)
            on_orderbook(stock_code, tick)
        except Exception:
            logger.exception("호가 이벤트 처리 실패")

    tickets = []
    for code in stock_codes:
        stock = kis.stock(symbol=code, market="KRX")
        tickets.append(stock.on(event="price", callback=_on_price))
        tickets.append(stock.on(event="orderbook", callback=_on_orderbook))

    logger.info("ws 구독 시작 종목수=%d", len(stock_codes))

    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())

    try:
        while not stop.is_set():
            stop.wait(1.0)
    finally:
        kis.websocket.disconnect()
        logger.info("ws 구독 종료")
