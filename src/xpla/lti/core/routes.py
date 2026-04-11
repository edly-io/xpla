"""Generic LTI 1.3 FastAPI router.

Provides OIDC login, launch callback, JWKS endpoint, and admin CRUD.
The application plugs in a launch_handler callback.
"""

import logging
from collections.abc import Awaitable, Callable

import jwt as pyjwt
from fastapi import APIRouter, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from xpla.lti.core.keys import KeySet
from xpla.lti.core.launch import LaunchData, LaunchError, validate_launch_jwt
from xpla.lti.core.models import Platform
from xpla.lti.core.oidc import build_auth_redirect, consume_nonce, store_nonce

logger = logging.getLogger(__name__)


def create_lti_router(
    *,
    db_engine: Engine,
    key_set: KeySet,
    launch_handler: Callable[[LaunchData, Request], Awaitable[Response]],
    base_url: str,
    templates: Jinja2Templates,
    prefix: str = "",
) -> APIRouter:
    """Create the LTI core router."""
    router = APIRouter()

    @router.get("/.well-known/jwks.json")
    async def jwks_endpoint() -> JSONResponse:
        return JSONResponse(key_set.jwks())

    @router.api_route("/auth/login", methods=["GET", "POST"])
    async def oidc_login(request: Request) -> Response:
        params = dict(request.query_params)
        if request.method == "POST":
            form = await request.form()
            params.update({k: str(v) for k, v in form.items()})

        issuer = params.get("iss", "")
        client_id = params.get("client_id", "")
        login_hint = params.get("login_hint", "")
        target_link_uri = params.get("target_link_uri", base_url + "/auth/callback")
        lti_message_hint = params.get("lti_message_hint")

        platform = _find_platform(db_engine, issuer, client_id)
        if platform is None:
            raise HTTPException(status_code=400, detail="Unknown platform")

        assert platform.id is not None
        redirect_uri = base_url + "/auth/callback"
        url, state, nonce = build_auth_redirect(
            platform,
            login_hint=login_hint,
            target_link_uri=target_link_uri,
            lti_message_hint=lti_message_hint,
            redirect_uri=redirect_uri,
        )

        with Session(db_engine) as session:
            store_nonce(session, nonce, platform.id)

        response = RedirectResponse(url=url, status_code=302)
        cookie_is_secure = request.scope["scheme"] == "https"
        response.set_cookie(
            "lti_state",
            state,
            max_age=600,
            httponly=True,
            samesite="none" if cookie_is_secure else None,
            secure=cookie_is_secure,
        )
        return response

    @router.post("/auth/callback")
    async def launch_callback(
        request: Request,
        id_token: str = Form(...),
        state: str = Form(""),
    ) -> Response:
        cookie_state = request.cookies.get("lti_state", "")
        if not state or state != cookie_state:
            return _error_response(templates, request, "Invalid state parameter")

        try:
            unverified = pyjwt.decode(id_token, options={"verify_signature": False})
        except pyjwt.PyJWTError:
            return _error_response(templates, request, "Malformed JWT")

        issuer = unverified.get("iss", "")
        client_id = unverified.get("aud", "")
        if isinstance(client_id, list):
            client_id = client_id[0] if client_id else ""

        platform = _find_platform(db_engine, issuer, client_id)
        if platform is None:
            return _error_response(templates, request, "Unknown platform")

        try:
            launch_data = validate_launch_jwt(
                id_token,
                jwks_url=platform.jwks_url,
                client_id=platform.client_id,
                issuer=platform.issuer,
            )
        except LaunchError as e:
            return _error_response(templates, request, str(e))

        nonce = unverified.get("nonce", "")
        assert platform.id is not None
        with Session(db_engine) as session:
            if not consume_nonce(session, nonce, platform.id):
                return _error_response(templates, request, "Nonce replay or expired")

        return await launch_handler(launch_data, request)

    _register_admin_routes(router, db_engine, base_url, templates, prefix)
    return router


