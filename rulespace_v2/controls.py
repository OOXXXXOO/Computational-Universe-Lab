"""rulespace_v2.controls -- M0' 控制矩阵(任务书 §4,8 行;判据/tol 在此写死,运行后不改)。

每行 = 用新评估器 evaluate_v2_candidate 重测该对象,与冻结 JSON 已知答案比对
(红线 5:v1 证书不得直接填 v2 门列——比对对象是"重测值 vs 冻结值")。

| # | 控制对象        | 期望(冻结出处)                                        | 关键比对 | tol      |
|---|-----------------|--------------------------------------------------------|----------|----------|
| 1 | R30 复形        | N_prop=2 断崖;eps_DOF=0(r30_results.json)            | G1 svn   | 1e-12    |
| 2 | R23 Yee/Maxwell | 光子 2 + Lorenz 闭合;eps_DOF=1(r23_results.json)     | G1/G3    | 1e-12    |
| 3 | null_damped     | N_prop=2,sv 断崖 ~1e4(r28_results.json PC3)          | G1       | 1e-10    |
| 4 | teeth 裸波      | N_prop=6(r25_emergence_timeseries_results.json)       | G1       | 精确     |
| 5 | 冻结走行族      | N_prop=[4,4,5,5];泄漏 34-49%;eps∈[0,0.25](r32/rc3ii/r36)| G1/G8 | 1e-13(walk 因子逐位) |
| 6 | tr_sign=0 炮    | Newton/偏折按 v1 记录击穿(总账 43c:h00/phi→4,偏折→1)| G4/G5    | 判 FAIL  |
| 7 | R36 (a) 清除件  | tau∈[39,62]、k-无关 1.59x、AC 残余 ≤2.3e-15(r36)      | G6/G7    | 1e-12    |
| 8 | R37 16^3 校准   | 三判据 k resid 与 rc3ii_results.json diff=0.0          | G2       | 0.0 逐位 |

行 6 说明:v1 记录是总账 43c 的文字记录(tr_sign=0 → 判据2 h00/phi: 2→4、判据3 偏折:
2→1,均 FAIL),无独立冻结 JSON 数值;本行判据 = 两裁判 v1 门均 FAIL,且读数与记录
方向一致(h00/phi 落在 4 附近、偏折落在 1 附近,窗 ±0.1,写死)。

M0' PASS = 8/8 全落位。任一不落位 => 停手(禁调 tol、禁改核),写追因小报告报车道A。
"""
from __future__ import annotations

import json
import os

import numpy as np

from . import frozen as FZ
from . import gates as G
from .candidate import CandidateV2

# ---- tol(写死;运行后不得回改) -----------------------------------------
TOL = {
    "row1_r30": 1e-12,
    "row2_r23": 1e-12,
    "row3_null_damped": 1e-10,
    "row4_teeth": 0.0,          # 整数精确
    "row5_frozen_walk": 1e-13,  # walk 因子逐位;浮点比对同 tol,计数精确
    "row6_tr_sign": None,       # 判 FAIL 即可(读数窗 ±0.1 对 v1 记录方向)
    "row7_r36": 1e-12,
    "row8_r37_calib": 0.0,      # 逐位
}
ROW6_H00_RECORD, ROW6_DEFL_RECORD, ROW6_WIN = 4.0, 1.0, 0.1


