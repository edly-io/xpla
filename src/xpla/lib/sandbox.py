import json
import logging
from pathlib import Path
from typing import Any, Callable

import extism
from extism import host_fn

# TODO this is not portable
# This allows developers to log and troubleshoot issues with `console.log(...)`
extism.set_log_file("/dev/stdout", "info")

logger = logging.getLogger(__file__)


class SandboxRuntime:
    """Manages an Extism plugin instance for xPLA."""

    def __init__(
        self,
        wasm_path: Path,
        host_functions: list[Any] | None = None,
    ) -> None:
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
        if self._plugin is None:
            raise RuntimeError("Plugin not loaded. Call load() first.")
        result = self._plugin.call(function_name, input_data)
        return bytes(result)


class SandboxExecutor:
    """
    Sandboxed Exism code execution.
    """

    def __init__(
        self, plugin_path: Path, host_functions: list[Callable[..., Any]]
    ) -> None:

        extism_host_functions = [host_fn()(func) for func in host_functions]
        self.wasm_runtime = SandboxRuntime(
            plugin_path, host_functions=extism_host_functions
        )
        self.wasm_runtime.load()

    # TODO exception management: not implemented error?
    def call_function(self, name: str, arg: Any) -> bytes:
        """
        Call a function that is exposed in the sandbox. Input data will be
        JSON-formatted.
        """
        arg_bytes = b"" if arg is None else json.dumps(arg).encode("utf8")
        return self.wasm_runtime.call(name, arg_bytes)
