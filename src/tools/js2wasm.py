#!/bin/env python
"""
Build utility for compiling JavaScript plugins to WebAssembly.

Uses esbuild to bundle imports, then extism-js to compile to WASM.
"""

import argparse
import subprocess
import tempfile
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

    with tempfile.TemporaryDirectory() as tmpdir:
        bundled_js = Path(tmpdir) / "bundled.js"

        print(f"Bundling {input_js}")
        subprocess.check_call(
            [
                "esbuild",
                str(input_js),
                "--bundle",
                "--format=cjs",
                "--platform=neutral",
                f"--outfile={bundled_js}",
            ]
        )

        print(f"Compiling -> {output_wasm}")
        dts_path = Path(__file__).parent.parent / "sandbox-lib" / "sandbox.d.ts"
        cmd = [
            "extism-js",
            str(bundled_js),
            "-o",
            str(output_wasm),
            "-i",
            str(dts_path),
        ]
        subprocess.check_call(cmd)


if __name__ == "__main__":
    main()
