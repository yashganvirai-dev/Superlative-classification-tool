"""Shared API response and error handling."""

import logging
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    ParseError,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework_simplejwt.exceptions import TokenError


logger = logging.getLogger("superlative.api")


def success(data: Any, status_code: int = status.HTTP_200_OK) -> Response:
    return Response({"success": True, "data": data}, status=status_code)


def _message_from_detail(detail: Any) -> str:
    if isinstance(detail, dict):
        for value in detail.values():
            message = _message_from_detail(value)
            if message:
                return message
    elif isinstance(detail, (list, tuple)):
        for value in detail:
            message = _message_from_detail(value)
            if message:
                return message
    return str(detail)


def _error(code: str, message: str, status_code: int, fields: Any = None) -> Response:
    error = {"code": code, "message": message}
    if fields is not None:
        error["fields"] = fields
    return Response({"success": False, "error": error}, status=status_code)


def api_exception_handler(exc: Exception, context: dict) -> Response | None:
    if isinstance(exc, Http404):
        return _error("NOT_FOUND", "The requested resource was not found.", 404)
    if isinstance(exc, DjangoPermissionDenied):
        return _error("PERMISSION_DENIED", "You do not have permission to do that.", 403)
    if isinstance(exc, TokenError):
        return _error("AUTHENTICATION_FAILED", "The token is invalid or expired.", 401)

    response = drf_exception_handler(exc, context)
    if response is None:
        logger.error(
            "Unhandled API exception: %s",
            exc,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return _error(
            "INTERNAL_SERVER_ERROR",
            "An unexpected error occurred.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, ValidationError):
        code = "VALIDATION_ERROR"
    elif isinstance(exc, NotAuthenticated):
        code = "AUTHENTICATION_REQUIRED"
    elif isinstance(exc, AuthenticationFailed):
        code = "AUTHENTICATION_FAILED"
    elif isinstance(exc, PermissionDenied):
        code = "PERMISSION_DENIED"
    elif isinstance(exc, Throttled):
        code = "THROTTLED"
    elif isinstance(exc, NotFound):
        code = "NOT_FOUND"
    elif isinstance(exc, MethodNotAllowed):
        code = "METHOD_NOT_ALLOWED"
    elif isinstance(exc, ParseError):
        code = "INVALID_REQUEST"
    elif isinstance(exc, APIException):
        code = "API_ERROR"
    else:
        code = "API_ERROR"

    detail = response.data
    message_detail = detail.get("detail", detail) if isinstance(detail, dict) else detail
    fields = detail if isinstance(detail, dict) and "detail" not in detail else None
    response.data = {
        "success": False,
        "error": {
            "code": code,
            "message": _message_from_detail(message_detail),
            **({"fields": fields} if fields is not None else {}),
        },
    }
    return response
