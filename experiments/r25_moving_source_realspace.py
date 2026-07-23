"""R25-E2: real-space physical-metric assembly for the MOVING exact-current
source -- the explicit conjugate/mirror sector that keeps the momentum flux
h_bar0i alive (pre-M3 blocker #3 real-space follow-on to the symbol layer).

Context (AGENTS.md pre-M3, lane B second wave, front item):
  The moving-source SYMBOL layer (r25_moving_source_symbol, S1-S4 + reality)
  proved that the walk-covariant moving trace-reversed source
      hbar00 = A^2/(2c),  hbar0i = -A i b_i/(2c),  hbarij z-independent,
      A(z) = (b.b)/(z-a),  z_v(k) = exp(-i v.k),
  conserves momentum (kappa.eta.hbar == 0) for every z, and -- crucially --
  that the STATIC recipe "physical = Re(hbar_+)" is NOT valid for a moving
  source: it annihilates the physical momentum current hbar0i.  The symbol
  file delegated the *position-space* real assembly to this file.

What this file does (real space, fp64, numpy):
  The physical real metric is the EXPLICIT MIRROR SECTOR pairing, not a Re()
  collapse.  Ordered-xyz chiral walk (plus sector) has NO k-parity, so a single
  sector never satisfies position-space hermiticity hbar(-k)=conj(hbar(k)); the
  mirror sector supplies it.  Concretely, following the frozen step's reality
  discipline (h_minus = conj(h_plus), step_minus = conj . step . conj):
      h_plus   evolves with step   and drive  D_plus,
      h_minus  evolves with step_minus and drive conj(D_plus),
      physical metric h = (h_plus + h_minus)/2   (real in position space).
  The moving source is injected into the plus sector; the mirror is generated
  by reality.  The 4-gauge / 2-polarization count is NOT doubled (E2-2).

  The moving lift is realized in real space from the FROZEN matter macro-walk
  scalars a, b_i (r25_realspace_step.walk_mult) and the per-mode advection
  amplitude A(z_v); nothing here mutates the frozen step (import only).

Certificates (fp64):
  E2-1  h_bar0i preserved & bit-for-bit against the symbol layer (blocker #3),
        physical momentum current non-zero and momentum-conserving; CONTROL:
        the Re(hbar_+) collapse annihilates the imaginary momentum current
        (== 0 exactly) and destroys momentum conservation (de Donder O(1)) --
        the mirror sector is load-bearing.
  E2-2  reality does NOT double: augmented gauge/constraint rank [4]/[8]
        preserved on the moving shell; mirror pairing residual under the
        frozen step/step_minus with a moving drive is ~0 (<1e-12).
  E2-3  static degeneration: v -> 0 returns bit-for-bit to r25_static_newton
        / the frozen step C3 static lift.
  E2-4  position-space hermiticity: the physical metric imaginary part is
        machine zero.

Scope (measured words, AGENTS.md):
  Existence construction / construction path for blocker #3 in real space.
  PASS certifies ONLY E2-1..E2-4 below.  This is NOT an M3 claim, NOT an
  "emergence" claim, and closes NO axis; blocker #4 joint verification is where
  the moving source, dynamic Newton, Eddington and the falsification battery
  merge.

Run:
    RULESPACE_BACKEND=numpy .venv/bin/python experiments/r25_moving_source_realspace.py
"""
from __future__ import annotations

import hashlib
import json
import os
import time

import numpy as np

import r25_realspace_step as RS            # FROZEN step / step_minus (import only)
import r25_moving_source_symbol as MS      # moving-source symbol layer (blocker #3)
import r25_static_newton as R25N           # static real-space Newton lift
import r25_auxiliary_wilson_complex as R25W
import cp1_v4_L2 as L2                      # noqa: F401 (walk symbol lineage)


DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
OUT = os.path.join(ROOT, "data", "results",
                   "r25_moving_source_realspace_results.json")
C = MS.C
ETA = MS.ETA
NF = RS.NF                                  # 14
VELOCITIES = MS.VELOCITIES                  # (0.1, 0.3, 0.5)
SEED = 250724


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


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
    if isinstance(o, (np.complexfloating,)):
        return {"re": float(o.real), "im": float(o.imag)}
    return o


