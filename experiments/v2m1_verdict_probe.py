"""v2m1_verdict_probe -- M1' 复核探针(车道A 指令 2026-07-26 §一-7,P3)。

只读两个冻结 JSON:
  data/results/v2m1_maxwell_loop_r3.json   (M1' 轮 3 主跑,冻结)
  data/results/v2m1_guns.json              (M1' 炮组,冻结)
从 runs 层原始读数出发,独立重算:
  (1) 八门 verdict(阈值在本探针重新声明,出处 = 轮 3 脚本头预注册);
  (2) T_cross 预言命中判定(±50% 带)+ 下采样曲线穿线一致性
      + 标定段/判门段时间分离检查(t_cross > t_calB, tau 段 < t_calA);
  (3) 分支判定(A/B/C/回退/计数)重放;
  (4) 炮组 C1-C4 击穿判定 + P0 正控判定 + C3 元判据双值(8.0/7.5)对照;
逐项与落盘 verdict 比对。**不重跑任何演化**;fp64;numpy;无 GPU;<1 分钟。
不写任何冻结路径;输出 data/results/v2m1_verdict_probe.json(新文件)。

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/v2m1_verdict_probe.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
R3_JSON = os.path.join(ROOT, "data", "results", "v2m1_maxwell_loop_r3.json")
GUNS_JSON = os.path.join(ROOT, "data", "results", "v2m1_guns.json")
OUT = os.path.join(ROOT, "data", "results", "v2m1_verdict_probe.json")

# ---- 阈值重声明(出处 = v2m1_maxwell_loop_r3.py / v2m1_guns.py 脚本头)----
TOL = 1e-12
L_LIST = [16, 24, 32, 48]
JUDGE_K16 = [(2, 0, 0), (0, 2, 0), (0, 0, 2), (2, 2, 0), (3, 1, 0),
             (2, 2, 2), (8, 0, 0)]
SV_THRESH = 0.05
G3_ISO_GATE = 1e-6
G3_P_TARGET, G3_P_TOL = 2.0, 0.1
G4A_CORR_LMAX_MIN, G4A_CORR_DROP_MAX, G4A_COEF_RELTOL = 0.97, 0.02, 0.05
G6_RESID_R36 = 1e-3
G6_TAU_R2_MIN = 0.9
SPREAD_GATE = 3.0
G7_RADIUS_GATE = 1e-9
T_CROSS_BAND = (0.5, 1.5)
CAL_R2_MIN, CAL_MIN_SAMPLES = 0.98, 8
ROUND2_PASS_GATES = ["G1_dof_nprop", "G2_sigma_scaling", "G3_j5_cocone",
                     "G4_newton", "G5_eddington", "G7_stability",
                     "G8_epsilon"]
# guns
C1_WDEV_BIN_FACTOR = 10.0
C2_NPROP_REQ, C2_M2_TRUE, C2_M2_TOL = 3, 0.16, 0.02
C3_CONT_MIN, C3_GAUSS_END_MIN = 1.0, 0.5
C3_T_INJ = 64
C3_GROWTH_MIN_ARCHIVED = 7.5      # 正式跑判定值(审计注:首跑为 8.0)
C3_GROWTH_MIN_FIRSTRUN = 8.0      # 双值对照(指令 P1-2)
C4_RESID_MIN = 1e-3


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def recompute_gates(R3):
    runs = R3["runs"]
    out = {}

    # G1: N_prop==2 全 7 判据 k 全 L + sv3 断崖 < SV_THRESH
    ok, sv3s = True, []
    for L in L_LIST:
        for n16 in JUDGE_K16:
            e = runs[str(L)]["per_k"][str(tuple(n16))]
            ok = ok and (e.get("n_prop") == 2)
            if e.get("sv3_main") is not None:
                sv3s.append(e["sv3_main"])
    out["G1_dof_nprop"] = "PASS" if (ok and max(sv3s) < SV_THRESH) else "FAIL"

    # G2: y_max = max(divE/divB 漂移, Gauss 锁) <= 1e-12 全 L(分支 i)
    ys = {}
    for L in L_LIST:
        r = runs[str(L)]
        m = r["wave_monitor"]
        gmax = max([g[2] for g in r["gauss_lock"]] + [r["gauss_lock_move"]])
        ys[str(L)] = max(m["divE_drift_rel"], m["divB_drift_rel"], gmax)
    out["G2_sigma_scaling"] = ("PASS" if all(v <= TOL for v in ys.values())
                               else "FAIL")

    # G3: 算子级 <=1e-12;谱级 <1 bin;iso <=1e-6;p=2±0.1(重拟合)
    ok = True
    for L in L_LIST:
        for n16 in JUDGE_K16:
            e = runs[str(L)]["per_k"][str(tuple(n16))]
            ok = ok and (e["oracle"]["w_op_vs_analytic"] <= TOL)
            dev, binw = e.get("w_meas_vs_yee"), e.get("bin_width")
            ok = ok and (dev is not None and dev < binw)
        ciso = [runs[str(L)]["per_k"][str(tuple(n16))]["c_meas"]
                for n16 in JUDGE_K16[:3]]
        ok = ok and ((max(ciso) - min(ciso)) / np.mean(ciso) <= G3_ISO_GATE)
    xk = np.array([2 * np.pi / L for L in L_LIST])
    yc = np.array([abs(runs[str(L)]["per_k"][str((1, 0, 0))]
                       ["w_op_measured"] / (2 * np.pi / L) - 1.0)
                   for L in L_LIST])
    pfit = float(np.polyfit(np.log(xk), np.log(yc), 1)[0])
    out["_g3_p_refit"] = pfit
    out["G3_j5_cocone"] = ("PASS" if (ok and abs(pfit - G3_P_TARGET)
                                      <= G3_P_TOL) else "FAIL")

    # G4a
    corrs = [runs[str(L)]["coulomb"]["corr"] for L in L_LIST]
    coefs = [runs[str(L)]["coulomb"]["coef_times_4pi_over_q"] for L in L_LIST]
    nondiv = all(corrs[i + 1] >= corrs[i] - G4A_CORR_DROP_MAX
                 for i in range(len(corrs) - 1))
    out["G4_newton"] = ("PASS" if (nondiv and corrs[-1] >= G4A_CORR_LMAX_MIN
                                   and abs(coefs[-1] - 1.0)
                                   <= G4A_COEF_RELTOL) else "FAIL")

    # G4b: 锥外泄漏 <=1e-12 全检查点
    ok = True
    for L in L_LIST:
        rows = runs[str(L)]["cone_rows_static"] + \
            ([runs[str(L)]["cone_move"]] if runs[str(L)]["cone_move"] else [])
        leaks = [r["leak"] for r in rows if r["leak"] is not None]
        ok = ok and bool(leaks) and all(v <= TOL for v in leaks)
    out["G5_eddington"] = "PASS" if ok else "FAIL"

    # G5 守恒 + G6 sponge(容器 G6_conservation)
    g5_ok = True
    for L in L_LIST:
        r = runs[str(L)]
        gmax = max([g[2] for g in r["gauss_lock"]] + [r["gauss_lock_move"]])
        h = r["wave_monitor"].get("yee_energy_drift_rel")
        g5_ok = g5_ok and (r["charge_continuity_residual_max"] <= TOL
                           and gmax <= TOL and h is not None and h <= TOL)
    g6_ok, tau_means = True, []
    for L in L_LIST:
        rows = runs[str(L)]["packet_rows"]
        taus = [p["tau_steps"] for p in rows]
        all_tau = all(t is not None for t in taus)
        spread = (max(taus) / min(taus)) if all_tau else None
        resid_max = max(p["residual_end"] for p in rows)
        g6_ok = g6_ok and bool(all_tau and spread <= SPREAD_GATE
                               and resid_max <= G6_RESID_R36
                               and resid_max <= TOL)
        tau_means.append(float(np.mean(taus)) if all_tau else None)
    if all(t is not None for t in tau_means):
        A_ = np.vstack([L_LIST, np.ones(len(L_LIST))]).T
        coef, _, _, _ = np.linalg.lstsq(A_, np.array(tau_means), rcond=None)
        yhat = A_ @ coef
        r2 = 1.0 - (float(np.sum((np.array(tau_means) - yhat) ** 2))
                    / (float(np.sum((np.array(tau_means)
                                     - np.mean(tau_means)) ** 2)) + 1e-300))
        g6_ok = bool(g6_ok and coef[0] > 0 and r2 >= G6_TAU_R2_MIN)
        out["_g6_tau_refit"] = {"slope": float(coef[0]), "R2": r2}
    else:
        g6_ok = False
    out["G6_conservation"] = "PASS" if (g5_ok and g6_ok) else "FAIL"

    # G7: 全 BZ 谱半径读数(gate_columns 在册原始读数)<= 1+1e-9
    g7 = R3["gate_columns"]["gates"]["G7_stability"]["per_L"]
    out["G7_stability"] = ("PASS" if all(
        g7[str(L)]["bz_radius_max"] <= 1.0 + G7_RADIUS_GATE for L in L_LIST)
        else "FAIL")

    # G8: j_inv==0 全 (k,L);epsilon_dof 实测
    ok, eps = True, []
    for L in L_LIST:
        for n16 in JUDGE_K16:
            e = runs[str(L)]["per_k"][str(tuple(n16))].get("epsilon_inv")
            if e is None:
                ok = False
                continue
            ok = ok and (e["j_inv"] == 0)
            eps.append(e["epsilon_dof"])
    out["_g8_eps_minmax"] = [min(eps), max(eps)] if eps else None
    out["G8_epsilon"] = "PASS" if ok else "FAIL"
    return out


def recompute_tcross(R3):
    rows, all_hit, sep_ok = {}, True, True
    for L in L_LIST:
        wr = R3["runs"][str(L)]["window_resign"]
        pred, meas = wr["t_cross_pred_steps"], wr["t_cross_meas_steps"]
        ratio = meas / pred if meas is not None else None
        hit = bool(ratio is not None
                   and T_CROSS_BAND[0] <= ratio <= T_CROSS_BAND[1])
        all_hit = all_hit and hit
        # 下采样曲线穿线一致性:meas 之前样本 >1e-12,meas 起样本 <=1e-12
        cur = wr["rmax_curve_downsampled"]
        pre = [r for t, r in cur if t < meas]
        post = [r for t, r in cur if t >= meas]
        cons = bool(all(r > TOL for r in pre)
                    and post and all(r <= TOL for r in post))
        # 标定段/判门段时间分离:穿线在标定段之后;tau(G6)在标定段之前
        taus = [p["tau_steps"]
                for p in R3["runs"][str(L)]["packet_rows"]]
        sep = bool(meas > wr["t_calB"] and max(taus) < wr["t_calA"])
        sep_ok = sep_ok and sep and cons
        cal_valid = bool(wr["n_cal_samples"] >= CAL_MIN_SAMPLES
                         and wr["R2_cal"] >= CAL_R2_MIN)
        rows[str(L)] = {"pred": pred, "meas": meas, "ratio": ratio,
                        "hit_pm50": hit, "curve_consistent": cons,
                        "t_calA": wr["t_calA"], "t_calB": wr["t_calB"],
                        "cal_segment_separated_from_gate_stats": sep,
                        "cal_valid_recheck": cal_valid,
                        "floor_flag": wr["floor_flag"],
                        "deviation_flag": wr["deviation_flag"]}
    return rows, all_hit, sep_ok


def recompute_branch(R3, gates, all_hit):
    verd = {k: v for k, v in gates.items() if not k.startswith("_")}
    regressed = [g for g in ROUND2_PASS_GATES if verd.get(g) != "PASS"]
    all_pass = all(v == "PASS" for v in verd.values())
    wr = {str(L): R3["runs"][str(L)]["window_resign"] for L in L_LIST}
    branch_b = [str(L) for L in L_LIST
                if wr[str(L)]["floor_flag"] or wr[str(L)]["deviation_flag"]]
    all_cal = all(wr[str(L)]["cal_valid"] is True for L in L_LIST)
    g6_pass = verd.get("G6_conservation") == "PASS"
    if regressed:
        br = "HALT-REGRESSION"
    elif branch_b:
        br = "B"
    elif g6_pass and all_pass and all_hit and all_cal:
        br = "A"
    elif g6_pass and all_pass:
        br = "C"
    else:
        br = "FAIL-COUNT-2"
    count = 1 + (1 if ((not g6_pass) or bool(branch_b)) else 0)
    return {"branch": br, "regressed": regressed, "g6_count": count,
            "all_pass": all_pass}


def recompute_guns(GJ):
    g = GJ["guns"]
    out = {}
    # C1
    c1 = g["C1_bad_placement"]
    wdev = c1["w_dev_max"]
    wdev_f = float(wdev) if not isinstance(wdev, str) else float(wdev)
    c1_re = bool(len(c1["breaks"]) > 0
                 and c1["nyquist"]["n_prop"] == 0
                 and (not math.isfinite(wdev_f)
                      or wdev_f > C1_WDEV_BIN_FACTOR * c1["bin_width"]))
    out["C1"] = {"recomputed": c1_re, "archived": c1["FAILS_as_required"]}
    # C2
    c2 = g["C2_proca"]
    devs = [abs(v - C2_M2_TRUE) for v in c2["m_eff2_per_k"].values()]
    c2_re = bool(len(c2["breaks"]) > 0
                 and all(n == C2_NPROP_REQ for n in c2["nprops"])
                 and len(devs) == 7 and max(devs) <= C2_M2_TOL)
    out["C2"] = {"recomputed": c2_re, "archived": c2["FAILS_as_required"]}
    # C3(双值)
    c3 = g["C3_nonconserved_source"]
    hist = c3["gauss_lock_history"]
    inj = [v for t, v in hist if t <= C3_T_INJ]
    mono = all(inj[i + 1] >= inj[i] * 0.99 for i in range(len(inj) - 1))
    growth = c3["gauss_growth_ratio"]
    base = bool(c3["continuity_residual_per_dq"] >= C3_CONT_MIN
                and c3["gauss_end_over_Q"] >= C3_GAUSS_END_MIN and mono)
    c3_75 = bool(base and growth >= C3_GROWTH_MIN_ARCHIVED)
    c3_80 = bool(base and growth >= C3_GROWTH_MIN_FIRSTRUN)
    out["C3"] = {"recomputed_at_7p5": c3_75, "recomputed_at_8p0": c3_80,
                 "archived": c3["FAILS_as_required"],
                 "growth_ratio": growth,
                 "main_criteria_layer_(cont/gauss_end/monotone)": base,
                 "dual_value_same_verdict": bool(c3_75 == c3_80)}
    # C4
    c4 = g["C4_no_damping"]
    c4_re = all((r["tau_steps"] is None or r["residual_end"] > C4_RESID_MIN)
                for r in c4["per_k"])
    out["C4"] = {"recomputed": c4_re, "archived": c4["FAILS_as_required"]}
    # P0
    p0 = g["P0_positive_control"]
    p0_re = bool(p0["a_yee_vs_frozen"]["n_prop_bitwise"]
                 and p0["a_yee_vs_frozen"]["max_judge_field_diff"] <= TOL
                 and p0["b_row2_r23"]["max_abs_diff"] <= TOL)
    out["P0"] = {"recomputed": p0_re, "archived": p0["pass"]}
    all_re = bool(out["C1"]["recomputed"] and out["C2"]["recomputed"]
                  and out["C3"]["recomputed_at_7p5"]
                  and out["C4"]["recomputed"])
    out["all_guns_fail_as_required"] = {
        "recomputed": all_re, "archived": GJ["all_guns_fail_as_required"]}
    return out


def main():
    t0 = time.time()
    with open(R3_JSON, "r", encoding="utf-8") as fh:
        R3 = json.load(fh)
    with open(GUNS_JSON, "r", encoding="utf-8") as fh:
        GJ = json.load(fh)

    gates = recompute_gates(R3)
    tcross, all_hit, sep_ok = recompute_tcross(R3)
    branch = recompute_branch(R3, gates, all_hit)
    guns = recompute_guns(GJ)

    # ---- 与落盘 verdict 比对 ---------------------------------------------
    mism = []
    for k, v in R3["verdict_table"].items():
        if gates.get(k) != v:
            mism.append("gate %s: probe=%s archived=%s"
                        % (k, gates.get(k), v))
    for L in L_LIST:
        a, b = tcross[str(L)], R3["t_cross_table"][str(L)]
        if a["hit_pm50"] != b["hit_pm50"] or a["meas"] != b["meas"]:
            mism.append("t_cross L=%d probe=%s archived=%s" % (L, a, b))
        if not a["curve_consistent"]:
            mism.append("t_cross L=%d curve inconsistency" % L)
    if branch["branch"] != R3["branch"]:
        mism.append("branch: probe=%s archived=%s"
                    % (branch["branch"], R3["branch"]))
    if branch["g6_count"] != R3["g6_consecutive_fail_count"]:
        mism.append("g6_count mismatch")
    if branch["regressed"] != R3["regression_check"]["regressed"]:
        mism.append("regression mismatch")
    for k in ("C1", "C2", "C4"):
        if guns[k]["recomputed"] != guns[k]["archived"]:
            mism.append("gun %s mismatch" % k)
    if guns["C3"]["recomputed_at_7p5"] != guns["C3"]["archived"]:
        mism.append("gun C3 (7.5) mismatch")
    if guns["P0"]["recomputed"] != guns["P0"]["archived"]:
        mism.append("P0 mismatch")
    if (guns["all_guns_fail_as_required"]["recomputed"]
            != guns["all_guns_fail_as_required"]["archived"]):
        mism.append("all_guns mismatch")
    if not sep_ok:
        mism.append("calibration/gate-statistics separation violated")

    payload = {
        "register": "v2m1-verdict-probe(车道A 指令 §一-7;判定逻辑跨环境件)",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "inputs_readonly": {
            "v2m1_maxwell_loop_r3.json": sha256_file(R3_JSON),
            "v2m1_guns.json": sha256_file(GUNS_JSON)},
        "no_evolution_rerun": True,
        "gate_verdicts_recomputed":
            {k: v for k, v in gates.items() if not k.startswith("_")},
        "gate_verdicts_archived": R3["verdict_table"],
        "auxiliary_refits": {"g3_p": gates["_g3_p_refit"],
                             "g6_tau_fit": gates.get("_g6_tau_refit"),
                             "g8_eps_minmax": gates.get("_g8_eps_minmax")},
        "t_cross_recheck": tcross,
        "branch_replay": branch,
        "branch_archived": {"branch": R3["branch"],
                            "g6_count": R3["g6_consecutive_fail_count"]},
        "guns_recheck": guns,
        "c3_dual_value_note": (
            "C3 元判据双值对照(指令 P1-2):growth_ratio=7.999999999999999;"
            "8.0 下元判据不成立(1 ULP),7.5 下成立——双值不同判;"
            "主判据层(cont>=1.0 / gauss_end>=0.5 / 单调)双值同判击穿。"
            "归类与处置见复核包 P1-2 文件,此处仅陈列数字。"),
        "mismatches": mism,
        "probe_consistent_with_archived": len(mism) == 0,
        "seconds": time.time() - t0,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    print("gates probe :", payload["gate_verdicts_recomputed"])
    print("gates frozen:", payload["gate_verdicts_archived"])
    for L in L_LIST:
        r = tcross[str(L)]
        print("T_cross L=%-3d meas=%s pred=%s hit=%s curve_ok=%s sep_ok=%s"
              % (L, r["meas"], r["pred"], r["hit_pm50"],
                 r["curve_consistent"],
                 r["cal_segment_separated_from_gate_stats"]))
    print("branch replay:", branch["branch"], "(archived %s)" % R3["branch"])
    print("guns:", {k: guns[k] for k in ("C1", "C2", "C3", "C4", "P0")})
    print("MISMATCHES:", mism if mism else "none")
    print("PROBE CONSISTENT:", payload["probe_consistent_with_archived"])
    print("%.2fs" % payload["seconds"])
    return 0 if payload["probe_consistent_with_archived"] else 1


if __name__ == "__main__":
    sys.exit(main())
