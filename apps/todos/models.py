from django.db import models


class Todo(models.Model):
    class Status(models.TextChoices):
        TODO = "TODO", "할 일"
        IN_PROGRESS = "IN_PROGRESS", "진행 중"
        DONE = "DONE", "완료"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TODO, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title
