"""Mechanical V3-M0 construction traces with pre-lowering provenance taint.

This module is deliberately pure: it classifies already supplied typed records,
builds restricted exact coefficient sidecars, and validates serialized traces.
It does not inspect factories or historical implementations.
"""

from __future__ import annotations

import math
import re
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from itertools import islice
from types import MappingProxyType
from typing import Any, Optional, Union

import sympy as sp

from .evidence import canonical_sha
from .frozen_call_graph import _freeze_project_class_methods


FROZEN_GRAMMAR_ID = "v3m0.local-linear-primitive.v1"
CONSTRUCTION_TRACE_SCHEMA = "v3m0.construction-trace.v1"
COEFFICIENT_EXPRESSION_SCHEMA = "v3m0.sympy-exact-ast.v1"
SNAPSHOT_MAX_DEPTH = 128
SNAPSHOT_MAX_NODES = 100_000
DAG_MAX_NODES = 4_096
DAG_MAX_EDGES = 16_384
DAG_MAX_DEPTH = 4_096
COEFFICIENT_AST_MAX_DEPTH = 64
COEFFICIENT_AST_MAX_NODES = 4_096
COEFFICIENT_INTEGER_MAX_DIGITS = 256
COEFFICIENT_POW_MAX_MAGNITUDE = 256

_BLIND_PRODUCTIONS = frozenset(
    (
        "integer_translation",
        "lattice_symmetry_mix",
        "local_canonical_shear",
        "frozen_matter_walk",
        "universal_mass_term",
        "universal_dispersion_term",
    )
)
_TARGET_PRODUCTIONS = frozenset(
    (
        "target_operator",
        "target_projector",
        "target_basis",
        "placed_target_coefficient",
        "target_repair_operator",
    )
)
_TARGET_OPERATIONS = frozenset(
    (
        "target_spec_read",
        "target_equation_read",
        "target_projector_read",
        "target_aware_objective",
    )
)
_INHERITING_OPERATIONS = frozenset(("derive", "cache", "copy", "rename"))
_SEARCH_OPERATIONS = frozenset(("search", "selection", "manual_selection"))
_TARGET_SYMBOLIC_TAGS = frozenset(
    (
        "c",
        "kerc",
        "inc",
        "tt_basis",
        "tt_projector",
        "r30_placed_yee",
        "target_n_prop_repair",
    )
)
_LOWER_HEX_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_DECIMAL_INTEGER = re.compile(r"-?(?:0|[1-9][0-9]*)\Z")


class MechanismKind(str, Enum):
    TARGET_BLIND = "target_blind"
    TARGET_CONDITIONED = "target_conditioned"
    UNCLASSIFIED = "unclassified"


class ProvenanceOperation(str, Enum):
    GRAMMAR_PRIMITIVE = "grammar_primitive"
    GRAMMAR_CONSTANT = "grammar_constant"
    TARGET_SPEC_READ = "target_spec_read"
    TARGET_EQUATION_READ = "target_equation_read"
    TARGET_PROJECTOR_READ = "target_projector_read"
    TARGET_AWARE_OBJECTIVE = "target_aware_objective"
    DERIVE = "derive"
    CACHE = "cache"
    COPY = "copy"
    RENAME = "rename"
    SEARCH = "search"
    SELECTION = "selection"
    MANUAL_SELECTION = "manual_selection"
    OPAQUE_LITERAL = "opaque_literal"
    UNCLASSIFIED = "unclassified"


