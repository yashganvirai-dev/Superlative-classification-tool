"""Production-oriented settings for a secured deployment."""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403


DEBUG = False

if len(SECRET_KEY) < 50:  # noqa: F405
    raise ImproperlyConfigured("SECRET_KEY must contain at least 50 characters in production.")
if not os.getenv("ALLOWED_HOSTS", "").strip():
    raise ImproperlyConfigured("ALLOWED_HOSTS must be set in production.")
if "*" in ALLOWED_HOSTS:  # noqa: F405
    raise ImproperlyConfigured("ALLOWED_HOSTS cannot contain a wildcard in production.")
if "*" in CORS_ALLOWED_ORIGINS:  # noqa: F405
    raise ImproperlyConfigured("CORS_ALLOWED_ORIGINS cannot contain a wildcard in production.")
if EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":  # noqa: F405
    raise ImproperlyConfigured("Production must use an SMTP email backend.")
if not EMAIL_HOST:  # noqa: F405
    raise ImproperlyConfigured("EMAIL_HOST must be set in production.")
if not EMAIL_USE_TLS:  # noqa: F405
    raise ImproperlyConfigured("EMAIL_USE_TLS must be enabled in production.")
if not FRONTEND_BASE_URL.startswith("https://"):  # noqa: F405
    raise ImproperlyConfigured("FRONTEND_BASE_URL must use HTTPS in production.")

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)  # noqa: F405
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)  # noqa: F405
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", True)  # noqa: F405
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 31536000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(  # noqa: F405
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", True
)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", True)  # noqa: F405
SECURE_CONTENT_TYPE_NOSNIFF = True

if os.getenv("SECURE_PROXY_SSL_HEADER"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
