from __future__ import annotations

from datetime import time
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.trader.services import run_trading_cycle

KST = ZoneInfo("Asia/Seoul")
MARKET_OPEN = time(9, 0)
MARKET_CLOSE = time(15, 30)


class Command(BaseCommand):
    help = "트레이딩 사이클을 1회 실행합니다."

    def handle(self, *args, **options):
        now_kst = timezone.now().astimezone(KST)
        if not (MARKET_OPEN <= now_kst.time() <= MARKET_CLOSE):
            return

        decision = run_trading_cycle()

        self.stdout.write("트레이딩 1회 실행 완료")
        self.stdout.write(
            "result={result} is_error={is_error} decision_history_id={id}".format(
                result=decision.result,
                is_error=decision.is_error,
                id=decision.id,
            )
        )
