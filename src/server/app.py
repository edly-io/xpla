"""
FastAPI application factory for the learning activity server.
"""

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from server.host_functions import create_host_functions
from server.runtime import PluginRuntime


app = FastAPI(
    title="Learning Activity Server",
    description="LMS simulation for learning activity development",
    version="0.2.0",
)


class Activity:
    """
    Static class to handle WASM runtime
    """

    RUNTIME: PluginRuntime | None = None

    @classmethod
    def load(cls, activity_dir: Path) -> None:
        """
        Load a .js activity file.
        """
        manifest = load_manifest(activity_dir)

        # Initialize host functions (KV store, LMS, etc.) with capability enforcement
        host_functions = create_host_functions(activity_dir, manifest)

        # Load plugin if present
        plugin_path = activity_dir / "plugin.wasm"

        if plugin_path.exists():
            cls.RUNTIME = PluginRuntime(plugin_path, host_functions=host_functions)
            cls.RUNTIME.load()

    @classmethod
    def unload(cls) -> None:
        """
        Call this whenever the activity runtime is no longer needed to free memory.
        """
        if cls.RUNTIME:
            cls.RUNTIME = None


def load_manifest(activity_dir: Path) -> dict[str, Any]:
    """Load the activity manifest from the directory."""
    manifest_path = activity_dir / "manifest.json"
    with manifest_path.open() as f:
        manifest: dict[str, Any] = json.load(f)
        return manifest


def create_app(activity_dir: Path, lib_dir: Path) -> FastAPI:
    """Create and configure the FastAPI application."""
    Activity.load(activity_dir)

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
    if Activity.RUNTIME is None:
        raise HTTPException(status_code=404, detail="Activity has no WASM runtime")

    body = await request.body()
    try:
        result = Activity.RUNTIME.call(function_name, body)
        return JSONResponse(content={"result": result.decode("utf-8")})
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up on shutdown."""
    Activity.unload()
