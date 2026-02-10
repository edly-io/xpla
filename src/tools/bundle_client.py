#!/bin/env python
"""
Build utility for bundling client-side JavaScript with npm dependencies.

Uses esbuild to bundle imports into a single ESM file suitable for browsers.
CSS imports are inlined as text strings (for shadow DOM injection).
"""

import argparse
import subprocess
from pathlib import Path


def main() -> None:
    """Entry point."""
    args = parse_args()

    input_js = args.input.resolve()
    output_js = args.output or input_js.with_suffix(".bundle.js")
    bundle_client(input_js, output_js)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Bundle client JavaScript with npm dependencies"
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input JavaScript file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output bundled file (default: <input>.bundle.js)",
    )
    return parser.parse_args()


def bundle_client(input_js: Path, output_js: Path) -> None:
    """Bundle a client JavaScript file with its dependencies.

    Args:
        input_js: Path to the input JavaScript file.
        output_js: Path to the output bundled file.
    """
    print(f"Bundling {input_js} -> {output_js}")
    subprocess.check_call(
        [
            "esbuild",
            str(input_js),
            "--bundle",
            "--format=esm",
            "--loader:.css=text",
            f"--outfile={output_js}",
        ]
    )


if __name__ == "__main__":
    main()
