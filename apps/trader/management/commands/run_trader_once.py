from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.trader.services import run_trading_cycle


class Command(BaseCommand):
    help = "트레이딩 사이클을 1회 실행합니다."

    def handle(self, *args, **options):
        decision = run_trading_cycle()

        self.stdout.write("트레이딩 1회 실행 완료")
        self.stdout.write(
            "result={result} is_error={is_error} decision_history_id={id}".format(
                result=decision.result,
                is_error=decision.is_error,
                id=decision.id,
            )
        )