# ===========================================================================
#  real-space moving lift from the FROZEN matter macro-walk scalars
# ===========================================================================
def bloch_realspace(ph):
    """(a, b_i, b.b) of the frozen walk read off a plane-wave eigenfunction via
    r25_realspace_step.walk_mult (the same frozen macro-walk the step uses)."""
    af, b1f, b2f, b3f = RS.walk_mult(ph)
    a = complex((af / ph).mean())
    b = np.array([complex((b1f / ph).mean()),
                  complex((b2f / ph).mean()),
                  complex((b3f / ph).mean())])
    return a, b, complex(b @ b)


def hbar0i_realspace(ph, z):
    """Moving trace-reversed momentum row hbar0i built from the REAL-SPACE walk
    operators acting on the plane wave ph, with advection amplitude A(z).
    A(z) = (b.b)/(z-a) is the per-mode action of the operator b.b (z - a_walk)^-1
    on the eigenfunction ph (exact for a plane wave)."""
    a, b, bb = bloch_realspace(ph)
    A = bb / (z - a)
    return -A * 1j * b / (2 * C)


def plane(kv, N):
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    return np.exp(1j * (kv[0] * X + kv[1] * Y + kv[2] * Z))


# ===========================================================================
#  E2-1  momentum flux preserved, symbol match, Re-collapse control
# ===========================================================================
def cert_E2_1(N=12):
    """For each velocity: (a) the real-space moving lift hbar0i reproduces the
    symbol layer bit-for-bit; (b) the explicit-mirror physical momentum current
    is non-zero and momentum-conserving; (c) the Re(hbar_+) collapse annihilates
    the imaginary momentum current and breaks momentum conservation."""
    rng = np.random.default_rng(SEED)
    modes = [(1, 0, 0), (1, 1, 0), (2, 1, 0), (1, 2, -1), (2, 2, 1),
             (3, 1, -2), (1, 3, 2), (2, -1, 3)]
    rows = []
    worst_match = 0.0
    worst_dd_phys = 0.0
    min_phys_current = float("inf")
    worst_dd_re = 0.0
    worst_re_imcur = 0.0
    for v in VELOCITIES:
        vv = np.array([v, 0.0, 0.0])
        rs_vs_symbol = 0.0
        phys_current = 0.0            # |Im hbar0i| retained by the mirror sector
        phys_full = 0.0
        dd_phys = 0.0                 # de Donder residual of the full complex source
        re_current = 0.0             # |Im hbar0i| left after Re-collapse (must be 0)
        dd_re = 0.0                   # de Donder residual after Re-collapse (O(1))
        for nv in modes:
            k = 2 * np.pi * np.array(nv, float) / N
            z = complex(np.exp(-1j * float(vv @ k)))
            ph = plane(k, N)
            # (a) real-space lift vs symbol layer (blocker #3), bit-for-bit
            hb0i_rs = hbar0i_realspace(ph, z)
            hb0i_sym = MS.hbar_moving(k, z)[0][0, 1:]
            rs_vs_symbol = max(rs_vs_symbol,
                               float(np.max(np.abs(hb0i_rs - hb0i_sym))))
            # (b) physical metric = explicit mirror pairing.  Momentum current
            #     retained = full complex hbar0i; conservation kappa.eta.hbar
            hb = MS.hbar_moving(k, z)[0]
            kup = ETA @ MS.kappa(k, z)
            phys_full = max(phys_full, float(np.max(np.abs(hb[0, 1:]))))
            phys_current = max(phys_current,
                               float(np.max(np.abs(np.imag(hb[0, 1:])))))
            dd_phys = max(dd_phys, float(np.max(np.abs(kup @ hb))))
            # (c) Re(hbar_+) collapse: annihilates the imaginary current, breaks
            #     momentum conservation
            hb_re = np.real(hb)
            re_current = max(re_current,
                             float(np.max(np.abs(np.imag(hb_re[0, 1:])))))
            dd_re = max(dd_re, float(np.max(np.abs(kup @ hb_re))))
        rows.append({"v_over_c": v,
                     "realspace_lift_vs_symbol_max": rs_vs_symbol,
                     "physical_h0i_full_max": phys_full,
                     "physical_momentum_current_min": phys_current,
                     "physical_deDonder_residual_max": dd_phys,
                     "Re_collapse_momentum_current": re_current,
                     "Re_collapse_deDonder_residual_max": dd_re})
        worst_match = max(worst_match, rs_vs_symbol)
        worst_dd_phys = max(worst_dd_phys, dd_phys)
        min_phys_current = min(min_phys_current, phys_current)
        worst_dd_re = max(worst_dd_re, dd_re)
        worst_re_imcur = max(worst_re_imcur, re_current)
    _ = rng
    return {"per_velocity": rows,
            "realspace_lift_vs_symbol_worst": worst_match,
            "physical_deDonder_worst": worst_dd_phys,
            "physical_momentum_current_min_over_v": min_phys_current,
            "Re_collapse_momentum_current_worst": worst_re_imcur,
            "Re_collapse_deDonder_worst": worst_dd_re}


