from __future__ import annotations

import logging
from datetime import time
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.trader.services import run_trading_cycle

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")
MARKET_OPEN = time(9, 11)
MARKET_CLOSE = time(15, 30)


class Command(BaseCommand):
    help = "트레이딩 사이클을 1회 실행합니다."

    def handle(self, *args, **options):
        now_kst = timezone.now().astimezone(KST)
        if not (MARKET_OPEN <= now_kst.time() <= MARKET_CLOSE):
            return

        decision = run_trading_cycle()

        logger.info(
            "트레이딩 1회 실행 완료 result=%s is_error=%s decision_history_id=%s",
            decision.result,
            decision.is_error,
            decision.id,
        )
