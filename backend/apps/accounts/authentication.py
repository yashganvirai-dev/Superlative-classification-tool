"""JWT authentication with current account-state enforcement."""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .permissions import can_access_platform


class RefreshAuthentication(BaseAuthentication):
    """Ignore access-token headers while preserving a 401 challenge."""

    def authenticate(self, request):
        return None

    def authenticate_header(self, request):
        return "Bearer"


class ApprovedJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not can_access_platform(user):
            raise AuthenticationFailed("This account cannot access the platform.")
        return user
