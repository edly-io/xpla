#!/bin/env python
"""
Build utility for compiling JavaScript plugins to WebAssembly.
"""

import argparse
import subprocess
from pathlib import Path


def main() -> None:
    """Entry point."""
    args = parse_args()

    input_js = args.input.resolve()
    output_wasm = args.output or input_js.with_suffix(".wasm")
    js_to_wasm(input_js, output_wasm)


def parse_args() -> argparse.Namespace:
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
    return parser.parse_args()


def js_to_wasm(input_js: Path, output_wasm: Path) -> None:
    """Compile a JavaScript file to WebAssembly.

    Args:
        input_js: Path to the input JavaScript file.
        output_wasm: Path to the output WebAssembly file.
    """
    # Check for optional TypeScript definitions
    dts_path = input_js.with_suffix(".d.ts")
    cmd = ["extism-js", str(input_js), "-o", str(output_wasm)]
    if dts_path.exists():
        cmd.extend(["-i", str(dts_path)])

    print(f"Compiling {input_js} -> {output_wasm}")
    subprocess.check_call(cmd)


if __name__ == "__main__":
    main()
