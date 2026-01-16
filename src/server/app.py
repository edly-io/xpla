"""
FastAPI application factory for the learning activity server.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from server.activities.context import ActivityContext, MissingSandboxError

app = FastAPI(
    title="Learning Activity Server",
    description="LMS simulation for learning activity development",
    version="0.2.0",
)


def create_app(activity_dir: Path, lib_dir: Path) -> FastAPI:
    """Create and configure the FastAPI application."""
    ActivityContext.load(activity_dir)

    # Serve core library from lib_dir (learningactivity.js)
    app.mount("/lib", StaticFiles(directory=lib_dir), name="lib")

    # Serve activity files (must be last - catch-all)
    app.mount("/", StaticFiles(directory=activity_dir, html=True), name="activity")

    return app


# TODO we need to simplify this to handle events instead of the frontend
# directly calling the plugin functions
@app.post("/api/plugin/{function_name}")
async def call_plugin(function_name: str, request: Request) -> JSONResponse:
    """Execute a function in the activity plugin."""
    # TODO get rid of this check once we load activities dynamically
    assert ActivityContext.INSTANCE is not None

    body = await request.body()
    try:
        result = ActivityContext.INSTANCE.call_sandbox_function(function_name, body)
    except MissingSandboxError as e:
        raise HTTPException(
            status_code=404, detail="Activity has no WASM runtime"
        ) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return JSONResponse(content={"result": result.decode("utf-8")})


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up on shutdown."""
    # TODO get rid of this
    ActivityContext.INSTANCE = None
