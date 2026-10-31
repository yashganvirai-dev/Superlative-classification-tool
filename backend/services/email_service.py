"""Transactional email notifications for account workflows."""

from urllib.parse import quote

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail


EMAIL_VERIFICATION_SALT = "superlative.accounts.email-verification"


def create_email_verification_token(user) -> str:
    return signing.dumps(
        {"user_id": user.pk, "email": user.email},
        salt=EMAIL_VERIFICATION_SALT,
        compress=True,
    )


def send_email_verification(user) -> int:
    token = create_email_verification_token(user)
    verification_url = (
        f"{settings.FRONTEND_BASE_URL}/verify-email?token={quote(token)}"
    )
    subject = "Verify your Superlative Classification email"
    message = (
        f"Hello {user.name},\n\n"
        "Verify your email address using the link below. Your account will remain "
        "pending until an administrator approves it.\n\n"
        f"{verification_url}\n"
    )
    return send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def send_new_registration_admin_email(user) -> int:
    """Notify configured Super Admins that a new developer registered."""
    recipients = list(getattr(settings, "SUPER_ADMIN_EMAILS", []) or [])
    if not recipients:
        possible_admins = []
        if hasattr(user, "_meta"):
            from apps.accounts.models import User, UserRole

            possible_admins = list(
                User.objects.filter(
                    role=UserRole.SUPER_ADMIN,
                    is_active=True,
                    is_staff=True,
                ).values_list("email", flat=True)
            )
        if possible_admins:
            recipients = possible_admins
        else:
            recipients = [settings.DEFAULT_FROM_EMAIL]

    subject = f"New developer registration: {user.name}"
    message = (
        f"A new developer has registered for approval.\n\n"
        f"Name: {user.name}\n"
        f"Email: {user.email}\n"
        f"Role: {user.role}\n\n"
        f"Review pending developers here: {settings.FRONTEND_BASE_URL}/admin/approvals\n"
    )
    return send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        recipients,
        fail_silently=False,
    )


def send_approval_email(user) -> int:
    """Notify a developer that their account is approved."""
    subject = "Your Superlative Classification account is approved"
    message = (
        f"Hello {user.name},\n\n"
        "Your Superlative Classification account has been approved. "
        f"You can now sign in at {settings.FRONTEND_BASE_URL}/login.\n"
    )
    return send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
