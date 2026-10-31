from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower


class UserRole(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    DEVELOPER = "DEVELOPER", "Developer"


class ApprovalStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str | None = None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email.strip()).lower()
        extra_fields.setdefault("role", UserRole.DEVELOPER)
        extra_fields.setdefault("approval_status", ApprovalStatus.PENDING)
        extra_fields.setdefault("is_active", False)
        extra_fields.setdefault("email_verified", False)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("role", UserRole.SUPER_ADMIN)
        extra_fields.setdefault("approval_status", ApprovalStatus.APPROVED)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("email_verified", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("role") != UserRole.SUPER_ADMIN:
            raise ValueError("Superusers must have the SUPER_ADMIN role.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superusers must have is_superuser=True.")
        if not extra_fields.get("is_staff"):
            raise ValueError("Superusers must have is_staff=True.")
        if not extra_fields.get("is_active"):
            raise ValueError("Superusers must be active.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.DEVELOPER,
        db_index=True,
    )
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        db_index=True,
    )
    is_active = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    verification_email_sent_at = models.DateTimeField(null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(Lower("email"), name="user_email_unique_ci"),
            models.CheckConstraint(
                condition=models.Q(role__in=[role.value for role in UserRole]),
                name="user_role_is_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    approval_status__in=[state.value for state in ApprovalStatus]
                ),
                name="user_approval_status_is_valid",
            ),
        ]

    def save(self, *args, **kwargs):
        self.email = type(self).objects.normalize_email(self.email.strip()).lower()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.email
