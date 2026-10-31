from django.core import signing
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from config.api import success

from .authentication import RefreshAuthentication
from .permissions import IsApprovedUser
from .serializers import (
    AccountTokenRefreshSerializer,
    LoginSerializer,
    LogoutSerializer,
    EmailRequestSerializer,
    RegistrationSerializer,
    UserSerializer,
)
from .services import (
    RegistrationConflict,
    register_developer,
    resend_verification_email,
    verify_developer_email,
)


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = register_developer(
                name=serializer.validated_data["name"],
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
            )
        except RegistrationConflict:
            return success(
                {
                    "message": "If the registration details are eligible, the account will require email verification and administrator approval."
                },
                status_code=status.HTTP_202_ACCEPTED,
            )
        return success(
            {
                "user": UserSerializer(result.user).data,
                "message": "Registration submitted for email verification and administrator approval.",
                "verification_email_sent": result.verification_email_sent,
            },
            status_code=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token", "")
        if not token:
            raise ValidationError({"token": "A verification token is required."})
        try:
            user = verify_developer_email(token)
        except (signing.BadSignature, signing.SignatureExpired, LookupError) as exc:
            raise ValidationError(
                {"token": "The verification link is invalid or expired."}
            ) from exc
        return success(
            {
                "email": user.email,
                "message": "Email verified. Your account is awaiting administrator approval.",
            }
        )


class ResendVerificationView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resend_verification_email(serializer.validated_data["email"])
        return success(
            {"message": "If the account is eligible, a verification email has been sent."},
            status_code=status.HTTP_202_ACCEPTED,
        )


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return success(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )


class RefreshView(APIView):
    authentication_classes = [RefreshAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AccountTokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return success(serializer.validated_data)


class LogoutView(APIView):
    permission_classes = [IsApprovedUser]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return success({"detail": "Logged out."})


class CurrentUserView(APIView):
    permission_classes = [IsApprovedUser]

    def get(self, request):
        return success(UserSerializer(request.user).data)