def _load(rel):
    with open(os.path.join(FZ.ROOT, rel), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _maxdiff(a, b):
    """标量/嵌套列表的最大逐元素绝对偏差。"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.shape != b.shape:
        return float("inf")
    return float(np.max(np.abs(a - b))) if a.size else 0.0


# ---- 控制候选定义(新评估器的输入) ---------------------------------------
def control_candidates() -> dict:
    L4 = [16, 24, 32, 48]
    return {
        "row1_r30": CandidateV2(
            sector="spin2", cand_id="ctrl_R30",
            geometry={"family": "R30", "params": {"dt": "c=cos(pi/3)"}},
            hand_built={"dof_indices": "all"},
            lattice={"L": L4, "judge_k_set": [[2, 0, 0], [0, 3, 0], [2, 2, 0],
                                              [2, 2, 2]],
                     "ray_directions": [[1, 0, 0], [1, 1, 0], [1, 1, 1]]}),
        "row2_r23": CandidateV2(
            sector="spin1", cand_id="ctrl_R23",
            geometry={"family": "yee_maxwell", "params": {}},
            hand_built={"dof_indices": None},
            lattice={"L": L4, "judge_k_set": [[2, 0, 0]],
                     "ray_directions": [[1, 0, 0]]}),
        "row3_null_damped": CandidateV2(
            sector="spin2", cand_id="ctrl_null_damped",
            geometry={"family": "null_damped", "params": {"kappa": 0.5}},
            lattice={"L": [16], "judge_k_set": [[2, 0, 0], [0, 3, 0], [2, 2, 0],
                                                [2, 2, 2]],
                     "ray_directions": []}),
        "row4_teeth": CandidateV2(
            sector="spin2", cand_id="ctrl_teeth",
            geometry={"family": "teeth_spin2", "params": {}},
            lattice={"L": [16], "judge_k_set": [[2, 0, 0], [0, 0, 2], [2, 2, 0],
                                                [2, 2, 2]],
                     "ray_directions": []}),
        "row5_frozen_walk": CandidateV2(
            sector="spin2", cand_id="ctrl_frozen_walk",
            geometry={"family": "frozen_walk",
                      "params": {"theta": "pi/3", "dm": 0.0, "c": 0.5}},
            hand_built={"dof_indices": "measure_rc3ii_R2"},
            lattice={"L": L4, "judge_k_set": [[2, 0, 0], [0, 3, 0], [2, 2, 0],
                                              [2, 2, 2]],
                     "ray_directions": [[1, 0, 0], [1, 1, 0], [1, 1, 1]]}),
        "row6_tr_sign": CandidateV2(
            sector="spin2", cand_id="ctrl_tr_sign0",
            geometry={"family": "tensor_qca", "params": {"L": 40}},
            coupling={"variant": "cannon", "tr_sign": 0.0},
            lattice={"L": [40], "judge_k_set": [], "ray_directions": []}),
        "row7_r36": CandidateV2(
            sector="spin2", cand_id="ctrl_r36_clearance",
            geometry={"family": "frozen_walk",
                      "params": {"theta": "pi/3", "dm": 0.0, "c": 0.5}},
            coupling={"variant": "r26_clearance", "kappa": 0.02},
            hand_built={"dof_indices": "measure_rc3ii_R2"},
            lattice={"L": L4, "judge_k_set": [[2, 0, 0], [0, 3, 0], [2, 2, 0],
                                              [2, 2, 2]],
                     "ray_directions": [[1, 0, 0], [1, 1, 0], [1, 1, 1]]}),
        # row8 用 sigma 外壳直接出读数(G2 校准),无独立候选对象
    }


# ---- 各行比对器 ------------------------------------------------------------
def row1_r30(gc) -> dict:
    frozen = _load("data/results/r30_results.json")["decisive_run"]
    tol = TOL["row1_r30"]
    remeas = gc.gates["G1_dof_nprop"]["per_L"]["16"]
    n_re = [r["N_prop"] for r in remeas]
    diffs = [_maxdiff(r["sv"], f["sv"]) for r, f in zip(remeas, frozen["per_k"])]
    eps = gc.gates["G8_epsilon"]["raw"]["epsilon_dof"]
    ok = (n_re == frozen["n_prop_seq"] == [2, 2, 2, 2]
          and max(diffs) <= tol and eps == 0.0)
    return {"name": "R30 复形 (G1 svn 断崖 + eps_DOF=0)",
            "remeasured": {"n_prop_seq": n_re, "epsilon_dof": eps,
                           "sv_L16": [r["sv"] for r in remeas]},
            "frozen": {"n_prop_seq": frozen["n_prop_seq"],
                       "epsilon_dof_anchor": 0.0,
                       "source": "r30_results.json decisive_run"},
            "tol": tol, "max_abs_diff": max(diffs), "pass": bool(ok)}


def row2_r23(gc) -> dict:
    frozen = _load("data/results/r23_results.json")
    tol = TOL["row2_r23"]
    r = gc.certificates["r23_full"]
    keys = ["null", "cg", "dist_transverse", "F_gauge", "F_transverse_min",
            "transverse_retention", "constraint_decay", "operator_err"]
    diffs = {k: abs(r[k] - frozen[k]) for k in keys}
    eps = gc.gates["G8_epsilon"]["raw"]["epsilon_dof"]
    ok = (r["dims"] == frozen["dims"] == [2] and r["ranks"] == frozen["ranks"]
          and max(diffs.values()) <= tol and r["all_pass"]
          and frozen["all_pass"] and eps == 1.0)
    return {"name": "R23 Yee/Maxwell (光子 2 + Lorenz 闭合 + eps_DOF=1)",
            "remeasured": {k: r[k] for k in keys + ["dims", "ranks", "all_pass"]}
            | {"epsilon_dof": eps},
            "frozen": {k: frozen[k] for k in keys + ["dims", "ranks", "all_pass"]}
            | {"epsilon_dof_anchor": 1.0, "source": "r23_results.json"},
            "tol": tol, "max_abs_diff": max(diffs.values()), "per_key_diff": diffs,
            "pass": bool(ok)}


def row3_null_damped(gc) -> dict:
    frozen = _load("data/results/r28_results.json")["controls"][
        "null_damped_ideal_shellmatched"]
    tol = TOL["row3_null_damped"]
    g1 = gc.gates["G1_dof_nprop"]
    n_re = g1["raw"]["n_prop_all"]
    sv_re = g1["diagnostics"]["sv_per_k"]
    diffs = [_maxdiff(a, b) for a, b in zip(sv_re, frozen["sv"])]
    cliffs = [sv[1] / sv[2] for sv in sv_re]      # sv2/sv3 断崖(诊断)
    ok = (n_re == frozen["n_prop"] == [2, 2, 2, 2] and max(diffs) <= tol)
    return {"name": "null_damped 正控 (N_prop=2, sv 断崖 ~1e4+)",
            "remeasured": {"n_prop": n_re, "sv": sv_re,
                           "sv2_over_sv3_cliff": cliffs},
            "frozen": {"n_prop": frozen["n_prop"], "sv": frozen["sv"],
                       "source": "r28_results.json controls.null_damped_ideal_shellmatched"},
            "tol": tol, "max_abs_diff": max(diffs), "pass": bool(ok)}


def row4_teeth(gc) -> dict:
    frozen = _load("data/results/r25_emergence_timeseries_results.json")[
        "teeth_bare_wave"]
    n_re = gc.gates["G1_dof_nprop"]["raw"]["n_prop_all"]
    ok = (n_re == frozen["n_prop_all"] == [6, 6, 6, 6])
    return {"name": "teeth 裸波负控 (N_prop=6 精确)",
            "remeasured": {"n_prop_all": n_re},
            "frozen": {"n_prop_all": frozen["n_prop_all"],
                       "source": "r25_emergence_timeseries_results.json teeth_bare_wave"},
            "tol": "exact", "max_abs_diff": 0 if ok else "mismatch",
            "pass": bool(ok)}


def row5_frozen_walk(gc) -> dict:
    tol = TOL["row5_frozen_walk"]
    r32f = _load("data/results/r32_results.json")["per_k"]
    rc3f = _load("data/results/rc3ii_results.json")[
        "candidate_R2_emergent_matter"]["per_k"]
    r36f = _load("data/results/r36_results.json")["certificates"][
        "walk_factor_max_diff_vs_frozen_D1"]
    g1 = gc.gates["G1_dof_nprop"]["per_L"]["16"]
    n_re = [r["N_prop"] for r in g1]
    n_fr = [p["N_prop_curv"] for p in r32f]
    leak_re = [r["leak_resid_mean"] for r in g1]
    leak_fr = [p["mean_resid_outside_kerC"] for p in r32f]
    leak_diff = max(abs(a - b) for a, b in zip(leak_re, leak_fr))
    sv_diff = max(_maxdiff(r["curv_sv"], p["curv_sv"])
                  for r, p in zip(g1, r32f))
    # walk 因子逐位(r36 证书同款:16 个随机 k,rng(7))
    RC = FZ.mod("rc1a_tensor_index_scan")
    D1 = FZ.mod("r25_dynamic_symbol")
    rng = np.random.default_rng(7)
    wmax = 0.0
    for _ in range(16):
        nv = rng.uniform(-3.0, 3.0, 3)
        wmax = max(wmax, float(np.abs(
            RC.damped_map_p(nv, RC.MU0, RC.TH0, 0.0, RC.C0)
            - D1.damped_map(nv, RC.MU0)[0]).max()))
    # G8:j_hand / epsilon
    e = gc.gates["G8_epsilon"]["diagnostics"]
    j_re = {k: v["j_hand"] for k, v in e["per_k"].items()}
    j_fr = {k: v["min_handbuilt_DOF_for_2"] for k, v in rc3f.items()}
    eps_rng = e["epsilon_dof_min_max"]
    ok = (n_re == n_fr == [4, 4, 5, 5]
          and leak_diff <= tol and sv_diff <= tol
          and 0.34 <= min(leak_re) and max(leak_re) <= 0.49
          and wmax <= tol and abs(wmax - r36f) <= tol
          and j_re == j_fr
          and 0.0 - 1e-12 <= eps_rng[0] and eps_rng[1] <= 0.25 + 1e-12)
    return {"name": "冻结走行族 (N_prop=[4,4,5,5] + 泄漏 34-49% + eps∈[0,0.25] + walk 因子逐位)",
            "remeasured": {"N_prop": n_re, "leak_resid_mean": leak_re,
                           "walk_factor_max_diff": wmax, "j_hand": j_re,
                           "epsilon_dof_min_max": eps_rng},
            "frozen": {"N_prop": n_fr, "leak_resid_mean": leak_fr,
                       "walk_factor_max_diff": r36f, "j_hand": j_fr,
                       "epsilon_anchor_range": [0.0, 0.25],
                       "source": "r32/rc3ii/r36 results.json"},
            "tol": tol,
            "max_abs_diff": max(leak_diff, sv_diff, wmax, abs(wmax - r36f)),
            "pass": bool(ok)}


def row6_tr_sign(gc) -> dict:
    g4, g5 = gc.gates["G4_newton"], gc.gates["G5_eddington"]
    h00 = g4["raw"]["h00_over_phi"]
    defl = g5["raw"]["deflection_ratio"]
    fails = (not g4["raw"]["v1_gate_pass"]) and (not g5["raw"]["v1_gate_pass"])
    dir_ok = (abs(h00 - ROW6_H00_RECORD) < ROW6_WIN
              and abs(defl - ROW6_DEFL_RECORD) < ROW6_WIN)
    ok = fails and dir_ok
    return {"name": "tr_sign=0 炮 (Newton/偏折按 v1 记录击穿)",
            "remeasured": {"h00_over_phi": h00, "deflection_ratio": defl,
                           "G4_v1_gate_pass": g4["raw"]["v1_gate_pass"],
                           "G5_v1_gate_pass": g5["raw"]["v1_gate_pass"]},
            "frozen": {"v1_record": "总账 43c: tr_sign=0 → h00/phi→4, 偏折→1, 双 FAIL",
                       "h00_expected_near": ROW6_H00_RECORD,
                       "deflection_expected_near": ROW6_DEFL_RECORD,
                       "window": ROW6_WIN},
            "tol": "judged-FAIL (读数窗 ±0.1)",
            "max_abs_diff": max(abs(h00 - ROW6_H00_RECORD),
                                abs(defl - ROW6_DEFL_RECORD)),
            "pass": bool(ok)}


def row7_r36(gc) -> dict:
    tol = TOL["row7_r36"]
    frozen = _load("data/results/r36_results.json")
    fC = frozen["part_C_a_half_realspace"]
    fB = frozen["part_B_stability_frontier"]
    g6, g7 = gc.gates["G6_conservation"], gc.gates["G7_stability"]
    tau_re = g6["raw"]["tau_per_k"]
    tau_fr = [r["tau_clear"] for r in fC["per_k"]]
    spread_diff = abs(g6["raw"]["tau_spread_ratio"] - fC["tau_spread_ratio"])
    ac_re = g6["raw"]["retained_clearable_max"]
    ac_diff = abs(ac_re - fC["retained_clearable_max"])
    rad_re = g7["raw"]["walk_bz_spectral_radius_max"]
    rad_diff = abs(rad_re - fB["walk_own_spectral_radius_max"])
    ok = (tau_re == tau_fr and all(39 <= t <= 62 for t in tau_re)
          and spread_diff <= tol and ac_diff <= tol
          and ac_re <= 2.4e-15                      # 冻结值 2.3275e-15 的入册界
          and rad_diff <= tol and g6["verdict"] == "PASS"
          and g7["verdict"] == "PASS")
    return {"name": "R36 (a) 清除件 (tau∈[39,62], k-无关 1.59x, AC 残余, BZ 谱半径)",
            "remeasured": {"tau_per_k": tau_re,
                           "tau_spread_ratio": g6["raw"]["tau_spread_ratio"],
                           "retained_clearable_max": ac_re,
                           "walk_bz_spectral_radius_max": rad_re},
            "frozen": {"tau_per_k": tau_fr,
                       "tau_spread_ratio": fC["tau_spread_ratio"],
                       "retained_clearable_max": fC["retained_clearable_max"],
                       "walk_own_spectral_radius_max":
                           fB["walk_own_spectral_radius_max"],
                       "source": "r36_results.json part_C/part_B"},
            "tol": tol,
            "max_abs_diff": max(spread_diff, ac_diff, rad_diff),
            "pass": bool(ok)}


def row8_r37_calib() -> dict:
    """G2 sigma 机器 16^3 校准:重测三判据 k 的 resid min/max,与
    rc3ii_results.json 逐位比对(diff 必须 0.0);另附 R37 方向拟合逐位对拍。"""
    from . import sigma as SIG_
    tol = TOL["row8_r37_calib"]
    rc3f = _load("data/results/rc3ii_results.json")[
        "candidate_R3_exact_constraint"]["per_k"]
    remeas = SIG_.calibration_16cube()
    diffs = {}
    for kstr, v in remeas.items():
        lo, hi = rc3f[kstr]["resid_outside_kerC_min_max"]
        diffs[kstr] = [abs(v["resid_min"] - lo), abs(v["resid_max"] - hi)]
    worst = max(max(d) for d in diffs.values())
    # 方向拟合对拍(诊断级,同 0 偏差预期;确定性协议)
    r37f = _load("data/results/r37_results.json")["direction_fits"]
    fits = SIG_.direction_fits()
    fit_diff = {}
    for J in r37f:
        d = J["direction"]
        m1 = J["power_model"]
        f = fits[d]
        fit_diff[d] = max(abs(f["A"] - m1["A"]), abs(f["alpha"] - m1["alpha"]),
                          abs(f["dAIC_const_minus_power"]
                              - J["dAIC_const_minus_power"]))
    worst_fit = max(fit_diff.values())
    ok = (worst <= tol and worst_fit <= 1e-12)
    return {"name": "R37 16^3 校准 (三判据 k resid 逐位 + 方向拟合对拍)",
            "remeasured": {"calib": remeas,
                           "fits": {d: {"A": f["A"], "alpha": f["alpha"],
                                        "dAIC": f["dAIC_const_minus_power"],
                                        "verdict": f["verdict"],
                                        "band_D3": f["band_D3"]}
                                    for d, f in fits.items()}},
            "frozen": {"calib": {k: v["resid_outside_kerC_min_max"]
                                 for k, v in rc3f.items()},
                       "source": "rc3ii_results.json candidate_R3 / r37_results.json"},
            "tol": tol, "max_abs_diff": worst,
            "fit_max_abs_diff": worst_fit, "pass": bool(ok)}
