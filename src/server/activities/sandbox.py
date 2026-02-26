import json
import logging
from pathlib import Path
from typing import Callable, Any

from extism import host_fn
from server.activities.runtime import PluginRuntime

logger = logging.getLogger(__file__)


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

    # TODO exception management: not implemented error?
    def call_function(self, name: str, arg: Any) -> bytes:
        """
        Call a function that is exposed in the sandbox. Input data will be
        JSON-formatted.
        """
        arg_bytes = b"" if arg is None else json.dumps(arg).encode("utf8")
        return self.wasm_runtime.call(name, arg_bytes)
