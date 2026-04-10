"""Authentication helpers: password hashing and cookie-based sessions."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, HTTPException
from sqlmodel import Session, select

from xpla.notebook.db import get_session
from xpla.notebook.models import User, UserSession

SESSION_COOKIE = "xpln_session"
SESSION_DURATION = timedelta(days=30)
_PBKDF2_ITERATIONS = 200_000
_SALT_BYTES = 16


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> tuple[str, str]:
    """Return (hex_hash, hex_salt) using pbkdf2_hmac-sha256."""
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    return digest.hex(), salt.hex()


def verify_password(password: str, hex_hash: str, hex_salt: str) -> bool:
    if not hex_hash or not hex_salt:
        return False
    salt = bytes.fromhex(hex_salt)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    return hmac.compare_digest(digest.hex(), hex_hash)


def create_session(session: Session, user_id: str) -> UserSession:
    user_session = UserSession(
        token=secrets.token_urlsafe(32),
        user_id=user_id,
        expires_at=_utcnow() + SESSION_DURATION,
    )
    session.add(user_session)
    session.commit()
    session.refresh(user_session)
    return user_session


def delete_session(session: Session, token: str) -> None:
    user_session = session.get(UserSession, token)
    if user_session:
        session.delete(user_session)
        session.commit()


def lookup_user(session: Session, token: str | None) -> User | None:
    """Resolve a session token to a User, or None if invalid/expired."""
    if not token:
        return None
    user_session = session.get(UserSession, token)
    if not user_session:
        return None
    expires_at = user_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < _utcnow():
        session.delete(user_session)
        session.commit()
        return None
    return session.get(User, user_session.user_id)


def get_current_user(
    xpln_session: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
) -> User:
    user = lookup_user(session, xpln_session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def get_optional_user(
    xpln_session: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
) -> User | None:
    return lookup_user(session, xpln_session)


def user_by_email(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(User.email == email)).first()
