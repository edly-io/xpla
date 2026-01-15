#!/bin/env python
"""
Learning Activity Development Server.

A minimal LMS simulation for testing learning activities locally.

Usage: python -m server [activity_dir]
"""

import argparse
import sys
from pathlib import Path

import uvicorn

from server.app import create_app


def parse_args(args: list[str]) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Learning Activity Development Server")
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

    lib_dir = Path(__file__).parent.parent / "lib"

    app = create_app(activity_dir, lib_dir)

    print(f"Serving activity from: {activity_dir}")
    print(f"Library files from: {lib_dir}")
    print(f"Open http://{args.host}:{args.port}/ in your browser")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