def _register_admin_routes(
    router: APIRouter,
    db_engine: Engine,
    base_url: str,
    templates: Jinja2Templates,
    prefix: str,
) -> None:
    """Register admin CRUD routes on the router."""

    @router.get("/admin/platforms", response_class=HTMLResponse)
    async def admin_list_platforms(request: Request) -> HTMLResponse:
        with Session(db_engine) as session:
            platforms = list(session.exec(select(Platform)).all())
        return templates.TemplateResponse(
            request=request,
            name="admin/platforms.html",
            context={
                "platforms": platforms,
                "base_url": base_url,
                "prefix": prefix,
            },
        )

    @router.get("/admin/platforms/new", response_class=HTMLResponse)
    async def admin_new_platform(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="admin/platform_form.html",
            context={
                "platform": None,
                "action": f"{prefix}/admin/platforms",
                "prefix": prefix,
            },
        )

    @router.post("/admin/platforms")
    async def admin_create_platform(
        name: str = Form(...),
        issuer: str = Form(...),
        client_id: str = Form(...),
        oidc_auth_url: str = Form(...),
        jwks_url: str = Form(...),
        access_token_url: str = Form(""),
    ) -> RedirectResponse:
        platform = Platform(
            name=name,
            issuer=issuer,
            client_id=client_id,
            oidc_auth_url=oidc_auth_url,
            jwks_url=jwks_url,
            access_token_url=access_token_url,
        )
        with Session(db_engine) as session:
            session.add(platform)
            session.commit()
        return RedirectResponse(url=f"{prefix}/admin/platforms", status_code=303)

    @router.get("/admin/platforms/{platform_id}/edit", response_class=HTMLResponse)
    async def admin_edit_platform(request: Request, platform_id: int) -> HTMLResponse:
        with Session(db_engine) as session:
            platform = session.get(Platform, platform_id)
        if platform is None:
            raise HTTPException(status_code=404, detail="Platform not found")
        return templates.TemplateResponse(
            request=request,
            name="admin/platform_form.html",
            context={
                "platform": platform,
                "action": f"{prefix}/admin/platforms/{platform_id}",
                "prefix": prefix,
            },
        )

    @router.post("/admin/platforms/{platform_id}")
    async def admin_update_platform(
        platform_id: int,
        name: str = Form(...),
        issuer: str = Form(...),
        client_id: str = Form(...),
        oidc_auth_url: str = Form(...),
        jwks_url: str = Form(...),
        access_token_url: str = Form(""),
    ) -> RedirectResponse:
        with Session(db_engine) as session:
            platform = session.get(Platform, platform_id)
            if platform is None:
                raise HTTPException(status_code=404, detail="Platform not found")
            platform.name = name
            platform.issuer = issuer
            platform.client_id = client_id
            platform.oidc_auth_url = oidc_auth_url
            platform.jwks_url = jwks_url
            platform.access_token_url = access_token_url
            session.add(platform)
            session.commit()
        return RedirectResponse(url=f"{prefix}/admin/platforms", status_code=303)

    @router.post("/admin/platforms/{platform_id}/delete")
    async def admin_delete_platform(platform_id: int) -> RedirectResponse:
        with Session(db_engine) as session:
            platform = session.get(Platform, platform_id)
            if platform is not None:
                session.delete(platform)
                session.commit()
        return RedirectResponse(url=f"{prefix}/admin/platforms", status_code=303)


def _find_platform(engine: Engine, issuer: str, client_id: str) -> Platform | None:
    with Session(engine) as session:
        stmt = select(Platform).where(
            Platform.issuer == issuer, Platform.client_id == client_id
        )
        return session.exec(stmt).first()


def _error_response(
    templates: Jinja2Templates, request: Request, message: str
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="launch_error.html",
        context={"error_message": message},
        status_code=400,
    )
