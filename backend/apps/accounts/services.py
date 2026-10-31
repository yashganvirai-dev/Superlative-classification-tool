"""Developer registration and approval business operations."""

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.db import IntegrityError, transaction
from django.utils import timezone

from services.email_service import (
    EMAIL_VERIFICATION_SALT,
    send_approval_email,
    send_email_verification,
    send_new_registration_admin_email,
)

from .models import ApprovalStatus, User, UserRole


logger = logging.getLogger("superlative.accounts")


class ApprovalStateError(Exception):
    """Raised when an account is not in a reviewable state."""


class RegistrationConflict(Exception):
    """Raised when a concurrent registration wins an email uniqueness race."""


@dataclass(frozen=True)
class RegistrationResult:
    user: User
    verification_email_sent: bool


def _send_and_record_verification(user: User) -> bool:
    sent_at = timezone.now()
    user.verification_email_sent_at = sent_at
    user.save(update_fields=["verification_email_sent_at", "updated_at"])
    try:
        sent = send_email_verification(user) > 0
        if not sent:
            User.objects.filter(pk=user.pk).update(verification_email_sent_at=None)
        return sent
    except Exception:
        User.objects.filter(pk=user.pk).update(verification_email_sent_at=None)
        raise


def _verification_resend_is_cooling_down(user: User) -> bool:
    if user.verification_email_sent_at is None:
        return False
    age = timezone.now() - user.verification_email_sent_at
    return age < timedelta(seconds=settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS)


@dataclass(frozen=True)
class ApprovalResult:
    user: User
    email_sent: bool


def register_developer(*, name: str, email: str, password: str) -> RegistrationResult:
    """Create a developer and send a verification email."""
    try:
        with transaction.atomic():
            user = User.objects.create_user(
                name=name,
                email=email,
                password=password,
                role=UserRole.DEVELOPER,
                approval_status=ApprovalStatus.PENDING,
                is_active=False,
                email_verified=False,
            )
    except IntegrityError as exc:
        raise RegistrationConflict("A user with this email already exists.") from exc

    try:
        verification_email_sent = _send_and_record_verification(user)
    except Exception:
        logger.exception("Verification email failed for user %s", user.pk)
        verification_email_sent = False

    try:
        send_new_registration_admin_email(user)
    except Exception:
        logger.exception("Admin notification email failed for newly registered user %s", user.pk)

    logger.info("Developer registration submitted for user %s", user.pk)
    return RegistrationResult(
        user=user,
        verification_email_sent=verification_email_sent,
    )


def verify_developer_email(token: str) -> User:
    payload = signing.loads(
        token,
        salt=EMAIL_VERIFICATION_SALT,
        max_age=settings.EMAIL_VERIFICATION_TOKEN_MAX_AGE,
    )
    user = User.objects.filter(
        pk=payload.get("user_id"),
        email__iexact=payload.get("email", ""),
    ).first()
    if user is None:
        raise LookupError("Email verification link is invalid.")
    if not user.email_verified:
        user.email_verified = True
        user.save(update_fields=["email_verified", "updated_at"])
        logger.info("Email verified for user %s", user.pk)
    return user


def resend_verification_email(email: str) -> bool:
    try:
        with transaction.atomic():
            user = User.objects.select_for_update().filter(
                email__iexact=email.strip().lower(),
                email_verified=False,
                approval_status__in=[ApprovalStatus.PENDING, ApprovalStatus.REJECTED],
            ).first()
            if user is None or _verification_resend_is_cooling_down(user):
                return False
            return _send_and_record_verification(user)
    except Exception:
        logger.exception("Verification email resend failed")
        return False


def approve_developer(user_id: int, actor_id: int) -> ApprovalResult:
    """Approve a pending developer and attempt to send the approval email."""
    with transaction.atomic():
        user = User.objects.select_for_update().get(
            pk=user_id,
            role=UserRole.DEVELOPER,
        )
        if user.approval_status != ApprovalStatus.PENDING:
            raise ApprovalStateError("Only pending developer accounts can be approved.")
        if not user.email_verified:
            raise ApprovalStateError("The developer must verify their email before approval.")

        user.approval_status = ApprovalStatus.APPROVED
        user.is_active = True
        user.save(update_fields=["approval_status", "is_active", "updated_at"])

    try:
        email_sent = send_approval_email(user) > 0
    except Exception:
        logger.exception("Approval email failed for user %s", user.pk)
        email_sent = False

    logger.info("Developer account %s approved by admin %s", user.pk, actor_id)
    return ApprovalResult(user=user, email_sent=email_sent)


def resend_approval_email(user_id: int, actor_id: int) -> bool:
    """Retry delivery of an approval notification for an approved developer."""
    user = User.objects.get(pk=user_id, role=UserRole.DEVELOPER)
    if (
        user.approval_status != ApprovalStatus.APPROVED
        or not user.is_active
        or not user.email_verified
    ):
        raise ApprovalStateError("Approval email can only be resent to approved developers.")
    try:
        email_sent = send_approval_email(user) > 0
    except Exception:
        logger.exception("Approval email resend failed for user %s", user.pk)
        email_sent = False
    logger.info("Approval email resend attempted for user %s by admin %s", user.pk, actor_id)
    return email_sent


def reject_developer(user_id: int, actor_id: int) -> User:
    """Reject a pending developer and keep the account inactive."""
    with transaction.atomic():
        user = User.objects.select_for_update().get(
            pk=user_id,
            role=UserRole.DEVELOPER,
        )
        if user.approval_status != ApprovalStatus.PENDING:
            raise ApprovalStateError("Only pending developer accounts can be rejected.")

        user.approval_status = ApprovalStatus.REJECTED
        user.is_active = False
        user.save(update_fields=["approval_status", "is_active", "updated_at"])
    logger.info("Developer account %s rejected by admin %s", user.pk, actor_id)
    return user

