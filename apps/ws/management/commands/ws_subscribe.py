from __future__ import annotations

from django.core.management.base import BaseCommand

from shared.external.kis_ws import build_ws_subscribe_messages
from shared.stock_universe import TARGET_STOCKS


class Command(BaseCommand):
    help = "대상 종목 웹소켓 구독 메시지를 생성합니다."

    def handle(self, *args, **options):
        messages: list[dict] = []
        for stock_code in TARGET_STOCKS.keys():
            messages.extend(build_ws_subscribe_messages(stock_code))

        self.stdout.write("웹소켓 구독 메시지 생성 완료")
        self.stdout.write(f"종목수={len(TARGET_STOCKS)} 메시지수={len(messages)}")
