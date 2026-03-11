from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.market import services


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
        raw_stock_codes = (options.get("stock_codes") or "").strip()
        stock_codes = (
            [code.strip() for code in raw_stock_codes.split(",") if code.strip()]
            if raw_stock_codes
            else None
        )

        result = services.collect_market_snapshots(stock_codes=stock_codes)

        self.stdout.write("종목 현재정보 수집 완료")
        self.stdout.write(
            "종목={stock_codes} fetched={fetched_items} saved={saved_items}".format(
                **result
            )
        )