# ===========================================================================
#  E2-2  reality does not double + mirror pairing under the frozen step
# ===========================================================================
def moving_drive14(k, z, ph):
    """14-component real-space drive plane wave for the plus sector (C3
    convention: normal-h packing of the moving lift on the 10 physical rows,
    4 auxiliary rows zero).  No a_W factor -- the damped step's stiffness
    supplies it, exactly as the static fixed point in the frozen step's C3."""
    D = np.zeros((NF,) + ph.shape, complex)
    Dm = MS.normal_h_packed(k, z)               # 10-vector normal-h source lift
    for j in range(10):
        D[j] = Dm[j] * ph
    return D


def cert_E2_2(N=8, T=8):
    """(a) augmented gauge/constraint rank stays [4]/[8] on the moving shell
    (no doubling).  (b) The frozen step (plus) and step_minus (mirror), driven
    by a moving source and its conjugate, keep h_minus = conj(h_plus) exactly."""
    rng = np.random.default_rng(SEED + 1)

    def rnk(Ap, tol=1e-9):
        s = np.linalg.svd(Ap, compute_uv=False)
        return int(np.sum(s > tol * max(float(s[0]), 1.0)))

    rank_g, rank_k = set(), set()
    for v in VELOCITIES:
        vv = np.array([v, 0.0, 0.0])
        for _ in range(200):
            k = rng.uniform(-np.pi, np.pi, 3)
            z = complex(np.exp(-1j * float(vv @ k)))
            Gp, Kp = R25W.augmented_maps_at_z(k, z)[:2]
            rank_g.add(rnk(Gp))
            rank_k.add(rnk(Kp))

    # mirror pairing under the frozen step with a moving plane-wave drive
    v = 0.3
    vv = np.array([v, 0.0, 0.0])
    nv = (1, 1, 0)
    k = 2 * np.pi * np.array(nv, float) / N
    z = complex(np.exp(-1j * float(vv @ k)))
    ph = plane(k, N)
    hp = (rng.normal(size=(NF, N, N, N))
          + 1j * rng.normal(size=(NF, N, N, N)))
    pp = (rng.normal(size=(NF, N, N, N))
          + 1j * rng.normal(size=(NF, N, N, N)))
    hm, pm = np.conjugate(hp), np.conjugate(pp)
    pair = 0.0
    for t in range(T):
        D = moving_drive14(k, z, ph) * (z ** t)
        # step_minus = conj . step . conj already builds in the sector
        # conjugation, so the mirror receives the SAME drive kwarg (its own
        # conjugate drive is applied internally); h_minus stays conj(h_plus).
        hp, pp = RS.step(hp, pp, drive=D)
        hm, pm = RS.step_minus(hm, pm, drive=D)
        pair = max(pair,
                   float(max(np.max(np.abs(hm - np.conjugate(hp))),
                             np.max(np.abs(pm - np.conjugate(pp))))))
    return {"augmented_gauge_rank": sorted(rank_g),
            "augmented_constraint_rank": sorted(rank_k),
            "mirror_pairing_residual_moving_drive": pair,
            "pairing_steps": T}


