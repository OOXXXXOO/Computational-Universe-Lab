"""rulespace_v2.controls -- M0' 控制矩阵(任务书 §4,8 行;判据/tol 在此写死,运行后不改)。

每行 = 用新评估器 evaluate_v2_candidate 重测该对象,与冻结 JSON 已知答案比对
(红线 5:v1 证书不得直接填 v2 门列——比对对象是"重测值 vs 冻结值")。

| # | 控制对象        | 期望(冻结出处)                                        | 关键比对 | tol      |
|---|-----------------|--------------------------------------------------------|----------|----------|
| 1 | R30 复形        | N_prop=2 断崖;eps_DOF=0(r30_results.json)            | G1 svn   | 1e-12    |
| 2 | R23 Yee/Maxwell | 光子 2 + Lorenz 闭合;eps_DOF=1(r23_results.json)     | G1/G3    | 1e-12    |
| 3 | null_damped     | N_prop=2,sv 断崖 ~1e4(r28_results.json PC3)          | G1       | 1e-10    |
| 4 | teeth 裸波      | N_prop=6(r25_emergence_timeseries_results.json)       | G1       | 精确     |
| 5 | 冻结走行族      | 逐位档:N_prop=[4,4,5,5] + walk 因子逐位(r32/r36);不变量档:j_hand_inv/主角谱基稳健 | G1/G8 | 整数精确 + 1e-13 + 漂移 1e-12 |
| 6 | tr_sign=0 炮    | Newton/偏折按 v1 记录击穿(总账 43c:h00/phi→4,偏折→1)| G4/G5    | 判 FAIL  |
| 7 | R36 (a) 清除件  | tau∈[39,62]、k-无关 1.59x、AC 残余 ≤2.3e-15(r36)      | G6/G7    | 1e-12    |
| 8 | R37 16^3 校准   | 不变量档:三判据 k (max sinθ, frob) 复现复核 §三判决数 + 基稳健 | G2  | sin 1e-4/frob 1e-3(显示精度)+ 漂移 1e-12 |

行 6 说明:v1 记录是总账 43c 的文字记录(tr_sign=0 → 判据2 h00/phi: 2→4、判据3 偏折:
2→1,均 FAIL),无独立冻结 JSON 数值;本行判据 = 两裁判 v1 门均 FAIL,且读数与记录
方向一致(h00/phi 落在 4 附近、偏折落在 1 附近,窗 ±0.1,写死)。

--- M0' 整改(2026-07-26,复核 §四 整改令 3/4;判据写死,运行后不回改)--------------
行5/行8 判据改口:逐位档只保留真逐位量(walk 因子、N_prop 整数列、hash);
连续读数改为**不变量**(主角谱/max sinθ/frob 泄漏/不变量 j_hand),比对纪律:
  * 跨环境可移植判据 = 不变量宿主/沙盒双跑 diff ≤ 1e-12(沙盒侧由车道A 复核执行;
    本模块在 JSON 里入册宿主参考值 + environment 字段 + cross_environment_status
    ="待沙盒确认");
  * 基稳健性自检列:对简并子空间做 3 次固定种子簇内酉旋转(invariants.ROT_SEEDS),
    不变量漂移 ≤ 1e-12(宿主侧本模块执行);
  * 旧口径逐模统计(resid_min/max、贪心 j_hand、逐列 sv 比对)降级为 legacy 诊断
    (环境绑定,as-recorded,不参与 pass 判定——它们正是复核抓出的非观测量)。
行2 加注:冻结 r23_results.json 环境谱系 = 沙盒系(与沙盒逐位 0.0,与宿主差 1.8e-15
ULP 级;复核 ② 确证,lane B 原标注诚实且正确)。
行8 判决参照(复核 §三,沙盒判决实验不变量列,写死):
  (2,0,0): max sinθ=1.0000, frob=1.035;(2,2,0): 0.1948, 0.304;(2,2,2): 0.1493, 0.211。

M0' 整改后 PASS 口径:宿主 8/8 + 基稳健自检全过 ≠ 收口;收口须双环境 8/8
(沙盒双跑由车道A 复核时执行)。任一不落位 => 停手(禁调 tol、禁改核),报车道A。
"""
from __future__ import annotations

import json
import math
import os

import numpy as np

