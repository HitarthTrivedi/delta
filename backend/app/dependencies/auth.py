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

from fastapi import Depends, Header, HTTPException, Path
from typing import Annotated


def require_owner(
    user_id: Annotated[str, Path(description="Resource owner's user ID")],
    x_user_id: Annotated[str, Header(description="Authenticated user ID from frontend")] = None,
) -> str:
    """
    Validates that the caller is the owner of the requested resource.
    Returns the verified user_id on success.
    Raises 401 if the header is missing, 403 if the IDs don't match.
    """
    if not x_user_id:
        raise HTTPException(
            status_code=401,
            detail="Missing X-User-Id header. Authentication required.",
        )
    if x_user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: you can only access your own resources.",
        )
    return user_id
