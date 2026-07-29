"""Runtime-output evaluator for the M3′ 30-cell real-space pilot."""

from __future__ import annotations

import hashlib
import math
from fractions import Fraction
import time

import numpy as np

from . import epsilon as EPS
from . import frozen as FROZEN
from . import invariants as INV
from . import m3_family as FAMILY
from . import m3_local_family as LOCAL


N_CHANNELS = 28
IMPULSE_L = 17
SUPPORT_RELATIVE_THRESHOLD = 1e-13
FLOQUET_MODULUS_TOL = 1e-10
PHASE_ZERO_TOL = 1e-9
SIGMA_TEETH_ABSOLUTE_MARGIN = 1e-8
DIRECTIONS = {
    "axial": (1, 0, 0),
    "face-diagonal": (1, 1, 0),
    "body-diagonal": (1, 1, 1),
}


def _flat_output(state: LOCAL.LocalFamilyState) -> np.ndarray:
    return np.concatenate((state.h, state.zeta, state.p_h, state.p_zeta))


def _excite_channel(
    state: LOCAL.LocalFamilyState,
    channel: int,
    center: int,
) -> None:
    if not 0 <= channel < N_CHANNELS:
        raise ValueError(f"channel must be in 0..{N_CHANNELS - 1}")
    if channel < 10:
        field, local_channel = state.h, channel
    elif channel < 14:
        field, local_channel = state.zeta, channel - 10
    elif channel < 24:
        field, local_channel = state.p_h, channel - 14
    else:
        field, local_channel = state.p_zeta, channel - 24
    field[local_channel, center, center, center] = 1.0


def _kernel_support_radius(kernel: np.ndarray, center: int) -> int:
    magnitude = np.max(np.abs(kernel), axis=(0, 1))
    peak = float(np.max(magnitude))
    if peak == 0.0:
        return 0
    active = np.argwhere(magnitude > SUPPORT_RELATIVE_THRESHOLD * peak)
    L = magnitude.shape[0]
    radius = 0
    for coordinate in active:
        periodic_distances = [
            min(abs(int(value) - center), L - abs(int(value) - center))
            for value in coordinate
        ]
        radius = max(radius, max(periodic_distances))
    return radius


def measure_impulse_kernel(
    q: int,
    kappa_c: float,
    L: int = IMPULSE_L,
) -> dict[str, object]:
    """Run 28 canonical delta inputs through the production real-space step."""

    if L % 2 != 1:
        raise ValueError("impulse lattice must be odd so it has one center")
    center = L // 2
    step = LOCAL.realspace_step_factory(q, kappa_c)
    kernel = np.empty(
        (N_CHANNELS, N_CHANNELS, L, L, L),
        dtype=np.complex128,
    )
    for input_channel in range(N_CHANNELS):
        state = LOCAL.LocalFamilyState.zeros(L)
        _excite_channel(state, input_channel, center)
        kernel[:, input_channel] = _flat_output(step(state))
    contiguous = np.ascontiguousarray(kernel)
    return {
        "q": q,
        "kappa_c": kappa_c,
        "L": L,
        "center": center,
        "realspace_runs": N_CHANNELS,
        "kernel": kernel,
        "kernel_sha256": hashlib.sha256(contiguous.view(np.uint8)).hexdigest(),
        "support_radius": _kernel_support_radius(kernel, center),
        "relative_support_threshold": SUPPORT_RELATIVE_THRESHOLD,
    }


