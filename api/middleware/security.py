"""Security middleware: prompt injection detection, input sanitization, rate abuse."""

import re
import logging
from typing import Any

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"you\s+are\s+now\s+[a-z]+\s*(AI|assistant|bot|model)",
    r"(system|assistant)\s*:\s*",
    r"<\|im_start\|>",
    r"\[\[INST\]\]",
    r"###\s*(instruction|system|prompt)",
    r"disregard\s+your\s+(training|guidelines|rules)",
    r"pretend\s+(you\s+are|to\s+be)",
    r"do\s+anything\s+now\s*\(",
    r"jailbreak",
    r"act\s+as\s+(if\s+you\s+are|an?\s+)",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

MAX_STRING_LENGTH = 50_000
BLOCKED_PATHS = {"/admin", "/internal", "/debug"}


def scan_for_injection(text: str) -> bool:
    return any(pat.search(text) for pat in _COMPILED)


def sanitize_string(value: str) -> str:
    value = value[:MAX_STRING_LENGTH]
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)
    return value


def sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_string(value)
    if isinstance(value, dict):
        return {k: sanitize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    return value


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in BLOCKED_PATHS:
            return JSONResponse({"detail": "Not found"}, status_code=404)

        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    body_bytes = await request.body()
                    body_text = body_bytes.decode("utf-8", errors="replace")

                    if scan_for_injection(body_text):
                        logger.warning(
                            "Prompt injection attempt from %s on %s",
                            request.client.host if request.client else "unknown",
                            request.url.path,
                        )
                        return JSONResponse(
                            {"detail": "Request contains disallowed content"},
                            status_code=400,
                        )

                    if len(body_text) > 1_000_000:
                        return JSONResponse(
                            {"detail": "Request body too large"},
                            status_code=413,
                        )
                except Exception:
                    pass

        try:
            response = await call_next(request)
        except Exception as e:
            logger.error("Unhandled error: %s", e)
            return JSONResponse({"detail": "Internal server error"}, status_code=500)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
