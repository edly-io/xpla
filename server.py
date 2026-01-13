#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastapi>=0.115.0",
#     "uvicorn[standard]>=0.32.0",
#     "extism>=1.0.0",
# ]
# ///
"""
Learning Activity Development Server.

A minimal LMS simulation for testing learning activities locally.

Usage: ./server.py [activity_dir]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from host_functions import create_host_functions
from runtime import PluginRuntime


def load_manifest(activity_dir: Path) -> dict[str, Any]:
    """Load the activity manifest from the directory."""
    manifest_path = activity_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest.json found in {activity_dir}")

    with manifest_path.open() as f:
        return json.load(f)


def create_app(activity_dir: Path, lib_dir: Path) -> FastAPI:
    """Create and configure the FastAPI application."""
    manifest = load_manifest(activity_dir)
    activity_id = str(manifest.get("name", "unknown"))

    app = FastAPI(
        title="Learning Activity Server",
        description="LMS simulation for learning activity development",
        version="0.2.0",
    )

    @app.get("/api/manifest")
    async def get_manifest() -> JSONResponse:
        """Return the activity manifest."""
        return JSONResponse(content=manifest)

    # Initialize host functions (KV store, LMS, etc.) with capability enforcement
    host_functions = create_host_functions(activity_dir, activity_id, manifest)

    # Load plugin if present
    plugin_path = activity_dir / "plugin.wasm"
    runtime: PluginRuntime | None = None

    if plugin_path.exists():
        runtime = PluginRuntime(plugin_path, host_functions=host_functions)
        runtime.load()

    @app.post("/api/plugin/{function_name}")
    async def call_plugin(function_name: str, request: Request) -> JSONResponse:
        """Execute a function in the activity plugin."""
        if runtime is None:
            raise HTTPException(status_code=404, detail="No plugin loaded")

        body = await request.body()
        try:
            result = runtime.call(function_name, body)
            return JSONResponse(content={"result": result.decode("utf-8")})
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        """Clean up plugin on shutdown."""
        if runtime is not None:
            runtime.close()

    # KV store API endpoints (for frontend and debugging)
    from host_functions import _kv_store

    @app.get("/api/kv/{key}")
    async def kv_get_endpoint(key: str) -> JSONResponse:
        """Get a value from the KV store."""
        if _kv_store is None:
            raise HTTPException(status_code=503, detail="KV store not initialized")
        value = _kv_store.get(key)
        if value is None:
            raise HTTPException(status_code=404, detail="Key not found")
        return JSONResponse(content={"key": key, "value": value})

    @app.put("/api/kv/{key}")
    async def kv_set_endpoint(key: str, request: Request) -> JSONResponse:
        """Set a value in the KV store."""
        if _kv_store is None:
            raise HTTPException(status_code=503, detail="KV store not initialized")
        body = await request.body()
        _kv_store.set(key, body.decode("utf-8"))
        return JSONResponse(content={"key": key, "status": "ok"})

    @app.delete("/api/kv/{key}")
    async def kv_delete_endpoint(key: str) -> JSONResponse:
        """Delete a key from the KV store."""
        if _kv_store is None:
            raise HTTPException(status_code=503, detail="KV store not initialized")
        if _kv_store.delete(key):
            return JSONResponse(content={"key": key, "status": "deleted"})
        raise HTTPException(status_code=404, detail="Key not found")

    @app.get("/api/kv")
    async def kv_list_endpoint() -> JSONResponse:
        """List all keys in the KV store."""
        if _kv_store is None:
            raise HTTPException(status_code=503, detail="KV store not initialized")
        return JSONResponse(content={"keys": _kv_store.keys()})

    # LMS simulation endpoints (use the LMS initialized by host functions)
    from host_functions import _lms as lms
    assert lms is not None  # Guaranteed by create_host_functions

    @app.get("/api/lms/user")
    async def get_lms_user() -> JSONResponse:
        """Get current LMS user info."""
        user = lms.get_current_user()
        return JSONResponse(
            content={
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "roles": user.roles,
            }
        )

    @app.post("/api/lms/grade")
    async def submit_lms_grade(request: Request) -> JSONResponse:
        """Submit a grade for the current activity."""
        body = await request.json()
        record = lms.submit_grade(
            score=float(body["score"]),
            max_score=float(body.get("max_score", 100)),
            comment=str(body.get("comment", "")),
        )
        return JSONResponse(
            content={
                "status": "submitted",
                "user_id": record.user_id,
                "score": record.score,
                "max_score": record.max_score,
                "timestamp": record.timestamp.isoformat(),
            }
        )

    @app.get("/api/lms/grades")
    async def get_lms_grades() -> JSONResponse:
        """Get all grades for the current activity."""
        records = lms.get_grades()
        return JSONResponse(content={"grades": [r.to_dict() for r in records]})

    @app.get("/api/lms/grades/best")
    async def get_lms_best_grade() -> JSONResponse:
        """Get the best grade for the current user."""
        record = lms.get_best_grade()
        if record is None:
            raise HTTPException(status_code=404, detail="No grades found")
        return JSONResponse(content=record.to_dict())

    # Serve core library from lib_dir (learningactivity.js)
    app.mount("/lib", StaticFiles(directory=lib_dir), name="lib")

    # Serve activity files (must be last - catch-all)
    app.mount("/", StaticFiles(directory=activity_dir, html=True), name="activity")

    return app


def parse_args(args: list[str]) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Learning Activity Development Server"
    )
    parser.add_argument(
        "activity_dir",
        type=Path,
        help="Path to activity directory containing manifest.json",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )
    return parser.parse_args(args)


def main() -> None:
    """Entry point for the server."""
    args = parse_args(sys.argv[1:])

    activity_dir = args.activity_dir.resolve()
    if not activity_dir.is_dir():
        print(f"Error: {activity_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    lib_dir = Path(__file__).parent

    try:
        app = create_app(activity_dir, lib_dir)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Serving activity from: {activity_dir}")
    print(f"Library files from: {lib_dir}")
    print(f"Open http://{args.host}:{args.port}/ in your browser")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
