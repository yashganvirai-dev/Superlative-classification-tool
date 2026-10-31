from django.apps import AppConfig


class ModelsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.models"
    verbose_name = "ML Models"

    def ready(self):
        from . import signals  # noqa: F401
