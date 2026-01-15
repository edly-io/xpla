"""
Extism runtime wrapper for learning activity plugins.

This module provides the interface between FastAPI and Extism plugins.
"""

from pathlib import Path
from typing import Any

import extism


class PluginRuntime:
    """Manages an Extism plugin instance for a learning activity."""

    def __init__(
        self,
        wasm_path: Path,
        host_functions: list[Any] | None = None,
    ) -> None:
        """Initialize the plugin runtime.

        Args:
            wasm_path: Path to the WebAssembly plugin file.
            host_functions: Optional list of host functions to register.

        Raises:
            FileNotFoundError: If the wasm file does not exist.
        """
        if not wasm_path.exists():
            raise FileNotFoundError(f"Plugin not found: {wasm_path}")

        self._wasm_path = wasm_path
        self._host_functions = host_functions or []
        self._plugin: extism.Plugin | None = None

    def load(self) -> None:
        """Load the plugin into memory."""
        manifest = {"wasm": [{"path": str(self._wasm_path)}]}
        self._plugin = extism.Plugin(
            manifest,
            wasi=True,
            functions=self._host_functions if self._host_functions else None,
        )

    def call(self, function_name: str, input_data: bytes) -> bytes:
        """Call a function in the plugin.

        Args:
            function_name: Name of the exported function to call.
            input_data: Input bytes to pass to the function.

        Returns:
            Output bytes from the function.

        Raises:
            RuntimeError: If plugin is not loaded or function call fails.
        """
        if self._plugin is None:
            raise RuntimeError("Plugin not loaded. Call load() first.")

        result = self._plugin.call(function_name, input_data)
        return bytes(result)

    def __enter__(self) -> "PluginRuntime":
        """Context manager entry."""
        self.load()
        return self
