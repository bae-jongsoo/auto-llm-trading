from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.news import services


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

        result = services.collect_news(stock_codes=stock_codes, limit=limit)

        self.stdout.write("뉴스 수집 완료")
        self.stdout.write(
            "종목={stock_codes} fetched={fetched_items} saved={saved_items} summarized={summarized_items}".format(
                **result
            )
        )
