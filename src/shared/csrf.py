"""CSRF protection via Origin/Referer header validation for form-based POST requests.

Rejects form POST requests where the Origin or Referer header does not match
the server's Host header. JSON API calls (no form content-type) are exempt.
Direct requests without Origin/Referer (curl, tests, same-site navigation) are
allowed — the SameSite=Lax cookie attribute handles the browser-CSRF risk there.
"""
from urllib.parse import urlparse

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_FORM_CONTENT_TYPES = (
    "application/x-www-form-urlencoded",
    "multipart/form-data",
)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Block cross-origin form submissions by validating Origin/Referer."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "POST" and self._is_form_request(request):
            host = request.headers.get("host", "")
            origin = request.headers.get("origin")
            referer = request.headers.get("referer")

            if origin is not None:
                if not self._origin_matches(origin, host):
                    return JSONResponse(
                        content={"detail": "CSRF check failed"}, status_code=403
                    )
            elif referer is not None:
                if not self._referer_matches(referer, host):
                    return JSONResponse(
                        content={"detail": "CSRF check failed"}, status_code=403
                    )
            # If both absent, allow — direct API calls and same-site navigations
            # that omit these headers are benign.

        return await call_next(request)

    @staticmethod
    def _is_form_request(request: Request) -> bool:
        content_type = request.headers.get("content-type", "")
        return any(ct in content_type for ct in _FORM_CONTENT_TYPES)

    @staticmethod
    def _origin_matches(origin: str, host: str) -> bool:
        """Return True if *origin* refers to the same host as the server."""
        if origin == "null":
            return False
        netloc = urlparse(origin).netloc
        return bool(netloc) and netloc == host

    @staticmethod
    def _referer_matches(referer: str, host: str) -> bool:
        """Return True if *referer* refers to the same host as the server."""
        netloc = urlparse(referer).netloc
        return bool(netloc) and netloc == host
