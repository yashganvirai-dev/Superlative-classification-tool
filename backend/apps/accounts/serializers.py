from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .permissions import can_access_platform


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "name",
            "email",
            "role",
            "approval_status",
            "is_active",
            "email_verified",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class RegistrationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Password confirmation does not match."}
            )
        validate_password(
            attrs["password"],
            user=User(name=attrs["name"], email=attrs["email"]),
        )
        return attrs


class EmailRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        attrs["email"] = attrs["email"].strip().lower()
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["email"],
            password=attrs["password"],
        )
        if user is None or not can_access_platform(user):
            raise serializers.ValidationError(
                "Unable to log in with the provided credentials.",
                code="invalid_credentials",
            )
        attrs["user"] = user
        return attrs


class AccountTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])
        user = User.objects.filter(pk=refresh.get("user_id")).first()
        if user is None or not can_access_platform(user):
            raise AuthenticationFailed("The account is not active.")
        return super().validate(attrs)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        refresh = RefreshToken(attrs["refresh"])
        if str(refresh.get("user_id")) != str(self.context["request"].user.pk):
            raise AuthenticationFailed("The refresh token does not belong to this account.")
        refresh.blacklist()
        return attrs
