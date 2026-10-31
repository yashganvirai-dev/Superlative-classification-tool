"""URL routes for Super Admin user management."""

from django.urls import path

from .admin_views import (
    AdminDashboardView,
    AdminUserListView,
    ApproveDeveloperView,
    PendingUserListView,
    RejectDeveloperView,
    ResendApprovalEmailView,
)


urlpatterns = [
    path("dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("users/", AdminUserListView.as_view(), name="admin-user-list"),
    path(
        "users/pending/",
        PendingUserListView.as_view(),
        name="admin-pending-user-list",
    ),
    path(
        "users/<int:user_id>/approve/",
        ApproveDeveloperView.as_view(),
        name="admin-approve-developer",
    ),
    path(
        "users/<int:user_id>/resend-approval/",
        ResendApprovalEmailView.as_view(),
        name="admin-resend-approval-email",
    ),
    path(
        "users/<int:user_id>/reject/",
        RejectDeveloperView.as_view(),
        name="admin-reject-developer",
    ),
]

