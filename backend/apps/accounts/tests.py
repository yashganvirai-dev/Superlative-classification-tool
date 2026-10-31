from datetime import timedelta
from unittest.mock import patch
from urllib.parse import unquote

from django.contrib.auth import get_user_model
from django.core import mail
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken


User = get_user_model()


class UserModelTests(TestCase):
    def test_user_password_is_hashed_and_email_is_login_field(self):
        user = User.objects.create_user(
            name="Dataset Owner",
            email="Owner@Example.com",
            password="correct horse battery staple",
            is_active=True,
        )

        self.assertEqual(User.USERNAME_FIELD, "email")
        self.assertNotEqual(user.password, "correct horse battery staple")
        self.assertTrue(user.check_password("correct horse battery staple"))
        self.assertEqual(user.email, "owner@example.com")

    def test_superuser_manager_sets_admin_fields(self):
        user = User.objects.create_superuser(
            name="Platform Admin",
            email="admin@example.com",
            password="correct horse battery staple",
        )

        self.assertEqual(user.role, "SUPER_ADMIN")
        self.assertEqual(user.approval_status, "APPROVED")
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_superuser_manager_rejects_inactive_admin(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                name="Platform Admin",
                email="admin@example.com",
                password="correct horse battery staple",
                is_active=False,
            )

    def test_email_uniqueness_is_case_insensitive(self):
        User.objects.create_user(
            name="Dataset Owner",
            email="owner@example.com",
            password="correct horse battery staple",
            is_active=True,
        )
        admin_created_user = User(name="Admin User", email="Admin@Example.com")
        admin_created_user.set_password("correct horse battery staple")
        admin_created_user.save()
        self.assertEqual(admin_created_user.email, "admin@example.com")

        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(
                name="Another Owner",
                email="OWNER@EXAMPLE.COM",
                password="correct horse battery staple",
                is_active=True,
            )


class AuthenticationApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            name="Dataset Owner",
            email="owner@example.com",
            password="correct horse battery staple",
            is_active=True,
            email_verified=True,
            approval_status="APPROVED",
        )

    def test_login_returns_consistent_success_response(self):
        response = self.client.post(
            reverse("login"),
            {"email": self.user.email, "password": "correct horse battery staple"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertIn("access", response.data["data"])
        self.assertIn("refresh", response.data["data"])
        self.assertEqual(response.data["data"]["user"]["email"], self.user.email)

    def test_invalid_login_returns_consistent_error_response(self):
        response = self.client.post(
            reverse("login"),
            {"email": self.user.email, "password": "wrong-password"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "VALIDATION_ERROR")

    def test_inactive_user_cannot_receive_tokens(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(
            reverse("login"),
            {"email": self.user.email, "password": "correct horse battery staple"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])

    def test_pending_user_cannot_receive_tokens(self):
        self.user.approval_status = "PENDING"
        self.user.save(update_fields=["approval_status"])

        response = self.client.post(
            reverse("login"),
            {"email": self.user.email, "password": "correct horse battery staple"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])

    def test_current_user_requires_authentication(self):
        response = self.client.get(reverse("current-user"))

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "AUTHENTICATION_REQUIRED")

    def test_current_user_returns_authenticated_user(self):
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

        response = self.client.get(reverse("current-user"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["email"], self.user.email)

    def test_access_token_is_rejected_after_approval_is_revoked(self):
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        self.user.approval_status = "REJECTED"
        self.user.save(update_fields=["approval_status"])

        response = self.client.get(reverse("current-user"))

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.data["success"])

    def test_refresh_returns_access_token(self):
        refresh = RefreshToken.for_user(self.user)

        response = self.client.post(
            reverse("token-refresh"), {"refresh": str(refresh)}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertIn("access", response.data["data"])

    def test_refresh_ignores_an_expired_access_token(self):
        refresh = RefreshToken.for_user(self.user)
        expired_access = AccessToken.for_user(self.user)
        expired_access.set_exp(from_time=timezone.now() - timedelta(minutes=5), lifetime=timedelta(seconds=1))
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {expired_access}"
        )

        response = self.client.post(
            reverse("token-refresh"), {"refresh": str(refresh)}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data["data"])

    def test_logout_blacklists_refresh_token(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )

        response = self.client.post(
            reverse("logout"), {"refresh": str(refresh)}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])

        refresh_response = self.client.post(
            reverse("token-refresh"), {"refresh": str(refresh)}, format="json"
        )
        self.assertEqual(refresh_response.status_code, 401)

    def test_invalid_refresh_returns_consistent_error_response(self):
        response = self.client.post(
            reverse("token-refresh"), {"refresh": "invalid-token"}, format="json"
        )

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "AUTHENTICATION_FAILED")

    def test_inactive_user_cannot_refresh_tokens(self):
        refresh = RefreshToken.for_user(self.user)
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(
            reverse("token-refresh"), {"refresh": str(refresh)}, format="json"
        )

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.data["success"])

    def test_pending_user_cannot_refresh_tokens(self):
        refresh = RefreshToken.for_user(self.user)
        self.user.approval_status = "PENDING"
        self.user.save(update_fields=["approval_status"])

        response = self.client.post(
            reverse("token-refresh"), {"refresh": str(refresh)}, format="json"
        )

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.data["success"])


