"""rulespace_v2.sigma -- G2 约束标度 sigma=(alpha, A) 机器(R37 协议外壳,核不重写)。

D3(docsv2/v2-裁定-D1D5-2026-07-26.md):拟合协议全文继承 R37
(experiments/r37_residual_scaling_audit.py,冻结):
  * 方向分层(axial / face-diagonal / body-diagonal 三射线,不跨方向平均);
  * 拟合窗:分量 k = 2*pi*n/L <= pi/4(n/L <= 1/8);上下文点记录、永不入拟合;
  * 剔除 k=0 邻域:合并点须至少一个 n>=2 出处;各格 n=1 原始读数照报;
  * 主判 resid_max,辅报 resid_mean;
  * 双模型 M0 常数 vs M1 幂律 A+B|k|^alpha(alpha 网格 0.05..4.00 步 0.01),
    AIC 判选,幂律胜出须 |dAIC|>=2;排零 |A|<=2 sigma_A。
本模块全部数字由 R37 冻结函数(collect_direction / judge_direction / resid_plus_modes)
产出;此处只做调用、两档分类与 16^3 校准比对材料。

D3 标度分档(写死):alpha >= 1 -> "clean"(干净标度);0 < alpha < 1 -> "weak"(弱标度)。
>=64^3 校准件是交付物 4(独立脚本 v2m0_sigma_calibration.py,本模块不涉)。

--- M0' 整改(2026-07-26,复核 §四 整改令 1;判据写死,运行后不回改)---------------
复核判决:resid_min/max 是 ±ω 精确简并子空间 LAPACK 任意基上的逐模统计,**不是
观测量**(基依赖,跨环境漂移)。σ 主读数不变量化:
  * 主判 y = max sin θ(span(B₊) vs ker C 主角谱;替代 resid_max);
  * 辅报 y = rms sin = frob/sqrt(m)(resid_mean 的严格不变量对应物);
  * 另报 {sin θ_i} 全谱、Frobenius 泄漏、≥0.05 主角计数(invariants.SIN_THRESH)。
R37 拟合协议(窗 = 分量 ≤ π/4、剔 n=1、去重、AIC 双模型、方向分层)**原样保留**
(fit_constant / fit_power 冻结代码对象直接调用),只换 y 值。
旧口径 resid_* 读数保留为"legacy(环境绑定)"注记,不再作跨环境判据。
首个自检(REVIEW_JUDGEMENT_16CUBE):本实现必须复现复核 §三判决表的 16³ 三 k
不变量数(max sinθ 1.0000/0.1948/0.1493;frob 1.035/0.304/0.211),容差 = 表列
显示精度(sin 1e-4 / frob 1e-3);对不上 = 实现有错,先修。
"""
from __future__ import annotations

import math
from fractions import Fraction

import numpy as np

from . import frozen as FZ
from . import invariants as INV

ALPHA_CLEAN_MIN = 1.0     # D3 两档边界(写死)

# 复核 §三 判决实验参照(沙盒不变量列;实现自检必须复现;写死)
REVIEW_JUDGEMENT_16CUBE = {
    (2, 0, 0): {"max_sin_theta": 1.0000, "frob_leak": 1.035},
    (2, 2, 0): {"max_sin_theta": 0.1948, "frob_leak": 0.304},
    (2, 2, 2): {"max_sin_theta": 0.1493, "frob_leak": 0.211},
}
REVIEW_SIN_TOL = 1e-4     # 复核表 4 位小数显示精度
REVIEW_FROB_TOL = 1e-3    # 复核表 3 位小数显示精度


def classify_alpha(alpha: float, verdict: str) -> str:
    """D3 两档:alpha>=1 干净 / 0<alpha<1 弱;仅当方向判定非 FAIL 时有意义。"""
    if verdict == "FAIL":
        return "O(1)-constant (no scaling)"
    if alpha >= ALPHA_CLEAN_MIN:
        return "clean (alpha>=1)"
    if alpha > 0.0:
        return "weak (0<alpha<1)"
    return "undefined"


def direction_fits() -> dict:
    """R37 冻结协议原样重跑(格子系列/射线/窗/剔点/AIC 全部来自 R37 模块常量)。
    返回 {direction: {A, sigma_A, B, alpha, dAIC, verdict, band(D3 两档), n_fit}}。"""
    R37 = FZ.mod("r37_residual_scaling_audit")
    out = {}
    for dname, dvec in R37.DIRS.items():
        pts = R37.collect_direction(dname, dvec)
        J = R37.judge_direction(dname, pts)
        m1 = J["power_model"]
        out[dname] = {
            "n_fit_points": J["n_fit_points"],
            "A": m1["A"], "sigma_A": m1["sigma_A"], "B": m1["B"],
            "alpha": m1["alpha"], "sigma_alpha": m1["sigma_alpha"],
            "dAIC_const_minus_power": J["dAIC_const_minus_power"],
            "winner": J["winner"], "decisive": J["decisive"],
            "verdict": J["verdict"],
            "band_D3": classify_alpha(m1["alpha"], J["verdict"]),
        }
    return out


