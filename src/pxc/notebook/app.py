from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from pxc.notebook import constants
from pxc.notebook.db import run_migrations
from pxc.notebook.views import (
    activities,
    activity_runtime,
    auth,
    course_activities,
    courses,
    lti,
)


class SPAStaticFiles(StaticFiles):
    """Static file server with SPA fallback to index.html.

    The Next.js frontend is a single-page app: all client-side routes (e.g.
    /courses/123) are handled by JavaScript in index.html. When the browser
    requests such a path directly (reload, deep link, prefetch), there is no
    matching file on disk. This subclass detects that and returns index.html
    so the client-side router can take over.
    """

    def lookup_path(self, path: str) -> tuple[str, os.stat_result | None]:
        full_path, stat_result = super().lookup_path(path)
        if stat_result is None:
            # No static file matches — fall back to index.html for SPA routing.
            return super().lookup_path("index.html")
        return full_path, stat_result


@asynccontextmanager
async def app_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    run_migrations()
    yield


app = FastAPI(title="PXC Notebook", version="0.1.0", lifespan=app_lifespan)

app.mount("/static", StaticFiles(directory=constants.STATIC_DIR), name="static")

app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(activities.router)
app.include_router(activity_runtime.router)
app.include_router(course_activities.router)
app.include_router(lti.router, prefix="/lti")

if constants.FRONTEND_DIR.is_dir():
    app.mount(
        "/",
        SPAStaticFiles(directory=constants.FRONTEND_DIR, html=True),
        name="frontend",
    )
