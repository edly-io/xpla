#!/usr/bin/env python
"""
Validate manifest.json files against the xPLA manifest schema.
"""

import argparse
import json
import sys
from pathlib import Path

import jsonschema


def main() -> None:
    """Entry point. Returns 0 on success, 1 on validation errors."""
    args = parse_args()
    schema = load_schema()
    validate_manifest(args.manifest, schema)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Validate xPLA manifest.json files")
    parser.add_argument(
        "manifest",
        type=Path,
        help="Path to manifest.json file",
    )
    return parser.parse_args()


def load_schema() -> dict[str, object]:
    """Load the JSON schema from the sandbox-lib directory."""
    schema_path = Path(__file__).parent.parent / "sandbox-lib" / "manifest.schema.json"
    with open(schema_path, encoding="utf-8") as f:
        schema: dict[str, object] = json.load(f)
    return schema


def validate_manifest(manifest_path: Path, schema: dict[str, object]) -> None:
    """Validate a single manifest file against the schema.

    Returns True if valid, False otherwise.
    """
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    try:
        jsonschema.validate(manifest, schema)
        print("OK👌")
    except jsonschema.ValidationError as e:
        print(f"ERROR: {e.message}")
        if e.absolute_path:
            path = ".".join(str(p) for p in e.absolute_path)
            print(f"  at: {path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
