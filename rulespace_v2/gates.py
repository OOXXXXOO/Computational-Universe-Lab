"""rulespace_v2.gates -- G1..G8 门列(v2 极限语言外壳 + v1 I 类判据核,核不重写)。

判据核继承表(任务书 §3;全部只读 import,红线 3:对拍偏差 >1e-12 即视为重写):
  G1 DOF/N_prop : r32_reachability_probe 的 Riemann-SVD 计数核
                  (kerC_basis/build_sectors/inc_matrix/walk_unit_modes/
                   dominant_branch/curvature_subspace, SV_THRESH=0.05 原样);
                  R30 族用 r30_tensor_complex_dynamical 的 leapfrog+placed 判据核;
                  自旋 1 用 r23_maxwell_control 的光子计数核;
                  null_damped/teeth 控制行用 rulespace_gpu.emergence_judge.judge_dof。
  G2 sigma      : r37_residual_scaling_audit 协议全文(sigma.py 外壳)。
  G3 J5 共锥    : rc3ii_relaxation_framework.j5_cocone_across_theta(阈 1e-6);
                  R30 族 = leapfrog 频率 == walk 壳证书;R23 = Lorenz 闭合。
  G4/G5         : rulespace_gpu.tensor_qca.judge_fact2/judge_fact3
                  (h00/phi 比 + 1/r 尾相关;偏折比;tr_sign 炮口)。
  G6 守恒       : R30 族 = de Donder darkness(fp64 门 1e-10,冻结口径);
                  清除列 = r36_r3_verification.part_C(R26 机制)。
  G7 稳定       : BZ 谱半径超增长(门 1e-9);走行族样本按 r36.part_B 预采样复刻。
  G8 epsilon    : epsilon.py(RC3-(ii) R2 冻结手搭计数机)。

极限语言(纲领 §四):谱层机器(G1/G2/G3)逐 L∈{16,24,32,48} 报告——机器是连续 k
谱机器,格子只通过可分辨 k = 2*pi*n/L 进入,因此逐 L = 同方向逐格采样;判据方向的
n 随 L 重标(n_L = round(n_16 * L/16),实际采样 k 如实入册)。实空间时序类控制行
(null_damped/teeth/R30 决定性跑/G4/G5 载体)是冻结 v1 协议的固定尺度对答案行,
verdict 一律记 "CONTROL",不作物理判定。
"""
from __future__ import annotations

import math

import numpy as np

from . import frozen as FZ
from . import epsilon as EPS
from . import sigma as SIG
from .candidate import CandidateV2, GateColumns

L_LIST_DEFAULT = [16, 24, 32, 48]
J5_GATE = 1e-6            # G3 阈(任务书 §3)
G6_DARK_GATE = 1e-10      # R30 de Donder darkness 冻结口径(r30 脚本 verdict 同值)
G7_RADIUS_GATE = 1e-9     # BZ 谱半径超增长门(任务书 §3)
NEWTON_TARGET = (2.0, 0.02)     # G4:2.00 +/- 0.02
EDDINGTON_TARGET = (2.0, 0.02)  # G5:2.00 +/- 0.02(炮行只要求 FAIL)


def _n_at_L(n16, L):
    """判据方向 n 向量随 L 重标(L_ref=16),四舍五入到该格可分辨整数模式。"""
    return [int(round(c * L / 16.0)) for c in n16]


