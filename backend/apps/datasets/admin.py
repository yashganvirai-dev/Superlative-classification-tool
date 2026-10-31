from django.contrib import admin

from .models import Dataset


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = (
        "model",
        "original_filename",
        "row_count",
        "column_count",
        "target_column",
        "created_at",
    )
    search_fields = ("model__name", "original_filename", "target_column")
    readonly_fields = ("sha256", "created_at", "updated_at")