from . import frozen as FZ
from . import gates as G
from . import invariants as INV
from . import sigma as SIG
from . import epsilon as EPS
from .candidate import CandidateV2

# ---- tol(写死;运行后不得回改) -----------------------------------------
TOL = {
    "row1_r30": 1e-12,
    "row2_r23": 1e-12,
    "row3_null_damped": 1e-10,
    "row4_teeth": 0.0,          # 整数精确
    "row5_frozen_walk": 1e-13,  # walk 因子逐位;N_prop 整数精确(逐位档)
    "row6_tr_sign": None,       # 判 FAIL 即可(读数窗 ±0.1 对 v1 记录方向)
    "row7_r36": 1e-12,
    "row8_r37_calib": 0.0,      # (旧口径,legacy 诊断列保留原 tol 记录)
    # ---- M0' 整改新增(整改令 3,写死) ------------------------------------
    "invariant_basis_drift": 1e-12,     # 基稳健自检:3 次固定种子酉旋转漂移门
    "invariant_cross_env": 1e-12,       # 跨环境不变量比对门(沙盒双跑,车道A)
    "row8_review_sin": SIG.REVIEW_SIN_TOL,    # 1e-4(复核表显示精度)
    "row8_review_frob": SIG.REVIEW_FROB_TOL,  # 1e-3(复核表显示精度)
}
ROW6_H00_RECORD, ROW6_DEFL_RECORD, ROW6_WIN = 4.0, 1.0, 0.1

