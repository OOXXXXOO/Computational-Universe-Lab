"""Independent exact reconstruction for the V3-M0 Phase-0 certificate.

The public verifier never evaluates certificate expressions supplied as
strings.  It rebuilds the frozen R15/R32 algebra from fixed primitives and
compares the resulting JSON claims structurally.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from functools import lru_cache
from typing import Any

import sympy as sp

from .evidence import canonical_sha


VARIABLE_ORDER = ("zx", "zy", "zz")
PACKING = (
    "h00", "h01", "h02", "h03", "h11",
    "h12", "h13", "h22", "h23", "h33",
)
PACKED_PAIRS = tuple(
    (m, n) for m in range(4) for n in range(m, 4)
)
WITNESS_ROWS = (17, 18, 19, 34, 35, 51)
DIRECTION_SPECS = (
    ("axial", (1, 0, 0), (0, 2, 3, 7, 8, 9)),
    ("face-diagonal", (1, 1, 0), (0, 1, 3, 4, 6, 9)),
    ("body-diagonal", (1, 1, 1), (0, 1, 2, 4, 5, 7)),
)
TOP_LEVEL_FIELDS = frozenset(
    (
        "schema",
        "artifact_kind",
        "evidence_kind",
        "raw_kernel_available",
        "raw_kernel_recomputed",
        "raw_kernel_independent_recomputation",
        "production_symbol_equivalence",
        "claim_ceiling",
        "status",
        "environment",
        "parent",
        "lineage",
        "manifest",
        "saved_scalar_reduction",
        "static_bridge",
        "exact",
        "formal",
        "gates",
        "certificate_sha",
    )
)
ENVIRONMENT_FIELDS = frozenset(
    (
        "numpy_version",
        "numpy_build",
        "numpy_build_config_sha256",
        "blas",
        "lapack",
        "threadpoolctl",
        "python",
        "platform",
        "machine",
        "system",
        "release",
        "attribution_only",
        "cross_platform_bit_identical_required",
    )
)


def _json_snapshot(
    value: object,
    path: str = "$",
    active: set[int] | None = None,
) -> Any:
    """Take one deep JSON snapshot of possibly adversarial mappings."""

    if active is None:
        active = set()
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite number")
        return value
    if isinstance(value, Mapping):
        marker = id(value)
        if marker in active:
            raise ValueError(f"{path} contains a cyclic mapping")
        active.add(marker)
        try:
            result: dict[str, Any] = {}
            for key, item in value.items():
                if type(key) is not str:
                    raise TypeError(f"{path} mapping key must be a string")
                if key in result:
                    raise ValueError(f"{path} contains duplicate key {key!r}")
                result[key] = _json_snapshot(item, f"{path}.{key}", active)
            return result
        finally:
            active.remove(marker)
    if type(value) in (list, tuple):
        marker = id(value)
        if marker in active:
            raise ValueError(f"{path} contains a cyclic array")
        active.add(marker)
        try:
            return [
                _json_snapshot(item, f"{path}[{index}]", active)
                for index, item in enumerate(value)
            ]
        finally:
            active.remove(marker)
    raise TypeError(f"{path} contains non-JSON type {type(value).__name__}")


def _pack(matrix: sp.Matrix) -> sp.Matrix:
    return sp.Matrix([matrix[m, n] for m, n in PACKED_PAIRS])


def _unpack(vector: sp.Matrix) -> sp.Matrix:
    matrix = sp.zeros(4)
    for index, (m, n) in enumerate(PACKED_PAIRS):
        matrix[m, n] = vector[index]
        matrix[n, m] = vector[index]
    return matrix


def _reference_kappa(direction: tuple[int, int, int]) -> sp.Matrix:
    m = sum(direction)
    a = sp.sqrt(2 - sp.sqrt(2))
    return sp.Matrix([sp.sqrt(m) * a, *(a * value for value in direction)])


def _incidence(kappa: sp.Matrix) -> sp.Matrix:
    columns: list[sp.Matrix] = []
    for column in range(10):
        packed = sp.zeros(10, 1)
        packed[column] = 1
        h = _unpack(packed)
        values = []
        for m in range(4):
            for a in range(4):
                for n in range(4):
                    for b in range(4):
                        values.append(
                            sp.expand(
                                (
                                    kappa[m] * kappa[n] * h[a, b]
                                    + kappa[a] * kappa[b] * h[m, n]
                                    - kappa[m] * kappa[b] * h[a, n]
                                    - kappa[a] * kappa[n] * h[m, b]
                                )
                                / 2
                            )
                        )
        columns.append(sp.Matrix(values))
    return sp.Matrix.hstack(*columns)


def _r15_gauge_then_r32_trace_reverse(kappa: sp.Matrix) -> sp.Matrix:
    eta = sp.diag(-1, 1, 1, 1)
    columns = []
    for a in range(4):
        xi = sp.eye(4)[:, a]
        k_dot_xi = (xi.T * eta * kappa)[0]
        hbar = kappa * xi.T + xi * kappa.T - eta * k_dot_xi
        trace = sum(eta[m, m] * hbar[m, m] for m in range(4))
        physical = hbar - eta * trace / 2
        columns.append(_pack(physical).applyfunc(sp.simplify))
    return sp.Matrix.hstack(*columns)


def _tt_basis(direction: tuple[int, int, int]) -> sp.Matrix:
    m = sum(direction)
    n = sp.Matrix(direction) / sp.sqrt(m)
    # Mirrors r15.tt_basis' frozen branch exactly for the three directions.
    seed = sp.Matrix((0, 1, 0)) if direction == (1, 0, 0) else sp.Matrix((1, 0, 0))
    e1 = n.cross(seed)
    e1 = e1 / sp.sqrt((e1.T * e1)[0])
    e2 = n.cross(e1)
    plus = e1 * e1.T - e2 * e2.T
    cross = e1 * e2.T + e2 * e1.T
    columns = []
    for polarization in (plus, cross):
        h = sp.zeros(4)
        h[1:4, 1:4] = polarization
        columns.append(_pack(h).applyfunc(sp.simplify))
    return sp.Matrix.hstack(*columns)


def _gram_projector(columns: sp.Matrix) -> sp.Matrix:
    gram = columns.conjugate().T * columns
    return (columns * gram.inv() * columns.conjugate().T).applyfunc(sp.simplify)


def _zero_matrix(matrix: sp.Matrix) -> bool:
    return all(sp.simplify(sp.sqrtdenest(value)) == 0 for value in matrix)


def _expr_text(value: sp.Expr) -> str:
    return sp.sstr(sp.factor(value)).replace("**", "^")


def _laurent_support(expression: sp.Expr, variables: tuple[sp.Symbol, ...]) -> list[list[int]]:
    expanded = sp.expand(expression)
    support: set[tuple[int, ...]] = set()
    for term in sp.Add.make_args(expanded):
        powers = term.as_powers_dict()
        support.add(tuple(int(powers.get(variable, 0)) for variable in variables))
    return [list(row) for row in sorted(support)]


def _constraint_coefficients() -> list[list[list[sp.Rational]]]:
    eta = sp.diag(-1, 1, 1, 1)
    coeff = [
        [[sp.Rational(0) for _axis in range(3)] for _component in range(10)]
        for _nu in range(4)
    ]
    for component, (m, n) in enumerate(PACKED_PAIRS):
        tensor = sp.zeros(4)
        tensor[m, n] = 1
        tensor[n, m] = 1
        trace = sum(eta[a, a] * tensor[a, a] for a in range(4))
        trace_reversed = tensor - eta * trace / 2
        for nu in range(4):
            for axis, i in enumerate((1, 2, 3)):
                coeff[nu][component][axis] = trace_reversed[i, nu]
    return coeff


def _laurent_claim() -> dict[str, object]:
    variables = sp.symbols("zx zy zz")
    differences = tuple(variable - 1 for variable in variables)
    adjoints = tuple(1 / variable - 1 for variable in variables)
    coeff = _constraint_coefficients()
    constraint = sp.zeros(4, 10)
    adjoint = sp.zeros(10, 4)
    for nu in range(4):
        for component in range(10):
            constraint[nu, component] = sum(
                coeff[nu][component][axis] * differences[axis]
                for axis in range(3)
            )
            adjoint[component, nu] = sum(
                coeff[nu][component][axis] * adjoints[axis]
                for axis in range(3)
            )
    dagger_product = (adjoint * constraint).applyfunc(sp.expand)
    product_support: set[tuple[int, ...]] = set()
    for value in dagger_product:
        product_support.update(
            tuple(row) for row in _laurent_support(value, variables)
        )
    involuted_constraint = constraint.T.xreplace(
        {variable: 1 / variable for variable in variables}
    )
    if not _zero_matrix(adjoint - involuted_constraint):
        raise AssertionError("fixed Laurent adjoint reconstruction failed")

    # The actual constraint-coupled potential block has C†C and paired C/C†
    # off-diagonal blocks.  Its Laurent involution is therefore Hermitian.
    potential = sp.zeros(14)
    potential[:10, :10] = sp.eye(10) + dagger_product / 16
    potential[:10, 10:14] = -adjoint / 4
    potential[10:14, :10] = -constraint / 4
    potential[10:14, 10:14] = sp.eye(4) * 2
    involution = potential.T.xreplace(
        {variable: 1 / variable for variable in variables}
    )
    if not _zero_matrix(potential - involution):
        raise AssertionError("fixed potential is not Laurent-Hermitian")
    return {
        "forward_difference_support": {
            VARIABLE_ORDER[axis]: _laurent_support(differences[axis], variables)
            for axis in range(3)
        },
        "adjoint_difference_support": {
            VARIABLE_ORDER[axis]: _laurent_support(adjoints[axis], variables)
            for axis in range(3)
        },
        "c_dagger_c_support": [list(row) for row in sorted(product_support)],
        "adjoint_residual": "0",
        "potential_hermitian_residual": "0",
        "potential_scope": (
            "constraint_coupling_block_only;"
            "q_dependent_diagonal_stiffness_excluded"
        ),
    }


def _symplectic_claim() -> dict[str, object]:
    # Bind the compact symplectic check mechanically to the actual C†C
    # potential: evaluate its Laurent variables on a frozen unit-torus point
    # and select the coupled (h02,zeta0) principal block.
    values = (-1, sp.I, 1)
    differences = tuple(value - 1 for value in values)
    coeff = _constraint_coefficients()
    constraint = sp.zeros(4, 10)
    for nu in range(4):
        for component in range(10):
            constraint[nu, component] = sum(
                coeff[nu][component][axis] * differences[axis]
                for axis in range(3)
            )
    full_potential = sp.zeros(14)
    full_potential[:10, :10] = (
        sp.eye(10) + constraint.conjugate().T * constraint / 16
    )
    full_potential[:10, 10:14] = -constraint.conjugate().T / 4
    full_potential[10:14, :10] = -constraint / 4
    full_potential[10:14, 10:14] = sp.eye(4) * 2
    potential = full_potential.extract((2, 10), (2, 10))
    if potential[0, 1] == 0:
        raise AssertionError("frozen actual-potential subblock lost its coupling")
    real = sp.Matrix.vstack(
        sp.Matrix.hstack(sp.re(potential), -sp.im(potential)),
        sp.Matrix.hstack(sp.im(potential), sp.re(potential)),
    )
    if real != real.T:
        raise AssertionError("Hermitian realification is not symmetric")
    dimension = real.rows
    identity = sp.eye(dimension)
    zero = sp.zeros(dimension)
    tau = sp.Rational(1, 3)
    kick = sp.Matrix.vstack(
        sp.Matrix.hstack(identity, zero),
        sp.Matrix.hstack(-tau * real / 2, identity),
    )
    drift = sp.Matrix.vstack(
        sp.Matrix.hstack(identity, tau * identity),
        sp.Matrix.hstack(zero, identity),
    )
    macro = kick * drift * kick
    canonical = sp.Matrix.vstack(
        sp.Matrix.hstack(zero, identity),
        sp.Matrix.hstack(-identity, zero),
    )
    residual = (macro.T * canonical * macro - canonical).applyfunc(sp.simplify)
    if not _zero_matrix(residual):
        raise AssertionError("fixed Verlet representative is not symplectic")
    return {
        "realification_dimension": 4,
        "verlet_phase_dimension": 8,
        "half_step": "1/6",
        "potential_symmetry_residual": "0",
        "residual": "0",
        "scope": (
            "constraint_coupling_block_h02_zeta0_principal_subblock;"
            "q_dependent_diagonal_stiffness_excluded"
        ),
        "laurent_evaluation": ["-1", "I", "1"],
        "principal_indices": [2, 10],
    }


def _direction_claim(
    name: str,
    direction: tuple[int, int, int],
    witness_columns: tuple[int, ...],
) -> dict[str, object]:
    reference_kappa = _reference_kappa(direction)
    m = sum(value * value for value in direction)
    # Every incidence entry is quadratic in kappa.  Remove the common
    # a=sqrt(2-sqrt(2)) while doing subspace algebra, then restore a^12 in
    # the 6x6 witness determinant.  This is exact, not a numerical rescale.
    kappa = sp.Matrix([sp.sqrt(m), *direction])
    incidence = _incidence(kappa)
    _, pivot_columns = incidence.rref()
    if tuple(pivot_columns) != witness_columns:
        raise AssertionError(f"{name}: RREF pivots differ from canonical witness")
    witness = incidence.extract(WITNESS_ROWS, witness_columns)
    minor = sp.factor(witness.det() * (2 - sp.sqrt(2)) ** 6)
    rank = incidence.rank()
    gauge = _r15_gauge_then_r32_trace_reverse(kappa)
    tt = _tt_basis(direction)
    pi_phys = sp.eye(10) - _gram_projector(gauge)
    quotient_tt = (pi_phys * tt).applyfunc(sp.simplify)
    dressing = sp.Matrix(
        [[sp.Rational((row + 1) * (col + 2), 17) for col in range(2)] for row in range(4)]
    )
    if not _zero_matrix(pi_phys * gauge):
        raise AssertionError(f"{name}: physical projector does not kill gauge")
    if not _zero_matrix(pi_phys * (tt + gauge * dressing) - quotient_tt):
        raise AssertionError(f"{name}: quotient dressing is not invariant")
    if quotient_tt.rank() != 2:
        raise AssertionError(f"{name}: wrong physical quotient dimension")
    if not _zero_matrix(incidence * gauge):
        raise AssertionError(f"{name}: gauge is not in incidence kernel")

    b = incidence.T[:, list(WITNESS_ROWS)]
    if not _zero_matrix(gauge.T.conjugate() * quotient_tt):
        raise AssertionError(f"{name}: physical TT is not orthogonal to gauge")
    k_sector = gauge.row_join(quotient_tt)
    k_sector_rank = k_sector.rank()
    if k_sector_rank != 6:
        raise AssertionError(f"{name}: physical ker-sector rank is not six")
    row_complement_dimension = 10 - k_sector_rank
    if row_complement_dimension != 4:
        raise AssertionError(f"{name}: row complement dimension is not four")
    p_b = _gram_projector(b)
    p_k = _gram_projector(k_sector)
    for label, projector in (("P_B", p_b), ("P_K", p_k)):
        if not _zero_matrix(projector.T.conjugate() - projector):
            raise AssertionError(f"{name}: {label} is not Hermitian")
        if not _zero_matrix(projector * projector - projector):
            raise AssertionError(f"{name}: {label} is not idempotent")

    restricted = (
        (b.T.conjugate() * b).inv()
        * b.T.conjugate()
        * (sp.eye(10) - p_k)
        * b
    ).applyfunc(sp.simplify)
    x = sp.Symbol("x")
    characteristic = sp.factor(restricted.charpoly(x).as_expr())
    expected_characteristic = x**2 * (x - 1) ** 4
    if sp.simplify(
        sp.sqrtdenest(characteristic - expected_characteristic)
    ) != 0:
        raise AssertionError(f"{name}: unexpected squared-sine spectrum")

    expected_reference = sp.factor(m * (2 - sp.sqrt(2)))
    reference = sp.factor(
        sum(value * value for value in reference_kappa[1:])
    )
    if sp.simplify(reference - expected_reference) != 0:
        raise AssertionError(f"{name}: bad reference incidence scale")
    rho = sp.Symbol("rho", positive=True)
    nu = 4 * sum(sp.sin(rho * value / 2) ** 2 for value in direction)
    ir_limit = sp.limit(nu / rho**2, rho, 0)
    if ir_limit != m:
        raise AssertionError(f"{name}: bad punctured IR scale")
    domain = sp.Interval.Lopen(0, sp.pi)
    active_components = tuple(value for value in direction if value != 0)
    binary_direction = all(value in (0, 1) for value in direction)
    factored_identity = sp.simplify(
        nu - 4 * len(active_components) * sp.sin(rho / 2) ** 2
    ) == 0
    zero_set = sp.solveset(sp.sin(rho / 2), rho, domain=domain)
    positive_on_domain = bool(
        binary_direction
        and active_components
        and factored_identity
        and zero_set == sp.EmptySet
    )
    if not positive_on_domain:
        raise AssertionError(f"{name}: nu positivity was not mechanically certified")

    return {
        "direction": name,
        "vector": list(direction),
        "k_domain": "0<rho<=pi (first-Brillouin punctured ray)",
        "reference_ratio": [1, 8],
        "reference_kappa": [_expr_text(value) for value in reference_kappa],
        "rank": rank,
        "pivot_columns": list(pivot_columns),
        "witness_rows": list(WITNESS_ROWS),
        "witness_columns": list(witness_columns),
        "minor": _expr_text(minor),
        "gauge_dimension": gauge.rank(),
        "physical_quotient_dimension": quotient_tt.rank(),
        "gauge_t_phys_orthogonality_residual": "0",
        "k_sector_rank": k_sector_rank,
        "row_complement_dimension": row_complement_dimension,
        "pi_phys_gauge_residual": "0",
        "quotient_dressing_residual": "0",
        "p_b_hermitian_residual": "0",
        "p_b_idempotence_residual": "0",
        "p_k_hermitian_residual": "0",
        "p_k_idempotence_residual": "0",
        "squared_sine_charpoly": "x^2*(x-1)^4",
        "squared_sine_multiset": [0, 0, 1, 1, 1, 1],
        "whitened_coisometry_required": True,
        "nu_definition": "4*sum_i(sin(rho*d_i/2)^2)",
        "nu_reference_value": _expr_text(expected_reference),
        "nu_ir_limit": int(ir_limit),
        "nu_order": 2,
        "nu_active_component_count": len(active_components),
        "nu_zero_set_on_domain": str(zero_set),
        "nu_positive_on_domain": positive_on_domain,
        "nu_claim_scope": "punctured_pointwise_second_order_analytic_scale",
        "laurent_divisibility_claimed": False,
    }


@lru_cache(maxsize=1)
def _exact_profile_cached() -> dict[str, object]:
    profile: dict[str, object] = {
        "schema": "v3m0-exact-v1",
        "variable_order": list(VARIABLE_ORDER),
        "packing": list(PACKING),
        "curvature_row_order": "R[m,a,n,b] C-order flatten",
        "laurent": _laurent_claim(),
        "symplectic": _symplectic_claim(),
        "directions": [
            _direction_claim(name, direction, columns)
            for name, direction, columns in DIRECTION_SPECS
        ],
    }
    return _json_snapshot(profile)


def exact_profile() -> dict[str, object]:
    """Build an independently mutable snapshot of the frozen exact profile."""

    return _json_snapshot(_exact_profile_cached())


def _validate_full_schema(snapshot: dict[str, Any]) -> None:
    keys = frozenset(snapshot)
    if keys != TOP_LEVEL_FIELDS:
        unknown = sorted(keys - TOP_LEVEL_FIELDS)
        missing = sorted(TOP_LEVEL_FIELDS - keys)
        raise ValueError(f"top-level schema mismatch; unknown={unknown}, missing={missing}")
    exact = snapshot["exact"]
    if not isinstance(exact, dict):
        raise TypeError("exact must be a mapping")
    expected_exact = exact_profile()
    if exact != expected_exact:
        raise ValueError("exact reconstruction mismatch")
    environment = snapshot["environment"]
    if not isinstance(environment, dict) or set(environment) != ENVIRONMENT_FIELDS:
        raise ValueError("environment schema mismatch")
    if environment["attribution_only"] is not True:
        raise ValueError("environment schema requires attribution_only=true")
    if environment["cross_platform_bit_identical_required"] is not False:
        raise ValueError(
            "environment schema forbids a cross-platform bit-identity gate"
        )
    numpy_build = environment["numpy_build"]
    if not isinstance(numpy_build, dict):
        raise ValueError("environment schema requires a NumPy build mapping")
    if environment["numpy_build_config_sha256"] != canonical_sha(numpy_build):
        raise ValueError("environment NumPy build digest mismatch")


def verify_exact_certificate(cert: Mapping[str, object]) -> None:
    """Verify one complete Phase-0 certificate by independent reconstruction."""

    if not isinstance(cert, Mapping):
        raise TypeError("certificate must be a mapping")
    snapshot = _json_snapshot(cert)
    if not isinstance(snapshot, dict):
        raise TypeError("certificate must normalize to a mapping")
    _validate_full_schema(snapshot)
    claimed_sha = snapshot["certificate_sha"]
    if not isinstance(claimed_sha, str):
        raise TypeError("certificate_sha must be a string")
    body = {key: value for key, value in snapshot.items() if key != "certificate_sha"}
    if claimed_sha != canonical_sha(body):
        raise ValueError("certificate_sha mismatch")
    if snapshot["evidence_kind"] != "source_sha_static_symbol_reconstruction":
        raise ValueError("evidence_kind exceeds the frozen claim")
    for field in (
        "raw_kernel_available",
        "raw_kernel_recomputed",
        "raw_kernel_independent_recomputation",
    ):
        if snapshot[field] is not False:
            raise ValueError(f"{field} must remain false")
    if snapshot["production_symbol_equivalence"] != "round0_plane_wave_spotcheck":
        raise ValueError("production_symbol_equivalence mismatch")
    if snapshot["claim_ceiling"] != "conditional_full_positive_observer_collapse":
        raise ValueError("claim_ceiling mismatch")
    parent = snapshot["parent"]
    if not isinstance(parent, dict) or set(parent) != {
        "path",
        "sha256",
        "manifest_sha256",
        "status",
        "raw_kernel_persisted",
    }:
        raise ValueError("parent schema mismatch")
    parent_path_value = parent["path"]
    if type(parent_path_value) is not str or not parent_path_value:
        raise ValueError("parent path mismatch")
    from pathlib import Path
    from experiments.v3m0_formal_nogo import (
        ROOT,
        _load_json,
        _rebuild_phase0_body,
        _verify_static_execution_closure,
    )

    parent_path = (ROOT / parent_path_value).resolve()
    if ROOT.resolve() not in parent_path.parents:
        raise ValueError("parent path must remain inside the repository")
    lineage = snapshot["lineage"]
    if not isinstance(lineage, dict):
        raise ValueError("lineage schema mismatch")
    recorded_closure = lineage.get("static_execution_closure")
    expected_closure = _verify_static_execution_closure(_load_json(parent_path))
    if recorded_closure != expected_closure:
        raise ValueError("static execution closure mismatch")
    expected_body = _rebuild_phase0_body(parent_path)
    if body != expected_body:
        raise ValueError("certificate evidence differs from independent reconstruction")


__all__ = ["exact_profile", "verify_exact_certificate"]
