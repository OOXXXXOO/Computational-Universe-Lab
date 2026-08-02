"""Adversarial tests for the shared v3 authority call-graph freezer."""

from __future__ import annotations

import subprocess
import sys
import unittest
from types import FunctionType
from unittest import mock


class FrozenCallGraphAuthorityTests(unittest.TestCase):
    def test_local_freezers_clone_cyclic_function_containers_without_recursion(
        self,
    ) -> None:
        import rulespace_v3.dynamics as dynamics
        import rulespace_v3.structure as structure

        def dependency_template():
            return 17

        def sequence_root_template(value):
            return value[1]()

        def mapping_root_template(value):
            return value["fn"]()

        freezer_cases = (
            (
                "dynamics",
                dynamics,
                lambda root: dynamics._freeze_dynamics_project_call_graphs(root)[0],
            ),
            (
                "structure",
                structure,
                structure._freeze_owner_call_graph,
            ),
        )
        for freezer_name, owner, freezer in freezer_cases:
            owner_globals = vars(owner)
            dependency = FunctionType(
                dependency_template.__code__,
                owner_globals,
                "cyclic_dependency",
            )
            containers: list[tuple[str, object, object]] = []

            list_cycle: list[object] = []
            list_cycle.extend((list_cycle, dependency))
            containers.append(
                (
                    "list",
                    list_cycle,
                    lambda frozen: frozen[0] is frozen,
                )
            )

            dict_cycle: dict[str, object] = {"fn": dependency}
            dict_cycle["self"] = dict_cycle
            containers.append(
                (
                    "dict",
                    dict_cycle,
                    lambda frozen: frozen["self"] is frozen,
                )
            )

            tuple_bridge: list[object] = []
            tuple_cycle = (tuple_bridge, dependency)
            tuple_bridge.append(tuple_cycle)
            containers.append(
                (
                    "tuple",
                    tuple_cycle,
                    lambda frozen: frozen[0][0] is frozen,
                )
            )

            for container_name, container, cycle_is_closed in containers:
                template = (
                    mapping_root_template
                    if container_name == "dict"
                    else sequence_root_template
                )
                root = FunctionType(
                    template.__code__,
                    owner_globals,
                    f"{container_name}_root",
                    (container,),
                )
                with self.subTest(
                    freezer=freezer_name,
                    container=container_name,
                ):
                    frozen_root = freezer(root)
                    frozen_container = frozen_root.__defaults__[0]
                    self.assertEqual(frozen_root(), 17)
                    self.assertTrue(cycle_is_closed(frozen_container))
                    self.assertIsNot(frozen_container, container)
                    frozen_dependency = (
                        frozen_container["fn"]
                        if container_name == "dict"
                        else frozen_container[1]
                    )
                    self.assertIsNot(frozen_dependency, dependency)

    def test_c19_snapshot_survives_later_dynamics_import_in_fresh_process(
        self,
    ) -> None:
        script = """
import threading
from types import FunctionType

from rulespace_v3.c19_refreeze import verify_c19_local_refreeze_preflight
import rulespace_v3.factory as factory
import rulespace_v3.trace as trace

rlock_type = type(threading.RLock())

def runtime_state(root):
    pending = [root]
    seen = set()
    dictionaries = set()
    locks = set()
    while pending:
        function = pending.pop()
        if type(function) is not FunctionType or id(function) in seen:
            continue
        seen.add(id(function))
        for cell in function.__closure__ or ():
            value = cell.cell_contents
            if type(value) is FunctionType:
                pending.append(value)
            elif type(value) is dict:
                dictionaries.add(id(value))
            elif type(value) is rlock_type:
                locks.add(id(value))
    return dictionaries, locks

before = runtime_state(factory._reverify_verified_factory)
owner_classes = (
    trace.ProvenanceNode,
    trace.CoefficientRecord,
    trace.PrimitiveSpec,
    trace.PrimitiveTrace,
    trace.ConstructionTrace,
    factory.BasisManifest,
    factory.FrozenComplexTensor,
    factory.PrimitiveInterface,
    factory.Primitive,
    factory.LinearRealspaceFactory,
    factory.PrimitiveOperatorWire,
    factory.CalibrationSeed,
    factory.CalibrationObservation,
    factory.FrozenSyntheticTarget,
    factory.VerifiedFactory,
    factory._VerifiedFactoryAuthority,
    factory._VerifiedFactoryView,
)

def owner_method_descriptors():
    return tuple(
        (owner, name, descriptor)
        for owner in owner_classes
        for name, descriptor in vars(owner).items()
        if type(descriptor) in (FunctionType, staticmethod, classmethod, property)
    )

before_methods = owner_method_descriptors()
import rulespace_v3.dynamics as dynamics
after = runtime_state(factory._reverify_verified_factory)
after_methods = owner_method_descriptors()
transition_register = runtime_state(dynamics._register_measured_transition)
transition_reverify = runtime_state(dynamics._reverify_verified_transition)
assert before == after
assert before[0] and before[1]
assert before_methods == after_methods
assert transition_register[0] & transition_reverify[0]
assert transition_register[1] & transition_reverify[1]
try:
    verify_c19_local_refreeze_preflight(None)
except TypeError:
    pass
else:
    raise AssertionError("c19 verifier accepted an invalid preflight")
"""
        completed = subprocess.run(
            (sys.executable, "-c", script),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )

    def test_dynamics_then_c19_keeps_invalid_preflight_error_in_fresh_process(
        self,
    ) -> None:
        script = """
import rulespace_v3.dynamics  # noqa: F401
from rulespace_v3.c19_refreeze import verify_c19_local_refreeze_preflight

try:
    verify_c19_local_refreeze_preflight(None)
except TypeError:
    pass
else:
    raise AssertionError("c19 verifier accepted an invalid preflight")
"""
        completed = subprocess.run(
            (sys.executable, "-c", script),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )

    def test_owner_method_freezer_is_private_idempotent_and_fail_closed(
        self,
    ) -> None:
        import rulespace_v3.frozen_call_graph as freezer_module

        owner_freezer = getattr(
            freezer_module,
            "_freeze_project_class_methods",
        )
        dependency_value = 7

        class CanonicalRecord:
            def value(self):
                return dependency_value

            @staticmethod
            def static_value():
                return dependency_value

            @classmethod
            def class_value(cls):
                return cls.__name__, dependency_value

            @property
            def property_value(self):
                return dependency_value

        class UnsupportedDescriptor:
            def __get__(self, instance, owner):
                del instance, owner
                descriptor_calls.append("__get__")
                return dependency_value

        class UnsupportedRecord:
            hook = UnsupportedDescriptor()

            def value(self):
                return dependency_value

        canonical_identity = CanonicalRecord
        descriptor_calls: list[str] = []
        returned = owner_freezer(CanonicalRecord)
        first_descriptors = {
            name: vars(CanonicalRecord)[name]
            for name in ("value", "static_value", "class_value", "property_value")
        }
        self.assertEqual(returned, (CanonicalRecord,))
        self.assertIs(CanonicalRecord, canonical_identity)
        self.assertNotIn("_freeze_project_class_methods", freezer_module.__all__)
        self.assertEqual(CanonicalRecord().value(), 7)
        self.assertEqual(CanonicalRecord.static_value(), 7)
        self.assertEqual(CanonicalRecord.class_value(), ("CanonicalRecord", 7))
        self.assertEqual(CanonicalRecord().property_value, 7)

        dependency_value = 11
        self.assertEqual(CanonicalRecord().value(), 7)
        self.assertEqual(CanonicalRecord.static_value(), 7)
        self.assertEqual(CanonicalRecord.class_value(), ("CanonicalRecord", 7))
        self.assertEqual(CanonicalRecord().property_value, 7)
        self.assertEqual(owner_freezer(CanonicalRecord), (CanonicalRecord,))
        self.assertEqual(
            {name: vars(CanonicalRecord)[name] for name in first_descriptors},
            first_descriptors,
        )

        original_method = vars(UnsupportedRecord)["value"]
        with self.assertRaisesRegex(TypeError, "unsupported descriptor"):
            owner_freezer(UnsupportedRecord)
        self.assertIs(vars(UnsupportedRecord)["value"], original_method)
        self.assertEqual(descriptor_calls, [])

    def test_public_protocol_authority_ignores_freezer_any_rebinding(self) -> None:
        # Assemble the complete public dependency graph before the attack.
        # This mirrors the repository import boundary under audit and avoids
        # making an unrelated lazy import inherit the temporary test binding.
        import rulespace_v3.application_authority_v2  # noqa: F401
        import rulespace_v3.application_materialization_v2  # noqa: F401
        import rulespace_v3.frozen_call_graph as freezer_module
        from rulespace_v3.scenario_response_protocol import (
            VerifiedApplicationScenarioResponseProtocolV2,
            issue_v3m0_scenario_response_protocol,
            verify_v3m0_scenario_response_protocol,
        )

        calls: list[str] = []

        def hostile_any(*args, **kwargs):
            del args, kwargs
            calls.append("any")
            raise AssertionError("shared-freezer module global reached")

        forged = object.__new__(VerifiedApplicationScenarioResponseProtocolV2)
        with mock.patch.object(
            freezer_module,
            "any",
            hostile_any,
            create=True,
        ):
            with self.assertRaisesRegex(
                TypeError,
                "formal_parent_v2 must be an exact live Parent-v2",
            ):
                issue_v3m0_scenario_response_protocol(
                    object(),
                    object(),
                    object(),
                )
            with self.assertRaisesRegex(
                ValueError,
                "scenario response protocol capability is not live",
            ):
                verify_v3m0_scenario_response_protocol(forged)

        self.assertEqual(calls, [])

    def test_public_replay_properties_ignore_module_builtin_rebinding(self) -> None:
        import rulespace_v3.current_window_replay as current_window_module
        import rulespace_v3.task8_control_replay as task8_module
        from rulespace_v3.current_window_replay import (
            VerifiedCurrentWindowCalibrationProtocolV2,
        )
        from rulespace_v3.task8_control_replay import (
            VerifiedCurrentControlRegistryV2,
        )

        cases = (
            (
                task8_module,
                VerifiedCurrentControlRegistryV2,
                "registry",
                "current control-registry identity is not live",
            ),
            (
                current_window_module,
                VerifiedCurrentWindowCalibrationProtocolV2,
                "protocol",
                "current window protocol identity is not live",
            ),
        )
        for module, capability_type, attribute, expected_error in cases:
            with self.subTest(capability=capability_type.__name__):
                calls: list[str] = []

                def hostile_len(*args, **kwargs):
                    del args, kwargs
                    calls.append("len")
                    return 0

                def hostile_runtime_error(*args, **kwargs):
                    del args, kwargs
                    calls.append("RuntimeError")
                    return AssertionError("property module global reached")

                forged = object.__new__(capability_type)
                with (
                    mock.patch.object(
                        module,
                        "len",
                        hostile_len,
                        create=True,
                    ),
                    mock.patch.object(
                        module,
                        "RuntimeError",
                        hostile_runtime_error,
                    ),
                ):
                    with self.assertRaisesRegex(ValueError, expected_error):
                        getattr(forged, attribute)

                self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
