#!/usr/bin/env python
"""
Load a WASM component such that its cache is up-to-date.
"""

import argparse
from pathlib import Path

from pxc.lib import sandbox


def main() -> None:
    parser = argparse.ArgumentParser(
        "Cache a .wasm component and store it in .wasm.bin for later reuse"
    )
    parser.add_argument("component_path", help="Path to the .wasm file", type=Path)
    args = parser.parse_args()

    engine = sandbox.create_engine()
    sandbox.load_component(engine, args.component_path)


if __name__ == "__main__":
    main()