class RegistrationApiTests(APITestCase):
    registration_data = {
        "name": "New Developer",
        "email": "new.developer@example.com",
        "password": "correct horse battery staple",
        "password_confirm": "correct horse battery staple",
    }

    @override_settings(SUPER_ADMIN_EMAILS=["admin@example.com"])
    def test_registration_creates_pending_inactive_developer(self):
        mail.outbox.clear()
        registration_data = {
            **self.registration_data,
            "role": "SUPER_ADMIN",
            "approval_status": "APPROVED",
            "is_active": True,
        }
        response = self.client.post(
            reverse("register"), registration_data, format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["success"])
        user = User.objects.get(email=self.registration_data["email"])
        self.assertEqual(user.role, "DEVELOPER")
        self.assertEqual(user.approval_status, "PENDING")
        self.assertFalse(user.is_active)
        self.assertTrue(user.check_password(self.registration_data["password"]))
        self.assertFalse(user.email_verified)
        self.assertNotIn("access", response.data["data"])
        self.assertNotIn("refresh", response.data["data"])
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("Verify your", mail.outbox[0].subject)
        self.assertIn("New developer registration", mail.outbox[1].subject)
        self.assertIn("admin@example.com", [recipient for email in mail.outbox for recipient in email.to])

    @override_settings(SUPER_ADMIN_EMAILS=["admin@example.com"])
    def test_registration_notifies_super_admin_about_new_developer(self):
        User.objects.create_superuser(
            name="Platform Admin",
            email="admin@example.com",
            password="correct horse battery staple",
        )
        mail.outbox.clear()

        response = self.client.post(reverse("register"), self.registration_data, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 2)
        admin_recipients = [recipient for email in mail.outbox for recipient in email.to]
        self.assertIn("admin@example.com", admin_recipients)
        self.assertTrue(any("New developer registration" in email.subject for email in mail.outbox))

    def test_registration_email_can_be_verified_without_approval(self):
        mail.outbox.clear()
        self.client.post(reverse("register"), self.registration_data, format="json")
        token = unquote(mail.outbox[0].body.split("token=", 1)[1].splitlines()[0])

        response = self.client.post(
            reverse("verify-email"), {"token": token}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email=self.registration_data["email"])
        self.assertTrue(user.email_verified)
        self.assertEqual(user.approval_status, "PENDING")
        self.assertFalse(user.is_active)

    def test_registration_does_not_disclose_duplicate_email(self):
        User.objects.create_user(
            name="Existing Developer",
            email=self.registration_data["email"],
            password=self.registration_data["password"],
        )

        response = self.client.post(
            reverse("register"), self.registration_data, format="json"
        )

        self.assertEqual(response.status_code, 202)
        self.assertTrue(response.data["success"])
        self.assertNotIn("error", response.data)

    def test_verification_email_can_be_resent(self):
        User.objects.create_user(
            name="Unverified Developer",
            email=self.registration_data["email"],
            password=self.registration_data["password"],
        )
        mail.outbox.clear()

        response = self.client.post(
            reverse("resend-verification"),
            {"email": self.registration_data["email"]},
            format="json",
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(len(mail.outbox), 1)
        second_response = self.client.post(
            reverse("resend-verification"),
            {"email": self.registration_data["email"]},
            format="json",
        )
        self.assertEqual(second_response.status_code, 202)
        self.assertEqual(len(mail.outbox), 1)

    def test_registration_rejects_password_confirmation_mismatch(self):
        data = {**self.registration_data, "password_confirm": "different password"}
        response = self.client.post(reverse("register"), data, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])


class AdminApprovalApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            name="Platform Admin",
            email="admin@example.com",
            password="correct horse battery staple",
        )
        self.developer = User.objects.create_user(
            name="Pending Developer",
            email="pending.developer@example.com",
            password="correct horse battery staple",
        )
        self.approved_developer = User.objects.create_user(
            name="Approved Developer",
            email="approved.developer@example.com",
            password="correct horse battery staple",
            is_active=True,
            email_verified=True,
            approval_status="APPROVED",
        )

    def authenticate(self, user):
        token = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    def verify_developer(self, user):
        user.email_verified = True
        user.save(update_fields=["email_verified", "updated_at"])

    def test_unauthenticated_user_cannot_access_admin_endpoints(self):
        response = self.client.get(reverse("admin-user-list"))

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.data["success"])

    def test_developer_cannot_access_admin_endpoints(self):
        self.authenticate(self.approved_developer)

        response = self.client.get(reverse("admin-user-list"))

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "PERMISSION_DENIED")

    def test_super_admin_can_view_pending_users_and_dashboard(self):
        self.authenticate(self.admin)

        pending_response = self.client.get(reverse("admin-pending-user-list"))
        dashboard_response = self.client.get(reverse("admin-dashboard"))

        self.assertEqual(pending_response.status_code, 200)
        self.assertEqual(pending_response.data["data"]["count"], 1)
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertEqual(dashboard_response.data["data"]["pending_developers"], 1)
        self.assertEqual(dashboard_response.data["data"]["approved_developers"], 1)

    def test_super_admin_can_approve_developer_and_send_email(self):
        self.authenticate(self.admin)
        self.verify_developer(self.developer)
        mail.outbox.clear()

        response = self.client.post(
            reverse("admin-approve-developer", args=[self.developer.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["data"]["email_sent"])
        self.developer.refresh_from_db()
        self.assertEqual(self.developer.approval_status, "APPROVED")
        self.assertTrue(self.developer.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.developer.email])
        self.assertIn("/login", mail.outbox[0].body)

        login_response = self.client.post(
            reverse("login"),
            {
                "email": self.developer.email,
                "password": "correct horse battery staple",
            },
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)

    def test_unverified_developer_cannot_be_approved(self):
        self.authenticate(self.admin)

        response = self.client.post(
            reverse("admin-approve-developer", args=[self.developer.id])
        )

        self.assertEqual(response.status_code, 400)
        self.developer.refresh_from_db()
        self.assertEqual(self.developer.approval_status, "PENDING")

    def test_approved_developer_cannot_be_approved_again(self):
        self.authenticate(self.admin)

        response = self.client.post(
            reverse("admin-approve-developer", args=[self.approved_developer.id])
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])

    def test_super_admin_can_resend_approval_email(self):
        self.authenticate(self.admin)
        self.verify_developer(self.developer)
        self.client.post(
            reverse("admin-approve-developer", args=[self.developer.id])
        )
        mail.outbox.clear()

        response = self.client.post(
            reverse("admin-resend-approval-email", args=[self.developer.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["data"]["email_sent"])
        self.assertEqual(len(mail.outbox), 1)

    def test_approval_survives_email_failure(self):
        self.authenticate(self.admin)
        self.verify_developer(self.developer)

        with patch(
            "apps.accounts.services.send_approval_email",
            side_effect=RuntimeError("SMTP unavailable"),
        ):
            response = self.client.post(
                reverse("admin-approve-developer", args=[self.developer.id])
            )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["data"]["email_sent"])
        self.developer.refresh_from_db()
        self.assertEqual(self.developer.approval_status, "APPROVED")

    def test_super_admin_can_reject_developer(self):
        self.authenticate(self.admin)

        response = self.client.post(
            reverse("admin-reject-developer", args=[self.developer.id])
        )

        self.assertEqual(response.status_code, 200)
        self.developer.refresh_from_db()
        self.assertEqual(self.developer.approval_status, "REJECTED")
        self.assertFalse(self.developer.is_active)

        login_response = self.client.post(
            reverse("login"),
            {
                "email": self.developer.email,
                "password": "correct horse battery staple",
            },
            format="json",
        )
        self.assertEqual(login_response.status_code, 400)

    def test_non_admin_cannot_approve_developer(self):
        self.authenticate(self.approved_developer)

        response = self.client.post(
            reverse("admin-approve-developer", args=[self.developer.id])
        )

        self.assertEqual(response.status_code, 403)
        self.developer.refresh_from_db()
        self.assertEqual(self.developer.approval_status, "PENDING")

