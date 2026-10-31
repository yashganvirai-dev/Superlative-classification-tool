from django.urls import path

from .views import MetricsView, PredictionSchemaView, PredictionView, TrainingView


urlpatterns = [
    path("<int:model_id>/training/", TrainingView.as_view(), name="model-training"),
    path("<int:model_id>/metrics/", MetricsView.as_view(), name="model-metrics"),
    path(
        "<int:model_id>/prediction/schema/",
        PredictionSchemaView.as_view(),
        name="model-prediction-schema",
    ),
    path(
        "<int:model_id>/prediction/",
        PredictionView.as_view(),
        name="model-prediction",
    ),
]
