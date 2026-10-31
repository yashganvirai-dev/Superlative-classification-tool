"""Development settings."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403


DEBUG = env_bool("DEBUG", True)  # noqa: F405

if not SECRET_KEY:  # noqa: F405
    raise ImproperlyConfigured(
        "SECRET_KEY must be set in backend/.env or the process environment."
    )
