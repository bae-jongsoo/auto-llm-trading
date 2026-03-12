from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.ws.services import save_quote_tick, save_trade_tick
from shared.external.kis import KisClient
from shared.stock_universe import TARGET_STOCKS


class Command(BaseCommand):
    help = "KIS 웹소켓 실시간 체결/호가 구독"

    def handle(self, *args, **options):
        stock_codes = list(TARGET_STOCKS.keys())

        self.stdout.write(f"ws 구독 시작 종목수={len(stock_codes)}")

        client = KisClient(use_websocket=True)
        client.subscribe_realtime(
            stock_codes=stock_codes,
            on_trade=lambda stock_code, tick: save_trade_tick(stock_code, tick),
            on_orderbook=lambda stock_code, tick: save_quote_tick(stock_code, tick),
        )
