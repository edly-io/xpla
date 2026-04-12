import re
import secrets

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlmodel import Session, select

from xpla.notebook.auth import (
    SESSION_COOKIE,
    SESSION_DURATION,
    create_session,
    delete_session,
    get_current_user,
    get_or_create_api_token,
    hash_password,
    user_by_email,
    verify_password,
)
from xpla.notebook.db import get_session
from xpla.notebook.models import ApiToken, User

router = APIRouter()

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
MIN_PASSWORD_LENGTH = 8


class CredentialsBody(BaseModel):
    email: str
    password: str


def _set_session_cookie(request: Request, response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=int(SESSION_DURATION.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        path="/",
    )


def _user_dict(user: User) -> dict[str, str]:
    return {"id": user.id, "email": user.email}


def _validate_credentials(email: str, password: str) -> str:
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Invalid email address")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters",
        )
    return email


@router.post("/api/auth/signup", status_code=201, summary="Create an account")
async def signup(
    body: CredentialsBody,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    email = _validate_credentials(body.email, body.password)
    if user_by_email(session, email):
        raise HTTPException(status_code=409, detail="Email already in use")
    password_hash, password_salt = hash_password(body.password)
    user = User(email=email, password_hash=password_hash, password_salt=password_salt)
    session.add(user)
    session.commit()
    session.refresh(user)
    user_session = create_session(session, user.id)
    get_or_create_api_token(session, user.id)
    _set_session_cookie(request, response, user_session.token)
    return _user_dict(user)


@router.post("/api/auth/login", summary="Log in")
async def login(
    body: CredentialsBody,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    email = body.email.strip().lower()
    user = user_by_email(session, email)
    if not user or not verify_password(
        body.password, user.password_hash, user.password_salt
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user_session = create_session(session, user.id)
    get_or_create_api_token(session, user.id)
    _set_session_cookie(request, response, user_session.token)
    return _user_dict(user)


@router.post("/api/auth/logout", status_code=204, summary="Log out")
async def logout(
    response: Response,
    xpln_session: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
) -> None:
    if xpln_session:
        delete_session(session, xpln_session)
    response.delete_cookie(key=SESSION_COOKIE, path="/")


@router.get("/api/me", summary="Current user")
async def me(current_user: User = Depends(get_current_user)) -> dict[str, str]:
    return _user_dict(current_user)


@router.get("/api/settings/api-token", summary="Get API token")
async def get_api_token(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """Return the current user's API token."""
    token_str = get_or_create_api_token(session, current_user.id)
    return {"token": token_str}


@router.post("/api/settings/api-token", summary="Regenerate API token")
async def regenerate_api_token(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """Delete and regenerate the current user's API token."""
    old = session.exec(
        select(ApiToken).where(ApiToken.user_id == current_user.id)
    ).first()
    if old:
        session.delete(old)
        session.commit()
    new_token = ApiToken(token=secrets.token_urlsafe(32), user_id=current_user.id)
    session.add(new_token)
    session.commit()
    session.refresh(new_token)
    return {"token": new_token.token}
