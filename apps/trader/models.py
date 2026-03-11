from django.db import models
from django.utils import timezone
from shared.models import StockNamedMixin


class DecisionHistory(models.Model):
    class Result(models.TextChoices):
        HOLD = "HOLD", "Hold"
        BUY = "BUY", "Buy"
        SELL = "SELL", "Sell"

    request_payload = models.TextField(
        verbose_name="request payload",
    )
    response_payload = models.TextField(
        verbose_name="response payload",
    )
    parsed_decision = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="parsed decision",
    )
    processing_time_ms = models.IntegerField(
        default=0,
        verbose_name="processing time (ms)",
    )
    is_error = models.BooleanField(
        default=False,
        verbose_name="is error",
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        default=None,
        verbose_name="error message",
    )
    result = models.CharField(
        max_length=16,
        choices=Result.choices,
        default=Result.HOLD,
        verbose_name="result",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="created at",
    )

    class Meta:
        indexes = [
            models.Index(fields=["result"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["is_error", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.id} [{self.result}]"


class OrderHistory(StockNamedMixin, models.Model):
    decision_history = models.ForeignKey(
        DecisionHistory,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name="decision history",
    )
    stock_code = models.CharField(
        max_length=32,
        verbose_name="stock code",
    )
    order_price = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name="order price",
    )
    order_quantity = models.BigIntegerField(
        verbose_name="order quantity",
    )
    order_total_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name="order total amount",
    )
    result_price = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name="result price",
    )
    result_quantity = models.BigIntegerField(
        verbose_name="result quantity",
    )
    result_total_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name="result total amount",
    )
    order_placed_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name="order placed at",
    )
    result_executed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="result executed at",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="created at",
    )

    class Meta:
        indexes = [
            models.Index(fields=["stock_code"]),
            models.Index(fields=["order_placed_at"]),
            models.Index(fields=["result_executed_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["stock_code", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.stock_code} x {self.order_quantity}"
