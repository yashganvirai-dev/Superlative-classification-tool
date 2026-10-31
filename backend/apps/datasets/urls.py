from django.urls import path

from .views import DatasetView, TargetColumnView


urlpatterns = [
    path("<int:model_id>/dataset/", DatasetView.as_view(), name="model-dataset"),
    path(
        "<int:model_id>/dataset/target/",
        TargetColumnView.as_view(),
        name="model-dataset-target",
    ),
]
