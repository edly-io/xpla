#!/bin/env python
"""
Build utility for compiling JavaScript plugins to WebAssembly.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Entry point."""
    args = parse_args(sys.argv[1:])

    input_js = args.input.resolve()
    output_wasm = args.output or input_js.with_suffix(".wasm")
    build_plugin(input_js, output_wasm)


def build_plugin(input_js: Path, output_wasm: Path) -> bool:
    """Compile a JavaScript file to WebAssembly.

    Args:
        input_js: Path to the input JavaScript file.
        output_wasm: Path to the output WebAssembly file.

    Returns:
        True if compilation succeeded, False otherwise.
    """
    if not input_js.exists():
        print(f"Error: Input file not found: {input_js}", file=sys.stderr)
        return False

    # Check for optional TypeScript definitions
    dts_path = input_js.with_suffix(".d.ts")
    cmd = ["extism-js", str(input_js), "-o", str(output_wasm)]

    if dts_path.exists():
        cmd.extend(["-i", str(dts_path)])

    print(f"Compiling {input_js} -> {output_wasm}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("Compilation failed:", file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        if result.stdout:
            print(result.stdout, file=sys.stderr)
        return False

    print(f"Successfully built: {output_wasm}")
    return True


def parse_args(args: list[str]) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Build JavaScript plugins to WebAssembly"
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
        help="Output WebAssembly file (default: <input>.wasm)",
    )
    return parser.parse_args(args)


if __name__ == "__main__":
    main()
