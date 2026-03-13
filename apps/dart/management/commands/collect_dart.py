from __future__ import annotations

import logging

from django.core.management.base import BaseCommand, CommandError

from apps.dart import services
from shared.stock_universe import validate_stock_code

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "다트 공시를 수집합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--stock-codes",
            type=str,
            default="",
            help="쉼표(,)로 구분한 종목코드 목록",
        )

    def handle(self, *args, **options):
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

        result = services.collect_dart(stock_codes=stock_codes)

        logger.info(
            "다트 공시 수집 완료 종목=%s fetched=%s saved=%s",
            result["stock_codes"],
            result["fetched_items"],
            result["saved_items"],
        )
