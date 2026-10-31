"""Super Admin user-management endpoints."""

from django.db.models import Count, Q
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.views import APIView

from config.api import success

from .models import ApprovalStatus, User, UserRole
from .permissions import IsSuperAdmin
from .serializers import UserSerializer
from .services import (
    ApprovalStateError,
    approve_developer,
    reject_developer,
    resend_approval_email,
)


class AdminUserListView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        status = request.query_params.get("status")
        if status and status not in ApprovalStatus.values:
            raise ValidationError({"status": "Unsupported approval status."})

        users = User.objects.all()
        if status:
            users = users.filter(approval_status=status)
        user_data = list(users.order_by("-created_at"))
        return success(
            {
                "users": UserSerializer(user_data, many=True).data,
                "count": len(user_data),
            }
        )


class PendingUserListView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        users = list(
            User.objects.filter(
                role=UserRole.DEVELOPER,
                approval_status=ApprovalStatus.PENDING,
            ).order_by("-created_at")
        )
        return success(
            {
                "users": UserSerializer(users, many=True).data,
                "count": len(users),
            }
        )


class AdminDashboardView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        counts = User.objects.aggregate(
            total_users=Count("id"),
            developers=Count("id", filter=Q(role=UserRole.DEVELOPER)),
            pending_developers=Count(
                "id",
                filter=Q(
                    role=UserRole.DEVELOPER,
                    approval_status=ApprovalStatus.PENDING,
                ),
            ),
            approved_developers=Count(
                "id",
                filter=Q(
                    role=UserRole.DEVELOPER,
                    approval_status=ApprovalStatus.APPROVED,
                ),
            ),
            rejected_developers=Count(
                "id",
                filter=Q(
                    role=UserRole.DEVELOPER,
                    approval_status=ApprovalStatus.REJECTED,
                ),
            ),
        )
        return success(counts)


class ApproveDeveloperView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request, user_id: int):
        try:
            result = approve_developer(user_id, request.user.pk)
        except User.DoesNotExist as exc:
            raise NotFound("Developer account not found.") from exc
        except ApprovalStateError as exc:
            raise ValidationError({"approval": str(exc)}) from exc
        return success(
            {
                "user": UserSerializer(result.user).data,
                "email_sent": result.email_sent,
            }
        )


class ResendApprovalEmailView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request, user_id: int):
        try:
            email_sent = resend_approval_email(user_id, request.user.pk)
        except User.DoesNotExist as exc:
            raise NotFound("Developer account not found.") from exc
        except ApprovalStateError as exc:
            raise ValidationError({"approval": str(exc)}) from exc
        return success({"email_sent": email_sent})


class RejectDeveloperView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request, user_id: int):
        try:
            user = reject_developer(user_id, request.user.pk)
        except User.DoesNotExist as exc:
            raise NotFound("Developer account not found.") from exc
        except ApprovalStateError as exc:
            raise ValidationError({"approval": str(exc)}) from exc
        return success({"user": UserSerializer(user).data})

