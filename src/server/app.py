"""
FastAPI application for the learning activity server.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from server.activities.context import ActivityContext, MissingSandboxError
from server import constants


class ActivityNotFound(Exception):
    """Raised when an activity cannot be found."""


def load_activity(activity_id: str) -> ActivityContext:
    """Load an activity by ID from the samples directory."""
    if activity_id not in list_activities():
        raise ActivityNotFound(f"Activity '{activity_id}' not found")

    activity_dir = constants.SAMPLES_DIR / activity_id
    manifest_path = activity_dir / "manifest.json"
    if not manifest_path.exists():
        raise ActivityNotFound(f"Activity '{activity_id}' has no manifest.json")

    return ActivityContext(activity_dir)


def list_activities() -> list[str]:
    return sorted(d.name for d in constants.SAMPLES_DIR.iterdir() if d.is_dir())


app = FastAPI(
    title="Learning Activity Server",
    description="LMS simulation for learning activity development",
    version="0.3.0",
)

app.mount("/static", StaticFiles(directory=constants.STATIC_DIR), name="static")
templates = Jinja2Templates(directory=constants.TEMPLATES_DIR)


@app.get("/")
async def home(request: Request) -> HTMLResponse:
    """List all available activities."""
    return templates.TemplateResponse(
        request=request, name="home.html", context={"activities": list_activities()}
    )


@app.get("/a/{activity_id}")
async def activity(request: Request, activity_id: str) -> HTMLResponse:
    """Serve an activity"""
    try:
        activity_context = load_activity(activity_id)
    except ActivityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    # TODO get user_id from session/auth
    user_id = "anonymous"
    initial_values = activity_context.get_all_values(user_id)

    return templates.TemplateResponse(
        request=request,
        name="activity.html",
        context={
            "activity_context": activity_context,
            "initial_values": initial_values,
        },
    )


@app.get("/a/{activity_id}/{file_path:path}")
async def activity_asset(activity_id: str, file_path: str) -> FileResponse:
    """Serve static files from an activity directory."""
    try:
        activity_context = load_activity(activity_id)
    except ActivityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    full_path = activity_context.activity_dir / file_path
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    # Security: ensure path doesn't escape activity directory
    try:
        full_path.resolve().relative_to(activity_context.activity_dir.resolve())
    except ValueError as e:
        raise HTTPException(status_code=403, detail="Access denied") from e

    return FileResponse(full_path)


@app.post("/api/{activity_id}/plugin/{function_name}")
async def call_plugin(
    activity_id: str, function_name: str, request: Request
) -> JSONResponse:
    """Execute a function in the activity plugin."""
    try:
        context = load_activity(activity_id)
    except ActivityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    body = await request.body()
    try:
        result = context.call_sandbox_function(function_name, body)
    except MissingSandboxError as e:
        raise HTTPException(
            status_code=404, detail="Activity has no WASM runtime"
        ) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return JSONResponse(content={"result": result.decode("utf-8")})
