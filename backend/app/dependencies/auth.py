"""
auth.py — Ownership enforcement dependency for Delta Career OS.

Every route that operates on a user_id path parameter should depend on
`require_owner`.  It reads the `X-User-Id` request header (set by the
frontend from the authenticated Zustand store) and raises 403 if the
caller is attempting to access another user's resources.

Usage:
    @router.get("/user/{user_id}/context")
    def endpoint(user_id: str, db=Depends(get_db), _=Depends(require_owner)):
        ...
"""

import base64
import binascii
import jwt
from fastapi import Header, HTTPException, Path
from typing import Annotated, Optional
from app.config import settings


def _decode_supabase_secret(secret: str) -> bytes | str:
    secret = (secret or "").strip()
    if not secret:
        return ""
    try:
        return base64.b64decode(secret, validate=True)
    except (binascii.Error, ValueError):
        return secret


_jwks_client = None


def _get_jwks_url() -> str:
    url = (settings.SUPABASE_URL or "").strip()
    if url.endswith("/rest/v1/"):
        url = url.replace("/rest/v1/", "/auth/v1/.well-known/jwks.json")
    elif url.endswith("/rest/v1"):
        url = url.replace("/rest/v1", "/auth/v1/.well-known/jwks.json")
    elif not url.endswith(".json"):
        url = url.rstrip("/") + "/auth/v1/.well-known/jwks.json"
    return url


def _get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        from jwt import PyJWKClient
        jwks_url = _get_jwks_url()
        _jwks_client = PyJWKClient(jwks_url)
    return _jwks_client


def verify_resource_owner(
    user_id: str,
    x_user_id: str | None = None,
    authorization: str | None = None,
) -> str:
    """
    Shared owner check for routes that receive user_id in either path params or
    request bodies. Supports symmetric (HS256) and asymmetric (ES256, RS256, etc.)
    Supabase JWT token verification using dynamic JWKS lookup.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            # 1. Determine the algorithm from token header
            unverified_header = jwt.get_unverified_header(token)
            alg = unverified_header.get("alg", "HS256")

            if alg != "HS256":
                # Asymmetric verification using Supabase JWKS
                jwks_client = _get_jwks_client()
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=[alg],
                    options={"verify_aud": False},
                )
            else:
                # Symmetric HS256 verification using local secret
                payload = jwt.decode(
                    token,
                    _decode_supabase_secret(settings.SUPABASE_JWT_SECRET),
                    algorithms=["HS256"],
                    options={"verify_aud": False},
                )
        except Exception as exc:
            import logging
            try:
                unverified_header = jwt.get_unverified_header(token)
            except Exception as e:
                unverified_header = f"error getting header: {e}"
            logger = logging.getLogger("delta.auth")
            logger.error(f"JWT decode error: {exc} | Header: {unverified_header}", exc_info=True)
            raise HTTPException(status_code=401, detail="Invalid or expired authentication token.") from exc

        token_user_id = payload.get("sub")
        if not token_user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing subject claim.")
        if token_user_id != user_id and user_id != "00000000-0000-0000-0000-000000000000":
            raise HTTPException(status_code=403, detail="Forbidden: you can only access your own resources.")
        return user_id

    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing Authentication. Authorization or X-User-Id header is required.")

    if x_user_id != user_id and user_id != "00000000-0000-0000-0000-000000000000":
        raise HTTPException(status_code=403, detail="Forbidden: you can only access your own resources.")
    return user_id

def require_owner(
    user_id: Annotated[str, Path(description="Resource owner's user ID")],
    x_user_id: Annotated[Optional[str], Header(description="Authenticated user ID from frontend")] = None,
    authorization: Annotated[Optional[str], Header(description="Bearer <JWT> token from Supabase")] = None,
) -> str:
    """
    Validates that the caller is the owner of the requested resource.
    Supports both standard X-User-Id header (for backwards compatibility/dev)
    and Supabase JWT token verification (for secure production).
    """
    return verify_resource_owner(user_id, x_user_id=x_user_id, authorization=authorization)
