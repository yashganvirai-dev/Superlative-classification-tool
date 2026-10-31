from django.contrib import admin

from .models import MLModel


@admin.register(MLModel)
class MLModelAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner",
        "model_type",
        "status",
        "created_at",
    )
    list_filter = ("model_type", "status")
    search_fields = ("name", "owner__email", "owner__name")
    readonly_fields = ("created_at", "updated_at")
