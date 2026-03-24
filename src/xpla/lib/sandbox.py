import logging
from pathlib import Path
from typing import Any, Callable

import wasmtime
import wasmtime.component

logger = logging.getLogger(__file__)


class SandboxRuntimeError(RuntimeError):
    """
    Raised whenever there is an error in a sandbox executor at runtime.
    """


class ForbiddenImportError(ValueError):
    """
    Raised when a WASM component imports a forbidden interface (e.g. wasi:http).
    """


class RecordArg:
    """
    This is used to convert from dict arguments/return values to WIT's 'record' type.
    """

    def __init__(self, values: dict[str, Any]) -> None:
        for key, value in values.items():
            setattr(self, key, value)


class SandboxExecutor:
    """
    Abstract base class implementation for all sandbox executors.
    """

    def __init__(
        self, plugin_path: Path, host_functions: dict[str, Callable[..., Any]]
    ) -> None:
        self._plugin_path = plugin_path
        self._host_functions = host_functions

    def call_function(self, function_name: str, *args: Any) -> bytes:
        raise NotImplementedError


class SandboxComponentExecutor(SandboxExecutor):
    """
    Sandboxed WASM Component Model execution via wasmtime.
    """

    def __init__(
        self, plugin_path: Path, host_functions: dict[str, Callable[..., Any]]
    ) -> None:
        super().__init__(plugin_path, host_functions)

        self._plugin_path = plugin_path
        self._host_functions = host_functions
        self.__store: wasmtime.Store | None = None
        self.__instance: wasmtime.component.Instance | None = None

    @property
    def _store(self) -> wasmtime.Store:
        """
        Create a wasmtime store and engine with wasi features.
        """
        if not self.__store:
            engine_config = wasmtime.Config()
            # engine_config.cache = True # Cache to directory. Do we need this?
            engine = wasmtime.Engine(engine_config)
            self.__store = wasmtime.Store(engine)
            wasi_config = wasmtime.WasiConfig()
            wasi_config.inherit_stdout()
            wasi_config.inherit_stderr()
            self._store.set_wasi(wasi_config)
        return self.__store

    @property
    def _instance(self) -> wasmtime.component.Instance:
        if not self.__instance:
            component = load_component(self._store.engine, self._plugin_path)
            linker = wasmtime.component.Linker(self._store.engine)
            linker.add_wasip2()

            # Register host functions — wrap to absorb the `store` first arg
            # (wasmtime passes store as first arg to all host function callbacks)
            with linker.root().add_instance("xpla:sandbox/host") as ctx:
                for wit_name, func in self._host_functions.items():
                    ctx.add_func(wit_name, make_host_function(func))

            self.__instance = linker.instantiate(self._store, component)
        return self.__instance

    def call_function(self, function_name: str, *args: Any) -> bytes:
        """
        Call an exported function on the WASM component.
        """
        func = self._instance.get_func(self._store, function_name)
        if func is None:
            raise SandboxRuntimeError(
                f"Component {self._plugin_path}: export '{function_name}' not found"
            )
        try:
            result = call_sandbox_function(self._store, func, *args)
        except wasmtime.WasmtimeError as e:
            raise SandboxRuntimeError(
                f"Component {self._plugin_path}: error running '{function_name}' with arguments: {args}"
            ) from e
        except Exception as e:
            raise SandboxRuntimeError(
                f"Component {self._plugin_path}: error running '{function_name}'"
            ) from e
        return result.encode("utf-8") if isinstance(result, str) else b""


def load_component(
    engine: wasmtime.Engine, plugin_path: Path
) -> wasmtime.component.Component:
    """
    Load a component and cache the result in a <plugin_path>.bin file. Automatically
    load this file if it's more recent than the plugin file. Else, update it.
    """
    bin_path = plugin_path.parent / (plugin_path.name + ".bin")
    if bin_path.exists() and bin_path.stat().st_mtime > plugin_path.stat().st_mtime:
        # Load serialized file
        return wasmtime.component.Component.deserialize_file(engine, str(bin_path))

    # Create new component and serialize
    component = wasmtime.component.Component.from_file(engine, str(plugin_path))
    bin_path.write_bytes(component.serialize())
    return component


def make_host_function(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Convert our host functions to a format that is understandable by wasmtime.

    1. All host functions take a Store as a first argument
    2. We need to convert Record args to dict
    """

    def host_function(_store: wasmtime.Store, *args: Any) -> Any:
        func_args = []
        for arg in args:
            # Convert Record args to dict
            if isinstance(arg, wasmtime.component.Record):
                arg_dict = arg.__dict__.copy()
                func_args.append(arg_dict)
            else:
                func_args.append(arg)
        result = func(*func_args)
        if isinstance(result, dict):
            return RecordArg(result)
        return result

    return host_function


def call_sandbox_function(
    store: wasmtime.Store, func: wasmtime.component.Func, *args: Any
) -> Any:
    """
    To call a sandbox function we must:

    1. add the store as the first argument
    2. convert dict arguments to records
    3. call "post_return" after every call, to avoid memory leaks
    """
    func_args = []
    for arg in args:
        if isinstance(arg, dict):
            record_arg = RecordArg(arg)
            func_args.append(record_arg)
        else:
            func_args.append(arg)
    try:
        return func(store, *func_args)
    finally:
        func.post_return(store)


def get_sandbox_executor(
    plugin_path: Path, host_functions: dict[str, Callable[..., Any]]
) -> SandboxExecutor:
    """
    Return a sandbox executor for this plugin.
    """
    return SandboxComponentExecutor(plugin_path, host_functions)
