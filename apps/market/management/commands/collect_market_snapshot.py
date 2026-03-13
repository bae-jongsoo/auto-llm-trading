from __future__ import annotations

import logging
from datetime import time
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.market import services
from shared.stock_universe import validate_stock_code

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")
MARKET_OPEN = time(8, 58)
MARKET_CLOSE = time(15, 32)


class Command(BaseCommand):
    help = "종목 현재정보를 수집합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--stock-codes",
            type=str,
            default="",
            help="쉼표(,)로 구분한 종목코드 목록",
        )

    def handle(self, *args, **options):
        now_kst = timezone.now().astimezone(KST)
        if not (MARKET_OPEN <= now_kst.time() <= MARKET_CLOSE):
            return
        raw_stock_codes = (options.get("stock_codes") or "").strip()
        stock_codes = (
            [code.strip() for code in raw_stock_codes.split(",") if code.strip()]
            if raw_stock_codes
            else None
        )

        if stock_codes:
            for code in stock_codes:
                try:
                    validate_stock_code(code)
                except ValueError as exc:
                    raise CommandError(str(exc))

        result = services.collect_market_snapshots(stock_codes=stock_codes)

        logger.info(
            "종목 현재정보 수집 완료 종목=%s fetched=%s saved=%s",
            result["stock_codes"],
            result["fetched_items"],
            result["saved_items"],
        )
