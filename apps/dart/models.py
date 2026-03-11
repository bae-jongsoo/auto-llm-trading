import hashlib

from django.db import models
from shared.models import CollectedRecord


class DartDisclosure(CollectedRecord):
    corp_code = models.CharField(
        max_length=64,
        verbose_name="corp code",
    )
    rcept_no = models.CharField(
        max_length=32,
        verbose_name="reception number",
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="title",
    )
    link = models.URLField(
        max_length=2048,
        blank=True,
        default="",
        verbose_name="link",
    )
    description = models.TextField(
        blank=True,
        null=True,
        default=None,
        verbose_name="description",
    )

    @staticmethod
    def build_external_id(corp_code: str, rcept_no: str) -> str:
        return hashlib.sha256(f"{corp_code}|{rcept_no}".encode("utf-8")).hexdigest()

    class Meta:
        indexes = [
            models.Index(fields=["corp_code"]),
        ]

    def __str__(self) -> str:
        return f"{self.stock_code} [{self.external_id}]"
