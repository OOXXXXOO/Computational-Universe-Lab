from __future__ import annotations

import copy
import dataclasses
import gc
import hashlib
import inspect
import json
import unittest
import weakref
from collections.abc import Mapping
from typing import get_type_hints

import sympy as sp

from rulespace_v3.evidence import canonical_sha
from rulespace_v3.trace import (
    COEFFICIENT_AST_MAX_DEPTH,
    COEFFICIENT_AST_MAX_NODES,
    COEFFICIENT_EXPRESSION_SCHEMA,
    COEFFICIENT_INTEGER_MAX_DIGITS,
    COEFFICIENT_POW_MAX_MAGNITUDE,
    CONSTRUCTION_TRACE_SCHEMA,
    DAG_MAX_NODES,
    FROZEN_GRAMMAR_ID,
    SNAPSHOT_MAX_DEPTH,
    SNAPSHOT_MAX_NODES,
    CoefficientRecord,
    ConstructionTrace,
    MechanismKind,
    PrimitiveSpec,
    PrimitiveTrace,
    ProvenanceNode,
    ProvenanceOperation,
    build_construction_trace,
    construction_trace_payload,
    evaluate_closed_coefficient,
    verify_construction_trace,
    _snapshot_json,
)


SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


class ItemsOnlyMapping(Mapping):
    """Mapping whose only trustworthy interface is its first items snapshot."""

    def __init__(self, pairs):
        self._pairs = list(pairs)
        self.items_calls = 0
        self.getitem_calls = 0

    def __getitem__(self, key):
        self.getitem_calls += 1
        raise AssertionError("__getitem__ must not be consulted")

    def __iter__(self):
        raise AssertionError("a Mapping must not be traversed twice")

    def __len__(self):
        return len(self._pairs)

    def items(self):
        self.items_calls += 1
        if self.items_calls != 1:
            raise AssertionError("items() must be called exactly once")
        return iter(self._pairs)


class MutatingItemsMapping(ItemsOnlyMapping):
    def items(self):
        result = iter(list(super().items()))
        self._pairs[:] = [("corrupted_after_snapshot", object())]
        return result


def node(
    provenance_id: str,
    operation: ProvenanceOperation,
    *,
    depends_on=(),
    target_refs=(),
    objective_tags=(),
    search_run_id=None,
    source_sha: str = SHA_A,
) -> ProvenanceNode:
    return ProvenanceNode(
        provenance_id=provenance_id,
        operation=operation,
        depends_on=tuple(depends_on),
        target_refs=tuple(target_refs),
        objective_tags=tuple(objective_tags),
        search_run_id=search_run_id,
        source_sha=source_sha,
    )


def spec(
    mechanism_id: str,
    production_id: str,
    provenance_root: str,
    *,
    depends_on=(),
    expression=None,
    variable_order=("x", "y"),
    design_objective_tags=(),
    search_run_id=None,
    support_offsets=((0, 0), (1, 0)),
    state_channels=("p", "q"),
) -> PrimitiveSpec:
    x, y = sp.symbols("x y")
    if expression is None:
        expression = x + sp.I * y / 2
    return PrimitiveSpec(
        mechanism_id=mechanism_id,
        production_id=production_id,
        depends_on=tuple(depends_on),
        support_offsets=tuple(tuple(offset) for offset in support_offsets),
        state_channels=tuple(state_channels),
        coefficient_expression=expression,
        coefficient_variable_order=tuple(variable_order),
        symbolic_origin_tags=("local",),
        neutral_ablation="identity",
        design_objective_tags=tuple(design_objective_tags),
        search_run_id=search_run_id,
        source_sha=SHA_B,
        design_provenance=provenance_root,
    )


def base_nodes():
    return (
        node("constant", ProvenanceOperation.GRAMMAR_CONSTANT),
        node(
            "target",
            ProvenanceOperation.TARGET_SPEC_READ,
            target_refs=("target:C",),
        ),
        node(
            "derived_target",
            ProvenanceOperation.DERIVE,
            depends_on=("target",),
        ),
        node("opaque", ProvenanceOperation.OPAQUE_LITERAL),
    )


def build_base_trace() -> ConstructionTrace:
    return build_construction_trace(
        target_spec_id="spin2.linearized.v1",
        provenance_nodes=base_nodes(),
        primitive_specs=(
            spec(
                "blind",
                "local_canonical_shear",
                "constant",
            ),
            spec(
                "conditioned",
                "integer_translation",
                "derived_target",
                depends_on=("blind",),
            ),
            spec(
                "opaque",
                "universal_mass_term",
                "opaque",
                depends_on=("blind",),
            ),
        ),
    )


def resigned(payload):
    result = copy.deepcopy(payload)
    body = {key: value for key, value in result.items() if key != "trace_sha"}
    result["trace_sha"] = canonical_sha(body)
    return result