# ==========================================================================
#  G1 -- DOF / N_prop
# ==========================================================================
def g1_frozen_walk(cand: CandidateV2) -> dict:
    """冻结走行族 G1:R32 计数核逐 L 逐判据方向。L=16 行即 R32 冻结读数。"""
    R32 = FZ.mod("r32_reachability_probe")
    per_L = {}
    for L in cand.lattice["L"]:
        rows = []
        for n16 in cand.lattice["judge_k_set"]:
            nL = _n_at_L(n16, L)
            k = np.array(nL, float) * (2 * np.pi / L)
            kap = R32.kappa_placed(k)
            if kap is None:
                rows.append({"n16": list(n16), "nL": nL, "off_band": True})
                continue
            Q_kerC = R32.kerC_basis(kap)
            inc = R32.inc_matrix(kap)
            U10, phases, _ = R32.walk_unit_modes(k, R32.MU0)
            dom = R32.dominant_branch(U10, phases, inc)
            Scurv, nprop, svn = R32.curvature_subspace(U10, phases, inc, dom)
            rmean, rmax = R32.residual_outside(U10, Q_kerC)
            rows.append({"n16": list(n16), "nL": nL,
                         "k": [float(x) for x in k],
                         "N_prop": int(nprop), "curv_sv": svn,
                         "dominant_branch": dom,
                         "leak_resid_mean": rmean, "leak_resid_max": rmax})
        per_L[str(L)] = rows
    # verdict:逐方向逐 L 的 N_prop 是否稳定(极限外壳 = 稳定值,非单尺度读数)
    stable, nprop_by_dir = True, {}
    for di, n16 in enumerate(cand.lattice["judge_k_set"]):
        vals = [per_L[str(L)][di].get("N_prop") for L in cand.lattice["L"]
                if not per_L[str(L)][di].get("off_band")]
        nprop_by_dir[str(tuple(n16))] = vals
        stable = stable and len(set(vals)) == 1
    raw16 = [r.get("N_prop") for r in per_L[str(cand.lattice["L"][0])]]
    return {"raw": {"N_prop_L16_judge_k": raw16},
            "per_L": per_L,
            "verdict": "PASS" if stable else "ambiguous",
            "diagnostics": {"N_prop_by_direction_across_L": nprop_by_dir,
                            "sv_thresh": R32.SV_THRESH,
                            "stable_across_L": bool(stable),
                            "core": "r32_reachability_probe (frozen)"}}


def g1_r30(cand: CandidateV2) -> dict:
    """R30 复形 G1:r30 冻结 leapfrog+placed Riemann-SVD 判据核逐 L。
    L=16 行 = 冻结 decisive run 的逐位复现(同 SEED、同消耗顺序)。"""
    R30M = FZ.mod("r30_tensor_complex_dynamical")
    per_L = {}
    for L in cand.lattice["L"]:
        rng = np.random.default_rng(R30M.SEED)
        rows = []
        for n16 in cand.lattice["judge_k_set"]:
            nL = _n_at_L(n16, L)
            k = np.array(nL, float) * (2 * np.pi / L)
            kap = R30M.kappa_placed(k)
            if kap is None:
                rows.append({"n16": list(n16), "nL": nL, "off_band": True})
                continue
            h0, pi0 = R30M.make_ic("clean_kerK", kap, k, R30M.TRIALS, rng)
            rec = R30M.evolve_components(h0, pi0, k, R30M.T_CLEAN)
            res = R30M.peak_and_svd_placed(rec, kap)
            dark = R30M.dedonder_darkness(rec, kap)
            rmean, rmax = R30M.kerK_residual(rec, kap)
            rows.append({"n16": list(n16), "nL": nL,
                         "N_prop": res["n_prop"], "sv": res.get("sv", []),
                         "dedonder_darkness_max_over_T": dark,
                         "kerK_residual_mean": rmean,
                         "kerK_residual_max": rmax})
        per_L[str(L)] = rows
    stable = True
    for di in range(len(cand.lattice["judge_k_set"])):
        vals = [per_L[str(L)][di].get("N_prop") for L in cand.lattice["L"]
                if not per_L[str(L)][di].get("off_band")]
        stable = stable and len(set(vals)) == 1 and vals and vals[0] == 2
    raw16 = [r.get("N_prop") for r in per_L[str(cand.lattice["L"][0])]]
    return {"raw": {"N_prop_L16_judge_k": raw16},
            "per_L": per_L,
            "verdict": "PASS" if stable else "ambiguous",
            "diagnostics": {"core": "r30_tensor_complex_dynamical (frozen)",
                            "seed": R30M.SEED, "T": R30M.T_CLEAN,
                            "trials": R30M.TRIALS,
                            "stable_across_L_at_2": bool(stable)}}


