"""Verify Supabase JWT and provide get_current_user dependency.

Supports two verification methods:
- Legacy: SUPABASE_JWT_SECRET (HS256). Supabase is migrating away from this; rotation is via standby key.
- Preferred: SUPABASE_URL only — fetch public keys from JWKS (auth/v1/.well-known/jwks.json) and verify
  with RS256/ES256. No secret needed; works with Supabase's new JWT Signing Keys.
"""
import os
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_SUPABASE_URL = (os.environ.get("SUPABASE_URL", "").strip()).rstrip("/")
_SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "").strip()
_HTTP_BEARER = HTTPBearer(auto_error=False)

# JWKS client for new Supabase JWT Signing Keys (lazy init, cached by PyJWKClient).
_jwks_client = None


def _get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        if not _SUPABASE_URL:
            return None
        try:
            from jwt import PyJWKClient
            _jwks_client = PyJWKClient(
                f"{_SUPABASE_URL}/auth/v1/.well-known/jwks.json",
                cache_jwk_set=True,
                lifespan=300,
            )
        except Exception:
            return None
    return _jwks_client


def _decode_supabase_jwt(token: str) -> dict:
    """Decode and validate Supabase access token; return payload or raise."""
    # 1) Prefer JWKS (new signing keys) if only SUPABASE_URL is set.
    if _SUPABASE_URL and not _SUPABASE_JWT_SECRET:
        client = _get_jwks_client()
        if client:
            try:
                signing_key = client.get_signing_key_from_jwt(token)
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256", "ES256"],
                    audience="authenticated",
                    options={"verify_aud": True},
                )
                return payload
            except jwt.ExpiredSignatureError:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
            except jwt.InvalidTokenError:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth not configured (SUPABASE_URL required for JWKS verification)",
        )

    # 2) Legacy: symmetric secret (HS256).
    if not _SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth not configured (set SUPABASE_URL for JWKS or SUPABASE_JWT_SECRET for legacy verification)",
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
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