class ConstructionTraceSchemaTests(unittest.TestCase):
    def test_frozen_ids_enums_and_builder_input_have_no_kind_escape_hatch(self):
        self.assertEqual(FROZEN_GRAMMAR_ID, "v3m0.local-linear-primitive.v1")
        self.assertEqual(
            CONSTRUCTION_TRACE_SCHEMA,
            "v3m0.construction-trace.v1",
        )
        self.assertEqual(
            COEFFICIENT_EXPRESSION_SCHEMA,
            "v3m0.sympy-exact-ast.v1",
        )
        self.assertEqual(
            [kind.value for kind in MechanismKind],
            ["target_blind", "target_conditioned", "unclassified"],
        )
        self.assertEqual(
            [operation.value for operation in ProvenanceOperation],
            [
                "grammar_primitive",
                "grammar_constant",
                "target_spec_read",
                "target_equation_read",
                "target_projector_read",
                "target_aware_objective",
                "derive",
                "cache",
                "copy",
                "rename",
                "search",
                "selection",
                "manual_selection",
                "opaque_literal",
                "unclassified",
            ],
        )
        self.assertNotIn(
            "kind",
            {field.name for field in dataclasses.fields(PrimitiveSpec)},
        )
        self.assertNotIn(
            "kind",
            inspect.signature(build_construction_trace).parameters,
        )

    def test_python39_type_hints_resolve_and_public_dataclasses_are_frozen(self):
        for value in (
            ProvenanceNode,
            CoefficientRecord,
            PrimitiveSpec,
            PrimitiveTrace,
            ConstructionTrace,
            build_construction_trace,
            verify_construction_trace,
            construction_trace_payload,
            evaluate_closed_coefficient,
        ):
            get_type_hints(value)

        trace = build_base_trace()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            trace.trace_sha = SHA_C  # type: ignore[misc]
        with self.assertRaises(TypeError):
            trace.primitives[0].support_offsets[0][0] = 9  # type: ignore[index]

    def test_build_computes_kinds_from_registry_provenance_and_primitive_dag(self):
        trace = build_base_trace()
        self.assertEqual(
            tuple(primitive.kind for primitive in trace.primitives),
            (
                MechanismKind.TARGET_BLIND,
                MechanismKind.TARGET_CONDITIONED,
                MechanismKind.UNCLASSIFIED,
            ),
        )
        self.assertEqual(
            tuple(record.mechanism_id for record in trace.coefficient_records),
            ("blind", "conditioned", "opaque"),
        )
        self.assertEqual(
            {primitive.grammar_id for primitive in trace.primitives},
            {FROZEN_GRAMMAR_ID},
        )

    def test_registry_target_and_unknown_productions_are_not_blind(self):
        trace = build_construction_trace(
            target_spec_id="target",
            provenance_nodes=(node("constant", ProvenanceOperation.GRAMMAR_CONSTANT),),
            primitive_specs=(
                spec("target", "target_projector", "constant"),
                spec("unknown", "new_unfrozen_primitive", "constant"),
            ),
        )
        self.assertEqual(
            [primitive.kind for primitive in trace.primitives],
            [MechanismKind.TARGET_CONDITIONED, MechanismKind.UNCLASSIFIED],
        )

    def test_target_conditioned_taint_dominates_unclassified_in_both_dags(self):
        nodes = base_nodes() + (
            node(
                "opaque_from_target",
                ProvenanceOperation.OPAQUE_LITERAL,
                depends_on=("target",),
            ),
        )
        trace = build_construction_trace(
            target_spec_id="target",
            provenance_nodes=nodes,
            primitive_specs=(
                spec("opaque", "universal_mass_term", "opaque"),
                spec("target", "integer_translation", "opaque_from_target"),
                spec(
                    "joined",
                    "unknown",
                    "constant",
                    depends_on=("opaque", "target"),
                ),
            ),
        )
        self.assertEqual(trace.primitives[0].kind, MechanismKind.UNCLASSIFIED)
        self.assertEqual(
            trace.primitives[1].kind,
            MechanismKind.TARGET_CONDITIONED,
        )
        self.assertEqual(
            trace.primitives[2].kind,
            MechanismKind.TARGET_CONDITIONED,
        )

    def test_search_and_selection_require_traceable_search_objective_ancestry(self):
        nodes = (
            node(
                "objective",
                ProvenanceOperation.GRAMMAR_CONSTANT,
                objective_tags=("spectral_flatness",),
            ),
            node("plain_constant", ProvenanceOperation.GRAMMAR_CONSTANT),
            node(
                "blind_search",
                ProvenanceOperation.SEARCH,
                depends_on=("objective",),
                objective_tags=("spectral_flatness",),
                search_run_id="run-blind-1",
            ),
            node(
                "blind_select",
                ProvenanceOperation.SELECTION,
                depends_on=("blind_search",),
                search_run_id="run-blind-1",
            ),
            node(
                "orphan_search",
                ProvenanceOperation.SEARCH,
                depends_on=("plain_constant",),
                objective_tags=("self_reported_only",),
                search_run_id="run-orphan-1",
            ),
            node(
                "wrapped_orphan",
                ProvenanceOperation.RENAME,
                depends_on=("orphan_search",),
            ),
            node(
                "orphan_manual",
                ProvenanceOperation.MANUAL_SELECTION,
                depends_on=("plain_constant",),
            ),
            node(
                "target_objective",
                ProvenanceOperation.TARGET_AWARE_OBJECTIVE,
                depends_on=("plain_constant",),
                target_refs=("target:TT",),
                objective_tags=("match_tt",),
            ),
            node(
                "target_search",
                ProvenanceOperation.SEARCH,
                depends_on=("target_objective",),
                objective_tags=("match_tt",),
                search_run_id="run-target-1",
            ),
            node(
                "cached_target",
                ProvenanceOperation.CACHE,
                depends_on=("target_search",),
            ),
        )
        trace = build_construction_trace(
            target_spec_id="target",
            provenance_nodes=nodes,
            primitive_specs=(
                spec(
                    "blind_search",
                    "universal_dispersion_term",
                    "blind_select",
                    design_objective_tags=("spectral_flatness",),
                    search_run_id="run-blind-1",
                ),
                spec(
                    "orphan_search",
                    "integer_translation",
                    "wrapped_orphan",
                    design_objective_tags=("self_reported_only",),
                    search_run_id="run-orphan-1",
                ),
                spec("orphan_manual", "integer_translation", "orphan_manual"),
                spec(
                    "target_search",
                    "integer_translation",
                    "cached_target",
                    design_objective_tags=("match_tt",),
                    search_run_id="run-target-1",
                ),
            ),
        )
        self.assertEqual(
            [primitive.kind for primitive in trace.primitives],
            [
                MechanismKind.TARGET_BLIND,
                MechanismKind.UNCLASSIFIED,
                MechanismKind.UNCLASSIFIED,
                MechanismKind.TARGET_CONDITIONED,
            ],
        )

    def test_selection_cannot_invent_a_search_run_id(self):
        nodes = (
            node(
                "objective",
                ProvenanceOperation.GRAMMAR_CONSTANT,
                objective_tags=("generic_loss",),
            ),
            node(
                "search",
                ProvenanceOperation.SEARCH,
                depends_on=("objective",),
                objective_tags=("generic_loss",),
                search_run_id="actual-run",
            ),
            node(
                "selection",
                ProvenanceOperation.SELECTION,
                depends_on=("search",),
                search_run_id="invented-run",
            ),
        )
        trace = build_construction_trace(
            target_spec_id="target",
            provenance_nodes=nodes,
            primitive_specs=(
                spec(
                    "selected",
                    "integer_translation",
                    "selection",
                    design_objective_tags=("generic_loss",),
                    search_run_id="invented-run",
                ),
            ),
        )
        self.assertEqual(
            trace.primitives[0].kind,
            MechanismKind.UNCLASSIFIED,
        )

    def test_cache_copy_and_rename_inherit_without_lowering_taint(self):
        nodes = list(base_nodes())
        previous = "target"
        for operation in (
            ProvenanceOperation.CACHE,
            ProvenanceOperation.COPY,
            ProvenanceOperation.RENAME,
        ):
            current = operation.value
            nodes.append(node(current, operation, depends_on=(previous,)))
            previous = current
        trace = build_construction_trace(
            target_spec_id="target",
            provenance_nodes=tuple(nodes),
            primitive_specs=(spec("copied", "integer_translation", previous),),
        )
        self.assertEqual(
            trace.primitives[0].kind,
            MechanismKind.TARGET_CONDITIONED,
        )

    def test_set_like_fields_are_sorted_and_duplicates_rejected(self):
        trace = build_construction_trace(
            target_spec_id="target",
            provenance_nodes=(
                node(
                    "constant",
                    ProvenanceOperation.GRAMMAR_CONSTANT,
                    target_refs=("z", "a"),
                    objective_tags=("z", "a"),
                ),
            ),
            primitive_specs=(
                spec(
                    "primitive",
                    "integer_translation",
                    "constant",
                    support_offsets=((1, 0), (0, 0)),
                    state_channels=("q", "p"),
                ),
            ),
        )
        primitive = trace.primitives[0]
        self.assertEqual(primitive.support_offsets, ((0, 0), (1, 0)))
        self.assertEqual(primitive.state_channels, ("p", "q"))
        self.assertEqual(trace.provenance_nodes[0].target_refs, ("a", "z"))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_construction_trace(
                target_spec_id="target",
                provenance_nodes=(
                    node(
                        "constant",
                        ProvenanceOperation.GRAMMAR_CONSTANT,
                        objective_tags=("same", "same"),
                    ),
                ),
                primitive_specs=(
                    spec("primitive", "integer_translation", "constant"),
                ),
            )

    def test_primitive_order_is_preserved_and_changes_trace_sha(self):
        nodes = (node("constant", ProvenanceOperation.GRAMMAR_CONSTANT),)
        first = spec("first", "integer_translation", "constant")
        second = spec("second", "universal_mass_term", "constant")
        forward = build_construction_trace(
            target_spec_id="target",
            provenance_nodes=nodes,
            primitive_specs=(first, second),
        )
        reverse = build_construction_trace(
            target_spec_id="target",
            provenance_nodes=nodes,
            primitive_specs=(second, first),
        )
        self.assertEqual(
            [primitive.mechanism_id for primitive in forward.primitives],
            ["first", "second"],
        )
        self.assertNotEqual(forward.trace_sha, reverse.trace_sha)

    def test_ids_and_both_dags_must_be_unique_acyclic_and_closed(self):
        duplicate_nodes = (
            node("same", ProvenanceOperation.GRAMMAR_CONSTANT),
            node("same", ProvenanceOperation.GRAMMAR_CONSTANT),
        )
        with self.assertRaisesRegex(ValueError, "duplicate provenance"):
            build_construction_trace(
                target_spec_id="target",
                provenance_nodes=duplicate_nodes,
                primitive_specs=(spec("p", "integer_translation", "same"),),
            )

        for nodes, pattern in (
            (
                (
                    node(
                        "self",
                        ProvenanceOperation.DERIVE,
                        depends_on=("self",),
                    ),
                ),
                "cycle",
            ),
            (
                (
                    node(
                        "dangling",
                        ProvenanceOperation.DERIVE,
                        depends_on=("missing",),
                    ),
                ),
                "missing provenance",
            ),
        ):
            with self.assertRaisesRegex(ValueError, pattern):
                build_construction_trace(
                    target_spec_id="target",
                    provenance_nodes=nodes,
                    primitive_specs=(spec("p", "integer_translation", nodes[0].provenance_id),),
                )

        nodes = (node("constant", ProvenanceOperation.GRAMMAR_CONSTANT),)
        with self.assertRaisesRegex(ValueError, "duplicate mechanism"):
            build_construction_trace(
                target_spec_id="target",
                provenance_nodes=nodes,
                primitive_specs=(
                    spec("same", "integer_translation", "constant"),
                    spec("same", "integer_translation", "constant"),
                ),
            )
        with self.assertRaisesRegex(ValueError, "missing primitive"):
            build_construction_trace(
                target_spec_id="target",
                provenance_nodes=nodes,
                primitive_specs=(
                    spec(
                        "p",
                        "integer_translation",
                        "constant",
                        depends_on=("missing",),
                    ),
                ),
            )
        with self.assertRaisesRegex(ValueError, "cycle"):
            build_construction_trace(
                target_spec_id="target",
                provenance_nodes=nodes,
                primitive_specs=(
                    spec("p", "integer_translation", "constant", depends_on=("q",)),
                    spec("q", "integer_translation", "constant", depends_on=("p",)),
                ),
            )

    def test_long_dags_are_iterative_and_oversized_dags_raise_valueerror(self):
        long_count = 1_200
        provenance_nodes = []
        for index in range(long_count):
            provenance_nodes.append(
                node(
                    f"n{index:04d}",
                    (
                        ProvenanceOperation.GRAMMAR_CONSTANT
                        if index == 0
                        else ProvenanceOperation.DERIVE
                    ),
                    depends_on=(
                        () if index == 0 else (f"n{index - 1:04d}",)
                    ),
                )
            )
        trace = build_construction_trace(
            target_spec_id="target",
            provenance_nodes=tuple(provenance_nodes),
            primitive_specs=(
                spec(
                    "p",
                    "integer_translation",
                    f"n{long_count - 1:04d}",
                ),
            ),
        )
        self.assertEqual(verify_construction_trace(trace), trace)

        primitive_nodes = (
            node("constant", ProvenanceOperation.GRAMMAR_CONSTANT),
        )
        primitive_specs = []
        for index in range(long_count):
            primitive_specs.append(
                spec(
                    f"p{index:04d}",
                    "integer_translation",
                    "constant",
                    depends_on=(
                        () if index == 0 else (f"p{index - 1:04d}",)
                    ),
                    expression=sp.Integer(1),
                    variable_order=(),
                )
            )
        primitive_trace = build_construction_trace(
            target_spec_id="target",
            provenance_nodes=primitive_nodes,
            primitive_specs=tuple(primitive_specs),
        )
        self.assertEqual(verify_construction_trace(primitive_trace), primitive_trace)

        oversized = tuple(
            node(
                f"wide{index:05d}",
                ProvenanceOperation.GRAMMAR_CONSTANT,
            )
            for index in range(DAG_MAX_NODES + 1)
        )
        with self.assertRaisesRegex(ValueError, "DAG node"):
            build_construction_trace(
                target_spec_id="target",
                provenance_nodes=oversized,
                primitive_specs=(
                    spec("p", "integer_translation", "wide00000"),
                ),
            )

    def test_source_sha_offsets_and_identifiers_are_strict(self):
        with self.assertRaisesRegex(ValueError, "source_sha"):
            build_construction_trace(
                target_spec_id="target",
                provenance_nodes=(
                    node(
                        "constant",
                        ProvenanceOperation.GRAMMAR_CONSTANT,
                        source_sha="A" * 64,
                    ),
                ),
                primitive_specs=(spec("p", "integer_translation", "constant"),),
            )
        with self.assertRaisesRegex(TypeError, "bool"):
            build_construction_trace(
                target_spec_id="target",
                provenance_nodes=(
                    node("constant", ProvenanceOperation.GRAMMAR_CONSTANT),
                ),
                primitive_specs=(
                    spec(
                        "p",
                        "integer_translation",
                        "constant",
                        support_offsets=((True, 0),),
                    ),
                ),
            )


