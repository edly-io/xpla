"""xPLA-specific LTI launch handling."""

import logging
import time

import jwt
from fastapi import Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from xpla.lib.permission import Permission
from xpla.lti.config import SAMPLES_DIR
from xpla.lti.core.deep_linking import build_deep_link_response
from xpla.lti.core.keys import KeySet
from xpla.lti.core.launch import LaunchData

logger = logging.getLogger(__name__)

# Instructor LTI roles
_INSTRUCTOR_ROLES = {
    "http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor",
    "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Instructor",
    "http://purl.imsglobal.org/vocab/lis/v2/membership#ContentDeveloper",
    "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Administrator",
}


def list_activities() -> list[str]:
    """List available sample activities."""
    return sorted(
        d.name
        for d in SAMPLES_DIR.iterdir()
        if d.is_dir() and (d / "manifest.json").exists()
    )


def _is_instructor(roles: list[str]) -> bool:
    return bool(set(roles) & _INSTRUCTOR_ROLES)


def create_launch_handler(
    templates: Jinja2Templates,
    key_set: KeySet,
    base_url: str,
    session_secret: str,
) -> "LaunchHandler":
    """Create a launch handler closure."""
    return LaunchHandler(templates, key_set, base_url, session_secret)


class LaunchHandler:
    """Handles LTI launches by routing to activity render or deep linking picker."""

    def __init__(
        self,
        templates: Jinja2Templates,
        key_set: KeySet,
        base_url: str,
        session_secret: str,
    ) -> None:
        self.templates = templates
        self.key_set = key_set
        self.base_url = base_url
        self.session_secret = session_secret

    async def __call__(self, launch_data: LaunchData, request: Request) -> Response:
        if launch_data.message_type == "LtiDeepLinkingRequest":
            return self._handle_deep_linking(launch_data, request)
        return self._handle_resource_link(launch_data, request)

    def _handle_deep_linking(
        self, launch_data: LaunchData, request: Request
    ) -> HTMLResponse:
        """Show activity picker for deep linking."""
        return self.templates.TemplateResponse(
            request=request,
            name="select_activity.html",
            context={
                "activities": list_activities(),
                "launch_data": launch_data,
                "return_url": launch_data.deep_link_return_url or "",
                "deployment_id": launch_data.deployment_id,
                "client_id": launch_data.client_id,
                "issuer": launch_data.issuer,
            },
        )

    def _handle_resource_link(
        self, launch_data: LaunchData, request: Request
    ) -> HTMLResponse | RedirectResponse:
        """Render an activity for a resource link launch."""
        activity_type = launch_data.custom.get("activity_type", "")
        if not activity_type:
            return self.templates.TemplateResponse(
                request=request,
                name="launch_error.html",
                context={"error_message": "No activity_type in custom parameters"},
                status_code=400,
            )

        activity_dir = SAMPLES_DIR / activity_type
        if not (activity_dir / "manifest.json").exists():
            return self.templates.TemplateResponse(
                request=request,
                name="launch_error.html",
                context={
                    "error_message": f"Activity '{activity_type}' not found",
                },
                status_code=404,
            )

        permission = (
            Permission.edit if _is_instructor(launch_data.roles) else Permission.play
        )
        token = self._make_session_token(launch_data, activity_type, permission)

        # Redirect to the activity page which will properly load context and render
        # Use 303 to change POST to GET
        return RedirectResponse(
            url=f"{self.base_url}/activity/{token}", status_code=303
        )

    def _make_session_token(
        self,
        launch_data: LaunchData,
        activity_type: str,
        permission: Permission,
    ) -> str:
        """Create a short-lived session JWT."""
        now = int(time.time())
        payload = {
            "sub": launch_data.user_id,
            "course_id": launch_data.context_id or "unknown",
            "activity_type": activity_type,
            "permission": permission.value,
            "iat": now,
            "exp": now + 7200,
        }
        token: str = jwt.encode(payload, self.session_secret, algorithm="HS256")
        return token

    def decode_session_token(self, token: str) -> dict[str, str]:
        """Decode and validate a session token."""
        claims: dict[str, str] = jwt.decode(
            token, self.session_secret, algorithms=["HS256"]
        )
        return claims

    def build_deep_link_jwt(
        self,
        activity_type: str,
        *,
        client_id: str,
        deployment_id: str,
    ) -> str:
        """Build a deep linking response JWT for an activity."""
        items = [
            {
                "type": "ltiResourceLink",
                "title": activity_type,
                "url": self.base_url + "/auth/login",
                "custom": {"activity_type": activity_type},
            }
        ]
        return build_deep_link_response(
            self.key_set,
            issuer=self.base_url,
            client_id=client_id,
            deployment_id=deployment_id,
            items=items,
        )
