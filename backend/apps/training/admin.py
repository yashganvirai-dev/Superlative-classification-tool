from django.contrib import admin

from .models import TrainingJob


@admin.register(TrainingJob)
class TrainingJobAdmin(admin.ModelAdmin):
    list_display = (
        "model",
        "status",
        "progress",
        "algorithm",
        "created_at",
        "completed_at",
    )
    list_filter = ("status", "algorithm")
    search_fields = ("model__name", "model__owner__email")
    readonly_fields = ("created_at", "started_at", "completed_at")