class ExactCoefficientTests(unittest.TestCase):
    def test_unevaluated_exact_nodes_are_canonicalized_before_digesting(self):
        x = sp.Symbol("x")
        expressions = (
            sp.Add(x, sp.Integer(0), evaluate=False),
            sp.Mul(x, sp.Integer(1), evaluate=False),
            sp.Pow(x, sp.Integer(1), evaluate=False),
        )
        for index, expression in enumerate(expressions):
            with self.subTest(expression=expression):
                trace = build_construction_trace(
                    target_spec_id="target",
                    provenance_nodes=base_nodes(),
                    primitive_specs=(
                        spec(
                            f"p{index}",
                            "local_canonical_shear",
                            "constant",
                            expression=expression,
                            variable_order=("x",),
                        ),
                    ),
                )
                self.assertEqual(verify_construction_trace(trace), trace)

    def test_closed_exact_coefficient_has_one_safe_runtime_lowering(self):
        trace = build_construction_trace(
            target_spec_id="target",
            provenance_nodes=base_nodes(),
            primitive_specs=(
                spec(
                    "p",
                    "local_canonical_shear",
                    "constant",
                    expression=sp.Rational(3, 2) + sp.I / 4,
                    variable_order=(),
                ),
            ),
        )
        value = evaluate_closed_coefficient(trace.coefficient_records[0])
        self.assertIs(type(value), complex)
        self.assertEqual(value, complex(1.5, 0.25))

    def test_closed_lowering_rejects_variables_tamper_and_nonfinite_values(self):
        x = sp.Symbol("x")
        variable_trace = build_construction_trace(
            target_spec_id="target",
            provenance_nodes=base_nodes(),
            primitive_specs=(
                spec(
                    "p",
                    "integer_translation",
                    "constant",
                    expression=x,
                    variable_order=("x",),
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "closed"):
            evaluate_closed_coefficient(variable_trace.coefficient_records[0])

        valid_record = build_construction_trace(
            target_spec_id="target",
            provenance_nodes=base_nodes(),
            primitive_specs=(
                spec(
                    "p",
                    "integer_translation",
                    "constant",
                    expression=sp.Integer(2),
                    variable_order=(),
                ),
            ),
        ).coefficient_records[0]
        tampered = dataclasses.replace(
            valid_record,
            expression_ast=("Integer", "9"),
        )
        with self.assertRaisesRegex(ValueError, "digest"):
            evaluate_closed_coefficient(tampered)

        nonfinite_ast = (
            "Pow",
            ("Integer", "0"),
            ("Integer", "-1"),
        )
        nonfinite_body = {
            "mechanism_id": "bad",
            "expression_schema": COEFFICIENT_EXPRESSION_SCHEMA,
            "variable_order": (),
            "expression_ast": nonfinite_ast,
            "provenance_root_id": "constant",
        }
        nonfinite = CoefficientRecord(
            mechanism_id="bad",
            expression_schema=COEFFICIENT_EXPRESSION_SCHEMA,
            variable_order=(),
            expression_ast=nonfinite_ast,
            provenance_root_id="constant",
            coefficient_digest=canonical_sha(nonfinite_body),
        )
        with self.assertRaisesRegex((TypeError, ValueError), "unsupported|finite"):
            evaluate_closed_coefficient(nonfinite)

    def test_symbols_must_be_standard_commutative_and_match_variable_order(self):
        standard = sp.Symbol("x")
        trace = build_construction_trace(
            target_spec_id="target",
            provenance_nodes=base_nodes(),
            primitive_specs=(
                spec(
                    "standard",
                    "integer_translation",
                    "constant",
                    expression=standard + 1,
                    variable_order=("x",),
                ),
            ),
        )
        self.assertEqual(verify_construction_trace(trace), trace)

        noncommutative = sp.Symbol("x", commutative=False)
        explicitly_assumed_commutative = sp.Symbol("x", commutative=True)
        assumed = sp.Symbol("x", real=True)
        ambiguous = sp.Add(standard, assumed, evaluate=False)
        cases = (
            (noncommutative, ("x",)),
            (explicitly_assumed_commutative, ("x",)),
            (assumed, ("x",)),
            (ambiguous, ("x",)),
            (standard, ("x", "unused")),
        )
        for expression, variable_order in cases:
            with self.subTest(expression=expression, variables=variable_order):
                with self.assertRaisesRegex(ValueError, "standard|variable_order"):
                    build_construction_trace(
                        target_spec_id="target",
                        provenance_nodes=base_nodes(),
                        primitive_specs=(
                            spec(
                                "invalid",
                                "integer_translation",
                                "constant",
                                expression=expression,
                                variable_order=variable_order,
                            ),
                        ),
                    )

    def test_exact_sympy_expression_builds_canonical_ast_and_digest(self):
        x, y = sp.symbols("x y")
        trace = build_construction_trace(
            target_spec_id="target",
            provenance_nodes=base_nodes(),
            primitive_specs=(
                spec(
                    "p",
                    "local_canonical_shear",
                    "constant",
                    expression=x ** sp.Rational(-1, 2) + sp.I * y / 3,
                ),
            ),
        )
        record = trace.coefficient_records[0]
        self.assertEqual(record.expression_schema, COEFFICIENT_EXPRESSION_SCHEMA)
        self.assertEqual(record.variable_order, ("x", "y"))
        self.assertEqual(record.expression_ast[0], "Add")
        self.assertRegex(record.coefficient_digest, r"\A[0-9a-f]{64}\Z")
        self.assertEqual(
            trace.primitives[0].coefficient_digest,
            record.coefficient_digest,
        )
        self.assertEqual(verify_construction_trace(trace), trace)

    def test_float_unknown_symbol_and_unknown_function_are_rejected(self):
        x, z = sp.symbols("x z")
        invalid = (
            (x + sp.Float("0.5"), ("x",), "Float"),
            (x + z, ("x",), "registered"),
            (sp.sin(x), ("x",), "unsupported"),
        )
        for expression, variables, pattern in invalid:
            with self.subTest(expression=expression):
                with self.assertRaisesRegex((TypeError, ValueError), pattern):
                    build_construction_trace(
                        target_spec_id="target",
                        provenance_nodes=(
                            node(
                                "constant",
                                ProvenanceOperation.GRAMMAR_CONSTANT,
                            ),
                        ),
                        primitive_specs=(
                            spec(
                                "p",
                                "integer_translation",
                                "constant",
                                expression=expression,
                                variable_order=variables,
                            ),
                        ),
                    )

    def test_tampering_ast_variable_order_root_or_digest_fails_after_resign(self):
        payload = construction_trace_payload(build_base_trace())
        mutations = []

        changed = copy.deepcopy(payload)
        changed["coefficient_records"][0]["expression_ast"] = ["Integer", "9"]
        mutations.append(changed)

        changed = copy.deepcopy(payload)
        changed["coefficient_records"][0]["variable_order"] = ["y", "x"]
        mutations.append(changed)

        changed = copy.deepcopy(payload)
        changed["coefficient_records"][0]["provenance_root_id"] = "opaque"
        mutations.append(changed)

        changed = copy.deepcopy(payload)
        changed["coefficient_records"][0]["coefficient_digest"] = SHA_C
        mutations.append(changed)

        for changed in mutations:
            with self.subTest(changed=changed["coefficient_records"][0]):
                with self.assertRaises((TypeError, ValueError)):
                    verify_construction_trace(resigned(changed))

    def test_validly_redigesting_a_noncanonical_ast_is_still_rejected(self):
        payload = construction_trace_payload(build_base_trace())
        record = payload["coefficient_records"][0]
        ast = record["expression_ast"]
        self.assertEqual(ast[0], "Add")
        record["expression_ast"] = ["Add", *reversed(ast[1:])]
        digest_body = {
            "mechanism_id": record["mechanism_id"],
            "expression_schema": record["expression_schema"],
            "variable_order": record["variable_order"],
            "expression_ast": record["expression_ast"],
            "provenance_root_id": record["provenance_root_id"],
        }
        record["coefficient_digest"] = canonical_sha(digest_body)
        with self.assertRaisesRegex(ValueError, "canonical"):
            verify_construction_trace(resigned(payload))


class TracePayloadSecurityTests(unittest.TestCase):
    def test_snapshot_memo_holds_original_object_and_confirms_identity(self):
        memo = {}
        source = ItemsOnlyMapping((("value", 1),))
        source_ref = weakref.ref(source)
        _snapshot_json(source, "$", set(), memo)
        del source
        gc.collect()
        self.assertIsNotNone(source_ref())

    def test_parent_items_and_sequence_are_materialized_before_children(self):
        class TailMutator(ItemsOnlyMapping):
            def __init__(self, pairs, mutation):
                super().__init__(pairs)
                self._mutation = mutation

            def items(self):
                result = super().items()
                self._mutation()
                return result

        parent_mapping = ItemsOnlyMapping(())
        child_mapping = TailMutator(
            (("child", "stable"),),
            lambda: parent_mapping._pairs.__setitem__(
                1,
                ("tail", "corrupted"),
            ),
        )
        parent_mapping._pairs[:] = [
            ("head", child_mapping),
            ("tail", "stable"),
        ]
        frozen_mapping = _snapshot_json(parent_mapping, "$", set())
        self.assertEqual(frozen_mapping["tail"], "stable")
        self.assertEqual(parent_mapping.items_calls, 1)
        self.assertEqual(child_mapping.items_calls, 1)

        parent_list = []
        child_list_mapping = TailMutator(
            (("child", "stable"),),
            lambda: parent_list.__setitem__(1, "corrupted"),
        )
        parent_list[:] = [child_list_mapping, "stable"]
        frozen_list = _snapshot_json(parent_list, "$", set())
        self.assertEqual(frozen_list[1], "stable")
        self.assertEqual(child_list_mapping.items_calls, 1)

    def test_one_global_snapshot_memoizes_stateful_mapping_aliases(self):
        payload = construction_trace_payload(build_base_trace())
        shared = ItemsOnlyMapping(payload["provenance_nodes"][0].items())
        payload["provenance_nodes"] = [shared, shared]
        with self.assertRaises(ValueError):
            verify_construction_trace(payload)
        self.assertEqual(shared.items_calls, 1)
        self.assertEqual(shared.getitem_calls, 0)

    def test_complete_body_is_hashed_and_fixed_utf8_golden_vector_holds(self):
        self.assertEqual(
            canonical_sha({"研究": "边界", "n": 3}),
            "045969cde539b379464ceae75b318b3e1160480edf28fda0a638882dddf99aea",
        )
        trace = build_base_trace()
        payload = construction_trace_payload(trace)
        body = {key: value for key, value in payload.items() if key != "trace_sha"}
        canonical_bytes = json.dumps(
            body,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        self.assertEqual(
            trace.trace_sha,
            hashlib.sha256(canonical_bytes).hexdigest(),
        )
        self.assertIn("provenance_nodes", body)
        self.assertIn("coefficient_records", body)
        self.assertIn("primitives", body)

    def test_roundtrip_payload_and_strict_schema(self):
        trace = build_base_trace()
        payload = construction_trace_payload(trace)
        self.assertEqual(verify_construction_trace(payload), trace)

        for path in ("top", "node", "record", "primitive"):
            changed = copy.deepcopy(payload)
            if path == "top":
                changed["unexpected"] = 1
            elif path == "node":
                changed["provenance_nodes"][0]["unexpected"] = 1
            elif path == "record":
                changed["coefficient_records"][0]["unexpected"] = 1
            else:
                changed["primitives"][0]["unexpected"] = 1
            with self.subTest(path=path):
                with self.assertRaisesRegex(ValueError, "unknown|schema"):
                    verify_construction_trace(resigned(changed))

    def test_computed_kind_tamper_fails_even_when_trace_sha_is_resigned(self):
        payload = construction_trace_payload(build_base_trace())
        payload["primitives"][0]["kind"] = "target_conditioned"
        with self.assertRaisesRegex(ValueError, "computed kind"):
            verify_construction_trace(resigned(payload))

    def test_items_snapshot_is_single_authority_and_getitem_is_never_used(self):
        payload = construction_trace_payload(build_base_trace())
        mapping = ItemsOnlyMapping(payload.items())
        verified = verify_construction_trace(mapping)
        self.assertEqual(verified, build_base_trace())
        self.assertEqual(mapping.items_calls, 1)
        self.assertEqual(mapping.getitem_calls, 0)

        mutating = MutatingItemsMapping(payload.items())
        verified = verify_construction_trace(mutating)
        self.assertEqual(verified, build_base_trace())
        self.assertEqual(mutating.items_calls, 1)
        self.assertEqual(mutating.getitem_calls, 0)

    def test_duplicate_mapping_items_non_string_keys_cycles_and_non_json_fail(self):
        payload = construction_trace_payload(build_base_trace())
        duplicate = ItemsOnlyMapping(
            list(payload.items()) + [("trace_sha", payload["trace_sha"])]
        )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            verify_construction_trace(duplicate)

        non_string = ItemsOnlyMapping([(1, "bad")])
        with self.assertRaisesRegex(TypeError, "str"):
            verify_construction_trace(non_string)

        cyclic = {}
        cyclic["self"] = cyclic
        with self.assertRaisesRegex(ValueError, "cyclic"):
            verify_construction_trace(cyclic)

        invalid = copy.deepcopy(payload)
        invalid["primitives"][0]["state_channels"] = [object()]
        with self.assertRaisesRegex(TypeError, "non-JSON"):
            verify_construction_trace(invalid)

    def test_empty_serialized_trace_is_rejected_like_empty_builder_inputs(self):
        body = {
            "schema_version": CONSTRUCTION_TRACE_SCHEMA,
            "grammar_id": FROZEN_GRAMMAR_ID,
            "target_spec_id": "target",
            "provenance_nodes": [],
            "coefficient_records": [],
            "primitives": [],
        }
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            verify_construction_trace(
                {**body, "trace_sha": canonical_sha(body)}
            )

    def test_snapshot_resource_limits_raise_valueerror_before_recursion(self):
        payload = construction_trace_payload(build_base_trace())
        too_deep = "leaf"
        for _ in range(SNAPSHOT_MAX_DEPTH + 2):
            too_deep = [too_deep]
        payload["too_deep"] = too_deep
        with self.assertRaisesRegex(ValueError, "snapshot depth"):
            verify_construction_trace(payload)

        payload = construction_trace_payload(build_base_trace())
        payload["too_many"] = list(range(SNAPSHOT_MAX_NODES + 1))
        with self.assertRaisesRegex(ValueError, "snapshot node"):
            verify_construction_trace(payload)

    def test_coefficient_resource_limits_reject_deep_large_and_giant_pow(self):
        x = sp.Symbol("x")

        deep = x
        for _ in range(COEFFICIENT_AST_MAX_DEPTH + 2):
            deep = sp.Pow(deep, sp.Integer(1), evaluate=False)
        with self.assertRaisesRegex(ValueError, "AST depth"):
            build_construction_trace(
                target_spec_id="target",
                provenance_nodes=base_nodes(),
                primitive_specs=(
                    spec(
                        "deep",
                        "integer_translation",
                        "constant",
                        expression=deep,
                        variable_order=("x",),
                    ),
                ),
            )

        wide = sp.Add(
            *(x for _ in range(COEFFICIENT_AST_MAX_NODES + 1)),
            evaluate=False,
        )
        with self.assertRaisesRegex(ValueError, "AST node"):
            build_construction_trace(
                target_spec_id="target",
                provenance_nodes=base_nodes(),
                primitive_specs=(
                    spec(
                        "wide",
                        "integer_translation",
                        "constant",
                        expression=wide,
                        variable_order=("x",),
                    ),
                ),
            )

        huge_integer = sp.Integer("9" * (COEFFICIENT_INTEGER_MAX_DIGITS + 1))
        with self.assertRaisesRegex(ValueError, "integer digit"):
            build_construction_trace(
                target_spec_id="target",
                provenance_nodes=base_nodes(),
                primitive_specs=(
                    spec(
                        "integer",
                        "integer_translation",
                        "constant",
                        expression=huge_integer,
                        variable_order=(),
                    ),
                ),
            )

        giant_pow = sp.Pow(
            x,
            sp.Integer(COEFFICIENT_POW_MAX_MAGNITUDE + 1),
            evaluate=False,
        )
        with self.assertRaisesRegex(ValueError, "Pow exponent"):
            build_construction_trace(
                target_spec_id="target",
                provenance_nodes=base_nodes(),
                primitive_specs=(
                    spec(
                        "pow",
                        "integer_translation",
                        "constant",
                        expression=giant_pow,
                        variable_order=("x",),
                    ),
                ),
            )

        eager_pow = sp.Pow(
            sp.Integer("9" * COEFFICIENT_INTEGER_MAX_DIGITS),
            sp.Integer(COEFFICIENT_POW_MAX_MAGNITUDE),
            evaluate=False,
        )
        with self.assertRaisesRegex(ValueError, "Pow eager"):
            build_construction_trace(
                target_spec_id="target",
                provenance_nodes=base_nodes(),
                primitive_specs=(
                    spec(
                        "eager_pow",
                        "integer_translation",
                        "constant",
                        expression=eager_pow,
                        variable_order=(),
                    ),
                ),
            )

    def test_builder_applies_the_complete_verifier_resource_gate(self):
        x = sp.Symbol("x")
        near_limit = x
        for _ in range(31):
            near_limit = sp.Pow(
                near_limit + 1,
                sp.Rational(1, 2),
                evaluate=False,
            )
        trace = build_construction_trace(
            target_spec_id="target",
            provenance_nodes=base_nodes(),
            primitive_specs=(
                spec(
                    "deep_payload",
                    "integer_translation",
                    "constant",
                    expression=near_limit,
                    variable_order=("x",),
                ),
            ),
        )
        self.assertEqual(verify_construction_trace(trace), trace)

        too_wide = tuple(
            node(
                f"wide{index:05d}",
                ProvenanceOperation.GRAMMAR_CONSTANT,
            )
            for index in range(7_000)
        )
        with self.assertRaises(ValueError):
            build_construction_trace(
                target_spec_id="target",
                provenance_nodes=too_wide,
                primitive_specs=(
                    spec("p", "integer_translation", "wide00000"),
                ),
            )

    def test_payload_validation_has_no_io_subprocess_factory_or_legacy_imports(self):
        import ast
        from pathlib import Path

        source_path = (
            Path(__file__).resolve().parents[1] / "rulespace_v3" / "trace.py"
        )
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imports = []
        calls = []
        for item in ast.walk(tree):
            if isinstance(item, ast.Import):
                imports.extend(alias.name for alias in item.names)
            elif isinstance(item, ast.ImportFrom):
                imports.append(item.module or "")
            elif isinstance(item, ast.Call):
                if isinstance(item.func, ast.Name):
                    calls.append(item.func.id)
                elif isinstance(item.func, ast.Attribute):
                    calls.append(item.func.attr)
        forbidden_import_prefixes = (
            "rulespace_v2",
            "rulespace_gpu",
            "experiments",
            "subprocess",
        )
        self.assertFalse(
            any(name.startswith(forbidden_import_prefixes) for name in imports)
        )
        self.assertTrue(
            {"open", "write_text", "write_bytes", "run", "Popen", "factory"}.isdisjoint(
                calls
            )
        )


if __name__ == "__main__":
    unittest.main()