def _require_nonempty_string(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be a string")
    if not value.strip():
        raise ValueError(f"{field} must be non-empty")
    return value


def _require_optional_string(value: object, field: str) -> Optional[str]:
    if value is None:
        return None
    return _require_nonempty_string(value, field)


def _require_sha(value: object, field: str) -> str:
    value = _require_nonempty_string(value, field)
    if _LOWER_HEX_SHA256.fullmatch(value) is None:
        raise ValueError(f"{field} must be a 64-digit lowercase hexadecimal SHA")
    return value


def _require_tuple(value: object, field: str) -> tuple[Any, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be a tuple")
    return value


def _string_tuple(
    value: object,
    field: str,
    *,
    canonicalize: bool,
) -> tuple[str, ...]:
    values = _require_tuple(value, field)
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(values):
        text = _require_nonempty_string(item, f"{field}[{index}]")
        if text in seen:
            raise ValueError(f"{field} contains duplicate value {text!r}")
        seen.add(text)
        result.append(text)
    if canonicalize:
        result.sort()
    return tuple(result)


def _support_tuple(
    value: object,
    field: str,
    *,
    canonicalize: bool,
) -> tuple[tuple[int, ...], ...]:
    offsets = _require_tuple(value, field)
    if not offsets:
        raise ValueError(f"{field} must not be empty")
    dimension: Optional[int] = None
    result: list[tuple[int, ...]] = []
    seen: set[tuple[int, ...]] = set()
    for row_index, offset in enumerate(offsets):
        raw_offset = _require_tuple(offset, f"{field}[{row_index}]")
        if not raw_offset:
            raise ValueError(f"{field}[{row_index}] must not be empty")
        if dimension is None:
            dimension = len(raw_offset)
        elif len(raw_offset) != dimension:
            raise ValueError(f"{field} offsets must have one common dimension")
        normalized: list[int] = []
        for column_index, coordinate in enumerate(raw_offset):
            if type(coordinate) is bool:
                raise TypeError(
                    f"{field}[{row_index}][{column_index}] rejects bool offsets"
                )
            if type(coordinate) is not int:
                raise TypeError(f"{field}[{row_index}][{column_index}] must be an int")
            normalized.append(coordinate)
        normalized_offset = tuple(normalized)
        if normalized_offset in seen:
            raise ValueError(f"{field} contains duplicate offset {normalized_offset!r}")
        seen.add(normalized_offset)
        result.append(normalized_offset)
    if canonicalize:
        result.sort()
    return tuple(result)


def _validate_immutable_ast_shape(value: object) -> None:
    if type(value) is not tuple:
        raise TypeError("expression_ast must be a recursively immutable tuple")
    stack: list[tuple[tuple[object, ...], int]] = [(value, 0)]
    nodes = 0
    while stack:
        current, depth = stack.pop()
        if depth > COEFFICIENT_AST_MAX_DEPTH:
            raise ValueError("coefficient AST depth limit exceeded")
        nodes += 1
        if nodes > COEFFICIENT_AST_MAX_NODES:
            raise ValueError("coefficient AST node limit exceeded")
        for item in current:
            if type(item) is tuple:
                stack.append((item, depth + 1))
            elif type(item) not in (str, int):
                raise TypeError(
                    "expression_ast must contain only immutable exact AST values"
                )


@dataclass(frozen=True)
class ProvenanceNode:
    provenance_id: str
    operation: ProvenanceOperation
    depends_on: tuple[str, ...]
    target_refs: tuple[str, ...]
    objective_tags: tuple[str, ...]
    search_run_id: Optional[str]
    source_sha: str

    def __post_init__(self) -> None:
        _require_nonempty_string(self.provenance_id, "provenance_id")
        if not isinstance(self.operation, ProvenanceOperation):
            raise TypeError("operation must be a ProvenanceOperation")
        _string_tuple(self.depends_on, "depends_on", canonicalize=False)
        _string_tuple(self.target_refs, "target_refs", canonicalize=False)
        _string_tuple(self.objective_tags, "objective_tags", canonicalize=False)
        _require_optional_string(self.search_run_id, "search_run_id")
        _require_sha(self.source_sha, "source_sha")


@dataclass(frozen=True)
class CoefficientRecord:
    mechanism_id: str
    expression_schema: str
    variable_order: tuple[str, ...]
    expression_ast: tuple[object, ...]
    provenance_root_id: str
    coefficient_digest: str

    def __post_init__(self) -> None:
        _require_nonempty_string(self.mechanism_id, "mechanism_id")
        _require_nonempty_string(self.expression_schema, "expression_schema")
        _string_tuple(self.variable_order, "variable_order", canonicalize=False)
        _validate_immutable_ast_shape(self.expression_ast)
        _require_nonempty_string(self.provenance_root_id, "provenance_root_id")
        _require_sha(self.coefficient_digest, "coefficient_digest")


@dataclass(frozen=True)
class PrimitiveSpec:
    """Builder input; intentionally has no caller-controlled ``kind`` field."""

    mechanism_id: str
    production_id: str
    depends_on: tuple[str, ...]
    support_offsets: tuple[tuple[int, ...], ...]
    state_channels: tuple[str, ...]
    coefficient_expression: object
    coefficient_variable_order: tuple[str, ...]
    symbolic_origin_tags: tuple[str, ...]
    neutral_ablation: Optional[str]
    design_objective_tags: tuple[str, ...]
    search_run_id: Optional[str]
    source_sha: str
    design_provenance: str

    def __post_init__(self) -> None:
        _require_nonempty_string(self.mechanism_id, "mechanism_id")
        _require_nonempty_string(self.production_id, "production_id")
        _string_tuple(self.depends_on, "depends_on", canonicalize=False)
        _support_tuple(self.support_offsets, "support_offsets", canonicalize=False)
        _string_tuple(self.state_channels, "state_channels", canonicalize=False)
        _string_tuple(
            self.coefficient_variable_order,
            "coefficient_variable_order",
            canonicalize=False,
        )
        _string_tuple(
            self.symbolic_origin_tags,
            "symbolic_origin_tags",
            canonicalize=False,
        )
        _require_optional_string(self.neutral_ablation, "neutral_ablation")
        _string_tuple(
            self.design_objective_tags,
            "design_objective_tags",
            canonicalize=False,
        )
        _require_optional_string(self.search_run_id, "search_run_id")
        _require_sha(self.source_sha, "source_sha")
        _require_nonempty_string(self.design_provenance, "design_provenance")


@dataclass(frozen=True)
class PrimitiveTrace:
    grammar_id: str
    target_spec_id: str
    mechanism_id: str
    production_id: str
    kind: MechanismKind
    depends_on: tuple[str, ...]
    support_offsets: tuple[tuple[int, ...], ...]
    state_channels: tuple[str, ...]
    coefficient_digest: str
    symbolic_origin_tags: tuple[str, ...]
    neutral_ablation: Optional[str]
    design_objective_tags: tuple[str, ...]
    search_run_id: Optional[str]
    source_sha: str
    design_provenance: str

    def __post_init__(self) -> None:
        _require_nonempty_string(self.grammar_id, "grammar_id")
        _require_nonempty_string(self.target_spec_id, "target_spec_id")
        _require_nonempty_string(self.mechanism_id, "mechanism_id")
        _require_nonempty_string(self.production_id, "production_id")
        if not isinstance(self.kind, MechanismKind):
            raise TypeError("kind must be a MechanismKind")
        _string_tuple(self.depends_on, "depends_on", canonicalize=False)
        _support_tuple(self.support_offsets, "support_offsets", canonicalize=False)
        _string_tuple(self.state_channels, "state_channels", canonicalize=False)
        _require_sha(self.coefficient_digest, "coefficient_digest")
        _string_tuple(
            self.symbolic_origin_tags,
            "symbolic_origin_tags",
            canonicalize=False,
        )
        _require_optional_string(self.neutral_ablation, "neutral_ablation")
        _string_tuple(
            self.design_objective_tags,
            "design_objective_tags",
            canonicalize=False,
        )
        _require_optional_string(self.search_run_id, "search_run_id")
        _require_sha(self.source_sha, "source_sha")
        _require_nonempty_string(self.design_provenance, "design_provenance")


@dataclass(frozen=True)
class ConstructionTrace:
    schema_version: str
    grammar_id: str
    target_spec_id: str
    provenance_nodes: tuple[ProvenanceNode, ...]
    coefficient_records: tuple[CoefficientRecord, ...]
    primitives: tuple[PrimitiveTrace, ...]
    trace_sha: str

    def __post_init__(self) -> None:
        _require_nonempty_string(self.schema_version, "schema_version")
        _require_nonempty_string(self.grammar_id, "grammar_id")
        _require_nonempty_string(self.target_spec_id, "target_spec_id")
        for field, item_type in (
            ("provenance_nodes", ProvenanceNode),
            ("coefficient_records", CoefficientRecord),
            ("primitives", PrimitiveTrace),
        ):
            values = _require_tuple(getattr(self, field), field)
            if not all(isinstance(item, item_type) for item in values):
                raise TypeError(f"{field} contains the wrong record type")
        _require_sha(self.trace_sha, "trace_sha")


def _join_kinds(kinds: Sequence[MechanismKind]) -> MechanismKind:
    if MechanismKind.TARGET_CONDITIONED in kinds:
        return MechanismKind.TARGET_CONDITIONED
    if MechanismKind.UNCLASSIFIED in kinds:
        return MechanismKind.UNCLASSIFIED
    return MechanismKind.TARGET_BLIND


def _normalize_node(value: ProvenanceNode) -> ProvenanceNode:
    if not isinstance(value, ProvenanceNode):
        raise TypeError("provenance_nodes must contain ProvenanceNode values")
    return ProvenanceNode(
        provenance_id=_require_nonempty_string(
            value.provenance_id,
            "provenance_id",
        ),
        operation=value.operation,
        depends_on=_string_tuple(
            value.depends_on,
            "depends_on",
            canonicalize=True,
        ),
        target_refs=_string_tuple(
            value.target_refs,
            "target_refs",
            canonicalize=True,
        ),
        objective_tags=_string_tuple(
            value.objective_tags,
            "objective_tags",
            canonicalize=True,
        ),
        search_run_id=_require_optional_string(
            value.search_run_id,
            "search_run_id",
        ),
        source_sha=_require_sha(value.source_sha, "source_sha"),
    )


def _normalize_spec(value: PrimitiveSpec) -> PrimitiveSpec:
    if not isinstance(value, PrimitiveSpec):
        raise TypeError("primitive_specs must contain PrimitiveSpec values")
    return PrimitiveSpec(
        mechanism_id=_require_nonempty_string(
            value.mechanism_id,
            "mechanism_id",
        ),
        production_id=_require_nonempty_string(
            value.production_id,
            "production_id",
        ),
        depends_on=_string_tuple(
            value.depends_on,
            "depends_on",
            canonicalize=True,
        ),
        support_offsets=_support_tuple(
            value.support_offsets,
            "support_offsets",
            canonicalize=True,
        ),
        state_channels=_string_tuple(
            value.state_channels,
            "state_channels",
            canonicalize=True,
        ),
        coefficient_expression=value.coefficient_expression,
        coefficient_variable_order=_string_tuple(
            value.coefficient_variable_order,
            "coefficient_variable_order",
            canonicalize=False,
        ),
        symbolic_origin_tags=_string_tuple(
            value.symbolic_origin_tags,
            "symbolic_origin_tags",
            canonicalize=True,
        ),
        neutral_ablation=_require_optional_string(
            value.neutral_ablation,
            "neutral_ablation",
        ),
        design_objective_tags=_string_tuple(
            value.design_objective_tags,
            "design_objective_tags",
            canonicalize=True,
        ),
        search_run_id=_require_optional_string(
            value.search_run_id,
            "search_run_id",
        ),
        source_sha=_require_sha(value.source_sha, "source_sha"),
        design_provenance=_require_nonempty_string(
            value.design_provenance,
            "design_provenance",
        ),
    )


def _topological_order(
    entries: Mapping[str, Sequence[str]],
    *,
    noun: str,
) -> tuple[str, ...]:
    if len(entries) > DAG_MAX_NODES:
        raise ValueError(f"{noun} DAG node limit exceeded")
    indegree: dict[str, int] = {}
    dependents: dict[str, list[str]] = {identifier: [] for identifier in entries}
    edge_count = 0
    for identifier, dependencies in entries.items():
        indegree[identifier] = len(dependencies)
        edge_count += len(dependencies)
        if edge_count > DAG_MAX_EDGES:
            raise ValueError(f"{noun} DAG edge limit exceeded")
        for dependency in dependencies:
            if dependency not in entries:
                raise ValueError(
                    f"{noun} {identifier!r} references missing {noun} {dependency!r}"
                )
            dependents[dependency].append(identifier)

    queue = deque(identifier for identifier in entries if indegree[identifier] == 0)
    order: list[str] = []
    depths: dict[str, int] = {}
    while queue:
        identifier = queue.popleft()
        dependencies = entries[identifier]
        depth = (
            1 + max(depths[dependency] for dependency in dependencies)
            if dependencies
            else 1
        )
        if depth > DAG_MAX_DEPTH:
            raise ValueError(f"{noun} DAG depth limit exceeded")
        depths[identifier] = depth
        order.append(identifier)
        for dependent in dependents[identifier]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                queue.append(dependent)
    if len(order) != len(entries):
        raise ValueError(f"{noun} DAG contains a cycle")
    return tuple(order)


def _validate_dag(
    entries: Mapping[str, Sequence[str]],
    *,
    noun: str,
) -> None:
    _topological_order(entries, noun=noun)


def _expression_to_ast(
    expression: object,
    registered_symbols: frozenset[str],
    *,
    _budget: Optional[list[int]] = None,
    _depth: int = 0,
    _seen_symbols: Optional[set[str]] = None,
) -> tuple[object, ...]:
    if _budget is None:
        _budget = [0]
    if _seen_symbols is None:
        _seen_symbols = set()
    if _depth > COEFFICIENT_AST_MAX_DEPTH:
        raise ValueError("coefficient AST depth limit exceeded")
    _budget[0] += 1
    if _budget[0] > COEFFICIENT_AST_MAX_NODES:
        raise ValueError("coefficient AST node limit exceeded")

    if expression is sp.I:
        return ("I",)
    if isinstance(expression, sp.Integer):
        encoded = str(int(expression))
        _parse_decimal_integer(encoded, "Integer")
        return ("Integer", encoded)
    if isinstance(expression, sp.Rational):
        numerator = str(int(expression.p))
        denominator = str(int(expression.q))
        _parse_decimal_integer(numerator, "Rational numerator")
        _parse_decimal_integer(denominator, "Rational denominator")
        return (
            "Rational",
            numerator,
            denominator,
        )
    if isinstance(expression, sp.Symbol):
        if (
            type(expression) is not sp.Symbol
            or expression.assumptions0 != {"commutative": True}
            or getattr(expression, "_assumptions_orig", None) != {}
        ):
            raise ValueError(
                "coefficient symbols must be standard commutative Symbols "
                "without assumptions"
            )
        name = str(expression)
        if name not in registered_symbols:
            raise ValueError(f"symbol {name!r} is not registered in variable_order")
        _seen_symbols.add(name)
        return ("Symbol", name)
    if isinstance(expression, sp.Add):
        return (
            "Add",
            *(
                _expression_to_ast(
                    argument,
                    registered_symbols,
                    _budget=_budget,
                    _depth=_depth + 1,
                    _seen_symbols=_seen_symbols,
                )
                for argument in expression.args
            ),
        )
    if isinstance(expression, sp.Mul):
        return (
            "Mul",
            *(
                _expression_to_ast(
                    argument,
                    registered_symbols,
                    _budget=_budget,
                    _depth=_depth + 1,
                    _seen_symbols=_seen_symbols,
                )
                for argument in expression.args
            ),
        )
    if isinstance(expression, sp.Pow):
        _validate_pow_exponent_value(expression.exp)
        return (
            "Pow",
            _expression_to_ast(
                expression.base,
                registered_symbols,
                _budget=_budget,
                _depth=_depth + 1,
                _seen_symbols=_seen_symbols,
            ),
            _expression_to_ast(
                expression.exp,
                registered_symbols,
                _budget=_budget,
                _depth=_depth + 1,
                _seen_symbols=_seen_symbols,
            ),
        )
    if isinstance(expression, sp.Float):
        raise TypeError("Float coefficients are forbidden; use exact Rational")
    if isinstance(expression, sp.Basic):
        raise TypeError(
            f"unsupported exact coefficient node {type(expression).__name__}"
        )
    raise TypeError("coefficient_expression must be an exact SymPy expression")


def _parse_decimal_integer(value: object, field: str) -> int:
    if type(value) is not str or _DECIMAL_INTEGER.fullmatch(value) is None:
        raise ValueError(f"{field} must be a canonical decimal integer string")
    digits = value[1:] if value.startswith("-") else value
    if len(digits) > COEFFICIENT_INTEGER_MAX_DIGITS:
        raise ValueError(f"{field} integer digit limit exceeded")
    parsed = int(value)
    if str(parsed) != value:
        raise ValueError(f"{field} must use canonical decimal spelling")
    return parsed


def _validate_pow_exponent_value(exponent: object) -> None:
    if isinstance(exponent, sp.Integer):
        magnitude = abs(_parse_decimal_integer(str(int(exponent)), "Pow exponent"))
        if magnitude > COEFFICIENT_POW_MAX_MAGNITUDE:
            raise ValueError("Pow exponent magnitude limit exceeded")
        return
    if isinstance(exponent, sp.Rational):
        numerator = abs(
            _parse_decimal_integer(str(int(exponent.p)), "Pow exponent numerator")
        )
        denominator = _parse_decimal_integer(
            str(int(exponent.q)),
            "Pow exponent denominator",
        )
        if (
            numerator > COEFFICIENT_POW_MAX_MAGNITUDE
            or denominator > COEFFICIENT_POW_MAX_MAGNITUDE
        ):
            raise ValueError("Pow exponent magnitude limit exceeded")
        return
    raise ValueError("Pow exponent must be an exact Integer or Rational")


def _validate_pow_exponent_ast(expression_ast: tuple[object, ...]) -> None:
    if not expression_ast or type(expression_ast[0]) is not str:
        raise ValueError("Pow exponent AST is malformed")
    tag = expression_ast[0]
    arguments = expression_ast[1:]
    if tag == "Integer" and len(arguments) == 1:
        magnitude = abs(_parse_decimal_integer(arguments[0], "Pow exponent"))
        if magnitude <= COEFFICIENT_POW_MAX_MAGNITUDE:
            return
    elif tag == "Rational" and len(arguments) == 2:
        numerator = abs(_parse_decimal_integer(arguments[0], "Pow exponent numerator"))
        denominator = _parse_decimal_integer(
            arguments[1],
            "Pow exponent denominator",
        )
        if (
            numerator <= COEFFICIENT_POW_MAX_MAGNITUDE
            and denominator <= COEFFICIENT_POW_MAX_MAGNITUDE
        ):
            return
    raise ValueError("Pow exponent must be a bounded exact Integer or Rational")


def _validate_eager_numeric_pow(base: sp.Basic, exponent: sp.Basic) -> None:
    if not isinstance(exponent, sp.Integer):
        return
    exponent_magnitude = abs(int(exponent))
    if exponent_magnitude <= 1:
        return
    components: tuple[int, ...]
    if isinstance(base, sp.Integer):
        components = (int(base),)
    elif isinstance(base, sp.Rational):
        components = (int(base.p), int(base.q))
    else:
        return
    for component in components:
        if abs(component) <= 1:
            continue
        component_digits = len(str(abs(component)))
        if component_digits * exponent_magnitude > COEFFICIENT_INTEGER_MAX_DIGITS:
            raise ValueError("Pow eager numeric result limit exceeded")


def _expression_from_ast(
    expression_ast: tuple[object, ...],
    symbols: Mapping[str, sp.Symbol],
    *,
    _budget: Optional[list[int]] = None,
    _depth: int = 0,
) -> sp.Basic:
    if _budget is None:
        _budget = [0]
    if _depth > COEFFICIENT_AST_MAX_DEPTH:
        raise ValueError("coefficient AST depth limit exceeded")
    _budget[0] += 1
    if _budget[0] > COEFFICIENT_AST_MAX_NODES:
        raise ValueError("coefficient AST node limit exceeded")
    if not expression_ast or type(expression_ast[0]) is not str:
        raise ValueError("expression_ast node must start with a string tag")
    tag = expression_ast[0]
    arguments = expression_ast[1:]
    if tag == "I":
        if arguments:
            raise ValueError("I AST node takes no arguments")
        return sp.I
    if tag == "Integer":
        if len(arguments) != 1:
            raise ValueError("Integer AST node takes one argument")
        return sp.Integer(_parse_decimal_integer(arguments[0], "Integer"))
    if tag == "Rational":
        if len(arguments) != 2:
            raise ValueError("Rational AST node takes two arguments")
        numerator = _parse_decimal_integer(arguments[0], "Rational numerator")
        denominator = _parse_decimal_integer(arguments[1], "Rational denominator")
        if denominator <= 1 or math.gcd(numerator, denominator) != 1:
            raise ValueError("Rational AST node must be reduced with denominator > 1")
        return sp.Rational(numerator, denominator)
    if tag == "Symbol":
        if len(arguments) != 1 or type(arguments[0]) is not str:
            raise ValueError("Symbol AST node takes one string argument")
        try:
            return symbols[arguments[0]]
        except KeyError as exc:
            raise ValueError(
                f"symbol {arguments[0]!r} is not registered in variable_order"
            ) from exc
    if tag in ("Add", "Mul"):
        if len(arguments) < 2:
            raise ValueError(f"{tag} AST node requires at least two arguments")
        children = tuple(
            _expression_from_ast(
                _as_ast_tuple(argument),
                symbols,
                _budget=_budget,
                _depth=_depth + 1,
            )
            for argument in arguments
        )
        return sp.Add(*children) if tag == "Add" else sp.Mul(*children)
    if tag == "Pow":
        if len(arguments) != 2:
            raise ValueError("Pow AST node takes two arguments")
        exponent_ast = _as_ast_tuple(arguments[1])
        _validate_pow_exponent_ast(exponent_ast)
        base = _expression_from_ast(
            _as_ast_tuple(arguments[0]),
            symbols,
            _budget=_budget,
            _depth=_depth + 1,
        )
        exponent = _expression_from_ast(
            exponent_ast,
            symbols,
            _budget=_budget,
            _depth=_depth + 1,
        )
        _validate_eager_numeric_pow(base, exponent)
        return sp.Pow(
            base,
            exponent,
        )
    raise ValueError(f"unsupported expression_ast tag {tag!r}")


def _as_ast_tuple(value: object) -> tuple[object, ...]:
    if type(value) is not tuple:
        raise TypeError("expression_ast child must be a tuple")
    return value


def _coefficient_digest_body(
    *,
    mechanism_id: str,
    expression_schema: str,
    variable_order: tuple[str, ...],
    expression_ast: tuple[object, ...],
    provenance_root_id: str,
) -> dict[str, object]:
    return {
        "mechanism_id": mechanism_id,
        "expression_schema": expression_schema,
        "variable_order": variable_order,
        "expression_ast": expression_ast,
        "provenance_root_id": provenance_root_id,
    }


def _build_coefficient_record(specification: PrimitiveSpec) -> CoefficientRecord:
    variable_order = _string_tuple(
        specification.coefficient_variable_order,
        "coefficient_variable_order",
        canonicalize=False,
    )
    registered_symbols = frozenset(variable_order)
    seen_symbols: set[str] = set()
    raw_expression_ast = _expression_to_ast(
        specification.coefficient_expression,
        registered_symbols,
        _seen_symbols=seen_symbols,
    )
    if seen_symbols != registered_symbols:
        raise ValueError(
            "coefficient variable_order must exactly match its standard Symbols"
        )
    normalized_expression = _expression_from_ast(
        raw_expression_ast,
        {name: sp.Symbol(name) for name in variable_order},
    )
    normalized_seen_symbols: set[str] = set()
    expression_ast = _expression_to_ast(
        normalized_expression,
        registered_symbols,
        _seen_symbols=normalized_seen_symbols,
    )
    if normalized_seen_symbols != registered_symbols:
        raise ValueError("coefficient variable_order changed during canonicalization")
    digest_body = _coefficient_digest_body(
        mechanism_id=specification.mechanism_id,
        expression_schema=COEFFICIENT_EXPRESSION_SCHEMA,
        variable_order=variable_order,
        expression_ast=expression_ast,
        provenance_root_id=specification.design_provenance,
    )
    return CoefficientRecord(
        mechanism_id=specification.mechanism_id,
        expression_schema=COEFFICIENT_EXPRESSION_SCHEMA,
        variable_order=variable_order,
        expression_ast=expression_ast,
        provenance_root_id=specification.design_provenance,
        coefficient_digest=canonical_sha(digest_body),
    )


def _evaluate_closed_ast(expression_ast: tuple[object, ...]) -> complex:
    tag = expression_ast[0]
    arguments = expression_ast[1:]
    if tag == "I":
        return complex(0.0, 1.0)
    if tag == "Integer":
        return complex(_parse_decimal_integer(arguments[0], "Integer"))
    if tag == "Rational":
        numerator = _parse_decimal_integer(arguments[0], "Rational numerator")
        denominator = _parse_decimal_integer(arguments[1], "Rational denominator")
        return complex(numerator / denominator)
    if tag == "Symbol":
        raise ValueError("runtime lowering requires a closed coefficient")
    if tag == "Add":
        return sum(
            (_evaluate_closed_ast(_as_ast_tuple(argument)) for argument in arguments),
            complex(0.0),
        )
    if tag == "Mul":
        result = complex(1.0)
        for argument in arguments:
            result *= _evaluate_closed_ast(_as_ast_tuple(argument))
        return result
    if tag == "Pow":
        return _evaluate_closed_ast(
            _as_ast_tuple(arguments[0])
        ) ** _evaluate_closed_ast(_as_ast_tuple(arguments[1]))
    raise ValueError(f"unsupported expression_ast tag {tag!r}")


def evaluate_closed_coefficient(record: CoefficientRecord) -> complex:
    """Safely lower one verified closed exact sidecar to a finite complex.

    Runtime callers cannot supply a replacement numeric value.  This function
    accepts no variables and never parses text as a SymPy expression.
    """

    if not isinstance(record, CoefficientRecord):
        raise TypeError("record must be a CoefficientRecord")
    if record.expression_schema != COEFFICIENT_EXPRESSION_SCHEMA:
        raise ValueError("unknown coefficient expression_schema")
    if record.variable_order:
        raise ValueError("runtime lowering requires a closed coefficient")
    expression = _expression_from_ast(record.expression_ast, {})
    canonical_ast = _expression_to_ast(expression, frozenset())
    if canonical_ast != record.expression_ast:
        raise ValueError("expression_ast is not canonical")
    digest_body = _coefficient_digest_body(
        mechanism_id=record.mechanism_id,
        expression_schema=record.expression_schema,
        variable_order=record.variable_order,
        expression_ast=record.expression_ast,
        provenance_root_id=record.provenance_root_id,
    )
    if record.coefficient_digest != canonical_sha(digest_body):
        raise ValueError("coefficient_digest does not match exact sidecar")
    try:
        value = _evaluate_closed_ast(record.expression_ast)
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise ValueError(
            "closed coefficient cannot be lowered to finite complex"
        ) from exc
    if not math.isfinite(value.real) or not math.isfinite(value.imag):
        raise ValueError("closed coefficient must lower to a finite complex")
    return value


def _provenance_analysis(
    nodes_by_id: Mapping[str, ProvenanceNode],
) -> tuple[
    dict[str, MechanismKind],
    dict[str, frozenset[str]],
    dict[str, frozenset[str]],
    dict[str, bool],
]:
    kinds: dict[str, MechanismKind] = {}
    objective_tags: dict[str, frozenset[str]] = {}
    search_ids: dict[str, frozenset[str]] = {}
    traceable_provenance: dict[str, bool] = {}

    entries = {identifier: node.depends_on for identifier, node in nodes_by_id.items()}
    for identifier in _topological_order(entries, noun="provenance"):
        current = nodes_by_id[identifier]
        dependency_kinds = [kinds[item] for item in current.depends_on]
        dependency_objectives: set[str] = set()
        dependency_search_ids: set[str] = set()
        has_traceable_ancestor = False
        for dependency in current.depends_on:
            dependency_objectives.update(objective_tags[dependency])
            dependency_search_ids.update(search_ids[dependency])
            has_traceable_ancestor |= traceable_provenance[dependency]

        operation = current.operation.value
        valid_search = (
            operation == ProvenanceOperation.SEARCH.value
            and has_traceable_ancestor
            and bool(current.objective_tags)
            and current.search_run_id is not None
        )
        valid_selection = (
            operation
            in (
                ProvenanceOperation.SELECTION.value,
                ProvenanceOperation.MANUAL_SELECTION.value,
            )
            and current.search_run_id is not None
            and current.search_run_id in dependency_search_ids
        )
        if operation in _TARGET_OPERATIONS or current.target_refs:
            own_kind = MechanismKind.TARGET_CONDITIONED
        elif operation in (
            ProvenanceOperation.OPAQUE_LITERAL.value,
            ProvenanceOperation.UNCLASSIFIED.value,
        ):
            own_kind = MechanismKind.UNCLASSIFIED
        elif operation in (
            ProvenanceOperation.GRAMMAR_PRIMITIVE.value,
            ProvenanceOperation.GRAMMAR_CONSTANT.value,
        ):
            own_kind = MechanismKind.TARGET_BLIND
        elif operation in _INHERITING_OPERATIONS:
            own_kind = (
                _join_kinds(dependency_kinds)
                if dependency_kinds
                else MechanismKind.UNCLASSIFIED
            )
        elif operation == ProvenanceOperation.SEARCH.value:
            own_kind = (
                _join_kinds(dependency_kinds)
                if valid_search
                else MechanismKind.UNCLASSIFIED
            )
        elif operation in (
            ProvenanceOperation.SELECTION.value,
            ProvenanceOperation.MANUAL_SELECTION.value,
        ):
            own_kind = (
                _join_kinds(dependency_kinds)
                if valid_selection
                else MechanismKind.UNCLASSIFIED
            )
        else:
            own_kind = MechanismKind.UNCLASSIFIED

        kinds[identifier] = _join_kinds([own_kind, *dependency_kinds])
        dependency_objectives.update(current.objective_tags)
        if valid_search:
            if current.search_run_id is None:
                raise AssertionError("valid search lost its search_run_id")
            dependency_search_ids.add(current.search_run_id)
        objective_tags[identifier] = frozenset(dependency_objectives)
        search_ids[identifier] = frozenset(dependency_search_ids)
        if operation == ProvenanceOperation.SEARCH.value:
            traceable_provenance[identifier] = valid_search
        elif operation in (
            ProvenanceOperation.SELECTION.value,
            ProvenanceOperation.MANUAL_SELECTION.value,
        ):
            traceable_provenance[identifier] = valid_selection
        else:
            traceable_provenance[identifier] = (
                has_traceable_ancestor
                or bool(current.objective_tags)
                or current.operation is ProvenanceOperation.TARGET_AWARE_OBJECTIVE
            )

    return kinds, objective_tags, search_ids, traceable_provenance


def _production_kind(production_id: str) -> MechanismKind:
    if production_id in _TARGET_PRODUCTIONS:
        return MechanismKind.TARGET_CONDITIONED
    if production_id in _BLIND_PRODUCTIONS:
        return MechanismKind.TARGET_BLIND
    return MechanismKind.UNCLASSIFIED


def _primitive_kinds(
    specifications: tuple[PrimitiveSpec, ...],
    provenance_kinds: Mapping[str, MechanismKind],
    provenance_objectives: Mapping[str, frozenset[str]],
    provenance_search_ids: Mapping[str, frozenset[str]],
) -> dict[str, MechanismKind]:
    specifications_by_id = {
        specification.mechanism_id: specification for specification in specifications
    }
    kinds: dict[str, MechanismKind] = {}
    entries = {
        identifier: specification.depends_on
        for identifier, specification in specifications_by_id.items()
    }
    for identifier in _topological_order(entries, noun="primitive"):
        specification = specifications_by_id[identifier]
        dependency_kinds = [
            kinds[dependency] for dependency in specification.depends_on
        ]
        root = specification.design_provenance
        kinds_to_join = [
            _production_kind(specification.production_id),
            provenance_kinds[root],
            *dependency_kinds,
        ]
        target_symbolic = any(
            tag.lower() in _TARGET_SYMBOLIC_TAGS or tag.lower().startswith("target:")
            for tag in specification.symbolic_origin_tags
        )
        if target_symbolic:
            kinds_to_join.append(MechanismKind.TARGET_CONDITIONED)

        recorded_objectives = frozenset(specification.design_objective_tags)
        inherited_objectives = provenance_objectives[root]
        recorded_search = specification.search_run_id
        inherited_searches = provenance_search_ids[root]
        if recorded_objectives != inherited_objectives:
            kinds_to_join.append(MechanismKind.UNCLASSIFIED)
        if (recorded_search is None and inherited_searches) or (
            recorded_search is not None and recorded_search not in inherited_searches
        ):
            kinds_to_join.append(MechanismKind.UNCLASSIFIED)
        kinds[identifier] = _join_kinds(kinds_to_join)
    return kinds


def _node_payload(node_value: ProvenanceNode) -> dict[str, object]:
    return {
        "provenance_id": node_value.provenance_id,
        "operation": node_value.operation.value,
        "depends_on": list(node_value.depends_on),
        "target_refs": list(node_value.target_refs),
        "objective_tags": list(node_value.objective_tags),
        "search_run_id": node_value.search_run_id,
        "source_sha": node_value.source_sha,
    }


def _coefficient_payload(record: CoefficientRecord) -> dict[str, object]:
    return {
        "mechanism_id": record.mechanism_id,
        "expression_schema": record.expression_schema,
        "variable_order": list(record.variable_order),
        "expression_ast": _tuple_tree_to_list(record.expression_ast),
        "provenance_root_id": record.provenance_root_id,
        "coefficient_digest": record.coefficient_digest,
    }


def _primitive_payload(primitive: PrimitiveTrace) -> dict[str, object]:
    return {
        "grammar_id": primitive.grammar_id,
        "target_spec_id": primitive.target_spec_id,
        "mechanism_id": primitive.mechanism_id,
        "production_id": primitive.production_id,
        "kind": primitive.kind.value,
        "depends_on": list(primitive.depends_on),
        "support_offsets": [list(offset) for offset in primitive.support_offsets],
        "state_channels": list(primitive.state_channels),
        "coefficient_digest": primitive.coefficient_digest,
        "symbolic_origin_tags": list(primitive.symbolic_origin_tags),
        "neutral_ablation": primitive.neutral_ablation,
        "design_objective_tags": list(primitive.design_objective_tags),
        "search_run_id": primitive.search_run_id,
        "source_sha": primitive.source_sha,
        "design_provenance": primitive.design_provenance,
    }


def _trace_body(
    *,
    schema_version: str,
    grammar_id: str,
    target_spec_id: str,
    provenance_nodes: tuple[ProvenanceNode, ...],
    coefficient_records: tuple[CoefficientRecord, ...],
    primitives: tuple[PrimitiveTrace, ...],
) -> dict[str, object]:
    return {
        "schema_version": schema_version,
        "grammar_id": grammar_id,
        "target_spec_id": target_spec_id,
        "provenance_nodes": [_node_payload(item) for item in provenance_nodes],
        "coefficient_records": [
            _coefficient_payload(item) for item in coefficient_records
        ],
        "primitives": [_primitive_payload(item) for item in primitives],
    }


def _tuple_tree_to_list(value: object) -> object:
    if type(value) is tuple:
        return [_tuple_tree_to_list(item) for item in value]
    return value


def build_construction_trace(
    *,
    target_spec_id: str,
    provenance_nodes: Sequence[ProvenanceNode],
    primitive_specs: Sequence[PrimitiveSpec],
    grammar_id: str = FROZEN_GRAMMAR_ID,
    schema_version: str = CONSTRUCTION_TRACE_SCHEMA,
) -> ConstructionTrace:
    """Build a trace whose mechanism kinds are mechanically recomputed."""

    target_spec_id = _require_nonempty_string(target_spec_id, "target_spec_id")
    grammar_id = _require_nonempty_string(grammar_id, "grammar_id")
    schema_version = _require_nonempty_string(schema_version, "schema_version")
    if grammar_id != FROZEN_GRAMMAR_ID:
        raise ValueError(f"grammar_id must be {FROZEN_GRAMMAR_ID!r}")
    if schema_version != CONSTRUCTION_TRACE_SCHEMA:
        raise ValueError(f"schema_version must be {CONSTRUCTION_TRACE_SCHEMA!r}")
    if not isinstance(provenance_nodes, Sequence) or isinstance(
        provenance_nodes,
        (str, bytes, bytearray),
    ):
        raise TypeError("provenance_nodes must be a sequence")
    if not isinstance(primitive_specs, Sequence) or isinstance(
        primitive_specs,
        (str, bytes, bytearray),
    ):
        raise TypeError("primitive_specs must be a sequence")

    normalized_nodes_input = tuple(_normalize_node(item) for item in provenance_nodes)
    if not normalized_nodes_input:
        raise ValueError("provenance_nodes must not be empty")
    nodes_by_id: dict[str, ProvenanceNode] = {}
    for node_value in normalized_nodes_input:
        if node_value.provenance_id in nodes_by_id:
            raise ValueError(f"duplicate provenance ID {node_value.provenance_id!r}")
        nodes_by_id[node_value.provenance_id] = node_value
    _validate_dag(
        {key: value.depends_on for key, value in nodes_by_id.items()},
        noun="provenance",
    )
    normalized_nodes = tuple(nodes_by_id[key] for key in sorted(nodes_by_id))

    normalized_specs = tuple(_normalize_spec(item) for item in primitive_specs)
    if not normalized_specs:
        raise ValueError("primitive_specs must not be empty")
    specs_by_id: dict[str, PrimitiveSpec] = {}
    for specification in normalized_specs:
        if specification.mechanism_id in specs_by_id:
            raise ValueError(f"duplicate mechanism ID {specification.mechanism_id!r}")
        if specification.design_provenance not in nodes_by_id:
            raise ValueError(
                f"mechanism {specification.mechanism_id!r} references missing "
                f"provenance {specification.design_provenance!r}"
            )
        specs_by_id[specification.mechanism_id] = specification
    _validate_dag(
        {key: value.depends_on for key, value in specs_by_id.items()},
        noun="primitive",
    )

    (
        provenance_kinds,
        provenance_objectives,
        provenance_search_ids,
        _,
    ) = _provenance_analysis(nodes_by_id)
    computed_kinds = _primitive_kinds(
        normalized_specs,
        provenance_kinds,
        provenance_objectives,
        provenance_search_ids,
    )

    coefficient_records = tuple(
        _build_coefficient_record(specification) for specification in normalized_specs
    )
    records_by_id = {record.mechanism_id: record for record in coefficient_records}
    primitives = tuple(
        PrimitiveTrace(
            grammar_id=grammar_id,
            target_spec_id=target_spec_id,
            mechanism_id=specification.mechanism_id,
            production_id=specification.production_id,
            kind=computed_kinds[specification.mechanism_id],
            depends_on=specification.depends_on,
            support_offsets=specification.support_offsets,
            state_channels=specification.state_channels,
            coefficient_digest=records_by_id[
                specification.mechanism_id
            ].coefficient_digest,
            symbolic_origin_tags=specification.symbolic_origin_tags,
            neutral_ablation=specification.neutral_ablation,
            design_objective_tags=specification.design_objective_tags,
            search_run_id=specification.search_run_id,
            source_sha=specification.source_sha,
            design_provenance=specification.design_provenance,
        )
        for specification in normalized_specs
    )
    body = _trace_body(
        schema_version=schema_version,
        grammar_id=grammar_id,
        target_spec_id=target_spec_id,
        provenance_nodes=normalized_nodes,
        coefficient_records=coefficient_records,
        primitives=primitives,
    )
    candidate = ConstructionTrace(
        schema_version=schema_version,
        grammar_id=grammar_id,
        target_spec_id=target_spec_id,
        provenance_nodes=normalized_nodes,
        coefficient_records=coefficient_records,
        primitives=primitives,
        trace_sha=canonical_sha(body),
    )
    return verify_construction_trace(candidate)


def construction_trace_payload(trace: ConstructionTrace) -> dict[str, object]:
    """Return the complete strict JSON payload for an immutable trace."""

    if not isinstance(trace, ConstructionTrace):
        raise TypeError("trace must be a ConstructionTrace")
    body = _trace_body(
        schema_version=trace.schema_version,
        grammar_id=trace.grammar_id,
        target_spec_id=trace.target_spec_id,
        provenance_nodes=trace.provenance_nodes,
        coefficient_records=trace.coefficient_records,
        primitives=trace.primitives,
    )
    return {**body, "trace_sha": trace.trace_sha}


def _snapshot_json(
    value: object,
    path: str,
    active_containers: set[int],
    memo: Optional[dict[int, tuple[object, object]]] = None,
    budget: Optional[list[int]] = None,
    depth: int = 0,
) -> object:
    if memo is None:
        memo = {}
    if budget is None:
        budget = [0]
    if depth > SNAPSHOT_MAX_DEPTH:
        raise ValueError(f"{path} exceeds the snapshot depth limit")
    budget[0] += 1
    if budget[0] > SNAPSHOT_MAX_NODES:
        raise ValueError(f"{path} exceeds the snapshot node limit")

    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite number")
        return value
    if isinstance(value, Mapping):
        container_id = id(value)
        if container_id in active_containers:
            raise ValueError(f"{path} contains a cyclic container")
        memo_entry = memo.get(container_id)
        if memo_entry is not None and memo_entry[0] is value:
            return memo_entry[1]
        active_containers.add(container_id)
        try:
            raw_items = tuple(islice(iter(value.items()), SNAPSHOT_MAX_NODES + 1))
            if len(raw_items) > SNAPSHOT_MAX_NODES:
                raise ValueError(f"{path} exceeds the snapshot node limit")
            result: dict[str, object] = {}
            for index, pair in enumerate(raw_items):
                if type(pair) is not tuple or len(pair) != 2:
                    raise TypeError(
                        f"{path}.items()[{index}] must be a key/value tuple"
                    )
                key, item = pair
                if type(key) is not str:
                    raise TypeError(f"{path} mapping key must be a str")
                if key in result:
                    raise ValueError(
                        f"{path} items snapshot contains duplicate key {key!r}"
                    )
                result[key] = _snapshot_json(
                    item,
                    f"{path}.{key}",
                    active_containers,
                    memo,
                    budget,
                    depth + 1,
                )
            frozen_result = MappingProxyType(result)
            memo[container_id] = (value, frozen_result)
            return frozen_result
        finally:
            active_containers.remove(container_id)
    if type(value) in (list, tuple):
        container_id = id(value)
        if container_id in active_containers:
            raise ValueError(f"{path} contains a cyclic container")
        memo_entry = memo.get(container_id)
        if memo_entry is not None and memo_entry[0] is value:
            return memo_entry[1]
        active_containers.add(container_id)
        try:
            raw_values = tuple(value)
            frozen_result = tuple(
                _snapshot_json(
                    item,
                    f"{path}[{index}]",
                    active_containers,
                    memo,
                    budget,
                    depth + 1,
                )
                for index, item in enumerate(raw_values)
            )
            memo[container_id] = (value, frozen_result)
            return frozen_result
        finally:
            active_containers.remove(container_id)
    raise TypeError(f"{path} contains a non-JSON value of type {type(value).__name__}")


def _strict_fields(
    payload: Mapping[str, object],
    expected: frozenset[str],
    path: str,
) -> None:
    actual = frozenset(payload)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        details = []
        if missing:
            details.append(f"missing={missing!r}")
        if unknown:
            details.append(f"unknown={unknown!r}")
        raise ValueError(f"{path} schema mismatch: {', '.join(details)}")


def _payload_tuple(value: object, field: str) -> tuple[object, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be a JSON array")
    return value


def _payload_string_tuple(value: object, field: str) -> tuple[str, ...]:
    result = _payload_tuple(value, field)
    return _string_tuple(result, field, canonicalize=False)


def _payload_support(value: object, field: str) -> tuple[tuple[int, ...], ...]:
    rows = _payload_tuple(value, field)
    converted: list[tuple[int, ...]] = []
    for index, row in enumerate(rows):
        converted.append(
            tuple(_payload_tuple(row, f"{field}[{index}]"))  # type: ignore[arg-type]
        )
    return _support_tuple(tuple(converted), field, canonicalize=False)


def _payload_ast(value: object, field: str) -> tuple[object, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be a JSON array")
    return tuple(
        _payload_ast(item, f"{field}[{index}]") if type(item) is tuple else item
        for index, item in enumerate(value)
    )


def _parse_trace_payload(snapshot: Mapping[str, object]) -> ConstructionTrace:
    _strict_fields(
        snapshot,
        frozenset(
            (
                "schema_version",
                "grammar_id",
                "target_spec_id",
                "provenance_nodes",
                "coefficient_records",
                "primitives",
                "trace_sha",
            )
        ),
        "$",
    )
    schema_version = _require_nonempty_string(
        snapshot["schema_version"],
        "schema_version",
    )
    grammar_id = _require_nonempty_string(snapshot["grammar_id"], "grammar_id")
    target_spec_id = _require_nonempty_string(
        snapshot["target_spec_id"],
        "target_spec_id",
    )
    trace_sha = _require_sha(snapshot["trace_sha"], "trace_sha")

    raw_nodes = _payload_tuple(snapshot["provenance_nodes"], "provenance_nodes")
    nodes: list[ProvenanceNode] = []
    node_fields = frozenset(
        (
            "provenance_id",
            "operation",
            "depends_on",
            "target_refs",
            "objective_tags",
            "search_run_id",
            "source_sha",
        )
    )
    for index, raw in enumerate(raw_nodes):
        if not isinstance(raw, Mapping):
            raise TypeError(f"provenance_nodes[{index}] must be a mapping")
        _strict_fields(raw, node_fields, f"provenance_nodes[{index}]")
        try:
            operation = ProvenanceOperation(raw["operation"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"provenance_nodes[{index}].operation is unknown") from exc
        nodes.append(
            ProvenanceNode(
                provenance_id=_require_nonempty_string(
                    raw["provenance_id"],
                    "provenance_id",
                ),
                operation=operation,
                depends_on=_payload_string_tuple(
                    raw["depends_on"],
                    "depends_on",
                ),
                target_refs=_payload_string_tuple(
                    raw["target_refs"],
                    "target_refs",
                ),
                objective_tags=_payload_string_tuple(
                    raw["objective_tags"],
                    "objective_tags",
                ),
                search_run_id=_require_optional_string(
                    raw["search_run_id"],
                    "search_run_id",
                ),
                source_sha=_require_sha(raw["source_sha"], "source_sha"),
            )
        )

    raw_records = _payload_tuple(
        snapshot["coefficient_records"],
        "coefficient_records",
    )
    records: list[CoefficientRecord] = []
    record_fields = frozenset(
        (
            "mechanism_id",
            "expression_schema",
            "variable_order",
            "expression_ast",
            "provenance_root_id",
            "coefficient_digest",
        )
    )
    for index, raw in enumerate(raw_records):
        if not isinstance(raw, Mapping):
            raise TypeError(f"coefficient_records[{index}] must be a mapping")
        _strict_fields(raw, record_fields, f"coefficient_records[{index}]")
        records.append(
            CoefficientRecord(
                mechanism_id=_require_nonempty_string(
                    raw["mechanism_id"],
                    "mechanism_id",
                ),
                expression_schema=_require_nonempty_string(
                    raw["expression_schema"],
                    "expression_schema",
                ),
                variable_order=_payload_string_tuple(
                    raw["variable_order"],
                    "variable_order",
                ),
                expression_ast=_payload_ast(
                    raw["expression_ast"],
                    "expression_ast",
                ),
                provenance_root_id=_require_nonempty_string(
                    raw["provenance_root_id"],
                    "provenance_root_id",
                ),
                coefficient_digest=_require_sha(
                    raw["coefficient_digest"],
                    "coefficient_digest",
                ),
            )
        )

    raw_primitives = _payload_tuple(snapshot["primitives"], "primitives")
    primitives: list[PrimitiveTrace] = []
    primitive_fields = frozenset(
        (
            "grammar_id",
            "target_spec_id",
            "mechanism_id",
            "production_id",
            "kind",
            "depends_on",
            "support_offsets",
            "state_channels",
            "coefficient_digest",
            "symbolic_origin_tags",
            "neutral_ablation",
            "design_objective_tags",
            "search_run_id",
            "source_sha",
            "design_provenance",
        )
    )
    for index, raw in enumerate(raw_primitives):
        if not isinstance(raw, Mapping):
            raise TypeError(f"primitives[{index}] must be a mapping")
        _strict_fields(raw, primitive_fields, f"primitives[{index}]")
        try:
            kind = MechanismKind(raw["kind"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"primitives[{index}].kind is unknown") from exc
        primitives.append(
            PrimitiveTrace(
                grammar_id=_require_nonempty_string(
                    raw["grammar_id"],
                    "grammar_id",
                ),
                target_spec_id=_require_nonempty_string(
                    raw["target_spec_id"],
                    "target_spec_id",
                ),
                mechanism_id=_require_nonempty_string(
                    raw["mechanism_id"],
                    "mechanism_id",
                ),
                production_id=_require_nonempty_string(
                    raw["production_id"],
                    "production_id",
                ),
                kind=kind,
                depends_on=_payload_string_tuple(
                    raw["depends_on"],
                    "depends_on",
                ),
                support_offsets=_payload_support(
                    raw["support_offsets"],
                    "support_offsets",
                ),
                state_channels=_payload_string_tuple(
                    raw["state_channels"],
                    "state_channels",
                ),
                coefficient_digest=_require_sha(
                    raw["coefficient_digest"],
                    "coefficient_digest",
                ),
                symbolic_origin_tags=_payload_string_tuple(
                    raw["symbolic_origin_tags"],
                    "symbolic_origin_tags",
                ),
                neutral_ablation=_require_optional_string(
                    raw["neutral_ablation"],
                    "neutral_ablation",
                ),
                design_objective_tags=_payload_string_tuple(
                    raw["design_objective_tags"],
                    "design_objective_tags",
                ),
                search_run_id=_require_optional_string(
                    raw["search_run_id"],
                    "search_run_id",
                ),
                source_sha=_require_sha(raw["source_sha"], "source_sha"),
                design_provenance=_require_nonempty_string(
                    raw["design_provenance"],
                    "design_provenance",
                ),
            )
        )
    return ConstructionTrace(
        schema_version=schema_version,
        grammar_id=grammar_id,
        target_spec_id=target_spec_id,
        provenance_nodes=tuple(nodes),
        coefficient_records=tuple(records),
        primitives=tuple(primitives),
        trace_sha=trace_sha,
    )


def verify_construction_trace(
    trace: Union[ConstructionTrace, Mapping[str, object]],
) -> ConstructionTrace:
    """Verify strict schema, exact sidecars, both DAGs, taint, and full SHA."""

    if isinstance(trace, ConstructionTrace):
        supplied_payload: object = construction_trace_payload(trace)
    elif isinstance(trace, Mapping):
        supplied_payload = trace
    else:
        raise TypeError("trace must be a ConstructionTrace or Mapping")
    snapshot = _snapshot_json(supplied_payload, "$", set())
    if not isinstance(snapshot, Mapping):
        raise TypeError("trace payload must normalize to a mapping")
    parsed = _parse_trace_payload(snapshot)

    if parsed.schema_version != CONSTRUCTION_TRACE_SCHEMA:
        raise ValueError("unexpected construction trace schema_version")
    if parsed.grammar_id != FROZEN_GRAMMAR_ID:
        raise ValueError("unexpected construction trace grammar_id")
    if not parsed.provenance_nodes:
        raise ValueError("provenance_nodes must not be empty")
    if not parsed.coefficient_records:
        raise ValueError("coefficient_records must not be empty")
    if not parsed.primitives:
        raise ValueError("primitives must not be empty")

    body = _trace_body(
        schema_version=parsed.schema_version,
        grammar_id=parsed.grammar_id,
        target_spec_id=parsed.target_spec_id,
        provenance_nodes=parsed.provenance_nodes,
        coefficient_records=parsed.coefficient_records,
        primitives=parsed.primitives,
    )
    expected_trace_sha = canonical_sha(body)
    if parsed.trace_sha != expected_trace_sha:
        raise ValueError("trace_sha does not match the complete canonical body")

    node_ids: set[str] = set()
    nodes_by_id: dict[str, ProvenanceNode] = {}
    for node_value in parsed.provenance_nodes:
        if node_value.provenance_id in node_ids:
            raise ValueError(f"duplicate provenance ID {node_value.provenance_id!r}")
        node_ids.add(node_value.provenance_id)
        nodes_by_id[node_value.provenance_id] = node_value
        if node_value.depends_on != tuple(sorted(node_value.depends_on)):
            raise ValueError("provenance depends_on is not canonical")
        if node_value.target_refs != tuple(sorted(node_value.target_refs)):
            raise ValueError("provenance target_refs is not canonical")
        if node_value.objective_tags != tuple(sorted(node_value.objective_tags)):
            raise ValueError("provenance objective_tags is not canonical")
    if tuple(nodes_by_id) != tuple(sorted(nodes_by_id)):
        raise ValueError("provenance_nodes are not in canonical ID order")
    _validate_dag(
        {key: value.depends_on for key, value in nodes_by_id.items()},
        noun="provenance",
    )

    record_ids: set[str] = set()
    records_by_id: dict[str, CoefficientRecord] = {}
    for record in parsed.coefficient_records:
        if record.mechanism_id in record_ids:
            raise ValueError(
                f"duplicate coefficient mechanism ID {record.mechanism_id!r}"
            )
        record_ids.add(record.mechanism_id)
        records_by_id[record.mechanism_id] = record
        if record.expression_schema != COEFFICIENT_EXPRESSION_SCHEMA:
            raise ValueError("unknown coefficient expression_schema")
        if record.provenance_root_id not in nodes_by_id:
            raise ValueError("coefficient references missing provenance root")
        symbols = {name: sp.Symbol(name) for name in record.variable_order}
        expression = _expression_from_ast(record.expression_ast, symbols)
        seen_symbols: set[str] = set()
        canonical_ast = _expression_to_ast(
            expression,
            frozenset(record.variable_order),
            _seen_symbols=seen_symbols,
        )
        if seen_symbols != frozenset(record.variable_order):
            raise ValueError(
                "coefficient variable_order must exactly match its Symbols"
            )
        if canonical_ast != record.expression_ast:
            raise ValueError("expression_ast is not canonical")
        digest_body = _coefficient_digest_body(
            mechanism_id=record.mechanism_id,
            expression_schema=record.expression_schema,
            variable_order=record.variable_order,
            expression_ast=record.expression_ast,
            provenance_root_id=record.provenance_root_id,
        )
        if record.coefficient_digest != canonical_sha(digest_body):
            raise ValueError("coefficient_digest does not match exact sidecar")

    primitive_ids: set[str] = set()
    primitives_by_id: dict[str, PrimitiveTrace] = {}
    for primitive in parsed.primitives:
        if primitive.mechanism_id in primitive_ids:
            raise ValueError(f"duplicate mechanism ID {primitive.mechanism_id!r}")
        primitive_ids.add(primitive.mechanism_id)
        primitives_by_id[primitive.mechanism_id] = primitive
        if primitive.grammar_id != parsed.grammar_id:
            raise ValueError("primitive grammar_id does not match trace")
        if primitive.target_spec_id != parsed.target_spec_id:
            raise ValueError("primitive target_spec_id does not match trace")
        if primitive.depends_on != tuple(sorted(primitive.depends_on)):
            raise ValueError("primitive depends_on is not canonical")
        if primitive.support_offsets != tuple(sorted(primitive.support_offsets)):
            raise ValueError("primitive support_offsets is not canonical")
        if primitive.state_channels != tuple(sorted(primitive.state_channels)):
            raise ValueError("primitive state_channels is not canonical")
        if primitive.symbolic_origin_tags != tuple(
            sorted(primitive.symbolic_origin_tags)
        ):
            raise ValueError("primitive symbolic_origin_tags is not canonical")
        if primitive.design_objective_tags != tuple(
            sorted(primitive.design_objective_tags)
        ):
            raise ValueError("primitive design_objective_tags is not canonical")
        if primitive.design_provenance not in nodes_by_id:
            raise ValueError("primitive references missing provenance root")
        if primitive.mechanism_id not in records_by_id:
            raise ValueError("primitive is missing a coefficient sidecar")
        record = records_by_id[primitive.mechanism_id]
        if record.provenance_root_id != primitive.design_provenance:
            raise ValueError("coefficient provenance root does not match primitive")
        if record.coefficient_digest != primitive.coefficient_digest:
            raise ValueError("coefficient digest does not match primitive")
    if record_ids != primitive_ids:
        raise ValueError("coefficient sidecars and primitives are not one-to-one")
    if tuple(records_by_id) != tuple(primitives_by_id):
        raise ValueError("coefficient sidecar order must match primitive order")
    _validate_dag(
        {key: value.depends_on for key, value in primitives_by_id.items()},
        noun="primitive",
    )

    (
        provenance_kinds,
        provenance_objectives,
        provenance_search_ids,
        _,
    ) = _provenance_analysis(nodes_by_id)
    specifications = tuple(
        PrimitiveSpec(
            mechanism_id=primitive.mechanism_id,
            production_id=primitive.production_id,
            depends_on=primitive.depends_on,
            support_offsets=primitive.support_offsets,
            state_channels=primitive.state_channels,
            coefficient_expression=sp.Integer(0),
            coefficient_variable_order=records_by_id[
                primitive.mechanism_id
            ].variable_order,
            symbolic_origin_tags=primitive.symbolic_origin_tags,
            neutral_ablation=primitive.neutral_ablation,
            design_objective_tags=primitive.design_objective_tags,
            search_run_id=primitive.search_run_id,
            source_sha=primitive.source_sha,
            design_provenance=primitive.design_provenance,
        )
        for primitive in parsed.primitives
    )
    computed_kinds = _primitive_kinds(
        specifications,
        provenance_kinds,
        provenance_objectives,
        provenance_search_ids,
    )
    for primitive in parsed.primitives:
        if primitive.kind is not computed_kinds[primitive.mechanism_id]:
            raise ValueError(f"computed kind mismatch for {primitive.mechanism_id!r}")
    return parsed


_freeze_project_class_methods(
    ProvenanceNode,
    CoefficientRecord,
    PrimitiveSpec,
    PrimitiveTrace,
    ConstructionTrace,
)


__all__ = [
    "COEFFICIENT_AST_MAX_DEPTH",
    "COEFFICIENT_AST_MAX_NODES",
    "COEFFICIENT_EXPRESSION_SCHEMA",
    "COEFFICIENT_INTEGER_MAX_DIGITS",
    "COEFFICIENT_POW_MAX_MAGNITUDE",
    "CONSTRUCTION_TRACE_SCHEMA",
    "DAG_MAX_DEPTH",
    "DAG_MAX_EDGES",
    "DAG_MAX_NODES",
    "FROZEN_GRAMMAR_ID",
    "SNAPSHOT_MAX_DEPTH",
    "SNAPSHOT_MAX_NODES",
    "CoefficientRecord",
    "ConstructionTrace",
    "MechanismKind",
    "PrimitiveSpec",
    "PrimitiveTrace",
    "ProvenanceNode",
    "ProvenanceOperation",
    "build_construction_trace",
    "construction_trace_payload",
    "evaluate_closed_coefficient",
    "verify_construction_trace",
]
