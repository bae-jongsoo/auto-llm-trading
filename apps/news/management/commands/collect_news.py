from __future__ import annotations

import logging

from django.core.management.base import BaseCommand, CommandError

from apps.news import services
from shared.stock_universe import validate_stock_code

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "네이버 뉴스를 수집하고 요약합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--stock-codes",
            type=str,
            default="",
            help="쉼표(,)로 구분한 종목코드 목록",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="종목당 수집 건수 (기본: 10)",
        )

    def handle(self, *args, **options):
        raw_stock_codes = (options.get("stock_codes") or "").strip()
        stock_codes = (
            [code.strip() for code in raw_stock_codes.split(",") if code.strip()]
            if raw_stock_codes
            else None
        )
        limit = options["limit"]

        if stock_codes:
            for code in stock_codes:
                try:
                    validate_stock_code(code)
                except ValueError as exc:
                    raise CommandError(str(exc))

        result = services.collect_news(stock_codes=stock_codes, limit=limit)

        logger.info(
            "뉴스 수집 완료 종목=%s fetched=%s saved=%s summarized=%s",
            result["stock_codes"],
            result["fetched_items"],
            result["saved_items"],
            result["summarized_items"],
        )
