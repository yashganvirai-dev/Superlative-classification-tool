"""Request-level protections applied before DRF parses uploads."""

import re

from django.conf import settings
from django.http import JsonResponse


DATASET_UPLOAD_PATH = re.compile(r"^/api/models/\d+/dataset/?$")


class DatasetRequestLimitMiddleware:
    """Reject oversized multipart requests using Content-Length before parsing."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST" and DATASET_UPLOAD_PATH.match(request.path):
            raw_length = request.META.get("CONTENT_LENGTH", "")
            try:
                content_length = int(raw_length)
            except (TypeError, ValueError):
                content_length = 0
            if content_length > settings.MAX_DATASET_REQUEST_BYTES:
                return JsonResponse(
                    {
                        "success": False,
                        "error": {
                            "code": "REQUEST_TOO_LARGE",
                            "message": "The dataset upload exceeds the request size limit.",
                        },
                    },
                    status=413,
                )
        return self.get_response(request)
