from django.db import models
from django.db.models import Q
from shared.models import StockNamedMixin


class Asset(StockNamedMixin, models.Model):
    """자산 단건(현금 또는 보유종목). stock_code 가 NULL이면 현금 row로 간주."""

    stock_code = models.CharField(
        max_length=32,
        null=True,
        blank=False,
        verbose_name="stock code",
    )
    quantity = models.BigIntegerField(
        verbose_name="quantity",
    )
    unit_price = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name="unit price",
    )
    total_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name="total amount",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="created at",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="updated at",
    )

    @property
    def is_cash(self) -> bool:
        return self.stock_code is None

    class Meta:
        indexes = [
            models.Index(fields=["stock_code"]),
            models.Index(fields=["stock_code", "updated_at"]),
        ]

    def __str__(self) -> str:
        return f"CASH ({self.total_amount})" if self.is_cash else f"{self.stock_code} x {self.quantity}"
