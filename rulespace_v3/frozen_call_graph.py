"""Private-global cloning for authority call graphs.

Authority entry points retain their normal Python signatures, while every
reachable project function and referenced module attribute is copied into a
private globals mapping.  Later module rebinding therefore cannot alter an
already assembled issuer or consumer graph.
"""

from __future__ import annotations

import functools
import inspect
import types
from typing import Callable


def freeze_rulespace_call_graph(
    root: Callable,
    *,
    _partial_type=functools.partial,
) -> Callable:
    """Clone one reachable ``rulespace_v3`` call graph into private globals."""

    function_memo: dict[int, Callable] = {}
    module_memo: dict[tuple[int, tuple[str, ...]], object] = {}
    class_snapshots: dict[
        int,
        tuple[
            type,
            tuple[tuple[str, object], ...],
            frozenset[str],
        ],
    ] = {}

    def capture_project_class(value: type) -> type:
        class_id = id(value)
        if class_id not in class_snapshots:
            items = tuple(vars(value).items())
            class_snapshots[class_id] = (
                value,
                items,
                frozenset(name for name, _ in items),
            )
        return value

    def referenced_code_names(code: types.CodeType) -> tuple[str, ...]:
        names = list(code.co_names)
        for constant in code.co_consts:
            if isinstance(constant, types.CodeType):
                names.extend(referenced_code_names(constant))
        return tuple(dict.fromkeys(names))

    def freeze_value(
        value: object,
        referenced_names: tuple[str, ...] = (),
    ) -> object:
        if inspect.isfunction(value) and value.__module__.startswith(
            "rulespace_v3."
        ):
            return freeze_function(value)
        if inspect.isclass(value) and value.__module__.startswith(
            "rulespace_v3."
        ):
            return capture_project_class(value)
        if type(value) is _partial_type:
            keywords = value.keywords or {}
            return _partial_type(
                freeze_value(value.func),
                *(freeze_value(item) for item in value.args),
                **{
                    key: freeze_value(item)
                    for key, item in keywords.items()
                },
            )
        if inspect.ismodule(value):
            module_values = vars(value)
            key = (id(value), referenced_names)
            cached = module_memo.get(key)
            if cached is not None:
                return cached
            proxy = types.SimpleNamespace()
            module_memo[key] = proxy
            for name in referenced_names:
                if name in module_values:
                    setattr(
                        proxy,
                        name,
                        freeze_value(module_values[name], referenced_names),
                    )
            return proxy
        if type(value) is tuple:
            return tuple(freeze_value(item) for item in value)
        if type(value) is list:
            return [freeze_value(item) for item in value]
        if type(value) is dict:
            return {key: freeze_value(item) for key, item in value.items()}
        return value

    def freeze_closure_value(
        value: object,
        referenced_names: tuple[str, ...],
    ) -> object:
        if inspect.isfunction(value) and value.__module__.startswith(
            "rulespace_v3."
        ):
            return freeze_function(value)
        if inspect.isclass(value) and value.__module__.startswith(
            "rulespace_v3."
        ):
            return capture_project_class(value)
        if type(value) is _partial_type:
            return freeze_value(value)
        if inspect.ismodule(value):
            return freeze_value(value, referenced_names)
        if type(value) is tuple:
            return tuple(
                freeze_closure_value(item, referenced_names)
                for item in value
            )
        return value

    def make_cell(value: object) -> object:
        def read_cell() -> object:
            return value

        return read_cell.__closure__[0]

    def freeze_function(function: Callable) -> Callable:
        cached = function_memo.get(id(function))
        if cached is not None:
            return cached
        source_globals = function.__globals__
        builtins_body = source_globals.get("__builtins__", {})
        private_builtins = (
            dict(builtins_body)
            if type(builtins_body) is dict
            else dict(vars(builtins_body))
        )
        private_globals: dict[str, object] = {
            "__builtins__": private_builtins,
            "__name__": source_globals.get("__name__", __name__),
            "__package__": source_globals.get("__package__", __package__),
        }
        source_closure = function.__closure__
        private_cells = (
            None
            if source_closure is None
            else tuple(make_cell(None) for _ in source_closure)
        )
        clone = types.FunctionType(
            function.__code__,
            private_globals,
            function.__name__,
            None,
            private_cells,
        )
        function_memo[id(function)] = clone
        referenced_names = referenced_code_names(function.__code__)
        if source_closure is not None:
            assert private_cells is not None
            for private_cell, source_cell in zip(
                private_cells,
                source_closure,
            ):
                private_cell.cell_contents = freeze_closure_value(
                    source_cell.cell_contents,
                    referenced_names,
                )
        for name in referenced_names:
            if name in source_globals:
                private_globals[name] = freeze_value(
                    source_globals[name],
                    referenced_names,
                )
        clone.__defaults__ = (
            None
            if function.__defaults__ is None
            else tuple(
                freeze_value(item, referenced_names)
                for item in function.__defaults__
            )
        )
        clone.__kwdefaults__ = (
            None
            if function.__kwdefaults__ is None
            else {
                key: freeze_value(item, referenced_names)
                for key, item in function.__kwdefaults__.items()
            }
        )
        clone.__annotations__ = dict(function.__annotations__)
        clone.__qualname__ = function.__qualname__
        clone.__doc__ = function.__doc__
        return clone

    frozen_root = freeze_function(root)
    snapshots = tuple(class_snapshots.values())
    missing = object()
    builtin_vars = vars
    runtime_error = RuntimeError

    def guarded_root(*args, **kwargs):
        for project_class, expected_items, expected_names in snapshots:
            current = builtin_vars(project_class)
            # ``copyreg`` may add a benign ``__slotnames__`` cache after the
            # graph is frozen.  Preserve every captured dependency exactly,
            # while allowing only that cache attribute to appear later.
            if any(
                name not in expected_names and name != "__slotnames__"
                for name in current
            ) or any(
                current.get(name, missing) is not expected
                for name, expected in expected_items
            ):
                raise runtime_error(
                    "frozen call-graph class dependency drifted: "
                    f"{project_class.__module__}.{project_class.__qualname__}"
                )
        return frozen_root(*args, **kwargs)

    guarded_root.__name__ = frozen_root.__name__
    guarded_root.__qualname__ = frozen_root.__qualname__
    guarded_root.__doc__ = frozen_root.__doc__
    guarded_root.__annotations__ = dict(frozen_root.__annotations__)
    guarded_root.__signature__ = inspect.signature(frozen_root)
    return guarded_root


__all__ = ["freeze_rulespace_call_graph"]
