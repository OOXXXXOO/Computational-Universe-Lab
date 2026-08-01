"""Focused exact-tree identity traversal regression tests."""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from unittest import mock


class ExactDataclassTreeTests(unittest.TestCase):
    def test_rejects_a_real_dataclass_cycle(self) -> None:
        from rulespace_v3.response import _exact_dataclass_tree

        @dataclass
        class Node:
            child: object | None = None

        node = Node()
        node.child = node
        with self.assertRaisesRegex(ValueError, "cyclic dataclass"):
            _exact_dataclass_tree(node, "node")

    def test_rejects_direct_sequence_and_mapping_cycles(self) -> None:
        from rulespace_v3.response import _exact_dataclass_tree

        sequence: list[object] = []
        sequence.append(sequence)
        with self.assertRaisesRegex(ValueError, "cyclic container"):
            _exact_dataclass_tree(sequence, "sequence")

        mapping: dict[str, object] = {}
        mapping["self"] = mapping
        with self.assertRaisesRegex(ValueError, "cyclic container"):
            _exact_dataclass_tree(mapping, "mapping")

    def test_preserves_non_string_mapping_key_rejection(self) -> None:
        from rulespace_v3.response import _exact_dataclass_tree

        with self.assertRaisesRegex(TypeError, "keys must be strings"):
            _exact_dataclass_tree({1: "value"}, "mapping")

    def test_black_alias_rejects_an_injected_field_after_first_validation(
        self,
    ) -> None:
        from rulespace_v3.response import _exact_dataclass_tree

        @dataclass(frozen=True)
        class Shared:
            value: int

        @dataclass
        class Trigger:
            value: int

        shared = Shared(1)

        class InjectUnknownField:
            def __get__(self, instance: object, owner: type) -> int:
                object.__setattr__(shared, "caller_extra", 2)
                return vars(instance)["value"]

            def __set__(self, instance: object, value: int) -> None:
                vars(instance)["value"] = value

        Trigger.value = InjectUnknownField()
        trigger = Trigger(1)

        with self.assertRaisesRegex(ValueError, "unknown fields"):
            _exact_dataclass_tree([shared, trigger, shared], "graph")

    def test_black_alias_rejects_same_identity_field_replacement(self) -> None:
        from rulespace_v3.response import _exact_dataclass_tree

        @dataclass(frozen=True)
        class Shared:
            value: object

        @dataclass
        class Trigger:
            value: int

        shared = Shared(object())
        replacement = object()

        class ReplaceField:
            def __get__(self, instance: object, owner: type) -> int:
                object.__setattr__(shared, "value", replacement)
                return vars(instance)["value"]

            def __set__(self, instance: object, value: int) -> None:
                vars(instance)["value"] = value

        Trigger.value = ReplaceField()
        trigger = Trigger(1)

        with self.assertRaisesRegex(ValueError, "changed after validation"):
            _exact_dataclass_tree([shared, trigger, shared], "graph")

    def test_postflight_rejects_resigned_descendant_behind_parent_alias(
        self,
    ) -> None:
        from rulespace_v3.response import _exact_dataclass_tree

        @dataclass(frozen=True)
        class Leaf:
            value: int
            body_sha: str

        @dataclass(frozen=True)
        class Parent:
            leaf: Leaf

        @dataclass
        class Trigger:
            value: int

        leaf = Leaf(1, "a" * 64)
        parent = Parent(leaf)

        class ResignLeaf:
            def __get__(self, instance: object, owner: type) -> int:
                object.__setattr__(leaf, "value", 2)
                object.__setattr__(leaf, "body_sha", "b" * 64)
                return vars(instance)["value"]

            def __set__(self, instance: object, value: int) -> None:
                vars(instance)["value"] = value

        Trigger.value = ResignLeaf()
        trigger = Trigger(1)

        with self.assertRaisesRegex(ValueError, "changed after validation"):
            _exact_dataclass_tree([parent, trigger, parent], "graph")

    def test_traverses_plain_dataclass_raw_storage_not_descriptor_view(
        self,
    ) -> None:
        from rulespace_v3.response import _exact_dataclass_tree

        @dataclass
        class MaskedBody:
            value: object

        masked = MaskedBody({1: "non-string-key"})
        descriptor_reads = 0

        class BenignView:
            def __get__(self, instance: object, owner: type) -> tuple[object, ...]:
                nonlocal descriptor_reads
                descriptor_reads += 1
                return ()

            def __set__(self, instance: object, value: object) -> None:
                vars(instance)["value"] = value

        MaskedBody.value = BenignView()

        with self.assertRaisesRegex(TypeError, "keys must be strings"):
            _exact_dataclass_tree(masked, "masked")
        self.assertEqual(descriptor_reads, 0)

    def test_replaced_slot_descriptor_cannot_mutate_prior_postflight_nodes(
        self,
    ) -> None:
        from rulespace_v3.response import _exact_dataclass_tree

        @dataclass(frozen=True)
        class Victim:
            value: int

        @dataclass
        class SlottedTrigger:
            __slots__ = ("value",)

            value: int

        victim = Victim(1)
        mapping: dict[object, object] = {"safe": "value"}
        trigger = SlottedTrigger(1)
        original_descriptor = vars(SlottedTrigger)["value"]
        descriptor_reads = 0

        class FourthReadMutator:
            def __get__(self, instance: object, owner: type) -> int:
                nonlocal descriptor_reads
                descriptor_reads += 1
                if descriptor_reads == 4:
                    object.__setattr__(victim, "caller_extra", 2)
                    mapping[1] = "non-string-key"
                return original_descriptor.__get__(instance, owner)

            def __set__(self, instance: object, value: int) -> None:
                original_descriptor.__set__(instance, value)

        SlottedTrigger.value = FourthReadMutator()

        with self.assertRaises((TypeError, ValueError)):
            _exact_dataclass_tree([victim, mapping, trigger], "graph")
        self.assertEqual(descriptor_reads, 0)

    def test_module_field_reader_rebind_cannot_hide_a_raw_dataclass(self) -> None:
        from rulespace_v3 import response

        @dataclass
        class Holder:
            value: object

        holder = Holder({1: "non-string-key"})
        with mock.patch.object(
            response,
            "_raw_dataclass_fields",
            return_value=None,
        ):
            with self.assertRaisesRegex(TypeError, "keys must be strings"):
                response._exact_dataclass_tree(holder, "holder")

    def test_module_storage_reader_rebind_cannot_substitute_benign_body(
        self,
    ) -> None:
        from rulespace_v3 import response

        @dataclass
        class Holder:
            value: object

        holder = Holder({1: "non-string-key"})

        def benign_reader(
            value: object,
            field: str,
            fields: dict[str, object],
        ) -> tuple[tuple[str, object], ...]:
            return (("value", ()),)

        with (
            mock.patch.object(
                response,
                "_exact_dataclass_items",
                side_effect=benign_reader,
            ),
            mock.patch.object(
                response,
                "_exact_dataclass_storage_items",
                side_effect=benign_reader,
            ),
        ):
            with self.assertRaisesRegex(TypeError, "keys must be strings"):
                response._exact_dataclass_tree(holder, "holder")

    def test_module_types_rebind_cannot_authorize_a_fake_slot_descriptor(
        self,
    ) -> None:
        import types as stdlib_types

        from rulespace_v3 import response

        @dataclass
        class Holder:
            __slots__ = ("value",)

            value: object

        holder = Holder({1: "non-string-key"})
        original_descriptor = vars(Holder)["value"]

        class View:
            def __get__(self, instance: object, owner: type) -> tuple[object, ...]:
                return ()

            def __set__(self, instance: object, value: object) -> None:
                original_descriptor.__set__(instance, value)

        Holder.value = View()
        fake_types = stdlib_types.SimpleNamespace(
            MemberDescriptorType=View,
            GetSetDescriptorType=stdlib_types.GetSetDescriptorType,
        )
        with mock.patch.object(response, "types", fake_types):
            with self.assertRaisesRegex(ValueError, "slot descriptor was replaced"):
                response._exact_dataclass_tree(holder, "holder")

    def test_plain_dataclass_accepts_a_function_stored_as_field_data(self) -> None:
        from rulespace_v3.response import _exact_dataclass_tree

        def callback() -> None:
            return None

        @dataclass
        class Holder:
            value: object = callback

        _exact_dataclass_tree(Holder(), "holder")

    def test_shared_alias_preserves_the_logical_node_charge(self) -> None:
        from rulespace_v3.response import _exact_dataclass_tree

        shared: object = 0
        for _ in range(24):
            shared = (shared, shared)
        with self.assertRaisesRegex(ValueError, "node cap"):
            _exact_dataclass_tree(shared, "graph")

    def test_shared_dag_has_two_unique_dataclass_bodies(self) -> None:
        from rulespace_v3.response import _exact_dataclass_tree

        @dataclass(frozen=True)
        class Leaf:
            value: int

        @dataclass(frozen=True)
        class Root:
            leaves: tuple[Leaf, ...]

        shared = Leaf(7)
        root = Root((shared,) * 4096)
        legacy_full_body_reads = 1 + len(root.leaves)
        unique_dataclass_bodies = len({id(root), id(shared)})

        self.assertEqual(legacy_full_body_reads, 4097)
        self.assertEqual(unique_dataclass_bodies, 2)
        _exact_dataclass_tree(root, "root")


if __name__ == "__main__":
    unittest.main()
