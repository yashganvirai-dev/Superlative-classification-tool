"""Authentication and platform-access permissions."""

from rest_framework.permissions import BasePermission

from .models import ApprovalStatus, UserRole


def can_access_platform(user) -> bool:
    return bool(
        getattr(user, "is_authenticated", False)
        and user.is_active
        and user.email_verified
        and user.approval_status == ApprovalStatus.APPROVED
    )


class IsApprovedUser(BasePermission):
    message = "Your account is not approved for platform access."

    def has_permission(self, request, view) -> bool:
        return can_access_platform(request.user)


class IsSuperAdmin(BasePermission):
    message = "Super Admin access is required."

    def has_permission(self, request, view) -> bool:
        return can_access_platform(request.user) and request.user.role == UserRole.SUPER_ADMIN
