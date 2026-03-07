"""Verify Supabase JWT via JWKS and provide get_current_user dependency.

Uses SUPABASE_URL only: fetches public keys from auth/v1/.well-known/jwks.json (JWKS)
and verifies tokens with RS256/ES256. No JWT secret needed.
JWKS is fetched with httpx to avoid SSL certificate issues on macOS.
"""
import logging
import os
import time
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger("pdf_processor_app.auth")

_SUPABASE_URL = (os.environ.get("SUPABASE_URL", "").strip()).rstrip("/")
_HTTP_BEARER = HTTPBearer(auto_error=False)

# Cached JWK set (fetched with httpx). (jwk_set, expiry_time).
_jwk_set_cache = None
_JWKS_CACHE_SECONDS = 300


def _fetch_jwks_via_httpx():
    """Fetch JWKS from Supabase using httpx (uses certifi; works on macOS)."""
    if not _SUPABASE_URL:
        return None
    try:
        import httpx
        url = f"{_SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        r = httpx.get(url, timeout=10.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("JWKS fetch failed: %s", e)
        return None


def _get_jwk_set():
    """Return PyJWKSet from cached or freshly fetched JWKS."""
    global _jwk_set_cache
    now = time.monotonic()
    if _jwk_set_cache is not None and now < _jwk_set_cache[1]:
        return _jwk_set_cache[0]
    data = _fetch_jwks_via_httpx()
    if data is None:
        return None
    try:
        from jwt import PyJWKSet
        jwk_set = PyJWKSet.from_dict(data)
        _jwk_set_cache = (jwk_set, now + _JWKS_CACHE_SECONDS)
        return jwk_set
    except Exception as e:
        logger.warning("JWKS parse failed: %s", e)
        return None


def _decode_supabase_jwt(token: str) -> dict:
    """Decode and validate Supabase access token with JWKS; return payload or raise."""
    if not _SUPABASE_URL:
        logger.warning("JWT verify: SUPABASE_URL not set -> 503")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth unavailable.",
        )
    jwk_set = _get_jwk_set()
    if not jwk_set:
        logger.warning("JWT verify: JWKS unavailable (fetch or parse failed) -> 503")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth unavailable.",
        )
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            logger.info("JWT verify: token missing kid -> 401")
            raise jwt.InvalidTokenError("missing kid")
        py_jwk = jwk_set[kid]
        payload = jwt.decode(
            token,
            py_jwk.key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
            options={"verify_aud": True},
        )
        return payload
    except KeyError:
        logger.info("JWT verify: kid %r not in JWKS -> 401", kid)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    except jwt.ExpiredSignatureError:
        logger.info("JWT verify: token expired (kid=%r) -> 401", kid)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired. Log in again.")
    except jwt.InvalidTokenError as e:
        logger.info("JWT verify: invalid token (kid=%r) -> 401, reason=%s", header.get("kid"), e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_HTTP_BEARER)],
) -> str:
    """Extract Bearer token, verify Supabase JWT via JWKS, return user id (UUID string)."""
    if not credentials or not credentials.credentials:
        logger.info("JWT verify: missing or empty Authorization header -> 401")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    payload = _decode_supabase_jwt(token)
    sub = payload.get("sub")
    if not sub:
        logger.info("JWT verify: payload missing sub -> 401")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    logger.debug("JWT verify: ok sub=%s", sub)
    return str(sub)
