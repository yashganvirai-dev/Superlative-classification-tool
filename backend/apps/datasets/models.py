from django.db import models


class Dataset(models.Model):
    model = models.OneToOneField(
        "models.MLModel",
        on_delete=models.CASCADE,
        related_name="dataset",
    )
    original_filename = models.CharField(max_length=255)
    storage_path = models.CharField(max_length=500)
    file_size = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    row_count = models.PositiveIntegerField()
    column_count = models.PositiveIntegerField()
    target_column = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.model.name} dataset"