def calibration_16cube() -> dict:
    """16^3 校准(旧口径,legacy):R37 冻结 resid 路径在三个 rc3ii 判据 k 的
    resid min/max。整改后地位 = 环境绑定 legacy 诊断(基依赖,非跨环境判据);
    这里只产出重测读数。"""
    R37 = FZ.mod("r37_residual_scaling_audit")
    out = {}
    for kl in ((2, 0, 0), (2, 2, 0), (2, 2, 2)):
        k = np.array(kl, float) * (2 * np.pi / 16)
        resid = R37.resid_plus_modes(k, R37.C0)
        out[str(kl)] = {"resid_min": float(resid.min()),
                        "resid_max": float(resid.max()),
                        "n_plus_modes": int(resid.size),
                        "legacy_basis_dependent": True}
    return out


# ==========================================================================
#  整改令 1:不变量 σ 机器(主判 y = max sin θ;R37 协议原样,只换 y)
# ==========================================================================
def invariant_plus_modes(k, c=None):
    """span(B₊) vs ker C 的不变量读数(替代 resid_plus_modes 的输出口径)。"""
    R37 = FZ.mod("r37_residual_scaling_audit")
    if c is None:
        c = R37.C0
    return INV.plus_branch_invariants(np.asarray(k, float), c)


def calibration_16cube_invariant() -> dict:
    """16³ 三判据 k 的不变量读数 + 复核 §三 判决数复现自检 + 基稳健性自检。
    这是整改后 row8 的判据材料(controls.py 比对)。"""
    R37 = FZ.mod("r37_residual_scaling_audit")
    out, ok_all = {}, True
    for kl, ref in REVIEW_JUDGEMENT_16CUBE.items():
        k = np.array(kl, float) * (2 * np.pi / 16)
        rob = INV.plus_branch_basis_robustness(k, R37.C0)
        inv = rob["base"]
        d_sin = abs(inv["max_sin_theta"] - ref["max_sin_theta"])
        d_frob = abs(inv["frob_leak"] - ref["frob_leak"])
        ok = bool(d_sin <= REVIEW_SIN_TOL and d_frob <= REVIEW_FROB_TOL
                  and rob["pass_drift_le_1e-12"])
        ok_all = ok_all and ok
        out[str(kl)] = {
            **inv,
            "review_ref": ref,
            "diff_vs_review": {"max_sin_theta": d_sin, "frob_leak": d_frob},
            "review_tol": {"max_sin_theta": REVIEW_SIN_TOL,
                           "frob_leak": REVIEW_FROB_TOL},
            "basis_robustness": {"drift_per_seed": rob["drift_per_seed"],
                                 "max_drift": rob["max_drift"],
                                 "seeds": rob["seeds"]},
            "ok": ok,
        }
    return {"per_k": out, "reproduces_review_judgement": bool(ok_all)}


def collect_direction_invariant(dname, dvec, lattices=None) -> list:
    """R37.collect_direction 的采样结构(窗/剔点/去重逐字同构,格子表参数化),
    每点同时记录不变量读数(新口径)与 resid_*(legacy,环境绑定注记)。"""
    R37 = FZ.mod("r37_residual_scaling_audit")
    if lattices is None:
        lattices = list(R37.LATTICES)
    samples = {}
    for L in lattices:
        n_max = int(R37.CTX_RATIO_MAX * L)
        for n in range(1, n_max + 1):
            r = Fraction(n, L)
            if r > R37.CTX_RATIO_MAX:
                continue
            if r in samples:
                samples[r]["provenance"].append([L, n])
                continue
            comp = 2.0 * math.pi * float(r)
            k = comp * np.array(dvec, float)
            resid = R37.resid_plus_modes(k, R37.C0)
            inv = INV.plus_branch_invariants(k, R37.C0)
            if resid is None or inv is None:
                samples[r] = {"ratio": [r.numerator, r.denominator],
                              "comp": comp,
                              "kabs": comp * math.sqrt(float(np.dot(dvec, dvec))),
                              "off_band": True, "provenance": [[L, n]]}
                continue
            samples[r] = {
                "ratio": [r.numerator, r.denominator],
                "comp": comp,
                "kabs": comp * math.sqrt(float(np.dot(dvec, dvec))),
                # ---- 不变量读数(新口径,判据) ------------------------------
                "n_plus_modes": inv["dim_P"],
                "sin_theta": inv["sin_theta"],
                "max_sin_theta": inv["max_sin_theta"],
                "frob_leak": inv["frob_leak"],
                "rms_sin": inv["rms_sin"],
                "n_ge_thresh": inv["n_ge_thresh"],
                # ---- legacy 逐模统计(环境绑定,注记) ------------------------
                "legacy_resid_min": float(resid.min()),
                "legacy_resid_max": float(resid.max()),
                "legacy_resid_mean": float(resid.mean()),
                "provenance": [[L, n]],
                "off_band": False,
            }
    out = []
    for r in sorted(samples):
        s = samples[r]
        in_window = r <= R37.FIT_RATIO_MAX
        has_n_ge2 = any(n >= 2 for _, n in s["provenance"])
        s["in_fit_window"] = bool(in_window)
        s["excluded_k0_neighbour"] = bool(in_window and not has_n_ge2)
        s["in_fit"] = bool(in_window and has_n_ge2 and not s.get("off_band"))
        out.append(s)
    return out


