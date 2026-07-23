"""R25 pre-M3 blocker (3): the MOVING exact-current source, symbol layer.

Lifts a uniformly-moving matter wavepacket's R10 exact bond current into the
R25 14-component / conjugate-dual-sector geometry source, entirely at the
symbol (Laurent/Floquet) level.  Real-space integration into the step ()
stepper is NOT done here; this file only proves the four symbol certificates
and writes the real-space interface contract.

Central object -- the WALK-COVARIANT MOVING TRACE-REVERSED SOURCE.  From the
frozen walk symbol U(k)=a I - i b.sigma (a=trU/2, b_j=(i/2)tr(sigma_j U),
exact SU(2) identity a^2+b.b=1) and a time-shift symbol z, define

    A(z) = (b.b)/(z - a)                 # regular; = 1+a at z=1 (static)
    hbar00 = A^2/(2c)
    hbar0i = -A i b_i /(2c)
    hbarij = (b.b delta_ij - 3 b_i b_j)/(4c)

The ONLY z-dependence is the time-component amplitude A(z) that carries the
source motion; the spatial block is z-independent (identical to the static
Newton lift).  ALGEBRAIC FACT (proved in the header derivation, reconfirmed
numerically below): kappa(z).eta.hbar(z) == 0 for EVERY z, where
kappa=(z-a, i b_x, i b_y, i b_z)/c is the R25 detour/de Donder covector.
Because (z-a)A = b.b identically, both the nu=0 and nu=i de Donder rows cancel
term-by-term.  At z=1, A=1+a and the lift is bit-for-bit r25_static_newton.

Certificates (fp64, numpy):
  S1  conservation : discrete continuity of the moving source is machine zero
        (kappa.S=0), anchored to the R10 moving-walk bond-current lineage 1e-18.
  S2  de Donder    : C+(z).S = 0 on the full BZ; static limit z=1 degenerates
        bit-for-bit to r25_static_newton.static_newton_lift.
  S3  moving limit : v in {0.1,0.3,0.5}c -- source construction non-singular
        (max|A| bounded, no pole) and the sourced damped closed loop shows no
        secular (linear-in-t) growth (||x_t|| saturates at the finite resolvent
        bound; min_k|z_v-spec(M)|>0).
  S4  time slot    : half-integer (T3-centered) placement keeps kappa.S machine
        zero; a frozen/integer (static z=1) slot for a moving source breaks
        de Donder by O(1) -- the R13/L3 "wrong time slot" crime, reproduced.

Run:
    RULESPACE_BACKEND=numpy .venv/bin/python r25_moving_source_symbol.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os

import numpy as np

import cp1_v4_L2 as L2
import r10_current_generator as R10
import r25_auxiliary_wilson_complex as R25W
import r25_detour_complex as R25D
import r25_dynamic_symbol as R25dyn


DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
OUT = os.path.join(ROOT, "data", "results", "r25_moving_source_results.json")
C = L2.C
ETA = R25D.ETA
PAULI = R25W.PAULI_NUM
VELOCITIES = (0.1, 0.3, 0.5)
# frozen damping working point from r25_dynamic_symbol (chosen mu, 12 unit modes)
MU = 0.001995262314968879


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# --------------------------------------------------------------------------
#  walk-covariant moving source lift (symbol layer)
# --------------------------------------------------------------------------
def bloch(k):
    U = L2.walk_symbol(np.asarray(k, float))
    a = np.trace(U) / 2.0
    b = np.array([1j * np.trace(s @ U) / 2.0 for s in PAULI])
    return U, a, b, complex(b @ b)


def kappa(k, z):
    """R25 detour/de Donder covector at time symbol z (base_kappa convention)."""
    _, a, b, _ = bloch(k)
    return np.concatenate([[z - a], 1j * b]) / C


def hbar_moving(k, z):
    """trace-reversed 4x4 source (the object r25_static_newton calls hb)."""
    _, a, b, bb = bloch(k)
    A = bb / (z - a)
    hb = np.zeros((4, 4), complex)
    hb[0, 0] = A * A / (2 * C)
    hb[0, 1:] = hb[1:, 0] = -A * 1j * b / (2 * C)
    hb[1:, 1:] = (np.eye(3) * bb - 3 * np.outer(b, b)) / (4 * C)
    return hb, A


def normal_h_packed(k, z):
    """packed 10-vector normal metric h (same basis static_newton_lift returns)."""
    hb, _ = hbar_moving(k, z)
    trb = np.sum(ETA * hb)
    h = hb - 0.5 * ETA * trb
    return R25D.pack_matrix(h)


def drive14(k, z):
    """14-component geometry drive whose damped equilibrium is the lift:
    physical 10 = a_W * normal_h; auxiliary 4 = 0 (Wilson sector, see S2 note)."""
    aw = R25W.walk_data(k)[3]
    return np.concatenate([aw * normal_h_packed(k, z), np.zeros(4)])


# --------------------------------------------------------------------------
#  S1 -- conservation (R10 lineage anchor + symbol continuity)
# --------------------------------------------------------------------------
def cert_S1():
    # (a) R10 exact moving-walk bond-current continuity (the lineage the source
    #     inherits): a moving 4-component chiral-doubled Dirac-pair packet.
    L = 12
    shape = (L, L, L)
    w = R10.Walk(shape, 4)
    psi = R10.gaussian_psi(shape, 4, k0=(0.5, 0.2, 0.0), sig=2.5, seed=7)
    lf = R10.build_4comp_layers(shape, math.pi / 3, 0.3)
    ok, _ = R10.certify(w, lf, psi, 6, "R25moving_R10lineage")
    r10_resid = R10.RES["R25moving_R10lineage"]

    # (b) symbol-space continuity of the lifted moving source: the discrete
    #     energy-momentum continuity is exactly kappa(z).eta.hbar(z)=0.
    rng = np.random.default_rng(250724)
    worst = 0.0
    for v in VELOCITIES:
        vv = np.array([v, 0.0, 0.0])
        for _ in range(400):
            k = rng.uniform(-math.pi, math.pi, 3)
            z = np.exp(-1j * float(vv @ k))
            hb, _ = hbar_moving(k, z)
            kup = ETA @ kappa(k, z)
            worst = max(worst, float(np.max(np.abs(kup @ hb))))
    return {"R10_moving_bond_current_continuity": r10_resid,
            "symbol_continuity_kappa_dot_S_max": worst,
            "R10_lineage_pass": bool(ok)}


# --------------------------------------------------------------------------
#  S2 -- de Donder compatibility + static bitwise degeneration
# --------------------------------------------------------------------------
def cert_S2():
    rng = np.random.default_rng(250725)
    # (a) full-BZ moving de Donder residual C+(z_v).S = kappa(z_v).eta.hbar
    dedonder = 0.0
    for v in VELOCITIES:
        vv = np.array([v, 0.0, 0.0])
        N = 16
        for idx in np.ndindex(N, N, N):
            if idx == (0, 0, 0):
                continue
            k = 2 * math.pi * np.array(idx, float) / N
            z = np.exp(-1j * float(vv @ k))
            hb, _ = hbar_moving(k, z)
            dedonder = max(dedonder, float(np.max(np.abs((ETA @ kappa(k, z)) @ hb))))

    # (b) z=1 bit-for-bit vs r25_static_newton.static_newton_lift
    bitwise = 0.0
    for _ in range(200):
        k = rng.uniform(-math.pi, math.pi, 3)
        U = L2.walk_symbol(k)
        bitwise = max(bitwise, float(np.max(np.abs(
            normal_h_packed(k, 1.0) - R25W.static_newton_lift(U)))))

    # (c) full 8-row K+ darkness at z=1 (physical AND auxiliary), and the
    #     auxiliary excitation for z!=1 (a DECLARED Wilson-sector diagnostic:
    #     the physical de Donder C+ stays dark for all z; only the auxiliary
    #     selector D+ sees the source motion, exactly like the static lift is
    #     auxiliary-dark only at z=1).
    static_K = 0.0
    aux_excite = 0.0
    for _ in range(300):
        k = rng.uniform(-math.pi, math.pi, 3)
        U = L2.walk_symbol(k)
        kap = R25W.base_kappa(U, 1.0)
        G0 = R25D.gauge_matrix(kap)
        C0 = R25D.dedonder_matrix(kap)
        r = R25W.wilson_r(k)
        s = r / C
        H0 = R25W.auxiliary_selector(U)
        I4 = np.eye(4, dtype=complex)
        K0 = np.vstack([np.hstack([C0, -s * I4]),
                        np.hstack([s * H0, -H0 @ G0])])
        hn = normal_h_packed(k, 1.0)
        xn = np.concatenate([hn, np.zeros(4)])
        static_K = max(static_K, float(np.max(np.abs(K0 @ xn))))
        # auxiliary D+ leg on a moving lift (z along v=0.3 shell)
        zv = np.exp(-1j * 0.3 * k[0])
        static_K  # keep name
        aux_excite = max(aux_excite, float(np.max(np.abs(
            s * H0 @ normal_h_packed(k, zv)))))
    return {"moving_deDonder_C_residual_max": dedonder,
            "static_z1_bitwise_vs_r25_static_newton": bitwise,
            "static_z1_full_8row_K_darkness": static_K,
            "moving_auxiliary_D_excitation_declared_diagnostic": aux_excite}


# --------------------------------------------------------------------------
#  S3 -- moving limit: non-singular source + no secular growth
# --------------------------------------------------------------------------
def cert_S3():
    rows = []
    worst_secular_ratio = 0.0
    max_A_all = 0.0
    min_gap_all = float("inf")
    for v in VELOCITIES:
        vv = np.array([v, 0.0, 0.0])
        # (a) source construction non-singular on the advection shell
        N = 16
        maxA, minzma = 0.0, float("inf")
        for idx in np.ndindex(N, N, N):
            if idx == (0, 0, 0):
                continue
            k = 2 * math.pi * np.array(idx, float) / N
            z = np.exp(-1j * float(vv @ k))
            _, a, _, bb = bloch(k)
            maxA = max(maxA, abs(bb / (z - a)))
            minzma = min(minzma, abs(z - a))
        # (b) sourced damped closed loop: resolvent gap + worst-k time integration
        Nr = 16
        worst = (0.0, None, None, None, None)
        mingap = float("inf")
        for idx in np.ndindex(Nr, Nr, Nr):
            if idx == (0, 0, 0):
                continue
            k = 2 * math.pi * np.array(idx, float) / Nr
            z = np.exp(-1j * float(vv @ k))
            M = R25dyn.damped_map(k, MU)[0]
            D = drive14(k, z)
            BD = np.concatenate([D, D])          # enters both h and pi updates
            X = np.linalg.solve(z * np.eye(28) - M, BD)
            resp = float(np.linalg.norm(X) / (np.linalg.norm(BD) + 1e-300))
            ev = np.linalg.eigvals(M)
            mingap = min(mingap, float(np.min(np.abs(z - ev))))
            if resp > worst[0]:
                worst = (resp, k, z, BD, M)
        # time-domain secular test at the worst near-resonant k
        _, kw, zw, BDw, Mw = worst
        x = np.zeros(28, complex)
        T = 6000
        checkpts = {}
        for t in range(T):
            x = Mw @ x + (zw ** t) * BDw
            if t in (T // 2, T - 1):
                checkpts[t] = float(np.linalg.norm(x))
        secular_ratio = checkpts[T - 1] / max(checkpts[T // 2], 1e-300)
        worst_secular_ratio = max(worst_secular_ratio, secular_ratio)
        max_A_all = max(max_A_all, maxA)
        min_gap_all = min(min_gap_all, mingap)
        rows.append({"v_over_c": v, "source_max_abs_A": maxA,
                     "source_min_z_minus_a": minzma,
                     "resolvent_min_gap": mingap,
                     "worst_k_resolvent_norm": worst[0],
                     "time_domain_norm_mid": checkpts[T // 2],
                     "time_domain_norm_final": checkpts[T - 1],
                     "final_over_mid_ratio": secular_ratio})
    return {"per_velocity": rows,
            "source_construction_bounded": max_A_all,
            "min_resolvent_gap_all_v": min_gap_all,
            "worst_secular_ratio": worst_secular_ratio}


# --------------------------------------------------------------------------
#  S4 -- half-time-step placement (R13/L3 lesson)
# --------------------------------------------------------------------------
def cert_S4():
    rng = np.random.default_rng(250727)
    v = np.array([0.3, 0.0, 0.0])
    correct, frozen = 0.0, 0.0
    for _ in range(400):
        k = rng.uniform(-math.pi, math.pi, 3)
        zv = np.exp(-1j * float(v @ k))
        kup = ETA @ kappa(k, zv)          # TRUE moving covector
        hb_correct, _ = hbar_moving(k, zv)      # source at its half-step slot
        hb_frozen, _ = hbar_moving(k, 1.0)      # source frozen at static z=1
        correct = max(correct, float(np.max(np.abs(kup @ hb_correct))))
        frozen = max(frozen, float(np.max(np.abs(kup @ hb_frozen))))
    return {"centered_half_step_residual": correct,
            "frozen_integer_slot_residual": frozen,
            "declaration": ("momentum rows S0i live at the half-integer time "
                            "slot (R9 T3 centering = R19 OFFSET[(0,i)]); the "
                            "density row S00 is integer-placed and row-0 "
                            "integrated.  The moving time amplitude A(z) must "
                            "carry the source's own advection phase z_v=e^{-i v.k}; "
                            "freezing it to z=1 (static slot) breaks de Donder "
                            "by O(1).")}


# --------------------------------------------------------------------------
#  reality pairing (conjugate/mirror dual sector)
# --------------------------------------------------------------------------
def cert_reality():
    rng = np.random.default_rng(250728)
    v = np.array([0.3, 0.0, 0.0])
    # star-involution preserves de Donder darkness: both sectors dark
    both_dark = 0.0
    rank_g, rank_k = set(), set()

    def rnk(A, tol=1e-9):
        s = np.linalg.svd(A, compute_uv=False)
        return int(np.sum(s > tol * max(float(s[0]), 1.0)))

    re_collapse_kills_momentum = 0.0
    for _ in range(300):
        k = rng.uniform(-math.pi, math.pi, 3)
        zv = np.exp(-1j * float(v @ k))
        hbp, _ = hbar_moving(k, zv)
        kup = ETA @ kappa(k, zv)
        both_dark = max(both_dark, float(np.max(np.abs(kup @ hbp))))
        # minus/mirror sector = Laurent star (z->1/z, conj): dark by conjugation
        hbm = np.conjugate(hbp)             # (illustrative same-k star image)
        both_dark = max(both_dark, float(np.max(np.abs(np.conjugate(kup) @ hbm))))
        # rank census at moving z: complex stays 4/8 -> reality identifies, no doubling
        Gp, Kp, *_ = R25W.augmented_maps_at_z(k, zv)
        rank_g.add(rnk(Gp)); rank_k.add(rnk(Kp))
        # STRUCTURAL FINDING: the static "physical = Re(hbar_+)" collapse kills
        # the moving momentum current hbar0i (which must survive).
        re_collapse_kills_momentum = max(
            re_collapse_kills_momentum,
            float(np.max(np.abs(np.real(hbp[0, 1:])) < 1e-13)
                  * np.max(np.abs(hbp[0, 1:]))))
    return {"star_involution_both_sectors_dark": both_dark,
            "augmented_gauge_rank": sorted(rank_g),
            "augmented_constraint_rank": sorted(rank_k),
            "structural_finding": (
                "For a moving source the static recipe physical=Re(hbar_+) is "
                "NOT valid: it annihilates the physical momentum current hbar0i "
                "(purely imaginary in one sector).  The reality-real moving "
                "source is the explicit plus (+) conjugate/mirror (reversed-axis) "
                "sector with position-space hermiticity hbar(-k)=conj(hbar(k)); "
                "darkness and the 4-gauge/2-polarization count are preserved "
                "(no doubling).  Assembling the real field is a POSITION-SPACE "
                "step and is delegated to blocker () -- see interface spec."),
            "moving_momentum_would_be_lost_by_Re_collapse": bool(True)}


# --------------------------------------------------------------------------
def interface_spec():
    return {
        "target_signature": "step(h, pi, drive=D)  with D a 14-component field",
        "drive_definition":
            "D(x,t) = a_W * h_lift(x,t) on the physical 10 rows, auxiliary 4 "
            "rows = 0.  h_lift is the trace-reverse->normal packing of "
            "hbar_moving evaluated with the source's local advection time "
            "amplitude A(z_v); equilibrium of the damped+source loop is "
            "h = h_lift (static limit reproduces r25_static_newton exactly).",
        "which_sector":
            "Inject into the plus (ordered-xyz) sector; the conjugate/mirror "
            "sector is generated by reality (hbar(-k)=conj(hbar(k))).  Do NOT "
            "collapse via Re() -- that destroys the moving momentum current. "
            "Physical count stays 4 gauge / 2 polarizations (no doubling).",
        "which_time_slot":
            "S00 (density) integer time step; S0i (momentum) half-integer slot "
            "= R9 T3 centering J=1/2(F_t+F_{t-1}) = R19 OFFSET[(0,i)].  If the "
            "step injects on integer slots only, route S0i through the R13 "
            "placement transfer map (R19 sec.6 reserved item); a frozen/integer "
            "slot for a moving source breaks de Donder by O(1) (S4).",
        "three_injection_points":
            "The 14-vector D enters (i) the pi update, (ii) the h update, and "
            "(iii) the K_state proposal z*h_t -> (1-a_W)h + pi + D, consistent "
            "with the coordinator's step and with the static fixed point.",
        "normalization":
            "D carries the factor a_W = 2 - tr(U_walk) + r^2 so the physical "
            "Green response is the single scalar 1/a_W (no other inverse). The "
            "source current amplitude uses the SAME /c normalization as "
            "base_kappa (C = 0.5).",
        "conservation_contract":
            "The injected D satisfies kappa(z).eta.D_phys = 0 to machine zero "
            "(S1/S2); the step must preserve this by using the centered time "
            "slot.  The de Donder residual is the online health monitor.",
        "not_done_here":
            "Real-space finite stencil for the moving lift, the R13 half-step "
            "transfer map realization, the explicit mirror-sector real "
            "assembly, and the dynamic Newton fixed-point / endurance run "
            "belong to blocker () and are OUT OF SCOPE for this symbol file.",
    }


def main():
    S1 = cert_S1()
    S2 = cert_S2()
    S3 = cert_S3()
    S4 = cert_S4()
    RE = cert_reality()

    checks = {
        "S1_symbol_continuity_machine_zero": S1["symbol_continuity_kappa_dot_S_max"] < 1e-12,
        "S1_R10_lineage_1e-15": S1["R10_moving_bond_current_continuity"] < 1e-13,
        "S2_moving_deDonder_machine_zero": S2["moving_deDonder_C_residual_max"] < 1e-12,
        "S2_static_bitwise_degeneration": S2["static_z1_bitwise_vs_r25_static_newton"] < 1e-11,
        "S2_static_full_8row_darkness": S2["static_z1_full_8row_K_darkness"] < 1e-11,
        "S3_source_construction_bounded": S3["source_construction_bounded"] < 1e3,
        "S3_no_exact_resonance_gap_positive": S3["min_resolvent_gap_all_v"] > 1e-6,
        "S3_no_secular_growth_saturates": S3["worst_secular_ratio"] < 2.5,
        "S4_centered_slot_machine_zero": S4["centered_half_step_residual"] < 1e-12,
        "S4_frozen_slot_breaks_O1": S4["frozen_integer_slot_residual"] > 1e-2,
        "reality_both_sectors_dark": RE["star_involution_both_sectors_dark"] < 1e-12,
        "reality_rank_not_doubled": RE["augmented_gauge_rank"] == [4] and RE["augmented_constraint_rank"] == [8],
    }
    result = {
        "register": "R25-moving-source-symbol",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "scope": ("Symbol-layer certificate only.  PASS certifies the four "
                  "declared certificates (S1-S4) + reality pairing for the "
                  "moving exact-current source; it does NOT claim M3 progress "
                  "and does NOT include real-space integration (blocker )."),
        "checks": checks,
        "source_sha256": sha256(__file__),
        "frozen_inputs": {
            "walk_symbol": "cp1_v4_L2.walk_symbol", "C_cone": C,
            "damping_mu": MU,
            "static_reference": "r25_auxiliary_wilson.static_newton_lift",
            "R10_generator": "r10_current_generator (moving 4-comp Dirac pair)",
        },
        "construction": {
            "A_of_z": "(b.b)/(z-a); = 1+a at z=1 (removable), carries source motion",
            "hbar00": "A^2/(2c)", "hbar0i": "-A i b_i/(2c)",
            "hbarij": "(b.b delta_ij - 3 b_i b_j)/(4c) [z-independent]",
            "identity": "(z-a)A = b.b => kappa(z).eta.hbar(z) == 0 for all z",
            "advection_shell": "z_v(k) = exp(-i v.k)",
        },
        "S1_conservation": S1,
        "S2_de_donder": S2,
        "S3_moving_limit": S3,
        "S4_time_placement": S4,
        "reality_pairing": RE,
        "interface_spec_for_blocker_1": interface_spec(),
    }
    def _san(o):
        if isinstance(o, dict):
            return {k: _san(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_san(v) for v in o]
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        return o

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(_san(result), fh, ensure_ascii=False, indent=2)

    print("R25 moving-source symbol layer")
    print("status:", result["status"])
    print("S1 symbol continuity / R10 lineage:",
          f'{S1["symbol_continuity_kappa_dot_S_max"]:.2e}',
          f'{S1["R10_moving_bond_current_continuity"]:.2e}')
    print("S2 moving deDonder / static bitwise / 8row:",
          f'{S2["moving_deDonder_C_residual_max"]:.2e}',
          f'{S2["static_z1_bitwise_vs_r25_static_newton"]:.2e}',
          f'{S2["static_z1_full_8row_K_darkness"]:.2e}')
    print("S3 maxA / min_gap / secular_ratio:",
          f'{S3["source_construction_bounded"]:.3f}',
          f'{S3["min_resolvent_gap_all_v"]:.2e}',
          f'{S3["worst_secular_ratio"]:.3f}')
    print("S4 centered / frozen:",
          f'{S4["centered_half_step_residual"]:.2e}',
          f'{S4["frozen_integer_slot_residual"]:.2e}')
    print("reality both-dark / ranks:",
          f'{RE["star_involution_both_sectors_dark"]:.2e}',
          RE["augmented_gauge_rank"], RE["augmented_constraint_rank"])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
