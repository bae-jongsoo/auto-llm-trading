import hashlib

from django.db import models
from shared.models import CollectedRecord


class News(CollectedRecord):
    link = models.URLField(
        max_length=2048,
        blank=True,
        default="",
        verbose_name="link",
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="title",
    )
    summary = models.TextField(
        blank=True,
        null=True,
        default=None,
        verbose_name="summary",
    )
    useful = models.BooleanField(
        null=True,
        blank=True,
        default=None,
        verbose_name="useful",
    )
    description = models.TextField(
        blank=True,
        null=True,
        default=None,
        verbose_name="description",
    )

    @staticmethod
    def build_external_id(stock_code: str, link: str) -> str:
        return hashlib.sha256(f"{stock_code}|{link}".encode("utf-8")).hexdigest()

    class Meta:
        indexes = [
            models.Index(fields=["stock_code", "useful", "created_at"]),
        ]
        abstract = False

    def __str__(self):
        return f"{self.stock_code} [{self.external_id}]"
