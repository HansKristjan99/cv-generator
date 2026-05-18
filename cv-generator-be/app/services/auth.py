"""Clerk authentication and just-in-time user provisioning.

`require_clerk_auth` validates the bearer token; `ensure_current_user` resolves
it to a persisted `User`, creating one on first sign-in. `CurrentUser` is the
FastAPI dependency endpoints should depend on.
"""

import logging
from functools import lru_cache
from typing import Annotated

from clerk_backend_api import AuthenticateRequestOptions, Clerk, authenticate_request
from clerk_backend_api.security.types import RequestState
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User

logger = logging.getLogger(__name__)

http_bearer = HTTPBearer(auto_error=False)


@lru_cache
def get_clerk_client() -> Clerk:
    if not settings.clerk_secret_key:
        raise HTTPException(status_code=500, detail="Clerk auth is not configured")
    return Clerk(bearer_auth=settings.clerk_secret_key)


def _auth_error_detail(reason: object, message: str | None) -> str:
    if message:
        return message
    value = getattr(reason, "value", None)
    if isinstance(value, str):
        return value
    return str(reason or "Unauthorized")


def require_clerk_auth(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)] = None,
) -> RequestState:
    if credentials is None or not credentials.credentials:
        logger.warning("Auth rejected: missing bearer token")
        raise HTTPException(
            status_code=401,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not settings.clerk_secret_key:
        logger.error("Auth misconfigured: CLERK_SECRET_KEY is not set")
        raise HTTPException(status_code=500, detail="Clerk auth is not configured")

    state = authenticate_request(
        request,
        AuthenticateRequestOptions(
            secret_key=settings.clerk_secret_key,
            jwt_key=settings.clerk_jwt_key,
            authorized_parties=settings.clerk_authorized_parties or None,
            accepts_token=["session_token"],
        ),
    )

    if not state.is_signed_in or not state.payload:
        logger.warning("Auth rejected: %s", _auth_error_detail(state.reason, state.message))
        raise HTTPException(
            status_code=401,
            detail=_auth_error_detail(state.reason, state.message),
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("Auth ok for subject=%s", (state.payload or {}).get("sub"))
    return state


def _claim_email(state: RequestState) -> str | None:
    payload = state.payload or {}
    for claim in ("email", "primary_email_address", "email_address"):
        value = payload.get(claim)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _clerk_primary_email(clerk_user_id: str) -> str:
    clerk_user = get_clerk_client().users.get(user_id=clerk_user_id)
    email_addresses = clerk_user.email_addresses or []
    primary_email_id = clerk_user.primary_email_address_id

    for email_address in email_addresses:
        if email_address.id == primary_email_id and email_address.email_address:
            return email_address.email_address

    if email_addresses and email_addresses[0].email_address:
        return email_addresses[0].email_address

    raise HTTPException(status_code=400, detail="Authenticated Clerk user has no email address")


def _auth_subject(state: RequestState) -> str:
    payload = state.payload or {}
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(status_code=401, detail="Clerk token is missing a subject")
    return subject


def ensure_current_user(
    state: Annotated[RequestState, Depends(require_clerk_auth)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    clerk_user_id = _auth_subject(state)
    email = _claim_email(state)

    user = db.scalar(select(User).where(User.idp_sub == clerk_user_id))
    if user is None:
        email = email or _clerk_primary_email(clerk_user_id)
        user = User(idp_sub=clerk_user_id, email=email)
        db.add(user)
        should_commit = True
    else:
        should_commit = email is not None and user.email != email
        if email is not None:
            user.email = email

    if not should_commit:
        return user

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = db.scalar(select(User).where(User.idp_sub == clerk_user_id))
        if existing is not None:
            return existing
        raise HTTPException(status_code=409, detail="User email already exists") from exc

    db.refresh(user)
    return user


CurrentUser = Annotated[User, Depends(ensure_current_user)]