def judge_direction_invariant(dname, pts, y_key="max_sin_theta") -> dict:
    """R37.judge_direction 的判定语义(双模型/AIC/排零/verdict 逐字同构,
    fit_constant/fit_power 冻结代码对象直接调用),y 值换不变量。"""
    R37 = FZ.mod("r37_residual_scaling_audit")
    fitpts = [s for s in pts if s["in_fit"]]
    x = np.array([s["kabs"] for s in fitpts])
    y = np.array([s[y_key] for s in fitpts])
    m0 = R37.fit_constant(x, y)
    m1 = R37.fit_power(x, y)
    daic = m0["AIC"] - m1["AIC"]
    winner = m1 if m1["AIC"] < m0["AIC"] else m0
    decisive = bool(abs(daic) >= R37.DAIC_DECISIVE)
    a_win, sig_win = winner["A"], winner["sigma_A"]
    pass_d = bool(winner is m1 and decisive and m1["alpha"] > 0.0
                  and abs(m1["A"]) <= 2.0 * m1["sigma_A"])
    fail_d = bool(abs(a_win) >= R37.A_O1_THRESH and abs(a_win) > 2.0 * sig_win)
    verdict = "FAIL" if fail_d else ("PASS" if pass_d else "ambiguous")
    ysec = np.array([s["rms_sin"] for s in fitpts])
    s0 = R37.fit_constant(x, ysec)
    s1 = R37.fit_power(x, ysec)
    return {
        "direction": dname, "y_observable": y_key,
        "n_fit_points": len(fitpts),
        "fit_kabs": [float(v) for v in x],
        "fit_y": [float(v) for v in y],
        "constant_model": m0, "power_model": m1,
        "dAIC_const_minus_power": daic,
        "winner": winner["model"], "decisive": decisive,
        "PASS_d": pass_d, "FAIL_d": fail_d, "verdict": verdict,
        "secondary_rms_sin": {"constant": s0, "power": s1,
                              "dAIC_const_minus_power": s0["AIC"] - s1["AIC"]},
    }


def direction_fits_invariant(lattices=None) -> dict:
    """不变量口径的三方向拟合(默认 R37 冻结格子系列 16-48;判据用)。
    返回 {direction: {A, sigma_A, alpha, dAIC, verdict, band_D3, ...}}。"""
    R37 = FZ.mod("r37_residual_scaling_audit")
    out = {}
    for dname, dvec in R37.DIRS.items():
        pts = collect_direction_invariant(dname, dvec, lattices)
        J = judge_direction_invariant(dname, pts)
        m1 = J["power_model"]
        out[dname] = {
            "y_observable": J["y_observable"],
            "n_fit_points": J["n_fit_points"],
            "A": m1["A"], "sigma_A": m1["sigma_A"], "B": m1["B"],
            "alpha": m1["alpha"], "sigma_alpha": m1["sigma_alpha"],
            "constant_A": J["constant_model"]["A"],
            "constant_sigma_A": J["constant_model"]["sigma_A"],
            "dAIC_const_minus_power": J["dAIC_const_minus_power"],
            "winner": J["winner"], "decisive": J["decisive"],
            "verdict": J["verdict"],
            "band_D3": classify_alpha(m1["alpha"], J["verdict"]),
            "secondary_rms_sin_dAIC":
                J["secondary_rms_sin"]["dAIC_const_minus_power"],
        }
    return out