def r23_remeasure() -> dict:
    """R23 自旋 1 全套证书重测:忠实复刻 r23_maxwell_control 冻结驱动序列
    (同 default_rng(0) 消耗顺序;判据函数 analyze/fmunu_energy/... 只 import)。
    G1 = 光子计数 dim(ker C/gauge)=2;G3 = Lorenz 闭合(C@gauge 湮灭 + 约束衰减)。"""
    R23 = FZ.mod("r23_maxwell_control")
    np_ = np
    rng = np_.random.default_rng(0)
    ks = [np_.array([0.5, 0.0, 0.0]), np_.array([0.35, 0.35, 0.35]),
          np_.array([0.7, 0.2, -0.4])]
    ks += [rng.uniform(-1.1, 1.1, 3) for _ in range(150)]
    ks = [k for k in ks if R23.shell_omega(k) is not None
          and np_.linalg.norm(k) > 1e-2]

    worst_null, worst_cg, worst_dtr = 0.0, 0.0, 0.0
    ranks, dims = set(), set()
    for k in ks:
        kap = R23.kappa_placed(k)
        worst_null = max(worst_null, abs(float(kap @ R23.ETA @ kap)))
        cg, rank, dimq, dtr = R23.analyze(kap)
        worst_cg = max(worst_cg, cg)
        ranks.add(rank)
        dims.add(dimq)
        if dimq == 2:
            worst_dtr = max(worst_dtr, dtr)

    worst_fg, min_ftr = 0.0, np_.inf
    for k in ks[:40]:
        kap = R23.kappa_placed(k)
        worst_fg = max(worst_fg, R23.fmunu_energy(kap, R23.gauge_vec(kap)[:, 0]))
        min_ftr = min(min_ftr, R23.fmunu_energy(kap, R23.transverse_basis(kap)[:, 0]))
        kap_off = kap.copy()
        kap_off[0] *= 1.37
        worst_fg = max(worst_fg, R23.fmunu_energy(kap_off, kap_off))

    kx = np_.array([0.7, 0.2, -0.4])
    w = R23.shell_omega(kx)
    kap = R23.kappa_placed(kx)
    K = R23.constraint_row(kap)
    TR = R23.transverse_basis(kap).astype(complex)
    gamma, T = 0.3, 400
    D = np_.eye(4) - gamma * (K.conj().T @ K)
    step = np_.exp(-1j * w) * D
    A0 = (TR @ (rng.normal(size=2) + 1j * rng.normal(size=2))
          + R23.gauge_vec(kap)[:, 0] * (0.7 + 0.2j)
          + 0.5 * (rng.normal(size=4) + 1j * rng.normal(size=4)))
    A = A0.copy()
    for _t in range(T):
        A = step @ A
    tr_ret = np_.linalg.norm(TR.conj().T @ A) / np_.linalg.norm(TR.conj().T @ A0)
    c0, cf = np_.linalg.norm(K @ A0), np_.linalg.norm(K @ A)

    negs = {}
    for nm, fn in (("unplaced", R23.kappa_unplaced), ("central", R23.kappa_central)):
        kap_n = fn(kx)
        cg, rank, dimq, _ = R23.analyze(kap_n)
        negs[nm] = {"cg": cg, "dim": dimq}

    errP6 = 0.0
    for k in ks[:40]:
        w = R23.shell_omega(k)
        k4 = np_.array([w, k[0], k[1], k[2]])
        kap = R23.kappa_placed(k)
        for mu in range(4):
            s = R23.stencil_symbol(k4, mu, True)
            s *= np_.exp(0.5j * k4[mu])
            s = s / R23.C_CONE if mu == 0 else s
            errP6 = max(errP6, abs(s - 1j * kap[mu]))

    ok = (worst_null < 1e-12 and worst_cg < 1e-12 and ranks == {1}
          and dims == {2} and worst_dtr < 1e-6 and worst_fg < 1e-24
          and min_ftr > 1e-3 and abs(tr_ret - 1.0) < 1e-10
          and cf / c0 < 1e-6
          and all(v["dim"] != 2 or v["cg"] > 1e-3 for v in negs.values())
          and errP6 < 1e-12)
    return {"null": worst_null, "cg": worst_cg, "ranks": sorted(ranks),
            "dims": sorted(dims), "dist_transverse": worst_dtr,
            "F_gauge": worst_fg, "F_transverse_min": float(min_ftr),
            "transverse_retention": float(tr_ret),
            "constraint_decay": float(cf / c0), "negatives": negs,
            "operator_err": errP6, "all_pass": bool(ok),
            "n_k_sample": len(ks)}


