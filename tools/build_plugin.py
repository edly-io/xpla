#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Build utility for compiling JavaScript plugins to WebAssembly.

Requires extism-js CLI to be installed:
  curl -O https://raw.githubusercontent.com/extism/js-pdk/main/install.sh
  bash install.sh

Also requires binaryen tools (wasm-merge, wasm-opt):
  - macOS: brew install binaryen
  - Linux: apt install binaryen

Usage: ./build_plugin.py <plugin.js> [-o output.wasm]
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def check_dependencies() -> bool:
    """Check that required tools are installed."""
    missing = []

    if shutil.which("extism-js") is None:
        missing.append("extism-js")

    if shutil.which("wasm-merge") is None:
        missing.append("wasm-merge (from binaryen)")

    if missing:
        print("Missing required tools:", file=sys.stderr)
        for tool in missing:
            print(f"  - {tool}", file=sys.stderr)
        print("\nInstall extism-js:", file=sys.stderr)
        print("  curl -O https://raw.githubusercontent.com/extism/js-pdk/main/install.sh", file=sys.stderr)
        print("  bash install.sh", file=sys.stderr)
        print("\nInstall binaryen:", file=sys.stderr)
        print("  macOS: brew install binaryen", file=sys.stderr)
        print("  Linux: apt install binaryen", file=sys.stderr)
        return False

    return True


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
        "-o", "--output",
        type=Path,
        default=None,
        help="Output WebAssembly file (default: <input>.wasm)",
    )
    return parser.parse_args(args)


def main() -> None:
    """Entry point."""
    args = parse_args(sys.argv[1:])

    if not check_dependencies():
        sys.exit(1)

    input_js = args.input.resolve()
    output_wasm = args.output or input_js.with_suffix(".wasm")

    if not build_plugin(input_js, output_wasm):
        sys.exit(1)


if __name__ == "__main__":
    main()
