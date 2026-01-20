from pathlib import Path
from typing import Callable, Any

from extism import host_fn
from server.activities.runtime import PluginRuntime


class SandboxExecutor:
    """
    Sandboxed Exism code execution.
    """

    def __init__(
        self, plugin_path: Path, host_functions: list[Callable[..., Any]]
    ) -> None:

        extism_host_functions = [host_fn()(func) for func in host_functions]
        self.wasm_runtime = PluginRuntime(
            plugin_path, host_functions=extism_host_functions
        )
        self.wasm_runtime.load()

    # TODO standardize the input_data format? We need something that is compact,
    # inspectable and works everywhere (including in the frontend)
    # TODO exception management: not implemented error?
    def call_function(self, name: str, input_data: bytes) -> bytes:
        return self.wasm_runtime.call(name, input_data)