def g1_control_judge_dof(rule_name: str) -> dict:
    """null_damped / teeth 控制行:emergence_judge.judge_dof 冻结机器原参数重跑。
    固定尺度(N=16 实空间时序,冻结 v1 协议)=> verdict='CONTROL'。"""
    EJ = FZ.mod("rulespace_gpu.emergence_judge")
    C2 = float(np.cos(np.pi / 3.0) ** 2)
    if rule_name == "null_damped":
        # r28_placed_judge_reverdict PC3 原参数(冻结出处 r28_results.json)
        res = EJ.judge_dof(EJ.make_rule_null_damped(cg2=C2, kappa=0.5), N=16,
                           T=512, trials=8,
                           kmodes=((2, 0, 0), (0, 3, 0), (2, 2, 0), (2, 2, 2)))
    elif rule_name == "teeth_spin2":
        # 卡点⑦ r25_emergence_timeseries teeth 原参数(冻结出处同名结果 JSON)
        res = EJ.judge_dof(EJ.make_rule_spin2(cg2=C2), N=16, T=384, trials=8,
                           kmodes=((2, 0, 0), (0, 0, 2), (2, 2, 0), (2, 2, 2)))
    else:
        raise ValueError(rule_name)
    return {"n_prop_all": res["n_prop_all"],
            "sv_per_k": [e.get("sv", [])[:6] for e in res["per_k"]],
            "stable": res["stable"],
            "core": "rulespace_gpu.emergence_judge.judge_dof (frozen)"}


# ==========================================================================
#  G3 -- J5 共锥 / 闭合
# ==========================================================================
def g3_frozen_walk() -> dict:
    RC3 = FZ.mod("rc3ii_relaxation_framework")
    rows = RC3.j5_cocone_across_theta()
    worst = max(r["max_abs_w_leapfrog_minus_walkshell"] for r in rows)
    return {"raw": {"j5_worst_abs_diff": worst}, "per_theta": rows,
            "verdict": "PASS" if worst < J5_GATE else "FAIL",
            "diagnostics": {"gate": J5_GATE,
                            "core": "rc3ii.j5_cocone_across_theta (frozen)"}}


def g3_r30(cand: CandidateV2) -> dict:
    R30M = FZ.mod("r30_tensor_complex_dynamical")
    kbroad = [tuple(n) for n in cand.lattice["judge_k_set"]] + \
        [(1, 3, 2), (4, 1, 0), (5, 0, 0), (3, 3, 3), (1, 0, 0),
         (6, 2, 1), (0, 5, 2), (2, 4, 3)]
    yc = R30M.yee_certificates(kbroad)
    return {"raw": {"max_freq_minus_shell": yc["max_freq_minus_shell"]},
            "yee_certificates": {k: v for k, v in yc.items() if k != "locality"},
            "verdict": "PASS" if yc["max_freq_minus_shell"] < J5_GATE else "FAIL",
            "diagnostics": {"gate": J5_GATE,
                            "core": "r30.yee_certificates (frozen)"}}


# ==========================================================================
#  G4 / G5 -- Newton / Eddington(v1 裁判组核,tr_sign 炮口)
# ==========================================================================
def g4_g5_newton_eddington(tr_sign: float = 1.0) -> dict:
    """tensor_qca.judge_fact2/judge_fact3 冻结裁判(fp64)。tr_sign=0 即炮。"""
    TQ = FZ.mod("rulespace_gpu.tensor_qca")
    f2 = TQ.judge_fact2(L=40, sigma=3.5, G=1.0, cg2=0.25, gamma=0.06,
                        tr_sign=tr_sign)
    f3 = TQ.judge_fact3(f2, L=40, sigma=3.5, G=1.0)
    f2c = {k: v for k, v in f2.items() if not k.startswith("_")}
    newton_ok = abs(f2["h00_over_phi"] - NEWTON_TARGET[0]) < NEWTON_TARGET[1]
    edd_ok = abs(f3["evolved_field_ratio"] - EDDINGTON_TARGET[0]) < EDDINGTON_TARGET[1]
    return {"tr_sign": tr_sign, "judge2_newton": f2c, "judge3_eddington": f3,
            "newton_ratio": f2["h00_over_phi"],
            "deflection_ratio": f3["evolved_field_ratio"],
            "newton_in_target": bool(newton_ok),
            "eddington_in_target": bool(edd_ok),
            "pass_G4": bool(f2["pass"]), "pass_G5": bool(f3["pass"]),
            "core": "rulespace_gpu.tensor_qca.judge_fact2/3 (frozen)"}


