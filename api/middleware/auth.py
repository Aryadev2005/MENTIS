"""Clerk JWT authentication middleware."""

import logging
from functools import lru_cache

import httpx
from fastapi import HTTPException, Request
from jose import JWTError, jwt

from ..config import settings

logger = logging.getLogger(__name__)

CLERK_JWKS_URL = "https://api.clerk.dev/v1/jwks"


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    with httpx.Client(timeout=5.0) as client:
        response = client.get(CLERK_JWKS_URL, headers={
            "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"
        })
        response.raise_for_status()
        return response.json()


def verify_clerk_token(token: str) -> dict:
    try:
        jwks = _get_jwks()
        header = jwt.get_unverified_header(token)
        key = next(
            (k for k in jwks["keys"] if k["kid"] == header["kid"]),
            None,
        )
        if not key:
            raise HTTPException(status_code=401, detail="Unknown signing key")

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except Exception as e:
        logger.error("Token verification failed: %s", e)
        raise HTTPException(status_code=401, detail="Authentication failed")


async def get_current_user(request: Request) -> dict:
    """FastAPI dependency: extract and verify Clerk JWT from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = auth_header.removeprefix("Bearer ")
    return verify_clerk_token(token)


async def optional_auth(request: Request) -> dict | None:
    """Like get_current_user but returns None instead of raising for missing tokens."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    try:
        token = auth_header.removeprefix("Bearer ")
        return verify_clerk_token(token)
    except HTTPException:
        return None
