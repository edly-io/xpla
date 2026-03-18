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


class SandboxRuntimeError(RuntimeError):
    """
    Raised whenever there is an error in a sandbox executor at runtime.
    """


class SandboxExecutor:
    """
    Abstract base class implementation for all sandbox executors.
    """

    def __init__(
        self, plugin_path: Path, host_functions: list[Callable[..., Any]]
    ) -> None:
        self._plugin_path = plugin_path
        self._host_functions = host_functions

    def call_function(self, function_name: str, data: Any) -> bytes:
        raise NotImplementedError


class SandboxWasmExecutor(SandboxExecutor):
    """
    Sandboxed Extism code execution.
    """

    def __init__(
        self, plugin_path: Path, host_functions: list[Callable[..., Any]]
    ) -> None:
        super().__init__(plugin_path, host_functions)
        extism_host_functions = [host_fn()(func) for func in self._host_functions]
        self._plugin = extism.Plugin(
            {"wasm": [{"path": str(self._plugin_path)}]},
            wasi=True,
            functions=extism_host_functions or None,
        )

    def call_function(self, function_name: str, data: Any) -> bytes:
        """
        Call a function that is exposed in the sandbox. Input data will be
        JSON-formatted.
        """
        data_bytes = b"" if data is None else json.dumps(data).encode("utf8")
        try:
            result = self._plugin.call(function_name, data_bytes)
        except extism.Error as e:
            raise SandboxRuntimeError(
                f"Extism plugin {self._plugin_path}: error running sandbox function '{function_name}': {e.args[0]}"
            ) from e
        return bytes(result)


def get_sandbox_executor(
    plugin_path: Path, host_functions: list[Callable[..., Any]]
) -> SandboxExecutor:
    """
    Return the right executor for this plugin

    For now we only support Wasm executor, but this could change in the future.
    """
    return SandboxWasmExecutor(plugin_path, host_functions)