# ==========================================================================
#  G6 / G7 -- 守恒清除列 + 稳定
# ==========================================================================
def g6_r36_clearance(kappa_work: float = 0.02) -> dict:
    """R26 机制清除列:r36_r3_verification.part_C 原样重跑(确定性,无 rng)。"""
    R36M = FZ.mod("r36_r3_verification")
    C = R36M.part_C(kappa_work)
    return {"raw": {"tau_per_k": [r["tau_clear"] for r in C["per_k"]],
                    "tau_spread_ratio": C["tau_spread_ratio"],
                    "retained_clearable_max": C["retained_clearable_max"]},
            "part_C": C,
            "verdict": "PASS" if (C["all_cleared"] and C["retained_gate_1e-3_all"]
                                  and C["negctrl_diffusion_tau"] is None) else "FAIL",
            "diagnostics": {"core": "r36_r3_verification.part_C (frozen)"}}


def g7_walk_bz_radius() -> dict:
    """G7 稳定:冻结走行符号 BZ 谱半径,样本复刻 r36.part_B 预采样
    (default_rng(3),同消耗顺序),门 = 1 + G7_RADIUS_GATE。"""
    R36M = FZ.mod("r36_r3_verification")
    D1 = FZ.mod("r25_dynamic_symbol")
    N = R36M.N
    rng = np.random.default_rng(3)
    kx = [np.array(kl, float) * (2 * np.pi / N) for kl in R36M.KJ]
    kx += [np.array(kl, float) * (2 * np.pi / N)
           for kl in [(0, 1, 0), (1, 1, 1), (4, 0, 0), (4, 4, 0), (5, 3, 1)]]
    kx += [rng.uniform(-np.pi, np.pi, 3) for _ in range(50)]
    rmax, nsamp = 0.0, 0
    for k in kx:
        kap = R36M.kappa_placed(k, R36M.C0)
        if kap is None:
            continue
        M = D1.damped_map(k, R36M.MU0)[0]
        rmax = max(rmax, float(np.max(np.abs(np.linalg.eigvals(M)))))
        nsamp += 1
    return {"raw": {"walk_bz_spectral_radius_max": rmax, "n_bz_sample": nsamp},
            "verdict": "PASS" if rmax < 1.0 + G7_RADIUS_GATE else "FAIL",
            "diagnostics": {"gate": G7_RADIUS_GATE,
                            "sample": "r36.part_B pre-loop 复刻 (rng(3))",
                            "core": "r25_dynamic_symbol.damped_map (frozen)"}}


