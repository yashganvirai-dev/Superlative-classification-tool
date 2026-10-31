"""URL configuration for the backend API and Django admin."""

from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/admin/", include("apps.accounts.admin_urls")),
    path("api/models/", include("apps.models.urls")),
    path("api/models/", include("apps.datasets.urls")),
    path("api/models/", include("apps.training.urls")),
]