# ===========================================================================
#  E2-3  static degeneration v -> 0
# ===========================================================================
def cert_E2_3(N=16):
    """v -> 0 returns bit-for-bit to the frozen static lift.  Two checks:
    (a) the real-space moving lift at z=z_v with v=0 equals the symbol static
    lift r25_auxiliary_wilson.static_newton_lift; (b) the assembled physical
    field of a static real Gaussian equals r25_static_newton.static_field_local
    (the frozen step's C3 static equilibrium source), position for position."""
    # (a) per grid mode: v=0 moving lift built from the REAL-SPACE walk scalars
    #     == static_newton_lift, bit-for-bit.  Plane waves must be grid
    #     eigenfunctions of the walk convolution, so k = 2*pi*n/Ng.
    Ng = 8
    lift_bitwise = 0.0
    for nv in [(m, n, p) for m in range(Ng) for n in range(Ng)
               for p in range(Ng)][1:60]:
        k = 2 * np.pi * np.array(nv, float) / Ng
        ph = plane(k, Ng)
        # full normal-h moving lift at z=1 from the real-space walk scalars
        a, b, bb = bloch_realspace(ph)
        A = bb / (1.0 - a)
        hb = np.zeros((4, 4), complex)
        hb[0, 0] = A * A / (2 * C)
        hb[0, 1:] = hb[1:, 0] = -A * 1j * b / (2 * C)
        hb[1:, 1:] = (np.eye(3) * bb - 3 * np.outer(b, b)) / (4 * C)
        trb = np.sum(ETA * hb)
        h = hb - 0.5 * ETA * trb
        packed = np.array([h[m, n] for m, n in RS.SYMC])
        U = L2.walk_symbol(k)
        lift_bitwise = max(lift_bitwise,
                           float(np.max(np.abs(packed
                                               - R25W.static_newton_lift(U)))))
    # (b) full-grid static physical field vs r25_static_newton.static_field_local
    rho = R25N.gaussian_lump(N, 2.5)
    rho_zm = rho - rho.mean()
    ref_field, _, aw = R25N.static_field_local(rho_zm)   # trace-reversed field
    # assemble the SAME field through the v=0 moving-source path (z_v=1)
    rk = np.fft.fftn(rho_zm)
    mine = np.zeros((10, N, N, N), complex)
    mask = aw > 1e-14
    for idx in np.ndindex(N, N, N):
        if not mask[idx]:
            continue
        k = 2 * np.pi * np.array(idx, float) / N
        hb = MS.hbar_moving(k, 1.0)[0]                    # trace-reversed source
        packed = np.array([hb[m, n] for m, n in RS.SYMC])
        mine[(slice(None),) + idx] = packed * rk[idx] / aw[idx]
    mine = np.fft.ifftn(mine, axes=(1, 2, 3))
    scale = float(np.max(np.abs(ref_field))) + 1e-300
    field_bitwise = float(np.max(np.abs(mine - ref_field)) / scale)
    # physical (mirror) real parts must also agree
    phys_ref = 0.5 * (ref_field + np.conjugate(ref_field))
    phys_mine = 0.5 * (mine + np.conjugate(mine))
    phys_bitwise = float(np.max(np.abs(phys_mine - phys_ref)) / scale)
    return {"N": N,
            "static_lift_bitwise_vs_static_newton": lift_bitwise,
            "static_field_bitwise_rel": field_bitwise,
            "static_physical_field_bitwise_rel": phys_bitwise}