CROSS_ENV_PENDING = ("待沙盒确认:整改后判据要求宿主+沙盒双环境不变量 diff <= "
                     "1e-12;沙盒双跑由车道A 复核时执行(本 JSON 为宿主参考值)")


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
            "frozen_json_lineage": ("沙盒系(Linux/OpenBLAS):复核 ② 确证冻结 "
                                    "r23_results.json 与沙盒重跑逐位 diff=0.0,"
                                    "与宿主(darwin/Accelerate)差 1.8e-15 ⟹ "
                                    "偏差纯环境属性(ULP 级),在 tol 1e-12 内"),
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
    """M0' 整改版(整改令 3):
    逐位档(判据)= N_prop 整数列 vs r32 + walk 因子逐位 vs r36;
    不变量档(判据)= 不变量 j_hand/主角谱 基稳健(3 种子酉旋转漂移 <=1e-12)
      + B₊ 主角谱/frob 宿主参考值入册(跨环境比对待沙盒);
    legacy 诊断(非判据)= 逐列 leak_resid_mean / curv_sv / 贪心 j_hand 比对
      (基依赖,环境绑定,as-recorded)。"""
    tol = TOL["row5_frozen_walk"]
    drift_tol = TOL["invariant_basis_drift"]
    r32f = _load("data/results/r32_results.json")["per_k"]
    rc3f = _load("data/results/rc3ii_results.json")[
        "candidate_R2_emergent_matter"]["per_k"]
    r36f = _load("data/results/r36_results.json")["certificates"][
        "walk_factor_max_diff_vs_frozen_D1"]
    g1 = gc.gates["G1_dof_nprop"]["per_L"]["16"]
    n_re = [r["N_prop"] for r in g1]
    n_fr = [p["N_prop_curv"] for p in r32f]
    # ---- 逐位档:walk 因子(r36 证书同款:16 个随机 k,rng(7)) ------------
    RC = FZ.mod("rc1a_tensor_index_scan")
    D1 = FZ.mod("r25_dynamic_symbol")
    rng = np.random.default_rng(7)
    wmax = 0.0
    for _ in range(16):
        nv = rng.uniform(-3.0, 3.0, 3)
        wmax = max(wmax, float(np.abs(
            RC.damped_map_p(nv, RC.MU0, RC.TH0, 0.0, RC.C0)
            - D1.damped_map(nv, RC.MU0)[0]).max()))
    bitwise_ok = (n_re == n_fr == [4, 4, 5, 5]
                  and wmax <= tol and abs(wmax - r36f) <= tol)
    # ---- 不变量档:G8 不变量 epsilon(含基稳健) + B₊ 主角谱逐判据 k --------
    e = gc.gates["G8_epsilon"]["diagnostics"]
    j_inv = {k: v["j_hand_invariant"] for k, v in e["per_k"].items()}
    eps_rng_inv = e["anchor_range_invariant"]
    eps_stable = bool(e["basis_stable"]) and e["max_drift"] <= drift_tol
    bplus_inv, bplus_drift = {}, 0.0
    for kl in [(2, 0, 0), (0, 3, 0), (2, 2, 0), (2, 2, 2)]:
        k = np.array(kl, float) * (2 * np.pi / 16)
        rob = INV.plus_branch_basis_robustness(k, math.cos(math.pi / 3.0))
        bplus_inv[str(kl)] = {
            "sin_theta": rob["base"]["sin_theta"],
            "max_sin_theta": rob["base"]["max_sin_theta"],
            "frob_leak": rob["base"]["frob_leak"],
            "rms_sin": rob["base"]["rms_sin"],
            "n_ge_thresh": rob["base"]["n_ge_thresh"],
            "basis_drift": rob["max_drift"]}
        bplus_drift = max(bplus_drift, rob["max_drift"])
    invariant_ok = eps_stable and bplus_drift <= drift_tol
    # ---- legacy 诊断(非判据;基依赖,环境绑定) ---------------------------
    leak_re = [r["leak_resid_mean"] for r in g1]
    leak_fr = [p["mean_resid_outside_kerC"] for p in r32f]
    leak_diff = max(abs(a - b) for a, b in zip(leak_re, leak_fr))
    sv_diff = max(_maxdiff(r["curv_sv"], p["curv_sv"])
                  for r, p in zip(g1, r32f))
    j_greedy = {k: v["legacy_greedy"]["j_hand"] for k, v in e["per_k"].items()}
    j_fr = {k: v["min_handbuilt_DOF_for_2"] for k, v in rc3f.items()}
    ok = bool(bitwise_ok and invariant_ok)
    return {"name": ("冻结走行族 (逐位:N_prop=[4,4,5,5]+walk 因子;不变量:"
                     "j_hand_inv/主角谱基稳健;legacy 逐模统计降级诊断)"),
            "remeasured": {
                "N_prop": n_re, "walk_factor_max_diff": wmax,
                "j_hand_invariant": j_inv,
                "epsilon_dof_min_max_invariant": eps_rng_inv,
                "epsilon_basis_stable": eps_stable,
                "bplus_invariants_per_k": bplus_inv,
                "basis_drift_max": max(bplus_drift, e["max_drift"])},
            "frozen": {"N_prop": n_fr, "walk_factor_max_diff": r36f,
                       "source": "r32/rc3ii/r36 results.json(逐位档比对);"
                                 "不变量档无先行冻结记录,本 JSON 即宿主参考值"},
            "legacy_diagnostics_basis_dependent": {
                "note": ("非判据(复核 §三:逐模统计随 LAPACK 基漂移);"
                         "as-recorded 环境绑定诊断"),
                "leak_resid_mean": leak_re,
                "leak_resid_mean_frozen": leak_fr,
                "leak_diff_vs_r32": leak_diff,
                "curv_sv_diff_vs_r32": sv_diff,
                "j_hand_greedy": j_greedy,
                "j_hand_greedy_frozen_rc3ii": j_fr,
                "j_greedy_matches_frozen": bool(j_greedy == j_fr),
                "epsilon_anchor_legacy_D1": [0.0, 0.25]},
            "tol": tol, "invariant_drift_tol": drift_tol,
            "max_abs_diff": max(wmax, abs(wmax - r36f)),
            "basis_robustness_check": {
                "seeds": list(INV.ROT_SEEDS),
                "max_drift": max(bplus_drift, e["max_drift"]),
                "pass": bool(invariant_ok)},
            "environment": INV.environment_record(),
            "cross_environment_status": CROSS_ENV_PENDING,
            "pass": ok}


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
    """M0' 整改版(整改令 1/3):
    不变量档(判据)= 三判据 k 的 (max sinθ, frob) 复现复核 §三判决数
      (tol = 显示精度 sin 1e-4 / frob 1e-3)+ 基稳健自检(3 种子漂移 <=1e-12);
      主角谱全谱入册为宿主参考值(跨环境 diff <=1e-12 待沙盒);
    不变量方向拟合(y=max sinθ,R37 协议原样)入册为宿主参考值;
    legacy 诊断(非判据)= 旧口径 resid 逐位 vs rc3ii + 旧口径拟合 vs r37_results
      (基依赖,环境绑定——正是复核抓出的失守读数,保留 as-recorded)。"""
    drift_tol = TOL["invariant_basis_drift"]
    # ---- 不变量档(判据) --------------------------------------------------
    calib_inv = SIG.calibration_16cube_invariant()
    fits_inv = SIG.direction_fits_invariant()
    inv_ok = bool(calib_inv["reproduces_review_judgement"])
    worst_drift = max(v["basis_robustness"]["max_drift"]
                      for v in calib_inv["per_k"].values())
    worst_review_diff = max(
        max(v["diff_vs_review"]["max_sin_theta"],
            v["diff_vs_review"]["frob_leak"])
        for v in calib_inv["per_k"].values())
    # ---- legacy 诊断(非判据;宿主环境绑定) -------------------------------
    tol_legacy = TOL["row8_r37_calib"]
    rc3f = _load("data/results/rc3ii_results.json")[
        "candidate_R3_exact_constraint"]["per_k"]
    remeas = SIG.calibration_16cube()
    diffs = {}
    for kstr, v in remeas.items():
        lo, hi = rc3f[kstr]["resid_outside_kerC_min_max"]
        diffs[kstr] = [abs(v["resid_min"] - lo), abs(v["resid_max"] - hi)]
    worst_legacy = max(max(d) for d in diffs.values())
    r37f = _load("data/results/r37_results.json")["direction_fits"]
    fits_legacy = SIG.direction_fits()
    fit_diff = {}
    for J in r37f:
        d = J["direction"]
        m1 = J["power_model"]
        f = fits_legacy[d]
        fit_diff[d] = max(abs(f["A"] - m1["A"]), abs(f["alpha"] - m1["alpha"]),
                          abs(f["dAIC_const_minus_power"]
                              - J["dAIC_const_minus_power"]))
    ok = inv_ok
    return {"name": ("R37 16^3 校准 (不变量:判决数复现+基稳健;"
                     "legacy resid 逐位降级诊断)"),
            "remeasured": {
                "calib_invariant": calib_inv["per_k"],
                "reproduces_review_judgement":
                    calib_inv["reproduces_review_judgement"],
                "fits_invariant": {d: {"A": f["A"], "sigma_A": f["sigma_A"],
                                       "alpha": f["alpha"],
                                       "dAIC": f["dAIC_const_minus_power"],
                                       "verdict": f["verdict"],
                                       "band_D3": f["band_D3"],
                                       "y_observable": f["y_observable"]}
                                   for d, f in fits_inv.items()}},
            "frozen": {"review_judgement_16cube":
                           {str(k): v for k, v
                            in SIG.REVIEW_JUDGEMENT_16CUBE.items()},
                       "source": ("复核 §三 判决实验不变量列(沙盒;环境无关"
                                  "参照);不变量拟合无先行冻结记录,本 JSON "
                                  "即宿主参考值")},
            "legacy_diagnostics_basis_dependent": {
                "note": ("非判据(复核 §三:resid_min/max 随 LAPACK 基漂移,"
                         "跨环境失守正发生在此列);as-recorded 环境绑定诊断"),
                "calib_legacy": remeas,
                "diff_vs_rc3ii": diffs,
                "worst_diff_vs_rc3ii": worst_legacy,
                "legacy_tol_was": tol_legacy,
                "fits_legacy": {d: {"A": f["A"], "alpha": f["alpha"],
                                    "dAIC": f["dAIC_const_minus_power"],
                                    "verdict": f["verdict"]}
                                for d, f in fits_legacy.items()},
                "fit_diff_vs_r37_results": fit_diff},
            "tol": {"review_sin": TOL["row8_review_sin"],
                    "review_frob": TOL["row8_review_frob"],
                    "basis_drift": drift_tol,
                    "cross_env": TOL["invariant_cross_env"]},
            "max_abs_diff": worst_review_diff,
            "basis_robustness_check": {
                "seeds": list(INV.ROT_SEEDS),
                "max_drift": worst_drift,
                "pass": bool(worst_drift <= drift_tol)},
            "environment": INV.environment_record(),
            "cross_environment_status": CROSS_ENV_PENDING,
            "pass": bool(ok)}
