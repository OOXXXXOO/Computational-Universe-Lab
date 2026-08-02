"""Private-global cloning for authority call graphs.

Authority entry points retain their normal Python signatures, while every
reachable project function and referenced module attribute is copied into a
private globals mapping.  Later module rebinding therefore cannot alter an
already assembled issuer or consumer graph.
"""

from __future__ import annotations

import functools
import inspect
import sys
import types
from typing import Callable


def _freeze_project_class_methods(
    *project_classes: type,
) -> tuple[type, ...]:
    """Freeze canonical owner methods in place without changing class identity."""

    classes = tuple(project_classes)
    if not classes:
        raise ValueError("at least one project class is required")
    if any(type(project_class) is not type for project_class in classes):
        raise TypeError("owner method freezing requires exact type instances")
    owner_names = {project_class.__module__ for project_class in classes}
    if len(owner_names) != 1:
        raise TypeError("owner method freezing cannot cross module ownership")
    owner_name = next(iter(owner_names))
    frame = inspect.currentframe()
    caller = None if frame is None else frame.f_back
    caller_name = None if caller is None else caller.f_globals.get("__name__")
    del caller, frame
    if caller_name != owner_name:
        raise TypeError("owner method freezing must run inside the owning module")

    frozen_marker = "__rulespace_owner_method_frozen__"
    function_memo: dict[int, types.FunctionType] = {}
    container_memo: dict[int, tuple[object, object]] = {}

    def is_unfrozen_owner_function(value: object) -> bool:
        if type(value) is not types.FunctionType:
            return False
        function = value
        if function.__dict__.get(frozen_marker) is True:
            return False
        if not (
            function.__module__ == owner_name
            or function.__module__.startswith("rulespace_v3.")
        ):
            return False
        owner = sys.modules.get(function.__module__)
        return owner is None or function.__globals__ is vars(owner)

    def referenced_code_names(code: types.CodeType) -> tuple[str, ...]:
        names = list(code.co_names)
        for constant in code.co_consts:
            if type(constant) is types.CodeType:
                names.extend(referenced_code_names(constant))
        return tuple(dict.fromkeys(names))

    def make_cell(value: object) -> object:
        def read_cell() -> object:
            return value

        return read_cell.__closure__[0]

    def contains_owner_function(
        value: object,
        seen: set[int] | None = None,
    ) -> bool:
        if is_unfrozen_owner_function(value):
            return True
        if type(value) not in (tuple, list, dict):
            return False
        if seen is None:
            seen = set()
        identity = id(value)
        if identity in seen:
            return False
        seen.add(identity)
        items = value.values() if type(value) is dict else value
        return any(contains_owner_function(item, seen) for item in items)

    def cached_container(value: object) -> object | None:
        cached = container_memo.get(id(value))
        if cached is not None and cached[0] is value:
            return cached[1]
        return None

    def freeze_container(value: object) -> object:
        cached = cached_container(value)
        if cached is not None:
            return cached
        if type(value) is tuple:
            items = tuple(freeze_value(item) for item in value)
            cached = cached_container(value)
            if cached is not None:
                return cached
            container_memo[id(value)] = (value, items)
            return items
        if type(value) is list:
            if not contains_owner_function(value):
                return value
            result: list[object] = []
            container_memo[id(value)] = (value, result)
            result.extend(freeze_value(item) for item in value)
            return result
        if type(value) is dict:
            if not contains_owner_function(value):
                return value
            result: dict[object, object] = {}
            container_memo[id(value)] = (value, result)
            result.update((key, freeze_value(item)) for key, item in value.items())
            return result
        raise TypeError("owner call-graph container type is not supported")

    def freeze_value(value: object) -> object:
        if is_unfrozen_owner_function(value):
            return freeze_function(value)
        if type(value) in (tuple, list, dict):
            return freeze_container(value)
        # Classes, modules, authority registries and locks retain exact identity.
        return value

    def freeze_function(function: types.FunctionType) -> types.FunctionType:
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
            "__name__": source_globals.get("__name__", function.__module__),
            "__package__": source_globals.get("__package__", None),
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
        if source_closure is not None:
            assert private_cells is not None
            for private_cell, source_cell in zip(private_cells, source_closure):
                private_cell.cell_contents = freeze_value(source_cell.cell_contents)
        for name in referenced_code_names(function.__code__):
            if name in source_globals:
                private_globals[name] = freeze_value(source_globals[name])
        clone.__defaults__ = freeze_value(function.__defaults__)
        clone.__kwdefaults__ = freeze_value(function.__kwdefaults__)
        clone.__annotations__ = dict(function.__annotations__)
        clone.__dict__.update(function.__dict__)
        clone.__dict__[frozen_marker] = True
        clone.__doc__ = function.__doc__
        clone.__module__ = function.__module__
        clone.__qualname__ = function.__qualname__
        return clone

    def unknown_descriptor(descriptor: object) -> bool:
        descriptor_type = type(descriptor)
        if descriptor_type in (
            types.FunctionType,
            staticmethod,
            classmethod,
            property,
            types.MemberDescriptorType,
            types.GetSetDescriptorType,
        ):
            return False
        return inspect.getattr_static(descriptor_type, "__get__", None) is not None

    # Validate every raw descriptor before changing any class.  In particular,
    # never invoke an untrusted descriptor's ``__get__`` during discovery.
    for project_class in classes:
        for name, descriptor in tuple(vars(project_class).items()):
            if unknown_descriptor(descriptor):
                raise TypeError(
                    "unsupported descriptor in owner method freeze: "
                    f"{project_class.__qualname__}.{name}"
                )

    replacements: list[tuple[type, str, object]] = []

    def freeze_method(method: object) -> object:
        if type(method) is not types.FunctionType:
            raise TypeError("owner method descriptor does not hold a function")
        if method.__dict__.get(frozen_marker) is True:
            return method
        return freeze_function(method)

    for project_class in classes:
        for name, descriptor in tuple(vars(project_class).items()):
            replacement: object = descriptor
            if type(descriptor) is types.FunctionType:
                replacement = freeze_method(descriptor)
            elif type(descriptor) is staticmethod:
                method = freeze_method(descriptor.__func__)
                if method is not descriptor.__func__:
                    replacement = staticmethod(method)
            elif type(descriptor) is classmethod:
                method = freeze_method(descriptor.__func__)
                if method is not descriptor.__func__:
                    replacement = classmethod(method)
            elif type(descriptor) is property:
                accessors = tuple(
                    None if method is None else freeze_method(method)
                    for method in (descriptor.fget, descriptor.fset, descriptor.fdel)
                )
                if accessors != (
                    descriptor.fget,
                    descriptor.fset,
                    descriptor.fdel,
                ):
                    replacement = property(*accessors, doc=descriptor.__doc__)
            if replacement is not descriptor:
                replacements.append((project_class, name, replacement))

    for project_class, name, replacement in replacements:
        setattr(project_class, name, replacement)
    return classes


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
        if inspect.isfunction(value) and value.__module__.startswith("rulespace_v3."):
            return freeze_function(value)
        if inspect.isclass(value) and value.__module__.startswith("rulespace_v3."):
            return capture_project_class(value)
        if type(value) is _partial_type:
            keywords = value.keywords or {}
            return _partial_type(
                freeze_value(value.func),
                *(freeze_value(item) for item in value.args),
                **{key: freeze_value(item) for key, item in keywords.items()},
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
        if inspect.isfunction(value) and value.__module__.startswith("rulespace_v3."):
            return freeze_function(value)
        if inspect.isclass(value) and value.__module__.startswith("rulespace_v3."):
            return capture_project_class(value)
        if type(value) is _partial_type:
            return freeze_value(value)
        if inspect.ismodule(value):
            return freeze_value(value, referenced_names)
        if type(value) is tuple:
            return tuple(freeze_closure_value(item, referenced_names) for item in value)
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
                freeze_value(item, referenced_names) for item in function.__defaults__
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
    builtin_any = any
    builtin_vars = vars
    runtime_error = RuntimeError

    def guarded_root(*args, **kwargs):
        for project_class, expected_items, expected_names in snapshots:
            current = builtin_vars(project_class)
            # ``copyreg`` may add a benign ``__slotnames__`` cache after the
            # graph is frozen.  Preserve every captured dependency exactly,
            # while allowing only that cache attribute to appear later.
            if builtin_any(
                name not in expected_names and name != "__slotnames__"
                for name in current
            ) or builtin_any(
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
