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
"""
from __future__ import annotations

import numpy as np

from . import frozen as FZ

ALPHA_CLEAN_MIN = 1.0     # D3 两档边界(写死)


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
    """16^3 校准:R37 冻结 resid 路径在三个 rc3ii 判据 k 的 resid min/max。
    与 rc3ii_results.json 的比对(diff 必须逐位 0.0)由 controls.py 完成;
    这里只产出重测读数。"""
    R37 = FZ.mod("r37_residual_scaling_audit")
    out = {}
    for kl in ((2, 0, 0), (2, 2, 0), (2, 2, 2)):
        k = np.array(kl, float) * (2 * np.pi / 16)
        resid = R37.resid_plus_modes(k, R37.C0)
        out[str(kl)] = {"resid_min": float(resid.min()),
                        "resid_max": float(resid.max()),
                        "n_plus_modes": int(resid.size)}
    return out
