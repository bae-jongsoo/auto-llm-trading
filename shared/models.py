from django.db import models
from shared.stock_universe import STOCK_NAMES


class StockNamedMixin:
    @property
    def stock_name(self) -> str:
        stock_code = getattr(self, "stock_code", "")
        if not stock_code:
            return ""
        return STOCK_NAMES.get(stock_code, "")


class CollectedRecord(StockNamedMixin, models.Model):
    stock_code = models.CharField(
        max_length=32,
        verbose_name="stock code",
    )
    external_id = models.CharField(
        max_length=128,
        unique=True,
        verbose_name="external id",
    )
    published_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="published at",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="created at",
    )

    @staticmethod
    def build_external_id(*args, **kwargs) -> str:
        raise NotImplementedError("Implement build_external_id in concrete collected models.")

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["stock_code"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["published_at"]),
            models.Index(fields=["stock_code", "published_at"]),
            models.Index(fields=["stock_code", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.stock_code} [{self.external_id}]"
