from django.db import models


class MinuteCandle(models.Model):
    stock_code = models.CharField(max_length=6)
    minute_at = models.DateTimeField()
    open = models.IntegerField()
    high = models.IntegerField()
    low = models.IntegerField()
    close = models.IntegerField()
    volume = models.BigIntegerField()

    class Meta:
        unique_together = ("stock_code", "minute_at")
        ordering = ["minute_at"]

    def __str__(self):
        return f"{self.stock_code} {self.minute_at} O={self.open} H={self.high} L={self.low} C={self.close} V={self.volume}"
