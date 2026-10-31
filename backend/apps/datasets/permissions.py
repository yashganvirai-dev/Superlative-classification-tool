"""Dataset ownership permissions."""

from rest_framework.permissions import BasePermission

from apps.accounts.permissions import can_access_platform
from apps.accounts.models import UserRole

from apps.models.models import MLModel


def can_manage_dataset(user, model: MLModel) -> bool:
    if not can_access_platform(user):
        return False
    return user.role == UserRole.SUPER_ADMIN


class IsDatasetOwnerOrSuperAdmin(BasePermission):
    message = "You do not have permission to manage this dataset."

    def has_object_permission(self, request, view, obj) -> bool:
        model = obj if isinstance(obj, MLModel) else obj.model
        return can_manage_dataset(request.user, model)
