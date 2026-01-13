#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastapi>=0.115.0",
#     "uvicorn[standard]>=0.32.0",
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
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles


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

    app = FastAPI(
        title="Learning Activity Server",
        description="LMS simulation for learning activity development",
        version="0.2.0",
    )

    @app.get("/api/manifest")
    async def get_manifest() -> JSONResponse:
        """Return the activity manifest."""
        return JSONResponse(content=manifest)

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
