"""OIDC login initiation for LTI 1.3."""

import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from sqlmodel import Session, select

from pxc.lti.core.models import Nonce, Platform


def build_auth_redirect(
    platform: Platform,
    *,
    login_hint: str,
    target_link_uri: str,
    lti_message_hint: str | None,
    redirect_uri: str,
) -> tuple[str, str, str]:
    """Build OIDC auth redirect URL.

    Returns (redirect_url, state, nonce).
    """
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)

    params: dict[str, str] = {
        "scope": "openid",
        "response_type": "id_token",
        "client_id": platform.client_id,
        "redirect_uri": redirect_uri,
        "login_hint": login_hint,
        "state": state,
        "response_mode": "form_post",
        "nonce": nonce,
        "prompt": "none",
        "target_link_uri": target_link_uri,
    }
    if lti_message_hint:
        params["lti_message_hint"] = lti_message_hint

    url = platform.oidc_auth_url + "?" + urlencode(params)
    return url, state, nonce


def store_nonce(session: Session, nonce: str, platform_id: int) -> None:
    """Store nonce for replay protection."""
    expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    session.add(Nonce(value=nonce, platform_id=platform_id, expires_at=expires))
    session.commit()


def consume_nonce(session: Session, nonce: str, platform_id: int) -> bool:
    """Consume a nonce. Returns True if valid, False if not found or expired."""
    stmt = select(Nonce).where(Nonce.value == nonce, Nonce.platform_id == platform_id)
    record = session.exec(stmt).first()
    if record is None:
        return False
    # Ensure both datetimes are timezone-aware for comparison
    expires_at = (
        record.expires_at
        if record.expires_at.tzinfo
        else record.expires_at.replace(tzinfo=timezone.utc)
    )
    if expires_at < datetime.now(timezone.utc):
        session.delete(record)
        session.commit()
        return False
    session.delete(record)
    session.commit()
    return True
