"""Test settings.

The test database is PostgreSQL so tests exercise the production database
engine. PostgreSQL is the only supported database.
"""

import os
import secrets

from .base import *  # noqa: F403


DEBUG = False
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(50)
SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.PBKDF2PasswordHasher"]
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "anon": "1000/min",
    "user": "1000/min",
}

DATABASES["default"]["TEST"] = {  # noqa: F405
    "NAME": os.getenv("POSTGRES_TEST_DB", "test_superlative_classification")
}