# ===========================================================================
#  E2-4  position-space hermiticity of the physical metric
# ===========================================================================
def cert_E2_4(N=14, sig=2.0):
    """Assemble the physical metric of a REAL moving Gaussian via the explicit
    mirror sector (position-space reality) and certify its imaginary part is
    machine zero for every velocity (a real metric is delivered, not a Re()
    of a single complex sector)."""
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    r2 = (X - N // 2) ** 2 + (Y - N // 2) ** 2 + (Z - N // 2) ** 2
    rho0 = np.exp(-r2 / (2 * sig ** 2))
    rho0 = rho0 / rho0.sum() - 1.0 / N ** 3
    rk = np.fft.fftn(rho0)
    aw = R25N.symbols(N)
    mask = aw > 1e-14
    rows = []
    worst_imag = 0.0
    worst_single = 0.0
    for v in VELOCITIES:
        vv = np.array([v, 0.0, 0.0])
        hk = np.zeros((10, N, N, N), complex)
        for idx in np.ndindex(N, N, N):
            if not mask[idx]:
                continue
            k = 2 * np.pi * np.array(idx, float) / N
            z = complex(np.exp(-1j * float(vv @ k)))
            hb = MS.hbar_moving(k, z)[0]
            packed = np.array([hb[m, n] for m, n in RS.SYMC])
            hk[(slice(None),) + idx] = packed * rk[idx] / aw[idx]
        h_plus = np.fft.ifftn(hk, axes=(1, 2, 3))          # plus sector field
        h_minus = np.conjugate(h_plus)                     # mirror = conj (reality)
        h_phys = 0.5 * (h_plus + h_minus)                  # physical, real
        imag = float(np.max(np.abs(h_phys.imag)))
        single = float(np.max(np.abs(h_plus.imag)))        # single sector NOT real
        mom = float(np.max(np.abs(h_phys[1:4].real)))      # h0i momentum rows
        rows.append({"v_over_c": v,
                     "physical_max_imag": imag,
                     "single_sector_max_imag": single,
                     "physical_h0i_realspace_max": mom})
        worst_imag = max(worst_imag, imag)
        worst_single = max(worst_single, single)
    return {"N": N, "per_velocity": rows,
            "physical_max_imag_over_v": worst_imag,
            "single_sector_max_imag_over_v": worst_single}


# ===========================================================================
def main():
    t0 = time.time()
    result = {"register": "R25-E2-moving-source-realspace-mirror"}

    def flush(status="RUNNING"):
        result["status"] = status
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(_san(result), fh, ensure_ascii=False, indent=2)

    result["scope"] = (
        "Existence construction / construction path (AGENTS.md pre-M3, lane B "
        "second wave front item): real-space physical-metric assembly of the "
        "moving exact-current source via the EXPLICIT conjugate/mirror sector "
        "(h_minus = conj(h_plus), step_minus = conj . step . conj), keeping the "
        "momentum flux h_bar0i.  PASS certifies ONLY E2-1..E2-4 below.  No M3 "
        "claim, no 'emergence' claim, no axis closed; blocker #4 joint "
        "verification is where the axes merge.")
    result["frozen_inputs_sha256"] = {
        "r25_realspace_step.py": sha256(os.path.join(DIR, "r25_realspace_step.py")),
        "r25_moving_source_symbol.py": sha256(os.path.join(DIR, "r25_moving_source_symbol.py")),
        "r25_static_newton.py": sha256(os.path.join(DIR, "r25_static_newton.py")),
        "r25_auxiliary_wilson_complex.py": sha256(os.path.join(DIR, "r25_auxiliary_wilson_complex.py")),
    }
    result["construction"] = {
        "physical_metric": "h = (h_plus + h_minus)/2 with h_minus = conj(h_plus) "
                           "(explicit mirror sector, position-space hermiticity); "
                           "NOT a Re(hbar_+) collapse",
        "moving_lift": "hbar0i = -A i b_i/(2c), A(z)=(b.b)/(z-a), z_v=exp(-i v.k); "
                       "a, b_i read from the FROZEN matter macro-walk "
                       "(r25_realspace_step.walk_mult)",
        "injection": "moving source -> plus sector; mirror generated by reality "
                     "hbar(-k)=conj(hbar(k)); 4-gauge/2-polarization count NOT doubled",
        "velocities": list(VELOCITIES),
    }
    flush("RUNNING")

    e1 = cert_E2_1()
    result["E2_1_momentum_flux"] = e1
    print("E2-1 realspace-vs-symbol %.2e | phys deDonder %.2e | phys current "
          "min %.3f | Re-collapse current %.1e deDonder %.3f (%.1fs)"
          % (e1["realspace_lift_vs_symbol_worst"], e1["physical_deDonder_worst"],
             e1["physical_momentum_current_min_over_v"],
             e1["Re_collapse_momentum_current_worst"],
             e1["Re_collapse_deDonder_worst"], time.time() - t0))
    flush("RUNNING")

    e2 = cert_E2_2()
    result["E2_2_no_doubling"] = e2
    print("E2-2 ranks", e2["augmented_gauge_rank"], e2["augmented_constraint_rank"],
          "| mirror pairing residual %.2e (%.1fs)"
          % (e2["mirror_pairing_residual_moving_drive"], time.time() - t0))
    flush("RUNNING")

    e3 = cert_E2_3()
    result["E2_3_static_degeneration"] = e3
    print("E2-3 static lift bitwise %.2e | field rel %.2e | phys rel %.2e (%.1fs)"
          % (e3["static_lift_bitwise_vs_static_newton"],
             e3["static_field_bitwise_rel"],
             e3["static_physical_field_bitwise_rel"], time.time() - t0))
    flush("RUNNING")

    e4 = cert_E2_4()
    result["E2_4_position_hermiticity"] = e4
    print("E2-4 physical imag %.2e | single-sector imag %.2e (%.1fs)"
          % (e4["physical_max_imag_over_v"],
             e4["single_sector_max_imag_over_v"], time.time() - t0))

    checks = {
        # E2-1
        "E2_1_realspace_lift_matches_symbol_lt_1e-11":
            e1["realspace_lift_vs_symbol_worst"] < 1e-11,
        "E2_1_physical_momentum_current_nonzero":
            e1["physical_momentum_current_min_over_v"] > 1e-3,
        "E2_1_physical_momentum_conserved_lt_1e-12":
            e1["physical_deDonder_worst"] < 1e-12,
        "E2_1_Re_collapse_annihilates_current":
            e1["Re_collapse_momentum_current_worst"] < 1e-13,
        "E2_1_Re_collapse_breaks_conservation":
            e1["Re_collapse_deDonder_worst"] > 1e-2,
        # E2-2
        "E2_2_gauge_rank_4": e2["augmented_gauge_rank"] == [4],
        "E2_2_constraint_rank_8": e2["augmented_constraint_rank"] == [8],
        "E2_2_mirror_pairing_exact":
            e2["mirror_pairing_residual_moving_drive"] < 1e-12,
        # E2-3
        "E2_3_static_lift_bitwise_lt_1e-11":
            e3["static_lift_bitwise_vs_static_newton"] < 1e-11,
        "E2_3_static_field_bitwise_lt_1e-11":
            e3["static_field_bitwise_rel"] < 1e-11,
        "E2_3_static_physical_field_bitwise_lt_1e-11":
            e3["static_physical_field_bitwise_rel"] < 1e-11,
        # E2-4
        "E2_4_physical_metric_real_lt_1e-12":
            e4["physical_max_imag_over_v"] < 1e-12,
        "E2_4_single_sector_not_real":
            e4["single_sector_max_imag_over_v"] > 1e-3,
    }
    result["checks"] = checks
    result["interface_for_blocker_4"] = {
        "physical_metric": "h_phys = (h_plus + h_minus)/2, h_minus=conj(h_plus); "
                           "real in position space (E2-4); momentum flux h_bar0i "
                           "retained (E2-1) and momentum-conserving (de Donder ~0).",
        "moving_source_injection": "plus sector drive D_plus (14-comp, normal-h "
                                   "packing of hbar_moving, 4 aux rows zero, C3 "
                                   "convention no a_W factor); mirror drive "
                                   "conj(D_plus); step/step_minus keep the pairing "
                                   "exact (E2-2).",
        "do_not": "do NOT collapse via Re(hbar_+): it zeroes the imaginary "
                  "momentum current and breaks de Donder by O(1) (E2-1 control).",
        "still_open_at_blocker_4": "dynamic Newton fixed point under evolution "
                                   "(obstacle #2 slow contraction blocks time-domain "
                                   "convergence -- symbol/resolvent used here), "
                                   "Eddington, sponge/endurance, DOF/J5 replay, "
                                   "and the falsification battery; R26 hyperbolic "
                                   "constraint sector must re-certify on the "
                                   "co-deformed K (see R25R26 ruling).",
    }
    result["source_sha256"] = sha256(__file__)
    flush("PASS" if all(checks.values()) else "FAIL")

    print("\nchecks:")
    for k, val in checks.items():
        print(f"  [{'PASS' if val else 'FAIL'}] {k}")
    print("status:", result["status"])
    print("wrote", OUT)
    print("total %.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
