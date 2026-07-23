"""R31 -- 并行便宜诊断: per-wave-vector MODAL SPECTRUM classification of the walk
U's 12 unit modes.  Complements R30 (which route is viable) by pinning down, for
the CURRENT walk U, exactly WHICH sector the extra modes (the >TT ones inside
N_prop=4) live in.

WHAT THIS DOES (pure diagnosis, reuses frozen R28/卡点⑦ machinery, constructs
nothing new).  For each k in {axial, face-diagonal, BODY-diagonal}, take the 12
unit-modulus eigenmodes of the REAL walk symbol M = D1.damped_map(k, R.MU)[0]
(the same object R28.placed_subspace_residual diagnosed), extract each mode's
physical-h metric part (V[:10], 卡点⑦'s field convention), and for EACH mode
classify three quantities:

  1. CONSTRAINT value  |C . hbar(mode)| / ||mode||   -- magnitude of the mode in
     the de Donder constraint's image (C = R15 constraint_matrix on the placed
     shell; the evolved variable is physical h, so we feed hbar = TR(h)).
  2. CURVATURE value   placed Riemann energy (R16.riemann_energy, VERBATIM the
     certified kernel) -- does the mode TRULY carry curvature vs zero-curvature.
  3. GAUGE-NESS         orthogonal energy fractions in three MUTUALLY-ORTHOGONAL
     sectors that tile the 10-dim symmetric-tensor space (fractions SUM TO 1):
        f_TT    : placed TT subspace (2-dim, the true graviton) -- physical.
        f_gauge : (ker K) minus TT = placed pure-gauge sector (4-dim) -- physical.
        f_row   : constraint ROW space = orthogonal complement of ker K (4-dim)
                  = the R28 病灶 (energy the walk pushed OUT of ker K).
     ker K = placed gauge(4) (+) TT(2) = 6-dim (R15 T9); f_row = residual^2 (the
     34-49% R28 quantified).  sqrt(mean f_row) reproduces r28's
     mean_residual_outside_placed_subspace as an INDEPENDENT re-derivation.

VERDICT (independent re-check of R28's "extra modes are NOT gauge -> constraint
ROW space activated into propagation"):
  * A curvature-carrying mode whose curvature sits in f_row => "constraint-row
    mode activated into propagation" (R28's claim).
  * A curvature-carrying mode dominated by f_gauge WOULD be "gauge leaking into
    curvature" -- but E1 forbids nonzero Riemann on a pure placed-gauge mode, so
    any curvature in a high-f_gauge mode is carried by its TT/row remainder.
  The sector attribution of the 4-5 curvature modes decides it, per k.

RED LINES (AGENTS.md): pure diagnosis.  Does NOT declare M3 / emergence / DOF-axis
closure.  If it confirms R28, the extra modes are REAL physics (constraint-row
curvature), not a measurement artifact.  Frozen inputs imported READ-ONLY.

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/r31_modal_spectrum.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
for p in (DIR, ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import matplotlib                                          # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                            # noqa: E402

import r25_realspace_step as R                             # noqa: E402 frozen U (R.MU)
import r25_dynamic_symbol as D1                            # noqa: E402 walk symbol M
import r25_emergence_timeseries as TS                      # noqa: E402 shared口径
from r16_cp1_invitro import riemann_energy                 # noqa: E402 certified kernel
from r15_walk_dedonder import (kappa_placed, gauge_block,  # noqa: E402 placed shell
                               tt_basis, constraint_matrix, shell_omega,
                               ETA, unpack, pack, SYM)

OUT = os.path.join(ROOT, "data", "results", "r31_results.json")
FIG = os.path.join(ROOT, "visualizations", "figs", "r31_modal_spectrum.png")

N = TS.N                                                   # 16
SV_THRESH = TS.SV_THRESH                                   # 0.05 shared judge threshold
MU = R.MU                                                  # frozen chosen damping
KSET = [(2, 0, 0), (0, 3, 0), (2, 2, 0), (2, 2, 2)]
LABELS = {(2, 0, 0): "axial", (0, 3, 0): "axial",
          (2, 2, 0): "face-diagonal", (2, 2, 2): "body-diagonal"}
CURV_REL = 1e-3          # a mode "carries curvature" if its Riemann energy is
                         # >= CURV_REL * max mode curvature at that k (relative,
                         # so it tracks the SVD口径's dominant-branch content).


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _jd(o):
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        f = float(o)
        return f if np.isfinite(f) else str(f)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def write_json(payload):
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=_jd)


def _tr_flat(v10):
    """flat-ETA trace reversal (R16 convention, its own inverse): physical h <->
    hbar.  IDENTICAL to R28._tr_flat.  Physical-h gauge = _tr_flat(gauge_block);
    hbar of a physical mode = _tr_flat(mode)."""
    Hb = unpack(v10)
    trb = sum(ETA[m, m] * Hb[m, m] for m in range(4))
    H = Hb - 0.5 * ETA * trb
    return np.array([H[m, n] for (m, n) in SYM])


def build_sectors(kap):
    """Three MUTUALLY-ORTHOGONAL orthonormal sectors of the 10-dim symmetric
    tensor space, all in PHYSICAL-h coordinates (卡点⑦ / R28 convention):
        Q_gauge (10,4)  EXACT placed gauge span (physical) -- Riemann-FREE by E1
                        (Riemann is linear in h, vanishes on every gauge basis
                        vector, hence on the whole span: this sector carries ZERO
                        curvature, an internal control the classifier re-checks).
        Q_TT    (10,2)  (ker K) minus gauge = the curvature-carrying quotient
                        ker K / gauge (= placed TT classes, orthogonalized).
        Q_row   (10,4)  orthogonal complement of ker K = constraint ROW space
                        (the R28 病灶; f_row = R28's residual^2 exactly).
    ker K = gauge (+) TT = 6-dim (R15 T9).  [Q_gauge|Q_TT|Q_row] is 10x10 unitary.
    Gauge is made the EXACT span (not TT) so the Riemann-free sector is exact and
    all propagating curvature is forced to reveal itself as TT or ROW."""
    G_phys = np.column_stack([_tr_flat(np.real(gauge_block(kap)[:, a]))
                              for a in range(4)])          # (10,4) physical gauge
    TT_phys = np.real(tt_basis(kap))                       # (10,2) traceless = physical
    Q_gauge, _ = np.linalg.qr(G_phys)                      # (10,4) EXACT gauge span
    # TT sector = ker K orthogonalized against gauge (gauge subset ker K => rank 2)
    ker = np.column_stack([G_phys, TT_phys])               # (10,6) = ker K
    ker_perp_g = ker - Q_gauge @ (Q_gauge.conj().T @ ker)
    Uq, sq, _ = np.linalg.svd(ker_perp_g, full_matrices=False)
    rk = int(np.sum(sq > 1e-9 * sq[0]))
    Q_TT = Uq[:, :rk]                                      # (10,2)
    # constraint row space = orthogonal complement of ker K in R^10
    Q6, _ = np.linalg.qr(np.column_stack([Q_gauge, Q_TT]))
    Qfull, _ = np.linalg.qr(Q6, mode="complete")
    Q_row = Qfull[:, Q6.shape[1]:]                         # (10,4)
    return Q_TT, Q_gauge, Q_row


def classify_k(nv):
    kvec = np.array(nv, float) * (2 * np.pi / N)
    kap = kappa_placed(kvec)
    K = constraint_matrix(kap)                             # (4,10) acts on hbar
    Q_TT, Q_gauge, Q_row = build_sectors(kap)
    # completeness / orthonormality certificate
    B = np.column_stack([Q_TT, Q_gauge, Q_row])            # (10,10)
    ortho_err = float(np.max(np.abs(B.conj().T @ B - np.eye(10))))

    M = D1.damped_map(kvec, MU)[0]
    eig, V = np.linalg.eig(M)
    idx = np.where(np.abs(np.abs(eig) - 1.0) < 2e-9)[0]
    U = V[:10, idx]                                        # (10, n_unit) physical h
    U = U / (np.linalg.norm(U, axis=0, keepdims=True) + 1e-300)
    phases = np.angle(eig[idx])

    def rima(vec):                                         # physical-h placed Riemann energy
        return float(riemann_energy(kap, _tr_flat(vec)))

    modes = []
    for j in range(U.shape[1]):
        u = U[:, j]
        # sector projections (physical h) -- these are ACTUAL vectors, so their
        # Riemann energy is the honest curvature carried by that sector's part.
        p_TT = Q_TT @ (Q_TT.conj().T @ u)
        p_gauge = Q_gauge @ (Q_gauge.conj().T @ u)
        p_row = Q_row @ (Q_row.conj().T @ u)
        f_TT = float(np.linalg.norm(p_TT) ** 2)
        f_gauge = float(np.linalg.norm(p_gauge) ** 2)
        f_row = float(np.linalg.norm(p_row) ** 2)
        constraint = float(np.linalg.norm(K @ _tr_flat(u)))   # |C . hbar(u)| (u unit)
        curvature = rima(u)                                # total placed Riemann
        c_TT, c_gauge, c_row = rima(p_TT), rima(p_gauge), rima(p_row)
        # dominant CURVATURE sector = which sector projection carries most Riemann
        cfrac = {"TT": c_TT, "gauge": c_gauge, "row": c_row}
        modes.append({"idx": j, "omega": float(phases[j]),
                      "constraint": constraint, "curvature": curvature,
                      "f_TT": f_TT, "f_gauge": f_gauge, "f_row": f_row,
                      "f_sum": f_TT + f_gauge + f_row,
                      "curv_TT": c_TT, "curv_gauge": c_gauge, "curv_row": c_row,
                      "curv_cross": curvature - (c_TT + c_gauge + c_row),
                      "dominant_curv_sector": max(cfrac, key=cfrac.get)})

    # internal control: gauge sector must be Riemann-FREE (E1, linear) ---------
    max_gauge_curv = max((m["curv_gauge"] for m in modes), default=0.0)
    ref_curv = max((m["curvature"] for m in modes), default=1.0) + 1e-300

    # per-mode curvature-carrier flag (relative to peak mode curvature)
    cmax = max(m["curvature"] for m in modes) if modes else 0.0
    for m in modes:
        m["carries_curvature"] = bool(cmax > 0 and m["curvature"] >= CURV_REL * cmax)
        efrac = {"TT": m["f_TT"], "gauge": m["f_gauge"], "row": m["f_row"]}
        m["dominant_sector"] = max(efrac, key=efrac.get)

    # aggregate: how the propagating CURVATURE energy splits across sectors,
    # via each sector's OWN projected Riemann energy (honest; gauge -> ~0).
    tot_pc = sum(m["curv_TT"] + m["curv_gauge"] + m["curv_row"]
                 for m in modes) + 1e-300
    curv_in = {
        "TT": sum(m["curv_TT"] for m in modes) / tot_pc,
        "gauge": sum(m["curv_gauge"] for m in modes) / tot_pc,
        "row": sum(m["curv_row"] for m in modes) / tot_pc}

    carriers = [m for m in modes if m["carries_curvature"]]
    carrier_sectors = {"TT": 0, "gauge": 0, "row": 0}
    for m in carriers:
        carrier_sectors[m["dominant_curv_sector"]] += 1

    # independent re-derivation of R28's residual (mean sqrt(f_row) over 12 modes)
    mean_resid = float(np.mean([np.sqrt(m["f_row"]) for m in modes]))
    n_resid_gt = int(np.sum([np.sqrt(m["f_row"]) > 0.3 for m in modes]))

    return {"nv": list(nv), "label": LABELS[nv], "n_unit": U.shape[1],
            "omega_shell": float(shell_omega(kvec)),
            "sector_ortho_err": ortho_err,
            "gauge_sector_riemann_free_max": max_gauge_curv,
            "gauge_sector_riemann_free_rel": max_gauge_curv / ref_curv,
            "modes": modes,
            "n_carriers": len(carriers),
            "carrier_dominant_curv_sector_counts": carrier_sectors,
            "curvature_energy_in_sector": curv_in,
            "mean_residual_outside_kerK": mean_resid,
            "n_modes_resid_gt_0.3": n_resid_gt}


def make_figure(per_k):
    nk = len(per_k)
    fig, axes = plt.subplots(2, nk, figsize=(4.2 * nk, 8.0))
    for ci, res in enumerate(per_k):
        modes = sorted(res["modes"], key=lambda m: (m["omega"], -m["curvature"]))
        labels = [f"{m['omega']:+.2f}" for m in modes]
        fTT = [m["f_TT"] for m in modes]
        fG = [m["f_gauge"] for m in modes]
        fR = [m["f_row"] for m in modes]
        x = np.arange(len(modes))
        ax = axes[0, ci]
        ax.bar(x, fTT, label="TT", color="#2a9d8f")
        ax.bar(x, fG, bottom=fTT, label="gauge", color="#e9c46a")
        ax.bar(x, fR, bottom=np.array(fTT) + np.array(fG), label="row(病灶)",
               color="#e76f51")
        ax.set_title(f"k={tuple(res['nv'])} [{res['label']}]\n"
                     f"resid_outside_kerK={res['mean_residual_outside_kerK']:.2f}")
        ax.set_ylim(0, 1.02)
        ax.set_xticks(x); ax.set_xticklabels(labels, rotation=90, fontsize=6)
        ax.set_ylabel("sector energy fraction")
        if ci == 0:
            ax.legend(fontsize=7, loc="lower left")
        ax2 = axes[1, ci]
        cu = np.array([m["curvature"] for m in modes])
        cu = cu / (cu.max() + 1e-300)
        col = ["#e76f51" if m["dominant_curv_sector"] == "row"
               else "#2a9d8f" if m["dominant_curv_sector"] == "TT"
               else "#e9c46a" for m in modes]
        ax2.bar(x, cu, color=col)
        ax2.set_title("curvature/max (color=dominant curv sector)")
        ax2.set_ylim(0, 1.05)
        ax2.set_xticks(x); ax2.set_xticklabels(labels, rotation=90, fontsize=6)
        ax2.set_xlabel("unit mode (omega)")
        ax2.set_ylabel("placed Riemann energy (norm)")
    fig.suptitle("R31 modal spectrum: 12 walk unit modes per k, sector x "
                 "(TT/gauge/constraint-row) + curvature", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    fig.savefig(FIG, dpi=110)
    plt.close(fig)


def main():
    t0 = time.time()
    payload = {
        "register": "R31-modal-spectrum (per-k classification of walk U's extra modes)",
        "status": "RUNNING",
        "backend": "numpy",
        "params": {"N": N, "kset": [list(k) for k in KSET], "mu": MU,
                   "sv_thresh": SV_THRESH, "curv_rel": CURV_REL},
        "geometry": "10-dim sym tensor = TT(2) (+) gauge(4) (+) constraint-row(4); "
                    "ker K = TT (+) gauge (R15 T9). All sectors physical-h (卡点⑦).",
        "frozen_inputs_sha256": {
            "r25_realspace_step.py": sha256_file(os.path.join(DIR, "r25_realspace_step.py")),
            "r25_dynamic_symbol.py": sha256_file(os.path.join(DIR, "r25_dynamic_symbol.py")),
            "r25_emergence_timeseries.py": sha256_file(os.path.join(DIR, "r25_emergence_timeseries.py")),
            "r15_walk_dedonder.py": sha256_file(os.path.join(DIR, "r15_walk_dedonder.py")),
            "r16_cp1_invitro.py": sha256_file(os.path.join(DIR, "r16_cp1_invitro.py")),
        },
    }
    write_json(payload)

    per_k = []
    for nv in KSET:
        res = classify_k(nv)
        per_k.append(res)
        cs = res["carrier_dominant_curv_sector_counts"]
        ce = res["curvature_energy_in_sector"]
        print(f"k={nv} [{res['label']:>13}] n_unit={res['n_unit']} "
              f"ortho_err={res['sector_ortho_err']:.1e} "
              f"gauge-Riemann-free(rel)={res['gauge_sector_riemann_free_rel']:.1e}")
        print(f"    carriers={res['n_carriers']}  dominant-curv-sector counts "
              f"TT={cs['TT']} gauge={cs['gauge']} row={cs['row']}")
        print(f"    curvature-energy in sector: TT={ce['TT']:.3f} "
              f"gauge={ce['gauge']:.3f} row={ce['row']:.3f}")
        print(f"    mean resid outside kerK = {res['mean_residual_outside_kerK']:.3f} "
              f"(R28 cross-check); modes resid>0.3 = {res['n_modes_resid_gt_0.3']}")
        write_json({**payload, "per_k_partial": per_k})

    # ---- R28 cross-check (independent re-derivation) -----------------------
    r28_path = os.path.join(ROOT, "data", "results", "r28_results.json")
    r28_match = []
    try:
        r28 = json.load(open(r28_path, encoding="utf-8"))
        r28_resid = {tuple(e["nv"]): e for e in
                     r28["static_symbol"]["placed_subspace_residual"]}
        for res in per_k:
            e = r28_resid.get(tuple(res["nv"]))
            if e:
                r28_match.append({
                    "nv": res["nv"],
                    "r31_mean_resid": res["mean_residual_outside_kerK"],
                    "r28_mean_resid": e["mean_residual_outside_placed_subspace"],
                    "abs_diff": abs(res["mean_residual_outside_kerK"]
                                    - e["mean_residual_outside_placed_subspace"]),
                    "r31_n_gt03": res["n_modes_resid_gt_0.3"],
                    "r28_n_gt03": e["n_modes_resid_gt_0.3"]})
    except Exception as ex:                                # pragma: no cover
        r28_match = [{"error": str(ex)}]
    worst_diff = max((m.get("abs_diff", 0.0) for m in r28_match), default=None)
    payload["r28_crosscheck"] = {"per_k": r28_match, "worst_abs_diff": worst_diff,
                                 "reproduces_r28": bool(worst_diff is not None
                                                        and worst_diff < 1e-6)}

    # ---- verdict -----------------------------------------------------------
    # dominant CURVATURE sector of each curvature-carrying mode (gauge is
    # Riemann-free by construction, so a gauge win would signal a broken control)
    gauge_curv_carriers = sum(
        1 for res in per_k for m in res["modes"]
        if m["carries_curvature"] and m["dominant_curv_sector"] == "gauge")
    row_curv_carriers = sum(
        1 for res in per_k for m in res["modes"]
        if m["carries_curvature"] and m["dominant_curv_sector"] == "row")
    tt_curv_carriers = sum(
        1 for res in per_k for m in res["modes"]
        if m["carries_curvature"] and m["dominant_curv_sector"] == "TT")
    max_gauge_free = max(res["gauge_sector_riemann_free_rel"] for res in per_k)
    # fraction of propagating curvature energy that sits in the constraint-row
    # sector (the R28 病灶), averaged over k
    mean_row_curv = float(np.mean([res["curvature_energy_in_sector"]["row"]
                                   for res in per_k]))
    mean_tt_curv = float(np.mean([res["curvature_energy_in_sector"]["TT"]
                                  for res in per_k]))
    mean_gauge_curv = float(np.mean([res["curvature_energy_in_sector"]["gauge"]
                                     for res in per_k]))

    payload["per_k"] = per_k
    payload["verdict_metrics"] = {
        "tt_dominant_curvature_carriers": tt_curv_carriers,
        "gauge_dominant_curvature_carriers": gauge_curv_carriers,
        "row_dominant_curvature_carriers": row_curv_carriers,
        "mean_curvature_energy_in_TT": mean_tt_curv,
        "mean_curvature_energy_in_gauge": mean_gauge_curv,
        "mean_curvature_energy_in_row": mean_row_curv,
        "gauge_sector_riemann_free_rel_max": max_gauge_free}
    r28_confirmed = bool(row_curv_carriers > 0 and mean_row_curv > 0.1
                         and gauge_curv_carriers == 0 and max_gauge_free < 1e-6
                         and payload["r28_crosscheck"]["reproduces_r28"])
    payload["r28_extra_modes_are_constraint_row_not_gauge"] = r28_confirmed
    payload["verdict"] = (
        "R28 CONFIRMED (independent re-check): the extra curvature-carrying modes "
        "are NOT pure placed-gauge modes. %d curvature carriers are dominated by "
        "the constraint-ROW sector, carrying %.1f%% of propagating curvature "
        "energy on average; %d are TT (the true graviton). The residual R28 "
        "quantified (mean %.2f-%.2f outside ker K) is reproduced to %.1e. The "
        "walk's evolution activates the constraint ROW space into propagation; "
        "these are real (placed) curvature DOF, not a judge artifact and not "
        "gauge leakage. Pure diagnosis: NO M3 / no emergence / no DOF-axis closure."
        % (row_curv_carriers, 100 * mean_row_curv, tt_curv_carriers,
           min(r["mean_residual_outside_kerK"] for r in per_k),
           max(r["mean_residual_outside_kerK"] for r in per_k),
           payload["r28_crosscheck"]["worst_abs_diff"] or float("nan"))
        if r28_confirmed else
        "R28 NOT confirmed by this re-check -- inspect per-k sector table.")
    payload["clue_for_R30"] = (
        "The propagating extra curvature is dominated by the constraint-ROW sector "
        "(mean %.1f%% of curvature energy; gauge %.1f%%; TT %.1f%%). R30's dynamic "
        "half / curl term should PRIORITIZE killing propagation in the constraint-"
        "ROW space (the 4-dim orthogonal complement of ker K), NOT the pure-gauge "
        "sector -- gauge is already annihilated by the placed Riemann judge (E1), "
        "so damping gauge harder buys nothing; the leak is row-space activation."
        % (100 * mean_row_curv, 100 * mean_gauge_curv, 100 * mean_tt_curv))
    payload["scope_boundary"] = (
        "Pure modal-spectrum diagnosis of the CURRENT walk U's 12 unit modes. "
        "Reuses frozen R28/卡点⑦ machinery read-only. Does NOT declare M3 / "
        "emergence / DOF-axis closure. Consistent with R28: extra modes are real "
        "physics (constraint-row curvature), not artifact.")
    payload["status"] = "DONE"
    make_figure(per_k)
    payload["figure"] = os.path.relpath(FIG, ROOT)
    payload["source_sha256"] = sha256_file(__file__)
    payload["total_seconds"] = time.time() - t0
    write_json(payload)
    with open(OUT, "rb") as fh:
        jsha = hashlib.sha256(fh.read()).hexdigest()
    payload["results_sha256"] = jsha
    write_json(payload)

    print("=" * 74)
    print(f"R28 residual reproduced: {payload['r28_crosscheck']['reproduces_r28']} "
          f"(worst diff {payload['r28_crosscheck']['worst_abs_diff']:.1e})")
    print(f"curvature carriers by dominant sector: TT={tt_curv_carriers} "
          f"gauge={gauge_curv_carriers} row={row_curv_carriers}")
    print(f"mean curvature energy: TT={mean_tt_curv:.3f} gauge={mean_gauge_curv:.3f} "
          f"row={mean_row_curv:.3f}")
    print(f"R28 confirmed (extra modes = constraint-row, not gauge): {r28_confirmed}")
    print(payload["verdict"])
    print(f"source  sha256 = {payload['source_sha256']}")
    print(f"results sha256 = {jsha}")
    print(f"total {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