# ==========================================================================
#  evaluate_v2_candidate -- 统一入口
# ==========================================================================
def evaluate_v2_candidate(cand: CandidateV2) -> GateColumns:
    """任意 (复形族成员 x 耦合 x epsilon x sigma) 候选 -> 全部门列读数。
    每门:原始读数、逐 L 表 / 极限外壳拟合 (A, alpha, dAIC)、verdict、诊断。
    任何 PASS/FAIL verdict 不由单一固定尺度读数产生;固定尺度控制行记 CONTROL。"""
    gc = GateColumns(cand_id=cand.cand_id or cand.family,
                     family=cand.family, sector=cand.sector)
    fz = FZ.verify_frozen()
    gc.certificates["frozen_sha256"] = fz
    if not fz["pass"]:
        gc.notes.append("ABORT: 冻结件 sha256 不匹配(红线 1)")
        return gc

    fam = cand.family
    if fam in ("frozen_walk",):
        RC = FZ.mod("rc1a_tensor_index_scan")
        cert = RC.faithfulness_certificate()
        gc.certificates["rc1a_faithfulness"] = cert
        if not cert["PASS"]:
            gc.notes.append("ABORT: RC1a 忠实性证书 FAIL")
            return gc
        g1 = g1_frozen_walk(cand)
        gc.set_gate("G1_dof_nprop", g1["raw"], g1["verdict"], per_L=g1["per_L"],
                    diagnostics=g1["diagnostics"])
        # M0' 整改令 1:主判 y = 不变量 max sin θ(替代 resid_max);
        # R37 拟合协议(窗/剔点/AIC)原样;旧口径拟合保留为 legacy 注记。
        fits = SIG.direction_fits_invariant()
        fits_legacy = SIG.direction_fits()
        worst_band = [f["band_D3"] for f in fits.values()]
        gc.set_gate("G2_sigma_scaling",
                    {d: {"A": f["A"], "alpha": f["alpha"],
                         "dAIC": f["dAIC_const_minus_power"],
                         "verdict": f["verdict"], "band_D3": f["band_D3"],
                         "y_observable": f["y_observable"]}
                     for d, f in fits.items()},
                    "ambiguous" if any(f["verdict"] == "ambiguous"
                                       for f in fits.values())
                    else ("FAIL" if any(f["verdict"] == "FAIL"
                                        for f in fits.values()) else "PASS"),
                    limit_fit={d: (f["A"], f["alpha"],
                                   f["dAIC_const_minus_power"])
                               for d, f in fits.items()},
                    diagnostics={"protocol": ("R37 拟合协议原样(冻结代码对象);"
                                              "y = 不变量 max sinθ(整改令 1)"),
                                 "bands_D3": worst_band,
                                 "calibration_16cube_invariant":
                                     SIG.calibration_16cube_invariant(),
                                 "legacy_fits_basis_dependent": {
                                     d: {"A": f["A"], "alpha": f["alpha"],
                                         "dAIC": f["dAIC_const_minus_power"],
                                         "verdict": f["verdict"],
                                         "note": "旧口径 resid_max(基依赖,"
                                                 "环境绑定,非判据)"}
                                     for d, f in fits_legacy.items()},
                                 "calibration_16cube_legacy":
                                     SIG.calibration_16cube()})
        g3 = g3_frozen_walk()
        gc.set_gate("G3_j5_cocone", g3["raw"], g3["verdict"],
                    per_L=g3["per_theta"], diagnostics=g3["diagnostics"])
        g6 = (g6_r36_clearance(cand.coupling.get("kappa", 0.02))
              if cand.coupling and cand.coupling.get("variant") == "r26_clearance"
              else None)
        if g6 is not None:
            gc.set_gate("G6_conservation", g6["raw"], g6["verdict"],
                        diagnostics={**g6["diagnostics"],
                                     "part_C": g6["part_C"]})
            g7 = g7_walk_bz_radius()
            gc.set_gate("G7_stability", g7["raw"], g7["verdict"],
                        diagnostics=g7["diagnostics"])
        e = EPS.epsilon_for_candidate(cand)
        gc.set_gate("G8_epsilon",
                    {"epsilon_dof_min_max": e.get("epsilon_dof_min_max"),
                     "epsilon_E_min_max": e.get("epsilon_E_min_max"),
                     "anchor_range_invariant": e.get("anchor_range_invariant"),
                     "anchor_range_legacy_D1": e.get("anchor_range_legacy_D1"),
                     "basis_stable": e.get("basis_stable")},
                    "PASS" if e.get("within_anchor_range") else "ambiguous",
                    diagnostics=e)

    elif fam == "R30":
        g1 = g1_r30(cand)
        gc.set_gate("G1_dof_nprop", g1["raw"], g1["verdict"], per_L=g1["per_L"],
                    diagnostics=g1["diagnostics"])
        g3 = g3_r30(cand)
        gc.set_gate("G3_j5_cocone", g3["raw"], g3["verdict"],
                    diagnostics={**g3["diagnostics"], **g3["yee_certificates"]})
        # G6:decisive run 的 de Donder darkness(逐 L 已在 G1 per_L 中)
        darks = {L: [r.get("dedonder_darkness_max_over_T")
                     for r in rows if not r.get("off_band")]
                 for L, rows in g1["per_L"].items()}
        worst_dark = max(max(v) for v in darks.values() if v)
        gc.set_gate("G6_conservation", {"dedonder_darkness_worst": worst_dark},
                    "PASS" if worst_dark < G6_DARK_GATE else "FAIL",
                    per_L=darks, diagnostics={"gate": G6_DARK_GATE})
        # G7:leapfrog 严格酉(|eig|-1)
        yc = g3["yee_certificates"]
        gc.set_gate("G7_stability",
                    {"max_abs_eig_minus_1": yc["max_abs_eig_minus_1"]},
                    "PASS" if yc["max_abs_eig_minus_1"] < G7_RADIUS_GATE else "FAIL",
                    diagnostics={"gate": G7_RADIUS_GATE})
        e = EPS.epsilon_for_candidate(cand)
        gc.set_gate("G8_epsilon", {"epsilon_dof": e["epsilon_dof"]},
                    "PASS", diagnostics=e)

    elif fam == "yee_maxwell":
        r = r23_remeasure()
        gc.set_gate("G1_dof_nprop",
                    {"photon_dims": r["dims"], "rank_C": r["ranks"],
                     "dist_transverse": r["dist_transverse"]},
                    "PASS" if r["dims"] == [2] else "FAIL",
                    diagnostics={"core": "r23_maxwell_control (frozen)",
                                 "note": ("符号层全 BZ 采样(153 k 点连续采样,"
                                          "格子无关);negatives 有牙"),
                                 "negatives": r["negatives"]})
        gc.set_gate("G3_j5_cocone",
                    {"lorenz_C_gauge_annihilation": r["cg"],
                     "constraint_decay": r["constraint_decay"],
                     "transverse_retention": r["transverse_retention"]},
                    "PASS" if (r["cg"] < 1e-12 and r["constraint_decay"] < 1e-6)
                    else "FAIL",
                    diagnostics={"F_gauge": r["F_gauge"],
                                 "operator_err": r["operator_err"],
                                 "all_pass_v1_gate": r["all_pass"]})
        e = EPS.epsilon_for_candidate(cand)
        gc.set_gate("G8_epsilon", {"epsilon_dof": e["epsilon_dof"]},
                    "PASS", diagnostics=e)
        gc.certificates["r23_full"] = r

    elif fam in ("null_damped", "teeth_spin2"):
        r = g1_control_judge_dof(fam)
        gc.set_gate("G1_dof_nprop", {"n_prop_all": r["n_prop_all"]},
                    "CONTROL", per_L={"16": r["n_prop_all"]},
                    diagnostics={**r, "note": ("固定尺度冻结 v1 时序协议控制行;"
                                               "不作物理判定(纲领 §四)")})

    elif fam == "tensor_qca":
        tr_sign = 1.0
        if cand.coupling:
            tr_sign = float(cand.coupling.get("tr_sign", 1.0))
        r = g4_g5_newton_eddington(tr_sign)
        v4 = "CONTROL" if tr_sign != 1.0 else ("PASS" if r["pass_G4"] else "FAIL")
        v5 = "CONTROL" if tr_sign != 1.0 else ("PASS" if r["pass_G5"] else "FAIL")
        gc.set_gate("G4_newton",
                    {"h00_over_phi": r["newton_ratio"],
                     "in_target_2.00+-0.02": r["newton_in_target"],
                     "v1_gate_pass": r["pass_G4"]},
                    v4, diagnostics=r["judge2_newton"])
        gc.set_gate("G5_eddington",
                    {"deflection_ratio": r["deflection_ratio"],
                     "in_target_2.00+-0.02": r["eddington_in_target"],
                     "v1_gate_pass": r["pass_G5"]},
                    v5, diagnostics=r["judge3_eddington"])
        gc.certificates["tr_sign"] = tr_sign

    else:
        raise ValueError(f"family {fam!r} not implemented in M0'")

    return gc
