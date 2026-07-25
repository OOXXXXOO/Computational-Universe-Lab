"""rulespace_v2.invariants -- 基不变观测量层(M0' 整改令,2026-07-26,lane B)。

AUTHORITY: docsv2/v2-复核-车道A-M0仪器迁移-2026-07-26.md §三/§四。
追因结论(复核判决实验,环境无关):±ω Floquet 支 6 重精确简并;简并子空间的
本征基是 LAPACK 的任意选择,逐模残差统计(resid_min/max、逐模贪心 j_hand)随基漂移,
**不是观测量**。真观测量 = 子空间对子空间的量:
  * 主角谱 {sin θ_i}(span(B₊) vs ker C;span(S_curv) vs ker C);
  * max sin θ(替代 resid_max);
  * Frobenius 泄漏 ||(I-P_kerC) B_on||_F = sqrt(Σ sin²θ_i)(旋转不变);
  * rms sin = frob/sqrt(m)(resid_mean 的严格不变量对应物);
  * ≥阈值主角计数(阈 = SIN_THRESH = 0.05 = SV_THRESH,预注册,整改令 1/2)。

本模块是**新代码路径**(整改令明文:不触碰任何 v1 冻结件;冻结脚本继续只读调用
取 U10/Q)。全部阈值/种子在此写死,运行后不回改:
  SIN_THRESH        = 0.05   (≥阈值主角计数 与 不变量 j_hand 的阈;同 SV_THRESH)
  ORTH_TOL          = 1e-9   (span 正交化的相对秩阈)
  PHASE_CLUSTER_TOL = 1e-9   (简并簇判定:|Δphase| < 1e-9,同 R36 简并证书量级)
  ROT_SEEDS         = (0,1,2)(基稳健性自检:3 次固定种子簇内酉旋转)
  DRIFT_TOL         = 1e-12  (不变量漂移门,整改令 3)
"""
from __future__ import annotations

import platform
import sys

import numpy as np

from . import frozen as FZ

SIN_THRESH = 0.05          # = R32.SV_THRESH(预注册,整改令 1/2;写死)
ORTH_TOL = 1e-9
PHASE_CLUSTER_TOL = 1e-9
ROT_SEEDS = (0, 1, 2)
DRIFT_TOL = 1e-12


# ==========================================================================
#  子空间原语(基不变)
# ==========================================================================
def orth(B: np.ndarray, tol: float = ORTH_TOL) -> np.ndarray:
    """span(B) 的正交规范基(SVD 秩截断;与列基选择无关,只依赖 span)。"""
    U, s, _ = np.linalg.svd(B, full_matrices=False)
    if s.size == 0:
        return U[:, :0]
    r = int(np.sum(s > tol * s[0]))
    return U[:, :r]


def principal_sines(P: np.ndarray, Q: np.ndarray) -> np.ndarray:
    """span(P) 相对 span(Q) 的主角正弦谱(升序)。
    实现:正交化后 R = P_on - Q_on (Q_on† P_on);svd(R) 的奇异值 = sin θ_i
    (小角度数值精确;对两侧任意基选择均不变)。"""
    Pn, Qn = orth(P), orth(Q)
    R = Pn - Qn @ (Qn.conj().T @ Pn)
    s = np.linalg.svd(R, compute_uv=False)
    return np.sort(np.clip(s, 0.0, 1.0))


def subspace_invariants(P: np.ndarray, Q: np.ndarray) -> dict:
    """span(P) vs span(Q) 的全套基不变读数。"""
    sines = principal_sines(P, Q)
    m = int(sines.size)
    frob = float(np.sqrt(np.sum(sines ** 2)))
    return {
        "dim_P": m,
        "sin_theta": [float(x) for x in sines],          # 升序全谱
        "max_sin_theta": float(sines[-1]) if m else 0.0,
        "frob_leak": frob,                               # sqrt(sum sin^2)
        "rms_sin": float(frob / np.sqrt(m)) if m else 0.0,
        "n_ge_thresh": int(np.sum(sines >= SIN_THRESH)),
        "sin_thresh": SIN_THRESH,
    }


# ==========================================================================
#  +ω 支不变量(σ 读数;整改令 1)
# ==========================================================================
def plus_branch_raw(k: np.ndarray, c: float):
    """冻结机器只读取数:ker C 基 Q(R37.kerC_basis 冻结代码对象)与
    +ω 支 LAPACK 列 Bpos(RC1a.walk_unit_modes_p 冻结代码对象)。
    返回 (Q, U10, phases, Bpos) 或 None(off-band)。"""
    R37 = FZ.mod("r37_residual_scaling_audit")
    RC = FZ.mod("rc1a_tensor_index_scan")
    Q = R37.kerC_basis(k, c)
    if Q is None:
        return None
    U10, phases, _ = RC.walk_unit_modes_p(k, R37.MU0, R37.TH0, 0.0, c)
    if U10.shape[1] == 0:
        return None
    Bpos = U10[:, phases > 1e-9]
    if Bpos.shape[1] == 0:
        return None
    return Q, U10, phases, Bpos