def kernel_matrix_at_k(
    kernel: np.ndarray,
    k: tuple[float, float, float] | np.ndarray,
) -> np.ndarray:
    """Evaluate the symbol of a measured centered impulse response."""

    if kernel.ndim != 5 or kernel.shape[:2] != (N_CHANNELS, N_CHANNELS):
        raise ValueError("kernel must have shape (28,28,L,L,L)")
    L = kernel.shape[2]
    if kernel.shape[2:] != (L, L, L) or L % 2 != 1:
        raise ValueError("kernel must live on one odd cubic lattice")
    center = L // 2
    offsets = np.arange(L, dtype=float) - center
    phase = np.exp(
        -1j
        * (
            float(k[0]) * offsets[:, None, None]
            + float(k[1]) * offsets[None, :, None]
            + float(k[2]) * offsets[None, None, :]
        )
    )
    with np.errstate(all="ignore"):
        matrix = np.einsum("oixyz,xyz->oi", kernel, phase, optimize=True)
    if not np.isfinite(matrix).all():
        raise FloatingPointError("non-finite measured kernel transform")
    return matrix


def _geometry_at_k(
    k: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    r15 = FROZEN.mod("r15_walk_dedonder")
    r32 = FROZEN.mod("r32_reachability_probe")
    placed = r15.kappa_placed(k, LOCAL.C_CONE)
    if placed is None:
        raise ValueError("k lies outside the frozen placed shell")
    q_tt, q_gauge, _ = r32.build_sectors(placed)
    q_ker_c = INV.orth(np.column_stack((q_tt, q_gauge)))
    return q_tt, q_ker_c, r32.inc_matrix(placed)


def _curvature_measurement(
    h_span: np.ndarray,
    q_tt: np.ndarray,
    q_ker_c: np.ndarray,
    incidence: np.ndarray,
) -> dict[str, object]:
    h_basis = INV.orth(h_span)
    if h_basis.shape[1] == 0:
        raise ValueError("positive Floquet branch has no physical-h support")
    with np.errstate(all="ignore"):
        curvature_images = incidence @ h_basis
    if not np.isfinite(curvature_images).all():
        raise FloatingPointError("non-finite curvature image")
    _, singular_values, vh = np.linalg.svd(
        curvature_images,
        full_matrices=False,
    )
    if singular_values.size == 0 or singular_values[0] <= 1e-300:
        raise ValueError("positive Floquet branch carries no curvature")
    normalized = singular_values / singular_values[0]
    n_curv = int(np.sum(normalized >= INV.SIN_THRESH))
    if n_curv <= 0:
        raise ValueError("curvature rank is zero")
    s_curv = INV.orth(h_basis @ vh.conj().T[:, :n_curv])
    invariants = INV.subspace_invariants(s_curv, q_ker_c)
    j_hand = int(invariants["n_ge_thresh"])
    epsilon_geo = EPS.epsilon_dof(j_hand, n_curv)
    epsilon_e = float(
        np.mean(np.linalg.norm(q_tt.conj().T @ s_curv, axis=0) ** 2)
    )
    return {
        "S_curv": s_curv,
        "N_curv": n_curv,
        "curvature_singular_values_normalized": [
            float(value) for value in normalized
        ],
        "invariants": invariants,
        "j_hand_invariant": j_hand,
        "epsilon_geo": epsilon_geo,
        "epsilon_E_diagnostic": epsilon_e,
    }


def _invariant_drift(left: dict, right: dict) -> float:
    left_sines = np.asarray(left["sin_theta"], dtype=float)
    right_sines = np.asarray(right["sin_theta"], dtype=float)
    if left_sines.shape != right_sines.shape:
        return float("inf")
    drift = float(np.max(np.abs(left_sines - right_sines)))
    for key in ("max_sin_theta", "frob_leak", "rms_sin"):
        drift = max(drift, abs(float(left[key]) - float(right[key])))
    if left["n_ge_thresh"] != right["n_ge_thresh"]:
        return float("inf")
    return drift


def evaluate_measured_kernel(
    kernel: np.ndarray,
    k: tuple[float, float, float] | np.ndarray,
) -> dict[str, object]:
    """Measure one Floquet-shell point solely from a real-space output kernel."""

    k_array = np.asarray(k, dtype=float)
    if k_array.shape != (3,) or not np.isfinite(k_array).all():
        raise ValueError("k must be one finite three-vector")
    if float(np.linalg.norm(k_array)) <= 0.0:
        raise ValueError("the pilot does not judge k=0")
    measured_matrix = kernel_matrix_at_k(kernel, k_array)
    with np.errstate(all="ignore"):
        eigenvalues, eigenvectors = np.linalg.eig(measured_matrix)
    if not np.isfinite(eigenvalues).all() or not np.isfinite(eigenvectors).all():
        raise FloatingPointError("non-finite measured Floquet eigensystem")
    phases = np.angle(eigenvalues)
    positive = phases > PHASE_ZERO_TOL
    negative = phases < -PHASE_ZERO_TOL
    modulus_error = np.abs(np.abs(eigenvalues) - 1.0)
    max_modulus_error = float(np.max(modulus_error))

    q_tt, q_ker_c, incidence = _geometry_at_k(k_array)
    raw_h = eigenvectors[:10, positive]
    h_basis = INV.orth(raw_h)
    base = _curvature_measurement(h_basis, q_tt, q_ker_c, incidence)

    drifts: list[float] = []
    j_per_seed: list[int] = []
    for seed in INV.ROT_SEEDS:
        with np.errstate(all="ignore"):
            rotated_raw_h = INV.rotate_within_clusters(
                raw_h,
                phases[positive],
                seed,
            )
        rotated = _curvature_measurement(
            INV.orth(rotated_raw_h),
            q_tt,
            q_ker_c,
            incidence,
        )
        drifts.append(
            _invariant_drift(base["invariants"], rotated["invariants"])
        )
        j_per_seed.append(int(rotated["j_hand_invariant"]))
    max_drift = float(max(drifts))
    j_stable = bool(
        all(value == base["j_hand_invariant"] for value in j_per_seed)
    )
    valid = bool(
        max_modulus_error <= FLOQUET_MODULUS_TOL
        and base["N_curv"] > 0
        and max_drift <= INV.DRIFT_TOL
        and j_stable
    )
    return {
        "k": [float(value) for value in k_array],
        "valid": valid,
        "floquet": {
            "n_modes": int(eigenvalues.size),
            "n_positive": int(np.sum(positive)),
            "n_negative": int(np.sum(negative)),
            "n_zero_phase": int(np.sum(~positive & ~negative)),
            "max_modulus_error": max_modulus_error,
            "modulus_tolerance": FLOQUET_MODULUS_TOL,
        },
        "positive_h_span_dimension": int(h_basis.shape[1]),
        "N_curv": int(base["N_curv"]),
        "curvature_singular_values_normalized": base[
            "curvature_singular_values_normalized"
        ],
        "invariants": base["invariants"],
        "j_hand_invariant": int(base["j_hand_invariant"]),
        "epsilon_geo": float(base["epsilon_geo"]),
        "epsilon_E_diagnostic": float(base["epsilon_E_diagnostic"]),
        "basis_robustness": {
            "kind": "raw-positive-Floquet-phase-cluster-unitary-rotation",
            "seeds": list(INV.ROT_SEEDS),
            "drift_per_seed": drifts,
            "max_drift": max_drift,
            "j_per_seed": j_per_seed,
            "j_stable": j_stable,
            "drift_tolerance": INV.DRIFT_TOL,
        },
    }


def collect_direction_from_kernel(
    kernel: np.ndarray,
    direction_name: str,
    direction: tuple[int, int, int],
    lattices: tuple[int, ...] | list[int] | None = None,
) -> list[dict[str, object]]:
    """Measure one R37 ray from an already executed real-space kernel."""

    r37 = FROZEN.mod("r37_residual_scaling_audit")
    if lattices is None:
        lattices = list(r37.LATTICES)
    samples: dict[Fraction, dict[str, object]] = {}
    direction_array = np.asarray(direction, dtype=float)
    for L in lattices:
        n_max = int(r37.CTX_RATIO_MAX * L)
        for n in range(1, n_max + 1):
            ratio = Fraction(n, L)
            if ratio > r37.CTX_RATIO_MAX:
                continue
            if ratio in samples:
                samples[ratio]["provenance"].append([int(L), int(n)])
                continue
            component = 2.0 * math.pi * float(ratio)
            k = component * direction_array
            measured = evaluate_measured_kernel(kernel, k)
            invariants = measured["invariants"]
            samples[ratio] = {
                "direction": direction_name,
                "ratio": [ratio.numerator, ratio.denominator],
                "comp": component,
                "kabs": float(np.linalg.norm(k)),
                "provenance": [[int(L), int(n)]],
                "off_band": False,
                "valid": bool(measured["valid"]),
                "N_curv": int(measured["N_curv"]),
                "j_hand_invariant": int(measured["j_hand_invariant"]),
                "epsilon_geo": float(measured["epsilon_geo"]),
                "epsilon_E_diagnostic": float(
                    measured["epsilon_E_diagnostic"]
                ),
                "sin_theta": invariants["sin_theta"],
                "max_sin_theta": float(invariants["max_sin_theta"]),
                "frob_leak": float(invariants["frob_leak"]),
                "rms_sin": float(invariants["rms_sin"]),
                "n_ge_thresh": int(invariants["n_ge_thresh"]),
                "floquet_max_modulus_error": float(
                    measured["floquet"]["max_modulus_error"]
                ),
                "basis_max_drift": float(
                    measured["basis_robustness"]["max_drift"]
                ),
            }
    output: list[dict[str, object]] = []
    for ratio in sorted(samples):
        sample = samples[ratio]
        in_window = ratio <= r37.FIT_RATIO_MAX
        has_n_ge_two = any(n >= 2 for _, n in sample["provenance"])
        sample["in_fit_window"] = bool(in_window)
        sample["excluded_k0_neighbour"] = bool(
            in_window and not has_n_ge_two
        )
        sample["in_fit"] = bool(
            in_window
            and has_n_ge_two
            and not sample["off_band"]
            and sample["valid"]
        )
        output.append(sample)
    return output


def _fit_pair(
    x: np.ndarray,
    y: np.ndarray,
) -> tuple[dict, dict, float]:
    r37 = FROZEN.mod("r37_residual_scaling_audit")
    constant = r37.fit_constant(x, y)
    power = r37.fit_power(x, y)
    return constant, power, float(constant["AIC"] - power["AIC"])


def judge_direction_full(
    direction_name: str,
    points: list[dict[str, object]],
    y_key: str = "max_sin_theta",
) -> dict[str, object]:
    """Apply the frozen R37 fit plus LOO and widened-window diagnostics."""

    r37 = FROZEN.mod("r37_residual_scaling_audit")
    fit_points = [point for point in points if point["in_fit"]]
    if len(fit_points) < 4:
        raise ValueError("R37 power fit requires at least four valid points")
    x = np.asarray([point["kabs"] for point in fit_points], dtype=float)
    y = np.asarray([point[y_key] for point in fit_points], dtype=float)
    constant, power, delta_aic = _fit_pair(x, y)
    winner = power if power["AIC"] < constant["AIC"] else constant
    decisive = bool(abs(delta_aic) >= r37.DAIC_DECISIVE)
    pass_direction = bool(
        winner is power
        and decisive
        and power["alpha"] > 0.0
        and abs(power["A"]) <= 2.0 * power["sigma_A"]
    )
    fail_direction = bool(
        abs(winner["A"]) >= r37.A_O1_THRESH
        and abs(winner["A"]) > 2.0 * winner["sigma_A"]
    )
    verdict = (
        "FAIL"
        if fail_direction
        else ("PASS" if pass_direction else "ambiguous")
    )

    secondary_y = np.asarray(
        [point["rms_sin"] for point in fit_points],
        dtype=float,
    )
    secondary_constant, secondary_power, secondary_delta = _fit_pair(
        x,
        secondary_y,
    )

    loo_rows: list[dict[str, object]] = []
    for index in range(len(x)):
        lx = np.delete(x, index)
        ly = np.delete(y, index)
        _, loo_power, loo_delta = _fit_pair(lx, ly)
        loo_rows.append(
            {
                "dropped_kabs": float(x[index]),
                "A": float(loo_power["A"]),
                "sigma_A": float(loo_power["sigma_A"]),
                "alpha": float(loo_power["alpha"]),
                "sigma_alpha": float(loo_power["sigma_alpha"]),
                "dAIC_const_minus_power": loo_delta,
                "zero_consistent": bool(
                    abs(loo_power["A"]) <= 2.0 * loo_power["sigma_A"]
                ),
            }
        )

    widened_points = [
        point
        for point in points
        if point["in_fit_window"] and not point.get("off_band", False)
    ]
    widened_x = np.asarray(
        [point["kabs"] for point in widened_points],
        dtype=float,
    )
    widened_y = np.asarray(
        [point[y_key] for point in widened_points],
        dtype=float,
    )
    widened_constant, widened_power, widened_delta = _fit_pair(
        widened_x,
        widened_y,
    )
    return {
        "direction": direction_name,
        "y_observable": y_key,
        "n_fit_points": len(fit_points),
        "fit_kabs": [float(value) for value in x],
        "fit_y": [float(value) for value in y],
        "constant_model": constant,
        "power_model": power,
        "sigma": {
            "alpha": float(power["alpha"]),
            "sigma_alpha": float(power["sigma_alpha"]),
            "A": float(power["A"]),
            "sigma_A": float(power["sigma_A"]),
            "B": float(power["B"]),
            "dAIC_const_minus_power": delta_aic,
        },
        "winner": winner["model"],
        "decisive": decisive,
        "PASS_d": pass_direction,
        "FAIL_d": fail_direction,
        "verdict": verdict,
        "secondary_rms_sin": {
            "constant": secondary_constant,
            "power": secondary_power,
            "dAIC_const_minus_power": secondary_delta,
        },
        "loo": {
            "rows": loo_rows,
            "A_range": [
                min(row["A"] for row in loo_rows),
                max(row["A"] for row in loo_rows),
            ],
            "zero_consistent_all": bool(
                all(row["zero_consistent"] for row in loo_rows)
            ),
            "zero_flips": (
                f"{sum(not row['zero_consistent'] for row in loo_rows)}"
                f"/{len(loo_rows)}"
            ),
        },
        "widened_window_diagnostic": {
            "note": "纳入纯 n=1 点；仅诊断，永不判定",
            "n_points": len(widened_points),
            "constant": widened_constant,
            "power": widened_power,
            "dAIC_const_minus_power": widened_delta,
            "zero_consistent": bool(
                abs(widened_power["A"])
                <= 2.0 * widened_power["sigma_A"]
            ),
        },
    }


def _plane_wave_bridge_from_kernel(
    kernel: np.ndarray,
    q: int,
    kappa_c: float,
    L: int,
) -> dict[str, object]:
    k_units = np.asarray((1, 2, 3), dtype=float)
    k = 2.0 * math.pi * k_units / L
    seed = 260730 + 1000 * q + int(round(kappa_c * 1_000_000))
    rng = np.random.default_rng(seed)
    amplitude = rng.normal(size=N_CHANNELS)
    amplitude = amplitude + 1j * rng.normal(size=N_CHANNELS)
    coordinates = np.indices((L, L, L), dtype=float)
    phase = np.exp(1j * np.einsum("i,ixyz->xyz", k, coordinates))

    def field(values: np.ndarray) -> np.ndarray:
        return values[:, None, None, None] * phase[None, ...]

    state = LOCAL.LocalFamilyState(
        h=field(amplitude[:10]),
        zeta=field(amplitude[10:14]),
        p_h=field(amplitude[14:24]),
        p_zeta=field(amplitude[24:]),
    )
    stepped = LOCAL.realspace_step_factory(q, kappa_c)(state)
    direct = _flat_output(stepped)[:, 0, 0, 0]
    with np.errstate(all="ignore"):
        reconstructed = kernel_matrix_at_k(kernel, k) @ amplitude
    if not np.isfinite(reconstructed).all():
        raise FloatingPointError("non-finite kernel plane-wave reconstruction")
    residual = float(
        np.linalg.norm(direct - reconstructed)
        / max(float(np.linalg.norm(direct)), 1e-300)
    )
    return {
        "L": L,
        "k_units": [int(value) for value in k_units],
        "seed": seed,
        "relative_residual": residual,
        "pass": bool(residual <= 1e-12),
    }


def measure_cell(
    q: int,
    kappa_c: float,
    L: int = IMPULSE_L,
) -> dict[str, object]:
    """Execute one manifest cell and measure epsilon_geo and sigma afterward."""

    pilot_cell = FAMILY.PilotCell(q=q, kappa_c=kappa_c)
    started = time.perf_counter()
    impulse = measure_impulse_kernel(q=q, kappa_c=kappa_c, L=L)
    kernel = impulse["kernel"]
    bridge = _plane_wave_bridge_from_kernel(kernel, q, kappa_c, L)

    point_sets: dict[str, list[dict[str, object]]] = {}
    judges: dict[str, dict[str, object]] = {}
    epsilon_rows: dict[str, dict[str, object]] = {}
    for direction_name, direction in DIRECTIONS.items():
        points = collect_direction_from_kernel(
            kernel,
            direction_name,
            direction,
        )
        point_sets[direction_name] = points
        judges[direction_name] = judge_direction_full(direction_name, points)
        reference = next(
            point for point in points if point["ratio"] == [1, 8]
        )
        epsilon_rows[direction_name] = {
            "ratio": [1, 8],
            "N_curv": int(reference["N_curv"]),
            "j_hand_invariant": int(reference["j_hand_invariant"]),
            "epsilon_geo": float(reference["epsilon_geo"]),
            "epsilon_E_diagnostic": float(
                reference["epsilon_E_diagnostic"]
            ),
            "sin_theta": reference["sin_theta"],
        }

    all_points = [
        point for points in point_sets.values() for point in points
    ]
    epsilon_values = [
        row["epsilon_geo"] for row in epsilon_rows.values()
    ]
    signature = [
        {
            "direction": direction_name,
            "N_curv": row["N_curv"],
            "j_hand_invariant": row["j_hand_invariant"],
        }
        for direction_name, row in epsilon_rows.items()
    ]
    failures: list[str] = []
    if impulse["realspace_runs"] != N_CHANNELS:
        failures.append("wrong_delta_run_count")
    if impulse["support_radius"] > LOCAL.DECLARED_COMPOSITION_RADIUS:
        failures.append("support_radius_exceeded")
    if not bridge["pass"]:
        failures.append("kernel_plane_bridge_failed")
    if not all(point["valid"] for point in all_points):
        failures.append("invalid_shell_measurement")
    if any(point["N_curv"] <= 0 for point in all_points):
        failures.append("empty_curvature_subspace")
    if max(point["basis_max_drift"] for point in all_points) > INV.DRIFT_TOL:
        failures.append("basis_invariant_drift")
    max_modulus_error = max(
        point["floquet_max_modulus_error"] for point in all_points
    )
    if max_modulus_error > FLOQUET_MODULUS_TOL:
        failures.append("floquet_modulus_error")

    sigma_by_direction = {
        name: {
            **judge["sigma"],
            "winner": judge["winner"],
            "decisive": judge["decisive"],
            "verdict": judge["verdict"],
        }
        for name, judge in judges.items()
    }
    elapsed = time.perf_counter() - started
    return {
        "cell_id": pilot_cell.cell_id,
        "construction": {"q": q, "kappa_c": kappa_c},
        "fixed": {
            "eta": pilot_cell.eta,
            "matter_epsilon": pilot_cell.matter_epsilon_fixed,
        },
        "valid": not failures,
        "failures": failures,
        "coordinates": {
            "epsilon_geo": {
                "by_direction": {
                    name: row["epsilon_geo"]
                    for name, row in epsilon_rows.items()
                },
                "min_max": [
                    float(min(epsilon_values)),
                    float(max(epsilon_values)),
                ],
            },
            "sigma": sigma_by_direction,
        },
        "epsilon_geo_by_direction": epsilon_rows,
        "epsilon_geo_min_max": [
            float(min(epsilon_values)),
            float(max(epsilon_values)),
        ],
        "epsilon_signature": signature,
        "sigma_by_direction": sigma_by_direction,
        "sigma_judges": judges,
        "shell_points": point_sets,
        "runtime": {
            "impulse_L": L,
            "delta_realspace_runs": int(impulse["realspace_runs"]),
            "validation_realspace_runs": 1,
            "kernel_shape": list(kernel.shape),
            "kernel_bytes": int(kernel.nbytes),
            "kernel_sha256": impulse["kernel_sha256"],
            "support_radius": int(impulse["support_radius"]),
            "support_relative_threshold": impulse[
                "relative_support_threshold"
            ],
            "plane_bridge_residual": bridge["relative_residual"],
            "plane_bridge": bridge,
            "max_floquet_modulus_error": float(max_modulus_error),
            "wall_seconds": float(elapsed),
        },
    }


def _epsilon_signature_key(cell: dict[str, object]) -> tuple:
    rows = {
        row["direction"]: (
            int(row["N_curv"]),
            int(row["j_hand_invariant"]),
        )
        for row in cell["epsilon_signature"]
    }
    return tuple((name, *rows[name]) for name in DIRECTIONS)


def _sigma_separation(
    cells: list[dict[str, object]],
) -> list[dict[str, object]]:
    witnesses: list[dict[str, object]] = []
    for direction in DIRECTIONS:
        for left_index, left in enumerate(cells):
            left_sigma = left["sigma_by_direction"][direction]
            left_low = left_sigma["A"] - 2.0 * left_sigma["sigma_A"]
            left_high = left_sigma["A"] + 2.0 * left_sigma["sigma_A"]
            left_loo = [
                row["A"]
                for row in left["sigma_judges"][direction]["loo"]["rows"]
            ]
            for right in cells[left_index + 1 :]:
                right_sigma = right["sigma_by_direction"][direction]
                right_low = right_sigma["A"] - 2.0 * right_sigma["sigma_A"]
                right_high = right_sigma["A"] + 2.0 * right_sigma["sigma_A"]
                right_loo = [
                    row["A"]
                    for row in right["sigma_judges"][direction]["loo"]["rows"]
                ]
                if right_low - left_high > SIGMA_TEETH_ABSOLUTE_MARGIN:
                    loo_gap = min(right_loo) - max(left_loo)
                    loo_order_stable = (
                        loo_gap > SIGMA_TEETH_ABSOLUTE_MARGIN
                    )
                    order = "left<right"
                elif left_low - right_high > SIGMA_TEETH_ABSOLUTE_MARGIN:
                    loo_gap = min(left_loo) - max(right_loo)
                    loo_order_stable = (
                        loo_gap > SIGMA_TEETH_ABSOLUTE_MARGIN
                    )
                    order = "right<left"
                else:
                    continue
                if loo_order_stable:
                    witnesses.append(
                        {
                            "direction": direction,
                            "left_cell": left["cell_id"],
                            "right_cell": right["cell_id"],
                            "left_interval_2sigma": [
                                float(left_low),
                                float(left_high),
                            ],
                            "right_interval_2sigma": [
                                float(right_low),
                                float(right_high),
                            ],
                            "loo_order": order,
                            "loo_minimum_gap": float(loo_gap),
                        }
                    )
    return witnesses


def assess_resolvability(
    cells: list[dict[str, object]],
    resource_review: dict[str, object],
) -> dict[str, object]:
    """Apply the preregistered pilot meta-criteria without unlocking a scan."""

    unique_ids = {cell.get("cell_id") for cell in cells}
    execution_valid = bool(
        len(cells) == 30
        and len(unique_ids) == 30
        and all(cell.get("valid") is True for cell in cells)
    )
    direction_complete = bool(
        all(
            set(cell.get("sigma_by_direction", {})) == set(DIRECTIONS)
            and set(cell.get("sigma_judges", {})) == set(DIRECTIONS)
            and {
                row.get("direction")
                for row in cell.get("epsilon_signature", [])
            }
            == set(DIRECTIONS)
            for cell in cells
        )
    )

    signatures = (
        {_epsilon_signature_key(cell) for cell in cells}
        if direction_complete
        else set()
    )
    epsilon_teeth = len(signatures) >= 2
    separation_witnesses = (
        _sigma_separation(cells) if direction_complete else []
    )
    sigma_teeth = bool(separation_witnesses)
    bracket_directions = []
    if direction_complete:
        for direction in DIRECTIONS:
            verdicts = {
                cell["sigma_by_direction"][direction]["verdict"]
                for cell in cells
            }
            if {"PASS", "FAIL"} <= verdicts:
                bracket_directions.append(direction)
    boundary_bracket = bool(bracket_directions)
    resource_pass = bool(
        resource_review.get("pass") is True
        and float(resource_review.get("margin_factor", 0.0)) >= 1.5
    )

    criteria = {
        "execution_validity": {
            "pass": execution_valid,
            "expected_cells": 30,
            "observed_cells": len(cells),
            "unique_cell_ids": len(unique_ids),
            "invalid_cells": [
                cell.get("cell_id")
                for cell in cells
                if cell.get("valid") is not True
            ],
        },
        "epsilon_counting_teeth": {
            "pass": epsilon_teeth,
            "unique_signature_count": len(signatures),
            "unique_signatures": [list(signature) for signature in signatures],
        },
        "sigma_continuous_teeth": {
            "pass": sigma_teeth,
            "absolute_margin_required": SIGMA_TEETH_ABSOLUTE_MARGIN,
            "witness_count": len(separation_witnesses),
            "witnesses": separation_witnesses,
        },
        "boundary_bracket_teeth": {
            "pass": boundary_bracket,
            "directions_with_PASS_and_FAIL": bracket_directions,
        },
        "direction_completeness": {
            "pass": direction_complete,
            "required_directions": list(DIRECTIONS),
        },
        "resource_margin": {
            "pass": resource_pass,
            "required_margin_factor": 1.5,
            "review": resource_review,
        },
    }
    if not execution_valid or not direction_complete:
        status = "HALT-PILOT-INVALID"
    elif all(row["pass"] for row in criteria.values()):
        status = "READY-FORMAL-PREREGISTRATION"
    else:
        status = "HALT-PILOT-UNRESOLVED"
    return {
        "status": status,
        "pilot_resolved": status == "READY-FORMAL-PREREGISTRATION",
        "formal_preregistration_unlocked": (
            status == "READY-FORMAL-PREREGISTRATION"
        ),
        "formal_scan_unlocked": False,
        "criteria": criteria,
        "wording": (
            "pilot 仅允许另行冻结正式预注册；本结果不授权正式扫描"
            if status == "READY-FORMAL-PREREGISTRATION"
            else "pilot 未形成可分辨边界；正式扫描保持锁定"
        ),
    }


__all__ = [
    "assess_resolvability",
    "collect_direction_from_kernel",
    "evaluate_measured_kernel",
    "judge_direction_full",
    "kernel_matrix_at_k",
    "measure_cell",
    "measure_impulse_kernel",
]
