"""Verify Supabase JWT and provide get_current_user dependency.

Supports two verification methods:
- Legacy: SUPABASE_JWT_SECRET (HS256). Supabase is migrating away from this; rotation is via standby key.
- Preferred: SUPABASE_URL only — fetch public keys from JWKS (auth/v1/.well-known/jwks.json) and verify
  with RS256/ES256. No secret needed; works with Supabase's new JWT Signing Keys.
  JWKS is fetched with httpx to avoid SSL certificate issues on macOS (Python urllib).
"""
import os
import time
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_SUPABASE_URL = (os.environ.get("SUPABASE_URL", "").strip()).rstrip("/")
_SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "").strip()
_HTTP_BEARER = HTTPBearer(auto_error=False)

# Cached JWK set (fetched with httpx to avoid SSL cert issues). (jwk_set, expiry_time).
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
    except Exception:
        return None


def _get_jwk_set():
    """Return PyJWKSet from cached or freshly fetched JWKS (httpx)."""
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
    except Exception:
        return None


def _decode_supabase_jwt(token: str) -> dict:
    """Decode and validate Supabase access token; return payload or raise."""
    # 1) Prefer JWKS (new Supabase signing keys) whenever SUPABASE_URL is set.
    if _SUPABASE_URL:
        jwk_set = _get_jwk_set()
        if jwk_set:
            try:
                header = jwt.get_unverified_header(token)
                kid = header.get("kid")
                if not kid:
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
                pass  # Key id not in set; fall through to legacy if configured
            except jwt.ExpiredSignatureError:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired. Log in again.")
            except jwt.InvalidTokenError:
                pass  # Fall through to legacy if configured
        if not _SUPABASE_JWT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth unavailable.",
            )

    # 2) Legacy: symmetric secret (HS256). Used when JWKS didn't verify or only secret is set.
    if not _SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth unavailable.",
        )
    try:
        payload = jwt.decode(
            token,
            _SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_aud": True},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired. Log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )
    return payload


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_HTTP_BEARER)],
) -> str:
    """Extract Bearer token, verify Supabase JWT, return user id (UUID string)."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode_supabase_jwt(credentials.credentials)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    return str(sub)
