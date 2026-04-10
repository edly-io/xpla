from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from xpla.notebook import constants
from xpla.notebook.db import run_migrations
from xpla.notebook.views import (
    activities,
    activity_runtime,
    auth,
    course_activities,
    courses,
)


@asynccontextmanager
async def app_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    run_migrations()
    yield


app = FastAPI(title="xPLN", version="0.1.0", lifespan=app_lifespan)

app.mount("/static", StaticFiles(directory=constants.STATIC_DIR), name="static")

if constants.FRONTEND_DIR.is_dir():
    app.mount(
        "/_next",
        StaticFiles(directory=constants.FRONTEND_DIR / "_next"),
        name="next-assets",
    )

app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(activities.router)
app.include_router(activity_runtime.router)
app.include_router(course_activities.router)


@app.get("/{path:path}", include_in_schema=False)
async def spa_fallback(path: str) -> HTMLResponse:  # pylint: disable=unused-argument
    """Serve the frontend index.html for any unmatched GET request (SPA fallback)."""
    index = constants.FRONTEND_DIR / "index.html"
    if not index.is_file():
        return HTMLResponse(
            "<h1>Frontend not built</h1><p>Run <code>make notebook-frontend-build</code></p>",
            status_code=503,
        )
    return HTMLResponse(index.read_text())
