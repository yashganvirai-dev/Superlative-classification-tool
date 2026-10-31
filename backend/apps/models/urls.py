from django.urls import path

from .views import AutomaticModelCreateView, ModelDetailView, ModelListCreateView


urlpatterns = [
    path("", ModelListCreateView.as_view(), name="model-list-create"),
    path("automatic/", AutomaticModelCreateView.as_view(), name="model-create-automatic"),
    path("<int:model_id>/", ModelDetailView.as_view(), name="model-detail"),
]