def plus_branch_invariants(k: np.ndarray, c: float):
    """span(B₊) vs ker C 的不变量读数(σ 机器主读数;None = off-band)。"""
    raw = plus_branch_raw(k, c)
    if raw is None:
        return None
    Q, _, _, Bpos = raw
    return subspace_invariants(Bpos, Q)


# ==========================================================================
#  基稳健性自检(整改令 3:3 次固定种子簇内酉旋转,不变量漂移 ≤ 1e-12)
# ==========================================================================
def rotate_within_clusters(U10: np.ndarray, phases: np.ndarray,
                           seed: int) -> np.ndarray:
    """按简并簇(|Δphase| < PHASE_CLUSTER_TOL)对本征列做固定种子随机酉旋转,
    模拟另一套 LAPACK 任意基(复核 §三 判决实验协议)。"""
    rng = np.random.default_rng(seed)
    Up = np.array(U10, copy=True)
    used = np.zeros(len(phases), bool)
    for i in range(len(phases)):
        if used[i]:
            continue
        cl = [j for j in range(len(phases))
              if abs(phases[j] - phases[i]) < PHASE_CLUSTER_TOL]
        for j in cl:
            used[j] = True
        if len(cl) > 1:
            Z = (rng.normal(size=(len(cl), len(cl)))
                 + 1j * rng.normal(size=(len(cl), len(cl))))
            V, _ = np.linalg.qr(Z)
            Up[:, cl] = U10[:, cl] @ V
    return Up


def _drift(inv_a: dict, inv_b: dict) -> float:
    """两套不变量读数的最大绝对漂移(谱逐元素 + 标量)。"""
    d = abs(inv_a["max_sin_theta"] - inv_b["max_sin_theta"])
    d = max(d, abs(inv_a["frob_leak"] - inv_b["frob_leak"]))
    d = max(d, abs(inv_a["rms_sin"] - inv_b["rms_sin"]))
    sa, sb = inv_a["sin_theta"], inv_b["sin_theta"]
    if len(sa) == len(sb):
        d = max(d, float(np.max(np.abs(np.array(sa) - np.array(sb))))
                if sa else 0.0)
    else:
        d = float("inf")
    if inv_a["n_ge_thresh"] != inv_b["n_ge_thresh"]:
        d = float("inf")
    return d


def plus_branch_basis_robustness(k: np.ndarray, c: float,
                                 seeds=ROT_SEEDS) -> dict:
    """+ω 支不变量在 3 次固定种子簇内酉旋转下的漂移(门 DRIFT_TOL)。"""
    raw = plus_branch_raw(k, c)
    if raw is None:
        return {"off_band": True}
    Q, U10, phases, Bpos = raw
    base = subspace_invariants(Bpos, Q)
    drifts = []
    for seed in seeds:
        Up = rotate_within_clusters(U10, phases, seed)
        Bp = Up[:, phases > 1e-9]
        drifts.append(_drift(base, subspace_invariants(Bp, Q)))
    return {"base": base, "seeds": list(seeds),
            "drift_per_seed": [float(x) for x in drifts],
            "max_drift": float(max(drifts)),
            "pass_drift_le_1e-12": bool(max(drifts) <= DRIFT_TOL)}


# ==========================================================================
#  环境入册(整改令 4)
# ==========================================================================
def environment_record() -> dict:
    """numpy 版本 + BLAS/LAPACK 后端字符串 + 平台谱系(selftest JSON 入册)。"""
    blas = lapack = "unknown"
    try:
        cfg = np.show_config(mode="dicts")
        dep = cfg.get("Build Dependencies", {})
        blas = str(dep.get("blas", {}).get("name", "unknown"))
        lapack = str(dep.get("lapack", {}).get("name", "unknown"))
    except TypeError:
        pass
    tp = None
    try:
        from threadpoolctl import threadpool_info
        tp = threadpool_info()
    except Exception:
        tp = "threadpoolctl unavailable"
    return {
        "numpy_version": np.__version__,
        "blas": blas, "lapack": lapack,
        "threadpoolctl": tp,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "lineage_note": ("宿主 = darwin/arm64 + Accelerate;冻结 r23_results.json "
                         "环境谱系 = 沙盒系 Linux/OpenBLAS(复核确证:与沙盒逐位 "
                         "diff=0.0,与宿主差 1.8e-15,ULP 级环境属性)"),
    }
